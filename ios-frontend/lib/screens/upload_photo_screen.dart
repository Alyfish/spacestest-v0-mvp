import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../utils/logger.dart';

class UploadPhotoContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onConfirmSelection;
  final bool isCamera;

  const UploadPhotoContent({
    super.key,
    this.onBack,
    this.onConfirmSelection,
    this.isCamera = false,
  });

  @override
  State<UploadPhotoContent> createState() => _UploadPhotoContentState();
}

class _UploadPhotoContentState extends State<UploadPhotoContent> {
  bool _hasTriggeredPicker = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_hasTriggeredPicker) {
        _hasTriggeredPicker = true;
        if (widget.isCamera) {
          _pickFromCamera();
        } else {
          _pickFromGallery();
        }
      }
    });
  }

  Future<void> _pickFromGallery() async {
    // Demo mode bypass
    if (ProjectProvider.demoMode) {
      await Future.delayed(const Duration(milliseconds: 500));
      if (mounted && widget.onConfirmSelection != null) {
        widget.onConfirmSelection!();
      }
      return;
    }

    try {
      // image_picker uses PHPickerViewController on iOS 14+ which
      // does not require explicit photo library permission.
      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (image != null && mounted) {
        final projectProvider = Provider.of<ProjectProvider>(
          context,
          listen: false,
        );

        // Guard: project must exist with valid ID
        if (projectProvider.currentProject?.id == null ||
            projectProvider.currentProject!.id.isEmpty) {
          AppLogger.error('Cannot set image: no active project');
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Project not ready. Please start again.'),
              backgroundColor: AppTheme.errorColor,
            ),
          );
          widget.onBack?.call();
          return;
        }

        AppLogger.info(
          'Image picked: path=${image.path}, ext=${image.path.split(".").last}',
        );

        final stored = projectProvider.setProjectImage(File(image.path));
        if (!stored) {
          AppLogger.error('setProjectImage returned false — aborting flow');
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('Failed to prepare image'),
                backgroundColor: AppTheme.errorColor,
              ),
            );
          }
          widget.onBack?.call();
          return;
        }

        // Only advance if image was actually stored
        widget.onConfirmSelection?.call();
      } else if (mounted) {
        // User cancelled picker - exit flow
        widget.onBack?.call();
      }
    } catch (e) {
      if (mounted) {
        _showPermissionSettingsDialog(
          title: 'Photo Access Required',
          message:
              'Please allow photo library access in Settings to select images.',
        );
      }
    }
  }

  Future<void> _pickFromCamera() async {
    // Demo mode bypass
    if (ProjectProvider.demoMode) {
      await Future.delayed(const Duration(milliseconds: 500));
      if (mounted && widget.onConfirmSelection != null) {
        widget.onConfirmSelection!();
      }
      return;
    }

    try {
      // Check camera permission
      var status = await Permission.camera.status;

      if (status.isDenied) {
        status = await Permission.camera.request();
      }

      if (status.isPermanentlyDenied) {
        if (mounted) {
          _showPermissionSettingsDialog(
            title: 'Camera Access Required',
            message:
                'Please allow camera access in Settings to take photos of your space.',
          );
        }
        return;
      }

      if (!status.isGranted) {
        if (mounted) {
          widget.onBack?.call();
        }
        return;
      }

      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (image != null && mounted) {
        final projectProvider = Provider.of<ProjectProvider>(
          context,
          listen: false,
        );

        // Guard: project must exist with valid ID
        if (projectProvider.currentProject?.id == null ||
            projectProvider.currentProject!.id.isEmpty) {
          AppLogger.error('Cannot set image: no active project');
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Project not ready. Please start again.'),
              backgroundColor: AppTheme.errorColor,
            ),
          );
          widget.onBack?.call();
          return;
        }

        AppLogger.info(
          'Image captured: path=${image.path}, ext=${image.path.split(".").last}',
        );

        final stored = projectProvider.setProjectImage(File(image.path));
        if (!stored) {
          AppLogger.error('setProjectImage returned false — aborting flow');
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('Failed to prepare image'),
                backgroundColor: AppTheme.errorColor,
              ),
            );
          }
          widget.onBack?.call();
          return;
        }

        // Only advance if image was actually stored
        widget.onConfirmSelection?.call();
      } else if (mounted) {
        // User cancelled camera - exit flow
        widget.onBack?.call();
      }
    } catch (e) {
      if (mounted) {
        _showPermissionSettingsDialog(
          title: 'Camera Access Required',
          message:
              'Please allow camera access in Settings to take photos of your space.',
        );
      }
    }
  }

  void _showPermissionSettingsDialog({
    required String title,
    required String message,
  }) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          title,
          style: AppTheme.dmSans(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppTheme.textPrimary,
          ),
        ),
        content: Text(
          message,
          style: AppTheme.dmSans(fontSize: 15, color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              widget.onBack?.call();
            },
            child: Text(
              'Cancel',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              openAppSettings();
            },
            child: Text(
              'Go to Settings',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: AppTheme.primaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(
            strokeWidth: 2,
            color: AppTheme.primaryColor,
          ),
          const SizedBox(height: 24),
          Text(
            widget.isCamera ? 'Opening camera...' : 'Opening gallery...',
            style: AppTheme.dmSans(fontSize: 16, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }
}
