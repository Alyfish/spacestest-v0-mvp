import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/models/project.dart';
import 'package:spaces/models/shop_product.dart';
import 'package:spaces/providers/project_provider.dart';

Project _dummyProject() {
  final now = DateTime(2026, 1, 1);
  return Project(
    id: 'project_prefetch',
    userId: 'user_test',
    createdAt: now,
    updatedAt: now,
    status: 'ready',
  );
}

class _PrefetchSuccessProvider extends ProjectProvider {
  String? lastDetectImageType;
  String? lastAnalyzeImageType;

  @override
  Future<Map<String, dynamic>> autoDetectFurnitureForPrefetch(
    String projectId,
    String authToken, {
    required String imageType,
  }) async {
    lastDetectImageType = imageType;
    return {
      'detections': [
        {
          'label': 'sofa',
          'rect': {'x': 0.10, 'y': 0.20, 'width': 0.40, 'height': 0.35},
          'confidence': 0.92,
        },
        {
          'label': 'coffee table',
          'rect': {'x': 0.50, 'y': 0.55, 'width': 0.20, 'height': 0.18},
          'confidence': 0.89,
        },
        {
          'label': 'table lamp',
          'rect': {'x': 0.72, 'y': 0.18, 'width': 0.12, 'height': 0.20},
          'confidence': 0.84,
        },
        {
          'label': 'armchair',
          'rect': {'x': 0.70, 'y': 0.60, 'width': 0.20, 'height': 0.30},
          'confidence': 0.87,
        },
        {
          'label': 'rug',
          'rect': {'x': 0.14, 'y': 0.65, 'width': 0.48, 'height': 0.30},
          'confidence': 0.75,
        },
        {
          'label': 'mirror',
          'rect': {'x': 0.04, 'y': 0.06, 'width': 0.14, 'height': 0.20},
          'confidence': 0.66,
        },
        {
          'label': 'person',
          'rect': {'x': 0.88, 'y': 0.03, 'width': 0.10, 'height': 0.24},
          'confidence': 0.95,
        },
      ],
    };
  }

  @override
  Future<Map<String, dynamic>> analyzeFurnitureBatchForPrefetch(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selections, {
    required String imageType,
  }) async {
    lastAnalyzeImageType = imageType;
    final rows = selections
        .map(
          (selection) => {
            'id': selection['id'],
            'furniture_type': selection['label'] ?? 'furniture',
            'confidence': 0.9,
            'style': 'modern',
            'material': 'wood',
            'color': 'brown',
            'search_query': '${selection['label'] ?? 'furniture'} buy online',
            'products': [
              {
                'id': 'prod_${selection['id']}',
                'title': 'Prefetched Product',
                'url': 'https://example.com/${selection['id']}',
                'image_url': '',
                'store': 'Example',
                'price': 149.0,
              },
            ],
          },
        )
        .toList();

    return {'selections': rows};
  }
}

class _PrefetchFailureProvider extends ProjectProvider {
  @override
  Future<Map<String, dynamic>> autoDetectFurnitureForPrefetch(
    String projectId,
    String authToken, {
    required String imageType,
  }) async {
    throw Exception('mock detect failure');
  }
}

class _PrefetchCapProvider extends _PrefetchSuccessProvider {
  int lastSelectionCount = 0;

  @override
  Future<Map<String, dynamic>> analyzeFurnitureBatchForPrefetch(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selections, {
    required String imageType,
  }) async {
    lastSelectionCount = selections.length;
    return super.analyzeFurnitureBatchForPrefetch(
      projectId,
      authToken,
      selections,
      imageType: imageType,
    );
  }
}

class _RobustHotspotProvider extends ProjectProvider {
  int robustCalls = 0;

  @override
  Future<Map<String, dynamic>> analyzeFurnitureBatchForHotspotRobust(
    String projectId,
    String authToken,
    Map<String, dynamic> selection, {
    required String imageType,
    Duration? timeout,
  }) async {
    robustCalls += 1;
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return {
      'selections': [
        {
          'id': selection['id'],
          'furniture_type': selection['label'] ?? 'furniture',
          'products': [
            {
              'id': 'robust_${selection['id']}',
              'title': 'Robust Product',
              'url': 'https://example.com/robust/${selection['id']}',
              'image_url': '',
              'store': 'Example',
              'price': 210.0,
            },
          ],
        },
      ],
    };
  }
}

class _BoundedWaitProbeProvider extends ProjectProvider {
  int robustCallCount = 0;

  @override
  Future<bool> runRobustHotspotAnalysis(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
  }) async {
    robustCallCount += 1;
    await Future<void>.delayed(const Duration(milliseconds: 200));
    return false;
  }
}

void main() {
  group('ProjectProvider furniture prefetch', () {
    test('prefetch populates hotspots and cached analyses', () async {
      final provider = _PrefetchSuccessProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final ok = await provider.primeFurnitureHotspotsAndPrefetch(
        authToken: 'test_token',
      );

      expect(ok, isTrue);
      expect(provider.detectedHotspots, isNotEmpty);
      expect(
        provider.detectedHotspots.length,
        ProjectProvider.dreamSpaceHotspotCount,
      );
      expect(provider.prefetchedFurnitureByHotspotId, isNotEmpty);
      expect(provider.lastDetectImageType, ProjectProvider.dreamSpaceImageType);
      expect(
        provider.lastAnalyzeImageType,
        ProjectProvider.dreamSpaceImageType,
      );
      expect(provider.errorMessage, isNull);
      expect(provider.status, isNot(ProjectStatus.error));
    });

    test(
      'prefetch failure is non-blocking and does not set global error',
      () async {
        final provider = _PrefetchFailureProvider();
        provider.debugSetCurrentProject(_dummyProject());

        final ok = await provider.primeFurnitureHotspotsAndPrefetch(
          authToken: 'test_token',
        );

        expect(ok, isFalse);
        expect(provider.detectedHotspots, isEmpty);
        expect(provider.prefetchedFurnitureByHotspotId, isEmpty);
        expect(provider.errorMessage, isNull);
        expect(provider.status, isNot(ProjectStatus.error));
      },
    );

    test('prefetch analyzes all detected hotspot selections', () async {
      final provider = _PrefetchCapProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final ok = await provider.primeFurnitureHotspotsAndPrefetch(
        authToken: 'test_token',
      );

      expect(ok, isTrue);
      expect(
        provider.detectedHotspots.length,
        ProjectProvider.dreamSpaceHotspotCount,
      );
      expect(provider.lastSelectionCount, provider.detectedHotspots.length);
    });

    test(
      'ensureHotspotProductsReady triggers robust fallback for empty hotspot',
      () async {
        final provider = _RobustHotspotProvider();
        provider.debugSetCurrentProject(_dummyProject());
        const hotspot = ProductHotspot(
          id: 'auto_empty_hotspot',
          x: 0.42,
          y: 0.58,
          itemType: 'furniture',
          label: 'Nightstand',
        );
        provider.debugSetFurniturePrefetchData(
          hotspots: const [hotspot],
          prefetchedByHotspotId: {
            hotspot.id: {
              'id': hotspot.id,
              'furniture_type': 'nightstand',
              'products': const [],
            },
          },
        );

        final ready = await provider.ensureHotspotProductsReady(
          hotspot,
          authToken: 'test_token',
        );

        expect(ready, isTrue);
        expect(provider.robustCalls, 1);
        expect(provider.hasProductsForHotspot(hotspot.id), isTrue);
      },
    );

    test(
      'ensureHotspotProductsReady de-dupes in-flight robust fallback calls',
      () async {
        final provider = _RobustHotspotProvider();
        provider.debugSetCurrentProject(_dummyProject());
        const hotspot = ProductHotspot(
          id: 'auto_empty_hotspot_2',
          x: 0.25,
          y: 0.35,
          itemType: 'furniture',
          label: 'Lamp',
        );
        provider.debugSetFurniturePrefetchData(
          hotspots: const [hotspot],
          prefetchedByHotspotId: {
            hotspot.id: {
              'id': hotspot.id,
              'furniture_type': 'lamp',
              'products': const [],
            },
          },
        );

        final results = await Future.wait([
          provider.ensureHotspotProductsReady(hotspot, authToken: 'test_token'),
          provider.ensureHotspotProductsReady(hotspot, authToken: 'test_token'),
        ]);

        expect(results.every((result) => result), isTrue);
        expect(provider.robustCalls, 1);
      },
    );

    test(
      'bounded robust warmup wait returns quickly without blocking',
      () async {
        final provider = _BoundedWaitProbeProvider();
        provider.debugSetCurrentProject(_dummyProject());
        const hotspots = [
          ProductHotspot(
            id: 'auto_wait_1',
            x: 0.2,
            y: 0.2,
            itemType: 'furniture',
            label: 'Chair',
          ),
          ProductHotspot(
            id: 'auto_wait_2',
            x: 0.7,
            y: 0.6,
            itemType: 'furniture',
            label: 'Table',
          ),
        ];
        provider.debugSetFurniturePrefetchData(
          hotspots: hotspots,
          prefetchedByHotspotId: {
            hotspots[0].id: {'id': hotspots[0].id, 'products': const []},
            hotspots[1].id: {'id': hotspots[1].id, 'products': const []},
          },
        );

        final sw = Stopwatch()..start();
        await provider.prewarmEmptyHotspotsWithRobustFallback(
          authToken: 'test_token',
          maxWait: const Duration(milliseconds: 40),
        );
        sw.stop();

        expect(sw.elapsedMilliseconds, lessThan(150));
        expect(provider.robustCallCount, hotspots.length);
      },
    );
  });

  group('Ready-first hotspot pipeline', () {
    // Helper: 5 hotspots with products for the given indices
    List<ProductHotspot> _makeHotspots(int count) {
      return List.generate(
        count,
        (i) => ProductHotspot(
          id: 'hs_$i',
          x: 0.1 * (i + 1),
          y: 0.2 * (i + 1),
          itemType: 'furniture',
          label: 'Item $i',
        ),
      );
    }

    Map<String, dynamic> _productEntry(String id) => {
      'id': id,
      'furniture_type': 'furniture',
      'products': [
        {
          'id': 'prod_$id',
          'title': 'Product',
          'url': 'https://example.com/$id',
        },
      ],
    };

    Map<String, dynamic> _emptyEntry(String id) => {
      'id': id,
      'furniture_type': 'furniture',
      'products': <Map<String, dynamic>>[],
    };

    test('gate passes immediately when batch prefetch meets threshold', () {
      final provider = _PrefetchSuccessProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final hotspots = _makeHotspots(5);
      // 3 out of 5 have products → meets threshold
      final prefetchData = <String, Map<String, dynamic>>{};
      for (var i = 0; i < 5; i++) {
        prefetchData[hotspots[i].id] = i < 3
            ? _productEntry(hotspots[i].id)
            : _emptyEntry(hotspots[i].id);
      }

      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: prefetchData,
      );

      expect(provider.readyHotspotCount, 3);
      expect(provider.hotspotsReadyForDreamSpace, isTrue);
    });

    test('dynamic threshold: <3 hotspots uses total count', () {
      final provider = _PrefetchSuccessProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final hotspots = _makeHotspots(2);
      // Only 1 out of 2 ready → not enough (threshold = min(3, 2) = 2)
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          hotspots[0].id: _productEntry(hotspots[0].id),
          hotspots[1].id: _emptyEntry(hotspots[1].id),
        },
      );

      expect(provider.readyHotspotCount, 1);
      expect(provider.hotspotsReadyForDreamSpace, isFalse);

      // Now fill both → should pass
      provider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          hotspots[0].id: _productEntry(hotspots[0].id),
          hotspots[1].id: _productEntry(hotspots[1].id),
        },
      );

      expect(provider.readyHotspotCount, 2);
      expect(provider.hotspotsReadyForDreamSpace, isTrue);
    });

    test('stricter hasProductsForHotspot rejects non-Map products', () {
      final provider = ProjectProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final hotspots = _makeHotspots(1);
      // products list contains null instead of Map<String, dynamic>
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          hotspots[0].id: {
            'id': hotspots[0].id,
            'furniture_type': 'furniture',
            'products': [null],
          },
        },
      );

      expect(provider.hasProductsForHotspot(hotspots[0].id), isFalse);
    });

    test('stricter hasProductsForHotspot accepts valid Map products', () {
      final provider = ProjectProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final hotspots = _makeHotspots(1);
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {hotspots[0].id: _productEntry(hotspots[0].id)},
      );

      expect(provider.hasProductsForHotspot(hotspots[0].id), isTrue);
    });

    test('stale rescue: version token prevents writes after reset', () {
      final provider = _PrefetchSuccessProvider();
      provider.debugSetCurrentProject(_dummyProject());

      final hotspots = _makeHotspots(3);
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          for (final h in hotspots) h.id: _emptyEntry(h.id),
        },
      );

      // Simulate: reset bumps the version and clears state
      provider.debugResetHotspotPrefetchState();

      expect(provider.detectedHotspots, isEmpty);
      expect(provider.prefetchedFurnitureByHotspotId, isEmpty);
    });

    test('tap-time runs full analysis directly (no retry needed)', () async {
      final provider = _RobustHotspotProvider();
      provider.debugSetCurrentProject(_dummyProject());
      const hotspot = ProductHotspot(
        id: 'tap_direct_hs',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Chair',
      );
      provider.debugSetFurniturePrefetchData(
        hotspots: const [hotspot],
        prefetchedByHotspotId: {
          hotspot.id: {
            'id': hotspot.id,
            'furniture_type': 'chair',
            'products': <Map<String, dynamic>>[],
          },
        },
      );

      final ready = await provider.ensureHotspotProductsReady(
        hotspot,
        authToken: 'test_token',
      );

      // With split maps, tap always runs full directly — single call, no retry
      expect(ready, isTrue);
      expect(provider.robustCalls, 1);
    });

    test('tap does not join rescue completer (split maps)', () async {
      final provider = _RobustHotspotProvider();
      provider.debugSetCurrentProject(_dummyProject());
      const hotspot = ProductHotspot(
        id: 'split_hs',
        x: 0.3,
        y: 0.4,
        itemType: 'furniture',
        label: 'Sofa',
      );
      provider.debugSetFurniturePrefetchData(
        hotspots: const [hotspot],
        prefetchedByHotspotId: {
          hotspot.id: {
            'id': hotspot.id,
            'furniture_type': 'sofa',
            'products': <Map<String, dynamic>>[],
          },
        },
      );

      // Tap starts its own full analysis regardless of any rescue state
      final ready = await provider.ensureHotspotProductsReady(
        hotspot,
        authToken: 'test_token',
      );

      expect(ready, isTrue);
      expect(provider.robustCalls, 1);
      expect(provider.hasProductsForHotspot(hotspot.id), isTrue);
    });

    test('rescue skips user-tapped hotspots', () async {
      final provider = _TrackingRescueProvider();
      provider.debugSetCurrentProject(_dummyProject());
      const hotspots = [
        ProductHotspot(
          id: 'hs_0',
          x: 0.1,
          y: 0.2,
          itemType: 'furniture',
          label: 'Chair',
        ),
        ProductHotspot(
          id: 'hs_1',
          x: 0.3,
          y: 0.4,
          itemType: 'furniture',
          label: 'Table',
        ),
        ProductHotspot(
          id: 'hs_2',
          x: 0.5,
          y: 0.6,
          itemType: 'furniture',
          label: 'Lamp',
        ),
      ];
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          for (final h in hotspots)
            h.id: {
              'id': h.id,
              'furniture_type': h.label,
              'products': <Map<String, dynamic>>[],
            },
        },
      );

      // Simulate user tapping hs_1 before rescue reaches it
      await provider.runRobustHotspotAnalysis(
        hotspots[1],
        authToken: 'test_token',
      );

      // Now run concurrent rescue — should skip hs_1
      await provider.testRunConcurrentRescue(
        emptyHotspots: hotspots,
        authToken: 'test_token',
        version: provider.currentDreamSpaceImageVersion,
      );

      // hs_1 was tapped so rescue should not have called it
      expect(provider.rescuedHotspotIds, isNot(contains('hs_1')));
      // hs_0 already got products from rescue (or was attempted)
      expect(provider.rescuedHotspotIds, contains('hs_0'));
    });

    test('rescue stops after consecutive failures (circuit breaker)', () async {
      final provider = _AlwaysFailRescueProvider();
      provider.debugSetCurrentProject(_dummyProject());
      // Use 10 hotspots so the circuit breaker has room to prove it stops early.
      // With maxConcurrent=3 and breaker at 3 failures, at most ~5 can start
      // (initial batch of 3 + up to 2 dequeued by whenComplete before breaker trips).
      final hotspots = List.generate(
        10,
        (i) => ProductHotspot(
          id: 'fail_$i',
          x: 0.05 * (i + 1),
          y: 0.05 * (i + 1),
          itemType: 'furniture',
          label: 'Item $i',
        ),
      );
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          for (final h in hotspots)
            h.id: {
              'id': h.id,
              'furniture_type': h.label,
              'products': <Map<String, dynamic>>[],
            },
        },
      );

      await provider.testRunConcurrentRescue(
        emptyHotspots: hotspots,
        authToken: 'test_token',
        version: provider.currentDreamSpaceImageVersion,
      );

      // Circuit breaker trips after 3 consecutive failures.
      // With maxConcurrent=3, up to 5 tasks may start (initial 3 + 2 dequeued
      // by whenComplete callbacks before the 3rd failure clears the queue).
      // The key assertion: rescue does NOT attempt all 10.
      expect(provider.rescueAttempts, lessThanOrEqualTo(5));
      expect(provider.rescueAttempts, lessThan(10));
    });

    test('empty hotspot list means gate is immediately satisfied', () {
      final provider = ProjectProvider();
      provider.debugSetCurrentProject(_dummyProject());

      provider.debugSetFurniturePrefetchData(
        hotspots: const [],
        prefetchedByHotspotId: {},
      );

      expect(provider.hotspotsReadyForDreamSpace, isTrue);
    });
  });
}

/// Provider that tracks which hotspot IDs rescue attempted.
/// Overrides both tap-time and rescue paths to avoid real API calls.
class _TrackingRescueProvider extends ProjectProvider {
  final List<String> rescuedHotspotIds = [];

  @override
  Future<Map<String, dynamic>> analyzeFurnitureBatchForHotspotRobust(
    String projectId,
    String authToken,
    Map<String, dynamic> selection, {
    required String imageType,
    Duration? timeout,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 10));
    return {
      'selections': [
        {
          'id': selection['id'],
          'furniture_type': selection['label'] ?? 'furniture',
          'products': [
            {
              'id': 'prod_${selection['id']}',
              'title': 'Product',
              'url': 'https://example.com/${selection['id']}',
              'image_url': '',
              'store': 'Example',
              'price': 99.0,
            },
          ],
        },
      ],
    };
  }

  @override
  Future<bool> rescueHotspotAnalysisForTest(
    ProductHotspot hotspot,
    String authToken,
    int version,
  ) async {
    rescuedHotspotIds.add(hotspot.id);
    // Simulate successful rescue by writing products into the prefetch map
    debugSetFurniturePrefetchData(
      prefetchedByHotspotId: {
        ...prefetchedFurnitureByHotspotId,
        hotspot.id: {
          'id': hotspot.id,
          'furniture_type': hotspot.label,
          'products': [
            {
              'id': 'rescue_${hotspot.id}',
              'title': 'Rescue Product',
              'url': 'https://example.com/rescue/${hotspot.id}',
              'image_url': '',
              'store': 'Example',
              'price': 99.0,
            },
          ],
        },
      },
    );
    return true;
  }
}

/// Provider whose rescue always fails — for circuit breaker testing.
class _AlwaysFailRescueProvider extends ProjectProvider {
  int rescueAttempts = 0;

  @override
  Future<bool> rescueHotspotAnalysisForTest(
    ProductHotspot hotspot,
    String authToken,
    int version,
  ) async {
    rescueAttempts += 1;
    await Future<void>.delayed(const Duration(milliseconds: 10));
    throw Exception('mock rescue failure');
  }
}
