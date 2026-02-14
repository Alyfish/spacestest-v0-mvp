import 'dart:math';
import 'package:flutter/material.dart';
import '../theme.dart';

/// Reusable card with animated gradient border (hint state) and uniform
/// selection styling (solid primary border + pink tint + checkmark).
class AnimatedBorderCard extends StatefulWidget {
  final Widget child;
  final bool isSelected;
  final bool animateWhenUnselected;
  final bool animateOnce;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry? padding;
  final double borderRadius;
  final bool showCheckmark;
  final double strokeWidth;

  const AnimatedBorderCard({
    super.key,
    required this.child,
    this.isSelected = false,
    this.animateWhenUnselected = true,
    this.animateOnce = false,
    this.onTap,
    this.padding,
    this.borderRadius = AppTheme.cardRadius,
    this.showCheckmark = true,
    this.strokeWidth = 1.5,
  });

  @override
  State<AnimatedBorderCard> createState() => _AnimatedBorderCardState();
}

class _AnimatedBorderCardState extends State<AnimatedBorderCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _onceCompleted = false;

  static const List<Color> _gradientColors = [
    Color(0xFFD02B48), // brand primary
    Color(0xFFE8446A), // lighter pink
    Color(0xFFFF7B54), // coral
    Color(0xFFFFAB76), // warm amber
    Color(0xFFE8446A), // lighter pink
    Color(0xFFD02B48), // brand primary (loop)
  ];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    if (widget.animateOnce) {
      _controller.addStatusListener(_onAnimationStatus);
    }
    _updateAnimation();
  }

  void _onAnimationStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) {
      setState(() => _onceCompleted = true);
      _controller.stop();
    }
  }

  @override
  void didUpdateWidget(covariant AnimatedBorderCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isSelected != widget.isSelected ||
        oldWidget.animateWhenUnselected != widget.animateWhenUnselected) {
      _updateAnimation();
    }
  }

  void _updateAnimation() {
    if (_onceCompleted) return;
    if (widget.animateWhenUnselected && !widget.isSelected) {
      if (!_controller.isAnimating) {
        if (widget.animateOnce) {
          _controller.forward(from: 0.0);
        } else {
          _controller.repeat();
        }
      }
    } else {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.removeStatusListener(_onAnimationStatus);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final shouldAnimate = widget.animateWhenUnselected && !widget.isSelected && !_onceCompleted;

    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return CustomPaint(
            foregroundPainter: shouldAnimate
                ? _GradientBorderPainter(
                    progress: _controller.value,
                    borderRadius: widget.borderRadius,
                    strokeWidth: widget.strokeWidth,
                    colors: _gradientColors,
                  )
                : null,
            child: child,
          );
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: widget.isSelected
                ? AppTheme.selectedCardBackground
                : AppTheme.surfaceColor,
            borderRadius: BorderRadius.circular(widget.borderRadius),
            border: shouldAnimate
                ? Border.all(color: Colors.transparent, width: widget.strokeWidth)
                : Border.all(
                    color: widget.isSelected
                        ? AppTheme.primaryColor
                        : AppTheme.cardBorderColor,
                    width: widget.isSelected ? 2.0 : 1.0,
                  ),
          ),
          child: Stack(
            children: [
              Padding(
                padding: widget.padding ?? EdgeInsets.all(AppTheme.cardPadding),
                child: widget.child,
              ),
              if (widget.isSelected && widget.showCheckmark)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: const BoxDecoration(
                      color: AppTheme.primaryColor,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.check,
                      size: 14,
                      color: Colors.white,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GradientBorderPainter extends CustomPainter {
  final double progress;
  final double borderRadius;
  final double strokeWidth;
  final List<Color> colors;

  _GradientBorderPainter({
    required this.progress,
    required this.borderRadius,
    required this.strokeWidth,
    required this.colors,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(
      rect.deflate(strokeWidth / 2),
      Radius.circular(borderRadius - strokeWidth / 2),
    );

    final gradient = SweepGradient(
      colors: [
        Colors.transparent,
        colors[0].withOpacity(0.0),
        colors[1].withOpacity(0.4),
        colors[2],
        colors[3],
        Colors.transparent,
      ],
      stops: const [0.0, 0.70, 0.80, 0.88, 0.95, 1.0],
      transform: GradientRotation(progress * 2 * pi),
    );

    final paint = Paint()
      ..shader = gradient.createShader(rect)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;

    canvas.drawRRect(rrect, paint);
  }

  @override
  bool shouldRepaint(covariant _GradientBorderPainter oldDelegate) {
    return progress != oldDelegate.progress;
  }
}
