// User model and authentication states
enum AuthState {
  unauthenticated,
  authenticating,
  authenticated,
}

class User {
  final String? id;
  final String? name;
  final String? email;
  final String? photoUrl;
  final String? token;

  const User({
    this.id,
    this.name,
    this.email,
    this.photoUrl,
    this.token,
  });

  // Create empty user for unauthenticated state
  factory User.empty() {
    return const User();
  }

  // Check if user is authenticated
  bool get isAuthenticated => id != null && id!.isNotEmpty;

  @override
  String toString() {
    return 'User{id: $id, name: $name, email: $email}';
  }
}
