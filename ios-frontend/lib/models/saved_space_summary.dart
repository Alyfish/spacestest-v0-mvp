import '../utils/logger.dart';

class SavedSpaceSummary {
  final String id;
  final String status;
  final DateTime createdAt;
  final String? baseImageRef;
  final String? generatedImageRef;
  final String? inspirationGeneratedImageRef;
  final String? spaceType;
  final String? improvementMode;

  const SavedSpaceSummary({
    required this.id,
    required this.status,
    required this.createdAt,
    this.baseImageRef,
    this.generatedImageRef,
    this.inspirationGeneratedImageRef,
    this.spaceType,
    this.improvementMode,
  });

  bool get isGenerated =>
      status == 'IMAGE_GENERATED' || status == 'INSPIRATION_REDESIGN_COMPLETE';

  String? get displayImageUrl {
    if (isGenerated) {
      final ref = inspirationGeneratedImageRef ?? generatedImageRef;
      if (ref != null && ref.startsWith('http')) return ref;
    } else {
      if (baseImageRef != null && baseImageRef!.startsWith('http')) {
        return baseImageRef;
      }
    }
    return null;
  }

  String get displayTitle {
    if (spaceType == null || spaceType!.isEmpty) return 'My Space';
    return spaceType!
        .split('_')
        .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }

  String? get displayMode {
    if (!isGenerated || improvementMode == null) return null;
    switch (improvementMode) {
      case 'iterative':
        return 'Iterative';
      case 'complete_revamp':
        return 'Complete Revamp';
      case 'inspiration':
        return 'Inspiration';
      default:
        return improvementMode;
    }
  }

  static List<SavedSpaceSummary> fromProjectsResponse(
    Map<String, dynamic> json,
  ) {
    final raw = json['projects'];
    final List<SavedSpaceSummary> results = [];

    if (raw is Map<String, dynamic>) {
      AppLogger.debug(
        'SavedSpaceSummary: projects response is Map with ${raw.length} entries',
      );
      for (final entry in raw.entries) {
        final project = entry.value;
        if (project is! Map<String, dynamic>) continue;
        final summary = _parseProject(entry.key, project);
        if (summary != null) results.add(summary);
      }
    } else if (raw is List) {
      AppLogger.debug(
        'SavedSpaceSummary: projects response is List with ${raw.length} entries',
      );
      for (final item in raw) {
        if (item is! Map<String, dynamic>) continue;
        final id = (item['id'] ?? item['project_id'] ?? '').toString();
        if (id.isEmpty) continue;
        final summary = _parseProject(id, item);
        if (summary != null) results.add(summary);
      }
    } else {
      AppLogger.debug(
        'SavedSpaceSummary: unexpected projects type: ${raw.runtimeType}',
      );
    }

    // Sort newest-first
    results.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return results;
  }

  static SavedSpaceSummary? _parseProject(
    String id,
    Map<String, dynamic> project,
  ) {
    final status = (project['status'] ?? '').toString();

    // Support both flat (summaries endpoint) and nested (legacy endpoint) formats
    final ctx = project['context'] as Map<String, dynamic>?;
    final bool isFlat = ctx == null;

    final baseImage = isFlat
        ? project['base_image']?.toString()
        : ctx!['base_image']?.toString();

    // Filter out projects with status NEW and no base image
    if (status == 'NEW' && (baseImage == null || baseImage.isEmpty)) {
      return null;
    }

    DateTime createdAt;
    try {
      createdAt = DateTime.parse(
        project['created_at']?.toString() ?? '',
      );
    } catch (_) {
      createdAt = DateTime.now();
    }

    if (isFlat) {
      return SavedSpaceSummary(
        id: id,
        status: status,
        createdAt: createdAt,
        baseImageRef: baseImage,
        generatedImageRef: project['generated_image']?.toString(),
        inspirationGeneratedImageRef:
            project['inspiration_generated_image']?.toString(),
        spaceType: project['space_type']?.toString(),
        improvementMode: project['improvement_mode']?.toString(),
      );
    }

    return SavedSpaceSummary(
      id: id,
      status: status,
      createdAt: createdAt,
      baseImageRef: baseImage,
      generatedImageRef: ctx!['generated_image_base64']?.toString(),
      inspirationGeneratedImageRef:
          ctx['inspiration_generated_image_base64']?.toString(),
      spaceType: ctx['space_type']?.toString(),
      improvementMode: ctx['improvement_mode']?.toString(),
    );
  }
}
