import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/splash_screen.dart';
import 'theme.dart';
import 'providers/user_provider.dart';
import 'providers/image_provider.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (context) => UserProvider()),
        ChangeNotifierProvider(create: (context) => CapturedImageProvider()),
      ],
      child: MaterialApp(
        title: 'Spaces',
        theme: AppTheme.lightTheme,
        home: const SplashScreen(),
      ),
    );
  }
}