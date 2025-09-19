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
    // Convert image coordinates to screen coordinates
    final normalizedX = marker.position.x / imageWidth;
    final normalizedY = marker.position.y / imageHeight;

    final screenX = displayOffset.dx + (normalizedX * displaySize.width);
    final screenY = displayOffset.dy + (normalizedY * displaySize.height);

    // Parse hex color
    Color markerColor;
    try {
      markerColor = Color(int.parse(marker.color.replaceFirst('#', '0xFF')));
    } catch (e) {
      markerColor = AppTheme.primaryColor; // Fallback color
    }

    return Positioned(
      left: screenX - 20, // Center the marker (marker width is 40)
      top: screenY - 20, // Center the marker (marker height is 40)
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.translucent,
        child: Container(
          width: 20,
          height: 20,
          decoration: BoxDecoration(
            color: markerColor,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.2),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: const Center(
            child: Icon(
              Icons.add,
              color: AppTheme.backgroundColor, // White plus sign
              size: 20,
              fontWeight: FontWeight.w900,
            ),
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
