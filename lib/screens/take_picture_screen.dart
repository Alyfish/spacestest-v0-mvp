import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/image_provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../utils/logger.dart';

class TakePictureScreen extends StatefulWidget {
  const TakePictureScreen({
    super.key,
    required this.onBack,
    required this.onConfirmSelection,
  });
  final VoidCallback onConfirmSelection;

  final VoidCallback onBack;

  @override
  State<TakePictureScreen> createState() => _TakePictureScreenState();
}

class TakePictureContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onConfirmSelection;
  const TakePictureContent({super.key, this.onBack, this.onConfirmSelection});

  @override
  State<TakePictureContent> createState() => _TakePictureContentState();
}

class _TakePictureScreenState extends State<TakePictureScreen> {
  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: TakePictureContent(
          onConfirmSelection: widget.onConfirmSelection,
          onBack: widget.onBack,
        ),
      ),
    );
  }
}

class _TakePictureContentState extends State<TakePictureContent> {
  bool _isLoading = false;
  String? _errorMessage;
  bool _isFlashOn = false;

  @override
  void initState() {
    super.initState();
    _checkPermissions();
  }

  Future<void> _checkPermissions() async {
    // Demo mode: skip permission check on web
    if (ProjectProvider.demoMode) return;
    
    final cameraStatus = await Permission.camera.status;
    if (cameraStatus.isDenied) {
      await Permission.camera.request();
    }
  }

  void _toggleFlash() {
    setState(() {
      _isFlashOn = !_isFlashOn;
    });
  }

  Future<void> _takePhoto() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Demo mode: skip camera and simulate capture
    if (ProjectProvider.demoMode) {
      await Future.delayed(const Duration(milliseconds: 500));
      AppLogger.info('DEMO MODE: Simulated photo capture');
      if (mounted) {
        setState(() => _isLoading = false);
        widget.onConfirmSelection?.call();
      }
      return;
    }

    try {
      // Capture the image using the image provider for camera functionality
      final imageProvider = Provider.of<CapturedImageProvider>(
        context,
        listen: false,
      );
      final File? capturedImage = await imageProvider.takePhoto();

      if (capturedImage != null && mounted) {
        // Set the captured image as project image in ProjectProvider only
        final projectProvider = Provider.of<ProjectProvider>(
          context,
          listen: false,
        );
        projectProvider.setProjectImage(capturedImage);

        AppLogger.info('Image captured and set as project image');

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
      setState(() {
        _errorMessage = 'Failed to take photo: ${e.toString()}';
      });
      AppLogger.error('Error taking photo: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Camera preview placeholder (dark background)
        Container(
          width: double.infinity,
          height: double.infinity,
          color: Colors.black,
          child: Container(
            alignment: AlignmentDirectional.topCenter,
            margin: const EdgeInsets.only(top: 20),
            child: const Text(
              'Taking Picture.',
              style: TextStyle(
                fontFamily: AppTheme.primaryFont,
                fontSize: 32,
                color: AppTheme.backgroundColor,
              ),
            ),
          ),
        ),

        // Top bar with flash and close button
        Positioned(
          top: 16,
          left: 16,
          right: 16,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Flash toggle
              IconButton(
                onPressed: _toggleFlash,
                icon: Icon(
                  _isFlashOn
                      ? IconsaxPlusLinear.flash_1
                      : IconsaxPlusLinear.flash,
                  color: _isFlashOn
                      ? AppTheme.warningColor
                      : AppTheme.backgroundColor,
                  size: 24,
                ),
              ),

              // Close button
              IconButton(
                onPressed: widget.onBack ?? () => Navigator.pop(context),
                icon: const Icon(
                  IconsaxPlusLinear.close_circle,
                  color: AppTheme.backgroundColor,
                  size: 24,
                ),
              ),
            ],
          ),
        ),

        // Bottom controls
        Positioned(
          bottom: 40,
          left: 0,
          right: 0,
          child: Column(
            children: [
              if (_errorMessage != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.errorColor.withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(color: AppTheme.backgroundColor),
                    textAlign: TextAlign.center,
                  ),
                ),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Capture button
                  GestureDetector(
                    onTap: _isLoading ? null : _takePhoto,
                    child: Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.backgroundColor,
                        border: Border.all(
                          color: AppTheme.backgroundColor,
                          width: 6,
                        ),
                      ),
                      child: Container(
                        margin: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppTheme.bodyTextColor,
                            width: 2,
                          ),
                        ),
                        child: _isLoading
                            ? Center(
                                child: CircularProgressIndicator(
                                  color: AppTheme.bodyTextColor,
                                  strokeWidth: 2,
                                ),
                              )
                            : Container(
                                decoration: BoxDecoration(
                                  color: AppTheme.backgroundColor,
                                  borderRadius: BorderRadius.circular(35),
                                ),
                                width: 70,
                                height: 70,
                              ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}
