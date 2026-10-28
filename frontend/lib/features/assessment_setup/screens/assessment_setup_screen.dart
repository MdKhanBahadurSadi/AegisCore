import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../services/aegiscore_configuration.dart';
import '../../../services/providers.dart';
import '../../../services/backend_errors.dart';

class AssessmentSetupScreen extends ConsumerStatefulWidget {
  const AssessmentSetupScreen({super.key});

  @override
  ConsumerState<AssessmentSetupScreen> createState() =>
      _AssessmentSetupScreenState();
}

class _AssessmentSetupScreenState extends ConsumerState<AssessmentSetupScreen> {
  bool _isSubmitting = false;
  String? _successSessionId;
  String? _errorMessage;

  final List<Map<String, String>> _availableSpecialists = const [
    {
      'id': 'sql_injection_analyst',
      'name': 'SQL Injection Analyst',
      'desc':
          'Examines SQL AST query traces, string interpolation, and database error signatures.',
    },
    {
      'id': 'xss_specialist',
      'name': 'XSS Specialist',
      'desc':
          'Analyzes DOM sinks, reflection contexts, and encoding bypass vectors.',
    },
    {
      'id': 'deserialization_specialist',
      'name': 'Deserialization Specialist',
      'desc':
          'Audits object serialization formats, unsafe parsers, and YAML/JSON gadgets.',
    },
    {
      'id': 'filesystem_specialist',
      'name': 'Filesystem & Path Specialist',
      'desc':
          'Audits file upload handlers, path normalization, and traversal controls.',
    },
  ];

  Future<void> _handleLaunchAssessment() async {
    if (_isSubmitting) return;
    final setup = ref.read(assessmentSetupProvider);
    if (!setup.isAuthorizedLabConfirmed) {
      setState(() {
        _errorMessage =
            'You must confirm that the target is an authorized, locally containerized lab.';
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
          'an authorized offline assessment submission API',
        );
      }
      if (!await repo.validateLabScope(setup.targetUrl)) {
        throw ArgumentError(
          'The target must be an HTTP localhost lab on port 3000 or 8080.',
        );
      }
      final sessionId = await repo.submitAssessmentSetup(setup);
      if (!mounted) return;
      setState(() {
        _isSubmitting = false;
        _successSessionId = sessionId;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSubmitting = false;
        _errorMessage = e is ArgumentError
            ? e.message.toString()
            : userFacingBackendError(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final setup = ref.watch(assessmentSetupProvider);
    final notifier = ref.read(assessmentSetupProvider.notifier);
    final repo = ref.watch(aegisCoreRepositoryProvider);
    final canSubmitAssessment = repo.supportsAssessmentSubmission;
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
              'Configure Multi-Specialist Roles & Evidence Grounding Rules',
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
            constraints: const BoxConstraints(maxWidth: 880),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Safety Boundary Notice Card
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.severityHigh.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppTheme.severityHigh.withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.security,
                        size: 22,
                        color: AppTheme.severityHigh,
                      ),
                      SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'SAFETY INVARIANT: STRICT AUTHORIZED LAB SCOPE',
                              style: TextStyle(
                                color: AppTheme.severityHigh,
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.5,
                              ),
                            ),
                            SizedBox(height: 4),
                            Text(
                              'AEGISCORE AI strictly prohibits automated execution against unapproved external targets. '
                              'Target scanning and assessment are restricted to offline local containerized environments '
                              '(localhost:3000 / localhost:8080).',
                              style: TextStyle(
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
                ),
                const SizedBox(height: 24),

                if (!canSubmitAssessment) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.severityHigh.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.severityHigh.withValues(alpha: 0.4),
                      ),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.info_outline,
                          color: AppTheme.severityHigh,
                          size: 20,
                        ),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Assessment submission is unavailable in live mode. The configured FastAPI backend has no authorized offline assessment execution endpoint; this form cannot start an assessment.',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 12,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                if (_successSessionId != null) ...[
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppTheme.statusVerified.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.statusVerified.withValues(alpha: 0.5),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: AppTheme.statusVerified,
                              size: 22,
                            ),
                            SizedBox(width: 10),
                            Text(
                              'Assessment Configuration Initialized',
                              style: TextStyle(
                                color: AppTheme.statusVerified,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          isDemoMode
                              ? 'Synthetic demo session created: $_successSessionId\nNo backend assessment was executed.'
                              : 'Session: $_successSessionId',
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            ElevatedButton(
                              onPressed: () =>
                                  context.go(RouteConstants.findings),
                              child: const Text('View Findings'),
                            ),
                            const SizedBox(width: 12),
                            OutlinedButton(
                              onPressed: () {
                                setState(() {
                                  _successSessionId = null;
                                  notifier.reset();
                                });
                              },
                              child: const Text('Configure Another'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                if (_errorMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.severityCritical.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.severityCritical.withValues(alpha: 0.5),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.error_outline,
                          color: AppTheme.severityCritical,
                          size: 20,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(
                              color: AppTheme.severityCritical,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // Step 1: Target Scope Selection
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '1. Target Lab Scope',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Select one of the authorized local container testbeds.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 16),
                        ...AppConstants.authorizedLabTargets.map((target) {
                          final isSelected = setup.labTargetId == target.id;
                          return InkWell(
                            onTap: () => notifier.updateLabTarget(
                              target.id,
                              target.defaultUrl,
                            ),
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 12),
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? AppTheme.primaryTeal.withValues(
                                        alpha: 0.08,
                                      )
                                    : AppTheme.surfaceVariant,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: isSelected
                                      ? AppTheme.primaryTeal
                                      : AppTheme.cardBorder,
                                  width: isSelected ? 1.5 : 1,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    isSelected
                                        ? Icons.radio_button_checked
                                        : Icons.radio_button_off,
                                    color: isSelected
                                        ? AppTheme.primaryTeal
                                        : AppTheme.textMuted,
                                    size: 20,
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Text(
                                              target.name,
                                              style: const TextStyle(
                                                color: AppTheme.textPrimary,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            StatusBadge(
                                              label: target.version,
                                              color: AppTheme.accentCyan,
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
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
                        }),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Step 2: Specialist Roles & Consensus
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '2. Multi-Specialist Roles',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Active domain specialists participate in consensus and uncertainty aggregation.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 16),
                        ..._availableSpecialists.map((spec) {
                          final isChecked = setup.selectedSpecialists.contains(
                            spec['id'],
                          );
                          return CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            value: isChecked,
                            onChanged: (_) =>
                                notifier.toggleSpecialist(spec['id']!),
                            title: Text(
                              spec['name']!,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            subtitle: Text(
                              spec['desc']!,
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                            activeColor: AppTheme.primaryTeal,
                          );
                        }),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Step 3: Adversarial Reviewer & Grounding Settings
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '3. Reviewer & Grounding Guards',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 16),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'Enable Adversarial Evidence Reviewer',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          subtitle: const Text(
                            'Challenges speculative jumps, missing HTTP parameter grounding, and unverified CVE gadgets.',
                            style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                          value: setup.adversarialReviewerEnabled,
                          onChanged: notifier.setAdversarialReviewer,
                          activeColor: AppTheme.primaryTeal,
                        ),
                        const Divider(height: 20, color: AppTheme.cardBorder),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'Enforce Strict Citation Grounding',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          subtitle: const Text(
                            'Claims without verified citations or matching locus coordinates are marked as unsupported.',
                            style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                          value: setup.strictEvidenceGrounding,
                          onChanged: notifier.setStrictEvidenceGrounding,
                          activeColor: AppTheme.primaryTeal,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Step 4: Confirmation & Submit
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  child: Column(
                    children: [
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: setup.isAuthorizedLabConfirmed,
                        onChanged: (val) =>
                            notifier.setAuthorizedLabConfirmed(val ?? false),
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
                          'No external traffic, unapproved credentials, or live exploit payloads will be transmitted.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 11,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          OutlinedButton(
                            onPressed: notifier.reset,
                            child: const Text('Reset to Defaults'),
                          ),
                          const SizedBox(width: 14),
                          ElevatedButton.icon(
                            onPressed:
                                _isSubmitting ||
                                    !setup.isAuthorizedLabConfirmed ||
                                    !canSubmitAssessment
                                ? null
                                : _handleLaunchAssessment,
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
                                  ? 'Initializing...'
                                  : canSubmitAssessment
                                  ? 'Create Demo Session'
                                  : 'Submission Unavailable',
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
