import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../models/shop_product.dart';
import '../providers/cart_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
import 'main_navigation_screen.dart';

/// Cart Screen - Shows grouped cart items by retailer with checkout info
class CartScreen extends StatelessWidget {
  final VoidCallback? onBack;

  const CartScreen({super.key, this.onBack});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        bottom: false,
        child: Consumer<CartProvider>(
          builder: (context, cartProvider, _) {
            return Column(
              children: [
                // Header
                _buildHeader(context),

                // Content
                Expanded(
                  child: cartProvider.isEmpty
                      ? _buildEmptyState()
                      : SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 8),

                              // Title
                              Text(
                                'Choose Cart.',
                                style: AppTheme.dmSans(
                                  fontSize: 26,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textPrimary,
                                ),
                              ),

                              const SizedBox(height: 20),

                              // Retailer grouped items
                              ...cartProvider.retailers.map(
                                (retailer) => _buildRetailerCard(
                                  context,
                                  retailer,
                                  cartProvider.getRetailerItems(retailer),
                                ),
                              ),

                              const SizedBox(height: 24),

                              // Delivery Address
                              _buildSectionTitle('Delivery Address'),
                              const SizedBox(height: 12),
                              _buildDeliveryAddressCard(),

                              const SizedBox(height: 24),

                              // Payment Method
                              _buildSectionTitle('Payment Method'),
                              const SizedBox(height: 12),
                              _buildPaymentMethodCard(),

                              const SizedBox(height: 24),

                              // Order Info
                              _buildSectionTitle('Order Info'),
                              const SizedBox(height: 12),
                              _buildOrderInfoCard(cartProvider),

                              const SizedBox(height: 100),
                            ],
                          ),
                        ),
                ),
              ],
            );
          },
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        selectedIndex: 0,
        onItemTapped: (index) => _handleNavTap(context, index),
        onFabPressed: () => _handleFabPressed(context),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Spaces. logo
          Image.asset(
            'assets/logo/logo.png',
            height: 32,
          ),
          // Settings icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.dividerColor,
                width: 1,
              ),
            ),
            child: IconButton(
              icon: const Icon(
                Icons.settings_outlined,
                color: AppTheme.textPrimary,
                size: 22,
              ),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            IconsaxPlusLinear.shopping_cart,
            size: 80,
            color: AppTheme.textTertiary,
          ),
          const SizedBox(height: 16),
          Text(
            'Your cart is empty',
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Add items from the marketplace',
            style: AppTheme.dmSans(
              fontSize: 16,
              color: AppTheme.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildRetailerCard(
    BuildContext context,
    String retailerName,
    List<ShopProduct> items,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row: logo, item count, delete button
            Row(
              children: [
                // Retailer logo
                _buildRetailerLogo(retailerName),
                const SizedBox(width: 12),
                // Item count
                Expanded(
                  child: Text(
                    '${items.length} Items',
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
                // Delete button
                GestureDetector(
                  onTap: () {
                    context.read<CartProvider>().clearRetailerItems(retailerName);
                  },
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppTheme.scaffoldBackground,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      IconsaxPlusLinear.trash,
                      size: 18,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            // Item list
            ...items.map((item) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    '\$${item.price.toStringAsFixed(0)} ${item.name} ${item.description}',
                    style: AppTheme.dmSans(
                      fontSize: 14,
                      color: AppTheme.textSecondary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildRetailerLogo(String retailerName) {
    // Return retailer logo based on name
    final logoPath = _getRetailerLogoPath(retailerName);
    if (logoPath != null) {
      return Image.asset(
        logoPath,
        width: 60,
        height: 24,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => _buildFallbackLogo(retailerName),
      );
    }
    return _buildFallbackLogo(retailerName);
  }

  String? _getRetailerLogoPath(String retailerName) {
    switch (retailerName.toLowerCase()) {
      case 'walmart':
        return 'assets/retailers/walmart.png';
      case 'ikea':
        return 'assets/retailers/ikea.png';
      case 'amazon':
        return 'assets/retailers/amazon.png';
      case 'target':
        return 'assets/retailers/target.png';
      case 'wayfair':
        return 'assets/retailers/wayfair.png';
      default:
        return null;
    }
  }

  Widget _buildFallbackLogo(String retailerName) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.scaffoldBackground,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        retailerName,
        style: AppTheme.dmSans(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: AppTheme.textPrimary,
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: AppTheme.dmSans(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        color: AppTheme.textPrimary,
      ),
    );
  }

  Widget _buildDeliveryAddressCard() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Map thumbnail placeholder
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppTheme.scaffoldBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                IconsaxPlusLinear.location,
                size: 28,
                color: AppTheme.primaryColor,
              ),
            ),
            const SizedBox(width: 16),
            // Address info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Chhatak, Sunamgonj 12/8AB',
                    style: AppTheme.dmSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Sylhet',
                    style: AppTheme.dmSans(
                      fontSize: 14,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            // Checkmark
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFF4CAF50),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPaymentMethodCard() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Visa logo placeholder
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppTheme.scaffoldBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Text(
                  'VISA',
                  style: AppTheme.dmSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF1A1F71),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),
            // Card info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Visa Classic',
                    style: AppTheme.dmSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '**** 7690',
                    style: AppTheme.dmSans(
                      fontSize: 14,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            // Checkmark
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFF4CAF50),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOrderInfoCard(CartProvider cartProvider) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildOrderInfoRow('Subtotal', '\$${cartProvider.subtotal.toStringAsFixed(2)}'),
            const SizedBox(height: 12),
            _buildOrderInfoRow('Shipping', '\$${cartProvider.shipping.toStringAsFixed(2)}'),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Divider(height: 1, color: AppTheme.dividerColor),
            ),
            _buildOrderInfoRow(
              'Total',
              '\$${cartProvider.total.toStringAsFixed(2)}',
              isBold: true,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOrderInfoRow(String label, String value, {bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: AppTheme.dmSans(
            fontSize: 15,
            fontWeight: isBold ? FontWeight.w600 : FontWeight.w400,
            color: isBold ? AppTheme.textPrimary : AppTheme.textSecondary,
          ),
        ),
        Text(
          value,
          style: AppTheme.dmSans(
            fontSize: 15,
            fontWeight: isBold ? FontWeight.w700 : FontWeight.w500,
            color: AppTheme.textPrimary,
          ),
        ),
      ],
    );
  }

  void _handleNavTap(BuildContext context, int index) {
    if (index == 2) return;
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
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
      (route) => false,
    );
  }

  void _handleFabPressed(BuildContext context) {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
      (route) => false,
    );
  }
}
