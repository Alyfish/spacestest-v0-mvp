import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

class SavedScreen extends StatelessWidget {
  const SavedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title
              Text(
                'Saved.',
                style: AppTheme.sectionTitleStyle,),
              const SizedBox(height: 24),
              
              // Content placeholder
              SizedBox(
                height: MediaQuery.of(context).size.height - 200,
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        IconsaxPlusLinear.heart,
                        size: 80,
                        color: AppTheme.grayColor,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No saved items',
                        style: TextStyle(
                          fontFamily: AppTheme.primaryFont,
                          fontSize: 24,
                          color: AppTheme.grayColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Save your favorite designs here',
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
