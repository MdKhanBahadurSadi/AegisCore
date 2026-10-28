"""Unit tests for typed multi-agent orchestration data contracts.

Verifies:
- AssessmentRequest validation, loopback/private lab constraints, and scope rejection.
- EvidenceBundle provenance validation, empty approved evidence invariants, and passive data handling.
- SpecialistFinding invariants (proposed finding only, is_confirmed=False, factual_support='not_evaluated').
- ClaimCitationRecord structure and non-entailment invariant.
- UncertaintyAssessment score bounding, sufficiency rules, and uncalibrated confidence invariant.
- ConflictAssessment distinction between explicit markers and un-evaluated semantic contradictions.
- AgentExecutionRecord token bounds, latency checks, and credential scrubbing.
- FinalGatedAssessmentResult gating integrity and fail-closed result enforcement.
"""

from __future__ import annotations

import pytest

from aegiscore.claim_validation import (
    ClaimValidationResult,
    EvidenceSufficiencyClassification,
    GatedGenerationResult,
)
from aegiscore.generation import (
    GeneratedClaim,
    GenerationContractError,
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
    ScopeViolationError,
    SpecialistFinding,
    UncertaintyAssessment,
)
import hashlib
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata
from aegiscore.rag_runtime import EvidenceRetrievalResult
from aegiscore.rag import RetrievalHit, RetrievalResult, RetrievalMetadata, RetrievalQuery


def _make_dummy_chunk(chunk_id: str = "chk-1", source_id: str = "src-1", content: str = "dummy content") -> SourceChunk:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    metadata = SourceMetadata(source_id=source_id, content_sha256=digest)
    return SourceChunk(
        chunk_id=chunk_id,
        provenance=metadata,
        ordinal=0,
        start_offset=0,
        end_offset=len(content),
        content=content,
        content_sha256=digest,
    )


# ---------------------------------------------------------------------------
# AssessmentRequest Contract Tests
# ---------------------------------------------------------------------------


def test_valid_assessment_request() -> None:
    req = AssessmentRequest(
        request_id="req-123",
        target_url="http://127.0.0.1:8080",
        vulnerability_category="XSS",
        authorized_scope=("/api/v1/search", "/api/v1/comments"),
        analysis_mode="passive_rag_only",
    )
    assert req.request_id == "req-123"
    assert req.target_url == "http://127.0.0.1:8080"
    assert req.vulnerability_category == "XSS"
    assert req.authorized_scope == ("/api/v1/search", "/api/v1/comments")
    assert req.analysis_mode == "passive_rag_only"
    assert req.permit_id is None


def test_assessment_request_active_mode_requires_permit() -> None:
    # Missing permit_id in active mode must raise OrchestrationContractError
    with pytest.raises(OrchestrationContractError, match="active_guarded analysis requires a non-empty permit_id"):
        AssessmentRequest(
            request_id="req-124",
            target_url="http://127.0.0.1:8080",
            vulnerability_category="SQLI",
            authorized_scope=("/rest/login",),
            analysis_mode="active_guarded",
            permit_id=None,
        )

    # Valid permit_id succeeds
    req = AssessmentRequest(
        request_id="req-124",
        target_url="http://127.0.0.1:8080",
        vulnerability_category="SQLI",
        authorized_scope=("/rest/login",),
        analysis_mode="active_guarded",
        permit_id="permit-xyz-999",
    )
    assert req.permit_id == "permit-xyz-999"


def test_assessment_request_rejects_empty_fields() -> None:
    with pytest.raises(OrchestrationContractError, match="request_id"):
        AssessmentRequest(
            request_id="",
            target_url="http://127.0.0.1:8080",
            vulnerability_category="XSS",
            authorized_scope=("/rest",),
        )

    with pytest.raises(OrchestrationContractError, match="vulnerability_category"):
        AssessmentRequest(
            request_id="req-1",
            target_url="http://127.0.0.1:8080",
            vulnerability_category="",
            authorized_scope=("/rest",),
        )


def test_assessment_request_rejects_unauthorized_external_targets() -> None:
    # Public external IP must fail closed
    with pytest.raises(ScopeViolationError, match="not an authorized private"):
        AssessmentRequest(
            request_id="req-ext-1",
            target_url="http://93.184.216.34:80",
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )

    # Public domain must fail closed
    with pytest.raises(ScopeViolationError, match="not an authorized internal lab domain"):
        AssessmentRequest(
            request_id="req-ext-2",
            target_url="https://example.com/login",
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )

    # Forbidden scheme (e.g. ftp)
    with pytest.raises(ScopeViolationError, match="scheme 'ftp' is not permitted"):
        AssessmentRequest(
            request_id="req-ftp",
            target_url="ftp://127.0.0.1/pub",
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )

    # Embedded credentials in URL
    with pytest.raises(ScopeViolationError, match="embedded user credentials"):
        AssessmentRequest(
            request_id="req-cred",
            target_url="http://admin:secret@127.0.0.1:8080",
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )

    # URL fragment
    with pytest.raises(ScopeViolationError, match="URL fragments"):
        AssessmentRequest(
            request_id="req-frag",
            target_url="http://127.0.0.1:8080/app#frag",
            vulnerability_category="XSS",
            authorized_scope=("/",),
        )


def test_assessment_request_rejects_empty_or_invalid_scope() -> None:
    # Empty tuple
    with pytest.raises(OrchestrationContractError, match="authorized_scope must not be empty"):
        AssessmentRequest(
            request_id="req-s1",
            target_url="http://127.0.0.1:8080",
            vulnerability_category="XSS",
            authorized_scope=(),
        )

    # Relative path
    with pytest.raises(ScopeViolationError, match="must be an absolute path starting with '/'"):
        AssessmentRequest(
            request_id="req-s2",
            target_url="http://127.0.0.1:8080",
            vulnerability_category="XSS",
            authorized_scope=("relative/path",),
        )


# ---------------------------------------------------------------------------
# EvidenceBundle Contract Tests
# ---------------------------------------------------------------------------


def test_valid_evidence_bundle() -> None:
    chunk1 = _make_dummy_chunk("chk-1", "src-1", "Reflected param payload")
    ref1 = CitationReference(source_id="src-1", chunk_id="chk-1")
    bundle = EvidenceBundle(
        bundle_id="bnd-01",
        request_id="req-100",
        retrieval_query="xss reflection in search",
        chunks=(chunk1,),
        citations=(ref1,),
        manifest_fingerprint="sha256-fingerprint-abc",
        approved_source_count=1,
    )
    assert bundle.bundle_id == "bnd-01"
    assert len(bundle.chunks) == 1
    assert len(bundle.citations) == 1
    assert bundle.approved_source_count == 1
    assert bundle.evidence_status == "evidence_found"


def test_evidence_bundle_rejects_mismatched_citation_reference() -> None:
    chunk1 = _make_dummy_chunk("chk-1", "src-1", "Some content")
    # Reference points to chk-999 which is NOT in chunks
    ref_missing = CitationReference(source_id="src-1", chunk_id="chk-999")
    with pytest.raises(OrchestrationContractError, match="does not match any chunk in evidence bundle"):
        EvidenceBundle(
            bundle_id="bnd-02",
            request_id="req-101",
            retrieval_query="query",
            chunks=(chunk1,),
            citations=(ref_missing,),
            manifest_fingerprint="sha256-abc",
            approved_source_count=1,
        )


def test_evidence_bundle_empty_approved_sources_invariant() -> None:
    # If approved_source_count is 0, chunks and citations must be empty
    bundle = EvidenceBundle(
        bundle_id="bnd-empty",
        request_id="req-102",
        retrieval_query="query",
        chunks=(),
        citations=(),
        manifest_fingerprint="sha256-abc",
        approved_source_count=0,
        evidence_status="no_approved_evidence",
    )
    assert bundle.approved_source_count == 0
    assert bundle.evidence_status == "no_approved_evidence"

    # Attempting to supply chunks when approved_source_count is 0 must fail
    chunk1 = _make_dummy_chunk("chk-1", "src-1")
    ref1 = CitationReference(source_id="src-1", chunk_id="chk-1")
    with pytest.raises(OrchestrationContractError, match="cannot contain chunks or citations when approved_source_count is 0"):
        EvidenceBundle(
            bundle_id="bnd-bad",
            request_id="req-103",
            retrieval_query="query",
            chunks=(chunk1,),
            citations=(ref1,),
            manifest_fingerprint="sha256-abc",
            approved_source_count=0,
            evidence_status="no_approved_evidence",
        )


# ---------------------------------------------------------------------------
# ClaimCitationRecord Contract Tests
# ---------------------------------------------------------------------------


def test_claim_citation_record_invariants() -> None:
    ref = CitationReference(source_id="src-1", chunk_id="chk-1")
    record = ClaimCitationRecord(
        claim_id="clm-1",
        citation=ref,
        cited_excerpt="Reflected param",
        factual_support="not_evaluated",
    )
    assert record.claim_id == "clm-1"
    assert record.citation.source_id == "src-1"
    assert record.citation.chunk_id == "chk-1"
    assert record.factual_support == "not_evaluated"

    # Factual support cannot be claimed as verified
    with pytest.raises(OrchestrationContractError, match="factual_support must be 'not_evaluated'"):
        ClaimCitationRecord(
            claim_id="clm-1",
            citation=ref,
            cited_excerpt="Reflected param",
            factual_support="verified",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# SpecialistFinding Contract Tests
# ---------------------------------------------------------------------------


def test_specialist_finding_invariants() -> None:
    ref = CitationReference(source_id="src-1", chunk_id="chk-1")
    claim = GeneratedClaim(text="Search parameter is vulnerable to reflected XSS", citations=(ref,))
    finding = SpecialistFinding(
        finding_id="fnd-1",
        request_id="req-1",
        specialist_role="vulnerability_specialist:xss",
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="Reflected XSS identified in query parameter 'q'",
        proposed_claims=(claim,),
        cwe_id="CWE-79",
        is_confirmed=False,
        factual_support="not_evaluated",
    )
    assert finding.finding_id == "fnd-1"
    assert finding.is_confirmed is False
    assert finding.factual_support == "not_evaluated"
    assert finding.severity == FindingSeverity.HIGH

    # Cannot assert is_confirmed=True (it is only a proposed finding)
    with pytest.raises(OrchestrationContractError, match="cannot be marked confirmed"):
        SpecialistFinding(
            finding_id="fnd-bad",
            request_id="req-1",
            specialist_role="vulnerability_specialist:xss",
            vulnerability_identified=True,
            severity=FindingSeverity.HIGH,
            summary="summary",
            proposed_claims=(claim,),
            is_confirmed=True,  # type: ignore[arg-type]
        )

    # Vulnerability identified with zero claims must be rejected
    with pytest.raises(OrchestrationContractError, match="vulnerability_identified is True but proposed_claims is empty"):
        SpecialistFinding(
            finding_id="fnd-bad2",
            request_id="req-1",
            specialist_role="vulnerability_specialist:xss",
            vulnerability_identified=True,
            severity=FindingSeverity.HIGH,
            summary="summary",
            proposed_claims=(),
        )


# ---------------------------------------------------------------------------
# UncertaintyAssessment Contract Tests
# ---------------------------------------------------------------------------


def test_uncertainty_assessment_invariants() -> None:
    ua = UncertaintyAssessment(
        assessment_id="ua-1",
        request_id="req-1",
        epistemic_uncertainty_detected=False,
        uncertainty_keywords=(),
        evidence_sufficiency_score=0.85,
        is_sufficient=True,
        abstention_recommended=False,
        justification="Evidence contains explicit source and sink demonstration",
        confidence_is_calibrated=False,
    )
    assert ua.is_sufficient is True
    assert ua.abstention_recommended is False
    assert ua.confidence_is_calibrated is False

    # Score out of bounds [0.0, 1.0]
    with pytest.raises(OrchestrationContractError, match="bounded in \\[0.0, 1.0\\]"):
        UncertaintyAssessment(
            assessment_id="ua-2",
            request_id="req-1",
            epistemic_uncertainty_detected=False,
            uncertainty_keywords=(),
            evidence_sufficiency_score=1.5,
            is_sufficient=True,
            abstention_recommended=False,
            justification="justification",
        )

    # If is_sufficient is False, abstention_recommended must be True
    with pytest.raises(OrchestrationContractError, match="abstention_recommended must be True when evidence is insufficient"):
        UncertaintyAssessment(
            assessment_id="ua-3",
            request_id="req-1",
            epistemic_uncertainty_detected=True,
            uncertainty_keywords=("unclear",),
            evidence_sufficiency_score=0.2,
            is_sufficient=False,
            abstention_recommended=False,  # Conflict: insufficient evidence cannot recommend proceed!
            justification="justification",
        )

    # Attempting to claim calibrated confidence must be rejected
    with pytest.raises(OrchestrationContractError, match="confidence_is_calibrated must be strictly False"):
        UncertaintyAssessment(
            assessment_id="ua-4",
            request_id="req-1",
            epistemic_uncertainty_detected=False,
            uncertainty_keywords=(),
            evidence_sufficiency_score=0.9,
            is_sufficient=True,
            abstention_recommended=False,
            justification="justification",
            confidence_is_calibrated=True,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# ConflictAssessment Contract Tests
# ---------------------------------------------------------------------------


def test_conflict_assessment_invariants() -> None:
    ca = ConflictAssessment(
        conflict_id="ca-1",
        request_id="req-1",
        conflicts_detected=True,
        conflict_markers=("sanitization present", "vulnerable sink"),
        opposing_roles=("Analyst", "Reviewer"),
        resolution_strategy="human_review_required",
        conflict_summary="Analyst identifies raw sink; Reviewer identifies htmlspecialchars call.",
        semantic_contradiction_detected="not_evaluated",
    )
    assert ca.conflicts_detected is True
    assert ca.resolution_strategy == "human_review_required"
    assert ca.semantic_contradiction_detected == "not_evaluated"

    # Conflicts detected but conflict_markers empty
    with pytest.raises(OrchestrationContractError, match="conflict_markers cannot be empty when conflicts_detected is True"):
        ConflictAssessment(
            conflict_id="ca-2",
            request_id="req-1",
            conflicts_detected=True,
            conflict_markers=(),
            resolution_strategy="fail_closed_abstain",
        )

    # Semantic contradiction cannot be marked evaluated
    with pytest.raises(OrchestrationContractError, match="semantic_contradiction_detected must be 'not_evaluated'"):
        ConflictAssessment(
            conflict_id="ca-3",
            request_id="req-1",
            conflicts_detected=False,
            conflict_markers=(),
            resolution_strategy="none",
            semantic_contradiction_detected="detected",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# AgentExecutionRecord Contract Tests
# ---------------------------------------------------------------------------


def test_agent_execution_record_invariants_and_scrubbing() -> None:
    rec = AgentExecutionRecord(
        execution_id="exec-1",
        request_id="req-1",
        agent_role="vulnerability_specialist:xss",
        model_identifier="DeterministicFakeGenerator",
        prompt_template_hash="sha256-hash-prompt-template",
        input_tokens_est=120,
        output_tokens_est=80,
        latency_ms=12.5,
        parsed_successfully=True,
        output_summary="Parsed finding with 1 claim citing chk-1",
    )
    assert rec.execution_id == "exec-1"
    assert rec.latency_ms == 12.5

    # Negative tokens or latency rejected
    with pytest.raises(OrchestrationContractError, match="non-negative integer"):
        AgentExecutionRecord(
            execution_id="exec-2",
            request_id="req-1",
            agent_role="role",
            model_identifier="model",
            prompt_template_hash="hash",
            input_tokens_est=-1,
            output_tokens_est=10,
            latency_ms=1.0,
            parsed_successfully=True,
            output_summary="summary",
        )

    # Sensitive credential pattern in output summary rejected
    with pytest.raises(OrchestrationContractError, match="output_summary contains prohibited credential pattern"):
        AgentExecutionRecord(
            execution_id="exec-3",
            request_id="req-1",
            agent_role="role",
            model_identifier="model",
            prompt_template_hash="hash",
            input_tokens_est=10,
            output_tokens_est=10,
            latency_ms=1.0,
            parsed_successfully=True,
            output_summary="Invoked with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz",
        )


# ---------------------------------------------------------------------------
# FinalGatedAssessmentResult Contract Tests
# ---------------------------------------------------------------------------


def test_final_gated_assessment_result_proceed_requires_valid_gating() -> None:
    ref = CitationReference(source_id="src-1", chunk_id="chk-1")
    claim = GeneratedClaim(text="Confirmed finding claim", citations=(ref,))
    finding = SpecialistFinding(
        finding_id="fnd-1",
        request_id="req-1",
        specialist_role="role",
        vulnerability_identified=True,
        severity=FindingSeverity.MEDIUM,
        summary="summary",
        proposed_claims=(claim,),
    )
    gen_result = GenerationResult(status="answered", claims=(claim,))
    claim_val = ClaimValidationResult(
        claim=claim,
        classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
        is_valid=True,
        citations_validated=(ref,),
    )
    valid_gating = GatedGenerationResult(
        generation_result=gen_result,
        overall_classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
        claim_validations=(claim_val,),
    )

    # Valid proceed result
    res = FinalGatedAssessmentResult(
        result_id="res-1",
        request_id="req-1",
        decision=GatingDecision.PROCEED,
        finding=finding,
        validation_result=valid_gating,
        abstention_reason=None,
    )
    assert res.decision == GatingDecision.PROCEED

    # Cannot emit PROCEED if validation classification is INSUFFICIENT_EVIDENCE
    insufficient_gating = GatedGenerationResult(
        generation_result=gen_result,
        overall_classification=EvidenceSufficiencyClassification.INSUFFICIENT_EVIDENCE,
        claim_validations=(claim_val,),
    )
    with pytest.raises(OrchestrationContractError, match="cannot emit proceed decision when validation classification is"):
        FinalGatedAssessmentResult(
            result_id="res-bad",
            request_id="req-1",
            decision=GatingDecision.PROCEED,
            finding=finding,
            validation_result=insufficient_gating,
            abstention_reason=None,
        )

    # ABSTAIN requires non-empty abstention_reason
    with pytest.raises(OrchestrationContractError, match="abstain decision requires a non-empty abstention_reason"):
        FinalGatedAssessmentResult(
            result_id="res-bad2",
            request_id="req-1",
            decision=GatingDecision.ABSTAIN,
            abstention_reason=None,
        )
