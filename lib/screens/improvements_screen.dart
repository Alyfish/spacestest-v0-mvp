import 'dart:math';

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
import '../widgets/icon_button.dart';
import 'design_style_selection_screen.dart';

class ImprovementsScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onImprove;

  const ImprovementsScreen({super.key, this.onBack, this.onImprove});

  @override
  State<ImprovementsScreen> createState() => _ImprovementsScreenState();
}

class _ImprovementsScreenState extends State<ImprovementsScreen> {
  final Set<String> _selectedActionIds = <String>{};

  final List<_ImprovementCardData> _staticActions = const [
    _ImprovementCardData(
      id: 'color_palette',
      title: 'color palette',
      assetPath: 'assets/images/improvements/imp_color_pallete.png',
      isStatic: true,
    ),
    _ImprovementCardData(
      id: 'design_style',
      title: 'design style',
      assetPath: 'assets/images/improvements/imp_design_style.png',
      isStatic: true,
    ),
  ];

  final List<_ImprovementCardData> _dynamicActions = <_ImprovementCardData>[];

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
          ..addAll(items
              .map((item) => _ImprovementCardData(
                    id: item['id'] as String,
                    title: item['title'] as String,
                    assetPath: item['assetPath'] as String,
                  )));
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Failed to load improvements. Please try again.';
      });
    }
  }

  Widget _buildHero() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Text(
        'Improvements',
        textAlign: TextAlign.left,
        style: TextStyle(
          fontFamily: AppTheme.primaryFont,
          fontSize: 40,
          color: AppTheme.primaryColor,
        ),
      ),
    );
  }

  void _handleCardTap(_ImprovementCardData data) {
    switch (data.id) {
      case 'color_palette':
        _openColorPalette();
        break;
      case 'design_style':
        _openDesignStyle();
        break;
      default:
        setState(() => _selectedActionIds.add(data.id));
    }
  }

  Future<void> _openColorPalette() async {
    final selected = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const ColorPaletteSelectionScreen()),
    );

    if (selected == true) {
      setState(() => _selectedActionIds.add('color_palette'));
    }
  }

  void _openDesignStyle() {
    showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
          ),
          child: DesignStyleSelectionContent(
            onBack: () => Navigator.pop(ctx, false),
            onSaved: () => Navigator.pop(ctx, true),
          ),
        );
      },
    ).then((selected) {
      if (selected == true) {
        setState(() => _selectedActionIds.add('design_style'));
      }
    });
  }

  void _handleImprove() {
    if (_selectedActionIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Select at least one improvement to continue',
            style: TextStyle(fontFamily: AppTheme.secondaryFont),
          ),
          backgroundColor: AppTheme.primaryColor,
        ),
      );
      return;
    }

    widget.onImprove?.call();
  }

  Widget _buildCard(_ImprovementCardData data, {bool isSelected = false}) {
    return InkWell(
      borderRadius: BorderRadius.circular(15),
      onTap: () => _handleCardTap(data),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 16),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.selectedCardBackground : Colors.white,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(
            color: isSelected
                ? AppTheme.selectedCardOutline
                : AppTheme.unselectedCardOutline,
            width: 3,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 4,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: data.assetPath.isNotEmpty
                  ? Image.asset(
                      data.assetPath,
                      width: 56,
                      height: 56,
                      fit: BoxFit.contain,
                    )
                  : Container(
                      width: 56,
                      height: 56,
                      color: AppTheme.grayColor.withValues(alpha: 0.12),
                      child: const Icon(IconsaxPlusLinear.image),
                    ),
            ),
            Expanded(
              child: Align(
                alignment: Alignment.center,
                child: Text(
                  data.title,
                  style: TextStyle(
                    fontFamily: AppTheme.secondaryFont,
                    fontSize: 20,
                    color: isSelected
                        ? AppTheme.primaryColor
                        : AppTheme.bodyTextColor,
                    fontWeight: FontWeight.w100,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            _error!,
            style: const TextStyle(
              fontFamily: AppTheme.secondaryFont,
              color: AppTheme.errorColor,
            ),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: _loadImprovementActions,
            child: const Text('Retry'),
          ),
        ],
      );
    }

    final cards = [..._staticActions, ..._dynamicActions];

    if (cards.isEmpty) {
      return const Center(child: Text('No improvements available'));
    }

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.only(top: 12.0),
            child: _buildHero(),
          ),
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: Image.asset(
                'assets/images/improvements/Improvements.png',
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 12),
          sliver: SliverList(
            delegate: SliverChildBuilderDelegate((context, index) {
              if (index.isOdd) {
                return const SizedBox(height: 14);
              }
              final data = cards[index ~/ 2];
              final isSelected = _selectedActionIds.contains(data.id);
              return _buildCard(data, isSelected: isSelected);
            }, childCount: cards.length * 2 - 1),
          ),
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 24),
            child: Row(
              children: [
                IconButtonWidget(
                  onPressed: widget.onBack ?? () => Navigator.pop(context),
                  icon: IconsaxPlusLinear.arrow_left_2,
                ),
                const SizedBox(width: 16),
                const Spacer(),
                CustomOutlinedButton(
                  text: 'Improve',
                  onPressed: _handleImprove,
                  icon: IconsaxPlusBold.arrow_right_3,
                  borderColor: AppTheme.primaryColor,
                  textColor: AppTheme.primaryColor,
                  iconColor: AppTheme.primaryColor,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(child: _buildContent());
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

  final List<_PaletteOption> _palettes = const [
    _PaletteOption(
      id: 'let_us_choose',
      name: 'Let us Choose',
      colors: [
        Color(0xFFA4553C),
        Color(0xFF3F5D59),
        Color(0xFF5B7A92),
        Color(0xFF7C99B8),
        Color(0xFFD7D7D7),
      ],
    ),
    _PaletteOption(
      id: 'deep_blues_a',
      name: 'Deep Blues',
      colors: [
        Color(0xFFB7CDB5),
        Color(0xFFD0A432),
        Color(0xFF7B92AD),
        Color(0xFF3F5E5C),
        Color(0xFFD7D7D7),
      ],
    ),
    _PaletteOption(
      id: 'greens',
      name: 'Greens',
      colors: [
        Color(0xFFA4553C),
        Color(0xFFB3C7A3),
        Color(0xFF4D746E),
        Color(0xFFD3D4D6),
        Color(0xFFC7A62D),
      ],
    ),
    _PaletteOption(
      id: 'high_reds_a',
      name: 'High Reds',
      colors: [
        Color(0xFF1F1F1F),
        Color(0xFF626E74),
        Color(0xFF4B0E14),
        Color(0xFF8C4A21),
        Color(0xFFD2D1CC),
      ],
    ),
    _PaletteOption(
      id: 'high_reds_b',
      name: 'High Reds',
      colors: [
        Color(0xFFA48C7D),
        Color(0xFFD6D1C9),
        Color(0xFFA26B3B),
        Color(0xFF70765F),
        Color(0xFF3C3C38),
      ],
    ),
    _PaletteOption(
      id: 'deep_blues_b',
      name: 'Deep Blues',
      colors: [
        Color(0xFFBCCEDB),
        Color(0xFFADB3B8),
        Color(0xFFD7D2CD),
        Color(0xFF5B7A92),
        Color(0xFFCAB1AB),
      ],
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedPalette = provider.colorPalette;
  }

  Future<void> _savePalette(String id) async {
    if (_isSaving) return;

    final provider = Provider.of<ProjectProvider>(context, listen: false);
    if (!provider.hasProject) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Create a project first'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final success = await provider.saveColorPalette(context, id);

    if (mounted) {
      setState(() {
        _isSaving = false;
        _selectedPalette = id;
      });

      if (success) {
        Navigator.pop(context, true);
      }
    }
  }

  Widget _buildPaletteCard(_PaletteOption option) {
    final isSelected = _selectedPalette == option.id;

    return LayoutBuilder(
      builder: (context, constraints) {
        const horizontalPadding = 8.0;
        const gap = 0.0;
        final swatchCount = option.colors.length;
        final availableWidth =
            constraints.maxWidth -
            (horizontalPadding * 2) -
            gap * (swatchCount - 1);
        final swatchWidth = (availableWidth / swatchCount).clamp(12.0, 48.0);

        return InkWell(
          borderRadius: BorderRadius.circular(26),
          onTap: () => _savePalette(option.id),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  vertical: 18,
                  horizontal: horizontalPadding,
                ),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(5),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 12,
                      offset: const Offset(0, 8),
                    ),
                  ],
                  border: Border.all(
                    color: isSelected
                        ? AppTheme.primaryColor.withValues(alpha: 0.4)
                        : Colors.transparent,
                    width: isSelected ? 2 : 0,
                  ),
                ),
                child: SizedBox(
                  height: 200,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: [
                      for (int i = 0; i < swatchCount; i++) ...[
                        Flexible(
                          child: _TexturedSwatch(
                            color: option.colors[i],
                            width: swatchWidth,
                            borderRadius: BorderRadius.circular(12),
                            seed: option.id.hashCode + i,
                          ),
                        ),
                        if (i != swatchCount - 1 && gap > 0)
                          SizedBox(width: gap),
                      ],
                    ],
                  ),
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    option.name,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: AppTheme.primaryFont,
                      fontSize: 22,
                      fontWeight: FontWeight.w400,
                      color: Colors.white,
                      shadows: const [
                        Shadow(
                          blurRadius: 8,
                          color: Colors.black54,
                          offset: Offset(0, 1),
                        ),
                      ],
                    ),
                  ),
                  if (isSelected) ...[
                    const SizedBox(height: 8),
                    const Icon(
                      IconsaxPlusLinear.tick_circle,
                      color: Colors.white,
                      size: 24,
                    ),
                  ],
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Stack(
          children: [
            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 80),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          'Choose Colors.',
                          style: const TextStyle(
                            fontFamily: AppTheme.primaryFont,
                            fontSize: 38,
                            fontWeight: FontWeight.w500,
                            color: AppTheme.primaryColor,
                          ),
                        ),
                      ),
                      OutlinedButton.icon(
                        onPressed: () {
                          setState(() => _selectedPalette = null);
                        },
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 10,
                          ),
                          side: BorderSide(
                            color: AppTheme.primaryColor.withValues(alpha: 0.8),
                            width: 1.4,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                        icon: const Icon(IconsaxPlusLinear.refresh, size: 18),
                        label: const Text(
                          'Clear All',
                          style: TextStyle(
                            fontFamily: AppTheme.secondaryFont,
                            fontSize: 14,
                            color: AppTheme.primaryColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _palettes.length,
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          mainAxisSpacing: 20,
                          crossAxisSpacing: 16,
                          childAspectRatio: 0.78,
                        ),
                    itemBuilder: (context, index) =>
                        _buildPaletteCard(_palettes[index]),
                  ),
                ],
              ),
            ),
            Positioned(
              left: 16,
              bottom: 16,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.all(12),
                  shape: const CircleBorder(),
                  side: BorderSide(
                    color: AppTheme.primaryColor.withValues(alpha: 0.8),
                    width: 1.4,
                  ),
                ),
                onPressed: () => Navigator.pop(context),
                child: const Icon(
                  IconsaxPlusLinear.arrow_left_2,
                  color: AppTheme.primaryColor,
                  size: 22,
                ),
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
  final String assetPath;
  final bool isStatic;

  const _ImprovementCardData({
    required this.id,
    required this.title,
    required this.assetPath,
    this.isStatic = false,
  });
}

class _PaletteOption {
  final String id;
  final String name;
  final List<Color> colors;

  const _PaletteOption({
    required this.id,
    required this.name,
    required this.colors,
  });
}

class _Badge extends StatelessWidget {
  final String label;

  const _Badge({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          color: Colors.white,
        ),
      ),
    );
  }
}

class _TexturedSwatch extends StatelessWidget {
  final Color color;
  final double width;
  final BorderRadius borderRadius;
  final int seed;

  const _TexturedSwatch({
    required this.color,
    required this.width,
    required this.borderRadius,
    required this.seed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: double.infinity,
      child: ClipRRect(
        borderRadius: borderRadius,
        child: Stack(
          fit: StackFit.expand,
          children: [
            ColoredBox(color: color),
            CustomPaint(painter: _NoisePainter(seed: seed)),
          ],
        ),
      ),
    );
  }
}

class _NoisePainter extends CustomPainter {
  final int seed;

  _NoisePainter({required this.seed});

  @override
  void paint(Canvas canvas, Size size) {
    final rnd = Random(seed);
    final paintLight = Paint()
      ..color = Colors.white.withValues(alpha: 0.08)
      ..style = PaintingStyle.fill;
    final paintDark = Paint()
      ..color = Colors.black.withValues(alpha: 0.05)
      ..style = PaintingStyle.fill;

    const dotCount = 220;
    for (int i = 0; i < dotCount; i++) {
      final dx = rnd.nextDouble() * size.width;
      final dy = rnd.nextDouble() * size.height;
      final radius = 0.45 + rnd.nextDouble() * 0.9;
      canvas.drawCircle(
        Offset(dx, dy),
        radius,
        i.isEven ? paintLight : paintDark,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _NoisePainter oldDelegate) =>
      oldDelegate.seed != seed;
}
