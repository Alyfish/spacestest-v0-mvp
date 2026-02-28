import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/screens/analyzing_screen.dart';

void main() {
  testWidgets('AnalyzingScreen starts asyncWork after first frame', (
    WidgetTester tester,
  ) async {
    final phases = <SchedulerPhase>[];

    Future<void> asyncWork() async {
      phases.add(SchedulerBinding.instance.schedulerPhase);
    }

    await tester.pumpWidget(
      MaterialApp(
        home: AnalyzingScreen(asyncWork: asyncWork, onComplete: () {}),
      ),
    );

    await tester.pump();
    if (phases.isEmpty) {
      await tester.pump(const Duration(milliseconds: 1));
    }

    expect(phases, isNotEmpty);
    expect(phases.first, isNot(SchedulerPhase.persistentCallbacks));
    expect(phases.first, isNot(SchedulerPhase.midFrameMicrotasks));

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    await tester.pump(const Duration(seconds: 3));
  });

  testWidgets('AnalyzingScreen retry action runs asyncWork again', (
    WidgetTester tester,
  ) async {
    var calls = 0;

    Future<void> asyncWork() async {
      calls++;
      await Future<void>.delayed(const Duration(milliseconds: 10));
      throw Exception('test failure');
    }

    await tester.pumpWidget(
      MaterialApp(
        home: AnalyzingScreen(asyncWork: asyncWork, onComplete: () {}),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 2600));
    await tester.pump(const Duration(milliseconds: 20));

    expect(find.text('Retry'), findsOneWidget);
    expect(calls, 1);

    final retryAction = tester.widget<SnackBarAction>(
      find.byType(SnackBarAction),
    );
    retryAction.onPressed();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 2600));
    await tester.pump(const Duration(milliseconds: 20));

    expect(calls, 2);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    await tester.pump(const Duration(seconds: 3));
  });
}
