import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';
import '../widgets/photo_action_widget.dart';
import '../widgets/marketplace_item_widget.dart';
import '../screens/take_picture_screen.dart';
import '../screens/upload_photo_screen.dart';
import '../screens/confirm_selection_screen.dart';

enum HomeContentType { main, uploadPhoto, confirmSelection }

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  HomeContentType _currentContent = HomeContentType.main;

  void _showUploadPhoto() {
    setState(() {
      _currentContent = HomeContentType.uploadPhoto;
    });
  }

  void _showMainContent() {
    setState(() {
      _currentContent = HomeContentType.main;
    });
  }

  void _showConfirmSelection() {
    setState(() {
      _currentContent = HomeContentType.confirmSelection;
    });
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
                style: const TextStyle(
                  fontFamily: AppTheme.primaryFont,
                  fontSize: 40,
                  fontWeight: FontWeight.normal,
                  color: AppTheme.primaryColor,
                ),
              ),
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
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const TakePictureScreen(),
                        ),
                      );
                    },
                  ),
                  PhotoActionWidget(
                    mirror: true,
                    scale: 1.8,
                    imagePath: 'assets/images/home/upload_photo.png', // Using existing logo as placeholder
                    buttonText: 'upload picture',
                    onPressed: () {
                      _showUploadPhoto();
                    },
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
                    style: const TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 32,
                      fontWeight: FontWeight.normal,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                  TextButton(
                    onPressed: () {
                      print('View Products pressed');
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
                      print('Wayfair item tapped');
                    },
                  ),
                  MarketplaceItemWidget(
                    imagePath: 'assets/images/extras/vase.png', // Using existing logo as placeholder for actual item
                    providerIconPath: 'assets/logo/ikea.png', // Provider icon overlay
                    title: 'vase',
                    subtitle: '\$5',
                    comingSoon: true,
                    onTap: () {
                      print('Amazon item tapped');
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
