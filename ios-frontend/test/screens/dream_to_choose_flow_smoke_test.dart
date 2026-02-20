import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:spaces/models/project.dart';
import 'package:spaces/models/shop_product.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/screens/choose_products_screen.dart';
import 'package:spaces/screens/dream_space_screen.dart';
import 'package:spaces/widgets/interactive_image_widget.dart';

const _tinyGeneratedPngBase64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/5f4AAAAASUVORK5CYII=';

Project _dummyProject() {
  final now = DateTime(2026, 1, 1);
  return Project(
    id: 'project_flow_smoke',
    userId: 'user_test',
    createdAt: now,
    updatedAt: now,
    status: 'ready',
  );
}

class _DreamFallbackProvider extends ProjectProvider {
  @override
  Future<bool> ensureHotspotProductsReady(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
    bool allowRobustFallback = true,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 150));
    debugSetFurniturePrefetchData(
      prefetchedByHotspotId: {
        hotspot.id: {
          'id': hotspot.id,
          'furniture_type': hotspot.label,
          'products': [
            {
              'id': 'dream_fallback_1',
              'title': 'Dream Fallback Product',
              'url': 'https://example.com/dream-fallback',
              'image_url': '',
              'store': 'Store',
              'price': 88.0,
            },
          ],
        },
      },
    );
    return true;
  }
}

Widget _buildFlowApp() {
  return Builder(
    builder: (context) {
      return DreamSpaceScreen(
        onHotspotTap: (hotspot) {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => ChooseProductsScreen(hotspot: hotspot),
            ),
          );
        },
      );
    },
  );
}

void main() {
  testWidgets('dream space generated image always uses contain fit (no crop)', (
    tester,
  ) async {
    final provider = ProjectProvider();
    provider.debugSetCurrentProject(
      _dummyProject().copyWith(approach: 'iterative'),
    );
    provider.debugSetGeneratedImageBytes(base64Decode(_tinyGeneratedPngBase64));

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ProjectProvider>.value(value: provider),
        ],
        child: MaterialApp(home: _buildFlowApp()),
      ),
    );
    await tester.pump();

    final imageWidgets = tester
        .widgetList<InteractiveImageWidget>(find.byType(InteractiveImageWidget))
        .toList();
    expect(imageWidgets, isNotEmpty);
    for (final imageWidget in imageWidgets) {
      expect(imageWidget.fit, BoxFit.contain);
    }
  });

  testWidgets(
    'smoke: DreamSpace renders 5 markers and hotspot tap opens ChooseProducts',
    (tester) async {
      final provider = ProjectProvider();
      provider.debugSetCurrentProject(_dummyProject());
      provider.debugSetGeneratedImageBytes(
        base64Decode(_tinyGeneratedPngBase64),
      );

      const hotspots = <ProductHotspot>[
        ProductHotspot(
          id: 'auto_0_220_280',
          x: 0.22,
          y: 0.28,
          itemType: 'furniture',
          label: 'Pendant light',
        ),
        ProductHotspot(
          id: 'auto_1_460_420',
          x: 0.46,
          y: 0.42,
          itemType: 'furniture',
          label: 'Bed frame',
        ),
        ProductHotspot(
          id: 'auto_2_710_460',
          x: 0.71,
          y: 0.46,
          itemType: 'furniture',
          label: 'Nightstand',
        ),
        ProductHotspot(
          id: 'auto_3_350_700',
          x: 0.35,
          y: 0.70,
          itemType: 'furniture',
          label: 'Rug',
        ),
        ProductHotspot(
          id: 'auto_4_610_760',
          x: 0.61,
          y: 0.76,
          itemType: 'furniture',
          label: 'Bench',
        ),
      ];
      provider.debugSetFurniturePrefetchData(
        hotspots: hotspots,
        prefetchedByHotspotId: {
          'auto_1_460_420': {
            'id': 'auto_1_460_420',
            'furniture_type': 'chair',
            'products': [
              {
                'id': 'flow_prefetched_1',
                'title': 'Flow Cached Chair',
                'url': 'https://example.com/flow-chair',
                'image_url': '',
                'store': 'Target',
                'price': 129.0,
                'description': 'Smoke flow cached product',
              },
            ],
          },
        },
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(value: provider),
          ],
          child: MaterialApp(home: _buildFlowApp()),
        ),
      );

      await tester.pump();
      final targetMarkerFinder = find.byKey(
        const ValueKey('auto_hotspot_auto_1_460_420'),
      );
      for (var i = 0; i < 20 && targetMarkerFinder.evaluate().isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      for (final hotspot in hotspots) {
        expect(
          find.byKey(ValueKey('auto_hotspot_${hotspot.id}')),
          findsOneWidget,
        );
      }

      await tester.tap(targetMarkerFinder);
      await tester.pumpAndSettle(const Duration(milliseconds: 800));

      expect(find.text('Flow Cached Chair'), findsOneWidget);
      expect(find.text('Failed to analyze furniture'), findsNothing);
    },
  );

  testWidgets(
    'smoke: empty hotspot triggers fallback loading then renders products',
    (tester) async {
      final provider = _DreamFallbackProvider();
      provider.debugSetCurrentProject(_dummyProject());
      provider.debugSetGeneratedImageBytes(
        base64Decode(_tinyGeneratedPngBase64),
      );

      const hotspot = ProductHotspot(
        id: 'auto_empty_for_fallback',
        x: 0.5,
        y: 0.5,
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

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(value: provider),
          ],
          child: MaterialApp(home: _buildFlowApp()),
        ),
      );

      await tester.pump();
      final markerFinder = find.byKey(
        const ValueKey('auto_hotspot_auto_empty_for_fallback'),
      );
      for (var i = 0; i < 20 && markerFinder.evaluate().isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(markerFinder, findsOneWidget);
      await tester.tap(markerFinder);
      await tester.pump(const Duration(milliseconds: 40));

      await tester.pumpAndSettle(const Duration(milliseconds: 500));
      expect(find.text('Dream Fallback Product'), findsOneWidget);
    },
  );
}
