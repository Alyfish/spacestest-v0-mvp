import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/theme.dart';

void main() {
  testWidgets('App theme smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: const Scaffold(
          body: Center(child: Text('Spaces')),
        ),
      ),
    );

    expect(find.text('Spaces'), findsOneWidget);
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(
      app.theme?.scaffoldBackgroundColor,
      AppTheme.lightTheme.scaffoldBackgroundColor,
    );
  });
}
