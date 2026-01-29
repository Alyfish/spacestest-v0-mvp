import 'package:flutter/material.dart';
import '../theme.dart';

/// A horizontal progress indicator showing step completion
/// with pill-shaped segments
class StepProgressBar extends StatelessWidget {
  final int currentStep; // 1-indexed (current step being displayed)
  final int totalSteps;

  const StepProgressBar({
    super.key,
    required this.currentStep,
    this.totalSteps = 11,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: List.generate(totalSteps, (index) {
          final stepNumber = index + 1;
          final isCompleted = stepNumber < currentStep;
          final isCurrent = stepNumber == currentStep;

          return Expanded(
            child: Container(
              height: 4,
              margin: EdgeInsets.only(
                right: index < totalSteps - 1 ? 4 : 0,
              ),
              decoration: BoxDecoration(
                color: isCompleted || isCurrent
                    ? AppTheme.primaryColor
                    : AppTheme.dividerColor,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          );
        }),
      ),
    );
  }
}
