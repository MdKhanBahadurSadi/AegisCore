"""End-to-end integration tests for uncertainty aggregation engine in multi-agent orchestration.

Phase 8F.2 — Uncertainty Engine Integration & End-to-End Workflow.
Demonstrates:
  1. The actual state machine invokes the uncertainty engine directly (assess_uncertainty).
  2. A consistent, evidence-supported fixture continues through the workflow to COMPLETED.
  3. Specialist disagreement produces the intended abstention behavior.
  4. Missing or insufficient evidence blocks positive verified result and fails closed.
  5. Invalid citations or excerpt mismatches prevent unsupported verification.
  6. Reviewer rejection is respected and transitions to REJECTED.
  7. Contradictory evidence (conflict markers) triggers conservative abstention.
  8. Reason codes remain traceable through to the FinalGatedAssessmentResult.
  9. Repeated identical inputs produce strictly deterministic aggregation and transitions.
  10. Unexpected engine errors fail closed by transitioning to FAILED and re-raising.
  11. Existing execution guards (scope violations, stage bypass, terminal state locks) remain enforced.
  12. Invariant confidence_is_calibrated is strictly False throughout the entire lifecycle.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

import pytest

from aegiscore.claim_validation import (
    ClaimValidationResult,
    EvidenceSufficiencyClassification,
    GatedGenerationResult,
)
from aegiscore.generation import (
    CitationGroundingError,
    GeneratedClaim,
    GenerationResult,
)
from aegiscore.orchestration import (
    AgentExecutionRecord,
    AssessmentRequest,
    ClaimCitationRecord,
    ConflictAssessment,
    EvidenceBundle,
    FinalGatedAssessmentResult,
    FindingSeverity,
    GatingDecision,
    OrchestrationContractError,
    OrchestrationState,
    OrchestrationStateMachine,
    ScopeViolationError,
    SpecialistFinding,
    StageBypassError,
    TerminalStateError,
    UncertaintyAssessment,
)
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata
from aegiscore.specialist_roles import (
    ROLE_BAC_ANALYST,
    ROLE_EVIDENCE_REVIEWER,
    ROLE_SQLI_ANALYST,
    ROLE_XSS_ANALYST,
    build_execution_record,
)
from aegiscore.uncertainty_engine import (
    AggregationRecommendation,
    UncertaintyAggregationEngine,
    UncertaintyAggregationResult,
    UncertaintyReasonCode,
)


# ---------------------------------------------------------------------------
# Test Fixture Helpers
# ---------------------------------------------------------------------------

def _chunk(chunk_id: str, source_id: str, content: str) -> SourceChunk:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    meta = SourceMetadata(source_id=source_id, content_sha256=digest)
    return SourceChunk(
        chunk_id=chunk_id,
        provenance=meta,
        ordinal=0,
        start_offset=0,
        end_offset=len(content),
        content=content,
        content_sha256=digest,
    )


def _bundle(
    request_id: str,
    chunk_id: str = "chk-e2e-1",
    source_id: str = "src-e2e-1",
    content: str = "Raw concatenation in query: SELECT * FROM items WHERE name = 'input'",
) -> EvidenceBundle:
    c = _chunk(chunk_id, source_id, content)
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    return EvidenceBundle(
        bundle_id=f"bnd-{request_id}",
        request_id=request_id,
        retrieval_query="vulnerability query",
        chunks=(c,),
        citations=(ref,),
        manifest_fingerprint="sha256-approved-test-manifest",
        approved_source_count=1,
    )


def _request(request_id: str = "req-e2e-01") -> AssessmentRequest:
    return AssessmentRequest(
        request_id=request_id,
        target_url="http://127.0.0.1:3000/rest/products/search",
        vulnerability_category="SQLI",
        authorized_scope=("/", "/rest/products/search"),
        analysis_mode="passive_rag_only",
    )


def _finding(
    request_id: str,
    chunk_id: str = "chk-e2e-1",
    source_id: str = "src-e2e-1",
    *,
    vulnerability_identified: bool = True,
    role: str = ROLE_SQLI_ANALYST,
    summary: str = "SQL injection candidate finding.",
    claim_text: str = "Raw concatenation of user input in database query.",
    cited_excerpt: str | None = None,
) -> SpecialistFinding:
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    claim = GeneratedClaim(text=claim_text, citations=(ref,))
    claim_citations = ()
    if cited_excerpt is not None:
        cc = ClaimCitationRecord(
            claim_id="clm-e2e-1",
            citation=ref,
            cited_excerpt=cited_excerpt,
        )
        claim_citations = (cc,)

    return SpecialistFinding(
        finding_id=f"fnd-{request_id}-{role}",
        request_id=request_id,
        specialist_role=role,
        vulnerability_identified=vulnerability_identified,
        severity=FindingSeverity.HIGH if vulnerability_identified else FindingSeverity.INFO,
        summary=summary,
        proposed_claims=(claim,),
        claim_citations=claim_citations,
    )


def _gated_sufficient(claim: GeneratedClaim) -> GatedGenerationResult:
    cv = ClaimValidationResult(
        claim=claim,
        classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
        is_valid=True,
        citations_validated=claim.citations,
        reason="Sufficient evidence.",
    )
    gen_result = GenerationResult(
        status="answered",
        claims=(claim,),
        factual_support="not_evaluated",
    )
    return GatedGenerationResult(
        generation_result=gen_result,
        overall_classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
        claim_validations=(cv,),
    )


# ---------------------------------------------------------------------------
# Test 1: State Machine Invokes Uncertainty Engine Directly
# ---------------------------------------------------------------------------

def test_state_machine_invokes_uncertainty_engine_directly() -> None:
    """The actual state machine invokes the uncertainty engine and preserves results."""
    req_id = "req-inv01"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Review completed. No defense observed.")

    assert sm.current_state == OrchestrationState.EVIDENCE_REVIEW_COMPLETED

    # Direct engine invocation on the state machine
    result = sm.assess_uncertainty()

    assert isinstance(result, UncertaintyAggregationResult)
    assert result.request_id == req_id
    assert result.recommendation == AggregationRecommendation.CONTINUE
    assert result.is_sufficient is True
    assert result.confidence_is_calibrated is False

    # State machine updated deterministically
    assert sm.current_state == OrchestrationState.UNCERTAINTY_ASSESSED
    assert sm.uncertainty_aggregation_result is result
    assert sm.uncertainty_assessment is not None
    assert sm.conflict_assessment is not None
    assert sm.uncertainty_assessment.confidence_is_calibrated is False


# ---------------------------------------------------------------------------
# Test 2: Consistent Evidence-Supported Fixture Continues to Completion
# ---------------------------------------------------------------------------

def test_consistent_evidence_fixture_continues_to_completion() -> None:
    """A consistent, evidence-supported fixture continues through the workflow to COMPLETED."""
    req_id = "req-happy-02"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Review confirms lack of parameterization.")

    # Uncertainty assessment advances state machine
    agg_result = sm.assess_uncertainty()
    assert agg_result.recommendation == AggregationRecommendation.CONTINUE
    assert sm.current_state == OrchestrationState.UNCERTAINTY_ASSESSED

    # Claim validation stage
    gated = _gated_sufficient(fnd.proposed_claims[0])
    sm.record_validation(gated)
    assert sm.current_state == OrchestrationState.VALIDATION_COMPLETED

    # Finalize with convenience factory
    final = sm.create_final_result("final-happy-02")
    final_out = sm.finalize_result(final)

    assert sm.current_state == OrchestrationState.COMPLETED
    assert final_out.decision == GatingDecision.PROCEED
    assert final_out.finding is fnd
    assert final_out.finding.is_confirmed is False  # Invariant: never auto-confirmed
    assert final_out.finding.factual_support == "not_evaluated"
    assert UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT.value in final_out.reason_codes


# ---------------------------------------------------------------------------
# Test 3: Specialist Disagreement Produces Abstention
# ---------------------------------------------------------------------------

def test_specialist_disagreement_produces_abstention() -> None:
    """Disagreement between primary and secondary specialists forces conservative abstention."""
    req_id = "req-dis-03"
    req = _request(req_id)
    bundle = _bundle(req_id)
    primary = _finding(req_id, vulnerability_identified=True, role=ROLE_SQLI_ANALYST)
    secondary = _finding(
        req_id,
        vulnerability_identified=False,
        role=ROLE_BAC_ANALYST,
        summary="No vulnerability identified in access control review.",
    )

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review("Specialists have differing hypotheses.")

    # Invoke with secondary findings
    result = sm.assess_uncertainty(secondary_findings=[secondary])

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes

    # State machine halts in terminal ABSTAINED state
    assert sm.current_state == OrchestrationState.ABSTAINED
    assert sm.is_terminal is True

    # Attempting to advance further fails closed
    with pytest.raises(TerminalStateError, match="terminal state 'abstained'"):
        sm.record_validation(_gated_sufficient(primary.proposed_claims[0]))


# ---------------------------------------------------------------------------
# Test 4: Missing Evidence Blocks Positive Result
# ---------------------------------------------------------------------------

def test_missing_evidence_blocks_positive_result() -> None:
    """Empty evidence bundle halts state machine at RETRIEVAL_COMPLETED fail-closed."""
    req_id = "req-empty-04"
    req = _request(req_id)
    empty_bundle = EvidenceBundle(
        bundle_id=f"bnd-{req_id}",
        request_id=req_id,
        retrieval_query="query",
        chunks=(),
        citations=(),
        manifest_fingerprint="sha256-fake",
        approved_source_count=0,
        evidence_status="no_approved_evidence",
    )

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(empty_bundle)

    # Immediately abstains on empty approved corpus
    assert sm.current_state == OrchestrationState.ABSTAINED
    assert sm.is_terminal is True


def test_insufficient_chunks_causes_engine_abstention() -> None:
    """Evidence with fewer chunks than min threshold causes engine to abstain."""
    req_id = "req-insuf-04b"
    req = _request(req_id)
    bundle = _bundle(req_id)  # has 1 chunk
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Review completed.")

    # Configure engine requiring 3 chunks
    strict_engine = UncertaintyAggregationEngine(min_sufficient_chunks=3)
    result = sm.assess_uncertainty(engine=strict_engine)

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert UncertaintyReasonCode.EVIDENCE_INSUFFICIENT in result.contributing_reason_codes
    assert sm.current_state == OrchestrationState.ABSTAINED
    assert sm.is_terminal is True


# ---------------------------------------------------------------------------
# Test 5: Invalid Citations and Excerpt Mismatches Prevent Verification
# ---------------------------------------------------------------------------

def test_invalid_citation_prevents_unsupported_verification() -> None:
    """A claim citation referencing a non-existent chunk forces fail-closed abstention or rejection."""
    req_id = "req-cit-05"
    req = _request(req_id)
    bundle = _bundle(req_id, chunk_id="chk-real")

    # 1. State machine level: record_specialist_analysis fails closed if citation not in bundle
    ref_bad = CitationReference(source_id="src-e2e-1", chunk_id="chk-nonexistent")
    claim_bad = GeneratedClaim(text="Claim.", citations=(ref_bad,))
    cc_bad = ClaimCitationRecord(claim_id="clm-bad", citation=ref_bad)
    fnd_bad = SpecialistFinding(
        finding_id=f"fnd-{req_id}",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="Finding.",
        proposed_claims=(claim_bad,),
        claim_citations=(cc_bad,),
    )
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    with pytest.raises(CitationGroundingError, match="not found in evidence"):
        sm.record_specialist_analysis(fnd_bad)
    assert sm.current_state == OrchestrationState.RETRIEVAL_COMPLETED

    # 2. Uncertainty engine level: engine flags CITATION_INVALID and recommends ABSTAIN
    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=fnd_bad)
    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert UncertaintyReasonCode.CITATION_INVALID in result.contributing_reason_codes


def test_excerpt_mismatch_prevents_unsupported_verification() -> None:
    """An excerpt that does not exist verbatim in the source chunk forces fail-closed abstention."""
    req_id = "req-exc-05b"
    req = _request(req_id)
    bundle = _bundle(req_id, content="Exact content: sanitized input.")

    # Construct finding citing non-verbatim excerpt
    ref = CitationReference(source_id="src-e2e-1", chunk_id="chk-e2e-1")
    claim = GeneratedClaim(text="Claim.", citations=(ref,))
    cc = ClaimCitationRecord(
        claim_id="clm-mismatch",
        citation=ref,
        cited_excerpt="this string definitely does not exist in chunk",
    )
    fnd = SpecialistFinding(
        finding_id=f"fnd-{req_id}",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="Finding.",
        proposed_claims=(claim,),
        claim_citations=(cc,),
    )

    # 1. State machine level guard
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    with pytest.raises(CitationGroundingError, match="verbatim in chunk"):
        sm.record_specialist_analysis(fnd)
    assert sm.current_state == OrchestrationState.RETRIEVAL_COMPLETED

    # 2. Engine level aggregation result
    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=fnd)
    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert UncertaintyReasonCode.EXCERPT_MISMATCH in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# Test 6: Reviewer Rejection is Respected (Transitions to REJECTED)
# ---------------------------------------------------------------------------

def test_reviewer_rejection_transitions_to_rejected_state() -> None:
    """Adversarial reviewer rejecting a candidate finding transitions state machine to REJECTED."""
    req_id = "req-rej-06"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review(
        "REJECTED: Finding is a false positive. Parameterized query is enforced upstream."
    )

    result = sm.assess_uncertainty()

    assert result.recommendation == AggregationRecommendation.REJECT
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes

    # State machine is in terminal REJECTED state
    assert sm.current_state == OrchestrationState.REJECTED
    assert sm.is_terminal is True


# ---------------------------------------------------------------------------
# Test 7: Contradictory Evidence Triggers Conservative Decision
# ---------------------------------------------------------------------------

def test_contradictory_evidence_triggers_abstention() -> None:
    """Explicit CONFLICT_MARKER in evidence review triggers fail-closed abstention."""
    req_id = "req-conf-07"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review(
        "CONFLICT_MARKER: prepared_statement_present vs raw_concatenation_asserted"
    )

    result = sm.assess_uncertainty()

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT in result.contributing_reason_codes
    assert sm.current_state == OrchestrationState.ABSTAINED
    assert sm.is_terminal is True


def test_flag_for_review_recommendation_transitions_correctly() -> None:
    """UncertaintyAggregationResult with FLAG_FOR_REVIEW transitions to FLAGGED_FOR_REVIEW."""
    req_id = "req-flag-07b"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Review notes.")

    # Create result with FLAG_FOR_REVIEW recommendation
    from aegiscore.uncertainty_engine import SignalAuditRecord
    sig = SignalAuditRecord(
        evidence_chunk_count=1,
        approved_source_count=1,
        evidence_sufficiency_score=0.7,
        epistemic_keywords_found=(),
        citation_checks_passed=1,
        citation_checks_failed=0,
        citation_failure_reasons=(),
        specialist_consensus="single_finding",
        conflicting_findings_count=0,
        reviewer_verdict="uncontested",
        conflict_markers_found=(),
        provenance_verified=True,
    )
    flag_result = UncertaintyAggregationResult(
        aggregation_id=f"agg-{req_id}",
        request_id=req_id,
        recommendation=AggregationRecommendation.FLAG_FOR_REVIEW,
        overall_heuristic_score=0.7,
        is_sufficient=True,
        abstention_recommended=False,
        primary_reason_code=UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,
        contributing_reason_codes=(UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,),
        justification="Human review required for high-risk finding.",
        signals=sig,
        confidence_is_calibrated=False,
    )

    sm.record_uncertainty_aggregation(flag_result)

    assert sm.current_state == OrchestrationState.FLAGGED_FOR_REVIEW
    assert sm.is_terminal is True


# ---------------------------------------------------------------------------
# Test 8: Reason Codes Traceable to Final Decision
# ---------------------------------------------------------------------------

def test_reason_codes_traceable_to_final_decision() -> None:
    """Reason codes from uncertainty aggregation propagate to FinalGatedAssessmentResult."""
    req_id = "req-trace-08"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Evidence verified.")
    agg_res = sm.assess_uncertainty()

    gated = _gated_sufficient(fnd.proposed_claims[0])
    sm.record_validation(gated)

    final = sm.create_final_result("final-trace-08")
    assert final.uncertainty_aggregation is agg_res
    assert isinstance(final.reason_codes, tuple)
    assert len(final.reason_codes) >= 1
    assert UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT.value in final.reason_codes


# ---------------------------------------------------------------------------
# Test 9: Deterministic Repeatability
# ---------------------------------------------------------------------------

def test_repeated_identical_inputs_produce_identical_results() -> None:
    """Identical request, bundle, finding, and notes yield identical aggregation IDs and states."""
    req_id = "req-det-09"

    def _execute_run() -> tuple[UncertaintyAggregationResult, tuple]:
        req = _request(req_id)
        bundle = _bundle(req_id)
        fnd = _finding(req_id)
        sm = OrchestrationStateMachine(req)
        sm.validate_request()
        sm.record_retrieval(bundle)
        sm.record_specialist_analysis(fnd)
        sm.record_evidence_review("Deterministic review.")
        res = sm.assess_uncertainty()
        return res, sm.transition_history

    res1, hist1 = _execute_run()
    res2, hist2 = _execute_run()

    assert res1.aggregation_id == res2.aggregation_id
    assert res1.overall_heuristic_score == res2.overall_heuristic_score
    assert res1.recommendation == res2.recommendation
    assert res1.primary_reason_code == res2.primary_reason_code
    assert hist1 == hist2


# ---------------------------------------------------------------------------
# Test 10: Unexpected Engine Errors Fail Closed
# ---------------------------------------------------------------------------

def test_unexpected_engine_errors_fail_closed() -> None:
    """An unhandled error in the engine transitions state machine to FAILED and re-raises."""
    req_id = "req-err-10"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Review notes.")

    # Create a mock engine that raises an unexpected runtime exception
    class FaultyEngine:
        def aggregate(self, *args, **kwargs):
            raise RuntimeError("Unexpected internal engine fault")

    with pytest.raises(RuntimeError, match="Unexpected internal engine fault"):
        sm.assess_uncertainty(engine=FaultyEngine())

    # State machine must fail closed into FAILED state
    assert sm.current_state == OrchestrationState.FAILED
    assert sm.is_terminal is True


# ---------------------------------------------------------------------------
# Test 11: Scope Violations and Execution Guards Enforced
# ---------------------------------------------------------------------------

def test_scope_violations_fail_closed() -> None:
    """Requests targeting unauthorized external IP ranges are rejected at creation."""
    with pytest.raises(ScopeViolationError):
        AssessmentRequest(
            request_id="req-scope-11",
            target_url="https://8.8.8.8/public",  # Public internet IP
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )


def test_stage_bypass_prohibited() -> None:
    """Attempting assess_uncertainty before evidence review raises StageBypassError."""
    req_id = "req-bypass-11"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)

    # State is SPECIALIST_ANALYSIS_COMPLETED, not EVIDENCE_REVIEW_COMPLETED
    with pytest.raises(StageBypassError, match="expected 'evidence_review_completed'"):
        sm.assess_uncertainty()


# ---------------------------------------------------------------------------
# Test 12: Invariant: confidence_is_calibrated is Strictly False
# ---------------------------------------------------------------------------

def test_confidence_is_calibrated_invariant_maintained() -> None:
    """confidence_is_calibrated remains strictly False across all result artifacts."""
    req_id = "req-cal-12"
    req = _request(req_id)
    bundle = _bundle(req_id)
    fnd = _finding(req_id)

    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(fnd)
    sm.record_evidence_review("Clean notes.")
    agg_res = sm.assess_uncertainty()

    assert agg_res.confidence_is_calibrated is False
    assert sm.uncertainty_assessment.confidence_is_calibrated is False

    gated = _gated_sufficient(fnd.proposed_claims[0])
    sm.record_validation(gated)
    final = sm.create_final_result("final-cal-12")

    assert final.uncertainty_summary.confidence_is_calibrated is False
    assert final.uncertainty_aggregation.confidence_is_calibrated is False
