import 'dart:math';

class MarkerPosition {
  final double x;
  final double y;

  const MarkerPosition({required this.x, required this.y});

  Map<String, dynamic> toJson() {
    return {'x': x, 'y': y};
  }

  factory MarkerPosition.fromJson(Map<String, dynamic> json) {
    return MarkerPosition(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
    );
  }

  @override
  String toString() => 'MarkerPosition(x: $x, y: $y)';

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is MarkerPosition && other.x == x && other.y == y;
  }

  @override
  int get hashCode => x.hashCode ^ y.hashCode;
}

class ImprovementMarker {
  final String id;
  final MarkerPosition position;
  final String description;
  final String color;

  const ImprovementMarker({
    required this.id,
    required this.position,
    required this.description,
    required this.color,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'position': position.toJson(),
      'description': description,
      'color': color,
    };
  }

  factory ImprovementMarker.fromJson(Map<String, dynamic> json) {
    return ImprovementMarker(
      id: json['id'] as String,
      position: MarkerPosition.fromJson(
        json['position'] as Map<String, dynamic>,
      ),
      description: json['description'] as String,
      color: json['color'] as String,
    );
  }

  ImprovementMarker copyWith({
    String? id,
    MarkerPosition? position,
    String? description,
    String? color,
  }) {
    return ImprovementMarker(
      id: id ?? this.id,
      position: position ?? this.position,
      description: description ?? this.description,
      color: color ?? this.color,
    );
  }

  @override
  String toString() {
    return 'ImprovementMarker(id: $id, position: $position, description: $description, color: $color)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ImprovementMarker &&
        other.id == id &&
        other.position == position &&
        other.description == description &&
        other.color == color;
  }

  @override
  int get hashCode {
    return id.hashCode ^
        position.hashCode ^
        description.hashCode ^
        color.hashCode;
  }

  /// Generates a random professional color from Material Design palette
  static String generateRandomColor() {
    final colors = [
      '#1976D2', // Blue 700
      '#388E3C', // Green 700
      '#F57C00', // Orange 700
      '#7B1FA2', // Purple 700
      '#C2185B', // Pink 700
      '#00796B', // Teal 700
      '#5D4037', // Brown 700
      '#455A64', // Blue Grey 700
      '#E64A19', // Deep Orange 700
      '#512DA8', // Deep Purple 700
      '#0097A7', // Cyan 700
      '#689F38', // Light Green 700
      '#FBC02D', // Yellow 700
      '#F44336', // Red 700
    ];

    final random = Random();
    return colors[random.nextInt(colors.length)];
  }
}
