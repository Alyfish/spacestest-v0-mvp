import 'package:flutter/material.dart';
import '../theme.dart';

/// Secondary outline button - 56px height, 16 radius, gray outline
class SecondaryButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;
  final bool fullWidth;

  const SecondaryButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.icon,
    this.fullWidth = true,
  });

  @override
  Widget build(BuildContext context) {
    final isDisabled = onPressed == null && !isLoading;
    
    return SizedBox(
      width: fullWidth ? double.infinity : null,
      height: AppTheme.buttonHeight,
      child: OutlinedButton(
        onPressed: isLoading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: isDisabled 
              ? AppTheme.disabledText 
              : AppTheme.textPrimary,
          side: BorderSide(
            color: isDisabled 
                ? AppTheme.disabledFill 
                : AppTheme.lightGrayColor,
            width: 1,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
          ),
        ),
        child: isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppTheme.textPrimary,
                ),
              )
            : Row(
                mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: 20),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    text,
                    style: AppTheme.dmSans(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: isDisabled ? AppTheme.disabledText : AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
