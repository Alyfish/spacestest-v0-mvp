import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';
import 'app_card.dart';

class MarketplaceItemWidget extends StatelessWidget {
  final String imagePath;
  final String title;
  final String subtitle;
  final String? providerIconPath;
  final bool comingSoon;
  final VoidCallback? onTap;

  const MarketplaceItemWidget({
    super.key,
    required this.imagePath,
    required this.title,
    required this.subtitle,
    this.providerIconPath,
    this.comingSoon = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: comingSoon ? null : onTap,
      padding: EdgeInsets.zero,
      showBorder: !comingSoon, // Hide border if coming soon (overlay handles visuals)
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Main Content
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Image Section
              Expanded(
                flex: 4,
                child: Stack(
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.grayColor.withOpacity(0.05),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                      ),
                      child: Image.asset(
                        imagePath,
                        fit: BoxFit.contain,
                      ),
                    ),
                    if (providerIconPath != null)
                      Positioned(
                        top: 8,
                        left: 8, // Moved to top-left as per plan "Store badge smaller, top-left"
                        child: Container(
                          width: 24,
                          height: 24,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                blurRadius: 4,
                              ),
                            ],
                          ),
                          padding: const EdgeInsets.all(4),
                          child: Image.asset(providerIconPath!),
                        ),
                      ),
                  ],
                ),
              ),
              
              // Text Section
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontFamily: AppTheme.secondaryFont,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.bodyTextColor,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          fontFamily: AppTheme.secondaryFont,
                          fontSize: 14,
                          color: AppTheme.grayColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),

          // Coming Soon Overlay
          if (comingSoon)
            Container(
              decoration: BoxDecoration(
                color: AppTheme.grayColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.9),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        IconsaxPlusLinear.lock,
                        size: 16,
                        color: AppTheme.grayColor,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Coming soon',
                        style: const TextStyle(
                          fontFamily: AppTheme.secondaryFont,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.grayColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
