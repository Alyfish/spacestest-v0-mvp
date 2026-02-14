import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:spaces/constants/api_constants.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/providers/user_provider.dart';

class E2EHarness {
  E2EHarness({required this.runId, required this.secret, required this.userId});

  final String runId;
  final String secret;
  final String userId;

  static E2EHarness fromDefines() {
    return E2EHarness(
      runId: ApiConstants.e2eRunId.trim(),
      secret: ApiConstants.e2eTestSecret.trim(),
      userId: ApiConstants.e2eTestUserId.trim(),
    );
  }

  String get apiBaseUrl => ApiConstants.baseUrl;

  String get seededAuthToken => 'e2e-token-$runId';

  void ensureConfigured() {
    if (runId.isEmpty || secret.isEmpty || userId.isEmpty) {
      throw StateError(
        'E2E headers are not configured. Provide '
        '--dart-define=E2E_RUN_ID, --dart-define=E2E_TEST_SECRET, '
        'and --dart-define=E2E_TEST_USER_ID.',
      );
    }
  }

  Map<String, String> _controlHeaders() => {
    'Accept': 'application/json',
    'X-E2E-Test-Secret': secret,
    'X-E2E-Run-ID': runId,
    'X-E2E-User-Id': userId,
  };

  Future<void> verifyBackendStatus() async {
    final uri = Uri.parse('$apiBaseUrl/e2e/status');
    final response = await http
        .get(uri, headers: _controlHeaders())
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw StateError(
        'E2E backend status check failed: ${response.statusCode} ${response.body}',
      );
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (body['status'] != 'ok' || body['enabled'] != true) {
      throw StateError('E2E backend is not enabled: ${response.body}');
    }
  }

  Future<void> clearTraces() async {
    final uri = Uri.parse('$apiBaseUrl/e2e/traces/$runId');
    final response = await http
        .delete(uri, headers: _controlHeaders())
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw StateError(
        'Failed to clear traces for run $runId: ${response.statusCode} ${response.body}',
      );
    }
  }

  Future<List<Map<String, dynamic>>> fetchTraces() async {
    final uri = Uri.parse('$apiBaseUrl/e2e/traces/$runId');
    final response = await http
        .get(uri, headers: _controlHeaders())
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw StateError(
        'Failed to fetch traces for run $runId: ${response.statusCode} ${response.body}',
      );
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final rawTraces = body['traces'] as List<dynamic>? ?? const [];
    return rawTraces
        .whereType<Map>()
        .map((trace) => Map<String, dynamic>.from(trace))
        .toList();
  }

  Future<BuildContext> pumpProviderHarness(WidgetTester tester) async {
    final contextCompleter = Completer<BuildContext>();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<UserProvider>(create: (_) => UserProvider()),
          ChangeNotifierProvider<ProjectProvider>(
            create: (_) => ProjectProvider(),
          ),
        ],
        child: MaterialApp(
          home: Builder(
            builder: (context) {
              if (!contextCompleter.isCompleted) {
                contextCompleter.complete(context);
              }
              return const SizedBox.shrink();
            },
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();
    return contextCompleter.future;
  }

  Future<File> writeDeterministicImage(String name) async {
    const stubPngBase64 =
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAAOb5QkAAAAASUVORK5CYII=';
    final bytes = base64Decode(stubPngBase64);

    final tmpDir = await Directory.systemTemp.createTemp('spaces_e2e_');
    final file = File('${tmpDir.path}/$name.png');
    await file.writeAsBytes(bytes, flush: true);
    return file;
  }
}
