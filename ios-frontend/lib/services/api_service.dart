import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:mime/mime.dart';
import '../constants/api_constants.dart';
import '../models/preferred_store.dart';
import '../utils/logger.dart';

enum PollingOutcome { done, jobFailed, networkFailed, timedOut }

class PollingResult {
  final PollingOutcome outcome;
  final Map<String, dynamic>? data;
  final String? errorMessage;

  const PollingResult._(this.outcome, {this.data, this.errorMessage});

  factory PollingResult.done(Map<String, dynamic> data) =>
      PollingResult._(PollingOutcome.done, data: data);
  factory PollingResult.jobFailed(String error) =>
      PollingResult._(PollingOutcome.jobFailed, errorMessage: error);
  factory PollingResult.networkFailed(String error) =>
      PollingResult._(PollingOutcome.networkFailed, errorMessage: error);
  factory PollingResult.timedOut(String jobId, Duration elapsed) =>
      PollingResult._(
        PollingOutcome.timedOut,
        errorMessage: 'Job $jobId timed out after ${elapsed.inSeconds}s',
      );
}

class ApiService {
  /// Assert projectId is non-empty before building any API URL.
  /// Prevents /api/projects//upload-image (double-slash) catastrophic URLs.
  static void _requireProjectId(String projectId) {
    if (projectId.isEmpty) {
      AppLogger.error('API call attempted with empty projectId');
      throw ArgumentError('projectId must not be empty');
    }
  }

  static const String _loopbackDeviceHint =
      'On a physical iPhone, localhost points to the phone. '
      'Use --dart-define=API_BASE_URL=http://<mac-ip>:8000/api.';

  static Object _maybeEnrichLoopbackConnectionError(Object error) {
    if (!ApiConstants.isLoopbackBaseUrl) return error;

    if (error is SocketException) {
      return SocketException('${error.message}. $_loopbackDeviceHint');
    }

    if (error is http.ClientException) {
      final uri = error.uri;
      final baseMessage = error.message;
      return http.ClientException('$baseMessage. $_loopbackDeviceHint', uri);
    }

    return error;
  }

  static Future<Map<String, dynamic>> createProject(String authToken) async {
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.createProject}',
      );

      AppLogger.info('Creating new project for user');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        AppLogger.info('Project created successfully: ${data['project_id']}');
        return data;
      } else {
        AppLogger.error(
          'Failed to create project: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to create project: ${response.statusCode}');
      }
    } catch (e) {
      final enrichedError = _maybeEnrichLoopbackConnectionError(e);
      AppLogger.error('Error creating project', enrichedError);
      if (identical(enrichedError, e)) {
        rethrow;
      }
      throw enrichedError;
    }
  }

  static Future<Map<String, dynamic>> getProject(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.getProject}/$projectId',
      );

      final response = await http.get(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        AppLogger.info('Project data retrieved successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to get project: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to get project: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error getting project', e);
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> updateProject(
    String projectId,
    String authToken,
    Map<String, dynamic> updates,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.updateProject}/$projectId',
      );

      final response = await http.put(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode(updates),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        AppLogger.info('Project updated successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to update project: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to update project: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error updating project', e);
      rethrow;
    }
  }

  /// Fetch preferred stores list (client-side static data)
  static Future<List<PreferredStore>> fetchPreferredStores() async {
    await Future.delayed(const Duration(milliseconds: 500));

    const mockResponse = [
      {'id': 'walmart', 'name': 'Walmart', 'logoUrl': ''},
      {'id': 'amazon', 'name': 'Amazon', 'logoUrl': 'assets/logo/amazon.png'},
      {'id': 'ikea', 'name': 'IKEA', 'logoUrl': 'assets/logo/ikea.png'},
      {'id': 'ashley', 'name': 'Ashley', 'logoUrl': ''},
      {'id': 'target', 'name': 'Target', 'logoUrl': 'assets/logo/target.png'},
      {'id': 'wayfair', 'name': 'Wayfair', 'logoUrl': ''},
      {'id': 'etsy', 'name': 'Etsy', 'logoUrl': 'assets/logo/etsy.png'},
      {'id': 'other', 'name': 'Other', 'logoUrl': ''},
    ];

    AppLogger.info('Fetched ${mockResponse.length} preferred stores');
    return mockResponse
        .map((storeJson) => PreferredStore.fromJson(storeJson))
        .toList();
  }

  /// Submit space type to backend
  static Future<Map<String, dynamic>> submitSpaceType(
    String projectId,
    String authToken,
    String spaceType,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.spaceType, projectId)}',
      );

      AppLogger.info('Submitting space type for $projectId: $spaceType');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({'space_type': spaceType}),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Space type submitted successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to submit space type: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to submit space type: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error submitting space type', e);
      rethrow;
    }
  }

  /// Skip inspiration images step (marks as skipped on backend)
  static Future<Map<String, dynamic>> skipInspirationImages(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.skipInspirationImages, projectId)}',
      );

      AppLogger.info('Skipping inspiration images for $projectId');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Inspiration images skipped successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to skip inspiration images: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to skip inspiration images: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error skipping inspiration images', e);
      rethrow;
    }
  }

  /// Skip color analysis to unblock downstream steps without Gemini call
  static Future<void> skipColorAnalysis(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    final url = Uri.parse(
      '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.skipColorAnalysis, projectId)}',
    );
    final response = await http.post(
      url,
      headers: ApiConstants.authHeaders(authToken),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to skip color analysis: ${response.statusCode}');
    }
  }

  /// Skip style analysis to unblock downstream steps without Gemini call
  static Future<void> skipStyleAnalysis(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    final url = Uri.parse(
      '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.skipStyleAnalysis, projectId)}',
    );
    final response = await http.post(
      url,
      headers: ApiConstants.authHeaders(authToken),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to skip style analysis: ${response.statusCode}');
    }
  }

  /// Submit design approach (iterative / complete_revamp)
  static Future<Map<String, dynamic>> submitApproach(
    String projectId,
    String authToken,
    String approach,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.improvementMode, projectId)}',
      );

      AppLogger.info('Submitting approach for $projectId: $approach');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({'mode': approach}),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Approach submitted successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to submit approach: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to submit approach: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error submitting approach', e);
      rethrow;
    }
  }

  /// Submit preferred store names
  static Future<Map<String, dynamic>> submitPreferredStores(
    String projectId,
    String authToken,
    List<String> storeNames,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.preferredStores, projectId)}',
      );

      AppLogger.info('Submitting preferred stores for $projectId: $storeNames');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({'stores': storeNames}),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Preferred stores submitted successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to submit preferred stores: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to submit preferred stores: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error submitting preferred stores', e);
      rethrow;
    }
  }

  /// Submit color palette for AI color analysis
  static Future<Map<String, dynamic>> submitColorPalette(
    String projectId,
    String authToken,
    String paletteName,
    List<String> colors, {
    bool letAiDecide = false,
  }) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.applyColorScheme, projectId)}',
      );

      AppLogger.info('Submitting color palette for $projectId: $paletteName');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({
          'palette_name': paletteName,
          'colors': colors,
          'let_ai_decide': letAiDecide,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Color palette submitted successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to submit color palette: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to submit color palette: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error submitting color palette', e);
      rethrow;
    }
  }

  /// Submit design style for AI style analysis
  static Future<Map<String, dynamic>> submitDesignStyle(
    String projectId,
    String authToken,
    String styleName, {
    bool letAiDecide = false,
  }) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.applyStyle, projectId)}',
      );

      AppLogger.info('Submitting design style for $projectId: $styleName');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({
          'style_name': styleName,
          'let_ai_decide': letAiDecide,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Design style submitted successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to submit design style: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to submit design style: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error submitting design style', e);
      rethrow;
    }
  }

  static Future<bool> uploadProjectImage(
    String projectId,
    String authToken,
    File imageFile, {
    bool isInspiration = false,
  }) async {
    _requireProjectId(projectId);
    try {
      final endpoint = isInspiration
          ? ApiConstants.withProjectId(
              ApiConstants.uploadInspiration,
              projectId,
            )
          : ApiConstants.withProjectId(ApiConstants.uploadImage, projectId);
      final url = Uri.parse('${ApiConstants.baseUrl}$endpoint');

      final fileName = imageFile.path.split('/').last;
      final mimeType = await _detectMimeType(imageFile);
      final fileSize = await imageFile.length();

      AppLogger.info(
        'Upload: project_id=$projectId, fileName=$fileName, contentType=$mimeType, size=$fileSize bytes',
      );

      var request = http.MultipartRequest('POST', url);
      request.headers.addAll(ApiConstants.authOnlyHeaders(authToken));

      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          imageFile.path,
          filename: fileName,
          contentType: MediaType.parse(mimeType),
        ),
      );

      request.fields['fileName'] = fileName;
      request.fields['mimeType'] = mimeType;
      request.fields['fieldName'] = isInspiration ? 'inspiration' : 'image';

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        AppLogger.info(
          '${isInspiration ? 'Inspiration' : 'Project'} image uploaded successfully',
        );
        return true;
      } else {
        AppLogger.error(
          'Failed to upload image: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to upload image: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error uploading image', e);
      rethrow;
    }
  }

  static Future<bool> uploadInspirationImagesBatch(
    String projectId,
    String authToken,
    List<File> imageFiles,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.uploadInspirationBatch, projectId)}',
      );

      AppLogger.info(
        'Uploading ${imageFiles.length} inspiration images in batch',
      );

      var request = http.MultipartRequest('POST', url);
      request.headers.addAll(ApiConstants.authOnlyHeaders(authToken));

      for (int i = 0; i < imageFiles.length; i++) {
        final imageFile = imageFiles[i];
        final fileName = imageFile.path.split('/').last;
        final mimeType = await _detectMimeType(imageFile);

        request.files.add(
          await http.MultipartFile.fromPath(
            'images',
            imageFile.path,
            filename: fileName,
            contentType: MediaType.parse(mimeType),
          ),
        );

        request.fields['fileName_$i'] = fileName;
        request.fields['mimeType_$i'] = mimeType;
      }

      request.fields['imageCount'] = imageFiles.length.toString();
      request.fields['batchId'] = DateTime.now().millisecondsSinceEpoch
          .toString();

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        AppLogger.info('Inspiration images batch uploaded successfully');
        return true;
      } else {
        AppLogger.error(
          'Failed to upload inspiration images batch: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to upload inspiration images batch: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error uploading inspiration images batch', e);
      rethrow;
    }
  }

  /// Fetch improvement actions (client-side static data for UI)
  static Future<List<Map<String, String>>> fetchImprovementActions() async {
    await Future.delayed(const Duration(milliseconds: 350));

    const mockActions = [
      {
        'id': 'add_change_vase',
        'title': 'add/change Vase',
        'assetPath': 'assets/images/extras/vase.png',
      },
      {
        'id': 'add_change_sofa',
        'title': 'add/change Sofa',
        'assetPath': 'assets/images/improvements/sofa.png',
      },
    ];

    AppLogger.info('Fetched ${mockActions.length} improvement actions');
    return mockActions;
  }

  /// Save improvement markers for a project
  static Future<Map<String, dynamic>> saveImprovementMarkers(
    String projectId,
    List<Map<String, dynamic>> markers,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.improvementMarkers, projectId)}',
      );

      AppLogger.info(
        'Saving ${markers.length} markers for project: $projectId (URL: $url)',
      );

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({'markers': markers}),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Markers saved successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to save markers: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to save markers: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error saving markers', e);
      rethrow;
    }
  }

  /// Fetch AI-generated marker recommendations
  static Future<List<String>> fetchMarkerRecommendations(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.markerRecommendations, projectId)}',
      );

      AppLogger.info('Fetching marker recommendations for $projectId');

      final response = await http.get(
        url,
        headers: ApiConstants.authHeaders(authToken),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final recommendations = List<String>.from(
          data['recommendations'] ?? [],
        );
        AppLogger.info(
          'Fetched ${recommendations.length} marker recommendations',
        );
        return recommendations;
      } else {
        AppLogger.error(
          'Failed to fetch marker recommendations: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to fetch marker recommendations: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error fetching marker recommendations', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Product Recommendations
  // ==========================================================================

  /// Generate AI product recommendations based on project context
  static Future<Map<String, dynamic>> getProductRecommendations(
    String projectId,
    String authToken, {
    bool autoSearch = false,
    http.Client? client,
  }) async {
    _requireProjectId(projectId);
    http.Client? ownedClient;
    try {
      final basePath = ApiConstants.withProjectId(
        ApiConstants.productRecommendations,
        projectId,
      );
      final baseUri = Uri.parse('${ApiConstants.baseUrl}$basePath');
      final url = autoSearch
          ? baseUri.replace(
              queryParameters: {
                ...baseUri.queryParameters,
                'auto_search': 'true',
              },
            )
          : baseUri;
      final httpClient = client ?? (ownedClient = http.Client());

      AppLogger.info('Generating product recommendations for $projectId');

      final response = await httpClient
          .post(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info(
          'Product recommendations generated: ${(data['recommendations'] as List?)?.length ?? 0} items',
        );
        return data;
      } else {
        AppLogger.error(
          'Failed to get product recommendations: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to get product recommendations: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error getting product recommendations', e);
      rethrow;
    } finally {
      ownedClient?.close();
    }
  }

  /// Select/toggle a product recommendation
  static Future<Map<String, dynamic>> selectProductRecommendation(
    String projectId,
    String authToken,
    String selectedRecommendation,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.productRecommendationSelection, projectId)}',
      );

      AppLogger.info(
        'Selecting product recommendation for $projectId: $selectedRecommendation',
      );

      final response = await http
          .post(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({
              'selected_recommendation': selectedRecommendation,
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Product recommendation selected successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to select product recommendation: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to select product recommendation: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error selecting product recommendation', e);
      rethrow;
    }
  }

  /// Atomically set the full list of selected product recommendations.
  static Future<Map<String, dynamic>> setSelectedRecommendations(
    String projectId,
    String authToken,
    List<String> recommendations,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.selectedProductRecommendations, projectId)}',
      );

      AppLogger.info(
        'Setting selected recommendations for $projectId: ${recommendations.length} items',
      );

      final response = await http
          .put(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({'recommendations': recommendations}),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Selected recommendations set successfully');
        return data;
      } else {
        AppLogger.error(
          'Failed to set selected recommendations: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to set selected recommendations: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error setting selected recommendations', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Product Search & Selection
  // ==========================================================================

  /// Get pre-searched product suggestions organized by category
  static Future<Map<String, dynamic>> getProductSuggestions(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.productSuggestions, projectId)}',
      );

      AppLogger.info('Fetching product suggestions for $projectId');

      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final rawTotalProducts = data['total_products'];
        final totalProducts = rawTotalProducts is num
            ? rawTotalProducts.toInt()
            : int.tryParse(rawTotalProducts?.toString() ?? '');
        final logMessage =
            'Product suggestions fetched: ${totalProducts ?? rawTotalProducts ?? 'unknown'} products';
        if (totalProducts == 0) {
          AppLogger.debug(logMessage);
        } else {
          AppLogger.info(logMessage);
        }
        return data;
      } else {
        AppLogger.error(
          'Failed to get product suggestions: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to get product suggestions: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error getting product suggestions', e);
      rethrow;
    }
  }

  /// Fetch trending products payload for the project.
  /// This can be used as a fast fallback source for the "Like These?" UI.
  static Future<Map<String, dynamic>> getTrendingProducts(
    String projectId,
    String authToken, {
    Duration timeout = const Duration(seconds: 30),
  }) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.trendingProducts, projectId)}',
      );

      AppLogger.info('Fetching trending products for $projectId');

      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info(
          'Trending products fetched: ${data['categories'] is List ? (data['categories'] as List).length : 0} categories',
        );
        return data;
      } else {
        AppLogger.error(
          'Failed to get trending products: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to get trending products: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error getting trending products', e);
      rethrow;
    }
  }

  /// Save user's favorite products from product suggestions
  static Future<Map<String, dynamic>> submitFavoriteProducts(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> favorites,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.favoriteProducts, projectId)}',
      );

      AppLogger.info(
        'Submitting ${favorites.length} favorite products for $projectId',
      );

      final response = await http
          .post(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({'favorites': favorites}),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info(
          'Favorite products submitted: ${data['favorites_count']} saved',
        );
        return data;
      } else {
        AppLogger.error(
          'Failed to submit favorite products: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to submit favorite products: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error submitting favorite products', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Background Jobs & Polling
  // ==========================================================================

  /// Start background product search for recommendations (returns job_id)
  static Future<Map<String, dynamic>> startSearchRecommendations(
    String projectId,
    String authToken,
    List<String> recommendations, {
    String? idempotencyKey,
  }) async {
    _requireProjectId(projectId);
    final url = Uri.parse(
      '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.searchRecommendations, projectId)}',
    );

    final headers = ApiConstants.authHeaders(authToken);
    if (idempotencyKey != null) {
      headers['X-Idempotency-Key'] = idempotencyKey;
    }

    const maxAttempts = 2;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        AppLogger.info(
          'Starting search recommendations job for $projectId (attempt $attempt/$maxAttempts)',
        );

        final response = await http
            .post(
              url,
              headers: headers,
              body: jsonEncode({'recommendations': recommendations}),
            )
            .timeout(const Duration(seconds: 30));

        if (response.statusCode == 200 || response.statusCode == 201) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          AppLogger.info(
            'Search recommendations job started: ${data['job_id']}',
          );
          return data;
        }

        AppLogger.error(
          'Failed to start search recommendations: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to start search recommendations: ${response.statusCode}',
        );
      } on TimeoutException catch (e) {
        if (attempt == maxAttempts) {
          AppLogger.error('Error starting search recommendations', e);
          rethrow;
        }
        const retryDelay = Duration(milliseconds: 1200);
        AppLogger.warning(
          'startSearchRecommendations timed out; retrying in ${retryDelay.inMilliseconds}ms',
        );
        await Future.delayed(retryDelay);
      } on SocketException catch (e) {
        if (attempt == maxAttempts) {
          AppLogger.error('Error starting search recommendations', e);
          rethrow;
        }
        const retryDelay = Duration(milliseconds: 1200);
        AppLogger.warning(
          'startSearchRecommendations socket error; retrying in ${retryDelay.inMilliseconds}ms: $e',
        );
        await Future.delayed(retryDelay);
      } catch (e) {
        final isTransient =
            e.toString().toLowerCase().contains('server disconnected') ||
            e.toString().toLowerCase().contains('connection closed');
        if (!isTransient || attempt == maxAttempts) {
          AppLogger.error('Error starting search recommendations', e);
          rethrow;
        }
        const retryDelay = Duration(milliseconds: 1200);
        AppLogger.warning(
          'startSearchRecommendations transient error; retrying in ${retryDelay.inMilliseconds}ms: $e',
        );
        await Future.delayed(retryDelay);
      }
    }

    throw Exception('Failed to start search recommendations');
  }

  /// Start background image generation (returns job_id)
  static Future<Map<String, dynamic>> startGenerateImage(
    String projectId,
    String authToken, {
    String? idempotencyKey,
  }) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.generateImage, projectId)}',
      );

      AppLogger.info('Starting image generation job for $projectId');

      final headers = ApiConstants.authHeaders(authToken);
      if (idempotencyKey != null) {
        headers['X-Idempotency-Key'] = idempotencyKey;
      }

      final response = await http
          .post(url, headers: headers)
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Image generation job started: ${data['job_id']}');
        return data;
      } else {
        AppLogger.error(
          'Failed to start image generation: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to start image generation: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error starting image generation', e);
      rethrow;
    }
  }

  /// Start background inspiration redesign (returns job_id)
  static Future<Map<String, dynamic>> startInspirationRedesign(
    String projectId,
    String authToken, {
    String? idempotencyKey,
  }) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.inspirationRedesign, projectId)}',
      );

      AppLogger.info('Starting inspiration redesign job for $projectId');

      final headers = ApiConstants.authHeaders(authToken);
      if (idempotencyKey != null) {
        headers['X-Idempotency-Key'] = idempotencyKey;
      }

      final response = await http
          .post(url, headers: headers)
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Inspiration redesign job started: ${data['job_id']}');
        return data;
      } else {
        AppLogger.error(
          'Failed to start inspiration redesign: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to start inspiration redesign: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error starting inspiration redesign', e);
      rethrow;
    }
  }

  /// Apply feedback edits to the existing generated inspiration redesign.
  static Future<Map<String, dynamic>> startRetryRedesign(
    String projectId,
    String authToken,
    String feedback,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.retryRedesign, projectId)}',
      );

      AppLogger.info('Starting retry redesign for $projectId');

      final response = await http
          .post(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({'feedback': feedback}),
          )
          .timeout(const Duration(seconds: 60));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info('Retry redesign completed');
        return data;
      } else {
        AppLogger.error(
          'Failed to start retry redesign: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to start retry redesign: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error starting retry redesign', e);
      rethrow;
    }
  }

  /// Poll job status for a background task
  static Future<Map<String, dynamic>> getJobStatus(
    String projectId,
    String jobId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectAndJobId(ApiConstants.jobStatus, projectId, jobId)}',
      );

      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return data;
      } else {
        if (response.statusCode == 404) {
          AppLogger.warning(
            'Job status not yet visible (404) for $jobId: ${response.body}',
          );
        } else {
          AppLogger.error(
            'Failed to get job status: ${response.statusCode} - ${response.body}',
          );
        }
        throw Exception('Failed to get job status: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('getJobStatus timeout/error for job=$jobId', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Generated Image & Redesign
  // ==========================================================================

  /// Fetch the generated image as binary PNG data.
  /// Unlike other methods, this returns raw bytes (Uint8List) instead of JSON.
  /// The backend may return a FileResponse (image/png) or a 302 redirect to
  /// a Supabase Storage URL — the http package follows redirects automatically.
  /// Fetch just the CDN URL of the generated image (fast, ~200 bytes response).
  /// Returns `null` when the backend stores the image as bytes/base64 only.
  static Future<String?> getGeneratedImageUrl(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.generatedImage, projectId)}?format=url',
      );
      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return data['image_url'] as String?;
      }
      return null;
    } catch (e) {
      AppLogger.warning('getGeneratedImageUrl failed: $e');
      return null;
    }
  }

  static Future<Uint8List> getGeneratedImage(
    String projectId,
    String authToken,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.generatedImage, projectId)}',
      );

      AppLogger.info('Fetching generated image for $projectId');

      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        AppLogger.info(
          'Generated image fetched: ${response.bodyBytes.length} bytes',
        );
        return response.bodyBytes;
      } else {
        AppLogger.error(
          'Failed to fetch generated image: ${response.statusCode}',
        );
        throw Exception(
          'Failed to fetch generated image: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error fetching generated image', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Furniture Analysis & Shopping
  // ==========================================================================

  /// Analyze furniture items at specified image coordinates
  static Future<Map<String, dynamic>> analyzeFurnitureBatch(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selections, {
    String imageType = 'product',
    String mode = 'full',
    Duration timeout = const Duration(seconds: 60),
    http.Client? client,
  }) async {
    _requireProjectId(projectId);
    http.Client? ownedClient;
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.analyzeFurnitureBatch, projectId)}',
      );
      final httpClient = client ?? (ownedClient = http.Client());

      AppLogger.info(
        'Analyzing ${selections.length} furniture items for $projectId (mode=$mode)',
      );

      final response = await httpClient
          .post(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({
              'selections': selections,
              'image_type': imageType,
              'mode': mode,
            }),
          )
          .timeout(timeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info(
          'Furniture analysis complete: ${data['total_items']} items',
        );
        return data;
      } else {
        AppLogger.error(
          'Failed to analyze furniture: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to analyze furniture: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error analyzing furniture', e);
      rethrow;
    } finally {
      ownedClient?.close();
    }
  }

  /// Auto-detect furniture hotspots from a generated image.
  static Future<Map<String, dynamic>> autoDetectFurniture(
    String projectId,
    String authToken, {
    String imageType = 'product',
  }) async {
    _requireProjectId(projectId);
    try {
      final path = ApiConstants.withProjectId(
        ApiConstants.autoDetect,
        projectId,
      );
      final url = Uri.parse(
        '${ApiConstants.baseUrl}$path?image_type=${Uri.encodeQueryComponent(imageType)}',
      );

      AppLogger.info(
        'Auto-detecting furniture for $projectId (imageType=$imageType)',
      );

      final response = await http
          .get(url, headers: ApiConstants.authHeaders(authToken))
          .timeout(const Duration(seconds: 45));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final detections = data['detections'] as List? ?? const [];
        AppLogger.info('Auto-detect complete: ${detections.length} detections');
        return data;
      } else {
        AppLogger.error(
          'Failed to auto-detect furniture: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to auto-detect furniture: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error auto-detecting furniture', e);
      rethrow;
    }
  }

  /// Process selected furniture products (resolve URLs, generate affiliate carts)
  static Future<Map<String, dynamic>> processFurnitureSelection(
    String projectId,
    String authToken,
    List<Map<String, dynamic>> selectedProducts,
  ) async {
    _requireProjectId(projectId);
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.withProjectId(ApiConstants.processFurnitureSelection, projectId)}',
      );

      AppLogger.info(
        'Processing ${selectedProducts.length} furniture selections for $projectId',
      );

      final response = await http
          .post(
            url,
            headers: ApiConstants.authHeaders(authToken),
            body: jsonEncode({'selected_products': selectedProducts}),
          )
          .timeout(const Duration(seconds: 60));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        AppLogger.info(
          'Furniture selection processed: ${data['total_products']} products',
        );
        return data;
      } else {
        AppLogger.error(
          'Failed to process furniture selection: ${response.statusCode} - ${response.body}',
        );
        throw Exception(
          'Failed to process furniture selection: ${response.statusCode}',
        );
      }
    } catch (e) {
      AppLogger.error('Error processing furniture selection', e);
      rethrow;
    }
  }

  // ==========================================================================
  // Job Polling
  // ==========================================================================

  /// Return an adaptive poll interval that starts fast (1 s) and backs off
  /// as the job takes longer (2 s after 20 s, 5 s after 60 s).
  static Duration _adaptivePollInterval(Duration elapsed) {
    if (elapsed.inSeconds < 20) return const Duration(seconds: 1);
    if (elapsed.inSeconds < 60) return const Duration(seconds: 2);
    return const Duration(seconds: 5);
  }

  /// Poll a background job until completion, failure, or timeout.
  /// Returns a [PollingResult] describing the outcome instead of throwing.
  /// Transient network errors are retried with exponential backoff.
  static Future<PollingResult> pollJobUntilDone(
    String projectId,
    String jobId,
    String authToken, {
    Duration pollInterval = const Duration(seconds: 2),
    Duration maxWait = const Duration(seconds: 120),
    void Function(int progressPct, String? phase)? onProgress,
  }) async {
    _requireProjectId(projectId);
    final stopwatch = Stopwatch()..start();
    int consecutiveFailures = 0;
    const maxConsecutiveFailures = 5;
    final random = Random();

    while (stopwatch.elapsed < maxWait) {
      try {
        final status = await getJobStatus(projectId, jobId, authToken);
        // Reset failure counter on successful poll
        if (consecutiveFailures > 0) {
          AppLogger.info(
            'Poll success for job=$jobId resetting failure counter '
            '(was $consecutiveFailures)',
          );
        }
        consecutiveFailures = 0;

        final jobStatus = status['status'] as String?;
        final progressPct = status['progress_pct'] as int? ?? 0;
        final phase = status['phase'] as String?;

        switch (jobStatus) {
          case 'done':
            AppLogger.info('Job $jobId completed successfully');
            return PollingResult.done(status);
          case 'error':
            final error = status['error'] as String? ?? 'Unknown error';
            AppLogger.error('Job $jobId failed: $error');
            return PollingResult.jobFailed(error);
          case 'cancelled':
            AppLogger.info('Job $jobId was cancelled');
            return PollingResult.jobFailed('Job was cancelled');
          case 'queued':
          case 'processing':
            onProgress?.call(progressPct, phase);
            await Future.delayed(_adaptivePollInterval(stopwatch.elapsed));
            break;
          default:
            AppLogger.error('Job $jobId unknown status: $jobStatus');
            return PollingResult.jobFailed('Unknown job status: $jobStatus');
        }
      } on TimeoutException {
        consecutiveFailures++;
        final backoffMs = min(
          2000 * pow(2, consecutiveFailures - 1),
          10000,
        ).toInt();
        final jitter = random.nextInt(500);
        final delayMs = backoffMs + jitter;
        AppLogger.error(
          'Poll timeout for job=$jobId '
          'consecutive=$consecutiveFailures nextDelay=${delayMs}ms',
        );
        if (consecutiveFailures >= maxConsecutiveFailures) {
          return PollingResult.networkFailed(
            'Lost connection to server after $consecutiveFailures consecutive failures',
          );
        }
        await Future.delayed(Duration(milliseconds: delayMs));
      } on SocketException catch (e) {
        consecutiveFailures++;
        final backoffMs = min(
          2000 * pow(2, consecutiveFailures - 1),
          10000,
        ).toInt();
        final jitter = random.nextInt(500);
        final delayMs = backoffMs + jitter;
        AppLogger.error(
          'Poll socket error for job=$jobId '
          'consecutive=$consecutiveFailures nextDelay=${delayMs}ms: $e',
        );
        if (consecutiveFailures >= maxConsecutiveFailures) {
          return PollingResult.networkFailed(
            'Network connection lost: ${e.message}',
          );
        }
        await Future.delayed(Duration(milliseconds: delayMs));
      } catch (e) {
        final isNotFound = e.toString().contains(
          'Failed to get job status: 404',
        );
        if (isNotFound && stopwatch.elapsed < const Duration(seconds: 15)) {
          AppLogger.warning(
            'Job $jobId not found yet (warm-up/replication), retrying...',
          );
          await Future.delayed(const Duration(milliseconds: 1200));
          continue;
        }
        // HTTP 500/502/503 from getJobStatus — treat as transient
        consecutiveFailures++;
        final backoffMs = min(
          2000 * pow(2, consecutiveFailures - 1),
          10000,
        ).toInt();
        final jitter = random.nextInt(500);
        final delayMs = backoffMs + jitter;
        AppLogger.error(
          'Poll error for job=$jobId '
          'consecutive=$consecutiveFailures nextDelay=${delayMs}ms: $e',
        );
        if (consecutiveFailures >= maxConsecutiveFailures) {
          return PollingResult.networkFailed(
            'Server error after $consecutiveFailures consecutive failures',
          );
        }
        await Future.delayed(Duration(milliseconds: delayMs));
      }
    }

    stopwatch.stop();
    AppLogger.error(
      'Job $jobId timed out after ${stopwatch.elapsed.inSeconds}s',
    );
    return PollingResult.timedOut(jobId, stopwatch.elapsed);
  }

  // TODO: Post-MVP — clipSearch(projectId, authToken, {x, y, width, height})
  // TODO: Post-MVP — getInspirationRecommendations(projectId, authToken)
  // TODO: Post-MVP — cancelJob(projectId, jobId, authToken)
  // TODO: Post-MVP — reverseSearchBatch(projectId, authToken, selections)
  // TODO: Post-MVP — autoSelectProduct(projectId, authToken)
  // TODO: Post-MVP — selectProduct(projectId, authToken, {url, title, imageUrl})

  // ==========================================================================
  // Private Helpers
  // ==========================================================================

  /// Detect MIME type from file magic bytes (most reliable), with extension fallback.
  /// HEIC files are re-mapped to image/jpeg since image_picker converts them.
  static Future<String> _detectMimeType(File file) async {
    try {
      // 1. Read first 12 bytes for magic-byte detection
      final stream = file.openRead(0, 12);
      final bytes = await stream.fold<List<int>>(
        [],
        (prev, chunk) => prev..addAll(chunk),
      );
      final mimeFromBytes = lookupMimeType(file.path, headerBytes: bytes);
      if (mimeFromBytes != null && mimeFromBytes.startsWith('image/')) {
        // HEIC/HEIF → treat as JPEG (image_picker converts on iOS)
        if (mimeFromBytes == 'image/heif' || mimeFromBytes == 'image/heic') {
          AppLogger.warning(
            'HEIC image detected via magic bytes, using image/jpeg',
          );
          return 'image/jpeg';
        }
        return mimeFromBytes;
      }
    } catch (e) {
      AppLogger.warning('Magic-byte MIME detection failed: $e');
    }

    // 2. Fallback: extension-based detection
    final ext = file.path.split('.').last.toLowerCase();
    switch (ext) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'webp':
        return 'image/webp';
      case 'heic':
      case 'heif':
        // HEIC → JPEG since image_picker converts on iOS
        return 'image/jpeg';
      default:
        AppLogger.warning('Unknown extension "$ext", defaulting to image/jpeg');
        return 'image/jpeg';
    }
  }
}
