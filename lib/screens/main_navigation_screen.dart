import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'discover_screen.dart';
import 'cart_screen.dart';
import 'saved_screen.dart';
import 'profile_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({Key? key}) : super(key: key);

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;

  final List<Widget> _screens = [
    const HomeScreen(),
    const DiscoverScreen(),
    const CartScreen(),
    const SavedScreen(),
    const ProfileScreen(),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

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
            Image.asset(
              'assets/logo/logo.png',
              height: 100,
              width: 100,
            ),
          ],
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(
            height: 1,
            color: Colors.grey.withValues(alpha: 0.2),
          ),
        ),
      ),
      body: _screens[_selectedIndex],
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: AppTheme.backgroundColor,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildNavItem(
                  index: 0,
                  icon: IconsaxPlusLinear.home_2,
                  selectedIcon: IconsaxPlusBold.home_2,
                  label: 'Home',
                ),
                _buildNavItem(
                  index: 1,
                  icon: IconsaxPlusLinear.search_normal,
                  selectedIcon: IconsaxPlusBold.search_normal,
                  label: 'Discover',
                ),
                _buildNavItem(
                  index: 2,
                  icon: IconsaxPlusLinear.bag,
                  selectedIcon: IconsaxPlusBold.bag,
                  label: '',
                  isSpecial: true, // This will be the circular cart icon
                ),
                _buildNavItem(
                  index: 3,
                  icon: IconsaxPlusLinear.bookmark,
                  selectedIcon: IconsaxPlusBold.bookmark,
                  label: 'Saved',
                ),
                _buildNavItem(
                  index: 4,
                  icon: IconsaxPlusLinear.profile,
                  selectedIcon: IconsaxPlusBold.profile,
                  label: 'Profile',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem({
    required int index,
    required IconData icon,
    required IconData selectedIcon,
    required String label,
    bool isSpecial = false,
  }) {
    final isSelected = _selectedIndex == index;
    
    if (isSpecial) {
      // Special circular cart button
      return GestureDetector(
        onTap: () => _onItemTapped(index),
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isSelected ? AppTheme.primaryColor : AppTheme.grayColor,
          ),
          child: Icon(
            isSelected ? selectedIcon : icon,
            color: AppTheme.darkGrayColor,
            size: 30,
          ),
        ),
      );
    }

    // Regular nav items
    return GestureDetector(
      onTap: () => _onItemTapped(index),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isSelected ? selectedIcon : icon,
              color: isSelected ? AppTheme.primaryColor : AppTheme.grayColor,
              size: 24,
            ),
            if (label.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontFamily: AppTheme.secondaryFont,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: isSelected ? AppTheme.primaryColor : AppTheme.grayColor,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
