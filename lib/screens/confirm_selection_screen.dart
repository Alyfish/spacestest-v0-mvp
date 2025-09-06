import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/image_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';

class ConfirmSelectionScreen extends StatefulWidget {
  const ConfirmSelectionScreen({Key? key}) : super(key: key);

  @override
  State<ConfirmSelectionScreen> createState() => _ConfirmSelectionScreenState();
}

class ConfirmSelectionContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSuccess;
  
  const ConfirmSelectionContent({Key? key, this.onBack, this.onSuccess}) : super(key: key);

  @override
  State<ConfirmSelectionContent> createState() => _ConfirmSelectionContentState();
}

class _ConfirmSelectionScreenState extends State<ConfirmSelectionScreen> {
  bool _isUploading = false;

  void _retakePhoto() {
    Navigator.pop(context);
  }

  Future<void> _confirmSelection() async {
    setState(() {
      _isUploading = true;
    });

    try {
      final imageProvider = Provider.of<CapturedImageProvider>(context, listen: false);
      final success = await imageProvider.confirmSelection();
      
      if (success && mounted) {
        // Navigate back to home or show success message
        Navigator.popUntil(context, (route) => route.isFirst);
        
        // Show success snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Image uploaded successfully!'),
            backgroundColor: AppTheme.primaryColor,
          ),
        );
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
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Consumer<CapturedImageProvider>(
          builder: (context, imageProvider, child) {
            if (!imageProvider.hasImage) {
              return const Center(
                child: Text(
                  'No image selected',
                  style: TextStyle(
                    fontFamily: AppTheme.secondaryFont,
                    fontSize: 16,
                  ),
                ),
              );
            }

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Row(
                    children: [
                      // Logo
                      Image.asset(
                        'assets/logo/logo.png',
                        height: 40,
                        width: 40,
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'spaces.',
                        style: const TextStyle(
                          fontFamily: AppTheme.primaryFont,
                          fontSize: 24,
                          color: AppTheme.primaryColor,
                        ),
                      ),
                    ],
                  ),
                ),
                
                // Title
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Confirm Selection.',
                    style: const TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 32,
                      fontWeight: FontWeight.normal,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                ),
                
                
                // Image preview
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Container(
                      width: double.infinity,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.1),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(24),
                        child: Image.file(
                          imageProvider.capturedImage!,
                          fit: BoxFit.cover,
                        ),
                      ),
                    ),
                  ),
                ),
                
                const SizedBox(height: 32),
                
                // Action buttons
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Row(
                    children: [
                      // Retake button
                      Expanded(
                        child: CustomOutlinedButton(
                          text: 'Retake',
                          icon: IconsaxPlusLinear.arrow_left_2,
                          onPressed: _isUploading ? () {} : _retakePhoto,
                          borderColor: AppTheme.primaryColor,
                          textColor: AppTheme.primaryColor,
                          iconColor: AppTheme.primaryColor,
                          fontSize: 18,
                        ),
                      ),
                      
                      const SizedBox(width: 16),
                      
                      // Start/Upload button
                      Expanded(
                        child: Container(
                          height: 56,
                          child: ElevatedButton.icon(
                            onPressed: _isUploading ? null : _confirmSelection,
                            icon: _isUploading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Icon(
                                    IconsaxPlusLinear.arrow_right,
                                    color: Colors.white,
                                    size: 20,
                                  ),
                            label: Text(
                              _isUploading ? 'Uploading...' : 'Start',
                              style: const TextStyle(
                                fontFamily: AppTheme.primaryFont,
                                fontSize: 18,
                                color: Colors.white,
                                fontWeight: FontWeight.normal,
                              ),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.primaryColor,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(28),
                              ),
                              elevation: 0,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
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
      final imageProvider = Provider.of<CapturedImageProvider>(context, listen: false);
      final success = await imageProvider.confirmSelection();
      
      if (success && mounted) {
        if (widget.onSuccess != null) {
          widget.onSuccess!();
        } else {
          // Navigate back to home or show success message
          Navigator.popUntil(context, (route) => route.isFirst);
        }
        
        // Show success snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Image uploaded successfully!'),
            backgroundColor: AppTheme.primaryColor,
          ),
        );
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
    return Consumer<CapturedImageProvider>(
      builder: (context, imageProvider, child) {
        if (!imageProvider.hasImage) {
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

        return Column(
          children: [
            // Title section
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  const Text(
                    'Confirm Selection',
                    style: TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 32,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                ],
              ),
            ),
            
            // Image preview
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 300,
                    height: 400,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.bodyTextColor.withValues(alpha:0.2),
                          blurRadius: 15,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: Image(
                        image: imageProvider.getImageProvider(),
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 40),
                  
                  // Action buttons
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
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
        );
      },
    );
  }
}
