import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/animated_border_card.dart';
import '../widgets/app_bottom_nav_bar.dart';
import '../widgets/bottom_cta_bar.dart';
import 'main_navigation_screen.dart';

/// Full-screen design style selection (new design)
class ChooseStyleScreen extends StatefulWidget {
  const ChooseStyleScreen({super.key});

  @override
  State<ChooseStyleScreen> createState() => _ChooseStyleScreenState();
}

class _ChooseStyleScreenState extends State<ChooseStyleScreen> {
  String? _selectedStyle;

  final List<_DesignStyleOption> _styles = const [
    _DesignStyleOption(
      id: 'ai_decide',
      name: 'Let AI Decide',
      description: 'AI picks the perfect style for your space',
      imagePath: '',
      isAiOption: true,
    ),
    _DesignStyleOption(
      id: 'bohemian',
      name: 'Bohemian',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_bohemian.png',
    ),
    _DesignStyleOption(
      id: 'scandinavian',
      name: 'Scandinavian',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_scandinavian.png',
    ),
    _DesignStyleOption(
      id: 'contemporary',
      name: 'Contemporary',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_contemporary_dark.png',
    ),
    _DesignStyleOption(
      id: 'coastal',
      name: 'Coastal',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_coastal.png',
    ),
    _DesignStyleOption(
      id: 'modern',
      name: 'Modern',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_modern_dark.png',
    ),
    _DesignStyleOption(
      id: 'art_deco',
      name: 'Art Deco',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_art_deco.png',
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedStyle = provider.designStyle;
  }

  void _selectStyle(String id) {
    setState(() => _selectedStyle = _selectedStyle == id ? null : id);
  }

  void _handleContinue() {
    if (_selectedStyle == null) {
      Navigator.pop(context);
      return;
    }

    final style = _styles.firstWhere((s) => s.id == _selectedStyle);

    if (style.isAiOption) {
      Navigator.pop<Map<String, dynamic>>(context, {
        'id': 'ai_decide',
        'name': 'Let AI Decide',
        'letAiDecide': true,
      });
    } else {
      Navigator.pop<Map<String, dynamic>>(context, {
        'id': _selectedStyle!,
        'name': style.name,
        'letAiDecide': false,
      });
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
                'Choose Style.',
                style: AppTheme.dmSans(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Style list
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                itemCount: _styles.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final style = _styles[index];
                  final isSelected = _selectedStyle == style.id;
                  return _DesignStyleRow(
                    style: style,
                    isSelected: isSelected,
                    onTap: () => _selectStyle(style.id),
                    animateHint: style.isAiOption && _selectedStyle == null,
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

/// Row widget for design style selection
class _DesignStyleRow extends StatelessWidget {
  final _DesignStyleOption style;
  final bool isSelected;
  final VoidCallback onTap;
  final bool animateHint;

  const _DesignStyleRow({
    required this.style,
    required this.isSelected,
    required this.onTap,
    this.animateHint = false,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBorderCard(
      isSelected: isSelected,
      animateWhenUnselected: animateHint,
      animateOnce: !style.isAiOption,
      onTap: onTap,
      borderRadius: 14.0,
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          if (style.isAiOption)
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
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.08),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.asset(
                  style.imagePath,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: AppTheme.scaffoldBackground,
                      child: const Center(
                        child: Icon(
                          IconsaxPlusLinear.home_2,
                          size: 24,
                          color: AppTheme.textTertiary,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  style.name,
                  style: AppTheme.dmSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  style.description,
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

class _DesignStyleOption {
  final String id;
  final String name;
  final String description;
  final String imagePath;
  final bool isAiOption;

  const _DesignStyleOption({
    required this.id,
    required this.name,
    required this.description,
    required this.imagePath,
    this.isAiOption = false,
  });
}

// Keep legacy classes for backward compatibility
class DesignStyleSelectionScreen extends StatelessWidget {
  const DesignStyleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const ChooseStyleScreen();
  }
}

class DesignStyleSelectionContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onSavedSimple;
  final void Function(String id, String name)? onSaved;

  const DesignStyleSelectionContent({
    super.key,
    this.onBack,
    this.onSaved,
    this.onSavedSimple,
  });

  @override
  State<DesignStyleSelectionContent> createState() =>
      _DesignStyleSelectionContentState();
}

class _DesignStyleSelectionContentState
    extends State<DesignStyleSelectionContent> {
  String? _selectedStyle;
  bool _isSaving = false;

  final List<_DesignStyleOption> _styles = const [
    _DesignStyleOption(
      id: 'ai_decide',
      name: 'Let AI Decide',
      description: 'AI picks the perfect style for your space',
      imagePath: '',
      isAiOption: true,
    ),
    _DesignStyleOption(
      id: 'bohemian',
      name: 'Bohemian',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_bohemian.png',
    ),
    _DesignStyleOption(
      id: 'scandinavian',
      name: 'Scandinavian',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_scandinavian.png',
    ),
    _DesignStyleOption(
      id: 'contemporary',
      name: 'Contemporary',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_contemporary_dark.png',
    ),
    _DesignStyleOption(
      id: 'coastal',
      name: 'Coastal',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_coastal.png',
    ),
    _DesignStyleOption(
      id: 'modern',
      name: 'Modern',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_modern_dark.png',
    ),
    _DesignStyleOption(
      id: 'art_deco',
      name: 'Art Deco',
      description:
          'Inviting shades of beige, terracotta, and for a cozy atmos.',
      imagePath: 'assets/images/choose_style/style_art_deco.png',
    ),
  ];

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedStyle = provider.designStyle;
  }

  void _selectStyle(String id) {
    setState(() => _selectedStyle = _selectedStyle == id ? null : id);
  }

  Future<void> _handleContinue() async {
    if (_selectedStyle == null) {
      widget.onBack?.call();
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

    final style = _styles.firstWhere((s) => s.id == _selectedStyle);

    if (style.isAiOption) {
      // Let AI Decide — send with letAiDecide flag
      setState(() => _isSaving = true);
      final success = await provider.saveDesignStyle(
        context,
        'ai_decide',
        'Let AI Decide',
        letAiDecide: true,
      );

      if (mounted) {
        setState(() => _isSaving = false);
        if (success) {
          if (widget.onSaved != null) {
            widget.onSaved!('ai_decide', 'Let AI Decide');
          } else if (widget.onSavedSimple != null) {
            widget.onSavedSimple!();
          }
        }
      }
    } else {
      setState(() => _isSaving = true);
      final success = await provider.saveDesignStyle(
        context,
        _selectedStyle!,
        style.name,
      );

      if (mounted) {
        setState(() => _isSaving = false);
        if (success) {
          if (widget.onSaved != null) {
            widget.onSaved!(_selectedStyle!, style.name);
          } else if (widget.onSavedSimple != null) {
            widget.onSavedSimple!();
          }
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Title
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
          child: Text(
            'Choose Style.',
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Style list (limited height for bottom sheet)
        SizedBox(
          height: 400,
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            itemCount: _styles.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final style = _styles[index];
              final isSelected = _selectedStyle == style.id;
              return _DesignStyleRow(
                style: style,
                isSelected: isSelected,
                onTap: () => _selectStyle(style.id),
              );
            },
          ),
        ),

        // Bottom buttons
        BottomCTABar(
          secondaryText: 'Back',
          onSecondaryPressed: widget.onBack,
          primaryText: 'Continue',
          onPrimaryPressed: _handleContinue,
          isLoading: _isSaving,
        ),
      ],
    );
  }
}
