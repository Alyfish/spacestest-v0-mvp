import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';


class ConfirmSelectionContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSuccess;

  const ConfirmSelectionContent({super.key, this.onBack, this.onSuccess});

  @override
  State<ConfirmSelectionContent> createState() => _ConfirmSelectionContentState();
}
class _ConfirmSelectionContentState extends State<ConfirmSelectionContent> {
  bool _isUploading = false;

  void _retakePhoto() {
    if (widget.onBack != null) {
      widget.onBack!();
    } else {
      Navigator.pop(context);
    }
  }

  Future<void> _confirmSelection() async {
    setState(() {
      _isUploading = true;
    });

    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      
      // Upload the project image
      final success = await projectProvider.uploadProjectImage(context);
      
      if (success && mounted) {
        // Clear project state after successful upload
        projectProvider.clearProject();
        
        if (widget.onSuccess != null) {
          widget.onSuccess!();
        } else {
          // Navigate back to home or show success message
          Navigator.popUntil(context, (route) => route.isFirst);
        }
        
        // Show success snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Project image uploaded successfully!'),
            backgroundColor: AppTheme.primaryColor,
          ),
        );
      } else {
        // Show error from project provider
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Upload failed: ${projectProvider.errorMessage ?? 'Unknown error'}'),
              backgroundColor: AppTheme.errorColor,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: ${e.toString()}'),
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
        if (!projectProvider.hasProjectImage) {
          return const Center(
            child: Text(
              'No image selected',
              style: TextStyle(
                fontFamily: AppTheme.secondaryFont,
                fontSize: 16,
                color: AppTheme.grayColor,
              ),
            ),
          );
        }

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 36.0, vertical: 24.0),
          child: Column(
            children: [
              // Title section
              Row(
                children: [
                  const Text(
                    'Confirm Selection',
                    style: AppTheme.sectionTitleStyle,),
                ],
              ),
              const SizedBox(height: 40),
              // Image preview
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                      Expanded(
                      child: Container(
                        width: double.infinity,
                        decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                          color: AppTheme.bodyTextColor.withValues(alpha:0.2),
                          blurRadius: 30,
                          spreadRadius: 5,
                          offset: const Offset(0, 8),
                          ),
                        ],
                        ),
                        child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: projectProvider.getProjectImageProvider() != null
                          ? Image(
                              image: projectProvider.getProjectImageProvider()!,
                              fit: BoxFit.cover,
                            )
                          : Container(
                              decoration: BoxDecoration(
                                color: AppTheme.grayColor.withValues(alpha: 0.3),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: const Center(
                                child: Icon(
                                  IconsaxPlusLinear.image,
                                  size: 48,
                                  color: AppTheme.grayColor,
                                ),
                              ),
                            ),
                        ),
                      ),
                      ),
                    
                    const SizedBox(height: 40),
                    
                    // Action buttons
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Retake button
                        CustomOutlinedButton(
                          onPressed: () => _retakePhoto(),
                          text: 'Retake',
                          icon: IconsaxPlusLinear.camera,
                        ),
                        
                        const SizedBox(width: 20),
                        
                        // Upload button
                        _isUploading
                            ? Container(
                                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                                decoration: BoxDecoration(
                                  color: AppTheme.primaryColor,
                                  borderRadius: BorderRadius.circular(25),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(
                                          AppTheme.backgroundColor,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    const Text(
                                      'Uploading...',
                                      style: TextStyle(
                                        color: AppTheme.backgroundColor,
                                        fontSize: 16,
                                        fontFamily: AppTheme.secondaryFont,
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            : CustomOutlinedButton(
                                onPressed: () => _confirmSelection(),
                                text: 'Upload',
                                icon: IconsaxPlusLinear.arrow_up,
                                borderColor: AppTheme.primaryColor,
                              ),
                      ],
                    ),
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
