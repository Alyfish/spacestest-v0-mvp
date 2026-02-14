import 'package:flutter/material.dart';
import '../models/shop_product.dart';

/// Provider for managing shopping cart state
class CartProvider extends ChangeNotifier {
  final List<ShopProduct> _cartItems = [];

  /// All items in the cart
  List<ShopProduct> get cartItems => List.unmodifiable(_cartItems);

  /// Total number of items in cart
  int get itemCount => _cartItems.length;

  /// Check if cart is empty
  bool get isEmpty => _cartItems.isEmpty;

  /// Check if cart has items
  bool get hasItems => _cartItems.isNotEmpty;

  /// Total price of all items
  double get subtotal {
    return _cartItems.fold(0, (sum, item) => sum + item.price);
  }

  /// Shipping cost (mock - could be calculated based on items)
  double get shipping => _cartItems.isEmpty ? 0 : 9.99;

  /// Total including shipping
  double get total => subtotal + shipping;

  /// Get items grouped by retailer
  Map<String, List<ShopProduct>> get itemsByRetailer {
    final Map<String, List<ShopProduct>> grouped = {};
    for (final item in _cartItems) {
      grouped.putIfAbsent(item.retailerName, () => []).add(item);
    }
    return grouped;
  }

  /// Get unique retailers in cart
  List<String> get retailers => itemsByRetailer.keys.toList();

  /// Check if a product is in the cart
  bool isInCart(String productId) {
    return _cartItems.any((item) => item.id == productId);
  }

  /// Add a product to cart
  void addToCart(ShopProduct product) {
    if (!isInCart(product.id)) {
      _cartItems.add(product);
      notifyListeners();
    }
  }

  /// Remove a product from cart by ID
  void removeFromCart(String productId) {
    _cartItems.removeWhere((item) => item.id == productId);
    notifyListeners();
  }

  /// Toggle product in cart (add if not present, remove if present)
  void toggleCartItem(ShopProduct product) {
    if (isInCart(product.id)) {
      removeFromCart(product.id);
    } else {
      addToCart(product);
    }
  }

  /// Remove all items from a specific retailer
  void clearRetailerItems(String retailerName) {
    _cartItems.removeWhere((item) => item.retailerName == retailerName);
    notifyListeners();
  }

  /// Clear entire cart
  void clearCart() {
    _cartItems.clear();
    notifyListeners();
  }

  /// Get count of items for a specific retailer
  int getRetailerItemCount(String retailerName) {
    return _cartItems.where((item) => item.retailerName == retailerName).length;
  }

  /// Get items for a specific retailer
  List<ShopProduct> getRetailerItems(String retailerName) {
    return _cartItems.where((item) => item.retailerName == retailerName).toList();
  }
}
