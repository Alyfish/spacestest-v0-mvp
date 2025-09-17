import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/project.dart';
import '../services/api_service.dart';
import '../providers/user_provider.dart';
import '../utils/logger.dart';

enum ProjectStatus { idle, creating, loading, ready, uploading, error }

class ProjectProvider extends ChangeNotifier {
  Project? _currentProject;
  ProjectStatus _status = ProjectStatus.idle;
  String? _errorMessage;

  // Getters
  Project? get currentProject => _currentProject;
  ProjectStatus get status => _status;
  String? get errorMessage => _errorMessage;
  bool get hasProject => _currentProject != null;
  bool get isLoading =>
      _status == ProjectStatus.loading || _status == ProjectStatus.creating;
  bool get hasProjectImage => _currentProject?.hasProjectImage ?? false;
  bool get hasInspirationImage => _currentProject?.hasInspirationImage ?? false;

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

  // Set inspiration image (local file)
  Future<void> setInspirationImage(File imageFile) async {
    if (_currentProject == null) {
      AppLogger.warning('No active project to set inspiration image for');
      return;
    }

    _currentProject = _currentProject!.copyWith(
      localInspirationImage: imageFile,
      updatedAt: DateTime.now(),
    );

    AppLogger.info('Inspiration image set locally');
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
        _currentProject = _currentProject!.copyWith(
          updatedAt: DateTime.now(),
        );
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

  // Upload inspiration image to server
  Future<bool> uploadInspirationImage(BuildContext context) async {
    if (_currentProject?.localInspirationImage == null) {
      _setError('No inspiration image to upload');
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

      AppLogger.info('Uploading inspiration image...');
      final success = await ApiService.uploadProjectImage(
        _currentProject!.id,
        authToken,
        _currentProject!.localInspirationImage!,
        isInspiration: true,
      );

      if (success) {
        _currentProject = _currentProject!.copyWith(
          updatedAt: DateTime.now(),
        );
        _setStatus(ProjectStatus.ready);
        AppLogger.info('Inspiration image uploaded successfully');
        return true;
      } else {
        _setError('Failed to upload inspiration image');
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to upload inspiration image', e);
      _setError('Failed to upload inspiration image: ${e.toString()}');
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

  // Clear current project
  void clearProject() {
    _currentProject = null;
    _errorMessage = null;
    _setStatus(ProjectStatus.idle);
    AppLogger.info('Project cleared');
  }

  // Get project image provider (for Image widget)
  ImageProvider? getProjectImageProvider() {
    if (_currentProject?.localProjectImage != null) {
      return FileImage(_currentProject!.localProjectImage!);
    } else if (_currentProject?.projectImageUrl != null) {
      return NetworkImage(_currentProject!.projectImageUrl!);
    }
    return null;
  }

  // Get inspiration image provider (for Image widget)
  ImageProvider? getInspirationImageProvider() {
    if (_currentProject?.localInspirationImage != null) {
      return FileImage(_currentProject!.localInspirationImage!);
    } else if (_currentProject?.inspirationImageUrl != null) {
      return NetworkImage(_currentProject!.inspirationImageUrl!);
    }
    return null;
  }
}
