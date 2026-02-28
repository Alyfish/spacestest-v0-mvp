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
  static const String _rcApiKey = String.fromEnvironment(
    'RC_API_KEY',
    defaultValue: '',
  );
  static const String _revenueCatPublicKey = String.fromEnvironment(
    'REVENUECAT_PUBLIC_KEY',
    defaultValue: '',
  );

  static String get _apiKey {
    final rcKey = _rcApiKey.trim();
    if (rcKey.isNotEmpty) return rcKey;
    return _revenueCatPublicKey.trim();
  }

  static const String entitlementId = String.fromEnvironment(
    'RC_ENTITLEMENT_ID',
    defaultValue: 'premium',
  );

  static bool _initialized = false;

  static bool get hasApiKey => _apiKey.isNotEmpty;

  static bool get isConfigured => _initialized;

  static bool _ensureConfigured(String action) {
    if (_initialized) return true;
    if (kDebugMode) {
      AppLogger.info('RevenueCat not configured; skipping $action');
    }
    return false;
  }

  static StateError _notConfiguredError(String action) {
    return StateError(
      'RevenueCat is not configured. Cannot $action without '
      'RC_API_KEY or REVENUECAT_PUBLIC_KEY.',
    );
  }

  // ============================================
  // INITIALIZATION
  // ============================================

  /// Configure the RevenueCat SDK.
  /// Pass [appUserID] to identify the user immediately (e.g. from a restored Supabase session).
  static Future<void> initialize({String? appUserID}) async {
    if (_initialized) {
      if (kDebugMode) {
        AppLogger.info('RevenueCat initialize skipped (already configured)');
      }
      return;
    }
    if (_apiKey.isEmpty) {
      const message =
          'RevenueCat API key is missing. '
          'Pass --dart-define=RC_API_KEY=<your-ios-public-sdk-key> '
          'or --dart-define=REVENUECAT_PUBLIC_KEY=<your-ios-public-sdk-key>.';
      if (kReleaseMode) {
        throw StateError(message);
      }
      if (kDebugMode) {
        AppLogger.warning(message);
        AppLogger.info(
          'RevenueCat status: hasApiKey=$hasApiKey configured=$isConfigured',
        );
      }
      return;
    }

    final configuration = PurchasesConfiguration(_apiKey)
      ..appUserID = appUserID;

    await Purchases.configure(configuration);
    _initialized = true;

    if (kDebugMode) {
      await Purchases.setLogLevel(LogLevel.debug);
      AppLogger.info(
        'RevenueCat initialized (user: ${appUserID ?? 'anonymous'}) '
        '[hasApiKey=$hasApiKey configured=$isConfigured entitlement=$entitlementId]',
      );
    }
  }

  /// Register a customer info listener. Safe no-op when RevenueCat is unavailable.
  static void addCustomerInfoListener(void Function(CustomerInfo) listener) {
    if (!_ensureConfigured('customer info listener registration')) return;
    Purchases.addCustomerInfoUpdateListener(listener);
  }

  // ============================================
  // IDENTITY
  // ============================================

  /// Identify the user with RevenueCat after Supabase sign-in.
  static Future<void> logIn(String userId) async {
    if (!_ensureConfigured('logIn')) return;
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
    if (!_ensureConfigured('logOut')) return;
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
    if (!_ensureConfigured('isPremium')) return false;
    try {
      final customerInfo = await Purchases.getCustomerInfo();
      return customerInfo.entitlements.active.containsKey(entitlementId);
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat isPremium check failed: $e');
      }
      return false;
    }
  }

  /// Fetch full customer info from RevenueCat.
  static Future<CustomerInfo> getCustomerInfo() async {
    if (!_ensureConfigured('getCustomerInfo')) {
      throw _notConfiguredError('fetch customer info');
    }
    return await Purchases.getCustomerInfo();
  }

  // ============================================
  // PAYWALL
  // ============================================

  /// Present the RevenueCat pre-built paywall UI.
  /// Returns the result of the paywall presentation.
  static Future<PaywallResult> presentPaywall() async {
    if (!_ensureConfigured('presentPaywall')) return PaywallResult.error;
    return await RevenueCatUI.presentPaywall();
  }

  /// Present the paywall only if the user does not have the "premium" entitlement.
  /// Returns the result of the paywall presentation.
  static Future<PaywallResult> presentPaywallIfNeeded() async {
    if (!_ensureConfigured('presentPaywallIfNeeded')) {
      return PaywallResult.notPresented;
    }
    return await RevenueCatUI.presentPaywallIfNeeded(entitlementId);
  }

  // ============================================
  // CUSTOMER CENTER
  // ============================================

  /// Present the RevenueCat Customer Center for subscription management.
  static Future<void> presentCustomerCenter() async {
    if (!_ensureConfigured('presentCustomerCenter')) return;
    await RevenueCatUI.presentCustomerCenter();
  }

  // ============================================
  // RESTORE & OFFERINGS
  // ============================================

  /// Restore previous purchases.
  static Future<CustomerInfo> restorePurchases() async {
    if (!_ensureConfigured('restorePurchases')) {
      throw _notConfiguredError('restore purchases');
    }
    return await Purchases.restorePurchases();
  }

  /// Fetch available offerings/products.
  static Future<Offerings> getOfferings() async {
    if (!_ensureConfigured('getOfferings')) {
      throw _notConfiguredError('fetch offerings');
    }
    return await Purchases.getOfferings();
  }
}
