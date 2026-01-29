import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
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
    final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
    _selectedApproach = projectProvider.approach;
  }

  Future<void> _handleContinue() async {
    if (_selectedApproach == null || _isSaving) return;

    final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
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
    final success = await projectProvider.saveApproach(context, _selectedApproach!);

    if (mounted) {
      setState(() => _isSaving = false);
      if (success) widget.onContinue?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with logo and settings
        _buildHeader(),

        // Progress bar
        const SizedBox(height: 8),
        const StepProgressBar(currentStep: 5, totalSteps: 8),

        // Content
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 24),

                // Title
                Text(
                  'Choose Approach.',
                  style: AppTheme.dmSans(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),

                const SizedBox(height: 24),

                // Project Image Preview
                _buildProjectImagePreview(),

                const SizedBox(height: 24),

                // Option Buttons
                _buildApproachOption(
                  id: 'iterative',
                  icon: IconsaxPlusLinear.home_2,
                  title: 'Iterative Improvement.',
                ),
                const SizedBox(height: 12),
                _buildApproachOption(
                  id: 'revamp',
                  icon: IconsaxPlusLinear.magic_star,
                  title: 'Complete Revamp.',
                ),

                const SizedBox(height: 100),
              ],
            ),
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
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Spaces. logo
          Image.asset(
            'assets/logo/logo.png',
            height: 32,
          ),
          // Settings icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.dividerColor,
                width: 1,
              ),
            ),
            child: IconButton(
              icon: const Icon(
                Icons.settings_outlined,
                color: AppTheme.textPrimary,
                size: 22,
              ),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProjectImagePreview() {
    return Consumer<ProjectProvider>(
      builder: (context, provider, child) {
        final imageProvider = provider.getProjectImageProvider();
        final isDemoMode = imageProvider == null || ProjectProvider.demoMode;

        return Container(
          height: 240,
          width: double.infinity,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 20,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: isDemoMode
                ? Image.asset(
                    'assets/images_for_choose_spaces_new/1_pb_8pa89uOlXOTsrM8sFWg.jpg',
                    fit: BoxFit.cover,
                  )
                : Image(
                    image: imageProvider,
                    fit: BoxFit.cover,
                  ),
          ),
        );
      },
    );
  }

  Widget _buildApproachOption({
    required String id,
    required IconData icon,
    required String title,
  }) {
    final isSelected = _selectedApproach == id;

    return GestureDetector(
      onTap: () => setState(() => _selectedApproach = id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 24,
              color: isSelected ? AppTheme.primaryColor : AppTheme.textSecondary,
            ),
            const SizedBox(width: 16),
            Text(
              title,
              style: AppTheme.dmSans(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimary,
              ),
            ),
          ],
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
                    side: const BorderSide(color: AppTheme.dividerColor, width: 1.5),
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
                  onPressed: continueEnabled && !_isSaving ? _handleContinue : null,
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
