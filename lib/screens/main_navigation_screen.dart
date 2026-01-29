import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/project_provider.dart';
import '../utils/logger.dart';
import '../widgets/app_bottom_nav_bar.dart';
import 'home_screen.dart';
import 'saved_screen.dart';
import 'profile_screen.dart';
import 'create_flow_screen.dart';

/// Main navigation with 5 items including center FAB.
/// - Home (functional)
/// - Discover (coming soon)
/// - Center FAB (upload photo)
/// - Saved (functional)
/// - Profile (functional)
class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;

  void _onItemTapped(int index) {
    // Index 2 is the FAB position - skip it in tab logic
    if (index == 2) return;

    // Check for "coming soon" tabs (only Discover now)
    if (index == 1) {
      _showComingSoonSnackbar();
      return;
    }

    setState(() {
      _selectedIndex = index;
    });
  }

  void _showComingSoonSnackbar() {
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              Icons.lock_outline,
              color: Colors.white,
              size: 18,
            ),
            const SizedBox(width: 12),
            Text(
              'Coming soon',
              style: AppTheme.dmSans(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: Colors.white,
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.textSecondary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Future<void> _onFabPressed() async {
    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      await projectProvider.createProject(context);

      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => const CreateFlowScreen(),
            fullscreenDialog: true,
          ),
        );
      }
    } catch (e) {
      AppLogger.error('Failed to create project', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Widget _getCurrentScreen() {
    switch (_selectedIndex) {
      case 0:
        return const HomeScreen();
      case 3:
        return const SavedScreen();
      case 4:
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
