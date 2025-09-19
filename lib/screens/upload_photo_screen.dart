import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../utils/logger.dart';

class UploadPhotoContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onConfirmSelection;
  
  const UploadPhotoContent({super.key, this.onBack, this.onConfirmSelection});

  @override
  State<UploadPhotoContent> createState() => _UploadPhotoContentState();
}

class _UploadPhotoContentState extends State<UploadPhotoContent> {
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Permissions will be requested when upload button is pressed
  }

  Future<void> _pickFromGallery() async {
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
              content: Text('Photo access permission is required to select images'),
              backgroundColor: AppTheme.errorColor,
              duration: Duration(seconds: 3),
            ),
          );
        }
        return;
      }

      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (image != null && mounted) {
        final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
        final File imageFile = File(image.path);
        
        // Store the selected image only in project provider
        projectProvider.setProjectImage(imageFile);
        
        AppLogger.info('Gallery image selected and set as project image');
        
        // Navigate to confirm selection screen
        if (mounted) {
          if (widget.onConfirmSelection != null) {
            widget.onConfirmSelection!();
          } else {
            // Log that confirm screen navigation is not working
            AppLogger.error('Confirm Screen is not passed.');
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to select image: ${e.toString()}'),
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
    return Column(
      children: [
        // Title section
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              const Text(
                'Upload Photo',
                style: AppTheme.sectionTitleStyle,),
            ],
          ),
        ),
        
        // Main content area
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Center image
              Container(
                width: 280,
                height: 280,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.bodyTextColor.withValues(alpha:0.1),
                      blurRadius: 20,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.asset(
                    'assets/images/upload_photo_screen.png',
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        decoration: BoxDecoration(
                          color: AppTheme.grayColor.withValues(alpha:0.2),
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
              
              
              // Upload button
              GestureDetector(
                onTap: _isLoading ? null : _pickFromGallery,
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
        ),
        
        // Back button at bottom
        if (widget.onBack != null)
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: IconButton(
                onPressed: widget.onBack,
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
  }
}
