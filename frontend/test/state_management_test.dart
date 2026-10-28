import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aegiscore_ui/services/aegiscore_repository.dart';
import 'package:aegiscore_ui/services/providers.dart';
import 'package:aegiscore_ui/features/assessment_setup/models/assessment_setup_model.dart';
import 'package:aegiscore_ui/features/findings/models/finding_model.dart';
import 'package:aegiscore_ui/features/evidence/models/evidence_model.dart';

void main() {
  group('AegisCoreRepository Contract & Validation Tests', () {
    late AegisCoreRepository repository;

    setUp(() {
      repository = DemoAegisCoreRepository();
    });

    test('getFindings returns structured non-empty demo findings', () async {
      final findings = await repository.getFindings();
      expect(findings, isNotEmpty);
      expect(findings.length, greaterThanOrEqualTo(4));

      final first = findings.first;
      expect(first.id, equals('FIND-JS-01'));
      expect(first.vulnerabilityClass, equals('sql_injection'));
      expect(first.severity, equals(SeverityLevel.critical));
      expect(first.reviewStatus, equals(ReviewStatus.verified));
      expect(first.locus.parameter, equals('q'));
      expect(first.claims, isNotEmpty);
    });

    test(
      'getFindingById returns matching finding or null for unknown ID',
      () async {
        final match = await repository.getFindingById('FIND-DVWA-01');
        expect(match, isNotNull);
        expect(match!.vulnerabilityClass, equals('cross_site_scripting'));

        final unknown = await repository.getFindingById('NON-EXISTENT-ID');
        expect(unknown, isNull);
      },
    );

    test(
      'getEvidenceList returns evidence artifacts with provenance digests',
      () async {
        final evidence = await repository.getEvidenceList();
        expect(evidence, isNotEmpty);

        final first = evidence.first;
        expect(first.provenanceDigest, startsWith('sha256:'));
        expect(first.approvalStatus, equals(EvidenceApprovalStatus.approved));
        expect(first.exactVersion, contains('Juice Shop'));
      },
    );

    test('validateLabScope enforces strict local container ports', () async {
      // Allowed local container targets
      expect(
        await repository.validateLabScope('http://localhost:3000'),
        isTrue,
      );
      expect(
        await repository.validateLabScope('http://localhost:8080'),
        isTrue,
      );
      expect(
        await repository.validateLabScope('http://127.0.0.1:3000'),
        isTrue,
      );

      // Blocked external or invalid targets
      expect(await repository.validateLabScope('https://example.com'), isFalse);
      expect(await repository.validateLabScope('http://localhost:80'), isFalse);
      expect(
        await repository.validateLabScope('http://192.168.1.50:3000'),
        isFalse,
      );
      expect(await repository.validateLabScope('not-a-valid-url'), isFalse);
    });

    test('submitAssessmentSetup throws when confirmation is false', () async {
      const unconfirmed = AssessmentSetupConfig(
        labTargetId: 'juice_shop_local',
        targetUrl: 'http://localhost:3000',
        selectedSpecialists: ['sql_injection_analyst'],
        isAuthorizedLabConfirmed: false,
      );

      expect(
        () => repository.submitAssessmentSetup(unconfirmed),
        throwsA(isA<ArgumentError>()),
      );
    });

    test(
      'submitAssessmentSetup succeeds when authorized lab confirmed',
      () async {
        const confirmed = AssessmentSetupConfig(
          labTargetId: 'juice_shop_local',
          targetUrl: 'http://localhost:3000',
          selectedSpecialists: ['sql_injection_analyst'],
          isAuthorizedLabConfirmed: true,
        );

        final sessionId = await repository.submitAssessmentSetup(confirmed);
        expect(sessionId, startsWith('SESSION-'));
      },
    );
  });

  group('AssessmentSetupNotifier State Management Tests', () {
    test('initializes with default safety configuration', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(assessmentSetupProvider);
      expect(state.labTargetId, equals('juice_shop_local'));
      expect(state.targetUrl, equals('http://localhost:3000'));
      expect(state.adversarialReviewerEnabled, isTrue);
      expect(state.strictEvidenceGrounding, isTrue);
      expect(state.isAuthorizedLabConfirmed, isFalse);
      expect(state.selectedSpecialists, contains('sql_injection_analyst'));
    });

    test('toggling specialists updates list and respects minimum', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(assessmentSetupProvider.notifier);

      notifier.toggleSpecialist('filesystem_specialist');
      expect(
        container.read(assessmentSetupProvider).selectedSpecialists,
        contains('filesystem_specialist'),
      );

      // Remove it again
      notifier.toggleSpecialist('filesystem_specialist');
      expect(
        container.read(assessmentSetupProvider).selectedSpecialists,
        isNot(contains('filesystem_specialist')),
      );
    });

    test('updating lab target resets confirmation flag', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(assessmentSetupProvider.notifier);
      notifier.setAuthorizedLabConfirmed(true);
      expect(
        container.read(assessmentSetupProvider).isAuthorizedLabConfirmed,
        isTrue,
      );

      notifier.updateLabTarget('dvwa_local', 'http://localhost:8080');
      final updated = container.read(assessmentSetupProvider);
      expect(updated.labTargetId, equals('dvwa_local'));
      expect(updated.targetUrl, equals('http://localhost:8080'));
      expect(updated.isAuthorizedLabConfirmed, isFalse);
    });
  });
}
