import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:spaces/screens/confirm_inspiration_screen.dart';
import 'package:spaces/screens/upload_inspiration_screen.dart';
import '../theme.dart';
import '../widgets/photo_action_widget.dart';
import '../widgets/marketplace_item_widget.dart';
import '../screens/take_picture_screen.dart';
import '../screens/upload_photo_screen.dart';
import '../screens/confirm_selection_screen.dart';
import '../screens/choose_space_screen.dart';
import '../screens/choose_items_screen.dart';
import '../screens/measure_room_screen.dart';
import '../providers/project_provider.dart';
import '../utils/logger.dart';

enum HomeContentType { main, uploadPhoto, confirmSelection, chooseSpace, chooseItems, measureRoom, uploadInspiration, confirmInspiration }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  HomeContentType _currentContent = HomeContentType.main;
  bool _isCreatingProject = false;

  void _showUploadPhoto() {
    setState(() {
      _currentContent = HomeContentType.uploadPhoto;
    });
  }

  void _showMainContent() {
    setState(() {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      projectProvider.clearProject();
      _currentContent = HomeContentType.main;
    });
  }

  void _showConfirmSelection() {
    setState(() {
      _currentContent = HomeContentType.confirmSelection;
    });
  }

  void _showChooseSpace() {
    setState(() {
      _currentContent = HomeContentType.chooseSpace;
    });
  }

  void _showChooseItems() {
    setState(() {
      _currentContent = HomeContentType.chooseItems;
    });
  }

  void _showMeasureRoom() {
    setState(() {
      _currentContent = HomeContentType.measureRoom;
    });
  }

  void _showUploadInspiration() {
    setState(() {
      _currentContent = HomeContentType.uploadInspiration;
    });
  }

  void _showConfirmInspiration() {
    setState(() {
      _currentContent = HomeContentType.confirmInspiration;
    });
  }

  Future<void> _createProjectAndNavigateToCamera() async {
    if (_isCreatingProject) return;

    setState(() {
      _isCreatingProject = true;
    });

    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      final success = await projectProvider.createProject(context);
      
      if (success && mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => TakePictureScreen(
              onBack: () {
                Navigator.pop(context);
              },
              onConfirmSelection: () {
                Navigator.pop(context);
                _showConfirmSelection();
              },
            ),
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to create project: ${projectProvider.errorMessage ?? 'Unknown error'}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        AppLogger.error('Error creating project: $e');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCreatingProject = false;
        });
      }
    }
  }

  Future<void> _createProjectAndShowUpload() async {
    if (_isCreatingProject) return;

    setState(() {
      _isCreatingProject = true;
    });

    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      final success = await projectProvider.createProject(context);
      
      if (success && mounted) {
        _showUploadPhoto();
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to create project: ${projectProvider.errorMessage ?? 'Unknown error'}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        AppLogger.error('Error creating project: $e');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCreatingProject = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: _currentContent == HomeContentType.uploadPhoto 
          ? UploadPhotoContent(
              onBack: _showMainContent,
              onConfirmSelection: _showConfirmSelection,
            )
          : _currentContent == HomeContentType.confirmSelection
            ? ConfirmSelectionContent(
                onBack: _showUploadPhoto,
                onSuccess: _showChooseSpace,
              )
            : _currentContent == HomeContentType.chooseSpace
              ? ChooseSpaceContent(
                  onBack: _showConfirmSelection,
                  onContinue: _showChooseItems,
                )
              : _currentContent == HomeContentType.chooseItems
                ? ChooseItemsContent(
                    onBack: _showChooseSpace,
                    onContinue: _showMeasureRoom,
                  )
                : _currentContent == HomeContentType.measureRoom
                ? MeasureRoomScreen(
                  onBack: _showChooseItems,
                  onContinue: _showUploadInspiration,
                )
                : _currentContent == HomeContentType.uploadInspiration
                  ? UploadInspirationContent(
                      onBack: _showMeasureRoom,
                      onConfirmSelection: _showConfirmInspiration,
                    ) : _currentContent == HomeContentType.confirmInspiration
                    ? ConfirmInspirationContent(
                        onBack: _showUploadInspiration,
                        onSuccess: _showMainContent,
                      )
                : _buildMainContent(),
      ),
    );
  }

  Widget _buildMainContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
              // Redesign Section
              Text(
                'Redesign.',
                style: AppTheme.sectionTitleStyle),
              const SizedBox(height: 24),
              
              // Photo Action Buttons - 2 Column Grid
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 0.65, // Reduced to give more height for content
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  PhotoActionWidget(
                    imagePath: 'assets/images/home/take_photo.png', // Using existing logo as placeholder
                    scale: 1.7,
                    buttonText: 'take photo',
                    onPressed: _isCreatingProject ? () {} : _createProjectAndNavigateToCamera,
                  ),
                  PhotoActionWidget(
                    mirror: true,
                    scale: 1.8,
                    imagePath: 'assets/images/home/upload_photo.png', // Using existing logo as placeholder
                    buttonText: 'upload picture',
                    onPressed: _isCreatingProject ? () {} : _createProjectAndShowUpload,
                  ),
                ],
              ),
              
              const SizedBox(height: 40),
              
              // Marketplace Section
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Marketplace.',
                    style: AppTheme.sectionTitleStyle,
                  ),
                  TextButton(
                    onPressed: () {
                      AppLogger.info('View Products pressed');
                      // TODO: Navigate to full marketplace
                    },
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'View Products',
                          style: TextStyle(
                            fontFamily: AppTheme.secondaryFont,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppTheme.bodyTextColor,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          IconsaxPlusLinear.arrow_right,
                          size: 16,
                          color: AppTheme.bodyTextColor,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // Marketplace Items - 2 Column Grid
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 0.8, // Adjust this to control height/width ratio
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  MarketplaceItemWidget(
                    imagePath: 'assets/images/extras/poster.jpg',
                    providerIconPath: 'assets/logo/amazon.png',
                    title: 'poster',
                    subtitle: '\$7',
                    comingSoon: true,
                    onTap: () {
                      AppLogger.info('Wayfair item tapped');
                    },
                  ),
                  MarketplaceItemWidget(
                    imagePath: 'assets/images/extras/vase.png', // Using existing logo as placeholder for actual item
                    providerIconPath: 'assets/logo/ikea.png', // Provider icon overlay
                    title: 'vase',
                    subtitle: '\$5',
                    comingSoon: true,
                    onTap: () {
                      AppLogger.info('Amazon item tapped');
                    },
                  ),
                  
                ],
              ),
              
              const SizedBox(height: 20),
            ],
        ),
      );
    }
}
