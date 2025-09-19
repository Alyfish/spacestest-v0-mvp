import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/user_provider.dart';
import 'main_navigation_screen.dart';

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
  late Animation<Offset> _squareCombinedSlide; // MODIFIED: Replaced moveLeft and moveDown
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

  @override
  void initState() {
    super.initState();

    // --- INTRO CONTROLLER (4.5 seconds total) ---
    _introController = AnimationController(
        duration: const Duration(milliseconds: 4500), vsync: this);

    // Phase 1: Square appears, rotates, and scales up
    _squareFadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _introController, curve: const Interval(0.0, 0.2)));
    _squareRotation = Tween<double>(begin: 0.0, end: -0.625).animate( // -225 deg
        CurvedAnimation(parent: _introController, curve: const Interval(0.2, 0.3, curve: Curves.easeInOut)));
    _squareScaleUp = Tween<double>(begin: 0.7, end: 2.0).animate( // Scale by 100%
        CurvedAnimation(parent: _introController, curve: const Interval(0.2, 0.3, curve: Curves.easeInOut)));
    
    // Phase 2: After a pause, square shrinks and moves left
    _squareShrink = Tween<double>(begin: 2.0, end: 0.09).animate( // Shrink to 9% of scaled-up size
        CurvedAnimation(parent: _introController, curve: const Interval(0.41, 0.5, curve: Curves.easeInOut)));
    
    // NEW: Combined slide animation for the square using fractional offsets
    _squareCombinedSlide = TweenSequence<Offset>([
      // Stays centered
      TweenSequenceItem(tween: ConstantTween(Offset.zero), weight: 41),
      // Moves left by half its width
      TweenSequenceItem(tween: Tween(begin: Offset.zero, end: const Offset(0.15, 0.012)).chain(CurveTween(curve: Curves.easeOut)),weight: 14),
      // Stays there
      TweenSequenceItem(tween: ConstantTween(const Offset(0.15, 0.012)), weight: 17),
      // Moves down off-screen
      TweenSequenceItem(tween: Tween(begin: const Offset(0.15, 0.012), end: const Offset(0.15, 0.012)), weight: 28),
    ]).animate(CurvedAnimation(parent: _introController, curve: Curves.easeInOut));
        
    // Phase 3: Logo slides in to overlap
    _logoInitialSlide = Tween<Offset>(begin: const Offset(-2.5, 0), end: const Offset(0, 0)).animate( // MODIFIED: End offset to align with square
        CurvedAnimation(parent: _introController, curve: const Interval(0.5, 0.60, curve: Curves.easeInOut)));

    // Phase 4: After another pause, the square explodes and fades
    _squareExplode = Tween<double>(begin: 0.09, end: 30.0).animate( // Explode to fill screen
        CurvedAnimation(parent: _introController, curve: const Interval(0.82, 1.0, curve: Curves.easeIn)));
    _squareFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
        CurvedAnimation(parent: _introController, curve: const Interval(0.82, 0.95, curve: Curves.easeIn)));
    _logoInitialFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
        CurvedAnimation(parent: _introController, curve: const Interval(0.78, 0.9, curve: Curves.easeIn)));


    // --- FINAL ELEMENTS CONTROLLER (2 seconds) ---
    _finalElementsController = AnimationController(
        duration: const Duration(milliseconds: 2000), vsync: this);

    _finalElementsFadeIn = CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.0, 0.3, curve: Curves.easeIn));
    _logoFinalSlide = Tween<Offset>(begin: const Offset(0, -0.5), end: const Offset(0, 0.1))
        .animate(CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.0, 0.4, curve: Curves.easeOutCubic)));
    _subtitleSlide = Tween<Offset>(begin: const Offset(0, 1), end: const Offset(0, 0.1))
        .animate(CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.0, 0.4, curve: Curves.easeOutCubic)));
    _blockMoveUp = Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero)
        .animate(CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.7, 0.9, curve: Curves.easeInOut)));
    _buttonFade = CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.7, 1.0, curve: Curves.easeIn));
    _buttonSlide = Tween<Offset>(begin: const Offset(0, -1), end: Offset.zero)
        .animate(CurvedAnimation(parent: _finalElementsController, curve: const Interval(0.7, 1.0, curve: Curves.easeOutBack)));

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
    super.dispose();
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
                  fit: StackFit.expand, // This forces the Stack to fill the screen
                  children: [
                    // The Square
                    SlideTransition(
                      position: _squareCombinedSlide, // MODIFIED: Use SlideTransition
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
                      position: _logoInitialSlide, // MODIFIED: Use SlideTransition
                      child: Opacity(
                        opacity: _logoInitialFadeOut.value,
                        child: Image.asset('assets/logo/logo.png', width: 220)
                      ),
                    ),
                  ],
                );
              },
            ),

          // Final Sign-In Elements
          if (_showFinalElements) ...[
            FadeTransition(
              opacity: _finalElementsFadeIn,
              child: SlideTransition(
                position: _blockMoveUp,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    SlideTransition(
                      position: _logoFinalSlide,
                      child: Image.asset('assets/logo/logo.png', width: 220),
                    ),
                    const SizedBox(height: 3), // Set space to 10px
                    SlideTransition(
                      position: _subtitleSlide,
                      child: Text(
                        'Reimagine Your World',
                        style: AppTheme.accentSubtitleStyle.copyWith(fontSize: 28),
                      ),
                    ),
                    const SizedBox(height: 140),
                  ],
                ),
              ),
            ),
            SizedBox(height: 85),
            Align(
             alignment: Alignment.center,
             child: Padding(
               padding: const EdgeInsets.only(top: 85.0, left: 33.0, right: 33.0),
               child: FadeTransition(
                 opacity: _buttonFade,
                 child: SlideTransition(
                   position: _buttonSlide,
                   child: SizedBox(
                     width: double.infinity,
                     child: Consumer<UserProvider>(
                       builder: (context, userProvider, child) {
                         return OutlinedButton.icon(
                           icon: userProvider.isAuthenticating 
                             ? const SizedBox(
                                 height: 20,
                                 width: 20,
                                 child: CircularProgressIndicator(
                                   strokeWidth: 2,
                                   valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryColor),
                                 ),
                               )
                             : Image.asset('assets/logo/google_icon.png', height: 20.0),
                           label: Text(
                             userProvider.isAuthenticating 
                               ? 'Signing in...' 
                               : 'Continue with Google',
                             style: Theme.of(context).textTheme.labelLarge?.copyWith(
                               color: AppTheme.bodyTextColor,
                             ),
                           ),
                           style: OutlinedButton.styleFrom(
                             shape: RoundedRectangleBorder(
                               borderRadius: BorderRadius.circular(15),
                             ),
                           ),
                           onPressed: userProvider.isAuthenticating 
                             ? null 
                             : () async {
                                 // Clear any existing snackbars
                                 ScaffoldMessenger.of(context).clearSnackBars();
                                 
                                 final navigator = Navigator.of(context);
                                 final scaffoldMessenger = ScaffoldMessenger.of(context);
                                 try {
                                   await userProvider.signInWithGoogle();
                                   if (mounted && userProvider.isAuthenticated) {
                                     // Navigate to main app screen
                                     navigator.pushReplacement(
                                       PageRouteBuilder(
                                         pageBuilder: (ctx, animation, secondary) => const MainNavigationScreen(),
                                         transitionsBuilder: (ctx, animation, secondary, child) {
                                           return FadeTransition(opacity: animation, child: child);
                                         },
                                         transitionDuration: const Duration(milliseconds: 500),
                                       ),
                                     );
                                   }
                                 } catch (e) {
                                   // Handle error - show a snackbar
                                   if (mounted) {
                                     scaffoldMessenger.showSnackBar(
                                       SnackBar(
                                         content: Text(
                                           'Sign in failed. Please try again.',
                                           style: TextStyle(color: AppTheme.backgroundColor),
                                         ),
                                         backgroundColor: Colors.red,
                                         duration: const Duration(seconds: 4),
                                         behavior: SnackBarBehavior.floating,
                                         shape: RoundedRectangleBorder(
                                           borderRadius: BorderRadius.circular(10),
                                         ),
                                         action: SnackBarAction(
                                           label: 'Dismiss',
                                           textColor: AppTheme.backgroundColor,
                                           onPressed: () {
                                             ScaffoldMessenger.of(context).hideCurrentSnackBar();
                                           },
                                         ),
                                       ),
                                     );
                                   }
                                 }
                               },
                         );
                       },
                     ),
                   ),
                 ),
               ),
             ),
           )
          ]
        ],
      ),
    );
  }
}



