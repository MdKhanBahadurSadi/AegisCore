class AssessmentSetupConfig {
  final String labTargetId;
  final String targetUrl;
  final List<String> selectedSpecialists;
  final bool adversarialReviewerEnabled;
  final bool strictEvidenceGrounding;
  final int maxTokens;
  final int timeoutSeconds;
  final bool isAuthorizedLabConfirmed;

  const AssessmentSetupConfig({
    required this.labTargetId,
    required this.targetUrl,
    required this.selectedSpecialists,
    this.adversarialReviewerEnabled = true,
    this.strictEvidenceGrounding = true,
    this.maxTokens = 2048,
    this.timeoutSeconds = 30,
    this.isAuthorizedLabConfirmed = false,
  });

  AssessmentSetupConfig copyWith({
    String? labTargetId,
    String? targetUrl,
    List<String>? selectedSpecialists,
    bool? adversarialReviewerEnabled,
    bool? strictEvidenceGrounding,
    int? maxTokens,
    int? timeoutSeconds,
    bool? isAuthorizedLabConfirmed,
  }) {
    return AssessmentSetupConfig(
      labTargetId: labTargetId ?? this.labTargetId,
      targetUrl: targetUrl ?? this.targetUrl,
      selectedSpecialists: selectedSpecialists ?? this.selectedSpecialists,
      adversarialReviewerEnabled:
          adversarialReviewerEnabled ?? this.adversarialReviewerEnabled,
      strictEvidenceGrounding:
          strictEvidenceGrounding ?? this.strictEvidenceGrounding,
      maxTokens: maxTokens ?? this.maxTokens,
      timeoutSeconds: timeoutSeconds ?? this.timeoutSeconds,
      isAuthorizedLabConfirmed:
          isAuthorizedLabConfirmed ?? this.isAuthorizedLabConfirmed,
    );
  }
}
