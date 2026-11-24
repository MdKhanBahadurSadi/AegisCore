import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegiscore_ui/features/assessment_setup/screens/assessment_details_screen.dart';
import 'package:aegiscore_ui/features/assessment_setup/screens/assessment_setup_screen.dart';
import 'package:aegiscore_ui/services/aegiscore_configuration.dart';
import 'package:aegiscore_ui/services/aegiscore_repository.dart';
import 'package:aegiscore_ui/services/api_aegiscore_repository.dart';
import 'package:aegiscore_ui/services/providers.dart';

void main() {
  testWidgets('setup creates through the existing target-only API contract', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    http.Request? createRequest;
    final client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/assessments') {
        return http.Response(
          jsonEncode({'items': [], 'total': 0, 'offset': 0, 'limit': 50}),
          200,
        );
      }
      if (request.method == 'POST' && request.url.path == '/assessments') {
        createRequest = request;
        return http.Response(
          jsonEncode({
            'assessment_id': _assessmentId,
            'target_url': 'http://127.0.0.1:3000',
            'status': 'created',
            'created_at': '2026-11-24T10:00:00Z',
            'updated_at': null,
            'execution_result': null,
          }),
          201,
        );
      }
      return http.Response('', 404);
    });
    final repository = ApiAegisCoreRepository(
      configuration: AegisCoreConfiguration(
        mode: AegisCoreMode.live,
        baseUri: Uri.parse('http://127.0.0.1:8000/'),
      ),
      client: client,
    );
    final router = GoRouter(
      initialLocation: '/setup',
      routes: [
        GoRoute(
          path: '/setup',
          builder: (context, state) => const AssessmentSetupScreen(),
        ),
        GoRoute(
          path: '/assessments/:id',
          builder: (context, state) => Text(state.pathParameters['id']!),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [aegisCoreRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byType(CheckboxListTile).first);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Create Assessment'));
    await tester.tap(find.text('Create Assessment'));
    await tester.pumpAndSettle();

    expect(createRequest, isNotNull);
    expect(createRequest!.method, 'POST');
    expect(jsonDecode(createRequest!.body), {
      'target_url': 'http://127.0.0.1:3000',
    });
    expect(find.text(_assessmentId), findsOneWidget);
  });

  testWidgets('renders deterministic findings separately from advisory text', (
    tester,
  ) async {
    await _pumpDetails(tester, _repository());

    expect(find.text('Official deterministic findings'), findsOneWidget);
    expect(find.text('Strict transport policy missing'), findsOneWidget);
    expect(find.text('MEDIUM'), findsOneWidget);
    expect(find.textContaining(_evidenceId), findsAtLeast(1));
    expect(find.text('AI advisory • non-authoritative'), findsOneWidget);
    expect(find.text('ADVISORY ONLY'), findsOneWidget);
    expect(
      find.textContaining('This observation could indicate a policy gap.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('References deterministic finding'),
      findsOneWidget,
    );
  });

  testWidgets('execution action refreshes the persisted terminal state', (
    tester,
  ) async {
    var executed = false;
    final client = MockClient((request) async {
      if (request.method == 'POST' &&
          request.url.path == '/assessments/$_assessmentId/execute') {
        executed = true;
        return http.Response(
          jsonEncode({
            'assessment_id': _assessmentId,
            'target_url': 'http://127.0.0.1:3000',
            'status': 'completed',
            'created_at': '2026-11-24T10:00:00Z',
            'updated_at': '2026-11-24T10:00:02Z',
            'execution_result': {
              'outcome': 'Passive HEAD completed.',
              'ai_review': {
                'status': 'disabled',
                'analysis_type': 'advisory_inference',
                'confidence_calibrated': false,
                'factual_support': 'not_evaluated',
                'reviews': [],
              },
            },
          }),
          200,
        );
      }
      if (request.url.path == '/assessments/$_assessmentId') {
        return http.Response(
          jsonEncode({
            'assessment_id': _assessmentId,
            'target_url': 'http://127.0.0.1:3000',
            'status': executed ? 'completed' : 'created',
            'created_at': '2026-11-24T10:00:00Z',
            'updated_at': '2026-11-24T10:00:02Z',
            'execution_result': executed
                ? {
                    'outcome': 'Passive HEAD completed.',
                    'ai_review': {
                      'status': 'disabled',
                      'analysis_type': 'advisory_inference',
                      'confidence_calibrated': false,
                      'factual_support': 'not_evaluated',
                      'reviews': [],
                    },
                  }
                : null,
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/findings') ||
          request.url.path.endsWith('/evidence')) {
        return http.Response(jsonEncode({'items': [], 'total': 0}), 200);
      }
      return http.Response('', 404);
    });
    final repository = ApiAegisCoreRepository(
      configuration: AegisCoreConfiguration(
        mode: AegisCoreMode.live,
        baseUri: Uri.parse('http://127.0.0.1:8000/'),
      ),
      client: client,
    );

    await _pumpDetails(tester, repository);
    expect(find.text('CREATED'), findsOneWidget);
    expect(find.text('Execute passive check'), findsOneWidget);

    await tester.tap(find.text('Execute passive check'));
    await tester.pumpAndSettle();

    expect(executed, isTrue);
    expect(find.text('COMPLETED'), findsOneWidget);
    expect(find.text('Passive HEAD completed.'), findsOneWidget);
    expect(find.text('Execute passive check'), findsNothing);
  });

  testWidgets('disabled and unavailable advisory results preserve findings', (
    tester,
  ) async {
    await _pumpDetails(tester, _repository(advisoryStatus: 'disabled'));
    expect(find.text('DISABLED'), findsOneWidget);
    expect(find.text('Strict transport policy missing'), findsOneWidget);
    expect(find.textContaining('reviewer is disabled'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    await _pumpDetails(tester, _repository(advisoryStatus: 'unavailable'));
    expect(find.text('UNAVAILABLE'), findsOneWidget);
    expect(find.text('Strict transport policy missing'), findsOneWidget);
    expect(find.textContaining('reviewer was unavailable'), findsOneWidget);
  });

  testWidgets(
    'fabricated advisory references are rejected, official finding remains',
    (tester) async {
      await _pumpDetails(
        tester,
        _repository(reviewFindingId: 'fnd_${List.filled(32, 'd').join()}'),
      );

      expect(find.text('REJECTED'), findsOneWidget);
      expect(find.textContaining('response was rejected'), findsOneWidget);
      expect(find.text('Strict transport policy missing'), findsOneWidget);
      expect(
        find.textContaining('This observation could indicate'),
        findsNothing,
      );

      await tester.pumpWidget(const SizedBox.shrink());
      await _pumpDetails(
        tester,
        _repository(reviewEvidenceId: 'evi_${List.filled(32, 'e').join()}'),
      );
      expect(find.text('REJECTED'), findsOneWidget);
      expect(find.text('Strict transport policy missing'), findsOneWidget);

      await tester.pumpWidget(const SizedBox.shrink());
      await _pumpDetails(tester, _repository(missingEvidence: true));
      expect(find.text('REJECTED'), findsOneWidget);
      expect(
        find.textContaining('not returned by the evidence API'),
        findsOneWidget,
      );
      expect(find.text('Strict transport policy missing'), findsOneWidget);
    },
  );

  testWidgets(
    'assessment not found and malformed responses show safe error states',
    (tester) async {
      await _pumpDetails(tester, _repository(notFound: true));
      expect(find.text('Assessment was not found.'), findsOneWidget);

      await tester.pumpWidget(const SizedBox.shrink());
      await _pumpDetails(tester, _repository(malformed: true));
      expect(find.textContaining('invalid response'), findsOneWidget);
    },
  );
}

Future<void> _pumpDetails(
  WidgetTester tester,
  AegisCoreRepository repository,
) async {
  tester.view.physicalSize = const Size(1280, 1100);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [aegisCoreRepositoryProvider.overrideWithValue(repository)],
      child: const MaterialApp(
        home: AssessmentDetailsScreen(assessmentId: _assessmentId),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

ApiAegisCoreRepository _repository({
  String advisoryStatus = 'reviewed',
  String? reviewFindingId,
  String? reviewEvidenceId,
  bool missingEvidence = false,
  bool notFound = false,
  bool malformed = false,
}) {
  final client = MockClient((request) async {
    if (request.url.path == '/assessments/$_assessmentId') {
      if (notFound) return http.Response('{}', 404);
      if (malformed) return http.Response('{bad json', 200);
      final advisory = <String, Object?>{
        'status': advisoryStatus,
        'analysis_type': 'advisory_inference',
        'confidence_calibrated': false,
        'factual_support': 'not_evaluated',
        'reviews': advisoryStatus == 'reviewed'
            ? [
                {
                  'finding_id': reviewFindingId ?? _findingId,
                  'evidence_ids': [reviewEvidenceId ?? _evidenceId],
                  'inferred_risk':
                      'This observation could indicate a policy gap.',
                  'uncertainty':
                      'A HEAD observation does not prove exploitability.',
                  'recommendation': 'Review the endpoint policy configuration.',
                },
              ]
            : [],
      };
      return http.Response(
        jsonEncode({
          'assessment_id': _assessmentId,
          'target_url': 'http://127.0.0.1:3000',
          'status': 'completed',
          'created_at': '2026-11-24T10:00:00Z',
          'updated_at': '2026-11-24T10:00:02Z',
          'execution_result': {'ai_review': advisory},
        }),
        200,
      );
    }
    if (request.url.path.endsWith('/findings')) {
      return http.Response(
        jsonEncode({
          'items': [_finding()],
          'total': 1,
        }),
        200,
      );
    }
    if (request.url.path.endsWith('/evidence')) {
      return http.Response(
        jsonEncode({
          'items': missingEvidence ? [] : [_evidence()],
          'total': missingEvidence ? 0 : 1,
        }),
        200,
      );
    }
    return http.Response('', 404);
  });
  return ApiAegisCoreRepository(
    configuration: AegisCoreConfiguration(
      mode: AegisCoreMode.live,
      baseUri: Uri.parse('http://127.0.0.1:8000/'),
    ),
    client: client,
  );
}

Map<String, Object?> _finding() => {
  'finding_id': _findingId,
  'assessment_id': _assessmentId,
  'rule_id': 'strict_transport_security_missing',
  'title': 'Strict transport policy missing',
  'description':
      'The response did not include the configured transport policy header.',
  'classification': 'configuration_observation',
  'severity': 'medium',
  'confidence': 'high',
  'status': 'detected',
  'evidence_ids': [_evidenceId],
  'remediation': 'Configure the expected header for the local service.',
  'created_at': '2026-11-24T10:00:01Z',
};

Map<String, Object?> _evidence() => {
  'evidence_id': _evidenceId,
  'assessment_id': _assessmentId,
  'evidence_type': 'http_security_headers',
  'source': 'passive_head_observation',
  'observed_at': '2026-11-24T10:00:00Z',
  'http_method': 'HEAD',
  'http_status': 200,
  'normalized_headers': <String, String>{},
  'header_flags': <String, String>{},
  'collection_status': 'observed',
  'provenance': <String, Object?>{},
};

const String _assessmentId = 'asm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const String _findingId = 'fnd_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
const String _evidenceId = 'evi_cccccccccccccccccccccccccccccccc';
