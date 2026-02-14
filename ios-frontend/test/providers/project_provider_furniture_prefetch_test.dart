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
}
