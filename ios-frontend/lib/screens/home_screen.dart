import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/project_provider.dart';
import '../providers/subscription_provider.dart';
import '../utils/logger.dart';
import '../widgets/animated_border_card.dart';
import 'create_flow_screen.dart';

/// Home tab - redesigned with action cards and marketplace grid.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

const bool _devBypassAuth = bool.fromEnvironment(
  'DEV_BYPASS_AUTH',
  defaultValue: false,
);

class _HomeScreenState extends State<HomeScreen> {
  bool _isCreatingProject = false;
  int _selectedActionCard = -1; // -1 = no pre-selection

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final sub = Provider.of<SubscriptionProvider>(context, listen: false);
      sub.setContext(context);
      sub.refreshUsageIfStale();
    });
  }

  Future<void> _startRedesignFlow({bool isCamera = false}) async {
    if (_isCreatingProject) return;

    final subProvider = Provider.of<SubscriptionProvider>(
      context,
      listen: false,
    );

    // Check cooldown first
    if (subProvider.cooldownSecondsLeft > 0) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Please wait ${subProvider.cooldownSecondsLeft}s before starting another redesign',
            ),
            backgroundColor: Colors.orange.shade700,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            margin: const EdgeInsets.all(16),
            duration: const Duration(seconds: 3),
          ),
        );
      }
      return;
    }

    // Credit gate
    final allowed = await subProvider.ensureCanGenerate(
      source: isCamera ? 'home_camera' : 'home_gallery',
      context: context,
    );
    if (!allowed || !mounted) return;

    setState(() => _isCreatingProject = true);

    try {
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      final created = await projectProvider.createProject(context);

      if (!mounted) return;

      if (!created) {
        final message =
            projectProvider.errorMessage ??
            'Failed to create project. Please try again.';
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(message),
              backgroundColor: AppTheme.errorColor,
            ),
          );
        }
        return;
      }

      // No credit debit here — credits are charged at job start
      // (inspiration-redesign), not at project creation.

      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CreateFlowScreen(isCamera: isCamera),
          fullscreenDialog: true,
        ),
      );
    } catch (e) {
      AppLogger.error('Failed to create project', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isCreatingProject = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with logo
              _buildHeader(),

              const SizedBox(height: 24),

              // Redesign section
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Redesign.',
                      style: AppTheme.dmSans(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const Spacer(),
                    if (kDebugMode && _devBypassAuth)
                      TextButton(
                        onPressed: () {
                          final sub = Provider.of<SubscriptionProvider>(
                            context,
                            listen: false,
                          );
                          sub.showPaywall(
                            source: 'dev_test_paywall_button',
                            context: context,
                          );
                        },
                        child: Text(
                          'Test Paywall',
                          style: AppTheme.dmSans(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.primaryColor,
                          ),
                        ),
                      ),
                    Flexible(
                      child: Consumer<SubscriptionProvider>(
                        builder: (context, sub, _) {
                          final credits = sub.creditsBalance;
                          final isPro = sub.isPremium;
                          if (isPro && credits > 10) {
                            return const SizedBox.shrink();
                          }
                          return GestureDetector(
                            onTap: () => sub.showPaywall(
                              source: 'home_remaining_chip',
                              context: context,
                            ),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: credits > 0
                                    ? AppTheme.primaryColor.withValues(
                                        alpha: 0.08,
                                      )
                                    : AppTheme.errorColor.withValues(
                                        alpha: 0.08,
                                      ),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                credits > 0
                                    ? '$credits credit${credits == 1 ? '' : 's'} left'
                                    : 'Get credits',
                                style: AppTheme.dmSans(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: credits > 0
                                      ? AppTheme.primaryColor
                                      : AppTheme.errorColor,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Action cards row
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Expanded(
                      child: _buildActionCard(
                        index: 0,
                        icon: Icons.image_outlined,
                        title: 'Take a Photo',
                        subtitle: 'Capture your space',
                        isSelected: _selectedActionCard == 0,
                        onTap: () {
                          setState(() => _selectedActionCard = 0);
                          _startRedesignFlow(isCamera: true);
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildActionCard(
                        index: 1,
                        icon: Icons.camera_alt_outlined,
                        title: 'Upload Picture',
                        subtitle: 'From your gallery',
                        isSelected: _selectedActionCard == 1,
                        onTap: () {
                          setState(() => _selectedActionCard = 1);
                          _startRedesignFlow(isCamera: false);
                        },
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 36),

              // How it works section
              _buildHowItWorksSection(),

              const SizedBox(height: 120), // Bottom padding for nav bar
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          Text(
            'Spaces',
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          Text(
            '.',
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.primaryColor,
              letterSpacing: -0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionCard({
    required int index,
    required IconData icon,
    required String title,
    required String subtitle,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return AnimatedBorderCard(
      isSelected: isSelected,
      onTap: _isCreatingProject ? null : onTap,
      showCheckmark: false,
      animateOnce: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: isSelected
                  ? AppTheme.primaryColor.withValues(alpha: 0.1)
                  : AppTheme.scaffoldBackground,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              icon,
              color: isSelected
                  ? AppTheme.primaryColor
                  : AppTheme.textSecondary,
              size: 24,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: AppTheme.dmSans(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTheme.dmSans(
              fontSize: 13,
              fontWeight: FontWeight.w400,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHowItWorksSection() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'How it works.',
            style: AppTheme.dmSans(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          _buildStepCard(
            stepNumber: '1',
            title: 'Snap your space',
            subtitle: 'Take a photo or upload an image of any room you want to redesign.',
            icon: Icons.camera_alt_outlined,
          ),
          const SizedBox(height: 12),
          _buildStepCard(
            stepNumber: '2',
            title: 'Pick your style',
            subtitle: 'Choose a design style, colors, and products that inspire you.',
            icon: Icons.palette_outlined,
          ),
          const SizedBox(height: 12),
          _buildStepCard(
            stepNumber: '3',
            title: 'See the magic',
            subtitle: 'Get a stunning AI-generated redesign of your room in seconds.',
            icon: Icons.auto_awesome_outlined,
          ),
        ],
      ),
    );
  }

  Widget _buildStepCard({
    required String stepNumber,
    required String title,
    required String subtitle,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor, width: 1),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              icon,
              color: AppTheme.primaryColor,
              size: 22,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTheme.dmSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
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
      ),
    );
  }
}
