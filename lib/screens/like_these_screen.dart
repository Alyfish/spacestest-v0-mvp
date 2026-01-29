import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/bottom_cta_bar.dart';
import 'main_navigation_screen.dart';

/// Model for a product item to display in the selection grid
class ProductItem {
  final String id;
  final String name;
  final String retailerName;
  final String? retailerLogoPath;
  final String? imagePath;
  final String? imageUrl;

  const ProductItem({
    required this.id,
    required this.name,
    required this.retailerName,
    this.retailerLogoPath,
    this.imagePath,
    this.imageUrl,
  });
}

/// Screen for selecting items (vases, sofas, etc.) from a grid of products
class LikeTheseScreen extends StatefulWidget {
  final String itemType; // e.g., 'vase', 'sofa', 'chair'
  final String? actionId; // e.g., 'add_vase', 'change_sofa'

  const LikeTheseScreen({
    super.key,
    required this.itemType,
    this.actionId,
  });

  @override
  State<LikeTheseScreen> createState() => _LikeTheseScreenState();
}

class _LikeTheseScreenState extends State<LikeTheseScreen> {
  final Set<String> _selectedIds = {};
  final bool _isLoading = false;

  // Sample product data - in a real app, this would come from an API
  List<ProductItem> get _products {
    // Generate sample products based on item type
    switch (widget.itemType.toLowerCase()) {
      case 'vase':
        return const [
          ProductItem(
            id: 'vase_1',
            name: 'Ceramic Vase',
            retailerName: 'Walmart',
            imagePath: 'assets/images/products/vase_1.png',
          ),
          ProductItem(
            id: 'vase_2',
            name: 'Glass Vase',
            retailerName: 'Ashley',
            imagePath: 'assets/images/products/vase_2.png',
          ),
          ProductItem(
            id: 'vase_3',
            name: 'Modern Vase',
            retailerName: 'amazon',
            imagePath: 'assets/images/products/vase_3.png',
          ),
          ProductItem(
            id: 'vase_4',
            name: 'Minimalist Vase',
            retailerName: 'IKEA',
            imagePath: 'assets/images/products/vase_4.png',
          ),
        ];
      case 'sofa':
        return const [
          ProductItem(
            id: 'sofa_1',
            name: 'Sectional Sofa',
            retailerName: 'Walmart',
            imagePath: 'assets/images/products/sofa_1.png',
          ),
          ProductItem(
            id: 'sofa_2',
            name: 'Modern Couch',
            retailerName: 'Ashley',
            imagePath: 'assets/images/products/sofa_2.png',
          ),
          ProductItem(
            id: 'sofa_3',
            name: 'Leather Sofa',
            retailerName: 'amazon',
            imagePath: 'assets/images/products/sofa_3.png',
          ),
          ProductItem(
            id: 'sofa_4',
            name: 'Fabric Couch',
            retailerName: 'IKEA',
            imagePath: 'assets/images/products/sofa_4.png',
          ),
        ];
      default:
        return const [
          ProductItem(
            id: 'item_1',
            name: 'Product 1',
            retailerName: 'Walmart',
            imagePath: 'assets/images/products/item_1.png',
          ),
          ProductItem(
            id: 'item_2',
            name: 'Product 2',
            retailerName: 'Ashley',
            imagePath: 'assets/images/products/item_2.png',
          ),
          ProductItem(
            id: 'item_3',
            name: 'Product 3',
            retailerName: 'amazon',
            imagePath: 'assets/images/products/item_3.png',
          ),
          ProductItem(
            id: 'item_4',
            name: 'Product 4',
            retailerName: 'IKEA',
            imagePath: 'assets/images/products/item_4.png',
          ),
        ];
    }
  }

  void _toggleSelection(String id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
  }

  void _handleContinue() {
    if (_selectedIds.isEmpty) {
      Navigator.pop(context);
      return;
    }

    // Return selected items to the previous screen
    final selectedProducts = _products
        .where((p) => _selectedIds.contains(p.id))
        .map((p) => {'id': p.id, 'name': p.name, 'retailer': p.retailerName})
        .toList();

    Navigator.pop(context, {
      'actionId': widget.actionId,
      'itemType': widget.itemType,
      'selectedItems': selectedProducts,
    });
  }

  void _openSettings() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Settings coming soon')),
    );
  }

  void _handleNavTap(int index) {
    // Index 2 is the FAB position - skip it
    if (index == 2) return;

    // Check for "coming soon" tabs (only Discover now)
    if (index == 1) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.lock_outline, color: Colors.white, size: 18),
              const SizedBox(width: 12),
              Text(
                'Coming soon',
                style: AppTheme.dmSans(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.white,
                ),
              ),
            ],
          ),
          backgroundColor: AppTheme.textSecondary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(16),
          duration: const Duration(seconds: 2),
        ),
      );
      return;
    }

    // Navigate to main navigation screen with selected tab
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
      (route) => false,
    );
  }

  Future<void> _handleFabPressed() async {
    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      await projectProvider.createProject(context);
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
          (route) => false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with logo and settings
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Spaces. logo
                  Text(
                    'Spaces.',
                    style: AppTheme.dmSans(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  // Settings icon
                  GestureDetector(
                    onTap: _openSettings,
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceColor,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: AppTheme.dividerColor,
                          width: 1,
                        ),
                      ),
                      child: const Center(
                        child: Icon(
                          IconsaxPlusLinear.setting_2,
                          size: 22,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Title
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
              child: Text(
                'Like These?',
                style: AppTheme.dmSans(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Product grid
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppTheme.primaryColor,
                      ),
                    )
                  : GridView.builder(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        childAspectRatio: 0.75,
                      ),
                      itemCount: _products.length,
                      itemBuilder: (context, index) {
                        final product = _products[index];
                        final isSelected = _selectedIds.contains(product.id);
                        return _ProductCard(
                          product: product,
                          isSelected: isSelected,
                          onTap: () => _toggleSelection(product.id),
                        );
                      },
                    ),
            ),

            // Bottom CTA bar
            BottomCTABar(
              secondaryText: 'Back',
              onSecondaryPressed: () => Navigator.pop(context),
              primaryText: 'Continue',
              onPrimaryPressed: _handleContinue,
            ),
          ],
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        selectedIndex: 0,
        onItemTapped: _handleNavTap,
        onFabPressed: _handleFabPressed,
      ),
    );
  }
}

/// Product card widget for the selection grid
class _ProductCard extends StatelessWidget {
  final ProductItem product;
  final bool isSelected;
  final VoidCallback onTap;

  const _ProductCard({
    required this.product,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
            width: isSelected ? 2 : 1,
          ),
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
            // Product image with retailer logo
            Expanded(
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
                      child: product.imagePath != null
                          ? Image.asset(
                              product.imagePath!,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) {
                                return _buildPlaceholder();
                              },
                            )
                          : product.imageUrl != null
                              ? Image.network(
                                  product.imageUrl!,
                                  fit: BoxFit.cover,
                                  errorBuilder: (context, error, stackTrace) {
                                    return _buildPlaceholder();
                                  },
                                )
                              : _buildPlaceholder(),
                    ),
                  ),
                  // Retailer logo badge
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
                      child: Text(
                        product.retailerName,
                        style: AppTheme.dmSans(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                  ),
                  // Selection indicator
                  if (isSelected)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: AppTheme.primaryColor,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.check,
                          color: Colors.white,
                          size: 16,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Product name
            Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                product.name,
                style: AppTheme.dmSans(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textPrimary,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
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
