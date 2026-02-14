import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spaces/services/api_service.dart';

void main() {
  group('ApiService.analyzeFurnitureBatch', () {
    test('sends mode in request body', () async {
      late Map<String, dynamic> capturedBody;
      final client = MockClient((http.Request request) async {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'project_id': 'project_1',
            'selections': const [],
            'overall_analysis': '',
            'total_items': 0,
            'status': 'success',
            'message': 'ok',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      await ApiService.analyzeFurnitureBatch(
        'project_1',
        'token_123',
        const [],
        imageType: 'inspiration',
        mode: 'fast_prefetch',
        timeout: const Duration(seconds: 1),
        client: client,
      );

      expect(capturedBody['image_type'], 'inspiration');
      expect(capturedBody['mode'], 'fast_prefetch');
    });

    test('respects custom timeout', () async {
      final client = MockClient((http.Request request) async {
        await Future<void>.delayed(const Duration(milliseconds: 50));
        return http.Response(
          jsonEncode({
            'project_id': 'project_1',
            'selections': const [],
            'overall_analysis': '',
            'total_items': 0,
            'status': 'success',
            'message': 'ok',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      expect(
        () => ApiService.analyzeFurnitureBatch(
          'project_1',
          'token_123',
          const [],
          timeout: const Duration(milliseconds: 5),
          client: client,
        ),
        throwsA(isA<TimeoutException>()),
      );
    });
  });
}
