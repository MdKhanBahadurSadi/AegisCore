import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../theme/app_theme.dart';
import '../../services/aegiscore_configuration.dart';
import '../../services/providers.dart';

/// Top banner informing user that the view is rendered with synthetic demo fixtures.
class DemoModeBanner extends ConsumerWidget {
  const DemoModeBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(repositoryModeProvider);
    if (mode == AegisCoreMode.live) {
      final health = ref.watch(backendHealthProvider);
      final (label, color) = health.when(
        data: (available) => available
            ? (
                'LIVE BACKEND MODE: Connected. Screens show only data returned by the configured API.',
                AppTheme.statusVerified,
              )
            : (
                'BACKEND UNAVAILABLE: Live mode is active; no synthetic data is substituted.',
                AppTheme.statusRejected,
              ),
        loading: () => (
          'LIVE BACKEND MODE: Checking the configured API. No synthetic data is substituted.',
          AppTheme.accentCyan,
        ),
        error: (_, _) => (
          'BACKEND UNAVAILABLE: Live mode is active; no synthetic data is substituted.',
          AppTheme.statusRejected,
        ),
      );
      return _ModeBanner(label: label, color: color);
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.severityMedium.withValues(alpha: 0.12),
        border: const Border(
          bottom: BorderSide(color: Color(0x40F59E0B), width: 1),
        ),
      ),
      child: const Row(
        children: [
          Icon(
            Icons.science_outlined,
            size: 16,
            color: AppTheme.severityMedium,
          ),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'DEMO FIXTURE MODE: Showing verified offline synthetic data. '
              'Live container scans require supervisor-adjudicated lab authorization.',
              style: TextStyle(
                color: Color(0xFFFDE68A),
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ModeBanner extends StatelessWidget {
  final String label;
  final Color color;

  const _ModeBanner({required this.label, required this.color});

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.1),
      border: Border(bottom: BorderSide(color: color.withValues(alpha: 0.4))),
    ),
    child: Row(
      children: [
        Icon(Icons.cloud_outlined, size: 16, color: color),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    ),
  );
}
