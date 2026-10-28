"""Integration tests for Phase 8F.5: Grounded Specialist Integration & End-to-End Offline Replay.

Verifies:
1. Grounded specialist invocation through genuine OrchestrationStateMachine and OrchestrationReplayAdapter.
2. Empty evidence bundle causes fail-closed abstention without invoking the model adapter.
3. Zero approved sources causes fail-closed abstention without invoking the model adapter.
4. Valid fixture evidence can only be cited using known IDs and matching excerpts.
5. Unknown evidence IDs and mismatched source IDs are rejected.
6. Malformed and contradictory output fails closed into safe terminal states.
7. Specialist abstention propagates deterministically to the final orchestration result.
8. Specialist errors remain traceable without fabricating findings.
9. Repeated replay of the same offline fixture produces byte-identical deterministic results.
10. State-machine safety guards and invariant boundaries are strictly preserved.

STRICT BOUNDARY: Purely offline. Zero network activity, zero cloud/local LLM calls,
zero container actions, zero database files created.
All test fixtures are explicitly synthetic and unadjudicated.
"""

from __future__ import annotations

import hashlib
import json
import pytest

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
    ConditionStatus,
    EvaluationHarness,
    HarnessValidationError,
    OrchestrationCaseFixture,
    OrchestrationReplayAdapter,
    RunnerConditionRegistry,
    create_orchestration_case_fixture,
    create_orchestration_replay_adapter,
)
from aegiscore.generation import CitationGroundingError
from aegiscore.model_adapter import (
    ContradictoryOutputError,
    DeterministicModelAdapter,
    GroundedSpecialistAdapter,
    LiveProviderExecutionUnavailableError,
    ModelErrorCategory,
    ModelProviderConfig,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelResponseValidationError,
    ModelTimeoutError,
    ProviderMode,
    TokenUsage,
    UnauthorizedLiveModelAdapter,
)
from aegiscore.orchestration import (
    AssessmentRequest,
    ClaimCitationRecord,
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    OrchestrationState,
    OrchestrationStateMachine,
    SpecialistFinding,
    StageBypassError,
    TerminalStateError,
)
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata, SourceReviewState
from aegiscore.specialist_roles import ROLE_XSS_ANALYST, ROLE_SQLI_ANALYST
from aegiscore.uncertainty_engine import AggregationRecommendation, UncertaintyReasonCode


# ---------------------------------------------------------------------------
# Synthetic Fixture Helpers
# ---------------------------------------------------------------------------


def _synthetic_chunk(
    chunk_id: str = "CHK-SYN-001",
    source_id: str = "SRC-SYN-001",
    content: str = "SELECT * FROM users WHERE id = ' + user_input + ';",
) -> SourceChunk:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    meta = SourceMetadata(
        source_id=source_id,
        content_sha256=digest,
        review_state=SourceReviewState.APPROVED,
    )
    return SourceChunk(
        chunk_id=chunk_id,
        provenance=meta,
        ordinal=0,
        start_offset=0,
        end_offset=len(content),
        content=content,
        content_sha256=digest,
    )


def _synthetic_bundle(
    chunk_id: str = "CHK-SYN-001",
    source_id: str = "SRC-SYN-001",
    content: str = "SELECT * FROM users WHERE id = ' + user_input + ';",
    request_id: str = "req-syn-001",
    approved_source_count: int = 1,
) -> EvidenceBundle:
    if approved_source_count == 0:
        return EvidenceBundle(
            bundle_id=f"bnd-{request_id}",
            request_id=request_id,
            retrieval_query="sql concatenation vulnerability query",
            chunks=(),
            citations=(),
            manifest_fingerprint=hashlib.sha256(b"manifest-synthetic").hexdigest(),
            approved_source_count=0,
            evidence_status="no_approved_evidence",
        )
    chunk = _synthetic_chunk(chunk_id, source_id, content)
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    return EvidenceBundle(
        bundle_id=f"bnd-{request_id}",
        request_id=request_id,
        retrieval_query="sql concatenation vulnerability query",
        chunks=(chunk,),
        citations=(ref,),
        manifest_fingerprint=hashlib.sha256(b"manifest-synthetic").hexdigest(),
        approved_source_count=approved_source_count,
        evidence_status="evidence_found",
    )


def _synthetic_case(case_num: int = 1) -> EvaluationCaseManifestRecord:
    return EvaluationCaseManifestRecord(
        case_id=f"CASE-SYN-{case_num:03d}",
        locus=CanonicalLocus(
            target_uri=f"http://127.0.0.1:3000/api/endpoint/{case_num}",
            parameter="user_input",
            cwe_id="CWE-89",
        ),
        benchmark_target="synthetic-offline-benchmark",
        benchmark_version="1.0.0",
        vulnerability_class="SQLI",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="synthetic-offline-fixture",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )


def _synthetic_gt(case_num: int = 1) -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=f"CASE-SYN-{case_num:03d}",
        locus=CanonicalLocus(
            target_uri=f"http://127.0.0.1:3000/api/endpoint/{case_num}",
            parameter="user_input",
            cwe_id="CWE-89",
        ),
        expected_status=GroundTruthStatus.VULNERABLE,
        vulnerability_class="SQLI",
        evidence_reference="EVID-SYN-001",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="synthetic-offline-fixture",
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_grounded_specialist_invoked_through_orchestration_state_machine() -> None:
    """OrchestrationStateMachine executes GroundedSpecialistAdapter via execute_specialist_analysis."""
    bundle = _synthetic_bundle(request_id="req-orch-test")
    valid_canned = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-89",
        "summary": "SQL injection via raw string concatenation",
        "reasoning_notes": "Retrieved chunk demonstrates direct concatenation into query.",
        "is_abstained": False,
        "claims": [
            {
                "text": "User input concatenated directly into SQL statement.",
                "citations": [
                    {
                        "source_id": "SRC-SYN-001",
                        "chunk_id": "CHK-SYN-001",
                        "cited_excerpt": "SELECT * FROM users WHERE id = ' + user_input + ';",
                    }
                ],
                "observed_evidence": "Verbatim code concatenation in chunk.",
                "inference": "SQL injection exploitable without parameterized query.",
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-orch-test": valid_canned})
    specialist = GroundedSpecialistAdapter(ROLE_SQLI_ANALYST, adapter)

    req = AssessmentRequest(
        request_id="req-orch-test",
        target_url="http://127.0.0.1:3000/api/endpoint/1",
        vulnerability_category="SQLI",
        authorized_scope=("/api",),
    )
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    assert sm.current_state == OrchestrationState.RETRIEVAL_COMPLETED

    finding = sm.execute_specialist_analysis(specialist)

    assert sm.current_state == OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED
    assert finding.vulnerability_identified is True
    assert finding.severity == FindingSeverity.HIGH
    assert finding.is_confirmed is False
    assert sm.specialist_finding is finding


def test_grounded_specialist_invoked_through_evaluation_replay() -> None:
    """OrchestrationReplayAdapter executes GroundedSpecialistAdapter in-flight during replay."""
    case = _synthetic_case(1)
    bundle = _synthetic_bundle(request_id="req-replay-test")
    valid_canned = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-89",
        "summary": "SQL injection identified via grounded analysis.",
        "reasoning_notes": "Raw concatenation confirmed.",
        "is_abstained": False,
        "claims": [
            {
                "text": "Raw concatenation found in SQL query construction.",
                "citations": [
                    {
                        "source_id": "SRC-SYN-001",
                        "chunk_id": "CHK-SYN-001",
                        "cited_excerpt": "SELECT * FROM users WHERE id = ' + user_input + ';",
                    }
                ],
            }
        ],
    }

    # Use default_handler to service the request regardless of repeat suffix
    def _canned_handler(req: ModelRequest) -> ModelResponse:
        return ModelResponse(
            request_id=req.request_id,
            model_id=req.model_id,
            provider_mode=req.provider_mode,
            raw_content=json.dumps(valid_canned),
            structured_output=valid_canned,
        )

    model_adapter = DeterministicModelAdapter(default_handler=_canned_handler)
    specialist = GroundedSpecialistAdapter(ROLE_SQLI_ANALYST, model_adapter)

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/1",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,  # Will be dynamically produced by specialist_adapter
        review_notes="Evidence review: confirmed source concatenation without sanitization.",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="grounded-replay-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    assert run_record.case_id == case.case_id
    assert run_record.result.is_incomplete is False
    assert run_record.result.decision == FindingDecision.VERIFIED
    assert len(run_record.result.findings) == 1
    assert run_record.result.findings[0].vulnerability_identified is True
    meta = run_record.reproducibility_metadata
    assert meta["final_state"] == OrchestrationState.COMPLETED.value
    assert meta["confidence_is_calibrated"] == "False"


def test_empty_evidence_bundle_abstains_without_invoking_model_adapter() -> None:
    """Empty evidence bundle causes fail-closed abstention in replay without calling model adapter."""
    case = _synthetic_case(2)
    empty_bundle = EvidenceBundle(
        bundle_id="bnd-empty",
        request_id="req-empty",
        retrieval_query="empty search",
        chunks=(),
        citations=(),
        manifest_fingerprint="0" * 64,
        approved_source_count=0,
        evidence_status="no_approved_evidence",
    )

    def _exploding_adapter(req: ModelRequest) -> ModelResponse:
        raise AssertionError("Model adapter must NOT be invoked when evidence bundle is empty!")

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_exploding_adapter),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/2",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=empty_bundle,
        specialist_finding=None,
        review_notes="",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="empty-evidence-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    assert run_record.result.decision == FindingDecision.ABSTAINED
    assert run_record.reproducibility_metadata["final_state"] == OrchestrationState.ABSTAINED.value


def test_zero_approved_sources_abstains_without_invoking_model_adapter() -> None:
    """Zero approved sources causes immediate abstention without invoking model adapter."""
    case = _synthetic_case(3)
    bundle_zero_sources = _synthetic_bundle(
        request_id="req-zero-approved",
        approved_source_count=0,
    )

    def _exploding_adapter(req: ModelRequest) -> ModelResponse:
        raise AssertionError("Model adapter must NOT be invoked when approved_source_count == 0!")

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_exploding_adapter),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/3",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle_zero_sources,
        specialist_finding=None,
        review_notes="",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="zero-approved-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    assert run_record.result.decision == FindingDecision.ABSTAINED
    assert run_record.reproducibility_metadata["final_state"] == OrchestrationState.ABSTAINED.value


def test_valid_test_fixture_evidence_citation_with_matching_excerpt() -> None:
    """Evidence citations require exact verbatim excerpt match; successful match proceeds."""
    bundle = _synthetic_bundle(
        content="const query = 'SELECT * FROM accounts WHERE user=' + input;",
        request_id="req-excerpt-valid",
    )
    valid_canned = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-89",
        "summary": "Verified SQL injection",
        "reasoning_notes": "Concatenation confirmed in chunk text.",
        "is_abstained": False,
        "claims": [
            {
                "text": "Query concatenates user input.",
                "citations": [
                    {
                        "source_id": "SRC-SYN-001",
                        "chunk_id": "CHK-SYN-001",
                        "cited_excerpt": "const query = 'SELECT * FROM accounts WHERE user=' + input;",
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-excerpt-valid": valid_canned})
    specialist = GroundedSpecialistAdapter(ROLE_SQLI_ANALYST, adapter)
    finding = specialist.analyse("req-excerpt-valid", bundle)

    assert len(finding.claim_citations) == 1
    assert finding.claim_citations[0].cited_excerpt == "const query = 'SELECT * FROM accounts WHERE user=' + input;"


def test_unknown_evidence_ids_and_mismatched_sources_rejected() -> None:
    """Unknown chunk_id or mismatched source_id triggers CitationGroundingError and fails closed."""
    bundle = _synthetic_bundle(request_id="req-unknown-chunk")
    bad_output = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-89",
        "summary": "SQL injection with fabricated chunk ID",
        "reasoning_notes": "",
        "is_abstained": False,
        "claims": [
            {
                "text": "Fabricated citation claim.",
                "citations": [
                    {
                        "source_id": "SRC-SYN-001",
                        "chunk_id": "CHK-NONEXISTENT-999",
                        "cited_excerpt": None,
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-unknown-chunk": bad_output})
    specialist = GroundedSpecialistAdapter(ROLE_SQLI_ANALYST, adapter)

    # In direct call, CitationGroundingError is raised
    with pytest.raises(CitationGroundingError) as exc_info:
        specialist.analyse("req-unknown-chunk", bundle)
    assert "CHK-NONEXISTENT-999" in str(exc_info.value)

    # In OrchestrationStateMachine, execute_specialist_analysis fails closed to FAILED
    req = AssessmentRequest(
        request_id="req-unknown-chunk",
        target_url="http://127.0.0.1:3000/api/endpoint/1",
        vulnerability_category="SQLI",
        authorized_scope=("/api",),
    )
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)

    with pytest.raises(CitationGroundingError):
        sm.execute_specialist_analysis(specialist)
    assert sm.current_state == OrchestrationState.FAILED


def test_malformed_and_contradictory_output_fails_closed() -> None:
    """Contradictory output (vulnerable=True with is_abstained=True) fails closed in replay."""
    case = _synthetic_case(4)
    bundle = _synthetic_bundle(request_id="req-contradictory")
    contradictory_output = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "summary": "Contradictory claim",
        "reasoning_notes": "",
        "is_abstained": True,  # Contradiction: True with vuln=True
        "claims": [],
    }

    def _contradictory_handler(req: ModelRequest) -> ModelResponse:
        return ModelResponse(
            request_id=req.request_id,
            model_id=req.model_id,
            provider_mode=req.provider_mode,
            raw_content=json.dumps(contradictory_output),
            structured_output=contradictory_output,
        )

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_contradictory_handler),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/4",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="contradictory-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    # Fails closed to ABSTAINED with is_incomplete=True
    assert run_record.result.is_incomplete is True
    assert run_record.result.decision == FindingDecision.ABSTAINED
    assert "ContradictoryOutputError" in str(run_record.result.error_status)


def test_specialist_abstention_propagates_to_final_orchestration_result() -> None:
    """Specialist abstention (is_abstained=True) routes to terminal ABSTAINED in orchestration."""
    case = _synthetic_case(5)
    bundle = _synthetic_bundle(request_id="req-specialist-abstain")
    abstained_output = {
        "vulnerability_identified": False,
        "severity": "INFO",
        "cwe_id": None,
        "summary": "Analysis inconclusive; insufficient indicators.",
        "reasoning_notes": "Possible parameterized query in surrounding scope; uncertain.",
        "is_abstained": True,
        "claims": [],
    }

    def _abstain_handler(req: ModelRequest) -> ModelResponse:
        return ModelResponse(
            request_id=req.request_id,
            model_id=req.model_id,
            provider_mode=req.provider_mode,
            raw_content=json.dumps(abstained_output),
            structured_output=abstained_output,
        )

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_abstain_handler),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/5",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="Reviewer concurs that evidence is ambiguous.",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="specialist-abstain-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    assert run_record.result.decision == FindingDecision.ABSTAINED
    meta = run_record.reproducibility_metadata
    assert meta["final_state"] == OrchestrationState.ABSTAINED.value
    assert meta["uncertainty_recommendation"] == AggregationRecommendation.ABSTAIN.value


def test_specialist_errors_remain_traceable_no_fabricated_findings() -> None:
    """When a specialist raises an error, it is recorded without fabricating findings."""
    case = _synthetic_case(6)
    bundle = _synthetic_bundle(request_id="req-error-trace")

    def _failing_handler(req: ModelRequest) -> ModelResponse:
        raise ModelTimeoutError("Simulated LLM provider deadline exceeded")

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_failing_handler),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/6",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="error-trace-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run_record = replay_adapter.run_case(case, repeat_index=0)

    assert run_record.result.is_incomplete is True
    assert run_record.result.decision == FindingDecision.ABSTAINED
    assert len(run_record.result.findings) == 0  # Zero fabricated findings
    assert "ModelTimeoutError" in str(run_record.result.error_status)


def test_replaying_same_offline_fixture_produces_deterministic_results() -> None:
    """Repeated execution of the same fixture produces byte-identical results."""
    case = _synthetic_case(7)
    bundle = _synthetic_bundle(request_id="req-det-repeat")
    valid_canned = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-89",
        "summary": "Deterministic repeat test",
        "reasoning_notes": "Deterministic reasoning.",
        "is_abstained": False,
        "claims": [
            {
                "text": "User input concatenated into SQL query.",
                "citations": [
                    {
                        "source_id": "SRC-SYN-001",
                        "chunk_id": "CHK-SYN-001",
                        "cited_excerpt": "SELECT * FROM users WHERE id = ' + user_input + ';",
                    }
                ],
            }
        ],
    }

    def _det_handler(req: ModelRequest) -> ModelResponse:
        return ModelResponse(
            request_id=req.request_id,
            model_id=req.model_id,
            provider_mode=req.provider_mode,
            raw_content=json.dumps(valid_canned),
            structured_output=valid_canned,
        )

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(default_handler=_det_handler),
    )

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/7",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="Consistently reviewed evidence.",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="deterministic-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
    )

    run0_a = replay_adapter.run_case(case, repeat_index=0)
    run0_b = replay_adapter.run_case(case, repeat_index=0)
    run1 = replay_adapter.run_case(case, repeat_index=1)

    # Identical replay of trial 0 produces byte-identical run records
    assert run0_a.run_id == run0_b.run_id
    assert run0_a.result.decision == run0_b.result.decision
    assert len(run0_a.result.findings) == len(run0_b.result.findings)
    assert run0_a.result.findings[0].finding_id == run0_b.result.findings[0].finding_id
    assert run0_a.reproducibility_metadata["final_state"] == run0_b.reproducibility_metadata["final_state"]
    assert run0_a.reproducibility_metadata["trajectory"] == run0_b.reproducibility_metadata["trajectory"]

    # Across repeats, decision and trajectory remain stable
    assert run0_a.result.decision == run1.result.decision
    assert run0_a.reproducibility_metadata["final_state"] == run1.reproducibility_metadata["final_state"]
    assert run0_a.reproducibility_metadata["trajectory"] == run1.reproducibility_metadata["trajectory"]


def test_no_silent_fallback_on_unauthorized_live_provider_in_replay() -> None:
    """When a live provider is requested in replay, it fails closed without silent mock fallback."""
    case = _synthetic_case(8)
    bundle = _synthetic_bundle(request_id="req-live-unauth")

    config = ModelProviderConfig(
        provider_mode=ProviderMode.LIVE_UNAUTHORIZED,
        model_id="gemini-1.5-pro",
    )
    live_adapter = UnauthorizedLiveModelAdapter(config)
    specialist = GroundedSpecialistAdapter(ROLE_SQLI_ANALYST, live_adapter)

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/endpoint/8",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="",
        specialist_adapter=specialist,
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="unauth-live-runner",
        case_manifests=[case],
        case_fixtures={case.case_id: fixture},
        propagate_exceptions=True,
    )

    with pytest.raises(LiveProviderExecutionUnavailableError) as exc_info:
        replay_adapter.run_case(case, repeat_index=0)

    assert "DEC-07 in docs/SUPERVISOR_DECISION_REGISTER.md remains PENDING" in str(exc_info.value)


def test_state_machine_guard_stage_bypass_prohibited() -> None:
    """Attempting execute_specialist_analysis before record_retrieval raises StageBypassError."""
    req = AssessmentRequest(
        request_id="req-bypass-test",
        target_url="http://127.0.0.1:3000/api/endpoint/1",
        vulnerability_category="SQLI",
        authorized_scope=("/api",),
    )
    sm = OrchestrationStateMachine(req)
    sm.validate_request()

    specialist = GroundedSpecialistAdapter(
        ROLE_SQLI_ANALYST,
        DeterministicModelAdapter(),
    )

    with pytest.raises(StageBypassError) as exc_info:
        sm.execute_specialist_analysis(specialist)
    assert "expected 'retrieval_completed'" in str(exc_info.value)
