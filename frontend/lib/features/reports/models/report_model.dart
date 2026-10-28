class CategoryMetricModel {
  final String categoryName;
  final int totalCases;
  final int truePositives;
  final int falsePositives;
  final int falseNegatives;
  final int trueNegatives;
  final double precision;
  final double recall;
  final double f1Score;

  const CategoryMetricModel({
    required this.categoryName,
    required this.totalCases,
    required this.truePositives,
    required this.falsePositives,
    required this.falseNegatives,
    required this.trueNegatives,
    required this.precision,
    required this.recall,
    required this.f1Score,
  });
}

class EvaluationReportModel {
  final String runId;
  final DateTime timestamp;
  final String targetSuite;
  final int totalCases;
  final int truePositives;
  final int falsePositives;
  final int trueNegatives;
  final int falseNegatives;
  final double precision;
  final double recall;
  final double specificity;
  final double f1Score;
  final double abstentionRate;
  final double coverage;
  final double evidenceGroundingRate;
  final double citationValidationRate;
  final int incompleteCases;
  final int failedCases;
  final int reviewerRejections;
  final int specialistDisagreements;
  final Map<String, CategoryMetricModel> categoryBreakdown;
  final bool isSyntheticDemo;
  final List<String> limitations;

  const EvaluationReportModel({
    required this.runId,
    required this.timestamp,
    required this.targetSuite,
    required this.totalCases,
    required this.truePositives,
    required this.falsePositives,
    required this.trueNegatives,
    required this.falseNegatives,
    required this.precision,
    required this.recall,
    required this.specificity,
    required this.f1Score,
    required this.abstentionRate,
    required this.coverage,
    required this.evidenceGroundingRate,
    required this.citationValidationRate,
    required this.incompleteCases,
    required this.failedCases,
    required this.reviewerRejections,
    required this.specialistDisagreements,
    required this.categoryBreakdown,
    required this.isSyntheticDemo,
    required this.limitations,
  });
}
