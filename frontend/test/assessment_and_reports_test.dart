import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aegiscore_ui/main.dart';

void main() {
  testWidgets(
    'Assessment setup shows safety notice and requires confirmation',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));
      await tester.pumpAndSettle();

      // Navigate to Assessment Setup
      await tester.tap(find.text('Assessment Setup'));
      await tester.pumpAndSettle();

      // Verify title and safety notice
      expect(find.text('Assessment Configuration'), findsOneWidget);
      expect(
        find.textContaining('STRICT AUTHORIZED LAB SCOPE'),
        findsOneWidget,
      );

      // Authorized lab targets should be listed
      expect(find.textContaining('OWASP Juice Shop'), findsAtLeast(1));
      expect(find.textContaining('Damn Vulnerable Web App'), findsAtLeast(1));

      // Scroll down to see confirmation area
      await tester.dragUntilVisible(
        find.textContaining('I confirm this assessment targets'),
        find.byType(SingleChildScrollView).first,
        const Offset(0, -150),
      );
      await tester.pumpAndSettle();

      // Verify confirmation text is present
      expect(
        find.textContaining('I confirm this assessment targets'),
        findsAtLeast(1),
      );
    },
  );

  testWidgets('Reports screen displays metrics and limitation banner', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));
    await tester.pumpAndSettle();

    // Navigate to Reports
    await tester.tap(find.text('Reports & Metrics'));
    await tester.pumpAndSettle();

    // Verify report screen title
    expect(find.text('Evaluation Metrics & Benchmark Reports'), findsOneWidget);

    // Verify synthetic run label is present
    expect(find.textContaining('SYNTHETIC DEMO HARNESS RUN'), findsOneWidget);

    // Verify limitations/integrity banner
    expect(
      find.text('EVALUATION INTEGRITY INVARIANTS & LIMITATIONS'),
      findsOneWidget,
    );

    // Verify category breakdown table exists
    expect(find.text('Per-Vulnerability-Category Breakdown'), findsOneWidget);
  });

  testWidgets('Settings screen shows backend connection section', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const ProviderScope(child: AegisCoreApp()));
    await tester.pumpAndSettle();

    // Navigate to Settings
    await tester.tap(find.text('Settings & Status'));
    await tester.pumpAndSettle();

    expect(find.text('Backend Service Connection'), findsOneWidget);
    expect(find.text('Test Connection'), findsOneWidget);

    // Verify capabilities inventory section
    expect(
      find.text('Backend Capabilities & Safety Contracts Inventory'),
      findsOneWidget,
    );

    // Verify the provider safety policy card
    expect(find.text('Provider & Safety Policy Status'), findsOneWidget);
    expect(find.textContaining('UNAPPROVED / DISABLED'), findsAtLeast(1));
  });
}
