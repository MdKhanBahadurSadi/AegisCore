import '../features/findings/models/finding_model.dart';
import '../features/evidence/models/evidence_model.dart';
import '../features/reports/models/report_model.dart';

/// Explicitly labeled synthetic demo fixtures for AEGISCORE AI frontend.
///
/// CAUTION: These records are structured synthetic fixtures designed to verify
/// UI/UX rendering, navigation, and state transitions. They do NOT represent
/// live vulnerability assessments or empirically adjudicated benchmark results.
class MockDemoData {
  MockDemoData._();

  static const bool isDemoData = true;

  static final List<FindingModel> findings = [
    FindingModel(
      id: 'FIND-JS-01',
      title: 'SQL Injection in Product Search Query via String Concatenation',
      vulnerabilityClass: 'sql_injection',
      severity: SeverityLevel.critical,
      reviewStatus: ReviewStatus.verified,
      targetApp: 'OWASP Juice Shop (v17.1.1)',
      locus: const LocusModel(
        url: 'http://localhost:3000/rest/products/search',
        method: 'GET',
        path: '/rest/products/search',
        parameter: 'q',
        sink: 'sequelize.query() in routes/search.ts:32',
      ),
      specialistRole: 'sql_injection_analyst',
      confidenceScore: 0.94,
      confidenceInterval: const ConfidenceIntervalModel(
        lower: 0.812,
        upper: 0.983,
        method: 'Wilson Score (95%)',
      ),
      claims: const [
        ClaimModel(
          id: 'CLM-01',
          statement:
              'The parameter "q" is directly concatenated into a raw SQL query without parameterization.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-JS-AST-02'],
        ),
        ClaimModel(
          id: 'CLM-02',
          statement:
              'A single apostrophe payload (\') generates an unhandled SQLite syntax error response.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-JS-SQLI-01'],
        ),
        ClaimModel(
          id: 'CLM-03',
          statement:
              'UNION SELECT payloads allow full exfiltration of the Users table credentials.',
          claimType: ClaimType.hypothesis,
          verdict: ClaimVerdict.extrapolated,
          citations: ['EVID-JS-SQLI-01'],
          reviewerNote:
              'Adversarial reviewer verified payload injection but noted exfiltration query requires authentication context.',
        ),
      ],
      evidenceIds: const ['EVID-JS-SQLI-01', 'EVID-JS-AST-02'],
      specialistDisagreement: false,
      isSyntheticDemo: true,
      discoveredAt: DateTime.now().subtract(
        const Duration(hours: 2, minutes: 15),
      ),
    ),
    FindingModel(
      id: 'FIND-DVWA-01',
      title: 'Reflected Cross-Site Scripting in Vulnerability Testbed',
      vulnerabilityClass: 'cross_site_scripting',
      severity: SeverityLevel.high,
      reviewStatus: ReviewStatus.verified,
      targetApp: 'Damn Vulnerable Web App (DVWA v1.10)',
      locus: const LocusModel(
        url: 'http://localhost:8080/vulnerabilities/xss_r/',
        method: 'GET',
        path: '/vulnerabilities/xss_r/',
        parameter: 'name',
        sink: 'echo in vulnerabilities/xss_r/source/low.php:8',
      ),
      specialistRole: 'xss_specialist',
      confidenceScore: 0.89,
      confidenceInterval: const ConfidenceIntervalModel(
        lower: 0.741,
        upper: 0.956,
        method: 'Wilson Score (95%)',
      ),
      claims: const [
        ClaimModel(
          id: 'CLM-04',
          statement:
              'Parameter "name" is rendered into response HTML without encoding or sanitization in low security mode.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-DVWA-XSS-01'],
        ),
        ClaimModel(
          id: 'CLM-05',
          statement:
              'Attackers can execute arbitrary JavaScript within the victim browser session.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-DVWA-XSS-01'],
        ),
      ],
      evidenceIds: const ['EVID-DVWA-XSS-01'],
      specialistDisagreement: false,
      isSyntheticDemo: true,
      discoveredAt: DateTime.now().subtract(
        const Duration(hours: 4, minutes: 30),
      ),
    ),
    FindingModel(
      id: 'FIND-JS-CHALLENGE-02',
      title: 'Speculative Remote Code Execution via Insecure YAML Parsing',
      vulnerabilityClass: 'insecure_deserialization',
      severity: SeverityLevel.critical,
      reviewStatus: ReviewStatus.rejected,
      targetApp: 'OWASP Juice Shop (v17.1.1)',
      locus: const LocusModel(
        url: 'http://localhost:3000/b2b/v2/orders',
        method: 'POST',
        path: '/b2b/v2/orders',
        parameter: 'orderFile',
        sink: 'yaml.load() speculative',
      ),
      specialistRole: 'deserialization_specialist',
      confidenceScore: 0.35,
      confidenceInterval: const ConfidenceIntervalModel(
        lower: 0.162,
        upper: 0.598,
        method: 'Wilson Score (95%)',
      ),
      challengeReason:
          'REJECTED by Adversarial Reviewer: Specialist jumped from a package dependency on js-yaml to an unverified RCE claim without providing locus transaction evidence or demonstrating payload execution.',
      claims: const [
        ClaimModel(
          id: 'CLM-06',
          statement:
              'The application imports js-yaml v3.13.1 which is vulnerable to arbitrary function execution.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-SPEC-UNVERIFIED'],
        ),
        ClaimModel(
          id: 'CLM-07',
          statement:
              'The order upload endpoint parses untrusted YAML using the unsafe schema.',
          claimType: ClaimType.hypothesis,
          verdict: ClaimVerdict.unsupported,
          citations: [],
          reviewerNote:
              'Reviewer check found that js-yaml safeLoad is utilized with custom validator, refuting specialist claim.',
        ),
      ],
      evidenceIds: const ['EVID-SPEC-UNVERIFIED'],
      specialistDisagreement: true,
      specialistDissentSummary:
          'Reviewer rejected claim due to lack of proof-of-concept trace and safe schema usage in source code.',
      isSyntheticDemo: true,
      discoveredAt: DateTime.now().subtract(const Duration(hours: 6)),
    ),
    FindingModel(
      id: 'FIND-JS-NEG-03',
      title: 'Negative Control: Profile Image Upload Path Traversal Check',
      vulnerabilityClass: 'path_traversal',
      severity: SeverityLevel.info,
      reviewStatus: ReviewStatus.abstained,
      targetApp: 'OWASP Juice Shop (v17.1.1)',
      locus: const LocusModel(
        url: 'http://localhost:3000/profile/image/file',
        method: 'POST',
        path: '/profile/image/file',
        parameter: 'file',
        sink: 'fs.writeFile',
      ),
      specialistRole: 'filesystem_specialist',
      confidenceScore: 0.10,
      confidenceInterval: const ConfidenceIntervalModel(
        lower: 0.021,
        upper: 0.345,
        method: 'Wilson Score (95%)',
      ),
      challengeReason:
          'ABSTAINED: Specialist model abstained from declaring vulnerability after filename normalization and path sanitization were confirmed in upload controller.',
      claims: const [
        ClaimModel(
          id: 'CLM-08',
          statement:
              'Uploaded filename is sanitized using path.basename and random UUID prefix.',
          claimType: ClaimType.fact,
          verdict: ClaimVerdict.grounded,
          citations: ['EVID-JS-AST-02'],
        ),
        ClaimModel(
          id: 'CLM-09',
          statement:
              'No directory traversal escape is possible via dot-dot-slash vectors.',
          claimType: ClaimType.unknown,
          verdict: ClaimVerdict.grounded,
          citations: [],
        ),
      ],
      evidenceIds: const ['EVID-JS-AST-02'],
      specialistDisagreement: false,
      isSyntheticDemo: true,
      discoveredAt: DateTime.now().subtract(const Duration(hours: 12)),
    ),
  ];

  static final List<EvidenceModel> evidenceList = [
    const EvidenceModel(
      id: 'EVID-JS-SQLI-01',
      sourceId: 'SRC-JS-TX-01',
      sourceTitle: 'Juice Shop HTTP Search Response Packet',
      sourceType: 'HTTP Transaction Evidence',
      approvalStatus: EvidenceApprovalStatus.approved,
      excerpt:
          'HTTP/1.1 500 Internal Server Error\nContent-Type: text/html\n\nSQLITE_ERROR: near "\'": syntax error at Sequelize.query (node_modules/sequelize/lib/dialects/sqlite/query.js:185)',
      exactVersion: 'OWASP Juice Shop v17.1.1',
      filePath: 'testbed/logs/juice_shop_http_trace_20261028.json',
      lineNumber: 142,
      locusMatch: true,
      relatedFindingIds: ['FIND-JS-01'],
      provenanceDigest:
          'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    ),
    const EvidenceModel(
      id: 'EVID-JS-AST-02',
      sourceId: 'SRC-JS-CODE-02',
      sourceTitle: 'Product Search Route Source Code',
      sourceType: 'Source Code AST Excerpt',
      approvalStatus: EvidenceApprovalStatus.approved,
      excerpt:
          r"models.sequelize.query(`SELECT * FROM Products WHERE ((name LIKE '%${criteria}%' OR description LIKE '%${criteria}%') AND deletedAt IS NULL) ORDER BY name`)",
      exactVersion: 'commit:7e4f9b1 (v17.1.1)',
      filePath: 'routes/search.ts',
      lineNumber: 32,
      locusMatch: true,
      relatedFindingIds: ['FIND-JS-01', 'FIND-JS-NEG-03'],
      provenanceDigest:
          'sha256:4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    ),
    const EvidenceModel(
      id: 'EVID-DVWA-XSS-01',
      sourceId: 'SRC-DVWA-TX-01',
      sourceTitle: 'DVWA Reflected XSS Response Packet',
      sourceType: 'HTTP Transaction Evidence',
      approvalStatus: EvidenceApprovalStatus.pendingReview,
      excerpt:
          'HTTP/1.1 200 OK\nContent-Type: text/html; charset=UTF-8\n\n<div class="vulnerable_code_area">\nHello <script>alert(1)</script></div>',
      exactVersion: 'DVWA v1.10 (Release)',
      filePath: 'vulnerabilities/xss_r/source/low.php',
      lineNumber: 8,
      locusMatch: true,
      relatedFindingIds: ['FIND-DVWA-01'],
      provenanceDigest:
          'sha256:91b2230114a8b7c3d198f23055e81d77aa12c011e4f9b2318ab44512cdfa1011',
    ),
    const EvidenceModel(
      id: 'EVID-SPEC-UNVERIFIED',
      sourceId: 'SRC-SPEC-NVD-01',
      sourceTitle: 'Unpinned CVE Vulnerability Reference',
      sourceType: 'External Threat Intelligence Reference',
      approvalStatus: EvidenceApprovalStatus.rejected,
      excerpt:
          'CVE-2019-10744: Versions of js-yaml prior to 3.13.1 are vulnerable to Code Injection through the load() function.',
      exactVersion: 'Unpinned / External',
      filePath: 'external/cve_feed_mock.json',
      lineNumber: null,
      locusMatch: false,
      relatedFindingIds: ['FIND-JS-CHALLENGE-02'],
      provenanceDigest:
          'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    ),
  ];

  static final EvaluationReportModel evaluationReport = EvaluationReportModel(
    runId: 'EVAL-RUN-REPRO-8G1',
    timestamp: DateTime.now().subtract(const Duration(hours: 1)),
    targetSuite: 'Benchmark Evaluation Catalog (36 Cases: Juice Shop + DVWA)',
    totalCases: 36,
    truePositives: 18,
    falsePositives: 2,
    trueNegatives: 12,
    falseNegatives: 4,
    precision: 0.900,
    recall: 0.818,
    specificity: 0.857,
    f1Score: 0.857,
    abstentionRate: 0.083,
    coverage: 0.917,
    evidenceGroundingRate: 0.944,
    citationValidationRate: 0.917,
    incompleteCases: 0,
    failedCases: 0,
    reviewerRejections: 3,
    specialistDisagreements: 2,
    categoryBreakdown: const {
      'sql_injection': CategoryMetricModel(
        categoryName: 'SQL Injection',
        totalCases: 14,
        truePositives: 10,
        falsePositives: 1,
        falseNegatives: 1,
        trueNegatives: 2,
        precision: 0.909,
        recall: 0.909,
        f1Score: 0.909,
      ),
      'cross_site_scripting': CategoryMetricModel(
        categoryName: 'Cross-Site Scripting (XSS)',
        totalCases: 12,
        truePositives: 8,
        falsePositives: 1,
        falseNegatives: 1,
        trueNegatives: 2,
        precision: 0.889,
        recall: 0.889,
        f1Score: 0.889,
      ),
      'insecure_deserialization': CategoryMetricModel(
        categoryName: 'Insecure Deserialization',
        totalCases: 6,
        truePositives: 0,
        falsePositives: 0,
        falseNegatives: 2,
        trueNegatives: 4,
        precision: 0.0,
        recall: 0.0,
        f1Score: 0.0,
      ),
      'path_traversal': CategoryMetricModel(
        categoryName: 'Path Traversal',
        totalCases: 4,
        truePositives: 0,
        falsePositives: 0,
        falseNegatives: 0,
        trueNegatives: 4,
        precision: 0.0,
        recall: 0.0,
        f1Score: 0.0,
      ),
    },
    isSyntheticDemo: true,
    limitations: const [
      'confidence_is_calibrated=false: Probabilities are raw specialist estimates or offline Wilson score intervals.',
      'Dataset readiness gate is currently blocked pending supervisor adjudication of DEC-01 through DEC-08.',
      'Results are produced by deterministic offline evaluation harness with synthetic testbed replays.',
      'No live inference was executed against unapproved or production environments.',
    ],
  );
}
