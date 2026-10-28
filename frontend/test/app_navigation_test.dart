import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aegiscore_ui/main.dart';
import 'package:aegiscore_ui/core/widgets/demo_mode_banner.dart';

void main() {
  testWidgets(
    'App initializes on Dashboard and renders responsive shell with demo banner',
    (WidgetTester tester) async {
      // Set a desktop surface size
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));

      // Allow demo data providers to settle
      await tester.pumpAndSettle();

      // Verify DemoModeBanner is present
      expect(find.byType(DemoModeBanner), findsOneWidget);
      expect(find.textContaining('DEMO FIXTURE MODE'), findsOneWidget);

      // Verify Dashboard AppBar title
      expect(find.text('Security Assessment Dashboard'), findsOneWidget);

      // Verify nav rail items are present in desktop mode
      expect(find.text('Dashboard'), findsAtLeast(1));
      expect(find.text('Assessment Setup'), findsOneWidget);
      expect(find.text('Findings'), findsOneWidget);
      expect(find.text('Evidence Explorer'), findsOneWidget);
      expect(find.text('Reports & Metrics'), findsOneWidget);
      expect(find.text('Settings & Status'), findsOneWidget);
    },
  );

  testWidgets('Dashboard loads stat cards and recent findings section', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));
    await tester.pumpAndSettle();

    // Verify dashboard screen heading and key sections
    expect(find.text('Security Assessment Dashboard'), findsOneWidget);
    // Verify assessment overview section titles via scroll
    expect(find.text('Recent Assessment Findings'), findsOneWidget);
    expect(find.text('Target Vulnerability Catalog'), findsOneWidget);
  });

  testWidgets('Navigation rail taps lead to correct screen titles', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));
    await tester.pumpAndSettle();

    // Navigate to Findings
    await tester.tap(find.text('Findings'));
    await tester.pumpAndSettle();
    expect(find.text('Security Assessment Findings'), findsOneWidget);

    // Navigate to Assessment Setup
    await tester.tap(find.text('Assessment Setup'));
    await tester.pumpAndSettle();
    expect(find.text('Assessment Configuration'), findsOneWidget);

    // Navigate to Evidence Explorer
    await tester.tap(find.text('Evidence Explorer'));
    await tester.pumpAndSettle();
    expect(find.text('Evidence & Provenance Explorer'), findsOneWidget);

    // Navigate to Reports
    await tester.tap(find.text('Reports & Metrics'));
    await tester.pumpAndSettle();
    expect(find.text('Evaluation Metrics & Benchmark Reports'), findsOneWidget);

    // Navigate to Settings
    await tester.tap(find.text('Settings & Status'));
    await tester.pumpAndSettle();
    expect(find.text('System Settings & Integration Status'), findsOneWidget);
  });
}
