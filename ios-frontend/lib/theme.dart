import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // ============================================
  // COLOR TOKENS
  // ============================================
  
  // Backgrounds
  static const Color scaffoldBackground = Color(0xFFFAFAFA); // Off-white
  static const Color surfaceColor = Color(0xFFFFFFFF); // Pure white
  static const Color backgroundColor = Color(0xFFFFFFFF); // Alias for surface
  
  // Text
  static const Color textPrimary = Color(0xFF111111); // Near black
  static const Color textSecondary = Color(0xFF6B7280); // Gray
  static const Color textTertiary = Color(0xFF9CA3AF); // Light gray
  static const Color bodyTextColor = Color(0xFF111111); // Alias for textPrimary
  
  // Borders & Dividers
  static const Color dividerColor = Color(0xFFEFEFEF);
  static const Color cardBorderColor = Color(0xFFEFEFEF);
  static const Color lightGrayColor = Color(0xFFE6E6E6);
  
  // States
  static const Color disabledFill = Color(0xFFF2F2F2);
  static const Color disabledText = Color(0xFFB0B0B0);
  
  // Accent
  static const Color primaryColor = Color(0xFFD02B48); // Brand Red
  static const Color selectedCardBackground = Color(0xFFFFF5F7);
  static const Color selectedCardOutline = Color(0xFFD02B48);
  
  // Legacy/Utility
  static const Color grayColor = Color(0xFF8C8C8C);
  static const Color darkGrayColor = Color(0xFF4A4A4A);
  static const Color greenColor = Color(0xFF05A00A);
  static const Color errorColor = Color(0xFFD32F2F);
  static const Color warningColor = Color(0xFFFFC107);
  static const Color overlayColor = Color(0x33D02B48);
  static const Color unselectedCardOutline = Color(0xFFEFEFEF);
  static const Color unselectedCardBackground = Color(0xFFFFFFFF);
  static const Color transparent = Colors.transparent;

  // ============================================
  // SPACING (8pt grid)
  // ============================================
  static const double spacingXs = 8.0;
  static const double spacingSm = 16.0;
  static const double spacingMd = 24.0;
  static const double spacingLg = 32.0;
  
  static const double screenPadding = 16.0;
  static const double sectionSpacing = 24.0;
  static const double cardPadding = 16.0;

  // ============================================
  // RADII
  // ============================================
  static const double cardRadius = 16.0;
  static const double buttonRadius = 16.0;
  static const double inputRadius = 12.0;

  // ============================================
  // BUTTON SPECS
  // ============================================
  static const double buttonHeight = 56.0;
  static const double minButtonHeight = 56.0;

  // ============================================
  // TYPOGRAPHY (DM Sans)
  // ============================================
  
  /// Base DM Sans text style
  static TextStyle dmSans({
    double fontSize = 16,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? height,
    double? letterSpacing,
  }) {
    return GoogleFonts.dmSans(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color ?? textPrimary,
      height: height,
      letterSpacing: letterSpacing,
      decoration: TextDecoration.none,
    );
  }

  /// Title: 32 / 700 / LH 38
  static TextStyle titleStyle({Color? color}) {
    return GoogleFonts.dmSans(
      fontSize: 32,
      fontWeight: FontWeight.w700,
      color: color ?? textPrimary,
      height: 38 / 32,
      decoration: TextDecoration.none,
    );
  }

  /// Section: 22 / 600 / LH 28
  static TextStyle sectionStyle({Color? color}) {
    return GoogleFonts.dmSans(
      fontSize: 22,
      fontWeight: FontWeight.w600,
      color: color ?? textPrimary,
      height: 28 / 22,
      decoration: TextDecoration.none,
    );
  }

  /// Header: 18-24 / 700 (flexible for app bars etc)
  static TextStyle headerStyle({
    double fontSize = 22,
    Color? color,
  }) {
    return GoogleFonts.dmSans(
      fontSize: fontSize,
      fontWeight: FontWeight.w700,
      color: color ?? textPrimary,
      decoration: TextDecoration.none,
    );
  }

  /// Body: 16 / 400 / LH 24
  static TextStyle bodyStyle({
    double fontSize = 16,
    Color? color,
  }) {
    return GoogleFonts.dmSans(
      fontSize: fontSize,
      fontWeight: FontWeight.w400,
      color: color ?? textPrimary,
      height: 24 / 16,
      decoration: TextDecoration.none,
    );
  }

  /// Caption: 13 / 400 / LH 18
  static TextStyle captionStyle({Color? color}) {
    return GoogleFonts.dmSans(
      fontSize: 13,
      fontWeight: FontWeight.w400,
      color: color ?? textTertiary,
      height: 18 / 13,
      decoration: TextDecoration.none,
    );
  }

  /// Label: 14 / 600
  static TextStyle labelStyle({
    double fontSize = 14,
    Color? color,
  }) {
    return GoogleFonts.dmSans(
      fontSize: fontSize,
      fontWeight: FontWeight.w600,
      color: color ?? darkGrayColor,
      decoration: TextDecoration.none,
    );
  }

  // ============================================
  // THEME DATA
  // ============================================
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      
      colorScheme: const ColorScheme.light(
        primary: primaryColor,
        secondary: primaryColor,
        surface: surfaceColor,
        onPrimary: surfaceColor,
        onSecondary: surfaceColor,
        onSurface: textPrimary,
        outline: cardBorderColor,
      ),

      scaffoldBackgroundColor: scaffoldBackground,

      appBarTheme: AppBarTheme(
        backgroundColor: scaffoldBackground,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: sectionStyle(),
        iconTheme: const IconThemeData(
          color: textPrimary,
          size: 24,
        ),
      ),

      textTheme: TextTheme(
        displayLarge: titleStyle(),
        displayMedium: titleStyle(),
        displaySmall: sectionStyle(),
        headlineLarge: sectionStyle(),
        headlineMedium: headerStyle(fontSize: 20),
        headlineSmall: headerStyle(fontSize: 18),
        titleLarge: headerStyle(fontSize: 18),
        titleMedium: dmSans(fontSize: 16, fontWeight: FontWeight.w500),
        titleSmall: dmSans(fontSize: 14, fontWeight: FontWeight.w500),
        bodyLarge: bodyStyle(),
        bodyMedium: bodyStyle(fontSize: 14),
        bodySmall: captionStyle(),
        labelLarge: labelStyle(),
        labelMedium: labelStyle(fontSize: 12),
        labelSmall: captionStyle(),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: surfaceColor,
          elevation: 0,
          minimumSize: const Size(double.infinity, buttonHeight),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: dmSans(fontSize: 17, fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          side: const BorderSide(color: lightGrayColor, width: 1),
          minimumSize: const Size(double.infinity, buttonHeight),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: dmSans(fontSize: 17, fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryColor,
          textStyle: dmSans(fontSize: 16, fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        ),
      ),

      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(cardRadius),
          side: const BorderSide(color: cardBorderColor, width: 1),
        ),
        margin: const EdgeInsets.all(0),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(inputRadius),
          borderSide: const BorderSide(color: cardBorderColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(inputRadius),
          borderSide: const BorderSide(color: cardBorderColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(inputRadius),
          borderSide: const BorderSide(color: primaryColor, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(inputRadius),
          borderSide: const BorderSide(color: errorColor),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        hintStyle: bodyStyle(color: textTertiary),
        labelStyle: labelStyle(color: textSecondary),
      ),

      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primaryColor,
        foregroundColor: surfaceColor,
        elevation: 4,
        shape: CircleBorder(),
      ),

      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surfaceColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: textTertiary,
        type: BottomNavigationBarType.fixed,
        elevation: 10,
        selectedLabelStyle: dmSans(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: dmSans(fontSize: 11, fontWeight: FontWeight.w400),
      ),

      dividerTheme: const DividerThemeData(
        thickness: 1,
        color: dividerColor,
        space: 1,
      ),
    );
  }

  // ============================================
  // DECORATIONS
  // ============================================
  
  static BoxDecoration get selectedCardDecoration => BoxDecoration(
    color: surfaceColor,
    borderRadius: BorderRadius.circular(cardRadius),
    border: Border.all(color: primaryColor, width: 2),
  );

  static BoxDecoration get unselectedCardDecoration => BoxDecoration(
    color: surfaceColor,
    borderRadius: BorderRadius.circular(cardRadius),
    border: Border.all(color: cardBorderColor, width: 1),
  );

  static BoxDecoration get elevatedCardDecoration => BoxDecoration(
    color: surfaceColor,
    borderRadius: BorderRadius.circular(cardRadius),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withValues(alpha: 0.05),
        blurRadius: 12,
        offset: const Offset(0, 4),
      ),
    ],
  );

  // ============================================
  // DEPRECATED (for backwards compatibility)
  // ============================================
  @Deprecated('Use dmSans() instead')
  static const String primaryFont = 'DM Sans';
  @Deprecated('Use dmSans() instead') 
  static const String secondaryFont = 'DM Sans';
  @Deprecated('Use dmSans() instead')
  static const String accentFont = 'DM Sans';

  @Deprecated('Use headerStyle() instead')
  static TextStyle get logoTextStyle => headerStyle(fontSize: 20);

  @Deprecated('Use sectionStyle() instead')
  static TextStyle get sectionTitleStyle => sectionStyle();

  @Deprecated('Use bodyStyle() instead')
  static TextStyle get subtitleStyle => bodyStyle(color: textSecondary);

  @Deprecated('Use dmSans() with white color instead')
  static TextStyle get buttonTextStyle => dmSans(
    fontSize: 17,
    fontWeight: FontWeight.w600,
    color: surfaceColor,
  );

  // Keep interStyle for backwards compatibility
  static TextStyle interStyle({
    double fontSize = 14,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? height,
  }) {
    return dmSans(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
    );
  }
}
