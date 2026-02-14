import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spaces/services/api_service.dart';

void main() {
  group('ApiService.getProductRecommendations', () {
    test('does not send auto_search by default', () async {
      late Uri capturedUri;
      final client = MockClient((http.Request request) async {
        capturedUri = request.url;
        return http.Response(
          jsonEncode({
            'project_id': 'project_1',
            'space_type': 'living_room',
            'recommendations': const [],
            'status': 'PRODUCT_RECOMMENDATIONS_READY',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      await ApiService.getProductRecommendations(
        'project_1',
        'token_123',
        client: client,
      );

      expect(capturedUri.queryParameters.containsKey('auto_search'), isFalse);
    });

    test('sends auto_search=true when enabled', () async {
      late Uri capturedUri;
      final client = MockClient((http.Request request) async {
        capturedUri = request.url;
        return http.Response(
          jsonEncode({
            'project_id': 'project_1',
            'space_type': 'living_room',
            'recommendations': const [],
            'status': 'PRODUCT_RECOMMENDATIONS_READY',
            'search_job_id': 'job_123',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      await ApiService.getProductRecommendations(
        'project_1',
        'token_123',
        autoSearch: true,
        client: client,
      );

      expect(capturedUri.queryParameters['auto_search'], 'true');
    });
  });
}
