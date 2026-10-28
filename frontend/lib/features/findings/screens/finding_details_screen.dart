import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../models/finding_model.dart';

class FindingDetailsScreen extends ConsumerWidget {
  final String findingId;

  const FindingDetailsScreen({super.key, required this.findingId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final findingAsync = ref.watch(findingDetailsProvider(findingId));

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(RouteConstants.findings),
          tooltip: 'Back to Findings',
        ),
        title: Text(
          'Finding Details: $findingId',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: findingAsync.when(
        data: (finding) {
          if (finding == null) {
            return EmptyStateView(
              title: 'Finding Not Found',
              message:
                  'No finding with identifier "$findingId" exists in the catalog.',
              action: ElevatedButton(
                onPressed: () => context.go(RouteConstants.findings),
                child: const Text('Back to Findings'),
              ),
            );
          }
          return _buildFindingDetailContent(context, finding);
        },
        loading: () => const LoadingStateView(
          message: 'Loading finding claims and evidence...',
        ),
        error: (err, _) => RepositoryErrorStateView(
          error: err,
          onRetry: () => ref.invalidate(findingDetailsProvider(findingId)),
        ),
      ),
    );
  }

  Widget _buildFindingDetailContent(BuildContext context, FindingModel f) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              StatusBadge(
                                label: f.severity.label,
                                color: f.severity.color,
                              ),
                              const SizedBox(width: 8),
                              StatusBadge(
                                label: f.reviewStatus.label,
                                color: f.reviewStatus.color,
                              ),
                              const SizedBox(width: 8),
                              StatusBadge(
                                label: f.vulnerabilityClass.toUpperCase(),
                                color: AppTheme.accentCyan,
                              ),
                            ],
                          ),
                          Text(
                            f.targetApp,
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        f.title,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Show a confidence score only when the stored record has one.
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceVariant,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.cardBorder),
                        ),
                        child:
                            f.confidenceScore != null &&
                                f.confidenceInterval != null
                            ? Wrap(
                                alignment: WrapAlignment.spaceBetween,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                spacing: 12,
                                runSpacing: 12,
                                children: [
                                  Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'SPECIALIST CONFIDENCE SCORE',
                                        style: TextStyle(
                                          color: AppTheme.textMuted,
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            '${(f.confidenceScore! * 100).toStringAsFixed(1)}%',
                                            style: const TextStyle(
                                              color: AppTheme.primaryTeal,
                                              fontSize: 20,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                          const SizedBox(width: 12),
                                          Text(
                                            'CI: ${f.confidenceInterval!.formatted}',
                                            style: const TextStyle(
                                              color: AppTheme.textSecondary,
                                              fontSize: 12,
                                              fontFamily: 'monospace',
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                  const StatusBadge(
                                    label: 'confidence_is_calibrated=false',
                                    color: AppTheme.statusAbstained,
                                  ),
                                ],
                              )
                            : Text(
                                'No confidence estimate was stored for this record. Heuristic confidence is not calibrated.',
                                style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 13,
                                ),
                              ),
                      ),
                      if (f.dataProvenanceLabel != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          f.dataProvenanceLabel!,
                          style: const TextStyle(
                            color: AppTheme.statusAbstained,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Canonical Locus Coordinates
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.gps_fixed,
                            size: 18,
                            color: AppTheme.accentCyan,
                          ),
                          SizedBox(width: 8),
                          Text(
                            'Canonical Locus Coordinates',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      const Divider(height: 1, color: AppTheme.cardBorder),
                      const SizedBox(height: 14),
                      _locusRow('Target URL', f.locus.url),
                      _locusRow('HTTP Method', f.locus.method),
                      _locusRow('Endpoint Path', f.locus.path),
                      _locusRow('Parameter', f.locus.parameter),
                      _locusRow('Vulnerable Sink', f.locus.sink),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Multi-Specialist & Reviewer Challenges Section
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.gavel,
                            size: 18,
                            color: AppTheme.severityHigh,
                          ),
                          SizedBox(width: 8),
                          Text(
                            f.isPersistedRecord
                                ? 'Offline Replay Outcome'
                                : 'Specialist Consensus & Adversarial Reviewer Decisions',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      const Divider(height: 1, color: AppTheme.cardBorder),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Text(
                            'Reporting Specialist:',
                            style: TextStyle(
                              color: AppTheme.textMuted,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(width: 10),
                          StatusBadge(
                            label: f.specialistRole,
                            color: AppTheme.accentBlue,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (f.isPersistedRecord) ...[
                        Text(
                          'Recorded decision: ${(f.recordedDecision ?? 'unknown').toUpperCase()}',
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (f.recordedRationale != null &&
                            f.recordedRationale!.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            f.recordedRationale!,
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ] else if (f.challengeReason != null) ...[
                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: AppTheme.severityHigh.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: AppTheme.severityHigh.withValues(
                                alpha: 0.4,
                              ),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(
                                    Icons.warning,
                                    size: 16,
                                    color: AppTheme.severityHigh,
                                  ),
                                  SizedBox(width: 8),
                                  Text(
                                    'Reviewer Challenge Note',
                                    style: TextStyle(
                                      color: AppTheme.severityHigh,
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                f.challengeReason!,
                                style: const TextStyle(
                                  color: Color(0xFFFDE68A),
                                  fontSize: 13,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ] else ...[
                        const Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              size: 16,
                              color: AppTheme.statusVerified,
                            ),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Adversarial reviewer confirmed locus grounding and citation integrity without challenges.',
                                style: TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                      if (f.specialistDisagreement &&
                          f.specialistDissentSummary != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.severityCritical.withValues(
                              alpha: 0.08,
                            ),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: AppTheme.severityCritical.withValues(
                                alpha: 0.3,
                              ),
                            ),
                          ),
                          child: Text(
                            'Dissent Summary: ${f.specialistDissentSummary!}',
                            style: const TextStyle(
                              color: AppTheme.severityCritical,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Claims Breakdown: Facts vs Hypotheses vs Unknowns
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(
                                Icons.format_list_bulleted,
                                size: 18,
                                color: AppTheme.primaryTeal,
                              ),
                              SizedBox(width: 8),
                              Text(
                                'Decomposed Claims & Grounding Verdicts',
                                style: TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          Text(
                            '${f.claims.length} Claims Total',
                            style: const TextStyle(
                              color: AppTheme.textMuted,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Claims are categorized into Facts, Hypotheses, Unknowns, and Assertions.',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Divider(height: 1, color: AppTheme.cardBorder),
                      const SizedBox(height: 14),
                      if (f.claims.isEmpty && f.isPersistedRecord)
                        const Text(
                          'No decomposed claim records were stored for this replay finding.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        )
                      else
                        ...f.claims.map(
                          (claim) => _buildClaimCard(context, claim),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Supporting Evidence References
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(
                                Icons.folder_shared,
                                size: 18,
                                color: AppTheme.accentCyan,
                              ),
                              SizedBox(width: 8),
                              Text(
                                'Associated Evidence Artifacts',
                                style: TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          TextButton(
                            onPressed: () =>
                                context.go(RouteConstants.evidence),
                            child: const Text('Open Evidence Explorer →'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: f.evidenceIds.map((evId) {
                          return ActionChip(
                            avatar: const Icon(
                              Icons.link,
                              size: 14,
                              color: AppTheme.primaryTeal,
                            ),
                            label: Text(evId),
                            onPressed: () =>
                                context.go(RouteConstants.evidence),
                            backgroundColor: AppTheme.surfaceVariant,
                            side: const BorderSide(color: AppTheme.cardBorder),
                          );
                        }).toList(),
                      ),
                      if (f.isPersistedRecord) ...[
                        const SizedBox(height: 10),
                        const Text(
                          'These are evidence reference IDs emitted by a synthetic replay. Their presence does not establish current source approval.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _locusRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(
                color: AppTheme.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 13,
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimCard(BuildContext context, ClaimModel claim) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceVariant,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  StatusBadge(
                    label: claim.claimType.label,
                    color: claim.claimType.color,
                  ),
                  const SizedBox(width: 8),
                  StatusBadge(
                    label: claim.verdict.label,
                    color: claim.verdict.color,
                  ),
                ],
              ),
              Text(
                claim.id,
                style: const TextStyle(
                  color: AppTheme.textMuted,
                  fontSize: 11,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            claim.statement,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          if (claim.citations.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                const Text(
                  'Citations: ',
                  style: TextStyle(color: AppTheme.textMuted, fontSize: 11),
                ),
                ...claim.citations.map(
                  (cite) => Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: Text(
                      '[$cite]',
                      style: const TextStyle(
                        color: AppTheme.primaryTeal,
                        fontSize: 11,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
          if (claim.reviewerNote != null) ...[
            const SizedBox(height: 8),
            Text(
              'Reviewer note: ${claim.reviewerNote!}',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 11,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
