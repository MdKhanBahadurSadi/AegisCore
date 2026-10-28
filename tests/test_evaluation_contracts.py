"""Unit tests for evaluation contracts, strict JSONL validators, and offline scoring framework.

Phase 8E.3: All tests are strictly offline and validate schema validation,
confusion matrix logic, abstention invariants, zero-denominator handling,
repeated-run aggregation, and runner interfaces on synthetic fixtures.
"""

from __future__ import annotations

import json
import pytest

from aegiscore.evaluation import (
    AdjudicationState,
    AssessmentFindingRecord,
    AssessmentResultRecord,
    CanonicalLocus,
    CaseEvaluationOutcome,
    EvaluationCaseManifestRecord,
    EvaluationContractError,
    EvaluationRunRecord,
    EvaluationValidationError,
    FindingDecision,
    FixtureBackedRunnerAdapter,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    MetricStatus,
    ScoringCalculationError,
    aggregate_repeated_runs,
    calculate_evaluation_scores,
    evaluate_case_outcome,
    validate_ground_truth_jsonl,
    validate_manifest_jsonl,
    validate_runs_jsonl,
)
from aegiscore.orchestration import FindingSeverity


# ---------------------------------------------------------------------------
# Fixture Helpers (Strictly Synthetic)
# ---------------------------------------------------------------------------

def _make_locus(uri: str = "/rest/products/search", param: str = "q", cwe: str = "CWE-79") -> CanonicalLocus:
    return CanonicalLocus(target_uri=uri, parameter=param, cwe_id=cwe)


def _make_manifest_record(
    case_id: str = "CASE-SYNTH-01",
    uri: str = "/rest/products/search",
    param: str = "q",
    cwe: str = "CWE-79",
    expected: GroundTruthStatus = GroundTruthStatus.VULNERABLE,
) -> EvaluationCaseManifestRecord:
    return EvaluationCaseManifestRecord(
        case_id=case_id,
        locus=_make_locus(uri, param, cwe),
        benchmark_target="juice-shop",
        benchmark_version="v15.0.0",
        vulnerability_class=cwe,
        expected_label=expected,
        ground_truth_provenance="Synthetic unit test fixture",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
        description="Synthetic test case for unit validation",
    )


def _make_gt_record(
    case_id: str = "CASE-SYNTH-01",
    uri: str = "/rest/products/search",
    param: str = "q",
    cwe: str = "CWE-79",
    expected: GroundTruthStatus = GroundTruthStatus.VULNERABLE,
    severity: FindingSeverity | None = FindingSeverity.HIGH,
) -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=case_id,
        locus=_make_locus(uri, param, cwe),
        expected_status=expected,
        vulnerability_class=cwe,
        expected_severity=severity,
        evidence_reference="SYNTH-EVAL-REF-01",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="Synthetic test ground truth",
    )


def _make_result_record(
    case_id: str = "CASE-SYNTH-01",
    run_id: str = "run-synth-01",
    decision: FindingDecision = FindingDecision.VERIFIED,
    severity: FindingSeverity | None = FindingSeverity.HIGH,
) -> AssessmentResultRecord:
    finding = AssessmentFindingRecord(
        finding_id=f"fnd-{case_id}",
        specialist_role="vulnerability_specialist:xss",
        vulnerability_identified=(decision == FindingDecision.VERIFIED),
        cwe_id="CWE-79",
        severity=severity or FindingSeverity.MEDIUM,
        decision=decision,
        evidence_citations=("src_test1#chk_test1",),
        rationale="Synthetic test finding",
    )
    return AssessmentResultRecord(
        case_id=case_id,
        run_id=run_id,
        decision=decision,
        findings=(finding,),
        primary_severity=severity,
        evidence_citations=("src_test1#chk_test1",),
    )


# ---------------------------------------------------------------------------
# Test 1: Canonical Locus Validation
# ---------------------------------------------------------------------------

def test_canonical_locus_valid_and_formatting() -> None:
    locus = CanonicalLocus(target_uri="/api/login", parameter="password", cwe_id="CWE-89")
    assert locus.target_uri == "/api/login"
    assert locus.parameter == "password"
    assert locus.cwe_id == "CWE-89"
    assert locus.locus_key == "/api/login:password:CWE-89"


def test_canonical_locus_rejects_empty_or_whitespace() -> None:
    with pytest.raises(EvaluationContractError, match="must be non-empty text"):
        CanonicalLocus(target_uri="", parameter="q", cwe_id="CWE-79")

    with pytest.raises(EvaluationContractError, match="contains un-trimmed"):
        CanonicalLocus(target_uri="/api/test ", parameter="q", cwe_id="CWE-79")


def test_canonical_locus_rejects_malformed_cwe_id() -> None:
    with pytest.raises(EvaluationContractError, match="must match format CWE-<number>"):
        CanonicalLocus(target_uri="/api/test", parameter="q", cwe_id="SQLI")

    with pytest.raises(EvaluationContractError, match="must match format CWE-<number>"):
        CanonicalLocus(target_uri="/api/test", parameter="q", cwe_id="cwe-79")


# ---------------------------------------------------------------------------
# Test 2: Serialization and Deserialization Roundtrip
# ---------------------------------------------------------------------------

def test_manifest_record_dict_roundtrip() -> None:
    rec = _make_manifest_record("CASE-01")
    as_dict = rec.to_dict()
    reconstructed = EvaluationCaseManifestRecord.from_dict(as_dict)
    assert reconstructed == rec


def test_ground_truth_record_dict_roundtrip() -> None:
    rec = _make_gt_record("CASE-01")
    as_dict = rec.to_dict()
    reconstructed = GroundTruthRecord.from_dict(as_dict)
    assert reconstructed == rec


def test_assessment_result_dict_roundtrip() -> None:
    res = _make_result_record("CASE-01", "run-01")
    as_dict = res.to_dict()
    reconstructed = AssessmentResultRecord.from_dict(as_dict)
    assert reconstructed == res


def test_evaluation_run_record_dict_roundtrip() -> None:
    res = _make_result_record("CASE-01", "run-01")
    run = EvaluationRunRecord(
        run_id="run-01",
        runner_id="proposed-multi-agent",
        case_id="CASE-01",
        repeat_index=0,
        result=res,
        reproducibility_metadata={"seed": "42", "temperature": "0.0"},
    )
    as_dict = run.to_dict()
    reconstructed = EvaluationRunRecord.from_dict(as_dict)
    assert reconstructed == run


# ---------------------------------------------------------------------------
# Test 3: JSONL Stream Validation & Duplicate Detection
# ---------------------------------------------------------------------------

def test_validate_manifest_jsonl_valid() -> None:
    rec1 = _make_manifest_record("CASE-01", "/api/1", "p1")
    rec2 = _make_manifest_record("CASE-02", "/api/2", "p2")
    stream = f"{json.dumps(rec1.to_dict())}\n{json.dumps(rec2.to_dict())}\n"

    parsed = validate_manifest_jsonl(stream)
    assert len(parsed) == 2
    assert parsed[0].case_id == "CASE-01"
    assert parsed[1].case_id == "CASE-02"


def test_validate_manifest_jsonl_detects_duplicate_case_id() -> None:
    rec1 = _make_manifest_record("CASE-DUP", "/api/1", "p1")
    rec2 = _make_manifest_record("CASE-DUP", "/api/2", "p2")
    stream = f"{json.dumps(rec1.to_dict())}\n{json.dumps(rec2.to_dict())}\n"

    with pytest.raises(EvaluationValidationError, match="Duplicate case_id 'CASE-DUP'"):
        validate_manifest_jsonl(stream)


def test_validate_manifest_jsonl_detects_duplicate_locus() -> None:
    rec1 = _make_manifest_record("CASE-01", "/api/common", "q", "CWE-79")
    rec2 = _make_manifest_record("CASE-02", "/api/common", "q", "CWE-79")
    stream = f"{json.dumps(rec1.to_dict())}\n{json.dumps(rec2.to_dict())}\n"

    with pytest.raises(EvaluationValidationError, match="Duplicate canonical locus"):
        validate_manifest_jsonl(stream)


def test_validate_manifest_jsonl_rejects_malformed_json() -> None:
    stream = "{\"case_id\": \"CASE-01\"}\nNOT_VALID_JSON\n"
    with pytest.raises(EvaluationValidationError, match="Malformed JSON"):
        validate_manifest_jsonl(stream)


def test_validate_ground_truth_jsonl_rejects_unknown_case_id() -> None:
    gt_rec = _make_gt_record("CASE-UNKNOWN")
    stream = json.dumps(gt_rec.to_dict())

    known_cases = {"CASE-APPROVED-01", "CASE-APPROVED-02"}
    with pytest.raises(EvaluationValidationError, match="not in the approved manifest cases"):
        validate_ground_truth_jsonl(stream, known_manifest_cases=known_cases)


def test_validate_runs_jsonl_detects_duplicate_run_id() -> None:
    res1 = _make_result_record("CASE-01", "run-dup")
    run1 = EvaluationRunRecord(run_id="run-dup", runner_id="proposed", case_id="CASE-01", repeat_index=0, result=res1)
    res2 = _make_result_record("CASE-02", "run-dup")
    run2 = EvaluationRunRecord(run_id="run-dup", runner_id="proposed", case_id="CASE-02", repeat_index=0, result=res2)
    stream = f"{json.dumps(run1.to_dict())}\n{json.dumps(run2.to_dict())}\n"

    with pytest.raises(EvaluationValidationError, match="Duplicate run_id 'run-dup'"):
        validate_runs_jsonl(stream)


def test_validate_runs_jsonl_detects_duplicate_repeat_index() -> None:
    res1 = _make_result_record("CASE-01", "run-01")
    run1 = EvaluationRunRecord(run_id="run-01", runner_id="proposed", case_id="CASE-01", repeat_index=0, result=res1)
    res2 = _make_result_record("CASE-01", "run-02")
    run2 = EvaluationRunRecord(run_id="run-02", runner_id="proposed", case_id="CASE-01", repeat_index=0, result=res2)
    stream = f"{json.dumps(run1.to_dict())}\n{json.dumps(run2.to_dict())}\n"

    with pytest.raises(EvaluationValidationError, match="Duplicate run episode"):
        validate_runs_jsonl(stream)


# ---------------------------------------------------------------------------
# Test 4: Confusion Matrix & Case Adjudication Logic
# ---------------------------------------------------------------------------

def test_case_outcome_true_positive() -> None:
    gt = _make_gt_record("C1", expected=GroundTruthStatus.VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.VERIFIED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "TP"
    assert out.is_covered is True


def test_case_outcome_false_negative_explicit() -> None:
    gt = _make_gt_record("C1", expected=GroundTruthStatus.VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.REJECTED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "FN"
    assert out.is_covered is True


def test_case_outcome_abstention_on_positive_is_false_negative() -> None:
    """CRITICAL: Abstaining on a genuine vulnerability counts as a False Negative in detection recall."""
    gt = _make_gt_record("C1", expected=GroundTruthStatus.VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.ABSTAINED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "ABSTAINED_POSITIVE"
    assert out.is_covered is False


def test_case_outcome_false_positive() -> None:
    gt = _make_gt_record("C1", expected=GroundTruthStatus.NON_VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.VERIFIED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "FP"
    assert out.is_covered is True


def test_case_outcome_true_negative_explicit() -> None:
    gt = _make_gt_record("C1", expected=GroundTruthStatus.NON_VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.REJECTED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "TN"
    assert out.is_covered is True


def test_case_outcome_abstention_on_negative_is_never_true_negative() -> None:
    """CRITICAL: Abstaining on a non-vulnerable case is an ABSTENTION, NEVER a True Negative."""
    gt = _make_gt_record("C1", expected=GroundTruthStatus.NON_VULNERABLE)
    res = _make_result_record("C1", "r1", decision=FindingDecision.ABSTAINED)
    out = evaluate_case_outcome(res, gt)
    assert out.classification == "ABSTAINED_NEGATIVE"
    assert out.is_covered is False


# ---------------------------------------------------------------------------
# Test 5: Metric Calculation & Zero Denominator Safety
# ---------------------------------------------------------------------------

def test_offline_scoring_balanced_synthetic_suite() -> None:
    """Evaluate a 10-case synthetic suite:
    - 5 Vulnerable: 3 TP, 1 FN (rejected), 1 Abstained
    - 5 Non-Vulnerable: 1 FP, 3 TN (rejected), 1 Abstained
    Total: 3 TP, 1 FP, 2 FN (1 rejected + 1 abs), 3 TN, 2 Abstained
    """
    outcomes = [
        # Positives
        CaseEvaluationOutcome("P1", _make_locus(uri="/p1"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True),
        CaseEvaluationOutcome("P2", _make_locus(uri="/p2"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True),
        CaseEvaluationOutcome("P3", _make_locus(uri="/p3"), GroundTruthStatus.VULNERABLE, FindingDecision.VERIFIED, "TP", True),
        CaseEvaluationOutcome("P4", _make_locus(uri="/p4"), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True),
        CaseEvaluationOutcome("P5", _make_locus(uri="/p5"), GroundTruthStatus.VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_POSITIVE", False),
        # Negatives
        CaseEvaluationOutcome("N1", _make_locus(uri="/n1"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.VERIFIED, "FP", True),
        CaseEvaluationOutcome("N2", _make_locus(uri="/n2"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
        CaseEvaluationOutcome("N3", _make_locus(uri="/n3"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
        CaseEvaluationOutcome("N4", _make_locus(uri="/n4"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
        CaseEvaluationOutcome("N5", _make_locus(uri="/n5"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.ABSTAINED, "ABSTAINED_NEGATIVE", False),
    ]

    summary = calculate_evaluation_scores(outcomes, total_raw_candidates=5)

    assert summary.tp_count == 3
    assert summary.fp_count == 1
    assert summary.fn_count == 2  # 1 explicit FN + 1 positive abstention
    assert summary.tn_count == 3  # Exactly 3, NOT 4! Abstention is not TN.
    assert summary.abstained_positive_count == 1
    assert summary.abstained_negative_count == 1
    assert summary.total_cases == 10

    # Precision = 3 / (3 + 1) = 0.75
    prec = summary.metrics["precision"]
    assert prec.status == MetricStatus.COMPUTED
    assert prec.value == pytest.approx(0.75)
    assert prec.numerator == 3
    assert prec.denominator == 4

    # Recall = 3 / (3 + 2) = 0.60 (abstained positive penalized recall)
    rec = summary.metrics["recall"]
    assert rec.status == MetricStatus.COMPUTED
    assert rec.value == pytest.approx(0.60)
    assert rec.numerator == 3
    assert rec.denominator == 5

    # F1 = 2 * (0.75 * 0.60) / (0.75 + 0.60) = 0.90 / 1.35 = 2/3 ≈ 0.6667
    f1 = summary.metrics["f1_score"]
    assert f1.status == MetricStatus.COMPUTED
    assert f1.value == pytest.approx(2.0 / 3.0)

    # FPR = FP / Total Negatives = 1 / 5 = 0.20
    fpr = summary.metrics["false_positive_rate"]
    assert fpr.status == MetricStatus.COMPUTED
    assert fpr.value == pytest.approx(0.20)

    # Abstention Rate = 2 / 10 = 0.20
    ar = summary.metrics["abstention_rate"]
    assert ar.status == MetricStatus.COMPUTED
    assert ar.value == pytest.approx(0.20)

    # Coverage = 8 / 10 = 0.80
    cov = summary.metrics["coverage"]
    assert cov.status == MetricStatus.COMPUTED
    assert cov.value == pytest.approx(0.80)

    # Selective Risk R(Phi) = FP_covered / (TP_covered + FP_covered) = 1 / 4 = 0.25
    sel_risk = summary.metrics["selective_risk"]
    assert sel_risk.status == MetricStatus.COMPUTED
    assert sel_risk.value == pytest.approx(0.25)

    # VFR = 3 / 5 = 0.60
    vfr = summary.metrics["verified_finding_rate"]
    assert vfr.status == MetricStatus.COMPUTED
    assert vfr.value == pytest.approx(0.60)

    # Calibration metrics must be explicitly NOT_SUPPORTED
    assert summary.metrics["brier_score"].status == MetricStatus.NOT_SUPPORTED
    assert summary.metrics["expected_calibration_error"].status == MetricStatus.NOT_SUPPORTED


def test_zero_findings_reported_yields_undefined_precision_and_f1() -> None:
    """When a system reports zero findings (TP=0, FP=0), Precision and F1 must be UNDEFINED, not 0.0 or 1.0."""
    outcomes = [
        CaseEvaluationOutcome("P1", _make_locus(uri="/p1"), GroundTruthStatus.VULNERABLE, FindingDecision.REJECTED, "FN", True),
        CaseEvaluationOutcome("N1", _make_locus(uri="/n1"), GroundTruthStatus.NON_VULNERABLE, FindingDecision.REJECTED, "TN", True),
    ]

    summary = calculate_evaluation_scores(outcomes)

    prec = summary.metrics["precision"]
    assert prec.status == MetricStatus.UNDEFINED
    assert prec.value is None

    f1 = summary.metrics["f1_score"]
    assert f1.status == MetricStatus.UNDEFINED
    assert f1.value is None

    # Recall is computed: 0 / 1 = 0.0
    rec = summary.metrics["recall"]
    assert rec.status == MetricStatus.COMPUTED
    assert rec.value == 0.0


# ---------------------------------------------------------------------------
# Test 6: Repeated-Run Aggregation (Majority Voting)
# ---------------------------------------------------------------------------

def test_aggregate_repeated_runs_majority_vote() -> None:
    """K=3 repeated runs: 2 VERIFIED, 1 ABSTAINED -> Aggregates to VERIFIED."""
    r0 = EvaluationRunRecord("r0", "proposed", "C1", 0, _make_result_record("C1", "r0", FindingDecision.VERIFIED))
    r1 = EvaluationRunRecord("r1", "proposed", "C1", 1, _make_result_record("C1", "r1", FindingDecision.VERIFIED))
    r2 = EvaluationRunRecord("r2", "proposed", "C1", 2, _make_result_record("C1", "r2", FindingDecision.ABSTAINED))

    agg = aggregate_repeated_runs([r0, r1, r2])
    assert len(agg) == 1
    assert agg[0].case_id == "C1"
    assert agg[0].decision == FindingDecision.VERIFIED


def test_aggregate_repeated_runs_split_vote_fails_closed_to_abstain() -> None:
    """K=3 repeated runs with split decision (1 VERIFIED, 1 REJECTED, 1 ABSTAINED) fails closed to ABSTAINED."""
    r0 = EvaluationRunRecord("r0", "proposed", "C1", 0, _make_result_record("C1", "r0", FindingDecision.VERIFIED))
    r1 = EvaluationRunRecord("r1", "proposed", "C1", 1, _make_result_record("C1", "r1", FindingDecision.REJECTED))
    r2 = EvaluationRunRecord("r2", "proposed", "C1", 2, _make_result_record("C1", "r2", FindingDecision.ABSTAINED))

    agg = aggregate_repeated_runs([r0, r1, r2])
    assert len(agg) == 1
    assert agg[0].case_id == "C1"
    assert agg[0].decision == FindingDecision.ABSTAINED


# ---------------------------------------------------------------------------
# Test 7: Runner Interface & Fixture Adapter
# ---------------------------------------------------------------------------

def test_fixture_backed_runner_adapter_executes_offline() -> None:
    """FixtureBackedRunnerAdapter replays synthetic results without external calls."""
    case = _make_manifest_record("CASE-01")
    expected_res = _make_result_record("CASE-01", "temp-run", FindingDecision.VERIFIED)

    adapter = FixtureBackedRunnerAdapter(
        runner_id="test-runner",
        fixture_results_by_case={"CASE-01": expected_res},
    )

    run_record = adapter.run_case(case, repeat_index=2)
    assert run_record.runner_id == "test-runner"
    assert run_record.case_id == "CASE-01"
    assert run_record.repeat_index == 2
    assert run_record.result.decision == FindingDecision.VERIFIED
    assert run_record.run_id == "run-test-runner-CASE-01-rep2"


def test_fixture_backed_runner_adapter_fails_on_missing_case() -> None:
    case = _make_manifest_record("CASE-MISSING")
    adapter = FixtureBackedRunnerAdapter(runner_id="test-runner", fixture_results_by_case={})

    with pytest.raises(EvaluationContractError, match="No synthetic fixture configured"):
        adapter.run_case(case)
