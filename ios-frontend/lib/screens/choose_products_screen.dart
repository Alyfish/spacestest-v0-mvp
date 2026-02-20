import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/shop_product.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/filters_bottom_sheet.dart';
import '../widgets/shop_product_card.dart';
import 'main_navigation_screen.dart';

class _RankedShopProduct {
  final ShopProduct product;
  final int relevanceScore;
  final int insertionOrder;

  const _RankedShopProduct({
    required this.product,
    required this.relevanceScore,
    required this.insertionOrder,
  });
}

/// Choose Products Screen - Shows product grid for a selected hotspot
class ChooseProductsScreen extends StatefulWidget {
  final ProductHotspot hotspot;
  final VoidCallback? onBack;

  const ChooseProductsScreen({super.key, required this.hotspot, this.onBack});

  @override
  State<ChooseProductsScreen> createState() => _ChooseProductsScreenState();
}

class _ChooseProductsScreenState extends State<ChooseProductsScreen> {
  ProductFilters _currentFilters = ProductFilters.empty;
  List<ShopProduct> _products = [];
  bool _isAnalyzing = true;
  String? _analysisError;

  bool get _isAutoHotspot => widget.hotspot.id.startsWith('auto_');

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _loadFurnitureProducts();
      }
    });
  }

  Future<void> _loadFurnitureProducts() async {
    if (mounted) {
      setState(() {
        _isAnalyzing = true;
        _analysisError = null;
      });
    }

    try {
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      if (_isAutoHotspot) {
        await _loadAutoHotspotProducts(provider);
      } else {
        await _loadManualTapProducts(provider);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _analysisError = e.toString();
        });
      }
    } finally {
      if (mounted) setState(() => _isAnalyzing = false);
    }
  }

  Future<void> _loadAutoHotspotProducts(ProjectProvider provider) async {
    var prefetched = provider.getPrefetchedFurnitureForHotspot(
      widget.hotspot.id,
    );
    var mapped = _mapProductsFromSelections(
      prefetched != null ? [prefetched] : const [],
    );

    // Normal case: prefetch is ready and marker taps are instant.
    if (mapped.isNotEmpty) {
      if (!mounted) return;
      setState(() => _products = mapped);
      return;
    }

    // Empty/missing hotspot cache uses robust fallback analysis.
    await provider.ensureHotspotProductsReady(widget.hotspot, context: context);
    prefetched = provider.getPrefetchedFurnitureForHotspot(widget.hotspot.id);
    mapped = _mapProductsFromSelections(
      prefetched != null ? [prefetched] : const [],
    );

    if (!mounted) return;
    setState(() {
      _products = mapped;
    });
  }

  Future<void> _loadManualTapProducts(ProjectProvider provider) async {
    final imageType = provider.dreamSpaceAnalysisImageType;
    final selections = [
      {
        'id': 'tap_${DateTime.now().millisecondsSinceEpoch}',
        'x': widget.hotspot.x,
        'y': widget.hotspot.y,
        'label': widget.hotspot.label,
      },
    ];

    final success = await provider.analyzeFurniture(
      context,
      selections,
      imageType: imageType,
    );

    if (!success) {
      final error = provider.errorMessage ?? '';
      if (error.isNotEmpty) {
        debugPrint('analyzeFurniture($imageType) failed: $error');
      }
      if (mounted) {
        setState(() {
          _analysisError = provider.errorMessage ?? 'Analysis failed';
        });
      }
      return;
    }

    if (provider.furnitureAnalysis != null) {
      final analysis = provider.furnitureAnalysis!;
      final selectionsList = _extractSelectionResults(analysis);
      final allProducts = _mapProductsFromSelections(selectionsList);
      if (mounted) {
        setState(() {
          _products = allProducts;
        });
      }
      return;
    }

    if (mounted) {
      setState(() {
        _analysisError = provider.errorMessage ?? 'Analysis failed';
      });
    }
  }

  List<dynamic> _extractSelectionResults(Map<String, dynamic> analysis) {
    final raw =
        analysis['selections'] ??
        analysis['results'] ??
        analysis['items'] ??
        (analysis['data'] is Map<String, dynamic>
            ? (analysis['data'] as Map<String, dynamic>)['selections']
            : null);
    if (raw is List) return raw;
    return const [];
  }

  List<ShopProduct> _mapProductsFromSelections(List<dynamic> selectionsList) {
    final rankedByKey = <String, _RankedShopProduct>{};
    final hotspotTokens = _buildHotspotTokens();
    var insertionOrder = 0;

    for (final selection in selectionsList) {
      if (selection is! Map<String, dynamic>) {
        continue;
      }
      final selMap = selection;
      final products = <Map<String, dynamic>>[];
      final primaryProducts = selMap['products'];
      if (primaryProducts is List) {
        for (final raw in primaryProducts) {
          if (raw is Map<String, dynamic>) {
            products.add(raw);
          }
        }
      }

      final bedComponents = selMap['bed_components'];
      if (bedComponents is Map) {
        for (final componentProducts in bedComponents.values) {
          if (componentProducts is! List) continue;
          for (final raw in componentProducts) {
            if (raw is Map<String, dynamic>) {
              products.add(raw);
            }
          }
        }
      }

      for (var i = 0; i < products.length; i++) {
        final p = products[i];
        final productUrl = p['url'] as String? ?? p['link'] as String? ?? '';
        final productId =
            p['id']?.toString() ??
            (productUrl.isNotEmpty ? productUrl : '${widget.hotspot.id}_$i');
        final dedupeKey = productUrl.isNotEmpty
            ? productUrl
            : productId.isNotEmpty
            ? productId
            : '${p['title'] ?? p['name'] ?? 'product'}_$i';
        final imageUrl =
            p['image_url'] as String? ??
            p['imageUrl'] as String? ??
            p['thumbnail'] as String? ??
            '';
        final retailerName =
            p['retailer'] as String? ??
            p['store'] as String? ??
            p['source'] as String? ??
            'Store';
        final normalizedName = _normalizeProductTitle(
          p['title'] as String? ?? p['name'] as String? ?? 'Product',
          retailerName,
        );
        final description =
            p['description'] as String? ??
            selMap['furniture_type'] as String? ??
            widget.hotspot.label;
        final price = _parseNumericPrice(p['price'], p['price_str']);
        final priceDisplay = _parsePriceDisplay(p['price_str'], price);
        final relevanceScore = _computeRelevanceScore(
          product: p,
          selection: selMap,
          title: normalizedName,
          description: description,
          retailer: retailerName,
          hotspotTokens: hotspotTokens,
        );

        final candidate = _RankedShopProduct(
          product: ShopProduct(
            id: productId,
            name: normalizedName,
            description: description,
            price: price,
            displayPrice: priceDisplay,
            retailerName: retailerName,
            imageUrl: imageUrl,
            productUrl: productUrl,
            category: p['category']?.toString(),
          ),
          relevanceScore: relevanceScore,
          insertionOrder: insertionOrder++,
        );

        final existing = rankedByKey[dedupeKey];
        if (existing == null) {
          rankedByKey[dedupeKey] = candidate;
          continue;
        }

        if (_isBetterCandidate(candidate, existing)) {
          rankedByKey[dedupeKey] = candidate;
        }
      }
    }

    final ranked = rankedByKey.values.toList();
    if (ranked.isEmpty) return const <ShopProduct>[];

    ranked.sort((a, b) {
      final scoreCmp = b.relevanceScore.compareTo(a.relevanceScore);
      if (scoreCmp != 0) return scoreCmp;

      final bHasImage = b.product.imageUrl.isNotEmpty ? 1 : 0;
      final aHasImage = a.product.imageUrl.isNotEmpty ? 1 : 0;
      final imageCmp = bHasImage.compareTo(aHasImage);
      if (imageCmp != 0) return imageCmp;

      final bHasPrice =
          (b.product.displayPrice?.trim().isNotEmpty ?? false) ||
          b.product.price > 0;
      final aHasPrice =
          (a.product.displayPrice?.trim().isNotEmpty ?? false) ||
          a.product.price > 0;
      final priceCmp = (bHasPrice ? 1 : 0).compareTo(aHasPrice ? 1 : 0);
      if (priceCmp != 0) return priceCmp;

      return a.insertionOrder.compareTo(b.insertionOrder);
    });

    return ranked.map((item) => item.product).toList();
  }

  bool _isBetterCandidate(_RankedShopProduct next, _RankedShopProduct current) {
    if (next.relevanceScore != current.relevanceScore) {
      return next.relevanceScore > current.relevanceScore;
    }
    final nextHasImage = next.product.imageUrl.isNotEmpty;
    final currentHasImage = current.product.imageUrl.isNotEmpty;
    if (nextHasImage != currentHasImage) {
      return nextHasImage;
    }
    final nextHasPrice =
        (next.product.displayPrice?.trim().isNotEmpty ?? false) ||
        next.product.price > 0;
    final currentHasPrice =
        (current.product.displayPrice?.trim().isNotEmpty ?? false) ||
        current.product.price > 0;
    if (nextHasPrice != currentHasPrice) {
      return nextHasPrice;
    }
    return next.insertionOrder < current.insertionOrder;
  }

  List<String> _buildHotspotTokens() {
    final source = '${widget.hotspot.label} ${widget.hotspot.itemType}'
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9\s]'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    if (source.isEmpty) return const <String>[];
    return source
        .split(' ')
        .where((token) => token.length >= 3)
        .toSet()
        .toList();
  }

  int _computeRelevanceScore({
    required Map<String, dynamic> product,
    required Map<String, dynamic> selection,
    required String title,
    required String description,
    required String retailer,
    required List<String> hotspotTokens,
  }) {
    var score = 0;
    final selectionId = selection['id']?.toString().trim() ?? '';
    if (selectionId == widget.hotspot.id) {
      score += 3;
    }

    final category =
        (product['category'] ??
                product['furniture_type'] ??
                selection['furniture_type'] ??
                '')
            .toString()
            .toLowerCase();
    final titleLower = title.toLowerCase();
    final descriptionLower = description.toLowerCase();
    final retailerLower = retailer.toLowerCase();
    final haystack = '$titleLower $descriptionLower $category $retailerLower';

    for (final token in hotspotTokens) {
      if (titleLower.contains(token)) {
        score += 4;
      } else if (descriptionLower.contains(token) || category.contains(token)) {
        score += 2;
      } else if (haystack.contains(token)) {
        score += 1;
      }
    }

    if (product['image_url']?.toString().trim().isNotEmpty == true ||
        product['imageUrl']?.toString().trim().isNotEmpty == true ||
        product['thumbnail']?.toString().trim().isNotEmpty == true) {
      score += 1;
    }

    final rawPrice = _parseNumericPrice(product['price'], product['price_str']);
    if (rawPrice > 0) {
      score += 1;
    }
    return score;
  }

  String _normalizeProductTitle(String rawTitle, String retailerName) {
    final title = rawTitle.trim();
    if (title.isEmpty) return 'Product';

    final retailerPattern = RegExp(
      '^${RegExp.escape(retailerName)}(?:\\.com)?\\s*[:\\-]\\s*',
      caseSensitive: false,
    );
    final cleaned = title.replaceFirst(retailerPattern, '').trim();
    return cleaned.isEmpty ? title : cleaned;
  }

  double _parseNumericPrice(dynamic rawPrice, dynamic rawPriceStr) {
    if (rawPrice is num) {
      return rawPrice.toDouble();
    }
    if (rawPrice is String) {
      final parsed = double.tryParse(rawPrice.replaceAll(',', '').trim());
      if (parsed != null) return parsed;
    }

    final priceStr = rawPriceStr?.toString() ?? '';
    if (priceStr.isEmpty) return 0.0;
    final match = RegExp(
      r'(\d+(?:\.\d+)?)',
    ).firstMatch(priceStr.replaceAll(',', ''));
    if (match == null) return 0.0;
    return double.tryParse(match.group(1) ?? '') ?? 0.0;
  }

  String? _parsePriceDisplay(dynamic rawPriceStr, double numericPrice) {
    final raw = rawPriceStr?.toString().trim() ?? '';
    if (raw.isNotEmpty) return raw;
    if (numericPrice <= 0) return null;
    return '\$${numericPrice.toStringAsFixed(2)}';
  }

  List<ShopProduct> get _filteredProducts {
    var products = _products;

    if (_currentFilters.minPrice != null) {
      products = products
          .where((p) => p.price >= _currentFilters.minPrice!)
          .toList();
    }
    if (_currentFilters.maxPrice != null) {
      products = products
          .where((p) => p.price <= _currentFilters.maxPrice!)
          .toList();
    }

    if (_currentFilters.selectedMarketplaces.isNotEmpty) {
      products = products
          .where(
            (p) =>
                _currentFilters.selectedMarketplaces.contains(p.retailerName),
          )
          .toList();
    }

    return products;
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
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

  Future<void> _openProductLink(ShopProduct product) async {
    final url = product.productUrl?.trim() ?? '';
    if (url.isEmpty) {
      _showSnackBar('Link not available');
      return;
    }

    final uri = Uri.tryParse(url);
    final hasValidScheme =
        uri != null && (uri.scheme == 'http' || uri.scheme == 'https');
    if (!hasValidScheme) {
      _showSnackBar('Link not available');
      return;
    }

    try {
      final didLaunch = await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
      if (!didLaunch) {
        _showSnackBar('Unable to open link');
      }
    } catch (_) {
      _showSnackBar('Unable to open link');
    }
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
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
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
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
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
    final products = _filteredProducts;

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Header with back button
            _buildHeader(),

            // Filters button
            if (!_isAnalyzing) _buildFiltersButton(),

            // Product grid / loading / error
            Expanded(
              child: _isAnalyzing
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const CircularProgressIndicator(
                            color: AppTheme.primaryColor,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Finding matching products...',
                            style: AppTheme.dmSans(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    )
                  : _analysisError != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            IconsaxPlusLinear.warning_2,
                            size: 48,
                            color: AppTheme.textTertiary,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to analyze furniture',
                            style: AppTheme.dmSans(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 40),
                            child: Text(
                              _analysisError!,
                              style: AppTheme.dmSans(
                                fontSize: 14,
                                color: AppTheme.textSecondary,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                          const SizedBox(height: 24),
                          ElevatedButton(
                            onPressed: _loadFurnitureProducts,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.primaryColor,
                            ),
                            child: Text(
                              'Retry',
                              style: AppTheme.dmSans(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                    )
                  : products.isEmpty
                  ? _buildEmptyState()
                  : GridView.builder(
                      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 12,
                            mainAxisSpacing: 12,
                            childAspectRatio: 0.65,
                          ),
                      itemCount: products.length,
                      itemBuilder: (context, index) {
                        final product = products[index];
                        return ShopProductCard(
                          product: product,
                          onTap: () => _openProductLink(product),
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
          Icon(IconsaxPlusLinear.box, size: 64, color: AppTheme.textTertiary),
          const SizedBox(height: 16),
          Text(
            'No products found for this hotspot',
            style: AppTheme.dmSans(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Try adjusting your filters',
            style: AppTheme.dmSans(fontSize: 14, color: AppTheme.textSecondary),
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
      child: SizedBox(
        height: 56,
        width: double.infinity,
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
    );
  }
}
