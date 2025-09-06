import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

class DiscoverScreen extends StatelessWidget {
  const DiscoverScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title
              Text(
                'Discover.',
                style: const TextStyle(
                  fontFamily: AppTheme.primaryFont,
                  fontSize: 32,
                  fontWeight: FontWeight.normal,
                  color: AppTheme.primaryColor,
                ),
              ),
              const SizedBox(height: 24),
              
              // Content placeholder
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        IconsaxPlusLinear.search_normal_1,
                        size: 80,
                        color: AppTheme.grayColor,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Coming Soon',
                        style: TextStyle(
                          fontFamily: AppTheme.primaryFont,
                          fontSize: 24,
                          color: AppTheme.grayColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Discover new design inspirations',
                        style: TextStyle(
                          fontFamily: AppTheme.secondaryFont,
                          fontSize: 16,
                          color: AppTheme.grayColor,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
