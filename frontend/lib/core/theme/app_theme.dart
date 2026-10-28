import 'package:flutter/material.dart';

/// Design tokens and Material 3 theme configuration for AEGISCORE AI.
/// Provides a dark-first cybersecurity SaaS aesthetic with restrained teal/cyan accents.
class AppTheme {
  AppTheme._();

  // Primary brand palette (Restrained teal & cybersecurity cyan)
  static const Color primaryTeal = Color(0xFF00C49F);
  static const Color primaryTealLight = Color(0xFF33DFBD);
  static const Color primaryTealDark = Color(0xFF00967A);

  static const Color accentCyan = Color(0xFF0EA5E9);
  static const Color accentBlue = Color(0xFF3B82F6);

  // Surface & background dark hierarchy
  static const Color scaffoldBackground = Color(0xFF0A0F18);
  static const Color surfaceDark = Color(0xFF101928);
  static const Color surfaceVariant = Color(0xFF16233B);
  static const Color cardBackground = Color(0xFF121E33);
  static const Color cardBorder = Color(0xFF1E3252);
  static const Color cardBorderFocused = Color(0xFF00C49F);

  // Status & Severity Indicators
  static const Color severityCritical = Color(0xFFEF4444);
  static const Color severityHigh = Color(0xFFF97316);
  static const Color severityMedium = Color(0xFFF59E0B);
  static const Color severityLow = Color(0xFF3B82F6);
  static const Color severityInfo = Color(0xFF64748B);

  static const Color statusVerified = Color(0xFF10B981);
  static const Color statusChallenged = Color(0xFFF59E0B);
  static const Color statusRejected = Color(0xFFEF4444);
  static const Color statusAbstained = Color(0xFF94A3B8);

  // Claim category colors
  static const Color claimFact = Color(0xFF10B981);
  static const Color claimHypothesis = Color(0xFF38BDF8);
  static const Color claimUnknown = Color(0xFF94A3B8);
  static const Color claimAssertion = Color(0xFFA855F7);

  // Typography colors
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get darkTheme {
    final colorScheme = ColorScheme(
      brightness: Brightness.dark,
      primary: primaryTeal,
      onPrimary: Colors.black,
      primaryContainer: primaryTealDark.withValues(alpha: 0.3),
      onPrimaryContainer: primaryTealLight,
      secondary: accentCyan,
      onSecondary: Colors.black,
      secondaryContainer: accentBlue.withValues(alpha: 0.25),
      onSecondaryContainer: const Color(0xFF93C5FD),
      tertiary: accentBlue,
      onTertiary: Colors.white,
      error: severityCritical,
      onError: Colors.white,
      surface: surfaceDark,
      onSurface: textPrimary,
      surfaceContainerHighest: surfaceVariant,
      outline: cardBorder,
      outlineVariant: cardBorder.withValues(alpha: 0.5),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: scaffoldBackground,
      canvasColor: surfaceDark,
      dividerColor: cardBorder,
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceDark,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: textPrimary),
      ),
      cardTheme: CardThemeData(
        color: cardBackground,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: cardBorder, width: 1),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceVariant,
        side: const BorderSide(color: cardBorder),
        labelStyle: const TextStyle(fontSize: 12, color: textPrimary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: surfaceDark,
        selectedIconTheme: IconThemeData(color: primaryTeal),
        unselectedIconTheme: IconThemeData(color: textMuted),
        selectedLabelTextStyle: TextStyle(
          color: primaryTeal,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: textMuted,
          fontWeight: FontWeight.w500,
          fontSize: 12,
        ),
        indicatorColor: Colors.transparent,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surfaceDark,
        indicatorColor: primaryTeal.withValues(alpha: 0.15),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(
              color: primaryTeal,
              fontWeight: FontWeight.w600,
              fontSize: 12,
            );
          }
          return const TextStyle(
            color: textMuted,
            fontWeight: FontWeight.w500,
            fontSize: 12,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: primaryTeal);
          }
          return const IconThemeData(color: textMuted);
        }),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: primaryTeal, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: severityCritical),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
        labelStyle: const TextStyle(color: textSecondary),
        hintStyle: const TextStyle(color: textMuted),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryTeal,
          foregroundColor: const Color(0xFF031612),
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          side: const BorderSide(color: cardBorder),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryTeal,
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        ),
      ),
    );
  }
}
