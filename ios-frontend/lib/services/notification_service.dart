import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import '../firebase_options.dart';
import '../utils/logger.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  AppLogger.info('Background message: ${message.messageId}');
}

class NotificationRegistration {
  final String token;
  final String platform;

  const NotificationRegistration({required this.token, required this.platform});
}

class NotificationService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  static void Function(String projectId)? _onNotificationTap;
  static void Function(String newToken)? _onTokenRefresh;

  /// Project ID from a notification that launched the app from terminated state.
  /// Consumed once by the first screen that checks it.
  static String? pendingProjectId;

  static Future<void> initialize({
    void Function(String projectId)? onNotificationTap,
    void Function(String newToken)? onTokenRefresh,
  }) async {
    _onNotificationTap = onNotificationTap;
    _onTokenRefresh = onTokenRefresh;

    await _messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      AppLogger.info(
        'Foreground message: ${message.notification?.title ?? message.messageId}',
      );
    });

    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      AppLogger.info(
        'Notification tap (background): ${message.notification?.title ?? message.messageId}',
      );
      _handleNotificationTap(message);
    });

    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      AppLogger.info(
        'Notification tap (terminated): ${initialMessage.notification?.title ?? initialMessage.messageId}',
      );
      final projectId = initialMessage.data['project_id'] as String?;
      if (projectId != null && projectId.isNotEmpty) {
        pendingProjectId = projectId;
      }
    }

    _messaging.onTokenRefresh.listen((String token) {
      AppLogger.info('FCM token refreshed');
      _onTokenRefresh?.call(token);
    });
  }

  static void _handleNotificationTap(RemoteMessage message) {
    final projectId = message.data['project_id'] as String?;
    if (projectId != null && projectId.isNotEmpty) {
      _onNotificationTap?.call(projectId);
    }
  }

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
