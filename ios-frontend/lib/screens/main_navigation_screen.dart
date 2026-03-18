import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/project_provider.dart';
import '../providers/subscription_provider.dart';

import '../utils/logger.dart';
import '../widgets/app_bottom_nav_bar.dart';
import 'home_screen.dart';
import 'saved_screen.dart';
import 'profile_screen.dart';
import 'create_flow_screen.dart';

/// Main navigation with 3 tabs + center CTA.
/// - Home
/// - Saved
/// - Profile
class MainNavigationScreen extends StatefulWidget {
  final int initialTab;
  const MainNavigationScreen({super.key, this.initialTab = 0});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  late int _selectedIndex = widget.initialTab;
  bool _isCreatingProject = false;

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  Future<void> _startRedesignFlow({required bool isCamera}) async {
    if (_isCreatingProject) return;

    // Freemium gate: check generation limit before creating project
    final subProvider = Provider.of<SubscriptionProvider>(context, listen: false);
    final allowed = await subProvider.ensureCanGenerate(source: isCamera ? 'nav_camera' : 'nav_gallery', context: context);
    if (!allowed || !mounted) return;

    setState(() => _isCreatingProject = true);

    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      final success = await projectProvider.createProject(context);

      if (!success ||
          projectProvider.currentProject?.id == null ||
          projectProvider.currentProject!.id.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                projectProvider.errorMessage ??
                    'Failed to create project. Check your connection.',
              ),
              backgroundColor: AppTheme.errorColor,
            ),
          );
        }
        return;
      }

      // No credit debit here — credits are charged at job start
      // (inspiration-redesign), not at project creation.

      if (mounted) {
        AppLogger.info(
          'Project created from center CTA: ${projectProvider.currentProject!.id}',
        );
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => CreateFlowScreen(isCamera: isCamera),
            fullscreenDialog: true,
          ),
        );
      }
    } catch (e) {
      AppLogger.error('Failed to create project from center CTA', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isCreatingProject = false);
      }
    }
  }

  void _onFabPressed() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Start a redesign',
                  style: AppTheme.dmSans(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Create a new room concept and shop matching products.',
                  style: AppTheme.dmSans(
                    fontSize: 14,
                    color: AppTheme.textSecondary,
                  ),
                ),
                const SizedBox(height: 16),
                ListTile(
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 2,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: AppTheme.dividerColor),
                  ),
                  leading: const Icon(
                    Icons.camera_alt_outlined,
                    color: AppTheme.primaryColor,
                  ),
                  title: Text(
                    'Take a Photo',
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    'Capture your current room instantly',
                    style: AppTheme.dmSans(fontSize: 13, color: AppTheme.textSecondary),
                  ),
                  onTap: () {
                    Navigator.pop(context);
                    _startRedesignFlow(isCamera: true);
                  },
                ),
                const SizedBox(height: 10),
                ListTile(
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 2,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: AppTheme.dividerColor),
                  ),
                  leading: const Icon(
                    Icons.image_outlined,
                    color: AppTheme.primaryColor,
                  ),
                  title: Text(
                    'Upload Picture',
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    'Use a photo from your gallery',
                    style: AppTheme.dmSans(fontSize: 13, color: AppTheme.textSecondary),
                  ),
                  onTap: () {
                    Navigator.pop(context);
                    _startRedesignFlow(isCamera: false);
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _getCurrentScreen() {
    switch (_selectedIndex) {
      case 0:
        return const HomeScreen();
      case 1:
        return const SavedScreen();
      case 2:
        return const ProfileScreen();
      default:
        return const HomeScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: _getCurrentScreen(),
      extendBody: true,
      bottomNavigationBar: AppBottomNavBar(
        selectedIndex: _selectedIndex,
        onItemTapped: _onItemTapped,
        onFabPressed: _onFabPressed,
      ),
    );
  }
}
