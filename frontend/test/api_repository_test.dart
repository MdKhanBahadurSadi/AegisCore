import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegiscore_ui/services/aegiscore_configuration.dart';
import 'package:aegiscore_ui/services/aegiscore_repository.dart';
import 'package:aegiscore_ui/services/api_aegiscore_repository.dart';
import 'package:aegiscore_ui/services/backend_contract_models.dart';
import 'package:aegiscore_ui/services/backend_errors.dart';
import 'package:aegiscore_ui/services/backend_assessment_models.dart';
import 'package:aegiscore_ui/services/providers.dart';
import 'package:aegiscore_ui/features/assessment_setup/models/assessment_setup_model.dart';
import 'package:aegiscore_ui/features/evidence/models/evidence_model.dart';

void main() {
  group('ApiAegisCoreRepository', () {
    test('parses the existing health and capabilities contracts', () async {
      final requestedPaths = <String>[];
      final client = MockClient((request) async {
        requestedPaths.add(request.url.path);
        if (request.url.path == '/api/health') {
          return http.Response('{"status":"ok"}', 200);
        }
        return http.Response(
          jsonEncode({
            'service': 'aegiscore-api',
            'version': '0.1.0',
            'implemented': ['api.health_endpoint', 'api.capabilities_endpoint'],
            'not_implemented': ['backend.vulnerability_assessment_workflow'],
          }),
          200,
        );
      });
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(
          baseUri: Uri.parse('http://localhost:8000/api'),
        ),
        client: client,
      );

      expect(await repository.checkBackendHealth(), isTrue);
      final capabilities = await repository.getBackendCapabilities();
      expect(capabilities, isA<BackendCapabilitiesResponse>());
      expect(capabilities.implemented, contains('api.health_endpoint'));
      expect(
        capabilities.notImplemented,
        contains('backend.vulnerability_assessment_workflow'),
      );
      expect(requestedPaths, ['/api/health', '/api/capabilities']);
      client.close();
    });

    test(
      'sends its bearer token and notifies auth when the session expires',
      () async {
        const token = 'signed-in-test-session-token';
        String? requestAuthorization;
        String? expiredToken;
        final client = MockClient((request) async {
          requestAuthorization = request.headers['Authorization'];
          return http.Response('{"detail":"generic"}', 401);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
          accessToken: token,
          onAuthenticationExpired: (value) => expiredToken = value,
        );

        await expectLater(
          repository.getFindings(),
          throwsA(isA<BackendAuthenticationException>()),
        );

        expect(requestAuthorization, 'Bearer $token');
        expect(expiredToken, token);
        client.close();
      },
    );

    test(
      'reports a permission denial without treating it as session expiry',
      () async {
        const token = 'signed-in-test-session-token';
        var expired = false;
        final client = MockClient(
          (_) async => http.Response('{"detail":"private"}', 403),
        );
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
          accessToken: token,
          onAuthenticationExpired: (_) => expired = true,
        );

        await expectLater(
          repository.getEvidenceList(),
          throwsA(isA<BackendAuthorizationException>()),
        );
        expect(expired, isFalse);
        client.close();
      },
    );

    test(
      'loads persisted summary, storage state, findings and synthetic reports',
      () async {
        final requests = <String>[];
        final report = {
          'report_id': 'report_0123456789abcdef0123456789abcdef',
          'created_at': '2026-10-28T10:00:00+00:00',
          'fixture_dataset_id': 'synthetic-suite',
          'fixture_dataset_version': '1.0',
          'runner_condition': 'proposed_multi_agent',
          'runner_id': 'fixture-runner',
          'execution_status': 'completed',
          'is_synthetic': true,
          'is_empirical': false,
          'incomplete_case_count': 0,
          'failed_case_count': 0,
          'total_cases': 1,
          'summary': {
            'tp_count': 1,
            'fp_count': 0,
            'fn_count': 0,
            'tn_count': 0,
            'abstained_positive_count': 0,
            'abstained_negative_count': 0,
            'total_cases': 1,
            'metrics': {
              'precision': {
                'metric_name': 'precision',
                'value': null,
                'status': 'undefined',
                'definition': 'undefined denominator fixture',
                'numerator': 0,
                'denominator': 0,
              },
            },
          },
          'trial_agreement': {'trial_agreement_rate': 1.0},
          'payload': null,
        };
        final finding = {
          'finding_id': 'finding_0123456789abcdef0123456789abcdef',
          'source_finding_id': 'fixture-finding-1',
          'session_id': 'session_0123456789abcdef0123456789abcdef',
          'report_id': report['report_id'],
          'case_id': 'CASE-01',
          'recorded_at': '2026-10-28T10:00:00+00:00',
          'specialist_role': 'offline_fixture_specialist',
          'vulnerability_identified': true,
          'cwe_id': 'CWE-89',
          'severity': 'high',
          'decision': 'verified',
          'evidence_refs': ['fixture-chunk-ref'],
          'rationale': 'Synthetic replay rationale',
          'locus': {
            'target_uri': 'http://127.0.0.1:3000/fixture',
            'parameter': 'item',
            'cwe_id': 'CWE-89',
          },
          'vulnerability_class': 'SQL injection',
          'is_synthetic': true,
          'is_empirical': false,
          'execution_mode': 'offline_fixture',
        };
        final client = MockClient((request) async {
          requests.add(request.url.path);
          if (request.url.path.endsWith('/dashboard/summary')) {
            return http.Response(
              jsonEncode({
                'session_count': 1,
                'completed_count': 1,
                'incomplete_count': 0,
                'failed_count': 0,
                'verified_run_count': 1,
                'abstained_run_count': 0,
                'finding_count': 1,
                'report_count': 1,
                'synthetic_offline_run_count': 1,
                'empirical_run_count': 0,
              }),
              200,
            );
          }
          if (request.url.path.endsWith('/sessions')) {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'session_id': 'session_0123456789abcdef0123456789abcdef',
                    'report_id': report['report_id'],
                    'run_id': 'replay-run-01',
                    'runner_id': 'fixture-runner',
                    'case_id': 'CASE-01',
                    'repeat_index': 0,
                    'started_at': '2026-10-28T09:59:00+00:00',
                    'ended_at': '2026-10-28T10:00:00+00:00',
                    'status': 'completed',
                    'disposition': 'verified',
                    'fixture_dataset_id': 'synthetic-suite',
                    'fixture_dataset_version': '1.0',
                    'execution_mode': 'offline_fixture',
                    'is_synthetic': true,
                    'is_empirical': false,
                    'result': {
                      'case_id': 'CASE-01',
                      'run_id': 'replay-run-01',
                      'decision': 'verified',
                      'findings': [],
                      'error_status': null,
                      'is_incomplete': false,
                    },
                    'case_context': null,
                  },
                ],
                'total': 1,
                'offset': 0,
                'limit': 10,
              }),
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
              jsonEncode({
                'items': [report],
                'total': 1,
                'offset': 0,
                'limit': 100,
              }),
              200,
            );
          }
          if (request.url.path.endsWith('/reports/${report['report_id']}')) {
            return http.Response(
              jsonEncode({
                ...report,
                'payload': {
                  'raw_trial_runs': [
                    {
                      'result': {'error_status': null},
                    },
                  ],
                  'aggregated_outcomes': [{}],
                },
              }),
              200,
            );
          }
          if (request.url.path.endsWith('/findings')) {
            return http.Response(
              jsonEncode({
                'items': [finding],
                'total': 1,
                'offset': 0,
                'limit': 100,
              }),
              200,
            );
          }
          return http.Response('', 404);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        final summary = await repository.getDashboardSummary();
        final sessions = await repository.getRecentSessions();
        final storage = await repository.getStorageStatus();
        final reports = await repository.getStoredEvaluationReports();
        final detail = await repository.getStoredEvaluationReportById(
          report['report_id'] as String,
        );
        final findings = await repository.getFindings();

        expect(summary.empiricalRunCount, 0);
        expect(sessions.single.isSynthetic, isTrue);
        expect(sessions.single.disposition, 'verified');
        expect(storage.status, 'available');
        expect(reports.single.isSynthetic, isTrue);
        expect(reports.single.isEmpirical, isFalse);
        expect(reports.single.metrics['precision']?.value, isNull);
        expect(detail?.rawRunCount, 1);
        expect(findings.single.isPersistedRecord, isTrue);
        expect(findings.single.confidenceScore, isNull);
        expect(findings.single.evidenceIds, ['fixture-chunk-ref']);
        expect(requests, contains('/findings'));
        client.close();
      },
    );

    test('maps HTTP errors without exposing response details', () async {
      final client = MockClient(
        (_) async => http.Response('private detail: token=secret', 503),
      );
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      await expectLater(
        repository.checkBackendHealth(),
        throwsA(
          isA<BackendHttpException>()
              .having((error) => error.statusCode, 'statusCode', 503)
              .having(
                (error) => error.toString(),
                'message',
                isNot(contains('secret')),
              ),
        ),
      );
      client.close();
    });

    test('loads persisted session detail by its exact identifier', () async {
      const sessionId = 'session_0123456789abcdef0123456789abcdef';
      var requestedPath = '';
      final client = MockClient((request) async {
        requestedPath = request.url.path;
        if (request.url.path == '/sessions/$sessionId') {
          return http.Response(
            jsonEncode({
              'session_id': sessionId,
              'report_id': 'report_0123456789abcdef0123456789abcdef',
              'run_id': 'replay-run-01',
              'runner_id': 'fixture-runner',
              'case_id': 'CASE-01',
              'repeat_index': 0,
              'started_at': null,
              'ended_at': null,
              'status': 'completed',
              'disposition': 'verified',
              'fixture_dataset_id': 'synthetic-suite',
              'fixture_dataset_version': '1.0',
              'execution_mode': 'offline_fixture',
              'is_synthetic': true,
              'is_empirical': false,
              'result': {
                'case_id': 'CASE-01',
                'run_id': 'replay-run-01',
                'decision': 'verified',
                'findings': [
                  {'finding_id': 'fixture-finding'},
                ],
                'error_status': null,
                'is_incomplete': false,
              },
              'case_context': {
                'locus': {
                  'target_uri': 'http://127.0.0.1/fixture',
                  'parameter': 'item',
                  'cwe_id': 'CWE-89',
                },
                'vulnerability_class': 'SQL injection',
                'classification': 'TP',
                'is_incomplete': false,
                'error_status': null,
              },
            }),
            200,
          );
        }
        return http.Response('{"detail":"not found"}', 404);
      });
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      final session = await repository.getOfflineSessionById(sessionId);
      expect(requestedPath, '/sessions/$sessionId');
      expect(session?.sessionId, sessionId);
      expect(session?.caseId, 'CASE-01');
      expect(session?.result['findings'], hasLength(1));
      expect(session?.caseContext?['vulnerability_class'], 'SQL injection');
      expect(
        await repository.getOfflineSessionById(
          'session_ffffffffffffffffffffffffffffffff',
        ),
        isNull,
      );
      client.close();
    });

    test('parses approved evidence across deterministic API pages', () async {
      final requestedOffsets = <String?>[];
      final client = MockClient((request) async {
        requestedOffsets.add(request.url.queryParameters['offset']);
        final offset = int.parse(request.url.queryParameters['offset']!);
        return http.Response(
          jsonEncode({
            'items': [_approvedEvidenceItem(id: 'chunk-$offset')],
            'total': 2,
            'approved_source_count': 1,
            'offset': offset,
            'limit': 100,
          }),
          200,
        );
      });
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      final evidence = await repository.getEvidenceList();

      expect(requestedOffsets, ['0', '1']);
      expect(evidence, hasLength(2));
      expect(evidence.first.id, 'chunk-0');
      expect(evidence.first.sourceId, 'source-1');
      expect(evidence.first.approvalStatus, EvidenceApprovalStatus.approved);
      expect(evidence.first.excerpt, 'Use parameterized SQL queries.');
      expect(evidence.first.exactVersion, 'recorded-v1');
      expect(
        evidence.first.canonicalReference,
        'https://example.invalid/guide',
      );
      expect(evidence.first.characterStart, 0);
      expect(evidence.first.characterEnd, 30);
      expect(evidence.first.filePath, isNull);
      expect(evidence.first.relatedFindingIds, isEmpty);
      expect(evidence.first.locusMatch, isNull);
      expect(evidence.first.sourceRevision, 2);
      expect(evidence.first.reviewEventCount, 3);
      expect(evidence.first.provenanceDigest, 'sha256:${_digest('a')}');
      client.close();
    });

    test('keeps an empty approved-evidence response empty', () async {
      final client = MockClient(
        (_) async => http.Response(
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
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      expect(await repository.getEvidenceList(), isEmpty);
      client.close();
    });

    test('maps approved evidence detail 404 to no matching record', () async {
      final client = MockClient(
        (_) async => http.Response('{"detail":"not found"}', 404),
      );
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      expect(await repository.getEvidenceById('missing'), isNull);
      client.close();
    });

    test(
      'preserves evidence service errors and rejects malformed pages',
      () async {
        final unavailableClient = MockClient(
          (_) async => http.Response('{"detail":"private path"}', 503),
        );
        final unavailableRepository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: unavailableClient,
        );
        await expectLater(
          unavailableRepository.getEvidenceList(),
          throwsA(
            isA<BackendHttpException>().having(
              (error) => error.statusCode,
              'statusCode',
              503,
            ),
          ),
        );
        unavailableClient.close();

        final malformedClient = MockClient(
          (_) async => http.Response('{"items":[],"total":0}', 200),
        );
        final malformedRepository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: malformedClient,
        );
        await expectLater(
          malformedRepository.getEvidenceList(),
          throwsA(isA<BackendResponseException>()),
        );
        malformedClient.close();
      },
    );

    test('rejects malformed response payloads', () async {
      final client = MockClient(
        (_) async => http.Response('{"status":"ok","extra":true}', 200),
      );
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      await expectLater(
        repository.checkBackendHealth(),
        throwsA(isA<BackendResponseException>()),
      );
      client.close();
    });

    test(
      'rejects capability values outside the Python literal schema',
      () async {
        final client = MockClient(
          (_) async => http.Response(
            jsonEncode({
              'service': 'aegiscore-api',
              'version': '9.9.9',
              'implemented': ['api.health_endpoint', 'invented.capability'],
              'not_implemented': [],
            }),
            200,
          ),
        );
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        await expectLater(
          repository.getBackendCapabilities(),
          throwsA(isA<BackendResponseException>()),
        );
        client.close();
      },
    );

    test('reports a connection timeout predictably', () async {
      final client = MockClient((_) => Completer<http.Response>().future);
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(
          connectTimeout: const Duration(milliseconds: 10),
        ),
        client: client,
      );

      await expectLater(
        repository.checkBackendHealth(),
        throwsA(
          isA<BackendTimeoutException>().having(
            (error) => error.phase,
            'phase',
            'connection',
          ),
        ),
      );
      client.close();
    });

    test('reports a response body timeout predictably', () async {
      final client = _SlowBodyClient();
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(
          requestTimeout: const Duration(milliseconds: 10),
        ),
        client: client,
      );

      await expectLater(
        repository.checkBackendHealth(),
        throwsA(
          isA<BackendTimeoutException>().having(
            (error) => error.phase,
            'phase',
            'request',
          ),
        ),
      );
      client.close();
    });

    test(
      'live mode exposes persisted API failure and never falls back to demo fixtures',
      () async {
        var requestCount = 0;
        final client = MockClient((_) async {
          requestCount++;
          return http.Response('{"detail":"unavailable"}', 503);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        expect(repository.mode, AegisCoreMode.live);
        await expectLater(
          repository.getFindings(),
          throwsA(isA<BackendHttpException>()),
        );
        expect(requestCount, 1);
        client.close();
      },
    );

    test(
      'does not submit assessments through a missing live endpoint',
      () async {
        final client = MockClient((_) async => http.Response('', 404));
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        await expectLater(
          repository.submitAssessmentSetup(
            const AssessmentSetupConfig(
              labTargetId: 'juice_shop_local',
              targetUrl: 'http://127.0.0.1:3000',
              isAuthorizedLabConfirmed: true,
            ),
          ),
          throwsA(isA<UnsupportedBackendCapabilityException>()),
        );
        client.close();
      },
    );

    test(
      'creates an assessment with only the supported target_url field',
      () async {
        http.Request? captured;
        final client = MockClient((request) async {
          captured = request;
          return http.Response(jsonEncode(_assessmentResponse()), 201);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
          accessToken: 'session-token',
        );

        final assessment = await repository.createAssessment(
          'http://127.0.0.1:3000',
        );

        expect(captured!.method, 'POST');
        expect(captured!.url.path, '/assessments');
        expect(captured!.headers['Authorization'], 'Bearer session-token');
        expect(jsonDecode(captured!.body), {
          'target_url': 'http://127.0.0.1:3000',
        });
        expect(assessment.assessmentId, _assessmentId);
        expect(assessment.status, BackendAssessmentStatus.created);
        client.close();
      },
    );

    test('parses bounded persisted assessment history', () async {
      http.Request? captured;
      final client = MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'items': [_assessmentResponse()],
            'total': 1,
            'offset': 0,
            'limit': 50,
          }),
          200,
        );
      });
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      final page = await repository.getAssessments();

      expect(captured!.method, 'GET');
      expect(captured!.url.path, '/assessments');
      expect(captured!.url.queryParameters, {'offset': '0', 'limit': '50'});
      expect(page.total, 1);
      expect(page.items.single.assessmentId, _assessmentId);
      client.close();
    });

    test('executes through the existing bodyless POST contract', () async {
      http.Request? captured;
      final client = MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode(
            _assessmentResponse(
              status: 'completed',
              executionResult: {
                'reachable': true,
                'outcome': 'Passive HEAD completed.',
                'ai_review': _reviewResponse(status: 'disabled', reviews: []),
              },
            ),
          ),
          200,
        );
      });
      final repository = ApiAegisCoreRepository(
        configuration: _configuration(),
        client: client,
      );

      final assessment = await repository.executeAssessment(_assessmentId);

      expect(captured!.method, 'POST');
      expect(captured!.url.path, '/assessments/$_assessmentId/execute');
      expect(captured!.body, isEmpty);
      expect(assessment.status, BackendAssessmentStatus.completed);
      expect(assessment.advisory.status, BackendAdvisoryStatus.disabled);
      client.close();
    });

    test(
      'loads persisted assessment, deterministic findings and evidence',
      () async {
        final requestPaths = <String>[];
        final client = MockClient((request) async {
          requestPaths.add(request.url.path);
          if (request.url.path == '/assessments/$_assessmentId') {
            return http.Response(
              jsonEncode(
                _assessmentResponse(
                  status: 'completed',
                  executionResult: {
                    'ai_review': _reviewResponse(status: 'reviewed'),
                  },
                ),
              ),
              200,
            );
          }
          if (request.url.path.endsWith('/findings')) {
            return http.Response(
              jsonEncode({
                'items': [_findingJson()],
                'total': 1,
              }),
              200,
            );
          }
          if (request.url.path.endsWith('/evidence')) {
            return http.Response(
              jsonEncode({
                'items': [_evidenceJson()],
                'total': 1,
              }),
              200,
            );
          }
          return http.Response('', 404);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        final details = await repository.getAssessmentDetails(_assessmentId);

        expect(details, isNotNull);
        expect(details!.assessment.status, BackendAssessmentStatus.completed);
        expect(details.findings!.single.severity, 'medium');
        expect(
          details.findings!.single.title,
          'Strict transport policy missing',
        );
        expect(details.evidence!.single.evidenceId, _evidenceId);
        expect(details.advisory.status, BackendAdvisoryStatus.reviewed);
        expect(requestPaths, contains('/assessments/$_assessmentId/findings'));
        expect(requestPaths, contains('/assessments/$_assessmentId/evidence'));
        client.close();
      },
    );

    test(
      'rejects invalid advisory references while preserving findings',
      () async {
        final wrongFinding = 'fnd_${List.filled(32, 'd').join()}';
        final client = MockClient((request) async {
          if (request.url.path == '/assessments/$_assessmentId') {
            return http.Response(
              jsonEncode(
                _assessmentResponse(
                  status: 'completed',
                  executionResult: {
                    'ai_review': _reviewResponse(findingId: wrongFinding),
                  },
                ),
              ),
              200,
            );
          }
          if (request.url.path.endsWith('/findings')) {
            return http.Response(
              jsonEncode({
                'items': [_findingJson()],
                'total': 1,
              }),
              200,
            );
          }
          if (request.url.path.endsWith('/evidence')) {
            return http.Response(
              jsonEncode({
                'items': [_evidenceJson()],
                'total': 1,
              }),
              200,
            );
          }
          return http.Response('', 404);
        });
        final repository = ApiAegisCoreRepository(
          configuration: _configuration(),
          client: client,
        );

        final details = await repository.getAssessmentDetails(_assessmentId);

        expect(details!.findings, hasLength(1));
        expect(details.advisory.status, BackendAdvisoryStatus.invalid);
        expect(details.advisory.reviews, isEmpty);
        client.close();
      },
    );

    test(
      'malformed and oversized advisory text is rejected without parsing HTML',
      () {
        final tooLong = _reviewResponse();
        (tooLong['reviews'] as List).first['recommendation'] = List.filled(
          601,
          'x',
        ).join();
        expect(
          BackendAdvisoryReview.fromJson(tooLong).status,
          BackendAdvisoryStatus.invalid,
        );

        final oversized = _reviewResponse();
        oversized['untrusted'] = List.filled(17000, 'x').join();
        expect(
          BackendAdvisoryReview.fromJson(oversized).status,
          BackendAdvisoryStatus.invalid,
        );

        final htmlText = _reviewResponse();
        (htmlText['reviews'] as List).first['recommendation'] =
            '<script>alert(1)</script>';
        final parsed = BackendAdvisoryReview.fromJson(htmlText);
        expect(parsed.status, BackendAdvisoryStatus.reviewed);
        expect(
          parsed.reviews.single.recommendation,
          '<script>alert(1)</script>',
        );
      },
    );
  });

  group('Riverpod repository selection', () {
    test('selects fixtures only when configured for demo mode', () {
      final container = ProviderContainer(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            _configuration(mode: AegisCoreMode.demo),
          ),
        ],
      );
      addTearDown(container.dispose);

      expect(
        container.read(aegisCoreRepositoryProvider),
        isA<DemoAegisCoreRepository>(),
      );
    });

    test('selects the API repository for live mode', () {
      final client = MockClient((_) async => http.Response('', 200));
      final container = ProviderContainer(
        overrides: [
          aegisCoreConfigurationProvider.overrideWithValue(
            _configuration(mode: AegisCoreMode.live),
          ),
          backendHttpClientProvider.overrideWithValue(client),
        ],
      );
      addTearDown(container.dispose);

      final repository = container.read(aegisCoreRepositoryProvider);
      expect(repository, isA<ApiAegisCoreRepository>());
      expect(repository.mode, AegisCoreMode.live);
    });
  });
}

AegisCoreConfiguration _configuration({
  AegisCoreMode mode = AegisCoreMode.live,
  Uri? baseUri,
  Duration connectTimeout = const Duration(seconds: 1),
  Duration requestTimeout = const Duration(seconds: 1),
}) => AegisCoreConfiguration(
  mode: mode,
  baseUri: baseUri ?? Uri.parse('http://127.0.0.1:8000/'),
  connectTimeout: connectTimeout,
  requestTimeout: requestTimeout,
);

class _SlowBodyClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final body = Future<List<int>>.delayed(
      const Duration(seconds: 1),
      () => utf8.encode('{"status":"ok"}'),
    );
    return http.StreamedResponse(Stream<List<int>>.fromFuture(body), 200);
  }
}

Map<String, Object?> _approvedEvidenceItem({required String id}) => {
  'source': {
    'source_id': 'source-1',
    'review_state': 'approved',
    'revision': 2,
    'content_sha256': _digest('a'),
    'title': 'Approved test guidance',
    'publisher': 'Test publisher',
    'canonical_reference': 'https://example.invalid/guide',
    'publication_date': null,
    'version': 'recorded-v1',
    'acquired_at': '2026-10-27',
    'source_type': 'security-reference',
    'scope_tags': ['security'],
    'review_event_count': 3,
    'approved_at': '2026-10-27T11:00:00Z',
  },
  'chunk': {
    'evidence_id': id,
    'ordinal': 0,
    'start_offset': 0,
    'end_offset': 30,
    'section': 'SQL safety',
    'excerpt': 'Use parameterized SQL queries.',
    'content_sha256': _digest('b'),
    'citation_source_id': 'source-1',
    'citation_chunk_id': id,
  },
};

final String _assessmentId = 'asm_${List.filled(32, 'a').join()}';
final String _findingId = 'fnd_${List.filled(32, 'b').join()}';
final String _evidenceId = 'evi_${List.filled(32, 'c').join()}';

Map<String, Object?> _assessmentResponse({
  String status = 'created',
  Map<String, Object?>? executionResult,
}) => {
  'assessment_id': _assessmentId,
  'target_id': 'local-test-target',
  'target_url': 'http://127.0.0.1:3000',
  'authorization_ref': 'opaque-server-reference',
  'canonical_endpoint': 'http://127.0.0.1:3000/',
  'status': status,
  'created_at': '2026-11-24T10:00:00Z',
  'updated_at': '2026-11-24T10:00:01Z',
  'execution_result': executionResult,
};

Map<String, Object?> _findingJson() => {
  'finding_id': _findingId,
  'assessment_id': _assessmentId,
  'rule_id': 'strict_transport_security_missing',
  'title': 'Strict transport policy missing',
  'description':
      'The observed response did not include a transport policy header.',
  'classification': 'configuration_observation',
  'severity': 'medium',
  'confidence': 'high',
  'status': 'detected',
  'evidence_ids': [_evidenceId],
  'remediation':
      'Configure the expected transport policy for this local service.',
  'created_at': '2026-11-24T10:00:01Z',
};

Map<String, Object?> _evidenceJson() => {
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
  'provenance': <String, Object?>{'duration_ms': 4},
};

Map<String, Object?> _reviewResponse({
  String status = 'reviewed',
  String findingId = 'fnd_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  String evidenceId = 'evi_cccccccccccccccccccccccccccccccc',
  List<Map<String, Object?>>? reviews,
}) => {
  'status': status,
  'analysis_type': 'advisory_inference',
  'model_id': 'deterministic-test-adapter',
  'provider_mode': 'deterministic_fake',
  'execution_duration_ms': 2.5,
  'confidence_calibrated': false,
  'factual_support': 'not_evaluated',
  'abstention_reason': null,
  'reviews':
      reviews ??
      (status == 'reviewed'
          ? [
              {
                'finding_id': findingId,
                'evidence_ids': [evidenceId],
                'inferred_risk':
                    'This observation could indicate a policy gap.',
                'uncertainty':
                    'A HEAD observation does not prove exploitability.',
                'recommendation': 'Review the endpoint policy configuration.',
              },
            ]
          : []),
};

String _digest(String character) => List.filled(64, character).join();
