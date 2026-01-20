import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
import '../widgets/icon_button.dart';

class DesignStyleSelectionScreen extends StatelessWidget {
  const DesignStyleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: DesignStyleSelectionContent(
        onBack: () => Navigator.pop(context, false),
        onSaved: () => Navigator.pop(context, true),
      ),
    );
  }
}

class DesignStyleSelectionContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSaved;

  const DesignStyleSelectionContent({super.key, this.onBack, this.onSaved});

  @override
  State<DesignStyleSelectionContent> createState() =>
      _DesignStyleSelectionContentState();
}

class _DesignStyleSelectionContentState
    extends State<DesignStyleSelectionContent> {
  String? _selectedStyle;
  bool _isSaving = false;
  late final PageController _pageController;
  int _currentPage = 0;

  late final List<List<_DesignStyleOption>> _pages;

  final List<_DesignStyleOption> _styles = const [
    _DesignStyleOption(
      id: 'bohemian',
      name: 'bohemian',
      imagePath: 'assets/images/choose_style/style_bohemian.png',
      accentColor: Color(0xFFA00534),
    ),
    _DesignStyleOption(
      id: 'scandinavian',
      name: 'scandinavian',
      imagePath: 'assets/images/choose_style/style_scandinavian.png',
      accentColor: Color(0xFF3F5870),
    ),
    _DesignStyleOption(
      id: 'contemporary_dark',
      name: 'contemporary',
      imagePath: 'assets/images/choose_style/style_contemporary_dark.png',
      accentColor: Color(0xFF8C1C1C),
    ),
    _DesignStyleOption(
      id: 'coastal',
      name: 'coastal',
      imagePath: 'assets/images/choose_style/style_coastal.png',
      accentColor: Color.fromARGB(255, 162, 133, 84),
    ),
    _DesignStyleOption(
      id: 'modern_dark',
      name: 'modern',
      imagePath: 'assets/images/choose_style/style_modern_dark.png',
      accentColor: Color(0xFF2F2F2F),
    ),
    _DesignStyleOption(
      id: 'art_deco',
      name: 'art deco',
      imagePath: 'assets/images/choose_style/style_art_deco.png',
      accentColor: Color(0xFF0C3D37),
    ),
    _DesignStyleOption(
      id: 'contemporary_light',
      name: 'contemporary soft',
      imagePath: 'assets/images/choose_style/style_contemporary_light.png',
      accentColor: Color(0xFFB4833E),
    ),
    _DesignStyleOption(
      id: 'modern_light',
      name: 'modern warm',
      imagePath: 'assets/images/choose_style/style_modern_light.png',
      accentColor: Color(0xFFD38D2F),
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedStyle = provider.designStyle;

    _pageController = PageController();
    _pages = [];
    for (int i = 0; i < _styles.length; i += 4) {
      final end = math.min(i + 4, _styles.length);
      _pages.add(_styles.sublist(i, end));
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _handleCardTap(String id) {
    setState(() {
      _selectedStyle = id;
    });
  }

  Future<void> _handleContinue() async {
    if (_selectedStyle == null || _isSaving) {
      return;
    }

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

    final success = await provider.saveDesignStyle(context, _selectedStyle!);

    if (mounted) {
      setState(() {
        _isSaving = false;
      });

      if (success) {
        if (widget.onSaved != null) {
          widget.onSaved!();
        } else {
          Navigator.pop(context, true);
        }
      }
    }
  }

  Widget _buildStyleCard(_DesignStyleOption option) {
    final isSelected = option.id == _selectedStyle;

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () => _handleCardTap(option.id),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isSelected
                ? option.accentColor
                : AppTheme.unselectedCardOutline,
            width: isSelected ? 2 : 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 10,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Image.asset(
                  option.imagePath,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Center(
                      child: Icon(
                        IconsaxPlusLinear.gallery,
                        size: 32,
                        color: AppTheme.grayColor.withValues(alpha: 0.6),
                      ),
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 10),
            Align(
              alignment: AlignmentGeometry.center,
              child: Text(
                option.name,
                style: TextStyle(
                  fontFamily: AppTheme.secondaryFont,
                  fontSize: 16,
                  fontWeight: FontWeight.w100,
                  color: AppTheme.bodyTextColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 36),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final cardWidth = (constraints.maxWidth - 14) / 2;
          final cardHeight = cardWidth / 0.9;
          final gridHeight = (cardHeight * 2) + 18;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Choose Style.', style: AppTheme.sectionTitleStyle),
              const SizedBox(height: 14),
              SizedBox(
                height: gridHeight.clamp(320, 560),
                child: PageView.builder(
                  controller: _pageController,
                  itemCount: _pages.length,
                  onPageChanged: (index) {
                    setState(() => _currentPage = index);
                  },
                  itemBuilder: (context, pageIndex) {
                    final pageItems = _pages[pageIndex];
                    return GridView.builder(
                      padding: EdgeInsets.zero,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            mainAxisSpacing: 18,
                            crossAxisSpacing: 14,
                            childAspectRatio: 0.9,
                          ),
                      itemCount: pageItems.length,
                      itemBuilder: (context, index) =>
                          _buildStyleCard(pageItems[index]),
                    );
                  },
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  _pages.length,
                  (index) => Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: _currentPage == index ? 12 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _currentPage == index
                          ? AppTheme.primaryColor
                          : AppTheme.grayColor.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButtonWidget(
                    icon: IconsaxPlusLinear.arrow_left_2,
                    onPressed: widget.onBack ?? () => Navigator.pop(context),
                  ),
                  const SizedBox(width: 16),
                  CustomOutlinedButton(
                    text: _isSaving ? 'Saving...' : 'Continue',
                    onPressed: _selectedStyle == null ? () {} : _handleContinue,
                    textColor: AppTheme.bodyTextColor,
                    borderColor: AppTheme.primaryColor,
                    iconColor: AppTheme.primaryColor,
                    icon: IconsaxPlusLinear.arrow_right_2,
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _DesignStyleOption {
  final String id;
  final String name;
  final String imagePath;
  final Color accentColor;

  const _DesignStyleOption({
    required this.id,
    required this.name,
    required this.imagePath,
    required this.accentColor,
  });
}
