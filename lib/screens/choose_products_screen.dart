import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../models/shop_product.dart';
import '../providers/cart_provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/filters_bottom_sheet.dart';
import '../widgets/shop_product_card.dart';
import 'cart_screen.dart';
import 'main_navigation_screen.dart';

/// Choose Products Screen - Shows product grid for a selected hotspot
class ChooseProductsScreen extends StatefulWidget {
  final ProductHotspot hotspot;
  final VoidCallback? onBack;

  const ChooseProductsScreen({
    super.key,
    required this.hotspot,
    this.onBack,
  });

  @override
  State<ChooseProductsScreen> createState() => _ChooseProductsScreenState();
}

class _ChooseProductsScreenState extends State<ChooseProductsScreen> {
  ProductFilters _currentFilters = ProductFilters.empty;

  // Sample products for demo - in real app, fetch from API based on hotspot
  List<ShopProduct> get _products {
    // Generate sample products based on item type
    final itemType = widget.hotspot.itemType.toLowerCase();
    return [
      ShopProduct(
        id: '${itemType}_1',
        name: _capitalizeFirst(itemType),
        description: 'Comfort ${_capitalizeFirst(itemType)}',
        price: 280.40,
        retailerName: 'Walmart',
        imageUrl: '',
      ),
      ShopProduct(
        id: '${itemType}_2',
        name: _capitalizeFirst(itemType),
        description: 'Comfort ${_capitalizeFirst(itemType)}',
        price: 280.40,
        retailerName: 'Walmart',
        imageUrl: '',
      ),
      ShopProduct(
        id: '${itemType}_3',
        name: _capitalizeFirst(itemType),
        description: 'Comfort ${_capitalizeFirst(itemType)}',
        price: 350.00,
        retailerName: 'Amazon',
        imageUrl: '',
      ),
      ShopProduct(
        id: '${itemType}_4',
        name: _capitalizeFirst(itemType),
        description: 'Comfort ${_capitalizeFirst(itemType)}',
        price: 420.99,
        retailerName: 'IKEA',
        imageUrl: '',
      ),
      ShopProduct(
        id: '${itemType}_5',
        name: _capitalizeFirst(itemType),
        description: 'Premium ${_capitalizeFirst(itemType)}',
        price: 599.00,
        retailerName: 'Ashley',
        imageUrl: '',
      ),
      ShopProduct(
        id: '${itemType}_6',
        name: _capitalizeFirst(itemType),
        description: 'Deluxe ${_capitalizeFirst(itemType)}',
        price: 750.00,
        retailerName: 'Wayfair',
        imageUrl: '',
      ),
    ];
  }

  List<ShopProduct> get _filteredProducts {
    var products = _products;

    // Apply price filter
    if (_currentFilters.minPrice != null) {
      products = products.where((p) => p.price >= _currentFilters.minPrice!).toList();
    }
    if (_currentFilters.maxPrice != null) {
      products = products.where((p) => p.price <= _currentFilters.maxPrice!).toList();
    }

    // Apply marketplace filter
    if (_currentFilters.selectedMarketplaces.isNotEmpty) {
      products = products
          .where((p) => _currentFilters.selectedMarketplaces.contains(p.retailerName))
          .toList();
    }

    return products;
  }

  String _capitalizeFirst(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }

  void _toggleProduct(ShopProduct product) {
    final cartProvider = context.read<CartProvider>();
    final isInCart = cartProvider.isInCart(product.id);

    cartProvider.toggleCartItem(product);

    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          isInCart ? 'Removed from cart' : 'Added to cart',
          style: AppTheme.dmSans(fontSize: 14, color: Colors.white),
        ),
        backgroundColor: AppTheme.textPrimary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Future<void> _openFilters() async {
    final result = await showFiltersBottomSheet(
      context,
      currentFilters: _currentFilters,
    );
    if (result != null) {
      setState(() => _currentFilters = result);
    }
  }

  void _handleNavTap(int index) {
    if (index == 2) return;
    if (index == 1) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.lock_outline, color: Colors.white, size: 18),
              const SizedBox(width: 12),
              Text('Coming soon', style: AppTheme.dmSans(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.white)),
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
          SnackBar(content: Text('Failed to start: ${e.toString()}'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
  }

  void _goToCart() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const CartScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final products = _filteredProducts;

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Header with back button and cart
            _buildHeader(),

            // Filters button
            _buildFiltersButton(),

            // Product grid
            Expanded(
              child: products.isEmpty
                  ? _buildEmptyState()
                  : Consumer<CartProvider>(
                      builder: (context, cartProvider, _) {
                        return GridView.builder(
                          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 12,
                            mainAxisSpacing: 12,
                            childAspectRatio: 0.65,
                          ),
                          itemCount: products.length,
                          itemBuilder: (context, index) {
                            final product = products[index];
                            final isSelected = cartProvider.isInCart(product.id);
                            return ShopProductCard(
                              product: product,
                              isSelected: isSelected,
                              onTap: () => _toggleProduct(product),
                            );
                          },
                        );
                      },
                    ),
            ),

            // Bottom CTA bar
            _buildBottomCTABar(),
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

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 20, 0),
      child: Row(
        children: [
          // Back button
          IconButton(
            icon: const Icon(
              Icons.arrow_back_ios_new_rounded,
              size: 20,
              color: AppTheme.textPrimary,
            ),
            onPressed: widget.onBack ?? () => Navigator.pop(context),
          ),
          const SizedBox(width: 4),
          // Title
          Expanded(
            child: Text(
              'Products for ${widget.hotspot.label}',
              style: AppTheme.dmSans(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppTheme.textPrimary,
              ),
            ),
          ),
          // Cart icon with badge
          Consumer<CartProvider>(
            builder: (context, cartProvider, _) {
              return GestureDetector(
                onTap: _goToCart,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        IconsaxPlusLinear.shopping_cart,
                        size: 16,
                        color: Colors.white,
                      ),
                      if (cartProvider.itemCount > 0) ...[
                        const SizedBox(width: 4),
                        Text(
                          '${cartProvider.itemCount}',
                          style: AppTheme.dmSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildFiltersButton() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: OutlinedButton(
        onPressed: _openFilters,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          side: BorderSide(
            color: _currentFilters.hasFilters
                ? AppTheme.primaryColor
                : AppTheme.dividerColor,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              IconsaxPlusLinear.filter,
              size: 18,
              color: _currentFilters.hasFilters
                  ? AppTheme.primaryColor
                  : AppTheme.textPrimary,
            ),
            const SizedBox(width: 8),
            Text(
              _currentFilters.hasFilters ? 'Filters Applied' : 'Filters',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: _currentFilters.hasFilters
                    ? AppTheme.primaryColor
                    : AppTheme.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            IconsaxPlusLinear.box,
            size: 64,
            color: AppTheme.textTertiary,
          ),
          const SizedBox(height: 16),
          Text(
            'No products found',
            style: AppTheme.dmSans(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Try adjusting your filters',
            style: AppTheme.dmSans(
              fontSize: 14,
              color: AppTheme.textSecondary,
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton(
            onPressed: () {
              setState(() => _currentFilters = ProductFilters.empty);
            },
            child: Text(
              'Clear Filters',
              style: AppTheme.dmSans(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppTheme.primaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomCTABar() {
    return Consumer<CartProvider>(
      builder: (context, cartProvider, _) {
        return Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
          decoration: BoxDecoration(
            color: AppTheme.surfaceColor,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 12,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: Row(
            children: [
              // Back button
              Expanded(
                child: SizedBox(
                  height: 56,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.textPrimary,
                      side: const BorderSide(color: AppTheme.dividerColor, width: 1.5),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    onPressed: widget.onBack ?? () => Navigator.pop(context),
                    child: Text(
                      'Back',
                      style: AppTheme.dmSans(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(width: 12),

              // Go to Cart button
              Expanded(
                child: SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    onPressed: _goToCart,
                    child: Text(
                      'Go to Cart',
                      style: AppTheme.dmSans(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
