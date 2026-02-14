import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/project_provider.dart';
import '../utils/logger.dart';
import '../widgets/animated_border_card.dart';
import 'create_flow_screen.dart';

/// Home tab - redesigned with action cards and marketplace grid.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isCreatingProject = false;
  int _selectedActionCard = -1; // -1 = no pre-selection

  Future<void> _startRedesignFlow({bool isCamera = false}) async {
    if (_isCreatingProject) return;

    setState(() => _isCreatingProject = true);

    try {
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      final created = await projectProvider.createProject(context);

      if (!mounted) return;

      if (!created) {
        final message =
            projectProvider.errorMessage ??
            'Failed to create project. Please try again.';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppTheme.errorColor,
          ),
        );
        return;
      }

      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CreateFlowScreen(isCamera: isCamera),
          fullscreenDialog: true,
        ),
      );
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
    } finally {
      if (mounted) {
        setState(() => _isCreatingProject = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with logo and settings
              _buildHeader(),

              const SizedBox(height: 24),

              // Redesign section
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  'Redesign.',
                  style: AppTheme.dmSans(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Action cards row
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Expanded(
                      child: _buildActionCard(
                        index: 0,
                        icon: Icons.image_outlined,
                        title: 'Take a Photo',
                        subtitle: 'Capture your space',
                        isSelected: _selectedActionCard == 0,
                        onTap: () {
                          setState(() => _selectedActionCard = 0);
                          _startRedesignFlow(isCamera: true);
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildActionCard(
                        index: 1,
                        icon: Icons.camera_alt_outlined,
                        title: 'Upload Picture',
                        subtitle: 'From your gallery',
                        isSelected: _selectedActionCard == 1,
                        onTap: () {
                          setState(() => _selectedActionCard = 1);
                          _startRedesignFlow(isCamera: false);
                        },
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // Marketplace section
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  'Marketplace.',
                  style: AppTheme.dmSans(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Marketplace grid - 2 items only for no-scroll layout
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Expanded(
                      child: _buildMarketplaceCard(
                        imagePath: 'assets/images/extras/poster.jpg',
                        title: 'Art Poster',
                        description: 'Wall decor',
                        price: '\$29.99',
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildMarketplaceCard(
                        imagePath: 'assets/images/extras/vase.png',
                        title: 'Ceramic Vase',
                        description: 'Home accent',
                        price: '\$45.00',
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 120), // Bottom padding for nav bar
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Spaces. logo
          Image.asset('assets/logo/logo.png', height: 32),
          // Settings icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.dividerColor, width: 1),
            ),
            child: IconButton(
              icon: const Icon(
                Icons.settings_outlined,
                color: AppTheme.textPrimary,
                size: 22,
              ),
              onPressed: () {
                AppLogger.info('Settings pressed');
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionCard({
    required int index,
    required IconData icon,
    required String title,
    required String subtitle,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return AnimatedBorderCard(
      isSelected: isSelected,
      onTap: _isCreatingProject ? null : onTap,
      showCheckmark: false,
      animateOnce: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: isSelected
                  ? AppTheme.primaryColor.withValues(alpha: 0.1)
                  : AppTheme.scaffoldBackground,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              icon,
              color: isSelected
                  ? AppTheme.primaryColor
                  : AppTheme.textSecondary,
              size: 24,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: AppTheme.dmSans(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTheme.dmSans(
              fontSize: 13,
              fontWeight: FontWeight.w400,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketplaceCard({
    required String imagePath,
    required String title,
    required String description,
    required String price,
  }) {
    return SizedBox(
      height: 220,
      child: Stack(
        children: [
          // Main card content
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.dividerColor, width: 1),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Image section
                Expanded(
                  flex: 3,
                  child: Container(
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: AppTheme.scaffoldBackground,
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(15),
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(15),
                      ),
                      child: Image.asset(imagePath, fit: BoxFit.cover),
                    ),
                  ),
                ),
                // Text section
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: AppTheme.dmSans(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        description,
                        style: AppTheme.dmSans(
                          fontSize: 12,
                          fontWeight: FontWeight.w400,
                          color: AppTheme.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        price,
                        style: AppTheme.dmSans(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.primaryColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Coming soon overlay
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.lock_outline,
                        size: 14,
                        color: AppTheme.textSecondary,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Coming soon',
                        style: AppTheme.dmSans(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
