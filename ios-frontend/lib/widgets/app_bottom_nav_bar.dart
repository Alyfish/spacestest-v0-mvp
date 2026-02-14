import 'package:flutter/material.dart';
import '../theme.dart';

/// Reusable bottom navigation with center quick-action CTA.
/// - Home (index 0)
/// - Discover (index 1)
/// - Plus CTA (index 2)
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
        border: const Border(
          top: BorderSide(
            color: AppTheme.dividerColor,
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 74,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.topCenter,
            children: [
              Row(
                children: [
                  Expanded(
                    child: _buildNavItem(
                      context: context,
                      index: 0,
                      icon: Icons.home_outlined,
                      selectedIcon: Icons.home_rounded,
                      label: 'Home',
                    ),
                  ),
                  Expanded(
                    child: _buildNavItem(
                      context: context,
                      index: 1,
                      icon: Icons.explore_outlined,
                      selectedIcon: Icons.explore,
                      label: 'Discover',
                    ),
                  ),
                  const Expanded(child: SizedBox()),
                  Expanded(
                    child: _buildNavItem(
                      context: context,
                      index: 3,
                      icon: Icons.bookmark_outline,
                      selectedIcon: Icons.bookmark,
                      label: 'Saved',
                    ),
                  ),
                  Expanded(
                    child: _buildNavItem(
                      context: context,
                      index: 4,
                      icon: Icons.person_outline,
                      selectedIcon: Icons.person,
                      label: 'Profile',
                    ),
                  ),
                ],
              ),
              Positioned(
                top: -24,
                child: GestureDetector(
                  onTap: () {
                    if (onFabPressed != null) {
                      onFabPressed!();
                    } else {
                      onItemTapped(2);
                    }
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 160),
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 4),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.primaryColor.withValues(alpha: 0.30),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.add_rounded,
                      color: Colors.white,
                      size: 30,
                    ),
                  ),
                ),
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
  }) {
    final isSelected = selectedIndex == index;

    return InkWell(
      onTap: () => onItemTapped(index),
      splashColor: Colors.transparent,
      highlightColor: Colors.transparent,
      child: Center(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: isSelected
                ? AppTheme.primaryColor.withValues(alpha: 0.10)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isSelected ? selectedIcon : icon,
                color: isSelected ? AppTheme.primaryColor : AppTheme.textTertiary,
                size: 22,
              ),
              const SizedBox(height: 3),
              Text(
                label,
                style: AppTheme.dmSans(
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? AppTheme.primaryColor : AppTheme.textTertiary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
