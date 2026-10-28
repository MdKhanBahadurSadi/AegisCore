import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

enum EvidenceApprovalStatus {
  approved,
  pendingReview,
  rejected,
  missing;

  String get label {
    switch (this) {
      case EvidenceApprovalStatus.approved:
        return 'Source Review Approved';
      case EvidenceApprovalStatus.pendingReview:
        return 'Pending Source Review';
      case EvidenceApprovalStatus.rejected:
        return 'Source Rejected';
      case EvidenceApprovalStatus.missing:
        return 'Missing Canonical Source';
    }
  }

  Color get color {
    switch (this) {
      case EvidenceApprovalStatus.approved:
        return AppTheme.statusVerified;
      case EvidenceApprovalStatus.pendingReview:
        return AppTheme.statusChallenged;
      case EvidenceApprovalStatus.rejected:
        return AppTheme.statusRejected;
      case EvidenceApprovalStatus.missing:
        return AppTheme.severityCritical;
    }
  }
}

class EvidenceModel {
  final String id;
  final String sourceId;
  final String sourceTitle;
  final String? sourceType;
  final EvidenceApprovalStatus approvalStatus;
  final String excerpt;
  final String? exactVersion;
  final String? filePath;
  final String? canonicalReference;
  final int? lineNumber;
  final int? characterStart;
  final int? characterEnd;
  final int? sourceRevision;
  final int? reviewEventCount;
  final String? approvedAt;
  final List<String> sourceScopeTags;
  final bool? locusMatch;
  final List<String> relatedFindingIds;
  final String provenanceDigest;
  final String? excerptDigest;

  const EvidenceModel({
    required this.id,
    required this.sourceId,
    required this.sourceTitle,
    this.sourceType,
    required this.approvalStatus,
    required this.excerpt,
    this.exactVersion,
    this.filePath,
    this.canonicalReference,
    this.lineNumber,
    this.characterStart,
    this.characterEnd,
    this.sourceRevision,
    this.reviewEventCount,
    this.approvedAt,
    this.sourceScopeTags = const [],
    this.locusMatch,
    this.relatedFindingIds = const [],
    required this.provenanceDigest,
    this.excerptDigest,
  });

  /// Parses one approved-only item returned by `GET /evidence/approved`.
  /// The backend omits local paths, finding links, and claim-entailment labels.
  factory EvidenceModel.fromApprovedApiJson(Object? json) {
    final item = _objectWithKeys(json, const {'source', 'chunk'});
    final source = _objectWithKeys(item['source'], const {
      'source_id',
      'review_state',
      'revision',
      'content_sha256',
      'title',
      'publisher',
      'canonical_reference',
      'publication_date',
      'version',
      'acquired_at',
      'source_type',
      'scope_tags',
      'review_event_count',
      'approved_at',
    });
    final chunk = _objectWithKeys(item['chunk'], const {
      'evidence_id',
      'ordinal',
      'start_offset',
      'end_offset',
      'section',
      'excerpt',
      'content_sha256',
      'citation_source_id',
      'citation_chunk_id',
    });

    final sourceId = source['source_id'];
    final evidenceId = chunk['evidence_id'];
    final contentDigest = source['content_sha256'];
    final excerptDigest = chunk['content_sha256'];
    final rawTags = source['scope_tags'];
    if (source['review_state'] != 'approved' ||
        sourceId is! String ||
        evidenceId is! String ||
        chunk['citation_source_id'] != sourceId ||
        chunk['citation_chunk_id'] != evidenceId ||
        contentDigest is! String ||
        !_sha256Pattern.hasMatch(contentDigest) ||
        excerptDigest is! String ||
        !_sha256Pattern.hasMatch(excerptDigest) ||
        chunk['excerpt'] is! String ||
        (rawTags != null &&
            (rawTags is! List || !rawTags.every((tag) => tag is String)))) {
      throw const FormatException('Unexpected approved evidence response.');
    }

    return EvidenceModel(
      id: evidenceId,
      sourceId: sourceId,
      sourceTitle: _optionalString(source['title']) ?? sourceId,
      sourceType: _optionalString(source['source_type']),
      approvalStatus: EvidenceApprovalStatus.approved,
      excerpt: chunk['excerpt'] as String,
      exactVersion: _optionalString(source['version']),
      canonicalReference: _optionalString(source['canonical_reference']),
      characterStart: _integer(chunk['start_offset']),
      characterEnd: _integer(chunk['end_offset']),
      sourceRevision: _integer(source['revision']),
      reviewEventCount: _integer(source['review_event_count']),
      approvedAt: _optionalString(source['approved_at']),
      sourceScopeTags: rawTags == null
          ? const []
          : List<String>.unmodifiable((rawTags as List).cast<String>()),
      relatedFindingIds: const [],
      provenanceDigest: 'sha256:$contentDigest',
      excerptDigest: 'sha256:$excerptDigest',
    );
  }
}

final _sha256Pattern = RegExp(r'^[0-9a-f]{64}$');

Map<String, Object?> _objectWithKeys(Object? value, Set<String> keys) {
  if (value is! Map<String, dynamic> ||
      value.keys.toSet().length != keys.length ||
      !value.keys.toSet().containsAll(keys)) {
    throw const FormatException('Unexpected approved evidence response.');
  }
  return value;
}

String? _optionalString(Object? value) {
  if (value == null || value is String) return value as String?;
  throw const FormatException('Unexpected approved evidence response.');
}

int _integer(Object? value) {
  if (value is int && value >= 0) return value;
  throw const FormatException('Unexpected approved evidence response.');
}
