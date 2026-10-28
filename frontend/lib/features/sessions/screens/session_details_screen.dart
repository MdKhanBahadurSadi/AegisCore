import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../services/backend_persisted_models.dart';
import '../../../services/providers.dart';

class SessionDetailsScreen extends ConsumerWidget {
  final String sessionId;

  const SessionDetailsScreen({super.key, required this.sessionId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionAsync = ref.watch(backendSessionDetailsProvider(sessionId));
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(RouteConstants.dashboard),
          tooltip: 'Back to Dashboard',
        ),
        title: Text(
          'Offline Session: $sessionId',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: sessionAsync.when(
        loading: () => const LoadingStateView(
          message: 'Loading persisted session details...',
        ),
        error: (error, _) => RepositoryErrorStateView(
          error: error,
          onRetry: () => ref.invalidate(backendSessionDetailsProvider(sessionId)),
        ),
        data: (session) => session == null
            ? EmptyStateView(
                title: 'Session Not Found',
                message: 'No persisted session matches "$sessionId".',
              )
            : _SessionDetails(session: session),
      ),
    );
  }
}

class _SessionDetails extends StatelessWidget {
  final BackendOfflineSession session;

  const _SessionDetails({required this.session});

  @override
  Widget build(BuildContext context) {
    final findings = session.result['findings'] as List;
    final error = session.result['error_status'];
    final locus = session.caseContext?['locus'];
    final targetUri = locus is Map<String, dynamic>
        ? locus['target_uri']
        : null;

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    StatusBadge(
                      label: session.status.toUpperCase(),
                      color: session.status == 'completed'
                          ? AppTheme.statusVerified
                          : AppTheme.severityHigh,
                    ),
                    const StatusBadge(
                      label: 'SYNTHETIC OFFLINE FIXTURE',
                      color: AppTheme.statusAbstained,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                _detailRow('Session ID', session.sessionId),
                _detailRow('Report ID', session.reportId),
                _detailRow('Run ID', session.runId),
                _detailRow('Case', session.caseId),
                _detailRow('Runner', session.runnerId),
                _detailRow('Decision', session.disposition.toUpperCase()),
                _detailRow(
                  'Fixture dataset',
                  '${session.fixtureDatasetId} v${session.fixtureDatasetVersion}',
                ),
                _detailRow('Execution mode', 'offline_fixture'),
                _detailRow(
                  'Ended',
                  session.endedAt?.toLocal().toString().split('.').first ??
                      'Time not recorded',
                ),
                if (targetUri is String && targetUri.isNotEmpty)
                  _detailRow('Recorded fixture locus', targetUri),
                _detailRow('Stored findings in this run', '${findings.length}'),
                if (error is String && error.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  const Text(
                    'Recorded failure diagnostic',
                    style: TextStyle(
                      color: AppTheme.severityHigh,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  SelectableText(
                    error,
                    style: const TextStyle(color: AppTheme.textSecondary),
                  ),
                ],
                const SizedBox(height: 14),
                const Text(
                  'This record is an offline synthetic replay output. It does not establish an empirical vulnerability finding.',
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _detailRow(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 150,
          child: Text(
            label,
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
          ),
        ),
        Expanded(
          child: SelectableText(
            value,
            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
          ),
        ),
      ],
    ),
  );
}
