import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

class CustomOutlinedButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;
  final IconData icon;
  final bool iconAfterText;
  final Color borderColor;
  final Color textColor;
  final Color iconColor;
  final double fontSize;
  final double iconSize;

  const CustomOutlinedButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.icon = IconsaxPlusLinear.arrow_right_2,
    this.iconAfterText = true,
    this.borderColor = AppTheme.bodyTextColor,
    this.textColor = AppTheme.primaryColor,
    this.iconColor = AppTheme.primaryColor,
    this.fontSize = 20,
    this.iconSize = 20,
  });

  @override
  Widget build(BuildContext context) {
    final iconWidget = Icon(
      icon,
      size: iconSize,
      color: iconColor,
    );

    final textWidget = Text(
      text,
      style: TextStyle(
        fontFamily: AppTheme.primaryFont,
        fontSize: fontSize,
        fontWeight: FontWeight.w500,
        color: textColor,
      ),
    );

    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        side: BorderSide(color: borderColor, width: 1.5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(25),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: iconAfterText
            ? [
                textWidget,
                const SizedBox(width: 8),
                iconWidget,
              ]
            : [
                iconWidget,
                const SizedBox(width: 8),
                textWidget,
              ],
      ),
    );
  }
}
