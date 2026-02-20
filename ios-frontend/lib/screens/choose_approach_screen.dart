import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/animated_border_card.dart';
import '../widgets/step_progress_bar.dart';

class ChooseApproachScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseApproachScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: ChooseApproachContent(onBack: onBack, onContinue: onContinue),
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
        SnackBar(
          content: Text(
            'Create a project first',
            style: AppTheme.dmSans(color: Colors.white),
          ),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);
    final success = await projectProvider.saveApproach(
      context,
      _selectedApproach!,
    );

    if (mounted) {
      setState(() => _isSaving = false);
      if (success) widget.onContinue?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with logo
        _buildHeader(),

        // Progress bar
        const SizedBox(height: 8),
        const StepProgressBar(currentStep: 5, totalSteps: 8),

        // Content
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 520),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildDecisionHero(),
                          const SizedBox(height: 18),

                          _buildApproachOption(
                            id: 'inspiration',
                            icon: IconsaxPlusLinear.gallery,
                            title: 'Generate with Inspiration',
                            description:
                                'Upload a reference image and match your room to that style.',
                            modeTag: 'Style Match',
                          ),
                          const SizedBox(height: 12),
                          _buildApproachOption(
                            id: 'complete_revamp',
                            icon: IconsaxPlusLinear.magic_star,
                            title: 'Complete Revamp',
                            description:
                                'Fresh start with new layout, palette, and decor.',
                            modeTag: 'Most Creative',
                          ),
                          const SizedBox(height: 12),
                          _buildApproachOption(
                            id: 'iterative',
                            icon: IconsaxPlusLinear.home_2,
                            title: 'Iterative Improvement',
                            description: 'Keep your layout, upgrade key areas.',
                            modeTag: 'Quick Win',
                            isRecommended: true,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),

        // Bottom Buttons
        _buildBottomButtons(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          // Spaces. logo
          Image.asset('assets/logo/logo.png', height: 32),
        ],
      ),
    );
  }

  Widget _buildDecisionHero() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Column(
        children: [
          Text(
            'Choose Your Approach.',
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 6),
          Text(
            'Choose your redesign direction.',
            style: AppTheme.dmSans(
              fontSize: 14,
              color: AppTheme.textSecondary,
              height: 1.35,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildApproachOption({
    required String id,
    required IconData icon,
    required String title,
    required String description,
    required String modeTag,
    bool isRecommended = false,
  }) {
    final isSelected = _selectedApproach == id;

    return AnimatedBorderCard(
      isSelected: isSelected,
      animateWhenUnselected: _selectedApproach == null,
      onTap: () => setState(() => _selectedApproach = id),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: isSelected
                      ? AppTheme.primaryColor.withValues(alpha: 0.12)
                      : AppTheme.scaffoldBackground,
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(
                  icon,
                  size: 20,
                  color: isSelected
                      ? AppTheme.primaryColor
                      : AppTheme.textSecondary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _buildModeTag(text: modeTag, highlight: isSelected),
                    if (isRecommended)
                      _buildModeTag(text: 'Recommended', highlight: true),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            title,
            style: AppTheme.dmSans(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            description,
            style: AppTheme.dmSans(
              fontSize: 13,
              fontWeight: FontWeight.w400,
              color: AppTheme.textSecondary,
              height: 1.34,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeTag({required String text, required bool highlight}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: highlight
            ? AppTheme.primaryColor.withValues(alpha: 0.10)
            : AppTheme.scaffoldBackground,
        borderRadius: BorderRadius.circular(99),
        border: Border.all(
          color: highlight
              ? AppTheme.primaryColor.withValues(alpha: 0.3)
              : AppTheme.dividerColor,
        ),
      ),
      child: Text(
        text,
        style: AppTheme.dmSans(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: highlight ? AppTheme.primaryColor : AppTheme.textSecondary,
        ),
      ),
    );
  }

  Widget _buildBottomButtons() {
    final continueEnabled = _selectedApproach != null;

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
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
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            // Cancel button
            Expanded(
              child: SizedBox(
                height: 56,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    side: const BorderSide(
                      color: AppTheme.dividerColor,
                      width: 1.5,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: widget.onBack,
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
            ),

            const SizedBox(width: 12),

            // Continue button
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: continueEnabled
                        ? AppTheme.primaryColor
                        : AppTheme.primaryColor.withValues(alpha: 0.5),
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: continueEnabled && !_isSaving
                      ? _handleContinue
                      : null,
                  child: _isSaving
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          'Continue',
                          style: AppTheme.dmSans(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
