class ApiConstants {
  // Base URL - change this to your actual API endpoint
  static const String baseUrl = 'https://642a5ef5-4d64-4800-ba33-94a5cde07741.mock.pstmn.io';

  // API Endpoints
  static const String makeProject = '/api/projects/create';
  static const String getProject = '/api/projects';
  static const String updateProject = '/api/projects';
  static const String uploadImage = '/api/projects/upload-image';
  static const String uploadInspiration = '/api/projects/upload-inspiration';

  // Headers
  static const Map<String, String> defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Map<String, String> authHeaders(String token) => {
    ...defaultHeaders,
    'Authorization': 'Bearer $token',
  };
}
