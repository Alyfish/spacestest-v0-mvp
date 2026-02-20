import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../providers/user_provider.dart';
import '../models/marker.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../utils/logger.dart';
import '../widgets/interactive_image_widget.dart';
import '../widgets/marker_input_dialog.dart';
import '../widgets/marker_widget.dart';
import '../widgets/step_progress_bar.dart';

/// Choose Items to Redesign - Marker placement screen
/// Users tap on the image to mark items they want to change
class ChooseItemsScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseItemsScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: ChooseItemsContent(onBack: onBack, onContinue: onContinue),
      ),
    );
  }
}

class ChooseItemsContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseItemsContent({super.key, this.onBack, this.onContinue});

  @override
  State<ChooseItemsContent> createState() => _ChooseItemsContentState();
}

class _ChooseItemsContentState extends State<ChooseItemsContent> {
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      setState(() {});
    });
  }

  void _showMarkerDialog(double x, double y) {
    showDialog(
      context: context,
      builder: (context) => MarkerInputDialog(
        x: x,
        y: y,
        onSave: (description) {
          final projectProvider = Provider.of<ProjectProvider>(
            context,
            listen: false,
          );
          projectProvider.addMarker(x, y, description);
        },
      ),
    );
  }

  void _editMarker(ImprovementMarker marker) {
    showDialog(
      context: context,
      builder: (context) => MarkerInputDialog(
        x: marker.position.x,
        y: marker.position.y,
        initialText: marker.description,
        isEditing: true,
        onSave: (description) {
          final projectProvider = Provider.of<ProjectProvider>(
            context,
            listen: false,
          );
          projectProvider.updateMarker(marker.id, description);
        },
        onDelete: () {
          final projectProvider = Provider.of<ProjectProvider>(
            context,
            listen: false,
          );
          projectProvider.deleteMarker(marker.id);
        },
      ),
    );
  }

  Future<void> _onContinue() async {
    if (_isLoading) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    final userProvider = Provider.of<UserProvider>(context, listen: false);

    // If no markers, just skip to next step
    if (!projectProvider.hasMarkers) {
      if (widget.onContinue != null) {
        widget.onContinue!();
      }
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final authToken = userProvider.user.token;
      if (authToken != null && projectProvider.currentProject != null) {
        await ApiService.saveImprovementMarkers(
          projectProvider.currentProject!.id,
          projectProvider.getMarkersJson(),
          authToken,
        );
      }

      if (mounted && widget.onContinue != null) {
        widget.onContinue!();
      }
    } catch (e) {
      AppLogger.error('Failed to save markers', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Couldn\'t save the data'),
            backgroundColor: AppTheme.errorColor,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            margin: const EdgeInsets.all(16),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _onSkip() {
    if (widget.onContinue != null) {
      widget.onContinue!();
    }
  }

  void _onCancel() {
    if (widget.onBack != null) {
      widget.onBack!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with logo
        _buildHeader(),

        // Progress bar
        const SizedBox(height: 8),
        const StepProgressBar(currentStep: 4, totalSteps: 8),

        // Content
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),

                // Title
                Text(
                  'Choose Items to Redesign.',
                  style: AppTheme.dmSans(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),

                const SizedBox(height: 8),

                // Subtitle
                Text(
                  'Tap on items you\'d like to change',
                  style: AppTheme.dmSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w400,
                    color: AppTheme.textSecondary,
                  ),
                ),

                const SizedBox(height: 24),

                // Interactive Image with Markers
                _buildInteractiveImage(),

                const SizedBox(height: 100), // Space for bottom buttons
              ],
            ),
          ),
        ),

        // Bottom Buttons
        _buildBottomButtons(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          // Spaces. logo
          Image.asset('assets/logo/logo.png', height: 32),
        ],
      ),
    );
  }

  Widget _buildInteractiveImage() {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final imageProvider = projectProvider.getProjectImageProvider();

        // Demo mode: use placeholder image when no project image
        final isDemoMode = imageProvider == null || ProjectProvider.demoMode;
        final displayProvider = isDemoMode
            ? const AssetImage(
                    'assets/images_for_choose_spaces_new/1_pb_8pa89uOlXOTsrM8sFWg.jpg',
                  )
                  as ImageProvider
            : imageProvider;

        return Container(
          height: MediaQuery.of(context).size.height * 0.52,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  color: Colors.black,
                  child: InteractiveImageWidget(
                    imageProvider: displayProvider,
                    fit: BoxFit.contain,
                    onImageTap: _showMarkerDialog,
                    overlayBuilder:
                        (imageWidth, imageHeight, displaySize, displayOffset) {
                          return Consumer<ProjectProvider>(
                            builder: (context, provider, child) {
                              return MarkerOverlay(
                                markers: provider.markers,
                                onMarkerTap: _editMarker,
                                imageWidth: imageWidth,
                                imageHeight: imageHeight,
                                displaySize: displaySize,
                                displayOffset: displayOffset,
                              );
                            },
                          );
                        },
                  ),
                ),
              ),
              // Demo mode badge
              if (isDemoMode)
                Positioned(
                  top: 12,
                  left: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
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
        );
      },
    );
  }

  Widget _buildBottomButtons() {
    return Consumer<ProjectProvider>(
      builder: (context, projectProvider, child) {
        final hasMarkers = projectProvider.hasMarkers;

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
            child: hasMarkers
                ? _buildCancelContinueButtons()
                : _buildSkipButton(),
          ),
        );
      },
    );
  }

  Widget _buildSkipButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: OutlinedButton(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppTheme.textSecondary,
          side: BorderSide(color: AppTheme.dividerColor, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        onPressed: _onSkip,
        child: Text(
          'Skip',
          style: AppTheme.dmSans(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            color: AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildCancelContinueButtons() {
    return Row(
      children: [
        // Cancel button
        Expanded(
          child: SizedBox(
            height: 56,
            child: OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.textPrimary,
                backgroundColor: AppTheme.scaffoldBackground,
                side: BorderSide(color: AppTheme.dividerColor, width: 1.5),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              onPressed: _onCancel,
              child: Text(
                'Back',
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
              onPressed: _isLoading ? null : _onContinue,
              child: _isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
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
    );
  }
}
