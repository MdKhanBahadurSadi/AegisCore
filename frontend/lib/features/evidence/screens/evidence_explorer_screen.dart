import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../models/evidence_model.dart';

class EvidenceExplorerScreen extends ConsumerStatefulWidget {
  const EvidenceExplorerScreen({super.key});

  @override
  ConsumerState<EvidenceExplorerScreen> createState() =>
      _EvidenceExplorerScreenState();
}

class _EvidenceExplorerScreenState
    extends ConsumerState<EvidenceExplorerScreen> {
  EvidenceApprovalStatus? _statusFilter;
  String _searchQuery = '';

  @override
  Widget build(BuildContext context) {
    final evidenceAsync = ref.watch(evidenceListProvider);

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Evidence & Provenance Explorer',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Approved source excerpts and recorded provenance',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
      body: evidenceAsync.when(
        data: (evidenceList) => _buildContent(context, evidenceList),
        loading: () =>
            const LoadingStateView(message: 'Loading evidence provenance...'),
        error: (err, _) => RepositoryErrorStateView(
          error: err,
          onRetry: () => ref.invalidate(evidenceListProvider),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, List<EvidenceModel> evidenceList) {
    final filtered = evidenceList.where((e) {
      if (_statusFilter != null && e.approvalStatus != _statusFilter) {
        return false;
      }
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final matchTitle = e.sourceTitle.toLowerCase().contains(query);
        final matchPath = (e.canonicalReference ?? e.filePath ?? '')
            .toLowerCase()
            .contains(query);
        final matchExcerpt = e.excerpt.toLowerCase().contains(query);
        final matchId = e.id.toLowerCase().contains(query);
        if (!matchTitle && !matchPath && !matchExcerpt && !matchId) {
          return false;
        }
      }
      return true;
    }).toList();

    return Column(
      children: [
        // Filter bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          color: AppTheme.surfaceDark,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                decoration: const InputDecoration(
                  hintText:
                      'Search by source ID, file path, or excerpt text...',
                  prefixIcon: Icon(
                    Icons.search,
                    size: 20,
                    color: AppTheme.textMuted,
                  ),
                  isDense: true,
                ),
                onChanged: (val) => setState(() => _searchQuery = val),
              ),
              const SizedBox(height: 12),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    const Text(
                      'APPROVAL STATUS:',
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _statusFilterChip('All', null),
                    _statusFilterChip(
                      'Source Review Approved',
                      EvidenceApprovalStatus.approved,
                      AppTheme.statusVerified,
                    ),
                    _statusFilterChip(
                      'Pending Review',
                      EvidenceApprovalStatus.pendingReview,
                      AppTheme.statusChallenged,
                    ),
                    _statusFilterChip(
                      'Rejected',
                      EvidenceApprovalStatus.rejected,
                      AppTheme.statusRejected,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1, color: AppTheme.cardBorder),

        // List
        Expanded(
          child: filtered.isEmpty
              ? EmptyStateView(
                  title: evidenceList.isEmpty
                      ? 'No Approved Evidence Available'
                      : 'No Matching Evidence Artifacts',
                  message: evidenceList.isEmpty
                      ? 'The backend returned no approved evidence chunks. Missing evidence does not show that a vulnerability is absent.'
                      : 'No evidence matched your filter criteria. Try resetting the status filter.',
                  icon: Icons.folder_off_outlined,
                  action: evidenceList.isEmpty
                      ? null
                      : ElevatedButton(
                          onPressed: () {
                            setState(() {
                              _statusFilter = null;
                              _searchQuery = '';
                            });
                          },
                          child: const Text('Reset Filters'),
                        ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(24),
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final ev = filtered[index];
                    return _buildEvidenceCard(context, ev);
                  },
                ),
        ),
      ],
    );
  }

  Widget _statusFilterChip(
    String label,
    EvidenceApprovalStatus? status, [
    Color? color,
  ]) {
    final isSelected = _statusFilter == status;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => setState(() => _statusFilter = status),
        selectedColor: (color ?? AppTheme.primaryTeal).withValues(alpha: 0.2),
        checkmarkColor: color ?? AppTheme.primaryTeal,
        labelStyle: TextStyle(
          color: isSelected
              ? (color ?? AppTheme.primaryTeal)
              : AppTheme.textSecondary,
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        ),
        side: BorderSide(
          color: isSelected
              ? (color ?? AppTheme.primaryTeal)
              : AppTheme.cardBorder,
        ),
      ),
    );
  }

  Widget _buildEvidenceCard(BuildContext context, EvidenceModel ev) {
    return Card(
      margin: const EdgeInsets.only(bottom: 20),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: ID, Source Title, Approval Status
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 12,
              runSpacing: 8,
              children: [
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    Text(
                      ev.id,
                      style: const TextStyle(
                        color: AppTheme.primaryTeal,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'monospace',
                      ),
                    ),
                    StatusBadge(
                      label: ev.approvalStatus.label,
                      color: ev.approvalStatus.color,
                    ),
                    if (ev.sourceType != null)
                      StatusBadge(
                        label: ev.sourceType!,
                        color: AppTheme.accentCyan,
                        isOutline: true,
                      ),
                  ],
                ),
                Text(
                  'Recorded version: ${ev.exactVersion ?? 'Not recorded'}',
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            Text(
              ev.sourceTitle,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),

            if (ev.characterStart != null && ev.characterEnd != null)
              Text(
                'Source characters ${ev.characterStart}–${ev.characterEnd}',
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontFamily: 'monospace',
                ),
              )
            else if (ev.canonicalReference != null || ev.filePath != null)
              Text(
                ev.canonicalReference ?? ev.filePath!,
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontFamily: 'monospace',
                ),
              ),
            const SizedBox(height: 14),

            if (ev.sourceRevision != null && ev.reviewEventCount != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  'Review revision ${ev.sourceRevision} • ${ev.reviewEventCount} recorded events${ev.approvedAt == null ? '' : ' • approved at ${ev.approvedAt}'}',
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 11,
                  ),
                ),
              ),

            const Text(
              'Source approval records review status; it does not establish that this excerpt supports a particular claim.',
              style: TextStyle(color: AppTheme.textMuted, fontSize: 11),
            ),
            const SizedBox(height: 14),

            // Raw Excerpt Container
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF070B12),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: SelectableText(
                ev.excerpt,
                style: const TextStyle(
                  color: Color(0xFFE2E8F0),
                  fontFamily: 'monospace',
                  fontSize: 12,
                  height: 1.45,
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Provenance Digest & Related Findings
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      const Icon(
                        Icons.fingerprint,
                        size: 14,
                        color: AppTheme.textMuted,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'Digest: ${ev.provenanceDigest}',
                          style: const TextStyle(
                            color: AppTheme.textMuted,
                            fontSize: 11,
                            fontFamily: 'monospace',
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(
                          Icons.copy,
                          size: 13,
                          color: AppTheme.textMuted,
                        ),
                        tooltip: 'Copy Digest',
                        onPressed: () {
                          Clipboard.setData(
                            ClipboardData(text: ev.provenanceDigest),
                          );
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text(
                                'Provenance digest copied to clipboard.',
                              ),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),
                Wrap(
                  spacing: 6,
                  children: ev.relatedFindingIds.map((fId) {
                    return InkWell(
                      onTap: () =>
                          context.go(RouteConstants.findingDetailsPath(fId)),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceVariant,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.cardBorder),
                        ),
                        child: Text(
                          'Finding: $fId',
                          style: const TextStyle(
                            color: AppTheme.primaryTeal,
                            fontSize: 11,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
