import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/widgets/stat_card.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../../../services/aegiscore_configuration.dart';
import '../../findings/models/finding_model.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(repositoryModeProvider) == AegisCoreMode.live) {
      return const _LiveDashboardScreen();
    }
    final findingsAsync = ref.watch(findingsProvider);
    final reportAsync = ref.watch(evaluationReportProvider);

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Security Assessment Dashboard',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Uncertainty-Aware Assessment & Evidence Verification Overview',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: ElevatedButton.icon(
              onPressed: () => context.go(RouteConstants.assessmentSetup),
              icon: const Icon(Icons.add_moderator, size: 16),
              label: const Text('New Assessment'),
            ),
          ),
        ],
      ),
      body: findingsAsync.when(
        data: (findings) {
          return reportAsync.when(
            data: (report) => _buildDashboardContent(context, findings, report),
            loading: () =>
                const LoadingStateView(message: 'Loading report metrics...'),
            error: (err, _) => RepositoryErrorStateView(
              error: err,
              onRetry: () {
                ref.invalidate(findingsProvider);
                ref.invalidate(evaluationReportProvider);
              },
            ),
          );
        },
        loading: () =>
            const LoadingStateView(message: 'Loading assessment overview...'),
        error: (err, _) => RepositoryErrorStateView(
          error: err,
          onRetry: () => ref.invalidate(findingsProvider),
        ),
      ),
    );
  }

  Widget _buildDashboardContent(
    BuildContext context,
    List<FindingModel> findings,
    dynamic report,
  ) {
    final verifiedCount = findings
        .where((f) => f.reviewStatus == ReviewStatus.verified)
        .length;
    final challengedCount = findings
        .where((f) => f.reviewStatus == ReviewStatus.challenged)
        .length;
    final rejectedCount = findings
        .where((f) => f.reviewStatus == ReviewStatus.rejected)
        .length;
    final abstainedCount = findings
        .where((f) => f.reviewStatus == ReviewStatus.abstained)
        .length;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Stat Cards Grid
          LayoutBuilder(
            builder: (context, constraints) {
              final crossAxisCount = constraints.maxWidth >= 1200
                  ? 4
                  : constraints.maxWidth >= 720
                  ? 2
                  : 1;

              return GridView.count(
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: crossAxisCount == 1 ? 2.5 : 1.8,
                children: [
                  StatCard(
                    title: 'Total Findings',
                    value: findings.length.toString(),
                    subtitle: 'Across active lab targets',
                    icon: Icons.bug_report_outlined,
                    accentColor: AppTheme.accentCyan,
                    trailingBadge: const StatusBadge(
                      label: 'OFFLINE FIXTURE',
                      color: AppTheme.statusAbstained,
                    ),
                  ),
                  StatCard(
                    title: 'Reviewer Verified',
                    value: verifiedCount.toString(),
                    subtitle: 'Grounded in valid evidence',
                    icon: Icons.verified_user_outlined,
                    accentColor: AppTheme.statusVerified,
                    trailingBadge: StatusBadge(
                      label:
                          '${((verifiedCount / (findings.isEmpty ? 1 : findings.length)) * 100).toInt()}%',
                      color: AppTheme.statusVerified,
                    ),
                  ),
                  StatCard(
                    title: 'Challenged / Rejected',
                    value: (challengedCount + rejectedCount).toString(),
                    subtitle: 'Adversarial reviewer interventions',
                    icon: Icons.gavel_outlined,
                    accentColor: AppTheme.severityHigh,
                    trailingBadge: StatusBadge(
                      label: '$rejectedCount REJECTED',
                      color: AppTheme.statusRejected,
                    ),
                  ),
                  StatCard(
                    title: 'Specialist Abstentions',
                    value: abstainedCount.toString(),
                    subtitle: 'Uncertainty engine fail-safe',
                    icon: Icons.pause_circle_outline,
                    accentColor: AppTheme.statusAbstained,
                    trailingBadge: const StatusBadge(
                      label: 'FAIL-SAFE',
                      color: AppTheme.statusAbstained,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 28),

          // Main Section: Recent Assessment History & Vulnerability Breakdown
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1000) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 6,
                      child: _buildRecentAssessmentsCard(context, findings),
                    ),
                    const SizedBox(width: 20),
                    Expanded(
                      flex: 4,
                      child: _buildVulnerabilityCategoryCard(context),
                    ),
                  ],
                );
              } else {
                return Column(
                  children: [
                    _buildRecentAssessmentsCard(context, findings),
                    const SizedBox(height: 20),
                    _buildVulnerabilityCategoryCard(context),
                  ],
                );
              }
            },
          ),
          const SizedBox(height: 28),

          // Secondary Section: Evidence Provenance & Benchmark Summary
          _buildBenchmarkQuickBanner(context, report),
        ],
      ),
    );
  }

  Widget _buildRecentAssessmentsCard(
    BuildContext context,
    List<FindingModel> findings,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Recent Assessment Findings',
                  style: TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                TextButton(
                  onPressed: () => context.go(RouteConstants.findings),
                  child: const Text('View All Findings →'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Divider(height: 1, color: AppTheme.cardBorder),
            const SizedBox(height: 12),
            if (findings.isEmpty)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: Text(
                    'No findings recorded yet.',
                    style: TextStyle(color: AppTheme.textMuted),
                  ),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: findings.take(4).length,
                separatorBuilder: (_, __) =>
                    const Divider(height: 16, color: AppTheme.cardBorder),
                itemBuilder: (context, index) {
                  final f = findings[index];
                  return InkWell(
                    onTap: () =>
                        context.go(RouteConstants.findingDetailsPath(f.id)),
                    borderRadius: BorderRadius.circular(6),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: 8,
                        horizontal: 4,
                      ),
                      child: Row(
                        children: [
                          StatusBadge(
                            label: f.severity.label,
                            color: f.severity.color,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  f.title,
                                  style: const TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${f.targetApp} • ${f.locus.formattedCoordinate}',
                                  style: const TextStyle(
                                    color: AppTheme.textSecondary,
                                    fontSize: 12,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          StatusBadge(
                            label: f.reviewStatus.label,
                            color: f.reviewStatus.color,
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildVulnerabilityCategoryCard(BuildContext context) {
    const categories = [
      {
        'name': 'SQL Injection',
        'count': '14 cases',
        'color': AppTheme.severityCritical,
      },
      {
        'name': 'Cross-Site Scripting (XSS)',
        'count': '12 cases',
        'color': AppTheme.severityHigh,
      },
      {
        'name': 'Insecure Deserialization',
        'count': '6 cases',
        'color': AppTheme.severityMedium,
      },
      {
        'name': 'Path Traversal',
        'count': '4 cases',
        'color': AppTheme.severityLow,
      },
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Target Vulnerability Catalog',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Distribution across benchmark suites',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            const Divider(height: 1, color: AppTheme.cardBorder),
            const SizedBox(height: 12),
            ...categories.map((cat) {
              final color = cat['color'] as Color;
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          cat['name'] as String,
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Text(
                      cat['count'] as String,
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildBenchmarkQuickBanner(BuildContext context, dynamic report) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.accentCyan.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppTheme.accentCyan.withValues(alpha: 0.3),
                ),
              ),
              child: const Icon(
                Icons.analytics_outlined,
                size: 28,
                color: AppTheme.accentCyan,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Offline Synthetic Evaluation Summary',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Precision: ${(report.precision * 100).toStringAsFixed(1)}% • '
                    'Recall: ${(report.recall * 100).toStringAsFixed(1)}% • '
                    'Specificity: ${(report.specificity * 100).toStringAsFixed(1)}% • '
                    'Grounding: ${(report.evidenceGroundingRate * 100).toStringAsFixed(1)}%',
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            OutlinedButton(
              onPressed: () => context.go(RouteConstants.reports),
              child: const Text('View Full Report'),
            ),
          ],
        ),
      ),
    );
  }
}

class _LiveDashboardScreen extends ConsumerWidget {
  const _LiveDashboardScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(backendDashboardSummaryProvider);
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Text('Persisted Backend Dashboard'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: StatusBadge(
              label: 'LIVE BACKEND MODE',
              color: AppTheme.accentCyan,
            ),
          ),
        ],
      ),
      body: summaryAsync.when(
        loading: () => const LoadingStateView(
          message: 'Loading persisted backend summary...',
        ),
        error: (error, _) => RepositoryErrorStateView(
          error: error,
          onRetry: () => ref.invalidate(backendDashboardSummaryProvider),
        ),
        data: (summary) => SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1000),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Counts from persisted offline fixture runs. These are synthetic replay outputs, not empirical assessments.',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 20),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final columns = constraints.maxWidth >= 720 ? 3 : 1;
                      return GridView.count(
                        crossAxisCount: columns,
                        crossAxisSpacing: 14,
                        mainAxisSpacing: 14,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        childAspectRatio: columns == 1 ? 2.5 : 1.8,
                        children: [
                          StatCard(
                            title: 'Stored Replay Runs',
                            value: summary.sessionCount.toString(),
                            subtitle:
                                'Synthetic: ${summary.syntheticOfflineRunCount} • Empirical: ${summary.empiricalRunCount}',
                            icon: Icons.history,
                            accentColor: AppTheme.accentCyan,
                          ),
                          StatCard(
                            title: 'Recorded Findings',
                            value: summary.findingCount.toString(),
                            subtitle:
                                '${summary.verifiedRunCount} verified runs',
                            icon: Icons.bug_report_outlined,
                            accentColor: AppTheme.statusVerified,
                          ),
                          StatCard(
                            title: 'Incomplete / Failed',
                            value:
                                '${summary.incompleteCount} / ${summary.failedCount}',
                            subtitle: 'Failures are reported separately',
                            icon: Icons.warning_amber_outlined,
                            accentColor: AppTheme.severityHigh,
                          ),
                          StatCard(
                            title: 'Completed Runs',
                            value: summary.completedCount.toString(),
                            subtitle: '${summary.abstainedRunCount} abstained',
                            icon: Icons.check_circle_outline,
                            accentColor: AppTheme.primaryTeal,
                          ),
                          StatCard(
                            title: 'Stored Evaluation Reports',
                            value: summary.reportCount.toString(),
                            subtitle: 'Generated by offline harness only',
                            icon: Icons.analytics_outlined,
                            accentColor: AppTheme.accentBlue,
                          ),
                        ],
                      );
                    },
                  ),
                  if (summary.sessionCount == 0) ...[
                    const SizedBox(height: 16),
                    const EmptyStateView(
                      title: 'No persisted replay records',
                      message:
                          'The configured local store is available but contains no completed offline workflow outputs yet.',
                    ),
                  ],
                  const SizedBox(height: 20),
                  const Text(
                    'Recent Offline Replay Sessions',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  ref
                      .watch(backendRecentSessionsProvider)
                      .when(
                        loading: () => const LoadingStateView(
                          message: 'Loading recent replay sessions...',
                        ),
                        error: (error, _) => RepositoryErrorStateView(
                          error: error,
                          onRetry: () =>
                              ref.invalidate(backendRecentSessionsProvider),
                        ),
                        data: (sessions) => sessions.isEmpty
                            ? const EmptyStateView(
                                title: 'No replay sessions',
                                message:
                                    'No saved offline run metadata is available.',
                              )
                            : Column(
                                children: sessions
                                    .map(
                                      (session) => Card(
                                        child: ListTile(
                                          onTap: () => context.go(
                                            RouteConstants.sessionDetailsPath(
                                              session.sessionId,
                                            ),
                                          ),
                                          title: Text(
                                            '${session.caseId} • ${session.disposition.toUpperCase()}',
                                          ),
                                          subtitle: Text(
                                            '${session.runnerId} • ${session.status} • ${session.endedAt?.toLocal().toString().split('.').first ?? 'Time not recorded'}',
                                          ),
                                          trailing: StatusBadge(
                                            label: session.isSynthetic
                                                ? 'SYNTHETIC'
                                                : 'EMPIRICAL',
                                            color: session.isSynthetic
                                                ? AppTheme.statusAbstained
                                                : AppTheme.statusVerified,
                                          ),
                                        ),
                                      ),
                                    )
                                    .toList(),
                              ),
                      ),
                  const SizedBox(height: 16),
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(18),
                      child: Text(
                        'Live target assessment execution is not available. This dashboard only summarizes records written by the offline evaluation workflow.',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
