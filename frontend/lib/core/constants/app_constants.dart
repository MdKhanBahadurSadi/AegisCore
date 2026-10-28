/// Application-wide constants for AEGISCORE AI Frontend.
class AppConstants {
  AppConstants._();

  static const String appName = 'AEGISCORE AI';
  static const String appSubtitle =
      'Uncertainty-Aware Web Application Security Assessment';
  static const String appVersion = 'v0.1.0-alpha';

  // Lab targets strictly restricted to local containerized testbeds
  static const List<LabTargetConfig> authorizedLabTargets = [
    LabTargetConfig(
      id: 'juice_shop_local',
      name: 'OWASP Juice Shop',
      version: 'v17.1.1',
      defaultUrl: 'http://localhost:3000',
      description:
          'OWASP Juice Shop official containerized lab. Target ports: 3000.',
      status: 'Active Lab',
    ),
    LabTargetConfig(
      id: 'dvwa_local',
      name: 'Damn Vulnerable Web App (DVWA)',
      version: 'v1.10',
      defaultUrl: 'http://localhost:8080',
      description:
          'DVWA PHP/MySQL vulnerable application container. Target ports: 8080.',
      status: 'Active Lab',
    ),
  ];

  static const String demoModeNotice =
      'DEMO FIXTURE MODE: The current view displays offline synthetic demonstration data. '
      'Live target assessment and empirical inference require active authorized testbed connection and supervisor adjudication.';

  static const String calibrationNotice =
      'CONFIDENCE NOTICE: confidence_is_calibrated=false. Probabilistic intervals represent uncalibrated specialist estimates or Wilson score intervals.';
}

class LabTargetConfig {
  final String id;
  final String name;
  final String version;
  final String defaultUrl;
  final String description;
  final String status;

  const LabTargetConfig({
    required this.id,
    required this.name,
    required this.version,
    required this.defaultUrl,
    required this.description,
    required this.status,
  });
}
