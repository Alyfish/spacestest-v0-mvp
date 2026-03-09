import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../providers/user_provider.dart';
import '../providers/subscription_provider.dart';
import '../utils/logger.dart';
import 'main_navigation_screen.dart';

enum _AuthProviderType { google, apple }

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  // Controller for the entire intro sequence
  late AnimationController _introController;

  // Animations for the square
  late Animation<double> _squareFadeIn;
  late Animation<double> _squareRotation;
  late Animation<double> _squareScaleUp;
  late Animation<double> _squareShrink;
  late Animation<Offset>
  _squareCombinedSlide; // MODIFIED: Replaced moveLeft and moveDown
  late Animation<double> _squareExplode;
  late Animation<double> _squareFadeOut;

  // Animations for the first logo appearance
  late Animation<Offset> _logoInitialSlide;
  late Animation<double> _logoInitialFadeOut;

  // Controller for the final screen composition
  late AnimationController _finalElementsController;
  late Animation<Offset> _logoFinalSlide;
  late Animation<Offset> _subtitleSlide;
  late Animation<double> _finalElementsFadeIn;
  late Animation<Offset> _blockMoveUp;
  late Animation<Offset> _buttonSlide;
  late Animation<double> _buttonFade;

  // State flags
  bool _showFinalElements = false;
  bool _showGoogleButton = false;
  _AuthProviderType? _activeAuthProvider;

  // Animation for Google button reveal
  late AnimationController _googleButtonController;
  late Animation<double> _googleButtonFade;
  late Animation<Offset> _googleButtonSlide;

  @override
  void initState() {
    super.initState();

    // --- INTRO CONTROLLER (4.5 seconds total) ---
    _introController = AnimationController(
      duration: const Duration(milliseconds: 4500),
      vsync: this,
    );

    // Phase 1: Square appears, rotates, and scales up
    _squareFadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.0, 0.2),
      ),
    );
    _squareRotation = Tween<double>(begin: 0.0, end: -0.625).animate(
      // -225 deg
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.2, 0.3, curve: Curves.easeInOut),
      ),
    );
    _squareScaleUp = Tween<double>(begin: 0.7, end: 2.0).animate(
      // Scale by 100%
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.2, 0.3, curve: Curves.easeInOut),
      ),
    );

    // Phase 2: After a pause, square shrinks and moves left
    _squareShrink = Tween<double>(begin: 2.0, end: 0.09).animate(
      // Shrink to 9% of scaled-up size
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.41, 0.5, curve: Curves.easeInOut),
      ),
    );

    // NEW: Combined slide animation for the square using fractional offsets
    _squareCombinedSlide =
        TweenSequence<Offset>([
          // Stays centered
          TweenSequenceItem(tween: ConstantTween(Offset.zero), weight: 41),
          // Moves left by half its width
          TweenSequenceItem(
            tween: Tween(
              begin: Offset.zero,
              end: const Offset(0.16, 0.015),
            ).chain(CurveTween(curve: Curves.easeOut)),
            weight: 14,
          ),
          // Stays there
          TweenSequenceItem(
            tween: ConstantTween(const Offset(0.16, 0.015)),
            weight: 17,
          ),
          // Moves down off-screen
          TweenSequenceItem(
            tween: Tween(
              begin: const Offset(0.16, 0.015),
              end: const Offset(0.16, 0.015),
            ),
            weight: 28,
          ),
        ]).animate(
          CurvedAnimation(parent: _introController, curve: Curves.easeInOut),
        );

    // Phase 3: Logo slides in to overlap
    _logoInitialSlide =
        Tween<Offset>(
          begin: const Offset(-2.5, 0),
          end: const Offset(0, 0),
        ).animate(
          // MODIFIED: End offset to align with square
          CurvedAnimation(
            parent: _introController,
            curve: const Interval(0.5, 0.60, curve: Curves.easeInOut),
          ),
        );

    // Phase 4: After another pause, the square explodes and fades
    _squareExplode = Tween<double>(begin: 0.09, end: 30.0).animate(
      // Explode to fill screen
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.82, 1.0, curve: Curves.easeIn),
      ),
    );
    _squareFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.82, 0.95, curve: Curves.easeIn),
      ),
    );
    _logoInitialFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(0.78, 0.9, curve: Curves.easeIn),
      ),
    );

    // --- FINAL ELEMENTS CONTROLLER (2 seconds) ---
    _finalElementsController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _finalElementsFadeIn = CurvedAnimation(
      parent: _finalElementsController,
      curve: const Interval(0.0, 0.3, curve: Curves.easeIn),
    );
    _logoFinalSlide =
        Tween<Offset>(
          begin: const Offset(0, -0.5),
          end: const Offset(0, 0.1),
        ).animate(
          CurvedAnimation(
            parent: _finalElementsController,
            curve: const Interval(0.0, 0.4, curve: Curves.easeOutCubic),
          ),
        );
    _subtitleSlide =
        Tween<Offset>(
          begin: const Offset(0, 1),
          end: const Offset(0, 0.1),
        ).animate(
          CurvedAnimation(
            parent: _finalElementsController,
            curve: const Interval(0.0, 0.4, curve: Curves.easeOutCubic),
          ),
        );
    _blockMoveUp = Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero)
        .animate(
          CurvedAnimation(
            parent: _finalElementsController,
            curve: const Interval(0.7, 0.9, curve: Curves.easeInOut),
          ),
        );
    _buttonFade = CurvedAnimation(
      parent: _finalElementsController,
      curve: const Interval(0.7, 1.0, curve: Curves.easeIn),
    );
    _buttonSlide = Tween<Offset>(begin: const Offset(0, -1), end: Offset.zero)
        .animate(
          CurvedAnimation(
            parent: _finalElementsController,
            curve: const Interval(0.7, 1.0, curve: Curves.easeOutBack),
          ),
        );

    // Google button reveal animation
    _googleButtonController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _googleButtonFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _googleButtonController, curve: Curves.easeOut),
    );
    _googleButtonSlide =
        Tween<Offset>(begin: const Offset(0, 0.3), end: Offset.zero).animate(
          CurvedAnimation(
            parent: _googleButtonController,
            curve: Curves.easeOutCubic,
          ),
        );

    _startAnimationSequence();
  }

  void _startAnimationSequence() async {
    // Start the intro animation
    await _introController.forward().orCancel;

    // Switch to the final elements
    setState(() {
      _showFinalElements = true;
    });

    // Start the final composition animation
    await _finalElementsController.forward().orCancel;

    // Navigate after a brief pause
  }

  @override
  void dispose() {
    _introController.dispose();
    _finalElementsController.dispose();
    _googleButtonController.dispose();
    super.dispose();
  }

  void _onGetStartedPressed() {
    setState(() {
      _showGoogleButton = true;
    });
    _googleButtonController.forward();
  }

  Future<void> _handleGoogleGetStarted(UserProvider userProvider) async {
    await _handleAuthSignIn(userProvider, _AuthProviderType.google);
  }

  Future<void> _handleAppleGetStarted(UserProvider userProvider) async {
    await _handleAuthSignIn(userProvider, _AuthProviderType.apple);
  }

  Future<void> _handleAuthSignIn(
    UserProvider userProvider,
    _AuthProviderType providerType,
  ) async {
    if (userProvider.isAuthenticating) return;
    ScaffoldMessenger.of(context).clearSnackBars();
    setState(() {
      _activeAuthProvider = providerType;
    });

    try {
      switch (providerType) {
        case _AuthProviderType.google:
          await userProvider.signInWithGoogle();
          break;
        case _AuthProviderType.apple:
          await userProvider.signInWithApple();
          break;
      }
      await _completeSignIn(userProvider);
    } catch (e) {
      if (mounted) {
        final wasCancelled = e.toString().toLowerCase().contains('cancel');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              wasCancelled
                  ? 'Sign in canceled.'
                  : 'Sign in failed. Please try again.',
              style: const TextStyle(color: Colors.white),
            ),
            backgroundColor: AppTheme.errorColor,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            margin: const EdgeInsets.all(16),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _activeAuthProvider = null;
        });
      }
    }
  }

  Future<void> _completeSignIn(UserProvider userProvider) async {
    if (!mounted || !userProvider.isAuthenticated) return;

    final userId = userProvider.user.id;
    if (userId != null && userId.isNotEmpty) {
      try {
        await context.read<SubscriptionProvider>().onUserLoggedIn(userId);
      } catch (e) {
        AppLogger.error('Subscription sync failed', e);
      }
      if (!mounted) return;
    }

    unawaited(_verifyBackendAuthToken(userProvider));

    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (ctx, animation, secondary) =>
            const MainNavigationScreen(),
        transitionsBuilder: (ctx, animation, secondary, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 500),
      ),
    );
  }

  Future<void> _verifyBackendAuthToken(UserProvider userProvider) async {
    final token = userProvider.user.token;
    if (token == null || token.isEmpty) return;

    try {
      await ApiService.getUsage(token);
      AppLogger.info('Auth token accepted by backend /usage endpoint');
    } catch (e) {
      AppLogger.warning(
        'Auth token verification failed against backend (non-fatal): $e',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: Stack(
        alignment: Alignment.center,
        children: [
          // Intro Animation Elements
          if (!_showFinalElements)
            AnimatedBuilder(
              animation: _introController,
              builder: (context, child) {
                // Determine scale based on animation phase
                double scale = _squareScaleUp.value;
                if (_introController.value >= 0.41) {
                  scale = _squareShrink.value;
                }
                if (_introController.value >= 0.72) {
                  scale = _squareExplode.value;
                }

                return Stack(
                  alignment: Alignment.center,
                  fit: StackFit
                      .expand, // This forces the Stack to fill the screen
                  children: [
                    // The Square
                    SlideTransition(
                      position:
                          _squareCombinedSlide, // MODIFIED: Use SlideTransition
                      child: Transform.scale(
                        scale: scale,
                        child: Transform.rotate(
                          angle: _squareRotation.value * 2 * 3.14159,
                          child: Opacity(
                            opacity: _squareFadeIn.value * _squareFadeOut.value,
                            child: Image.asset(
                              'assets/logo/Rectangle 3.png',
                              width: 100,
                              height: 100,
                            ),
                          ),
                        ),
                      ),
                    ),

                    // The Sliding Logo
                    SlideTransition(
                      position:
                          _logoInitialSlide, // MODIFIED: Use SlideTransition
                      child: Opacity(
                        opacity: _logoInitialFadeOut.value,
                        child: Image.asset('assets/logo/logo.png', width: 220),
                      ),
                    ),
                  ],
                );
              },
            ),

          // Final Welcome Screen Elements
          if (_showFinalElements) ...[
            // Main content - centered vertically with logo, image, and text
            FadeTransition(
              opacity: _finalElementsFadeIn,
              child: SlideTransition(
                position: _blockMoveUp,
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 40),
                    child: Column(
                      children: [
                        const SizedBox(height: 48),
                        // Logo with tagline
                        SlideTransition(
                          position: _logoFinalSlide,
                          child: Image.asset(
                            'assets/logo/logo.png',
                            width: 180,
                          ),
                        ),
                        const SizedBox(height: 6),
                        SlideTransition(
                          position: _subtitleSlide,
                          child: Text(
                            'Reimagine Your World',
                            style: AppTheme.headerStyle(
                              fontSize: 20,
                              color: AppTheme.primaryColor,
                            ),
                          ),
                        ),
                        const SizedBox(height: 32),
                        // Room image - prominent and centered
                        Expanded(
                          child: Center(
                            child: Container(
                              constraints: const BoxConstraints(
                                maxWidth: 320,
                                maxHeight: 320,
                              ),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(24),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.08),
                                    blurRadius: 32,
                                    offset: const Offset(0, 16),
                                    spreadRadius: 0,
                                  ),
                                ],
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(24),
                                child: Image.asset(
                                  'assets/images/choose_space/choose_living.png',
                                  fit: BoxFit.cover,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 40),
                        // Get Started button
                        FadeTransition(
                          opacity: _buttonFade,
                          child: SlideTransition(
                            position: _buttonSlide,
                            child: SizedBox(
                              width: double.infinity,
                              height: 56,
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.primaryColor,
                                  foregroundColor: Colors.white,
                                  elevation: 0,
                                  shadowColor: AppTheme.primaryColor.withValues(
                                    alpha: 0.3,
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                ),
                                onPressed: _showGoogleButton
                                    ? null
                                    : _onGetStartedPressed,
                                child: Text(
                                  'Get Started',
                                  style: AppTheme.dmSans(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        // Continue with Google button (appears after Get Started)
                        if (_showGoogleButton) ...[
                          const SizedBox(height: 16),
                          FadeTransition(
                            opacity: _googleButtonFade,
                            child: SlideTransition(
                              position: _googleButtonSlide,
                              child: Consumer<UserProvider>(
                                builder: (context, userProvider, child) {
                                  final isAuthenticating =
                                      userProvider.isAuthenticating;
                                  final activeProvider = _activeAuthProvider;

                                  return Column(
                                    children: [
                                      SizedBox(
                                        width: double.infinity,
                                        height: 56,
                                        child: OutlinedButton(
                                          style: OutlinedButton.styleFrom(
                                            backgroundColor: Colors.white,
                                            foregroundColor:
                                                AppTheme.textPrimary,
                                            side: BorderSide(
                                              color: AppTheme.primaryColor
                                                  .withValues(alpha: 0.4),
                                              width: 1.5,
                                            ),
                                            shape: RoundedRectangleBorder(
                                              borderRadius:
                                                  BorderRadius.circular(16),
                                            ),
                                            elevation: 0,
                                          ),
                                          onPressed: isAuthenticating
                                              ? null
                                              : () => _handleGoogleGetStarted(
                                                  userProvider,
                                                ),
                                          child:
                                              isAuthenticating &&
                                                  activeProvider ==
                                                      _AuthProviderType.google
                                              ? SizedBox(
                                                  height: 22,
                                                  width: 22,
                                                  child: CircularProgressIndicator(
                                                    strokeWidth: 2.5,
                                                    valueColor:
                                                        const AlwaysStoppedAnimation<
                                                          Color
                                                        >(
                                                          AppTheme.primaryColor,
                                                        ),
                                                  ),
                                                )
                                              : Row(
                                                  mainAxisAlignment:
                                                      MainAxisAlignment.center,
                                                  children: [
                                                    Image.asset(
                                                      'assets/logo/google_icon.png',
                                                      height: 22,
                                                      width: 22,
                                                    ),
                                                    const SizedBox(width: 12),
                                                    Text(
                                                      'Continue with Google',
                                                      style: AppTheme.dmSans(
                                                        fontSize: 16,
                                                        fontWeight:
                                                            FontWeight.w500,
                                                        color: AppTheme
                                                            .textPrimary,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                        ),
                                      ),
                                      if (Platform.isIOS) ...[
                                        const SizedBox(height: 12),
                                        SizedBox(
                                          width: double.infinity,
                                          height: 56,
                                          child: ElevatedButton(
                                            onPressed: isAuthenticating
                                                ? null
                                                : () => _handleAppleGetStarted(
                                                    userProvider,
                                                  ),
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor:
                                                  AppTheme.textPrimary,
                                              foregroundColor: Colors.white,
                                              elevation: 0,
                                              shape: RoundedRectangleBorder(
                                                borderRadius:
                                                    BorderRadius.circular(16),
                                              ),
                                            ),
                                            child:
                                                isAuthenticating &&
                                                    activeProvider ==
                                                        _AuthProviderType.apple
                                                ? const SizedBox(
                                                    height: 22,
                                                    width: 22,
                                                    child: CircularProgressIndicator(
                                                      strokeWidth: 2.5,
                                                      valueColor:
                                                          AlwaysStoppedAnimation<
                                                            Color
                                                          >(Colors.white),
                                                    ),
                                                  )
                                                : Row(
                                                    mainAxisAlignment:
                                                        MainAxisAlignment
                                                            .center,
                                                    children: [
                                                      const Icon(
                                                        Icons.apple,
                                                        size: 24,
                                                        color: Colors.white,
                                                      ),
                                                      const SizedBox(width: 10),
                                                      Text(
                                                        'Continue with Apple',
                                                        style: AppTheme.dmSans(
                                                          fontSize: 16,
                                                          fontWeight:
                                                              FontWeight.w600,
                                                          color: Colors.white,
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  );
                                },
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
