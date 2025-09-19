import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../providers/user_provider.dart';
// import '../services/api_service.dart'; // Keep for when API is uncommented
import '../theme.dart';
import '../utils/logger.dart';
import '../widgets/custom_outlined_button.dart';

class ConfirmInspirationContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSuccess;

  const ConfirmInspirationContent({super.key, this.onBack, this.onSuccess});

  @override
  State<ConfirmInspirationContent> createState() =>
      _ConfirmInspirationContentState();
}

class _ConfirmInspirationContentState extends State<ConfirmInspirationContent> {
  final PageController _pageController = PageController();
  int _currentIndex = 0;
  bool _isUploading = false;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _addMoreImages() {
    if (widget.onBack != null) {
      widget.onBack!();
    } else {
      Navigator.pop(context);
    }
  }

  Future<void> _confirmSelection() async {
    if (_isUploading) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    final userProvider = Provider.of<UserProvider>(context, listen: false);

    if (!projectProvider.hasMultipleInspirationImages) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No inspiration images to upload'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() {
      _isUploading = true;
    });

    try {
      final authToken = userProvider.user.token;
      if (authToken == null) {
        throw Exception('Authentication token not available');
      }

      AppLogger.info(
        'Uploading ${projectProvider.inspirationImages.length} inspiration images...',
      );

      // TODO: Uncomment when API is ready
      // final success = await ApiService.uploadInspirationImagesBatch(
      //   projectProvider.currentProject!.id,
      //   authToken,
      //   projectProvider.inspirationImages,
      // );

      // if (success) {
      //   AppLogger.info('Inspiration images uploaded successfully');
      //   // Call success callback to move to next screen
      //   if (widget.onSuccess != null) {
      //     widget.onSuccess!();
      //   }
      // } else {
      //   throw Exception('Failed to upload inspiration images');
      // }

      // Mock API call - simulate upload delay and success
      await Future.delayed(const Duration(seconds: 2));
      
      AppLogger.info('Inspiration images uploaded successfully (MOCKED)');

      // Call success callback to move to next screen
      if (widget.onSuccess != null) {
        widget.onSuccess!();
      }
    } catch (e) {
      AppLogger.error('Failed to upload inspiration images', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  Widget _buildCarousel(List<File> images) {
    return Column(
      children: [
        // Main carousel
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            onPageChanged: (index) {
              setState(() {
                _currentIndex = index;
              });
            },
            itemCount: images.length,
            itemBuilder: (context, index) {
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.bodyTextColor.withValues(alpha: 0.1),
                      blurRadius: 20,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.file(
                    images[index],
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
              );
            },
          ),
        ),

        const SizedBox(height: 24),

        // Image counter
        Text(
          '${_currentIndex + 1} of ${images.length}',
          style: TextStyle(
            fontFamily: AppTheme.secondaryFont,
            fontSize: 16,
            fontWeight: FontWeight.w300,
            color: AppTheme.bodyTextColor.withValues(alpha: 0.7),
          ),
        ),

        const SizedBox(height: 16),

        // Page indicators (dots)
        if (images.length > 1)
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              images.length,
              (index) => Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _currentIndex == index
                      ? AppTheme.bodyTextColor
                      : AppTheme.bodyTextColor.withValues(alpha: 0.3),
                ),
              ),
            ),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final images = projectProvider.inspirationImages;

        if (images.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  IconsaxPlusLinear.gallery,
                  size: 80,
                  color: AppTheme.grayColor,
                ),
                const SizedBox(height: 16),
                const Text(
                  'No inspiration images selected',
                  style: TextStyle(
                    fontFamily: AppTheme.secondaryFont,
                    fontSize: 16,
                    color: AppTheme.grayColor,
                  ),
                ),
                const SizedBox(height: 24),
                CustomOutlinedButton(
                  text: 'Add Images',
                  onPressed: _addMoreImages,
                ),
              ],
            ),
          );
        }

        return Column(
          children: [
            // Title section
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  const Text(
                    'Confirm Selection',
                    style: AppTheme.sectionTitleStyle,
                  ),
                ],
              ),
            ),

            // Carousel section
            Expanded(child: _buildCarousel(images)),

            // Action buttons
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  // Add More button
                  Expanded(
                    child: _isUploading
                        ? OutlinedButton(
                            onPressed: null,
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: const Text(
                              'Add More',
                              style: TextStyle(
                                fontFamily: AppTheme.primaryFont,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.grayColor,
                              ),
                            ),
                          )
                        : CustomOutlinedButton(
                            text: 'Add More',
                            onPressed: _addMoreImages,
                          ),
                  ),

                  const SizedBox(width: 16),

                  // Confirm button
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _isUploading ? null : _confirmSelection,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _isUploading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              'Confirm',
                              style: TextStyle(
                                fontFamily: AppTheme.primaryFont,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),

            // Back button at bottom (optional, for consistency)
            if (widget.onBack != null)
              Padding(
                padding: const EdgeInsets.only(
                  left: 16.0,
                  right: 16.0,
                  bottom: 16.0,
                ),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: IconButton(
                    onPressed: _isUploading ? null : widget.onBack,
                    icon: const Icon(
                      IconsaxPlusLinear.arrow_left_2,
                      color: AppTheme.bodyTextColor,
                      size: 32,
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
