import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../features/assessment_setup/models/assessment_setup_model.dart';
import '../features/evidence/models/evidence_model.dart';
import '../features/findings/models/finding_model.dart';
import '../features/reports/models/report_model.dart';
import 'aegiscore_configuration.dart';
import 'aegiscore_repository.dart';
import 'backend_contract_models.dart';
import 'backend_errors.dart';
import 'backend_persisted_models.dart';
import 'backend_assessment_models.dart';
import 'lab_scope.dart';

const int _maxAssessmentApiResponseBytes = 2 * 1024 * 1024;

/// Live repository for the authenticated FastAPI contracts that currently exist.
/// Assessment operations use the server's authorization and lifecycle contracts;
/// the client does not create approval references or execution policy.
class ApiAegisCoreRepository implements AegisCoreRepository {
  final AegisCoreConfiguration configuration;
  final http.Client _client;
  final String? accessToken;
  final void Function(String token)? onAuthenticationExpired;

  ApiAegisCoreRepository({
    required this.configuration,
    required http.Client client,
    this.accessToken,
    this.onAuthenticationExpired,
  }) : _client = client;

  @override
  AegisCoreMode get mode => AegisCoreMode.live;

  @override
  String get displayEndpoint => configuration.displayEndpoint;

  @override
  bool get supportsAssessmentSubmission => true;

  @override
  Future<bool> checkBackendHealth() async {
    await _getJson('health', BackendHealthResponse.fromJson);
    return true;
  }

  @override
  Future<BackendCapabilitiesResponse> getBackendCapabilities() =>
      _getJson('capabilities', BackendCapabilitiesResponse.fromJson);

  @override
  Future<BackendDashboardSummary> getDashboardSummary() =>
      _getJson('dashboard/summary', BackendDashboardSummary.fromJson);

  @override
  Future<BackendStorageStatus> getStorageStatus() =>
      _getJson('storage/status', BackendStorageStatus.fromJson);

  @override
  Future<List<BackendOfflineSession>> getRecentSessions() async {
    final page = await _getJson(
      'sessions?offset=0&limit=10',
      BackendOfflineSessionPage.fromJson,
    );
    if (page.offset != 0 ||
        page.items.length > 10 ||
        page.items.isEmpty && page.total > 0) {
      throw const BackendResponseException();
    }
    return page.items;
  }

  @override
  Future<BackendOfflineSession?> getOfflineSessionById(String id) async {
    try {
      return await _getJson(
        'sessions/${Uri.encodeComponent(id)}',
        BackendOfflineSession.fromJson,
      );
    } on BackendHttpException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<List<StoredEvaluationReportModel>> getStoredEvaluationReports() async {
    final reports = <StoredEvaluationReportModel>[];
    var offset = 0;
    var total = 0;
    do {
      final page = await _getJson(
        'reports?offset=$offset&limit=100',
        StoredEvaluationReportPage.fromJson,
      );
      if (offset == 0) total = page.total;
      if (page.total != total ||
          page.offset != offset ||
          page.items.isEmpty && offset < total) {
        throw const BackendResponseException();
      }
      reports.addAll(page.items);
      offset += page.items.length;
    } while (offset < total);
    return List<StoredEvaluationReportModel>.unmodifiable(reports);
  }

  @override
  Future<StoredEvaluationReportModel?> getStoredEvaluationReportById(
    String id,
  ) async {
    try {
      return await _getJson(
        'reports/${Uri.encodeComponent(id)}',
        StoredEvaluationReportModel.fromJson,
      );
    } on BackendHttpException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<BackendAssessmentPage> getAssessments({
    int offset = 0,
    int limit = 50,
  }) {
    if (offset < 0 || limit < 1 || limit > 100) {
      throw ArgumentError('Assessment page bounds are invalid.');
    }
    return _getJson(
      'assessments?offset=$offset&limit=$limit',
      BackendAssessmentPage.fromJson,
    );
  }

  @override
  Future<BackendAssessmentRecord?> getAssessmentById(String id) async {
    try {
      return await _getJson(
        'assessments/${Uri.encodeComponent(id)}',
        BackendAssessmentRecord.fromJson,
      );
    } on BackendHttpException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<BackendAssessmentRecord> createAssessment(String targetUrl) =>
      _postJson(
        'assessments',
        BackendAssessmentRecord.fromJson,
        body: {'target_url': targetUrl},
      );

  @override
  Future<BackendAssessmentRecord> executeAssessment(String id) => _postJson(
    'assessments/${Uri.encodeComponent(id)}/execute',
    BackendAssessmentRecord.fromJson,
  );

  @override
  Future<List<BackendAssessmentFinding>> getAssessmentFindings(
    String id,
  ) async {
    final page = await _getJson(
      'assessments/${Uri.encodeComponent(id)}/findings',
      (json) => _parseAssessmentList<BackendAssessmentFinding>(
        json,
        BackendAssessmentFinding.fromJson,
        'assessment finding',
      ),
    );
    return page;
  }

  @override
  Future<List<BackendAssessmentEvidence>> getAssessmentEvidence(
    String id,
  ) async {
    return _getJson(
      'assessments/${Uri.encodeComponent(id)}/evidence',
      (json) => _parseAssessmentList<BackendAssessmentEvidence>(
        json,
        BackendAssessmentEvidence.fromJson,
        'assessment evidence',
      ),
    );
  }

  @override
  Future<BackendAssessmentDetails?> getAssessmentDetails(String id) async {
    final assessment = await getAssessmentById(id);
    if (assessment == null) return null;
    final findingsFuture = _loadApiAssessmentResource(
      () => getAssessmentFindings(id),
    );
    final evidenceFuture = _loadApiAssessmentResource(
      () => getAssessmentEvidence(id),
    );
    final findings = await findingsFuture;
    final evidence = await evidenceFuture;
    var findingsValue = findings.value;
    var findingsError = findings.error;
    var evidenceValue = evidence.value;
    var evidenceError = evidence.error;
    if (findingsValue?.any(
          (item) => item.assessmentId != assessment.assessmentId,
        ) ==
        true) {
      findingsValue = null;
      findingsError =
          'The backend returned findings for a different assessment.';
    }
    if (evidenceValue?.any(
          (item) => item.assessmentId != assessment.assessmentId,
        ) ==
        true) {
      evidenceValue = null;
      evidenceError =
          'The backend returned evidence for a different assessment.';
    }
    return BackendAssessmentDetails(
      assessment: assessment,
      findings: findingsValue,
      findingsError: findingsError,
      evidence: evidenceValue,
      evidenceError: evidenceError,
    );
  }

  @override
  Future<List<FindingModel>> getFindings() async {
    final findings = <FindingModel>[];
    var offset = 0;
    var total = 0;
    do {
      final page = await _getJson(
        'findings?offset=$offset&limit=100',
        _parseFindingPage,
      );
      if (offset == 0) total = page.total;
      if (page.total != total ||
          page.offset != offset ||
          page.items.isEmpty && offset < total) {
        throw const BackendResponseException();
      }
      findings.addAll(page.items);
      offset += page.items.length;
    } while (offset < total);
    return List<FindingModel>.unmodifiable(findings);
  }

  @override
  Future<FindingModel?> getFindingById(String id) async {
    try {
      return await _getJson(
        'findings/${Uri.encodeComponent(id)}',
        _parseStoredFinding,
      );
    } on BackendHttpException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<List<EvidenceModel>> getEvidenceList() async {
    final evidence = <EvidenceModel>[];
    var offset = 0;
    var total = 0;
    do {
      final page = await _getJson(
        'evidence/approved?offset=$offset&limit=100',
        _parseEvidencePage,
      );
      if (offset == 0) total = page.total;
      if (page.total != total ||
          page.offset != offset ||
          page.items.isEmpty && offset < total) {
        throw const BackendResponseException();
      }
      evidence.addAll(page.items);
      offset += page.items.length;
    } while (offset < total);
    return List<EvidenceModel>.unmodifiable(evidence);
  }

  @override
  Future<EvidenceModel?> getEvidenceById(String id) async {
    try {
      return await _getJson(
        'evidence/approved/${Uri.encodeComponent(id)}',
        EvidenceModel.fromApprovedApiJson,
      );
    } on BackendHttpException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<EvaluationReportModel> getLatestEvaluationReport() =>
      _unsupported('the legacy single-report API; use persisted reports');

  @override
  Future<bool> validateLabScope(String targetUrl) async =>
      isAuthorizedLocalLabTarget(targetUrl);

  @override
  Future<String> submitAssessmentSetup(AssessmentSetupConfig config) async {
    if (!config.isAuthorizedLabConfirmed) {
      throw ArgumentError(
        'Assessment cannot proceed without explicit authorized lab confirmation.',
      );
    }
    throw UnsupportedBackendCapabilityException(
      'an authorized offline assessment submission API',
    );
  }

  Future<T> _unsupported<T>(String capability) =>
      Future<T>.error(UnsupportedBackendCapabilityException(capability));

  Future<T> _getJson<T>(String path, T Function(Object? json) parse) =>
      _requestJson('GET', path, parse);

  Future<T> _postJson<T>(
    String path,
    T Function(Object? json) parse, {
    Object? body,
  }) => _requestJson('POST', path, parse, body: body);

  Future<T> _requestJson<T>(
    String method,
    String path,
    T Function(Object? json) parse, {
    Object? body,
  }) async {
    final request = http.Request(method, configuration.endpoint(path));
    if (accessToken != null) {
      request.headers['Authorization'] = 'Bearer $accessToken';
    }
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    late final http.StreamedResponse streamed;
    try {
      streamed = await _client
          .send(request)
          .timeout(
            configuration.connectTimeout,
            onTimeout: () => throw const BackendTimeoutException('connection'),
          );
    } on BackendException {
      rethrow;
    } on TimeoutException {
      throw const BackendTimeoutException('connection');
    } on http.ClientException {
      throw const BackendConnectionException();
    } catch (_) {
      throw const BackendConnectionException();
    }

    late final http.Response response;
    try {
      if (streamed.contentLength != null &&
          streamed.contentLength! > _maxAssessmentApiResponseBytes) {
        throw const BackendResponseException();
      }
      response = await http.Response.fromStream(streamed).timeout(
        configuration.requestTimeout,
        onTimeout: () => throw const BackendTimeoutException('request'),
      );
    } on BackendException {
      rethrow;
    } on TimeoutException {
      throw const BackendTimeoutException('request');
    } on http.ClientException {
      throw const BackendConnectionException();
    } catch (_) {
      throw const BackendConnectionException();
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      if (response.statusCode == 401) {
        final token = accessToken;
        if (token != null) onAuthenticationExpired?.call(token);
        throw const BackendAuthenticationException();
      }
      if (response.statusCode == 403) {
        throw const BackendAuthorizationException();
      }
      throw BackendHttpException(response.statusCode);
    }
    if (response.bodyBytes.length > _maxAssessmentApiResponseBytes) {
      throw const BackendResponseException();
    }
    try {
      return parse(jsonDecode(response.body));
    } on BackendException {
      rethrow;
    } catch (_) {
      throw const BackendResponseException();
    }
  }

  static List<T> _parseAssessmentList<T>(
    Object? value,
    T Function(Object? value) parseItem,
    String label,
  ) {
    if (value is! Map<String, dynamic> ||
        value.length != 2 ||
        !value.keys.toSet().containsAll(const {'items', 'total'})) {
      throw FormatException('Unexpected $label list response.');
    }
    final items = value['items'];
    final total = value['total'];
    if (items is! List || total is! int || total < 0 || items.length != total) {
      throw FormatException('Unexpected $label list response.');
    }
    return List<T>.unmodifiable(items.map(parseItem));
  }

  static _EvidencePage _parseEvidencePage(Object? json) {
    if (json is! Map<String, dynamic> ||
        json.keys.toSet().length != 5 ||
        !json.keys.toSet().containsAll(const {
          'items',
          'total',
          'approved_source_count',
          'offset',
          'limit',
        })) {
      throw const FormatException('Unexpected approved evidence response.');
    }
    final items = json['items'];
    final total = json['total'];
    final sourceCount = json['approved_source_count'];
    final offset = json['offset'];
    final limit = json['limit'];
    if (items is! List ||
        total is! int ||
        total < 0 ||
        sourceCount is! int ||
        sourceCount < 0 ||
        offset is! int ||
        offset < 0 ||
        limit is! int ||
        limit < 1 ||
        limit > 100 ||
        items.length > limit ||
        offset + items.length > total) {
      throw const FormatException('Unexpected approved evidence response.');
    }
    return _EvidencePage(
      items: List<EvidenceModel>.unmodifiable(
        items.map(EvidenceModel.fromApprovedApiJson),
      ),
      total: total,
      offset: offset,
    );
  }

  static _FindingPage _parseFindingPage(Object? json) {
    if (json is! Map<String, dynamic> ||
        json.keys.toSet().length != 4 ||
        !json.keys.toSet().containsAll(const {
          'items',
          'total',
          'offset',
          'limit',
        })) {
      throw const FormatException('Unexpected findings response.');
    }
    final rawItems = json['items'];
    final total = json['total'];
    final offset = json['offset'];
    final limit = json['limit'];
    if (rawItems is! List ||
        total is! int ||
        total < 0 ||
        offset is! int ||
        offset < 0 ||
        limit is! int ||
        limit < 1 ||
        limit > 100 ||
        rawItems.length > limit ||
        offset + rawItems.length > total) {
      throw const FormatException('Unexpected findings response.');
    }
    return _FindingPage(
      items: List<FindingModel>.unmodifiable(rawItems.map(_parseStoredFinding)),
      total: total,
      offset: offset,
    );
  }

  static FindingModel _parseStoredFinding(Object? json) {
    const expected = {
      'finding_id',
      'source_finding_id',
      'session_id',
      'report_id',
      'case_id',
      'recorded_at',
      'specialist_role',
      'vulnerability_identified',
      'cwe_id',
      'severity',
      'decision',
      'evidence_refs',
      'rationale',
      'locus',
      'vulnerability_class',
      'is_synthetic',
      'is_empirical',
      'execution_mode',
    };
    if (json is! Map<String, dynamic> ||
        json.length != expected.length ||
        !json.keys.toSet().containsAll(expected)) {
      throw const FormatException('Unexpected stored finding response.');
    }
    final id = json['finding_id'];
    final sourceFindingId = json['source_finding_id'];
    final sessionId = json['session_id'];
    final reportId = json['report_id'];
    final caseId = json['case_id'];
    final role = json['specialist_role'];
    final cwe = json['cwe_id'];
    final severityRaw = json['severity'];
    final decision = json['decision'];
    final evidenceRefs = json['evidence_refs'];
    final rationale = json['rationale'];
    final synthetic = json['is_synthetic'];
    final empirical = json['is_empirical'];
    final executionMode = json['execution_mode'];
    final locus = json['locus'];
    final recordedAt = json['recorded_at'];
    if (id is! String ||
        sourceFindingId is! String ||
        sessionId is! String ||
        reportId is! String ||
        caseId is! String ||
        role is! String ||
        cwe is! String ||
        json['vulnerability_identified'] is! bool ||
        severityRaw is! String ||
        !{'info', 'low', 'medium', 'high', 'critical'}.contains(severityRaw) ||
        !{'verified', 'rejected', 'abstained'}.contains(decision) ||
        evidenceRefs is! List ||
        !evidenceRefs.every((item) => item is String) ||
        rationale is! String ||
        (json['vulnerability_class'] != null &&
            json['vulnerability_class'] is! String) ||
        synthetic != true ||
        empirical != false ||
        executionMode != 'offline_fixture' ||
        (recordedAt != null &&
            (recordedAt is! String || DateTime.tryParse(recordedAt) == null))) {
      throw const FormatException('Unexpected stored finding response.');
    }
    if (locus != null &&
        (locus is! Map<String, dynamic> ||
            !{
              'target_uri',
              'parameter',
              'cwe_id',
            }.every((key) => locus[key] is String))) {
      throw const FormatException('Unexpected stored finding locus.');
    }
    final targetUri = locus is Map<String, dynamic>
        ? locus['target_uri'] as String
        : '';
    final parameter = locus is Map<String, dynamic>
        ? locus['parameter'] as String
        : '';
    final cweFromLocus = locus is Map<String, dynamic>
        ? locus['cwe_id'] as String
        : cwe;
    final uri = Uri.tryParse(targetUri);
    final reviewStatus = switch (decision) {
      'verified' => ReviewStatus.recorded,
      'rejected' => ReviewStatus.rejected,
      _ => ReviewStatus.abstained,
    };
    return FindingModel(
      id: id,
      title: '${json['vulnerability_class'] ?? cwe} ($cwe)',
      vulnerabilityClass: json['vulnerability_class'] is String
          ? json['vulnerability_class'] as String
          : cwe,
      severity: _severity(severityRaw),
      reviewStatus: reviewStatus,
      targetApp: 'Synthetic offline fixture replay',
      locus: LocusModel(
        url: targetUri,
        method: 'Offline replay',
        path: uri?.path.isNotEmpty == true ? uri!.path : targetUri,
        parameter: parameter,
        sink: cweFromLocus,
      ),
      specialistRole: role,
      claims: const [],
      evidenceIds: List<String>.unmodifiable(evidenceRefs.cast<String>()),
      isSyntheticDemo: true,
      discoveredAt: recordedAt is String ? DateTime.tryParse(recordedAt) : null,
      isPersistedRecord: true,
      dataProvenanceLabel: 'SYNTHETIC OFFLINE FIXTURE REPLAY • $caseId',
      sourceSessionId: sessionId,
      recordedRationale: rationale,
      recordedDecision: decision as String,
    );
  }

  static SeverityLevel _severity(String value) => switch (value) {
    'critical' => SeverityLevel.critical,
    'high' => SeverityLevel.high,
    'medium' => SeverityLevel.medium,
    'low' => SeverityLevel.low,
    _ => SeverityLevel.info,
  };
}

class _EvidencePage {
  final List<EvidenceModel> items;
  final int total;
  final int offset;

  const _EvidencePage({
    required this.items,
    required this.total,
    required this.offset,
  });
}

class _FindingPage {
  final List<FindingModel> items;
  final int total;
  final int offset;

  const _FindingPage({
    required this.items,
    required this.total,
    required this.offset,
  });
}

Future<({List<T>? value, String? error})> _loadApiAssessmentResource<T>(
  Future<List<T>> Function() load,
) async {
  try {
    return (value: await load(), error: null);
  } catch (error) {
    return (value: null, error: assessmentResourceError(error));
  }
}
