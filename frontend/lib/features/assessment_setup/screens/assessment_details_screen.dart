import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../services/backend_assessment_models.dart';
import '../../../services/backend_errors.dart';
import '../../../services/providers.dart';

class AssessmentDetailsScreen extends ConsumerStatefulWidget {
  final String assessmentId;

  const AssessmentDetailsScreen({super.key, required this.assessmentId});

  @override
  ConsumerState<AssessmentDetailsScreen> createState() =>
      _AssessmentDetailsScreenState();
}

class _AssessmentDetailsScreenState
    extends ConsumerState<AssessmentDetailsScreen> {
  bool _isExecuting = false;
  String? _actionError;

  Future<void> _executeAssessment() async {
    if (_isExecuting) return;
    setState(() {
      _isExecuting = true;
      _actionError = null;
    });
    try {
      await ref
          .read(aegisCoreRepositoryProvider)
          .executeAssessment(widget.assessmentId);
      ref.invalidate(backendAssessmentDetailsProvider(widget.assessmentId));
      ref.invalidate(backendAssessmentsProvider);
    } catch (error) {
      if (mounted) setState(() => _actionError = userFacingBackendError(error));
    } finally {
      if (mounted) setState(() => _isExecuting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final details = ref.watch(
      backendAssessmentDetailsProvider(widget.assessmentId),
    );
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assessment Details'),
        actions: [
          IconButton(
            tooltip: 'Refresh assessment',
            onPressed: _isExecuting
                ? null
                : () => ref.invalidate(
                    backendAssessmentDetailsProvider(widget.assessmentId),
                  ),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: details.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _loadError(
          userFacingBackendError(error),
          () => ref.invalidate(
            backendAssessmentDetailsProvider(widget.assessmentId),
          ),
        ),
        data: (value) => value == null
            ? _loadError(
                'Assessment was not found.',
                () => Navigator.of(context).maybePop(),
              )
            : _buildDetails(value),
      ),
    );
  }

  Widget _buildDetails(BackendAssessmentDetails details) {
    final assessment = details.assessment;
    final canExecute =
        assessment.status == BackendAssessmentStatus.created ||
        assessment.status == BackendAssessmentStatus.pending;
    final evidenceById = {
      for (final item
          in details.evidence ?? const <BackendAssessmentEvidence>[])
        item.evidenceId: item,
    };

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _sectionCard(
                title: 'Assessment',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 12,
                      runSpacing: 10,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        StatusBadge(
                          label: _statusLabel(assessment.status),
                          color: _statusColor(assessment.status),
                        ),
                        Text(
                          assessment.assessmentId,
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _keyValue('Target endpoint', assessment.targetUrl),
                    _keyValue('Created', assessment.createdAt),
                    if (assessment.updatedAt != null)
                      _keyValue('Updated', assessment.updatedAt!),
                    if (assessment.outcome != null) ...[
                      const SizedBox(height: 8),
                      const Text(
                        'Execution outcome',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        assessment.outcome!,
                        style: const TextStyle(color: AppTheme.textPrimary),
                      ),
                    ],
                    if (assessment.status ==
                        BackendAssessmentStatus.running) ...[
                      const SizedBox(height: 14),
                      const Text(
                        'Execution is still running. Refresh to retrieve the latest persisted status.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      ),
                    ],
                    if (_actionError != null) ...[
                      const SizedBox(height: 12),
                      _message(_actionError!, isError: true),
                    ],
                    if (canExecute) ...[
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: _isExecuting ? null : _executeAssessment,
                        icon: _isExecuting
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.play_arrow),
                        label: Text(
                          _isExecuting
                              ? 'Executing passive check…'
                              : 'Execute passive check',
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'The backend revalidates authorization and lifecycle state before its single passive HTTP HEAD request.',
                        style: TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 12,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _sectionCard(
                title: 'Official deterministic findings',
                trailing: details.findings == null
                    ? null
                    : StatusBadge(
                        label: '${details.findings!.length} findings',
                        color: AppTheme.accentCyan,
                      ),
                child: details.findingsError != null
                    ? _message(details.findingsError!, isError: true)
                    : details.findings == null
                    ? const Text(
                        'Findings could not be loaded. Assessment status remains available above.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      )
                    : details.findings!.isEmpty
                    ? const Text(
                        'No deterministic findings were returned for this assessment.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      )
                    : Column(
                        children: [
                          for (final finding in details.findings!)
                            _findingCard(finding, evidenceById),
                        ],
                      ),
              ),
              const SizedBox(height: 20),
              _advisorySection(details),
              const SizedBox(height: 20),
              _sectionCard(
                title: 'Persisted evidence',
                trailing: details.evidence == null
                    ? null
                    : StatusBadge(
                        label: '${details.evidence!.length} items',
                        color: AppTheme.accentCyan,
                      ),
                child: details.evidenceError != null
                    ? _message(details.evidenceError!, isError: true)
                    : details.evidence == null
                    ? const Text(
                        'Evidence could not be loaded. Official findings are shown separately.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      )
                    : details.evidence!.isEmpty
                    ? const Text(
                        'No evidence items have been persisted.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      )
                    : Column(
                        children: [
                          for (final item in details.evidence!)
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(
                                Icons.receipt_long_outlined,
                                color: AppTheme.accentCyan,
                              ),
                              title: Text(
                                item.evidenceId,
                                style: const TextStyle(fontSize: 12),
                              ),
                              subtitle: Text(
                                'HTTP HEAD • ${item.collectionStatus}${item.httpStatus == null ? '' : ' • ${item.httpStatus}'} • ${item.observedAt}',
                                style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                        ],
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _findingCard(
    BackendAssessmentFinding finding,
    Map<String, BackendAssessmentEvidence> evidenceById,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: AppTheme.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 10,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                StatusBadge(
                  label: finding.severity.toUpperCase(),
                  color: _severityColor(finding.severity),
                ),
                Text(
                  finding.title,
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              finding.description,
              style: const TextStyle(color: AppTheme.textPrimary, height: 1.45),
            ),
            const SizedBox(height: 8),
            Text(
              'Rule ${finding.ruleId} • confidence ${finding.confidence}',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 12,
              ),
            ),
            if (finding.remediation.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Remediation: ${finding.remediation}',
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  height: 1.4,
                ),
              ),
            ],
            if (finding.evidenceIds.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Evidence references',
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              for (final id in finding.evidenceIds)
                Text(
                  evidenceById.containsKey(id)
                      ? '$id • ${evidenceById[id]!.collectionStatus}'
                      : '$id • not returned by the evidence API',
                  style: TextStyle(
                    color: evidenceById.containsKey(id)
                        ? AppTheme.textPrimary
                        : AppTheme.statusAbstained,
                    fontSize: 12,
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _advisorySection(BackendAssessmentDetails details) {
    final advisory = details.advisory;
    final message = switch (advisory.status) {
      BackendAdvisoryStatus.notReturned =>
        'No advisory review result was returned for this assessment.',
      BackendAdvisoryStatus.disabled =>
        'The advisory reviewer is disabled by backend configuration. Deterministic findings are unaffected.',
      BackendAdvisoryStatus.unavailable =>
        'The advisory reviewer was unavailable. Deterministic findings remain authoritative and unchanged.',
      BackendAdvisoryStatus.abstained =>
        'The reviewer abstained. No advisory interpretation is displayed.',
      BackendAdvisoryStatus.invalid =>
        'The advisory response was rejected because its structure or finding and evidence references could not be validated.',
      BackendAdvisoryStatus.reviewed => null,
    };

    return _sectionCard(
      title: 'AI advisory • non-authoritative',
      trailing: StatusBadge(
        label: switch (advisory.status) {
          BackendAdvisoryStatus.notReturned => 'NOT RETURNED',
          BackendAdvisoryStatus.disabled => 'DISABLED',
          BackendAdvisoryStatus.unavailable => 'UNAVAILABLE',
          BackendAdvisoryStatus.abstained => 'ABSTAINED',
          BackendAdvisoryStatus.invalid => 'REJECTED',
          BackendAdvisoryStatus.reviewed => 'ADVISORY ONLY',
        },
        color: AppTheme.statusAbstained,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'This is optional AI-generated commentary. It is not an official finding and cannot change backend severity or assessment status.',
            style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 12),
          if (message != null)
            Text(message, style: const TextStyle(color: AppTheme.textPrimary))
          else
            for (final review in advisory.reviews) ...[
              Card(
                margin: const EdgeInsets.only(bottom: 10),
                color: AppTheme.cardBackground,
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'References deterministic finding ${review.findingId}',
                        style: const TextStyle(
                          color: AppTheme.accentCyan,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      _advisoryTextBlock('Inferred risk', review.inferredRisk),
                      _advisoryTextBlock('Uncertainty', review.uncertainty),
                      _advisoryTextBlock(
                        'Recommendation',
                        review.recommendation,
                      ),
                      Text(
                        'Evidence: ${review.evidenceIds.join(', ')}',
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
        ],
      ),
    );
  }

  Widget _advisoryTextBlock(String title, String content) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        // Plain Text intentionally renders server content without HTML/Markdown.
        Text(content, style: const TextStyle(color: AppTheme.textPrimary)),
      ],
    ),
  );

  Widget _sectionCard({
    required String title,
    required Widget child,
    Widget? trailing,
  }) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              if (trailing != null) trailing,
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    ),
  );

  Widget _keyValue(String label, String value) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 118,
          child: Text(
            label,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12),
          ),
        ),
      ],
    ),
  );

  Widget _message(String value, {bool isError = false}) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: (isError ? AppTheme.severityCritical : AppTheme.accentCyan)
          .withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(
        color: (isError ? AppTheme.severityCritical : AppTheme.accentCyan)
            .withValues(alpha: 0.45),
      ),
    ),
    child: Text(value, style: const TextStyle(color: AppTheme.textPrimary)),
  );

  Widget _loadError(String value, VoidCallback onRetry) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 560),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: AppTheme.severityCritical),
            const SizedBox(height: 10),
            Text(value, textAlign: TextAlign.center),
            const SizedBox(height: 14),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    ),
  );

  static String _statusLabel(BackendAssessmentStatus status) =>
      switch (status) {
        BackendAssessmentStatus.created => 'CREATED',
        BackendAssessmentStatus.pending => 'PENDING',
        BackendAssessmentStatus.running => 'RUNNING',
        BackendAssessmentStatus.completed => 'COMPLETED',
        BackendAssessmentStatus.failed => 'FAILED',
      };

  static Color _statusColor(BackendAssessmentStatus status) => switch (status) {
    BackendAssessmentStatus.created ||
    BackendAssessmentStatus.pending => AppTheme.accentCyan,
    BackendAssessmentStatus.running => AppTheme.severityMedium,
    BackendAssessmentStatus.completed => AppTheme.statusVerified,
    BackendAssessmentStatus.failed => AppTheme.severityCritical,
  };

  static Color _severityColor(String severity) => switch (severity) {
    'critical' => AppTheme.severityCritical,
    'high' => AppTheme.severityHigh,
    'medium' => AppTheme.severityMedium,
    'low' => AppTheme.severityLow,
    _ => AppTheme.severityInfo,
  };
}
