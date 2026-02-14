import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/project_provider.dart';
import '../providers/user_provider.dart';

// Import all screens
import 'home_screen.dart';
import 'choose_space_screen.dart';
import 'choose_items_screen.dart';
import 'choose_approach_screen.dart';
import 'preferred_stores_screen.dart';
import 'measure_room_screen.dart';
import 'upload_photo_screen.dart';
import 'upload_inspiration_screen.dart';
import 'confirm_selection_screen.dart';
import 'confirm_inspiration_screen.dart';
import 'analyzing_screen.dart';
import 'discover_screen.dart';
import 'cart_screen.dart';
import 'saved_screen.dart';
import 'profile_screen.dart';

/// Demo navigator screen to preview all screens in the app
class DemoNavigatorScreen extends StatefulWidget {
  const DemoNavigatorScreen({super.key});

  @override
  State<DemoNavigatorScreen> createState() => _DemoNavigatorScreenState();
}

class _DemoNavigatorScreenState extends State<DemoNavigatorScreen> {
  @override
  void initState() {
    super.initState();
    // Ensure we have a demo project
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      if (projectProvider.currentProject == null) {
        projectProvider.createProject(context);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundColor,
        elevation: 0,
        title: const Text(
          'Demo Navigator',
          style: TextStyle(
            fontFamily: AppTheme.primaryFont,
            fontSize: 24,
            color: AppTheme.bodyTextColor,
          ),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppTheme.bodyTextColor),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Main Flow Screens
            _buildSectionTitle('Main User Flow'),
            _buildScreenTile('1. Home Screen', () => _navigateTo(context, const HomeScreen())),
            _buildScreenTile('2. Upload Photo', () => _navigateTo(context, UploadPhotoContent(onBack: () => Navigator.pop(context), onConfirmSelection: () => Navigator.pop(context)))),
            _buildScreenTile('3. Confirm Selection', () => _navigateTo(context, ConfirmSelectionContent(onBack: () => Navigator.pop(context), onSuccess: () => Navigator.pop(context)))),
            _buildScreenTile('4. Choose Space', () => _navigateTo(context, ChooseSpaceContent(onBack: () => Navigator.pop(context), onContinue: () => Navigator.pop(context)))),
            _buildScreenTile('5. Choose Items (Markers)', () => _navigateTo(context, ChooseItemsScreen(onBack: () => Navigator.pop(context), onContinue: () => Navigator.pop(context)))),
            _buildScreenTile('6. Measure Room', () => _navigateTo(context, MeasureRoomScreen(onBack: () => Navigator.pop(context), onContinue: () => Navigator.pop(context)))),
            _buildScreenTile('7. Upload Inspiration', () => _navigateTo(context, UploadInspirationContent(onBack: () => Navigator.pop(context), onConfirmSelection: () => Navigator.pop(context), onSkipToApproach: () => Navigator.pop(context)))),
            _buildScreenTile('8. Confirm Inspiration', () => _navigateTo(context, ConfirmInspirationContent(onBack: () => Navigator.pop(context), onSuccess: () => Navigator.pop(context)))),
            _buildScreenTile('9. Choose Approach', () => _navigateTo(context, ChooseApproachContent(onBack: () => Navigator.pop(context), onContinue: () => Navigator.pop(context)))),
            _buildScreenTile('10. Preferred Stores', () => _navigateTo(context, PreferredStoresContent(onBack: () => Navigator.pop(context), onContinue: () => Navigator.pop(context)))),
            _buildScreenTile('11. Analyzing', () => _navigateTo(context, AnalyzingScreen(onBack: () => Navigator.pop(context), onComplete: () => Navigator.pop(context)))),
            
            const SizedBox(height: 24),
            
            // Tab Navigation Screens
            _buildSectionTitle('Tab Navigation Screens'),
            _buildScreenTile('Discover', () => _navigateTo(context, const DiscoverScreen())),
            _buildScreenTile('Cart', () => _navigateTo(context, const CartScreen())),
            _buildScreenTile('Saved', () => _navigateTo(context, const SavedScreen())),
            _buildScreenTile('Profile', () => _navigateTo(context, const ProfileScreen())),
            
            const SizedBox(height: 24),
            
            // Status info
            _buildSectionTitle('App Status'),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.grayColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '⚠️ Note: This app is a work in progress.',
                    style: TextStyle(
                      fontFamily: AppTheme.secondaryFont,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.bodyTextColor,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    '• Discover, Cart, Saved are placeholder screens\n'
                    '• Results/Recommendations screen not yet implemented\n'
                    '• AR Measurement is commented out\n'
                    '• Demo mode bypasses all API calls',
                    style: TextStyle(
                      fontFamily: AppTheme.secondaryFont,
                      fontSize: 12,
                      color: AppTheme.grayColor,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Text(
        title,
        style: const TextStyle(
          fontFamily: AppTheme.primaryFont,
          fontSize: 20,
          fontWeight: FontWeight.bold,
          color: AppTheme.bodyTextColor,
        ),
      ),
    );
  }

  Widget _buildScreenTile(String name, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            border: Border.all(color: AppTheme.grayColor.withValues(alpha: 0.3)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  name,
                  style: const TextStyle(
                    fontFamily: AppTheme.secondaryFont,
                    fontSize: 16,
                    color: AppTheme.bodyTextColor,
                  ),
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16, color: AppTheme.grayColor),
            ],
          ),
        ),
      ),
    );
  }

  void _navigateTo(BuildContext context, Widget screen) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => Scaffold(
        backgroundColor: AppTheme.backgroundColor,
        body: SafeArea(child: screen),
      )),
    );
  }
}
