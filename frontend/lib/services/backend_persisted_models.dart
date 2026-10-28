// Typed models for records actually persisted by the offline backend.

class BackendDashboardSummary {
  final int sessionCount;
  final int completedCount;
  final int incompleteCount;
  final int failedCount;
  final int verifiedRunCount;
  final int abstainedRunCount;
  final int findingCount;
  final int reportCount;
  final int syntheticOfflineRunCount;
  final int empiricalRunCount;

  const BackendDashboardSummary({
    required this.sessionCount,
    required this.completedCount,
    required this.incompleteCount,
    required this.failedCount,
    required this.verifiedRunCount,
    required this.abstainedRunCount,
    required this.findingCount,
    required this.reportCount,
    required this.syntheticOfflineRunCount,
    required this.empiricalRunCount,
  });

  factory BackendDashboardSummary.fromJson(Object? json) {
    final map = _object(json, const {
      'session_count',
      'completed_count',
      'incomplete_count',
      'failed_count',
      'verified_run_count',
      'abstained_run_count',
      'finding_count',
      'report_count',
      'synthetic_offline_run_count',
      'empirical_run_count',
    });
    int read(String key) {
      final value = map[key];
      if (value is! int || value < 0) throw const FormatException();
      return value;
    }

    return BackendDashboardSummary(
      sessionCount: read('session_count'),
      completedCount: read('completed_count'),
      incompleteCount: read('incomplete_count'),
      failedCount: read('failed_count'),
      verifiedRunCount: read('verified_run_count'),
      abstainedRunCount: read('abstained_run_count'),
      findingCount: read('finding_count'),
      reportCount: read('report_count'),
      syntheticOfflineRunCount: read('synthetic_offline_run_count'),
      empiricalRunCount: read('empirical_run_count'),
    );
  }
}

class BackendStorageStatus {
  final String status;
  final String reason;
  final List<String> supportedRecordTypes;

  const BackendStorageStatus({
    required this.status,
    required this.reason,
    required this.supportedRecordTypes,
  });

  factory BackendStorageStatus.fromJson(Object? json) {
    final map = _object(json, const {
      'status',
      'reason',
      'supported_record_types',
    });
    final status = map['status'];
    final reason = map['reason'];
    final types = map['supported_record_types'];
    if ((status != 'available' && status != 'unavailable') ||
        (reason != 'ready' &&
            reason != 'not_configured' &&
            reason != 'unavailable') ||
        types is! List ||
        !types.every((item) => item is String)) {
      throw const FormatException();
    }
    return BackendStorageStatus(
      status: status as String,
      reason: reason as String,
      supportedRecordTypes: List<String>.unmodifiable(types.cast<String>()),
    );
  }
}

class BackendOfflineSession {
  final String sessionId;
  final String reportId;
  final String runId;
  final String runnerId;
  final String caseId;
  final int repeatIndex;
  final DateTime? startedAt;
  final DateTime? endedAt;
  final String status;
  final String disposition;
  final String fixtureDatasetId;
  final String fixtureDatasetVersion;
  final bool isSynthetic;
  final bool isEmpirical;
  final Map<String, dynamic> result;
  final Map<String, dynamic>? caseContext;

  const BackendOfflineSession({
    required this.sessionId,
    required this.reportId,
    required this.runId,
    required this.runnerId,
    required this.caseId,
    required this.repeatIndex,
    required this.startedAt,
    required this.endedAt,
    required this.status,
    required this.disposition,
    required this.fixtureDatasetId,
    required this.fixtureDatasetVersion,
    required this.isSynthetic,
    required this.isEmpirical,
    required this.result,
    required this.caseContext,
  });

  factory BackendOfflineSession.fromJson(Object? json) {
    final map = _object(json, const {
      'session_id',
      'report_id',
      'run_id',
      'runner_id',
      'case_id',
      'repeat_index',
      'started_at',
      'ended_at',
      'status',
      'disposition',
      'fixture_dataset_id',
      'fixture_dataset_version',
      'execution_mode',
      'is_synthetic',
      'is_empirical',
      'result',
      'case_context',
    });
    DateTime? date(String key) {
      final value = map[key];
      if (value == null) return null;
      if (value is! String || DateTime.tryParse(value) == null) {
        throw const FormatException();
      }
      return DateTime.parse(value);
    }

    for (final key in const [
      'session_id',
      'report_id',
      'run_id',
      'runner_id',
      'case_id',
      'fixture_dataset_id',
      'fixture_dataset_version',
    ]) {
      if (map[key] is! String) throw const FormatException();
    }
    final result = map['result'];
    final caseContext = map['case_context'];
    if (map['repeat_index'] is! int ||
        (map['repeat_index'] as int) < 0 ||
        !{'completed', 'incomplete', 'failed'}.contains(map['status']) ||
        !{'verified', 'rejected', 'abstained'}.contains(map['disposition']) ||
        map['execution_mode'] != 'offline_fixture' ||
        map['is_synthetic'] != true ||
        map['is_empirical'] != false ||
        result is! Map<String, dynamic> ||
        result['case_id'] != map['case_id'] ||
        result['run_id'] != map['run_id'] ||
        !{'verified', 'rejected', 'abstained'}.contains(result['decision']) ||
        result['decision'] != map['disposition'] ||
        result['findings'] is! List ||
        (result['error_status'] != null && result['error_status'] is! String) ||
        result['is_incomplete'] is! bool ||
        (caseContext != null && caseContext is! Map<String, dynamic>)) {
      throw const FormatException();
    }
    return BackendOfflineSession(
      sessionId: map['session_id'] as String,
      reportId: map['report_id'] as String,
      runId: map['run_id'] as String,
      runnerId: map['runner_id'] as String,
      caseId: map['case_id'] as String,
      repeatIndex: map['repeat_index'] as int,
      startedAt: date('started_at'),
      endedAt: date('ended_at'),
      status: map['status'] as String,
      disposition: map['disposition'] as String,
      fixtureDatasetId: map['fixture_dataset_id'] as String,
      fixtureDatasetVersion: map['fixture_dataset_version'] as String,
      isSynthetic: true,
      isEmpirical: false,
      result: Map<String, dynamic>.unmodifiable(result),
      caseContext: caseContext == null
          ? null
          : Map<String, dynamic>.unmodifiable(
              caseContext as Map<String, dynamic>,
            ),
    );
  }
}

class BackendOfflineSessionPage {
  final List<BackendOfflineSession> items;
  final int total;
  final int offset;
  final int limit;

  const BackendOfflineSessionPage({
    required this.items,
    required this.total,
    required this.offset,
    required this.limit,
  });

  factory BackendOfflineSessionPage.fromJson(Object? json) {
    final map = _object(json, const {'items', 'total', 'offset', 'limit'});
    final rawItems = map['items'];
    if (rawItems is! List) throw const FormatException();
    final total = _nonNegativeInt(map['total']);
    final offset = _nonNegativeInt(map['offset']);
    final limit = _nonNegativeInt(map['limit']);
    if (limit < 1 ||
        limit > 100 ||
        rawItems.length > limit ||
        offset + rawItems.length > total) {
      throw const FormatException();
    }
    return BackendOfflineSessionPage(
      items: List<BackendOfflineSession>.unmodifiable(
        rawItems.map(BackendOfflineSession.fromJson),
      ),
      total: total,
      offset: offset,
      limit: limit,
    );
  }
}

class StoredMetricModel {
  final String name;
  final double? value;
  final String status;
  final num? numerator;
  final num? denominator;
  final String definition;

  const StoredMetricModel({
    required this.name,
    required this.value,
    required this.status,
    required this.numerator,
    required this.denominator,
    required this.definition,
  });
}

class StoredEvaluationReportModel {
  final String reportId;
  final DateTime createdAt;
  final String fixtureDatasetId;
  final String fixtureDatasetVersion;
  final String runnerCondition;
  final String runnerId;
  final String executionStatus;
  final bool isSynthetic;
  final bool isEmpirical;
  final int incompleteCaseCount;
  final int failedCaseCount;
  final int totalCases;
  final int truePositives;
  final int falsePositives;
  final int falseNegatives;
  final int trueNegatives;
  final int abstainedCases;
  final int coveredCases;
  final Map<String, StoredMetricModel> metrics;
  final int rawRunCount;
  final int outcomeCount;
  final List<String> failureDiagnostics;

  const StoredEvaluationReportModel({
    required this.reportId,
    required this.createdAt,
    required this.fixtureDatasetId,
    required this.fixtureDatasetVersion,
    required this.runnerCondition,
    required this.runnerId,
    required this.executionStatus,
    required this.isSynthetic,
    required this.isEmpirical,
    required this.incompleteCaseCount,
    required this.failedCaseCount,
    required this.totalCases,
    required this.truePositives,
    required this.falsePositives,
    required this.falseNegatives,
    required this.trueNegatives,
    required this.abstainedCases,
    required this.coveredCases,
    required this.metrics,
    required this.rawRunCount,
    required this.outcomeCount,
    required this.failureDiagnostics,
  });

  factory StoredEvaluationReportModel.fromJson(Object? json) {
    final map = _object(json, const {
      'report_id',
      'created_at',
      'fixture_dataset_id',
      'fixture_dataset_version',
      'runner_condition',
      'runner_id',
      'execution_status',
      'is_synthetic',
      'is_empirical',
      'incomplete_case_count',
      'failed_case_count',
      'total_cases',
      'summary',
      'trial_agreement',
      'payload',
    });
    final summary = map['summary'];
    if (summary is! Map<String, dynamic>) throw const FormatException();
    final rawMetrics = summary['metrics'];
    if (rawMetrics is! Map<String, dynamic>) throw const FormatException();
    final metrics = <String, StoredMetricModel>{};
    for (final entry in rawMetrics.entries) {
      if (entry.value is! Map<String, dynamic>) throw const FormatException();
      final metric = entry.value as Map<String, dynamic>;
      final value = metric['value'];
      final numerator = metric['numerator'];
      final denominator = metric['denominator'];
      if ((value != null && value is! num) ||
          (numerator != null && numerator is! num) ||
          (denominator != null && denominator is! num) ||
          metric['status'] is! String ||
          metric['definition'] is! String) {
        throw const FormatException();
      }
      metrics[entry.key] = StoredMetricModel(
        name: entry.key,
        value: (value as num?)?.toDouble(),
        status: metric['status'] as String,
        numerator: numerator as num?,
        denominator: denominator as num?,
        definition: metric['definition'] as String,
      );
    }
    int readCount(String key) {
      final value = summary[key];
      if (value is! int || value < 0) throw const FormatException();
      return value;
    }

    final createdAtRaw = map['created_at'];
    final dataset = map['fixture_dataset_id'];
    final datasetVersion = map['fixture_dataset_version'];
    final condition = map['runner_condition'];
    final runner = map['runner_id'];
    final status = map['execution_status'];
    final synthetic = map['is_synthetic'];
    final empirical = map['is_empirical'];
    if (createdAtRaw is! String ||
        DateTime.tryParse(createdAtRaw) == null ||
        dataset is! String ||
        datasetVersion is! String ||
        condition is! String ||
        runner is! String ||
        status != 'completed' ||
        synthetic is! bool ||
        empirical is! bool ||
        synthetic != true ||
        empirical != false) {
      throw const FormatException();
    }
    final total = readCount('total_cases');
    final abstained =
        readCount('abstained_positive_count') +
        readCount('abstained_negative_count');
    final rawPayload = map['payload'];
    var rawRunCount = 0;
    var outcomeCount = 0;
    final diagnostics = <String>[];
    if (rawPayload != null) {
      if (rawPayload is! Map<String, dynamic>) throw const FormatException();
      final rawRuns = rawPayload['raw_trial_runs'];
      final outcomes = rawPayload['aggregated_outcomes'];
      if (rawRuns is! List || outcomes is! List) throw const FormatException();
      rawRunCount = rawRuns.length;
      outcomeCount = outcomes.length;
      for (final run in rawRuns) {
        if (run is! Map<String, dynamic>) throw const FormatException();
        final result = run['result'];
        if (result is! Map<String, dynamic>) throw const FormatException();
        final error = result['error_status'];
        if (error is String && error.isNotEmpty) diagnostics.add(error);
      }
      for (final outcome in outcomes) {
        if (outcome is! Map<String, dynamic>) throw const FormatException();
        final error = outcome['error_status'];
        if (error is String && error.isNotEmpty) diagnostics.add(error);
      }
    }
    return StoredEvaluationReportModel(
      reportId: map['report_id'] as String,
      createdAt: DateTime.parse(createdAtRaw),
      fixtureDatasetId: dataset,
      fixtureDatasetVersion: datasetVersion,
      runnerCondition: condition,
      runnerId: runner,
      executionStatus: status as String,
      isSynthetic: synthetic,
      isEmpirical: empirical,
      incompleteCaseCount: _nonNegativeInt(map['incomplete_case_count']),
      failedCaseCount: _nonNegativeInt(map['failed_case_count']),
      totalCases: total,
      truePositives: readCount('tp_count'),
      falsePositives: readCount('fp_count'),
      falseNegatives: readCount('fn_count'),
      trueNegatives: readCount('tn_count'),
      abstainedCases: abstained,
      coveredCases: (total - abstained).clamp(0, total),
      metrics: Map<String, StoredMetricModel>.unmodifiable(metrics),
      rawRunCount: rawRunCount,
      outcomeCount: outcomeCount,
      failureDiagnostics: List<String>.unmodifiable(diagnostics.toSet()),
    );
  }
}

class StoredEvaluationReportPage {
  final List<StoredEvaluationReportModel> items;
  final int total;
  final int offset;
  final int limit;

  const StoredEvaluationReportPage({
    required this.items,
    required this.total,
    required this.offset,
    required this.limit,
  });

  factory StoredEvaluationReportPage.fromJson(Object? json) {
    final map = _object(json, const {'items', 'total', 'offset', 'limit'});
    final items = map['items'];
    if (items is! List) throw const FormatException();
    final total = _nonNegativeInt(map['total']);
    final offset = _nonNegativeInt(map['offset']);
    final limit = _nonNegativeInt(map['limit']);
    if (limit < 1 ||
        limit > 100 ||
        items.length > limit ||
        offset + items.length > total) {
      throw const FormatException();
    }
    return StoredEvaluationReportPage(
      items: List<StoredEvaluationReportModel>.unmodifiable(
        items.map(StoredEvaluationReportModel.fromJson),
      ),
      total: total,
      offset: offset,
      limit: limit,
    );
  }
}

Map<String, dynamic> _object(Object? json, Set<String> keys) {
  if (json is! Map<String, dynamic> ||
      json.length != keys.length ||
      !json.keys.toSet().containsAll(keys)) {
    throw const FormatException('Unexpected persisted backend response shape.');
  }
  return json;
}

int _nonNegativeInt(Object? value) {
  if (value is! int || value < 0) throw const FormatException();
  return value;
}
