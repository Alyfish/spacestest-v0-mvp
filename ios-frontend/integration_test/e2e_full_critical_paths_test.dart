import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:provider/provider.dart';
import 'package:spaces/constants/api_constants.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/providers/user_provider.dart';
import 'package:spaces/services/api_service.dart';

import 'helpers/e2e_harness.dart';
import 'helpers/trace_assertions.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('full critical paths hit expected backend endpoints', (
    tester,
  ) async {
    final harness = E2EHarness.fromDefines();
    harness.ensureConfigured();

    await harness.verifyBackendStatus();
    await harness.clearTraces();

    final context = await harness.pumpProviderHarness(tester);
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    userProvider.seedTestUser(
      userId: harness.userId,
      token: harness.seededAuthToken,
      email: '${harness.userId}@spaces.local',
      name: 'E2E Harness User',
    );

    // ------------------------------------------------------------------------
    // Scenario: create_flow_pipeline
    // ------------------------------------------------------------------------
    expect(await projectProvider.createProject(context), isTrue);
    final projectId = projectProvider.currentProject!.id;

    final imageFile = await harness.writeDeterministicImage('base_image');
    expect(projectProvider.setProjectImage(imageFile), isTrue);
    expect(await projectProvider.uploadProjectImage(context), isTrue);

    expect(await projectProvider.saveSpaceType(context, 'living_room'), isTrue);
    expect(
      await projectProvider.saveApproach(context, 'complete_revamp'),
      isTrue,
    );

    projectProvider.setPreferredStoresLocal(const ['Target', 'Wayfair']);
    expect(await projectProvider.ensurePreferredStoresSynced(context), isTrue);

    expect(await projectProvider.ensureRecommendationsLoaded(context), isTrue);
    expect(projectProvider.productRecommendations, isNotEmpty);

    expect(
      await projectProvider.ensureSearchJobStarted(
        context,
        projectProvider.productRecommendations,
      ),
      isTrue,
    );

    await projectProvider.refreshProductSuggestionsSnapshot(context);
    await projectProvider.preloadTrendingProducts(context);

    // ------------------------------------------------------------------------
    // Scenario: improvements_to_redesign
    // ------------------------------------------------------------------------
    final authToken = userProvider.user.token!;

    final selectedRecommendations = projectProvider.productRecommendations
        .take(2)
        .toList();
    if (selectedRecommendations.isNotEmpty) {
      final selectedResponse = await ApiService.setSelectedRecommendations(
        projectId,
        authToken,
        selectedRecommendations,
      );
      final selected = selectedResponse['selected_recommendations'] as List?;
      expect(selected, isNotNull);
    }

    final imageJob = await ApiService.startGenerateImage(
      projectId,
      authToken,
      idempotencyKey: '${projectId}_e2e_generate',
    );
    final imageJobId = imageJob['job_id'] as String;

    final pollResult = await ApiService.pollJobUntilDone(
      projectId,
      imageJobId,
      authToken,
      maxWait: const Duration(seconds: 60),
      pollInterval: const Duration(milliseconds: 500),
    );
    expect(pollResult.outcome, PollingOutcome.done);

    final generatedImageBytes = await ApiService.getGeneratedImage(
      projectId,
      authToken,
    );
    expect(generatedImageBytes, isNotEmpty);

    // ------------------------------------------------------------------------
    // Scenario: hotspot_and_cart
    // ------------------------------------------------------------------------
    final autoDetectResponse = await ApiService.autoDetectFurniture(
      projectId,
      authToken,
      imageType: 'product',
    );

    final detections = _toMapList(autoDetectResponse['detections']);
    expect(detections, isNotEmpty);

    final firstDetection = detections.first;
    final selectionPayload = {
      'id': firstDetection['id']?.toString() ?? 'sel_1',
      'x': _asDouble(firstDetection['x']) ?? 0.5,
      'y': _asDouble(firstDetection['y']) ?? 0.5,
      'label': firstDetection['label']?.toString() ?? 'chair',
    };

    final batchAnalysis = await ApiService.analyzeFurnitureBatch(
      projectId,
      authToken,
      [selectionPayload],
      imageType: 'product',
      mode: 'full',
      timeout: const Duration(seconds: 60),
    );

    final analyzedSelections = _toMapList(batchAnalysis['selections']);
    expect(analyzedSelections, isNotEmpty);

    final firstSelection = analyzedSelections.first;
    final productCandidates = _toMapList(firstSelection['products']);
    expect(productCandidates, isNotEmpty);

    final firstCandidate = productCandidates.first;
    final selectedProductsPayload = [
      {
        'url': (firstCandidate['url'] ?? 'https://example.com/stub').toString(),
        'title': (firstCandidate['title'] ?? 'Stub Product').toString(),
        'image_url': firstCandidate['image_url']?.toString(),
        'store': firstCandidate['store']?.toString(),
        'price_str': firstCandidate['price_str']?.toString(),
        'price': _asDouble(firstCandidate['price']),
        'furniture_id': firstSelection['id']?.toString() ?? 'sel_1',
      },
    ];

    final processedSelection = await ApiService.processFurnitureSelection(
      projectId,
      authToken,
      selectedProductsPayload,
    );
    final resolvedProducts = _toMapList(
      processedSelection['resolved_products'],
    );
    expect(resolvedProducts, isNotEmpty);

    final affiliateItems = resolvedProducts
        .map(
          (product) => {
            'shopping_url':
                (product['resolved_url'] ?? product['original_url'] ?? '')
                    .toString(),
            'retailer_hint': (product['store'] ?? 'Stub Store').toString(),
            'title': (product['title'] ?? 'Stub Product').toString(),
          },
        )
        .where((item) => (item['shopping_url'] ?? '').toString().isNotEmpty)
        .toList();

    final affiliateResponse = await http
        .post(
          Uri.parse('${ApiConstants.baseUrl}/affiliate/generate-cart'),
          headers: ApiConstants.authHeaders(authToken),
          body: jsonEncode({'items': affiliateItems, 'strict_mode': false}),
        )
        .timeout(const Duration(seconds: 30));

    expect(
      affiliateResponse.statusCode,
      anyOf(200, 201),
      reason: affiliateResponse.body,
    );

    // ------------------------------------------------------------------------
    // Trace assertions
    // ------------------------------------------------------------------------
    final traces = await harness.fetchTraces();
    expect(traces, isNotEmpty);

    expectEndpointOrder(traces, [
      {'method': 'POST', 'path': '/projects'},
      {'method': 'POST', 'path': '/projects/$projectId/upload-image'},
      {'method': 'POST', 'path': '/projects/$projectId/space-type'},
      {'method': 'POST', 'path': '/projects/$projectId/improvement-mode'},
      {'method': 'POST', 'path': '/projects/$projectId/preferred-stores'},
      {
        'method': 'POST',
        'path': '/projects/$projectId/product-recommendations',
      },
      {'method': 'GET', 'path': '/projects/$projectId/job-status/'},
      {'method': 'GET', 'path': '/projects/$projectId/product-suggestions'},
      {'method': 'GET', 'path': '/projects/$projectId/trending-products'},
      {'method': 'POST', 'path': '/projects/$projectId/generate-image'},
      {'method': 'GET', 'path': '/projects/$projectId/generated-image'},
      {'method': 'GET', 'path': '/projects/$projectId/auto-detect'},
      {
        'method': 'POST',
        'path': '/projects/$projectId/analyze-furniture-batch',
      },
      {
        'method': 'POST',
        'path': '/projects/$projectId/process-furniture-selection',
      },
      {'method': 'POST', 'path': '/affiliate/generate-cart'},
    ]);

    expectEndpointHit(
      traces,
      method: 'POST',
      path: RegExp('^/projects/$projectId/product-recommendations\$'),
      queryKey: 'auto_search',
      queryValue: 'true',
    );

    expectEndpointHit(
      traces,
      method: 'POST',
      path: RegExp('^/projects/$projectId/skip-inspiration-images\$'),
    );
    expectEndpointHit(
      traces,
      method: 'POST',
      path: RegExp('^/projects/$projectId/skip-color-analysis\$'),
    );
    expectEndpointHit(
      traces,
      method: 'POST',
      path: RegExp('^/projects/$projectId/skip-style-analysis\$'),
    );

    expectNoDuplicateSearchKickoff(traces, projectId, maxAllowed: 0);
  });
}

List<Map<String, dynamic>> _toMapList(dynamic value) {
  final list = value as List<dynamic>? ?? const [];
  return list
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
}

double? _asDouble(dynamic value) {
  if (value is num) return value.toDouble();
  if (value == null) return null;
  return double.tryParse(value.toString());
}
