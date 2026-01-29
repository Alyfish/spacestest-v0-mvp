import 'dart:async';
import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import 'package:video_player/video_player.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
import 'main_navigation_screen.dart';

class AnalyzingScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onComplete;
  final VideoPlayerController? controller;
  final String? title;
  final String? subtitle;

  const AnalyzingScreen({
    super.key,
    this.onBack,
    this.onComplete,
    this.controller,
    this.title,
    this.subtitle,
  });

  static Future<VideoPlayerController> preloadController() async {
    return VideoPlayerController.networkUrl(Uri.parse(''));
  }

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen>
    with TickerProviderStateMixin {

  // Animation controllers for each icon
  late List<AnimationController> _iconControllers;
  late List<Animation<double>> _fadeAnimations;
  late List<Animation<double>> _scaleAnimations;

  // Breathing animation for after all icons appear
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;

  // Icon configuration - furniture icons for loading animation
  static const List<_LoadingIcon> _icons = [
    _LoadingIcon(icon: IconsaxPlusLinear.lamp_on, label: 'Sofa'),
    _LoadingIcon(icon: IconsaxPlusLinear.lamp_1, label: 'Bed'),
    _LoadingIcon(icon: IconsaxPlusLinear.lamp_charge, label: 'Lamp'),
    _LoadingIcon(icon: IconsaxPlusLinear.home_2, label: 'House'),
  ];

  // Timing constants
  static const Duration _iconAppearDuration = Duration(milliseconds: 600);
  static const Duration _staggerDelay = Duration(milliseconds: 1250);
  static const Duration _totalDuration = Duration(milliseconds: 5500);

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _startStaggeredAnimation();
    _scheduleCompletion();
  }

  void _initAnimations() {
    // Create controllers for each icon
    _iconControllers = List.generate(
      _icons.length,
      (index) => AnimationController(
        vsync: this,
        duration: _iconAppearDuration,
      ),
    );

    // Create fade animations with easeOut curve
    _fadeAnimations = _iconControllers.map((controller) {
      return Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(
          parent: controller,
          curve: Curves.easeOut,
        ),
      );
    }).toList();

    // Create scale animations with slight overshoot for playful feel
    _scaleAnimations = _iconControllers.map((controller) {
      return Tween<double>(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(
          parent: controller,
          curve: Curves.elasticOut,
        ),
      );
    }).toList();

    // Breathing animation for subtle life after reveal
    _breathingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );

    _breathingAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(
        parent: _breathingController,
        curve: Curves.easeInOut,
      ),
    );
  }

  void _startStaggeredAnimation() async {
    for (int i = 0; i < _icons.length; i++) {
      if (!mounted) return;

      // Start this icon's animation
      _iconControllers[i].forward();

      // Wait before starting next icon (except for last)
      if (i < _icons.length - 1) {
        await Future.delayed(_staggerDelay);
      }
    }

    // Start breathing animation after all icons appear
    await Future.delayed(const Duration(milliseconds: 400));
    if (mounted) {
      _breathingController.repeat(reverse: true);
    }
  }

  void _scheduleCompletion() {
    Future.delayed(_totalDuration, () {
      if (mounted && widget.onComplete != null) {
        widget.onComplete!();
      }
    });
  }

  @override
  void dispose() {
    for (final controller in _iconControllers) {
      controller.dispose();
    }
    _breathingController.dispose();
    super.dispose();
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
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(flex: 3),

              // Animated icons row
              AnimatedBuilder(
                animation: _breathingController,
                builder: (context, child) {
                  return Transform.scale(
                    scale: _breathingAnimation.value,
                    child: child,
                  );
                },
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(_icons.length, (index) {
                    return Padding(
                      padding: EdgeInsets.symmetric(
                        horizontal: index == 0 || index == _icons.length - 1
                            ? 12.0
                            : 16.0,
                      ),
                      child: _buildAnimatedIcon(index),
                    );
                  }),
                ),
              ),

              const SizedBox(height: 56),

              // Title with fade-in
              FadeTransition(
                opacity: _fadeAnimations.isNotEmpty
                    ? _fadeAnimations[0]
                    : const AlwaysStoppedAnimation(1.0),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32),
                  child: Text(
                    widget.title ?? 'Creating your space',
                    style: AppTheme.dmSans(
                      fontSize: 24,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),

              const SizedBox(height: 12),

              // Subtitle
              FadeTransition(
                opacity: _fadeAnimations.length > 1
                    ? _fadeAnimations[1]
                    : const AlwaysStoppedAnimation(1.0),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 40),
                  child: Text(
                    widget.subtitle ?? 'Finding the perfect pieces for you',
                    style: AppTheme.dmSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w400,
                      color: AppTheme.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),

              const Spacer(flex: 4),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        selectedIndex: 0,
        onItemTapped: _handleNavTap,
        onFabPressed: _handleFabPressed,
      ),
    );
  }

  Widget _buildAnimatedIcon(int index) {
    return AnimatedBuilder(
      animation: _iconControllers[index],
      builder: (context, child) {
        return Opacity(
          opacity: _fadeAnimations[index].value,
          child: Transform.scale(
            scale: _scaleAnimations[index].value,
            child: child,
          ),
        );
      },
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Center(
          child: Icon(
            _icons[index].icon,
            size: 28,
            color: AppTheme.primaryColor,
          ),
        ),
      ),
    );
  }
}

class _LoadingIcon {
  final IconData icon;
  final String label;

  const _LoadingIcon({
    required this.icon,
    required this.label,
  });
}
