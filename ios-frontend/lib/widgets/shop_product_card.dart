import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../models/shop_product.dart';
import '../theme.dart';

/// Product card widget for the Choose Products screen
/// Shows retailer logo, product image, name, description, and price
class ShopProductCard extends StatelessWidget {
  final ShopProduct product;
  final VoidCallback onTap;

  const ShopProductCard({
    super.key,
    required this.product,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final hasDisplayPrice = product.displayPrice?.trim().isNotEmpty ?? false;
    final hasNumericPrice = product.price > 0;
    final priceLabel = hasDisplayPrice
        ? product.displayPrice!
        : hasNumericPrice
        ? '\$${product.price.toStringAsFixed(2)}'
        : 'Price unavailable';
    final priceColor = (hasDisplayPrice || hasNumericPrice)
        ? AppTheme.primaryColor
        : AppTheme.textSecondary;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.dividerColor, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Image section with retailer badge
            Expanded(
              flex: 3,
              child: Stack(
                children: [
                  // Product image
                  ClipRRect(
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(15),
                    ),
                    child: Container(
                      width: double.infinity,
                      color: AppTheme.scaffoldBackground,
                      child: product.imageUrl.isNotEmpty
                          ? Image.network(
                              product.imageUrl,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) {
                                return _buildPlaceholder();
                              },
                            )
                          : _buildPlaceholder(),
                    ),
                  ),
                  // Retailer logo badge (top-left)
                  Positioned(
                    top: 8,
                    left: 8,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(6),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.1),
                            blurRadius: 4,
                            offset: const Offset(0, 1),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (product.retailerLogoUrl != null) ...[
                            Image.network(
                              product.retailerLogoUrl!,
                              width: 16,
                              height: 16,
                              errorBuilder: (_, __, ___) =>
                                  const SizedBox.shrink(),
                            ),
                            const SizedBox(width: 4),
                          ],
                          Text(
                            product.retailerName,
                            style: AppTheme.dmSans(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Text section
            Expanded(
              flex: 2,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Product name
                    Text(
                      product.name,
                      style: AppTheme.dmSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    // Product description
                    Text(
                      product.description,
                      style: AppTheme.dmSans(
                        fontSize: 12,
                        fontWeight: FontWeight.w400,
                        color: AppTheme.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    // Price
                    Text(
                      priceLabel,
                      style: AppTheme.dmSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: priceColor,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Center(
      child: Icon(
        IconsaxPlusLinear.box,
        size: 40,
        color: AppTheme.textTertiary,
      ),
    );
  }
}
