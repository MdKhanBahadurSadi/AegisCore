import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

enum SeverityLevel {
  critical,
  high,
  medium,
  low,
  info;

  String get label {
    switch (this) {
      case SeverityLevel.critical:
        return 'CRITICAL';
      case SeverityLevel.high:
        return 'HIGH';
      case SeverityLevel.medium:
        return 'MEDIUM';
      case SeverityLevel.low:
        return 'LOW';
      case SeverityLevel.info:
        return 'INFORMATIONAL';
    }
  }

  Color get color {
    switch (this) {
      case SeverityLevel.critical:
        return AppTheme.severityCritical;
      case SeverityLevel.high:
        return AppTheme.severityHigh;
      case SeverityLevel.medium:
        return AppTheme.severityMedium;
      case SeverityLevel.low:
        return AppTheme.severityLow;
      case SeverityLevel.info:
        return AppTheme.severityInfo;
    }
  }
}

enum ReviewStatus {
  verified,
  recorded,
  challenged,
  rejected,
  abstained;

  String get label {
    switch (this) {
      case ReviewStatus.verified:
        return 'Verified by Reviewer';
      case ReviewStatus.recorded:
        return 'Recorded';
      case ReviewStatus.challenged:
        return 'Challenged / Incomplete';
      case ReviewStatus.rejected:
        return 'Rejected';
      case ReviewStatus.abstained:
        return 'Abstained';
    }
  }

  Color get color {
    switch (this) {
      case ReviewStatus.verified:
        return AppTheme.statusVerified;
      case ReviewStatus.recorded:
        return AppTheme.accentCyan;
      case ReviewStatus.challenged:
        return AppTheme.statusChallenged;
      case ReviewStatus.rejected:
        return AppTheme.statusRejected;
      case ReviewStatus.abstained:
        return AppTheme.statusAbstained;
    }
  }
}

enum ClaimType {
  fact,
  hypothesis,
  unknown,
  assertion;

  String get label => name.toUpperCase();

  Color get color {
    switch (this) {
      case ClaimType.fact:
        return AppTheme.claimFact;
      case ClaimType.hypothesis:
        return AppTheme.claimHypothesis;
      case ClaimType.unknown:
        return AppTheme.claimUnknown;
      case ClaimType.assertion:
        return AppTheme.claimAssertion;
    }
  }
}

enum ClaimVerdict {
  grounded,
  extrapolated,
  unsupported,
  refuted;

  String get label {
    switch (this) {
      case ClaimVerdict.grounded:
        return 'Grounded in Evidence';
      case ClaimVerdict.extrapolated:
        return 'Extrapolated';
      case ClaimVerdict.unsupported:
        return 'Unsupported by Citations';
      case ClaimVerdict.refuted:
        return 'Refuted by Reviewer';
    }
  }

  Color get color {
    switch (this) {
      case ClaimVerdict.grounded:
        return AppTheme.statusVerified;
      case ClaimVerdict.extrapolated:
        return AppTheme.statusChallenged;
      case ClaimVerdict.unsupported:
        return AppTheme.statusRejected;
      case ClaimVerdict.refuted:
        return AppTheme.severityCritical;
    }
  }
}

class LocusModel {
  final String url;
  final String method;
  final String path;
  final String parameter;
  final String sink;

  const LocusModel({
    required this.url,
    required this.method,
    required this.path,
    required this.parameter,
    required this.sink,
  });

  String get formattedCoordinate => '$method $path [$parameter -> $sink]';
}

class ConfidenceIntervalModel {
  final double lower;
  final double upper;
  final String method;

  const ConfidenceIntervalModel({
    required this.lower,
    required this.upper,
    required this.method,
  });

  String get formatted =>
      '${(lower * 100).toStringAsFixed(1)}% – ${(upper * 100).toStringAsFixed(1)}% ($method)';
}

class ClaimModel {
  final String id;
  final String statement;
  final ClaimType claimType;
  final ClaimVerdict verdict;
  final List<String> citations;
  final String? reviewerNote;

  const ClaimModel({
    required this.id,
    required this.statement,
    required this.claimType,
    required this.verdict,
    required this.citations,
    this.reviewerNote,
  });
}

class FindingModel {
  final String id;
  final String title;
  final String vulnerabilityClass;
  final SeverityLevel severity;
  final ReviewStatus reviewStatus;
  final String targetApp;
  final LocusModel locus;
  final String specialistRole;
  final double? confidenceScore;
  final ConfidenceIntervalModel? confidenceInterval;
  final String? challengeReason;
  final List<ClaimModel> claims;
  final List<String> evidenceIds;
  final bool specialistDisagreement;
  final String? specialistDissentSummary;
  final bool isSyntheticDemo;
  final DateTime? discoveredAt;
  final bool isPersistedRecord;
  final String? dataProvenanceLabel;
  final String? sourceSessionId;
  final String? recordedRationale;
  final String? recordedDecision;

  const FindingModel({
    required this.id,
    required this.title,
    required this.vulnerabilityClass,
    required this.severity,
    required this.reviewStatus,
    required this.targetApp,
    required this.locus,
    required this.specialistRole,
    this.confidenceScore,
    this.confidenceInterval,
    this.challengeReason,
    required this.claims,
    required this.evidenceIds,
    this.specialistDisagreement = false,
    this.specialistDissentSummary,
    this.isSyntheticDemo = true,
    this.discoveredAt,
    this.isPersistedRecord = false,
    this.dataProvenanceLabel,
    this.sourceSessionId,
    this.recordedRationale,
    this.recordedDecision,
  });
}
