import 'package:flutter/material.dart';
import '../theme.dart';
import 'primary_button.dart';
import 'secondary_button.dart';

/// Sticky bottom CTA bar with safe area padding
class BottomCTABar extends StatelessWidget {
  final String primaryText;
  final VoidCallback? onPrimaryPressed;
  final String? secondaryText;
  final VoidCallback? onSecondaryPressed;
  final bool isLoading;
  final IconData? primaryIcon;

  const BottomCTABar({
    super.key,
    required this.primaryText,
    this.onPrimaryPressed,
    this.secondaryText,
    this.onSecondaryPressed,
    this.isLoading = false,
    this.primaryIcon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: AppTheme.screenPadding,
        right: AppTheme.screenPadding,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: BoxDecoration(
        color: AppTheme.backgroundColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: secondaryText != null
          ? Row(
              children: [
                Expanded(
                  child: SecondaryButton(
                    text: secondaryText!,
                    onPressed: onSecondaryPressed,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: PrimaryButton(
                    text: primaryText,
                    onPressed: onPrimaryPressed,
                    isLoading: isLoading,
                    icon: primaryIcon,
                  ),
                ),
              ],
            )
          : PrimaryButton(
              text: primaryText,
              onPressed: onPrimaryPressed,
              isLoading: isLoading,
              icon: primaryIcon,
            ),
    );
  }
}
