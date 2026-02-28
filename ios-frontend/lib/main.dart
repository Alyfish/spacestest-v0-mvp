import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'screens/splash_screen.dart';
import 'screens/main_navigation_screen.dart';
import 'theme.dart';
import 'providers/user_provider.dart';
import 'providers/image_provider.dart';
import 'providers/project_provider.dart';
import 'providers/subscription_provider.dart';
import 'constants/api_constants.dart';
import 'services/revenuecat_service.dart';
import 'services/notification_service.dart';
import 'services/supabase_service.dart';
import 'utils/logger.dart';
import 'firebase_options.dart';

const bool _debugBypassAuth = bool.fromEnvironment(
  'DEV_BYPASS_AUTH',
  defaultValue: false,
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (kReleaseMode && ApiConstants.isLoopbackBaseUrl) {
    throw StateError(
      'API_BASE_URL must be set for release builds. '
      'Pass --dart-define=API_BASE_URL=https://<your-backend>/api',
    );
  }

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    AppLogger.info('Firebase initialized');
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  } catch (e) {
    AppLogger.error('Firebase initialization failed', e);
  }
  try {
    await SupabaseService.initialize();
  } catch (e) {
    AppLogger.error('Supabase initialization failed', e);
  }
  try {
    final session = SupabaseService.currentSession;
    await RevenueCatService.initialize(appUserID: session?.user.id);
  } catch (e) {
    AppLogger.error('RevenueCat initialization failed', e);
    if (kReleaseMode) {
      rethrow;
    }
  }
  try {
    await NotificationService.initialize();
  } catch (e) {
    AppLogger.error('NotificationService initialization failed', e);
  }
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (context) => UserProvider()),
        ChangeNotifierProvider(create: (context) => CapturedImageProvider()),
        ChangeNotifierProvider(create: (context) => ProjectProvider()),
        ChangeNotifierProvider(create: (context) => SubscriptionProvider()),
      ],
      child: MaterialApp(
        title: 'Spaces',
        theme: AppTheme.lightTheme,
        home: const _AuthGate(),
      ),
    );
  }
}

/// Cold-start auth gate: shows MainNavigationScreen if a persisted session
/// was restored, otherwise SplashScreen (login flow).
///
/// Reads `Supabase.instance.client.auth.currentSession` directly so there is
/// no dependency on UserProvider being fully hydrated at this point.
/// All subsequent navigation (sign-in, sign-out) is handled by explicit
/// Navigator calls in SplashScreen / ProfileScreen.
class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    if (kDebugMode && _debugBypassAuth) {
      debugPrint('[AUTH_GATE] DEV_BYPASS_AUTH enabled');
      return const MainNavigationScreen();
    }
    final session = Supabase.instance.client.auth.currentSession;
    if (kDebugMode) debugPrint('[AUTH_GATE] session=${session != null}');
    return session != null
        ? const MainNavigationScreen()
        : const SplashScreen();
  }
}
