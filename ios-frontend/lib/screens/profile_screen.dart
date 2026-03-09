import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import '../constants/api_constants.dart';
import '../services/supabase_service.dart';
import '../theme.dart';
import '../providers/subscription_provider.dart';
import '../providers/user_provider.dart';
import '../utils/logger.dart';
import 'splash_screen.dart';

/// Profile screen with user info, feedback option, and logout
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  void _showFeedbackDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Provide Feedback',
          style: AppTheme.dmSans(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppTheme.textPrimary,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Send your feedback or report issues to:',
              style: AppTheme.dmSans(
                fontSize: 15,
                color: AppTheme.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            GestureDetector(
              onTap: () {
                Clipboard.setData(
                  const ClipboardData(text: 'spaces.ai.biz@gmail.com'),
                );
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Email copied to clipboard'),
                    backgroundColor: AppTheme.primaryColor,
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    margin: const EdgeInsets.all(16),
                    duration: const Duration(seconds: 2),
                  ),
                );
                Navigator.pop(context);
              },
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.scaffoldBackground,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.email_outlined,
                      size: 20,
                      color: AppTheme.primaryColor,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'spaces.ai.biz@gmail.com',
                        style: AppTheme.dmSans(
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.primaryColor,
                        ),
                      ),
                    ),
                    Icon(
                      Icons.copy_rounded,
                      size: 18,
                      color: AppTheme.textTertiary,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap to copy email address',
              style: AppTheme.dmSans(
                fontSize: 12,
                color: AppTheme.textTertiary,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Close',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _handleRefillCredits(BuildContext context) async {
    final token = SupabaseService.accessToken;
    if (token == null) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Not authenticated')),
        );
      }
      return;
    }
    try {
      final response = await http.post(
        Uri.parse('${ApiConstants.baseUrl}/dev/grant-credits'),
        headers: ApiConstants.authHeaders(token),
      );
      if (!context.mounted) return;
      if (response.statusCode == 200) {
        await Provider.of<SubscriptionProvider>(context, listen: false)
            .refreshUsageIfStale(force: true);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('Added 2 credits!'),
              backgroundColor: AppTheme.primaryColor,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              margin: const EdgeInsets.all(16),
            ),
          );
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed: ${response.statusCode}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } catch (e) {
      AppLogger.error('Dev credit refill failed', e);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Future<void> _handleLogout(BuildContext context) async {
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final subscriptionProvider = Provider.of<SubscriptionProvider>(
      context,
      listen: false,
    );

    // Show confirmation dialog
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Log Out',
          style: AppTheme.dmSans(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppTheme.textPrimary,
          ),
        ),
        content: Text(
          'Are you sure you want to log out?',
          style: AppTheme.dmSans(fontSize: 15, color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(
              'Cancel',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(
              'Log Out',
              style: AppTheme.dmSans(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: Colors.red,
              ),
            ),
          ),
        ],
      ),
    );

    if (shouldLogout == true && context.mounted) {
      await subscriptionProvider.onUserLoggedOut();
      await userProvider.signOut();
      // Navigate to splash screen
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const SplashScreen()),
        (route) => false,
      );
    }
  }

  Future<void> _handleManageSubscription(BuildContext context) async {
    final subscriptionProvider = Provider.of<SubscriptionProvider>(
      context,
      listen: false,
    );
    await subscriptionProvider.manageSubscription();
  }

  Future<void> _handleRestorePurchases(BuildContext context) async {
    final subscriptionProvider = Provider.of<SubscriptionProvider>(
      context,
      listen: false,
    );
    final restored = await subscriptionProvider.restorePurchases();
    if (!context.mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          restored
              ? 'Premium subscription restored.'
              : 'No active purchases found to restore.',
        ),
        backgroundColor: restored
            ? AppTheme.primaryColor
            : AppTheme.textSecondary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: Consumer<UserProvider>(
          builder: (context, userProvider, child) {
            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),

                  // Title
                  Text(
                    'Profile.',
                    style: AppTheme.dmSans(
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),

                  const SizedBox(height: 24),

                  // User Info Card
                  if (userProvider.isAuthenticated) ...[
                    _buildUserCard(userProvider),
                    const SizedBox(height: 24),
                  ],

                  // Menu Options
                  _buildBillingSection(context),

                  const SizedBox(height: 16),

                  _buildMenuSection(context),

                  const SizedBox(height: 100), // Bottom padding for nav bar
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildUserCard(UserProvider userProvider) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor, width: 1),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: AppTheme.primaryColor,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Center(
              child: Text(
                userProvider.user.name?.substring(0, 1).toUpperCase() ?? 'U',
                style: AppTheme.dmSans(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          // User info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  userProvider.user.name ?? 'User',
                  style: AppTheme.dmSans(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  userProvider.user.email ?? 'user@example.com',
                  style: AppTheme.dmSans(
                    fontSize: 14,
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

  Widget _buildMenuSection(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor, width: 1),
      ),
      child: Column(
        children: [
          // Feedback / Report Problem
          _buildMenuItem(
            icon: Icons.feedback_outlined,
            title: 'Provide Feedback / Report a Problem',
            onTap: () => _showFeedbackDialog(context),
          ),

          // Divider
          Divider(height: 1, color: AppTheme.dividerColor, indent: 56),

          // Logout
          _buildMenuItem(
            icon: Icons.logout_rounded,
            title: 'Log Out',
            isDestructive: true,
            onTap: () => _handleLogout(context),
          ),
        ],
      ),
    );
  }

  Widget _buildBillingSection(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.dividerColor, width: 1),
      ),
      child: Column(
        children: [
          if (kDebugMode) ...[
            _buildMenuItem(
              icon: Icons.add_card_rounded,
              title: '[DEV] Add 2 Credits',
              onTap: () => _handleRefillCredits(context),
            ),
            Divider(height: 1, color: AppTheme.dividerColor, indent: 56),
          ],
          _buildMenuItem(
            icon: Icons.credit_card_outlined,
            title: 'Manage Subscription',
            onTap: () => _handleManageSubscription(context),
          ),
          Divider(height: 1, color: AppTheme.dividerColor, indent: 56),
          _buildMenuItem(
            icon: Icons.restore_rounded,
            title: 'Restore Purchases',
            onTap: () => _handleRestorePurchases(context),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: isDestructive
                    ? Colors.red.withValues(alpha: 0.1)
                    : AppTheme.scaffoldBackground,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                icon,
                size: 20,
                color: isDestructive ? Colors.red : AppTheme.textSecondary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: AppTheme.dmSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: isDestructive ? Colors.red : AppTheme.textPrimary,
                ),
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              size: 20,
              color: isDestructive ? Colors.red : AppTheme.textTertiary,
            ),
          ],
        ),
      ),
    );
  }
}
