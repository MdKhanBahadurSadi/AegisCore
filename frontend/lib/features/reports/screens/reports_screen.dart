import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/stat_card.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../../../services/aegiscore_configuration.dart';
import '../../../services/backend_persisted_models.dart';
import '../models/report_model.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(repositoryModeProvider) == AegisCoreMode.live) {
      final reportsAsync = ref.watch(storedEvaluationReportsProvider);
      return Scaffold(
        backgroundColor: AppTheme.scaffoldBackground,
        appBar: AppBar(
          title: const Text('Persisted Offline Evaluation Reports'),
        ),
        body: reportsAsync.when(
          data: (reports) => reports.isEmpty
              ? const EmptyStateView(
                  title: 'No stored evaluation reports',
                  message:
                      'The local store is available but no completed offline evaluation report has been persisted.',
                  icon: Icons.analytics_outlined,
                )
              : _buildStoredReports(reports),
          loading: () => const LoadingStateView(
            message: 'Loading persisted evaluation reports...',
          ),
          error: (error, _) => RepositoryErrorStateView(
            error: error,
            onRetry: () => ref.invalidate(storedEvaluationReportsProvider),
          ),
        ),
      );
    }
    final reportAsync = ref.watch(evaluationReportProvider);

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Evaluation Metrics & Benchmark Reports',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Reproducible Offline Benchmark Metrics, Wilson Score Intervals & Limitations',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
      body: reportAsync.when(
        data: (report) => _buildReportContent(context, report),
        loading: () =>
            const LoadingStateView(message: 'Loading evaluation report...'),
        error: (err, _) => RepositoryErrorStateView(
          error: err,
          onRetry: () => ref.invalidate(evaluationReportProvider),
        ),
      ),
    );
  }

  Widget _buildStoredReports(List<StoredEvaluationReportModel> reports) {
    return ListView.separated(
      padding: const EdgeInsets.all(24),
      itemCount: reports.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (context, index) =>
          _StoredReportCard(report: reports[index]),
    );
  }

  Widget _buildReportContent(BuildContext context, EvaluationReportModel r) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1080),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Report Run Metadata Banner
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Wrap(
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 16,
                    runSpacing: 12,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            crossAxisAlignment: WrapCrossAlignment.center,
                            spacing: 10,
                            runSpacing: 6,
                            children: [
                              Text(
                                r.runId,
                                style: const TextStyle(
                                  color: AppTheme.primaryTeal,
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  fontFamily: 'monospace',
                                ),
                              ),
                              const StatusBadge(
                                label: 'SYNTHETIC DEMO HARNESS RUN',
                                color: AppTheme.statusAbstained,
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Target Suite: ${r.targetSuite}',
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        'Executed: ${r.timestamp.toLocal().toString().split('.')[0]}',
                        style: const TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 12,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Confusion Matrix & Primary Metric Grid
              LayoutBuilder(
                builder: (context, constraints) {
                  final cols = constraints.maxWidth >= 900 ? 4 : 2;
                  return GridView.count(
                    crossAxisCount: cols,
                    crossAxisSpacing: 14,
                    mainAxisSpacing: 14,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    childAspectRatio: 1.8,
                    children: [
                      StatCard(
                        title: 'Precision (PPV)',
                        value: '${(r.precision * 100).toStringAsFixed(1)}%',
                        subtitle:
                            'TP: ${r.truePositives} / Pred Pos: ${r.truePositives + r.falsePositives}',
                        icon: Icons.precision_manufacturing_outlined,
                        accentColor: AppTheme.primaryTeal,
                      ),
                      StatCard(
                        title: 'Recall (Sensitivity)',
                        value: '${(r.recall * 100).toStringAsFixed(1)}%',
                        subtitle:
                            'TP: ${r.truePositives} / Actual Pos: ${r.truePositives + r.falseNegatives}',
                        icon: Icons.search_outlined,
                        accentColor: AppTheme.accentCyan,
                      ),
                      StatCard(
                        title: 'Specificity (TNR)',
                        value: '${(r.specificity * 100).toStringAsFixed(1)}%',
                        subtitle:
                            'TN: ${r.trueNegatives} / Actual Neg: ${r.trueNegatives + r.falsePositives}',
                        icon: Icons.shield_outlined,
                        accentColor: AppTheme.statusVerified,
                      ),
                      StatCard(
                        title: 'F1 Score',
                        value: '${(r.f1Score * 100).toStringAsFixed(1)}%',
                        subtitle: 'Harmonic mean (non-linear)',
                        icon: Icons.balance_outlined,
                        accentColor: AppTheme.accentBlue,
                      ),
                      StatCard(
                        title: 'Evaluation Coverage',
                        value: '${(r.coverage * 100).toStringAsFixed(1)}%',
                        subtitle:
                            '${r.totalCases - (r.totalCases * r.abstentionRate).toInt()} of ${r.totalCases} cases evaluated',
                        icon: Icons.pie_chart_outline,
                        accentColor: AppTheme.accentCyan,
                      ),
                      StatCard(
                        title: 'Abstention Rate',
                        value:
                            '${(r.abstentionRate * 100).toStringAsFixed(1)}%',
                        subtitle: 'Fail-safe uncertain cases',
                        icon: Icons.pause_circle_outline,
                        accentColor: AppTheme.statusAbstained,
                      ),
                      StatCard(
                        title: 'Evidence Grounding',
                        value:
                            '${(r.evidenceGroundingRate * 100).toStringAsFixed(1)}%',
                        subtitle: 'Grounded in valid locus',
                        icon: Icons.link_outlined,
                        accentColor: AppTheme.primaryTeal,
                      ),
                      StatCard(
                        title: 'Citation Validation',
                        value:
                            '${(r.citationValidationRate * 100).toStringAsFixed(1)}%',
                        subtitle: 'Verified excerpt matches',
                        icon: Icons.fact_check_outlined,
                        accentColor: AppTheme.statusVerified,
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: 24),

              // Evaluation Limitations & Integrity Invariants Notice
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.severityHigh.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppTheme.severityHigh.withValues(alpha: 0.4),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(
                          Icons.warning_amber_rounded,
                          size: 20,
                          color: AppTheme.severityHigh,
                        ),
                        SizedBox(width: 10),
                        Text(
                          'EVALUATION INTEGRITY INVARIANTS & LIMITATIONS',
                          style: TextStyle(
                            color: AppTheme.severityHigh,
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    ...r.limitations.map(
                      (lim) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '• ',
                              style: TextStyle(color: AppTheme.severityHigh),
                            ),
                            Expanded(
                              child: Text(
                                lim,
                                style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Per-Vulnerability Category Breakdown Table
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Per-Vulnerability-Category Breakdown',
                        style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Confusion matrix metrics isolated by vulnerability class to prevent cross-category locus inflation.',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: DataTable(
                          columnSpacing: 24,
                          headingRowColor: WidgetStateProperty.all(
                            AppTheme.surfaceVariant,
                          ),
                          columns: const [
                            DataColumn(label: Text('Vulnerability Category')),
                            DataColumn(label: Text('Cases')),
                            DataColumn(label: Text('TP')),
                            DataColumn(label: Text('FP')),
                            DataColumn(label: Text('TN')),
                            DataColumn(label: Text('FN')),
                            DataColumn(label: Text('Precision')),
                            DataColumn(label: Text('Recall')),
                            DataColumn(label: Text('F1 Score')),
                          ],
                          rows: r.categoryBreakdown.entries.map((entry) {
                            final c = entry.value;
                            return DataRow(
                              cells: [
                                DataCell(
                                  Text(
                                    c.categoryName,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                                DataCell(Text(c.totalCases.toString())),
                                DataCell(Text(c.truePositives.toString())),
                                DataCell(Text(c.falsePositives.toString())),
                                DataCell(Text(c.trueNegatives.toString())),
                                DataCell(Text(c.falseNegatives.toString())),
                                DataCell(
                                  Text(
                                    '${(c.precision * 100).toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                                DataCell(
                                  Text(
                                    '${(c.recall * 100).toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                                DataCell(
                                  Text(
                                    '${(c.f1Score * 100).toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                              ],
                            );
                          }).toList(),
                        ),
                      ),
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
}

class _StoredReportCard extends ConsumerStatefulWidget {
  final StoredEvaluationReportModel report;

  const _StoredReportCard({required this.report});

  @override
  ConsumerState<_StoredReportCard> createState() => _StoredReportCardState();
}

class _StoredReportCardState extends ConsumerState<_StoredReportCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final report = widget.report;
    String metricText(StoredMetricModel? metric) {
      if (metric == null) return 'Not reported';
      if (metric.value == null) return 'Undefined (${metric.status})';
      return '${(metric.value! * 100).toStringAsFixed(1)}%';
    }

    return Card(
      child: ExpansionTile(
        onExpansionChanged: (expanded) => setState(() => _expanded = expanded),
        title: Text(
          report.reportId,
          style: const TextStyle(
            color: AppTheme.primaryTeal,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
        subtitle: Text(
          '${report.fixtureDatasetId} v${report.fixtureDatasetVersion} • ${report.runnerCondition}',
          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
        ),
        leading: const StatusBadge(
          label: 'SYNTHETIC',
          color: AppTheme.statusAbstained,
        ),
        childrenPadding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Runner: ${report.runnerId} • ${report.totalCases} cases • ${report.createdAt.toLocal().toString().split('.').first}',
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _count('TP', report.truePositives),
                    _count('FP', report.falsePositives),
                    _count('FN', report.falseNegatives),
                    _count('TN', report.trueNegatives),
                    _count('Abstained', report.abstainedCases),
                    _count('Incomplete', report.incompleteCaseCount),
                    _count('Failed', report.failedCaseCount),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Precision ${metricText(report.metrics['precision'])} • Recall ${metricText(report.metrics['recall'])} • F1 ${metricText(report.metrics['f1_score'])}',
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Synthetic fixture replay metrics; not empirical validation or live target findings.',
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                ),
                if (_expanded) ...[
                  const Divider(height: 24),
                  ref
                      .watch(
                        storedEvaluationReportDetailsProvider(report.reportId),
                      )
                      .when(
                        loading: () => const LoadingStateView(
                          message: 'Loading stored report details...',
                        ),
                        error: (error, _) => RepositoryErrorStateView(
                          error: error,
                          onRetry: () => ref.invalidate(
                            storedEvaluationReportDetailsProvider(
                              report.reportId,
                            ),
                          ),
                        ),
                        data: (detail) => detail == null
                            ? const Text('Stored report detail was not found.')
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Persisted runs: ${detail.rawRunCount} • Aggregated outcomes: ${detail.outcomeCount}',
                                  ),
                                  if (detail.failureDiagnostics.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    const Text(
                                      'Recorded failure diagnostics:',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    ...detail.failureDiagnostics.map(
                                      (diagnostic) => Padding(
                                        padding: const EdgeInsets.only(top: 4),
                                        child: Text(
                                          diagnostic,
                                          style: const TextStyle(
                                            color: AppTheme.severityHigh,
                                            fontSize: 12,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                      ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _count(String label, int value) => Chip(
    label: Text('$label: $value'),
    visualDensity: VisualDensity.compact,
    side: const BorderSide(color: AppTheme.cardBorder),
    backgroundColor: AppTheme.surfaceVariant,
  );
}
