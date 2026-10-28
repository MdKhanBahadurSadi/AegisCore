/// Named route paths and navigation identifiers for AEGISCORE AI.
class RouteConstants {
  RouteConstants._();

  static const String dashboard = '/';
  static const String assessmentSetup = '/assessment-setup';
  static const String findings = '/findings';
  static const String findingDetails = '/findings/:id';
  static const String sessionDetails = '/sessions/:id';
  static const String evidence = '/evidence';
  static const String reports = '/reports';
  static const String settings = '/settings';

  static String findingDetailsPath(String findingId) => '/findings/$findingId';
  static String sessionDetailsPath(String sessionId) => '/sessions/$sessionId';
}
