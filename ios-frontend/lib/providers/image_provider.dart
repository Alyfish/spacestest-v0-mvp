import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' as widgets;
import 'package:image_picker/image_picker.dart';

class CapturedImageProvider extends ChangeNotifier {
  File? _capturedImage;
  Uint8List? _imageBytes;
  String? _imagePath;
  bool _isLoading = false;

  // Getters
  File? get capturedImage => _capturedImage;
  Uint8List? get imageBytes => _imageBytes;
  String? get imagePath => _imagePath;
  bool get isLoading => _isLoading;
  bool get hasImage => _capturedImage != null;

  // Image picker instance
  final ImagePicker _picker = ImagePicker();

  // Set captured image
  Future<void> setCapturedImage(File imageFile) async {
    _isLoading = true;
    notifyListeners();

    try {
      _capturedImage = imageFile;
      _imagePath = imageFile.path;
      
      // Read image bytes for API calls
      _imageBytes = await imageFile.readAsBytes();
      
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      throw Exception('Failed to process image: $e');
    }
  }

  // Take photo using camera
  Future<File?> takePhoto() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
        preferredCameraDevice: CameraDevice.rear,
      );

      if (photo != null) {
        final File imageFile = File(photo.path);
        await setCapturedImage(imageFile);
        return imageFile;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to take photo: $e');
    }
  }

  // Pick image from gallery
  Future<File?> pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );

      if (image != null) {
        final File imageFile = File(image.path);
        await setCapturedImage(imageFile);
        return imageFile;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to pick image: $e');
    }
  }

  // Clear captured image
  void clearImage() {
    _capturedImage = null;
    _imageBytes = null;
    _imagePath = null;
    _isLoading = false;
    notifyListeners();
  }

  // Confirm selection (this would trigger API call to backend)
  Future<bool> confirmSelection() async {
    if (_imageBytes == null) {
      throw Exception('No image to confirm');
    }

    _isLoading = true;
    notifyListeners();

    try {
      // TODO: Implement API call to send binary data to backend
      // Example API call structure:
      /*
      final response = await http.post(
        Uri.parse('YOUR_API_ENDPOINT'),
        headers: {
          'Content-Type': 'application/octet-stream',
          // Add other headers as needed
        },
        body: _imageBytes,
      );
      
      if (response.statusCode == 200) {
        // Handle successful upload
        return true;
      } else {
        throw Exception('Upload failed: ${response.statusCode}');
      }
      */
      
      // Simulate API call for now
      await Future.delayed(const Duration(seconds: 2));
      
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      throw Exception('Failed to upload image: $e');
    }
  }

  // Get image for display
  widgets.ImageProvider getImageProvider() {
    if (_capturedImage != null) {
      return widgets.FileImage(_capturedImage!);
    }
    throw Exception('No image available');
  }
}
