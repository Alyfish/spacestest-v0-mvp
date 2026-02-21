import 'dart:async';
import 'dart:math' show max;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import '../services/api_service.dart';
import '../services/revenuecat_service.dart';
import '../services/analytics_service.dart';
import '../services/supabase_service.dart';
import '../utils/logger.dart';

/// Provider for subscription/premium state using RevenueCat.
///
/// Matches the UserProvider pattern — ChangeNotifier with reactive getters.
/// Register in MultiProvider in main.dart.
class SubscriptionProvider extends ChangeNotifier {
  bool _isPremium = false;

  // Freemium usage tracking
  int _generationsUsed = 0;
  int _iterationsUsed = 0;
  int _freeGenerationLimit = 5;
  int _freeIterationLimit = 2;
  DateTime? _usageLoadedAt;
  static const _usageTtl = Duration(seconds: 60);

  // ============================================
  // GETTERS
  // ============================================

  bool get isPremium => _isPremium;
  int get generationsUsed => _generationsUsed;
  int get iterationsUsed => _iterationsUsed;
  int get remainingGenerations => max(0, _freeGenerationLimit - _generationsUsed);
  int get remainingIterations => max(0, _freeIterationLimit - _iterationsUsed);
  bool get canGenerate => _isPremium || _generationsUsed < _freeGenerationLimit;
  bool get canIterate => _isPremium || _iterationsUsed < _freeIterationLimit;
  int get freeGenerationLimit => _freeGenerationLimit;
  int get freeIterationLimit => _freeIterationLimit;

  // ============================================
  // INITIALIZATION
  // ============================================

  SubscriptionProvider() {
    _init();
  }

  Future<void> _init() async {
    // Listen for real-time customer info updates (purchases, renewals, expirations)
    try {
      Purchases.addCustomerInfoUpdateListener(_onCustomerInfoUpdated);
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Failed to add RevenueCat listener: $e');
      }
    }
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
  // USAGE TRACKING
  // ============================================

  /// Refresh usage from the server if TTL has expired (or forced).
  Future<void> refreshUsageIfStale({bool force = false}) async {
    if (!force &&
        _usageLoadedAt != null &&
        DateTime.now().difference(_usageLoadedAt!) < _usageTtl) {
      return; // Still fresh
    }

    try {
      final authToken = SupabaseService.accessToken;
      if (authToken == null) return;

      final data = await ApiService.getUsage(authToken);
      _generationsUsed = data['generations_used'] as int? ?? 0;
      _iterationsUsed = data['iterations_used'] as int? ?? 0;

      final limits = data['limits'] as Map<String, dynamic>?;
      if (limits != null) {
        _freeGenerationLimit = limits['free_generations'] as int? ?? 5;
        _freeIterationLimit = limits['free_iterations'] as int? ?? 2;
      }

      _usageLoadedAt = DateTime.now();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Usage refresh failed: $e');
      }
      // Fail-open: don't block the user, server enforcement is the backstop
    }
  }

  /// Optimistic bump after a generation starts. Reconciles with server.
  void recordGenerationUsed() {
    _generationsUsed++;
    notifyListeners();
    refreshUsageIfStale(force: true);
  }

  /// Optimistic bump after a retry succeeds. Reconciles with server.
  void recordIterationUsed() {
    _iterationsUsed++;
    notifyListeners();
    refreshUsageIfStale(force: true);
  }

  // ============================================
  // FREEMIUM GATES
  // ============================================

  /// Gate: returns true if the user can start a new generation.
  /// If not premium and over limit, shows paywall. Returns true if premium after paywall.
  Future<bool> ensureCanGenerate({required String source}) async {
    try {
      if (_isPremium) return true;

      // Re-check premium in case of stale state
      await refreshStatus();
      if (_isPremium) return true;

      // Check usage
      await refreshUsageIfStale();
      if (canGenerate) return true;

      // Over limit — show paywall
      await showPaywall(source: source);
      return _isPremium;
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('ensureCanGenerate error: $e');
      }
      // Fail-open: allow through, server enforcement is the backstop
      return true;
    }
  }

  /// Gate: returns true if the user can retry/iterate.
  /// If not premium and over limit, shows paywall. Returns true if premium after paywall.
  Future<bool> ensureCanIterate({required String source}) async {
    try {
      if (_isPremium) return true;

      await refreshStatus();
      if (_isPremium) return true;

      await refreshUsageIfStale();
      if (canIterate) return true;

      // Over limit — show paywall
      await showPaywall(source: source);
      return _isPremium;
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('ensureCanIterate error: $e');
      }
      return true;
    }
  }

  // ============================================
  // LEGACY GATE (kept for compatibility)
  // ============================================

  /// Gate method: returns true if the user is premium, else shows the paywall.
  Future<bool> ensurePremium({required String source}) async {
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
    await refreshUsageIfStale(force: true);
  }

  /// Call when user signs out.
  Future<void> onUserLoggedOut() async {
    await RevenueCatService.logOut();
    _isPremium = false;
    _generationsUsed = 0;
    _iterationsUsed = 0;
    _usageLoadedAt = null;
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
