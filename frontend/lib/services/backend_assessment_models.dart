import 'dart:convert';

import 'backend_errors.dart';

const _assessmentIdPattern = r'^asm_[0-9a-f]{32}$';
const _findingIdPattern = r'^fnd_[0-9a-f]{32}$';
const _evidenceIdPattern = r'^evi_[0-9a-f]{32}$';

enum BackendAssessmentStatus { created, pending, running, completed, failed }

enum BackendAdvisoryStatus {
  notReturned,
  disabled,
  unavailable,
  abstained,
  reviewed,
  invalid,
}

/// Persisted passive assessment record returned by the backend API.
class BackendAssessmentRecord {
  final String assessmentId;
  final String targetUrl;
  final BackendAssessmentStatus status;
  final String createdAt;
  final String? updatedAt;
  final String? outcome;
  final BackendAdvisoryReview advisory;

  const BackendAssessmentRecord({
    required this.assessmentId,
    required this.targetUrl,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.outcome,
    required this.advisory,
  });

  factory BackendAssessmentRecord.fromJson(Object? value) {
    final json = _object(value);
    final id = _string(json, 'assessment_id', maxLength: 64);
    final target = _string(json, 'target_url', maxLength: 2048);
    final statusRaw = _string(json, 'status', maxLength: 16);
    final status = switch (statusRaw) {
      'created' => BackendAssessmentStatus.created,
      'pending' => BackendAssessmentStatus.pending,
      'running' => BackendAssessmentStatus.running,
      'completed' => BackendAssessmentStatus.completed,
      'failed' => BackendAssessmentStatus.failed,
      _ => throw const FormatException('Invalid assessment status.'),
    };
    final createdAt = _string(json, 'created_at', maxLength: 80);
    final updatedAt = json['updated_at'];
    if (!RegExp(_assessmentIdPattern).hasMatch(id) ||
        target.trim().isEmpty ||
        DateTime.tryParse(createdAt) == null ||
        (updatedAt != null &&
            (updatedAt is! String || DateTime.tryParse(updatedAt) == null))) {
      throw const FormatException('Invalid assessment record.');
    }

    final rawResult = json['execution_result'];
    if (rawResult != null && rawResult is! Map<String, dynamic>) {
      throw const FormatException('Invalid assessment execution result.');
    }
    final result = rawResult is Map<String, dynamic> ? rawResult : null;
    final outcome = result?['outcome'];
    if (outcome != null && (outcome is! String || outcome.length > 1000)) {
      throw const FormatException('Invalid assessment outcome.');
    }

    return BackendAssessmentRecord(
      assessmentId: id,
      targetUrl: target,
      status: status,
      createdAt: createdAt,
      updatedAt: updatedAt as String?,
      outcome: outcome as String?,
      advisory: BackendAdvisoryReview.fromJson(result?['ai_review']),
    );
  }
}

class BackendAssessmentPage {
  final List<BackendAssessmentRecord> items;
  final int total;
  final int offset;
  final int limit;

  const BackendAssessmentPage({
    required this.items,
    required this.total,
    required this.offset,
    required this.limit,
  });

  factory BackendAssessmentPage.fromJson(Object? value) {
    final json = _object(value);
    if (json.length != 4 ||
        !json.keys.toSet().containsAll(const {
          'items',
          'total',
          'offset',
          'limit',
        })) {
      throw const FormatException('Invalid assessment list response.');
    }
    final rows = json['items'];
    final total = json['total'];
    final offset = json['offset'];
    final limit = json['limit'];
    if (rows is! List ||
        total is! int ||
        offset is! int ||
        limit is! int ||
        total < 0 ||
        offset < 0 ||
        limit < 1 ||
        limit > 100 ||
        rows.length > limit ||
        offset + rows.length > total) {
      throw const FormatException('Invalid assessment list response.');
    }
    return BackendAssessmentPage(
      items: List.unmodifiable(rows.map(BackendAssessmentRecord.fromJson)),
      total: total,
      offset: offset,
      limit: limit,
    );
  }
}

class BackendAssessmentFinding {
  final String findingId;
  final String assessmentId;
  final String ruleId;
  final String title;
  final String description;
  final String severity;
  final String confidence;
  final List<String> evidenceIds;
  final String remediation;

  const BackendAssessmentFinding({
    required this.findingId,
    required this.assessmentId,
    required this.ruleId,
    required this.title,
    required this.description,
    required this.severity,
    required this.confidence,
    required this.evidenceIds,
    required this.remediation,
  });

  factory BackendAssessmentFinding.fromJson(Object? value) {
    final json = _object(value);
    const fields = {
      'finding_id',
      'assessment_id',
      'rule_id',
      'title',
      'description',
      'classification',
      'severity',
      'confidence',
      'status',
      'evidence_ids',
      'remediation',
      'created_at',
    };
    if (json.length != fields.length ||
        !json.keys.toSet().containsAll(fields)) {
      throw const FormatException('Invalid assessment finding response.');
    }
    final findingId = _string(json, 'finding_id', maxLength: 64);
    final assessmentId = _string(json, 'assessment_id', maxLength: 64);
    final evidence = json['evidence_ids'];
    const severities = {'info', 'low', 'medium', 'high', 'critical'};
    const confidences = {'low', 'medium', 'high'};
    if (!RegExp(_findingIdPattern).hasMatch(findingId) ||
        !RegExp(_assessmentIdPattern).hasMatch(assessmentId) ||
        json['classification'] != 'configuration_observation' ||
        json['status'] != 'detected' ||
        !severities.contains(json['severity']) ||
        !confidences.contains(json['confidence']) ||
        evidence is! List ||
        !evidence.every(
          (item) => item is String && RegExp(_evidenceIdPattern).hasMatch(item),
        ) ||
        DateTime.tryParse(_string(json, 'created_at', maxLength: 80)) == null) {
      throw const FormatException('Invalid assessment finding response.');
    }
    return BackendAssessmentFinding(
      findingId: findingId,
      assessmentId: assessmentId,
      ruleId: _string(json, 'rule_id', maxLength: 200),
      title: _string(json, 'title', maxLength: 1000),
      description: _string(json, 'description', maxLength: 4000),
      severity: json['severity'] as String,
      confidence: json['confidence'] as String,
      evidenceIds: List.unmodifiable(evidence.cast<String>()),
      remediation: _string(json, 'remediation', maxLength: 4000),
    );
  }
}

class BackendAssessmentEvidence {
  final String evidenceId;
  final String assessmentId;
  final String observedAt;
  final int? httpStatus;
  final String collectionStatus;

  const BackendAssessmentEvidence({
    required this.evidenceId,
    required this.assessmentId,
    required this.observedAt,
    required this.httpStatus,
    required this.collectionStatus,
  });

  factory BackendAssessmentEvidence.fromJson(Object? value) {
    final json = _object(value);
    const fields = {
      'evidence_id',
      'assessment_id',
      'evidence_type',
      'source',
      'observed_at',
      'http_method',
      'http_status',
      'normalized_headers',
      'header_flags',
      'collection_status',
      'provenance',
    };
    final evidenceId = _string(json, 'evidence_id', maxLength: 64);
    final assessmentId = _string(json, 'assessment_id', maxLength: 64);
    final status = json['collection_status'];
    final httpStatus = json['http_status'];
    if (json.length != fields.length ||
        !json.keys.toSet().containsAll(fields) ||
        !RegExp(_evidenceIdPattern).hasMatch(evidenceId) ||
        !RegExp(_assessmentIdPattern).hasMatch(assessmentId) ||
        json['http_method'] != 'HEAD' ||
        json['source'] != 'passive_head_observation' ||
        !{'observed', 'failed', 'unreachable'}.contains(status) ||
        (httpStatus != null && httpStatus is! int) ||
        json['normalized_headers'] is! Map<String, dynamic> ||
        json['header_flags'] is! Map<String, dynamic> ||
        json['provenance'] is! Map<String, dynamic>) {
      throw const FormatException('Invalid assessment evidence response.');
    }
    final observedAt = _string(json, 'observed_at', maxLength: 80);
    if (DateTime.tryParse(observedAt) == null) {
      throw const FormatException('Invalid assessment evidence response.');
    }
    return BackendAssessmentEvidence(
      evidenceId: evidenceId,
      assessmentId: assessmentId,
      observedAt: observedAt,
      httpStatus: httpStatus as int?,
      collectionStatus: status as String,
    );
  }
}

class BackendAssessmentDetails {
  final BackendAssessmentRecord assessment;
  final List<BackendAssessmentFinding>? findings;
  final String? findingsError;
  final List<BackendAssessmentEvidence>? evidence;
  final String? evidenceError;

  const BackendAssessmentDetails({
    required this.assessment,
    required this.findings,
    required this.findingsError,
    required this.evidence,
    required this.evidenceError,
  });

  BackendAdvisoryReview get advisory =>
      assessment.advisory.validateReferences(findings, evidence);
}

class BackendAdvisoryItem {
  final String findingId;
  final String inferredRisk;
  final String uncertainty;
  final String recommendation;
  final List<String> evidenceIds;

  const BackendAdvisoryItem({
    required this.findingId,
    required this.inferredRisk,
    required this.uncertainty,
    required this.recommendation,
    required this.evidenceIds,
  });
}

class BackendAdvisoryReview {
  final BackendAdvisoryStatus status;
  final List<BackendAdvisoryItem> reviews;

  const BackendAdvisoryReview(this.status, [this.reviews = const []]);

  factory BackendAdvisoryReview.fromJson(Object? value) {
    if (value == null) {
      return const BackendAdvisoryReview(BackendAdvisoryStatus.notReturned);
    }
    try {
      if (jsonEncode(value).length > 16384) {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
      final json = _object(value);
      const allowedKeys = {
        'status',
        'analysis_type',
        'model_id',
        'provider_mode',
        'execution_duration_ms',
        'confidence_calibrated',
        'factual_support',
        'abstention_reason',
        'failure_code',
        'reviews',
      };
      if (!allowedKeys.containsAll(json.keys) ||
          json['analysis_type'] != 'advisory_inference' ||
          json['confidence_calibrated'] != false ||
          json['factual_support'] != 'not_evaluated') {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
      final duration = json['execution_duration_ms'];
      if (duration != null &&
          (duration is! num ||
              !duration.isFinite ||
              duration < 0 ||
              duration > 2000)) {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
      for (final key in const ['model_id', 'provider_mode', 'failure_code']) {
        final field = json[key];
        if (field != null && (field is! String || field.length > 128)) {
          return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
        }
      }
      final status = switch (json['status']) {
        'disabled' => BackendAdvisoryStatus.disabled,
        'unavailable' => BackendAdvisoryStatus.unavailable,
        'abstained' => BackendAdvisoryStatus.abstained,
        'reviewed' => BackendAdvisoryStatus.reviewed,
        _ => BackendAdvisoryStatus.invalid,
      };
      final rawReviews = json['reviews'];
      if (rawReviews is! List || rawReviews.length > 5) {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
      final reviews = <BackendAdvisoryItem>[];
      for (final raw in rawReviews) {
        final item = _object(raw);
        const fields = {
          'finding_id',
          'evidence_ids',
          'inferred_risk',
          'uncertainty',
          'recommendation',
        };
        final evidence = item['evidence_ids'];
        if (item.length != fields.length ||
            !item.keys.toSet().containsAll(fields) ||
            evidence is! List ||
            evidence.isEmpty ||
            evidence.length > 5 ||
            !evidence.every(
              (id) => id is String && RegExp(_evidenceIdPattern).hasMatch(id),
            )) {
          return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
        }
        final findingId = _string(item, 'finding_id', maxLength: 64);
        if (!RegExp(_findingIdPattern).hasMatch(findingId)) {
          return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
        }
        reviews.add(
          BackendAdvisoryItem(
            findingId: findingId,
            evidenceIds: List.unmodifiable(evidence.cast<String>()),
            inferredRisk: _advisoryText(item, 'inferred_risk'),
            uncertainty: _advisoryText(item, 'uncertainty'),
            recommendation: _advisoryText(item, 'recommendation'),
          ),
        );
      }
      if (status == BackendAdvisoryStatus.reviewed && reviews.isEmpty ||
          status != BackendAdvisoryStatus.reviewed && reviews.isNotEmpty) {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
      return BackendAdvisoryReview(status, List.unmodifiable(reviews));
    } catch (_) {
      return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
    }
  }

  BackendAdvisoryReview validateReferences(
    List<BackendAssessmentFinding>? findings,
    List<BackendAssessmentEvidence>? evidence,
  ) {
    if (status != BackendAdvisoryStatus.reviewed) return this;
    if (findings == null || evidence == null) {
      return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
    }
    final findingById = {for (final item in findings) item.findingId: item};
    final evidenceIds = evidence.map((item) => item.evidenceId).toSet();
    final reviewFindingIds = reviews.map((item) => item.findingId).toSet();
    if (reviewFindingIds.length != reviews.length ||
        reviewFindingIds.length != findingById.length ||
        !reviewFindingIds.containsAll(findingById.keys)) {
      return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
    }
    for (final review in reviews) {
      final finding = findingById[review.findingId];
      if (finding == null ||
          review.evidenceIds.any(
            (id) =>
                !finding.evidenceIds.contains(id) || !evidenceIds.contains(id),
          )) {
        return const BackendAdvisoryReview(BackendAdvisoryStatus.invalid);
      }
    }
    return this;
  }
}

Map<String, dynamic> _object(Object? value) {
  if (value is! Map<String, dynamic>) {
    throw const FormatException('Unexpected API response object.');
  }
  return value;
}

String _string(
  Map<String, dynamic> json,
  String key, {
  required int maxLength,
}) {
  final value = json[key];
  if (value is! String || value.isEmpty || value.length > maxLength) {
    throw const FormatException('Unexpected API response text.');
  }
  return value;
}

String _advisoryText(Map<String, dynamic> json, String key) {
  final value = _string(json, key, maxLength: 600);
  if (value.trim().isEmpty || value.contains('\u0000')) {
    throw const FormatException('Invalid advisory response text.');
  }
  return value;
}

/// Converts an optional per-resource error into a safe UI message.
String assessmentResourceError(Object error) => userFacingBackendError(error);
