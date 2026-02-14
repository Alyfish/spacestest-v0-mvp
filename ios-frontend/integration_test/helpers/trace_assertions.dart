import 'package:flutter_test/flutter_test.dart';

int countEndpointHits(
  List<Map<String, dynamic>> traces, {
  required String method,
  required Pattern path,
}) {
  return traces.where((trace) {
    final traceMethod = (trace['method'] as String? ?? '').toUpperCase();
    final tracePath = trace['path'] as String? ?? '';
    return traceMethod == method.toUpperCase() &&
        path.allMatches(tracePath).isNotEmpty;
  }).length;
}

void expectEndpointHit(
  List<Map<String, dynamic>> traces, {
  required String method,
  required Pattern path,
  String? queryKey,
  String? queryValue,
}) {
  final match = traces.where((trace) {
    final traceMethod = (trace['method'] as String? ?? '').toUpperCase();
    final tracePath = trace['path'] as String? ?? '';
    if (traceMethod != method.toUpperCase()) return false;
    if (path.allMatches(tracePath).isEmpty) return false;

    if (queryKey != null) {
      final rawQuery = trace['query'];
      final query = rawQuery is Map
          ? Map<String, dynamic>.from(rawQuery)
          : null;
      final value = query?[queryKey]?.toString();
      if (queryValue != null) {
        return value == queryValue;
      }
      return value != null;
    }

    return true;
  }).isNotEmpty;

  expect(
    match,
    isTrue,
    reason:
        'Expected endpoint not hit: $method $path${queryKey == null ? '' : ' ($queryKey=$queryValue)'}',
  );
}

void expectEndpointOrder(
  List<Map<String, dynamic>> traces,
  List<Map<String, String>> expectedSequence,
) {
  var cursor = -1;
  for (final expected in expectedSequence) {
    final method = (expected['method'] ?? '').toUpperCase();
    final path = expected['path'] ?? '';

    var foundAt = -1;
    for (var i = cursor + 1; i < traces.length; i++) {
      final traceMethod = (traces[i]['method'] as String? ?? '').toUpperCase();
      final tracePath = traces[i]['path'] as String? ?? '';
      if (traceMethod == method && tracePath.contains(path)) {
        foundAt = i;
        break;
      }
    }

    expect(
      foundAt,
      greaterThanOrEqualTo(0),
      reason:
          'Expected ordered endpoint not found after index $cursor: $method $path',
    );
    cursor = foundAt;
  }
}

void expectNoDuplicateSearchKickoff(
  List<Map<String, dynamic>> traces,
  String projectId, {
  int maxAllowed = 0,
}) {
  final path = '/projects/$projectId/search-recommendations';
  final count = countEndpointHits(
    traces,
    method: 'POST',
    path: RegExp('^${RegExp.escape(path)}\$'),
  );
  expect(
    count,
    lessThanOrEqualTo(maxAllowed),
    reason:
        'Expected <=$maxAllowed kickoff calls to $path, but observed $count',
  );
}
