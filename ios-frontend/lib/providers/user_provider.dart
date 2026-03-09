import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart' as supa;
import '../utils/logger.dart';
import '../models/user.dart';
import '../services/supabase_service.dart';

class UserProvider extends ChangeNotifier {
  AuthState _authState = AuthState.unauthenticated;
  User _user = User.empty();
  String? _errorMessage;
  StreamSubscription<supa.AuthState>? _authSub;

  UserProvider() {
    final session = SupabaseService.currentSession;
    final supabaseUser = session?.user;
    if (session != null && supabaseUser != null) {
      _user = User(
        id: supabaseUser.id,
        name:
            _displayNameFromMetadata(supabaseUser.userMetadata) ??
            supabaseUser.email,
        email: supabaseUser.email,
        photoUrl: _photoUrlFromMetadata(supabaseUser.userMetadata),
        token: session.accessToken,
      );
      _authState = AuthState.authenticated;
    }
    _listenAuthState();
  }

  void _listenAuthState() {
    _authSub = SupabaseService.authStateChanges.listen((data) {
      final event = data.event;
      if (event == supa.AuthChangeEvent.signedOut) {
        if (_authState != AuthState.unauthenticated) {
          AppLogger.info('Auth state change: $event — signing out');
          _authState = AuthState.unauthenticated;
          _user = User.empty();
          _errorMessage = null;
          notifyListeners();
        }
      } else if (event == supa.AuthChangeEvent.tokenRefreshed &&
                 data.session != null) {
        _user = User(
          id: _user.id,
          name: _user.name,
          email: _user.email,
          photoUrl: _user.photoUrl,
          token: data.session!.accessToken,
        );
        notifyListeners();
      }
    });
  }

  static String? _displayNameFromMetadata(Map<String, dynamic>? metadata) {
    if (metadata == null) return null;
    return (metadata['full_name'] ??
            metadata['name'] ??
            metadata['display_name'] ??
            metadata['user_name'])
        ?.toString();
  }

  static String? _photoUrlFromMetadata(Map<String, dynamic>? metadata) {
    if (metadata == null) return null;
    return (metadata['avatar_url'] ?? metadata['picture'])?.toString();
  }

  // Getters
  AuthState get authState => _authState;
  User get user => _user;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _authState == AuthState.authenticated;
  bool get isAuthenticating => _authState == AuthState.authenticating;
  bool get isSignedIn => _authState == AuthState.authenticated;

  // Sign in with Google via Supabase OAuth
  Future<void> signInWithGoogle() async {
    try {
      _errorMessage = null;
      _authState = AuthState.authenticating;
      notifyListeners();

      final response = await SupabaseService.signInWithGoogle();
      final signedInUser = response.user ?? SupabaseService.currentUser;
      final session = response.session ?? SupabaseService.currentSession;

      if (signedInUser == null || session == null) {
        throw Exception('Google sign-in succeeded but no session was returned');
      }

      _user = User(
        id: signedInUser.id,
        name:
            _displayNameFromMetadata(signedInUser.userMetadata) ??
            signedInUser.email,
        email: signedInUser.email,
        photoUrl: _photoUrlFromMetadata(signedInUser.userMetadata),
        token: session.accessToken,
      );

      _authState = AuthState.authenticated;
      _errorMessage = null;
      notifyListeners();

      if (kDebugMode) {
        AppLogger.info('✅ User signed in successfully: ${_user.name}');
      }
    } catch (e) {
      _errorMessage = e.toString();
      _authState = AuthState.unauthenticated;
      _user = User.empty();
      notifyListeners();

      if (kDebugMode) {
        AppLogger.error('❌ Sign in failed: $e');
      }
      rethrow;
    }
  }

  // Sign in with Apple via Supabase OAuth
  Future<void> signInWithApple() async {
    try {
      _errorMessage = null;
      _authState = AuthState.authenticating;
      notifyListeners();

      final response = await SupabaseService.signInWithApple();
      final signedInUser = response.user ?? SupabaseService.currentUser;
      final session = response.session ?? SupabaseService.currentSession;

      if (signedInUser == null || session == null) {
        throw Exception('Apple sign-in succeeded but no session was returned');
      }

      _user = User(
        id: signedInUser.id,
        name:
            _displayNameFromMetadata(signedInUser.userMetadata) ??
            signedInUser.email,
        email: signedInUser.email,
        photoUrl: _photoUrlFromMetadata(signedInUser.userMetadata),
        token: session.accessToken,
      );

      _authState = AuthState.authenticated;
      _errorMessage = null;
      notifyListeners();

      if (kDebugMode) {
        AppLogger.info('✅ User signed in successfully: ${_user.name}');
      }
    } catch (e) {
      _errorMessage = e.toString();
      _authState = AuthState.unauthenticated;
      _user = User.empty();
      notifyListeners();

      if (kDebugMode) {
        AppLogger.error('❌ Sign in failed: $e');
      }
      rethrow;
    }
  }

  // Sign out
  Future<void> signOut() async {
    try {
      await SupabaseService.signOut();
    } catch (e) {
      if (kDebugMode) {
        AppLogger.error('Sign out failed at provider level', e);
      }
    } finally {
      _authState = AuthState.unauthenticated;
      _user = User.empty();
      _errorMessage = null;
      notifyListeners();
    }

    if (kDebugMode) {
      AppLogger.info('👋 User signed out');
    }
  }

  // Reset to initial state
  void reset() {
    _authState = AuthState.unauthenticated;
    _user = User.empty();
    _errorMessage = null;
    notifyListeners();
  }

  @visibleForTesting
  void seedTestUser({
    required String userId,
    required String token,
    String? email,
    String? name,
    String? photoUrl,
  }) {
    final normalizedUserId = userId.trim();
    final normalizedToken = token.trim();
    if (normalizedUserId.isEmpty || normalizedToken.isEmpty) {
      throw ArgumentError('userId and token must be non-empty');
    }

    _user = User(
      id: normalizedUserId,
      name: name ?? email ?? normalizedUserId,
      email: email ?? '$normalizedUserId@spaces.local',
      photoUrl: photoUrl,
      token: normalizedToken,
    );
    _authState = AuthState.authenticated;
    _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _authSub?.cancel();
    super.dispose();
  }
}
