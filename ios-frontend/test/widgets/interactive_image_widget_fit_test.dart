import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/widgets/interactive_image_widget.dart';
import 'package:spaces/models/shop_product.dart';

void main() {
  group('calculateImageDisplayBounds', () {
    test('contain fit preserves full image with letterboxing bounds', () {
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(1200, 800),
        containerSize: const Size(300, 300),
        fit: BoxFit.contain,
      );

      expect(bounds.displaySize.width, closeTo(300.0, 0.001));
      expect(bounds.displaySize.height, closeTo(200.0, 0.001));
      expect(bounds.displayOffset.dx, closeTo(0.0, 0.001));
      expect(bounds.displayOffset.dy, closeTo(50.0, 0.001));
    });

    test('cover fit fills container and crops overflow', () {
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(1200, 800),
        containerSize: const Size(300, 300),
        fit: BoxFit.cover,
      );

      expect(bounds.displaySize.width, closeTo(450.0, 0.001));
      expect(bounds.displaySize.height, closeTo(300.0, 0.001));
      expect(bounds.displayOffset.dx, closeTo(-75.0, 0.001));
      expect(bounds.displayOffset.dy, closeTo(0.0, 0.001));
    });

    test('portrait image in landscape container — cover crops top/bottom', () {
      // 800x1200 portrait image in 400x300 landscape container
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(800, 1200),
        containerSize: const Size(400, 300),
        fit: BoxFit.cover,
      );

      // Cover scales by the larger ratio: width ratio = 400/800 = 0.5,
      // height ratio = 300/1200 = 0.25 → scale by 0.5
      expect(bounds.displaySize.width, closeTo(400.0, 0.001));
      expect(bounds.displaySize.height, closeTo(600.0, 0.001));
      // Centered vertically: (300 - 600) / 2 = -150
      expect(bounds.displayOffset.dx, closeTo(0.0, 0.001));
      expect(bounds.displayOffset.dy, closeTo(-150.0, 0.001));
    });

    test('landscape image in portrait container — cover crops left/right', () {
      // 1200x800 landscape image in 300x400 portrait container
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(1200, 800),
        containerSize: const Size(300, 400),
        fit: BoxFit.cover,
      );

      // Cover scales by the larger ratio: width ratio = 300/1200 = 0.25,
      // height ratio = 400/800 = 0.5 → scale by 0.5
      expect(bounds.displaySize.width, closeTo(600.0, 0.001));
      expect(bounds.displaySize.height, closeTo(400.0, 0.001));
      // Centered horizontally: (300 - 600) / 2 = -150
      expect(bounds.displayOffset.dx, closeTo(-150.0, 0.001));
      expect(bounds.displayOffset.dy, closeTo(0.0, 0.001));
    });
  });

  group('mapHotspotToRenderedImageTopLeft', () {
    test('round-trip: tap at screen center → normalize → map back → same position', () {
      // Setup: 800x1200 portrait image in 400x800 container, cover fit
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(800, 1200),
        containerSize: const Size(400, 800),
        fit: BoxFit.cover,
      );
      final displaySize = bounds.displaySize;
      final displayOffset = bounds.displayOffset;

      // Simulate a tap at screen center (200, 400)
      const tapX = 200.0;
      const tapY = 400.0;

      // Normalize to image coordinates (what InteractiveImageWidget does)
      final normalizedX = (tapX - displayOffset.dx) / displaySize.width;
      final normalizedY = (tapY - displayOffset.dy) / displaySize.height;

      // Create a hotspot at the normalized coords
      final hotspot = ProductHotspot(
        id: 'test',
        x: normalizedX,
        y: normalizedY,
        itemType: 'furniture',
        label: 'Test',
      );

      // Map back to rendered position
      const markerRadius = 20.0;
      final topLeft = mapHotspotToRenderedImageTopLeft(
        hotspot,
        displaySize,
        displayOffset,
        markerRadius: markerRadius,
      );

      // The marker center should be at the original tap point
      expect(topLeft.dx + markerRadius, closeTo(tapX, 0.001));
      expect(topLeft.dy + markerRadius, closeTo(tapY, 0.001));
    });

    test('cropped hotspot at left edge gets clamped to visible inset', () {
      // Cover fit with negative x offset means left part of image is cropped
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(1200, 800),
        containerSize: const Size(300, 300),
        fit: BoxFit.cover,
      );
      final displaySize = bounds.displaySize;
      final displayOffset = bounds.displayOffset;

      // Hotspot at far left edge of image (x=0.0, y=0.5)
      final hotspot = ProductHotspot(
        id: 'edge',
        x: 0.0,
        y: 0.5,
        itemType: 'furniture',
        label: 'Edge',
      );

      // Without clamping
      final unclamped = mapHotspotToRenderedImageTopLeft(
        hotspot,
        displaySize,
        displayOffset,
      );
      // rawX = offset.dx + 0 * width = -75.0, center = -75.0 - 20 = -95.0
      expect(unclamped.dx, lessThan(0));

      // With clamping to visible container
      final clamped = mapHotspotToRenderedImageTopLeft(
        hotspot,
        displaySize,
        displayOffset,
        visibleSize: const Size(300, 300),
      );

      // Marker center should be clamped to inset, so topLeft = kClampInset - 20
      expect(clamped.dx, closeTo(kClampInset - 20.0, 0.001));
      // Y should be unaffected (it's at center of visible area)
      final rawY = displayOffset.dy + (0.5 * displaySize.height);
      expect(clamped.dy + 20.0, closeTo(rawY, 0.001));
    });

    test('hotspot at right edge gets clamped to visible inset', () {
      final bounds = calculateImageDisplayBounds(
        imageSize: const Size(1200, 800),
        containerSize: const Size(300, 300),
        fit: BoxFit.cover,
      );
      final displaySize = bounds.displaySize;
      final displayOffset = bounds.displayOffset;

      // Hotspot at far right edge of image (x=1.0, y=0.5)
      final hotspot = ProductHotspot(
        id: 'right-edge',
        x: 1.0,
        y: 0.5,
        itemType: 'furniture',
        label: 'Right Edge',
      );

      // With clamping
      final clamped = mapHotspotToRenderedImageTopLeft(
        hotspot,
        displaySize,
        displayOffset,
        visibleSize: const Size(300, 300),
      );

      // rawX = -75 + 1.0 * 450 = 375, clamped to 300 - kClampInset
      expect(clamped.dx + 20.0, closeTo(300.0 - kClampInset, 0.001));
    });

    test('without visibleSize, no clamping is applied', () {
      final hotspot = ProductHotspot(
        id: 'test',
        x: 0.5,
        y: 0.5,
        itemType: 'furniture',
        label: 'Test',
      );

      const displaySize = Size(400, 300);
      const displayOffset = Offset(-50, -25);

      final result = mapHotspotToRenderedImageTopLeft(
        hotspot,
        displaySize,
        displayOffset,
      );

      // rawX = -50 + 0.5 * 400 = 150, rawY = -25 + 0.5 * 300 = 125
      expect(result.dx, closeTo(150.0 - 20.0, 0.001));
      expect(result.dy, closeTo(125.0 - 20.0, 0.001));
    });
  });
}
