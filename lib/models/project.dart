import 'dart:io';

class Project {
  final String id;
  final String userId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String status;
  final Map<String, dynamic> metadata;

  // Image properties
  final String? projectImageUrl;
  final String? inspirationImageUrl;
  final File? localProjectImage;
  final File? localInspirationImage;

  // Project properties (can be expanded)
  final String? name;
  final String? description;
  final String? spaceChosen;
  final List<String> tags;
  final Map<String, dynamic> designPreferences;

  const Project({
    required this.id,
    required this.userId,
    required this.createdAt,
    required this.updatedAt,
    required this.status,
    this.metadata = const {},
    this.projectImageUrl,
    this.inspirationImageUrl,
    this.localProjectImage,
    this.localInspirationImage,
    this.name,
    this.description,
    this.spaceChosen,
    this.tags = const [],
    this.designPreferences = const {},
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
      projectImageUrl: json['projectImageUrl'],
      inspirationImageUrl: json['inspirationImageUrl'],
      name: json['name'],
      description: json['description'],
      spaceChosen: json['spaceChosen'],
      tags: List<String>.from(json['tags'] ?? []),
      designPreferences: json['designPreferences'] ?? {},
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
      'projectImageUrl': projectImageUrl,
      'inspirationImageUrl': inspirationImageUrl,
      'name': name,
      'description': description,
      'tags': tags,
      'designPreferences': designPreferences,
    };
  }

  Project copyWith({
    String? id,
    String? userId,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? status,
    Map<String, dynamic>? metadata,
    String? projectImageUrl,
    String? inspirationImageUrl,
    File? localProjectImage,
    File? localInspirationImage,
    String? name,
    String? description,
    String? spaceChosen,
    List<String>? tags,
    Map<String, dynamic>? designPreferences,
  }) {
    return Project(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      status: status ?? this.status,
      metadata: metadata ?? this.metadata,
      projectImageUrl: projectImageUrl ?? this.projectImageUrl,
      inspirationImageUrl: inspirationImageUrl ?? this.inspirationImageUrl,
      localProjectImage: localProjectImage ?? this.localProjectImage,
      localInspirationImage:
          localInspirationImage ?? this.localInspirationImage,
      name: name ?? this.name,
      description: description ?? this.description,
      spaceChosen: spaceChosen ?? this.spaceChosen,
      tags: tags ?? this.tags,
      designPreferences: designPreferences ?? this.designPreferences,
    );
  }

  bool get hasProjectImage =>
      projectImageUrl != null || localProjectImage != null;
  bool get hasInspirationImage =>
      inspirationImageUrl != null || localInspirationImage != null;
  bool get isComplete => hasProjectImage && hasInspirationImage;
}
