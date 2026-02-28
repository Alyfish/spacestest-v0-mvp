import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:purchases_ui_flutter/purchases_ui_flutter.dart';
import '../constants/api_constants.dart';
import '../utils/logger.dart';
import 'revenuecat_service.dart';
import 'supabase_service.dart';

/// Purchase result returned by billing service methods.
class PurchaseResult {
  final bool success;
  final String? error;
  const PurchaseResult({required this.success, this.error});
}

/// Abstract billing interface — swap between Mock IAP and RevenueCat.
abstract class BillingService {
  Future<PurchaseResult> purchaseAnnual(BuildContext context);
  Future<PurchaseResult> purchaseCredits(BuildContext context);
  Future<void> restorePurchases();
  Future<void> showPaywall(BuildContext context, {required String source});
}

/// Mock billing service that calls /dev/grant-* endpoints.
/// Shows a simple confirmation dialog as the "paywall".
class MockBillingService implements BillingService {
  @override
  Future<PurchaseResult> purchaseAnnual(BuildContext context) async {
    final authToken = SupabaseService.accessToken;
    if (authToken == null) {
      return const PurchaseResult(success: false, error: 'Not authenticated');
    }
    try {
      final url = Uri.parse('${ApiConstants.baseUrl}/dev/grant-annual');
      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );
      if (response.statusCode == 200) {
        return const PurchaseResult(success: true);
      }
      return PurchaseResult(
        success: false,
        error: 'Server returned ${response.statusCode}',
      );
    } catch (e) {
      return PurchaseResult(success: false, error: e.toString());
    }
  }

  @override
  Future<PurchaseResult> purchaseCredits(BuildContext context) async {
    final authToken = SupabaseService.accessToken;
    if (authToken == null) {
      return const PurchaseResult(success: false, error: 'Not authenticated');
    }
    try {
      final url = Uri.parse('${ApiConstants.baseUrl}/dev/grant-credits');
      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );
      if (response.statusCode == 200) {
        return const PurchaseResult(success: true);
      }
      return PurchaseResult(
        success: false,
        error: 'Server returned ${response.statusCode}',
      );
    } catch (e) {
      return PurchaseResult(success: false, error: e.toString());
    }
  }

  @override
  Future<void> restorePurchases() async {
    // No-op for mock — credits are server-side
    if (kDebugMode) {
      AppLogger.info('MockBillingService: restorePurchases (no-op)');
    }
  }

  @override
  Future<void> showPaywall(BuildContext context, {required String source}) async {
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Get More Credits'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Choose an option:'),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx, 'annual'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Spaces Pro — \$39.99/yr (45 credits)'),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => Navigator.pop(ctx, 'credits'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Buy 2 Credits — \$4.99'),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );

    if (result == null || !context.mounted) return;

    PurchaseResult purchaseResult;
    if (result == 'annual') {
      purchaseResult = await purchaseAnnual(context);
    } else {
      purchaseResult = await purchaseCredits(context);
    }

    if (context.mounted && purchaseResult.success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Credits added!')),
      );
    } else if (context.mounted && purchaseResult.error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Purchase failed: ${purchaseResult.error}')),
      );
    }
  }
}

/// RevenueCat-backed billing service — wraps RevenueCatService and polls /usage after purchase.
class RevenueCatBillingService implements BillingService {
  PurchaseResult _mapPaywallResult(PaywallResult result) {
    switch (result) {
      case PaywallResult.purchased:
      case PaywallResult.restored:
        return const PurchaseResult(success: true);
      case PaywallResult.cancelled:
      case PaywallResult.notPresented:
        return const PurchaseResult(success: false, error: 'Purchase cancelled');
      case PaywallResult.error:
        return const PurchaseResult(
          success: false,
          error: 'RevenueCat paywall failed',
        );
    }
  }

  @override
  Future<PurchaseResult> purchaseAnnual(BuildContext context) async {
    if (!RevenueCatService.isConfigured) {
      if (kDebugMode) {
        AppLogger.warning(
          'RevenueCat purchaseAnnual requested but SDK is not configured',
        );
      }
      return const PurchaseResult(
        success: false,
        error: 'RevenueCat is not configured on this build.',
      );
    }
    try {
      final result = await RevenueCatService.presentPaywall();
      return _mapPaywallResult(result);
    } catch (e) {
      return PurchaseResult(success: false, error: e.toString());
    }
  }

  @override
  Future<PurchaseResult> purchaseCredits(BuildContext context) async {
    if (!RevenueCatService.isConfigured) {
      if (kDebugMode) {
        AppLogger.warning(
          'RevenueCat purchaseCredits requested but SDK is not configured',
        );
      }
      return const PurchaseResult(
        success: false,
        error: 'RevenueCat is not configured on this build.',
      );
    }
    try {
      final result = await RevenueCatService.presentPaywall();
      return _mapPaywallResult(result);
    } catch (e) {
      return PurchaseResult(success: false, error: e.toString());
    }
  }

  @override
  Future<void> restorePurchases() async {
    if (!RevenueCatService.isConfigured) {
      if (kDebugMode) {
        AppLogger.info(
          'RevenueCat restorePurchases skipped (SDK not configured)',
        );
      }
      return;
    }
    await RevenueCatService.restorePurchases();
  }

  @override
  Future<void> showPaywall(BuildContext context, {required String source}) async {
    if (!RevenueCatService.isConfigured) {
      if (kDebugMode) {
        AppLogger.warning(
          'RevenueCat paywall requested from $source but SDK is not configured',
        );
      }
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Purchases are unavailable in this build (RevenueCat not configured).',
            ),
          ),
        );
      }
      return;
    }
    try {
      final result = await RevenueCatService.presentPaywallIfNeeded();
      if (kDebugMode) {
        AppLogger.info('RevenueCat paywall result ($source): $result');
      }
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat paywall failed: $e');
      }
    }
  }
}

/// Factory to get the appropriate billing service based on env config.
BillingService createBillingService() {
  const useMockIap = bool.fromEnvironment(
    'DEV_IAP_ENABLED',
    defaultValue: false,
  );
  if (useMockIap) {
    if (kDebugMode) {
      AppLogger.info(
        'BillingService: using MockBillingService (DEV_IAP_ENABLED=true) '
        '[rcHasKey=${RevenueCatService.hasApiKey} rcConfigured=${RevenueCatService.isConfigured}]',
      );
    }
    return MockBillingService();
  }
  if (kDebugMode) {
    AppLogger.info(
      'BillingService: using RevenueCatBillingService '
      '[rcHasKey=${RevenueCatService.hasApiKey} rcConfigured=${RevenueCatService.isConfigured}]',
    );
  }
  return RevenueCatBillingService();
}
