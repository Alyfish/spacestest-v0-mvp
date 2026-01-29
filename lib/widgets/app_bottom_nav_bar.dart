import 'package:flutter/material.dart';
import '../theme.dart';

/// Reusable bottom navigation bar widget with 5 items including center FAB.
/// - Home (index 0)
/// - Discover (index 1, coming soon)
/// - Center FAB (index 2, triggers onFabPressed)
/// - Saved (index 3)
/// - Profile (index 4)
class AppBottomNavBar extends StatelessWidget {
  final int selectedIndex;
  final Function(int) onItemTapped;
  final VoidCallback? onFabPressed;

  const AppBottomNavBar({
    super.key,
    required this.selectedIndex,
    required this.onItemTapped,
    this.onFabPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        child: SizedBox(
          height: 64,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              // Home
              _buildNavItem(
                context: context,
                index: 0,
                icon: Icons.home_outlined,
                selectedIcon: Icons.home_rounded,
                label: 'Home',
              ),
              // Discover (coming soon)
              _buildNavItem(
                context: context,
                index: 1,
                icon: Icons.explore_outlined,
                selectedIcon: Icons.explore,
                label: 'Discover',
                isComingSoon: true,
              ),
              // Center FAB
              _buildCenterFab(),
              // Saved
              _buildNavItem(
                context: context,
                index: 3,
                icon: Icons.bookmark_outline,
                selectedIcon: Icons.bookmark,
                label: 'Saved',
              ),
              // Profile
              _buildNavItem(
                context: context,
                index: 4,
                icon: Icons.person_outline,
                selectedIcon: Icons.person,
                label: 'Profile',
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem({
    required BuildContext context,
    required int index,
    required IconData icon,
    required IconData selectedIcon,
    required String label,
    bool isComingSoon = false,
  }) {
    final isSelected = selectedIndex == index && !isComingSoon;

    return GestureDetector(
      onTap: () => onItemTapped(index),
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 64,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isSelected ? selectedIcon : icon,
              color: isComingSoon
                  ? AppTheme.textTertiary.withValues(alpha: 0.5)
                  : (isSelected ? AppTheme.primaryColor : AppTheme.textTertiary),
              size: 24,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: AppTheme.dmSans(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                color: isComingSoon
                    ? AppTheme.textTertiary.withValues(alpha: 0.5)
                    : (isSelected ? AppTheme.primaryColor : AppTheme.textTertiary),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCenterFab() {
    return GestureDetector(
      onTap: onFabPressed,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppTheme.primaryColor,
              AppTheme.primaryColor.withValues(alpha: 0.85),
            ],
          ),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: AppTheme.primaryColor.withValues(alpha: 0.35),
              blurRadius: 12,
              offset: const Offset(0, 4),
              spreadRadius: 0,
            ),
          ],
        ),
        child: const Icon(
          Icons.add_rounded,
          color: Colors.white,
          size: 28,
        ),
      ),
    );
  }
}
