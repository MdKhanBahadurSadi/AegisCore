/// Local presentation state for selecting a preconfigured loopback target.
/// The backend receives only `targetUrl`; the confirmation is not authorization.
class AssessmentSetupConfig {
  final String labTargetId;
  final String targetUrl;
  final bool isAuthorizedLabConfirmed;

  const AssessmentSetupConfig({
    required this.labTargetId,
    required this.targetUrl,
    this.isAuthorizedLabConfirmed = false,
  });

  AssessmentSetupConfig copyWith({
    String? labTargetId,
    String? targetUrl,
    bool? isAuthorizedLabConfirmed,
  }) => AssessmentSetupConfig(
    labTargetId: labTargetId ?? this.labTargetId,
    targetUrl: targetUrl ?? this.targetUrl,
    isAuthorizedLabConfirmed:
        isAuthorizedLabConfirmed ?? this.isAuthorizedLabConfirmed,
  );
}
