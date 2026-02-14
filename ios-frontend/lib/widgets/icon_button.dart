import 'package:flutter/material.dart';
import '../theme.dart';

class IconButtonWidget extends StatelessWidget {
  final IconData icon;
  final double size;
  final Color color;
  final VoidCallback onPressed;

  const IconButtonWidget({
    super.key,
    required this.icon,
    required this.onPressed,
    this.size = 24,
    this.color = AppTheme.bodyTextColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: Icon(icon, size: size, color: color),
    );
  }
}
