import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/route_constants.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../models/finding_model.dart';

class FindingsScreen extends ConsumerStatefulWidget {
  const FindingsScreen({super.key});

  @override
  ConsumerState<FindingsScreen> createState() => _FindingsScreenState();
}

class _FindingsScreenState extends ConsumerState<FindingsScreen> {
  ReviewStatus? _selectedStatusFilter;
  String _selectedCategory = 'ALL';
  String _searchQuery = '';

  @override
  Widget build(BuildContext context) {
    final findingsAsync = ref.watch(findingsProvider);

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Security Assessment Findings',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Grounded Claims, Adversarial Reviews & Confidence Intervals',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
      body: findingsAsync.when(
        data: (findings) => _buildContent(context, findings),
        loading: () =>
            const LoadingStateView(message: 'Loading findings catalog...'),
        error: (err, _) => RepositoryErrorStateView(
          error: err,
          onRetry: () => ref.invalidate(findingsProvider),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, List<FindingModel> allFindings) {
    // Filter
    final filtered = allFindings.where((f) {
      if (_selectedStatusFilter != null &&
          f.reviewStatus != _selectedStatusFilter) {
        return false;
      }
      if (_selectedCategory != 'ALL' &&
          f.vulnerabilityClass.toLowerCase() !=
              _selectedCategory.toLowerCase()) {
        return false;
      }
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final matchTitle = f.title.toLowerCase().contains(query);
        final matchPath = f.locus.path.toLowerCase().contains(query);
        final matchParam = f.locus.parameter.toLowerCase().contains(query);
        final matchRole = f.specialistRole.toLowerCase().contains(query);
        if (!matchTitle && !matchPath && !matchParam && !matchRole) {
          return false;
        }
      }
      return true;
    }).toList();

    return Column(
      children: [
        // Filter & Search Header
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          color: AppTheme.surfaceDark,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Search Bar
              TextField(
                decoration: const InputDecoration(
                  hintText:
                      'Search by title, path, parameter, or specialist...',
                  prefixIcon: Icon(
                    Icons.search,
                    size: 20,
                    color: AppTheme.textMuted,
                  ),
                  isDense: true,
                ),
                onChanged: (val) => setState(() => _searchQuery = val),
              ),
              const SizedBox(height: 14),

              // Filter Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    const Text(
                      'STATUS:',
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _statusFilterChip(label: 'All', status: null),
                    _statusFilterChip(
                      label: 'Verified',
                      status: ReviewStatus.verified,
                      color: AppTheme.statusVerified,
                    ),
                    _statusFilterChip(
                      label: 'Recorded replay',
                      status: ReviewStatus.recorded,
                      color: AppTheme.accentCyan,
                    ),
                    _statusFilterChip(
                      label: 'Challenged',
                      status: ReviewStatus.challenged,
                      color: AppTheme.statusChallenged,
                    ),
                    _statusFilterChip(
                      label: 'Rejected',
                      status: ReviewStatus.rejected,
                      color: AppTheme.statusRejected,
                    ),
                    _statusFilterChip(
                      label: 'Abstained',
                      status: ReviewStatus.abstained,
                      color: AppTheme.statusAbstained,
                    ),
                    const SizedBox(width: 20),
                    const Text(
                      'CATEGORY:',
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _categoryChip('ALL', 'All'),
                    _categoryChip('sql_injection', 'SQLi'),
                    _categoryChip('cross_site_scripting', 'XSS'),
                    _categoryChip(
                      'insecure_deserialization',
                      'Deserialization',
                    ),
                    _categoryChip('path_traversal', 'Path Traversal'),
                  ],
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1, color: AppTheme.cardBorder),

        // Results List
        Expanded(
          child: filtered.isEmpty
              ? EmptyStateView(
                  title: 'No Matching Findings',
                  message:
                      'No findings matched the current filter or search criteria. Try clearing your filters.',
                  icon: Icons.filter_alt_off,
                  action: ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _selectedStatusFilter = null;
                        _selectedCategory = 'ALL';
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
                    final finding = filtered[index];
                    return _buildFindingCard(context, finding);
                  },
                ),
        ),
      ],
    );
  }

  Widget _statusFilterChip({
    required String label,
    required ReviewStatus? status,
    Color? color,
  }) {
    final isSelected = _selectedStatusFilter == status;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => setState(() => _selectedStatusFilter = status),
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

  Widget _categoryChip(String categoryId, String label) {
    final isSelected = _selectedCategory == categoryId;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: ChoiceChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (selected) {
          if (selected) {
            setState(() => _selectedCategory = categoryId);
          }
        },
        selectedColor: AppTheme.accentCyan.withValues(alpha: 0.2),
        labelStyle: TextStyle(
          color: isSelected ? AppTheme.accentCyan : AppTheme.textSecondary,
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        ),
        side: BorderSide(
          color: isSelected ? AppTheme.accentCyan : AppTheme.cardBorder,
        ),
      ),
    );
  }

  Widget _buildFindingCard(BuildContext context, FindingModel finding) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: InkWell(
        onTap: () => context.go(RouteConstants.findingDetailsPath(finding.id)),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Row: ID, Badges, Severity
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(
                        finding.id,
                        style: const TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(width: 10),
                      StatusBadge(
                        label: finding.severity.label,
                        color: finding.severity.color,
                      ),
                      const SizedBox(width: 8),
                      StatusBadge(
                        label: finding.reviewStatus.label,
                        color: finding.reviewStatus.color,
                      ),
                    ],
                  ),
                  if (finding.confidenceScore != null)
                    Row(
                      children: [
                        const Icon(
                          Icons.bolt,
                          size: 14,
                          color: AppTheme.primaryTeal,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'Score: ${(finding.confidenceScore! * 100).toInt()}%',
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Title
              Text(
                finding.title,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),

              // Locus Coordinate
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceVariant,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppTheme.cardBorder),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.code,
                      size: 14,
                      color: AppTheme.accentCyan,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'LOCUS: ${finding.locus.formattedCoordinate}',
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                          fontFamily: 'monospace',
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              // Bottom Details Row: Specialist, Citations, Confidence Interval
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Flexible(
                    child: Row(
                      children: [
                        const Icon(
                          Icons.person_outline,
                          size: 14,
                          color: AppTheme.textMuted,
                        ),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            finding.specialistRole,
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Icon(
                          Icons.link,
                          size: 14,
                          color: AppTheme.textMuted,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${finding.evidenceIds.length} Evidence Artifacts',
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (finding.confidenceInterval != null)
                    Text(
                      'CI: ${finding.confidenceInterval!.formatted}',
                      style: const TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 11,
                        fontFamily: 'monospace',
                      ),
                    ),
                ],
              ),

              if (finding.dataProvenanceLabel != null) ...[
                const SizedBox(height: 8),
                Text(
                  finding.dataProvenanceLabel!,
                  style: const TextStyle(
                    color: AppTheme.statusAbstained,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.3,
                  ),
                ),
              ],

              if (finding.challengeReason != null) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.severityHigh.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: AppTheme.severityHigh.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.warning_amber_rounded,
                        size: 16,
                        color: AppTheme.severityHigh,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          finding.challengeReason!,
                          style: const TextStyle(
                            color: Color(0xFFFDE68A),
                            fontSize: 11,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
