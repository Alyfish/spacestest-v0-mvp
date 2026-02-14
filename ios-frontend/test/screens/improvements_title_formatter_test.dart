import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/screens/improvements_screen.dart';

void main() {
  group('formatImprovementRecommendationTitle', () {
    test('keeps action-based recommendations unchanged', () {
      expect(
        formatImprovementRecommendationTitle('replace headboard'),
        'replace headboard',
      );
      expect(
        formatImprovementRecommendationTitle('Add floor lamp'),
        'Add floor lamp',
      );
    });

    test('adds Update prefix for noun-only recommendations', () {
      expect(
        formatImprovementRecommendationTitle('headboard'),
        'Update headboard',
      );
      expect(
        formatImprovementRecommendationTitle('  nightstand  '),
        'Update nightstand',
      );
    });
  });
}
