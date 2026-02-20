import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import '../utils/logger.dart';

class NotificationRegistration {
  final String token;
  final String platform;

  const NotificationRegistration({required this.token, required this.platform});
}

class NotificationService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  static Future<NotificationRegistration?>
  requestPermissionAndGetToken() async {
    try {
      final settings = await _messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
      );

      final authorized =
          settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional;
      if (!authorized) {
        AppLogger.warning(
          'Push permission not granted '
          '(status=${settings.authorizationStatus.name})',
        );
        return null;
      }

      final token = await _messaging.getToken();
      if (token == null || token.trim().isEmpty) {
        AppLogger.warning('Failed to fetch FCM token');
        return null;
      }

      return NotificationRegistration(
        token: token.trim(),
        platform: _platformName(),
      );
    } catch (e) {
      AppLogger.error('Failed to request push permission/token', e);
      return null;
    }
  }

  static String _platformName() {
    if (defaultTargetPlatform == TargetPlatform.iOS) return 'ios';
    return 'android';
  }
}
