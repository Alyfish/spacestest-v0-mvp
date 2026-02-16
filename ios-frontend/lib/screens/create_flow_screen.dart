import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/scheduler.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
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

/// Full-screen route that manages the redesign flow.
/// Pushed from Home - completely separate from bottom navigation.
class CreateFlowScreen extends StatefulWidget {
  final bool isCamera;

  const CreateFlowScreen({super.key, this.isCamera = false});

  @override
  State<CreateFlowScreen> createState() => _CreateFlowScreenState();
}

class _CreateFlowScreenState extends State<CreateFlowScreen> {
  CreateFlowStep _currentStep = CreateFlowStep.uploadPhoto;
  ProductHotspot? _selectedHotspot;
  String? _pendingRetryFeedback;
  ValueNotifier<String?>? _analyzingSubtitleNotifier;
  List<String>? _pendingRecsToSelect;
  bool _pendingNeedsColorSave = false;
  bool _pendingNeedsStyleSave = false;

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
              (product['image_url'] ?? product['imageUrl'] ?? product['thumbnail'])
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
            const maxWait = Duration(seconds: 45);
            const pollInterval = Duration(seconds: 2);

            // Phase 1: Sync preferred stores (~500ms)
            await provider
                .ensurePreferredStoresSynced(context)
                .timeout(
                  const Duration(seconds: 5),
                  onTimeout: () => false,
                );

            // Phase 2: Ensure recommendations loaded
            // (likely already done — started at Choose Approach ~10-20s ago)
            await provider
                .ensureRecommendationsLoaded(context)
                .timeout(
                  const Duration(seconds: 15),
                  onTimeout: () => false,
                );

            // Phase 3: Ensure search job is running
            final searchRecs = provider.productRecommendations;
            if (searchRecs.isNotEmpty) {
              unawaited(
                provider.ensureSearchJobStarted(null, searchRecs),
              );
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

              await Future.wait([
                provider.refreshProductSuggestionsSnapshot(context),
                provider.preloadTrendingProducts(context),
              ]);

              if (provider.hasImageBackedSuggestions) break;

              final remaining = deadline.difference(DateTime.now());
              if (remaining <= Duration.zero) break;
              await Future.delayed(
                remaining < pollInterval ? remaining : pollInterval,
              );
            }

            // Phase 5: Pre-cache product images so they display instantly
            if (provider.hasImageBackedSuggestions) {
              _analyzingSubtitleNotifier?.value = 'Preparing your results...';
              try {
                final imageUrls = _extractProductImageUrls(provider);
                if (imageUrls.isNotEmpty && mounted) {
                  await Future.wait(
                    imageUrls.take(8).map(
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
        return ImprovementsScreen(
          onBack: _goBack,
          onImprove: (recsToSelect, needsColorSave, needsStyleSave) {
            _pendingRecsToSelect = recsToSelect;
            _pendingNeedsColorSave = needsColorSave;
            _pendingNeedsStyleSave = needsStyleSave;
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
          onComplete: () => _goToStep(CreateFlowStep.dreamSpace),
          asyncWork: () async {
            final provider = Provider.of<ProjectProvider>(
              context,
              listen: false,
            );

            // Phase 0: Run pending saves in parallel (deferred from ImprovementsScreen)
            final saveFutures = <Future<bool>>[];
            if (_pendingNeedsColorSave) {
              saveFutures.add(provider.saveColorPalette(
                context, 'ai_decide', 'Let AI Decide', [],
                letAiDecide: true, background: false,
              ));
            }
            if (_pendingNeedsStyleSave) {
              saveFutures.add(provider.saveDesignStyle(
                context, 'ai_decide', 'Let AI Decide',
                letAiDecide: true, background: false,
              ));
            }
            if (_pendingRecsToSelect != null && _pendingRecsToSelect!.isNotEmpty) {
              saveFutures.add(provider.setSelectedRecommendations(context, _pendingRecsToSelect!));
            }
            final safeFutures = saveFutures.map((f) async {
              try {
                return await f;
              } catch (e, st) {
                debugPrint('[DEFERRED_SAVE] Save failed (non-blocking): $e');
                debugPrint('$st');
                return false;
              }
            }).toList();
            if (safeFutures.isNotEmpty) {
              await Future.wait(safeFutures);
            }
            _pendingRecsToSelect = null;
            _pendingNeedsColorSave = false;
            _pendingNeedsStyleSave = false;

            if (provider.productRecommendations.isEmpty) {
              final recommendationsReady = await provider
                  .ensureRecommendationsLoaded(context);
              if (!mounted) return;
              if (!recommendationsReady) {
                throw Exception(
                  provider.errorMessage ??
                      'Still preparing recommendations. Please try again in a moment.',
                );
              }
            }
            final isRetry =
                _pendingRetryFeedback != null &&
                _pendingRetryFeedback!.trim().isNotEmpty;
            final success = isRetry
                ? await provider.retryDesignImage(
                    _pendingRetryFeedback!,
                    onRetrying: () => _analyzingSubtitleNotifier?.value = 'Reconnecting...',
                  )
                : await provider.generateDesignImage(
                    onRetrying: () => _analyzingSubtitleNotifier?.value = 'Reconnecting...',
                  );
            _analyzingSubtitleNotifier?.value = null;
            if (!success) {
              throw Exception(
                provider.errorMessage ?? 'Failed to generate design image',
              );
            }
            _pendingRetryFeedback = null;
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
              onRetrying: () => _analyzingSubtitleNotifier?.value = 'Reconnecting...',
            );
            _analyzingSubtitleNotifier?.value = null;
            if (!success) {
              throw Exception(
                provider.errorMessage ?? 'Failed to generate inspired design',
              );
            }
          },
        );

      case CreateFlowStep.dreamSpace:
        return DreamSpaceScreen(
          onRetry: () => _goToStep(CreateFlowStep.describeChanges),
          onRestart: () => _goToStep(CreateFlowStep.uploadPhoto),
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
