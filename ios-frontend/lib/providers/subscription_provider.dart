import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import '../services/revenuecat_service.dart';
import '../services/analytics_service.dart';
import '../utils/logger.dart';

/// Provider for subscription/premium state using RevenueCat.
///
/// Matches the UserProvider pattern — ChangeNotifier with reactive getters.
/// Register in MultiProvider in main.dart.
class SubscriptionProvider extends ChangeNotifier {
  bool _isPremium = false;

  // ============================================
  // GETTERS
  // ============================================

  bool get isPremium => _isPremium;

  // ============================================
  // INITIALIZATION
  // ============================================

  SubscriptionProvider() {
    _init();
  }

  Future<void> _init() async {
    // Listen for real-time customer info updates (purchases, renewals, expirations)
    Purchases.addCustomerInfoUpdateListener(_onCustomerInfoUpdated);
    // Fetch initial state
    await refreshStatus();
  }

  void _onCustomerInfoUpdated(CustomerInfo customerInfo) {
    final wasPremium = _isPremium;
    _isPremium = customerInfo.entitlements.active.containsKey('premium');
    if (wasPremium != _isPremium) {
      notifyListeners();
      if (kDebugMode) {
        AppLogger.info('Subscription status changed: isPremium=$_isPremium');
      }
    }
  }

  // ============================================
  // PREMIUM GATE
  // ============================================

  /// Gate method: returns true if the user is premium, else shows the paywall.
  /// Use before any generation step:
  /// ```dart
  /// if (!await subscriptionProvider.ensurePremium(source: 'improvements_generate')) return;
  /// ```
  Future<bool> ensurePremium({required String source}) async {
    // TODO: Remove this bypass to enable paywall gates
    return true;

    if (_isPremium) return true;

    // Refresh in case of stale state
    await refreshStatus();
    if (_isPremium) return true;

    // Show paywall
    await showPaywall(source: source);
    return _isPremium;
  }

  // ============================================
  // PAYWALL
  // ============================================

  /// Present the RevenueCat paywall and log the analytics event.
  Future<void> showPaywall({required String source}) async {
    await AnalyticsService.logPaywallShown(source: source);
    try {
      await RevenueCatService.presentPaywallIfNeeded();
      // Refresh after paywall closes to pick up any new purchase
      await refreshStatus();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Paywall presentation failed: $e');
      }
    }
  }

  // ============================================
  // RESTORE
  // ============================================

  /// Restore previous purchases. Returns true if premium was restored.
  Future<bool> restorePurchases() async {
    try {
      final customerInfo = await RevenueCatService.restorePurchases();
      _isPremium = customerInfo.entitlements.active.containsKey('premium');
      notifyListeners();
      return _isPremium;
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Restore purchases failed: $e');
      }
      return false;
    }
  }

  // ============================================
  // SUBSCRIPTION MANAGEMENT
  // ============================================

  /// Open RevenueCat Customer Center for subscription management.
  Future<void> manageSubscription() async {
    try {
      await RevenueCatService.presentCustomerCenter();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Customer center failed: $e');
      }
    }
  }

  // ============================================
  // IDENTITY SYNC
  // ============================================

  /// Call when user signs in via Supabase.
  Future<void> onUserLoggedIn(String userId) async {
    await RevenueCatService.logIn(userId);
    await refreshStatus();
  }

  /// Call when user signs out.
  Future<void> onUserLoggedOut() async {
    await RevenueCatService.logOut();
    _isPremium = false;
    notifyListeners();
  }

  // ============================================
  // REFRESH
  // ============================================

  /// Force-refresh premium status from RevenueCat.
  Future<void> refreshStatus() async {
    try {
      _isPremium = await RevenueCatService.isPremium();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Subscription refresh failed: $e');
      }
    }
  }
}
