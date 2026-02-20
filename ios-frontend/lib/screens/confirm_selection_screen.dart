import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/step_progress_bar.dart';

class ConfirmSelectionContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSuccess;

  const ConfirmSelectionContent({super.key, this.onBack, this.onSuccess});

  @override
  State<ConfirmSelectionContent> createState() =>
      _ConfirmSelectionContentState();
}

class _ConfirmSelectionContentState extends State<ConfirmSelectionContent> {
  void _retakePhoto() {
    if (widget.onBack != null) {
      widget.onBack!();
    } else {
      Navigator.pop(context);
    }
  }

  void _confirmSelection() {
    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    // Fire-and-forget: upload runs in background.
    // Upload-readiness is checked downstream on the analyzing screen.
    projectProvider.uploadProjectImage(context);

    if (widget.onSuccess != null) {
      widget.onSuccess!();
    } else {
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        if (!projectProvider.hasProjectImage && !ProjectProvider.demoMode) {
          return Center(
            child: Text(
              'No image selected',
              style: AppTheme.dmSans(
                fontSize: 16,
                color: AppTheme.textSecondary,
              ),
            ),
          );
        }

        return Column(
          children: [
            // Header with logo
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
              child: Row(
                children: [
                  // Spaces. logo
                  Text(
                    'Spaces.',
                    style: AppTheme.dmSans(
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
            ),

            // Progress bar
            const StepProgressBar(currentStep: 2, totalSteps: 8),

            // Scrollable content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 24),

                    // Title
                    Text(
                      'Confirm Selection.',
                      style: AppTheme.dmSans(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),

                    const SizedBox(height: 24),

                    // Large image preview
                    Container(
                      width: double.infinity,
                      height: MediaQuery.of(context).size.height * 0.55,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.08),
                            blurRadius: 20,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: projectProvider.getProjectImageProvider() != null
                            ? Image(
                                image: projectProvider
                                    .getProjectImageProvider()!,
                                fit: BoxFit.cover,
                              )
                            : Container(
                                color: AppTheme.scaffoldBackground,
                                child: Center(
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        IconsaxPlusLinear.image,
                                        size: 48,
                                        color: AppTheme.textTertiary,
                                      ),
                                      const SizedBox(height: 12),
                                      Text(
                                        'Demo Mode',
                                        style: AppTheme.dmSans(
                                          fontSize: 14,
                                          color: AppTheme.textTertiary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                      ),
                    ),

                    const SizedBox(height: 100), // Space for bottom bar
                  ],
                ),
              ),
            ),

            // Sticky bottom CTA bar
            _buildBottomButtons(),
          ],
        );
      },
    );
  }

  Widget _buildBottomButtons() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 12,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            // Retake button
            Expanded(
              child: SizedBox(
                height: 56,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    side: const BorderSide(
                      color: AppTheme.dividerColor,
                      width: 1.5,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: _retakePhoto,
                  child: Text(
                    'Retake Photo',
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
              ),
            ),

            const SizedBox(width: 12),

            // Use Photo button
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: _confirmSelection,
                  child: Text(
                    'Continue',
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
