import '../features/findings/models/finding_model.dart';
import '../features/evidence/models/evidence_model.dart';
import '../features/reports/models/report_model.dart';
import '../features/assessment_setup/models/assessment_setup_model.dart';
import 'aegiscore_configuration.dart';
import 'backend_contract_models.dart';
import 'backend_errors.dart';
import 'backend_persisted_models.dart';
import 'lab_scope.dart';
import 'mock_demo_data.dart';

/// Contract interface for AEGISCORE AI backend interactions.
/// Designed for clean decoupling between offline demo fixtures and future live FastAPI integration.
abstract class AegisCoreRepository {
  AegisCoreMode get mode;
  String get displayEndpoint;
  bool get supportsAssessmentSubmission;
  Future<bool> checkBackendHealth();
  Future<BackendCapabilitiesResponse> getBackendCapabilities();
  Future<BackendDashboardSummary> getDashboardSummary();
  Future<BackendStorageStatus> getStorageStatus();
  Future<List<BackendOfflineSession>> getRecentSessions();
  Future<BackendOfflineSession?> getOfflineSessionById(String id);
  Future<List<StoredEvaluationReportModel>> getStoredEvaluationReports();
  Future<StoredEvaluationReportModel?> getStoredEvaluationReportById(String id);
  Future<List<FindingModel>> getFindings();
  Future<FindingModel?> getFindingById(String id);
  Future<List<EvidenceModel>> getEvidenceList();
  Future<EvidenceModel?> getEvidenceById(String id);
  Future<EvaluationReportModel> getLatestEvaluationReport();
  Future<bool> validateLabScope(String targetUrl);
  Future<String> submitAssessmentSetup(AssessmentSetupConfig config);
}

/// Offline demo repository implementation providing verified synthetic testbed data.
class DemoAegisCoreRepository implements AegisCoreRepository {
  @override
  AegisCoreMode get mode => AegisCoreMode.demo;

  @override
  String get displayEndpoint => 'Not used in demo mode';

  @override
  bool get supportsAssessmentSubmission => true;

  @override
  Future<bool> checkBackendHealth() async {
    // Simulated offline state
    await Future.delayed(const Duration(milliseconds: 300));
    return false; // Backend is offline by default until live server is launched
  }

  @override
  Future<BackendCapabilitiesResponse> getBackendCapabilities() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return const BackendCapabilitiesResponse(
      service: 'aegiscore-api',
      version: '0.1.0',
      implemented: [
        'api.health_endpoint',
        'api.capabilities_endpoint',
        'safety.in_memory_policy_contracts',
        'safety.fake_transport_only_guarded_execution_contract',
      ],
      notImplemented: [
        'backend.real_target_transport',
        'backend.rag',
        'backend.multi_agent_orchestration',
        'backend.vulnerability_assessment_workflow',
        'backend.external_llm_provider',
        'backend.persistent_application_storage',
      ],
    );
  }

  @override
  Future<BackendDashboardSummary> getDashboardSummary() => Future.error(
    UnsupportedBackendCapabilityException('a live dashboard API'),
  );

  @override
  Future<BackendStorageStatus> getStorageStatus() => Future.error(
    UnsupportedBackendCapabilityException('a live storage status API'),
  );

  @override
  Future<List<BackendOfflineSession>> getRecentSessions() => Future.error(
    UnsupportedBackendCapabilityException('a persisted sessions API'),
  );

  @override
  Future<BackendOfflineSession?> getOfflineSessionById(String id) =>
      Future.error(
        UnsupportedBackendCapabilityException('a persisted session detail API'),
      );

  @override
  Future<List<StoredEvaluationReportModel>> getStoredEvaluationReports() =>
      Future.error(
        UnsupportedBackendCapabilityException('a persisted reports API'),
      );

  @override
  Future<StoredEvaluationReportModel?> getStoredEvaluationReportById(
    String id,
  ) => Future.error(
    UnsupportedBackendCapabilityException('a persisted report detail API'),
  );

  @override
  Future<List<FindingModel>> getFindings() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return MockDemoData.findings;
  }

  @override
  Future<FindingModel?> getFindingById(String id) async {
    await Future.delayed(const Duration(milliseconds: 150));
    try {
      return MockDemoData.findings.firstWhere((f) => f.id == id);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<List<EvidenceModel>> getEvidenceList() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return MockDemoData.evidenceList;
  }

  @override
  Future<EvidenceModel?> getEvidenceById(String id) async {
    await Future.delayed(const Duration(milliseconds: 150));
    try {
      return MockDemoData.evidenceList.firstWhere((e) => e.id == id);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<EvaluationReportModel> getLatestEvaluationReport() async {
    await Future.delayed(const Duration(milliseconds: 250));
    return MockDemoData.evaluationReport;
  }

  @override
  Future<bool> validateLabScope(String targetUrl) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return isAuthorizedLocalLabTarget(targetUrl);
  }

  @override
  Future<String> submitAssessmentSetup(AssessmentSetupConfig config) async {
    await Future.delayed(const Duration(milliseconds: 500));
    if (!config.isAuthorizedLabConfirmed) {
      throw ArgumentError(
        'Assessment cannot proceed without explicit authorized lab confirmation.',
      );
    }
    return 'SESSION-${DateTime.now().millisecondsSinceEpoch}';
  }
}
