"""Phase 8G.1 — Empirical Evaluation Readiness & Metrics Integration Tests.

Comprehensive validation of:
  1. Confusion matrix counts (TP, FP, FN, TN, ABSTAINED_POSITIVE, ABSTAINED_NEGATIVE).
  2. Core detection metrics (Precision, Recall, F1, Specificity, FPR).
  3. Selective reporting metrics (Abstention Rate, Coverage, Selective Risk).
  4. Operational reliability metrics (Evidence Grounding Rate, Citation Validation Rate,
     Incomplete Rate, Reviewer Rejection Rate, Specialist Disagreement Rate).
  5. Strict zero-denominator handling without fabricated 0.0 or 1.0 scores.
  6. Incomplete execution fail-closed behavior: never counted as covered or True Negative.
  7. Wilson score confidence interval computation and boundary bounds [0.0, 1.0].
  8. Non-linear F1 score limitation audit (single-proportion intervals not applicable).
  9. Per-category evaluation scoring with isolated locus denominators.
  10. Deterministic repeated trials aggregation preserving error diagnostics.
  11. Machine-checkable repository readiness audit over actual canonical catalog artifacts:
      verifying exact-version support, unadjudicated ground truth, unapproved partitions,
      source manifest approval status, and pending supervisor decision gates.
  12. Synthetic ready catalog test verifying that is_ready_for_empirical_run evaluates to True
      only when all prerequisites are satisfied.

STRICT BOUNDARIES:
  - Fully offline only: zero network calls, zero live model inference, zero container operations.
  - No database creation.
  - Does not modify source-review-manifest.json or supervisor decision register.
  - All test fixtures are synthetic software doubles, not real vulnerability evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from aegiscore.evaluation import (
    AdjudicationState,
    AssessmentFindingRecord,
    AssessmentResultRecord,
    CanonicalLocus,
    CaseEvaluationOutcome,
    EvaluationCaseManifestRecord,
    EvaluationScoreSummary,
    FindingDecision,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    MetricOutputRecord,
    MetricStatus,
    ScoringCalculationError,
    aggregate_repeated_runs,
    calculate_evaluation_scores,
    calculate_per_category_scores,
    compute_wilson_score_interval,
    evaluate_case_outcome,
)
from aegiscore.orchestration import FindingSeverity
from aegiscore.catalog import (
    AdjudicationStatus,
    BenchmarkReadinessReport,
    CatalogRecord,
    CatalogRecordStatus,
    IndependenceStatus,
    LocusEstablishmentStatus,
    LocusVerificationStatus,
    PartitionAssignment,
    PartitionAssignmentRecord,
    GroundTruthReviewRecord,
    RuntimeVerificationStatus,
    ScenarioRegistrationStatus,
    SourceEvidenceStatus,
    audit_benchmark_readiness,
    load_and_audit_repository_readiness,
)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _locus(uri: str = "/api/v1/test", param: str = "id", cwe: str = "CWE-89") -> CanonicalLocus:
    return CanonicalLocus(target_uri=uri, parameter=param, cwe_id=cwe)


def _gt(
    case_id: str,
    status: GroundTruthStatus = GroundTruthStatus.VULNERABLE,
    vuln_class: str = "SQLi",
    adjudication: AdjudicationState = AdjudicationState.ADJUDICATED,
) -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=case_id,
        locus=_locus(uri=f"/{case_id}"),
        expected_status=status,
        vulnerability_class=vuln_class,
        evidence_reference=f"EVID-{case_id}",
        adjudication_state=adjudication,
        provenance="synthetic_fixture",
    )


def _result(
    case_id: str,
    decision: FindingDecision,
    is_incomplete: bool = False,
    error_status: str | None = None,
    citations: tuple[str, ...] = ("CHK-001",),
) -> AssessmentResultRecord:
    findings = ()
    if decision == FindingDecision.VERIFIED:
        findings = (
            AssessmentFindingRecord(
                finding_id=f"fnd-{case_id}",
                specialist_role="sql_injection_analyst",
                vulnerability_identified=True,
                cwe_id="CWE-89",
                severity=FindingSeverity.HIGH,
                decision=FindingDecision.VERIFIED,
                evidence_citations=citations,
            ),
        )
    return AssessmentResultRecord(
        case_id=case_id,
        run_id=f"run-{case_id}",
        decision=decision,
        findings=findings,
        primary_severity=FindingSeverity.HIGH if decision == FindingDecision.VERIFIED else None,
        evidence_citations=citations if decision == FindingDecision.VERIFIED else (),
        error_status=error_status,
        is_incomplete=is_incomplete,
    )


# ---------------------------------------------------------------------------
# 1. Metric Correctness & Confusion Matrix Tests
# ---------------------------------------------------------------------------

def test_full_confusion_matrix_accounting() -> None:
    """Verify TP, FP, FN, TN, ABSTAINED_POSITIVE, ABSTAINED_NEGATIVE accounting."""
    outcomes = [
        # 3 True Positives
        CaseEvaluationOutcome("C1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("C2", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("C3", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="SQLi"),
        # 1 Explicit False Negative (system rejected vulnerable target)
        CaseEvaluationOutcome("C4", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True, vulnerability_class="SQLi"),
        # 1 Abstained Positive (abstention on vulnerable target penalizes recall as FN)
        CaseEvaluationOutcome("C5", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_POSITIVE", False, vulnerability_class="SQLi"),
        # 1 False Positive
        CaseEvaluationOutcome("C6", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.VERIFIED, "FP", True, vulnerability_class="SQLi"),
        # 2 True Negatives
        CaseEvaluationOutcome("C7", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("C8", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True, vulnerability_class="SQLi"),
        # 2 Abstained Negatives (abstention on non-vulnerable target is NOT a TN)
        CaseEvaluationOutcome("C9", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_NEGATIVE", False, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("C10", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_NEGATIVE", False, vulnerability_class="SQLi"),
    ]

    summary = calculate_evaluation_scores(outcomes)

    assert summary.tp_count == 3
    assert summary.fp_count == 1
    # total_fn = fn_explicit (1) + abs_pos (1) = 2
    assert summary.fn_count == 2
    assert summary.tn_count == 2
    assert summary.abstained_positive_count == 1
    assert summary.abstained_negative_count == 2
    assert summary.total_cases == 10

    # Precision = TP / (TP + FP) = 3 / (3 + 1) = 0.75
    prec = summary.metrics["precision"]
    assert prec.status == MetricStatus.COMPUTED
    assert prec.value == pytest.approx(0.75)
    assert prec.numerator == 3
    assert prec.denominator == 4

    # Recall = TP / (TP + total_fn) = 3 / (3 + 2) = 0.60
    rec = summary.metrics["recall"]
    assert rec.status == MetricStatus.COMPUTED
    assert rec.value == pytest.approx(0.60)
    assert rec.numerator == 3
    assert rec.denominator == 5

    # Specificity = TN / Total Negatives = 2 / (FP(1) + TN(2) + abs_neg(2)) = 2 / 5 = 0.40
    spec = summary.metrics["specificity"]
    assert spec.status == MetricStatus.COMPUTED
    assert spec.value == pytest.approx(0.40)
    assert spec.numerator == 2
    assert spec.denominator == 5

    # False Positive Rate = FP / Total Negatives = 1 / 5 = 0.20
    fpr = summary.metrics["false_positive_rate"]
    assert fpr.status == MetricStatus.COMPUTED
    assert fpr.value == pytest.approx(0.20)
    assert fpr.numerator == 1
    assert fpr.denominator == 5

    # Specificity + FPR + (abs_neg / Total Negatives) == 1.0
    assert (spec.value + fpr.value + (2 / 5)) == pytest.approx(1.0)

    # Abstention Rate = (abs_pos(1) + abs_neg(2)) / 10 = 0.30
    ar = summary.metrics["abstention_rate"]
    assert ar.value == pytest.approx(0.30)
    assert ar.numerator == 3
    assert ar.denominator == 10

    # Coverage = (10 - 3) / 10 = 0.70
    cov = summary.metrics["coverage"]
    assert cov.value == pytest.approx(0.70)
    assert cov.numerator == 7
    assert cov.denominator == 10


def test_f1_score_calculation() -> None:
    """Verify harmonic mean calculation for F1-score."""
    # TP=4, FP=1 (Prec=0.8), FN=1 (Recall=0.8) -> F1=0.8
    outcomes = [
        CaseEvaluationOutcome(f"P{i}", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True)
        for i in range(1, 5)
    ]
    outcomes.append(CaseEvaluationOutcome("P5", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True))
    outcomes.append(CaseEvaluationOutcome("N1", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.VERIFIED, "FP", True))
    outcomes.append(CaseEvaluationOutcome("N2", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True))

    summary = calculate_evaluation_scores(outcomes)
    f1 = summary.metrics["f1_score"]
    assert f1.status == MetricStatus.COMPUTED
    assert f1.value == pytest.approx(0.80)
    assert f1.ci_method == "not_applicable"
    assert "Non-linear derived metric" in f1.limitations[0]


# ---------------------------------------------------------------------------
# 2. Strict Zero Denominator Handling
# ---------------------------------------------------------------------------

def test_zero_denominator_precision_undefined() -> None:
    """When system produces 0 positive predictions, precision is UNDEFINED, not 0.0 or 1.0."""
    outcomes = [
        # All rejected or abstained; zero positive findings
        CaseEvaluationOutcome("C1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True),
        CaseEvaluationOutcome("C2", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
    ]
    summary = calculate_evaluation_scores(outcomes)
    prec = summary.metrics["precision"]
    assert prec.status == MetricStatus.UNDEFINED
    assert prec.value is None
    assert prec.denominator == 0


def test_zero_denominator_recall_undefined() -> None:
    """When evaluation includes 0 vulnerable cases, recall is UNDEFINED."""
    outcomes = [
        # Only negative controls evaluated
        CaseEvaluationOutcome("N1", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
        CaseEvaluationOutcome("N2", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.VERIFIED, "FP", True),
    ]
    summary = calculate_evaluation_scores(outcomes)
    rec = summary.metrics["recall"]
    assert rec.status == MetricStatus.UNDEFINED
    assert rec.value is None
    assert rec.denominator == 0


def test_zero_denominator_specificity_and_fpr_undefined() -> None:
    """When evaluation includes 0 non-vulnerable cases, specificity and FPR are UNDEFINED."""
    outcomes = [
        # Only vulnerable targets evaluated
        CaseEvaluationOutcome("P1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True),
        CaseEvaluationOutcome("P2", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True),
    ]
    summary = calculate_evaluation_scores(outcomes)
    assert summary.metrics["specificity"].status == MetricStatus.UNDEFINED
    assert summary.metrics["specificity"].value is None
    assert summary.metrics["false_positive_rate"].status == MetricStatus.UNDEFINED
    assert summary.metrics["false_positive_rate"].value is None


def test_empty_outcomes_raises_calculation_error() -> None:
    """Empty outcome list raises ScoringCalculationError."""
    with pytest.raises(ScoringCalculationError, match="empty outcomes"):
        calculate_evaluation_scores([])


# ---------------------------------------------------------------------------
# 3. Incomplete Case Fail-Closed Handling
# ---------------------------------------------------------------------------

def test_incomplete_case_on_vulnerable_target_is_fn() -> None:
    """An incomplete run on a vulnerable target fails closed as FN and is_covered=False."""
    gt = _gt("CASE-INC-01", status=GroundTruthStatus.VULNERABLE)
    res = _result("CASE-INC-01", decision=FindingDecision.ABSTAINED, is_incomplete=True, error_status="RuntimeError: timeout")

    outcome = evaluate_case_outcome(res, gt)

    assert outcome.is_covered is False
    assert outcome.classification == "FN"
    assert outcome.is_incomplete is True
    assert outcome.error_status == "RuntimeError: timeout"


def test_incomplete_case_on_non_vulnerable_target_never_tn() -> None:
    """An incomplete run on a non-vulnerable target is ABSTAINED_NEGATIVE, never a True Negative."""
    gt = _gt("CASE-INC-02", status=GroundTruthStatus.NON_VULNERABLE)
    res = _result("CASE-INC-02", decision=FindingDecision.REJECTED, is_incomplete=True, error_status="ProviderFailure")

    outcome = evaluate_case_outcome(res, gt)

    # Incomplete must NEVER be a True Negative
    assert outcome.classification == "ABSTAINED_NEGATIVE"
    assert outcome.is_covered is False
    assert outcome.is_incomplete is True


def test_incomplete_rate_metric_accounting() -> None:
    """Incomplete rate correctly reflects the fraction of failed/incomplete cases."""
    outcomes = [
        CaseEvaluationOutcome("C1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, is_incomplete=False),
        CaseEvaluationOutcome("C2", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.ABSTAINED, "FN", False, is_incomplete=True, error_status="SpecialistError"),
        CaseEvaluationOutcome("C3", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True, is_incomplete=False),
        CaseEvaluationOutcome("C4", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_NEGATIVE", False, is_incomplete=True, error_status="Timeout"),
    ]
    summary = calculate_evaluation_scores(outcomes)
    assert summary.incomplete_cases_count == 2
    assert summary.failed_cases_count == 2

    inc_metric = summary.metrics["incomplete_rate"]
    assert inc_metric.status == MetricStatus.COMPUTED
    assert inc_metric.value == pytest.approx(0.50)
    assert inc_metric.numerator == 2
    assert inc_metric.denominator == 4


# ---------------------------------------------------------------------------
# 4. Wilson Score Confidence Interval Tests
# ---------------------------------------------------------------------------

def test_wilson_score_interval_bounds() -> None:
    """Wilson interval bounds must always fall within [0.0, 1.0]."""
    # Boundary: k=0, n=10
    lower, upper = compute_wilson_score_interval(0, 10)
    assert lower is not None and upper is not None
    assert lower == 0.0
    assert 0.0 < upper < 1.0

    # Boundary: k=10, n=10
    lower, upper = compute_wilson_score_interval(10, 10)
    assert lower is not None and upper is not None
    assert 0.0 < lower < 1.0
    assert upper == 1.0

    # Interior: k=5, n=10 (p=0.5)
    lower, upper = compute_wilson_score_interval(5, 10)
    assert lower is not None and upper is not None
    assert 0.2 < lower < 0.5
    assert 0.5 < upper < 0.8
    # Symmetric around 0.5
    assert (0.5 - lower) == pytest.approx(upper - 0.5, abs=0.01)


def test_wilson_score_interval_zero_denominator() -> None:
    """Wilson interval returns (None, None) when denominator is 0."""
    lower, upper = compute_wilson_score_interval(0, 0)
    assert lower is None
    assert upper is None


def test_metrics_populate_wilson_confidence_intervals() -> None:
    """Binomial proportion metrics in summary have ci_lower, ci_upper, and ci_method set."""
    outcomes = [
        CaseEvaluationOutcome(f"P{i}", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True)
        for i in range(1, 11)
    ]
    outcomes.extend([
        CaseEvaluationOutcome(f"N{i}", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True)
        for i in range(1, 11)
    ])
    summary = calculate_evaluation_scores(outcomes)

    for metric_name in ("recall", "specificity", "coverage", "abstention_rate"):
        m = summary.metrics[metric_name]
        assert m.status == MetricStatus.COMPUTED
        assert m.ci_lower is not None
        assert m.ci_upper is not None
        assert m.ci_method == "wilson_score"
        assert 0.0 <= m.ci_lower <= m.value <= m.ci_upper <= 1.0


# ---------------------------------------------------------------------------
# 5. Operational Reliability Metrics (Grounding, Citations, Reviewer, Disagreement)
# ---------------------------------------------------------------------------

def test_evidence_grounding_and_citation_rates() -> None:
    """Verify evidence grounding rate and citation validation rate calculations."""
    outcomes = [
        # Outcome with 2 validated citations and 0 uncited findings
        CaseEvaluationOutcome(
            "C1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True,
            evidence_citations_count=2, uncited_findings_count=0,
        ),
        # Outcome with 0 citations and 1 uncited finding
        CaseEvaluationOutcome(
            "C2", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True,
            evidence_citations_count=0, uncited_findings_count=1,
        ),
    ]
    summary = calculate_evaluation_scores(outcomes, total_raw_candidates=2)

    egr = summary.metrics["evidence_grounding_rate"]
    assert egr.status == MetricStatus.COMPUTED
    # 2 candidates - 1 uncited = 1 grounded / 2 = 0.50
    assert egr.value == pytest.approx(0.50)

    cvr = summary.metrics["citation_validation_rate"]
    assert cvr.status == MetricStatus.COMPUTED
    # 2 citations / (2 + 1) = 0.6667
    assert cvr.value == pytest.approx(2 / 3, abs=0.01)


def test_reviewer_rejection_and_disagreement_accounting() -> None:
    """Verify reviewer rejection and specialist disagreement counts."""
    outcomes = [
        CaseEvaluationOutcome("C1", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True, reviewer_rejection=True),
        CaseEvaluationOutcome("C2", _locus(), GroundTruthStatus.VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_POSITIVE", False, specialist_disagreement=True),
        CaseEvaluationOutcome("C3", _locus(), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
    ]
    summary = calculate_evaluation_scores(outcomes)

    assert summary.reviewer_rejections_count == 1
    assert summary.specialist_disagreements_count == 1
    assert summary.metrics["reviewer_rejection_rate"].value == pytest.approx(1 / 3)
    assert summary.metrics["specialist_disagreement_rate"].value == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# 6. Per-Category Evaluation Scores
# ---------------------------------------------------------------------------

def test_calculate_per_category_scores() -> None:
    """Per-category scores isolate metrics by vulnerability class and compute aggregate."""
    outcomes = [
        # SQLi: 2 TP, 0 FP, 0 FN, 1 TN
        CaseEvaluationOutcome("S1", _locus(cwe="CWE-89"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("S2", _locus(cwe="CWE-89"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="SQLi"),
        CaseEvaluationOutcome("S3", _locus(cwe="CWE-89"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True, vulnerability_class="SQLi"),
        # XSS: 1 TP, 1 FN, 1 FP, 0 TN
        CaseEvaluationOutcome("X1", _locus(cwe="CWE-79"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="XSS"),
        CaseEvaluationOutcome("X2", _locus(cwe="CWE-79"), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True, vulnerability_class="XSS"),
        CaseEvaluationOutcome("X3", _locus(cwe="CWE-79"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.VERIFIED, "FP", True, vulnerability_class="XSS"),
    ]

    per_cat = calculate_per_category_scores(outcomes)

    assert "SQLi" in per_cat
    assert "XSS" in per_cat
    assert "AGGREGATE" in per_cat

    # SQLi metrics
    sqli = per_cat["SQLi"]
    assert sqli.tp_count == 2
    assert sqli.metrics["precision"].value == pytest.approx(1.0)
    assert sqli.metrics["recall"].value == pytest.approx(1.0)
    assert sqli.metrics["false_positive_rate"].value == pytest.approx(0.0)

    # XSS metrics
    xss = per_cat["XSS"]
    assert xss.tp_count == 1
    assert xss.fp_count == 1
    assert xss.metrics["precision"].value == pytest.approx(0.50)
    assert xss.metrics["recall"].value == pytest.approx(0.50)
    assert xss.metrics["false_positive_rate"].value == pytest.approx(1.0)

    # Aggregate metrics
    agg = per_cat["AGGREGATE"]
    assert agg.total_cases == 6
    assert agg.tp_count == 3
    assert agg.fp_count == 1
    assert agg.metrics["precision"].value == pytest.approx(0.75)


def test_per_category_handles_missing_controls_cleanly() -> None:
    """A category with 0 negative controls reports specificity as UNDEFINED without crashing."""
    outcomes = [
        CaseEvaluationOutcome("B1", _locus(cwe="CWE-862"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="BAC"),
        CaseEvaluationOutcome("B2", _locus(cwe="CWE-862"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True, vulnerability_class="BAC"),
    ]
    per_cat = calculate_per_category_scores(outcomes)
    bac = per_cat["BAC"]
    assert bac.metrics["specificity"].status == MetricStatus.UNDEFINED
    assert bac.metrics["specificity"].value is None
    assert bac.metrics["false_positive_rate"].status == MetricStatus.UNDEFINED


# ---------------------------------------------------------------------------
# 7. Repeated Runs Deterministic Aggregation
# ---------------------------------------------------------------------------

def test_aggregate_repeated_runs_preserves_incomplete_and_diagnostics() -> None:
    """aggregate_repeated_runs preserves is_incomplete and error diagnostics across trials."""
    from aegiscore.evaluation import EvaluationRunRecord

    # Create 3 trials for CASE-FAIL: Trial 1 & 2 fail closed with error, Trial 3 succeeds
    res1 = _result("CASE-FAIL", FindingDecision.ABSTAINED, is_incomplete=True, error_status="TimeoutError")
    res2 = _result("CASE-FAIL", FindingDecision.ABSTAINED, is_incomplete=True, error_status="TimeoutError")
    res3 = _result("CASE-FAIL", FindingDecision.VERIFIED, is_incomplete=False)

    r1 = EvaluationRunRecord(
        run_id=res1.run_id, runner_id="r", case_id="CASE-FAIL", repeat_index=0,
        result=res1,
    )
    r2 = EvaluationRunRecord(
        run_id=res2.run_id, runner_id="r", case_id="CASE-FAIL", repeat_index=1,
        result=res2,
    )
    r3 = EvaluationRunRecord(
        run_id=res3.run_id, runner_id="r", case_id="CASE-FAIL", repeat_index=2,
        result=res3,
    )

    agg = aggregate_repeated_runs([r1, r2, r3])
    assert len(agg) == 1
    res = agg[0]
    # Majority decision is ABSTAINED (2/3)
    assert res.decision == FindingDecision.ABSTAINED
    # is_incomplete is preserved
    assert res.is_incomplete is True
    assert res.error_status == "TimeoutError"


# ---------------------------------------------------------------------------
# 8. Machine-Checkable Repository Readiness Audit
# ---------------------------------------------------------------------------

def test_load_and_audit_repository_readiness_on_actual_repo() -> None:
    """Audit actual repository artifacts and confirm honest unadjudicated benchmark status.

    VERIFIES:
      - 36 cases in draft catalog (24 Juice Shop, 12 DVWA, as proposed in DEC-02).
      - 23 cases missing canonical locus coordinates (JS-PROP-12..24, DVWA-PROP-06..12, 3 partial).
      - 28 cases lacking exact-version pinned source evidence.
      - 36 cases awaiting empirical testbed verification.
      - 36 cases unadjudicated in ground truth review template.
      - 36 cases in unapproved/unassigned partitions.
      - 0 approved sources in source review manifest.
      - 8 supervisor decisions pending in SUPERVISOR_DECISION_REGISTER.md.
      - is_ready_for_empirical_run is False.
    """
    repo_root = Path(__file__).resolve().parent.parent
    report = load_and_audit_repository_readiness(repo_root)

    assert isinstance(report, BenchmarkReadinessReport)
    assert report.total_catalog_cases == 36

    # Locus completeness check: 20 candidate pool + 3 partial negative controls = 23
    assert len(report.cases_missing_locus_metadata) == 23
    assert "JS-PROP-12" in report.cases_missing_locus_metadata
    assert "DVWA-PROP-06" in report.cases_missing_locus_metadata
    assert "JS-XSS-R-02" in report.cases_missing_locus_metadata  # partial locus

    # Source evidence check: 28 cases lack exact pinned version (8 pinned + 28 unpinned/candidate = 36)
    assert len(report.cases_lacking_exact_source_support) == 28

    # Empirical testbed verification check: all 36 await live lab verification
    assert len(report.cases_awaiting_empirical_verification) == 36

    # Ground truth adjudication check: all 36 are unadjudicated
    assert len(report.cases_without_adjudicated_ground_truth) == 36

    # Partition approval check: all 36 are unassigned
    assert len(report.unapproved_partitions) == 36

    # Source manifest check: 0 sources approved
    assert report.manifest_approved_sources_count == 0

    # Decision register check: 8 decisions pending
    assert len(report.pending_supervisor_decisions) == 8
    for dec in ("DEC-01", "DEC-02", "DEC-03", "DEC-04", "DEC-05", "DEC-06", "DEC-07", "DEC-08"):
        assert dec in report.pending_supervisor_decisions

    # Benchmark CANNOT run empirically without supervisor decisions and approvals
    assert report.is_ready_for_empirical_run is False
    assert len(report.blocking_reasons) >= 6

    # Test serialization
    d = report.to_dict()
    assert d["is_ready_for_empirical_run"] is False
    assert d["total_catalog_cases"] == 36


def test_synthetic_ready_benchmark_evaluates_to_ready() -> None:
    """Verify that audit_benchmark_readiness evaluates to True when all requirements are met."""
    catalog = [
        CatalogRecord(
            case_id="READY-001",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            target_uri="/api/ready",
            parameter="user",
            cwe_id="CWE-89",
            vulnerability_class="SQLi",
            expected_label_proposal="vulnerable",
            catalog_status=CatalogRecordStatus.CONFIRMED,
            locus_status=LocusEstablishmentStatus.ESTABLISHED,
            scenario_registration_status=ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED,
            locus_verification_status=LocusVerificationStatus.EMPIRICALLY_VERIFIED,
            source_evidence_status=SourceEvidenceStatus.EXACT_VERSION_PINNED,
            runtime_verification_status=RuntimeVerificationStatus.EMPIRICALLY_VERIFIED,
            independence_status=IndependenceStatus.INDEPENDENT,
            evidence_source="pinned_source",
            evidence_reference="src/ready.ts:10",
            scenario_description="Synthetic confirmed benchmark locus for testing",
            review_notes="Fully verified by supervisor",
        )
    ]
    gt_reviews = [
        GroundTruthReviewRecord(
            case_id="READY-001",
            adjudication_status=AdjudicationStatus.ADJUDICATED,
            proposed_label="vulnerable",
            evidence_basis="Verified in lab",
            evidence_source="Juice Shop v15.0.0",
            evidence_source_version="15.0.0",
            reviewer_identity="Supervisor-01",
            adjudication_date="2026-10-28",
            adjudication_rationale="Fully verified locus",
            unresolved_disagreements="none",
            eligible_for_dataset=True,
        )
    ]
    partitions = [
        PartitionAssignmentRecord(
            case_id="READY-001",
            benchmark_name="juice-shop",
            partition=PartitionAssignment.TEST,
            approved_by="Supervisor-01",
            approval_date="2026-10-28",
            assignment_rationale="Stratified test partition",
            notes="Formal supervisor sign-off recorded",
        )
    ]
    manifest_dict = {
        "approval_status": "sources_approved",
        "entries": [{"review_state": "approved"}],
    }
    supervisor_decisions = {f"DEC-{i:02d}": "APPROVED" for i in range(1, 9)}

    report = audit_benchmark_readiness(
        catalog=catalog,
        ground_truth_reviews=gt_reviews,
        partition_assignments=partitions,
        source_manifest_dict=manifest_dict,
        supervisor_decisions_status=supervisor_decisions,
    )

    assert report.is_ready_for_empirical_run is True
    assert len(report.blocking_reasons) == 0
    assert len(report.pending_supervisor_decisions) == 0
