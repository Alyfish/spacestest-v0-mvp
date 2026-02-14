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
  final String? customSpaceDescription;
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
    this.customSpaceDescription,
    this.approach,
    this.tags = const [],
    this.designPreferences = const {},
    this.preferredStores = const [],
  });

  factory Project.fromJson(Map<String, dynamic> json) {
    DateTime parseDate(dynamic value) {
      if (value is String && value.isNotEmpty) {
        final parsed = DateTime.tryParse(value);
        if (parsed != null) return parsed;
      }
      return DateTime.now();
    }

    Map<String, dynamic> parseMap(dynamic value) {
      if (value is Map) return Map<String, dynamic>.from(value);
      return <String, dynamic>{};
    }

    List<String> parseStringList(dynamic value) {
      if (value is List) {
        return value.map((item) => item.toString()).toList();
      }
      return const <String>[];
    }

    final context = parseMap(json['context']);
    final contextPreferences = <String, dynamic>{
      if (context['color_analysis'] != null)
        'colorAnalysis': context['color_analysis'],
      if (context['style_analysis'] != null)
        'styleAnalysis': context['style_analysis'],
      if (context['design_style'] != null)
        'designStyle': context['design_style'],
      if (context['color_scheme'] != null)
        'colorScheme': context['color_scheme'],
    };
    final designPreferences = {
      ...contextPreferences,
      ...parseMap(json['designPreferences'] ?? json['design_preferences']),
    };
    final metadata = {
      ...parseMap(json['metadata']),
      if (context.isNotEmpty) 'context': context,
    };
    final preferredStores = parseStringList(
      json['preferredStores'] ??
          json['preferred_stores'] ??
          context['preferred_stores'] ??
          context['preferredStores'] ??
          designPreferences['preferredStores'] ??
          designPreferences['preferred_stores'],
    );

    final rawSpaceChosen =
        json['spaceChosen'] ??
        json['space_type'] ??
        json['spaceType'] ??
        context['space_type'] ??
        context['spaceType'];
    final rawApproach =
        json['approach'] ??
        json['improvement_mode'] ??
        context['improvement_mode'] ??
        context['improvementMode'] ??
        designPreferences['approach'];
    final rawCustomSpaceDescription =
        json['customSpaceDescription'] ?? json['custom_space_description'];

    return Project(
      id: json['id'] ?? json['project_id'] ?? json['projectId'] ?? '',
      userId: (json['userId'] ?? json['user_id'] ?? '').toString(),
      createdAt: parseDate(json['createdAt'] ?? json['created_at']),
      updatedAt: parseDate(json['updatedAt'] ?? json['updated_at']),
      status: json['status'] ?? 'draft',
      metadata: metadata,
      name: json['name'],
      description: json['description'],
      spaceChosen: rawSpaceChosen?.toString(),
      customSpaceDescription: rawCustomSpaceDescription?.toString(),
      approach: rawApproach?.toString(),
      tags: parseStringList(json['tags']),
      designPreferences: designPreferences,
      preferredStores: preferredStores,
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
      'customSpaceDescription': customSpaceDescription,
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
    String? customSpaceDescription,
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
      customSpaceDescription:
          customSpaceDescription ?? this.customSpaceDescription,
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
