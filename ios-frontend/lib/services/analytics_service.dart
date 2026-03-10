import 'package:firebase_analytics/firebase_analytics.dart';
import '../utils/logger.dart';

/// Static service for Firebase Analytics event tracking.
///
/// Follows the same pattern as SupabaseService — all methods are static.
/// Call methods directly: `AnalyticsService.logProjectCreated(projectId: id)`
class AnalyticsService {
  static final FirebaseAnalytics _analytics = FirebaseAnalytics.instance;

  /// Set the user ID for all subsequent analytics events.
  /// Pass empty string to clear on sign-out.
  static Future<void> setUserId(String userId) async {
    try {
      await _analytics.setUserId(id: userId.isEmpty ? null : userId);
    } catch (e) {
      AppLogger.error('Analytics setUserId failed: $e');
    }
  }

  /// Log when a new project is created.
  static Future<void> logProjectCreated({required String projectId}) async {
    await _logEvent('project_created', {'project_id': projectId});
  }

  /// Log when a room image is uploaded.
  static Future<void> logImageUploaded({required String projectId}) async {
    await _logEvent('image_uploaded', {'project_id': projectId});
  }

  /// Log when image generation starts.
  static Future<void> logGenerationStarted({
    required String projectId,
    required int creditsSpent,
  }) async {
    await _logEvent('generation_started', {
      'project_id': projectId,
      'credits_spent': creditsSpent,
    });
  }

  /// Log when image generation completes.
  static Future<void> logGenerationCompleted({
    required String projectId,
    required int creditsSpent,
  }) async {
    await _logEvent('generation_completed', {
      'project_id': projectId,
      'credits_spent': creditsSpent,
    });
  }

  /// Log when a product search is executed.
  static Future<void> logProductSearch({
    required String projectId,
    required String query,
  }) async {
    await _logEvent('product_search', {
      'project_id': projectId,
      'query': query,
    });
  }

  /// Log when credits are purchased.
  static Future<void> logCreditsPurchased({required int amount}) async {
    await _logEvent('credits_purchased', {'amount': amount});
  }

  /// Log when the paywall is shown.
  static Future<void> logPaywallShown({required String source}) async {
    await _logEvent('paywall_shown', {'source': source});
  }

  /// Internal helper to log events with error handling.
  static Future<void> _logEvent(
    String name,
    Map<String, Object> parameters,
  ) async {
    try {
      await _analytics.logEvent(name: name, parameters: parameters);
    } catch (e) {
      AppLogger.error('Analytics logEvent ($name) failed: $e');
    }
  }
}
