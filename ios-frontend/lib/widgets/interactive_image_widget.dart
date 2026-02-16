import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:ui' as ui;
import 'dart:async';

typedef ImageBoundsCallback =
    Widget Function(
      double imageWidth,
      double imageHeight,
      Size displaySize,
      Offset displayOffset,
    );

@visibleForTesting
class ImageDisplayBounds {
  final Size displaySize;
  final Offset displayOffset;

  const ImageDisplayBounds({
    required this.displaySize,
    required this.displayOffset,
  });
}

@visibleForTesting
ImageDisplayBounds calculateImageDisplayBounds({
  required Size imageSize,
  required Size containerSize,
  required BoxFit fit,
}) {
  if (imageSize.isEmpty || containerSize.isEmpty) {
    return const ImageDisplayBounds(
      displaySize: Size.zero,
      displayOffset: Offset.zero,
    );
  }

  final FittedSizes fitted = applyBoxFit(fit, imageSize, containerSize);
  // Scale from source-sub-rect to destination-sub-rect
  final double scaleX = fitted.destination.width / fitted.source.width;
  final double scaleY = fitted.destination.height / fitted.source.height;
  final displayedWidth = imageSize.width * scaleX;
  final displayedHeight = imageSize.height * scaleY;

  final offsetX = (containerSize.width - displayedWidth) / 2;
  final offsetY = (containerSize.height - displayedHeight) / 2;

  return ImageDisplayBounds(
    displaySize: Size(displayedWidth, displayedHeight),
    displayOffset: Offset(offsetX, offsetY),
  );
}

class InteractiveImageWidget extends StatefulWidget {
  /// Set to true in debug builds to draw image-rect and container-rect borders.
  static bool debugShowImageBounds = false;

  final ImageProvider imageProvider;
  final Function(double x, double y) onImageTap;
  final ImageBoundsCallback? overlayBuilder;
  final BoxFit fit;

  const InteractiveImageWidget({
    super.key,
    required this.imageProvider,
    required this.onImageTap,
    this.overlayBuilder,
    this.fit = BoxFit.cover,
  });

  @override
  State<InteractiveImageWidget> createState() => _InteractiveImageWidgetState();
}

class _InteractiveImageWidgetState extends State<InteractiveImageWidget> {
  ui.Image? _image;
  Size? _imageSize;
  Offset? _imageOffset;

  @override
  void initState() {
    super.initState();
    _loadImage();
  }

  @override
  void didUpdateWidget(InteractiveImageWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.imageProvider != widget.imageProvider) {
      _loadImage();
    }
  }

  Future<void> _loadImage() async {
    try {
      final ImageStream stream = widget.imageProvider.resolve(
        const ImageConfiguration(),
      );
      final completer = Completer<ui.Image>();
      late ImageStreamListener listener;

      listener = ImageStreamListener((ImageInfo info, bool synchronousCall) {
        if (!completer.isCompleted) {
          completer.complete(info.image);
        }
        stream.removeListener(listener);
      });

      stream.addListener(listener);
      final image = await completer.future;

      if (mounted) {
        setState(() {
          _image = image;
        });
      }
    } catch (e) {
      debugPrint('Error loading image: $e');
    }
  }

  void _calculateImageBounds(Size containerSize) {
    final imageWidth = _image?.width.toDouble() ?? containerSize.width;
    final imageHeight = _image?.height.toDouble() ?? containerSize.height;

    if (kDebugMode) {
      debugPrint('InteractiveImage native: ${imageWidth.toInt()}x${imageHeight.toInt()}, '
          'container: ${containerSize.width.toInt()}x${containerSize.height.toInt()}');
    }

    final bounds = calculateImageDisplayBounds(
      imageSize: Size(imageWidth, imageHeight),
      containerSize: containerSize,
      fit: widget.fit,
    );
    final newSize = bounds.displaySize;
    final newOffset = bounds.displayOffset;

    // Only update and trigger rebuild if values have changed
    if (_imageSize != newSize || _imageOffset != newOffset) {
      setState(() {
        _imageSize = newSize;
        _imageOffset = newOffset;
      });
    }
  }

  void _handleTap(TapUpDetails details) {
    if (_imageSize == null || _imageOffset == null) return;

    final tapPosition = details.localPosition;

    // Check if tap is within the image bounds
    final imageRect = Rect.fromLTWH(
      _imageOffset!.dx,
      _imageOffset!.dy,
      _imageSize!.width,
      _imageSize!.height,
    );

    if (!imageRect.contains(tapPosition)) return;

    // Convert tap position to image coordinates
    final relativeX = tapPosition.dx - _imageOffset!.dx;
    final relativeY = tapPosition.dy - _imageOffset!.dy;

    // Convert to normalized coordinates (0-1 range)
    final normalizedX = relativeX / _imageSize!.width;
    final normalizedY = relativeY / _imageSize!.height;

    widget.onImageTap(normalizedX, normalizedY);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final containerSize = Size(constraints.maxWidth, constraints.maxHeight);

        // Calculate image bounds whenever container size changes
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _calculateImageBounds(containerSize);
        });

        return GestureDetector(
          onTapUp: _handleTap,
          behavior: HitTestBehavior.translucent,
          child: SizedBox(
            width: double.infinity,
            height: double.infinity,
            child: Stack(
              fit: StackFit.expand,
              children: [
                // Main image
                Image(
                  image: widget.imageProvider,
                  fit: widget.fit,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: Colors.grey[300],
                      child: const Center(
                        child: Icon(
                          Icons.error_outline,
                          size: 48,
                          color: Colors.grey,
                        ),
                      ),
                    );
                  },
                ),

                // Overlay widgets (markers, etc.)
                if (widget.overlayBuilder != null &&
                    _imageSize != null &&
                    _imageOffset != null)
                  widget.overlayBuilder!(
                    _image?.width.toDouble() ?? _imageSize!.width,
                    _image?.height.toDouble() ?? _imageSize!.height,
                    _imageSize!,
                    _imageOffset!,
                  ),

                // Debug overlay: image rect + container bounds
                if (kDebugMode &&
                    InteractiveImageWidget.debugShowImageBounds &&
                    _imageSize != null &&
                    _imageOffset != null)
                  Positioned(
                    left: _imageOffset!.dx,
                    top: _imageOffset!.dy,
                    child: IgnorePointer(
                      child: Container(
                        width: _imageSize!.width,
                        height: _imageSize!.height,
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.red, width: 2),
                        ),
                        child: Align(
                          alignment: Alignment.topLeft,
                          child: Container(
                            color: Colors.black54,
                            padding: const EdgeInsets.all(4),
                            child: Text(
                              'native: ${_image?.width ?? "?"}x${_image?.height ?? "?"}\n'
                              'display: ${_imageSize!.width.toInt()}x${_imageSize!.height.toInt()}\n'
                              'offset: (${_imageOffset!.dx.toInt()}, ${_imageOffset!.dy.toInt()})\n'
                              'container: ${containerSize.width.toInt()}x${containerSize.height.toInt()}',
                              style: const TextStyle(
                                color: Colors.red,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
