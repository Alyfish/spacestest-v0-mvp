import 'dart:io';

class Project {
  final String id;
  final String userId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String status;
  final Map<String, dynamic> metadata;

  // Image properties
  final File? localProjectImage;
  final List<File>? localInspirationImages;

  // Project properties (can be expanded)
  final String? name;
  final String? description;
  final String? spaceChosen;
  final String? approach;
  final List<String> tags;
  final Map<String, dynamic> designPreferences;
  final List<String> preferredStores;

  const Project({
    required this.id,
    required this.userId,
    required this.createdAt,
    required this.updatedAt,
    required this.status,
    this.metadata = const {},
    this.localProjectImage,
    this.localInspirationImages,
    this.name,
    this.description,
    this.spaceChosen,
    this.approach,
    this.tags = const [],
    this.designPreferences = const {},
    this.preferredStores = const [],
  });

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: json['id'] ?? json['projectId'] ?? '',
      userId: json['userId'] ?? '',
      createdAt: DateTime.parse(
        json['createdAt'] ?? DateTime.now().toIso8601String(),
      ),
      updatedAt: DateTime.parse(
        json['updatedAt'] ?? DateTime.now().toIso8601String(),
      ),
      status: json['status'] ?? 'draft',
      metadata: json['metadata'] ?? {},
      name: json['name'],
      description: json['description'],
      spaceChosen: json['spaceChosen'],
      approach:
          json['approach'] ??
          (json['designPreferences'] != null
              ? json['designPreferences']['approach']
              : null),
      tags: List<String>.from(json['tags'] ?? []),
      designPreferences: json['designPreferences'] ?? {},
      preferredStores: List<String>.from(
        json['preferredStores'] ??
            (json['designPreferences'] != null
                ? json['designPreferences']['preferredStores'] ?? []
                : []),
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'userId': userId,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'status': status,
      'metadata': metadata,
      'name': name,
      'description': description,
      'spaceChosen': spaceChosen,
      'approach': approach,
      'tags': tags,
      'designPreferences': designPreferences,
      'preferredStores': preferredStores,
    };
  }

  Project copyWith({
    String? id,
    String? userId,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? status,
    Map<String, dynamic>? metadata,
    File? localProjectImage,
    List<File>? localInspirationImages,
    String? name,
    String? description,
    String? spaceChosen,
    String? approach,
    List<String>? tags,
    Map<String, dynamic>? designPreferences,
    List<String>? preferredStores,
  }) {
    return Project(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      status: status ?? this.status,
      metadata: metadata ?? this.metadata,
      localProjectImage: localProjectImage ?? this.localProjectImage,
      localInspirationImages:
          localInspirationImages ?? this.localInspirationImages,
      name: name ?? this.name,
      description: description ?? this.description,
      spaceChosen: spaceChosen ?? this.spaceChosen,
      approach: approach ?? this.approach,
      tags: tags ?? this.tags,
      designPreferences: designPreferences ?? this.designPreferences,
      preferredStores: preferredStores ?? this.preferredStores,
    );
  }

  bool get hasProjectImage => localProjectImage != null;
  bool get hasInspirationImage =>
      localInspirationImages != null && localInspirationImages!.isNotEmpty;
  bool get hasMultipleInspirationImages =>
      localInspirationImages != null && localInspirationImages!.isNotEmpty;
  List<File> get inspirationImages => localInspirationImages ?? [];
  bool get isComplete => hasProjectImage && hasInspirationImage;
}
