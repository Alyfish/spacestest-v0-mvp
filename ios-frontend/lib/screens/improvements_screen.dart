import 'dart:async';

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/animated_border_card.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/bottom_cta_bar.dart';
import 'design_style_selection_screen.dart' show ChooseStyleScreen;
import 'like_these_screen.dart';
import 'main_navigation_screen.dart';

/// Model for storing selection details to display in expanded rows
class _SelectionDetails {
  final String title;
  final String description;

  const _SelectionDetails({required this.title, required this.description});
}

const List<String> _recommendationActionPrefixes = [
  'add ',
  'change ',
  'replace ',
  'update ',
  'install ',
  'hang ',
  'place ',
];

@visibleForTesting
String formatImprovementRecommendationTitle(String recommendation) {
  final trimmed = recommendation.trim();
  if (trimmed.isEmpty) {
    return 'Update item';
  }

  final lower = trimmed.toLowerCase();
  for (final prefix in _recommendationActionPrefixes) {
    if (lower.startsWith(prefix)) {
      return trimmed;
    }
  }
  return 'Update $trimmed';
}

class ImprovementsScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final void Function(
    List<String> recsToSelect,
    bool needsColorSave,
    bool needsStyleSave,
  )?
  onImprove;

  const ImprovementsScreen({super.key, this.onBack, this.onImprove});

  @override
  State<ImprovementsScreen> createState() => _ImprovementsScreenState();
}

class _ImprovementsScreenState extends State<ImprovementsScreen> {
  ProjectProvider? _projectProvider;
  bool _backgroundErrorHookRegistered = false;
  bool _isSubmitting = false;
  Timer? _productPollTimer;
  final Set<String> _selectedActionIds = <String>{};
  final Map<String, _SelectionDetails> _selectionDetails = {};
  final List<_ImprovementCardData> _staticActions = const [
    _ImprovementCardData(
      id: 'color_palette',
      title: 'Color Palette',
      icon: IconsaxPlusLinear.colorfilter,
    ),
    _ImprovementCardData(
      id: 'design_style',
      title: 'Design Style',
      icon: IconsaxPlusLinear.brush_2,
    ),
  ];

  @override
  void initState() {
    super.initState();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final provider = context.read<ProjectProvider>();
    if (!_backgroundErrorHookRegistered) {
      _projectProvider = provider;
      provider.onBackgroundSaveError = (message) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppTheme.errorColor,
            duration: const Duration(seconds: 4),
          ),
        );
      };
      _backgroundErrorHookRegistered = true;
    }

    // Keep recommendation + image-backed suggestion warmup running in background.
    if (provider.productRecommendations.isEmpty ||
        !provider.hasImageBackedSuggestions) {
      unawaited(provider.warmRecommendationsAndSearch(context));
    }

    // Poll for partial product results arriving on the backend.
    if (!provider.hasImageBackedSuggestions && _productPollTimer == null) {
      _productPollTimer = Timer.periodic(
        const Duration(seconds: 3),
        (_) => _pollForProducts(),
      );
    }
  }

  @override
  void dispose() {
    _productPollTimer?.cancel();
    _productPollTimer = null;
    // Clean up callback to avoid stale references
    _projectProvider?.onBackgroundSaveError = null;
    super.dispose();
  }

  Future<void> _pollForProducts() async {
    if (!mounted) {
      _productPollTimer?.cancel();
      _productPollTimer = null;
      return;
    }
    final provider = context.read<ProjectProvider>();
    if (provider.hasImageBackedSuggestions) {
      _productPollTimer?.cancel();
      _productPollTimer = null;
      return;
    }
    await Future.wait([
      provider.refreshProductSuggestionsSnapshot(context),
      provider.preloadTrendingProducts(context),
    ]);
  }

  /// Build dynamic actions from AI-generated product recommendations.
  List<_ImprovementCardData> _dynamicActions(ProjectProvider provider) {
    return provider.productRecommendations.take(2).toList().asMap().entries.map(
      (entry) {
        final index = entry.key;
        final rec = entry.value;
        final compactId = rec
            .toLowerCase()
            .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
            .replaceAll(RegExp(r'_+'), '_')
            .replaceAll(RegExp(r'^_|_$'), '');
        final id = compactId.isEmpty ? 'recommendation_$index' : compactId;
        return _ImprovementCardData(
          id: id,
          title: formatImprovementRecommendationTitle(rec),
          icon: _getIconForKeyword(rec),
          recommendation: rec,
        );
      },
    ).toList();
  }

  IconData _getIconForKeyword(String keyword) {
    final lower = keyword.toLowerCase();
    if (lower.contains('lamp') || lower.contains('light')) {
      return IconsaxPlusLinear.lamp_on;
    } else if (lower.contains('sofa') ||
        lower.contains('couch') ||
        lower.contains('chair')) {
      return IconsaxPlusLinear.lamp_on;
    } else if (lower.contains('vase') ||
        lower.contains('plant') ||
        lower.contains('flower')) {
      return IconsaxPlusLinear.lovely;
    } else if (lower.contains('table') || lower.contains('desk')) {
      return IconsaxPlusLinear.box;
    } else if (lower.contains('rug') || lower.contains('carpet')) {
      return IconsaxPlusLinear.colorfilter;
    } else if (lower.contains('pillow') ||
        lower.contains('cushion') ||
        lower.contains('throw')) {
      return IconsaxPlusLinear.lovely;
    } else if (lower.contains('art') ||
        lower.contains('picture') ||
        lower.contains('frame')) {
      return IconsaxPlusLinear.brush_2;
    } else {
      return IconsaxPlusLinear.add_circle;
    }
  }

  void _handleCardTap(_ImprovementCardData data) {
    // If already selected, deselect and clear provider state
    if (_selectedActionIds.contains(data.id)) {
      setState(() {
        _selectedActionIds.remove(data.id);
        _selectionDetails.remove(data.id);
      });
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      if (data.id == 'color_palette') {
        provider.clearColorPalette();
      } else if (data.id == 'design_style') {
        provider.clearDesignStyle();
      }
      return;
    }

    // Not selected — open picker
    if (data.id == 'color_palette') {
      _openColorPalette();
    } else if (data.id == 'design_style') {
      _openDesignStyle();
    } else {
      final itemType = data.recommendation;
      if (itemType == null || itemType.isEmpty) return;
      _openLikeThese(itemType, data.id, data.title);
    }
  }

  Future<void> _openLikeThese(
    String itemType,
    String actionId,
    String title,
  ) async {
    final result = await Navigator.push<Map<String, dynamic>?>(
      context,
      MaterialPageRoute(
        builder: (_) => LikeTheseScreen(itemType: itemType, actionId: actionId),
      ),
    );
    if (result == null) return;

    final selectedItemsRaw = result['selectedItems'];
    if (selectedItemsRaw is! List || selectedItemsRaw.isEmpty) return;

    final selectedOptionTitle = result['selectedOptionTitle'] as String?;
    final selectionSummary = result['selectionSummary'] as String?;
    final firstItemRaw = selectedItemsRaw.first;
    final firstItem = firstItemRaw is Map
        ? Map<String, dynamic>.from(firstItemRaw)
        : const <String, dynamic>{};

    final fallbackDescription =
        '${selectedItemsRaw.length} item${selectedItemsRaw.length > 1 ? 's' : ''} selected from '
        '${firstItem['store'] ?? firstItem['retailer'] ?? 'Store'}';

    setState(() {
      _selectedActionIds.add(actionId);
      _selectionDetails[actionId] = _SelectionDetails(
        title: selectedOptionTitle ?? title,
        description: selectionSummary ?? fallbackDescription,
      );
    });
  }

  Future<void> _openColorPalette() async {
    final result = await Navigator.push<Map<String, String>?>(
      context,
      MaterialPageRoute(builder: (_) => const ColorPaletteSelectionScreen()),
    );
    if (result != null) {
      setState(() {
        _selectedActionIds.add('color_palette');
        _selectionDetails['color_palette'] = _SelectionDetails(
          title: result['name'] ?? 'Selected Palette',
          description: 'Unselected items remain unchanged in your design',
        );
      });
    }
  }

  Future<void> _openDesignStyle() async {
    final result = await Navigator.push<Map<String, String>?>(
      context,
      MaterialPageRoute(builder: (_) => const ChooseStyleScreen()),
    );
    if (result != null) {
      setState(() {
        _selectedActionIds.add('design_style');
        _selectionDetails['design_style'] = _SelectionDetails(
          title: result['name'] ?? 'Selected Style',
          description:
              'Inviting shades of beige, terracotta, and for a cozy atmos.',
        );
      });
    }
  }

  void _handleContinue() {
    if (_isSubmitting) return;
    setState(() => _isSubmitting = true);

    final provider = Provider.of<ProjectProvider>(context, listen: false);

    // Compute recsToSelect synchronously
    final dynamicActions = _dynamicActions(provider);
    final List<String> recsToSelect;
    if (dynamicActions.isNotEmpty) {
      final hasAnyRecommendationSelected = dynamicActions.any(
        (action) => _selectedActionIds.contains(action.id),
      );
      if (hasAnyRecommendationSelected) {
        recsToSelect = dynamicActions
            .where((a) => _selectedActionIds.contains(a.id))
            .map((a) => a.recommendation!)
            .toList();
      } else {
        recsToSelect = List<String>.from(provider.productRecommendations);
      }
    } else {
      recsToSelect = List<String>.from(provider.productRecommendations);
    }

    final needsColorSave =
        !_selectedActionIds.contains('color_palette') &&
        provider.colorPalette == null;
    final needsStyleSave =
        !_selectedActionIds.contains('design_style') &&
        provider.designStyle == null;

    // Navigate immediately — saves run behind the AnalyzingScreen.
    // _isSubmitting resets naturally when the widget tree rebuilds on navigation.
    widget.onImprove?.call(recsToSelect, needsColorSave, needsStyleSave);
  }

  void _handleNavTap(int index) {
    if (index == 2) return; // FAB position
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
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with logo
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
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
                ],
              ),
            ),

            // Main scrollable content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Text(
                      'Improvements.',
                      style: AppTheme.dmSans(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),

                    const SizedBox(height: 24),

                    // 3D Cube Image - centered
                    Center(
                      child: Container(
                        height: 170,
                        width: 170,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(24),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.08),
                              blurRadius: 20,
                              offset: const Offset(0, 8),
                            ),
                          ],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(24),
                          child: Image.asset(
                            'assets/images/choose_space/choose_office.png',
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) {
                              return Container(
                                color: AppTheme.scaffoldBackground,
                                child: const Center(
                                  child: Icon(
                                    IconsaxPlusLinear.home_2,
                                    size: 48,
                                    color: AppTheme.textTertiary,
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 32),

                    Consumer<ProjectProvider>(
                      builder: (context, provider, _) {
                        final loadingRecommendations =
                            provider.productRecommendations.isEmpty &&
                            provider.isRecommendationsLoading;
                        final loadingImageBackedSuggestions =
                            provider.productRecommendations.isNotEmpty &&
                            !provider.hasImageBackedSuggestions;
                        final loadingMessage = loadingRecommendations
                            ? 'Finding product recommendations in background...'
                            : provider.isSearchInFlight
                            ? 'Preparing live product images...'
                            : 'Waiting for image-ready product suggestions...';

                        return Column(
                          children: [
                            if (loadingRecommendations ||
                                loadingImageBackedSuggestions)
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(12),
                                margin: const EdgeInsets.only(bottom: 12),
                                decoration: BoxDecoration(
                                  color: AppTheme.scaffoldBackground,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: AppTheme.dividerColor,
                                    width: 1,
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    const SizedBox(
                                      width: 14,
                                      height: 14,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: AppTheme.primaryColor,
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        loadingMessage,
                                        style: AppTheme.dmSans(
                                          fontSize: 12,
                                          color: AppTheme.textSecondary,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ..._buildOptionsList(
                              provider: provider,
                              dynamicRecommendationsEnabled:
                                  provider.hasImageBackedSuggestions,
                            ),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),

            // Bottom CTA bar
            BottomCTABar(
              secondaryText: 'Back',
              onSecondaryPressed: widget.onBack ?? () => Navigator.pop(context),
              primaryText: _selectedActionIds.isEmpty ? 'Skip' : 'Improve',
              onPrimaryPressed: _isSubmitting ? null : _handleContinue,
              isLoading: _isSubmitting,
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

  List<Widget> _buildOptionsList({
    required ProjectProvider provider,
    required bool dynamicRecommendationsEnabled,
  }) {
    final items = [..._staticActions, ..._dynamicActions(provider)];
    return items.asMap().entries.map((entry) {
      final index = entry.key;
      final item = entry.value;
      final isSelected = _selectedActionIds.contains(item.id);
      final details = _selectionDetails[item.id];
      final isDynamicRecommendation = item.recommendation != null;
      final isTapEnabled =
          !isDynamicRecommendation || dynamicRecommendationsEnabled;

      return Padding(
        padding: EdgeInsets.only(bottom: index < items.length - 1 ? 12 : 24),
        child: _ImprovementRow(
          icon: item.icon,
          title: item.title,
          isSelected: isSelected,
          isEnabled: isTapEnabled,
          selectionDetails: details,
          onTap: isTapEnabled ? () => _handleCardTap(item) : null,
        ),
      );
    }).toList();
  }
}

class ColorPaletteSelectionScreen extends StatefulWidget {
  const ColorPaletteSelectionScreen({super.key});

  @override
  State<ColorPaletteSelectionScreen> createState() =>
      _ColorPaletteSelectionScreenState();
}

class _ColorPaletteSelectionScreenState
    extends State<ColorPaletteSelectionScreen> {
  String? _selectedPalette;
  bool _isSaving = false;

  // 2026 curated palettes + Let AI Decide
  final List<_PaletteOption> _palettes = const [
    _PaletteOption(
      id: 'ai_decide',
      name: 'Let AI Decide',
      description: 'AI picks the perfect colors for your space',
      colors: [],
      isAiOption: true,
    ),
    _PaletteOption(
      id: 'dopamine_pop',
      name: 'Dopamine Pop',
      description: 'Creative, bold personality — playful energy',
      colors: [
        Color(0xFFFF5C34),
        Color(0xFFD7EFFF),
        Color(0xFFE9F056),
        Color(0xFF351E28),
        Color(0xFFF6F6F2),
      ],
    ),
    _PaletteOption(
      id: 'dramatic_contrast',
      name: 'Dramatic Contrast',
      description: 'Bold, confident, luxe — editorial drama',
      colors: [
        Color(0xFF7A1E2C),
        Color(0xFF1F2A44),
        Color(0xFF2E2B2A),
        Color(0xFFF5E7D0),
        Color(0xFFB08D57),
      ],
    ),
    _PaletteOption(
      id: 'monochrome_modern',
      name: 'Monochrome Modern',
      description: 'Clean, structured — sleek architecture',
      colors: [
        Color(0xFFF2F2F2),
        Color(0xFF8E8E8E),
        Color(0xFF2E2E2E),
        Color(0xFF111111),
        Color(0xFFBFBFBF),
      ],
    ),
    _PaletteOption(
      id: 'pinterest_2026',
      name: 'Pinterest 2026',
      description: 'Bold + bright — 2026 Pinterest trending',
      colors: [
        Color(0xFFD7EFFF),
        Color(0xFFAEB8A0),
        Color(0xFF351E28),
        Color(0xFFE9F056),
        Color(0xFFFF5C34),
      ],
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedPalette = provider.colorPalette;
  }

  void _selectPalette(String id) {
    setState(() => _selectedPalette = _selectedPalette == id ? null : id);
  }

  Future<void> _handleContinue() async {
    if (_selectedPalette == null) {
      Navigator.pop(context);
      return;
    }

    final provider = Provider.of<ProjectProvider>(context, listen: false);
    final palette = _palettes.firstWhere((p) => p.id == _selectedPalette);

    setState(() => _isSaving = true);

    final bool success;
    if (palette.isAiOption) {
      // Let AI Decide — send empty colors with letAiDecide flag
      success = await provider.saveColorPalette(
        context,
        'ai_decide',
        'Let AI Decide',
        [],
        letAiDecide: true,
      );
    } else {
      final hexColors = palette.colors
          .map(
            (c) =>
                '#${c.toARGB32().toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}',
          )
          .toList();

      success = await provider.saveColorPalette(
        context,
        _selectedPalette!,
        palette.name,
        hexColors,
      );
    }

    if (!mounted) return;
    setState(() => _isSaving = false);

    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            provider.errorMessage ??
                'Failed to save color palette. Please try again.',
          ),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    Navigator.pop(context, {'id': _selectedPalette!, 'name': palette.name});
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
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with logo
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  Text(
                    'Spaces.',
                    style: AppTheme.dmSans(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
            ),

            // Title
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
              child: Text(
                'Choose Colors.',
                style: AppTheme.dmSans(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Palette list
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                itemCount: _palettes.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final palette = _palettes[index];
                  final isSelected = _selectedPalette == palette.id;
                  return _ColorPaletteRow(
                    palette: palette,
                    isSelected: isSelected,
                    onTap: () => _selectPalette(palette.id),
                    animateHint: palette.isAiOption && _selectedPalette == null,
                  );
                },
              ),
            ),

            // Bottom buttons
            BottomCTABar(
              secondaryText: 'Back',
              onSecondaryPressed: () => Navigator.pop(context),
              primaryText: 'Continue',
              onPrimaryPressed: _handleContinue,
              isLoading: _isSaving,
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

/// Row widget for color palette selection
class _ColorPaletteRow extends StatelessWidget {
  final _PaletteOption palette;
  final bool isSelected;
  final VoidCallback onTap;
  final bool animateHint;

  const _ColorPaletteRow({
    required this.palette,
    required this.isSelected,
    required this.onTap,
    this.animateHint = false,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBorderCard(
      isSelected: isSelected,
      animateWhenUnselected: animateHint,
      animateOnce: !palette.isAiOption,
      onTap: onTap,
      borderRadius: 14.0,
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          if (palette.isAiOption)
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Icon(
                  IconsaxPlusLinear.magic_star,
                  size: 28,
                  color: AppTheme.primaryColor,
                ),
              ),
            )
          else
            Row(
              mainAxisSize: MainAxisSize.min,
              children: palette.colors.take(5).map((color) {
                return Container(
                  width: 22,
                  height: 22,
                  margin: const EdgeInsets.only(right: 3),
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.black.withValues(alpha: 0.08),
                      width: 0.5,
                    ),
                  ),
                );
              }).toList(),
            ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  palette.name,
                  style: AppTheme.dmSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  palette.description,
                  style: AppTheme.dmSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w400,
                    color: AppTheme.textSecondary,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ImprovementCardData {
  final String id;
  final String title;
  final IconData icon;
  final String? recommendation;
  const _ImprovementCardData({
    required this.id,
    required this.title,
    required this.icon,
    this.recommendation,
  });
}

/// Row widget with icon + title + chevron and expandable details
class _ImprovementRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final bool isSelected;
  final bool isEnabled;
  final _SelectionDetails? selectionDetails;
  final VoidCallback? onTap;

  const _ImprovementRow({
    required this.icon,
    required this.title,
    required this.isSelected,
    this.isEnabled = true,
    required this.onTap,
    this.selectionDetails,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AnimatedOpacity(
          opacity: isEnabled ? 1.0 : 0.55,
          duration: const Duration(milliseconds: 180),
          child: AnimatedBorderCard(
            isSelected: isSelected,
            animateOnce: true,
            onTap: onTap ?? () {},
            borderRadius: 14.0,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Center(
                    child: Icon(icon, color: AppTheme.primaryColor, size: 20),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    title,
                    style: AppTheme.dmSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
                if (isEnabled)
                  Icon(
                    IconsaxPlusLinear.arrow_right_3,
                    color: AppTheme.textTertiary,
                    size: 20,
                  )
                else
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppTheme.primaryColor,
                    ),
                  ),
              ],
            ),
          ),
        ),
        if (isSelected && selectionDetails != null)
          Container(
            margin: const EdgeInsets.only(top: 8, left: 4, right: 4),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(12),
              border: Border(
                left: BorderSide(color: AppTheme.primaryColor, width: 3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  selectionDetails!.title,
                  style: AppTheme.dmSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  selectionDetails!.description,
                  style: AppTheme.dmSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w400,
                    color: AppTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _PaletteOption {
  final String id;
  final String name;
  final String description;
  final List<Color> colors;
  final bool isAiOption;
  const _PaletteOption({
    required this.id,
    required this.name,
    required this.description,
    required this.colors,
    this.isAiOption = false,
  });
}
