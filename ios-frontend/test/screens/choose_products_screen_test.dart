import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:spaces/models/project.dart';
import 'package:spaces/models/shop_product.dart';
import 'package:spaces/providers/cart_provider.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/screens/choose_products_screen.dart';
import 'package:spaces/widgets/shop_product_card.dart';

Project _dummyProject() {
  final now = DateTime(2026, 1, 1);
  return Project(
    id: 'project_choose_products',
    userId: 'user_test',
    createdAt: now,
    updatedAt: now,
    status: 'ready',
  );
}

class _FallbackSuccessProvider extends ProjectProvider {
  bool fallbackCalled = false;

  @override
  Future<bool> ensureHotspotProductsReady(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
    bool allowRobustFallback = true,
  }) async {
    fallbackCalled = true;
    debugSetFurniturePrefetchData(
      prefetchedByHotspotId: {
        hotspot.id: {
          'id': hotspot.id,
          'furniture_type': hotspot.label,
          'products': [
            {
              'id': 'fallback_prod_1',
              'title': 'Fallback Nightstand',
              'url': 'https://example.com/fallback-nightstand',
              'image_url': '',
              'store': 'Target',
              'price': 119.0,
            },
          ],
        },
      },
    );
    return true;
  }
}

class _FallbackDelayedProvider extends ProjectProvider {
  final Duration delay;
  bool fallbackCalled = false;

  _FallbackDelayedProvider({required this.delay});

  @override
  Future<bool> ensureHotspotProductsReady(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
    bool allowRobustFallback = true,
  }) async {
    fallbackCalled = true;
    await Future<void>.delayed(delay);
    debugSetFurniturePrefetchData(
      prefetchedByHotspotId: {
        hotspot.id: {
          'id': hotspot.id,
          'furniture_type': hotspot.label,
          'products': [
            {
              'id': 'delayed_prod_1',
              'title': 'Delayed Fallback Product',
              'url': 'https://example.com/delayed-fallback',
              'image_url': '',
              'store': 'Wayfair',
              'price': 99.0,
            },
          ],
        },
      },
    );
    return true;
  }
}

class _FallbackEmptyProvider extends ProjectProvider {
  bool fallbackCalled = false;

  @override
  Future<bool> ensureHotspotProductsReady(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
    bool allowRobustFallback = true,
  }) async {
    fallbackCalled = true;
    return false;
  }
}

void main() {
  testWidgets(
    'ChooseProductsScreen renders prefetched hotspot products without analysis call',
    (tester) async {
      final projectProvider = ProjectProvider();
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_0_500_500': {
            'id': 'auto_0_500_500',
            'furniture_type': 'chair',
            'products': [
              {
                'id': 'prefetched_1',
                'title': 'Cached Accent Chair',
                'url': 'https://example.com/chair',
                'image_url': '',
                'store': 'Wayfair',
                'price': 199.99,
                'description': 'A comfy chair',
              },
            ],
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_0_500_500',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Chair',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Cached Accent Chair'), findsOneWidget);
      expect(find.text('Failed to analyze furniture'), findsNothing);
    },
  );

  testWidgets(
    'ChooseProductsScreen renders bed component products when top-level products are empty',
    (tester) async {
      final projectProvider = ProjectProvider();
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_bed_1': {
            'id': 'auto_bed_1',
            'furniture_type': 'bed',
            'products': const [],
            'is_bed': true,
            'bed_components': {
              'bed_frame': [
                {
                  'id': 'frame_1',
                  'title': 'Walnut Bed Frame',
                  'url': 'https://example.com/frame-1',
                  'image_url': '',
                  'store': 'West Elm',
                  'price': 899.0,
                },
              ],
            },
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_bed_1',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Bed',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Walnut Bed Frame'), findsOneWidget);
      expect(find.text('No products found for this hotspot'), findsNothing);
      expect(find.text('Failed to analyze furniture'), findsNothing);
    },
  );

  testWidgets(
    'ChooseProductsScreen uses robust fallback for empty auto-hotspot cache',
    (tester) async {
      final projectProvider = _FallbackSuccessProvider();
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_empty_fallback': {
            'id': 'auto_empty_fallback',
            'furniture_type': 'nightstand',
            'products': const [],
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_empty_fallback',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Nightstand',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(projectProvider.fallbackCalled, isTrue);
      expect(find.text('Fallback Nightstand'), findsOneWidget);
      expect(find.text('No products found for this hotspot'), findsNothing);
    },
  );

  testWidgets(
    'ChooseProductsScreen shows empty-success UI when fallback still has no products',
    (tester) async {
      final projectProvider = _FallbackEmptyProvider();
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_empty_1': {
            'id': 'auto_empty_1',
            'furniture_type': 'chair',
            'products': const [],
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_empty_1',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Chair',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(projectProvider.fallbackCalled, isTrue);
      expect(find.text('No products found for this hotspot'), findsOneWidget);
      expect(find.text('Failed to analyze furniture'), findsNothing);
    },
  );

  testWidgets(
    'ChooseProductsScreen shows Price unavailable for missing prices',
    (tester) async {
      final projectProvider = ProjectProvider();
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_price_1': {
            'id': 'auto_price_1',
            'furniture_type': 'chair',
            'products': [
              {
                'id': 'missing_price_1',
                'title': 'No Price Chair',
                'url': 'https://example.com/no-price-chair',
                'image_url': '',
                'store': 'Store',
              },
            ],
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_price_1',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Chair',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('No Price Chair'), findsOneWidget);
      expect(find.text('Price unavailable'), findsOneWidget);
      expect(find.text('\$0.00'), findsNothing);
    },
  );

  testWidgets('ChooseProductsScreen ranks hotspot-relevant products first', (
    tester,
  ) async {
    final projectProvider = ProjectProvider();
    projectProvider.debugSetCurrentProject(_dummyProject());
    projectProvider.debugSetFurniturePrefetchData(
      prefetchedByHotspotId: {
        'auto_rank_1': {
          'id': 'auto_rank_1',
          'furniture_type': 'nightstand',
          'products': [
            {
              'id': 'irrelevant_1',
              'title': 'Wall Clock',
              'url': 'https://example.com/wall-clock',
              'image_url': '',
              'store': 'Store',
              'price': 55.0,
            },
            {
              'id': 'relevant_1',
              'title': 'Amazon.com: Wood Nightstand',
              'url': 'https://example.com/nightstand',
              'image_url': '',
              'store': 'Amazon.com',
              'price': 95.0,
            },
          ],
        },
      },
    );

    const hotspot = ProductHotspot(
      id: 'auto_rank_1',
      x: 0.5,
      y: 0.5,
      itemType: 'furniture',
      label: 'Nightstand',
    );

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ProjectProvider>.value(value: projectProvider),
          ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
        ],
        child: const MaterialApp(home: ChooseProductsScreen(hotspot: hotspot)),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    final cards = find.byType(ShopProductCard);
    expect(cards, findsNWidgets(2));
    final firstCard = cards.first;

    expect(
      find.descendant(of: firstCard, matching: find.text('Wood Nightstand')),
      findsOneWidget,
    );
    expect(find.text('Amazon.com: Wood Nightstand'), findsNothing);
  });

  testWidgets(
    'ChooseProductsScreen shows loader during delayed fallback then renders products',
    (tester) async {
      final projectProvider = _FallbackDelayedProvider(
        delay: const Duration(milliseconds: 200),
      );
      projectProvider.debugSetCurrentProject(_dummyProject());
      projectProvider.debugSetFurniturePrefetchData(
        prefetchedByHotspotId: {
          'auto_delayed_fallback': {
            'id': 'auto_delayed_fallback',
            'furniture_type': 'nightstand',
            'products': const [],
          },
        },
      );

      const hotspot = ProductHotspot(
        id: 'auto_delayed_fallback',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Nightstand',
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ProjectProvider>.value(
              value: projectProvider,
            ),
            ChangeNotifierProvider<CartProvider>(create: (_) => CartProvider()),
          ],
          child: const MaterialApp(
            home: ChooseProductsScreen(hotspot: hotspot),
          ),
        ),
      );

      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 260));
      expect(find.text('Delayed Fallback Product'), findsOneWidget);
    },
  );
}
