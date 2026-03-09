import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/scheduler.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../providers/subscription_provider.dart';
import '../services/api_service.dart';
import '../services/notification_service.dart';
import '../services/supabase_service.dart';
import '../theme.dart';
import '../utils/logger.dart';
import '../widgets/app_bottom_nav_bar.dart';

// Import all flow screens
import 'upload_photo_screen.dart';
import 'confirm_selection_screen.dart';
import 'choose_space_screen.dart';
import 'describe_custom_space_screen.dart';
import 'choose_items_screen.dart';
import 'upload_inspiration_screen.dart';
import 'confirm_inspiration_screen.dart';
import 'choose_approach_screen.dart';
import 'preferred_stores_screen.dart';
import 'analyzing_screen.dart';
import 'improvements_screen.dart';
import 'main_navigation_screen.dart';
import 'dream_space_screen.dart';
import 'choose_products_screen.dart';
import 'describe_changes_screen.dart';
import '../models/shop_product.dart';

/// Enum representing each step in the create/redesign flow
enum CreateFlowStep {
  uploadPhoto, // Step 1
  confirmSelection, // Step 2
  chooseSpace, // Step 3
  describeCustomSpace, // Step 3 (conditional)
  chooseItems, // Step 4
  chooseApproach, // Step 5
  preferredStores, // Step 6
  analyzing, // Step 7
  improvements, // Step 8
  improvementsAnalyzing, // Step 9 (after clicking Improve)
  dreamSpace, // Step 10 (generated room with hotspots)
  chooseProducts, // Step 11 (product grid for selected hotspot)
  describeChanges, // Step 12 (retry - describe changes)
  // Inspiration steps
  uploadInspiration,
  confirmInspiration,
  inspirationAnalyzing, // Direct inspiration → generation (skips recs/improvements)
}

/// Map a backend project status string to the correct CreateFlowStep for resumption.
CreateFlowStep stepForProjectStatus(String status) {
  switch (status) {
    case 'NEW':
      return CreateFlowStep.uploadPhoto;
    case 'BASE_IMAGE_UPLOADED':
      return CreateFlowStep.chooseSpace;
    case 'SPACE_TYPE_SELECTED':
      return CreateFlowStep.chooseItems;
    case 'IMPROVEMENT_MARKERS_SAVED':
    case 'MARKER_RECOMMENDATIONS_READY':
      return CreateFlowStep.chooseApproach;
    case 'INSPIRATION_IMAGES_UPLOADED':
    case 'INSPIRATION_RECOMMENDATIONS_READY':
      return CreateFlowStep.inspirationAnalyzing;
    case 'PRODUCT_RECOMMENDATIONS_READY':
    case 'PRODUCT_RECOMMENDATIONS_SELECTED':
    case 'PRODUCT_SEARCH_STARTED':
    case 'PRODUCT_SEARCH_COMPLETE':
    case 'PRODUCT_SELECTED':
      return CreateFlowStep.improvements;
    case 'IMAGE_GENERATED':
    case 'INSPIRATION_REDESIGN_COMPLETE':
      return CreateFlowStep.dreamSpace;
    default:
      return CreateFlowStep.uploadPhoto;
  }
}

/// Full-screen route that manages the redesign flow.
/// Pushed from Home - completely separate from bottom navigation.
class CreateFlowScreen extends StatefulWidget {
  final bool isCamera;
  final CreateFlowStep? startStep;

  const CreateFlowScreen({super.key, this.isCamera = false, this.startStep});

  @override
  State<CreateFlowScreen> createState() => _CreateFlowScreenState();
}

class _CreateFlowScreenState extends State<CreateFlowScreen> {
  late CreateFlowStep _currentStep;
  ProductHotspot? _selectedHotspot;
  String? _pendingRetryFeedback;
  ValueNotifier<String?>? _analyzingSubtitleNotifier;
  List<String>? _pendingRecsToSelect;
  Map<String, dynamic>? _pendingColorPalette;
  Map<String, dynamic>? _pendingStyleData;
  List<Map<String, dynamic>>? _pendingTrendingItems;
  final Set<String> _notifyPromptShownJobIds = <String>{};
  bool _generationComplete = false;
  bool _isRestarting = false;

  // PERF timing
  int? _flowStartMs;
  int? _improvementsShownMs;

  @override
  void initState() {
    super.initState();
    _currentStep = widget.startStep ?? CreateFlowStep.uploadPhoto;
  }

  @override
  void dispose() {
    _analyzingSubtitleNotifier?.dispose();
    super.dispose();
  }

  void _setFlowState(VoidCallback fn) {
    if (!mounted) return;
    final phase = SchedulerBinding.instance.schedulerPhase;
    final isBuilding =
        phase == SchedulerPhase.transientCallbacks ||
        phase == SchedulerPhase.midFrameMicrotasks ||
        phase == SchedulerPhase.persistentCallbacks;
    if (isBuilding) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(fn);
      });
      return;
    }
    setState(fn);
  }

  void _goToStep(CreateFlowStep step) {
    _setFlowState(() => _currentStep = step);
  }

  void _goToProducts(ProductHotspot hotspot) {
    _setFlowState(() {
      _selectedHotspot = hotspot;
      _currentStep = CreateFlowStep.chooseProducts;
    });
  }

  List<String> _extractProductImageUrls(ProjectProvider provider) {
    final urls = <String>[];
    void extract(Map<String, dynamic>? payload) {
      if (payload == null) return;
      final categories = payload['categories'] as List? ?? const [];
      for (final raw in categories) {
        if (raw is! Map) continue;
        final products = raw['products'] as List? ?? const [];
        for (final product in products) {
          if (product is! Map) continue;
          final url =
              (product['image_url'] ??
                      product['imageUrl'] ??
                      product['thumbnail'])
                  ?.toString()
                  .trim();
          if (url != null && url.isNotEmpty) urls.add(url);
        }
      }
    }

    extract(provider.productSuggestions);
    extract(provider.trendingProducts);
    return urls;
  }

  Future<void> _maybePromptNotifyWhenReady(ProjectProvider provider) async {
    final jobId = provider.currentJobId;
    final projectId = provider.currentProject?.id;
    if (!mounted || jobId == null || projectId == null) return;
    if (_notifyPromptShownJobIds.contains(jobId)) return;
    _notifyPromptShownJobIds.add(jobId);

    final action = await showDialog<_NotifyWhenReadyAction>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Tell me when to come back!'),
          content: const Text(
            'We can notify your phone as soon as your design is ready.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(
                dialogContext,
              ).pop(_NotifyWhenReadyAction.notNow),
              child: const Text('Not now'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(
                dialogContext,
              ).pop(_NotifyWhenReadyAction.notifyMe),
              child: const Text('Notify me'),
            ),
          ],
        );
      },
    );

    if (!mounted || action != _NotifyWhenReadyAction.notifyMe) return;

    final authToken = SupabaseService.accessToken;
    if (authToken == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Please sign in to enable notifications.'),
          ),
        );
      }
      return;
    }

    final registration =
        await NotificationService.requestPermissionAndGetToken();
    if (registration == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Notifications are disabled. Enable them in settings to get alerts.',
            ),
          ),
        );
      }
      return;
    }

    try {
      final response = await ApiService.notifyWhenReady(
        projectId,
        jobId,
        authToken,
        deviceToken: registration.token,
        platform: registration.platform,
      );
      final status = (response['status'] ?? 'registered').toString();
      final message = status == 'already_done'
          ? 'Your design is already ready.'
          : 'Great, we will notify you when your design is ready.';
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(message)));
      }
    } catch (e) {
      AppLogger.error('Failed to register notify-when-ready', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not register notification. Please try again.'),
          ),
        );
      }
    }
  }

  void _goBack() {
    switch (_currentStep) {
      case CreateFlowStep.uploadPhoto:
        Navigator.of(context).pop(); // Exit flow
        break;
      case CreateFlowStep.confirmSelection:
        _goToStep(CreateFlowStep.uploadPhoto);
        break;
      case CreateFlowStep.chooseSpace:
        _goToStep(CreateFlowStep.confirmSelection);
        break;
      case CreateFlowStep.describeCustomSpace:
        _goToStep(CreateFlowStep.chooseSpace);
        break;
      case CreateFlowStep.chooseItems:
        // Check if user came from custom space
        final provider = Provider.of<ProjectProvider>(context, listen: false);
        if (provider.currentProject?.spaceChosen == 'other') {
          _goToStep(CreateFlowStep.describeCustomSpace);
        } else {
          _goToStep(CreateFlowStep.chooseSpace);
        }
        break;
      case CreateFlowStep.chooseApproach:
        _goToStep(CreateFlowStep.chooseItems);
        break;
      case CreateFlowStep.uploadInspiration:
        _goToStep(CreateFlowStep.chooseApproach);
        break;
      case CreateFlowStep.confirmInspiration:
        _goToStep(CreateFlowStep.uploadInspiration);
        break;
      case CreateFlowStep.preferredStores:
        _goToStep(CreateFlowStep.chooseApproach);
        break;
      case CreateFlowStep.analyzing:
        _goToStep(CreateFlowStep.preferredStores);
        break;
      case CreateFlowStep.improvements:
        _goToStep(CreateFlowStep.preferredStores);
        break;
      case CreateFlowStep.improvementsAnalyzing:
        _goToStep(CreateFlowStep.improvements);
        break;
      case CreateFlowStep.inspirationAnalyzing:
        _goToStep(CreateFlowStep.confirmInspiration);
        break;
      case CreateFlowStep.dreamSpace:
        // Can't go back from dream space - it's the result
        // User should use Restart button instead
        break;
      case CreateFlowStep.chooseProducts:
        _goToStep(CreateFlowStep.dreamSpace);
        break;
      case CreateFlowStep.describeChanges:
        _goToStep(CreateFlowStep.dreamSpace);
        break;
    }
  }

  void _handleNavTap(int index) {
    if (index == 2) return; // FAB position
    if (index == 1) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.lock_outline, color: Colors.white, size: 18),
              const SizedBox(width: 12),
              Text(
                'Coming soon',
                style: AppTheme.dmSans(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.white,
                ),
              ),
            ],
          ),
          backgroundColor: AppTheme.textSecondary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          margin: const EdgeInsets.all(16),
          duration: const Duration(seconds: 2),
        ),
      );
      return;
    }
    // Navigate to main navigation (home/saved/profile)
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
      (route) => false,
    );
  }

  Future<void> _handleFabPressed() async {
    try {
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      await projectProvider.createProject(context);
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
          (route) => false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  /// Check if the current step already has its own Scaffold with nav bar
  bool _stepHasOwnScaffold(CreateFlowStep step) {
    return step == CreateFlowStep.improvements ||
        step == CreateFlowStep.improvementsAnalyzing ||
        step == CreateFlowStep.analyzing ||
        step == CreateFlowStep.inspirationAnalyzing ||
        step == CreateFlowStep.dreamSpace ||
        step == CreateFlowStep.chooseProducts ||
        step == CreateFlowStep.describeChanges;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _currentStep == CreateFlowStep.uploadPhoto,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _goBack();
        }
      },
      child: _stepHasOwnScaffold(_currentStep)
          ? _buildCurrentStep()
          : Scaffold(
              backgroundColor: AppTheme.scaffoldBackground,
              body: SafeArea(bottom: false, child: _buildCurrentStep()),
              bottomNavigationBar: AppBottomNavBar(
                selectedIndex: 0,
                onItemTapped: _handleNavTap,
                onFabPressed: _handleFabPressed,
              ),
            ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case CreateFlowStep.uploadPhoto:
        return UploadPhotoContent(
          isCamera: widget.isCamera,
          onBack: _goBack,
          onConfirmSelection: () => _goToStep(CreateFlowStep.confirmSelection),
        );

      case CreateFlowStep.confirmSelection:
        return ConfirmSelectionContent(
          onBack: _goBack,
          onSuccess: () {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            // Start fetching any existing trending payload as soon as base image is uploaded.
            unawaited(provider.preloadTrendingProducts());
            _goToStep(CreateFlowStep.chooseSpace);
          },
        );

      case CreateFlowStep.chooseSpace:
        return ChooseSpaceContent(
          onBack: _goBack,
          onContinue: () {
            // Check if custom space was selected
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            if (provider.currentProject?.spaceChosen == 'other') {
              _goToStep(CreateFlowStep.describeCustomSpace);
            } else {
              _goToStep(CreateFlowStep.chooseItems);
            }
          },
        );

      case CreateFlowStep.describeCustomSpace:
        return DescribeCustomSpaceScreen(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.chooseItems),
        );

      case CreateFlowStep.chooseItems:
        return ChooseItemsContent(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.chooseApproach),
        );

      case CreateFlowStep.uploadInspiration:
        return UploadInspirationContent(
          onBack: _goBack,
          onConfirmSelection: () =>
              _goToStep(CreateFlowStep.confirmInspiration),
          onSkipToApproach: () => _goToStep(CreateFlowStep.chooseApproach),
        );

      case CreateFlowStep.confirmInspiration:
        return ConfirmInspirationContent(
          onBack: _goBack,
          onSuccess: () => _goToStep(CreateFlowStep.inspirationAnalyzing),
        );

      case CreateFlowStep.chooseApproach:
        return ChooseApproachContent(
          onBack: _goBack,
          onContinue: () {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            if (provider.approach == 'inspiration') {
              _goToStep(CreateFlowStep.uploadInspiration);
            } else {
              // Fire recommendations early — they only need base_image,
              // space_type, markers, and improvement_mode (all saved by now).
              // Gives ~10-20s head start while user picks stores.
              unawaited(provider.ensureRecommendationsLoaded(context));
              _goToStep(CreateFlowStep.preferredStores);
            }
          },
        );

      case CreateFlowStep.preferredStores:
        return PreferredStoresContent(
          onBack: _goBack,
          onContinue: () {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            // Start recommendation generation early, but avoid additional
            // trending/search prewarm contention at this stage.
            unawaited(provider.ensureRecommendationsLoaded(context));
            _goToStep(CreateFlowStep.analyzing);
          },
        );

      case CreateFlowStep.analyzing:
        _analyzingSubtitleNotifier ??= ValueNotifier<String?>(null);
        return AnalyzingScreen(
          onBack: _goBack,
          onComplete: () => _goToStep(CreateFlowStep.improvements),
          subtitleNotifier: _analyzingSubtitleNotifier,
          asyncWork: () async {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            final stopwatch = Stopwatch()..start();
            const maxWait = Duration(seconds: 120);

            _flowStartMs ??= DateTime.now().millisecondsSinceEpoch;
            AppLogger.info('PERF_IOS analyzing_start');

            // Phases 1+2 in parallel — blocks max(5s, 15s) instead of 5s+15s
            final storeSync = provider
                .ensurePreferredStoresSynced(context)
                .timeout(const Duration(seconds: 5), onTimeout: () => false);

            final recsLoad = provider
                .ensureRecommendationsLoaded(context)
                .timeout(const Duration(seconds: 15), onTimeout: () => false);

            await Future.wait([storeSync, recsLoad]);

            if (!mounted) return;

            AppLogger.info(
              'PERF_IOS phases_1_2_done_ms=${DateTime.now().millisecondsSinceEpoch - _flowStartMs!}',
            );

            // Phase 3: Ensure search job is running (AFTER recs — needs productRecommendations)
            final searchRecs = provider.productRecommendations;
            if (searchRecs.isNotEmpty) {
              unawaited(provider.ensureSearchJobStarted(null, searchRecs));
            }

            // Phase 4: Poll until image-backed products are ready.
            // This is the GATE — we stay on the analyzing screen until
            // products arrive or we hit the 45s max timeout.
            final deadline = DateTime.now().add(maxWait);

            while (!provider.hasImageBackedSuggestions &&
                DateTime.now().isBefore(deadline)) {
              final elapsed = stopwatch.elapsed;
              if (elapsed.inSeconds > 25) {
                _analyzingSubtitleNotifier?.value = 'Almost there...';
              } else if (elapsed.inSeconds > 10) {
                _analyzingSubtitleNotifier?.value =
                    'Finding your perfect products...';
              }

              if (!mounted) return;
              await Future.wait([
                provider.refreshProductSuggestionsSnapshot(context),
                provider.preloadTrendingProducts(context),
              ]);

              if (provider.hasImageBackedSuggestions) break;

              // Adaptive polling: 1s for first 20s, 2s after
              final pollInterval = stopwatch.elapsed.inSeconds < 20
                  ? const Duration(seconds: 1)
                  : const Duration(seconds: 2);

              final remaining = deadline.difference(DateTime.now());
              if (remaining <= Duration.zero) break;
              await Future.delayed(
                remaining < pollInterval ? remaining : pollInterval,
              );
            }

            if (provider.hasImageBackedSuggestions) {
              AppLogger.info(
                'PERF_IOS products_ready_ms=${DateTime.now().millisecondsSinceEpoch - _flowStartMs!}',
              );
            }

            // Phase 5: Pre-cache product images so they display instantly
            if (provider.hasImageBackedSuggestions) {
              _analyzingSubtitleNotifier?.value = 'Preparing your results...';
              try {
                final imageUrls = _extractProductImageUrls(provider);
                if (imageUrls.isNotEmpty && mounted) {
                  await Future.wait(
                    imageUrls
                        .take(8)
                        .map(
                          (url) => precacheImage(NetworkImage(url), context),
                        ),
                  ).timeout(
                    const Duration(seconds: 5),
                    onTimeout: () => <void>[],
                  );
                }
              } catch (e) {
                AppLogger.warning('Image pre-cache failed (non-fatal): $e');
              }
            } else {
              AppLogger.warning(
                'Analyzing timed out after ${stopwatch.elapsed.inSeconds}s '
                'waiting for image-backed suggestions; transitioning anyway.',
              );
            }
          },
        );

      case CreateFlowStep.improvements:
        _improvementsShownMs = DateTime.now().millisecondsSinceEpoch;

        // Pre-warm image generation after a settle delay (800ms).
        // Guards: must be mounted, must have recs AND selections, 800ms prevents waste on rapid tap-through.
        final prewarmProvider = Provider.of<ProjectProvider>(
          context,
          listen: false,
        );
        if (prewarmProvider.productRecommendations.isNotEmpty &&
            prewarmProvider.selectedRecommendations.isNotEmpty) {
          Future.delayed(const Duration(milliseconds: 800), () {
            if (mounted) {
              Provider.of<ProjectProvider>(
                context,
                listen: false,
              ).startPrewarmGeneration();
            }
          });
        }

        return ImprovementsScreen(
          onBack: _goBack,
          onImprove: (recsToSelect, pendingColorPalette, pendingStyleData, trendingItems) {
            _pendingRecsToSelect = recsToSelect;
            _pendingColorPalette = pendingColorPalette;
            _pendingStyleData = pendingStyleData;
            _pendingTrendingItems = trendingItems.isNotEmpty ? trendingItems : null;
            _goToStep(CreateFlowStep.improvementsAnalyzing);
          },
        );

      case CreateFlowStep.improvementsAnalyzing:
        _analyzingSubtitleNotifier ??= ValueNotifier<String?>(null);
        return AnalyzingScreen(
          onBack: _goBack,
          title: 'Redesigning Your Space and\nFinding Products..',
          subtitle: 'Please wait a moment while we prepare\nyour new space',
          subtitleNotifier: _analyzingSubtitleNotifier,
          onComplete: () {
            AppLogger.info(
              'PERF_IOS dream_space_navigate_total_ms='
              '${DateTime.now().millisecondsSinceEpoch - (_flowStartMs ?? 0)}',
            );
            _goToStep(CreateFlowStep.dreamSpace);
          },
          asyncWork: () async {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );

            final improvementsTimeMs =
                DateTime.now().millisecondsSinceEpoch -
                (_improvementsShownMs ?? 0);
            AppLogger.info('PERF_IOS improvements_time_ms=$improvementsTimeMs');
            AppLogger.info(
              'PERF_IOS improvements_analyzing_start_ms='
              '${DateTime.now().millisecondsSinceEpoch - (_flowStartMs ?? 0)}',
            );

            // Phase 0a: Force-invalidate prewarm early if any saves are pending
            // (we know saves will change the fingerprint, no point letting prewarm run)
            if (_pendingColorPalette != null ||
                _pendingStyleData != null ||
                _pendingTrendingItems != null ||
                (_pendingRecsToSelect != null &&
                    _pendingRecsToSelect!.isNotEmpty)) {
              provider.forceInvalidatePrewarm();
            }

            // Phase 0b: Run pending saves in parallel (deferred from ImprovementsScreen)
            final saveOperations = <String, Future<bool> Function()>{};
            if (_pendingColorPalette != null) {
              final cp = _pendingColorPalette!;
              saveOperations['color'] = () => provider.saveColorPalette(
                context,
                cp['id'] as String,
                cp['name'] as String,
                List<String>.from(cp['hexColors'] as List? ?? []),
                letAiDecide: cp['letAiDecide'] == true,
                background: false,
              );
            }
            if (_pendingStyleData != null) {
              final sd = _pendingStyleData!;
              saveOperations['style'] = () => provider.saveDesignStyle(
                context,
                sd['id'] as String,
                sd['name'] as String,
                letAiDecide: sd['letAiDecide'] == true,
                background: false,
              );
            }
            if (_pendingRecsToSelect != null &&
                _pendingRecsToSelect!.isNotEmpty) {
              saveOperations['selected_recommendations'] = () => provider
                  .setSelectedRecommendations(context, _pendingRecsToSelect!);
            }
            if (_pendingTrendingItems != null &&
                _pendingTrendingItems!.isNotEmpty) {
              saveOperations['trending_products'] = () => provider
                  .saveSelectedTrendingProducts(context, _pendingTrendingItems!);
            }

            Future<Map<String, bool>> runSavePass(
              List<String> keys,
              String phase,
            ) async {
              final entries = await Future.wait(
                keys.map((key) async {
                  final operation = saveOperations[key];
                  if (operation == null) return MapEntry(key, true);
                  try {
                    final ok = await operation();
                    return MapEntry(key, ok);
                  } catch (e, st) {
                    debugPrint(
                      '[DEFERRED_SAVE] Save failed ($phase, $key): $e',
                    );
                    debugPrint('$st');
                    return MapEntry(key, false);
                  }
                }),
              );
              return Map<String, bool>.fromEntries(entries);
            }

            if (saveOperations.isNotEmpty) {
              final pendingKeys = saveOperations.keys.toList();
              AppLogger.info(
                '[gen_ctx_sync] start pending=${pendingKeys.join(",")}',
              );

              final firstPassResults = await runSavePass(
                pendingKeys,
                'first_pass',
              );
              final firstPassFailed = firstPassResults.entries
                  .where((entry) => entry.value == false)
                  .map((entry) => entry.key)
                  .toList();
              AppLogger.info(
                '[gen_ctx_sync] first_pass '
                'success=${pendingKeys.length - firstPassFailed.length} '
                'failed=${firstPassFailed.length}',
              );

              if (firstPassFailed.isNotEmpty) {
                AppLogger.warning(
                  '[gen_ctx_sync] retry_pass pending=${firstPassFailed.join(",")}',
                );
                final retryPassResults = await runSavePass(
                  firstPassFailed,
                  'retry_pass',
                );
                final retryStillFailed = retryPassResults.entries
                    .where((entry) => entry.value == false)
                    .map((entry) => entry.key)
                    .toList();
                AppLogger.info(
                  '[gen_ctx_sync] retry_pass '
                  'success=${firstPassFailed.length - retryStillFailed.length} '
                  'failed=${retryStillFailed.length}',
                );
                if (retryStillFailed.isNotEmpty) {
                  AppLogger.warning(
                    '[gen_ctx_sync] proceed_with_partial '
                    'failed=${retryStillFailed.join(",")}',
                  );
                }
              }
            }

            _pendingRecsToSelect = null;
            _pendingColorPalette = null;
            _pendingStyleData = null;
            _pendingTrendingItems = null;

            // Invalidate pre-warm if saves changed the inputs
            provider.invalidatePrewarmIfStale();

            if (!mounted) return;
            if (provider.productRecommendations.isEmpty) {
              final isIterative = provider.approach == 'iterative';
              final markerCount = provider.markers.length;
              final canSkip = isIterative && markerCount > 0;

              final ok = await provider
                  .ensureRecommendationsLoaded(context)
                  .timeout(
                    const Duration(seconds: 15),
                    onTimeout: () {
                      AppLogger.warning(
                        'PERF_IOS recs_timeout_15s isIterative=$isIterative markerCount=$markerCount',
                      );
                      return false;
                    },
                  );
              if (!mounted) return;
              if (!ok) {
                if (canSkip) {
                  AppLogger.info(
                    'PERF_IOS iterative_skip_recs markerCount=$markerCount',
                  );
                } else {
                  throw Exception(
                    provider.errorMessage ??
                        'Still preparing recommendations. Please try again in a moment.',
                  );
                }
              }
            }

            AppLogger.info(
              'PERF_IOS pre_generation approach=${provider.approach} '
              'markerCount=${provider.markers.length} '
              'recsCount=${provider.productRecommendations.length} '
              'selectedRecsCount=${provider.selectedRecommendations.length} '
              'projectId=${provider.currentProject?.id}',
            );

            final isRetry =
                _pendingRetryFeedback != null &&
                _pendingRetryFeedback!.trim().isNotEmpty;

            _generationComplete = false;

            // Show notification prompt after 15s if still generating
            Future<void>.delayed(const Duration(seconds: 15), () {
              if (!_generationComplete && mounted) {
                _maybePromptNotifyWhenReady(provider);
              }
            });

            late final bool success;
            try {
              success =
                  await (isRetry
                          ? provider.retryDesignImage(
                              _pendingRetryFeedback!,
                              onRetrying: () =>
                                  _analyzingSubtitleNotifier?.value =
                                      'Reconnecting...',
                            )
                          : provider.generateDesignImage(
                              onRetrying: () =>
                                  _analyzingSubtitleNotifier?.value =
                                      'Reconnecting...',
                            ))
                      .timeout(
                        const Duration(seconds: 120),
                        onTimeout: () {
                          AppLogger.warning(
                            'PERF_IOS design_generation_timeout after 120s — proceeding to DreamSpace',
                          );
                          return false; // NOT a failure — just a timeout
                        },
                      );
            } on PaywallRequiredException {
              if (mounted) {
                final subProvider = Provider.of<SubscriptionProvider>(context, listen: false);
                await subProvider.showPaywall(source: 'server_402_retry');
                _goToStep(CreateFlowStep.dreamSpace);
              }
              return;
            }

            _generationComplete = true;

            final prewarmReused = provider.lastPrewarmReused;
            AppLogger.info(
              'PERF_IOS design_image_done_ms='
              '${DateTime.now().millisecondsSinceEpoch - (_flowStartMs ?? 0)} '
              'prewarm_reused=$prewarmReused success=$success',
            );

            _analyzingSubtitleNotifier?.value = null;

            // Distinguish timeout (job alive) from real failure (no job)
            if (!success && provider.currentJobId != null) {
              // TIMEOUT path: job still running on backend, proceed to DreamSpace.
              // Do NOT throw, do NOT clear job_id — DreamSpace will pick up polling.
              // (onComplete fires next → navigates to DreamSpace with loading overlay)
            } else if (!success) {
              // REAL FAILURE: no job_id means the job never started or truly failed
              throw Exception(
                provider.errorMessage ?? 'Failed to generate design image',
              );
            }

            // Optimistic usage counter bump
            if (success && mounted) {
              final subProvider = Provider.of<SubscriptionProvider>(context, listen: false);
              if (isRetry) {
                subProvider.recordIterationUsed();
              }
            }
            _pendingRetryFeedback = null;

            // Pre-decode generated image so DreamSpaceScreen mounts without jank
            if (provider.generatedImageUrl != null && mounted) {
              try {
                await precacheImage(
                  NetworkImage(provider.generatedImageUrl!),
                  context,
                ).timeout(const Duration(seconds: 3), onTimeout: () {});
              } catch (_) {}
            } else if (provider.generatedImageBytes != null && mounted) {
              try {
                await precacheImage(
                  MemoryImage(provider.generatedImageBytes!),
                  context,
                ).timeout(const Duration(milliseconds: 500), onTimeout: () {});
              } catch (_) {}
            }
          },
        );

      case CreateFlowStep.inspirationAnalyzing:
        _analyzingSubtitleNotifier ??= ValueNotifier<String?>(null);
        return AnalyzingScreen(
          onBack: _goBack,
          title: 'Creating Your Inspired\nDesign..',
          subtitle: 'We\'re redesigning your room to match\nyour inspiration',
          subtitleNotifier: _analyzingSubtitleNotifier,
          onComplete: () => _goToStep(CreateFlowStep.dreamSpace),
          asyncWork: () async {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );
            if (!mounted) return;
            final success = await provider.generateInspirationDirectly(
              context,
              onRetrying: () =>
                  _analyzingSubtitleNotifier?.value = 'Reconnecting...',
            );
            _analyzingSubtitleNotifier?.value = null;
            if (!success) {
              throw Exception(
                provider.errorMessage ?? 'Failed to generate inspired design',
              );
            }

            // Pre-decode generated image so DreamSpaceScreen mounts without jank
            if (provider.generatedImageUrl != null && mounted) {
              try {
                await precacheImage(
                  NetworkImage(provider.generatedImageUrl!),
                  context,
                ).timeout(const Duration(seconds: 3), onTimeout: () {});
              } catch (_) {}
            } else if (provider.generatedImageBytes != null && mounted) {
              try {
                await precacheImage(
                  MemoryImage(provider.generatedImageBytes!),
                  context,
                ).timeout(const Duration(milliseconds: 500), onTimeout: () {});
              } catch (_) {}
            }
          },
        );

      case CreateFlowStep.dreamSpace:
        return DreamSpaceScreen(
          onRetry: () async {
            final subProvider = Provider.of<SubscriptionProvider>(context, listen: false);
            final allowed = await subProvider.ensureCanIterate(source: 'dream_space_retry');
            if (!allowed || !mounted) return;
            _goToStep(CreateFlowStep.describeChanges);
          },
          onRestart: () async {
            if (_isRestarting || !mounted) return;
            setState(() => _isRestarting = true);
            try {
              final subProvider = Provider.of<SubscriptionProvider>(context, listen: false);
              final allowed = await subProvider.ensureCanGenerate(source: 'dream_space_restart');
              if (!allowed || !mounted) return;

              final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
              try {
                final ok = await projectProvider.createProject(context);
                if (!ok || !mounted) return;
                subProvider.recordGenerationUsed();

                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    builder: (_) => CreateFlowScreen(isCamera: widget.isCamera),
                    fullscreenDialog: true,
                  ),
                );
              } on PaywallRequiredException {
                if (mounted) await subProvider.showPaywall(source: 'server_402_restart');
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Failed to restart: ${e.toString()}'),
                      backgroundColor: AppTheme.errorColor,
                    ),
                  );
                }
              }
            } finally {
              if (mounted) setState(() => _isRestarting = false);
            }
          },
          onHotspotTap: _goToProducts,
        );

      case CreateFlowStep.chooseProducts:
        return ChooseProductsScreen(
          hotspot:
              _selectedHotspot ??
              const ProductHotspot(
                id: 'default',
                x: 0.5,
                y: 0.5,
                itemType: 'item',
                label: 'Product',
              ),
          onBack: () => _goToStep(CreateFlowStep.dreamSpace),
        );

      case CreateFlowStep.describeChanges:
        return DescribeChangesScreen(
          onBack: () => _goToStep(CreateFlowStep.dreamSpace),
          onSubmit: (feedback) {
            _setFlowState(() {
              _pendingRetryFeedback = feedback;
              _currentStep = CreateFlowStep.improvementsAnalyzing;
            });
          },
        );
    }
  }
}

enum _NotifyWhenReadyAction { notNow, notifyMe }
