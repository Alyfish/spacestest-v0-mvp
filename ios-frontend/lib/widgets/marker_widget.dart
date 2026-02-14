import 'package:flutter/material.dart';
import '../models/marker.dart';
import '../theme.dart';

class MarkerWidget extends StatelessWidget {
  final ImprovementMarker marker;
  final VoidCallback onTap;
  final double imageWidth;
  final double imageHeight;
  final Size displaySize;
  final Offset displayOffset;

  const MarkerWidget({
    super.key,
    required this.marker,
    required this.onTap,
    required this.imageWidth,
    required this.imageHeight,
    required this.displaySize,
    required this.displayOffset,
  });

  @override
  Widget build(BuildContext context) {
    // Marker positions are already normalized to 0..1.
    final normalizedX = marker.position.x.clamp(0.0, 1.0).toDouble();
    final normalizedY = marker.position.y.clamp(0.0, 1.0).toDouble();

    final screenX = displayOffset.dx + (normalizedX * displaySize.width);
    final screenY = displayOffset.dy + (normalizedY * displaySize.height);

    // Marker styling constants
    const double markerSize = 32.0;

    // Always use primary color (pink) for consistency
    const Color markerColor = AppTheme.primaryColor;

    return Positioned(
      left: screenX - (markerSize / 2),
      top: screenY - (markerSize / 2),
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          width: markerSize,
          height: markerSize,
          decoration: BoxDecoration(
            color: markerColor,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 2.5),
            boxShadow: [
              BoxShadow(
                color: markerColor.withValues(alpha: 0.3),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: const Center(
            child: Icon(Icons.add, color: Colors.white, size: 18),
          ),
        ),
      ),
    );
  }
}

class MarkerOverlay extends StatelessWidget {
  final List<ImprovementMarker> markers;
  final Function(ImprovementMarker) onMarkerTap;
  final double imageWidth;
  final double imageHeight;
  final Size displaySize;
  final Offset displayOffset;

  const MarkerOverlay({
    super.key,
    required this.markers,
    required this.onMarkerTap,
    required this.imageWidth,
    required this.imageHeight,
    required this.displaySize,
    required this.displayOffset,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: markers.map((marker) {
        return MarkerWidget(
          marker: marker,
          onTap: () => onMarkerTap(marker),
          imageWidth: imageWidth,
          imageHeight: imageHeight,
          displaySize: displaySize,
          displayOffset: displayOffset,
        );
      }).toList(),
    );
  }
}
