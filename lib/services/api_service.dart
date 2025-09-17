import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../constants/api_constants.dart';
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
        'Uploading ${isInspiration ? 'inspiration' : 'project'} image as file (${fileSize} bytes)',
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
}
