import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aegiscore_ui/main.dart';

void main() {
  testWidgets('Findings screen renders list and filters by status', (
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

    // Verify findings screen title
    expect(find.text('Security Assessment Findings'), findsOneWidget);

    // Verify APPROVAL STATUS filter bar present
    expect(find.text('STATUS:'), findsOneWidget);
    expect(find.text('CATEGORY:'), findsOneWidget);

    // Verify individual finding IDs appear in the list (lazy-render: scrollable)
    expect(find.text('FIND-JS-01'), findsOneWidget);
    expect(find.text('FIND-DVWA-01'), findsOneWidget);
    expect(find.text('FIND-JS-CHALLENGE-02'), findsOneWidget);

    // Test Status Filter: tap 'Rejected' chip
    final rejectedChip = find.widgetWithText(FilterChip, 'Rejected');
    expect(rejectedChip, findsOneWidget);
    await tester.tap(rejectedChip);
    await tester.pumpAndSettle();

    // Only rejected findings should appear
    expect(find.text('FIND-JS-CHALLENGE-02'), findsOneWidget);
    expect(find.text('FIND-JS-01'), findsNothing);
    expect(find.text('FIND-DVWA-01'), findsNothing);
  });

  testWidgets('Finding detail screen shows locus coordinates and claims', (
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

    // Tap on the first SQLi finding card
    await tester.tap(find.text('FIND-JS-01'));
    await tester.pumpAndSettle();

    // Verify Finding Details view loads
    expect(find.text('Finding Details: FIND-JS-01'), findsOneWidget);

    // Verify locus section exists
    expect(find.text('Canonical Locus Coordinates'), findsOneWidget);

    // Verify claims section
    expect(find.text('Decomposed Claims & Grounding Verdicts'), findsOneWidget);

    // Verify back navigation returns to Findings
    await tester.tap(find.byTooltip('Back to Findings'));
    await tester.pumpAndSettle();

    expect(find.text('Security Assessment Findings'), findsOneWidget);
  });
}
