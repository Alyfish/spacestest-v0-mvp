import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/models/project.dart';
import 'package:spaces/providers/project_provider.dart';

Project _dummyProject() {
  final now = DateTime(2026, 1, 1);
  return Project(
    id: 'project_test',
    userId: 'user_test',
    createdAt: now,
    updatedAt: now,
    status: 'ready',
  );
}

Map<String, dynamic> _imageBackedPayload() {
  return {
    'categories': [
      {
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

class _WarmupProbeProjectProvider extends ProjectProvider {
  int ensureSearchJobStartedCalls = 0;
  Completer<bool>? _searchInFlight;
  List<String>? lastSearchRecommendations;

  @override
  Future<bool> ensureRecommendationsLoaded(BuildContext? context) async {
    return true;
  }

  @override
  Future<bool> ensureSearchJobStarted(
    BuildContext? context,
    List<String> recommendations,
  ) {
    if (_searchInFlight != null && !_searchInFlight!.isCompleted) {
      return _searchInFlight!.future;
    }

    ensureSearchJobStartedCalls += 1;
    lastSearchRecommendations = List<String>.from(recommendations);
    _searchInFlight = Completer<bool>();
    Future<void>.delayed(const Duration(milliseconds: 40), () {
      if (!(_searchInFlight?.isCompleted ?? true)) {
        _searchInFlight!.complete(true);
      }
    });
    return _searchInFlight!.future;
  }

  @override
  Future<bool> preloadTrendingProducts([BuildContext? context]) async {
    return false;
  }

  @override
  Future<bool> refreshProductSuggestionsSnapshot([
    BuildContext? context,
  ]) async {
    return false;
  }
}

class _WaitSuccessProjectProvider extends ProjectProvider {
  int refreshCalls = 0;

  @override
  Future<bool> refreshProductSuggestionsSnapshot([
    BuildContext? context,
  ]) async {
    refreshCalls += 1;
    if (refreshCalls == 2) {
      debugSetSuggestionPayloads(productSuggestions: _imageBackedPayload());
      return true;
    }
    return false;
  }

  @override
  Future<bool> preloadTrendingProducts([BuildContext? context]) async {
    return false;
  }
}

class _WaitTimeoutProjectProvider extends ProjectProvider {
  int refreshCalls = 0;

  @override
  Future<bool> refreshProductSuggestionsSnapshot([
    BuildContext? context,
  ]) async {
    refreshCalls += 1;
    return false;
  }

  @override
  Future<bool> preloadTrendingProducts([BuildContext? context]) async {
    return false;
  }
}

void main() {
  group('ProjectProvider warmup and image-backed wait', () {
    test(
      'warmRecommendationsAndSearch dedupes in-flight search start',
      () async {
        final provider = _WarmupProbeProjectProvider();
        provider.debugSetCurrentProject(_dummyProject());
        provider.debugSetProductRecommendations(['replace headboard']);

        await provider.warmRecommendationsAndSearch();
        await provider.warmRecommendationsAndSearch();

        await Future<void>.delayed(const Duration(milliseconds: 80));
        expect(provider.ensureSearchJobStartedCalls, 1);
      },
    );

    test(
      'warmRecommendationsAndSearch passes only visible first two recommendations',
      () async {
        final provider = _WarmupProbeProjectProvider();
        provider.debugSetCurrentProject(_dummyProject());
        provider.debugSetProductRecommendations([
          'Update bedding set',
          'Add area rug',
          'Replace lamp',
        ]);

        await provider.warmRecommendationsAndSearch();
        await Future<void>.delayed(const Duration(milliseconds: 80));

        expect(provider.lastSearchRecommendations, <String>[
          'Update bedding set',
          'Add area rug',
        ]);
      },
    );

    test(
      'waitForImageBackedSuggestions returns true when payload appears',
      () async {
        final provider = _WaitSuccessProjectProvider();
        provider.debugSetCurrentProject(_dummyProject());

        final ready = await provider.waitForImageBackedSuggestions(
          timeout: const Duration(milliseconds: 240),
          pollInterval: const Duration(milliseconds: 20),
        );

        expect(ready, isTrue);
        expect(provider.hasImageBackedSuggestions, isTrue);
        expect(provider.refreshCalls, greaterThanOrEqualTo(2));
      },
    );

    test(
      'waitForImageBackedSuggestions times out when no payload arrives',
      () async {
        final provider = _WaitTimeoutProjectProvider();
        provider.debugSetCurrentProject(_dummyProject());

        final ready = await provider.waitForImageBackedSuggestions(
          timeout: const Duration(milliseconds: 120),
          pollInterval: const Duration(milliseconds: 20),
        );

        expect(ready, isFalse);
        expect(provider.refreshCalls, greaterThan(1));
      },
    );
  });
}
