import 'package:flutter/material.dart';

class AppTheme {
  // Color Constants
  static const Color primaryColor = Color(0xFFA00534); // Secondary/Primary brand color
  static const Color backgroundColor = Color(0xFFFFFFFF); // White background
  static const Color bodyTextColor = Color(0xFF000000); // Black text
  static const Color grayColor = Color(0xFF8C8C8C); // Gray
  static const Color darkGrayColor = Color(0xFF13283C); // Darker gray
  static const Color greenColor = Color(0xFF05A00A); // Green
  static const Color errorColor = Color(0xFFD32F2F); // Error red color
  static const Color warningColor = Color(0xFFFFC107); // Warning yellow color
  static const Color overlayColor = Color(0x33A00534); // #A00534 with 20% opacity
  static const Color selectedCardBackground = Color(0xFFFAF2F5); // Selected card background
  static const Color selectedCardOutline = Color(0xFFA00534); // Selected card outline
  static const Color unselectedCardOutline = Color(0xFFEBEBEB); // Unselected card outline
  static const Color unselectedCardBackground = Color(0xFFFFFFFF); // Unselected card background

  // Font Families
  static const String primaryFont = 'AnnieUseYourTelescope'; // Main font
  static const String secondaryFont = 'SF Pro Rounded'; // Secondary font
  static const String accentFont = 'Kristi'; // Accent decorative font

  // Theme Data
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      
      // Color Scheme
      colorScheme: const ColorScheme.light(
        primary: primaryColor,
        secondary: primaryColor,
        surface: backgroundColor,
        background: backgroundColor,
        onPrimary: backgroundColor,
        onSecondary: backgroundColor,
        onSurface: bodyTextColor,
        onBackground: bodyTextColor,
        outline: unselectedCardOutline,
      ),

      // Scaffold
      scaffoldBackgroundColor: backgroundColor,

      // App Bar Theme
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundColor,
        foregroundColor: bodyTextColor,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: primaryFont,
          fontSize: 24,
          fontWeight: FontWeight.normal,
          color: bodyTextColor,
        ),
      ),

      // Text Theme
      textTheme: const TextTheme(
        // Display styles (using AnnieUseYourTelescope for titles)
        displayLarge: TextStyle(
          fontFamily: primaryFont,
          fontSize: 32,
          fontWeight: FontWeight.normal,
          color: bodyTextColor,
        ),
        displayMedium: TextStyle(
          fontFamily: primaryFont,
          fontSize: 28,
          fontWeight: FontWeight.normal,
          color: bodyTextColor,
        ),
        displaySmall: TextStyle(
          fontFamily: primaryFont,
          fontSize: 24,
          fontWeight: FontWeight.normal,
          color: bodyTextColor,
        ),

        // Headline styles (using AnnieUseYourTelescope for section titles)
        headlineLarge: TextStyle(
          fontFamily: primaryFont,
          fontSize: 24,
          fontWeight: FontWeight.normal,
          color: primaryColor, // Using the brand color for emphasis
        ),
        headlineMedium: TextStyle(
          fontFamily: primaryFont,
          fontSize: 20,
          fontWeight: FontWeight.normal,
          color: primaryColor,
        ),
        headlineSmall: TextStyle(
          fontFamily: primaryFont,
          fontSize: 18,
          fontWeight: FontWeight.normal,
          color: primaryColor,
        ),

        // Title styles (using SF Pro for subtitles)
        titleLarge: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 18,
          fontWeight: FontWeight.w400,
          color: bodyTextColor,
        ),
        titleMedium: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: bodyTextColor,
        ),
        titleSmall: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: bodyTextColor,
        ),

        // Body styles (using SF Pro for body text)
        bodyLarge: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: bodyTextColor,
        ),
        bodyMedium: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: bodyTextColor,
        ),
        bodySmall: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: grayColor,
        ),

        // Label styles (using SF Pro for buttons and labels)
        labelLarge: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: bodyTextColor,
        ),
        labelMedium: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: bodyTextColor,
        ),
        labelSmall: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 10,
          fontWeight: FontWeight.w500,
          color: grayColor,
        ),
      ),

      // Button Themes
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: backgroundColor,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(25),
          ),
          textStyle: const TextStyle(
            fontFamily: secondaryFont,
            fontSize: 16,
            fontWeight: FontWeight.w500,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryColor,
          side: const BorderSide(color: primaryColor, width: 1),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(25),
          ),
          textStyle: const TextStyle(
            fontFamily: secondaryFont,
            fontSize: 16,
            fontWeight: FontWeight.w500,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryColor,
          textStyle: const TextStyle(
            fontFamily: secondaryFont,
            fontSize: 16,
            fontWeight: FontWeight.w500,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        ),
      ),

      // Card Theme
      cardTheme: CardThemeData(
        color: backgroundColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(
            color: unselectedCardOutline,
            width: 1,
          ),
        ),
        margin: const EdgeInsets.all(8),
      ),

      // Input Decoration Theme
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: backgroundColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: unselectedCardOutline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: unselectedCardOutline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryColor, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Colors.red),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        hintStyle: const TextStyle(
          fontFamily: secondaryFont,
          color: grayColor,
        ),
        labelStyle: const TextStyle(
          fontFamily: secondaryFont,
          color: grayColor,
        ),
      ),

      // Floating Action Button Theme
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primaryColor,
        foregroundColor: backgroundColor,
        elevation: 4,
      ),

      // Bottom Navigation Bar Theme
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: backgroundColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: grayColor,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
        unselectedLabelStyle: TextStyle(
          fontFamily: secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w400,
        ),
      ),
    );
  }

  // Custom Card Styles
  static BoxDecoration get selectedCardDecoration => BoxDecoration(
    color: selectedCardBackground,
    borderRadius: BorderRadius.circular(12),
    border: Border.all(
      color: selectedCardOutline,
      width: 2,
    ),
  );

  static BoxDecoration get unselectedCardDecoration => BoxDecoration(
    color: unselectedCardBackground,
    borderRadius: BorderRadius.circular(12),
    border: Border.all(
      color: unselectedCardOutline,
      width: 1,
    ),
  );

  // Custom Text Styles for specific use cases
  static const TextStyle logoTextStyle = TextStyle(
    fontFamily: primaryFont,
    fontSize: 28,
    fontWeight: FontWeight.normal,
    color: bodyTextColor,
  );

  static const TextStyle sectionTitleStyle = TextStyle(
    fontFamily: primaryFont,
    fontSize: 24,
    fontWeight: FontWeight.normal,
    color: primaryColor,
  );

  // Accent subtitle (script) style using Kristi to complement the logo
  static const TextStyle accentSubtitleStyle = TextStyle(
    fontFamily: accentFont,
    fontSize: 24,
    fontWeight: FontWeight.w400,
    color: primaryColor,
    height: 1.1,
  );

  static const TextStyle subtitleStyle = TextStyle(
    fontFamily: secondaryFont,
    fontSize: 16,
    fontWeight: FontWeight.w400,
    color: grayColor,
  );

  static const TextStyle buttonTextStyle = TextStyle(
    fontFamily: secondaryFont,
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: backgroundColor,
  );

  static const TextStyle captionStyle = TextStyle(
    fontFamily: secondaryFont,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: grayColor,
  );
}
