import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../utils/logger.dart';

/// Supabase service for authentication and client access.
///
/// Initialize in main.dart before runApp:
/// ```dart
/// await SupabaseService.initialize();
/// ```
class SupabaseService {
  // Supabase project configuration
  static const String _supabaseUrl = 'https://ocjxdxkugztdthpehkhm.supabase.co';
  static const String _supabaseAnonKey = 'sb_publishable_vTPYfC80qr9rAoQNPYioOQ_fssreR4P';

  // Google OAuth client IDs
  static const String _googleWebClientId = '331774678727-f5u1tf88duhp9hpgcebs0fe1s7psncvd.apps.googleusercontent.com';
  static const String _googleIosClientId = '331774678727-6r50kaulqi0pcnqqtupsdt2ugp1b9bc9.apps.googleusercontent.com';

  // Secure storage for session persistence
  static final FlutterSecureStorage _secureStorage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  // ============================================
  // CLIENT ACCESS
  // ============================================

  /// Get the Supabase client instance.
  static SupabaseClient get client => Supabase.instance.client;

  /// Get the current authenticated user (null if not authenticated).
  static User? get currentUser => client.auth.currentUser;

  /// Get the current session (null if not authenticated).
  static Session? get currentSession => client.auth.currentSession;

  /// Get the current access token (null if not authenticated).
  static String? get accessToken => currentSession?.accessToken;

  /// Check if user is authenticated.
  static bool get isAuthenticated => currentUser != null;

  // ============================================
  // INITIALIZATION
  // ============================================

  /// Initialize Supabase. Call this in main.dart before runApp.
  static Future<void> initialize() async {
    await Supabase.initialize(
      url: _supabaseUrl,
      anonKey: _supabaseAnonKey,
      authOptions: FlutterAuthClientOptions(
        authFlowType: AuthFlowType.pkce,
        localStorage: SecureLocalStorage(_secureStorage),
      ),
    );

    if (kDebugMode) {
      AppLogger.info('Supabase initialized');
      if (currentSession != null) {
        AppLogger.info('Existing session found for: ${currentUser?.email}');
      }
    }
  }

  // ============================================
  // AUTH STATE STREAM
  // ============================================

  /// Stream of authentication state changes.
  /// Listen to this to react to sign in/out events.
  static Stream<AuthState> get authStateChanges => client.auth.onAuthStateChange;

  // ============================================
  // GOOGLE OAUTH
  // ============================================

  /// Sign in with Google OAuth.
  /// Requires Google Sign In to be configured in the Supabase dashboard
  /// with "Skip nonce check" enabled for iOS.
  static Future<AuthResponse> signInWithGoogle() async {
    final GoogleSignIn googleSignIn = GoogleSignIn(
      clientId: _googleIosClientId,
      serverClientId: _googleWebClientId,
    );

    final googleUser = await googleSignIn.signIn();
    if (googleUser == null) {
      throw const AuthException('Google sign in was cancelled');
    }

    final googleAuth = await googleUser.authentication;
    final idToken = googleAuth.idToken;
    final accessToken = googleAuth.accessToken;

    if (idToken == null) {
      throw const AuthException('No ID token received from Google');
    }

    final response = await client.auth.signInWithIdToken(
      provider: OAuthProvider.google,
      idToken: idToken,
      accessToken: accessToken,
    );

    if (kDebugMode) {
      AppLogger.info('User signed in with Google: ${response.user?.email}');
    }

    return response;
  }

  // ============================================
  // APPLE OAUTH
  // ============================================

  /// Sign in with Apple.
  /// Apple Sign In is required by Apple if you offer any other OAuth provider.
  static Future<AuthResponse> signInWithApple() async {
    // Generate nonce for security
    final rawNonce = _generateNonce();
    final hashedNonce = sha256.convert(utf8.encode(rawNonce)).toString();

    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
      nonce: hashedNonce,
    );

    final idToken = credential.identityToken;
    if (idToken == null) {
      throw const AuthException('No ID token received from Apple');
    }

    final response = await client.auth.signInWithIdToken(
      provider: OAuthProvider.apple,
      idToken: idToken,
      nonce: rawNonce,
    );

    if (kDebugMode) {
      AppLogger.info('User signed in with Apple: ${response.user?.email}');
    }

    return response;
  }

  // ============================================
  // SIGN OUT
  // ============================================

  /// Sign out the current user and clear stored session.
  static Future<void> signOut() async {
    await client.auth.signOut();
    await _secureStorage.deleteAll();

    if (kDebugMode) {
      AppLogger.info('User signed out');
    }
  }

  // ============================================
  // SESSION MANAGEMENT
  // ============================================

  /// Refresh the current session.
  static Future<AuthResponse> refreshSession() async {
    return await client.auth.refreshSession();
  }

  // ============================================
  // HELPERS
  // ============================================

  /// Generate a cryptographically secure nonce for Apple Sign In.
  static String _generateNonce([int length = 32]) {
    const charset = '0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._';
    final random = Random.secure();
    return List.generate(length, (_) => charset[random.nextInt(charset.length)]).join();
  }
}

/// Secure storage adapter for Supabase session persistence.
class SecureLocalStorage extends LocalStorage {
  final FlutterSecureStorage _storage;
  static const String _sessionKey = 'supabase_session';

  SecureLocalStorage(this._storage);

  @override
  Future<void> initialize() async {
    // Clean up legacy key from previous implementation
    await _storage.delete(key: 'supabase_access_token');
  }

  @override
  Future<String?> accessToken() async {
    return await _storage.read(key: _sessionKey);
  }

  @override
  Future<bool> hasAccessToken() async {
    return await accessToken() != null;
  }

  @override
  Future<void> persistSession(String persistSessionString) async {
    await _storage.write(key: _sessionKey, value: persistSessionString);
  }

  @override
  Future<void> removePersistedSession() async {
    await _storage.delete(key: _sessionKey);
  }
}
