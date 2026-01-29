import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/shop_product.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
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

class _DreamSpaceScreenState extends State<DreamSpaceScreen> {
  // Sample hotspots for demo - in real app, these come from API
  final List<ProductHotspot> _hotspots = const [
    ProductHotspot(
      id: 'hotspot_1',
      x: 0.3,
      y: 0.6,
      itemType: 'couch',
      label: 'Couch',
    ),
    ProductHotspot(
      id: 'hotspot_2',
      x: 0.7,
      y: 0.4,
      itemType: 'lamp',
      label: 'Lamp',
    ),
    ProductHotspot(
      id: 'hotspot_3',
      x: 0.5,
      y: 0.75,
      itemType: 'table',
      label: 'Coffee Table',
    ),
  ];

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
              Text('Coming soon', style: AppTheme.dmSans(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.white)),
            ],
          ),
          backgroundColor: AppTheme.textSecondary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
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
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
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
          SnackBar(content: Text('Failed to start: ${e.toString()}'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Main content - image with overlay
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Background image
                  _buildBackgroundImage(),

                  // Gradient overlay for text readability
                  _buildGradientOverlay(),

                  // Welcome text overlay
                  _buildWelcomeText(),

                  // Tappable hotspots
                  ..._buildHotspots(),

                  // Instruction text at bottom of image
                  _buildInstructionText(),
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

  Widget _buildBackgroundImage() {
    // In real app, use the generated image from ProjectProvider
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.scaffoldBackground,
        image: const DecorationImage(
          image: AssetImage('assets/images/choose_space/choose_living_room.png'),
          fit: BoxFit.cover,
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
          colors: [
            Colors.black.withValues(alpha: 0.5),
            Colors.transparent,
          ],
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

  List<Widget> _buildHotspots() {
    return _hotspots.map((hotspot) {
      return Positioned(
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final x = hotspot.x * constraints.maxWidth;
            final y = hotspot.y * constraints.maxHeight;

            return Stack(
              children: [
                Positioned(
                  left: x - 20,
                  top: y - 20,
                  child: GestureDetector(
                    onTap: () {
                      if (widget.onHotspotTap != null) {
                        widget.onHotspotTap!(hotspot);
                      }
                    },
                    child: _HotspotMarker(label: hotspot.label),
                  ),
                ),
              ],
            );
          },
        ),
      );
    }).toList();
  }

  Widget _buildInstructionText() {
    return Positioned(
      bottom: 20,
      left: 20,
      right: 20,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          'Tap on items to shop products',
          style: AppTheme.dmSans(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: Colors.white,
          ),
          textAlign: TextAlign.center,
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

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.3).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
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
                  child: const Icon(
                    Icons.add,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}
