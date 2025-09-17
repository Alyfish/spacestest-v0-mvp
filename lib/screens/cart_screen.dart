import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

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
                'Cart.',
                style: AppTheme.sectionTitleStyle,
              ),
              const SizedBox(height: 24),
              
              // Content placeholder
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        IconsaxPlusLinear.shopping_cart,
                        size: 80,
                        color: AppTheme.grayColor,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Your cart is empty',
                        style: TextStyle(
                          fontFamily: AppTheme.primaryFont,
                          fontSize: 24,
                          color: AppTheme.grayColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Add items from the marketplace',
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
