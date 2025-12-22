import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:spaces/widgets/icon_button.dart';
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
    return SizedBox(
      width: MediaQuery.of(context).size.width,
      child: Column(
        children: [
          // Main carousel with blurred background
          Stack(
            children: [
              // Blurred background image
              if (images.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0),
                  height: MediaQuery.of(context).size.height * 0.45,
                  margin: const EdgeInsets.only(bottom: 20),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: ImageFiltered(
                      imageFilter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                      child: Image.file(
                        images[_currentIndex % images.length],
                        fit: BoxFit.cover,
                        color: Colors.black.withValues(alpha: 0.2),
                        colorBlendMode: BlendMode.darken,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            decoration: BoxDecoration(
                              color: AppTheme.grayColor.withValues(alpha: 0.3),
                              borderRadius: BorderRadius.circular(20),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                ),

              // Main carousel
              Container(
                height: MediaQuery.of(context).size.height * 0.45,
                decoration: BoxDecoration(
                  color: AppTheme.transparent,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.2),
                      blurRadius: 20,
                      spreadRadius: 5,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: PageView.builder(
                  controller: _pageController,
                  onPageChanged: (index) {
                    setState(() {
                      _currentIndex = index;
                    });
                  },
                  itemCount: images.length,
                  itemBuilder: (context, index) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 4.0,
                      ), // Gap between images
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: Image.file(
                          images[index],
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) {
                            return Container(
                              decoration: BoxDecoration(
                                color: AppTheme.grayColor.withValues(
                                  alpha: 0.2,
                                ),
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
            ],
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
                        ? AppTheme.primaryColor
                        : AppTheme.primaryColor.withValues(alpha: 0.1),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final images = projectProvider.inspirationImages;

        if (images.isEmpty) {
          return Column(
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
          );
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12),
          child: Column(
            children: [
              // Title section
              Row(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4.0),
                    child: const Text(
                      'Confirm Selection',
                      style: AppTheme.sectionTitleStyle,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 16),
              // Carousel section
              SizedBox(
                height: MediaQuery.of(context).size.height * 0.52,
                child: _buildCarousel(images),
              ),

              // Back button at bottom (optional, for consistency)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (widget.onBack != null) ...[
                      Align(
                        alignment: Alignment.centerLeft,
                        child: IconButtonWidget(
                          icon: IconsaxPlusLinear.arrow_left_2,
                          onPressed: widget.onBack!,
                        ),
                      ),
                    ],
                    if (widget.onSuccess != null) ...[
                      CustomOutlinedButton(
                        text: _isUploading ? 'Uploading...' : 'Continue',
                        onPressed: _confirmSelection,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
