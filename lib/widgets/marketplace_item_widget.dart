import 'package:flutter/material.dart';
import '../theme.dart';

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
    return GestureDetector(
      onTap: comingSoon ? null : onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.primaryColor,
            width: 2,
          ),
          color: AppTheme.backgroundColor,
        ),
        child: Stack(
          children: [
            // Content
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Image with provider icon overlay
                Expanded(
                  flex: 3,
                  child: Stack(
                    children: [
                      // Main item image
                      Container(
                        width: double.infinity,
                        decoration: BoxDecoration(
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
                        ),
                        child: ClipRRect(
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
                          child: Container(
                            color: Colors.transparent,
                            child: Image.asset(
                              imagePath,
                              fit: BoxFit.contain, // Show full image without cropping
                              color: comingSoon ? AppTheme.grayColor.withValues(alpha: 0.5) : null,
                              colorBlendMode: comingSoon ? BlendMode.srcATop : null,
                            ),
                          ),
                        ),
                      ),
                      // Provider icon overlay
                      if (providerIconPath != null)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            constraints: const BoxConstraints(
                              maxWidth: 60,
                            ),
                            height: 23, // 10% of typical tile height (~230px)
                            decoration: BoxDecoration(
                              color: AppTheme.backgroundColor,
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.1),
                                  blurRadius: 4,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              child: Image.asset(
                                providerIconPath!,
                                fit: BoxFit.contain, // Show full logo without cropping
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                // Item name
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    title,
                    style: TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 30,
                      fontWeight: FontWeight.normal,
                      color: comingSoon ? AppTheme.grayColor : AppTheme.bodyTextColor,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
            // Coming Soon Overlay
            if (comingSoon)
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: AppTheme.backgroundColor.withValues(alpha: 0.9),
                ),
                child: const Center(
                  child: Text(
                    'coming soon...',
                    style: TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 30,
                      fontWeight: FontWeight.normal,
                      color: AppTheme.grayColor,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
