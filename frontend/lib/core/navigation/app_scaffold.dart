import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme/app_theme.dart';
import '../widgets/demo_mode_banner.dart';
import '../widgets/status_badge.dart';
import '../constants/route_constants.dart';

/// Top-level responsive application shell for AEGISCORE AI.
/// Provides desktop navigation rail, tablet rail, and mobile bottom bar.
class AppScaffold extends StatelessWidget {
  final Widget child;

  const AppScaffold({super.key, required this.child});

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    if (location == RouteConstants.dashboard) return 0;
    if (location.startsWith(RouteConstants.assessmentSetup)) return 1;
    if (location.startsWith(RouteConstants.findings)) return 2;
    if (location.startsWith(RouteConstants.evidence)) return 3;
    if (location.startsWith(RouteConstants.reports)) return 4;
    if (location.startsWith(RouteConstants.settings)) return 5;
    return 0;
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0:
        context.go(RouteConstants.dashboard);
        break;
      case 1:
        context.go(RouteConstants.assessmentSetup);
        break;
      case 2:
        context.go(RouteConstants.findings);
        break;
      case 3:
        context.go(RouteConstants.evidence);
        break;
      case 4:
        context.go(RouteConstants.reports);
        break;
      case 5:
        context.go(RouteConstants.settings);
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedIndex = _calculateSelectedIndex(context);
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 1024;
    final isTablet = width >= 640 && width < 1024;

    return Scaffold(
      body: Column(
        children: [
          const DemoModeBanner(),
          Expanded(
            child: Row(
              children: [
                if (isDesktop || isTablet)
                  _buildNavigationRail(context, selectedIndex, isDesktop),
                Expanded(
                  child: Container(
                    color: AppTheme.scaffoldBackground,
                    child: child,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: (!isDesktop && !isTablet)
          ? NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: (idx) => _onItemTapped(idx, context),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.dashboard_outlined),
                  selectedIcon: Icon(Icons.dashboard),
                  label: 'Dashboard',
                ),
                NavigationDestination(
                  icon: Icon(Icons.tune_outlined),
                  selectedIcon: Icon(Icons.tune),
                  label: 'Setup',
                ),
                NavigationDestination(
                  icon: Icon(Icons.bug_report_outlined),
                  selectedIcon: Icon(Icons.bug_report),
                  label: 'Findings',
                ),
                NavigationDestination(
                  icon: Icon(Icons.folder_open_outlined),
                  selectedIcon: Icon(Icons.folder_open),
                  label: 'Evidence',
                ),
                NavigationDestination(
                  icon: Icon(Icons.analytics_outlined),
                  selectedIcon: Icon(Icons.analytics),
                  label: 'Reports',
                ),
                NavigationDestination(
                  icon: Icon(Icons.settings_outlined),
                  selectedIcon: Icon(Icons.settings),
                  label: 'Settings',
                ),
              ],
            )
          : null,
    );
  }

  Widget _buildNavigationRail(
    BuildContext context,
    int selectedIndex,
    bool isDesktop,
  ) {
    return Container(
      width: isDesktop ? 240 : 72,
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDark,
        border: Border(right: BorderSide(color: AppTheme.cardBorder, width: 1)),
      ),
      child: Column(
        children: [
          // Header / Logo
          Container(
            padding: EdgeInsets.symmetric(
              horizontal: isDesktop ? 20 : 12,
              vertical: 24,
            ),
            child: Row(
              mainAxisAlignment: isDesktop
                  ? MainAxisAlignment.start
                  : MainAxisAlignment.center,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryTeal.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppTheme.primaryTeal.withValues(alpha: 0.6),
                    ),
                  ),
                  child: const Icon(
                    Icons.shield_outlined,
                    color: AppTheme.primaryTeal,
                    size: 18,
                  ),
                ),
                if (isDesktop) ...[
                  const SizedBox(width: 12),
                  const Flexible(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'AEGISCORE AI',
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          'EVAL PLATFORM',
                          style: TextStyle(
                            color: AppTheme.primaryTeal,
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1.2,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const Divider(height: 1, color: AppTheme.cardBorder),
          const SizedBox(height: 12),

          // Nav Items
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              children: [
                _navItem(
                  context: context,
                  index: 0,
                  icon: Icons.dashboard_outlined,
                  selectedIcon: Icons.dashboard,
                  title: 'Dashboard',
                  isSelected: selectedIndex == 0,
                  isDesktop: isDesktop,
                ),
                _navItem(
                  context: context,
                  index: 1,
                  icon: Icons.tune_outlined,
                  selectedIcon: Icons.tune,
                  title: 'Assessment Setup',
                  isSelected: selectedIndex == 1,
                  isDesktop: isDesktop,
                ),
                _navItem(
                  context: context,
                  index: 2,
                  icon: Icons.bug_report_outlined,
                  selectedIcon: Icons.bug_report,
                  title: 'Findings',
                  isSelected: selectedIndex == 2,
                  isDesktop: isDesktop,
                ),
                _navItem(
                  context: context,
                  index: 3,
                  icon: Icons.folder_open_outlined,
                  selectedIcon: Icons.folder_open,
                  title: 'Evidence Explorer',
                  isSelected: selectedIndex == 3,
                  isDesktop: isDesktop,
                ),
                _navItem(
                  context: context,
                  index: 4,
                  icon: Icons.analytics_outlined,
                  selectedIcon: Icons.analytics,
                  title: 'Reports & Metrics',
                  isSelected: selectedIndex == 4,
                  isDesktop: isDesktop,
                ),
                _navItem(
                  context: context,
                  index: 5,
                  icon: Icons.settings_outlined,
                  selectedIcon: Icons.settings,
                  title: 'Settings & Status',
                  isSelected: selectedIndex == 5,
                  isDesktop: isDesktop,
                ),
              ],
            ),
          ),

          // Footer / Calibration & Scope Indicator
          if (isDesktop)
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: StatusBadge(
                      label: 'UNCALIBRATED',
                      color: AppTheme.statusAbstained,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'confidence_is_calibrated=false\nLab scope restricted to container targets.',
                    style: TextStyle(
                      color: AppTheme.textMuted,
                      fontSize: 10,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _navItem({
    required BuildContext context,
    required int index,
    required IconData icon,
    required IconData selectedIcon,
    required String title,
    required bool isSelected,
    required bool isDesktop,
  }) {
    final activeColor = isSelected
        ? AppTheme.primaryTeal
        : AppTheme.textSecondary;
    final bgColor = isSelected
        ? AppTheme.primaryTeal.withValues(alpha: 0.12)
        : Colors.transparent;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Tooltip(
        message: isDesktop ? '' : title,
        waitDuration: const Duration(milliseconds: 400),
        child: InkWell(
          onTap: () => _onItemTapped(index, context),
          borderRadius: BorderRadius.circular(6),
          child: Container(
            padding: EdgeInsets.symmetric(
              horizontal: isDesktop ? 14 : 10,
              vertical: 11,
            ),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(6),
              border: isSelected
                  ? Border.all(
                      color: AppTheme.primaryTeal.withValues(alpha: 0.4),
                      width: 1,
                    )
                  : null,
            ),
            child: Row(
              mainAxisAlignment: isDesktop
                  ? MainAxisAlignment.start
                  : MainAxisAlignment.center,
              children: [
                Icon(
                  isSelected ? selectedIcon : icon,
                  size: 20,
                  color: activeColor,
                ),
                if (isDesktop) ...[
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        color: isSelected
                            ? AppTheme.textPrimary
                            : AppTheme.textSecondary,
                        fontSize: 13,
                        fontWeight: isSelected
                            ? FontWeight.w600
                            : FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
