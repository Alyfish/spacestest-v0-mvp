import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:spaces/models/project.dart';
import 'package:spaces/models/shop_product.dart';
import 'package:spaces/providers/cart_provider.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/screens/choose_products_screen.dart';
import 'package:spaces/screens/dream_space_screen.dart';

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
  testWidgets(
    'smoke: DreamSpace hotspot tap opens ChooseProducts with prefetched cards',
    (tester) async {
      final provider = ProjectProvider();
      provider.debugSetCurrentProject(_dummyProject());

      const hotspot = ProductHotspot(
        id: 'auto_0_500_500',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Chair',
      );
      provider.debugSetFurniturePrefetchData(
        hotspots: const [hotspot],
        prefetchedByHotspotId: {
          'auto_0_500_500': {
            'id': 'auto_0_500_500',
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
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: MaterialApp(home: _buildFlowApp()),
        ),
      );

      await tester.pump();
      final markerFinder = find.byKey(
        const ValueKey('auto_hotspot_auto_0_500_500'),
      );
      for (var i = 0; i < 20 && markerFinder.evaluate().isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(markerFinder, findsOneWidget);
      await tester.tap(markerFinder);
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
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
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
