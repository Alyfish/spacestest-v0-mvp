import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/step_progress_bar.dart';

class UploadInspirationContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onConfirmSelection;
  final VoidCallback? onSkipToApproach;

  const UploadInspirationContent({
    super.key,
    this.onBack,
    this.onConfirmSelection,
    this.onSkipToApproach,
  });

  @override
  State<UploadInspirationContent> createState() =>
      _UploadInspirationContentState();
}

class _UploadInspirationContentState extends State<UploadInspirationContent> {
  bool _isLoading = false;

  Future<void> _pickMultipleFromGallery() async {
    setState(() => _isLoading = true);

    if (ProjectProvider.demoMode) {
      await Future.delayed(const Duration(milliseconds: 500));
      if (mounted) {
        setState(() => _isLoading = false);
        if (widget.onConfirmSelection != null) widget.onConfirmSelection!();
      }
      return;
    }

    try {
      final result = await Permission.photos.request();
      if (!result.isGranted && !result.isLimited) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Photo access permission required',
                style: AppTheme.dmSans(color: Colors.white),
              ),
              backgroundColor: AppTheme.errorColor,
            ),
          );
        }
        setState(() => _isLoading = false);
        return;
      }

      final ImagePicker picker = ImagePicker();
      final List<XFile> images = await picker.pickMultiImage(
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (images.isNotEmpty && mounted) {
        final projectProvider = Provider.of<ProjectProvider>(
          context,
          listen: false,
        );
        projectProvider.setInspirationImages(
          images.map((x) => File(x.path)).toList(),
        );

        // Navigate to confirm screen
        if (widget.onConfirmSelection != null) {
          widget.onConfirmSelection!();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Failed to pick images: $e',
              style: AppTheme.dmSans(color: Colors.white),
            ),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final selectedImages = projectProvider.inspirationImages;
        final hasImages = selectedImages.isNotEmpty;

        return Scaffold(
          backgroundColor: AppTheme.scaffoldBackground,
          body: SafeArea(
            child: Column(
              children: [
                // Header with logo
                _buildHeader(),

                // Progress bar
                const SizedBox(height: 8),
                const StepProgressBar(currentStep: 5, totalSteps: 10),

                // Content
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 24),

                        // Title
                        Text(
                          'Upload Inspiration.',
                          style: AppTheme.dmSans(
                            fontSize: 26,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textPrimary,
                          ),
                        ),

                        const SizedBox(height: 8),

                        // Subtitle
                        Text(
                          'Add photos that inspire your vision',
                          style: AppTheme.dmSans(
                            fontSize: 15,
                            color: AppTheme.textSecondary,
                          ),
                        ),

                        const SizedBox(height: 32),

                        // Upload Card
                        _buildUploadCard(),

                        // Selected images grid
                        if (hasImages) ...[
                          const SizedBox(height: 24),
                          Text(
                            '${selectedImages.length} image${selectedImages.length == 1 ? '' : 's'} selected',
                            style: AppTheme.dmSans(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.primaryColor,
                            ),
                          ),
                          const SizedBox(height: 12),
                          _buildSelectedImagesGrid(selectedImages),
                        ],

                        const SizedBox(height: 100),
                      ],
                    ),
                  ),
                ),

                // Bottom Buttons
                _buildBottomButtons(hasImages),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          // Spaces. logo
          Image.asset('assets/logo/logo.png', height: 32),
        ],
      ),
    );
  }

  Widget _buildUploadCard() {
    return GestureDetector(
      onTap: _isLoading ? null : _pickMultipleFromGallery,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 48),
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.dividerColor, width: 1.5),
        ),
        child: Column(
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(16),
              ),
              child: _isLoading
                  ? Padding(
                      padding: const EdgeInsets.all(20),
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: AppTheme.primaryColor,
                      ),
                    )
                  : Icon(
                      IconsaxPlusLinear.gallery_add,
                      size: 32,
                      color: AppTheme.primaryColor,
                    ),
            ),
            const SizedBox(height: 16),
            Text(
              'Tap to add photos',
              style: AppTheme.dmSans(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Select multiple inspiration images',
              style: AppTheme.dmSans(
                fontSize: 14,
                color: AppTheme.textTertiary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSelectedImagesGrid(List<File> images) {
    return SizedBox(
      height: 80,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: images.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          return ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(
              images[index],
              width: 80,
              height: 80,
              fit: BoxFit.cover,
            ),
          );
        },
      ),
    );
  }

  Widget _buildBottomButtons(bool hasImages) {
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
            // Cancel button
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
                  onPressed: widget.onBack,
                  child: Text(
                    'Back',
                    style: AppTheme.dmSans(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
              ),
            ),

            const SizedBox(width: 12),

            // Continue/Skip button
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
                  onPressed: hasImages
                      ? widget.onConfirmSelection
                      : widget.onSkipToApproach,
                  child: Text(
                    hasImages ? 'Continue' : 'Skip',
                    style: AppTheme.dmSans(
                      fontSize: 17,
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
