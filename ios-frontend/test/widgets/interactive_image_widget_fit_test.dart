import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/widgets/interactive_image_widget.dart';

void main() {
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
}
