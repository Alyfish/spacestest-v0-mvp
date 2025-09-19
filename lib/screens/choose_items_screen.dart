import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:spaces/utils/logger.dart';
import '../providers/project_provider.dart';
import '../providers/user_provider.dart';
import '../models/marker.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
import '../widgets/interactive_image_widget.dart';
import '../widgets/marker_input_dialog.dart';
import '../widgets/marker_widget.dart';

class ChooseItemsScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseItemsScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundColor,
        elevation: 0,
        toolbarHeight: 70,
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10.0),
              child: Image.asset(
                'assets/logo/logo.png',
                height: 100,
                width: 100,
              ),
            ),
          ],
        ),
      ),
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: ChooseItemsContent(onBack: onBack, onContinue: onContinue),
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.backgroundColor,
        selectedItemColor: AppTheme.primaryColor,
        unselectedItemColor: AppTheme.grayColor,
        selectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
        unselectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w400,
        ),
        currentIndex: 0, // Home tab stays selected during flow
        onTap: (_) {}, // Disabled during flow
        items: const [
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.home),
            activeIcon: Icon(IconsaxPlusBold.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.discover),
            activeIcon: Icon(IconsaxPlusBold.discover),
            label: 'Discover',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bag_2),
            activeIcon: Icon(IconsaxPlusBold.bag_2),
            label: 'Cart',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bookmark),
            activeIcon: Icon(IconsaxPlusBold.bookmark),
            label: 'Saved',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.profile_circle),
            activeIcon: Icon(IconsaxPlusBold.profile_circle),
            label: 'Profile',
          ),
        ],
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
    print('ChooseItemsScreen: initState called');

    // Trigger a rebuild to ensure markers are displayed when screen loads
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

  void _onContinue() async {
    if (_isLoading) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    AppLogger.info(projectProvider.getMarkersJson().toString());
    // Check if there are any markers to save
    if (!projectProvider.hasMarkers) {
      // Allow continuing without markers
      if (widget.onContinue != null) {
        widget.onContinue!();
      }
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // Save markers to API when continue is pressed
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
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Couldn\'t save the data'),
            backgroundColor: AppTheme.errorColor,
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

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 36.0, vertical: 24.0),
      child: Column(
        children: [
          // Title and subtitle section
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Choose Items to Redesign.',
                    style: AppTheme.sectionTitleStyle.copyWith(fontSize: 36),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Unselected items remain unchanged in your design',
                style: TextStyle(
                  fontFamily: AppTheme.secondaryFont,
                  fontSize: 15,
                  fontWeight: FontWeight.w100,
                  color: AppTheme.bodyTextColor,
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Image section with markers
          Expanded(
            child: Consumer<ProjectProvider>(
              builder: (context, projectProvider, child) {
                final imageProvider = projectProvider.getProjectImageProvider();

                if (imageProvider == null) {
                  return Container(
                    decoration: BoxDecoration(
                      color: AppTheme.grayColor.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            IconsaxPlusLinear.gallery,
                            size: 48,
                            color: AppTheme.grayColor,
                          ),
                          SizedBox(height: 16),
                          Text(
                            'No image available',
                            style: TextStyle(
                              fontFamily: AppTheme.secondaryFont,
                              fontSize: 16,
                              color: AppTheme.grayColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }
                AppLogger.info(
                  'Displaying project image with markers ${projectProvider.markers.toString()}',
                );
                return ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: InteractiveImageWidget(
                    imageProvider: imageProvider,
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
                );
              },
            ),
          ),

          const SizedBox(height: 40),

          // Action buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Back button
              CustomOutlinedButton(
                text: '',
                icon: IconsaxPlusLinear.arrow_left_2,
                onPressed: widget.onBack ?? () => Navigator.pop(context),
                textColor: AppTheme.bodyTextColor,
                borderColor: AppTheme.transparent,
                iconColor: AppTheme.bodyTextColor,
              ),

              const SizedBox(width: 16),
              CustomOutlinedButton(
                text: 'Continue',
                icon: IconsaxPlusLinear.arrow_right_2,
                onPressed: _onContinue,
                textColor: AppTheme.primaryColor,
                borderColor: AppTheme.bodyTextColor,
                iconColor: AppTheme.primaryColor,
              ),

              // Continue button
            ],
          ),
        ],
      ),
    );
  }
}
