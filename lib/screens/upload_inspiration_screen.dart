import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:spaces/widgets/custom_outlined_button.dart';
import 'package:spaces/widgets/icon_button.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../utils/logger.dart';

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

  @override
  void initState() {
    super.initState();
    // Permissions will be requested when upload button is pressed
  }

  void _onContinue() {
    if (!mounted) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    final hasInspiration = projectProvider.inspirationImages.isNotEmpty;

    if (hasInspiration) {
      if (widget.onConfirmSelection != null) {
        widget.onConfirmSelection!();
      } else {
        AppLogger.error('Confirm Screen is not passed.');
      }
      return;
    }

    // Skip confirm step when nothing was uploaded
    if (widget.onSkipToApproach != null) {
      widget.onSkipToApproach!();
    } else {
      AppLogger.error('Skip-to-approach callback is not provided.');
    }
  }

  Future<void> _pickMultipleFromGallery() async {
    setState(() {
      _isLoading = true;
    });

    try {
      // Always request permission when button is pressed
      final result = await Permission.photos.request();

      if (result.isGranted) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Photo access permission is required to select images',
              ),
              backgroundColor: AppTheme.errorColor,
              duration: Duration(seconds: 3),
            ),
          );
        }
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
        final List<File> imageFiles = images
            .map((xfile) => File(xfile.path))
            .toList();

        // Store the selected images in project provider
        projectProvider.setInspirationImages(imageFiles);

        AppLogger.info('${images.length} inspiration images selected and set');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to select images: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final selectedImages = projectProvider.inspirationImages;

        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12),
          child: Column(
            children: [
              // Title section
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    const Text(
                      'Upload Inspiration',
                      style: AppTheme.sectionTitleStyle,
                    ),
                  ],
                ),
              ),

              // Main content area
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Center inspiration image (always shows the same image)
                  SizedBox(
                    width: MediaQuery.of(context).size.width,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: Image.asset(
                        'assets/images/upload_inspiration.png',
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            decoration: BoxDecoration(
                              color: AppTheme.grayColor.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Center(
                              child: Icon(
                                IconsaxPlusLinear.gallery,
                                size: 80,
                                color: AppTheme.grayColor,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ),

                  // const SizedBox(height: 12),

                  // Show count if images are selected
                  if (selectedImages.isNotEmpty) ...[
                    Text(
                      '${selectedImages.length} image${selectedImages.length == 1 ? '' : 's'} selected',
                      style: TextStyle(
                        fontFamily: AppTheme.secondaryFont,
                        fontSize: 16,
                        fontWeight: FontWeight.w300,
                        color: AppTheme.bodyTextColor.withValues(alpha: 0.7),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],

                  // Upload button
                  GestureDetector(
                    onTap: _isLoading ? null : _pickMultipleFromGallery,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _isLoading
                            ? CircularProgressIndicator(
                                color: AppTheme.bodyTextColor,
                                strokeWidth: 2,
                              )
                            : const Icon(
                                IconsaxPlusLinear.arrow_up_2,
                                color: AppTheme.bodyTextColor,
                                size: 32,
                              ),
                        const SizedBox(height: 8),
                        Text(
                          'upload',
                          style: TextStyle(
                            fontFamily: AppTheme.secondaryFont,
                            fontSize: 20,
                            fontWeight: FontWeight.w200,
                            color: AppTheme.bodyTextColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Back button at bottom
                  IconButtonWidget(
                    icon: IconsaxPlusLinear.arrow_left_2,
                    onPressed: widget.onBack ?? () => Navigator.pop(context),
                  ),

                  const SizedBox(width: 16),
                  CustomOutlinedButton(
                    text: 'Continue',
                    icon: IconsaxPlusLinear.arrow_right_2,
                    onPressed: _onContinue,
                    textColor: AppTheme.primaryColor,
                    borderColor: AppTheme.bodyTextColor,
                    iconColor: AppTheme.primaryColor,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}
