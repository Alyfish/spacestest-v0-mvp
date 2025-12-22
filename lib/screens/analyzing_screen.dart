import 'dart:async';

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:video_player/video_player.dart';
import '../theme.dart';
import '../widgets/icon_button.dart';

class AnalyzingScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onComplete;
  final VideoPlayerController? controller;

  const AnalyzingScreen({
    super.key,
    this.onBack,
    this.onComplete,
    this.controller,
  });

  /// Preload a video controller so playback is ready before showing the screen.
  static Future<VideoPlayerController> preloadController() async {
    final controller = VideoPlayerController.asset(
      'assets/animations/analyzing/analyzing_animation.mp4',
    );
    await controller.initialize();
    controller
      ..setLooping(true)
      ..setVolume(0)
      ..play();
    return controller;
  }

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen>
    with SingleTickerProviderStateMixin {
  late VideoPlayerController _videoController;
  bool _ownsController = true;
  bool _isVideoReady = false;
  Timer? _textTimer;
  int _textIndex = 0;
  static const _textRotation = <String>[
    'analyzing your SPACE...',
    'finding what MATTERS most...',
    'spotting patterns YOU LOVE...',
    'checking PRACTICALITY...',
    'balancing COMFORT and STYLE...',
    'curating pieces that FIT...',
    'measuring VIBE vs. FUNCTION...',
    'optimizing LAYOUT choices...',
    'almost THERE...',
  ];

  @override
  void initState() {
    super.initState();
    _initVideo();
    _startTextRotation();
    _mockApiComplete();
  }

  Future<void> _initVideo() async {
    if (widget.controller != null) {
      _videoController = widget.controller!;
      _ownsController = false;
      _isVideoReady = _videoController.value.isInitialized;
      if (_isVideoReady) {
        _videoController
          ..setLooping(true)
          ..setVolume(0)
          ..play();
      }
      setState(() {});
      return;
    }

    _videoController = await AnalyzingScreen.preloadController();
    if (mounted) {
      setState(() {
        _isVideoReady = true;
      });
    }
  }

  void _startTextRotation() {
    _textTimer = Timer.periodic(const Duration(milliseconds: 1800), (_) {
      if (!mounted) return;
      setState(() {
        _textIndex = (_textIndex + 1) % _textRotation.length;
      });
    });
  }

  InlineSpan _buildColoredText(String text, {bool isPrimary = false}) {
    final parts = text.split(' ');
    final spans = <TextSpan>[];
    for (var i = 0; i < parts.length; i++) {
      final word = parts[i];
      final isAllCaps = word.isNotEmpty && word.toUpperCase() == word;
      spans.add(
        TextSpan(
          text: word + (i == parts.length - 1 ? '' : ' '),
          style: TextStyle(
            color: isAllCaps ? AppTheme.primaryColor : AppTheme.bodyTextColor,
            fontFamily: AppTheme.secondaryFont,
            fontSize: 16,
            fontWeight: FontWeight.w400,
          ),
        ),
      );
    }
    return TextSpan(children: spans);
  }

  void _mockApiComplete() {
    Future.delayed(const Duration(seconds: 7), () {
      if (mounted && widget.onComplete != null) {
        widget.onComplete!();
      }
    });
  }

  @override
  void dispose() {
    _textTimer?.cancel();
    if (_ownsController) {
      _videoController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              const Text('Analyzing...', style: AppTheme.sectionTitleStyle),
              const SizedBox(height: 16),

              const SizedBox(height: 8),

              // Top text (fixed to top-right)
              Container(
                height: 44,
                margin: EdgeInsets.only(right: 32),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 1000),
                    transitionBuilder: (child, anim) =>
                        FadeTransition(opacity: anim, child: child),
                    layoutBuilder: (currentChild, previousChildren) {
                      return Stack(
                        alignment: Alignment.centerRight,
                        children: <Widget>[
                          ...previousChildren,
                          if (currentChild != null) currentChild,
                        ],
                      );
                    },
                    child: RichText(
                      key: ValueKey('top-text-${_textIndex}'),
                      textAlign: TextAlign.right,
                      text: _buildColoredText(_textRotation[_textIndex]),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 8),

              // Video area with locked aspect ratio (vertical)
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final aspect =
                        _isVideoReady && _videoController.value.aspectRatio != 0
                        ? _videoController.value.aspectRatio
                        : 3 / 4;
                    final maxHeight = constraints.maxHeight
                        .clamp(0, 500)
                        .toDouble();
                    final height = maxHeight > 0.0 ? maxHeight : 500.0;
                    final width = height * aspect;

                    return Center(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(24),
                        child: SizedBox(
                          height: height,
                          width: width,
                          child: _isVideoReady
                              ? FittedBox(
                                  fit: BoxFit.cover,
                                  alignment: Alignment.center,
                                  child: SizedBox(
                                    width: _videoController.value.size.width,
                                    height: _videoController.value.size.height,
                                    child: VideoPlayer(_videoController),
                                  ),
                                )
                              : Container(
                                  color: AppTheme.grayColor.withValues(
                                    alpha: 0.1,
                                  ),
                                  child: const Center(
                                    child: CircularProgressIndicator(),
                                  ),
                                ),
                        ),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 8),

              // Bottom floating texts (kept outside video)
              SizedBox(
                height: 44,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 1000),
                  transitionBuilder: (child, anim) =>
                      FadeTransition(opacity: anim, child: child),
                  layoutBuilder: (currentChild, previousChildren) {
                    return Stack(
                      alignment: Alignment.centerLeft,
                      children: <Widget>[
                        ...previousChildren,
                        if (currentChild != null) currentChild,
                      ],
                    );
                  },
                  child: RichText(
                    key: ValueKey('bottom-text-${_textIndex}'),
                    textAlign: TextAlign.left,
                    text: _buildColoredText(
                      _textRotation[(_textIndex + 2) % _textRotation.length],
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Back button
              Align(
                alignment: Alignment.centerLeft,
                child: IconButtonWidget(
                  onPressed: widget.onBack ?? () => Navigator.pop(context),
                  icon: IconsaxPlusLinear.arrow_left_2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
