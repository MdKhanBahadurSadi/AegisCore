"""Deterministic, transparent uncertainty aggregation engine for AEGISCORE AI.

This module provides the core uncertainty aggregation component for multi-agent
orchestration. It systematically synthesizes multiple analytical signals:
  1. Evidence sufficiency (chunk count, approved source status)
  2. Specialist consensus vs. disagreement (finding alignment across roles)
  3. Evidence reviewer verdicts (challenges, mitigations, rejections)
  4. Citation and verbatim excerpt integrity (grounding verification)
  5. Contradictory evidence and category-specific conflict markers
  6. Epistemic uncertainty terminology ("unclear", "possible", "unconfirmed")
  7. Source provenance integrity (approved chunk verification)

It produces a deterministic UncertaintyAggregationResult with machine-readable
reason codes, an uncalibrated heuristic index (confidence_is_calibrated=False),
a clear recommendation (CONTINUE, REJECT, ABSTAIN, FLAG_FOR_REVIEW), and an
auditable record of all evaluated signals.

Zero external network calls, zero API keys, zero LLM dependencies, offline only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Sequence

from aegiscore.generation import (
    ConflictRule,
    DEFAULT_CONFLICT_RULES,
    GeneratedClaim,
)
from aegiscore.orchestration import (
    ClaimCitationRecord,
    ConflictAssessment,
    EvidenceBundle,
    OrchestrationContractError,
    SpecialistFinding,
    UncertaintyAssessment,
)
from aegiscore.rag import (
    CitationReference,
    RagContractError,
    SourceChunk,
    _nonempty_text,
)


# ---------------------------------------------------------------------------
# Reason Codes & Recommendations
# ---------------------------------------------------------------------------


class UncertaintyReasonCode(str, Enum):
    """Explicit, machine-readable reason codes explaining uncertainty aggregation decisions."""

    EVIDENCE_ABSENT = "evidence_absent"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    UNGROUNDED_CLAIM = "ungrounded_claim"
    CITATION_INVALID = "citation_invalid"
    EXCERPT_MISMATCH = "excerpt_mismatch"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    SPECIALIST_DISAGREEMENT = "specialist_disagreement"
    REVIEWER_REJECTION = "reviewer_rejection"
    REVIEWER_CHALLENGE = "reviewer_challenge"
    CONFLICT_MARKERS_PRESENT = "conflict_markers_present"
    EPISTEMIC_AMBIGUITY = "epistemic_ambiguity"
    UNVERIFIED_PROVENANCE = "unverified_provenance"
    SUFFICIENT_AND_CONSISTENT = "sufficient_and_consistent"


class AggregationRecommendation(str, Enum):
    """Action recommendation emitted by the uncertainty aggregation engine."""

    CONTINUE = "continue"
    REJECT = "reject"
    ABSTAIN = "abstain"
    FLAG_FOR_REVIEW = "flag_for_review"


# ---------------------------------------------------------------------------
# Lexical & Conflict Patterns
# ---------------------------------------------------------------------------

_EPISTEMIC_KEYWORDS: tuple[str, ...] = (
    "unclear",
    "insufficient",
    "possible",
    "possibly",
    "uncertain",
    "ambiguous",
    "may be",
    "might be",
    "could be",
    "not confirmed",
    "unverified",
)

_CATEGORY_CONFLICT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("htmlspecialchars", "reflected without encoding"),
    ("csp header present", "no content-security-policy"),
    ("input sanitized", "raw html output"),
    ("prepared statement", "raw sql concatenation"),
    ("parameterized query", "string interpolation"),
    ("orm used", "direct query construction"),
    ("authorization check present", "no authorization check"),
    ("role validation enforced", "role not verified"),
)

_REJECTION_MARKERS: tuple[str, ...] = (
    "REJECTED",
    "VULNERABILITY_REJECTED",
    "STATUS: REJECT",
    "DECISION: REJECT",
)


# ---------------------------------------------------------------------------
# Audit Data Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignalAuditRecord:
    """Auditable record of all individual signals evaluated by the uncertainty engine."""

    evidence_chunk_count: int
    approved_source_count: int
    evidence_sufficiency_score: float
    epistemic_keywords_found: tuple[str, ...]
    citation_checks_passed: int
    citation_checks_failed: int
    citation_failure_reasons: tuple[str, ...]
    specialist_consensus: str
    conflicting_findings_count: int
    reviewer_verdict: str
    conflict_markers_found: tuple[str, ...]
    provenance_verified: bool


@dataclass(frozen=True, slots=True)
class UncertaintyAggregationResult:
    """Deterministic outcome of uncertainty signal aggregation.

    Model confidence scores are strictly uncalibrated heuristics.
    confidence_is_calibrated is strictly False.
    """

    aggregation_id: str
    request_id: str
    recommendation: AggregationRecommendation
    overall_heuristic_score: float
    is_sufficient: bool
    abstention_recommended: bool
    primary_reason_code: UncertaintyReasonCode
    contributing_reason_codes: tuple[UncertaintyReasonCode, ...]
    justification: str
    signals: SignalAuditRecord
    confidence_is_calibrated: Literal[False] = False

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.aggregation_id, "aggregation_id")
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.justification, "justification")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.recommendation, AggregationRecommendation):
            raise OrchestrationContractError("recommendation must be an AggregationRecommendation")
        if not isinstance(self.primary_reason_code, UncertaintyReasonCode):
            raise OrchestrationContractError("primary_reason_code must be an UncertaintyReasonCode")
        if not isinstance(self.contributing_reason_codes, tuple):
            raise OrchestrationContractError("contributing_reason_codes must be a tuple")
        for rc in self.contributing_reason_codes:
            if not isinstance(rc, UncertaintyReasonCode):
                raise OrchestrationContractError("every item in contributing_reason_codes must be an UncertaintyReasonCode")

        if isinstance(self.overall_heuristic_score, bool) or not isinstance(self.overall_heuristic_score, (int, float)):
            raise OrchestrationContractError("overall_heuristic_score must be a numeric float")
        if not (0.0 <= float(self.overall_heuristic_score) <= 1.0):
            raise OrchestrationContractError("overall_heuristic_score must be bounded in [0.0, 1.0]")

        if not self.is_sufficient and not self.abstention_recommended:
            raise OrchestrationContractError("abstention_recommended must be True when evidence is insufficient")

        if self.confidence_is_calibrated is not False:
            raise OrchestrationContractError("confidence_is_calibrated must be strictly False (uncalibrated)")

    def to_uncertainty_assessment(self) -> UncertaintyAssessment:
        """Convert to standard UncertaintyAssessment contract for backward compatibility."""
        return UncertaintyAssessment(
            assessment_id=f"ua_{self.aggregation_id}",
            request_id=self.request_id,
            epistemic_uncertainty_detected=len(self.signals.epistemic_keywords_found) > 0,
            uncertainty_keywords=self.signals.epistemic_keywords_found,
            evidence_sufficiency_score=float(self.overall_heuristic_score),
            is_sufficient=self.is_sufficient,
            abstention_recommended=self.abstention_recommended,
            justification=self.justification,
            confidence_is_calibrated=False,
        )

    def to_conflict_assessment(self) -> ConflictAssessment:
        """Convert to standard ConflictAssessment contract for backward compatibility."""
        has_conflicts = (
            len(self.signals.conflict_markers_found) > 0
            or self.signals.conflicting_findings_count > 0
            or self.primary_reason_code in (
                UncertaintyReasonCode.CONFLICTING_EVIDENCE,
                UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT,
                UncertaintyReasonCode.SPECIALIST_DISAGREEMENT,
            )
        )
        strategy: Literal["fail_closed_abstain", "human_review_required", "none"]
        if self.recommendation == AggregationRecommendation.FLAG_FOR_REVIEW:
            strategy = "human_review_required"
        elif has_conflicts or self.recommendation in (AggregationRecommendation.ABSTAIN, AggregationRecommendation.REJECT):
            strategy = "fail_closed_abstain"
        else:
            strategy = "none"

        markers = self.signals.conflict_markers_found
        if has_conflicts and len(markers) == 0:
            if self.signals.conflicting_findings_count > 0:
                markers = ("specialist_findings_disagreement",)
            elif self.primary_reason_code == UncertaintyReasonCode.CONFLICTING_EVIDENCE:
                markers = ("conflicting_evidence_detected",)
            else:
                markers = ("unresolved_conflict",)

        summary = (
            f"Conflict detected. Markers: {list(markers)}. Strategy: {strategy}."
            if has_conflicts else "No explicit conflict markers detected."
        )

        return ConflictAssessment(
            conflict_id=f"ca_{self.aggregation_id}",
            request_id=self.request_id,
            conflicts_detected=has_conflicts,
            conflict_markers=markers,
            opposing_roles=(),
            resolution_strategy=strategy if has_conflicts else "none",
            conflict_summary=summary,
            semantic_contradiction_detected="not_evaluated",
        )


# ---------------------------------------------------------------------------
# Aggregation Engine
# ---------------------------------------------------------------------------


class UncertaintyAggregationEngine:
    """Deterministic, transparent uncertainty aggregation engine.

    Aggregates available evidence, citations, specialist consensus, adversarial reviewer
    feedback, and conflict markers into a deterministic uncertainty assessment with
    auditable reason codes and an uncalibrated heuristic index.
    """

    def __init__(
        self,
        *,
        min_sufficient_chunks: int = 1,
        conflict_rules: Sequence[ConflictRule] = DEFAULT_CONFLICT_RULES,
        sufficiency_threshold: float = 0.5,
    ) -> None:
        self._min_sufficient_chunks = max(1, int(min_sufficient_chunks))
        self._conflict_rules = tuple(conflict_rules)
        self._sufficiency_threshold = float(sufficiency_threshold)

    def aggregate(
        self,
        request_id: str,
        bundle: EvidenceBundle,
        primary_finding: SpecialistFinding | None = None,
        secondary_findings: Sequence[SpecialistFinding] = (),
        review_notes: str = "",
        *,
        force_sufficient: bool | None = None,
        force_conflict: bool | None = None,
        forced_conflict_markers: Sequence[str] | None = None,
    ) -> UncertaintyAggregationResult:
        """Deterministically aggregate uncertainty signals into an auditable assessment."""
        # 1. Parameter Validation
        try:
            _nonempty_text(request_id, "request_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")
        if bundle.request_id != request_id:
            raise OrchestrationContractError(
                f"bundle request_id '{bundle.request_id}' mismatches aggregation request_id '{request_id}'"
            )

        all_findings: list[SpecialistFinding] = []
        if primary_finding is not None:
            if not isinstance(primary_finding, SpecialistFinding):
                raise OrchestrationContractError("primary_finding must be a SpecialistFinding instance")
            if primary_finding.request_id != request_id:
                raise OrchestrationContractError("primary_finding request_id mismatches aggregation request_id")
            all_findings.append(primary_finding)

        for sec in (secondary_findings or ()):
            if not isinstance(sec, SpecialistFinding):
                raise OrchestrationContractError("every secondary finding must be a SpecialistFinding instance")
            if sec.request_id != request_id:
                raise OrchestrationContractError("secondary finding request_id mismatches aggregation request_id")
            all_findings.append(sec)

        # 2. Evidence Sufficiency Signal
        chunk_count = len(bundle.chunks)
        approved_sources = bundle.approved_source_count
        evidence_absent = (
            approved_sources == 0
            or chunk_count == 0
            or bundle.evidence_status == "no_approved_evidence"
        )
        evidence_insufficient = chunk_count < self._min_sufficient_chunks and not evidence_absent

        # 3. Provenance Integrity Signal
        provenance_valid = True
        if not bundle.manifest_fingerprint or bundle.manifest_fingerprint.strip() == "":
            provenance_valid = False
        for c in bundle.chunks:
            chunk_source = getattr(c, "source_id", "")
            if hasattr(c, "provenance") and hasattr(c.provenance, "source_id"):
                chunk_source = c.provenance.source_id
            if not chunk_source or not c.chunk_id:
                provenance_valid = False

        # 4. Citation and Excerpt Integrity Signal
        citation_passed = 0
        citation_failed = 0
        citation_failure_reasons: list[str] = []
        has_excerpt_mismatch = False
        has_invalid_citation = False
        has_ungrounded_claim = False

        chunk_map = {c.chunk_id: c for c in bundle.chunks}

        def get_source_id(c: SourceChunk) -> str:
            if hasattr(c, "provenance") and hasattr(c.provenance, "source_id"):
                return c.provenance.source_id
            return getattr(c, "source_id", "")

        for fnd in all_findings:
            if fnd.vulnerability_identified:
                if len(fnd.proposed_claims) == 0:
                    citation_failed += 1
                    has_ungrounded_claim = True
                    citation_failure_reasons.append(
                        f"Finding {fnd.finding_id}: vulnerability identified with zero claims"
                    )
                for clm in fnd.proposed_claims:
                    if len(clm.citations) == 0:
                        citation_failed += 1
                        has_ungrounded_claim = True
                        citation_failure_reasons.append(
                            f"Finding {fnd.finding_id} claim '{clm.text[:30]}...' has zero citations"
                        )
                    for ref in clm.citations:
                        target_chunk = chunk_map.get(ref.chunk_id)
                        if target_chunk is None:
                            citation_failed += 1
                            has_invalid_citation = True
                            citation_failure_reasons.append(
                                f"Claim citation chunk '{ref.chunk_id}' not found in evidence bundle"
                            )
                        else:
                            expected_source = get_source_id(target_chunk)
                            if ref.source_id != expected_source:
                                citation_failed += 1
                                has_invalid_citation = True
                                citation_failure_reasons.append(
                                    f"Claim citation source_id '{ref.source_id}' mismatches chunk source_id '{expected_source}'"
                                )


            # Inspect claim-to-chunk provenance and excerpts
            for cc in fnd.claim_citations:
                target_chunk = chunk_map.get(cc.citation.chunk_id)
                if target_chunk is None:
                    citation_failed += 1
                    has_invalid_citation = True
                    citation_failure_reasons.append(
                        f"Chunk '{cc.citation.chunk_id}' not found in evidence bundle"
                    )
                else:
                    expected_source = get_source_id(target_chunk)
                    if cc.citation.source_id != expected_source:
                        citation_failed += 1
                        has_invalid_citation = True
                        citation_failure_reasons.append(
                            f"Citation source_id '{cc.citation.source_id}' mismatches chunk source_id '{expected_source}'"
                        )
                    elif cc.cited_excerpt is not None and cc.cited_excerpt != "":
                        if cc.cited_excerpt not in target_chunk.content:
                            citation_failed += 1
                            has_excerpt_mismatch = True
                            citation_failure_reasons.append(
                                f"Cited excerpt does not appear verbatim in chunk '{cc.citation.chunk_id}' content"
                            )
                        else:
                            citation_passed += 1
                    else:
                        citation_passed += 1

        # 5. Specialist Consensus vs. Disagreement Signal
        specialist_consensus: str
        conflicting_findings_count = 0
        has_specialist_disagreement = False

        if len(all_findings) >= 2:
            vuln_flags = [f.vulnerability_identified for f in all_findings]
            if len(set(vuln_flags)) > 1:
                specialist_consensus = "disagreement"
                conflicting_findings_count = len(all_findings)
                has_specialist_disagreement = True
            else:
                specialist_consensus = "unanimous"
        elif len(all_findings) == 1:
            specialist_consensus = "single_finding"
        else:
            specialist_consensus = "no_finding"

        # 6. Reviewer Verdict Signal
        review_upper = review_notes.upper()
        reviewer_verdict: str
        has_reviewer_rejection = False
        has_reviewer_challenge = False

        if any(marker in review_upper for marker in _REJECTION_MARKERS):
            reviewer_verdict = "rejected"
            has_reviewer_rejection = True
        elif "CONFLICT_MARKER:" in review_notes or "CHALLENGE:" in review_notes:
            reviewer_verdict = "challenged"
            has_reviewer_challenge = True
        elif "NO CHALLENGE" in review_upper or "ACCEPTED" in review_upper or "CONFIRMED" in review_upper:
            reviewer_verdict = "accepted"
        else:
            reviewer_verdict = "uncontested" if review_notes.strip() else "not_evaluated"

        # 7. Contradictory Evidence & Conflict Markers
        conflict_markers_found: list[str] = []

        if forced_conflict_markers:
            conflict_markers_found.extend(forced_conflict_markers)

        # Extract explicit markers from review notes
        if "CONFLICT_MARKER:" in review_notes:
            for line in review_notes.split("\n"):
                if "CONFLICT_MARKER:" in line:
                    marker = line.split("CONFLICT_MARKER:")[-1].strip(" .\r")
                    if marker and marker not in conflict_markers_found:
                        conflict_markers_found.append(marker)

        # Evaluate rule-based conflicts across chunk content
        chunk_texts = [c.content.lower() for c in bundle.chunks]
        all_chunk_text = " ".join(chunk_texts)
        for rule in self._conflict_rules:
            if rule.first.lower() in all_chunk_text and rule.second.lower() in all_chunk_text:
                marker = f"{rule.first}_vs_{rule.second}"
                if marker not in conflict_markers_found:
                    conflict_markers_found.append(marker)

        # Evaluate category-specific conflict patterns
        combined_audit_text = (
            all_chunk_text + " " +
            " ".join(f.summary.lower() + " " + f.reasoning_notes.lower() for f in all_findings) + " " +
            review_notes.lower()
        )
        for first_pat, sec_pat in _CATEGORY_CONFLICT_PATTERNS:
            if first_pat in combined_audit_text and sec_pat in combined_audit_text:
                marker = f"{first_pat}_vs_{sec_pat}"
                if marker not in conflict_markers_found:
                    conflict_markers_found.append(marker)

        if force_conflict is not None:
            if force_conflict:
                if not conflict_markers_found:
                    conflict_markers_found.append("forced_conflict")
            else:
                conflict_markers_found = []

        has_conflicts = len(conflict_markers_found) > 0

        # 8. Epistemic Uncertainty Keywords Signal
        keywords_detected: list[str] = []
        for kw in _EPISTEMIC_KEYWORDS:
            if kw in combined_audit_text:
                keywords_detected.append(kw)
        has_epistemic_ambiguity = len(keywords_detected) > 0

        # 9. Deterministic Scoring & Reason Assembly
        contributing_reasons: list[UncertaintyReasonCode] = []

        if evidence_absent:
            contributing_reasons.append(UncertaintyReasonCode.EVIDENCE_ABSENT)
        if evidence_insufficient:
            contributing_reasons.append(UncertaintyReasonCode.EVIDENCE_INSUFFICIENT)
        if not provenance_valid:
            contributing_reasons.append(UncertaintyReasonCode.UNVERIFIED_PROVENANCE)
        if has_ungrounded_claim:
            contributing_reasons.append(UncertaintyReasonCode.UNGROUNDED_CLAIM)
        if has_invalid_citation:
            contributing_reasons.append(UncertaintyReasonCode.CITATION_INVALID)
        if has_excerpt_mismatch:
            contributing_reasons.append(UncertaintyReasonCode.EXCERPT_MISMATCH)
        if has_specialist_disagreement:
            contributing_reasons.append(UncertaintyReasonCode.SPECIALIST_DISAGREEMENT)
        if has_reviewer_rejection:
            contributing_reasons.append(UncertaintyReasonCode.REVIEWER_REJECTION)
        if has_reviewer_challenge:
            contributing_reasons.append(UncertaintyReasonCode.REVIEWER_CHALLENGE)
        if has_conflicts:
            contributing_reasons.append(UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT)
            contributing_reasons.append(UncertaintyReasonCode.CONFLICTING_EVIDENCE)
        if has_epistemic_ambiguity:
            contributing_reasons.append(UncertaintyReasonCode.EPISTEMIC_AMBIGUITY)

        # Calculate heuristic score (explicitly uncalibrated index)
        if evidence_absent or has_invalid_citation or has_excerpt_mismatch or has_reviewer_rejection or has_ungrounded_claim:
            raw_score = 0.0
        elif has_conflicts:
            raw_score = 0.15
        elif has_specialist_disagreement:
            raw_score = 0.25
        elif has_reviewer_challenge:
            raw_score = 0.35
        elif has_epistemic_ambiguity:
            raw_score = 0.40
        elif evidence_insufficient or not provenance_valid:
            raw_score = 0.45
        else:
            raw_score = 1.0

        if force_sufficient is not None:
            score = 1.0 if force_sufficient else 0.0
            is_sufficient = force_sufficient
            abstention_recommended = not force_sufficient
        else:
            score = raw_score
            is_sufficient = score >= self._sufficiency_threshold
            abstention_recommended = not is_sufficient

        # Select primary reason code
        if evidence_absent:
            primary_reason = UncertaintyReasonCode.EVIDENCE_ABSENT
        elif has_invalid_citation:
            primary_reason = UncertaintyReasonCode.CITATION_INVALID
        elif has_excerpt_mismatch:
            primary_reason = UncertaintyReasonCode.EXCERPT_MISMATCH
        elif has_ungrounded_claim:
            primary_reason = UncertaintyReasonCode.UNGROUNDED_CLAIM
        elif has_reviewer_rejection:
            primary_reason = UncertaintyReasonCode.REVIEWER_REJECTION
        elif has_conflicts:
            primary_reason = UncertaintyReasonCode.CONFLICT_MARKERS_PRESENT
        elif has_specialist_disagreement:
            primary_reason = UncertaintyReasonCode.SPECIALIST_DISAGREEMENT
        elif has_reviewer_challenge:
            primary_reason = UncertaintyReasonCode.REVIEWER_CHALLENGE
        elif has_epistemic_ambiguity:
            primary_reason = UncertaintyReasonCode.EPISTEMIC_AMBIGUITY
        elif evidence_insufficient:
            primary_reason = UncertaintyReasonCode.EVIDENCE_INSUFFICIENT
        elif not provenance_valid:
            primary_reason = UncertaintyReasonCode.UNVERIFIED_PROVENANCE
        else:
            primary_reason = UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT
            if not contributing_reasons:
                contributing_reasons.append(UncertaintyReasonCode.SUFFICIENT_AND_CONSISTENT)

        # Determine recommendation
        if has_reviewer_rejection:
            recommendation = AggregationRecommendation.REJECT
        elif has_specialist_disagreement and has_conflicts:
            recommendation = AggregationRecommendation.FLAG_FOR_REVIEW
        elif abstention_recommended:
            recommendation = AggregationRecommendation.ABSTAIN
        else:
            recommendation = AggregationRecommendation.CONTINUE

        # Construct Signal Audit Record
        signals = SignalAuditRecord(
            evidence_chunk_count=chunk_count,
            approved_source_count=approved_sources,
            evidence_sufficiency_score=score,
            epistemic_keywords_found=tuple(keywords_detected),
            citation_checks_passed=citation_passed,
            citation_checks_failed=citation_failed,
            citation_failure_reasons=tuple(citation_failure_reasons),
            specialist_consensus=specialist_consensus,
            conflicting_findings_count=conflicting_findings_count,
            reviewer_verdict=reviewer_verdict,
            conflict_markers_found=tuple(conflict_markers_found),
            provenance_verified=provenance_valid,
        )

        finding_ref = primary_finding.finding_id if primary_finding else "none"
        aggregation_id = _stable_id("agg", request_id, finding_ref)

        justification = (
            f"recommendation={recommendation.value}, primary_reason={primary_reason.value}, "
            f"score={score:.2f}, sufficient={is_sufficient}, chunks={chunk_count}, "
            f"consensus={specialist_consensus}, reviewer={reviewer_verdict}, "
            f"conflicts={len(conflict_markers_found)}, epistemic_kw={list(keywords_detected)}"
        )

        return UncertaintyAggregationResult(
            aggregation_id=aggregation_id,
            request_id=request_id,
            recommendation=recommendation,
            overall_heuristic_score=score,
            is_sufficient=is_sufficient,
            abstention_recommended=abstention_recommended,
            primary_reason_code=primary_reason,
            contributing_reason_codes=tuple(contributing_reasons),
            justification=justification,
            signals=signals,
            confidence_is_calibrated=False,
        )


def _stable_id(*parts: str) -> str:
    """Generate a deterministic, short identifier from component parts."""
    raw = "|".join(parts)
    return "agg_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
