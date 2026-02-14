import 'package:flutter/material.dart';
import '../theme.dart';

/// Shell wrapper for all screens in the create/redesign flow.
/// Provides consistent top bar + sticky bottom CTA, no bottom navigation.
class CreateFlowShell extends StatelessWidget {
  /// Title displayed in the app bar
  final String title;
  
  /// Called when back button is pressed
  final VoidCallback onBack;
  
  /// Optional widget on the right side of header (Skip / Help / Close)
  final Widget? headerRight;
  
  /// Whether to show a divider line under the app bar
  final bool showDividerUnderAppBar;
  
  /// Whether the screen is in a loading/busy state
  final bool isBusy;
  
  /// Padding for the main content area
  final EdgeInsets contentPadding;
  
  /// Text for the primary CTA button (if null, no CTA shown)
  final String? primaryButtonText;
  
  /// Called when primary CTA is pressed (null = disabled state)
  final VoidCallback? onPrimaryPressed;
  
  /// Helper text shown when CTA is disabled
  final String? disabledHelperText;
  
  /// The main content of the screen
  final Widget child;

  const CreateFlowShell({
    super.key,
    required this.title,
    required this.onBack,
    this.headerRight,
    this.showDividerUnderAppBar = false,
    this.isBusy = false,
    this.contentPadding = const EdgeInsets.all(16),
    this.primaryButtonText,
    this.onPrimaryPressed,
    this.disabledHelperText,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final bottomSafeArea = MediaQuery.of(context).padding.bottom;
    const ctaBarHeight = 56.0 + 16.0 + 16.0; // button + padding top + padding bottom
    
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.scaffoldBackground,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 20),
          color: AppTheme.textPrimary,
          onPressed: onBack,
        ),
        title: Text(
          title,
          style: AppTheme.sectionStyle(),
        ),
        actions: headerRight != null ? [headerRight!] : null,
        bottom: showDividerUnderAppBar
            ? PreferredSize(
                preferredSize: const Size.fromHeight(1),
                child: Container(
                  height: 1,
                  color: AppTheme.dividerColor,
                ),
              )
            : null,
      ),
      body: Stack(
        children: [
          // Scrollable content with bottom padding for CTA
          Positioned.fill(
            child: SingleChildScrollView(
              padding: contentPadding.copyWith(
                bottom: primaryButtonText != null
                    ? ctaBarHeight + bottomSafeArea + 16
                    : contentPadding.bottom,
              ),
              child: child,
            ),
          ),
          
          // Sticky CTA bar at bottom
          if (primaryButtonText != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _buildCtaBar(context, bottomSafeArea),
            ),
          
          // Loading overlay
          if (isBusy)
            Positioned.fill(
              child: Container(
                color: Colors.white.withValues(alpha: 0.8),
                child: const Center(
                  child: CircularProgressIndicator(
                    color: AppTheme.primaryColor,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildCtaBar(BuildContext context, double bottomSafeArea) {
    final isDisabled = onPrimaryPressed == null;
    
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: bottomSafeArea + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Helper text when disabled
          if (isDisabled && disabledHelperText != null) ...[
            Text(
              disabledHelperText!,
              style: AppTheme.captionStyle(color: AppTheme.textTertiary),
            ),
            const SizedBox(height: 8),
          ],
          
          // Primary CTA button
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: onPrimaryPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: isDisabled 
                    ? AppTheme.disabledFill 
                    : AppTheme.primaryColor,
                foregroundColor: isDisabled 
                    ? AppTheme.disabledText 
                    : Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: Text(
                primaryButtonText!,
                style: AppTheme.dmSans(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: isDisabled ? AppTheme.disabledText : Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
