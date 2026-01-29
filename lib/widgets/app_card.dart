import 'package:flutter/material.dart';
import '../theme.dart';

/// Reusable card with consistent styling - radius 16, subtle border
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final double? borderRadius;
  final bool showBorder;
  final bool showShadow;
  final VoidCallback? onTap;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.backgroundColor,
    this.borderRadius,
    this.showBorder = true,
    this.showShadow = true, // Default enabled for premium look
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: padding ?? EdgeInsets.all(AppTheme.cardPadding),
      decoration: BoxDecoration(
        color: backgroundColor ?? AppTheme.backgroundColor,
        borderRadius: BorderRadius.circular(borderRadius ?? AppTheme.cardRadius),
        border: showBorder
            ? Border.all(
                color: AppTheme.unselectedCardOutline.withOpacity(0.12),
                width: 1,
              )
            : null,
        boxShadow: showShadow
            ? [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: card,
      );
    }

    return card;
  }
}
