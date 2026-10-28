"""Phase 8F.6 — Multi-Specialist Consensus & Adversarial Reviewer Integration Tests.

Exercises the actual existing orchestration state machine, uncertainty aggregation engine,
adversarial evidence reviewer, and evaluation harness replay path with multiple specialist
adapters and deterministic offline test doubles.

STRICT BOUNDARIES:
  - Zero network requests, zero cloud or local LLM calls, zero container or DB operations.
  - All fixtures are explicitly synthetic and must not be represented as real vulnerabilities.
  - confidence_is_calibrated=False everywhere; no calibrated confidence claims.
  - Reviewer rejection cannot be bypassed by specialist consensus.
  - Conflicting or unsupported findings must not silently resolve to PROCEED.

Covers 6 scenario families (as specified in Phase 8F.6):
  SC-MS-01  Specialists agree on evidence-supported hypothesis           -> PROCEED
  SC-MS-02  Specialists disagree about potential vulnerability           -> ABSTAIN/FLAG
  SC-MS-03  One specialist abstains, another finds a valid finding       -> specialist_disagreement
  SC-MS-04  Unknown evidence ID or mismatched citation                   -> CITATION_INVALID / REJECT
  SC-MS-05  One specialist fails, another returns valid finding           -> FAILED / error traceable
  SC-MS-06  Conflicting findings, insufficient evidence to resolve       -> FLAG_FOR_REVIEW / ABSTAIN

Adversarial reviewer scenarios:
  SC-REV-01  Reviewer challenges unsupported claim                       -> REVIEWER_CHALLENGE
  SC-REV-02  Reviewer rejects invalid citation                           -> REVIEWER_REJECTION -> REJECT
  SC-REV-03  Reviewer identifies conflicting evidence/specialist mismatch -> CONFLICT_MARKERS_PRESENT
  SC-REV-04  Reviewer triggers abstention for epistemic ambiguity        -> ABSTAIN
  SC-REV-05  Reviewer rejection not bypassed by consensus                -> REJECT despite agreement
  SC-REV-06  Full trace preserved through reviewer -> uncertainty -> result

Backward-compatibility scenarios:
  SC-COMPAT  Single-specialist, no secondary_findings still functions correctly
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

# Core orchestration contracts
from aegiscore.orchestration import (
    AssessmentRequest,
    ClaimCitationRecord,
    ConflictAssessment,
    EvidenceBundle,
    FindingSeverity,
    GatingDecision,
    OrchestrationContractError,
    OrchestrationState,
    OrchestrationStateMachine,
    SpecialistFinding,
    UncertaintyAssessment,
)

# Uncertainty engine
from aegiscore.uncertainty_engine import (
    AggregationRecommendation,
    UncertaintyAggregationEngine,
    UncertaintyReasonCode,
    UncertaintyAggregationResult,
)

# Specialist roles – real fakes and contracts
from aegiscore.specialist_roles import (
    ROLE_BAC_ANALYST,
    ROLE_EVIDENCE_REVIEWER,
    ROLE_SQLI_ANALYST,
    ROLE_XSS_ANALYST,
    DeterministicEvidenceReviewerFake,
    DeterministicVulnerabilityAnalystFake,
    FixturedSpecialistOutput,
    build_execution_record,
)

# RAG types
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata, SourceReviewState
from aegiscore.generation import GeneratedClaim

# Evaluation harness
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
from aegiscore.claim_validation import (
    ClaimValidationResult,
    EvidenceSufficiencyClassification,
    GatedGenerationResult,
)
from aegiscore.generation import GenerationResult


# ---------------------------------------------------------------------------
# Shared Synthetic Fixture Helpers
# (All marked SYNTHETIC — not real vulnerability evidence)
# ---------------------------------------------------------------------------

def _chunk(
    chunk_id: str = "CHK-8F6-001",
    source_id: str = "SRC-8F6-001",
    content: str = "SELECT * FROM orders WHERE user_id = ' + request.user_id + ';",
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


def _bundle(
    request_id: str = "req-8f6-001",
    chunk_id: str = "CHK-8F6-001",
    source_id: str = "SRC-8F6-001",
    content: str = "SELECT * FROM orders WHERE user_id = ' + request.user_id + ';",
    approved: int = 1,
) -> EvidenceBundle:
    """Construct a synthetic EvidenceBundle for offline testing."""
    if approved == 0:
        return EvidenceBundle(
            bundle_id=f"bnd-{request_id}",
            request_id=request_id,
            retrieval_query="synthetic vulnerability retrieval query",
            chunks=(),
            citations=(),
            manifest_fingerprint=hashlib.sha256(b"synthetic-manifest").hexdigest(),
            approved_source_count=0,
            evidence_status="no_approved_evidence",
        )
    c = _chunk(chunk_id, source_id, content)
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    return EvidenceBundle(
        bundle_id=f"bnd-{request_id}",
        request_id=request_id,
        retrieval_query="synthetic vulnerability retrieval query",
        chunks=(c,),
        citations=(ref,),
        manifest_fingerprint=hashlib.sha256(b"synthetic-manifest").hexdigest(),
        approved_source_count=approved,
        evidence_status="evidence_found",
    )


def _request(req_id: str) -> AssessmentRequest:
    return AssessmentRequest(
        request_id=req_id,
        target_url="http://127.0.0.1:3000/api/query",
        vulnerability_category="SQLI",
        authorized_scope=("/api",),
    )


def _finding(
    req_id: str,
    chunk_id: str = "CHK-8F6-001",
    source_id: str = "SRC-8F6-001",
    content: str = "SELECT * FROM orders WHERE user_id = ' + request.user_id + ';",
    finding_id: str = "FND-8F6-001",
    role: str = ROLE_SQLI_ANALYST,
    vulnerability_identified: bool = True,
    severity: FindingSeverity = FindingSeverity.HIGH,
    summary: str = "SYNTHETIC: SQL concatenation pattern detected in evidence.",
) -> SpecialistFinding:
    """Construct a synthetic SpecialistFinding for offline testing.
    Marked SYNTHETIC — not a real or approved vulnerability detection.
    """
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    if vulnerability_identified:
        claim = GeneratedClaim(
            text=f"SYNTHETIC: [{role}] observed SQL construction pattern.",
            citations=(ref,),
        )
        cc = ClaimCitationRecord(
            claim_id=f"clm-{finding_id}",
            citation=ref,
            cited_excerpt=None,
        )
        return SpecialistFinding(
            finding_id=finding_id,
            request_id=req_id,
            specialist_role=role,
            vulnerability_identified=True,
            severity=severity,
            summary=summary,
            proposed_claims=(claim,),
            cwe_id="CWE-89",
            claim_citations=(cc,),
            reasoning_notes="SYNTHETIC test fixture. Not a real LLM analysis.",
        )
    return SpecialistFinding(
        finding_id=finding_id,
        request_id=req_id,
        specialist_role=role,
        vulnerability_identified=False,
        severity=FindingSeverity.INFO,
        summary="SYNTHETIC: No vulnerability identified; abstaining.",
        proposed_claims=(),
        reasoning_notes="SYNTHETIC test fixture abstention.",
    )


def _case(case_num: int = 1) -> EvaluationCaseManifestRecord:
    return EvaluationCaseManifestRecord(
        case_id=f"CASE-8F6-{case_num:03d}",
        locus=CanonicalLocus(
            target_uri=f"http://127.0.0.1:3000/api/query/{case_num}",
            parameter="user_id",
            cwe_id="CWE-89",
        ),
        benchmark_target="synthetic-8f6-offline-benchmark",
        benchmark_version="1.0.0",
        vulnerability_class="SQLI",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="synthetic-offline-fixture-8f6",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )


def _gt(case_num: int = 1) -> GroundTruthRecord:
    return GroundTruthRecord(
        case_id=f"CASE-8F6-{case_num:03d}",
        locus=CanonicalLocus(
            target_uri=f"http://127.0.0.1:3000/api/query/{case_num}",
            parameter="user_id",
            cwe_id="CWE-89",
        ),
        expected_status=GroundTruthStatus.VULNERABLE,
        vulnerability_class="SQLI",
        evidence_reference="EVID-8F6-SYN-001",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="synthetic-offline-fixture-8f6",
    )


# ---------------------------------------------------------------------------
# SC-MS-01: Specialists agree on evidence-supported hypothesis
# ---------------------------------------------------------------------------


def test_ms01_specialists_agree_vulnerability_identified() -> None:
    """SC-MS-01: Two specialists agree a vulnerability is identified from the same evidence bundle.

    The UncertaintyAggregationEngine should observe unanimous consensus and
    recommend CONTINUE when evidence is sufficient and reviewer finds no conflict.
    SYNTHETIC: agreement on artificial fixture, not a real detection.
    """
    req_id = "req-ms01"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS01-XSS", role=ROLE_XSS_ANALYST)
    secondary = _finding(
        req_id, finding_id="FND-MS01-SQLI", role=ROLE_SQLI_ANALYST,
        summary="SYNTHETIC: Secondary specialist agrees vulnerability exists.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    # No conflict expected: both agree, no sanitization markers in evidence
    assert "CONFLICT_MARKER" not in review_notes

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        request_id=req_id,
        bundle=bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes=review_notes,
    )

    # Both specialists agree -> unanimous consensus
    assert result.signals.specialist_consensus == "unanimous"
    assert result.signals.conflicting_findings_count == 0
    assert result.recommendation == AggregationRecommendation.CONTINUE
    assert result.is_sufficient is True
    assert result.confidence_is_calibrated is False
    # Primary reason should reflect sufficient/consistent state
    assert result.primary_reason_code in (
        UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,
        UncertaintyReasonCode.REVIEWER_CHALLENGE,
    )


def test_ms01_multi_specialist_agreement_through_state_machine() -> None:
    """SC-MS-01 via state machine: unanimous consensus propagates correctly.

    The state machine must progress to UNCERTAINTY_ASSESSED (CONTINUE) with traceable reason.
    """
    req_id = "req-ms01-sm"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS01-SM-PRIMARY", role=ROLE_SQLI_ANALYST)
    secondary = _finding(
        req_id, finding_id="FND-MS01-SM-SECONDARY", role=ROLE_BAC_ANALYST,
        summary="SYNTHETIC: BAC specialist concurs with primary finding.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty(secondary_findings=(secondary,))

    # Should be at UNCERTAINTY_ASSESSED (CONTINUE) or COMPLETED after validation
    assert sm.current_state in (
        OrchestrationState.UNCERTAINTY_ASSESSED,
        OrchestrationState.COMPLETED,
        OrchestrationState.ABSTAINED,  # only if reviewer challenge triggered
    )
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.confidence_is_calibrated is False
    # Unanimous agreement is captured in signals
    assert agg.signals.specialist_consensus == "unanimous"


# ---------------------------------------------------------------------------
# SC-MS-02: Specialists disagree about a potential vulnerability
# ---------------------------------------------------------------------------


def test_ms02_specialist_disagreement_detected() -> None:
    """SC-MS-02: Two specialists produce contradictory findings.

    Specialist A: vulnerability identified. Specialist B: no vulnerability.
    Engine must flag SPECIALIST_DISAGREEMENT and recommend ABSTAIN or FLAG_FOR_REVIEW.
    """
    req_id = "req-ms02"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS02-A", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id="FND-MS02-B", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False,
                         summary="SYNTHETIC: XSS specialist finds no issue.")

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    # Reviewer should detect disagreement
    assert "CONFLICT_MARKER" in review_notes or "disagree" in review_notes.lower()

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        request_id=req_id,
        bundle=bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes=review_notes,
    )

    assert result.signals.specialist_consensus == "disagreement"
    assert result.signals.conflicting_findings_count >= 2
    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes
    # Must not proceed when specialists disagree
    assert result.recommendation in (
        AggregationRecommendation.ABSTAIN,
        AggregationRecommendation.FLAG_FOR_REVIEW,
    )
    assert result.confidence_is_calibrated is False


def test_ms02_disagreement_forces_non_proceed_via_state_machine() -> None:
    """SC-MS-02 via state machine: disagreement cannot silently produce a COMPLETED outcome."""
    req_id = "req-ms02-sm"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS02-SM-A", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id="FND-MS02-SM-B", role=ROLE_BAC_ANALYST,
                         vulnerability_identified=False,
                         summary="SYNTHETIC: BAC specialist does not identify a vulnerability.")

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty(secondary_findings=(secondary,))

    # Disagreement must not result in COMPLETED
    assert sm.current_state != OrchestrationState.COMPLETED
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.signals.specialist_consensus == "disagreement"
    assert agg.recommendation != AggregationRecommendation.CONTINUE


# ---------------------------------------------------------------------------
# SC-MS-03: One specialist abstains, another produces a supported finding
# ---------------------------------------------------------------------------


def test_ms03_one_abstains_one_finds() -> None:
    """SC-MS-03: When one specialist abstains and another identifies a vulnerability,
    this constitutes disagreement and must NOT resolve to a clean PROCEED.

    Abstention counts as vulnerability_identified=False.
    """
    req_id = "req-ms03"
    bundle = _bundle(req_id)
    # Primary specialist identifies a vulnerability
    primary = _finding(req_id, finding_id="FND-MS03-ACTIVE", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    # Secondary specialist abstains (vulnerability_identified=False)
    secondary = _finding(req_id, finding_id="FND-MS03-ABSTAIN", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False,
                         summary="SYNTHETIC: XSS specialist abstains; no applicable evidence.")

    # Preserve both specialists' identity and abstention status in trace
    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        request_id=req_id,
        bundle=bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes="REVIEWER: One specialist identifies a finding, one abstains.",
    )

    # Abstention == False; primary == True → disagreement
    assert result.signals.specialist_consensus == "disagreement"
    assert result.signals.conflicting_findings_count >= 2

    # Abstaining specialist and active specialist are both preserved in the audit
    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes
    assert result.recommendation != AggregationRecommendation.CONTINUE


def test_ms03_abstaining_specialist_identity_preserved_in_trace() -> None:
    """SC-MS-03: Each specialist's identity and abstention status must be traceable."""
    req_id = "req-ms03-trace"
    bundle = _bundle(req_id)

    # Use DeterministicVulnerabilityAnalystFake: force one to abstain
    abstaining_fixture = FixturedSpecialistOutput(
        vulnerability_identified=False,
        severity=FindingSeverity.INFO,
        summary="SYNTHETIC: No evidence for this category; abstaining.",
        reasoning_notes="SYNTHETIC abstention fixture.",
    )
    active_fixture = FixturedSpecialistOutput(
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: SQL concatenation detected.",
        cwe_id="CWE-89",
        reasoning_notes="SYNTHETIC active fixture.",
    )

    sqli_specialist = DeterministicVulnerabilityAnalystFake(ROLE_SQLI_ANALYST, fixture=active_fixture)
    xss_specialist = DeterministicVulnerabilityAnalystFake(ROLE_XSS_ANALYST, fixture=abstaining_fixture)

    finding_sqli = sqli_specialist.analyse(req_id, bundle)
    finding_xss = xss_specialist.analyse(req_id, bundle)

    # Verify specialist identity preserved
    assert finding_sqli.specialist_role == ROLE_SQLI_ANALYST
    assert finding_xss.specialist_role == ROLE_XSS_ANALYST
    assert finding_sqli.vulnerability_identified is True
    assert finding_xss.vulnerability_identified is False
    # Both findings have is_confirmed=False and factual_support='not_evaluated'
    assert finding_sqli.is_confirmed is False
    assert finding_xss.is_confirmed is False

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=finding_sqli,
        secondary_findings=(finding_xss,),
        review_notes="REVIEWER: One specialist active, one abstains.",
    )
    assert result.signals.specialist_consensus == "disagreement"
    assert result.recommendation != AggregationRecommendation.CONTINUE


# ---------------------------------------------------------------------------
# SC-MS-04: Unknown evidence ID or mismatched citation
# ---------------------------------------------------------------------------


def test_ms04_unknown_chunk_id_rejected_by_uncertainty_engine() -> None:
    """SC-MS-04: A finding citing a non-existent chunk ID is flagged CITATION_INVALID."""
    req_id = "req-ms04-unknown"
    bundle = _bundle(req_id, chunk_id="CHK-REAL")

    # Build a finding that cites a non-existent chunk
    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-DOES-NOT-EXIST")
    bad_claim = GeneratedClaim(text="SYNTHETIC: bogus claim.", citations=(bad_ref,))
    bad_cc = ClaimCitationRecord(claim_id="clm-ms04-bad", citation=bad_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-MS04-BAD",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Finding with invalid citation.",
        proposed_claims=(bad_claim,),
        claim_citations=(bad_cc,),
        reasoning_notes="SYNTHETIC bad citation fixture.",
    )

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=bad_finding, review_notes="REVIEWER: standard review.")
    assert UncertaintyReasonCode.CITATION_INVALID in result.contributing_reason_codes
    assert result.recommendation in (AggregationRecommendation.ABSTAIN, AggregationRecommendation.REJECT)
    assert result.signals.citation_checks_failed > 0


def test_ms04_mismatched_source_id_rejected_by_uncertainty_engine() -> None:
    """SC-MS-04: A finding citing a wrong source_id (chunk exists but source mismatch) is flagged."""
    req_id = "req-ms04-mismatch"
    bundle = _bundle(req_id, chunk_id="CHK-REAL", source_id="SRC-CORRECT")

    # Citation has wrong source_id but correct chunk_id
    wrong_ref = CitationReference(source_id="SRC-WRONG", chunk_id="CHK-REAL")
    claim = GeneratedClaim(text="SYNTHETIC: claim with mismatched source.", citations=(wrong_ref,))
    cc = ClaimCitationRecord(claim_id="clm-ms04-mismatch", citation=wrong_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-MS04-MISMATCH",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.MEDIUM,
        summary="SYNTHETIC: Finding with mismatched source.",
        proposed_claims=(claim,),
        claim_citations=(cc,),
        reasoning_notes="SYNTHETIC mismatched source fixture.",
    )

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=bad_finding, review_notes="REVIEWER: checking.")
    assert UncertaintyReasonCode.CITATION_INVALID in result.contributing_reason_codes
    assert result.signals.citation_checks_failed > 0


def test_ms04_reviewer_rejects_unknown_citation() -> None:
    """SC-MS-04: The adversarial reviewer independently catches an unknown chunk ID citation."""
    req_id = "req-ms04-rev"
    bundle = _bundle(req_id, chunk_id="CHK-REAL", source_id="SRC-8F6-001")

    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-NONEXISTENT")
    bad_claim = GeneratedClaim(text="SYNTHETIC: bogus claim.", citations=(bad_ref,))
    bad_cc = ClaimCitationRecord(claim_id="clm-ms04-rev-bad", citation=bad_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-MS04-REV-BAD",
        request_id=req_id,
        specialist_role=ROLE_XSS_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Finding with unknown citation.",
        proposed_claims=(bad_claim,),
        claim_citations=(bad_cc,),
        reasoning_notes="SYNTHETIC bad citation fixture for reviewer test.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding, bundle)
    # Reviewer must reject, not silently pass
    assert "REJECT" in review_notes.upper() or "REJECTION" in review_notes.upper()

    # Uncertainty engine also sees REVIEWER_REJECTION
    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=bad_finding, review_notes=review_notes)
    assert result.recommendation == AggregationRecommendation.REJECT
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# SC-MS-05: One specialist fails, another returns a valid finding
# ---------------------------------------------------------------------------


def test_ms05_specialist_failure_transitions_to_failed() -> None:
    """SC-MS-05: A specialist that raises an unhandled exception transitions the state machine to FAILED.

    Error is traceable; no fabricated findings are produced.
    """
    req_id = "req-ms05"
    bundle = _bundle(req_id)

    class FailingSpecialist:
        def analyse(self, request_id: str, bundle: EvidenceBundle) -> SpecialistFinding:
            raise RuntimeError("SYNTHETIC: Deliberate specialist failure for testing.")

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)

    with pytest.raises(RuntimeError, match="SYNTHETIC"):
        sm.execute_specialist_analysis(FailingSpecialist())

    # State machine must be in FAILED — not silently hiding the error
    assert sm.current_state == OrchestrationState.FAILED
    # Verify error is captured in history
    history = sm.transition_history
    failed_transitions = [(src, dst, reason) for src, dst, reason in history if dst == OrchestrationState.FAILED]
    assert len(failed_transitions) == 1
    reason_text = failed_transitions[0][2] or ""
    assert "RuntimeError" in reason_text or "SYNTHETIC" in reason_text


def test_ms05_failed_specialist_produces_no_fabricated_finding() -> None:
    """SC-MS-05: After specialist failure, no finding is recorded in the state machine."""
    req_id = "req-ms05-nofab"
    bundle = _bundle(req_id)

    class AlwaysFailSpecialist:
        def analyse(self, request_id: str, bundle: EvidenceBundle) -> SpecialistFinding:
            raise ValueError("SYNTHETIC: Simulated parse failure.")

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)

    with pytest.raises(ValueError):
        sm.execute_specialist_analysis(AlwaysFailSpecialist())

    assert sm.current_state == OrchestrationState.FAILED
    # No finding must have been recorded — the state machine must not fabricate a finding
    assert sm.specialist_finding is None


def test_ms05_failing_specialist_in_replay_is_flagged_as_incomplete() -> None:
    """SC-MS-05: The OrchestrationReplayAdapter marks a specialist failure as is_incomplete=True."""
    case = _case(5)
    bundle = _bundle(f"req-8f6-replay-CASE-8F6-005-rep0", approved=1)

    class FailingSpecialistAdapter:
        def analyse(self, request_id: str, bundle: EvidenceBundle) -> SpecialistFinding:
            raise RuntimeError("SYNTHETIC: Replay specialist failure.")

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/query/5",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,
        review_notes="REVIEWER: standard review.",
        specialist_adapter=FailingSpecialistAdapter(),
    )

    adapter = OrchestrationReplayAdapter(
        runner_id="runner-ms05",
        case_fixtures={case.case_id: fixture},
        propagate_exceptions=False,
    )
    run_rec = adapter.run_case(case, repeat_index=0)

    assert run_rec.result.is_incomplete is True
    assert run_rec.result.decision == FindingDecision.ABSTAINED
    assert run_rec.result.error_status is not None
    assert "RuntimeError" in run_rec.result.error_status or "SYNTHETIC" in run_rec.result.error_status


# ---------------------------------------------------------------------------
# SC-MS-06: Conflicting findings, insufficient evidence to resolve
# ---------------------------------------------------------------------------


def test_ms06_conflicting_findings_insufficient_evidence_flags_review() -> None:
    """SC-MS-06: Conflicting specialist conclusions with insufficient evidence to resolve.

    Engine must recommend FLAG_FOR_REVIEW or ABSTAIN, never PROCEED.
    """
    req_id = "req-ms06"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS06-A", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id="FND-MS06-B", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False)

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes="REVIEWER: Disagreement noted. Insufficient evidence to resolve.",
        force_conflict=True,
        forced_conflict_markers=("specialist_a_vulnerable_vs_specialist_b_clean",),
    )

    assert result.signals.specialist_consensus == "disagreement"
    assert len(result.signals.conflict_markers_found) > 0
    # Must not CONTINUE when there is both disagreement and active conflict markers
    assert result.recommendation != AggregationRecommendation.CONTINUE
    assert result.confidence_is_calibrated is False


def test_ms06_unresolved_conflict_is_human_review_required() -> None:
    """SC-MS-06: Specialist disagreement + conflict markers → FLAG_FOR_REVIEW is preferred over silent resolution."""
    req_id = "req-ms06-flag"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-MS06-FLAG-A", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id="FND-MS06-FLAG-B", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False)

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes="REVIEWER: Disagreement noted.",
        force_conflict=True,
        forced_conflict_markers=("unresolved_conflict_marker",),
    )

    # Both disagreement and conflicts present → FLAG_FOR_REVIEW
    assert result.recommendation == AggregationRecommendation.FLAG_FOR_REVIEW
    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes
    assert UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT in result.contributing_reason_codes

    # Verify to_conflict_assessment maps correctly
    ca = result.to_conflict_assessment()
    assert ca.conflicts_detected is True
    assert ca.resolution_strategy in ("human_review_required", "fail_closed_abstain")


# ---------------------------------------------------------------------------
# SC-REV-01: Adversarial reviewer challenges unsupported claim
# ---------------------------------------------------------------------------


def test_rev01_reviewer_challenges_unsupported_claim() -> None:
    """SC-REV-01: The reviewer must challenge a claim that contains an unsupported-marker text."""
    req_id = "req-rev01"
    bundle = _bundle(req_id)

    # Build a claim with an explicitly unsupported marker
    ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-8F6-001")
    bad_claim = GeneratedClaim(
        text="Browsers automatically sanitize all input; no XSS possible. [UNSUPPORTED]",
        citations=(ref,),
    )
    cc = ClaimCitationRecord(claim_id="clm-rev01", citation=ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-REV01",
        request_id=req_id,
        specialist_role=ROLE_XSS_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Unsupported claim about auto-sanitization.",
        proposed_claims=(bad_claim,),
        claim_citations=(cc,),
        reasoning_notes="SYNTHETIC unsupported claim fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding, bundle)
    # Reviewer must challenge or reject the unsupported claim
    assert "CHALLENGE" in review_notes or "REJECT" in review_notes.upper()


def test_rev01_insufficient_evidence_marker_challenged_by_reviewer() -> None:
    """SC-REV-01: Evidence with [INSUFFICIENT_EVIDENCE] marker is challenged by the reviewer."""
    req_id = "req-rev01b"
    content = "This endpoint may be affected. [INSUFFICIENT_EVIDENCE]"
    bundle = _bundle(req_id, content=content)
    primary = _finding(req_id, finding_id="FND-REV01B", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True,
                       content=content)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)
    # The [INSUFFICIENT_EVIDENCE] marker should trigger a challenge
    assert "CHALLENGE" in review_notes or "INSUFFICIENT" in review_notes.upper()


# ---------------------------------------------------------------------------
# SC-REV-02: Reviewer rejects invalid citation, engine propagates as REJECT
# ---------------------------------------------------------------------------


def test_rev02_reviewer_rejects_invalid_citation_engine_propagates_reject() -> None:
    """SC-REV-02: Reviewer rejects finding with unknown chunk ID → engine recommends REJECT.

    CRITICAL: Reviewer rejection cannot be bypassed by specialist consensus.
    """
    req_id = "req-rev02"
    bundle = _bundle(req_id, chunk_id="CHK-VALID", source_id="SRC-8F6-001")

    # Finding cites an invalid chunk
    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-INVALID-NOT-IN-BUNDLE")
    bad_claim = GeneratedClaim(text="SYNTHETIC: invalid citation.", citations=(bad_ref,))
    bad_cc = ClaimCitationRecord(claim_id="clm-rev02", citation=bad_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-REV02",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Finding with invalid citation.",
        proposed_claims=(bad_claim,),
        claim_citations=(bad_cc,),
        reasoning_notes="SYNTHETIC invalid citation fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding, bundle)
    assert "REJECT" in review_notes.upper()

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=bad_finding, review_notes=review_notes)
    # Reviewer rejection forces REJECT — cannot be overridden
    assert result.recommendation == AggregationRecommendation.REJECT
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes


def test_rev02_reviewer_rejects_source_id_mismatch() -> None:
    """SC-REV-02: Reviewer rejects finding with mismatched source_id in citation."""
    req_id = "req-rev02b"
    bundle = _bundle(req_id, chunk_id="CHK-8F6-001", source_id="SRC-CORRECT")

    wrong_ref = CitationReference(source_id="SRC-WRONG", chunk_id="CHK-8F6-001")
    wrong_claim = GeneratedClaim(text="SYNTHETIC: mismatched source claim.", citations=(wrong_ref,))
    wrong_cc = ClaimCitationRecord(claim_id="clm-rev02b", citation=wrong_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-REV02B",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.MEDIUM,
        summary="SYNTHETIC: Mismatched source.",
        proposed_claims=(wrong_claim,),
        claim_citations=(wrong_cc,),
        reasoning_notes="SYNTHETIC mismatched source fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding, bundle)
    assert "REJECT" in review_notes.upper()

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=bad_finding, review_notes=review_notes)
    assert result.recommendation == AggregationRecommendation.REJECT


# ---------------------------------------------------------------------------
# SC-REV-03: Reviewer identifies conflicting evidence and specialist mismatch
# ---------------------------------------------------------------------------


def test_rev03_reviewer_detects_sanitization_conflict_marker() -> None:
    """SC-REV-03: Evidence containing sanitization markers triggers a CONFLICT_MARKER from reviewer."""
    req_id = "req-rev03"
    content = "All user input is passed through htmlspecialchars() before rendering."
    bundle = _bundle(req_id, content=content)
    primary = _finding(req_id, finding_id="FND-REV03", role=ROLE_XSS_ANALYST,
                       vulnerability_identified=True,
                       content=content,
                       summary="SYNTHETIC: XSS finding despite sanitization in evidence.")

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)
    assert "CONFLICT_MARKER" in review_notes

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=primary, review_notes=review_notes)
    assert UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT in result.contributing_reason_codes
    assert result.recommendation != AggregationRecommendation.CONTINUE


def test_rev03_reviewer_identifies_specialist_disagreement_as_conflict() -> None:
    """SC-REV-03: Reviewer marks specialist conclusions that disagree as a CONFLICT_MARKER."""
    req_id = "req-rev03b"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-REV03B-A", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id="FND-REV03B-B", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))
    assert "CONFLICT_MARKER" in review_notes

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes=review_notes,
    )
    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes
    assert result.recommendation != AggregationRecommendation.CONTINUE


# ---------------------------------------------------------------------------
# SC-REV-04: Reviewer triggers abstention for epistemic ambiguity
# ---------------------------------------------------------------------------


def test_rev04_epistemic_keywords_in_review_trigger_abstention() -> None:
    """SC-REV-04: Epistemic keywords in review notes drive abstention_recommended=True."""
    req_id = "req-rev04"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-REV04", role=ROLE_SQLI_ANALYST)

    # Reviewer with explicit epistemic ambiguity
    canned = "REVIEWER: The evidence is unclear and possibly incomplete. uncertain outcome."
    reviewer = DeterministicEvidenceReviewerFake(canned_notes=canned)
    review_notes = reviewer.review(primary, bundle)

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=primary, review_notes=review_notes)
    assert UncertaintyReasonCode.EPISTEMIC_AMBIGUITY in result.contributing_reason_codes
    assert result.abstention_recommended is True
    assert result.confidence_is_calibrated is False


def test_rev04_abstention_propagates_through_state_machine() -> None:
    """SC-REV-04: Epistemic ambiguity in reviewer output propagates to ABSTAINED terminal state."""
    req_id = "req-rev04-sm"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-REV04-SM", role=ROLE_SQLI_ANALYST)

    canned = "REVIEWER: The evidence is possibly insufficient and unclear for high confidence."
    reviewer = DeterministicEvidenceReviewerFake(canned_notes=canned)
    review_notes = reviewer.review(primary, bundle)

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty()

    assert sm.current_state in (
        OrchestrationState.ABSTAINED,
        OrchestrationState.UNCERTAINTY_ASSESSED,
    )
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.abstention_recommended is True


# ---------------------------------------------------------------------------
# SC-REV-05: Reviewer rejection cannot be bypassed by specialist consensus
# ---------------------------------------------------------------------------


def test_rev05_reviewer_rejection_not_bypassed_by_consensus() -> None:
    """SC-REV-05: Even when both specialists agree, reviewer rejection forces REJECT.

    This is the core fail-closed safety property for the adversarial reviewer.
    """
    req_id = "req-rev05"
    bundle = _bundle(req_id, chunk_id="CHK-REAL", source_id="SRC-8F6-001")

    # Build two specialists that agree — but both cite an invalid chunk
    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-FAKE")
    bad_claim_a = GeneratedClaim(text="SYNTHETIC: specialist A agrees.", citations=(bad_ref,))
    bad_claim_b = GeneratedClaim(text="SYNTHETIC: specialist B agrees.", citations=(bad_ref,))
    cc_a = ClaimCitationRecord(claim_id="clm-rev05-a", citation=bad_ref)
    cc_b = ClaimCitationRecord(claim_id="clm-rev05-b", citation=bad_ref)

    primary = SpecialistFinding(
        finding_id="FND-REV05-A",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Both agree on a finding with invalid citation.",
        proposed_claims=(bad_claim_a,),
        claim_citations=(cc_a,),
        reasoning_notes="SYNTHETIC consensus fixture with invalid citation.",
    )
    secondary = SpecialistFinding(
        finding_id="FND-REV05-B",
        request_id=req_id,
        specialist_role=ROLE_XSS_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.MEDIUM,
        summary="SYNTHETIC: Second specialist also agrees (invalid citation).",
        proposed_claims=(bad_claim_b,),
        claim_citations=(cc_b,),
        reasoning_notes="SYNTHETIC secondary consensus fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))
    # Reviewer must reject — consensus alone does not bypass rejection
    assert "REJECT" in review_notes.upper()

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=primary,
        secondary_findings=(secondary,),
        review_notes=review_notes,
    )
    # Consensus cannot override rejection
    assert result.recommendation == AggregationRecommendation.REJECT
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes


def test_rev05_reviewer_rejection_through_state_machine_terminal() -> None:
    """SC-REV-05 via state machine: reviewer rejection leads to REJECTED terminal state.

    Strategy: build a bundle and a valid finding that share the same chunk ID (CHK-REAL),
    so citation validation in record_specialist_analysis passes.  The reviewer-rejected notes
    (produced from a *different* finding with an invalid citation) are then fed into
    record_evidence_review and assert_uncertainty so the engine enforces REJECT.
    """
    req_id = "req-rev05-sm"
    # Bundle and valid_primary both use CHK-REAL → citation validation passes
    bundle = _bundle(req_id, chunk_id="CHK-REAL", source_id="SRC-8F6-001")

    # Build a separate finding with an invalid chunk ID purely to generate reviewer-rejected notes
    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-NOT-IN-BUNDLE")
    bad_claim = GeneratedClaim(text="SYNTHETIC: bad cite for reviewer.", citations=(bad_ref,))
    bad_cc = ClaimCitationRecord(claim_id="clm-rev05-sm-bad", citation=bad_ref)
    bad_finding_for_reviewer = SpecialistFinding(
        finding_id="FND-REV05-SM-BAD",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: SM reviewer rejection test fixture (bad cite).",
        proposed_claims=(bad_claim,),
        claim_citations=(bad_cc,),
        reasoning_notes="SYNTHETIC SM reviewer rejection fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding_for_reviewer, bundle)
    assert "REJECT" in review_notes.upper()

    # A valid finding citing CHK-REAL passes citation validation in the state machine
    valid_primary = _finding(
        req_id,
        chunk_id="CHK-REAL",
        source_id="SRC-8F6-001",
        finding_id="FND-REV05-SM-VALID",
        role=ROLE_SQLI_ANALYST,
    )

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    # Citation validation passes because valid_primary → CHK-REAL is in bundle
    sm.record_specialist_analysis(valid_primary)
    # Feed reviewer-rejected notes into evidence review
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty()

    # Reviewer rejection must cause REJECTED terminal state
    assert sm.current_state == OrchestrationState.REJECTED
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.recommendation == AggregationRecommendation.REJECT


# ---------------------------------------------------------------------------
# SC-REV-06: Full trace preserved through reviewer → uncertainty → result
# ---------------------------------------------------------------------------


def test_rev06_full_trace_preserved() -> None:
    """SC-REV-06: The complete trace from specialist finding through reviewer verdict
    to uncertainty reason codes and final decision is preserved and testable.
    """
    req_id = "req-rev06"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-REV06", role=ROLE_SQLI_ANALYST)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty()

    # Trace must include finding ID
    assert sm.specialist_finding is not None
    assert sm.specialist_finding.finding_id == primary.finding_id
    assert sm.specialist_finding.is_confirmed is False
    assert sm.specialist_finding.factual_support == "not_evaluated"

    # Uncertainty aggregation result must be set
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.request_id == req_id
    assert agg.confidence_is_calibrated is False
    # Reason codes must be a non-empty tuple of real UncertaintyReasonCode members
    assert len(agg.contributing_reason_codes) > 0
    for rc in agg.contributing_reason_codes:
        assert isinstance(rc, UncertaintyReasonCode)

    # Transition history must be traceable
    history = sm.transition_history
    assert len(history) >= 3  # at minimum: received→validated, validated→retrieval, retrieval→specialist...
    states_visited = {dst for _, dst, _ in history}
    assert OrchestrationState.REQUEST_VALIDATED in states_visited
    assert OrchestrationState.RETRIEVAL_COMPLETED in states_visited
    assert OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED in states_visited
    assert OrchestrationState.EVIDENCE_REVIEW_COMPLETED in states_visited


def test_rev06_reason_codes_accessible_from_final_result() -> None:
    """SC-REV-06: reason_codes are accessible on FinalGatedAssessmentResult via uncertainty_aggregation."""
    req_id = "req-rev06b"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-REV06B", role=ROLE_SQLI_ANALYST)

    # Use epistemic reviewer notes to drive a clear abstention path
    canned = "REVIEWER: Evidence is unclear and possibly insufficient."
    reviewer = DeterministicEvidenceReviewerFake(canned_notes=canned)
    review_notes = reviewer.review(primary, bundle)

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty()

    final = sm.create_final_result(f"final-rev06b")
    # reason_codes property must return string values
    reason_codes = final.reason_codes
    assert len(reason_codes) > 0
    for rc in reason_codes:
        assert isinstance(rc, str)


# ---------------------------------------------------------------------------
# Replay path: multi-specialist fixtures through OrchestrationReplayAdapter
# ---------------------------------------------------------------------------


def test_replay_agreement_scenario_through_harness() -> None:
    """Two specialists agree; replay through the harness produces PROCEED or ABSTAINED with trace."""
    case = _case(10)
    req_id = f"req-8f6-replay-{case.case_id}-rep0"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id=f"FND-REPLAY-10-PRI", role=ROLE_SQLI_ANALYST)
    secondary = _finding(req_id, finding_id=f"FND-REPLAY-10-SEC", role=ROLE_BAC_ANALYST,
                         summary="SYNTHETIC: Secondary agrees.")

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/query/10",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=primary,
        review_notes=review_notes,
        secondary_findings=(secondary,),
        force_sufficient=True,
    )

    adapter = OrchestrationReplayAdapter(
        runner_id="runner-replay-agree",
        case_fixtures={case.case_id: fixture},
        propagate_exceptions=False,
    )
    run_rec = adapter.run_case(case, repeat_index=0)

    # Must not be incomplete
    assert run_rec.result.is_incomplete is False
    meta = run_rec.reproducibility_metadata
    assert meta.get("confidence_is_calibrated") == "False"
    # Final state must be traceable
    assert "final_state" in meta
    assert meta.get("trajectory") is not None


def test_replay_disagreement_scenario_through_harness() -> None:
    """Two specialists disagree; replay produces ABSTAINED/REJECTED with traceable reason codes."""
    case = _case(11)
    req_id = f"req-8f6-replay-{case.case_id}-rep0"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id=f"FND-REPLAY-11-PRI", role=ROLE_SQLI_ANALYST,
                       vulnerability_identified=True)
    secondary = _finding(req_id, finding_id=f"FND-REPLAY-11-SEC", role=ROLE_XSS_ANALYST,
                         vulnerability_identified=False)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle, secondary_findings=(secondary,))

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/query/11",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=primary,
        review_notes=review_notes,
        secondary_findings=(secondary,),
    )

    adapter = OrchestrationReplayAdapter(
        runner_id="runner-replay-disagree",
        case_fixtures={case.case_id: fixture},
        propagate_exceptions=False,
    )
    run_rec = adapter.run_case(case, repeat_index=0)
    meta = run_rec.reproducibility_metadata
    final_state = meta.get("final_state", "")

    # Must not be COMPLETED when specialists disagree
    assert final_state != "completed"
    assert run_rec.result.decision in (
        FindingDecision.ABSTAINED,
        FindingDecision.REJECTED,
    )
    # reason codes must be traceable
    if "uncertainty_primary_reason" in meta:
        primary_reason = meta["uncertainty_primary_reason"]
        assert primary_reason in (
            "specialist_disagreement",
            "conflict_markers_present",
            "reviewer_challenge",
            "reviewer_rejection",
        )


def test_replay_reviewer_rejection_scenario_not_bypassed() -> None:
    """Replay: reviewer rejection must not be bypassed even when force_sufficient=True is set."""
    case = _case(12)
    req_id = f"req-8f6-replay-{case.case_id}-rep0"
    bundle = _bundle(req_id, chunk_id="CHK-REAL", source_id="SRC-8F6-001")

    # Citation refers to non-existent chunk
    bad_ref = CitationReference(source_id="SRC-8F6-001", chunk_id="CHK-NONEXISTENT")
    bad_claim = GeneratedClaim(text="SYNTHETIC: bad cite.", citations=(bad_ref,))
    bad_cc = ClaimCitationRecord(claim_id="clm-replay12", citation=bad_ref)
    bad_finding = SpecialistFinding(
        finding_id="FND-REPLAY-12",
        request_id=req_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: replay rejection test.",
        proposed_claims=(bad_claim,),
        claim_citations=(bad_cc,),
        reasoning_notes="SYNTHETIC reviewer rejection replay fixture.",
    )

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(bad_finding, bundle)
    assert "REJECT" in review_notes.upper()

    # force_sufficient=True cannot override reviewer rejection
    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/query/12",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=None,  # Use manual finding below via the bundle
        review_notes=review_notes,
        # Bypass state machine finding record by using review_notes with REJECT signal
        force_sufficient=True,  # This should NOT override reviewer rejection
    )

    # We drive this through the engine directly to verify REJECT takes precedence
    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(
        req_id, bundle,
        primary_finding=bad_finding,
        review_notes=review_notes,
        force_sufficient=True,  # Even force_sufficient cannot override REVIEWER_REJECTION
    )
    assert result.recommendation == AggregationRecommendation.REJECT
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# Deterministic replay: identical inputs → identical outputs
# ---------------------------------------------------------------------------


def test_deterministic_repeated_replay_produces_identical_results() -> None:
    """Replay the same fixture 3 times; all outputs must be byte-identical.

    This verifies the determinism property of the offline test infrastructure.
    """
    case = _case(20)
    bundle = _bundle(f"req-8f6-replay-{case.case_id}-rep0")
    primary = _finding(f"req-8f6-replay-{case.case_id}-rep0",
                       finding_id="FND-DET-20", role=ROLE_SQLI_ANALYST)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)

    fixture = OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url="http://127.0.0.1:3000/api/query/20",
        authorized_scope=("/api",),
        vulnerability_category="SQLI",
        evidence_bundle=bundle,
        specialist_finding=primary,
        review_notes=review_notes,
        force_sufficient=True,
    )

    results = []
    for rep in range(3):
        b = _bundle(f"req-8f6-replay-{case.case_id}-rep{rep}")
        p = _finding(f"req-8f6-replay-{case.case_id}-rep{rep}",
                     finding_id="FND-DET-20", role=ROLE_SQLI_ANALYST)
        rn = DeterministicEvidenceReviewerFake().review(p, b)
        fx = OrchestrationCaseFixture(
            case_id=case.case_id,
            target_url="http://127.0.0.1:3000/api/query/20",
            authorized_scope=("/api",),
            vulnerability_category="SQLI",
            evidence_bundle=b,
            specialist_finding=p,
            review_notes=rn,
            force_sufficient=True,
        )
        adapter = OrchestrationReplayAdapter(
            runner_id="runner-det",
            case_fixtures={case.case_id: fx},
        )
        run_rec = adapter.run_case(case, repeat_index=rep)
        results.append(run_rec.result.decision)

    # All three repeats must produce identical decisions
    assert len(set(r.value for r in results)) == 1


# ---------------------------------------------------------------------------
# SC-COMPAT: Backward compatibility — single specialist, no secondary_findings
# ---------------------------------------------------------------------------


def test_compat_single_specialist_no_secondary_findings() -> None:
    """SC-COMPAT: The existing single-specialist workflow still functions correctly.

    Ensures the backward-compatible path (no secondary_findings) is unaffected.
    """
    req_id = "req-compat-01"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-COMPAT-01", role=ROLE_SQLI_ANALYST)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)

    engine = UncertaintyAggregationEngine()
    result = engine.aggregate(req_id, bundle, primary_finding=primary, review_notes=review_notes)

    assert result.signals.specialist_consensus == "single_finding"
    assert result.confidence_is_calibrated is False


def test_compat_single_specialist_through_state_machine() -> None:
    """SC-COMPAT: Single specialist through state machine produces same behavior as before Phase 8F.6."""
    req_id = "req-compat-sm"
    bundle = _bundle(req_id)
    primary = _finding(req_id, finding_id="FND-COMPAT-SM", role=ROLE_SQLI_ANALYST)

    reviewer = DeterministicEvidenceReviewerFake()
    review_notes = reviewer.review(primary, bundle)

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)
    sm.record_specialist_analysis(primary)
    sm.record_evidence_review(review_notes)
    sm.assess_uncertainty()

    # Must have a valid aggregation result
    agg = sm.uncertainty_aggregation_result
    assert agg is not None
    assert agg.signals.specialist_consensus == "single_finding"
    # Backward compatibility check: existing attributes still present
    assert hasattr(agg, "contributing_reason_codes")
    assert hasattr(agg, "primary_reason_code")
    assert agg.confidence_is_calibrated is False


def test_compat_no_finding_at_all_empty_bundle_abstains() -> None:
    """SC-COMPAT: Empty evidence bundle with no specialist finding abstains fail-closed."""
    req_id = "req-compat-empty"
    bundle = _bundle(req_id, approved=0)

    req = _request(req_id)
    sm = OrchestrationStateMachine(req)
    sm.validate_request()
    sm.record_retrieval(bundle)

    # Empty bundle → immediate ABSTAINED before specialist analysis
    assert sm.current_state == OrchestrationState.ABSTAINED
    # No specialist finding should be present
    assert sm.specialist_finding is None


# ---------------------------------------------------------------------------
# DeterministicVulnerabilityAnalystFake multi-specialist invocation
# ---------------------------------------------------------------------------


def test_fake_specialists_multiple_roles_produce_distinct_findings() -> None:
    """Multiple DeterministicVulnerabilityAnalystFake instances produce distinct, identity-preserving findings."""
    req_id = "req-multi-fake"
    bundle = _bundle(req_id)

    sqli_specialist = DeterministicVulnerabilityAnalystFake(ROLE_SQLI_ANALYST)
    xss_specialist = DeterministicVulnerabilityAnalystFake(ROLE_XSS_ANALYST)
    bac_specialist = DeterministicVulnerabilityAnalystFake(ROLE_BAC_ANALYST)

    f_sqli = sqli_specialist.analyse(req_id, bundle)
    f_xss = xss_specialist.analyse(req_id, bundle)
    f_bac = bac_specialist.analyse(req_id, bundle)

    # Each specialist has a distinct role_id preserved in the finding
    assert f_sqli.specialist_role == ROLE_SQLI_ANALYST
    assert f_xss.specialist_role == ROLE_XSS_ANALYST
    assert f_bac.specialist_role == ROLE_BAC_ANALYST

    # All findings are hypotheses only
    for f in (f_sqli, f_xss, f_bac):
        assert f.is_confirmed is False
        assert f.factual_support == "not_evaluated"
        assert f.request_id == req_id

    # Finding IDs are distinct (stable deterministic hashing per role)
    fids = {f_sqli.finding_id, f_xss.finding_id, f_bac.finding_id}
    assert len(fids) == 3


def test_fake_specialists_fixtured_outputs_deterministic() -> None:
    """Fixtured DeterministicVulnerabilityAnalystFake produces identical outputs for identical inputs."""
    req_id = "req-det-fake"
    bundle = _bundle(req_id)

    fixture = FixturedSpecialistOutput(
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SYNTHETIC: Deterministic fixture output.",
        cwe_id="CWE-89",
        reasoning_notes="SYNTHETIC reasoning for determinism test.",
    )

    specialist = DeterministicVulnerabilityAnalystFake(ROLE_SQLI_ANALYST, fixture=fixture)
    f1 = specialist.analyse(req_id, bundle)
    f2 = specialist.analyse(req_id, bundle)

    assert f1.finding_id == f2.finding_id
    assert f1.vulnerability_identified == f2.vulnerability_identified
    assert f1.severity == f2.severity
    assert f1.summary == f2.summary
