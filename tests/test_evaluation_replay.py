"""End-to-end integration tests for Phase 8F.3: Evaluation Harness Integration & Offline Replay.

Verifies:
- Harness invokes the genuine OrchestrationStateMachine and UncertaintyAggregationEngine.
- Uncertainty engine recommendations directly influence harness results (VERIFIED, REJECTED, ABSTAINED).
- Evidence-supported synthetic cases proceed to verified positive outcomes.
- Insufficient or missing evidence causes fail-closed abstention.
- Adversarial evidence reviewer rejection produces REJECTED terminal result.
- Specialist disagreement preserves correct reason codes and causes abstention.
- Invalid citations or excerpt mismatch cannot produce a verified positive result.
- Run records correspond to correct case and repeat index without canonical loci inflation.
- Scores can be traced back to case-level outcomes.
- Unknown, planned, or prohibited conditions fail closed with distinct typed errors.
- Unexpected orchestration exceptions fail closed and cannot produce successful assessments.
- Deterministic fixture replays produce identical outputs across repeated executions.
- Invariants: confidence_is_calibrated=False, factual_support='not_evaluated'.

STRICT RESTRICTION: Fully offline only. Zero network requests, zero container
operations, zero LLM provider calls, zero scanner executions. All fixture results
are explicitly marked as synthetic simulations.
"""

from __future__ import annotations

import hashlib
import json
import pytest

from aegiscore.orchestration import (
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    OrchestrationState,
    SpecialistFinding,
    ClaimCitationRecord,
)
from aegiscore.generation import (
    GeneratedClaim,
    CitationGroundingError,
)
from aegiscore.rag import (
    CitationReference,
    SourceChunk,
    SourceMetadata,
    SourceReviewState,
)
from aegiscore.uncertainty_engine import (
    AggregationRecommendation,
    UncertaintyReasonCode,
)
from aegiscore.evaluation import (
    AdjudicationState,
    CanonicalLocus,
    EvaluationCaseManifestRecord,
    FindingDecision,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    RunnerCondition,
)
from aegiscore.evaluation_harness import (
    ConditionNotRegisteredError,
    ConditionStatus,
    ConditionUnavailableError,
    EvaluationHarness,
    HarnessValidationError,
    LiveExecutionProhibitedError,
    OrchestrationCaseFixture,
    OrchestrationReplayAdapter,
    RunnerConditionRegistry,
    create_orchestration_case_fixture,
    create_orchestration_replay_adapter,
)


# ---------------------------------------------------------------------------
# Test Helpers & Fixture Builders
# ---------------------------------------------------------------------------

def _make_locus(case_num: int, cwe: str = "CWE-89") -> CanonicalLocus:
    return CanonicalLocus(
        target_uri=f"http://172.28.0.10:3000/api/endpoint/{case_num}",
        parameter=f"param_{case_num}",
        cwe_id=cwe,
    )


def _make_case(
    case_num: int,
    cwe: str = "CWE-89",
    expected_label: GroundTruthStatus = GroundTruthStatus.VULNERABLE,
    adjudication_state: AdjudicationState = AdjudicationState.ADJUDICATED,
) -> EvaluationCaseManifestRecord:
    return EvaluationCaseManifestRecord(
        case_id=f"CASE-REPLAY-{case_num:03d}",
        locus=_make_locus(case_num, cwe),
        benchmark_target="synthetic-replay-benchmark",
        benchmark_version="1.0.0",
        vulnerability_class="SQLI" if cwe == "CWE-89" else "XSS",
        expected_label=expected_label,
        ground_truth_provenance="synthetic-offline-test",
        review_status=adjudication_state,
        inclusion_status=InclusionStatus.INCLUDED,
    )


def _make_gt(
    case_num: int,
    status: GroundTruthStatus = GroundTruthStatus.VULNERABLE,
    cwe: str = "CWE-89",
    adjudication_state: AdjudicationState = AdjudicationState.ADJUDICATED,
) -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=f"CASE-REPLAY-{case_num:03d}",
        locus=_make_locus(case_num, cwe),
        expected_status=status,
        vulnerability_class="SQLI" if cwe == "CWE-89" else "XSS",
        evidence_reference="EVID-REF-001",
        adjudication_state=adjudication_state,
        provenance="synthetic-offline-test",
    )


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_harness_invokes_genuine_orchestration_state_machine() -> None:
    """Demonstrate that the evaluation harness invokes the genuine OrchestrationStateMachine."""
    case = _make_case(1)
    gt = _make_gt(1)

    adapter = create_orchestration_replay_adapter("test-runner", [case])
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=[case],
        ground_truth_records=[gt],
        repeat_count=1,
    )

    assert len(report.raw_trial_runs) == 1
    run = report.raw_trial_runs[0]
    meta = run.reproducibility_metadata

    assert meta["adapter_type"] == "OrchestrationReplayAdapter"
    assert meta["final_state"] == OrchestrationState.COMPLETED.value
    assert "request_received->request_validated" in meta["trajectory"]
    assert "request_validated->retrieval_completed" in meta["trajectory"]
    assert "retrieval_completed->specialist_analysis_completed" in meta["trajectory"]
    assert "specialist_analysis_completed->evidence_review_completed" in meta["trajectory"]
    assert "evidence_review_completed->uncertainty_assessed" in meta["trajectory"]
    assert "uncertainty_assessed->validation_completed" in meta["trajectory"]
    assert "validation_completed->completed" in meta["trajectory"]

    assert meta["confidence_is_calibrated"] == "False"
    assert meta["uncertainty_recommendation"] == AggregationRecommendation.CONTINUE.value
    assert run.result.decision == FindingDecision.VERIFIED
    assert len(run.result.findings) == 1
    assert run.result.findings[0].vulnerability_identified is True


def test_uncertainty_engine_affects_harness_result() -> None:
    """Verify that the uncertainty engine directly influences the final result returned to the harness."""
    case_ok = _make_case(1)
    gt_ok = _make_gt(1)

    case_abstain = _make_case(2)
    gt_abstain = _make_gt(2)

    # Case 1: valid evidence -> uncertainty engine recommends CONTINUE -> VERIFIED
    fixture_ok = create_orchestration_case_fixture(
        case_ok,
        evidence_text="Direct query concatenation: SELECT * FROM users WHERE id = ' + param",
        review_notes="Evidence is verified and excerpt exists verbatim.",
    )

    # Case 2: insufficient evidence forced -> uncertainty engine recommends ABSTAIN
    fixture_abstain = create_orchestration_case_fixture(
        case_abstain,
        evidence_text="Concatenation query.",
        force_sufficient=False,
    )

    adapter = OrchestrationReplayAdapter(
        runner_id="uncertainty-adapter",
        case_fixtures={
            case_ok.case_id: fixture_ok,
            case_abstain.case_id: fixture_abstain,
        },
    )

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=[case_ok, case_abstain],
        ground_truth_records=[gt_ok, gt_abstain],
    )

    run_map = {r.case_id: r for r in report.raw_trial_runs}
    run_ok = run_map[case_ok.case_id]
    run_abs = run_map[case_abstain.case_id]

    assert run_ok.result.decision == FindingDecision.VERIFIED
    assert run_ok.reproducibility_metadata["uncertainty_recommendation"] == "continue"

    assert run_abs.result.decision == FindingDecision.ABSTAINED
    assert run_abs.reproducibility_metadata["final_state"] == OrchestrationState.ABSTAINED.value
    assert run_abs.reproducibility_metadata["uncertainty_recommendation"] == "abstain"


def test_evidence_supported_synthetic_cases_proceed_as_expected() -> None:
    """Verify evidence-supported synthetic cases produce true positive outcomes."""
    case = _make_case(1, cwe="CWE-89")
    gt = _make_gt(1, status=GroundTruthStatus.VULNERABLE, cwe="CWE-89")

    adapter = create_orchestration_replay_adapter("replay-adapter", [case])
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    assert len(report.aggregated_outcomes) == 1
    outcome = report.aggregated_outcomes[0]
    assert outcome.classification == "TP"
    assert outcome.system_decision == FindingDecision.VERIFIED
    assert report.score_summary.tp_count == 1
    assert report.score_summary.fp_count == 0
    assert report.score_summary.metrics["precision"].value == 1.0
    assert report.score_summary.metrics["recall"].value == 1.0


def test_insufficient_evidence_causes_abstention() -> None:
    """Verify that an empty or missing evidence bundle causes fail-closed abstention."""
    case = _make_case(1, expected_label=GroundTruthStatus.VULNERABLE)
    gt = _make_gt(1, status=GroundTruthStatus.VULNERABLE)

    # Empty evidence bundle triggers record_retrieval abstention
    fixture = create_orchestration_case_fixture(case, evidence_text="")
    adapter = OrchestrationReplayAdapter("replay-adapter", {case.case_id: fixture})

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    run = report.raw_trial_runs[0]
    assert run.result.decision == FindingDecision.ABSTAINED
    assert run.reproducibility_metadata["final_state"] == OrchestrationState.ABSTAINED.value
    assert "retrieval_completed->abstained" in run.reproducibility_metadata["trajectory"]

    outcome = report.aggregated_outcomes[0]
    # For a vulnerable target, abstention is scored as ABSTAINED_POSITIVE (not covered FN)
    assert outcome.classification == "ABSTAINED_POSITIVE"
    assert report.score_summary.abstained_positive_count == 1


def test_reviewer_rejection_produces_rejected_terminal_result() -> None:
    """Verify that adversarial evidence reviewer rejection causes REJECTED terminal result."""
    case = _make_case(1, expected_label=GroundTruthStatus.NON_VULNERABLE)
    gt = _make_gt(1, status=GroundTruthStatus.NON_VULNERABLE)

    fixture = create_orchestration_case_fixture(
        case,
        review_notes="REJECTED: Grounding fails completely. DECISION: REJECT hypothesis.",
    )
    adapter = OrchestrationReplayAdapter("replay-adapter", {case.case_id: fixture})

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    run = report.raw_trial_runs[0]
    assert run.result.decision == FindingDecision.REJECTED
    assert run.reproducibility_metadata["final_state"] == OrchestrationState.REJECTED.value
    assert run.reproducibility_metadata["uncertainty_recommendation"] == "reject"
    assert (
        run.reproducibility_metadata["uncertainty_primary_reason"]
        == UncertaintyReasonCode.REVIEWER_REJECTION.value
    )

    # Rejecting a non-vulnerable scenario produces a True Negative (TN)
    outcome = report.aggregated_outcomes[0]
    assert outcome.classification == "TN"
    assert report.score_summary.tn_count == 1


def test_specialist_disagreement_preserves_reason_codes() -> None:
    """Verify specialist disagreement preserves reason codes and leads to abstention."""
    case = _make_case(1)
    gt = _make_gt(1)

    # Primary finding is SQLi
    # Secondary finding asserts no vulnerability or conflicting CWE
    digest = hashlib.sha256(b"Evidence chunk").hexdigest()
    src_meta = SourceMetadata(source_id="SRC-TEST-001", content_sha256=digest, review_state=SourceReviewState.APPROVED)
    chunk = SourceChunk(chunk_id="CHK-TEST-001", provenance=src_meta, ordinal=0, start_offset=0, end_offset=14, content="Evidence chunk", content_sha256=digest)
    cit_ref = CitationReference(source_id="SRC-TEST-001", chunk_id="CHK-TEST-001")

    secondary = SpecialistFinding(
        finding_id=f"fnd-{case.case_id}-sec",
        request_id=f"req-{case.case_id}",
        specialist_role="secondary_specialist",
        vulnerability_identified=False,  # Conflict: primary says True, secondary says False
        severity=FindingSeverity.INFO,
        summary="Secondary analysis concluded not vulnerable",
        proposed_claims=(),
        claim_citations=(),
    )

    fixture = create_orchestration_case_fixture(
        case,
        evidence_text="Evidence chunk",
        secondary_findings=(secondary,),
    )
    adapter = OrchestrationReplayAdapter("replay-adapter", {case.case_id: fixture})

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    run = report.raw_trial_runs[0]
    assert run.result.decision == FindingDecision.ABSTAINED
    assert run.reproducibility_metadata["uncertainty_recommendation"] == "abstain"
    assert (
        run.reproducibility_metadata["uncertainty_primary_reason"]
        == UncertaintyReasonCode.SPECIALIST_DISAGREEMENT.value
    )
    assert "specialist_disagreement" in run.reproducibility_metadata["uncertainty_contributing_reasons"]


def test_invalid_citations_cannot_produce_verified_positive_result() -> None:
    """Verify that an invalid citation excerpt or non-existent chunk ID cannot produce a verified result."""
    case = _make_case(1)
    gt = _make_gt(1)

    # Create evidence bundle with one chunk
    digest = hashlib.sha256(b"Genuine server response text").hexdigest()
    src_meta = SourceMetadata(source_id="SRC-TEST-001", content_sha256=digest, review_state=SourceReviewState.APPROVED)
    chunk = SourceChunk(
        chunk_id="CHK-TEST-001",
        provenance=src_meta,
        ordinal=0,
        start_offset=0,
        end_offset=28,
        content="Genuine server response text",
        content_sha256=digest,
    )
    cit_ref = CitationReference(source_id="SRC-TEST-001", chunk_id="CHK-TEST-001")
    bundle = EvidenceBundle(
        bundle_id=f"bnd-{case.case_id}",
        request_id=f"req-{case.case_id}",
        retrieval_query="vulnerability query",
        chunks=(chunk,),
        citations=(cit_ref,),
        manifest_fingerprint=digest,
        approved_source_count=1,
    )

    # Specialist finding with non-matching cited excerpt
    claim = GeneratedClaim(text="Fabricated exploit claim", citations=(cit_ref,))
    claim_cit = ClaimCitationRecord(
        claim_id=f"clm-{case.case_id}",
        citation=cit_ref,
        cited_excerpt="This substring does not exist in chunk",
    )
    finding = SpecialistFinding(
        finding_id=f"fnd-{case.case_id}",
        request_id=f"req-{case.case_id}",
        specialist_role="vulnerability_specialist:sqli",
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="Analysis with invalid excerpt",
        proposed_claims=(claim,),
        cwe_id="CWE-89",
        claim_citations=(claim_cit,),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://172.28.0.10:3000/api/endpoint/1",
        authorized_scope=("/",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=finding,
        review_notes="Reviewer passed",
    )

    adapter = OrchestrationReplayAdapter("replay-adapter", {case.case_id: fixture})
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    run = report.raw_trial_runs[0]
    # Fail-closed: cannot become VERIFIED
    assert run.result.decision != FindingDecision.VERIFIED
    assert run.result.is_incomplete is True
    assert run.result.error_status is not None
    assert "CitationGroundingError" in run.result.error_status
    assert run.reproducibility_metadata["final_state"] == OrchestrationState.FAILED.value


def test_run_records_correspond_to_correct_case_and_repeat_index() -> None:
    """Verify that run records preserve correct case_id and repeat_index across trials."""
    cases = [_make_case(i) for i in range(1, 4)]
    gts = [_make_gt(i) for i in range(1, 4)]

    adapter = create_orchestration_replay_adapter("replay-adapter", cases)
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    repeat_count = 3
    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
        repeat_count=repeat_count,
    )

    assert len(report.raw_trial_runs) == len(cases) * repeat_count
    seen_runs: set[str] = set()

    for r in report.raw_trial_runs:
        assert r.run_id not in seen_runs
        seen_runs.add(r.run_id)
        assert r.repeat_index in (0, 1, 2)
        assert r.case_id in {c.case_id for c in cases}
        assert r.reproducibility_metadata["repeat_index"] == str(r.repeat_index)
        assert r.reproducibility_metadata["case_id"] == r.case_id


def test_repeated_trials_retained_individually_and_aggregated_without_loci_inflation() -> None:
    """Verify repeated trials do not inflate the canonical Unit of Analysis (N)."""
    cases = [_make_case(i) for i in range(1, 5)]  # N=4 cases
    gts = [_make_gt(i) for i in range(1, 5)]

    adapter = create_orchestration_replay_adapter("replay-adapter", cases)
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(
        condition=RunnerCondition.PROPOSED_MULTI_AGENT,
        manifest_records=cases,
        ground_truth_records=gts,
        repeat_count=3,
    )

    # 4 cases * 3 repeats = 12 raw trial runs
    assert len(report.raw_trial_runs) == 12
    # Canonical loci count must remain exactly 4
    assert report.unique_case_loci_count == 4
    assert len(report.aggregated_outcomes) == 4
    assert report.trial_agreement.total_cases == 4
    assert report.trial_agreement.unanimous_cases_count == 4
    assert report.trial_agreement.trial_agreement_rate == 1.0


def test_scores_can_be_traced_back_to_case_level_outcomes() -> None:
    """Verify that aggregate score summary is directly traceable to case-level outcomes."""
    cases = [
        _make_case(1, expected_label=GroundTruthStatus.VULNERABLE),
        _make_case(2, expected_label=GroundTruthStatus.NON_VULNERABLE),
    ]
    gts = [
        _make_gt(1, status=GroundTruthStatus.VULNERABLE),
        _make_gt(2, status=GroundTruthStatus.NON_VULNERABLE),
    ]

    fixture_tp = create_orchestration_case_fixture(cases[0])
    fixture_tn = create_orchestration_case_fixture(
        cases[1],
        review_notes="REJECTED: Grounding fails. DECISION: REJECT.",
    )

    adapter = OrchestrationReplayAdapter(
        "replay-adapter",
        {cases[0].case_id: fixture_tp, cases[1].case_id: fixture_tn},
    )

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, cases, gts)

    outcomes_by_id = {o.case_id: o for o in report.aggregated_outcomes}
    assert outcomes_by_id[cases[0].case_id].classification == "TP"
    assert outcomes_by_id[cases[1].case_id].classification == "TN"

    scores = report.score_summary
    assert scores.tp_count == 1
    assert scores.tn_count == 1
    assert scores.fp_count == 0
    assert scores.fn_count == 0
    assert scores.total_cases == 2


def test_unknown_and_unavailable_conditions_fail_closed() -> None:
    """Verify unknown, planned, or live-prohibited conditions fail closed without silent fallback."""
    reg = RunnerConditionRegistry.create_default_registry()

    # 1. Unknown condition string
    with pytest.raises(ConditionNotRegisteredError):
        reg.get_adapter("unknown-custom-condition")

    # 2. Planned but unavailable baseline
    with pytest.raises(ConditionUnavailableError) as exc_info:
        reg.get_adapter(RunnerCondition.BASELINE_SINGLE_AGENT)
    assert "PLANNED_UNAVAILABLE" in str(exc_info.value)

    # 3. Live execution prohibited baseline
    with pytest.raises(LiveExecutionProhibitedError) as exc_info:
        reg.get_adapter(RunnerCondition.BASELINE_DAST_ZAP)
    assert "LIVE_PROHIBITED" in str(exc_info.value)


def test_unexpected_exceptions_cannot_produce_successful_assessment() -> None:
    """Verify that unexpected exceptions in the state machine workflow fail closed and never yield VERIFIED."""
    case = _make_case(1)
    gt = _make_gt(1)

    # Target URL violating lab scope (e.g. public external IP) causes ScopeViolationError
    fixture = create_orchestration_case_fixture(
        case,
        target_url="http://8.8.8.8/api/endpoint",  # Public IP forbidden in lab scope
    )
    adapter = OrchestrationReplayAdapter("replay-adapter", {case.case_id: fixture})

    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    report = harness.execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [gt])

    run = report.raw_trial_runs[0]
    assert run.result.decision != FindingDecision.VERIFIED
    assert run.result.is_incomplete is True
    assert "ScopeViolationError" in (run.result.error_status or "")
    assert run.reproducibility_metadata["final_state"] == "init_failed"


def test_identical_fixture_inputs_produce_deterministic_outputs() -> None:
    """Verify that replaying identical fixture sets produces byte-for-byte deterministic outcomes."""
    cases = [_make_case(i) for i in range(1, 4)]
    gts = [_make_gt(i) for i in range(1, 4)]

    adapter1 = create_orchestration_replay_adapter("replay-adapter", cases)
    adapter2 = create_orchestration_replay_adapter("replay-adapter", cases)

    reg1 = RunnerConditionRegistry()
    reg1.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter1)
    harness1 = EvaluationHarness(registry=reg1)

    reg2 = RunnerConditionRegistry()
    reg2.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter2)
    harness2 = EvaluationHarness(registry=reg2)

    rep1 = harness1.execute(RunnerCondition.PROPOSED_MULTI_AGENT, cases, gts, repeat_count=2)
    rep2 = harness2.execute(RunnerCondition.PROPOSED_MULTI_AGENT, cases, gts, repeat_count=2)

    assert rep1.manifest.configuration_fingerprint == rep2.manifest.configuration_fingerprint
    assert len(rep1.raw_trial_runs) == len(rep2.raw_trial_runs)

    for r1, r2 in zip(rep1.raw_trial_runs, rep2.raw_trial_runs):
        assert r1.run_id == r2.run_id
        assert r1.result.decision == r2.result.decision
        assert r1.reproducibility_metadata["trajectory"] == r2.reproducibility_metadata["trajectory"]
        assert r1.reproducibility_metadata["reason_codes"] == r2.reproducibility_metadata["reason_codes"]

    # Score summaries must match deterministically
    assert rep1.score_summary.tp_count == rep2.score_summary.tp_count
    assert rep1.score_summary.fp_count == rep2.score_summary.fp_count
    assert rep1.score_summary.fn_count == rep2.score_summary.fn_count
    assert rep1.score_summary.tn_count == rep2.score_summary.tn_count
    assert rep1.score_summary.total_cases == rep2.score_summary.total_cases


def test_strict_adjudication_fails_closed_on_unadjudicated_case() -> None:
    """Verify that strict adjudication check rejects unadjudicated ground truth."""
    case = _make_case(1, adjudication_state=AdjudicationState.UNVERIFIED)
    gt = _make_gt(1, adjudication_state=AdjudicationState.UNVERIFIED)

    adapter = create_orchestration_replay_adapter("replay-adapter", [case])
    reg = RunnerConditionRegistry()
    reg.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    harness = EvaluationHarness(registry=reg)

    with pytest.raises(HarnessValidationError) as exc_info:
        harness.execute(
            condition=RunnerCondition.PROPOSED_MULTI_AGENT,
            manifest_records=[case],
            ground_truth_records=[gt],
            strict_adjudication=True,
        )
    assert "strict_adjudication requires 'adjudicated'" in str(exc_info.value)
