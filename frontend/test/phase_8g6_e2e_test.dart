import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegiscore_ui/core/constants/route_constants.dart';
import 'package:aegiscore_ui/core/navigation/app_router.dart';
import 'package:aegiscore_ui/main.dart';
import 'package:aegiscore_ui/services/aegiscore_configuration.dart';
import 'package:aegiscore_ui/services/authentication.dart';
import 'package:aegiscore_ui/services/providers.dart';

void main() {
  final bundlePath = Platform.environment['AEGISCORE_PHASE_8G6_E2E_BUNDLE'];

  testWidgets(
    'restored authenticated Live Mode renders FastAPI persisted records',
    (tester) async {
      final bundle = jsonDecode(File(bundlePath!).readAsStringSync())
          as Map<String, dynamic>;
      final responses = Map<String, dynamic>.from(
        bundle['responses'] as Map,
      );
      final expected = Map<String, dynamic>.from(bundle['expected'] as Map);
      final accessToken = expected['access_token'] as String;
      final sessionPage = Map<String, dynamic>.from(
        responses['/api/sessions?offset=0&limit=10'] as Map,
      );
      final findingPage = Map<String, dynamic>.from(
        responses['/api/findings?offset=0&limit=100'] as Map,
      );
      final reportPage = Map<String, dynamic>.from(
        responses['/api/reports?offset=0&limit=100'] as Map,
      );
      final session = Map<String, dynamic>.from(
        (sessionPage['items'] as List).single as Map,
      );
      final finding = Map<String, dynamic>.from(
        (findingPage['items'] as List).single as Map,
      );
      final report = Map<String, dynamic>.from(
        (reportPage['items'] as List).single as Map,
      );
      final sessionId = session['session_id'] as String;
      final findingId = finding['finding_id'] as String;
      final reportId = report['report_id'] as String;
      final reportDetail = Map<String, dynamic>.from(
        responses['/api/reports/$reportId'] as Map,
      );
      expect(session['case_id'], expected['case_id']);
      expect(session['run_id'], expected['run_id']);
      expect(
        reportDetail['payload']['manifest']['manifest_id'],
        expected['manifest_id'],
      );
      expect(finding['session_id'], sessionId);
      expect(finding['report_id'], reportId);

      final requestedPaths = <String>[];
      final protectedRequestAuthorizations = <String?>[];
      final client = MockClient((request) async {
        final key = '${request.url.path}${request.url.hasQuery ? '?${request.url.query}' : ''}';
        requestedPaths.add(key);
        if (key == '/api/auth/session' ||
            key.startsWith('/api/dashboard/') ||
            key.startsWith('/api/sessions') ||
            key.startsWith('/api/findings') ||
            key.startsWith('/api/reports') ||
            key.startsWith('/api/evidence/')) {
          protectedRequestAuthorizations.add(
            request.headers['Authorization'] ?? request.headers['authorization'],
          );
        }
        final body = responses[key];
        if (body == null) {
          return http.Response('{"detail":"not found"}', 404);
        }
        return http.Response(jsonEncode(body), 200);
      });
      addTearDown(client.close);

      tester.view.physicalSize = const Size(1440, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      appRouter.go(RouteConstants.dashboard);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            aegisCoreConfigurationProvider.overrideWithValue(
              AegisCoreConfiguration(
                mode: AegisCoreMode.live,
                baseUri: Uri.parse('http://127.0.0.1:8000/api/'),
              ),
            ),
            backendHttpClientProvider.overrideWithValue(client),
            sessionTokenStorageProvider.overrideWithValue(
              _MemorySessionTokenStorage(accessToken),
            ),
          ],
          child: const AegisCoreApp(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('LIVE BACKEND MODE: Connected'), findsOneWidget);
      expect(find.textContaining('Synthetic: 1 • Empirical: 0'), findsOneWidget);
      expect(find.textContaining(expected['case_id'] as String), findsOneWidget);
      expect(find.text('FIND-JS-01'), findsNothing);

      await tester.tap(find.textContaining(expected['case_id'] as String));
      await tester.pumpAndSettle();
      expect(find.textContaining(sessionId), findsWidgets);
      expect(find.text(expected['run_id'] as String), findsOneWidget);
      expect(find.text('SYNTHETIC OFFLINE FIXTURE'), findsOneWidget);

      await tester.tap(find.text('Findings'));
      await tester.pumpAndSettle();
      expect(find.text(findingId), findsOneWidget);
      await tester.tap(find.text(findingId));
      await tester.pumpAndSettle();
      expect(find.textContaining(findingId), findsWidgets);
      expect(find.textContaining('SYNTHETIC OFFLINE FIXTURE REPLAY'), findsOneWidget);
      expect(find.text(finding['rationale'] as String), findsOneWidget);
      expect(find.text(finding['evidence_refs'].first as String), findsOneWidget);

      await tester.tap(find.text('Reports & Metrics'));
      await tester.pumpAndSettle();
      expect(find.text(reportId), findsOneWidget);
      expect(find.textContaining('SYNTHETIC'), findsOneWidget);
      await tester.tap(find.text(reportId));
      await tester.pumpAndSettle();
      expect(find.textContaining('Persisted runs: 1'), findsOneWidget);
      expect(find.textContaining('Aggregated outcomes: 1'), findsOneWidget);

      await tester.tap(find.text('Settings & Status'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining(
          'Persisted offline replay sessions and synthetic evaluation reports are available.',
        ),
        findsOneWidget,
      );

      expect(requestedPaths, contains('/api/health'));
      expect(requestedPaths, contains('/api/dashboard/summary'));
      expect(requestedPaths, contains('/api/sessions?offset=0&limit=10'));
      expect(requestedPaths, contains('/api/sessions/$sessionId'));
      expect(requestedPaths, contains('/api/findings?offset=0&limit=100'));
      expect(requestedPaths, contains('/api/findings/$findingId'));
      expect(requestedPaths, contains('/api/reports?offset=0&limit=100'));
      expect(requestedPaths, contains('/api/reports/$reportId'));
      expect(requestedPaths, contains('/api/storage/status'));
      expect(requestedPaths, contains('/api/auth/session'));
      expect(
        protectedRequestAuthorizations,
        isNotEmpty,
      );
      expect(
        protectedRequestAuthorizations,
        everyElement('Bearer $accessToken'),
      );
      expect(find.text('FIND-JS-01'), findsNothing);
    },
    skip: bundlePath == null,
  );
}

class _MemorySessionTokenStorage implements SessionTokenStorage {
  String? _token;

  _MemorySessionTokenStorage(this._token);

  @override
  Future<String?> read() async => _token;

  @override
  Future<void> write(String token) async => _token = token;

  @override
  Future<void> delete() async => _token = null;
}
