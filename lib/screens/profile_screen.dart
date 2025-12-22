import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import '../theme.dart';
import '../providers/user_provider.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Consumer<UserProvider>(
          builder: (context, userProvider, child) {
            return SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title
                  Text('Profile.', style: AppTheme.sectionTitleStyle),
                  const SizedBox(height: 24),

                  // User Info
                  if (userProvider.isAuthenticated) ...[
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: AppTheme.selectedCardDecoration,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 30,
                                backgroundColor: AppTheme.primaryColor,
                                child: Text(
                                  userProvider.user.name
                                          ?.substring(0, 1)
                                          .toUpperCase() ??
                                      'U',
                                  style: const TextStyle(
                                    fontSize: 24,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.backgroundColor,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      userProvider.user.name ?? 'User',
                                      style: const TextStyle(
                                        fontFamily: AppTheme.secondaryFont,
                                        fontSize: 20,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.bodyTextColor,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      userProvider.user.email ??
                                          'user@example.com',
                                      style: const TextStyle(
                                        fontFamily: AppTheme.secondaryFont,
                                        fontSize: 14,
                                        color: AppTheme.grayColor,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton(
                              onPressed: () async {
                                await userProvider.signOut();
                              },
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(color: Colors.red),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: Text(
                                'Sign Out',
                                style: TextStyle(
                                  fontFamily: AppTheme.secondaryFont,
                                  color: Colors.red,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ] else ...[
                    // Not authenticated state
                    Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            IconsaxPlusLinear.profile_circle,
                            size: 80,
                            color: AppTheme.grayColor,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Not signed in',
                            style: TextStyle(
                              fontFamily: AppTheme.primaryFont,
                              fontSize: 24,
                              color: AppTheme.grayColor,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Sign in to access your profile',
                            style: TextStyle(
                              fontFamily: AppTheme.secondaryFont,
                              fontSize: 16,
                              color: AppTheme.grayColor,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
