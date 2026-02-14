import 'package:flutter/foundation.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import 'package:purchases_ui_flutter/purchases_ui_flutter.dart';
import '../utils/logger.dart';

/// Static singleton service wrapping the RevenueCat SDK.
///
/// Matches the SupabaseService pattern — all methods are static.
/// Initialize in main.dart before runApp:
/// ```dart
/// await RevenueCatService.initialize(appUserID: userId);
/// ```
class RevenueCatService {
  static const String _apiKey = String.fromEnvironment(
    'RC_API_KEY',
    defaultValue: 'test_texCLiyZavOiZPgrUEGsDPbDpgq',
  );

  static bool _initialized = false;

  // ============================================
  // INITIALIZATION
  // ============================================

  /// Configure the RevenueCat SDK.
  /// Pass [appUserID] to identify the user immediately (e.g. from a restored Supabase session).
  static Future<void> initialize({String? appUserID}) async {
    if (_initialized) return;

    final configuration = PurchasesConfiguration(_apiKey)
      ..appUserID = appUserID;

    await Purchases.configure(configuration);
    _initialized = true;

    if (kDebugMode) {
      await Purchases.setLogLevel(LogLevel.debug);
      AppLogger.info('RevenueCat initialized (user: ${appUserID ?? 'anonymous'})');
    }
  }

  // ============================================
  // IDENTITY
  // ============================================

  /// Identify the user with RevenueCat after Supabase sign-in.
  static Future<void> logIn(String userId) async {
    try {
      await Purchases.logIn(userId);
      if (kDebugMode) {
        AppLogger.info('RevenueCat logIn: $userId');
      }
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat logIn failed: $e');
      }
    }
  }

  /// Reset to anonymous user on sign-out.
  static Future<void> logOut() async {
    try {
      await Purchases.logOut();
      if (kDebugMode) {
        AppLogger.info('RevenueCat logOut');
      }
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat logOut failed: $e');
      }
    }
  }

  // ============================================
  // ENTITLEMENTS
  // ============================================

  /// Check if the user has an active "premium" entitlement.
  static Future<bool> isPremium() async {
    try {
      final customerInfo = await Purchases.getCustomerInfo();
      return customerInfo.entitlements.active.containsKey('premium');
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat isPremium check failed: $e');
      }
      return false;
    }
  }

  /// Fetch full customer info from RevenueCat.
  static Future<CustomerInfo> getCustomerInfo() async {
    return await Purchases.getCustomerInfo();
  }

  // ============================================
  // PAYWALL
  // ============================================

  /// Present the RevenueCat pre-built paywall UI.
  /// Returns the result of the paywall presentation.
  static Future<PaywallResult> presentPaywall() async {
    return await RevenueCatUI.presentPaywall();
  }

  /// Present the paywall only if the user does not have the "premium" entitlement.
  /// Returns the result of the paywall presentation.
  static Future<PaywallResult> presentPaywallIfNeeded() async {
    return await RevenueCatUI.presentPaywallIfNeeded(
      'premium',
    );
  }

  // ============================================
  // CUSTOMER CENTER
  // ============================================

  /// Present the RevenueCat Customer Center for subscription management.
  static Future<void> presentCustomerCenter() async {
    await RevenueCatUI.presentCustomerCenter();
  }

  // ============================================
  // RESTORE & OFFERINGS
  // ============================================

  /// Restore previous purchases.
  static Future<CustomerInfo> restorePurchases() async {
    return await Purchases.restorePurchases();
  }

  /// Fetch available offerings/products.
  static Future<Offerings> getOfferings() async {
    return await Purchases.getOfferings();
  }
}
