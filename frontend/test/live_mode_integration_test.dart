import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegiscore_ui/features/assessment_setup/models/assessment_setup_model.dart';
import 'package:aegiscore_ui/features/assessment_setup/screens/assessment_setup_screen.dart';
import 'package:aegiscore_ui/features/evidence/screens/evidence_explorer_screen.dart';
import 'package:aegiscore_ui/features/findings/screens/findings_screen.dart';
import 'package:aegiscore_ui/features/reports/screens/reports_screen.dart';
import 'package:aegiscore_ui/features/settings/screens/settings_screen.dart';
import 'package:aegiscore_ui/main.dart';
import 'package:aegiscore_ui/services/aegiscore_configuration.dart';
import 'package:aegiscore_ui/services/aegiscore_repository.dart';
import 'package:aegiscore_ui/services/authentication.dart';
import 'package:aegiscore_ui/services/providers.dart';

void main() {
  testWidgets(
    'live reports show persisted incomplete and failure diagnostics',
    (tester) async {
      const reportId = 'report_0123456789abcdef0123456789abcdef';
      final report = {
        'report_id': reportId,
        'created_at': '2026-10-28T10:00:00+00:00',
        'fixture_dataset_id': 'synthetic-suite',
        'fixture_dataset_version': '1.0',
        'runner_condition': 'proposed_multi_agent',
        'runner_id': 'fixture-runner',
        'execution_status': 'completed',
        'is_synthetic': true,
        'is_empirical': false,
        'incomplete_case_count': 1,
        'failed_case_count': 1,
        'total_cases': 1,
        'summary': {
          'tp_count': 0,
          'fp_count': 0,
          'fn_count': 1,
          'tn_count': 0,
          'abstained_positive_count': 1,
          'abstained_negative_count': 0,
          'total_cases': 1,
          'metrics': {
            'precision': {
              'value': null,
              'status': 'undefined',
              'definition': 'Undefined fixture precision',
              'numerator': 0,
              'denominator': 0,
            },
          },
        },
        'trial_agreement': {'trial_agreement_rate': 1.0},
        'payload': null,
      };
      final client = MockClient((request) async {
        if (request.url.path.endsWith('/reports')) {
          return http.Response(
            jsonEncode({
              'items': [report],
              'total': 1,
              'offset': 0,
              'limit': 100,
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/reports/$reportId')) {
          return http.Response(
            jsonEncode({
              ...report,
              'payload': {
                'raw_trial_runs': [
                  {
                    'result': {'error_status': 'ScopeViolationError: blocked'},
                  },
                ],
                'aggregated_outcomes': [
                  {'error_status': 'ScopeViolationError: blocked'},
                ],
              },
            }),
            200,
          );
        }
        return http.Response('', 404);
      });
      addTearDown(client.close);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            aegisCoreConfigurationProvider.overrideWithValue(
              AegisCoreConfiguration(
                mode: AegisCoreMode.live,
                baseUri: Uri.parse('http://127.0.0.1/'),
              ),
            ),
            backendHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(home: ReportsScreen()),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text(reportId), findsOneWidget);
      expect(find.textContaining('SYNTHETIC'), findsOneWidget);

      await tester.tap(find.text(reportId));
      await tester.pumpAndSettle();
      expect(find.textContaining('Incomplete: 1'), findsOneWidget);
      expect(find.textContaining('Failed: 1'), findsOneWidget);
      expect(find.text('Recorded failure diagnostics:'), findsOneWidget);
      expect(find.text('ScopeViolationError: blocked'), findsOneWidget);
    },
  );

  testWidgets('live evidence screen renders loading and empty states', (
    tester,
  ) async {
    final response = Completer<http.Response>();
    final client = MockClient((_) => response.future);
    addTearDown(client.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.live,
              baseUri: Uri.parse('http://127.0.0.1/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(client),
        ],
        child: const MaterialApp(home: EvidenceExplorerScreen()),
      ),
    );
    await tester.pump();
    expect(find.text('Loading evidence provenance...'), findsOneWidget);

    response.complete(
      http.Response(
        jsonEncode({
          'items': [],
          'total': 0,
          'approved_source_count': 0,
          'offset': 0,
          'limit': 100,
        }),
        200,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No Approved Evidence Available'), findsOneWidget);
    expect(
      find.textContaining('Missing evidence does not show'),
      findsOneWidget,
    );
  });

  testWidgets('live evidence screen keeps backend errors visible', (
    tester,
  ) async {
    final client = MockClient(
      (_) async => http.Response('{"detail":"private path"}', 503),
    );
    addTearDown(client.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.live,
              baseUri: Uri.parse('http://127.0.0.1/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(client),
        ],
        child: const MaterialApp(home: EvidenceExplorerScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Failed to Load Data'), findsOneWidget);
    expect(find.text('The backend request failed (HTTP 503).'), findsOneWidget);
    expect(find.textContaining('private path'), findsNothing);
  });

  testWidgets('live app shows persisted backend states without demo fallback', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);

    final requestedPaths = <String>[];
    final client = MockClient((request) async {
      requestedPaths.add(request.url.path);
      if (request.url.path.endsWith('/auth/session')) {
        return http.Response(
          jsonEncode({
            'authenticated': true,
            'username': 'widget-test-user',
            'permissions': ['records:read', 'evidence:read'],
            'expires_in': 1200,
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/health')) {
        return http.Response('{"status":"ok"}', 200);
      }
      if (request.url.path.endsWith('/capabilities')) {
        return http.Response(
          jsonEncode({
            'service': 'aegiscore-api',
            'version': '0.1.0',
            'implemented': ['api.health_endpoint', 'api.capabilities_endpoint'],
            'not_implemented': [
              'backend.vulnerability_assessment_workflow',
              'backend.rag',
            ],
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/evidence/approved')) {
        return http.Response(
          jsonEncode({
            'items': [],
            'total': 0,
            'approved_source_count': 0,
            'offset': int.parse(request.url.queryParameters['offset']!),
            'limit': int.parse(request.url.queryParameters['limit']!),
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/dashboard/summary')) {
        return http.Response(
          jsonEncode({
            'session_count': 0,
            'completed_count': 0,
            'incomplete_count': 0,
            'failed_count': 0,
            'verified_run_count': 0,
            'abstained_run_count': 0,
            'finding_count': 0,
            'report_count': 0,
            'synthetic_offline_run_count': 0,
            'empirical_run_count': 0,
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/findings')) {
        return http.Response(
          jsonEncode({'items': [], 'total': 0, 'offset': 0, 'limit': 100}),
          200,
        );
      }
      if (request.url.path.endsWith('/sessions')) {
        return http.Response(
          jsonEncode({'items': [], 'total': 0, 'offset': 0, 'limit': 10}),
          200,
        );
      }
      if (request.url.path.endsWith('/storage/status')) {
        return http.Response(
          jsonEncode({
            'status': 'available',
            'reason': 'ready',
            'supported_record_types': [
              'offline_fixture_sessions',
              'synthetic_evaluation_reports',
            ],
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/reports')) {
        return http.Response(
          jsonEncode({'items': [], 'total': 0, 'offset': 0, 'limit': 100}),
          200,
        );
      }
      return http.Response('Not Found', 404);
    });
    addTearDown(client.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.live,
              baseUri: Uri.parse('http://127.0.0.1/api/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(client),
          sessionTokenStorageProvider.overrideWithValue(
            _TestSessionTokenStorage(List.filled(43, 'R').join()),
          ),
        ],
        child: const AegisCoreApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('LIVE BACKEND MODE: Connected'), findsOneWidget);
    expect(find.text('No persisted replay records'), findsOneWidget);
    expect(find.text('FIND-JS-01'), findsNothing);

    await tester.tap(find.text('Findings'));
    await tester.pumpAndSettle();
    expect(find.text('Security Assessment Findings'), findsOneWidget);
    expect(find.text('No Matching Findings'), findsOneWidget);
    expect(find.text('FIND-JS-01'), findsNothing);

    await tester.tap(find.text('Evidence Explorer'));
    await tester.pumpAndSettle();
    expect(find.text('Evidence & Provenance Explorer'), findsOneWidget);
    expect(find.text('No Approved Evidence Available'), findsOneWidget);
    expect(requestedPaths, contains('/api/evidence/approved'));
    expect(find.text('FIND-JS-01'), findsNothing);

    await tester.tap(find.text('Settings & Status'));
    await tester.pumpAndSettle();
    expect(find.text('LIVE BACKEND MODE'), findsOneWidget);
    expect(find.textContaining('127.0.0.1/api/'), findsOneWidget);
    expect(find.text('api.health_endpoint'), findsOneWidget);
    expect(requestedPaths, contains('/api/capabilities'));
    expect(requestedPaths, contains('/api/storage/status'));
    expect(requestedPaths, contains('/api/findings'));
    expect(requestedPaths, contains('/api/sessions'));

    await tester.tap(find.text('Reports & Metrics'));
    await tester.pumpAndSettle();
    expect(find.text('Persisted Offline Evaluation Reports'), findsOneWidget);
    expect(find.text('No stored evaluation reports'), findsOneWidget);
    expect(requestedPaths, contains('/api/reports'));
  });

  testWidgets('live findings retry an API failure without demo substitution', (
    tester,
  ) async {
    var requestCount = 0;
    var allowSuccess = false;
    final client = MockClient((request) async {
      requestCount++;
      if (!allowSuccess) {
        return http.Response('{"detail":"private diagnostic"}', 503);
      }
      return http.Response(
        jsonEncode({'items': [], 'total': 0, 'offset': 0, 'limit': 100}),
        200,
      );
    });
    addTearDown(client.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.live,
              baseUri: Uri.parse('http://127.0.0.1/api/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(client),
        ],
        child: const MaterialApp(home: FindingsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Failed to Load Data'), findsOneWidget);
    expect(find.text('The backend request failed (HTTP 503).'), findsOneWidget);
    expect(find.textContaining('private diagnostic'), findsNothing);
    expect(requestCount, greaterThan(1));

    final failedRequestCount = requestCount;
    allowSuccess = true;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('No Matching Findings'), findsOneWidget);
    expect(find.text('FIND-JS-01'), findsNothing);
    expect(requestCount, greaterThan(failedRequestCount));
  });

  testWidgets('settings keeps unavailable storage distinct from empty storage', (
    tester,
  ) async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/capabilities')) {
        return http.Response(
          jsonEncode({
            'service': 'aegiscore-api',
            'version': '0.1.0',
            'implemented': ['api.health_endpoint', 'api.capabilities_endpoint'],
            'not_implemented': ['backend.vulnerability_assessment_workflow'],
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/storage/status')) {
        return http.Response(
          jsonEncode({
            'status': 'unavailable',
            'reason': 'not_configured',
            'supported_record_types': [
              'offline_fixture_sessions',
              'synthetic_evaluation_reports',
            ],
          }),
          200,
        );
      }
      return http.Response('', 404);
    });
    addTearDown(client.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            AegisCoreConfiguration(
              mode: AegisCoreMode.live,
              baseUri: Uri.parse('http://127.0.0.1/api/'),
            ),
          ),
          backendHttpClientProvider.overrideWithValue(client),
        ],
        child: const MaterialApp(home: SettingsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('No local persistence path is configured on the backend.'),
      findsOneWidget,
    );
    expect(find.text('Store status:'), findsOneWidget);
    expect(find.text('UNAVAILABLE'), findsOneWidget);
    expect(
      find.text(
        'Persisted offline replay sessions and synthetic evaluation reports are available.',
      ),
      findsNothing,
    );
  });

  testWidgets(
    'live assessment setup disables submission without a backend contract',
    (tester) async {
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            aegisCoreConfigurationProvider.overrideWithValue(
              AegisCoreConfiguration(
                mode: AegisCoreMode.live,
                baseUri: Uri.parse('http://127.0.0.1/'),
              ),
            ),
            backendHttpClientProvider.overrideWithValue(
              MockClient((_) async => http.Response('', 404)),
            ),
          ],
          child: const MaterialApp(home: AssessmentSetupScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining(
          'has no authorized offline assessment execution endpoint',
        ),
        findsOneWidget,
      );
      expect(find.text('Submission Unavailable'), findsOneWidget);
    },
  );

  testWidgets('repeated taps create at most one demo setup session', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    final repository = _CountingDemoRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [aegisCoreRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: AssessmentSetupScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final confirmation = find.byType(CheckboxListTile).last;
    await tester.ensureVisible(confirmation);
    await tester.tap(confirmation);
    await tester.pump();

    final submitLabel = find.text('Create Demo Session');
    await tester.ensureVisible(submitLabel);
    await tester.tap(submitLabel);
    await tester.tap(submitLabel);
    await tester.pump();
    await tester.pump();

    expect(repository.submitCount, 1);
    repository.session.complete('DEMO-SESSION-1');
    await tester.pumpAndSettle();
    expect(
      find.textContaining('No backend assessment was executed.'),
      findsOneWidget,
    );
  });
}

class _TestSessionTokenStorage implements SessionTokenStorage {
  String? token;

  _TestSessionTokenStorage(this.token);

  @override
  Future<String?> read() async => token;

  @override
  Future<void> write(String value) async => token = value;

  @override
  Future<void> delete() async => token = null;
}

class _CountingDemoRepository extends DemoAegisCoreRepository {
  int submitCount = 0;
  final Completer<String> session = Completer<String>();

  @override
  Future<bool> validateLabScope(String targetUrl) async => true;

  @override
  Future<String> submitAssessmentSetup(AssessmentSetupConfig config) {
    submitCount++;
    return session.future;
  }
}
