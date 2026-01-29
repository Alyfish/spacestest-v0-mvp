import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
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

class ImprovementsScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onImprove;

  const ImprovementsScreen({super.key, this.onBack, this.onImprove});

  @override
  State<ImprovementsScreen> createState() => _ImprovementsScreenState();
}

class _ImprovementsScreenState extends State<ImprovementsScreen> {
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
  final List<_ImprovementCardData> _dynamicActions = [];
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadImprovementActions();
  }

  Future<void> _loadImprovementActions() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final items = await ApiService.fetchImprovementActions();
      setState(() {
        _dynamicActions
          ..clear()
          ..addAll(items.map((item) => _ImprovementCardData(
                id: item['id'] as String,
                title: item['title'] as String,
                icon: _getIconForAction(item['id'] as String),
              )));
      });
    } catch (e) {
      setState(() => _error = 'Failed to load improvements');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  IconData _getIconForAction(String id) {
    switch (id) {
      case 'add_vase':
      case 'change_vase':
        return IconsaxPlusLinear.lovely;
      case 'add_sofa':
      case 'change_sofa':
        return IconsaxPlusLinear.lamp_on;
      default:
        return IconsaxPlusLinear.add_circle;
    }
  }

  void _handleCardTap(_ImprovementCardData data) {
    if (data.id == 'color_palette') {
      _openColorPalette();
    } else if (data.id == 'design_style') {
      _openDesignStyle();
    } else if (data.id.contains('vase')) {
      _openLikeThese('vase', data.id, data.title);
    } else if (data.id.contains('sofa')) {
      _openLikeThese('sofa', data.id, data.title);
    } else {
      setState(() => _selectedActionIds.add(data.id));
    }
  }

  Future<void> _openLikeThese(String itemType, String actionId, String title) async {
    final result = await Navigator.push<Map<String, dynamic>?>(
      context,
      MaterialPageRoute(
        builder: (_) => LikeTheseScreen(
          itemType: itemType,
          actionId: actionId,
        ),
      ),
    );
    if (result != null && result['selectedItems'] != null) {
      final selectedItems = result['selectedItems'] as List;
      if (selectedItems.isNotEmpty) {
        final firstItem = selectedItems.first as Map<String, dynamic>;
        setState(() {
          _selectedActionIds.add(actionId);
          _selectionDetails[actionId] = _SelectionDetails(
            title: firstItem['name'] ?? title,
            description: '${selectedItems.length} item${selectedItems.length > 1 ? 's' : ''} selected from ${firstItem['retailer']}',
          );
        });
      }
    }
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
          description: 'Inviting shades of beige, terracotta, and for a cozy atmos.',
        );
      });
    }
  }

  void _handleContinue() {
    widget.onImprove?.call();
  }

  void _openSettings() {
    // Navigate to settings - placeholder for now
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Settings coming soon')),
    );
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

                    // Improvement options list
                    if (_isLoading)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(32),
                          child: CircularProgressIndicator(
                            color: AppTheme.primaryColor,
                          ),
                        ),
                      )
                    else if (_error != null)
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.all(32),
                          child: Column(
                            children: [
                              Text(_error!,
                                  style: AppTheme.bodyStyle(
                                      color: AppTheme.textSecondary)),
                              const SizedBox(height: 12),
                              TextButton(
                                onPressed: _loadImprovementActions,
                                child: const Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    else
                      ..._buildOptionsList(),
                  ],
                ),
              ),
            ),

            // Bottom CTA bar
            BottomCTABar(
              secondaryText: 'Back',
              onSecondaryPressed: widget.onBack ?? () => Navigator.pop(context),
              primaryText: _selectedActionIds.isEmpty ? 'Skip' : 'Improve',
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

  List<Widget> _buildOptionsList() {
    final items = [..._staticActions, ..._dynamicActions];
    return items.asMap().entries.map((entry) {
      final index = entry.key;
      final item = entry.value;
      final isSelected = _selectedActionIds.contains(item.id);
      final details = _selectionDetails[item.id];

      return Padding(
        padding: EdgeInsets.only(bottom: index < items.length - 1 ? 12 : 24),
        child: _ImprovementRow(
          icon: item.icon,
          title: item.title,
          isSelected: isSelected,
          selectionDetails: details,
          onTap: () => _handleCardTap(item),
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

  // Updated palettes with 6 colors and descriptions
  final List<_PaletteOption> _palettes = const [
    _PaletteOption(
      id: 'warm_cozy',
      name: 'Warm and Cozy',
      description: 'Inviting shades of beige, terracotta, and for a cozy atmos.',
      colors: [
        Color(0xFFD4C4B0), // beige
        Color(0xFFE8A87C), // orange
        Color(0xFFF5E6D3), // cream
        Color(0xFFC9B896), // tan
        Color(0xFFD35D4E), // terracotta
        Color(0xFFF0E4D7), // light cream
      ],
    ),
    _PaletteOption(
      id: 'modern_minimal',
      name: 'Modern Minimal',
      description: 'Unselected items remain unchanged in your design',
      colors: [
        Color(0xFF9DB17C), // sage green
        Color(0xFFC5D86D), // lime
        Color(0xFFF5E6D3), // cream
        Color(0xFFE8A87C), // orange
        Color(0xFFD35D4E), // orange-red
        Color(0xFFF0E4D7), // cream
      ],
    ),
    _PaletteOption(
      id: 'cool_calm',
      name: 'Cool and Calm',
      description: 'Unselected items remain unchanged in your design',
      colors: [
        Color(0xFF7BA3C9), // blue
        Color(0xFF8FBC8F), // green
        Color(0xFFF5E6D3), // cream
        Color(0xFFE8A87C), // orange
        Color(0xFFE8B4B8), // pink
        Color(0xFFF0E4D7), // cream
      ],
    ),
    _PaletteOption(
      id: 'earthy_natural',
      name: 'Earthy & Natural',
      description: 'Unselected items remain unchanged in your design',
      colors: [
        Color(0xFFCBA6C3), // mauve
        Color(0xFFE8A87C), // orange
        Color(0xFFC9B896), // tan
        Color(0xFF8FBC8F), // green
        Color(0xFF5F9EA0), // teal
        Color(0xFF7BA3C9), // blue
      ],
    ),
    _PaletteOption(
      id: 'vibrant',
      name: 'Vibrant',
      description: 'Unselected items remain unchanged in your design',
      colors: [
        Color(0xFFF8D7DA), // light pink
        Color(0xFFE8A87C), // orange
        Color(0xFFF5E6D3), // cream
        Color(0xFFD8BFD8), // lavender
        Color(0xFFE8B4B8), // pink
        Color(0xFFF0E4D7), // cream
      ],
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedPalette = provider.colorPalette;
  }

  void _clearSelection() {
    setState(() => _selectedPalette = null);
  }

  void _selectPalette(String id) {
    setState(() => _selectedPalette = id);
  }

  Future<void> _handleContinue() async {
    if (_selectedPalette == null) {
      Navigator.pop(context);
      return;
    }

    setState(() => _isSaving = true);
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    final success = await provider.saveColorPalette(context, _selectedPalette!);

    if (mounted) {
      setState(() => _isSaving = false);
      if (success) {
        final palette = _palettes.firstWhere((p) => p.id == _selectedPalette);
        Navigator.pop(context, {'id': _selectedPalette!, 'name': palette.name});
      }
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
                  Text(
                    'Spaces.',
                    style: AppTheme.dmSans(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  GestureDetector(
                    onTap: () {},
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceColor,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.dividerColor),
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

            // Title row with Clear All
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Choose Colors.',
                    style: AppTheme.dmSans(
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  GestureDetector(
                    onTap: _clearSelection,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.textPrimary,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        'Clear All',
                        style: AppTheme.dmSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ],
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

  const _ColorPaletteRow({
    required this.palette,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          border: Border.all(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
            width: isSelected ? 1.5 : 1,
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            // Color swatches grid (2 rows × 3 columns)
            SizedBox(
              width: 72,
              height: 48,
              child: Column(
                children: [
                  // Top row of colors
                  Row(
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: palette.colors.take(3).map((color) {
                      return Container(
                        width: 20,
                        height: 20,
                        margin: const EdgeInsets.only(right: 4),
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 4),
                  // Bottom row of colors
                  Row(
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: palette.colors.skip(3).take(3).map((color) {
                      return Container(
                        width: 20,
                        height: 20,
                        margin: const EdgeInsets.only(right: 4),
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            // Name and description
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
      ),
    );
  }
}

class _ImprovementCardData {
  final String id;
  final String title;
  final IconData icon;
  const _ImprovementCardData(
      {required this.id, required this.title, required this.icon});
}

/// Row widget with icon + title + chevron and expandable details
class _ImprovementRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final bool isSelected;
  final _SelectionDetails? selectionDetails;
  final VoidCallback onTap;

  const _ImprovementRow({
    required this.icon,
    required this.title,
    required this.isSelected,
    required this.onTap,
    this.selectionDetails,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header Row (always visible)
        GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: AppTheme.surfaceColor,
              border: Border.all(
                color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
                width: isSelected ? 1.5 : 1,
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                // Icon container
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Center(
                    child: Icon(
                      icon,
                      color: AppTheme.primaryColor,
                      size: 20,
                    ),
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
                Icon(
                  IconsaxPlusLinear.arrow_right_3,
                  color: AppTheme.textTertiary,
                  size: 20,
                ),
              ],
            ),
          ),
        ),
        // Expanded Detail (only when selected)
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
  const _PaletteOption({
    required this.id,
    required this.name,
    required this.description,
    required this.colors,
  });
}
