import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' show min;
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../models/project.dart';
import '../models/marker.dart';
import '../models/shop_product.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../providers/user_provider.dart';
import '../utils/logger.dart';

enum ProjectStatus { idle, creating, loading, ready, uploading, error }

enum SearchFailureReason { none, jobFailed, networkError, timeout }

enum _RetryAction { resumePoll, restartJob, giveUp }

class ProjectProvider extends ChangeNotifier {
  /// Set to true to bypass all API calls and use mock data for UI testing
  static const bool demoMode = false;

  /// Feature flag: allows quick rollback to legacy top-4 hotspot behavior.
  static const bool enableBalancedAutoHotspotDensity = bool.fromEnvironment(
    'ENABLE_BALANCED_AUTO_HOTSPOT_DENSITY',
    defaultValue: true,
  );
  static const int dreamSpaceHotspotCount = 5;
  static const int dreamSpaceReadinessThreshold = 3;
  static const Duration dreamSpaceReadinessTimeout = Duration(seconds: 12);
  static const Duration rescuePrewarmPerHotspotTimeout = Duration(seconds: 18);
  static const Duration tapTimeFallbackTimeout = Duration(seconds: 25);
  static const Duration _rescueTotalTimeout = Duration(seconds: 60);
  static const int _rescueMaxConsecutiveFailures = 3;
  static const String dreamSpaceImageType = 'active';
  Project? _currentProject;
  ProjectStatus _status = ProjectStatus.idle;
  String? _errorMessage;
  bool _lastErrorTransient = false;
  final List<ImprovementMarker> _markers = [];
  final Uuid _uuid = const Uuid();

  // Room dimensions
  double? _roomWidth;
  double? _roomHeight;
  double? _roomLength;

  // Product recommendations from AI
  List<String> _productRecommendations = [];
  List<String> _selectedRecommendations = [];

  // Product suggestions from "Like These?" search
  Map<String, dynamic>? _productSuggestions;
  Map<String, dynamic>? _trendingProducts;

  // Generated image (from backend)
  Uint8List? _generatedImageBytes;
  String? _generatedImageUrl;
  DateTime? _imageUrlSetAt; // [REGEN_VERIFY] temp debug field

  // Background save error callback (for optimistic UI pattern)
  void Function(String errorMessage)? onBackgroundSaveError;

  // Job tracking
  String? _currentJobId;
  String? _lastCompletedJobId; // [REGEN_VERIFY] temp debug field
  String? _pendingSearchJobId;
  int _jobProgress = 0;
  String? _jobPhase;

  // Generation retry state
  Future<bool>? _generateDesignFuture; // concurrency guard
  bool _generationRetrying = false; // optional UX flag

  // Pre-warm generation state
  String? _prewarmFingerprint;
  bool _lastPrewarmReused = false;

  // Base image upload tracking
  Future<bool>? _projectImageUploadFuture;
  bool _isProjectImageUploading = false;
  bool _hasUploadedProjectImage = false;
  bool _preferredStoresDirty = false;

  // Search job lock (prevents duplicate search jobs)
  Completer<bool>? _searchJobCompleter;
  Completer<bool>? _recommendationsCompleter;
  Completer<bool>? _trendingPreloadCompleter;

  // Search failure reason (for UI differentiation)
  SearchFailureReason _searchFailureReason = SearchFailureReason.none;

  // Rescue / readiness-gate state
  int _dreamSpaceImageVersion = 0;

  // Furniture analysis results
  Map<String, dynamic>? _furnitureAnalysis;
  Map<String, dynamic>? _processedFurniture;
  List<ProductHotspot> _detectedHotspots = [];
  final Map<String, Map<String, dynamic>> _prefetchedFurnitureByHotspotId = {};
  Completer<bool>? _furniturePrefetchCompleter;
  final Map<String, Completer<bool>> _robustHotspotAnalysisCompleters = {};
  final Map<String, Completer<bool>> _rescueHotspotCompleters = {};
  final Set<String> _userTappedHotspots = {};

  // Getters
  Project? get currentProject => _currentProject;
  ProjectStatus get status => _status;
  String? get errorMessage => _errorMessage;
  bool get hasProject => _currentProject != null;
  bool get isLoading =>
      _status == ProjectStatus.loading || _status == ProjectStatus.creating;
  bool get hasProjectImage => _currentProject?.hasProjectImage ?? false;
  bool get hasInspirationImage => _currentProject?.hasInspirationImage ?? false;
  bool get hasMultipleInspirationImages =>
      _currentProject?.hasMultipleInspirationImages ?? false;
  List<File> get inspirationImages => _currentProject?.inspirationImages ?? [];
  List<ImprovementMarker> get markers => List.unmodifiable(_markers);
  bool get hasMarkers => _markers.isNotEmpty;
  double? get roomWidth => _roomWidth;
  double? get roomHeight => _roomHeight;
  double? get roomLength => _roomLength;
  bool get hasRoomDimensions =>
      _roomWidth != null && _roomHeight != null && _roomLength != null;
  List<String> get preferredStores => _currentProject?.preferredStores ?? [];
  String? get approach => _currentProject?.approach;
  String? get colorPalette =>
      _currentProject?.designPreferences['colorPalette'] as String?;
  String? get designStyle =>
      _currentProject?.designPreferences['designStyle'] as String?;

  // New getters for product/image flow
  List<String> get productRecommendations => _productRecommendations;
  List<String> get selectedRecommendations => _selectedRecommendations;
  Map<String, dynamic>? get productSuggestions => _productSuggestions;
  Map<String, dynamic>? get trendingProducts => _trendingProducts;
  Uint8List? get generatedImageBytes => _generatedImageBytes;
  String? get generatedImageUrl => _generatedImageUrl;
  String? get currentJobId => _currentJobId;
  String? get lastCompletedJobId => _lastCompletedJobId; // [REGEN_VERIFY]
  DateTime? get imageUrlSetAt => _imageUrlSetAt; // [REGEN_VERIFY]
  int get jobProgress => _jobProgress;
  String? get jobPhase => _jobPhase;
  bool get generationRetrying => _generationRetrying;
  bool get lastPrewarmReused => _lastPrewarmReused;
  bool get isRecommendationsLoading =>
      _recommendationsCompleter != null &&
      !_recommendationsCompleter!.isCompleted;
  bool get isSearchInFlight =>
      _searchJobCompleter != null && !_searchJobCompleter!.isCompleted;
  bool get isProjectImageUploading => _isProjectImageUploading;
  bool get hasUploadedProjectImage => _hasUploadedProjectImage;
  Map<String, dynamic>? get furnitureAnalysis => _furnitureAnalysis;
  Map<String, dynamic>? get processedFurniture => _processedFurniture;
  List<ProductHotspot> get detectedHotspots =>
      List<ProductHotspot>.unmodifiable(_detectedHotspots);
  Map<String, Map<String, dynamic>> get prefetchedFurnitureByHotspotId =>
      Map<String, Map<String, dynamic>>.unmodifiable(
        _prefetchedFurnitureByHotspotId,
      );
  bool get isFurniturePrefetching =>
      _furniturePrefetchCompleter != null &&
      !_furniturePrefetchCompleter!.isCompleted;
  String get dreamSpaceAnalysisImageType => dreamSpaceImageType;
  SearchFailureReason get searchFailureReason => _searchFailureReason;
  bool get hasImageBackedSuggestions =>
      _hasImageBackedPayload(_productSuggestions) ||
      _hasImageBackedPayload(_trendingProducts);

  int get readyHotspotCount =>
      _detectedHotspots.where((h) => hasProductsForHotspot(h.id)).length;

  int get _effectiveReadinessThreshold => _detectedHotspots.isEmpty
      ? 0
      : min(dreamSpaceReadinessThreshold, _detectedHotspots.length);

  bool get hotspotsReadyForDreamSpace =>
      _detectedHotspots.isEmpty ||
      readyHotspotCount >= _effectiveReadinessThreshold;

  void _setStatus(ProjectStatus status) {
    _status = status;
    notifyListeners();
  }

  /// Update the generated image URL, evicting the old URL from Flutter's
  /// image cache so stale images are never shown after regeneration.
  void _updateGeneratedImageUrl(String? newUrl) {
    if (_generatedImageUrl != null && _generatedImageUrl != newUrl) {
      imageCache.evict(NetworkImage(_generatedImageUrl!));
    }
    _generatedImageUrl = newUrl;
    if (newUrl != null) {
      _imageUrlSetAt = DateTime.now(); // [REGEN_VERIFY]
    }
  }

  void _setError(String error, {bool transient = false}) {
    _errorMessage = error;
    _lastErrorTransient = transient;
    _setStatus(ProjectStatus.error);
  }

  void clearError() {
    _errorMessage = null;
    _lastErrorTransient = false;
    if (_status == ProjectStatus.error) {
      _setStatus(
        _currentProject != null ? ProjectStatus.ready : ProjectStatus.idle,
      );
    }
  }

  void _safeNotifyListeners() {
    try {
      final phase = SchedulerBinding.instance.schedulerPhase;
      if (phase == SchedulerPhase.persistentCallbacks ||
          phase == SchedulerPhase.midFrameMicrotasks) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          try {
            notifyListeners();
          } catch (_) {}
        });
      } else {
        notifyListeners();
      }
    } catch (_) {}
  }

  String? _resolveAuthToken([BuildContext? context]) {
    final sessionToken = SupabaseService.accessToken;
    if (sessionToken != null && sessionToken.isNotEmpty) {
      return sessionToken;
    }
    if (context == null) return null;
    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final token = userProvider.user.token;
      if (token != null && token.isNotEmpty) return token;
    } catch (e) {
      AppLogger.warning('Context lookup failed (detached widget/background): $e');
    }
    return null;
  }

  String _buildSearchIdempotencyKey(List<String> recommendations) {
    final normalized =
        recommendations
            .map((r) => r.trim().toLowerCase())
            .where((r) => r.isNotEmpty)
            .toSet()
            .toList()
          ..sort();
    final compact = normalized
        .join('_')
        .replaceAll(RegExp(r'[^a-z0-9_]+'), '_');
    final suffix = compact.isEmpty
        ? 'default'
        : (compact.length > 80 ? compact.substring(0, 80) : compact);
    return '${_currentProject!.id}_search_$suffix';
  }

  List<String> _visibleLikeTheseRecommendations() {
    final visible = <String>[];
    final seen = <String>{};
    for (final raw in _productRecommendations) {
      final trimmed = raw.trim();
      if (trimmed.isEmpty) continue;
      final normalized = trimmed.toLowerCase();
      if (!seen.add(normalized)) continue;
      visible.add(trimmed);
      if (visible.length == 2) break;
    }
    return visible;
  }

  bool _hasTrendingPayload(Map<String, dynamic>? payload) {
    if (payload == null) return false;

    final categories = payload['categories'] as List? ?? const [];
    for (final raw in categories) {
      if (raw is! Map) continue;
      final products = raw['products'] as List? ?? const [];
      if (products.isNotEmpty) return true;
    }

    final selectedProducts = payload['selected_products'] as List? ?? const [];
    if (selectedProducts.isNotEmpty) return true;

    final favoriteProducts = payload['favorite_products'] as List? ?? const [];
    return favoriteProducts.isNotEmpty;
  }

  bool _hasImageBackedPayload(Map<String, dynamic>? payload) {
    if (payload == null) return false;

    final categories = payload['categories'] as List? ?? const [];
    for (final raw in categories) {
      if (raw is! Map) continue;
      if (_containsImageBackedProducts(raw['products'])) {
        return true;
      }
    }

    if (_containsImageBackedProducts(payload['selected_products'])) {
      return true;
    }
    if (_containsImageBackedProducts(payload['favorite_products'])) {
      return true;
    }
    return false;
  }

  bool _containsImageBackedProducts(dynamic rawProducts) {
    if (rawProducts is! List) return false;
    for (final raw in rawProducts) {
      if (raw is! Map) continue;
      final imageUrl =
          (raw['image_url'] ??
                  raw['imageUrl'] ??
                  raw['thumbnail'] ??
                  raw['image'])
              ?.toString()
              .trim() ??
          '';
      if (imageUrl.isNotEmpty) {
        return true;
      }
    }
    return false;
  }

  bool _responseHasBaseImage(Map<String, dynamic> response) {
    final context = response['context'] as Map<String, dynamic>?;
    final baseImage = context?['base_image'];
    return baseImage != null && baseImage.toString().trim().isNotEmpty;
  }

  List<dynamic> _extractSelectionResults(Map<String, dynamic> analysis) {
    final raw =
        analysis['selections'] ??
        analysis['results'] ??
        analysis['items'] ??
        (analysis['data'] is Map<String, dynamic>
            ? (analysis['data'] as Map<String, dynamic>)['selections']
            : null);
    if (raw is List) return raw;
    return const [];
  }

  bool _looksLikeFurnitureLabel(String label) {
    final lower = label.toLowerCase();
    const keywords = <String>[
      'sofa',
      'couch',
      'chair',
      'table',
      'desk',
      'bed',
      'dresser',
      'nightstand',
      'cabinet',
      'shelf',
      'lamp',
      'stool',
      'bench',
      'ottoman',
      'armoire',
      'bookcase',
      'rug',
      'mirror',
      'headboard',
      'furniture',
    ];
    return keywords.any((keyword) => lower.contains(keyword));
  }

  Map<String, double>? _extractDetectionRect(dynamic raw) {
    if (raw is! Map) return null;
    final rectRaw = raw['rect'];
    if (rectRaw is Map) {
      final x = (rectRaw['x'] as num?)?.toDouble();
      final y = (rectRaw['y'] as num?)?.toDouble();
      final width = (rectRaw['width'] as num?)?.toDouble();
      final height = (rectRaw['height'] as num?)?.toDouble();
      if (x != null && y != null && width != null && height != null) {
        return {'x': x, 'y': y, 'width': width, 'height': height};
      }
    }

    final bboxRaw = raw['bbox'];
    if (bboxRaw is Map) {
      final x1 = (bboxRaw['x1'] as num?)?.toDouble();
      final y1 = (bboxRaw['y1'] as num?)?.toDouble();
      final x2 = (bboxRaw['x2'] as num?)?.toDouble();
      final y2 = (bboxRaw['y2'] as num?)?.toDouble();
      if (x1 != null && y1 != null && x2 != null && y2 != null) {
        return {'x': x1, 'y': y1, 'width': (x2 - x1), 'height': (y2 - y1)};
      }
    }

    if (bboxRaw is List && bboxRaw.length == 4) {
      final ymin = (bboxRaw[0] as num?)?.toDouble();
      final xmin = (bboxRaw[1] as num?)?.toDouble();
      final ymax = (bboxRaw[2] as num?)?.toDouble();
      final xmax = (bboxRaw[3] as num?)?.toDouble();
      if (ymin != null && xmin != null && ymax != null && xmax != null) {
        return {
          'x': xmin,
          'y': ymin,
          'width': (xmax - xmin),
          'height': (ymax - ymin),
        };
      }
    }
    return null;
  }

  void _appendFallbackHotspotAnchors(
    List<Map<String, dynamic>> selectedDetections,
  ) {
    const anchors = <Map<String, double>>[
      {'x': 0.20, 'y': 0.30},
      {'x': 0.50, 'y': 0.28},
      {'x': 0.80, 'y': 0.30},
      {'x': 0.26, 'y': 0.58},
      {'x': 0.50, 'y': 0.56},
      {'x': 0.74, 'y': 0.58},
      {'x': 0.34, 'y': 0.80},
      {'x': 0.66, 'y': 0.80},
    ];
    for (final anchor in anchors) {
      if (selectedDetections.length >= dreamSpaceHotspotCount) {
        break;
      }
      final candidate = <String, dynamic>{
        'x': anchor['x']!,
        'y': anchor['y']!,
        'label': 'Furniture',
        'area': 0.02,
        'confidence': 0.2,
        'score': 0.0,
        'source': 'synthetic_anchor',
      };
      if (_isHotspotCandidateFarEnough(
        candidate,
        selectedDetections,
        minDistance: 0.06,
      )) {
        selectedDetections.add(candidate);
      }
    }

    // If spacing constraints are still too strict, fill remaining slots
    // deterministically so Dream Space always has 5 tappable markers.
    for (final anchor in anchors) {
      if (selectedDetections.length >= dreamSpaceHotspotCount) {
        break;
      }
      final candidate = <String, dynamic>{
        'x': anchor['x']!,
        'y': anchor['y']!,
        'label': 'Furniture',
        'area': 0.02,
        'confidence': 0.2,
        'score': 0.0,
        'source': 'synthetic_anchor',
      };
      final existsNearby = selectedDetections.any((item) {
        final dx = (item['x'] as double) - (candidate['x'] as double);
        final dy = (item['y'] as double) - (candidate['y'] as double);
        return (dx * dx) + (dy * dy) < 0.0004;
      });
      if (!existsNearby) {
        selectedDetections.add(candidate);
      }
    }
  }

  bool _isHotspotCandidateFarEnough(
    Map<String, dynamic> candidate,
    List<Map<String, dynamic>> selected, {
    double minDistance = 0.06,
  }) {
    final x = candidate['x'] as double;
    final y = candidate['y'] as double;
    for (final item in selected) {
      final sx = item['x'] as double;
      final sy = item['y'] as double;
      final distance = ((x - sx) * (x - sx) + (y - sy) * (y - sy)) * 1.0;
      if (distance < (minDistance * minDistance)) {
        return false;
      }
    }
    return true;
  }

  Map<String, dynamic>? getPrefetchedFurnitureForHotspot(String hotspotId) {
    final item = _prefetchedFurnitureByHotspotId[hotspotId];
    if (item == null) return null;
    return Map<String, dynamic>.from(item);
  }

  bool _selectionHasProducts(Map<String, dynamic>? selection) {
    if (selection == null) return false;

    final products = selection['products'];
    if (products is List && products.any((p) => p is Map<String, dynamic>))
      return true;

    final bedComponents = selection['bed_components'];
    if (bedComponents is Map) {
      for (final rawProducts in bedComponents.values) {
        if (rawProducts is List &&
            rawProducts.any((p) => p is Map<String, dynamic>)) {
          return true;
        }
      }
    }
    return false;
  }

  bool hasProductsForHotspot(String hotspotId) {
    return _selectionHasProducts(_prefetchedFurnitureByHotspotId[hotspotId]);
  }

  void _seedHotspotCachePlaceholders(List<ProductHotspot> hotspots) {
    for (final hotspot in hotspots) {
      _prefetchedFurnitureByHotspotId.putIfAbsent(hotspot.id, () {
        return {
          'id': hotspot.id,
          'label': hotspot.label,
          'furniture_type': hotspot.label,
          'products': <Map<String, dynamic>>[],
          'x': hotspot.x,
          'y': hotspot.y,
        };
      });
    }
  }

  @visibleForTesting
  Future<Map<String, dynamic>> autoDetectFurnitureForPrefetch(
    String projectId,
    String authToken, {
    required String imageType,
  }) {
    return ApiService.autoDetectFurniture(
      projectId,
      authToken,
      imageType: imageType,
    );
  }

  Future<Map<String, dynamic>> _analyzeFurnitureBatchResilient(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selections, {
    required String imageType,
    required String mode,
    required Duration timeout,
    required String logContext,
    int maxAttempts = 2,
  }) async {
    Object? lastError;
    final attempts = maxAttempts < 1 ? 1 : maxAttempts;

    for (var attempt = 1; attempt <= attempts; attempt++) {
      try {
        if (attempt > 1) {
          AppLogger.info(
            '$logContext retry attempt $attempt/$attempts '
            '(mode=$mode, imageType=$imageType)',
          );
        }
        return await ApiService.analyzeFurnitureBatch(
          projectId,
          authToken,
          selections,
          imageType: imageType,
          mode: mode,
          timeout: timeout,
        );
      } catch (e) {
        lastError = e;
        final transient = _isTransientFurnitureAnalysisError(e);
        final isFinalAttempt = attempt >= attempts;
        if (!transient || isFinalAttempt) {
          rethrow;
        }

        final backoffMs = min(800 * (1 << (attempt - 1)), 2400);
        AppLogger.warning(
          '$logContext transient failure on attempt $attempt/$attempts; '
          'retrying in ${backoffMs}ms: $e',
        );
        await Future.delayed(Duration(milliseconds: backoffMs));
      }
    }

    throw lastError ?? Exception('$logContext failed');
  }

  bool _isTransientFurnitureAnalysisError(Object error) {
    if (_isTransientException(error)) return true;
    final message = error.toString().toLowerCase();
    return message.contains('failed to analyze furniture: 500') ||
        message.contains('failed to analyze furniture: 502') ||
        message.contains('failed to analyze furniture: 503') ||
        message.contains('failed to analyze furniture: 504') ||
        message.contains('http_error') ||
        message.contains('connection reset') ||
        message.contains('connection aborted');
  }

  @visibleForTesting
  Future<Map<String, dynamic>> analyzeFurnitureBatchForPrefetch(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selections, {
    required String imageType,
    Duration timeout = const Duration(seconds: 45),
    int maxAttempts = 2,
  }) {
    return _analyzeFurnitureBatchResilient(
      projectId,
      authToken,
      selections,
      imageType: imageType,
      mode: 'fast_prefetch',
      timeout: timeout,
      maxAttempts: maxAttempts,
      logContext: '[HotspotPrefetch]',
    );
  }

  @visibleForTesting
  Future<Map<String, dynamic>> analyzeFurnitureBatchForHotspotRobust(
    String projectId,
    String authToken,
    Map<String, dynamic> selection, {
    required String imageType,
    Duration? timeout,
    int maxAttempts = 2,
  }) {
    return _analyzeFurnitureBatchResilient(
      projectId,
      authToken,
      [selection],
      imageType: imageType,
      mode: 'full',
      timeout: timeout ?? tapTimeFallbackTimeout,
      maxAttempts: maxAttempts,
      logContext: '[HotspotTap]',
    );
  }

  Future<bool> preloadTrendingProducts([BuildContext? context]) async {
    if (_currentProject == null) return false;

    if (_hasTrendingPayload(_trendingProducts)) {
      return true;
    }

    if (_trendingPreloadCompleter != null &&
        !_trendingPreloadCompleter!.isCompleted) {
      AppLogger.info('Trending preload already in-flight — waiting');
      return _trendingPreloadCompleter!.future;
    }

    _trendingPreloadCompleter = Completer<bool>();

    final authToken = _resolveAuthToken(context);
    if (authToken == null) {
      AppLogger.warning('Skipping trending preload: auth token unavailable');
      _trendingPreloadCompleter!.complete(false);
      _trendingPreloadCompleter = null;
      return false;
    }

    try {
      Map<String, dynamic> data;
      try {
        data = await ApiService.getTrendingProducts(
          _currentProject!.id,
          authToken,
          timeout: const Duration(seconds: 8),
        );
      } on TimeoutException {
        // First pass keeps UI responsive. A single follow-up attempt reduces
        // placeholder persistence on slower connections/cold backends.
        AppLogger.warning(
          'Trending preload timed out at 8s, retrying once with 16s timeout',
        );
        data = await ApiService.getTrendingProducts(
          _currentProject!.id,
          authToken,
          timeout: const Duration(seconds: 16),
        );
      }
      _trendingProducts = data;

      final hasAnyProducts = _hasTrendingPayload(data);
      if (hasAnyProducts) {
        notifyListeners();
      }
      _trendingPreloadCompleter!.complete(hasAnyProducts);
      return hasAnyProducts;
    } catch (e) {
      AppLogger.warning('Trending preload failed (non-fatal): $e');
      if (!_trendingPreloadCompleter!.isCompleted) {
        _trendingPreloadCompleter!.complete(false);
      }
      return false;
    } finally {
      _trendingPreloadCompleter = null;
    }
  }

  Future<bool> _tryHydrateProductSuggestions(String authToken) async {
    if (_currentProject == null) return false;
    try {
      final suggestions = await ApiService.getProductSuggestions(
        _currentProject!.id,
        authToken,
      );
      final categories = suggestions['categories'] as List? ?? const [];
      if (categories.isNotEmpty) {
        _productSuggestions = suggestions;
        notifyListeners();
        AppLogger.info(
          'Recovered ${categories.length} product suggestion categories after degraded search flow',
        );
        return true;
      }
      return false;
    } catch (e) {
      AppLogger.warning('Product suggestions hydration failed: $e');
      return false;
    }
  }

  /// Lightweight fetch for "Like These?" screen while job is still running.
  /// Returns true as soon as at least one category is available.
  Future<bool> refreshProductSuggestionsSnapshot([
    BuildContext? context,
  ]) async {
    if (_currentProject == null) return false;
    final authToken = _resolveAuthToken(context);
    if (authToken == null) return false;
    return _tryHydrateProductSuggestions(authToken);
  }

  /// Starts recommendation/search warmup in background.
  /// Safe to call repeatedly; search startup remains single-flight.
  Future<bool> warmRecommendationsAndSearch([BuildContext? context]) async {
    if (_currentProject == null) return false;

    if (_productRecommendations.isEmpty) {
      final inFlightRecommendations = _recommendationsCompleter;
      if (isRecommendationsLoading && inFlightRecommendations != null) {
        unawaited(() async {
          try {
            final ready = await inFlightRecommendations.future;
            final searchRecommendations = _visibleLikeTheseRecommendations();
            if (!ready || searchRecommendations.isEmpty) return;
            await ensureSearchJobStarted(context, searchRecommendations);
          } catch (e) {
            AppLogger.warning('Deferred warmup search failed: $e');
          } finally {
            unawaited(preloadTrendingProducts(context));
          }
        }());
        unawaited(preloadTrendingProducts(context));
        return true;
      }

      final recommendationsReady = await ensureRecommendationsLoaded(context);
      if (!recommendationsReady) return false;
    }

    if (_productRecommendations.isEmpty) {
      unawaited(preloadTrendingProducts(context));
      return true;
    }

    unawaited(() async {
      try {
        final searchRecommendations = _visibleLikeTheseRecommendations();
        if (searchRecommendations.isEmpty) return;
        await ensureSearchJobStarted(context, searchRecommendations);
      } catch (e) {
        AppLogger.warning('Warmup search failed: $e');
      }
    }());
    unawaited(preloadTrendingProducts(context));
    return true;
  }

  /// Polls for live suggestions that include at least one image-backed product.
  Future<bool> waitForImageBackedSuggestions({
    BuildContext? context,
    Duration timeout = const Duration(seconds: 6),
    Duration pollInterval = const Duration(milliseconds: 500),
  }) async {
    if (_currentProject == null) return false;
    if (hasImageBackedSuggestions) return true;

    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      await refreshProductSuggestionsSnapshot(context);
      if (hasImageBackedSuggestions) return true;

      unawaited(preloadTrendingProducts(context));

      final remaining = deadline.difference(DateTime.now());
      if (remaining <= Duration.zero) break;
      await Future.delayed(remaining < pollInterval ? remaining : pollInterval);
    }

    await refreshProductSuggestionsSnapshot(context);
    return hasImageBackedSuggestions;
  }

  @visibleForTesting
  void debugSetCurrentProject(Project? project) {
    _currentProject = project;
  }

  @visibleForTesting
  void debugSetProductRecommendations(List<String> recommendations) {
    _productRecommendations = List<String>.from(recommendations);
  }

  @visibleForTesting
  void debugSetCompleters({
    Completer<bool>? recommendationsCompleter,
    Completer<bool>? searchJobCompleter,
  }) {
    _recommendationsCompleter = recommendationsCompleter;
    _searchJobCompleter = searchJobCompleter;
  }

  @visibleForTesting
  void debugSetSuggestionPayloads({
    Map<String, dynamic>? productSuggestions,
    Map<String, dynamic>? trendingProducts,
  }) {
    _productSuggestions = productSuggestions;
    _trendingProducts = trendingProducts;
    notifyListeners();
  }

  @visibleForTesting
  void debugSetFurniturePrefetchData({
    List<ProductHotspot>? hotspots,
    Map<String, Map<String, dynamic>>? prefetchedByHotspotId,
  }) {
    if (hotspots != null) {
      _detectedHotspots = List<ProductHotspot>.from(hotspots);
    }
    if (prefetchedByHotspotId != null) {
      _prefetchedFurnitureByHotspotId
        ..clear()
        ..addAll(prefetchedByHotspotId);
    }
    notifyListeners();
  }

  @visibleForTesting
  void debugSetGeneratedImageBytes(Uint8List? bytes) {
    _generatedImageBytes = bytes;
    notifyListeners();
  }

  @visibleForTesting
  void debugResetHotspotPrefetchState() {
    _resetHotspotPrefetchStateForNewImage();
  }

  @visibleForTesting
  int get currentDreamSpaceImageVersion => _dreamSpaceImageVersion;

  @visibleForTesting
  Future<void> testRunConcurrentRescue({
    required List<ProductHotspot> emptyHotspots,
    required String authToken,
    required int version,
    VoidCallback? onEachComplete,
  }) {
    return _runConcurrentRescue(
      emptyHotspots: emptyHotspots,
      authToken: authToken,
      version: version,
      onEachComplete: onEachComplete,
    );
  }

  // Create a new project
  Future<bool> createProject(BuildContext context) async {
    try {
      _setStatus(ProjectStatus.creating);
      _errorMessage = null;

      // Demo mode: Create a mock project without API call
      if (demoMode) {
        AppLogger.info('DEMO MODE: Creating mock project...');
        await Future.delayed(const Duration(milliseconds: 500));
        _currentProject = Project(
          id: 'demo-${DateTime.now().millisecondsSinceEpoch}',
          userId: 'demo-user',
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
          status: 'created',
        );
        _hasUploadedProjectImage = false;
        _projectImageUploadFuture = null;
        _isProjectImageUploading = false;
        _preferredStoresDirty = false;
        _pendingSearchJobId = null;
        _setStatus(ProjectStatus.ready);
        AppLogger.info(
          'DEMO MODE: Mock project created: ${_currentProject!.id}',
        );
        return true;
      }

      final userProvider = Provider.of<UserProvider>(context, listen: false);

      if (!userProvider.isSignedIn) {
        _setError('User must be signed in to create a project');
        return false;
      }

      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Creating new project...');
      final response = await ApiService.createProject(authToken);

      AppLogger.info(
        'createProject: response keys=${response.keys.toList()}, project_id=${response["project_id"]}',
      );
      clearProject(); // Wipe all cached flow state from prior project
      _currentProject = Project.fromJson(response);
      _hasUploadedProjectImage = _responseHasBaseImage(response);
      _projectImageUploadFuture = null;
      _isProjectImageUploading = false;
      _preferredStoresDirty = false;
      _pendingSearchJobId = null;
      _setStatus(ProjectStatus.ready);

      if (_currentProject!.id.isEmpty) {
        AppLogger.error(
          'createProject: project created but parsed ID is empty! Response: $response',
        );
        _setError('Project created but ID is missing');
        return false;
      }
      AppLogger.info('createProject: parsed project id=${_currentProject!.id}');
      return true;
    } on PaywallRequiredException catch (e) {
      AppLogger.info('Create project blocked by paywall: ${e.code}');
      _setError(e.message);
      _setStatus(ProjectStatus.idle);
      rethrow;
    } catch (e) {
      AppLogger.error('Failed to create project', e);
      _setError('Failed to create project: ${e.toString()}');
      return false;
    }
  }

  // Load an existing project
  Future<bool> loadProject(String projectId, BuildContext context) async {
    try {
      _setStatus(ProjectStatus.loading);
      _errorMessage = null;

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Loading project: $projectId');
      final response = await ApiService.getProject(projectId, authToken);

      _currentProject = Project.fromJson(response);
      _hasUploadedProjectImage = _responseHasBaseImage(response);
      _projectImageUploadFuture = null;
      _isProjectImageUploading = false;
      _preferredStoresDirty = false;
      _pendingSearchJobId = null;

      // Clear stale hotspot/product caches from previous project
      _resetHotspotPrefetchStateForNewImage();
      _processedFurniture = null;

      // Extract generated image URL from context so DreamSpace can render immediately
      final ctx = response['context'] as Map<String, dynamic>?;
      final inspRef = ctx?['inspiration_generated_image_base64'] as String?;
      final genRef = ctx?['generated_image_base64'] as String?;
      final ref = inspRef ?? genRef;
      _generatedImageUrl = (ref != null && ref.startsWith('http')) ? ref : null;

      _setStatus(ProjectStatus.ready);

      AppLogger.info('Project loaded successfully');
      return true;
    } catch (e) {
      AppLogger.error('Failed to load project', e);
      _setError('Failed to load project: ${e.toString()}');
      return false;
    }
  }

  // Set project image (local file). Returns false if no active project or file missing.
  bool setProjectImage(File imageFile) {
    if (_currentProject == null || _currentProject!.id.isEmpty) {
      AppLogger.error(
        'setProjectImage FAILED: no active project (currentProject=${_currentProject?.id})',
      );
      return false;
    }
    if (!imageFile.existsSync()) {
      AppLogger.error(
        'setProjectImage FAILED: file does not exist: ${imageFile.path}',
      );
      return false;
    }

    _currentProject = _currentProject!.copyWith(
      localProjectImage: imageFile,
      updatedAt: DateTime.now(),
    );
    _hasUploadedProjectImage = false;
    _projectImageUploadFuture = null;
    _isProjectImageUploading = false;

    AppLogger.info(
      'Project image set: project_id=${_currentProject!.id}, path=${imageFile.path}',
    );
    notifyListeners();
    return true;
  }

  Future<void> setInspirationImages(List<File> imageFiles) async {
    if (_currentProject == null) {
      AppLogger.warning('No active project to set inspiration images for');
      return;
    }

    _currentProject = _currentProject!.copyWith(
      localInspirationImages: imageFiles,
      updatedAt: DateTime.now(),
    );

    AppLogger.info('${imageFiles.length} inspiration images set locally');
    notifyListeners();
  }

  Future<void> addInspirationImages(List<File> imageFiles) async {
    if (_currentProject == null) {
      AppLogger.warning('No active project to add inspiration images to');
      return;
    }

    final currentImages = _currentProject!.inspirationImages;
    final updatedImages = [...currentImages, ...imageFiles];

    _currentProject = _currentProject!.copyWith(
      localInspirationImages: updatedImages,
      updatedAt: DateTime.now(),
    );

    AppLogger.info(
      'Added ${imageFiles.length} inspiration images (total: ${updatedImages.length})',
    );
    notifyListeners();
  }

  void clearInspirationImages() {
    if (_currentProject == null) {
      AppLogger.warning('No active project to clear inspiration images from');
      return;
    }

    _currentProject = _currentProject!.copyWith(
      localInspirationImages: [],
      updatedAt: DateTime.now(),
    );

    AppLogger.info('Cleared all inspiration images');
    notifyListeners();
  }

  // Set chosen space type
  void setSpaceChosen(String spaceType) {
    if (_currentProject == null) {
      AppLogger.warning('No active project to set space type for');
      return;
    }

    _currentProject = _currentProject!.copyWith(
      spaceChosen: spaceType,
      updatedAt: DateTime.now(),
    );

    AppLogger.info('Space type set to: $spaceType');
    notifyListeners();
  }

  /// Save space type to backend and update local state
  Future<bool> saveSpaceType(BuildContext context, String spaceType) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      await ApiService.submitSpaceType(
        _currentProject!.id,
        authToken,
        spaceType,
      );

      _currentProject = _currentProject!.copyWith(
        spaceChosen: spaceType,
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save space type', e);
      _setError('Failed to save space type: ${e.toString()}');
      return false;
    }
  }

  // Set custom space description
  void setCustomSpaceDescription(String description) {
    if (_currentProject == null) {
      AppLogger.warning(
        'No active project to set custom space description for',
      );
      return;
    }

    _currentProject = _currentProject!.copyWith(
      customSpaceDescription: description,
      updatedAt: DateTime.now(),
    );

    AppLogger.info('Custom space description set');
    notifyListeners();
  }

  // Upload project image in background-safe mode with de-duplication.
  Future<bool> startProjectImageUpload(
    BuildContext context, {
    bool forceRestart = false,
  }) {
    return _runProjectImageUpload(context, forceRestart: forceRestart);
  }

  // Ensure base image upload is complete before continuing deeper in the flow.
  Future<bool> ensureProjectImageUploaded(BuildContext context) {
    return _runProjectImageUpload(context);
  }

  // Backwards-compatible upload entrypoint.
  Future<bool> uploadProjectImage(BuildContext context) {
    return _runProjectImageUpload(context);
  }

  Future<bool> _runProjectImageUpload(
    BuildContext context, {
    bool forceRestart = false,
  }) {
    if (!forceRestart && _hasUploadedProjectImage) {
      return Future.value(true);
    }
    if (!forceRestart && _projectImageUploadFuture != null) {
      return _projectImageUploadFuture!;
    }

    final uploadFuture = _performProjectImageUpload(context);
    _projectImageUploadFuture = uploadFuture;
    _isProjectImageUploading = true;
    notifyListeners();

    uploadFuture.whenComplete(() {
      if (!identical(_projectImageUploadFuture, uploadFuture)) return;
      _projectImageUploadFuture = null;
      _isProjectImageUploading = false;
      notifyListeners();
    });

    return uploadFuture;
  }

  Future<bool> _performProjectImageUpload(BuildContext context) async {
    if (_currentProject?.localProjectImage == null) {
      _hasUploadedProjectImage = false;
      _setError('No project image to upload');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      // Demo mode: Skip actual upload
      if (demoMode) {
        AppLogger.info('DEMO MODE: Simulating image upload...');
        await Future.delayed(const Duration(milliseconds: 800));
        _currentProject = _currentProject!.copyWith(updatedAt: DateTime.now());
        _hasUploadedProjectImage = true;
        _setStatus(ProjectStatus.ready);
        AppLogger.info('DEMO MODE: Image upload simulated successfully');
        return true;
      }

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _hasUploadedProjectImage = false;
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Uploading project image...');
      final success = await ApiService.uploadProjectImage(
        _currentProject!.id,
        authToken,
        _currentProject!.localProjectImage!,
        isInspiration: false,
      );

      if (success) {
        _currentProject = _currentProject!.copyWith(updatedAt: DateTime.now());
        _hasUploadedProjectImage = true;
        _setStatus(ProjectStatus.ready);
        AppLogger.info('Project image uploaded successfully');
        return true;
      } else {
        _hasUploadedProjectImage = false;
        _setError('Failed to upload project image');
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to upload project image', e);
      _hasUploadedProjectImage = false;
      _setError('Failed to upload project image: ${e.toString()}');
      return false;
    }
  }

  // Update project properties
  Future<bool> updateProject(
    BuildContext context,
    Map<String, dynamic> updates,
  ) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Updating project properties...');
      final response = await ApiService.updateProject(
        _currentProject!.id,
        authToken,
        updates,
      );

      _currentProject = Project.fromJson(response);
      _setStatus(ProjectStatus.ready);

      AppLogger.info('Project updated successfully');
      return true;
    } catch (e) {
      AppLogger.error('Failed to update project', e);
      _setError('Failed to update project: ${e.toString()}');
      return false;
    }
  }

  /// Save chosen approach (iterative / complete_revamp)
  Future<bool> saveApproach(BuildContext context, String approach) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      await ApiService.submitApproach(_currentProject!.id, authToken, approach);

      _currentProject = _currentProject!.copyWith(
        approach: approach,
        designPreferences: {
          ..._currentProject!.designPreferences,
          'approach': approach,
        },
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save approach', e);
      _setError('Failed to save approach: ${e.toString()}');
      return false;
    }
  }

  /// Save preferred stores selection (sends store names to backend)
  Future<bool> savePreferredStores(
    BuildContext context,
    List<String> storeNames,
  ) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      await ApiService.submitPreferredStores(
        _currentProject!.id,
        authToken,
        storeNames,
      );

      _currentProject = _currentProject!.copyWith(
        preferredStores: storeNames,
        designPreferences: {
          ..._currentProject!.designPreferences,
          'preferredStores': storeNames,
        },
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      _preferredStoresDirty = false;
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save preferred stores', e);
      _setError('Failed to save preferred stores: ${e.toString()}');
      return false;
    }
  }

  /// Stage preferred stores locally for optimistic navigation.
  void setPreferredStoresLocal(List<String> storeNames) {
    if (_currentProject == null) {
      _setError('No active project to update');
      return;
    }

    final normalizedStores = storeNames
        .map((name) => name.trim())
        .where((name) => name.isNotEmpty)
        .toSet()
        .toList();

    _currentProject = _currentProject!.copyWith(
      preferredStores: normalizedStores,
      designPreferences: {
        ..._currentProject!.designPreferences,
        'preferredStores': normalizedStores,
      },
      updatedAt: DateTime.now(),
    );
    _preferredStoresDirty = true;
    notifyListeners();
  }

  /// Ensure any staged preferred stores are synced before downstream work.
  Future<bool> ensurePreferredStoresSynced(BuildContext context) async {
    if (!_preferredStoresDirty) {
      return true;
    }
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }
    return savePreferredStores(
      context,
      List<String>.from(_currentProject!.preferredStores),
    );
  }

  void clearColorPalette() {
    _currentProject?.designPreferences.remove('colorPalette');
    notifyListeners();
  }

  void clearDesignStyle() {
    _currentProject?.designPreferences.remove('designStyle');
    notifyListeners();
  }

  /// Save color palette selection (triggers AI color analysis on backend)
  Future<bool> saveColorPalette(
    BuildContext context,
    String paletteId,
    String paletteName,
    List<String> colorHexCodes, {
    bool background = false,
    bool letAiDecide = false,
  }) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final authToken = userProvider.user.token;

    if (authToken == null) {
      _setError('Authentication token not available');
      return false;
    }

    // Save locally immediately
    _currentProject = _currentProject!.copyWith(
      designPreferences: {
        ..._currentProject!.designPreferences,
        'colorPalette': paletteId,
      },
      updatedAt: DateTime.now(),
    );
    notifyListeners();

    if (background) {
      // Fire-and-forget API call with auto-retry
      _syncColorPaletteToBackend(
        _currentProject!.id,
        authToken,
        paletteName,
        colorHexCodes,
        letAiDecide: letAiDecide,
      );
      return true;
    }

    try {
      _setStatus(ProjectStatus.uploading);
      await ApiService.submitColorPalette(
        _currentProject!.id,
        authToken,
        paletteName,
        colorHexCodes,
        letAiDecide: letAiDecide,
      );
      _setStatus(ProjectStatus.ready);
      return true;
    } catch (e) {
      AppLogger.error('Failed to save color palette', e);
      _setError('Failed to save color palette: ${e.toString()}');
      return false;
    }
  }

  Future<void> _syncColorPaletteToBackend(
    String projectId,
    String authToken,
    String paletteName,
    List<String> colorHexCodes, {
    bool letAiDecide = false,
  }) async {
    for (int attempt = 0; attempt < 2; attempt++) {
      try {
        await ApiService.submitColorPalette(
          projectId,
          authToken,
          paletteName,
          colorHexCodes,
          letAiDecide: letAiDecide,
        );
        AppLogger.info('Color palette synced to backend');
        return;
      } catch (e) {
        AppLogger.error(
          'Background color palette save failed (attempt ${attempt + 1})',
          e,
        );
        if (attempt == 0) {
          await Future.delayed(const Duration(seconds: 2));
        }
      }
    }
    // Both attempts failed — notify via callback
    onBackgroundSaveError?.call(
      "Couldn't save color palette — please try again",
    );
  }

  /// Save design style selection (triggers AI style analysis on backend)
  Future<bool> saveDesignStyle(
    BuildContext context,
    String styleId,
    String styleName, {
    bool background = false,
    bool letAiDecide = false,
  }) async {
    if (_currentProject == null) {
      _setError('No active project to update');
      return false;
    }

    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final authToken = userProvider.user.token;

    if (authToken == null) {
      _setError('Authentication token not available');
      return false;
    }

    // Save locally immediately
    _currentProject = _currentProject!.copyWith(
      designPreferences: {
        ..._currentProject!.designPreferences,
        'designStyle': styleId,
      },
      updatedAt: DateTime.now(),
    );
    notifyListeners();

    if (background) {
      // Fire-and-forget API call with auto-retry
      _syncDesignStyleToBackend(
        _currentProject!.id,
        authToken,
        styleName,
        letAiDecide: letAiDecide,
      );
      return true;
    }

    try {
      _setStatus(ProjectStatus.uploading);
      await ApiService.submitDesignStyle(
        _currentProject!.id,
        authToken,
        styleName,
        letAiDecide: letAiDecide,
      );
      _setStatus(ProjectStatus.ready);
      return true;
    } catch (e) {
      AppLogger.error('Failed to save design style', e);
      _setError('Failed to save design style: ${e.toString()}');
      return false;
    }
  }

  Future<void> _syncDesignStyleToBackend(
    String projectId,
    String authToken,
    String styleName, {
    bool letAiDecide = false,
  }) async {
    for (int attempt = 0; attempt < 2; attempt++) {
      try {
        await ApiService.submitDesignStyle(
          projectId,
          authToken,
          styleName,
          letAiDecide: letAiDecide,
        );
        AppLogger.info('Design style synced to backend');
        return;
      } catch (e) {
        AppLogger.error(
          'Background design style save failed (attempt ${attempt + 1})',
          e,
        );
        if (attempt == 0) {
          await Future.delayed(const Duration(seconds: 2));
        }
      }
    }
    // Both attempts failed — notify via callback
    onBackgroundSaveError?.call(
      "Couldn't save design style — please try again",
    );
  }

  /// Save improvement markers to backend
  Future<bool> saveMarkers(BuildContext context) async {
    if (_currentProject == null || _markers.isEmpty) {
      _setError('No markers to save');
      return false;
    }

    try {
      _setStatus(ProjectStatus.uploading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      await ApiService.saveImprovementMarkers(
        _currentProject!.id,
        getMarkersJson(),
        authToken,
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save markers', e);
      _setError('Failed to save markers: ${e.toString()}');
      return false;
    }
  }

  /// Fetch AI-generated marker recommendations from backend
  Future<List<String>> fetchRecommendations(BuildContext context) async {
    if (_currentProject == null) return [];

    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;

      if (authToken == null) return [];

      return await ApiService.fetchMarkerRecommendations(
        _currentProject!.id,
        authToken,
      );
    } catch (e) {
      AppLogger.error('Failed to fetch recommendations', e);
      return [];
    }
  }

  // Clear current project
  void clearProject() {
    _currentProject = null;
    _errorMessage = null;
    _markers.clear();
    _productRecommendations = [];
    _selectedRecommendations = [];
    _productSuggestions = null;
    _trendingProducts = null;
    _generatedImageBytes = null;
    _updateGeneratedImageUrl(null);
    _currentJobId = null;
    _pendingSearchJobId = null;
    _jobProgress = 0;
    _jobPhase = null;
    _searchJobCompleter = null;
    _recommendationsCompleter = null;
    _trendingPreloadCompleter = null;
    _projectImageUploadFuture = null;
    _isProjectImageUploading = false;
    _hasUploadedProjectImage = false;
    _preferredStoresDirty = false;
    _searchFailureReason = SearchFailureReason.none;
    _prewarmFingerprint = null;
    _lastPrewarmReused = false;
    _generateDesignFuture = null;
    _generationRetrying = false;
    _furnitureAnalysis = null;
    _processedFurniture = null;
    _detectedHotspots = [];
    _prefetchedFurnitureByHotspotId.clear();
    _furniturePrefetchCompleter = null;
    _robustHotspotAnalysisCompleters.clear();
    _rescueHotspotCompleters.clear();
    _userTappedHotspots.clear();
    _lastCompletedJobId = null;
    _dreamSpaceImageVersion = 0;
    _setStatus(ProjectStatus.idle);
    AppLogger.info('Project cleared');
  }

  // Get project image provider (for Image widget)
  ImageProvider? getProjectImageProvider() {
    if (_currentProject?.localProjectImage != null) {
      return FileImage(_currentProject!.localProjectImage!);
    }
    // Fallback: load from backend base_image URL
    final ctx = _currentProject?.metadata['context'] as Map<String, dynamic>?;
    final baseUrl = ctx?['base_image']?.toString();
    if (baseUrl != null && baseUrl.isNotEmpty && baseUrl.startsWith('http')) {
      return NetworkImage(baseUrl);
    }
    return null;
  }

  ImageProvider? getInspirationImageProvider() {
    final images = _currentProject?.localInspirationImages;
    if (images != null && images.isNotEmpty) {
      return FileImage(images.first);
    }
    return null;
  }

  // Marker management methods
  void addMarker(double x, double y, String description) {
    final trimmedDescription = description.trim();

    final marker = ImprovementMarker(
      id: _uuid.v4(),
      position: MarkerPosition(x: x, y: y),
      description: trimmedDescription,
      color: ImprovementMarker.generateRandomColor(),
    );
    _markers.add(marker);
    notifyListeners();
    AppLogger.info(
      'Marker added at (${x.toStringAsFixed(2)}, ${y.toStringAsFixed(2)})',
    );
  }

  void updateMarker(String markerId, String newDescription) {
    final index = _markers.indexWhere((marker) => marker.id == markerId);
    if (index != -1) {
      final updatedMarker = _markers[index].copyWith(
        description: newDescription.trim(),
      );
      _markers[index] = updatedMarker;
      notifyListeners();
      AppLogger.info('Marker updated: $markerId');
    }
  }

  void deleteMarker(String markerId) {
    final initialLength = _markers.length;
    _markers.removeWhere((marker) => marker.id == markerId);
    if (_markers.length < initialLength) {
      notifyListeners();
      AppLogger.info('Marker deleted: $markerId');
    }
  }

  void clearMarkers() {
    _markers.clear();
    notifyListeners();
    AppLogger.info('All markers cleared');
  }

  ImprovementMarker? getMarkerById(String markerId) {
    try {
      return _markers.firstWhere((marker) => marker.id == markerId);
    } catch (e) {
      return null;
    }
  }

  /// Get markers as JSON array for API submission
  List<Map<String, dynamic>> getMarkersJson() {
    return _markers.map((marker) => marker.toJson()).toList();
  }

  /// Set room dimensions
  void setRoomDimensions({
    required double width,
    required double height,
    required double length,
  }) {
    _roomWidth = width;
    _roomHeight = height;
    _roomLength = length;
    notifyListeners();
    AppLogger.info('Room dimensions set: ${width}x${height}x$length');
  }

  /// Clear room dimensions
  void clearRoomDimensions() {
    _roomWidth = null;
    _roomHeight = null;
    _roomLength = null;
    notifyListeners();
    AppLogger.info('Room dimensions cleared');
  }

  // ==========================================================================
  // Product Recommendations & Image Generation Flow
  // ==========================================================================

  /// Fetch AI product recommendations during first analyzing phase.
  /// Auto-applies "Let AI Decide" for color and style if not already set,
  /// since the backend requires inspiration_recommendations or skipped status.
  Future<bool> fetchProductRecommendations(BuildContext context) async {
    return ensureRecommendationsLoaded(context);
  }

  /// Ensures recommendation fetch runs at most once in-flight.
  Future<bool> ensureRecommendationsLoaded(BuildContext? context) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    if (_productRecommendations.isNotEmpty) {
      return true;
    }

    if (_recommendationsCompleter != null &&
        !_recommendationsCompleter!.isCompleted) {
      AppLogger.info('Recommendations already in-flight — waiting');
      return _recommendationsCompleter!.future;
    }

    _recommendationsCompleter = Completer<bool>();
    try {
      final authToken = _resolveAuthToken(context);
      if (authToken == null) {
        _setError('Authentication token not available');
        _recommendationsCompleter!.complete(false);
        return false;
      }

      final success = await _fetchProductRecommendationsWithToken(authToken);
      _recommendationsCompleter!.complete(success);
      return success;
    } catch (e) {
      if (!_recommendationsCompleter!.isCompleted) {
        _recommendationsCompleter!.complete(false);
      }
      AppLogger.error('Failed to ensure recommendations loaded', e);
      _setError('Failed to fetch recommendations: ${e.toString()}');
      return false;
    }
  }

  /// Pre-warm the entire "Like These?" pipeline in background.
  /// Safe to call multiple times — it reuses in-flight locks.
  Future<bool> ensureLikeThesePreloaded([BuildContext? context]) async {
    final recommendationsReady = await ensureRecommendationsLoaded(context);
    if (!recommendationsReady) return false;

    if (_productSuggestions != null) {
      final categories =
          _productSuggestions!['categories'] as List? ?? const [];
      if (categories.isNotEmpty) {
        // Trending payload is purely read-model data. Fetch it only when
        // categories already exist so we don't add early network contention.
        unawaited(preloadTrendingProducts());
        return true;
      }
    }

    final searchRecommendations = _visibleLikeTheseRecommendations();
    if (searchRecommendations.isEmpty) return true;
    final searchReady = await ensureSearchJobStarted(
      null,
      searchRecommendations,
    );
    if (searchReady) {
      // Refresh trending snapshot after search produces data.
      unawaited(preloadTrendingProducts());
    }
    return searchReady;
  }

  Future<bool> _fetchProductRecommendationsWithToken(String authToken) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final projectId = _currentProject!.id;

      // --- Run prerequisites in parallel for speed ---
      AppLogger.info('Running prerequisites in parallel...');

      // These 4 calls are independent — run them concurrently
      final prerequisites = <Future<void>>[];

      // Prerequisite 1: Skip inspiration images if not in flow
      prerequisites.add(
        (() async {
          try {
            await ApiService.skipInspirationImages(projectId, authToken);
          } catch (e) {
            AppLogger.warning('Skip inspiration images failed (non-fatal): $e');
          }
        })(),
      );

      // Prerequisite 2: Skip color analysis if not set (fast — no Gemini call)
      if (colorPalette == null) {
        prerequisites.add(
          (() async {
            try {
              await ApiService.skipColorAnalysis(projectId, authToken);
            } catch (e) {
              AppLogger.warning(
                'Skip color failed, falling back to analysis: $e',
              );
              try {
                await ApiService.submitColorPalette(
                  projectId,
                  authToken,
                  'AI Selected',
                  [],
                  letAiDecide: true,
                );
              } catch (e2) {
                AppLogger.warning(
                  'Color palette fallback also failed (non-fatal): $e2',
                );
              }
            }
          })(),
        );
      }

      // Prerequisite 3: Skip style analysis if not set (fast — no Gemini call)
      if (designStyle == null) {
        prerequisites.add(
          (() async {
            try {
              await ApiService.skipStyleAnalysis(projectId, authToken);
            } catch (e) {
              AppLogger.warning(
                'Skip style failed, falling back to analysis: $e',
              );
              try {
                await ApiService.submitDesignStyle(
                  projectId,
                  authToken,
                  'AI Selected',
                  letAiDecide: true,
                );
              } catch (e2) {
                AppLogger.warning(
                  'Design style fallback also failed (non-fatal): $e2',
                );
              }
            }
          })(),
        );
      }

      await Future.wait(prerequisites);

      // --- Step 5: Fetch product recommendations ---
      AppLogger.info('Fetching product recommendations...');
      final response = await ApiService.getProductRecommendations(
        _currentProject!.id,
        authToken,
        autoSearch: true,
      );
      final rawSearchJobId = response['search_job_id'];
      if (rawSearchJobId is String && rawSearchJobId.trim().isNotEmpty) {
        _pendingSearchJobId = rawSearchJobId.trim();
        AppLogger.info(
          'Received auto-search job from recommendations endpoint: $_pendingSearchJobId',
        );
      } else {
        _pendingSearchJobId = null;
      }

      _productRecommendations = List<String>.from(
        response['recommendations'] ?? [],
      );
      _safeNotifyListeners();

      AppLogger.info(
        'Got ${_productRecommendations.length} product recommendations',
      );
      return true;
    } catch (e) {
      AppLogger.error('Failed to fetch product recommendations', e);
      _setError('Failed to fetch recommendations: ${e.toString()}');
      return false;
    }
  }

  /// Toggle a product recommendation selection
  Future<bool> toggleRecommendation(
    BuildContext context,
    String recommendation,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      final response = await ApiService.selectProductRecommendation(
        _currentProject!.id,
        authToken,
        recommendation,
      );

      _selectedRecommendations = List<String>.from(
        response['selected_recommendations'] ?? [],
      );
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to toggle recommendation', e);
      _setError('Failed to select recommendation: ${e.toString()}');
      return false;
    }
  }

  /// Store selected recommendations locally without hitting backend.
  void setSelectedRecommendationsLocal(List<String> recommendations) {
    final cleanedRecommendations = recommendations
        .map((recommendation) => recommendation.trim())
        .where((recommendation) => recommendation.isNotEmpty)
        .toSet()
        .toList();
    _selectedRecommendations = cleanedRecommendations;
    notifyListeners();
  }

  /// Atomically set the full list of selected recommendations (single PUT).
  Future<bool> setSelectedRecommendations(
    BuildContext context,
    List<String> recommendations,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      final response = await ApiService.setSelectedRecommendations(
        _currentProject!.id,
        authToken,
        recommendations,
      );

      _selectedRecommendations = List<String>.from(
        response['selected_recommendations'] ?? [],
      );
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.warning(
        'Failed to sync selected recommendations to backend: $e',
      );
      _selectedRecommendations = List<String>.from(recommendations);
      notifyListeners();
      return false;
    }
  }

  /// Save selected trending products to backend for image generation.
  Future<bool> saveSelectedTrendingProducts(
    BuildContext context,
    List<Map<String, dynamic>> items,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }
    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }
      await ApiService.setSelectedTrendingProducts(
        _currentProject!.id,
        authToken,
        items,
      );
      return true;
    } catch (e) {
      AppLogger.warning('Failed to save selected trending products: $e');
      return false;
    }
  }

  /// Ensures exactly one search job is running. Returns the existing
  /// job's future if one is in-flight, otherwise starts a new one.
  Future<bool> ensureSearchJobStarted(
    BuildContext? context,
    List<String> recommendations,
  ) async {
    if (_productSuggestions != null) {
      final categories =
          _productSuggestions!['categories'] as List? ?? const [];
      if (categories.isNotEmpty) {
        return true;
      }
    }

    if (_searchJobCompleter != null && !_searchJobCompleter!.isCompleted) {
      AppLogger.info('Search job already in-flight ($_currentJobId) — waiting');
      return _searchJobCompleter!.future;
    }

    _searchJobCompleter = Completer<bool>();
    try {
      final pendingJobId = _pendingSearchJobId;
      _pendingSearchJobId = null;
      final result = pendingJobId != null && pendingJobId.isNotEmpty
          ? await _pollExistingSearchJob(context, pendingJobId)
          : await startProductSearch(context, recommendations);
      _searchJobCompleter!.complete(result);
      return result;
    } catch (e) {
      _searchJobCompleter!.completeError(e);
      rethrow;
    }
  }

  Future<bool> _pollExistingSearchJob(
    BuildContext? context,
    String jobId,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      _searchFailureReason = SearchFailureReason.jobFailed;
      return false;
    }

    try {
      _searchFailureReason = SearchFailureReason.none;

      final authToken = _resolveAuthToken(context);
      if (authToken == null) {
        _setError('Authentication token not available');
        _searchFailureReason = SearchFailureReason.jobFailed;
        return false;
      }

      _currentJobId = jobId;
      _jobProgress = 0;
      _jobPhase = 'Searching...';
      notifyListeners();

      final pollingResult = await ApiService.pollJobUntilDone(
        _currentProject!.id,
        jobId,
        authToken,
        onProgress: (progressPct, phase) {
          _jobProgress = progressPct;
          _jobPhase = phase;
          notifyListeners();
        },
      );

      _currentJobId = null;

      switch (pollingResult.outcome) {
        case PollingOutcome.done:
          _productSuggestions = await ApiService.getProductSuggestions(
            _currentProject!.id,
            authToken,
          );
          notifyListeners();
          AppLogger.info('Existing product search complete');
          return true;

        case PollingOutcome.jobFailed:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.jobFailed;
          _setError(pollingResult.errorMessage ?? 'Product search failed');
          return false;

        case PollingOutcome.networkFailed:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.networkError;
          _setError(pollingResult.errorMessage ?? 'Network connection lost');
          return false;

        case PollingOutcome.timedOut:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.timeout;
          _setError(pollingResult.errorMessage ?? 'Request timed out');
          return false;
      }
    } catch (e) {
      AppLogger.error('Failed while polling existing search job', e);
      _currentJobId = null;
      _searchFailureReason = SearchFailureReason.networkError;
      final authToken = _resolveAuthToken();
      if (authToken != null) {
        await _tryHydrateProductSuggestions(authToken);
        await preloadTrendingProducts();
      }
      _setError('Product search failed: ${e.toString()}');
      return false;
    }
  }

  /// Start product search and poll until done, then fetch suggestions.
  /// Uses [PollingResult] to distinguish failure modes instead of throwing.
  Future<bool> startProductSearch(
    BuildContext? context,
    List<String> recommendations,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      _searchFailureReason = SearchFailureReason.jobFailed;
      return false;
    }

    try {
      _searchFailureReason = SearchFailureReason.none;
      _pendingSearchJobId = null;

      final authToken = _resolveAuthToken(context);
      if (authToken == null) {
        _setError('Authentication token not available');
        _searchFailureReason = SearchFailureReason.jobFailed;
        return false;
      }

      final cleanedRecommendations = recommendations
          .map((r) => r.trim())
          .where((r) => r.isNotEmpty)
          .toSet()
          .toList();
      if (cleanedRecommendations.isEmpty) {
        _setError('No recommendations provided');
        _searchFailureReason = SearchFailureReason.jobFailed;
        return false;
      }

      final idempotencyKey = _buildSearchIdempotencyKey(cleanedRecommendations);

      AppLogger.info('Starting product search...');
      final jobResponse = await ApiService.startSearchRecommendations(
        _currentProject!.id,
        authToken,
        cleanedRecommendations,
        idempotencyKey: idempotencyKey,
      );

      final jobId = jobResponse['job_id'] as String;
      _currentJobId = jobId;
      _jobProgress = 0;
      _jobPhase = 'Searching...';
      notifyListeners();

      final pollingResult = await ApiService.pollJobUntilDone(
        _currentProject!.id,
        jobId,
        authToken,
        onProgress: (progressPct, phase) {
          _jobProgress = progressPct;
          _jobPhase = phase;
          notifyListeners();
        },
      );

      _currentJobId = null;

      switch (pollingResult.outcome) {
        case PollingOutcome.done:
          // Fetch the results
          _productSuggestions = await ApiService.getProductSuggestions(
            _currentProject!.id,
            authToken,
          );
          notifyListeners();
          AppLogger.info('Product search complete');
          return true;

        case PollingOutcome.jobFailed:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.jobFailed;
          _setError(pollingResult.errorMessage ?? 'Product search failed');
          return false;

        case PollingOutcome.networkFailed:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.networkError;
          _setError(pollingResult.errorMessage ?? 'Network connection lost');
          return false;

        case PollingOutcome.timedOut:
          await _tryHydrateProductSuggestions(authToken);
          await preloadTrendingProducts();
          _searchFailureReason = SearchFailureReason.timeout;
          _setError(pollingResult.errorMessage ?? 'Request timed out');
          return false;
      }
    } catch (e) {
      AppLogger.error('Failed to search products', e);
      _currentJobId = null;
      _searchFailureReason = SearchFailureReason.networkError;
      final authToken = _resolveAuthToken();
      if (authToken != null) {
        await _tryHydrateProductSuggestions(authToken);
        await preloadTrendingProducts();
      }
      _setError('Product search failed: ${e.toString()}');
      return false;
    }
  }

  /// Save user's favorite products from suggestions
  Future<bool> saveFavorites(
    BuildContext context,
    List<Map<String, dynamic>> favorites,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      await ApiService.submitFavoriteProducts(
        _currentProject!.id,
        authToken,
        favorites,
      );
      return true;
    } catch (e) {
      AppLogger.error('Failed to save favorites', e);
      _setError('Failed to save favorites: ${e.toString()}');
      return false;
    }
  }

  /// Generate design directly from inspiration images, skipping the
  /// recommendations/improvements steps. Used by the "Generate with Inspiration"
  /// approach shortcut flow.
  ///
  /// [onRetrying] is invoked when a transient failure triggers an automatic
  /// retry, allowing the UI to show a "Reconnecting..." label.
  Future<bool> generateInspirationDirectly(
    BuildContext context, {
    void Function()? onRetrying,
  }) async {
    return _withTransientRetry(
      () => _generateInspirationDirectlyOnce(context),
      'generateInspirationDirectly',
      onRetrying: onRetrying,
    );
  }

  Future<bool> _generateInspirationDirectlyOnce(BuildContext context) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final authToken = _resolveAuthToken(context);
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      final projectId = _currentProject!.id;

      // 1. Skip color & style analysis, save markers (run in parallel)
      await Future.wait([
        (() async {
          try {
            await ApiService.skipColorAnalysis(projectId, authToken);
          } catch (e) {
            AppLogger.warning('Skip color analysis failed (non-fatal): $e');
          }
        })(),
        (() async {
          try {
            await ApiService.skipStyleAnalysis(projectId, authToken);
          } catch (e) {
            AppLogger.warning('Skip style analysis failed (non-fatal): $e');
          }
        })(),
      ]);

      // 2. Upload inspiration images to backend
      final images = inspirationImages;
      if (images.isNotEmpty) {
        AppLogger.info(
          'Uploading ${images.length} inspiration images for direct generation',
        );
        await ApiService.uploadInspirationImagesBatch(
          projectId,
          authToken,
          images,
        );
      }

      // 3. Kick off the inspiration redesign generation
      final idempotencyKey =
          '${projectId}_inspiration_direct_${DateTime.now().millisecondsSinceEpoch}';

      AppLogger.info('Starting direct inspiration design generation...');
      final jobResponse = await ApiService.startInspirationRedesign(
        projectId,
        authToken,
        idempotencyKey: idempotencyKey,
      );

      final jobId = jobResponse['job_id'] as String;
      _currentJobId = jobId;
      _updateGeneratedImageUrl(null);
      _jobProgress = 0;
      _jobPhase = 'Starting...';
      notifyListeners();

      // 4. Poll for completion
      final pollingResult = await ApiService.pollJobUntilDone(
        projectId,
        jobId,
        authToken,
        onProgress: (progressPct, phase) {
          _jobProgress = progressPct;
          _jobPhase = phase;
          notifyListeners();
        },
      );

      _currentJobId = null;

      switch (pollingResult.outcome) {
        case PollingOutcome.done:
          // Try URL-first path (CDN-cached, ~200 bytes response)
          final imageUrl = await ApiService.getGeneratedImageUrl(
            projectId,
            authToken,
          );
          if (imageUrl != null) {
            _updateGeneratedImageUrl(imageUrl);
            notifyListeners();
            AppLogger.info('Inspiration design URL received: $imageUrl');
            // Download bytes in background for offline fallback
            ApiService.getGeneratedImage(projectId, authToken)
                .then((bytes) {
                  _generatedImageBytes = bytes;
                  notifyListeners();
                })
                .catchError((e) {
                  AppLogger.warning('Background bytes download failed: $e');
                });
          } else {
            _generatedImageBytes = await ApiService.getGeneratedImage(
              projectId,
              authToken,
            );
            notifyListeners();
            AppLogger.info(
              'Inspiration design generated: ${_generatedImageBytes?.length ?? 0} bytes',
            );
          }
          AppLogger.info(
            '[inspiration_direct] Preparing Dream Space hotspots '
            '(imageType=$dreamSpaceAnalysisImageType)',
          );
          try {
            await _prepareDreamSpaceHotspots(authToken);
          } catch (e, st) {
            AppLogger.warning(
              '[inspiration_direct] Dream Space hotspot prep failed (non-fatal): $e',
              e,
              st,
            );
          }
          AppLogger.info(
            '[inspiration_direct] Dream Space hotspot prep complete: '
            'detected=${_detectedHotspots.length} '
            'ready=$readyHotspotCount/${_detectedHotspots.length}',
          );
          return true;

        case PollingOutcome.jobFailed:
          _setError(pollingResult.errorMessage ?? 'Image generation failed');
          return false;

        case PollingOutcome.networkFailed:
          _setError(
            pollingResult.errorMessage ?? 'Network connection lost',
            transient: true,
          );
          return false;

        case PollingOutcome.timedOut:
          _setError(
            pollingResult.errorMessage ?? 'Request timed out',
            transient: true,
          );
          return false;
      }
    } catch (e) {
      AppLogger.error('Failed to generate inspiration design directly', e);
      _currentJobId = null;
      _setError(
        'Inspiration design generation failed: ${e.toString()}',
        transient: _isTransientException(e),
      );
      return false;
    }
  }

  void _resetHotspotPrefetchStateForNewImage() {
    _dreamSpaceImageVersion += 1;
    _furnitureAnalysis = null;
    _detectedHotspots = [];
    _prefetchedFurnitureByHotspotId.clear();
    _furniturePrefetchCompleter = null;
    _robustHotspotAnalysisCompleters.clear();
    _rescueHotspotCompleters.clear();
    _userTappedHotspots.clear();
    notifyListeners();
  }

  Future<void> _prepareDreamSpaceHotspots(String authToken) async {
    // Guard — don't prime hotspots if no generated image available
    final hasGeneratedImage =
        (_generatedImageUrl != null && _generatedImageUrl!.isNotEmpty) ||
        _generatedImageBytes != null;
    if (!hasGeneratedImage) {
      AppLogger.warning(
        'Hotspot prime skipped: no generated image available '
        '(url=${_generatedImageUrl != null}, bytes=${_generatedImageBytes != null})',
      );
      return;
    }

    _resetHotspotPrefetchStateForNewImage();
    final version = _dreamSpaceImageVersion;

    final prefetched = await primeFurnitureHotspotsAndPrefetch(
      authToken: authToken,
      imageType: dreamSpaceAnalysisImageType,
    );
    if (!prefetched) {
      AppLogger.warning(
        'Furniture hotspot prefetch did not complete successfully '
        '(imageType=$dreamSpaceAnalysisImageType)',
      );
    }

    // Fast path: gate already satisfied after batch prefetch
    if (hotspotsReadyForDreamSpace) {
      AppLogger.info(
        '[HotspotGate] Passed immediately after prefetch: '
        '$readyHotspotCount/${_detectedHotspots.length} ready (v$version)',
      );
      _launchBackgroundRescuePrewarm(authToken, version);
      return;
    }

    // Slow path: sequential rescue until threshold ready or 12s elapsed
    await _rescuePrewarmWithReadinessGate(authToken, version);
  }

  @Deprecated('Use _rescuePrewarmWithReadinessGate instead')
  Future<void> prewarmEmptyHotspotsWithRobustFallback({
    BuildContext? context,
    String? authToken,
    Duration maxWait = const Duration(seconds: 12),
  }) async {
    if (_currentProject == null || _detectedHotspots.isEmpty) return;

    final emptyHotspots = _detectedHotspots
        .where((hotspot) => !hasProductsForHotspot(hotspot.id))
        .toList();
    if (emptyHotspots.isEmpty) return;

    AppLogger.info(
      'Hotspot warmup: starting ${emptyHotspots.length} hotspots '
      '(max concurrent=$_hotspotWarmupMaxConcurrent)',
    );

    final sw = Stopwatch()..start();
    final gate = Completer<void>();
    var readyCount = readyHotspotCount;
    var settledCount = 0;
    final total = emptyHotspots.length;
    final threshold = _effectiveReadinessThreshold;
    final queue = List<ProductHotspot>.from(emptyHotspots);
    var running = 0;

    void onSettled(bool success) {
      if (success) readyCount++;
      settledCount++;
      if (!gate.isCompleted &&
          (readyCount >= threshold || settledCount >= total)) {
        gate.complete();
      }
    }

    void startNext() {
      while (running < _hotspotWarmupMaxConcurrent && queue.isNotEmpty) {
        final hotspot = queue.removeAt(0);
        if (hasProductsForHotspot(hotspot.id)) {
          onSettled(true);
          continue;
        }
        running++;
        runRobustHotspotAnalysis(
              hotspot,
              context: context,
              authToken: authToken,
            )
            .then((_) {
              onSettled(hasProductsForHotspot(hotspot.id));
            })
            .catchError((Object e) {
              onSettled(false);
            })
            .whenComplete(() {
              running--;
              startNext();
            });
      }
      if (running == 0 && queue.isEmpty && !gate.isCompleted) {
        gate.complete();
      }
    }

    startNext();

    try {
      await gate.future.timeout(maxWait);
      AppLogger.info(
        'Hotspot warmup gate: $readyCount/$total ready '
        'in ${sw.elapsedMilliseconds}ms (threshold=$threshold)',
      );
    } on TimeoutException {
      AppLogger.info(
        'Hotspot warmup gate: timed out after ${maxWait.inSeconds}s '
        'with $readyCount/$total ready',
      );
    }
  }

  Future<void> _rescuePrewarmWithReadinessGate(
    String authToken,
    int version,
  ) async {
    final emptyHotspots = _detectedHotspots
        .where((h) => !hasProductsForHotspot(h.id))
        .toList();
    if (emptyHotspots.isEmpty) return;

    AppLogger.info(
      '[HotspotGate] Starting rescue gate: ${emptyHotspots.length} empty, '
      'need ${_effectiveReadinessThreshold - readyHotspotCount} more (v$version)',
    );

    final gateCompleter = Completer<void>();
    final sw = Stopwatch()..start();

    // Timeout arm
    final timer = Timer(dreamSpaceReadinessTimeout, () {
      if (!gateCompleter.isCompleted) {
        AppLogger.info(
          '[HotspotGate] Timeout: $readyHotspotCount/${_detectedHotspots.length} '
          'ready after ${sw.elapsedMilliseconds}ms (v$version)',
        );
        gateCompleter.complete();
      }
    });

    // Concurrent rescue arm (continues in background after gate resolves)
    _runConcurrentRescue(
      emptyHotspots: emptyHotspots,
      authToken: authToken,
      version: version,
      onEachComplete: () {
        if (hotspotsReadyForDreamSpace && !gateCompleter.isCompleted) {
          AppLogger.info(
            '[HotspotGate] Threshold met by rescue: '
            '$readyHotspotCount/${_detectedHotspots.length} ready '
            'in ${sw.elapsedMilliseconds}ms (v$version)',
          );
          gateCompleter.complete();
        }
      },
    );

    await gateCompleter.future;
    timer.cancel();
    sw.stop();
  }

  static const int _hotspotWarmupMaxConcurrent = 3;

  Future<void> _runConcurrentRescue({
    required List<ProductHotspot> emptyHotspots,
    required String authToken,
    required int version,
    VoidCallback? onEachComplete,
  }) async {
    AppLogger.info(
      'Hotspot warmup: starting ${emptyHotspots.length} hotspots '
      '(max concurrent=$_hotspotWarmupMaxConcurrent)',
    );

    final queue = List<ProductHotspot>.from(emptyHotspots);
    var running = 0;
    var consecutiveFailures = 0;
    final rescueSw = Stopwatch()..start();
    final allDone = Completer<void>();

    void startNext() {
      while (running < _hotspotWarmupMaxConcurrent && queue.isNotEmpty) {
        // Circuit breaker: stop scheduling new work after consecutive failures
        if (consecutiveFailures >= _rescueMaxConsecutiveFailures) {
          queue.clear();
          break;
        }
        // Wall-clock cap
        if (rescueSw.elapsed > _rescueTotalTimeout) {
          AppLogger.info(
            '[HotspotRescue] Aborting: wall-clock cap exceeded '
            '(${rescueSw.elapsed.inSeconds}s > ${_rescueTotalTimeout.inSeconds}s)',
          );
          queue.clear();
          break;
        }
        // Stale version guard: image was regenerated, abort this rescue
        if (version != _dreamSpaceImageVersion) {
          AppLogger.info(
            '[HotspotRescue] Aborting: version stale '
            '(started=$version, current=$_dreamSpaceImageVersion)',
          );
          queue.clear();
          break;
        }
        if (_currentProject == null) {
          queue.clear();
          break;
        }

        final hotspot = queue.removeAt(0);
        if (hasProductsForHotspot(hotspot.id)) {
          onEachComplete?.call();
          continue;
        }
        if (_userTappedHotspots.contains(hotspot.id)) {
          onEachComplete?.call();
          continue;
        }

        running++;
        rescueHotspotAnalysisForTest(hotspot, authToken, version)
            .then((_) {
              consecutiveFailures = 0;
              onEachComplete?.call();
            })
            .catchError((Object e) {
              consecutiveFailures++;
              AppLogger.warning('[HotspotRescue] Failed for ${hotspot.id}: $e');
              if (consecutiveFailures >= _rescueMaxConsecutiveFailures) {
                AppLogger.info(
                  '[HotspotRescue] Circuit breaker: '
                  '$consecutiveFailures consecutive failures, stopping rescue',
                );
                queue.clear();
              }
              onEachComplete?.call();
            })
            .whenComplete(() {
              running--;
              if (queue.isEmpty && running == 0) {
                if (!allDone.isCompleted) allDone.complete();
              } else {
                startNext();
              }
            });
      }

      // If nothing is running and queue is empty, we're done
      if (running == 0 && queue.isEmpty && !allDone.isCompleted) {
        allDone.complete();
      }
    }

    startNext();
    await allDone.future;
  }

  Future<bool> _runRescueHotspotAnalysis(
    ProductHotspot hotspot,
    String authToken,
    int version,
  ) async {
    if (_currentProject == null) return false;
    final projectId = _currentProject!.id;

    // Dedup: join in-flight rescue if exists (separate from tap-time map)
    final inFlight = _rescueHotspotCompleters[hotspot.id];
    if (inFlight != null && !inFlight.isCompleted) return inFlight.future;
    if (hasProductsForHotspot(hotspot.id)) return true;

    final completer = Completer<bool>();
    _rescueHotspotCompleters[hotspot.id] = completer;

    try {
      final selection = <String, dynamic>{
        'id': hotspot.id,
        'x': hotspot.x,
        'y': hotspot.y,
        'label': hotspot.label,
      };

      AppLogger.info(
        '[HotspotRescue] Starting ${hotspot.id} '
        '(mode=fast_prefetch, timeout=${rescuePrewarmPerHotspotTimeout.inSeconds}s, v$version)',
      );
      final rescueSw = Stopwatch()..start();

      final response = await analyzeFurnitureBatchForPrefetch(
        projectId,
        authToken,
        [selection],
        imageType: dreamSpaceAnalysisImageType,
        timeout: rescuePrewarmPerHotspotTimeout,
        maxAttempts: 2,
      );

      rescueSw.stop();

      // Version guard: don't write stale results into a new image's map
      if (version != _dreamSpaceImageVersion) {
        AppLogger.info(
          '[HotspotRescue] Discarding ${hotspot.id} result: '
          'version stale (started=$version, current=$_dreamSpaceImageVersion)',
        );
        completer.complete(false);
        return false;
      }

      final selectionResults = _extractSelectionResults(response);
      var updated = false;
      for (final raw in selectionResults) {
        if (raw is! Map<String, dynamic>) continue;
        final responseId = raw['id']?.toString().trim() ?? '';
        final hotspotId = responseId.isNotEmpty ? responseId : hotspot.id;
        _prefetchedFurnitureByHotspotId[hotspotId] = Map<String, dynamic>.from(
          raw,
        );
        updated = true;
      }
      if (updated) notifyListeners();

      final success = hasProductsForHotspot(hotspot.id);
      AppLogger.info(
        '[HotspotRescue] Finished ${hotspot.id}: '
        'success=$success, ${rescueSw.elapsedMilliseconds}ms (v$version)',
      );
      completer.complete(success);
      return success;
    } catch (e) {
      AppLogger.warning('[HotspotRescue] Failed ${hotspot.id}: $e');
      if (!completer.isCompleted) completer.complete(false);
      return false;
    } finally {
      _rescueHotspotCompleters.remove(hotspot.id);
    }
  }

  @visibleForTesting
  Future<bool> rescueHotspotAnalysisForTest(
    ProductHotspot hotspot,
    String authToken,
    int version,
  ) {
    return _runRescueHotspotAnalysis(hotspot, authToken, version);
  }

  void _launchBackgroundRescuePrewarm(String authToken, int version) {
    final emptyHotspots = _detectedHotspots
        .where((h) => !hasProductsForHotspot(h.id))
        .toList();
    if (emptyHotspots.isEmpty) return;
    AppLogger.info(
      '[HotspotRescue] Background rescue for '
      '${emptyHotspots.length} empty hotspots (v$version)',
    );
    _runConcurrentRescue(
      emptyHotspots: emptyHotspots,
      authToken: authToken,
      version: version,
    );
  }

  Future<bool> ensureHotspotProductsReady(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
    bool allowRobustFallback = true,
  }) async {
    if (hasProductsForHotspot(hotspot.id)) return true;
    if (!allowRobustFallback) return false;
    return runRobustHotspotAnalysis(
      hotspot,
      context: context,
      authToken: authToken,
    );
  }

  Future<bool> _runRobustHotspotAnalysisWithImageType(
    ProductHotspot hotspot,
    String authToken, {
    required String imageType,
  }) async {
    if (_currentProject == null) return false;
    final projectId = _currentProject!.id;
    final selection = <String, dynamic>{
      'id': hotspot.id,
      'x': hotspot.x,
      'y': hotspot.y,
      'label': hotspot.label,
    };

    try {
      final response = await analyzeFurnitureBatchForHotspotRobust(
        projectId,
        authToken,
        selection,
        imageType: imageType,
      );
      final selectionResults = _extractSelectionResults(response);
      var updated = false;
      for (final raw in selectionResults) {
        if (raw is! Map<String, dynamic>) continue;
        final responseId = raw['id']?.toString().trim() ?? '';
        final hotspotId = responseId.isNotEmpty ? responseId : hotspot.id;
        _prefetchedFurnitureByHotspotId[hotspotId] = Map<String, dynamic>.from(
          raw,
        );
        updated = true;
      }
      if (!updated) {
        _prefetchedFurnitureByHotspotId.putIfAbsent(hotspot.id, () {
          return {
            'id': hotspot.id,
            'label': hotspot.label,
            'furniture_type': hotspot.label,
            'products': <Map<String, dynamic>>[],
            'x': hotspot.x,
            'y': hotspot.y,
          };
        });
      }
      notifyListeners();
      return hasProductsForHotspot(hotspot.id);
    } catch (e) {
      AppLogger.warning(
        'Robust hotspot analysis failed for ${hotspot.id} ($imageType): $e',
      );
      return false;
    }
  }

  Future<bool> runRobustHotspotAnalysis(
    ProductHotspot hotspot, {
    BuildContext? context,
    String? authToken,
  }) async {
    if (_currentProject == null) return false;
    _userTappedHotspots.add(hotspot.id);

    final inFlight = _robustHotspotAnalysisCompleters[hotspot.id];
    if (inFlight != null && !inFlight.isCompleted) {
      return inFlight.future;
    }

    final completer = Completer<bool>();
    _robustHotspotAnalysisCompleters[hotspot.id] = completer;

    try {
      if (hasProductsForHotspot(hotspot.id)) {
        completer.complete(true);
        return true;
      }

      final resolvedAuthToken = authToken ?? _resolveAuthToken(context);
      if (resolvedAuthToken == null) {
        AppLogger.warning(
          'Skipping robust hotspot analysis for ${hotspot.id}: auth token unavailable',
        );
        completer.complete(false);
        return false;
      }

      AppLogger.info(
        '[HotspotTap] Starting full analysis for ${hotspot.id} '
        '(timeout=${tapTimeFallbackTimeout.inSeconds}s)',
      );
      final tapSw = Stopwatch()..start();

      var success = await _runRobustHotspotAnalysisWithImageType(
        hotspot,
        resolvedAuthToken,
        imageType: dreamSpaceAnalysisImageType,
      );
      if (!success &&
          !hasProductsForHotspot(hotspot.id) &&
          dreamSpaceAnalysisImageType != 'product') {
        AppLogger.info(
          '[HotspotTap] Retrying ${hotspot.id} with fallback imageType=product',
        );
        success = await _runRobustHotspotAnalysisWithImageType(
          hotspot,
          resolvedAuthToken,
          imageType: 'product',
        );
      }

      tapSw.stop();
      AppLogger.info(
        '[HotspotTap] Finished ${hotspot.id}: '
        'success=$success, ${tapSw.elapsedMilliseconds}ms',
      );

      completer.complete(success);
      return success;
    } catch (e) {
      AppLogger.warning(
        'Robust hotspot analysis crashed for ${hotspot.id} (non-fatal): $e',
      );
      if (!completer.isCompleted) {
        completer.complete(false);
      }
      return false;
    } finally {
      _robustHotspotAnalysisCompleters.remove(hotspot.id);
    }
  }

  // ---------------------------------------------------------------------------
  // Transient retry wrapper
  // ---------------------------------------------------------------------------

  Future<bool> _withTransientRetry(
    Future<bool> Function() operation,
    String operationName, {
    void Function()? onRetrying,
  }) async {
    final result = await operation();
    if (result) return true;

    // Only retry on transient failures (network/timeout), not job failures
    if (!_lastErrorTransient) return false;

    AppLogger.info('$operationName: transient failure, retrying once...');
    onRetrying?.call();
    clearError();
    final retryResult = await operation();
    if (retryResult) {
      AppLogger.info('$operationName: retry succeeded');
    } else {
      AppLogger.info(
        '$operationName: retry also failed: ${_errorMessage ?? "unknown"}',
      );
    }
    return retryResult;
  }

  // ---------------------------------------------------------------------------
  // Phase-aware retry helpers for generateDesignImage
  // ---------------------------------------------------------------------------

  // pollJobUntilDone returns jobFailed only when the backend reports
  // status='error'. Transport errors (socket, timeout) return networkFailed
  // instead. So "server disconnected" in a jobFailed means the worker
  // crashed — the job is dead and must be restarted.
  static _RetryAction _classifyPollingFailure(PollingResult result) {
    switch (result.outcome) {
      case PollingOutcome.networkFailed:
        return _RetryAction.resumePoll;
      case PollingOutcome.timedOut:
        return _RetryAction.resumePoll;
      case PollingOutcome.jobFailed:
        final msg = (result.errorMessage ?? '').toLowerCase();
        if (msg.contains('server disconnected') ||
            msg.contains('connection closed') ||
            msg.contains('connection reset')) {
          return _RetryAction.restartJob;
        }
        return _RetryAction.giveUp;
      case PollingOutcome.done:
        return _RetryAction.giveUp; // should never reach here
    }
  }

  static bool _isTransientException(Object e) {
    if (e is TimeoutException) return true;
    if (e is SocketException) return true;
    final msg = e.toString().toLowerCase();
    return msg.contains('server disconnected') ||
        msg.contains('connection closed');
  }

  // ═══ PRE-WARM GENERATION SUPPORT ═══

  /// Fingerprint of stable user-choice fields that affect the redesign prompt.
  /// Excludes AI-generated product_recommendations (unstable ordering).
  String get redesignInputsFingerprint {
    final sortedSelectedRecs = List<String>.from(_selectedRecommendations)
      ..sort();

    final markerFingerprints =
        _markers
            .map(
              (m) =>
                  '${m.id}:${(m.position.x * 100).round()}:${(m.position.y * 100).round()}',
            )
            .toList()
          ..sort();

    final fields = <String, dynamic>{
      'project_id': _currentProject?.id,
      'space_type': _currentProject?.spaceChosen,
      'design_style': _currentProject?.designPreferences['designStyle'],
      'color_scheme': _currentProject?.designPreferences['colorPalette'],
      'selected_recs': sortedSelectedRecs,
      'markers': markerFingerprints,
      'approach': _currentProject?.approach,
    };
    final json = jsonEncode(fields);
    return md5.convert(utf8.encode(json)).toString();
  }

  /// Force-invalidate prewarm immediately (called when we know saves are pending).
  void forceInvalidatePrewarm() {
    if (_generateDesignFuture != null) {
      AppLogger.info('PERF_PREWARM force_invalidated (pending saves detected)');
      _generateDesignFuture = null;
      _prewarmFingerprint = null;
    }
    _lastPrewarmReused = false;
  }

  /// Invalidate pre-warmed generation if inputs changed.
  void invalidatePrewarmIfStale() {
    _lastPrewarmReused = false;
    final current = redesignInputsFingerprint;
    if (_generateDesignFuture != null && _prewarmFingerprint != current) {
      AppLogger.info(
        'PERF_PREWARM invalidated: hash_mismatch '
        '(prewarm=$_prewarmFingerprint current=$current)',
      );
      _generateDesignFuture = null;
      _prewarmFingerprint = null;
    } else if (_generateDesignFuture != null) {
      _lastPrewarmReused = true;
      AppLogger.info('PERF_PREWARM reuse=true hash=$current');
    }
  }

  /// Start pre-warm and record fingerprint.
  void startPrewarmGeneration() {
    if (_generateDesignFuture != null) return; // already running
    _prewarmFingerprint = redesignInputsFingerprint;
    AppLogger.info('PERF_PREWARM started: hash=$_prewarmFingerprint');
    generateDesignImage(); // singleflight — sets _generateDesignFuture
  }

  /// Generate design image (inspiration redesign) during second analyzing phase.
  ///
  /// Concurrency guard: if called while already in-flight, returns the same
  /// Future (prevents duplicate jobs from fast re-taps).
  Future<bool> generateDesignImage({void Function()? onRetrying}) {
    _generateDesignFuture ??= _doGenerateDesignImage(onRetrying: onRetrying)
        .whenComplete(() {
          _generateDesignFuture = null;
        });
    return _generateDesignFuture!;
  }

  /// Internal orchestration with single-retry budget across start/poll/fetch.
  Future<bool> _doGenerateDesignImage({void Function()? onRetrying}) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    final authToken = SupabaseService.accessToken;
    if (authToken == null) {
      _setError('Authentication token not available');
      return false;
    }

    final projectId = _currentProject!.id;
    final requestId =
        '${projectId}_redesign_${DateTime.now().millisecondsSinceEpoch}';
    String? jobId;
    bool jobRetryUsed = false;
    bool fetchRetryUsed = false;

    try {
      // ═══ PHASE 1: START JOB ═══
      AppLogger.info(
        '[gen] attempt=1 phase=start '
        'approach=$approach '
        'markerCount=${_markers.length} '
        'recsCount=${_productRecommendations.length} '
        'projectId=$projectId',
      );
      try {
        final jobResponse = await ApiService.startInspirationRedesign(
          projectId,
          authToken,
          idempotencyKey: requestId,
        );
        jobId = jobResponse['job_id'] as String;
      } catch (e) {
        final transient = _isTransientException(e);
        AppLogger.warning(
          '[gen] attempt=1 phase=start outcome=failed '
          'transient=$transient restart=${transient && !jobRetryUsed} '
          'reason=${e.runtimeType}',
        );
        if (transient && !jobRetryUsed) {
          jobRetryUsed = true;
          onRetrying?.call();
          await Future.delayed(const Duration(milliseconds: 1500));
          AppLogger.info('[gen] attempt=2 phase=start restart=true');
          try {
            final jobResponse = await ApiService.startInspirationRedesign(
              projectId,
              authToken,
              idempotencyKey: '${requestId}_retry1',
            );
            jobId = jobResponse['job_id'] as String;
          } catch (e2) {
            AppLogger.error('[gen] attempt=2 phase=start failed', e2);
            _setError('Image generation failed: ${e2.toString()}');
            return false;
          }
        } else {
          _setError('Image generation failed: ${e.toString()}');
          return false;
        }
      }

      _currentJobId = jobId;
      _updateGeneratedImageUrl(null);
      _jobProgress = 0;
      _jobPhase = 'Starting...';
      _safeNotifyListeners();

      // ═══ PHASE 2: POLL JOB ═══
      AppLogger.info('[gen] attempt=1 phase=poll jobId=$jobId');
      var pollingResult = await ApiService.pollJobUntilDone(
        projectId,
        jobId,
        authToken,
        onProgress: (progressPct, phase) {
          _jobProgress = progressPct;
          _jobPhase = phase;
          _safeNotifyListeners();
        },
      );

      if (pollingResult.outcome != PollingOutcome.done && !jobRetryUsed) {
        final action = _classifyPollingFailure(pollingResult);
        AppLogger.warning(
          '[gen] attempt=1 phase=poll jobId=$jobId '
          'outcome=${pollingResult.outcome} transient=${action != _RetryAction.giveUp} '
          'restart=${action == _RetryAction.restartJob} '
          'reason=${pollingResult.errorMessage}',
        );

        switch (action) {
          case _RetryAction.resumePoll:
            jobRetryUsed = true;
            onRetrying?.call();
            _generationRetrying = true;
            _safeNotifyListeners();
            await Future.delayed(const Duration(milliseconds: 1500));
            AppLogger.info(
              '[gen] attempt=2 phase=poll jobId=$jobId restart=false (resume)',
            );
            try {
              pollingResult = await ApiService.pollJobUntilDone(
                projectId,
                jobId,
                authToken,
                onProgress: (progressPct, phase) {
                  _jobProgress = progressPct;
                  _jobPhase = phase;
                  _safeNotifyListeners();
                },
              );
            } finally {
              _generationRetrying = false;
              _safeNotifyListeners();
            }

          case _RetryAction.restartJob:
            jobRetryUsed = true;
            onRetrying?.call();
            _currentJobId = null;
            _generationRetrying = true;
            _safeNotifyListeners();
            await Future.delayed(const Duration(milliseconds: 1500));
            AppLogger.info(
              '[gen] attempt=2 phase=start restart=true reason=transientJobFailed',
            );
            try {
              final jobResponse = await ApiService.startInspirationRedesign(
                projectId,
                authToken,
                idempotencyKey: '${requestId}_retry1',
              );
              jobId = jobResponse['job_id'] as String;
              _currentJobId = jobId;
              _updateGeneratedImageUrl(null);
              _jobProgress = 0;
              _jobPhase = 'Starting...';
              _safeNotifyListeners();
              pollingResult = await ApiService.pollJobUntilDone(
                projectId,
                jobId,
                authToken,
                onProgress: (progressPct, phase) {
                  _jobProgress = progressPct;
                  _jobPhase = phase;
                  _safeNotifyListeners();
                },
              );
            } catch (e) {
              AppLogger.error('[gen] attempt=2 phase=start/poll failed', e);
              _currentJobId = null;
              _setError('Image generation failed: ${e.toString()}');
              return false;
            } finally {
              _generationRetrying = false;
              _safeNotifyListeners();
            }

          case _RetryAction.giveUp:
            break; // fall through to error handling below
        }
      }

      if (pollingResult.outcome != PollingOutcome.done) {
        _currentJobId = null;
        _safeNotifyListeners();
        switch (pollingResult.outcome) {
          case PollingOutcome.jobFailed:
            _setError(pollingResult.errorMessage ?? 'Image generation failed');
          case PollingOutcome.networkFailed:
            _setError(pollingResult.errorMessage ?? 'Network connection lost');
          case PollingOutcome.timedOut:
            _setError(pollingResult.errorMessage ?? 'Request timed out');
          case PollingOutcome.done:
            break; // unreachable
        }
        return false;
      }

      // ═══ PHASE 3: FETCH IMAGE ═══
      // Try URL-first path (CDN-cached, ~200 bytes response), fall back to bytes.
      // Keep _currentJobId alive for debugging until fetch completes.
      bool urlFetched = false;
      try {
        final imageUrl = await ApiService.getGeneratedImageUrl(
          projectId,
          authToken,
        );
        if (imageUrl != null) {
          _updateGeneratedImageUrl(imageUrl);
          urlFetched = true;
          _safeNotifyListeners();
          AppLogger.info('[gen] phase=fetch url=$imageUrl');
          // Download bytes in background for offline fallback
          ApiService.getGeneratedImage(projectId, authToken)
              .then((bytes) {
                _generatedImageBytes = bytes;
                _safeNotifyListeners();
              })
              .catchError((e) {
                AppLogger.warning('[gen] background bytes download failed: $e');
              });
        }
      } catch (e) {
        AppLogger.warning('[gen] phase=fetch_url failed: $e');
      }

      if (!urlFetched) {
        try {
          _generatedImageBytes = await ApiService.getGeneratedImage(
            projectId,
            authToken,
          );
        } catch (e) {
          final transient = _isTransientException(e);
          AppLogger.warning(
            '[gen] phase=fetch failed transient=$transient'
            '${transient && !fetchRetryUsed ? ", retrying..." : ""}',
          );
          if (transient && !fetchRetryUsed) {
            fetchRetryUsed = true;
            onRetrying?.call();
            await Future.delayed(const Duration(milliseconds: 1500));
            try {
              _generatedImageBytes = await ApiService.getGeneratedImage(
                projectId,
                authToken,
              );
            } catch (e2) {
              AppLogger.error('[gen] phase=fetch retry failed', e2);
              _currentJobId = null;
              _safeNotifyListeners();
              _setError('Image generation failed: ${e2.toString()}');
              return false;
            }
          } else {
            _currentJobId = null;
            _safeNotifyListeners();
            _setError('Image generation failed: ${e.toString()}');
            return false;
          }
        }
      }

      _lastCompletedJobId = _currentJobId; // [REGEN_VERIFY]
      _currentJobId = null;
      _safeNotifyListeners();
      AppLogger.info(
        '[gen] phase=fetch success urlFetched=$urlFetched bytes=${_generatedImageBytes?.length ?? 0}',
      );
      AppLogger.info(
        '[gen] Preparing Dream Space hotspots '
        '(approach=$approach imageType=$dreamSpaceAnalysisImageType)',
      );
      await _prepareDreamSpaceHotspots(authToken);
      AppLogger.info(
        '[gen] Dream Space hotspot prep complete: '
        'detected=${_detectedHotspots.length} '
        'ready=$readyHotspotCount/${_detectedHotspots.length}',
      );
      return true;
    } catch (e) {
      AppLogger.error('[gen] unexpected error', e);
      _currentJobId = null;
      _generationRetrying = false;
      _safeNotifyListeners();
      _setError('Image generation failed: ${e.toString()}');
      return false;
    }
  }

  /// Fetch the generated image after a background job completes.
  /// Used when DreamSpace navigated before generation finished.
  Future<bool> fetchGeneratedImage() async {
    if (_currentProject == null || _currentJobId == null) return false;
    final authToken = SupabaseService.accessToken;
    if (authToken == null) return false;

    try {
      final imageUrl = await ApiService.getGeneratedImageUrl(
        _currentProject!.id,
        authToken,
      );
      if (imageUrl != null) {
        _updateGeneratedImageUrl(imageUrl);
        notifyListeners();

        // Fetch bytes in background for offline/caching
        ApiService.getGeneratedImage(_currentProject!.id, authToken)
            .then((bytes) {
              _generatedImageBytes = bytes;
              notifyListeners();
            })
            .catchError((e) {
              AppLogger.warning(
                '[gen] fetchGeneratedImage background bytes failed: $e',
              );
            });
      }

      // Prepare hotspots for the generated image
      AppLogger.info(
        '[gen_bg] Preparing Dream Space hotspots '
        '(approach=$approach imageType=$dreamSpaceAnalysisImageType)',
      );
      await _prepareDreamSpaceHotspots(authToken);
      AppLogger.info(
        '[gen_bg] Dream Space hotspot prep complete: '
        'detected=${_detectedHotspots.length} '
        'ready=$readyHotspotCount/${_detectedHotspots.length}',
      );

      _lastCompletedJobId = _currentJobId; // [REGEN_VERIFY]
      _currentJobId = null;
      notifyListeners();
      return _generatedImageUrl != null;
    } catch (e) {
      AppLogger.error('[gen] fetchGeneratedImage failed', e);
      return false;
    }
  }

  /// Retry redesign with explicit user feedback.
  ///
  /// This intentionally avoids BuildContext so long-running requests cannot
  /// outlive widget lifecycle.
  ///
  /// [onRetrying] is invoked when a transient failure triggers an automatic
  /// retry, allowing the UI to show a "Reconnecting..." label.
  Future<bool> retryDesignImage(
    String feedback, {
    void Function()? onRetrying,
  }) async {
    if (feedback.trim().isEmpty) {
      _setError('Feedback is required');
      return false;
    }
    return _withTransientRetry(
      () => _retryDesignImageOnce(feedback),
      'retryDesignImage',
      onRetrying: onRetrying,
    );
  }

  Future<bool> _retryDesignImageOnce(String feedback) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      final authToken = SupabaseService.accessToken;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Starting retry redesign with feedback...');
      final attemptId = _uuid.v4();
      await ApiService.startRetryRedesign(
        _currentProject!.id,
        authToken,
        feedback,
        attemptId: attemptId,
      );

      // Try URL-first, then fall back to bytes download.
      final imageUrl = await ApiService.getGeneratedImageUrl(
        _currentProject!.id,
        authToken,
      );
      if (imageUrl != null) {
        _updateGeneratedImageUrl(imageUrl);
        notifyListeners();
        // Background bytes fetch for offline fallback
        ApiService.getGeneratedImage(_currentProject!.id, authToken)
            .then((bytes) {
              _generatedImageBytes = bytes;
              notifyListeners();
            })
            .catchError((e) {
              AppLogger.warning('Retry: background bytes download failed: $e');
            });
      } else {
        _generatedImageBytes = await ApiService.getGeneratedImage(
          _currentProject!.id,
          authToken,
        );
        notifyListeners();
      }
      AppLogger.info(
        '[retry_design] Preparing Dream Space hotspots '
        '(imageType=$dreamSpaceAnalysisImageType)',
      );
      try {
        await _prepareDreamSpaceHotspots(authToken);
      } catch (e, st) {
        AppLogger.warning(
          '[retry_design] Dream Space hotspot prep failed (non-fatal): $e',
          e,
          st,
        );
      }
      AppLogger.info(
        '[retry_design] Dream Space hotspot prep complete: '
        'detected=${_detectedHotspots.length} '
        'ready=$readyHotspotCount/${_detectedHotspots.length}',
      );

      AppLogger.info(
        'Retry redesign complete: url=${_generatedImageUrl != null} bytes=${_generatedImageBytes?.length ?? 0}',
      );
      return true;
    } on PaywallRequiredException {
      AppLogger.info('Retry blocked by paywall');
      _setError('Free retry limit reached');
      _setStatus(ProjectStatus.idle);
      rethrow;
    } catch (e) {
      AppLogger.error('Failed to retry design image', e);
      _setError(
        'Retry redesign failed: ${e.toString()}',
        transient: _isTransientException(e),
      );
      return false;
    }
  }

  /// Analyze furniture items at specified image coordinates
  Future<bool> analyzeFurniture(
    BuildContext context,
    List<Map<String, dynamic>> selections, {
    String imageType = 'product',
  }) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      _setStatus(ProjectStatus.loading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Analyzing furniture...');
      _furnitureAnalysis = await _analyzeFurnitureBatchResilient(
        _currentProject!.id,
        authToken,
        selections,
        imageType: imageType,
        mode: 'full',
        timeout: const Duration(seconds: 90),
        maxAttempts: 2,
        logContext: 'analyzeFurniture',
      );
      _setStatus(ProjectStatus.ready);
      notifyListeners();

      AppLogger.info('Furniture analysis complete');
      return true;
    } catch (e) {
      AppLogger.error('Failed to analyze furniture', e);
      _setError(
        'Furniture analysis failed: ${e.toString()}',
        transient: _isTransientFurnitureAnalysisError(e),
      );
      return false;
    }
  }

  /// Auto-detect hotspot candidates and prefetch product analysis in background.
  ///
  /// This method intentionally avoids setting global error status so Dream Space
  /// can stay interactive even if detection/prefetch fails.
  Future<bool> primeFurnitureHotspotsAndPrefetch({
    BuildContext? context,
    String imageType = dreamSpaceImageType,
    String? authToken,
  }) async {
    if (_currentProject == null) return false;
    final projectId = _currentProject!.id;

    if (_furniturePrefetchCompleter != null &&
        !_furniturePrefetchCompleter!.isCompleted) {
      return _furniturePrefetchCompleter!.future;
    }

    _furniturePrefetchCompleter = Completer<bool>();
    final resolvedAuthToken = authToken ?? _resolveAuthToken(context);
    if (resolvedAuthToken == null) {
      AppLogger.warning('Skipping furniture prefetch: auth token unavailable');
      _furniturePrefetchCompleter?.complete(false);
      _furniturePrefetchCompleter = null;
      return false;
    }

    try {
      final detectResponse = await autoDetectFurnitureForPrefetch(
        projectId,
        resolvedAuthToken,
        imageType: imageType,
      );
      final rawDetections = detectResponse['detections'] as List? ?? const [];
      final sourceW = detectResponse['source_image_width'];
      final sourceH = detectResponse['source_image_height'];
      AppLogger.info(
        'Auto-detect source image: ${sourceW ?? '?'}x${sourceH ?? '?'}',
      );
      if (sourceW == null || sourceH == null) {
        AppLogger.warning(
          'Auto-detect returned null dimensions — backend may lack active image',
        );
      }
      final resolvedImageType =
          detectResponse['resolved_image_type']?.toString().trim().isNotEmpty ==
              true
          ? detectResponse['resolved_image_type'].toString().trim()
          : imageType;
      final rawDetectionCount = rawDetections.length;

      final parsedDetections = <Map<String, dynamic>>[];
      for (final raw in rawDetections) {
        if (raw is! Map) continue;
        final rect = _extractDetectionRect(raw);
        if (rect == null) continue;

        final x = rect['x'];
        final y = rect['y'];
        final width = rect['width'];
        final height = rect['height'];

        if (x == null ||
            y == null ||
            width == null ||
            height == null ||
            width <= 0 ||
            height <= 0) {
          continue;
        }

        final safeX = x.clamp(0.0, 1.0).toDouble();
        final safeY = y.clamp(0.0, 1.0).toDouble();
        final safeW = width.clamp(0.0, 1.0).toDouble();
        final safeH = height.clamp(0.0, 1.0).toDouble();
        final centerX = (safeX + (safeW / 2)).clamp(0.0, 1.0).toDouble();
        final centerY = (safeY + (safeH / 2)).clamp(0.0, 1.0).toDouble();
        final area = (safeW * safeH).clamp(0.0, 1.0).toDouble();
        final confidence = ((raw['confidence'] as num?)?.toDouble() ?? 0.0)
            .clamp(0.0, 1.0)
            .toDouble();
        final label = raw['label']?.toString().trim().isNotEmpty == true
            ? raw['label'].toString().trim()
            : 'Furniture';

        parsedDetections.add({
          'x': centerX,
          'y': centerY,
          'label': label,
          'area': area,
          'confidence': confidence,
          'score': (area * 0.60) + (confidence * 0.40),
          'source': raw['source']?.toString() ?? 'detector',
        });
      }
      final parsedDetectionCount = parsedDetections.length;

      parsedDetections.sort(
        (a, b) => (b['score'] as num).compareTo(a['score'] as num),
      );

      var ranked = parsedDetections
          .where((d) => _looksLikeFurnitureLabel(d['label'] as String))
          .toList();
      if (ranked.isEmpty) {
        ranked = parsedDetections;
      }
      const targetHotspots = dreamSpaceHotspotCount;
      final selectedDetections = <Map<String, dynamic>>[];
      for (final item in ranked) {
        if (_isHotspotCandidateFarEnough(item, selectedDetections)) {
          selectedDetections.add(item);
        }
        if (selectedDetections.length >= targetHotspots) {
          break;
        }
      }
      if (selectedDetections.length < targetHotspots) {
        for (final item in ranked) {
          if (selectedDetections.contains(item)) continue;
          if (_isHotspotCandidateFarEnough(
            item,
            selectedDetections,
            minDistance: 0.045,
          )) {
            selectedDetections.add(item);
          }
          if (selectedDetections.length >= targetHotspots) {
            break;
          }
        }
      }
      if (selectedDetections.length < targetHotspots) {
        _appendFallbackHotspotAnchors(selectedDetections);
      }
      if (selectedDetections.length > targetHotspots) {
        selectedDetections.removeRange(
          targetHotspots,
          selectedDetections.length,
        );
      }
      ranked = selectedDetections;
      final syntheticCount = ranked
          .where((d) => (d['source']?.toString() ?? '').startsWith('synthetic'))
          .length;

      final hotspots = <ProductHotspot>[];
      final selections = <Map<String, dynamic>>[];
      for (var i = 0; i < ranked.length; i++) {
        final d = ranked[i];
        final x = d['x'] as double;
        final y = d['y'] as double;
        final label = d['label'] as String;
        final hotspotId =
            'auto_${i}_${(x * 1000).round()}_${(y * 1000).round()}';

        hotspots.add(
          ProductHotspot(
            id: hotspotId,
            x: x,
            y: y,
            itemType: 'furniture',
            label: label,
          ),
        );
        selections.add({'id': hotspotId, 'x': x, 'y': y, 'label': label});
      }

      _detectedHotspots = hotspots;
      final validHotspotIds = hotspots.map((h) => h.id).toSet();
      _prefetchedFurnitureByHotspotId.removeWhere(
        (key, _) => !validHotspotIds.contains(key),
      );
      _seedHotspotCachePlaceholders(hotspots);
      notifyListeners();

      if (selections.isEmpty) {
        AppLogger.info(
          'Dream Space hotspot pipeline: requested=$imageType resolved=$resolvedImageType raw=$rawDetectionCount parsed=$parsedDetectionCount rendered=0 synthetic=0 prefetchSuccess=0',
        );
        _furniturePrefetchCompleter?.complete(true);
        _furniturePrefetchCompleter = null;
        return true;
      }

      try {
        final analysisResponse = await analyzeFurnitureBatchForPrefetch(
          projectId,
          resolvedAuthToken,
          selections,
          imageType: imageType,
        );
        final selectionResults = _extractSelectionResults(analysisResponse);
        for (final raw in selectionResults) {
          if (raw is! Map<String, dynamic>) continue;
          final hotspotId = raw['id']?.toString().trim() ?? '';
          if (hotspotId.isEmpty) continue;
          _prefetchedFurnitureByHotspotId[hotspotId] =
              Map<String, dynamic>.from(raw);
        }
        notifyListeners();
      } catch (e) {
        AppLogger.warning('Furniture prefetch analysis failed (non-fatal): $e');
      }

      final prefetchSuccessCount = hotspots
          .where((hotspot) => hasProductsForHotspot(hotspot.id))
          .length;
      AppLogger.info(
        'Dream Space hotspot pipeline: requested=$imageType resolved=$resolvedImageType raw=$rawDetectionCount parsed=$parsedDetectionCount rendered=${hotspots.length} synthetic=$syntheticCount prefetchSuccess=$prefetchSuccessCount',
      );

      _furniturePrefetchCompleter?.complete(true);
      _furniturePrefetchCompleter = null;
      return true;
    } catch (e) {
      AppLogger.warning('Furniture hotspot prime failed (non-fatal): $e');
      _furniturePrefetchCompleter?.complete(false);
      _furniturePrefetchCompleter = null;
      return false;
    }
  }

  /// Process selected furniture products (resolve URLs, generate carts)
  Future<bool> processFurniture(
    BuildContext context,
    List<Map<String, dynamic>> selectedProducts,
  ) async {
    if (_currentProject == null) {
      _setError('No active project');
      return false;
    }

    try {
      _setStatus(ProjectStatus.loading);

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final authToken = userProvider.user.token;
      if (authToken == null) {
        _setError('Authentication token not available');
        return false;
      }

      AppLogger.info('Processing furniture selection...');
      _processedFurniture = await ApiService.processFurnitureSelection(
        _currentProject!.id,
        authToken,
        selectedProducts,
      );
      _setStatus(ProjectStatus.ready);
      notifyListeners();

      AppLogger.info('Furniture selection processed');
      return true;
    } catch (e) {
      AppLogger.error('Failed to process furniture', e);
      _setError('Failed to process furniture: ${e.toString()}');
      return false;
    }
  }
}
