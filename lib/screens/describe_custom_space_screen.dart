import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/step_progress_bar.dart';

/// Screen for describing a custom space type
class DescribeCustomSpaceScreen extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const DescribeCustomSpaceScreen({
    super.key,
    this.onBack,
    this.onContinue,
  });

  @override
  State<DescribeCustomSpaceScreen> createState() =>
      _DescribeCustomSpaceScreenState();
}

class _DescribeCustomSpaceScreenState extends State<DescribeCustomSpaceScreen> {
  final TextEditingController _descriptionController = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    // Load existing description if any
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      final existingDescription =
          projectProvider.currentProject?.customSpaceDescription;
      if (existingDescription != null && existingDescription.isNotEmpty) {
        _descriptionController.text = existingDescription;
      }
    });
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onContinue() {
    final description = _descriptionController.text.trim();
    if (description.isEmpty) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    projectProvider.setCustomSpaceDescription(description);

    if (widget.onContinue != null) {
      widget.onContinue!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: Column(
          children: [
            // Header with back button
            _buildHeader(),

            // Progress bar
            const SizedBox(height: 8),
            const StepProgressBar(currentStep: 3, totalSteps: 8),

            // Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  children: [
                    const SizedBox(height: 48),

                    // Centered icon
                    Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        color: AppTheme.primaryColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Icon(
                        IconsaxPlusLinear.lamp_1,
                        size: 40,
                        color: AppTheme.primaryColor,
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Title
                    Text(
                      'Describe Custom Space',
                      style: AppTheme.dmSans(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                      textAlign: TextAlign.center,
                    ),

                    const SizedBox(height: 16),

                    // Subtitle in pink pill container
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 14,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryColor.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        'What are the changes that you would like to make on this final design of your space?',
                        style: AppTheme.dmSans(
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.primaryColor,
                          height: 1.4,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Text input field
                    TextField(
                      controller: _descriptionController,
                      focusNode: _focusNode,
                      maxLines: 5,
                      style: AppTheme.dmSans(
                        fontSize: 16,
                        color: AppTheme.textPrimary,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Describe your custom space...',
                        hintStyle: AppTheme.dmSans(
                          fontSize: 16,
                          color: AppTheme.textTertiary,
                        ),
                        filled: true,
                        fillColor: AppTheme.surfaceColor,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                          borderSide: BorderSide(
                            color: AppTheme.dividerColor,
                            width: 1,
                          ),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                          borderSide: BorderSide(
                            color: AppTheme.dividerColor,
                            width: 1,
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                          borderSide: BorderSide(
                            color: AppTheme.primaryColor,
                            width: 2,
                          ),
                        ),
                        contentPadding: const EdgeInsets.all(20),
                      ),
                      onChanged: (_) => setState(() {}),
                    ),

                    const SizedBox(height: 100), // Space for bottom button
                  ],
                ),
              ),
            ),

            // Bottom CTA
            _buildBottomButton(),
          ],
        ),
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
        ],
      ),
    );
  }

  Widget _buildBottomButton() {
    final hasDescription = _descriptionController.text.trim().isNotEmpty;

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
        child: SizedBox(
          width: double.infinity,
          height: 56,
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: hasDescription
                  ? AppTheme.primaryColor
                  : AppTheme.primaryColor.withValues(alpha: 0.5),
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
            onPressed: hasDescription ? _onContinue : null,
            child: Text(
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
    );
  }
}
