import 'package:flutter/material.dart';
import '../theme.dart';

/// Modern filled text field with label support
class AppTextField extends StatelessWidget {
  final String? label;
  final String? hint;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? suffix;
  final int maxLines;
  final ValueChanged<String>? onChanged;
  final String? errorText;
  final bool enabled;
  final Widget? prefixIcon;

  const AppTextField({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.obscureText = false,
    this.keyboardType,
    this.suffix,
    this.maxLines = 1,
    this.onChanged,
    this.errorText,
    this.enabled = true,
    this.prefixIcon,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: const TextStyle(
              fontFamily: AppTheme.secondaryFont,
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: AppTheme.bodyTextColor,
            ),
          ),
          const SizedBox(height: 8),
        ],
        TextField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          maxLines: maxLines,
          enabled: enabled,
          onChanged: onChanged,
          style: const TextStyle(
            fontFamily: AppTheme.secondaryFont,
            fontSize: 16,
            color: AppTheme.bodyTextColor,
          ),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: AppTheme.grayColor.withOpacity(0.08),
            prefixIcon: prefixIcon,
            suffixText: suffix,
            suffixStyle: const TextStyle(
              fontFamily: AppTheme.secondaryFont,
              fontSize: 16,
              color: AppTheme.grayColor,
            ),
            errorText: errorText,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide: BorderSide.none,
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide: BorderSide.none,
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide: const BorderSide(color: AppTheme.primaryColor, width: 2),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppTheme.inputRadius),
              borderSide: const BorderSide(color: AppTheme.errorColor),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          ),
        ),
      ],
    );
  }
}
