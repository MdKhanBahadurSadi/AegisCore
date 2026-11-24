import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../services/aegiscore_configuration.dart';
import '../../../services/backend_assessment_models.dart';
import '../../../services/backend_errors.dart';
import '../../../services/lab_scope.dart';
import '../../../services/providers.dart';

class AssessmentSetupScreen extends ConsumerStatefulWidget {
  const AssessmentSetupScreen({super.key});

  @override
  ConsumerState<AssessmentSetupScreen> createState() =>
      _AssessmentSetupScreenState();
}

class _AssessmentSetupScreenState extends ConsumerState<AssessmentSetupScreen> {
  bool _isSubmitting = false;
  String? _demoSessionId;
  String? _errorMessage;

  Future<void> _createAssessment() async {
    if (_isSubmitting) return;
    final setup = ref.read(assessmentSetupProvider);
    if (!setup.isAuthorizedLabConfirmed) {
      setState(() {
        _errorMessage = 'Confirm that this is an authorized local test target.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final repo = ref.read(aegisCoreRepositoryProvider);
      if (!repo.supportsAssessmentSubmission) {
        throw UnsupportedBackendCapabilityException(
          'the passive assessment API',
        );
      }
      if (!isAuthorizedLocalLabTarget(setup.targetUrl)) {
        throw ArgumentError(
          'Choose an HTTP loopback lab on port 3000 or 8080. The backend applies its own authorization checks.',
        );
      }

      if (repo.mode == AegisCoreMode.demo) {
        final sessionId = await repo.submitAssessmentSetup(setup);
        if (!mounted) return;
        setState(() {
          _demoSessionId = sessionId;
          _isSubmitting = false;
        });
        return;
      }

      final assessment = await repo.createAssessment(setup.targetUrl);
      if (!mounted) return;
      ref.invalidate(backendAssessmentsProvider);
      context.push(
        RouteConstants.assessmentDetailsPath(assessment.assessmentId),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = error is ArgumentError
            ? error.message.toString()
            : userFacingBackendError(error);
      });
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final setup = ref.watch(assessmentSetupProvider);
    final notifier = ref.read(assessmentSetupProvider.notifier);
    final repo = ref.watch(aegisCoreRepositoryProvider);
    final isDemoMode = repo.mode == AegisCoreMode.demo;

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Assessment Configuration',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Create and review passive HTTP HEAD assessments',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _notice(
                  icon: Icons.security,
                  title: 'PASSIVE ASSESSMENT SAFETY',
                  message:
                      'The backend must already have an authorized registration for the exact loopback endpoint. This screen cannot grant authorization. Execution remains server-validated and uses the existing passive HTTP HEAD boundary. The API has no per-assessment advisory opt-in; the reviewer remains disabled unless backend configuration enables it.',
                  color: AppTheme.severityHigh,
                ),
                const SizedBox(height: 20),
                if (isDemoMode)
                  _notice(
                    icon: Icons.info_outline,
                    title: 'DEMO FIXTURE MODE',
                    message:
                        'Demo setup creates a synthetic local session only. It does not create or execute a backend assessment.',
                    color: AppTheme.accentCyan,
                  ),
                if (isDemoMode) const SizedBox(height: 20),
                if (_errorMessage != null) ...[
                  _notice(
                    icon: Icons.error_outline,
                    title: 'REQUEST NOT COMPLETED',
                    message: _errorMessage!,
                    color: AppTheme.severityCritical,
                  ),
                  const SizedBox(height: 20),
                ],
                if (_demoSessionId != null) ...[
                  _notice(
                    icon: Icons.check_circle_outline,
                    title: 'SYNTHETIC DEMO SESSION CREATED',
                    message:
                        'Demo session: $_demoSessionId\nNo backend assessment was executed.',
                    color: AppTheme.statusVerified,
                  ),
                  const SizedBox(height: 20),
                ],
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Target loopback endpoint',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Select a configured local lab endpoint. The backend independently checks its exact authorization binding.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                            height: 1.4,
                          ),
                        ),
                        const SizedBox(height: 16),
                        for (final target in AppConstants.authorizedLabTargets)
                          _targetOption(
                            target,
                            selected: setup.labTargetId == target.id,
                            onTap: () => notifier.updateLabTarget(
                              target.id,
                              target.defaultUrl,
                            ),
                          ),
                        const SizedBox(height: 4),
                        Text(
                          'Selected endpoint: ${setup.targetUrl}',
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      children: [
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          value: setup.isAuthorizedLabConfirmed,
                          onChanged: (value) => notifier
                              .setAuthorizedLabConfirmed(value ?? false),
                          activeColor: AppTheme.primaryTeal,
                          title: const Text(
                            'I confirm this assessment targets an authorized, locally isolated container environment.',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          subtitle: const Text(
                            'This is a user confirmation only. The backend authorization registry remains authoritative.',
                            style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 11,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          alignment: WrapAlignment.end,
                          spacing: 12,
                          runSpacing: 10,
                          children: [
                            OutlinedButton(
                              onPressed: () {
                                notifier.reset();
                                setState(() {
                                  _demoSessionId = null;
                                  _errorMessage = null;
                                });
                              },
                              child: const Text('Reset'),
                            ),
                            ElevatedButton.icon(
                              onPressed:
                                  _isSubmitting ||
                                      !setup.isAuthorizedLabConfirmed
                                  ? null
                                  : _createAssessment,
                              icon: _isSubmitting
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.play_arrow, size: 18),
                              label: Text(
                                _isSubmitting
                                    ? 'Creating…'
                                    : isDemoMode
                                    ? 'Create Demo Session'
                                    : 'Create Assessment',
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                if (!isDemoMode) ...[
                  const SizedBox(height: 24),
                  _assessmentHistory(),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _assessmentHistory() {
    final assessments = ref.watch(backendAssessmentsProvider);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Persisted assessments',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh assessment history',
                  onPressed: () => ref.invalidate(backendAssessmentsProvider),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 8),
            assessments.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (error, _) => Text(
                userFacingBackendError(error),
                style: const TextStyle(color: AppTheme.severityCritical),
              ),
              data: (page) => page.items.isEmpty
                  ? const Text(
                      'No persisted assessments were found.',
                      style: TextStyle(color: AppTheme.textSecondary),
                    )
                  : Column(
                      children: [
                        for (final assessment in page.items)
                          _assessmentRow(assessment),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _assessmentRow(BackendAssessmentRecord assessment) => ListTile(
    contentPadding: EdgeInsets.zero,
    onTap: () => context.push(
      RouteConstants.assessmentDetailsPath(assessment.assessmentId),
    ),
    title: Text(
      assessment.targetUrl,
      style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
    ),
    subtitle: Text(
      '${assessment.assessmentId} • ${assessment.createdAt}',
      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
    ),
    trailing: StatusBadge(
      label: _statusLabel(assessment.status),
      color: _statusColor(assessment.status),
    ),
  );

  Widget _targetOption(
    LabTargetConfig target, {
    required bool selected,
    required VoidCallback onTap,
  }) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(8),
    child: Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: selected
            ? AppTheme.primaryTeal.withValues(alpha: 0.08)
            : AppTheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: selected ? AppTheme.primaryTeal : AppTheme.cardBorder,
        ),
      ),
      child: Row(
        children: [
          Icon(
            selected ? Icons.radio_button_checked : Icons.radio_button_off,
            color: selected ? AppTheme.primaryTeal : AppTheme.textMuted,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  target.name,
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '${target.defaultUrl} • ${target.description}',
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );

  Widget _notice({
    required IconData icon,
    required String title,
    required String message,
    required Color color,
  }) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: color.withValues(alpha: 0.4)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 22, color: color),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: color,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.4,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                message,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
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
}
