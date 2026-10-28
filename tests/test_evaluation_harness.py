"""Unit tests for AEGISCORE AI offline evaluation harness and runner registry (Phase 8E.4).

Verifies:
- End-to-end fixture ingestion, validation, execution, and scoring.
- Unknown, planned/unavailable, and live-prohibited runner conditions.
- Strict rejection of unapproved live execution or target-dispatch modes.
- Invalid JSONL and malformed records handling.
- Duplicate run IDs, duplicate loci, and inconsistent case IDs rejection.
- Preservation of raw repeated trials and trial agreement analysis.
- Deterministic output serialization and traceability.
- Abstention accounting invariants and zero-denominator safety.
- Zero network requests and zero external dependencies.
"""

from __future__ import annotations

import json
import pytest

from aegiscore.evaluation import (
    AdjudicationState,
    CanonicalLocus,
    EvaluationCaseManifestRecord,
    EvaluationContractError,
    EvaluationRunRecord,
    FindingDecision,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    MetricStatus,
    RunnerCondition,
    EvaluationRunnerInterface,
)
from aegiscore.evaluation_harness import (
    ConditionNotRegisteredError,
    ConditionStatus,
    ConditionUnavailableError,
    EvaluationHarness,
    HarnessError,
    HarnessExecutionReport,
    HarnessValidationError,
    LiveExecutionProhibitedError,
    RunnerConditionRegistry,
    create_synthetic_fixture_adapter,
    normalize_condition,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

def _make_locus(case_num: int, cwe: str = "CWE-79") -> CanonicalLocus:
    return CanonicalLocus(
        target_uri=f"http://172.28.0.10:3000/api/endpoint/{case_num}",
        parameter=f"param_{case_num}",
        cwe_id=cwe,
    )


def _make_case(case_num: int, cwe: str = "CWE-79") -> EvaluationCaseManifestRecord:
    return EvaluationCaseManifestRecord(
        case_id=f"CASE-TEST-{case_num:03d}",
        locus=_make_locus(case_num, cwe),
        benchmark_target="synthetic-benchmark",
        benchmark_version="1.0.0",
        vulnerability_class="XSS",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="synthetic-offline-test",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )


def _make_gt(case_num: int, status: GroundTruthStatus = GroundTruthStatus.VULNERABLE, cwe: str = "CWE-79") -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=f"CASE-TEST-{case_num:03d}",
        locus=_make_locus(case_num, cwe),
        expected_status=status,
        vulnerability_class="XSS",
        evidence_reference=f"REF-EVAL-{case_num:03d}",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="synthetic-offline-ground-truth",
    )


# ---------------------------------------------------------------------------
# Registry & Condition Tests
# ---------------------------------------------------------------------------

def test_registry_default_conditions_status() -> None:
    """Default registry configures planned conditions and strictly prohibits live DAST/ZAP."""
    reg = RunnerConditionRegistry.create_default_registry()
    statuses = reg.list_conditions()

    assert statuses[RunnerCondition.BASELINE_DAST_ZAP] == ConditionStatus.LIVE_PROHIBITED
    assert statuses[RunnerCondition.PROPOSED_MULTI_AGENT] == ConditionStatus.PLANNED_UNAVAILABLE
    assert statuses[RunnerCondition.BASELINE_SINGLE_AGENT] == ConditionStatus.PLANNED_UNAVAILABLE
    assert statuses[RunnerCondition.BASELINE_MA_NO_ABSTENTION] == ConditionStatus.PLANNED_UNAVAILABLE
    assert statuses[RunnerCondition.ABLATION_NO_RAG] == ConditionStatus.PLANNED_UNAVAILABLE
    assert statuses[RunnerCondition.ABLATION_NO_REVIEWER] == ConditionStatus.PLANNED_UNAVAILABLE


def test_registry_normalize_condition() -> None:
    """Aliases and strings are normalized to canonical RunnerCondition enums."""
    assert normalize_condition("SINGLE_AGENT_BASELINE") == RunnerCondition.BASELINE_SINGLE_AGENT
    assert normalize_condition("MULTI_AGENT_FULL") == RunnerCondition.PROPOSED_MULTI_AGENT
    assert normalize_condition("proposed-multi-agent") == RunnerCondition.PROPOSED_MULTI_AGENT
    assert normalize_condition("RAG_DISABLED_ABLATION") == RunnerCondition.ABLATION_NO_RAG
    assert normalize_condition("EVIDENCE_REVIEWER_DISABLED_ABLATION") == RunnerCondition.ABLATION_NO_REVIEWER
    assert normalize_condition("DAST_ZAP") == RunnerCondition.BASELINE_DAST_ZAP

    with pytest.raises(ConditionNotRegisteredError):
        normalize_condition("NON_EXISTENT_CONDITION")


def test_registry_live_prohibited_fails_closed() -> None:
    """Attempting to access a LIVE_PROHIBITED condition raises LiveExecutionProhibitedError."""
    reg = RunnerConditionRegistry.create_default_registry()
    with pytest.raises(LiveExecutionProhibitedError, match="LIVE_PROHIBITED"):
        reg.get_adapter(RunnerCondition.BASELINE_DAST_ZAP)


def test_registry_planned_unavailable_fails_closed() -> None:
    """Attempting to access a PLANNED_UNAVAILABLE condition raises ConditionUnavailableError."""
    reg = RunnerConditionRegistry.create_default_registry()
    with pytest.raises(ConditionUnavailableError, match="PLANNED_UNAVAILABLE"):
        reg.get_adapter(RunnerCondition.PROPOSED_MULTI_AGENT)


def test_registry_register_and_get_fixture_adapter() -> None:
    """Registering a fixture adapter updates status to FIXTURE_IMPLEMENTED and retrieves cleanly."""
    reg = RunnerConditionRegistry.create_default_registry()
    cases = [_make_case(1)]
    adapter = create_synthetic_fixture_adapter("runner-test", cases)

    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    assert reg.get_status(RunnerCondition.PROPOSED_MULTI_AGENT) == ConditionStatus.FIXTURE_IMPLEMENTED
    retrieved = reg.get_adapter(RunnerCondition.PROPOSED_MULTI_AGENT)
    assert retrieved.runner_id == "runner-test"


# ---------------------------------------------------------------------------
# Harness Safety & Validation Tests
# ---------------------------------------------------------------------------

def test_harness_rejects_live_execution_mode() -> None:
    """Harness fails closed if live execution mode is passed to constructor."""
    with pytest.raises(LiveExecutionProhibitedError, match="Execution mode must be 'offline_fixture'"):
        EvaluationHarness(execution_mode="live")

    with pytest.raises(LiveExecutionProhibitedError, match="Execution mode must be 'offline_fixture'"):
        EvaluationHarness(execution_mode="target_dispatch")


def test_harness_rejects_empty_inputs() -> None:
    """Harness fails closed if manifests or ground truths are empty."""
    harness = EvaluationHarness()
    with pytest.raises(HarnessValidationError, match="manifest records sequence must not be empty"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [], [_make_gt(1)])

    with pytest.raises(HarnessValidationError, match="Ground truth records sequence must not be empty"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [_make_case(1)], [])


def test_harness_rejects_duplicate_case_ids() -> None:
    """Harness detects duplicate case IDs in manifest."""
    harness = EvaluationHarness()
    case1 = _make_case(1)
    case2 = EvaluationCaseManifestRecord(
        case_id=case1.case_id,
        locus=_make_locus(2),
        benchmark_target="test",
        benchmark_version="1.0.0",
        vulnerability_class="XSS",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="prov",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )
    with pytest.raises(HarnessValidationError, match="Duplicate case_id"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case1, case2], [_make_gt(1)])


def test_harness_rejects_duplicate_canonical_loci() -> None:
    """Harness detects duplicate canonical loci with different case IDs."""
    harness = EvaluationHarness()
    locus = _make_locus(1)
    case1 = EvaluationCaseManifestRecord(
        case_id="CASE-001",
        locus=locus,
        benchmark_target="test",
        benchmark_version="1.0.0",
        vulnerability_class="XSS",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="prov",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )
    case2 = EvaluationCaseManifestRecord(
        case_id="CASE-002",
        locus=locus,
        benchmark_target="test",
        benchmark_version="1.0.0",
        vulnerability_class="XSS",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="prov",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )
    with pytest.raises(HarnessValidationError, match="Duplicate canonical locus"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case1, case2], [_make_gt(1)])


def test_harness_fails_on_missing_ground_truth() -> None:
    """Harness fails closed if any case manifest has missing ground truth."""
    cases = [_make_case(1), _make_case(2)]
    gts = [_make_gt(1)]  # Missing case 2

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter("runner-test", cases)
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    with pytest.raises(HarnessValidationError, match="Missing ground truth for cases"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, cases, gts)


def test_harness_fails_on_unadjudicated_ground_truth_under_strict_mode() -> None:
    """Harness fails closed if ground truth is not adjudicated and strict mode is active."""
    case = _make_case(1)
    gt_unverified = GroundTruthRecord(
        case_id=case.case_id,
        locus=case.locus,
        expected_status=GroundTruthStatus.VULNERABLE,
        vulnerability_class="XSS",
        evidence_reference="REF-001",
        adjudication_state=AdjudicationState.UNVERIFIED,
        provenance="unverified",
    )

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter("runner-test", [case])
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    with pytest.raises(HarnessValidationError, match="strict_adjudication requires 'adjudicated'"):
        harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt_unverified], strict_adjudication=True)


# ---------------------------------------------------------------------------
# End-to-End Execution & Repeated Runs Tests
# ---------------------------------------------------------------------------

def test_harness_e2e_single_trial_execution() -> None:
    """End-to-end execution of a 4-case fixture evaluation produces complete score summary."""
    cases = [_make_case(1), _make_case(2), _make_case(3), _make_case(4)]
    # Case 1: VULN, Case 2: VULN, Case 3: NON_VULN, Case 4: NON_VULN
    gts = [
        _make_gt(1, GroundTruthStatus.VULNERABLE),
        _make_gt(2, GroundTruthStatus.VULNERABLE),
        _make_gt(3, GroundTruthStatus.NON_VULNERABLE),
        _make_gt(4, GroundTruthStatus.NON_VULNERABLE),
    ]

    # Decisions: Case 1: VERIFIED (TP), Case 2: REJECTED (FN), Case 3: VERIFIED (FP), Case 4: REJECTED (TN)
    custom_decisions = {
        "CASE-TEST-001": FindingDecision.VERIFIED,
        "CASE-TEST-002": FindingDecision.REJECTED,
        "CASE-TEST-003": FindingDecision.VERIFIED,
        "CASE-TEST-004": FindingDecision.REJECTED,
    }

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter(
        runner_id="test-runner-single",
        case_manifests=cases,
        custom_decisions=custom_decisions,
    )
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
        repeat_count=1,
    )

    assert isinstance(report, HarnessExecutionReport)
    assert report.unique_case_loci_count == 4
    assert len(report.raw_trial_runs) == 4
    assert len(report.aggregated_outcomes) == 4

    scores = report.score_summary
    assert scores.tp_count == 1
    assert scores.fn_count == 1
    assert scores.fp_count == 1
    assert scores.tn_count == 1
    assert scores.total_cases == 4

    # Precision = TP / (TP + FP) = 1 / 2 = 0.5
    assert scores.metrics["precision"].value == 0.5
    # Recall = TP / (TP + FN) = 1 / 2 = 0.5
    assert scores.metrics["recall"].value == 0.5
    # F1 = 0.5
    assert scores.metrics["f1_score"].value == 0.5


def test_harness_repeated_runs_preservation_and_agreement() -> None:
    """Repeated trials (K=3) are preserved individually while majority voting aggregates outcomes."""
    cases = [_make_case(1), _make_case(2)]
    gts = [
        _make_gt(1, GroundTruthStatus.VULNERABLE),
        _make_gt(2, GroundTruthStatus.NON_VULNERABLE),
    ]

    custom_decisions = {
        "CASE-TEST-001": FindingDecision.VERIFIED,
        "CASE-TEST-002": FindingDecision.REJECTED,
    }

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter(
        runner_id="test-runner-k3",
        case_manifests=cases,
        custom_decisions=custom_decisions,
    )
    reg.register_fixture_adapter(RunnerCondition.BASELINE_SINGLE_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.BASELINE_SINGLE_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
        repeat_count=3,
    )

    # 2 cases * 3 repeats = 6 raw trial runs
    assert len(report.raw_trial_runs) == 6
    # Exactly 2 unique case loci aggregated
    assert len(report.aggregated_outcomes) == 2
    assert report.unique_case_loci_count == 2

    # Verify repeat indices
    rep_indices = [r.repeat_index for r in report.raw_trial_runs]
    assert rep_indices == [0, 0, 1, 1, 2, 2]

    # Verify trial agreement
    assert report.trial_agreement.total_cases == 2
    assert report.trial_agreement.unanimous_cases_count == 2
    assert report.trial_agreement.split_decision_cases_count == 0
    assert report.trial_agreement.trial_agreement_rate == 1.0
    assert report.trial_agreement.is_deterministic_fixture_behavior is True


def test_harness_abstention_invariants_and_selective_risk() -> None:
    """Abstention on VULNERABLE is FN; abstention on NON_VULNERABLE is NOT TN."""
    cases = [_make_case(1), _make_case(2)]
    gts = [
        _make_gt(1, GroundTruthStatus.VULNERABLE),
        _make_gt(2, GroundTruthStatus.NON_VULNERABLE),
    ]

    # Both abstain
    custom_decisions = {
        "CASE-TEST-001": FindingDecision.ABSTAINED,
        "CASE-TEST-002": FindingDecision.ABSTAINED,
    }

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter("runner-abs", cases, custom_decisions=custom_decisions)
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
        repeat_count=1,
    )

    scores = report.score_summary
    assert scores.tp_count == 0
    assert scores.fp_count == 0
    assert scores.fn_count == 1  # Abstained positive is empirical FN!
    assert scores.tn_count == 0  # Abstained negative is NOT TN!
    assert scores.abstained_positive_count == 1
    assert scores.abstained_negative_count == 1

    # Abstention rate = 2 / 2 = 1.0
    assert scores.metrics["abstention_rate"].value == 1.0
    # Coverage = 0.0
    assert scores.metrics["coverage"].value == 0.0
    # Precision is UNDEFINED (0 findings verified)
    assert scores.metrics["precision"].status == MetricStatus.UNDEFINED
    assert scores.metrics["precision"].value is None
    # Selective risk is UNDEFINED (0 covered predictions)
    assert scores.metrics["selective_risk"].status == MetricStatus.UNDEFINED
    assert scores.metrics["selective_risk"].value is None


def test_harness_execute_from_jsonl() -> None:
    """Harness successfully parses JSONL streams, validates them, and executes evaluation."""
    manifest_jsonl = (
        '{"case_id": "CASE-JSONL-001", "locus": {"target_uri": "http://172.28.0.10:3000/rest/user", "parameter": "q", "cwe_id": "CWE-89"}, "benchmark_target": "juice-shop", "benchmark_version": "15.0.0", "vulnerability_class": "SQLi", "expected_label": "vulnerable", "ground_truth_provenance": "manual-audit", "review_status": "adjudicated", "inclusion_status": "included"}\n'
        '{"case_id": "CASE-JSONL-002", "locus": {"target_uri": "http://172.28.0.10:3000/rest/search", "parameter": "term", "cwe_id": "CWE-79"}, "benchmark_target": "juice-shop", "benchmark_version": "15.0.0", "vulnerability_class": "XSS", "expected_label": "non_vulnerable", "ground_truth_provenance": "manual-audit", "review_status": "adjudicated", "inclusion_status": "included"}\n'
    )

    gt_jsonl = (
        '{"case_id": "CASE-JSONL-001", "locus": {"target_uri": "http://172.28.0.10:3000/rest/user", "parameter": "q", "cwe_id": "CWE-89"}, "expected_status": "vulnerable", "vulnerability_class": "SQLi", "evidence_reference": "REF-001", "adjudication_state": "adjudicated", "provenance": "audit"}\n'
        '{"case_id": "CASE-JSONL-002", "locus": {"target_uri": "http://172.28.0.10:3000/rest/search", "parameter": "term", "cwe_id": "CWE-79"}, "expected_status": "non_vulnerable", "vulnerability_class": "XSS", "evidence_reference": "REF-002", "adjudication_state": "adjudicated", "provenance": "audit"}\n'
    )

    from aegiscore.evaluation import validate_manifest_jsonl
    cases = validate_manifest_jsonl(manifest_jsonl)

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter(
        runner_id="runner-jsonl",
        case_manifests=cases,
        default_decision=FindingDecision.VERIFIED,
    )
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute_from_jsonl(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_jsonl=manifest_jsonl,
        ground_truth_jsonl=gt_jsonl,
        repeat_count=1,
    )

    assert report.unique_case_loci_count == 2
    # Case 1: VULN + VERIFIED = TP
    # Case 2: NON_VULN + VERIFIED = FP
    assert report.score_summary.tp_count == 1
    assert report.score_summary.fp_count == 1
    assert report.score_summary.metrics["precision"].value == 0.5


def test_harness_output_serialization_deterministic() -> None:
    """Report cleanly serializes to JSON dictionary and string deterministically."""
    cases = [_make_case(1)]
    gts = [_make_gt(1)]

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter("runner-json", cases)
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
    )

    dict_output = report.to_dict()
    assert isinstance(dict_output, dict)
    assert dict_output["manifest"]["is_synthetic_simulation"] is True
    assert "metrics" in dict_output["score_summary"]
    assert "brier_score" in dict_output["score_summary"]["metrics"]
    assert dict_output["score_summary"]["metrics"]["brier_score"]["status"] == "not_supported"

    json_str = report.to_json()
    assert isinstance(json_str, str)
    # Parse back to verify validity
    parsed = json.loads(json_str)
    assert parsed["manifest"]["manifest_id"] == dict_output["manifest"]["manifest_id"]


def test_harness_repeated_runs_split_decision_fails_closed_to_abstained() -> None:
    """When repeated trials (K=3) produce split decisions (1 verified, 1 rejected, 1 abstained), majority voting fails closed to ABSTAINED."""
    case = _make_case(1)
    gt = _make_gt(1, GroundTruthStatus.VULNERABLE)

    # Custom runner that produces varying decisions per repeat_index
    class SplitDecisionRunner(EvaluationRunnerInterface):
        runner_id = "runner-split"

        def run_case(self, case_manifest: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
            from aegiscore.evaluation import AssessmentResultRecord
            decisions = [FindingDecision.VERIFIED, FindingDecision.REJECTED, FindingDecision.ABSTAINED]
            dec = decisions[repeat_index % 3]
            run_id = f"run-split-{case_manifest.case_id}-rep{repeat_index}"
            return EvaluationRunRecord(
                run_id=run_id,
                runner_id=self.runner_id,
                case_id=case_manifest.case_id,
                repeat_index=repeat_index,
                result=AssessmentResultRecord(
                    case_id=case_manifest.case_id,
                    run_id=run_id,
                    decision=dec,
                    findings=(),
                ),
            )

    reg = RunnerConditionRegistry.create_default_registry()
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, SplitDecisionRunner())
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=[case],
        ground_truth_records=[gt],
        repeat_count=3,
    )

    assert report.trial_agreement.total_cases == 1
    assert report.trial_agreement.unanimous_cases_count == 0
    assert report.trial_agreement.split_decision_cases_count == 1
    assert report.trial_agreement.trial_agreement_rate == 0.0

    # Aggregated outcome must fail closed to ABSTAINED
    assert len(report.aggregated_outcomes) == 1
    agg_outcome = report.aggregated_outcomes[0]
    assert agg_outcome.system_decision == FindingDecision.ABSTAINED
    assert agg_outcome.classification == "ABSTAINED_POSITIVE"
    assert report.score_summary.abstained_positive_count == 1
    assert report.score_summary.fn_count == 1  # Abstained positive counted as empirical FN


def test_harness_rejects_duplicate_run_ids() -> None:
    """Harness fails closed if adapter returns duplicate run_id across executions."""
    case = _make_case(1)
    gt = _make_gt(1)

    class DuplicateRunIdRunner(EvaluationRunnerInterface):
        runner_id = "runner-dup"

        def run_case(self, case_manifest: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
            from aegiscore.evaluation import AssessmentResultRecord
            # Fixed duplicate run_id across repeats
            run_id = "constant-run-id"
            return EvaluationRunRecord(
                run_id=run_id,
                runner_id=self.runner_id,
                case_id=case_manifest.case_id,
                repeat_index=repeat_index,
                result=AssessmentResultRecord(
                    case_id=case_manifest.case_id,
                    run_id=run_id,
                    decision=FindingDecision.VERIFIED,
                ),
            )

    reg = RunnerConditionRegistry.create_default_registry()
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, DuplicateRunIdRunner())
    harness = EvaluationHarness(registry=reg)

    with pytest.raises(HarnessValidationError, match="Duplicate run_id 'constant-run-id' encountered"):
        harness.execute(
            condition=RunnerCondition.PROPOSED_MULTI_AGENT,
            manifest_records=[case],
            ground_truth_records=[gt],
            repeat_count=2,
        )


def test_harness_rejects_inconsistent_case_id_from_adapter() -> None:
    """Harness fails closed if adapter returns a run record for a different case_id."""
    case = _make_case(1)
    gt = _make_gt(1)

    class InconsistentCaseIdRunner(EvaluationRunnerInterface):
        runner_id = "runner-inconsistent"

        def run_case(self, case_manifest: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
            from aegiscore.evaluation import AssessmentResultRecord
            run_id = f"run-{case_manifest.case_id}-{repeat_index}"
            return EvaluationRunRecord(
                run_id=run_id,
                runner_id=self.runner_id,
                case_id="DIFFERENT-CASE-ID",  # Inconsistent!
                repeat_index=repeat_index,
                result=AssessmentResultRecord(
                    case_id="DIFFERENT-CASE-ID",
                    run_id=run_id,
                    decision=FindingDecision.VERIFIED,
                ),
            )

    reg = RunnerConditionRegistry.create_default_registry()
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, InconsistentCaseIdRunner())
    harness = EvaluationHarness(registry=reg)

    with pytest.raises(HarnessValidationError, match="does not match target case"):
        harness.execute(
            condition=RunnerCondition.PROPOSED_MULTI_AGENT,
            manifest_records=[case],
            ground_truth_records=[gt],
            repeat_count=1,
        )


def test_harness_rejects_malformed_manifest_jsonl() -> None:
    """Harness fails closed when malformed or invalid JSON is supplied in JSONL stream."""
    harness = EvaluationHarness()
    malformed_jsonl = '{"case_id": "CASE-001", "unclosed_brace": \n'
    gt_jsonl = '{"case_id": "CASE-001"}\n'

    from aegiscore.evaluation import EvaluationValidationError
    with pytest.raises(EvaluationValidationError):
        harness.execute_from_jsonl(
            condition=RunnerCondition.PROPOSED_MULTI_AGENT,
            manifest_jsonl=malformed_jsonl,
            ground_truth_jsonl=gt_jsonl,
        )


def test_harness_zero_network_access_guarantee(monkeypatch: pytest.MonkeyPatch) -> None:
    """Harness execution operates completely offline; any attempt to open network sockets fails immediately."""
    import socket

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network socket connection attempted during offline harness execution!")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    case = _make_case(1)
    gt = _make_gt(1)

    reg = RunnerConditionRegistry.create_default_registry()
    adapter = create_synthetic_fixture_adapter("runner-offline-guarantee", [case])
    reg.register_fixture_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    # Must complete cleanly with zero socket connections attempted
    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=[case],
        ground_truth_records=[gt],
        repeat_count=3,
    )
    assert report.manifest.is_synthetic_simulation is True
    assert report.score_summary.tp_count == 1


