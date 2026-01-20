import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
import '../widgets/icon_button.dart';

class ChooseApproachScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseApproachScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundColor,
        elevation: 0,
        toolbarHeight: 70,
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10.0),
              child: Image.asset(
                'assets/logo/logo.png',
                height: 100,
                width: 100,
              ),
            ),
          ],
        ),
      ),
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: ChooseApproachContent(onBack: onBack, onContinue: onContinue),
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.backgroundColor,
        selectedItemColor: AppTheme.primaryColor,
        unselectedItemColor: AppTheme.grayColor,
        selectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
        unselectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w400,
        ),
        currentIndex: 0,
        onTap: (_) {},
        items: const [
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.home),
            activeIcon: Icon(IconsaxPlusBold.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.discover),
            activeIcon: Icon(IconsaxPlusBold.discover),
            label: 'Discover',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bag_2),
            activeIcon: Icon(IconsaxPlusBold.bag_2),
            label: 'Cart',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bookmark),
            activeIcon: Icon(IconsaxPlusBold.bookmark),
            label: 'Saved',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.profile_circle),
            activeIcon: Icon(IconsaxPlusBold.profile_circle),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}

class ChooseApproachContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseApproachContent({super.key, this.onBack, this.onContinue});

  @override
  State<ChooseApproachContent> createState() => _ChooseApproachContentState();
}

class _ChooseApproachContentState extends State<ChooseApproachContent> {
  String? _selectedApproach;
  bool _isSaving = false;

  final List<_ApproachOption> _options = const [
    _ApproachOption(
      id: 'iterative',
      title: 'Iterative Improvement.',
      icon: IconsaxPlusLinear.refresh,
      activeColor: AppTheme.primaryColor,
      iconBackground: Color(0xFFF6D3DD),
    ),
    _ApproachOption(
      id: 'revamp',
      title: 'Complete Revamp.',
      icon: IconsaxPlusLinear.magicpen,
      activeColor: Color(0xFF00A651),
      iconBackground: Color(0xFFDDF4E5),
    ),
  ];

  @override
  void initState() {
    super.initState();
    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    _selectedApproach = projectProvider.approach;
  }

  Future<void> _handleContinue() async {
    if (_selectedApproach == null || _isSaving) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    if (!projectProvider.hasProject) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Create a project before choosing an approach'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final success = await projectProvider.saveApproach(
      context,
      _selectedApproach!,
    );

    if (mounted) {
      setState(() {
        _isSaving = false;
      });

      if (success && widget.onContinue != null) {
        widget.onContinue!();
      }
    }
  }

  void _onOptionTap(String id) {
    setState(() {
      _selectedApproach = id;
    });
  }

  Widget _buildImage(ProjectProvider provider) {
    final imageProvider =
        provider.getProjectImageProvider() ??
        provider.getInspirationImageProvider();

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: Container(
        width: double.infinity,
        height: MediaQuery.of(context).size.height * 0.36,
        decoration: BoxDecoration(
          color: AppTheme.grayColor.withValues(alpha: 0.15),
        ),
        child: imageProvider != null
            ? Image(image: imageProvider, fit: BoxFit.cover)
            : const Center(
                child: Icon(
                  IconsaxPlusLinear.image,
                  size: 48,
                  color: AppTheme.grayColor,
                ),
              ),
      ),
    );
  }

  Widget _buildOption(_ApproachOption option) {
    final isSelected = _selectedApproach == option.id;

    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () => _onOptionTap(option.id),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: isSelected
                ? option.activeColor
                : AppTheme.unselectedCardOutline,
            width: isSelected ? 2 : 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: option.iconBackground,
                shape: BoxShape.circle,
              ),
              child: Icon(option.icon, size: 18, color: option.activeColor),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                option.title,
                style: TextStyle(
                  fontFamily: AppTheme.secondaryFont,
                  fontSize: 16,
                  fontWeight: FontWeight.w400,
                  color: AppTheme.bodyTextColor,
                ),
              ),
            ),
            Icon(
              IconsaxPlusLinear.arrow_right_2,
              size: 20,
              color: isSelected ? option.activeColor : AppTheme.grayColor,
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
      child: Consumer<ProjectProvider>(
        builder: (context, provider, _) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Choose Approach.', style: AppTheme.sectionTitleStyle),
              const SizedBox(height: 12),
              _buildImage(provider),
              const SizedBox(height: 16),
              ..._options.map(
                (opt) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildOption(opt),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButtonWidget(
                    onPressed: widget.onBack ?? () => Navigator.pop(context),
                    icon: IconsaxPlusLinear.arrow_left_2,
                  ),
                  const SizedBox(width: 16),
                  CustomOutlinedButton(
                    text: _isSaving ? 'Saving...' : 'Continue',
                    icon: IconsaxPlusLinear.arrow_right_2,
                    onPressed: _selectedApproach == null || _isSaving
                        ? () {}
                        : _handleContinue,
                    textColor: AppTheme.bodyTextColor,
                    borderColor: AppTheme.primaryColor,
                    iconColor: AppTheme.primaryColor,
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

class _ApproachOption {
  final String id;
  final String title;
  final IconData icon;
  final Color activeColor;
  final Color iconBackground;

  const _ApproachOption({
    required this.id,
    required this.title,
    required this.icon,
    required this.activeColor,
    required this.iconBackground,
  });
}
