import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../providers/user_provider.dart';
import '../theme.dart';
import '../utils/logger.dart';
import '../widgets/step_progress_bar.dart';

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

  Future<void> _confirmSelection() async {
    if (_isUploading) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    final userProvider = Provider.of<UserProvider>(context, listen: false);

    if (!projectProvider.hasMultipleInspirationImages) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'No inspiration images to upload',
            style: AppTheme.dmSans(color: Colors.white),
          ),
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

      // Mock API call - simulate upload delay and success
      await Future.delayed(const Duration(seconds: 1));

      AppLogger.info('Inspiration images uploaded successfully');

      // Call success callback to move to next screen
      if (widget.onSuccess != null) {
        widget.onSuccess!();
      }
    } catch (e) {
      AppLogger.error('Failed to upload inspiration images', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Upload failed: ${e.toString()}',
              style: AppTheme.dmSans(color: Colors.white),
            ),
            backgroundColor: AppTheme.errorColor,
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

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final images = projectProvider.inspirationImages;

        if (images.isEmpty && !ProjectProvider.demoMode) {
          return Scaffold(
            backgroundColor: AppTheme.scaffoldBackground,
            body: SafeArea(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      IconsaxPlusLinear.gallery,
                      size: 64,
                      color: AppTheme.textTertiary,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'No inspiration images selected',
                      style: AppTheme.dmSans(
                        fontSize: 16,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),
                    TextButton(
                      onPressed: widget.onBack,
                      child: Text(
                        'Go Back',
                        style: AppTheme.dmSans(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.primaryColor,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }

        return Scaffold(
          backgroundColor: AppTheme.scaffoldBackground,
          body: SafeArea(
            child: Column(
              children: [
                // Header with logo and settings
                _buildHeader(),

                // Progress bar
                const SizedBox(height: 8),
                const StepProgressBar(currentStep: 6, totalSteps: 10),

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
                          'Confirm Inspiration.',
                          style: AppTheme.dmSans(
                            fontSize: 26,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textPrimary,
                          ),
                        ),

                        const SizedBox(height: 8),

                        // Subtitle
                        Text(
                          '${images.length} image${images.length == 1 ? '' : 's'} selected',
                          style: AppTheme.dmSans(
                            fontSize: 15,
                            color: AppTheme.textSecondary,
                          ),
                        ),

                        const SizedBox(height: 24),

                        // Image Carousel
                        _buildImageCarousel(images),

                        const SizedBox(height: 100),
                      ],
                    ),
                  ),
                ),

                // Bottom Buttons
                _buildBottomButtons(),
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
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Spaces. logo
          Image.asset(
            'assets/logo/logo.png',
            height: 32,
          ),
          // Settings icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.dividerColor,
                width: 1,
              ),
            ),
            child: IconButton(
              icon: const Icon(
                Icons.settings_outlined,
                color: AppTheme.textPrimary,
                size: 22,
              ),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImageCarousel(List<File> images) {
    // For demo mode, show placeholder
    if (ProjectProvider.demoMode && images.isEmpty) {
      return Container(
        height: MediaQuery.of(context).size.height * 0.5,
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
          child: Stack(
            fit: StackFit.expand,
            children: [
              Image.asset(
                'assets/images_for_choose_spaces_new/unsplash_7pCFUybP_P8_house cleaning.jpg',
                fit: BoxFit.cover,
              ),
              Positioned(
                top: 12,
                left: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    'Demo Mode',
                    style: AppTheme.dmSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        // Main carousel
        Container(
          height: MediaQuery.of(context).size.height * 0.5,
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
          child: PageView.builder(
            controller: _pageController,
            itemCount: images.length,
            onPageChanged: (index) => setState(() => _currentIndex = index),
            itemBuilder: (context, index) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.file(
                    images[index],
                    fit: BoxFit.cover,
                  ),
                ),
              );
            },
          ),
        ),

        // Page indicators
        if (images.length > 1) ...[
          const SizedBox(height: 16),
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
                      : AppTheme.primaryColor.withValues(alpha: 0.2),
                ),
              ),
            ),
          ),
        ],
      ],
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
            // Add More button
            Expanded(
              child: SizedBox(
                height: 56,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    side: const BorderSide(color: AppTheme.dividerColor, width: 1.5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: widget.onBack,
                  child: Text(
                    'Add More',
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

            // Continue button
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
                  onPressed: _isUploading ? null : _confirmSelection,
                  child: _isUploading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          'Continue',
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
