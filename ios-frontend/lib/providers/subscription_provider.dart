import 'dart:async';
import 'dart:math' show max;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import '../services/api_service.dart';
import '../services/billing_service.dart';
import '../services/revenuecat_service.dart';
import '../services/analytics_service.dart';
import '../services/supabase_service.dart';
import '../utils/logger.dart';

/// Provider for subscription/credit state.
///
/// Reads plan_tier, credits_balance, daily_remaining, cooldown from /usage.
/// Uses BillingService abstraction for purchases (Mock IAP or RevenueCat).
class SubscriptionProvider extends ChangeNotifier {
  // Credit system state (from /usage v2)
  String _planTier = 'free';
  int _creditsBalance = 3;
  int _dailyRemaining = 3;
  int _dailyCap = 3;
  int _cooldownSecondsLeft = 0;
  int _redesignsUsedToday = 0;
  bool _isPremium = false;

  DateTime? _usageLoadedAt;
  static const _usageTtl = Duration(seconds: 60);

  // Billing service (injectable)
  late final BillingService _billingService;

  // Keep a BuildContext reference for paywall dialog (set via showPaywall)
  BuildContext? _lastContext;

  // ============================================
  // GETTERS
  // ============================================

  String get planTier => _planTier;
  int get creditsBalance => _creditsBalance;
  int get dailyRemaining => _dailyRemaining;
  int get dailyCap => _dailyCap;
  int get cooldownSecondsLeft => _cooldownSecondsLeft;
  int get redesignsUsedToday => _redesignsUsedToday;
  bool get isPremium => _isPremium;

  // Unified credit check (replaces old canGenerate / canIterate)
  bool get canGenerate => _creditsBalance > 0 && _dailyRemaining > 0;
  bool get canIterate => canGenerate; // Unified pool
  int get remainingGenerations => _creditsBalance; // Alias for backward compat

  // ============================================
  // INITIALIZATION
  // ============================================

  SubscriptionProvider() {
    _billingService = createBillingService();
    _init();
  }

  Future<void> _init() async {
    // Listen for real-time customer info updates (purchases, renewals, expirations)
    try {
      RevenueCatService.addCustomerInfoListener(_onCustomerInfoUpdated);
      if (kDebugMode) {
        AppLogger.info(
          'SubscriptionProvider init: billing listener setup '
          '(rcHasKey=${RevenueCatService.hasApiKey}, rcConfigured=${RevenueCatService.isConfigured})',
        );
      }
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Failed to add RevenueCat listener: $e');
      }
    }
    // Fetch initial state
    await refreshStatus();
  }

  void _onCustomerInfoUpdated(CustomerInfo customerInfo) {
    final hadPro = _isPremium;
    _isPremium = customerInfo.entitlements.active.containsKey(
      RevenueCatService.entitlementId,
    );
    if (hadPro != _isPremium) {
      // Entitlement changed — refresh credits from server
      refreshUsageIfStale(force: true);
      if (kDebugMode) {
        AppLogger.info('Subscription status changed: isPremium=$_isPremium');
      }
    }
  }

  // ============================================
  // USAGE TRACKING (v2 — credit-based)
  // ============================================

  /// Refresh usage from the server if TTL has expired (or forced).
  Future<void> refreshUsageIfStale({bool force = false}) async {
    if (!force &&
        _usageLoadedAt != null &&
        DateTime.now().difference(_usageLoadedAt!) < _usageTtl) {
      return;
    }

    try {
      var authToken = SupabaseService.accessToken;
      if (authToken == null) return;

      Map<String, dynamic> data;
      try {
        data = await ApiService.getUsage(authToken);
      } catch (e) {
        // Token may be expired from a restored session — refresh and retry once
        if (e.toString().contains('401')) {
          await SupabaseService.refreshSession();
          authToken = SupabaseService.accessToken;
          if (authToken == null) return;
          data = await ApiService.getUsage(authToken);
        } else {
          rethrow;
        }
      }
      _planTier = data['plan_tier'] as String? ?? 'free';
      _creditsBalance = data['credits_balance'] as int? ?? 0;
      _dailyRemaining = data['daily_remaining'] as int? ?? 0;
      _dailyCap = data['daily_cap'] as int? ?? 3;
      _cooldownSecondsLeft = data['cooldown_seconds_left'] as int? ?? 0;
      _redesignsUsedToday = data['redesigns_used_today'] as int? ?? 0;
      _isPremium = _planTier == 'pro_yearly';

      _usageLoadedAt = DateTime.now();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Usage refresh failed: $e');
      }
    }
  }

  /// Optimistic bump after a generation/iteration starts.
  void recordGenerationUsed() {
    _creditsBalance = max(0, _creditsBalance - 1);
    _dailyRemaining = max(0, _dailyRemaining - 1);
    _redesignsUsedToday++;
    _cooldownSecondsLeft = 30;
    notifyListeners();
    refreshUsageIfStale(force: true);
  }

  /// Alias for backward compatibility.
  void recordIterationUsed() => recordGenerationUsed();

  // ============================================
  // FREEMIUM GATES (unified credit pool)
  // ============================================

  /// Gate: returns true if the user can start a new generation.
  /// If out of credits, shows paywall. Returns true if credits available after paywall.
  Future<bool> ensureCanGenerate({required String source, BuildContext? context}) async {
    try {
      await refreshUsageIfStale();
      if (canGenerate && _cooldownSecondsLeft <= 0) return true;

      if (_cooldownSecondsLeft > 0) {
        // Cooldown active — don't show paywall, just inform caller
        return false;
      }

      // Out of credits or daily cap — show paywall
      final ctx = context ?? _lastContext;
      if (ctx != null && ctx.mounted) {
        await showPaywall(source: source, context: ctx);
        await refreshUsageIfStale(force: true);
      }
      return canGenerate;
    } catch (e) {
      AppLogger.error('ensureCanGenerate error: $e');
      return true; // Fail-open
    }
  }

  /// Gate: returns true if the user can retry/iterate.
  Future<bool> ensureCanIterate({required String source, BuildContext? context}) async {
    return ensureCanGenerate(source: source, context: context);
  }

  /// Legacy gate — returns true if the user has credits.
  Future<bool> ensurePremium({required String source}) async {
    await refreshUsageIfStale();
    if (canGenerate) return true;
    return false;
  }

  // ============================================
  // PAYWALL
  // ============================================

  /// Present the paywall (uses BillingService abstraction).
  Future<void> showPaywall({required String source, BuildContext? context}) async {
    final ctx = context ?? _lastContext;
    await AnalyticsService.logPaywallShown(source: source);
    try {
      if (ctx != null && ctx.mounted) {
        await _billingService.showPaywall(ctx, source: source);
        // Refresh after paywall closes to pick up any new credits
        await refreshUsageIfStale(force: true);
      }
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Paywall presentation failed: $e');
      }
    }
  }

  /// Store the latest context for paywall access.
  void setContext(BuildContext context) {
    _lastContext = context;
  }

  // ============================================
  // RESTORE
  // ============================================

  /// Restore previous purchases.
  Future<bool> restorePurchases() async {
    try {
      await _billingService.restorePurchases();
      await refreshUsageIfStale(force: true);
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

  /// Open subscription management UI.
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
    await refreshUsageIfStale(force: true);
  }

  /// Call when user signs out.
  Future<void> onUserLoggedOut() async {
    await RevenueCatService.logOut();
    _isPremium = false;
    _planTier = 'free';
    _creditsBalance = 0;
    _dailyRemaining = 0;
    _cooldownSecondsLeft = 0;
    _redesignsUsedToday = 0;
    _usageLoadedAt = null;
    notifyListeners();
  }

  // ============================================
  // REFRESH
  // ============================================

  /// Force-refresh premium status from RevenueCat + credits from server.
  Future<void> refreshStatus() async {
    try {
      _isPremium = await RevenueCatService.isPremium();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('RevenueCat refresh failed: $e');
      }
    }
    await refreshUsageIfStale(force: true);
  }
}
