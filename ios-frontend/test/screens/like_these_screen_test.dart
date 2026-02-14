import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:spaces/providers/project_provider.dart';
import 'package:spaces/screens/like_these_screen.dart';

Map<String, dynamic> _imageBackedPayload() {
  return {
    'categories': [
      {
        'recommendation': 'replace headboard',
        'products': [
          {
            'url': 'https://example.com/product/1',
            'title': 'Live Headboard',
            'store': 'Store',
            'image_url': 'https://example.com/image.jpg',
          },
        ],
      },
    ],
  };
}

class _LikeTheseTestProvider extends ProjectProvider {
  @override
  Future<bool> warmRecommendationsAndSearch([BuildContext? context]) async {
    return true;
  }

  @override
  Future<bool> waitForImageBackedSuggestions({
    BuildContext? context,
    Duration timeout = const Duration(seconds: 6),
    Duration pollInterval = const Duration(milliseconds: 500),
  }) async {
    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      if (hasImageBackedSuggestions) return true;
      await Future<void>.delayed(pollInterval);
    }
    return hasImageBackedSuggestions;
  }

  @override
  Future<bool> refreshProductSuggestionsSnapshot([
    BuildContext? context,
  ]) async {
    return hasImageBackedSuggestions;
  }

  @override
  Future<bool> preloadTrendingProducts([BuildContext? context]) async {
    return false;
  }
}

Map<String, dynamic> _namedCategoryPayload({
  required String categoryName,
  required String productTitle,
}) {
  return {
    'categories': [
      {
        'recommendation': categoryName,
        'products': [
          {
            'url': 'https://example.com/product/fallback',
            'title': productTitle,
            'store': 'TestStore',
            'image_url': 'https://example.com/fallback.jpg',
          },
        ],
      },
    ],
  };
}

void main() {
  testWidgets(
    'shows loading until image-backed products arrive, then renders grid cards',
    (tester) async {
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        final exception = details.exception;
        if (exception is NetworkImageLoadException) {
          return;
        }
        originalOnError?.call(details);
      };
      addTearDown(() {
        FlutterError.onError = originalOnError;
      });

      final provider = _LikeTheseTestProvider();

      await tester.pumpWidget(
        ChangeNotifierProvider<ProjectProvider>.value(
          value: provider,
          child: const MaterialApp(
            home: LikeTheseScreen(itemType: 'replace headboard'),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(find.text('Live Headboard'), findsNothing);

      provider.debugSetSuggestionPayloads(
        productSuggestions: _imageBackedPayload(),
      );

      await tester.pump(const Duration(milliseconds: 600));
      await tester.pumpAndSettle(const Duration(milliseconds: 600));

      expect(find.text('Live Headboard'), findsOneWidget);
    },
  );

  group('_extractProductsFromPayload strict category matching', () {
    testWidgets(
      'does not fall back to another category when itemType does not match',
      (tester) async {
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (details) {
          if (details.exception is NetworkImageLoadException) return;
          originalOnError?.call(details);
        };
        addTearDown(() {
          FlutterError.onError = originalOnError;
        });

        final provider = _LikeTheseTestProvider();

        // itemType 'fancy ottoman' does NOT match category 'replace headboard'
        await tester.pumpWidget(
          ChangeNotifierProvider<ProjectProvider>.value(
            value: provider,
            child: const MaterialApp(
              home: LikeTheseScreen(itemType: 'fancy ottoman'),
            ),
          ),
        );

        expect(find.byType(CircularProgressIndicator), findsWidgets);

        provider.debugSetSuggestionPayloads(
          productSuggestions: _namedCategoryPayload(
            categoryName: 'replace headboard',
            productTitle: 'Fallback Chair',
          ),
        );

        await tester.pump(const Duration(milliseconds: 600));
        await tester.pumpAndSettle(const Duration(milliseconds: 600));

        // Strict matching should avoid cross-category fallback.
        expect(find.text('Fallback Chair'), findsNothing);
      },
    );

    testWidgets(
      'shows matched-category products when category matches itemType',
      (tester) async {
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (details) {
          if (details.exception is NetworkImageLoadException) return;
          originalOnError?.call(details);
        };
        addTearDown(() {
          FlutterError.onError = originalOnError;
        });

        final provider = _LikeTheseTestProvider();

        // itemType should match category recommendation after normalization.
        await tester.pumpWidget(
          ChangeNotifierProvider<ProjectProvider>.value(
            value: provider,
            child: const MaterialApp(
              home: LikeTheseScreen(itemType: 'replace headboard'),
            ),
          ),
        );

        expect(find.byType(CircularProgressIndicator), findsWidgets);

        provider.debugSetSuggestionPayloads(
          productSuggestions: _namedCategoryPayload(
            categoryName: 'replace headboard',
            productTitle: 'Matched Headboard',
          ),
        );

        await tester.pump(const Duration(milliseconds: 600));
        await tester.pumpAndSettle(const Duration(milliseconds: 600));

        // Primary matching path should find the product
        expect(find.text('Matched Headboard'), findsOneWidget);
      },
    );

    testWidgets(
      'waits for exact category when non-matching category arrives first',
      (tester) async {
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (details) {
          if (details.exception is NetworkImageLoadException) return;
          originalOnError?.call(details);
        };
        addTearDown(() {
          FlutterError.onError = originalOnError;
        });

        final provider = _LikeTheseTestProvider();

        await tester.pumpWidget(
          ChangeNotifierProvider<ProjectProvider>.value(
            value: provider,
            child: const MaterialApp(
              home: LikeTheseScreen(itemType: 'replace headboard'),
            ),
          ),
        );

        provider.debugSetSuggestionPayloads(
          productSuggestions: _namedCategoryPayload(
            categoryName: 'add area rug',
            productTitle: 'Wrong Rug',
          ),
        );

        await tester.pump(const Duration(milliseconds: 600));
        await tester.pump(const Duration(seconds: 2));

        expect(find.text('Wrong Rug'), findsNothing);

        provider.debugSetSuggestionPayloads(
          productSuggestions: _namedCategoryPayload(
            categoryName: 'replace headboard',
            productTitle: 'Matched Headboard',
          ),
        );

        await tester.pump(const Duration(milliseconds: 600));
        await tester.pump(const Duration(seconds: 2));
        await tester.pumpAndSettle(const Duration(milliseconds: 600));

        expect(find.text('Matched Headboard'), findsOneWidget);
      },
    );
  });
}
