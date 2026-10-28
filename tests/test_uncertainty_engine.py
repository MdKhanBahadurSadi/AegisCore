"""Focused tests for the UncertaintyAggregationEngine (aegiscore/uncertainty_engine.py).

Covers:
  1.  Normal evidence-supported decision → CONTINUE + SUFFICIENT_AND_CONSISTENT
  2.  Absent evidence (zero chunks / no_approved_evidence) → ABSTAIN + EVIDENCE_ABSENT
  3.  Insufficient evidence (below min chunk threshold) → ABSTAIN + EVIDENCE_INSUFFICIENT
  4.  Invalid citation (chunk not in bundle) → ABSTAIN + CITATION_INVALID
  5.  Verbatim excerpt mismatch → ABSTAIN + EXCERPT_MISMATCH
  6.  Reviewer explicit rejection → REJECT + REVIEWER_REJECTION
  7.  Conflict markers in review notes → ABSTAIN + CONFLICT_MARKERS_PRESENT
  8.  Conflicting specialist findings (disagreement) → ABSTAIN / FLAG + SPECIALIST_DISAGREEMENT
  9.  Epistemic uncertainty keywords in combined text → ABSTAIN + EPISTEMIC_AMBIGUITY
  10. Ungrounded claim (vulnerability identified but no claims) → not applicable here
      (SpecialistFinding contract already rejects that; we test claim with zero citations path via claim_citations)
  11. Deterministic outputs — identical inputs yield identical aggregation_id and scores
  12. force_sufficient and force_conflict overrides
  13. UncertaintyAggregationResult converts to standard UncertaintyAssessment + ConflictAssessment
  14. Contract rejects bad request_id / bad bundle type
  15. Category-specific conflict patterns detected across chunk content
  16. Rule-based conflicts across retrieved chunk content
  17. Reviewer challenge without full rejection → ABSTAIN + REVIEWER_CHALLENGE
  18. Mixed signals: epistemic ambiguity + conflict → conflict wins as primary
  19. Multiple findings with same vulnerability flag → unanimous consensus
  20. SignalAuditRecord fields populated correctly
"""

from __future__ import annotations

import hashlib

import pytest

from aegiscore.generation import GeneratedClaim
from aegiscore.orchestration import (
    ClaimCitationRecord,
    ConflictAssessment,
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    SpecialistFinding,
    UncertaintyAssessment,
)
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata
from aegiscore.specialist_roles import ROLE_XSS_ANALYST, ROLE_SQLI_ANALYST
from aegiscore.uncertainty_engine import (
    AggregationRecommendation,
    UncertaintyAggregationEngine,
    UncertaintyAggregationResult,
    UncertaintyReasonCode,
)


# ---------------------------------------------------------------------------
# Fixture helpers
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
    chunk_id: str = "chk-1",
    source_id: str = "src-1",
    content: str = "SQL injection raw concatenation evidence.",
    request_id: str = "req-test",
) -> EvidenceBundle:
    c = _chunk(chunk_id, source_id, content)
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    return EvidenceBundle(
        bundle_id="bnd-test",
        request_id=request_id,
        retrieval_query="test query",
        chunks=(c,),
        citations=(ref,),
        manifest_fingerprint="sha256-fakefingerprint",
        approved_source_count=1,
    )


def _empty_bundle(request_id: str = "req-test") -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id="bnd-empty",
        request_id=request_id,
        retrieval_query="test query",
        chunks=(),
        citations=(),
        manifest_fingerprint="sha256-fakefingerprint",
        approved_source_count=0,
        evidence_status="no_approved_evidence",
    )


def _finding(
    finding_id: str,
    request_id: str,
    source_id: str,
    chunk_id: str,
    vulnerability_identified: bool = True,
    summary: str = "Reflected XSS detected.",
    reasoning_notes: str = "",
    role: str = ROLE_XSS_ANALYST,
) -> SpecialistFinding:
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    claim = GeneratedClaim(text="Unencoded reflection in response.", citations=(ref,))
    return SpecialistFinding(
        finding_id=finding_id,
        request_id=request_id,
        specialist_role=role,
        vulnerability_identified=vulnerability_identified,
        severity=FindingSeverity.HIGH,
        summary=summary,
        proposed_claims=(claim,),
        reasoning_notes=reasoning_notes,
    )


def _finding_no_vuln(
    finding_id: str,
    request_id: str,
    source_id: str,
    chunk_id: str,
    role: str = ROLE_SQLI_ANALYST,
) -> SpecialistFinding:
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    claim = GeneratedClaim(text="No SQL injection path identified.", citations=(ref,))
    return SpecialistFinding(
        finding_id=finding_id,
        request_id=request_id,
        specialist_role=role,
        vulnerability_identified=False,
        severity=FindingSeverity.INFO,
        summary="No vulnerability identified.",
        proposed_claims=(claim,),
    )


def _engine() -> UncertaintyAggregationEngine:
    return UncertaintyAggregationEngine()


# ---------------------------------------------------------------------------
# Test 1: Normal evidence-supported path → CONTINUE
# ---------------------------------------------------------------------------

def test_normal_supported_decision_returns_continue() -> None:
    """Clear evidence, no conflicts, no epistemic keywords → CONTINUE + score=1.0."""
    bundle = _bundle()
    fnd = _finding("fnd-1", "req-test", "src-1", "chk-1")
    engine = _engine()
    result = engine.aggregate("req-test", bundle, primary_finding=fnd)

    assert result.recommendation == AggregationRecommendation.CONTINUE
    assert result.is_sufficient is True
    assert result.abstention_recommended is False
    assert result.overall_heuristic_score == 1.0
    assert result.primary_reason_code == UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT
    assert result.confidence_is_calibrated is False


# ---------------------------------------------------------------------------
# Test 2: Absent evidence → ABSTAIN + EVIDENCE_ABSENT
# ---------------------------------------------------------------------------

def test_absent_evidence_returns_abstain() -> None:
    """Empty bundle with no_approved_evidence → ABSTAIN, score=0.0, EVIDENCE_ABSENT."""
    bundle = _empty_bundle()
    engine = _engine()
    result = engine.aggregate("req-test", bundle)

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert result.is_sufficient is False
    assert result.abstention_recommended is True
    assert result.overall_heuristic_score == 0.0
    assert result.primary_reason_code == UncertaintyReasonCode.EVIDENCE_ABSENT


# ---------------------------------------------------------------------------
# Test 3: Insufficient evidence (below min chunks) → ABSTAIN + EVIDENCE_INSUFFICIENT
# ---------------------------------------------------------------------------

def test_insufficient_evidence_below_threshold() -> None:
    """Engine with min_sufficient_chunks=3 and only 1 chunk → INSUFFICIENT."""
    bundle = _bundle()
    engine = UncertaintyAggregationEngine(min_sufficient_chunks=3)
    result = engine.aggregate("req-test", bundle)

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert result.is_sufficient is False
    assert UncertaintyReasonCode.EVIDENCE_INSUFFICIENT in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# Test 4: Invalid citation (chunk not in bundle) → CITATION_INVALID
# ---------------------------------------------------------------------------

def test_invalid_citation_chunk_not_in_bundle() -> None:
    """ClaimCitationRecord pointing to a chunk absent from the bundle → CITATION_INVALID."""
    bundle = _bundle("chk-real", "src-real", "Evidence text.", "req-cit")
    ref_bad = CitationReference(source_id="src-real", chunk_id="chk-missing")
    claim = GeneratedClaim(text="A claim.", citations=(ref_bad,))
    cc = ClaimCitationRecord(claim_id="clm-bad", citation=ref_bad)
    fnd = SpecialistFinding(
        finding_id="fnd-cit",
        request_id="req-cit",
        specialist_role=ROLE_XSS_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="XSS detected.",
        proposed_claims=(claim,),
        claim_citations=(cc,),
    )
    engine = _engine()
    result = engine.aggregate("req-cit", bundle, primary_finding=fnd)

    assert result.is_sufficient is False
    assert result.abstention_recommended is True
    assert result.primary_reason_code == UncertaintyReasonCode.CITATION_INVALID
    assert UncertaintyReasonCode.CITATION_INVALID in result.contributing_reason_codes
    assert result.signals.citation_checks_failed >= 1
    assert len(result.signals.citation_failure_reasons) >= 1


# ---------------------------------------------------------------------------
# Test 5: Verbatim excerpt mismatch → EXCERPT_MISMATCH
# ---------------------------------------------------------------------------

def test_excerpt_mismatch_returns_excerpt_mismatch() -> None:
    """ClaimCitationRecord with an excerpt that is NOT in the chunk → EXCERPT_MISMATCH."""
    bundle = _bundle("chk-ex", "src-ex", "The actual chunk content here.", "req-ex")
    ref = CitationReference(source_id="src-ex", chunk_id="chk-ex")
    claim = GeneratedClaim(text="Claim.", citations=(ref,))
    cc = ClaimCitationRecord(
        claim_id="clm-ex",
        citation=ref,
        cited_excerpt="this excerpt is NOT in the chunk at all",
    )
    fnd = SpecialistFinding(
        finding_id="fnd-ex",
        request_id="req-ex",
        specialist_role=ROLE_XSS_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.MEDIUM,
        summary="Finding.",
        proposed_claims=(claim,),
        claim_citations=(cc,),
    )
    engine = _engine()
    result = engine.aggregate("req-ex", bundle, primary_finding=fnd)

    assert result.is_sufficient is False
    assert result.primary_reason_code == UncertaintyReasonCode.EXCERPT_MISMATCH
    assert UncertaintyReasonCode.EXCERPT_MISMATCH in result.contributing_reason_codes
    assert result.signals.citation_checks_failed >= 1


# ---------------------------------------------------------------------------
# Test 6: Reviewer explicit rejection → REJECT
# ---------------------------------------------------------------------------

def test_reviewer_rejection_returns_reject() -> None:
    """Review notes containing REJECTED → recommendation REJECT, REVIEWER_REJECTION primary."""
    bundle = _bundle("chk-rv", "src-rv", "Evidence of potential XSS.", "req-rv")
    fnd = _finding("fnd-rv", "req-rv", "src-rv", "chk-rv")
    engine = _engine()
    result = engine.aggregate(
        "req-rv", bundle, primary_finding=fnd,
        review_notes="REJECTED: The finding is a false positive. STATUS: REJECT.",
    )

    assert result.recommendation == AggregationRecommendation.REJECT
    assert result.primary_reason_code == UncertaintyReasonCode.REVIEWER_REJECTION
    assert UncertaintyReasonCode.REVIEWER_REJECTION in result.contributing_reason_codes
    assert result.signals.reviewer_verdict == "rejected"
    assert result.is_sufficient is False


# ---------------------------------------------------------------------------
# Test 7: Conflict markers in review notes → ABSTAIN + CONFLICT_MARKERS_PRESENT
# ---------------------------------------------------------------------------

def test_conflict_markers_in_review_notes_returns_abstain() -> None:
    """CONFLICT_MARKER in review notes → ABSTAIN + CONFLICT_MARKERS_PRESENT."""
    bundle = _bundle("chk-cm", "src-cm", "SQL evidence here.", "req-cm")
    fnd = _finding("fnd-cm", "req-cm", "src-cm", "chk-cm", role=ROLE_SQLI_ANALYST)
    engine = _engine()
    result = engine.aggregate(
        "req-cm", bundle, primary_finding=fnd,
        review_notes=(
            "REVIEWER: Challenge raised.\n"
            "CONFLICT_MARKER: prepared_statement_present vs raw_sql_concatenation_claimed."
        ),
    )

    assert result.recommendation == AggregationRecommendation.ABSTAIN
    assert result.primary_reason_code == UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT
    assert UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT in result.contributing_reason_codes
    assert len(result.signals.conflict_markers_found) >= 1
    assert any("prepared_statement_present" in m for m in result.signals.conflict_markers_found)


# ---------------------------------------------------------------------------
# Test 8: Conflicting specialist findings (disagreement between two findings)
# ---------------------------------------------------------------------------

def test_specialist_disagreement_detected() -> None:
    """Primary finding: vulnerable. Secondary: not vulnerable. → SPECIALIST_DISAGREEMENT."""
    request_id = "req-dis"
    bundle = _bundle("chk-d", "src-d", "Some evidence.", request_id)
    fnd1 = _finding("fnd-d1", request_id, "src-d", "chk-d", vulnerability_identified=True)
    fnd2 = _finding_no_vuln("fnd-d2", request_id, "src-d", "chk-d", role=ROLE_SQLI_ANALYST)
    fnd2_updated = SpecialistFinding(
        finding_id="fnd-d2",
        request_id=request_id,
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=False,
        severity=FindingSeverity.INFO,
        summary="No vulnerability found.",
        proposed_claims=fnd2.proposed_claims,
    )
    engine = _engine()
    result = engine.aggregate(
        request_id, bundle,
        primary_finding=fnd1,
        secondary_findings=[fnd2_updated],
    )

    assert UncertaintyReasonCode.SPECIALIST_DISAGREEMENT in result.contributing_reason_codes
    assert result.signals.specialist_consensus == "disagreement"
    assert result.signals.conflicting_findings_count == 2
    assert result.is_sufficient is False


# ---------------------------------------------------------------------------
# Test 9: Epistemic uncertainty keywords in combined text → EPISTEMIC_AMBIGUITY
# ---------------------------------------------------------------------------

def test_epistemic_keywords_trigger_ambiguity() -> None:
    """Finding with 'unclear' in summary → EPISTEMIC_AMBIGUITY, abstention."""
    bundle = _bundle("chk-ep", "src-ep", "Evidence is unclear.", "req-ep")
    fnd = _finding(
        "fnd-ep", "req-ep", "src-ep", "chk-ep",
        summary="It is unclear whether the endpoint is vulnerable.",
        reasoning_notes="Possibly a vulnerability but not confirmed.",
    )
    engine = _engine()
    result = engine.aggregate("req-ep", bundle, primary_finding=fnd)

    assert UncertaintyReasonCode.EPISTEMIC_AMBIGUITY in result.contributing_reason_codes
    assert len(result.signals.epistemic_keywords_found) >= 1
    assert "unclear" in result.signals.epistemic_keywords_found or "possibly" in result.signals.epistemic_keywords_found
    assert result.is_sufficient is False


# ---------------------------------------------------------------------------
# Test 10: Deterministic outputs — identical inputs yield identical IDs and scores
# ---------------------------------------------------------------------------

def test_identical_inputs_yield_identical_outputs() -> None:
    """Calling aggregate twice with identical arguments produces byte-identical results."""
    bundle = _bundle("chk-det", "src-det", "Clean evidence.", "req-det")
    fnd = _finding("fnd-det", "req-det", "src-det", "chk-det")
    engine = _engine()

    r1 = engine.aggregate("req-det", bundle, primary_finding=fnd)
    r2 = engine.aggregate("req-det", bundle, primary_finding=fnd)

    assert r1.aggregation_id == r2.aggregation_id
    assert r1.overall_heuristic_score == r2.overall_heuristic_score
    assert r1.recommendation == r2.recommendation
    assert r1.primary_reason_code == r2.primary_reason_code
    assert r1.justification == r2.justification


# ---------------------------------------------------------------------------
# Test 11: force_sufficient override
# ---------------------------------------------------------------------------

def test_force_sufficient_overrides_evidence_signals() -> None:
    """force_sufficient=True with epistemic-keyword evidence still returns sufficient."""
    bundle = _bundle("chk-fs", "src-fs", "This is unclear and possibly insufficient.", "req-fs")
    fnd = _finding("fnd-fs", "req-fs", "src-fs", "chk-fs",
                   summary="Unclear situation.", reasoning_notes="Possibly.")
    engine = _engine()
    result = engine.aggregate("req-fs", bundle, primary_finding=fnd, force_sufficient=True)

    assert result.is_sufficient is True
    assert result.abstention_recommended is False
    assert result.overall_heuristic_score == 1.0


def test_force_sufficient_false_overrides_clean_evidence() -> None:
    """force_sufficient=False with clean evidence forces abstention."""
    bundle = _bundle("chk-ff", "src-ff", "Clean, clear, confirmed evidence.", "req-ff")
    fnd = _finding("fnd-ff", "req-ff", "src-ff", "chk-ff",
                   summary="Clear vulnerability.", reasoning_notes="No ambiguity.")
    engine = _engine()
    result = engine.aggregate("req-ff", bundle, primary_finding=fnd, force_sufficient=False)

    assert result.is_sufficient is False
    assert result.abstention_recommended is True
    assert result.overall_heuristic_score == 0.0


# ---------------------------------------------------------------------------
# Test 12: force_conflict override
# ---------------------------------------------------------------------------

def test_force_conflict_true_injects_conflict() -> None:
    """force_conflict=True with clean review notes → conflict markers detected."""
    bundle = _bundle("chk-fc", "src-fc", "Clean evidence.", "req-fc")
    fnd = _finding("fnd-fc", "req-fc", "src-fc", "chk-fc")
    engine = _engine()
    result = engine.aggregate(
        "req-fc", bundle, primary_finding=fnd,
        force_conflict=True,
        forced_conflict_markers=["marker_injected_a", "marker_injected_b"],
    )

    assert len(result.signals.conflict_markers_found) >= 1
    assert "marker_injected_a" in result.signals.conflict_markers_found


def test_force_conflict_false_clears_conflict_markers() -> None:
    """force_conflict=False with CONFLICT_MARKER in review notes clears detected markers."""
    bundle = _bundle("chk-cl", "src-cl", "Evidence.", "req-cl")
    fnd = _finding("fnd-cl", "req-cl", "src-cl", "chk-cl")
    engine = _engine()
    result = engine.aggregate(
        "req-cl", bundle, primary_finding=fnd,
        review_notes="CONFLICT_MARKER: a_vs_b.",
        force_conflict=False,
    )

    assert len(result.signals.conflict_markers_found) == 0


# ---------------------------------------------------------------------------
# Test 13: to_uncertainty_assessment and to_conflict_assessment conversions
# ---------------------------------------------------------------------------

def test_to_uncertainty_assessment_roundtrip() -> None:
    """to_uncertainty_assessment() produces a valid UncertaintyAssessment."""
    bundle = _bundle("chk-ua", "src-ua", "Clean evidence.", "req-ua")
    fnd = _finding("fnd-ua", "req-ua", "src-ua", "chk-ua")
    engine = _engine()
    result = engine.aggregate("req-ua", bundle, primary_finding=fnd)

    ua = result.to_uncertainty_assessment()
    assert isinstance(ua, UncertaintyAssessment)
    assert ua.request_id == "req-ua"
    assert ua.confidence_is_calibrated is False
    assert ua.is_sufficient == result.is_sufficient
    assert 0.0 <= ua.evidence_sufficiency_score <= 1.0


def test_to_conflict_assessment_roundtrip_no_conflict() -> None:
    """to_conflict_assessment() produces a valid ConflictAssessment (no-conflict path)."""
    bundle = _bundle("chk-ca", "src-ca", "Clean evidence.", "req-ca")
    fnd = _finding("fnd-ca", "req-ca", "src-ca", "chk-ca")
    engine = _engine()
    result = engine.aggregate("req-ca", bundle, primary_finding=fnd)

    ca = result.to_conflict_assessment()
    assert isinstance(ca, ConflictAssessment)
    assert ca.request_id == "req-ca"
    assert ca.semantic_contradiction_detected == "not_evaluated"


def test_to_conflict_assessment_with_conflict_markers() -> None:
    """to_conflict_assessment() produces conflicts_detected=True when markers are present."""
    bundle = _bundle("chk-cac", "src-cac", "Evidence.", "req-cac")
    fnd = _finding("fnd-cac", "req-cac", "src-cac", "chk-cac")
    engine = _engine()
    result = engine.aggregate(
        "req-cac", bundle, primary_finding=fnd,
        review_notes="CONFLICT_MARKER: evidence_a vs evidence_b.",
    )

    ca = result.to_conflict_assessment()
    assert ca.conflicts_detected is True
    assert len(ca.conflict_markers) >= 1
    assert ca.resolution_strategy in ("fail_closed_abstain", "human_review_required")


# ---------------------------------------------------------------------------
# Test 14: Contract rejects bad inputs
# ---------------------------------------------------------------------------

def test_aggregate_rejects_empty_request_id() -> None:
    """aggregate() raises OrchestrationContractError on empty request_id."""
    bundle = _bundle()
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="request_id"):
        engine.aggregate("", bundle)


def test_aggregate_rejects_non_bundle_type() -> None:
    """aggregate() raises OrchestrationContractError when bundle is not an EvidenceBundle."""
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="EvidenceBundle"):
        engine.aggregate("req-bad", "not-a-bundle")  # type: ignore[arg-type]


def test_aggregate_rejects_bundle_request_id_mismatch() -> None:
    """aggregate() raises OrchestrationContractError when bundle.request_id mismatches."""
    bundle = _bundle(request_id="req-other")
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="mismatches"):
        engine.aggregate("req-test", bundle)


def test_aggregate_rejects_non_finding_type() -> None:
    """aggregate() raises OrchestrationContractError when primary_finding is wrong type."""
    bundle = _bundle()
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="SpecialistFinding"):
        engine.aggregate("req-test", bundle, primary_finding="not-a-finding")  # type: ignore[arg-type]


def test_aggregate_rejects_finding_with_wrong_request_id() -> None:
    """aggregate() raises OrchestrationContractError when finding.request_id mismatches."""
    bundle = _bundle("chk-mismatch", "src-mismatch", "Evidence.", "req-correct")
    fnd = _finding("fnd-wrong", "req-wrong", "src-mismatch", "chk-mismatch")
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="mismatches"):
        engine.aggregate("req-correct", bundle, primary_finding=fnd)


def test_aggregate_rejects_secondary_finding_with_wrong_request_id() -> None:
    """aggregate() raises OrchestrationContractError when secondary_finding.request_id mismatches."""
    bundle = _bundle("chk-sf", "src-sf", "Evidence.", "req-sfid")
    fnd1 = _finding("fnd-sf1", "req-sfid", "src-sf", "chk-sf")
    fnd_bad = _finding("fnd-bad", "req-WRONG", "src-sf", "chk-sf", role=ROLE_SQLI_ANALYST)
    engine = _engine()
    with pytest.raises(OrchestrationContractError, match="mismatches"):
        engine.aggregate("req-sfid", bundle, primary_finding=fnd1, secondary_findings=[fnd_bad])


# ---------------------------------------------------------------------------
# Test 15: Category-specific conflict patterns detected
# ---------------------------------------------------------------------------

def test_category_conflict_pattern_in_chunk_content() -> None:
    """If chunk text contains both ends of a conflict pair, conflict marker is raised."""
    # "prepared statement" AND "raw sql concatenation" in same content:
    content = (
        "The login route uses a prepared statement for safe queries. "
        "However, the search endpoint relies on raw sql concatenation of user input."
    )
    bundle = _bundle("chk-cp", "src-cp", content, "req-cp")
    fnd = _finding("fnd-cp", "req-cp", "src-cp", "chk-cp")
    engine = _engine()
    result = engine.aggregate("req-cp", bundle, primary_finding=fnd)

    assert len(result.signals.conflict_markers_found) >= 1
    combined_markers = " ".join(result.signals.conflict_markers_found)
    assert "prepared statement" in combined_markers or "raw sql concatenation" in combined_markers


# ---------------------------------------------------------------------------
# Test 16: Rule-based conflicts from DEFAULT_CONFLICT_RULES
# ---------------------------------------------------------------------------

def test_rule_based_conflict_detection_across_chunks() -> None:
    """DEFAULT_CONFLICT_RULES: 'vulnerability:confirmed' vs 'vulnerability:disproved' in chunks."""
    c1 = _chunk("chk-r1", "src-r", "vulnerability:confirmed by active testing.")
    c2 = _chunk("chk-r2", "src-r", "vulnerability:disproved after review.")
    ref1 = CitationReference(source_id="src-r", chunk_id="chk-r1")
    ref2 = CitationReference(source_id="src-r", chunk_id="chk-r2")
    bundle = EvidenceBundle(
        bundle_id="bnd-rule",
        request_id="req-rule",
        retrieval_query="query",
        chunks=(c1, c2),
        citations=(ref1, ref2),
        manifest_fingerprint="sha256-rule-fp",
        approved_source_count=1,
    )
    engine = _engine()
    result = engine.aggregate("req-rule", bundle)

    assert len(result.signals.conflict_markers_found) >= 1


# ---------------------------------------------------------------------------
# Test 17: Reviewer challenge (not full rejection) → REVIEWER_CHALLENGE
# ---------------------------------------------------------------------------

def test_reviewer_challenge_lowers_score() -> None:
    """CHALLENGE: in review notes (without REJECTED) → REVIEWER_CHALLENGE, score < 0.5."""
    bundle = _bundle("chk-rc", "src-rc", "Evidence.", "req-rc")
    fnd = _finding("fnd-rc", "req-rc", "src-rc", "chk-rc")
    engine = _engine()
    result = engine.aggregate(
        "req-rc", bundle, primary_finding=fnd,
        review_notes="CHALLENGE: Insufficient reachability proof.",
    )

    assert UncertaintyReasonCode.REVIEWER_CHALLENGE in result.contributing_reason_codes
    assert result.signals.reviewer_verdict == "challenged"
    assert result.is_sufficient is False
    assert result.recommendation == AggregationRecommendation.ABSTAIN


# ---------------------------------------------------------------------------
# Test 18: Mixed signals — conflict wins as primary over epistemic ambiguity
# ---------------------------------------------------------------------------

def test_conflict_primary_over_epistemic_ambiguity() -> None:
    """When both conflicts and epistemic keywords are present, conflict is primary reason."""
    bundle = _bundle("chk-mx", "src-mx", "Possibly vulnerable evidence.", "req-mx")
    fnd = _finding("fnd-mx", "req-mx", "src-mx", "chk-mx",
                   summary="Unclear finding — possibly an issue.")
    engine = _engine()
    result = engine.aggregate(
        "req-mx", bundle, primary_finding=fnd,
        review_notes="CONFLICT_MARKER: conflicting_defense vs attack_path.",
    )

    assert result.primary_reason_code == UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT
    assert UncertaintyReasonCode.EPISTEMIC_AMBIGUITY in result.contributing_reason_codes
    assert UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# Test 19: Multiple findings unanimous → consensus='unanimous'
# ---------------------------------------------------------------------------

def test_multiple_unanimous_findings_consensus() -> None:
    """Two findings both identifying vulnerability → unanimous consensus."""
    request_id = "req-un"
    bundle = _bundle("chk-un", "src-un", "XSS evidence.", request_id)
    fnd1 = _finding("fnd-un1", request_id, "src-un", "chk-un", vulnerability_identified=True)
    fnd2 = _finding("fnd-un2", request_id, "src-un", "chk-un",
                    vulnerability_identified=True, role=ROLE_SQLI_ANALYST)
    engine = _engine()
    result = engine.aggregate(request_id, bundle, primary_finding=fnd1, secondary_findings=[fnd2])

    assert result.signals.specialist_consensus == "unanimous"
    assert result.signals.conflicting_findings_count == 0


# ---------------------------------------------------------------------------
# Test 20: SignalAuditRecord fields populated correctly
# ---------------------------------------------------------------------------

def test_signal_audit_record_fields_populated() -> None:
    """SignalAuditRecord captures all expected signal fields."""
    bundle = _bundle("chk-sig", "src-sig", "Clear SQL injection evidence.", "req-sig")
    fnd = _finding("fnd-sig", "req-sig", "src-sig", "chk-sig")
    engine = _engine()
    result = engine.aggregate(
        "req-sig", bundle, primary_finding=fnd,
        review_notes="No challenges raised.",
    )

    sig = result.signals
    assert sig.evidence_chunk_count == 1
    assert sig.approved_source_count == 1
    assert 0.0 <= sig.evidence_sufficiency_score <= 1.0
    assert isinstance(sig.epistemic_keywords_found, tuple)
    assert isinstance(sig.citation_checks_passed, int)
    assert isinstance(sig.citation_checks_failed, int)
    assert isinstance(sig.citation_failure_reasons, tuple)
    assert sig.specialist_consensus == "single_finding"
    assert sig.conflicting_findings_count == 0
    assert isinstance(sig.reviewer_verdict, str)
    assert isinstance(sig.conflict_markers_found, tuple)
    assert sig.provenance_verified is True


# ---------------------------------------------------------------------------
# Test 21: confidence_is_calibrated is always False (contract enforced)
# ---------------------------------------------------------------------------

def test_confidence_is_calibrated_always_false() -> None:
    """confidence_is_calibrated must always be False in all result paths."""
    bundle = _bundle("chk-cal", "src-cal", "Evidence.", "req-cal")
    engine = _engine()

    # Test with no finding
    result_empty = engine.aggregate("req-cal", _empty_bundle("req-cal"))
    assert result_empty.confidence_is_calibrated is False

    # Test with clean finding
    fnd = _finding("fnd-cal", "req-cal", "src-cal", "chk-cal")
    result_clean = engine.aggregate("req-cal", bundle, primary_finding=fnd)
    assert result_clean.confidence_is_calibrated is False

    # Test to_uncertainty_assessment also preserves False
    ua = result_clean.to_uncertainty_assessment()
    assert ua.confidence_is_calibrated is False


# ---------------------------------------------------------------------------
# Test 22: Verbatim excerpt present in chunk → citation passes
# ---------------------------------------------------------------------------

def test_valid_excerpt_citation_passes() -> None:
    """ClaimCitationRecord with excerpt that exists verbatim → no citation failure."""
    content = "The endpoint uses raw SQL: SELECT * FROM users WHERE id = '" + "' + userInput"
    verbatim_excerpt = "raw SQL"
    bundle = _bundle("chk-vex", "src-vex", content, "req-vex")
    ref = CitationReference(source_id="src-vex", chunk_id="chk-vex")
    claim = GeneratedClaim(text="Raw SQL injection found.", citations=(ref,))
    cc = ClaimCitationRecord(claim_id="clm-vex", citation=ref, cited_excerpt=verbatim_excerpt)
    fnd = SpecialistFinding(
        finding_id="fnd-vex",
        request_id="req-vex",
        specialist_role=ROLE_SQLI_ANALYST,
        vulnerability_identified=True,
        severity=FindingSeverity.HIGH,
        summary="SQL injection.",
        proposed_claims=(claim,),
        claim_citations=(cc,),
    )
    engine = _engine()
    result = engine.aggregate("req-vex", bundle, primary_finding=fnd)

    assert result.signals.citation_checks_failed == 0
    assert result.signals.citation_checks_passed == 1
    assert UncertaintyReasonCode.EXCERPT_MISMATCH not in result.contributing_reason_codes
    assert UncertaintyReasonCode.CITATION_INVALID not in result.contributing_reason_codes


# ---------------------------------------------------------------------------
# Test 23: No primary finding, no secondary findings → no_finding consensus
# ---------------------------------------------------------------------------

def test_no_findings_produces_no_finding_consensus() -> None:
    """aggregate() with no primary or secondary findings → consensus='no_finding'."""
    bundle = _bundle("chk-nf", "src-nf", "Evidence.", "req-nf")
    engine = _engine()
    result = engine.aggregate("req-nf", bundle)

    assert result.signals.specialist_consensus == "no_finding"
    assert result.signals.conflicting_findings_count == 0


# ---------------------------------------------------------------------------
# Test 24: UncertaintyAggregationResult contract reject bad types
# ---------------------------------------------------------------------------

def test_result_contract_rejects_bad_recommendation_type() -> None:
    """UncertaintyAggregationResult raises on invalid recommendation type."""
    from aegiscore.uncertainty_engine import SignalAuditRecord
    sig = SignalAuditRecord(
        evidence_chunk_count=1,
        approved_source_count=1,
        evidence_sufficiency_score=0.8,
        epistemic_keywords_found=(),
        citation_checks_passed=0,
        citation_checks_failed=0,
        citation_failure_reasons=(),
        specialist_consensus="single_finding",
        conflicting_findings_count=0,
        reviewer_verdict="uncontested",
        conflict_markers_found=(),
        provenance_verified=True,
    )
    with pytest.raises(OrchestrationContractError, match="AggregationRecommendation"):
        UncertaintyAggregationResult(
            aggregation_id="agg-bad",
            request_id="req-bad",
            recommendation="BAD_RECOMMENDATION",  # type: ignore[arg-type]
            overall_heuristic_score=0.8,
            is_sufficient=True,
            abstention_recommended=False,
            primary_reason_code=UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,
            contributing_reason_codes=(UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,),
            justification="test",
            signals=sig,
            confidence_is_calibrated=False,
        )


def test_result_contract_rejects_out_of_range_score() -> None:
    """UncertaintyAggregationResult raises on overall_heuristic_score > 1.0."""
    from aegiscore.uncertainty_engine import SignalAuditRecord
    sig = SignalAuditRecord(
        evidence_chunk_count=1, approved_source_count=1,
        evidence_sufficiency_score=1.5, epistemic_keywords_found=(),
        citation_checks_passed=0, citation_checks_failed=0,
        citation_failure_reasons=(), specialist_consensus="single_finding",
        conflicting_findings_count=0, reviewer_verdict="uncontested",
        conflict_markers_found=(), provenance_verified=True,
    )
    with pytest.raises(OrchestrationContractError, match="bounded"):
        UncertaintyAggregationResult(
            aggregation_id="agg-out",
            request_id="req-out",
            recommendation=AggregationRecommendation.CONTINUE,
            overall_heuristic_score=1.5,
            is_sufficient=True,
            abstention_recommended=False,
            primary_reason_code=UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT,
            contributing_reason_codes=(),
            justification="test",
            signals=sig,
            confidence_is_calibrated=False,
        )
