"""Provider-neutral specialist role contracts and deterministic fake specialists.

This module defines:
  - Role specification dataclasses describing the narrow responsibility, permitted input,
    required evidence references, output contract, uncertainty behaviour, abstention
    conditions, prohibited actions, and validation rules for each specialist.
  - Deterministic fake specialist implementations suitable for offline unit testing.
    The fakes are fixture-driven, repeatable for identical inputs, and never perform
    network requests, target dispatch, scanning, or exploit execution.

Passing the deterministic fake specialists does NOT demonstrate real-world vulnerability
detection accuracy.  Role definitions are analytical hypotheses only; factual support
remains strictly 'not_evaluated'.

No external LLM providers, no API keys, no LangGraph / CrewAI / AutoGen, no
network egress.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Literal, Protocol, Sequence

from aegiscore.generation import GeneratedClaim, GenerationContractError
from aegiscore.orchestration import (
    AgentExecutionRecord,
    ClaimCitationRecord,
    ConflictAssessment,
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    SpecialistFinding,
    UncertaintyAssessment,
)
from aegiscore.rag import CitationReference, RagContractError, SourceChunk, _nonempty_text


# ---------------------------------------------------------------------------
# Role Identifiers
# ---------------------------------------------------------------------------

ROLE_XSS_ANALYST = "vulnerability_specialist:xss"
ROLE_SQLI_ANALYST = "vulnerability_specialist:sqli"
ROLE_BAC_ANALYST = "vulnerability_specialist:bac"
ROLE_EVIDENCE_REVIEWER = "evidence_review_specialist"
ROLE_UNCERTAINTY_ASSESSOR = "uncertainty_conflict_assessor"

_VALID_ROLES: frozenset[str] = frozenset({
    ROLE_XSS_ANALYST,
    ROLE_SQLI_ANALYST,
    ROLE_BAC_ANALYST,
    ROLE_EVIDENCE_REVIEWER,
    ROLE_UNCERTAINTY_ASSESSOR,
})

# Epistemic uncertainty keywords used by the fake uncertainty assessor
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

# Conflict marker pairs for each category
_XSS_CONFLICT_MARKERS: tuple[tuple[str, str], ...] = (
    ("htmlspecialchars", "reflected without encoding"),
    ("csp header present", "no content-security-policy"),
    ("input sanitized", "raw html output"),
)
_SQLI_CONFLICT_MARKERS: tuple[tuple[str, str], ...] = (
    ("prepared statement", "raw sql concatenation"),
    ("parameterized query", "string interpolation"),
    ("orm used", "direct query construction"),
)
_BAC_CONFLICT_MARKERS: tuple[tuple[str, str], ...] = (
    ("authorization check present", "no authorization check"),
    ("role validation enforced", "role not verified"),
)

# Minimum required chunk count for sufficient evidence
_MIN_SUFFICIENT_CHUNKS = 1


# ---------------------------------------------------------------------------
# Role Specification Contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Provider-neutral specification for one specialist role.

    Defines the narrow responsibility and behavioral constraints.  This is a
    specification document, not a trust boundary; critical constraints are
    enforced in deterministic code, not in prompts.
    """

    role_id: str
    display_name: str
    responsibility: str
    permitted_categories: tuple[str, ...]
    cwe_ids: tuple[str, ...]
    output_contract_summary: str
    uncertainty_behavior: str
    abstention_conditions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.role_id, "role_id")
            _nonempty_text(self.display_name, "display_name")
            _nonempty_text(self.responsibility, "responsibility")
            _nonempty_text(self.output_contract_summary, "output_contract_summary")
            _nonempty_text(self.uncertainty_behavior, "uncertainty_behavior")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc
        if self.role_id not in _VALID_ROLES:
            raise OrchestrationContractError(
                f"role_id '{self.role_id}' is not a recognised specialist role"
            )
        if not isinstance(self.permitted_categories, tuple):
            raise OrchestrationContractError("permitted_categories must be a tuple")
        if not isinstance(self.abstention_conditions, tuple) or len(self.abstention_conditions) == 0:
            raise OrchestrationContractError("abstention_conditions must be a non-empty tuple")
        if not isinstance(self.prohibited_actions, tuple) or len(self.prohibited_actions) == 0:
            raise OrchestrationContractError("prohibited_actions must be a non-empty tuple")


# ---------------------------------------------------------------------------
# Standard Role Specifications
# ---------------------------------------------------------------------------

XSS_ANALYST_SPEC = RoleSpec(
    role_id=ROLE_XSS_ANALYST,
    display_name="XSS Vulnerability Analyst",
    responsibility=(
        "Analyse retrieved evidence for Cross-Site Scripting (Reflected and Stored) "
        "indicators.  Identify unencoded user-controlled input reaching HTML output, "
        "DOM sinks, or event handlers.  Produce candidate claims with citation references. "
        "This role does NOT confirm vulnerabilities; it proposes hypotheses for review."
    ),
    permitted_categories=("XSS", "GENERAL"),
    cwe_ids=("CWE-79",),
    output_contract_summary=(
        "SpecialistFinding with vulnerability_identified bool, FindingSeverity, "
        "one or more GeneratedClaim each citing retrieved chunks, "
        "factual_support='not_evaluated', is_confirmed=False."
    ),
    uncertainty_behavior=(
        "If retrieved evidence is ambiguous or uses epistemic keywords such as 'unclear', "
        "'possible', or 'may be', set uncertainty_detected=True in the reasoning_notes and "
        "recommend abstention.  Do not claim HIGH/CRITICAL severity without explicit "
        "unencoded sink evidence."
    ),
    abstention_conditions=(
        "No retrieved chunks reference HTML output or user-controlled input.",
        "Evidence contains sanitization markers (htmlspecialchars, encodeURIComponent, CSP) "
        "without corresponding bypass evidence.",
        "Evidence is flagged [INSUFFICIENT_EVIDENCE].",
        "Fewer than one approved chunk is available.",
    ),
    prohibited_actions=(
        "Claiming semantic entailment is verified.",
        "Marking finding as is_confirmed=True.",
        "Performing HTTP requests or DOM interaction.",
        "Executing JavaScript or generating payloads for active dispatch.",
        "Approving source corpus entries.",
        "Mutating state machine transitions directly.",
    ),
)

SQLI_ANALYST_SPEC = RoleSpec(
    role_id=ROLE_SQLI_ANALYST,
    display_name="SQL Injection Analyst",
    responsibility=(
        "Analyse retrieved evidence for SQL Injection indicators.  Identify raw SQL "
        "string concatenation with user-controlled values, absence of parameterised "
        "queries or ORM abstraction, and error messages exposing DB structure.  "
        "Produce candidate claims with citation references. "
        "This role does NOT confirm vulnerabilities."
    ),
    permitted_categories=("SQLI", "GENERAL"),
    cwe_ids=("CWE-89",),
    output_contract_summary=(
        "SpecialistFinding with vulnerability_identified bool, FindingSeverity, "
        "one or more GeneratedClaim each citing retrieved chunks, "
        "factual_support='not_evaluated', is_confirmed=False."
    ),
    uncertainty_behavior=(
        "If evidence shows both parameterised and non-parameterised paths, flag conflict. "
        "If evidence contains epistemic markers, abstract to lower confidence and recommend "
        "abstention rather than claiming HIGH severity."
    ),
    abstention_conditions=(
        "No retrieved chunks reference SQL queries, database calls, or query construction.",
        "Evidence explicitly shows prepared statements or ORM wrappers without bypass path.",
        "Evidence is flagged [INSUFFICIENT_EVIDENCE].",
        "Fewer than one approved chunk is available.",
    ),
    prohibited_actions=(
        "Claiming semantic entailment is verified.",
        "Marking finding as is_confirmed=True.",
        "Generating SQL payloads for active dispatch.",
        "Performing live database queries.",
        "Approving source corpus entries.",
    ),
)

BAC_ANALYST_SPEC = RoleSpec(
    role_id=ROLE_BAC_ANALYST,
    display_name="Broken Access Control Analyst",
    responsibility=(
        "Analyse retrieved evidence for Broken Access Control indicators.  Identify "
        "missing or bypassable authorisation checks, IDOR patterns, privilege escalation "
        "paths, and insecure direct object references.  "
        "Produce candidate claims with citation references. "
        "This role does NOT confirm vulnerabilities."
    ),
    permitted_categories=("BAC", "GENERAL"),
    cwe_ids=("CWE-284", "CWE-639"),
    output_contract_summary=(
        "SpecialistFinding with vulnerability_identified bool, FindingSeverity, "
        "one or more GeneratedClaim each citing retrieved chunks, "
        "factual_support='not_evaluated', is_confirmed=False."
    ),
    uncertainty_behavior=(
        "If evidence shows authorisation checks present without complete bypass evidence, "
        "recommend abstention.  Use LOW/MEDIUM severity when authorisation logic is partially "
        "visible but bypass path is unclear."
    ),
    abstention_conditions=(
        "No retrieved chunks reference access control, authorisation, or object reference.",
        "Evidence explicitly shows proper RBAC or authorisation checks without bypass.",
        "Evidence is flagged [INSUFFICIENT_EVIDENCE].",
        "Fewer than one approved chunk is available.",
    ),
    prohibited_actions=(
        "Claiming semantic entailment is verified.",
        "Marking finding as is_confirmed=True.",
        "Dispatching authenticated requests or privilege-escalation probes.",
        "Approving source corpus entries.",
    ),
)

EVIDENCE_REVIEWER_SPEC = RoleSpec(
    role_id=ROLE_EVIDENCE_REVIEWER,
    display_name="Adversarial Evidence Reviewer",
    responsibility=(
        "Independently challenge the specialist finding by looking for benign explanations, "
        "sanitization present, proper encoding, authorisation guards, alternative "
        "interpretations, and unsupported generalisations.  "
        "Emit conflict markers when specialist and evidence disagree.  "
        "Does not re-confirm findings."
    ),
    permitted_categories=("XSS", "SQLI", "BAC", "GENERAL"),
    cwe_ids=(),
    output_contract_summary=(
        "Review notes string with challenge annotations and optional conflict markers. "
        "The reviewer does not emit a SpecialistFinding and cannot approve findings."
    ),
    uncertainty_behavior=(
        "Explicitly note when evidence is ambiguous or when the specialist's claim is "
        "unsupported by the retrieved text.  Flag disagreement as a conflict marker."
    ),
    abstention_conditions=(
        "Finding is already abstained; no review is needed.",
        "Evidence bundle is empty.",
    ),
    prohibited_actions=(
        "Approving or confirming findings.",
        "Claiming semantic entailment.",
        "Performing network requests.",
        "Mutating state machine transitions.",
    ),
)

UNCERTAINTY_ASSESSOR_SPEC = RoleSpec(
    role_id=ROLE_UNCERTAINTY_ASSESSOR,
    display_name="Uncertainty and Conflict Assessor",
    responsibility=(
        "Deterministically compute evidence sufficiency score, detect epistemic uncertainty "
        "keywords, and evaluate explicit conflict markers between the specialist finding "
        "and the evidence review.  Emit UncertaintyAssessment and ConflictAssessment. "
        "Does NOT perform semantic entailment checking."
    ),
    permitted_categories=("XSS", "SQLI", "BAC", "GENERAL"),
    cwe_ids=(),
    output_contract_summary=(
        "UncertaintyAssessment + ConflictAssessment pair. "
        "confidence_is_calibrated=False always. "
        "semantic_contradiction_detected='not_evaluated' always."
    ),
    uncertainty_behavior=(
        "Score = approved_chunk_count / max(approved_chunk_count, 1) weighted by "
        "epistemic_keyword_absence.  If any epistemic keyword present, is_sufficient=False."
    ),
    abstention_conditions=(
        "Evidence bundle is empty (approved_source_count == 0).",
        "Epistemic uncertainty keywords detected in finding or review notes.",
        "Explicit conflict markers detected.",
    ),
    prohibited_actions=(
        "Claiming to resolve semantic contradictions.",
        "Performing network requests.",
        "Marking confidence_is_calibrated=True.",
    ),
)

# Registry for lookup by role_id
ROLE_REGISTRY: dict[str, RoleSpec] = {
    spec.role_id: spec
    for spec in (
        XSS_ANALYST_SPEC,
        SQLI_ANALYST_SPEC,
        BAC_ANALYST_SPEC,
        EVIDENCE_REVIEWER_SPEC,
        UNCERTAINTY_ASSESSOR_SPEC,
    )
}


def get_role_spec(role_id: str) -> RoleSpec:
    """Return the RoleSpec for the given role_id or raise OrchestrationContractError."""
    try:
        spec = ROLE_REGISTRY.get(role_id)
    except Exception as exc:
        raise OrchestrationContractError(f"Role lookup failed: {exc}") from exc
    if spec is None:
        raise OrchestrationContractError(f"No role specification found for role_id '{role_id}'")
    return spec


# ---------------------------------------------------------------------------
# Specialist Protocol
# ---------------------------------------------------------------------------

class VulnerabilityAnalystFakeProtocol(Protocol):
    """Provider-neutral interface for a deterministic vulnerability analyst fake."""

    def analyse(
        self,
        request_id: str,
        bundle: EvidenceBundle,
    ) -> SpecialistFinding:
        """Produce a deterministic SpecialistFinding from the supplied evidence bundle."""
        ...


class EvidenceReviewerFakeProtocol(Protocol):
    """Provider-neutral interface for a deterministic evidence reviewer fake."""

    def review(
        self,
        finding: SpecialistFinding,
        bundle: EvidenceBundle,
    ) -> str:
        """Return review notes string challenging or annotating the candidate finding."""
        ...


class UncertaintyAssessorFakeProtocol(Protocol):
    """Provider-neutral interface for a deterministic uncertainty/conflict assessor fake."""

    def assess(
        self,
        request_id: str,
        finding: SpecialistFinding,
        review_notes: str,
        bundle: EvidenceBundle,
    ) -> tuple[UncertaintyAssessment, ConflictAssessment]:
        """Deterministically compute UncertaintyAssessment and ConflictAssessment."""
        ...


# ---------------------------------------------------------------------------
# Deterministic Fake Implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixturedSpecialistOutput:
    """Explicit fixture for one deterministic fake output.

    Preferred over keyword heuristics for test stability.
    When canned_finding is None, the fake uses its default logic.
    """

    vulnerability_identified: bool = False
    severity: FindingSeverity = FindingSeverity.INFO
    summary: str = "Deterministic fake analysis: no vulnerability detected."
    cwe_id: str | None = None
    reasoning_notes: str = "Fixture-driven output; not a real LLM analysis."


class DeterministicVulnerabilityAnalystFake:
    """Deterministic vulnerability analyst fake for offline testing.

    Returns a predefined finding fixture for fixture-driven test scenarios or,
    when no fixture is supplied, derives a minimal finding from the evidence bundle.

    Is deterministic: identical inputs yield identical outputs.
    Never claims semantic entailment is verified.
    Never performs network I/O, target dispatch, or exploit execution.
    """

    def __init__(
        self,
        role_id: str,
        *,
        fixture: FixturedSpecialistOutput | None = None,
    ) -> None:
        if role_id not in (ROLE_XSS_ANALYST, ROLE_SQLI_ANALYST, ROLE_BAC_ANALYST):
            raise OrchestrationContractError(
                f"DeterministicVulnerabilityAnalystFake requires an analyst role_id, got '{role_id}'"
            )
        self._role_id = role_id
        self._fixture = fixture

    @property
    def role_id(self) -> str:
        return self._role_id

    def analyse(self, request_id: str, bundle: EvidenceBundle) -> SpecialistFinding:
        """Produce a deterministic SpecialistFinding from the supplied evidence bundle."""
        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")
        try:
            _nonempty_text(request_id, "request_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        # Fail-closed: no evidence means no finding with vulnerability_identified=True
        if bundle.approved_source_count == 0 or len(bundle.chunks) == 0:
            finding_id = _stable_id("finding", request_id, self._role_id, "no_evidence")
            return SpecialistFinding(
                finding_id=finding_id,
                request_id=request_id,
                specialist_role=self._role_id,
                vulnerability_identified=False,
                severity=FindingSeverity.INFO,
                summary="No approved evidence available; abstaining.",
                proposed_claims=(),
                reasoning_notes="Empty evidence bundle; no analysis performed.",
            )

        fixture = self._fixture
        finding_id = _stable_id("finding", request_id, self._role_id, bundle.bundle_id)

        if fixture is not None:
            # Fixture-driven path: build claims from first chunk if vulnerability claimed
            if fixture.vulnerability_identified and len(bundle.chunks) > 0:
                chunk = bundle.chunks[0]
                ref = CitationReference(
                    source_id=chunk.provenance.source_id,
                    chunk_id=chunk.chunk_id,
                )
                claim = GeneratedClaim(
                    text=f"[{self._role_id}] Fixture finding: {fixture.summary}",
                    citations=(ref,),
                )
                raw_excerpt = chunk.content[:80] if len(chunk.content) >= 80 else chunk.content
                safe_excerpt = raw_excerpt.replace("\x00", "")
                citation_record = ClaimCitationRecord(
                    claim_id=_stable_id("claim", request_id, chunk.chunk_id),
                    citation=ref,
                    cited_excerpt=safe_excerpt if safe_excerpt.strip() else None,
                )
                return SpecialistFinding(
                    finding_id=finding_id,
                    request_id=request_id,
                    specialist_role=self._role_id,
                    vulnerability_identified=True,
                    severity=fixture.severity,
                    summary=fixture.summary,
                    proposed_claims=(claim,),
                    cwe_id=fixture.cwe_id,
                    claim_citations=(citation_record,),
                    reasoning_notes=fixture.reasoning_notes,
                )
            else:
                # No vulnerability: produce clean finding with no claims
                return SpecialistFinding(
                    finding_id=finding_id,
                    request_id=request_id,
                    specialist_role=self._role_id,
                    vulnerability_identified=False,
                    severity=fixture.severity,
                    summary=fixture.summary,
                    proposed_claims=(),
                    cwe_id=fixture.cwe_id,
                    reasoning_notes=fixture.reasoning_notes,
                )

        # Default evidence-derived path (no fixture)
        # Build one claim per chunk using provenance reference
        claims: list[GeneratedClaim] = []
        citation_records: list[ClaimCitationRecord] = []
        for chunk in bundle.chunks:
            ref = CitationReference(
                source_id=chunk.provenance.source_id,
                chunk_id=chunk.chunk_id,
            )
            claim = GeneratedClaim(
                text=f"[{self._role_id}] Retrieved evidence documents security-relevant content.",
                citations=(ref,),
            )
            claims.append(claim)
            raw_excerpt = chunk.content[:60] if len(chunk.content) >= 60 else chunk.content
            safe_excerpt = raw_excerpt.replace("\x00", "")
            citation_records.append(
                ClaimCitationRecord(
                    claim_id=_stable_id("claim", request_id, chunk.chunk_id),
                    citation=ref,
                    cited_excerpt=safe_excerpt if safe_excerpt.strip() else None,
                )
            )

        return SpecialistFinding(
            finding_id=finding_id,
            request_id=request_id,
            specialist_role=self._role_id,
            vulnerability_identified=True,
            severity=FindingSeverity.MEDIUM,
            summary="Evidence-derived candidate finding; human review required.",
            proposed_claims=tuple(claims),
            claim_citations=tuple(citation_records),
            reasoning_notes="Default fake analysis from evidence bundle; not a real LLM.",
        )


class DeterministicEvidenceReviewerFake:
    """Deterministic adversarial evidence reviewer fake.

    Returns predefined review notes string for fixture-driven scenarios.
    Never approves or confirms findings.
    Never performs network I/O.
    """

    def __init__(self, *, canned_notes: str | None = None) -> None:
        if canned_notes is not None:
            try:
                _nonempty_text(canned_notes, "canned_notes")
            except RagContractError as exc:
                raise OrchestrationContractError(str(exc)) from exc
        self._canned_notes = canned_notes

    @property
    def role_id(self) -> str:
        return ROLE_EVIDENCE_REVIEWER

    def review(
        self,
        finding: SpecialistFinding | None,
        bundle: EvidenceBundle,
        *,
        secondary_findings: Sequence[SpecialistFinding] = (),
    ) -> str:
        """Deterministically return challenge review notes for candidate finding(s)."""
        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")

        if self._canned_notes is not None:
            return self._canned_notes

        if finding is None:
            if not secondary_findings:
                return (
                    "REVIEWER [FAKE]: No candidate specialist finding provided. "
                    "CHALLENGE: No finding available for evidence review."
                )
            primary = secondary_findings[0]
            rest_secondaries = tuple(secondary_findings[1:])
        else:
            if not isinstance(finding, SpecialistFinding):
                raise OrchestrationContractError("finding must be a SpecialistFinding instance")
            primary = finding
            rest_secondaries = tuple(secondary_findings)

        all_findings = [primary] + list(rest_secondaries)
        chunk_map = {c.chunk_id: c for c in bundle.chunks}

        def get_source_id(c: SourceChunk) -> str:
            if hasattr(c, "provenance") and hasattr(c.provenance, "source_id"):
                return c.provenance.source_id
            return getattr(c, "source_id", "")

        # 1. Adversarial Citation & Grounding Verification
        for fnd in all_findings:
            # Check claim citations
            for cc in fnd.claim_citations:
                c_id = cc.citation.chunk_id
                if c_id not in chunk_map:
                    return (
                        f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                        f"cites unknown chunk ID '{c_id}' not in evidence bundle."
                    )
                chk = chunk_map[c_id]
                expected_src = get_source_id(chk)
                if cc.citation.source_id != expected_src:
                    return (
                        f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                        f"cites mismatched source ID '{cc.citation.source_id}' (expected '{expected_src}')."
                    )
                if cc.cited_excerpt and cc.cited_excerpt not in chk.content:
                    return (
                        f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                        f"cited excerpt does not appear verbatim in chunk '{c_id}'."
                    )

            # Check proposed claims citations
            for clm in fnd.proposed_claims:
                for ref in clm.citations:
                    if ref.chunk_id not in chunk_map:
                        return (
                            f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                            f"claim references unknown chunk ID '{ref.chunk_id}'."
                        )
                    chk = chunk_map[ref.chunk_id]
                    expected_src = get_source_id(chk)
                    if ref.source_id != expected_src:
                        return (
                            f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                            f"claim references mismatched source ID '{ref.source_id}' (expected '{expected_src}')."
                        )

        # 2. Adversarial Challenge of Unsupported Claims
        for fnd in all_findings:
            if fnd.vulnerability_identified:
                if len(fnd.proposed_claims) == 0:
                    return (
                        f"STATUS: REJECT - REVIEWER REJECTION: Specialist '{fnd.specialist_role}' "
                        "asserts vulnerability but proposes zero claims."
                    )
                for clm in fnd.proposed_claims:
                    if len(clm.citations) == 0:
                        return (
                            f"CHALLENGE: Specialist '{fnd.specialist_role}' claim '{clm.text[:40]}' "
                            "has zero citations; claim is unsupported by evidence."
                        )
                    if any(term in clm.text.lower() for term in ("[unsupported]", "unsupported_claim", "automatically sanitize")):
                        return (
                            f"CHALLENGE: Specialist '{fnd.specialist_role}' asserts unsupported claim "
                            f"'{clm.text[:40]}'. Evidentiary backing is absent."
                        )

        # Check for explicit insufficiency markers in evidence
        if any("[INSUFFICIENT_EVIDENCE]" in c.content for c in bundle.chunks):
            return (
                "CHALLENGE: Evidence bundle contains explicit [INSUFFICIENT_EVIDENCE] marker. "
                "Claims cannot be substantiated."
            )

        # 3. Conflicting Specialist Conclusions
        if len(all_findings) >= 2:
            vuln_flags = [f.vulnerability_identified for f in all_findings]
            if len(set(vuln_flags)) > 1:
                roles = [f.specialist_role for f in all_findings]
                return (
                    f"REVIEWER [FAKE]: Specialist conclusions disagree across roles: {roles}. "
                    "CHALLENGE: One or more specialists do not find an evidence-supported vulnerability. "
                    "CONFLICT_MARKER: specialist_findings_disagreement."
                )

        # 4. Check if finding reports no vulnerability
        if not any(f.vulnerability_identified for f in all_findings):
            return (
                "REVIEWER [FAKE]: Specialist reports no vulnerability. "
                "No challenge raised. Finding may proceed to uncertainty assessment."
            )

        # 5. Check if any chunk text contains sanitization / mitigation markers
        sanitization_terms = (
            "htmlspecialchars", "encodeURIComponent", "prepared statement",
            "parameterized", "htmlentities", "sanitize", "escape",
        )
        sanitation_found = any(
            any(term in chunk.content.lower() for term in sanitization_terms)
            for chunk in bundle.chunks
        )

        if sanitation_found:
            return (
                "REVIEWER [FAKE]: Evidence contains sanitization or encoding markers. "
                "CHALLENGE: The proposed vulnerability may be mitigated. "
                "CONFLICT_MARKER: sanitization_present vs vulnerability_claimed."
            )

        return (
            "REVIEWER [FAKE]: Evidence verified and citations grounded. "
            "No definitive conflict or mitigation detected by deterministic reviewer."
        )


class DeterministicUncertaintyAssessorFake:
    """Deterministic uncertainty and conflict assessor fake.

    Uses explicit rules to compute sufficiency score and detect epistemic keywords
    and conflict markers.  Does NOT interpret confidence scores as calibrated.
    Does NOT claim to resolve semantic contradictions.
    """

    def __init__(
        self,
        *,
        force_sufficient: bool | None = None,
        force_conflict: bool | None = None,
        conflict_markers: tuple[str, ...] | None = None,
    ) -> None:
        """
        Args:
            force_sufficient: if set, overrides the derived sufficiency result.
            force_conflict: if set, overrides conflict detection.
            conflict_markers: if set, used as explicit conflict markers.
        """
        self._force_sufficient = force_sufficient
        self._force_conflict = force_conflict
        self._forced_conflict_markers = conflict_markers or ()

    def assess(
        self,
        request_id: str,
        finding: SpecialistFinding,
        review_notes: str,
        bundle: EvidenceBundle,
    ) -> tuple[UncertaintyAssessment, ConflictAssessment]:
        """Deterministically compute UncertaintyAssessment and ConflictAssessment."""
        if not isinstance(finding, SpecialistFinding):
            raise OrchestrationContractError("finding must be a SpecialistFinding instance")
        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")
        try:
            _nonempty_text(request_id, "request_id")
            # review_notes may contain newlines from reviewer output; validate the stripped summary
            _nonempty_text(review_notes.replace("\n", " ").replace("\r", " "), "review_notes")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        assessment_id = _stable_id("ua", request_id, finding.finding_id)
        conflict_id = _stable_id("ca", request_id, finding.finding_id)

        # --- Epistemic uncertainty detection ---
        combined_text = (
            finding.summary + " " +
            finding.reasoning_notes + " " +
            review_notes
        ).lower()
        detected_keywords = tuple(
            kw for kw in _EPISTEMIC_KEYWORDS if kw in combined_text
        )
        epistemic_detected = len(detected_keywords) > 0

        # --- Evidence sufficiency score ---
        chunk_count = len(bundle.chunks)
        if chunk_count == 0:
            raw_score = 0.0
        elif chunk_count >= _MIN_SUFFICIENT_CHUNKS:
            raw_score = 1.0 if not epistemic_detected else 0.4
        else:
            raw_score = 0.0
        score = float(self._force_sufficient is None and raw_score or (
            1.0 if self._force_sufficient else 0.0
        ) if self._force_sufficient is not None else raw_score)

        is_sufficient = (score >= 0.5) if self._force_sufficient is None else self._force_sufficient
        abstention_recommended = not is_sufficient

        justification = (
            f"chunk_count={chunk_count}, epistemic_keywords={list(detected_keywords)}, "
            f"score={score:.2f}, sufficient={is_sufficient}"
        )

        uncertainty = UncertaintyAssessment(
            assessment_id=assessment_id,
            request_id=request_id,
            epistemic_uncertainty_detected=epistemic_detected,
            uncertainty_keywords=detected_keywords,
            evidence_sufficiency_score=score,
            is_sufficient=is_sufficient,
            abstention_recommended=abstention_recommended,
            justification=justification,
            confidence_is_calibrated=False,
        )

        # --- Conflict detection ---
        conflicts_detected: bool
        conflict_markers_out: tuple[str, ...]
        if self._force_conflict is not None:
            conflicts_detected = self._force_conflict
            conflict_markers_out = (
                self._forced_conflict_markers
                if self._force_conflict
                else ()
            )
        else:
            # Detect conflict markers in review notes text
            detected_markers: list[str] = []
            if "CONFLICT_MARKER:" in review_notes:
                # Extract markers following the CONFLICT_MARKER: prefix
                for line in review_notes.split("\n"):
                    if "CONFLICT_MARKER:" in line:
                        marker = line.split("CONFLICT_MARKER:")[-1].strip(" .")
                        if marker:
                            detected_markers.append(marker)
            conflicts_detected = len(detected_markers) > 0
            conflict_markers_out = tuple(detected_markers)

        resolution = "none"
        if conflicts_detected:
            resolution = "fail_closed_abstain"

        conflict = ConflictAssessment(
            conflict_id=conflict_id,
            request_id=request_id,
            conflicts_detected=conflicts_detected,
            conflict_markers=conflict_markers_out,
            opposing_roles=(finding.specialist_role, ROLE_EVIDENCE_REVIEWER) if conflicts_detected else (),
            resolution_strategy=resolution,
            conflict_summary=(
                f"Deterministic fake assessor. Markers: {list(conflict_markers_out)}"
                if conflicts_detected else "No explicit conflict markers detected."
            ),
            semantic_contradiction_detected="not_evaluated",
        )

        return uncertainty, conflict


# ---------------------------------------------------------------------------
# AgentExecutionRecord builder helper
# ---------------------------------------------------------------------------

def build_execution_record(
    request_id: str,
    agent_role: str,
    output_summary: str,
    *,
    input_tokens_est: int = 0,
    output_tokens_est: int = 0,
    latency_ms: float = 0.0,
    parsed_successfully: bool = True,
    error_message: str | None = None,
) -> AgentExecutionRecord:
    """Construct an AgentExecutionRecord for a deterministic fake specialist invocation."""
    execution_id = _stable_id("exec", request_id, agent_role)
    prompt_hash = hashlib.sha256(
        f"fake_prompt_template:{agent_role}".encode("utf-8")
    ).hexdigest()
    return AgentExecutionRecord(
        execution_id=execution_id,
        request_id=request_id,
        agent_role=agent_role,
        model_identifier="DeterministicFakeSpecialist",
        prompt_template_hash=prompt_hash,
        input_tokens_est=input_tokens_est,
        output_tokens_est=output_tokens_est,
        latency_ms=latency_ms,
        parsed_successfully=parsed_successfully,
        output_summary=output_summary,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stable_id(*parts: str) -> str:
    """Produce a stable short identifier from component strings."""
    raw = "|".join(parts)
    return "fake_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

