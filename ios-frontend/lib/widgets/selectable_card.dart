import 'package:flutter/material.dart';
import '../theme.dart';

/// Selectable card with clean selection state
/// Selected: 2px primary border + check badge (no pink tint)
class SelectableCard extends StatelessWidget {
  final Widget child;
  final bool isSelected;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry? padding;
  final bool showCheckIcon;
  final double? borderRadius;

  const SelectableCard({
    super.key,
    required this.child,
    this.isSelected = false,
    this.onTap,
    this.padding,
    this.showCheckIcon = true,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: padding ?? EdgeInsets.all(AppTheme.cardPadding),
        decoration: BoxDecoration(
          // No tint - just white background
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(borderRadius ?? AppTheme.cardRadius),
          border: Border.all(
            color: isSelected 
                ? AppTheme.primaryColor 
                : AppTheme.cardBorderColor,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Stack(
          children: [
            child,
            // Check badge in top-right
            if (isSelected && showCheckIcon)
              Positioned(
                top: 0,
                right: 0,
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
    );
  }
}
