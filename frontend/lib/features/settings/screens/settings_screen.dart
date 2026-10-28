import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/state_views.dart';
import '../../../services/providers.dart';
import '../../../services/aegiscore_configuration.dart';
import '../../../services/backend_errors.dart';
import '../../../services/authentication.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _isTestingHealth = false;
  String? _healthResult;

  Future<void> _testBackendConnection() async {
    setState(() {
      _isTestingHealth = true;
      _healthResult = null;
    });

    try {
      final repo = ref.read(aegisCoreRepositoryProvider);
      if (repo.mode == AegisCoreMode.demo) {
        setState(() {
          _isTestingHealth = false;
          _healthResult =
              'Demo fixture mode is active; no backend health request was made.';
        });
        return;
      }
      final isUp = await repo.checkBackendHealth();
      if (!mounted) return;
      setState(() {
        _isTestingHealth = false;
        _healthResult = isUp
            ? 'Backend process responded at ${repo.displayEndpoint} (status: ok).'
            : 'Backend unavailable at the configured endpoint.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isTestingHealth = false;
        _healthResult = userFacingBackendError(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final capabilitiesAsync = ref.watch(backendCapabilitiesProvider);
    final repo = ref.watch(aegisCoreRepositoryProvider);
    final configuration = ref.watch(aegisCoreConfigurationProvider);
    final authentication = ref.watch(authenticationProvider);
    final isDemo = repo.mode == AegisCoreMode.demo;
    final permissions = authentication.permissions.toList()..sort();

    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'System Settings & Integration Status',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
            Text(
              'Backend Foundation, Safety Policy Boundaries & Provider Inventory',
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
                if (!isDemo) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Local Backend Session',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'Signed in as ${authentication.username ?? 'local user'}',
                            style: const TextStyle(color: AppTheme.textSecondary),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Permissions: ${permissions.join(', ')}',
                            style: const TextStyle(color: AppTheme.textMuted),
                          ),
                          const SizedBox(height: 10),
                          const Text(
                            'Identity grants read access only. It does not authorize a security assessment or target scan.',
                            style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: () => ref
                                .read(authenticationProvider.notifier)
                                .signOut(),
                            icon: const Icon(Icons.logout),
                            label: const Text('Sign out'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
                // Backend Connection Status Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          alignment: WrapAlignment.spaceBetween,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.dns_outlined,
                                  size: 20,
                                  color: AppTheme.primaryTeal,
                                ),
                                SizedBox(width: 10),
                                Text(
                                  'Backend Service Connection',
                                  style: TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            ElevatedButton.icon(
                              onPressed: _isTestingHealth
                                  ? null
                                  : _testBackendConnection,
                              icon: _isTestingHealth
                                  ? const SizedBox(
                                      width: 14,
                                      height: 14,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.sync, size: 16),
                              label: const Text('Test Connection'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        const Divider(height: 1, color: AppTheme.cardBorder),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            const SizedBox(
                              width: 140,
                              child: Text(
                                'Service Endpoint:',
                                style: TextStyle(
                                  color: AppTheme.textMuted,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            Expanded(
                              child: SelectableText(
                                isDemo
                                    ? configuration.displayEndpoint
                                    : repo.displayEndpoint,
                                style: TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontSize: 13,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const SizedBox(
                              width: 140,
                              child: Text(
                                'Current Mode:',
                                style: TextStyle(
                                  color: AppTheme.textMuted,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            StatusBadge(
                              label: isDemo
                                  ? 'DEMO FIXTURE MODE'
                                  : 'LIVE BACKEND MODE',
                              color: isDemo
                                  ? AppTheme.statusAbstained
                                  : AppTheme.accentCyan,
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          isDemo
                              ? 'Synthetic fixtures only. The endpoint is not contacted in demo mode.'
                              : 'The configured API is queried directly. Failed or missing contracts never fall back to fixtures.',
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                        if (_healthResult != null) ...[
                          const SizedBox(height: 14),
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceVariant,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: AppTheme.cardBorder),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.info_outline,
                                  size: 16,
                                  color: AppTheme.accentCyan,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    _healthResult!,
                                    style: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontSize: 12,
                                    ),
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
                const SizedBox(height: 20),

                if (!isDemo) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Local Persistence Availability',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 12),
                          ref
                              .watch(backendStorageStatusProvider)
                              .when(
                                data: (status) => Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        const Text(
                                          'Store status:',
                                          style: TextStyle(
                                            color: AppTheme.textSecondary,
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        StatusBadge(
                                          label: status.status.toUpperCase(),
                                          color: status.status == 'available'
                                              ? AppTheme.statusVerified
                                              : AppTheme.statusAbstained,
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      status.reason == 'ready'
                                          ? 'Persisted offline replay sessions and synthetic evaluation reports are available.'
                                          : status.reason == 'not_configured'
                                          ? 'No local persistence path is configured on the backend.'
                                          : 'The configured local store cannot currently be read.',
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 12,
                                      ),
                                    ),
                                    if (status
                                        .supportedRecordTypes
                                        .isNotEmpty) ...[
                                      const SizedBox(height: 6),
                                      Text(
                                        'Supported records: ${status.supportedRecordTypes.join(', ')}',
                                        style: const TextStyle(
                                          color: AppTheme.textMuted,
                                          fontSize: 11,
                                          fontFamily: 'monospace',
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                                loading: () => const LoadingStateView(
                                  message: 'Checking local storage...',
                                ),
                                error: (error, _) => RepositoryErrorStateView(
                                  error: error,
                                  onRetry: () => ref.invalidate(
                                    backendStorageStatusProvider,
                                  ),
                                ),
                              ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],

                // Backend Capabilities Inventory Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(
                              Icons.checklist,
                              size: 20,
                              color: AppTheme.accentCyan,
                            ),
                            SizedBox(width: 10),
                            Text(
                              'Backend Capabilities & Safety Contracts Inventory',
                              style: TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Directly maps to aegiscore/api/schemas.py CapabilitiesResponse.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 14),
                        const Divider(height: 1, color: AppTheme.cardBorder),
                        const SizedBox(height: 14),
                        capabilitiesAsync.when(
                          data: (cap) {
                            final implemented = cap.implemented;
                            final notImplemented = cap.notImplemented;

                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Implemented Backend Capabilities:',
                                  style: TextStyle(
                                    color: AppTheme.statusVerified,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                ...implemented.map(
                                  (item) => Padding(
                                    padding: const EdgeInsets.symmetric(
                                      vertical: 3,
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(
                                          Icons.check_circle,
                                          size: 14,
                                          color: AppTheme.statusVerified,
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          item,
                                          style: const TextStyle(
                                            color: AppTheme.textPrimary,
                                            fontSize: 12,
                                            fontFamily: 'monospace',
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 16),
                                const Text(
                                  'Restricted / Unimplemented Capabilities (Honest Disclosure):',
                                  style: TextStyle(
                                    color: AppTheme.severityHigh,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                ...notImplemented.map(
                                  (item) => Padding(
                                    padding: const EdgeInsets.symmetric(
                                      vertical: 3,
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(
                                          Icons.block,
                                          size: 14,
                                          color: AppTheme.severityHigh,
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          item,
                                          style: const TextStyle(
                                            color: AppTheme.textSecondary,
                                            fontSize: 12,
                                            fontFamily: 'monospace',
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            );
                          },
                          loading: () => const LoadingStateView(
                            message: 'Loading inventory...',
                          ),
                          error: (e, _) => RepositoryErrorStateView(
                            error: e,
                            onRetry: () =>
                                ref.invalidate(backendCapabilitiesProvider),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // External Provider Safety Policy Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(
                              Icons.shield,
                              size: 20,
                              color: AppTheme.severityHigh,
                            ),
                            SizedBox(width: 10),
                            Text(
                              'Provider & Safety Policy Status',
                              style: TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        const Divider(height: 1, color: AppTheme.cardBorder),
                        const SizedBox(height: 14),
                        _providerStatusRow(
                          'Cloud LLM Providers (OpenAI, Anthropic, Gemini):',
                          'UNAPPROVED / DISABLED',
                          AppTheme.statusRejected,
                          'Strict boundary: No outbound API calls or live model inference permitted.',
                        ),
                        const SizedBox(height: 12),
                        _providerStatusRow(
                          'Target HTTP Transport:',
                          'NOT IMPLEMENTED',
                          AppTheme.statusAbstained,
                          'No live target transport or assessment-execution API is configured; submission remains disabled.',
                        ),
                        const SizedBox(height: 12),
                        _providerStatusRow(
                          'Confidence Calibration:',
                          'UNCALIBRATED (Raw Intervals)',
                          AppTheme.statusAbstained,
                          'confidence_is_calibrated=false preserved across all UI views and models.',
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Application Info Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'About AEGISCORE AI',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'AEGISCORE AI is an uncertainty-aware web application security assessment '
                          'and evidence review research platform. Phase 8G.2 establishes the Flutter UI/UX '
                          'foundation with responsive navigation, multi-specialist consensus displays, '
                          'claim verification inspector, and reproducible offline benchmark reporting.',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            StatusBadge(
                              label: AppConstants.appVersion,
                              color: AppTheme.primaryTeal,
                            ),
                            const SizedBox(width: 10),
                            const StatusBadge(
                              label: 'Flutter 3.32 / Dart 3.8 / Material 3',
                              color: AppTheme.accentCyan,
                              isOutline: true,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _providerStatusRow(
    String title,
    String statusLabel,
    Color statusColor,
    String subtitle,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 8),
            StatusBadge(label: statusLabel, color: statusColor),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
        ),
      ],
    );
  }
}
