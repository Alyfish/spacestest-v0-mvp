import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';
import '../widgets/app_text_field.dart';

class DiscoverScreen extends StatelessWidget {
  const DiscoverScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock Data
    final inspirationImages = List.generate(10, (index) => 'assets/images/onboarding/${(index % 3) + 1}.png');

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Column(
          children: [
             Padding(
              padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Discover', style: AppTheme.headerStyle(fontSize: 20)),
                  const SizedBox(height: 16),
                  AppTextField(
                    controller: TextEditingController(),
                    hint: 'Search styles, furniture, ideas...',
                    prefixIcon: const Icon(IconsaxPlusLinear.search_normal_1, color: AppTheme.grayColor),
                  ),
                ],
              ),
            ),
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 0.7, // Portrait Aspect Ratio
                ),
                itemCount: inspirationImages.length,
                itemBuilder: (context, index) {
                  return Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        )
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.asset(
                        inspirationImages[index],
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          color: Colors.grey[200],
                          child: const Center(child: Icon(IconsaxPlusLinear.image, color: Colors.grey)),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            BottomNavigationBar(
              type: BottomNavigationBarType.fixed,
              backgroundColor: AppTheme.backgroundColor,
              selectedItemColor: AppTheme.primaryColor,
              unselectedItemColor: AppTheme.grayColor,
              showSelectedLabels: false,
              showUnselectedLabels: false,
              currentIndex: 1, // Discover Tab
              onTap: (_) {}, 
              items: const [
                BottomNavigationBarItem(icon: Icon(IconsaxPlusLinear.home), activeIcon: Icon(IconsaxPlusBold.home), label: 'Home'),
                BottomNavigationBarItem(icon: Icon(IconsaxPlusLinear.discover), activeIcon: Icon(IconsaxPlusBold.discover), label: 'Discover'),
                BottomNavigationBarItem(icon: Icon(IconsaxPlusLinear.bag_2), activeIcon: Icon(IconsaxPlusBold.bag_2), label: 'Cart'),
                BottomNavigationBarItem(icon: Icon(IconsaxPlusLinear.bookmark), activeIcon: Icon(IconsaxPlusBold.bookmark), label: 'Saved'),
                BottomNavigationBarItem(icon: Icon(IconsaxPlusLinear.profile_circle), activeIcon: Icon(IconsaxPlusBold.profile_circle), label: 'Profile'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
