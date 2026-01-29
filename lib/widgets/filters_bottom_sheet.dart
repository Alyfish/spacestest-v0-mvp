import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

/// Filter state model
class ProductFilters {
  final double? minPrice;
  final double? maxPrice;
  final Set<String> selectedColors;
  final Set<String> selectedMarketplaces;

  const ProductFilters({
    this.minPrice,
    this.maxPrice,
    this.selectedColors = const {},
    this.selectedMarketplaces = const {},
  });

  ProductFilters copyWith({
    double? minPrice,
    double? maxPrice,
    Set<String>? selectedColors,
    Set<String>? selectedMarketplaces,
  }) {
    return ProductFilters(
      minPrice: minPrice ?? this.minPrice,
      maxPrice: maxPrice ?? this.maxPrice,
      selectedColors: selectedColors ?? this.selectedColors,
      selectedMarketplaces: selectedMarketplaces ?? this.selectedMarketplaces,
    );
  }

  bool get hasFilters =>
      minPrice != null ||
      maxPrice != null ||
      selectedColors.isNotEmpty ||
      selectedMarketplaces.isNotEmpty;

  static const ProductFilters empty = ProductFilters();
}

/// Shows the filters bottom sheet and returns the selected filters
Future<ProductFilters?> showFiltersBottomSheet(
  BuildContext context, {
  ProductFilters? currentFilters,
}) {
  return showModalBottomSheet<ProductFilters>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => FiltersBottomSheet(
      initialFilters: currentFilters ?? ProductFilters.empty,
    ),
  );
}

/// Filters bottom sheet widget
class FiltersBottomSheet extends StatefulWidget {
  final ProductFilters initialFilters;

  const FiltersBottomSheet({
    super.key,
    required this.initialFilters,
  });

  @override
  State<FiltersBottomSheet> createState() => _FiltersBottomSheetState();
}

class _FiltersBottomSheetState extends State<FiltersBottomSheet> {
  late ProductFilters _filters;

  // Expandable section states
  bool _priceExpanded = false;
  bool _colorsExpanded = false;
  bool _marketplaceExpanded = false;

  // Available options
  static const List<String> _availableColors = [
    'White',
    'Black',
    'Gray',
    'Brown',
    'Beige',
    'Blue',
    'Green',
    'Red',
  ];

  static const List<String> _availableMarketplaces = [
    'Walmart',
    'Amazon',
    'IKEA',
    'Ashley',
    'Target',
    'Wayfair',
  ];

  // Price range values
  RangeValues _priceRange = const RangeValues(0, 1000);

  @override
  void initState() {
    super.initState();
    _filters = widget.initialFilters;
    if (_filters.minPrice != null || _filters.maxPrice != null) {
      _priceRange = RangeValues(
        _filters.minPrice ?? 0,
        _filters.maxPrice ?? 1000,
      );
    }
  }

  void _clearAll() {
    setState(() {
      _filters = ProductFilters.empty;
      _priceRange = const RangeValues(0, 1000);
    });
  }

  void _applyFilters() {
    final appliedFilters = ProductFilters(
      minPrice: _priceRange.start > 0 ? _priceRange.start : null,
      maxPrice: _priceRange.end < 1000 ? _priceRange.end : null,
      selectedColors: _filters.selectedColors,
      selectedMarketplaces: _filters.selectedMarketplaces,
    );
    Navigator.pop(context, appliedFilters);
  }

  void _toggleColor(String color) {
    setState(() {
      final colors = Set<String>.from(_filters.selectedColors);
      if (colors.contains(color)) {
        colors.remove(color);
      } else {
        colors.add(color);
      }
      _filters = _filters.copyWith(selectedColors: colors);
    });
  }

  void _toggleMarketplace(String marketplace) {
    setState(() {
      final marketplaces = Set<String>.from(_filters.selectedMarketplaces);
      if (marketplaces.contains(marketplace)) {
        marketplaces.remove(marketplace);
      } else {
        marketplaces.add(marketplace);
      }
      _filters = _filters.copyWith(selectedMarketplaces: marketplaces);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 60),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppTheme.dividerColor,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Title
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
            child: Row(
              children: [
                Text(
                  'Filters',
                  style: AppTheme.dmSans(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ],
            ),
          ),

          // Filter sections
          Flexible(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                children: [
                  // Price Range
                  _buildExpandableSection(
                    title: 'Price Range',
                    isExpanded: _priceExpanded,
                    onTap: () => setState(() => _priceExpanded = !_priceExpanded),
                    child: _buildPriceRangeContent(),
                  ),

                  const SizedBox(height: 12),

                  // Colors
                  _buildExpandableSection(
                    title: 'Colors',
                    isExpanded: _colorsExpanded,
                    onTap: () => setState(() => _colorsExpanded = !_colorsExpanded),
                    child: _buildColorsContent(),
                  ),

                  const SizedBox(height: 12),

                  // Marketplace
                  _buildExpandableSection(
                    title: 'Marketplace',
                    isExpanded: _marketplaceExpanded,
                    onTap: () => setState(() => _marketplaceExpanded = !_marketplaceExpanded),
                    child: _buildMarketplaceContent(),
                  ),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),

          // Bottom buttons
          Container(
            padding: EdgeInsets.fromLTRB(
              20,
              16,
              20,
              MediaQuery.of(context).padding.bottom + 16,
            ),
            decoration: BoxDecoration(
              color: AppTheme.surfaceColor,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Row(
              children: [
                // Clear All button
                Expanded(
                  child: OutlinedButton(
                    onPressed: _clearAll,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      side: const BorderSide(color: AppTheme.dividerColor),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: Text(
                      'Clear All',
                      style: AppTheme.dmSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Apply Filters button
                Expanded(
                  child: ElevatedButton(
                    onPressed: _applyFilters,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: Text(
                      'Apply Filters',
                      style: AppTheme.dmSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpandableSection({
    required String title,
    required bool isExpanded,
    required VoidCallback onTap,
    required Widget child,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.dividerColor),
      ),
      child: Column(
        children: [
          // Header
          InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    title,
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                  Icon(
                    isExpanded
                        ? IconsaxPlusLinear.minus
                        : IconsaxPlusLinear.add,
                    size: 20,
                    color: AppTheme.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          // Expandable content
          if (isExpanded) ...[
            const Divider(height: 1, color: AppTheme.dividerColor),
            Padding(
              padding: const EdgeInsets.all(16),
              child: child,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPriceRangeContent() {
    return Column(
      children: [
        RangeSlider(
          values: _priceRange,
          min: 0,
          max: 1000,
          divisions: 20,
          activeColor: AppTheme.primaryColor,
          inactiveColor: AppTheme.dividerColor,
          labels: RangeLabels(
            '\$${_priceRange.start.round()}',
            '\$${_priceRange.end.round()}',
          ),
          onChanged: (values) {
            setState(() => _priceRange = values);
          },
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '\$${_priceRange.start.round()}',
              style: AppTheme.dmSans(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
            Text(
              '\$${_priceRange.end.round()}',
              style: AppTheme.dmSans(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildColorsContent() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _availableColors.map((color) {
        final isSelected = _filters.selectedColors.contains(color);
        return FilterChip(
          label: Text(color),
          selected: isSelected,
          onSelected: (_) => _toggleColor(color),
          selectedColor: AppTheme.primaryColor.withValues(alpha: 0.15),
          checkmarkColor: AppTheme.primaryColor,
          labelStyle: AppTheme.dmSans(
            fontSize: 14,
            color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimary,
          ),
          side: BorderSide(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildMarketplaceContent() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _availableMarketplaces.map((marketplace) {
        final isSelected = _filters.selectedMarketplaces.contains(marketplace);
        return FilterChip(
          label: Text(marketplace),
          selected: isSelected,
          onSelected: (_) => _toggleMarketplace(marketplace),
          selectedColor: AppTheme.primaryColor.withValues(alpha: 0.15),
          checkmarkColor: AppTheme.primaryColor,
          labelStyle: AppTheme.dmSans(
            fontSize: 14,
            color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimary,
          ),
          side: BorderSide(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        );
      }).toList(),
    );
  }
}
