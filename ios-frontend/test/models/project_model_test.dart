import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/models/project.dart';

void main() {
  group('Project.fromJson — snake_case backend responses', () {
    test('parses project_id correctly', () {
      final json = {
        'project_id': 'abc-123-def',
        'status': 'NEW',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {},
      };
      final project = Project.fromJson(json);
      expect(project.id, 'abc-123-def');
    });

    test('parses space_type from nested context', () {
      final json = {
        'project_id': 'p1',
        'status': 'SPACE_TYPE_SELECTED',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {
          'space_type': 'bedroom',
        },
      };
      final project = Project.fromJson(json);
      expect(project.spaceChosen, 'bedroom');
    });

    test('parses improvement_mode from context', () {
      final json = {
        'project_id': 'p2',
        'status': 'MODE_SELECTED',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {
          'improvement_mode': 'iterative',
        },
      };
      final project = Project.fromJson(json);
      expect(project.approach, 'iterative');
    });

    test('parses preferred_stores from context', () {
      final json = {
        'project_id': 'p3',
        'status': 'STORES_SET',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {
          'preferred_stores': ['IKEA', 'West Elm', 'CB2'],
        },
      };
      final project = Project.fromJson(json);
      expect(project.preferredStores, ['IKEA', 'West Elm', 'CB2']);
    });

    test('parses user_id from snake_case', () {
      final json = {
        'project_id': 'p4',
        'user_id': 'user-uuid-123',
        'status': 'NEW',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {},
      };
      final project = Project.fromJson(json);
      expect(project.userId, 'user-uuid-123');
    });

    test('parses full backend response with all fields', () {
      final json = {
        'project_id': 'full-test-id',
        'user_id': 'user-001',
        'status': 'PRODUCT_RECOMMENDATIONS_READY',
        'created_at': '2026-02-10T08:30:00Z',
        'updated_at': '2026-02-10T09:15:00Z',
        'context': {
          'space_type': 'living_room',
          'improvement_mode': 'complete_revamp',
          'preferred_stores': ['Target', 'Wayfair'],
          'color_analysis': {
            'design_philosophy': 'Modern warmth',
            'palette_name': 'Sunset Glow',
          },
          'style_analysis': {
            'style_overview': 'Scandinavian minimalism',
          },
          'design_style': 'Scandinavian',
          'color_scheme': ['#FF5733', '#C70039'],
        },
      };
      final project = Project.fromJson(json);
      expect(project.id, 'full-test-id');
      expect(project.userId, 'user-001');
      expect(project.spaceChosen, 'living_room');
      expect(project.approach, 'complete_revamp');
      expect(project.preferredStores, ['Target', 'Wayfair']);
      expect(project.designPreferences['colorAnalysis'], isNotNull);
      expect(project.designPreferences['styleAnalysis'], isNotNull);
      expect(project.designPreferences['designStyle'], 'Scandinavian');
    });

    test('handles missing context gracefully', () {
      final json = {
        'project_id': 'p5',
        'status': 'NEW',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
      };
      final project = Project.fromJson(json);
      expect(project.id, 'p5');
      expect(project.spaceChosen, isNull);
      expect(project.approach, isNull);
      expect(project.preferredStores, isEmpty);
    });

    test('handles null context values', () {
      final json = {
        'project_id': 'p6',
        'status': 'NEW',
        'created_at': '2026-02-10T12:00:00Z',
        'updated_at': '2026-02-10T12:00:00Z',
        'context': {
          'space_type': null,
          'improvement_mode': null,
          'preferred_stores': null,
        },
      };
      final project = Project.fromJson(json);
      expect(project.spaceChosen, isNull);
      expect(project.approach, isNull);
      expect(project.preferredStores, isEmpty);
    });

    test('camelCase fallback still works (legacy)', () {
      final json = {
        'id': 'legacy-id',
        'userId': 'legacy-user',
        'createdAt': '2026-01-01T00:00:00Z',
        'updatedAt': '2026-01-01T00:00:00Z',
        'status': 'draft',
        'spaceChosen': 'kitchen',
        'approach': 'iterative',
        'preferredStores': ['Amazon'],
        'context': {},
      };
      final project = Project.fromJson(json);
      expect(project.id, 'legacy-id');
      expect(project.userId, 'legacy-user');
      expect(project.spaceChosen, 'kitchen');
      expect(project.approach, 'iterative');
      expect(project.preferredStores, ['Amazon']);
    });
  });

  group('Project.toJson', () {
    test('round-trip: toJson produces expected keys', () {
      final project = Project(
        id: 'rt-1',
        userId: 'user-rt',
        createdAt: DateTime.parse('2026-02-10T12:00:00Z'),
        updatedAt: DateTime.parse('2026-02-10T12:00:00Z'),
        status: 'NEW',
        spaceChosen: 'bedroom',
        approach: 'iterative',
        preferredStores: ['IKEA'],
      );
      final json = project.toJson();
      expect(json['id'], 'rt-1');
      expect(json['spaceChosen'], 'bedroom');
      expect(json['preferredStores'], ['IKEA']);
    });
  });

  group('Project.copyWith', () {
    test('copies with new space', () {
      final original = Project(
        id: 'cw-1',
        userId: 'u1',
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        status: 'NEW',
      );
      final copied = original.copyWith(spaceChosen: 'kitchen');
      expect(copied.spaceChosen, 'kitchen');
      expect(copied.id, 'cw-1'); // unchanged
    });
  });
}
