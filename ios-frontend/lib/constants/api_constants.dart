class ApiConstants {
  // Configurable base URL:
  //   Simulator default: http://localhost:8000/api
  //   Real device: pass --dart-define=API_BASE_URL=http://192.168.x.x:8000/api
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api',
  );

  /// Parsed API base URI used for host-level diagnostics.
  static Uri get baseUri => Uri.parse(baseUrl);

  /// True when API base resolves to local loopback.
  static bool get isLoopbackBaseUrl {
    final host = baseUri.host.toLowerCase();
    return host == 'localhost' || host == '127.0.0.1' || host == '::1';
  }

  // Project CRUD
  static const String createProject = '/projects';
  static const String getProject = '/projects';
  static const String updateProject = '/projects';

  // Image Upload
  static const String uploadImage = '/projects/{project_id}/upload-image';
  static const String uploadInspiration =
      '/projects/{project_id}/inspiration-image';
  static const String uploadInspirationBatch =
      '/projects/{project_id}/inspiration-images-batch';

  // Design Flow
  static const String spaceType = '/projects/{project_id}/space-type';
  static const String improvementMode =
      '/projects/{project_id}/improvement-mode';
  static const String improvementMarkers =
      '/projects/{project_id}/improvement-markers';
  static const String markerRecommendations =
      '/projects/{project_id}/marker-recommendations';
  static const String applyColorScheme =
      '/projects/{project_id}/apply-color-scheme';
  static const String applyStyle = '/projects/{project_id}/apply-style';
  static const String preferredStores =
      '/projects/{project_id}/preferred-stores';
  static const String skipInspirationImages =
      '/projects/{project_id}/skip-inspiration-images';
  static const String skipColorAnalysis =
      '/projects/{project_id}/skip-color-analysis';
  static const String skipStyleAnalysis =
      '/projects/{project_id}/skip-style-analysis';

  // Product Recommendations
  static const String productRecommendations =
      '/projects/{project_id}/product-recommendations';
  static const String productRecommendationSelection =
      '/projects/{project_id}/product-recommendation-selection';
  static const String selectedProductRecommendations =
      '/projects/{project_id}/selected-product-recommendations';

  // "Like These?" Product Search (background job)
  static const String searchRecommendations =
      '/projects/{project_id}/search-recommendations';
  static const String productSuggestions =
      '/projects/{project_id}/product-suggestions';
  static const String favoriteProducts =
      '/projects/{project_id}/favorite-products';
  static const String trendingProducts =
      '/projects/{project_id}/trending-products';

  // Image Generation & Redesign (background jobs)
  static const String inspirationRedesign =
      '/projects/{project_id}/inspiration-redesign';
  static const String generateImage = '/projects/{project_id}/generate-image';
  static const String generatedImage = '/projects/{project_id}/generated-image';
  static const String retryRedesign = '/projects/{project_id}/retry-redesign';

  // Product Search & Furniture Analysis
  static const String productSearch = '/projects/{project_id}/product-search';
  static const String analyzeFurnitureBatch =
      '/projects/{project_id}/analyze-furniture-batch';
  static const String reverseSearchBatch =
      '/projects/{project_id}/reverse-search-batch';
  static const String autoDetect = '/projects/{project_id}/auto-detect';
  static const String processFurnitureSelection =
      '/projects/{project_id}/process-furniture-selection';

  // Product Selection & Auto-Select
  static const String autoSelectProduct =
      '/projects/{project_id}/auto-select-product';
  static const String productSelection =
      '/projects/{project_id}/product-selection';

  // CLIP Search
  static const String clipSearch = '/projects/{project_id}/clip-search';

  // Inspiration Recommendations
  static const String inspirationRecommendations =
      '/projects/{project_id}/inspiration-recommendations';

  // Job Management
  static const String jobStatus = '/projects/{project_id}/job-status/{job_id}';
  static const String cancelJob = '/projects/{project_id}/jobs/{job_id}/cancel';

  // Headers
  static const Map<String, String> defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Map<String, String> authHeaders(String token) => {
    ...defaultHeaders,
    'Authorization': 'Bearer $token',
  };

  /// Headers for multipart uploads — no Content-Type (Dart http sets it with boundary)
  static Map<String, String> authOnlyHeaders(String token) => {
    'Accept': 'application/json',
    'Authorization': 'Bearer $token',
  };

  // Helper: replace {project_id} in path template
  static String withProjectId(String path, String projectId) {
    assert(projectId.isNotEmpty, 'projectId must not be empty');
    return path.replaceAll('{project_id}', projectId);
  }

  // Helper: replace both {project_id} and {job_id} in path template
  static String withProjectAndJobId(
    String path,
    String projectId,
    String jobId,
  ) {
    assert(projectId.isNotEmpty, 'projectId must not be empty');
    assert(jobId.isNotEmpty, 'jobId must not be empty');
    return path
        .replaceAll('{project_id}', projectId)
        .replaceAll('{job_id}', jobId);
  }
}
