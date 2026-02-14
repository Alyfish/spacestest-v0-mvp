import 'package:flutter/material.dart';
import 'custom_outlined_button.dart';

class PhotoActionWidget extends StatelessWidget {
  final String imagePath;
  final String buttonText;
  final VoidCallback onPressed;
  final double? imageWidth;
  final double? imageHeight;
  final Color? backgroundColor;
  final bool mirror;
  final double fontSize;
  final double iconSize;
  final double scale;

  const PhotoActionWidget({
    super.key,
    required this.imagePath,
    required this.buttonText,
    required this.onPressed,
    this.imageWidth = 160,
    this.imageHeight = 160,
    this.backgroundColor,
    this.mirror = false,
    this.fontSize = 20,
    this.iconSize = 24,
    this.scale = 1.5,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Simple Image Display
        Expanded(
          flex: 3,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: OverflowBox(
              maxWidth: double.infinity,
              maxHeight: double.infinity,
              child: Transform(
                alignment: Alignment.center,
                transform: mirror ? Matrix4.rotationY(3.14159) : Matrix4.identity(),
                child: Transform.scale(
                  scale: scale, // Scale up to make main content larger, allowing shadows to overflow
                  child: Image.asset(
                    imagePath,
                    width: imageWidth,
                    height: imageHeight,
                    fit: BoxFit.contain, // Use contain but with scaling
                    alignment: Alignment.center,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        // Button - Full Width
        SizedBox(
          width: double.infinity,
          child: CustomOutlinedButton(
            text: buttonText,
            onPressed: onPressed,
            fontSize: fontSize,
            iconSize: iconSize,
          ),
        ),
      ],
    );
  }
}
