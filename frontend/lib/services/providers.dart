import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/findings/models/finding_model.dart';
import '../features/evidence/models/evidence_model.dart';
import '../features/reports/models/report_model.dart';
import '../features/assessment_setup/models/assessment_setup_model.dart';
import 'aegiscore_repository.dart';
import 'aegiscore_configuration.dart';
import 'authentication.dart';
import 'backend_http_client.dart';
import 'api_aegiscore_repository.dart';
import 'backend_contract_models.dart';
import 'backend_persisted_models.dart';

export 'backend_http_client.dart'
    show aegisCoreConfigurationProvider, backendHttpClientProvider;

/// Repository provider for AEGISCORE AI. Easily overridden in tests or live environments.
final aegisCoreRepositoryProvider = Provider<AegisCoreRepository>((ref) {
  final configuration = ref.watch(aegisCoreConfigurationProvider);
  if (configuration.mode == AegisCoreMode.live) {
    final auth = ref.watch(authenticationProvider);
    return ApiAegisCoreRepository(
      configuration: configuration,
      client: ref.watch(backendHttpClientProvider),
      accessToken: auth.accessToken,
      onAuthenticationExpired: auth.accessToken == null
          ? null
          : (token) => ref
                .read(authenticationProvider.notifier)
                .expireSession(token),
    );
  }
  return DemoAegisCoreRepository();
});

final repositoryModeProvider = Provider<AegisCoreMode>(
  (ref) => ref.watch(aegisCoreRepositoryProvider).mode,
);

/// Asynchronously loads all findings.
final findingsProvider = FutureProvider<List<FindingModel>>((ref) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getFindings();
});

/// Asynchronously loads finding by ID.
final findingDetailsProvider = FutureProvider.family<FindingModel?, String>((
  ref,
  id,
) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getFindingById(id);
});

/// Asynchronously loads all evidence artifacts.
final evidenceListProvider = FutureProvider<List<EvidenceModel>>((ref) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getEvidenceList();
});

/// Asynchronously loads evidence by ID.
final evidenceDetailsProvider = FutureProvider.family<EvidenceModel?, String>((
  ref,
  id,
) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getEvidenceById(id);
});

/// Asynchronously loads the latest evaluation benchmark report.
final evaluationReportProvider = FutureProvider<EvaluationReportModel>((
  ref,
) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getLatestEvaluationReport();
});

/// Checks backend health endpoint.
final backendHealthProvider = FutureProvider<bool>((ref) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.checkBackendHealth();
});

/// Fetches backend capabilities inventory.
final backendCapabilitiesProvider = FutureProvider<BackendCapabilitiesResponse>(
  (ref) async {
    final repo = ref.watch(aegisCoreRepositoryProvider);
    return repo.getBackendCapabilities();
  },
);

final backendStorageStatusProvider = FutureProvider<BackendStorageStatus>((
  ref,
) async {
  final repo = ref.watch(aegisCoreRepositoryProvider);
  return repo.getStorageStatus();
});

final backendRecentSessionsProvider =
    FutureProvider<List<BackendOfflineSession>>((ref) async {
      final repo = ref.watch(aegisCoreRepositoryProvider);
      return repo.getRecentSessions();
    });

final backendSessionDetailsProvider =
    FutureProvider.family<BackendOfflineSession?, String>((ref, id) async {
      final repo = ref.watch(aegisCoreRepositoryProvider);
      return repo.getOfflineSessionById(id);
    });

final backendDashboardSummaryProvider = FutureProvider<BackendDashboardSummary>(
  (ref) async {
    final repo = ref.watch(aegisCoreRepositoryProvider);
    return repo.getDashboardSummary();
  },
);

final storedEvaluationReportsProvider =
    FutureProvider<List<StoredEvaluationReportModel>>((ref) async {
      final repo = ref.watch(aegisCoreRepositoryProvider);
      return repo.getStoredEvaluationReports();
    });

final storedEvaluationReportDetailsProvider =
    FutureProvider.family<StoredEvaluationReportModel?, String>((
      ref,
      id,
    ) async {
      final repo = ref.watch(aegisCoreRepositoryProvider);
      return repo.getStoredEvaluationReportById(id);
    });

/// Assessment setup configuration controller.
class AssessmentSetupNotifier extends Notifier<AssessmentSetupConfig> {
  @override
  AssessmentSetupConfig build() {
    return const AssessmentSetupConfig(
      labTargetId: 'juice_shop_local',
      targetUrl: 'http://localhost:3000',
      selectedSpecialists: [
        'sql_injection_analyst',
        'xss_specialist',
        'deserialization_specialist',
      ],
      adversarialReviewerEnabled: true,
      strictEvidenceGrounding: true,
      isAuthorizedLabConfirmed: false,
    );
  }

  void updateLabTarget(String labTargetId, String targetUrl) {
    state = state.copyWith(
      labTargetId: labTargetId,
      targetUrl: targetUrl,
      isAuthorizedLabConfirmed: false,
    );
  }

  void toggleSpecialist(String specialist) {
    final list = List<String>.from(state.selectedSpecialists);
    if (list.contains(specialist)) {
      if (list.length > 1) {
        list.remove(specialist);
      }
    } else {
      list.add(specialist);
    }
    state = state.copyWith(selectedSpecialists: list);
  }

  void setAdversarialReviewer(bool enabled) {
    state = state.copyWith(adversarialReviewerEnabled: enabled);
  }

  void setStrictEvidenceGrounding(bool enabled) {
    state = state.copyWith(strictEvidenceGrounding: enabled);
  }

  void setAuthorizedLabConfirmed(bool confirmed) {
    state = state.copyWith(isAuthorizedLabConfirmed: confirmed);
  }

  void reset() {
    state = build();
  }
}

final assessmentSetupProvider =
    NotifierProvider<AssessmentSetupNotifier, AssessmentSetupConfig>(
      AssessmentSetupNotifier.new,
    );
