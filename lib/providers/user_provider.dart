import 'package:flutter/foundation.dart';
import '../models/user.dart';

class UserProvider extends ChangeNotifier {
  AuthState _authState = AuthState.unauthenticated;
  User _user = User.empty();

  // Getters
  AuthState get authState => _authState;
  User get user => _user;
  bool get isAuthenticated => _authState == AuthState.authenticated;
  bool get isAuthenticating => _authState == AuthState.authenticating;

  // Sign in with Google (mock implementation)
  Future<void> signInWithGoogle() async {
    try {
      // Set authenticating state
      _authState = AuthState.authenticating;
      notifyListeners();

      // Simulate network delay
      await Future.delayed(const Duration(milliseconds: 1500));

      // Simulate random failure for testing (20% chance)
      // Remove this line in production
      if (DateTime.now().millisecondsSinceEpoch % 5 == 0) {
        throw Exception('Mock authentication failed');
      }

      // Mock successful authentication
      _user = const User(
        id: 'mock_user_123',
        name: 'John Doe',
        email: 'john.doe@example.com',
        photoUrl: 'https://via.placeholder.com/150',
      );

      _authState = AuthState.authenticated;
      notifyListeners();

      if (kDebugMode) {
        print('✅ User signed in successfully: ${_user.name}');
      }
    } catch (e) {
      // Handle error
      _authState = AuthState.unauthenticated;
      _user = User.empty();
      notifyListeners();

      if (kDebugMode) {
        print('❌ Sign in failed: $e');
      }
      rethrow;
    }
  }

  // Sign out
  Future<void> signOut() async {
    _authState = AuthState.unauthenticated;
    _user = User.empty();
    notifyListeners();

    if (kDebugMode) {
      print('👋 User signed out');
    }
  }

  // Reset to initial state
  void reset() {
    _authState = AuthState.unauthenticated;
    _user = User.empty();
    notifyListeners();
  }
}
