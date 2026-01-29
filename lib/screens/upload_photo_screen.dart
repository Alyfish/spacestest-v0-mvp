import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import '../providers/project_provider.dart';
import '../theme.dart';

class UploadPhotoContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onConfirmSelection;

  const UploadPhotoContent({super.key, this.onBack, this.onConfirmSelection});

  @override
  State<UploadPhotoContent> createState() => _UploadPhotoContentState();
}

class _UploadPhotoContentState extends State<UploadPhotoContent> {
  bool _hasTriggeredPicker = false;

  @override
  void initState() {
    super.initState();
    // Auto-trigger gallery picker when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_hasTriggeredPicker) {
        _hasTriggeredPicker = true;
        _pickFromGallery();
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
      final result = await Permission.photos.request();
      if (!result.isGranted && !result.isLimited) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Photo access permission is required'), backgroundColor: AppTheme.errorColor),
          );
          // Exit flow if permission denied
          if (widget.onBack != null) {
            widget.onBack!();
          }
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
        projectProvider.setProjectImage(File(image.path));

        if (widget.onConfirmSelection != null) {
          widget.onConfirmSelection!();
        }
      } else if (mounted) {
        // User cancelled picker - exit flow
        if (widget.onBack != null) {
          widget.onBack!();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: AppTheme.errorColor),
        );
        // Exit flow on error
        if (widget.onBack != null) {
          widget.onBack!();
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Minimal UI - just show loading while picker is open
    // Note: Scaffold is provided by CreateFlowScreen
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
            'Opening gallery...',
            style: AppTheme.dmSans(
              fontSize: 16,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
