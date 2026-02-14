import 'dart:async';

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/animated_border_card.dart';
import '../widgets/bottom_cta_bar.dart';

/// Lightweight model used only for display inside this screen.
class _Product {
  final String url;
  final String title;
  final String store;
  final String? imageUrl;

  const _Product({
    required this.url,
    required this.title,
    required this.store,
    this.imageUrl,
  });
}

/// Screen for selecting products that match a specific improvement recommendation.
///
/// Data priority:
///   1. Cached `productSuggestions` from provider
///   2. Cached/fetched `trendingProducts` as fallback
///   3. Adaptive polling (500ms x4, then 2s) up to ~30s
class LikeTheseScreen extends StatefulWidget {
  final String itemType;
  final String? actionId;

  const LikeTheseScreen({super.key, required this.itemType, this.actionId});

  @override
  State<LikeTheseScreen> createState() => _LikeTheseScreenState();
}

class _LikeTheseScreenState extends State<LikeTheseScreen> {
  List<_Product> _products = [];
  String? _selectedUrl;
  bool _isLoading = true;
  bool _isStillWorking = false;
  bool _hasError = false;
  Timer? _pollTimer;
  Timer? _stillWorkingTimer;
  int _pollCount = 0;
  static const int _maxPolls = 18;

  // ---------------------------------------------------------------------------
  // Category matching helpers (strict, no fallback)
  // ---------------------------------------------------------------------------

  static String _normalize(String s) => s.trim().toLowerCase();

  static bool _isMatchingCategory(
    Map<dynamic, dynamic> category,
    String itemType,
  ) {
    final rec = _normalize(
      (category['recommendation'] ?? category['name'] ?? '').toString(),
    );
    final target = _normalize(itemType);
    if (rec.isEmpty || target.isEmpty) return false;
    return rec == target || rec.contains(target) || target.contains(rec);
  }

  /// Extract products from a suggestions/trending payload for the given itemType.
  /// Returns empty list if no matching category found (strict — no fallback).
  static List<_Product> _extractProducts(
    Map<String, dynamic>? payload,
    String itemType,
  ) {
    if (payload == null) return [];

    final categories = payload['categories'] as List? ?? const [];
    for (final raw in categories) {
      if (raw is! Map) continue;
      if (!_isMatchingCategory(raw, itemType)) continue;

      final products = raw['products'] as List? ?? const [];
      return products
          .whereType<Map>()
          .where(
            (p) =>
                (p['image_url'] ?? p['imageUrl'] ?? '').toString().isNotEmpty,
          )
          .take(4)
          .map(
            (p) => _Product(
              url: (p['url'] ?? '').toString(),
              title: (p['title'] ?? p['name'] ?? 'Product').toString(),
              store: (p['store'] ?? p['retailer'] ?? '').toString(),
              imageUrl: (p['image_url'] ?? p['imageUrl'] ?? '').toString(),
            ),
          )
          .toList();
    }

    // Also check selected_products / favorite_products with category filtering.
    final selected = payload['selected_products'] as List? ?? const [];
    final favorites = payload['favorite_products'] as List? ?? const [];
    final merged = [...selected, ...favorites];
    final matched = merged.whereType<Map>().where((p) {
      final cat = _normalize((p['category'] ?? '').toString());
      final target = _normalize(itemType);
      return cat == target || cat.contains(target) || target.contains(cat);
    }).toList();

    if (matched.isNotEmpty) {
      return matched
          .where(
            (p) =>
                (p['image_url'] ?? p['imageUrl'] ?? '').toString().isNotEmpty,
          )
          .take(4)
          .map(
            (p) => _Product(
              url: (p['url'] ?? '').toString(),
              title: (p['title'] ?? p['name'] ?? 'Product').toString(),
              store: (p['store'] ?? p['retailer'] ?? '').toString(),
              imageUrl: (p['image_url'] ?? p['imageUrl'] ?? '').toString(),
            ),
          )
          .toList();
    }

    return [];
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _stillWorkingTimer?.cancel();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Data loading with adaptive polling
  // ---------------------------------------------------------------------------

  Future<void> _loadProducts() async {
    final provider = Provider.of<ProjectProvider>(context, listen: false);

    // 1. Try cached productSuggestions.
    var found = _extractProducts(provider.productSuggestions, widget.itemType);
    if (found.isNotEmpty) {
      _showProducts(found);
      return;
    }

    // 2. Try cached trendingProducts.
    found = _extractProducts(provider.trendingProducts, widget.itemType);
    if (found.isNotEmpty) {
      _showProducts(found);
      return;
    }

    // 3. Start "still working" timer (fires after 15s).
    _stillWorkingTimer = Timer(const Duration(seconds: 15), () {
      if (mounted && _isLoading) {
        setState(() => _isStillWorking = true);
      }
    });

    // 4. Adaptive polling: first 4 at 500ms, then 2s.
    _poll(provider);
  }

  void _poll(ProjectProvider provider) {
    if (!mounted || _pollCount >= _maxPolls) {
      // Exhausted — check for error reason from provider.
      if (mounted && _products.isEmpty) {
        setState(() {
          _isLoading = false;
          _hasError = true;
        });
      }
      return;
    }

    final interval = _pollCount < 4
        ? const Duration(milliseconds: 500)
        : const Duration(seconds: 2);

    _pollTimer = Timer(interval, () async {
      if (!mounted) return;
      _pollCount++;

      await Future.wait([
        provider.refreshProductSuggestionsSnapshot(context),
        provider.preloadTrendingProducts(context),
      ]);

      if (!mounted) return;

      var found = _extractProducts(
        provider.productSuggestions,
        widget.itemType,
      );
      if (found.isEmpty) {
        found = _extractProducts(provider.trendingProducts, widget.itemType);
      }

      if (found.isNotEmpty) {
        _showProducts(found);
        return;
      }

      // Keep polling.
      _poll(provider);
    });
  }

  void _showProducts(List<_Product> products) {
    _pollTimer?.cancel();
    _stillWorkingTimer?.cancel();
    if (!mounted) return;
    setState(() {
      _products = products;
      _isLoading = false;
      _isStillWorking = false;
      _hasError = false;
    });
  }

  void _retry() {
    setState(() {
      _isLoading = true;
      _isStillWorking = false;
      _hasError = false;
      _products = [];
      _selectedUrl = null;
      _pollCount = 0;
    });
    _loadProducts();
  }

  // ---------------------------------------------------------------------------
  // Selection & navigation
  // ---------------------------------------------------------------------------

  void _toggleSelection(String url) {
    setState(() {
      _selectedUrl = _selectedUrl == url ? null : url;
    });
  }

  void _handleContinue() {
    if (_selectedUrl == null) {
      Navigator.pop(context);
      return;
    }

    final selected = _products.firstWhere((p) => p.url == _selectedUrl);

    Navigator.pop(context, {
      'actionId': widget.actionId,
      'itemType': widget.itemType,
      'selectedOptionId': 'trending',
      'selectedOptionTitle': selected.title,
      'selectionSummary': '${selected.title} from ${selected.store}',
      'selectedItems': [
        {
          'url': selected.url,
          'title': selected.title,
          'store': selected.store,
          'image_url': selected.imageUrl,
        },
      ],
    });
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 4),
              child: Text(
                'Like These?',
                style: AppTheme.dmSans(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),
            // Subtitle
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              child: Text(
                'Pick a product you love.',
                style: AppTheme.dmSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w400,
                  color: AppTheme.textSecondary,
                ),
              ),
            ),

            // Content area
            Expanded(child: _buildContent()),

            // Bottom CTA bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: BottomCTABar(
                secondaryText: 'Back',
                onSecondaryPressed: () => Navigator.pop(context),
                primaryText: _selectedUrl != null ? 'Continue' : 'Skip',
                onPrimaryPressed: _handleContinue,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) return _buildLoading();
    if (_hasError) return _buildError();
    if (_products.isEmpty) return _buildEmpty();
    return _buildGrid();
  }

  Widget _buildLoading() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(color: AppTheme.primaryColor),
          const SizedBox(height: 16),
          Text(
            _isStillWorking
                ? 'Still working on it...'
                : 'Searching for matching products...',
            style: AppTheme.dmSans(fontSize: 14, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildError() {
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    final reason = provider.searchFailureReason;

    String title;
    String subtitle;
    switch (reason) {
      case SearchFailureReason.networkError:
        title = 'Connection issue';
        subtitle = 'Check your internet and try again.';
        break;
      case SearchFailureReason.timeout:
        title = 'Request timed out';
        subtitle = 'The search is taking longer than expected.';
        break;
      case SearchFailureReason.jobFailed:
      default:
        title = 'Something went wrong';
        subtitle = 'We couldn\'t find products right now.';
        break;
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              IconsaxPlusLinear.info_circle,
              size: 48,
              color: AppTheme.textTertiary,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: AppTheme.dmSans(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: AppTheme.dmSans(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.dividerColor),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'Back',
                    style: AppTheme.dmSans(color: AppTheme.textPrimary),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _retry,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'Retry',
                    style: AppTheme.dmSans(color: Colors.white),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(IconsaxPlusLinear.box, size: 48, color: AppTheme.textTertiary),
          const SizedBox(height: 16),
          Text(
            'No products found for "${widget.itemType}" yet.',
            textAlign: TextAlign.center,
            style: AppTheme.dmSans(fontSize: 14, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _retry,
            child: Text(
              'Try again',
              style: AppTheme.dmSans(color: AppTheme.primaryColor),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGrid() {
    return GridView.builder(
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
        final isSelected = _selectedUrl == product.url;
        return AnimatedBorderCard(
          isSelected: isSelected,
          animateWhenUnselected: false,
          onTap: () => _toggleSelection(product.url),
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Product image
              Expanded(
                child: Stack(
                  children: [
                    ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(AppTheme.cardRadius),
                      ),
                      child: Container(
                        width: double.infinity,
                        color: AppTheme.scaffoldBackground,
                        child:
                            product.imageUrl != null &&
                                product.imageUrl!.isNotEmpty
                            ? Image.network(
                                product.imageUrl!,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) =>
                                    _buildPlaceholder(),
                              )
                            : _buildPlaceholder(),
                      ),
                    ),
                    // Retailer badge
                    if (product.store.isNotEmpty)
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
                            product.store,
                            style: AppTheme.dmSans(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textPrimary,
                            ),
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
                  product.title,
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
        );
      },
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
