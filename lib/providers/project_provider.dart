import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../models/project.dart';
import '../models/marker.dart';
import '../services/api_service.dart';
import '../providers/user_provider.dart';
import '../utils/logger.dart';

enum ProjectStatus { idle, creating, loading, ready, uploading, error }

class ProjectProvider extends ChangeNotifier {
  Project? _currentProject;
  ProjectStatus _status = ProjectStatus.idle;
  String? _errorMessage;
  final List<ImprovementMarker> _markers = [];
  final Uuid _uuid = const Uuid();

  // Room dimensions
  double? _roomWidth;
  double? _roomHeight;
  double? _roomLength;

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

  void _setStatus(ProjectStatus status) {
    _status = status;
    notifyListeners();
  }

  void _setError(String error) {
    _errorMessage = error;
    _setStatus(ProjectStatus.error);
  }

  void clearError() {
    _errorMessage = null;
    if (_status == ProjectStatus.error) {
      _setStatus(
        _currentProject != null ? ProjectStatus.ready : ProjectStatus.idle,
      );
    }
  }

  // Create a new project
  Future<bool> createProject(BuildContext context) async {
    try {
      _setStatus(ProjectStatus.creating);
      _errorMessage = null;

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

      _currentProject = Project.fromJson(response);
      _setStatus(ProjectStatus.ready);

      AppLogger.info('Project created successfully: ${_currentProject!.id}');
      return true;
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
      _setStatus(ProjectStatus.ready);

      AppLogger.info('Project loaded successfully');
      return true;
    } catch (e) {
      AppLogger.error('Failed to load project', e);
      _setError('Failed to load project: ${e.toString()}');
      return false;
    }
  }

  // Set project image (local file)
  Future<void> setProjectImage(File imageFile) async {
    if (_currentProject == null) {
      AppLogger.warning('No active project to set image for');
      return;
    }

    _currentProject = _currentProject!.copyWith(
      localProjectImage: imageFile,
      updatedAt: DateTime.now(),
    );

    AppLogger.info('Project image set locally');
    notifyListeners();
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

  // Upload project image to server
  Future<bool> uploadProjectImage(BuildContext context) async {
    if (_currentProject?.localProjectImage == null) {
      _setError('No project image to upload');
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

      AppLogger.info('Uploading project image...');
      final success = await ApiService.uploadProjectImage(
        _currentProject!.id,
        authToken,
        _currentProject!.localProjectImage!,
        isInspiration: false,
      );

      if (success) {
        _currentProject = _currentProject!.copyWith(updatedAt: DateTime.now());
        _setStatus(ProjectStatus.ready);
        AppLogger.info('Project image uploaded successfully');
        return true;
      } else {
        _setError('Failed to upload project image');
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to upload project image', e);
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

  /// Save chosen approach (mocked API call)
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

  /// Save preferred stores selection (mocked API call)
  Future<bool> savePreferredStores(
    BuildContext context,
    List<String> storeIds,
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
        storeIds,
      );

      _currentProject = _currentProject!.copyWith(
        preferredStores: storeIds,
        designPreferences: {
          ..._currentProject!.designPreferences,
          'preferredStores': storeIds,
        },
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save preferred stores', e);
      _setError('Failed to save preferred stores: ${e.toString()}');
      return false;
    }
  }

  /// Save color palette selection (mocked API call)
  Future<bool> saveColorPalette(
    BuildContext context,
    String paletteId,
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

      await ApiService.submitColorPalette(
        _currentProject!.id,
        authToken,
        paletteId,
      );

      _currentProject = _currentProject!.copyWith(
        designPreferences: {
          ..._currentProject!.designPreferences,
          'colorPalette': paletteId,
        },
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save color palette', e);
      _setError('Failed to save color palette: ${e.toString()}');
      return false;
    }
  }

  /// Save design style selection (mocked API call)
  Future<bool> saveDesignStyle(
    BuildContext context,
    String styleId,
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

      await ApiService.submitDesignStyle(
        _currentProject!.id,
        authToken,
        styleId,
      );

      _currentProject = _currentProject!.copyWith(
        designPreferences: {
          ..._currentProject!.designPreferences,
          'designStyle': styleId,
        },
        updatedAt: DateTime.now(),
      );

      _setStatus(ProjectStatus.ready);
      notifyListeners();
      return true;
    } catch (e) {
      AppLogger.error('Failed to save design style', e);
      _setError('Failed to save design style: ${e.toString()}');
      return false;
    }
  }

  // Clear current project
  void clearProject() {
    _currentProject = null;
    _errorMessage = null;
    _markers.clear();
    _setStatus(ProjectStatus.idle);
    AppLogger.info('Project cleared');
  }

  // Get project image provider (for Image widget)
  ImageProvider? getProjectImageProvider() {
    if (_currentProject?.localProjectImage != null) {
      return FileImage(_currentProject!.localProjectImage!);
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
}
