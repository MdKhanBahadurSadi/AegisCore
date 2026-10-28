import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../constants/route_constants.dart';
import 'authenticated_shell.dart';
import '../../features/dashboard/screens/dashboard_screen.dart';
import '../../features/assessment_setup/screens/assessment_setup_screen.dart';
import '../../features/findings/screens/findings_screen.dart';
import '../../features/findings/screens/finding_details_screen.dart';
import '../../features/sessions/screens/session_details_screen.dart';
import '../../features/evidence/screens/evidence_explorer_screen.dart';
import '../../features/reports/screens/reports_screen.dart';
import '../../features/settings/screens/settings_screen.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>(
  debugLabel: 'root',
);
final GlobalKey<NavigatorState> _shellNavigatorKey = GlobalKey<NavigatorState>(
  debugLabel: 'shell',
);

/// Central GoRouter configuration for AEGISCORE AI.
final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: RouteConstants.dashboard,
  routes: [
    ShellRoute(
      navigatorKey: _shellNavigatorKey,
      builder: (context, state, child) {
        return AuthenticatedShell(child: child);
      },
      routes: [
        GoRoute(
          path: RouteConstants.dashboard,
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: RouteConstants.assessmentSetup,
          builder: (context, state) => const AssessmentSetupScreen(),
        ),
        GoRoute(
          path: RouteConstants.findings,
          builder: (context, state) => const FindingsScreen(),
        ),
        GoRoute(
          path: RouteConstants.findingDetails,
          builder: (context, state) {
            final id = state.pathParameters['id'] ?? '';
            return FindingDetailsScreen(findingId: id);
          },
        ),
        GoRoute(
          path: RouteConstants.sessionDetails,
          builder: (context, state) {
            final id = state.pathParameters['id'] ?? '';
            return SessionDetailsScreen(sessionId: id);
          },
        ),
        GoRoute(
          path: RouteConstants.evidence,
          builder: (context, state) => const EvidenceExplorerScreen(),
        ),
        GoRoute(
          path: RouteConstants.reports,
          builder: (context, state) => const ReportsScreen(),
        ),
        GoRoute(
          path: RouteConstants.settings,
          builder: (context, state) => const SettingsScreen(),
        ),
      ],
    ),
  ],
);
