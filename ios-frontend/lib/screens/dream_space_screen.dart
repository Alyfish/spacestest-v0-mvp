import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/shop_product.dart';
import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../theme.dart';
import '../utils/logger.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/interactive_image_widget.dart';
import '../constants/feature_flags.dart';
import 'main_navigation_screen.dart';

/// Dream Space Screen - Shows the generated room with tappable product hotspots
class DreamSpaceScreen extends StatefulWidget {
  final VoidCallback? onRetry;
  final VoidCallback? onRestart;
  final Function(ProductHotspot)? onHotspotTap;

  const DreamSpaceScreen({
    super.key,
    this.onRetry,
    this.onRestart,
    this.onHotspotTap,
  });

  @override
  State<DreamSpaceScreen> createState() => _DreamSpaceScreenState();
}

class _DreamSpaceScreenState extends State<DreamSpaceScreen>
    with SingleTickerProviderStateMixin {
  final PageController _pageController = PageController();

  // Background generation polling state
  bool _pollingStarted = false;
  bool _disposed = false;
  String? _localPhase;
  int _localProgress = 0;
  late AnimationController _shimmerController;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    // Check if we need to poll for a still-generating image
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_disposed) return;
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      if (provider.generatedImageUrl == null &&
          provider.generatedImageBytes == null &&
          provider.currentJobId != null) {
        _shimmerController.repeat();
        _startBackgroundPolling(provider);
      }
    });
  }

  @override
  void dispose() {
    _disposed = true;
    _shimmerController.dispose();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _startBackgroundPolling(ProjectProvider provider) async {
    if (_pollingStarted) return;
    _pollingStarted = true;

    final projectId = provider.currentProject?.id;
    final jobId = provider.currentJobId;
    final authToken = SupabaseService.accessToken;

    if (projectId == null || jobId == null || authToken == null) return;

    try {
      final result = await ApiService.pollJobUntilDone(
        projectId,
        jobId,
        authToken,
        onProgress: (progressPct, phase) {
          if (_disposed) return;
          if (mounted) {
            setState(() {
              _localProgress = progressPct;
              _localPhase = phase;
            });
          }
        },
      );

      if (_disposed) return;

      if (result.outcome == PollingOutcome.done) {
        await provider.fetchGeneratedImage();
        if (mounted) {
          _shimmerController.stop();
          setState(() {}); // trigger rebuild to show result or retry
        }
      } else {
        // Job failed — allow retry
        if (mounted) {
          _shimmerController.stop();
          setState(() {});
        }
      }
    } catch (e) {
      AppLogger.warning('[DreamSpace] background polling failed: $e');
      if (mounted) setState(() {});
    }
  }

  void _retryBackgroundPolling() {
    _pollingStarted = false;
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _startBackgroundPolling(provider);
  }

  void _handleNavTap(int index) {
    if (index == 2) return;
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

  void _handleImageTap(double x, double y) {
    final hotspot = ProductHotspot(
      id: 'tap_${DateTime.now().millisecondsSinceEpoch}',
      x: x.clamp(0.0, 1.0).toDouble(),
      y: y.clamp(0.0, 1.0).toDouble(),
      itemType: 'furniture',
      label: 'Furniture',
    );
    widget.onHotspotTap?.call(hotspot);
  }

  ImageProvider _getGeneratedImageProvider(ProjectProvider provider) {
    if (provider.generatedImageUrl != null) {
      return NetworkImage(provider.generatedImageUrl!);
    }
    final imageBytes = provider.generatedImageBytes;
    if (imageBytes != null) {
      return MemoryImage(imageBytes);
    }
    return const AssetImage('assets/images/choose_space/choose_living.png');
  }

  BoxFit _dreamSpaceFit() {
    // Dream Space must always preserve full image bounds (no cropping).
    return BoxFit.contain;
  }

  Widget _buildGeneratedInteractiveImage(
    ProjectProvider provider,
    List<ProductHotspot> hotspots,
  ) {
    // Check if generation is still in progress (navigated early via timeout)
    if (provider.generatedImageUrl == null &&
        provider.generatedImageBytes == null) {
      if (provider.currentJobId != null) {
        return _buildGeneratingOverlay(provider);
      }
      // Fallback: show original image without overlay
      AppLogger.warning(
        '[DreamSpace] FALLBACK original_image — '
        'generatedImageUrl=null generatedImageBytes=null currentJobId=null '
        'approach=${provider.approach} '
        'errorMessage=${provider.errorMessage}',
      );
      return _buildOriginalImage();
    }

    // Normal path: show generated image with hotspots
    InteractiveImageWidget.debugShowImageBounds = kShowMarkerDebugOverlay;
    return Container(
      key: ValueKey(provider.generatedImageUrl),
      color: Colors.black,
      child: InteractiveImageWidget(
        imageProvider: _getGeneratedImageProvider(provider),
        fit: _dreamSpaceFit(),
        onImageTap: _handleImageTap,
        overlayBuilder: (imageWidth, imageHeight, displaySize, displayOffset) {
          return LayoutBuilder(
            builder: (context, constraints) {
              final visibleSize = Size(
                constraints.maxWidth,
                constraints.maxHeight,
              );
              return Stack(
                clipBehavior: Clip.hardEdge,
                children: hotspots.map((hotspot) {
                  final markerTopLeft = mapHotspotToRenderedImageTopLeft(
                    hotspot,
                    displaySize,
                    displayOffset,
                    visibleSize: visibleSize,
                  );
                  return Positioned(
                    left: markerTopLeft.dx,
                    top: markerTopLeft.dy,
                    child: GestureDetector(
                      key: ValueKey<String>('auto_hotspot_${hotspot.id}'),
                      behavior: HitTestBehavior.opaque,
                      onTap: () => widget.onHotspotTap?.call(hotspot),
                      child: _HotspotMarker(label: hotspot.label),
                    ),
                  );
                }).toList(),
              );
            },
          );
        },
      ),
    );
  }

  /// Shows the original room photo with a shimmer overlay + progress indicator
  /// while the backend generation job is still running.
  Widget _buildGeneratingOverlay(ProjectProvider provider) {
    final originalImageProvider = provider.getProjectImageProvider();
    final phase =
        _localPhase ?? provider.jobPhase ?? 'Finishing your design...';

    return Stack(
      fit: StackFit.expand,
      children: [
        // Original room photo as background
        if (originalImageProvider != null)
          Container(
            color: Colors.black,
            child: InteractiveImageWidget(
              imageProvider: originalImageProvider,
              fit: _dreamSpaceFit(),
              onImageTap: (_, __) {},
            ),
          )
        else
          Container(color: Colors.black),

        // Shimmer/pulse overlay
        AnimatedBuilder(
          animation: _shimmerController,
          builder: (context, child) {
            final opacity = 0.15 + 0.15 * _shimmerController.value;
            return Container(color: Colors.white.withValues(alpha: opacity));
          },
        ),

        // Progress indicator
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(
                width: 40,
                height: 40,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                phase,
                style: AppTheme.dmSans(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                _localProgress > 0
                    ? '$_localProgress% complete'
                    : 'Almost there',
                style: AppTheme.dmSans(
                  fontSize: 13,
                  fontWeight: FontWeight.w400,
                  color: Colors.white.withValues(alpha: 0.7),
                ),
              ),
              // Show retry button if polling hasn't started or failed
              if (_pollingStarted &&
                  provider.generatedImageUrl == null &&
                  provider.generatedImageBytes == null) ...[
                const SizedBox(height: 20),
                TextButton(
                  onPressed: _retryBackgroundPolling,
                  child: Text(
                    'Still working... Tap to retry',
                    style: AppTheme.dmSans(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: Colors.white.withValues(alpha: 0.8),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Main content - swipeable before/after
            Expanded(
              child: PageView(
                controller: _pageController,
                children: [
                  // Page 0: Generated dream space (interactive)
                  Stack(
                    fit: StackFit.expand,
                    children: [
                      Consumer<ProjectProvider>(
                        builder: (context, provider, _) {
                          return _buildGeneratedInteractiveImage(
                            provider,
                            provider.detectedHotspots,
                          );
                        },
                      ),
                      IgnorePointer(child: _buildGradientOverlay()),
                      _buildWelcomeText(),
                      const _RotatingHintPill(),
                    ],
                  ),

                  // Page 1: Original room image (view only)
                  Stack(
                    fit: StackFit.expand,
                    children: [
                      _buildOriginalImage(),
                      IgnorePointer(child: _buildGradientOverlay()),
                      // "Original" badge
                      Positioned(
                        bottom: 20,
                        left: 20,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.6),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            'Original',
                            style: AppTheme.dmSans(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      _buildSwipeHint('Swipe back to interact'),
                    ],
                  ),
                ],
              ),
            ),

            // Bottom buttons
            _buildBottomButtons(),
          ],
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        selectedIndex: 0,
        onItemTapped: _handleNavTap,
        onFabPressed: _handleFabPressed,
      ),
    );
  }

  Widget _buildOriginalImage() {
    final provider = Provider.of<ProjectProvider>(context, listen: true);
    final imageProvider = provider.getProjectImageProvider();

    if (imageProvider != null) {
      return Container(
        color: Colors.black,
        child: InteractiveImageWidget(
          imageProvider: imageProvider,
          fit: _dreamSpaceFit(),
          onImageTap: (_, __) {}, // no-op, view-only
        ),
      );
    }

    // Fallback
    return Container(
      color: AppTheme.scaffoldBackground,
      child: Center(
        child: Text(
          'Original not available',
          style: AppTheme.dmSans(fontSize: 14, color: AppTheme.textSecondary),
        ),
      ),
    );
  }

  Widget _buildGradientOverlay() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.center,
          colors: [Colors.black.withValues(alpha: 0.5), Colors.transparent],
        ),
      ),
    );
  }

  Widget _buildWelcomeText() {
    return Positioned(
      top: 20,
      left: 20,
      right: 20,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Welcome to',
            style: AppTheme.dmSans(
              fontSize: 16,
              fontWeight: FontWeight.w400,
              color: Colors.white.withValues(alpha: 0.9),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Your Dream Space.',
            style: AppTheme.dmSans(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSwipeHint(String text) {
    return Positioned(
      bottom: 20,
      left: 20,
      right: 20,
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.swipe_outlined,
                size: 16,
                color: Colors.white.withValues(alpha: 0.9),
              ),
              const SizedBox(width: 8),
              Text(
                text,
                style: AppTheme.dmSans(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: Colors.white,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBottomButtons() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Retry button
          Expanded(
            child: OutlinedButton(
              onPressed: widget.onRetry,
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                side: const BorderSide(color: AppTheme.dividerColor),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text(
                'Retry',
                style: AppTheme.dmSans(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Restart button
          Expanded(
            child: ElevatedButton(
              onPressed: widget.onRestart,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                padding: const EdgeInsets.symmetric(vertical: 16),
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text(
                'Restart',
                style: AppTheme.dmSans(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Animated hotspot marker widget
class _HotspotMarker extends StatefulWidget {
  final String label;

  const _HotspotMarker({required this.label});

  @override
  State<_HotspotMarker> createState() => _HotspotMarkerState();
}

class _HotspotMarkerState extends State<_HotspotMarker>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();

    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.3,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Pulsing ring
        AnimatedBuilder(
          animation: _pulseAnimation,
          builder: (context, child) {
            return Container(
              width: 40 * _pulseAnimation.value,
              height: 40 * _pulseAnimation.value,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppTheme.primaryColor.withValues(
                    alpha: 0.5 * (2 - _pulseAnimation.value),
                  ),
                  width: 2,
                ),
              ),
              child: Center(
                child: Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryColor.withValues(alpha: 0.4),
                        blurRadius: 8,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.add, color: Colors.white, size: 16),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

/// Simple data class for a hint's icon and text.
class _HintConfig {
  final IconData icon;
  final String text;
  const _HintConfig({required this.icon, required this.text});
}

/// A pill that rotates between two hint messages with a crossfade animation.
class _RotatingHintPill extends StatefulWidget {
  const _RotatingHintPill();

  @override
  State<_RotatingHintPill> createState() => _RotatingHintPillState();
}

class _RotatingHintPillState extends State<_RotatingHintPill> {
  static const _hints = [
    _HintConfig(icon: Icons.swipe_outlined, text: 'Swipe to see original'),
    _HintConfig(
      icon: Icons.touch_app_outlined,
      text: 'Tap any item to find products',
    ),
  ];

  int _index = 0;
  late final Timer _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 3500), (_) {
      setState(() => _index = (_index + 1) % _hints.length);
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hint = _hints[_index];
    return Positioned(
      bottom: 20,
      left: 20,
      right: 20,
      child: Center(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          transitionBuilder: (child, animation) {
            return FadeTransition(
              opacity: animation,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0.0, 0.15),
                  end: Offset.zero,
                ).animate(animation),
                child: child,
              ),
            );
          },
          child: Container(
            key: ValueKey<int>(_index),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  hint.icon,
                  size: 16,
                  color: Colors.white.withValues(alpha: 0.9),
                ),
                const SizedBox(width: 8),
                Text(
                  hint.text,
                  style: AppTheme.dmSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
