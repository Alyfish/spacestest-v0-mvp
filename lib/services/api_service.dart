import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../constants/api_constants.dart';
import '../models/preferred_store.dart';
import '../utils/logger.dart';

class ApiService {
  static Future<Map<String, dynamic>> createProject(String authToken) async {
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.makeProject}',
      );

      AppLogger.info('Creating new project for user');

      final response = await http.post(
        url,
        headers: ApiConstants.authHeaders(authToken),
        body: jsonEncode({
          'timestamp': DateTime.now().toIso8601String(),
          'platform': Platform.operatingSystem,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        AppLogger.info('Project created successfully: ${data['projectId']}');
        return data;
      } else {
        AppLogger.error(
          'Failed to create project: ${response.statusCode} - ${response.body}',
        );
        throw Exception('Failed to create project: ${response.statusCode}');
      }
    } catch (e) {
      AppLogger.error('Error creating project', e);
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> getProject(
    String projectId,
    String authToken,
  ) async {
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

  /// Mocked fetch of preferred stores list
  static Future<List<PreferredStore>> fetchPreferredStores() async {
    await Future.delayed(const Duration(milliseconds: 500));

    // Demo mode: using local assets where available, empty for fallback icon
    const mockResponse = [
      {
        'id': 'walmart',
        'name': 'Walmart',
        'logoUrl': '', // Uses fallback icon for demo
      },
      {
        'id': 'amazon',
        'name': 'Amazon',
        'logoUrl': 'assets/logo/amazon.png',
      },
      {
        'id': 'ikea',
        'name': 'IKEA',
        'logoUrl': 'assets/logo/ikea.png',
      },
      {
        'id': 'ashley',
        'name': 'Ashley',
        'logoUrl': '', // Uses fallback icon for demo
      },
      {
        'id': 'target',
        'name': 'Target',
        'logoUrl': 'assets/logo/target.png',
      },
      {
        'id': 'wayfair',
        'name': 'Wayfair',
        'logoUrl': '', // Uses fallback icon for demo
      },
      {
        'id': 'etsy',
        'name': 'Etsy',
        'logoUrl': 'assets/logo/etsy.png',
      },
      {
        'id': 'other',
        'name': 'Other',
        'logoUrl': '', // Uses fallback icon
      },
    ];

    AppLogger.info('Fetched ${mockResponse.length} preferred stores (mock)');
    return mockResponse
        .map((storeJson) => PreferredStore.fromJson(storeJson))
        .toList();
  }

  /// Mocked submission of design approach selection
  static Future<Map<String, dynamic>> submitApproach(
    String projectId,
    String authToken,
    String approach,
  ) async {
    await Future.delayed(const Duration(milliseconds: 400));

    AppLogger.info('Submitting approach for $projectId: $approach');

    return {
      'projectId': projectId,
      'approach': approach,
      'updatedAt': DateTime.now().toIso8601String(),
    };
  }

  /// Mocked submission of preferred stores selection
  static Future<Map<String, dynamic>> submitPreferredStores(
    String projectId,
    String authToken,
    List<String> storeIds,
  ) async {
    await Future.delayed(const Duration(milliseconds: 500));

    AppLogger.info('Submitting preferred stores for $projectId: $storeIds');

    return {
      'projectId': projectId,
      'preferredStores': storeIds,
      'updatedAt': DateTime.now().toIso8601String(),
    };
  }

  /// Mocked submission of color palette selection
  static Future<Map<String, dynamic>> submitColorPalette(
    String projectId,
    String authToken,
    String paletteId,
  ) async {
    await Future.delayed(const Duration(milliseconds: 420));

    AppLogger.info('Submitting color palette for $projectId: $paletteId');

    // Real API call placeholder; update endpoint and payload once backend is ready.
    // final url = Uri.parse(
    //   '${ApiConstants.baseUrl}/projects/$projectId/color-palette',
    // );
    // final response = await http.post(
    //   url,
    //   headers: ApiConstants.authHeaders(authToken),
    //   body: jsonEncode({'paletteId': paletteId}),
    // );
    // if (response.statusCode == 200 || response.statusCode == 201) {
    //   final data = jsonDecode(response.body) as Map<String, dynamic>;
    //   return data;
    // } else {
    //   AppLogger.error(
    //     'Failed to submit color palette: ${response.statusCode} - ${response.body}',
    //   );
    //   throw Exception(
    //     'Failed to submit color palette: ${response.statusCode}',
    //   );
    // }

    return {
      'projectId': projectId,
      'colorPalette': paletteId,
      'updatedAt': DateTime.now().toIso8601String(),
    };
  }

  /// Mocked submission of design style selection
  static Future<Map<String, dynamic>> submitDesignStyle(
    String projectId,
    String authToken,
    String styleId,
  ) async {
    await Future.delayed(const Duration(milliseconds: 420));

    AppLogger.info('Submitting design style for $projectId: $styleId');

    return {
      'projectId': projectId,
      'designStyle': styleId,
      'updatedAt': DateTime.now().toIso8601String(),
    };
  }

  static Future<bool> uploadProjectImage(
    String projectId,
    String authToken,
    File imageFile, {
    bool isInspiration = false,
  }) async {
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${isInspiration ? ApiConstants.uploadInspiration : ApiConstants.uploadImage}/?projectId=$projectId',
      );

      // Get file information
      final fileName = imageFile.path.split('/').last;
      final fileExtension = fileName.split('.').last.toLowerCase();
      final mimeType = _getMimeType(fileExtension);
      final fileSize = await imageFile.length();

      AppLogger.info(
        'Uploading ${isInspiration ? 'inspiration' : 'project'} image as file ($fileSize bytes)',
      );

      // Create multipart request
      var request = http.MultipartRequest('POST', url);
      request.headers.addAll(ApiConstants.authHeaders(authToken));

      // Add the actual image file
      request.files.add(
        await http.MultipartFile.fromPath(
          'imageFile',
          imageFile.path,
          filename: fileName,
        ),
      );

      // Add form fields for metadata
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
    try {
      final url = Uri.parse(
        '${ApiConstants.baseUrl}${ApiConstants.uploadInspirationBatch.replaceAll('{project_id}', projectId)}',
      );

      AppLogger.info(
        'Uploading ${imageFiles.length} inspiration images in batch',
      );

      // Create multipart request
      var request = http.MultipartRequest('POST', url);
      request.headers.addAll(ApiConstants.authHeaders(authToken));

      // Add all image files
      for (int i = 0; i < imageFiles.length; i++) {
        final imageFile = imageFiles[i];
        final fileName = imageFile.path.split('/').last;
        final fileExtension = fileName.split('.').last.toLowerCase();
        final mimeType = _getMimeType(fileExtension);

        request.files.add(
          await http.MultipartFile.fromPath(
            'images', // Use same field name for all images so they become an array
            imageFile.path,
            filename: fileName,
          ),
        );

        // Add metadata for each image
        request.fields['fileName_$i'] = fileName;
        request.fields['mimeType_$i'] = mimeType;
      }

      // Add batch metadata
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

  /// Mocked fetch for improvement actions suggested by AI
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

    AppLogger.info('Fetched ${mockActions.length} improvement actions (mock)');

    // Real API call placeholder; wire up auth and parsing once backend is ready.
    // final url = Uri.parse('${ApiConstants.baseUrl}/improvement-actions');
    // final response = await http.get(
    //   url,
    //   headers: ApiConstants.authHeaders('<authToken>'),
    // );
    // if (response.statusCode == 200) {
    //   final data = jsonDecode(response.body) as List<dynamic>;
    //   return data
    //       .cast<Map<String, dynamic>>()
    //       .map((item) => item.map((k, v) => MapEntry(k, v.toString())))
    //       .toList();
    // } else {
    //   AppLogger.error(
    //     'Failed to fetch improvement actions: ${response.statusCode} - ${response.body}',
    //   );
    //   throw Exception(
    //     'Failed to fetch improvement actions: ${response.statusCode}',
    //   );
    // }

    return mockActions;
  }

  // Helper method to determine MIME type from file extension
  static String _getMimeType(String extension) {
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'webp':
        return 'image/webp';
      case 'bmp':
        return 'image/bmp';
      default:
        return 'image/jpeg'; // Default to JPEG
    }
  }

  /// Mocked save improvement markers for a project (demo mode)
  static Future<void> saveImprovementMarkers(
    String projectId,
    List<Map<String, dynamic>> markers,
    String authToken,
  ) async {
    // Demo mode: simulate network delay and succeed
    await Future.delayed(const Duration(milliseconds: 300));

    AppLogger.info(
      'Saving ${markers.length} markers for project: $projectId (demo mode)',
    );
    AppLogger.info('Markers saved successfully (demo mode - local only)');

    // Real API call placeholder; wire up when backend is ready.
    // try {
    //   final url = Uri.parse(
    //     '${ApiConstants.baseUrl}/projects/$projectId/improvement-markers',
    //   );
    //
    //   final response = await http.post(
    //     url,
    //     headers: ApiConstants.authHeaders(authToken),
    //     body: jsonEncode({'markers': markers}),
    //   );
    //
    //   if (response.statusCode == 200 || response.statusCode == 201) {
    //     AppLogger.info('Markers saved successfully');
    //   } else {
    //     AppLogger.error(
    //       'Failed to save markers: ${response.statusCode} - ${response.body}',
    //     );
    //     throw Exception('Failed to save markers: ${response.statusCode}');
    //   }
    // } catch (e) {
    //   AppLogger.error('Error saving markers', e);
    //   rethrow;
    // }
  }
}
