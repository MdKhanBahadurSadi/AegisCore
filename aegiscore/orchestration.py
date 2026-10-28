"""Typed multi-agent data contracts and deterministic orchestration state machine.

This module provides the typed contract foundation and deterministic orchestration state
machine for AEGISCORE AI specialist agents, bridging offline RAG retrieval, specialist
vulnerability analysis, independent adversarial evidence review, uncertainty assessment,
and fail-closed response gating.

It operates entirely offline with zero external dependencies, no API keys, and no
external LLM calls. All transitions are explicit, validated, and fail-closed.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Literal, Mapping, Sequence
from urllib.parse import urlsplit

from aegiscore.claim_validation import (
    ClaimValidationResult,
    EvidenceSufficiencyClassification,
    GatedGenerationResult,
    validate_citation_excerpt,
)
from aegiscore.generation import (
    GeneratedClaim,
    GenerationContractError,
    GenerationError,
    GenerationResult,
)
from aegiscore.rag import (
    CitationReference,
    RagContractError,
    SourceChunk,
    _nonempty_text,
)
from aegiscore.rag_runtime import EvidenceRetrievalResult


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------


class OrchestrationError(Exception):
    """Base exception for all orchestration errors."""


class OrchestrationContractError(OrchestrationError):
    """An orchestration request, evidence bundle, or finding violates contractual invariants."""


class ScopeViolationError(OrchestrationContractError):
    """A target URL, hostname, or path violates authorized scope boundaries."""


class InvalidTransitionError(OrchestrationContractError):
    """Attempted an invalid or forbidden state transition in the orchestration state machine."""


class TerminalStateError(InvalidTransitionError):
    """Attempted to transition out of a terminal state."""


class StageBypassError(InvalidTransitionError):
    """Attempted to finalize a workflow without completing required prerequisite validation stages."""


# ---------------------------------------------------------------------------
# Scope Validation Helpers
# ---------------------------------------------------------------------------

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)
_SENSITIVE_PATTERNS = (
    re.compile(r"bearer\s+[a-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"]?[a-z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*['\"]?[^\s'\"]{4,}", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*basic\s+[a-z0-9+/=]{8,}", re.IGNORECASE),
)


def _validate_lab_target_url(url: str) -> None:
    """Validate that target URL belongs strictly to local loopback or RFC1918 private lab space."""
    if not isinstance(url, str) or not url.strip():
        raise ScopeViolationError("target_url must be non-empty trimmed text")
    if url != url.strip():
        raise ScopeViolationError("target_url contains un-trimmed leading/trailing whitespace")

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ScopeViolationError(f"target_url scheme '{parsed.scheme}' is not permitted; must be http or https")
    if parsed.username or parsed.password:
        raise ScopeViolationError("target_url must not contain embedded user credentials")
    if parsed.fragment:
        raise ScopeViolationError("target_url must not contain URL fragments")

    hostname = parsed.hostname
    if not hostname:
        raise ScopeViolationError("target_url must contain a valid hostname or IP address")

    hostname = hostname.lower()
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            return
        if any(ip.version == net.version and ip in net for net in _PRIVATE_NETWORKS):
            return
        raise ScopeViolationError(
            f"target_url IP '{hostname}' is not an authorized private (RFC1918) or loopback lab address"
        )
    except ValueError:
        if hostname == "localhost":
            return
        labels = hostname.split(".")
        if any(_DNS_LABEL.fullmatch(label) is None for label in labels):
            raise ScopeViolationError(f"target_url hostname '{hostname}' is non-canonical or invalid")
        if not hostname.endswith(".local") and not hostname.endswith(".internal"):
            raise ScopeViolationError(
                f"target_url hostname '{hostname}' is not an authorized internal lab domain (*.local, *.internal, localhost)"
            )


# ---------------------------------------------------------------------------
# Enums and Types
# ---------------------------------------------------------------------------

AnalysisMode = Literal["passive_rag_only", "active_guarded"]


class FindingSeverity(str, Enum):
    """Standardized finding severity ratings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GatingDecision(str, Enum):
    """Terminal response gating outcome."""

    PROCEED = "proceed"
    ABSTAIN = "abstain"
    FLAG_FOR_REVIEW = "flag_for_review"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssessmentRequest:
    """Authorized assessment request contract.

    Caller-supplied strings are not treated as proof of authorization. The URL must
    satisfy lab target constraints and active execution requires an explicit permit.
    """

    request_id: str
    target_url: str
    vulnerability_category: str
    authorized_scope: tuple[str, ...]
    analysis_mode: AnalysisMode = "passive_rag_only"
    permit_id: str | None = None
    created_at_utc: str = ""

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.vulnerability_category, "vulnerability_category")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        _validate_lab_target_url(self.target_url)

        if not isinstance(self.authorized_scope, tuple):
            raise OrchestrationContractError("authorized_scope must be a tuple of allowed path prefixes")
        if len(self.authorized_scope) == 0:
            raise OrchestrationContractError("authorized_scope must not be empty")
        for path in self.authorized_scope:
            if not isinstance(path, str) or not path.startswith("/"):
                raise ScopeViolationError(f"authorized_scope entry '{path}' must be an absolute path starting with '/'")

        if self.analysis_mode not in ("passive_rag_only", "active_guarded"):
            raise OrchestrationContractError(f"analysis_mode '{self.analysis_mode}' is not recognized")

        if self.analysis_mode == "active_guarded":
            if not self.permit_id or not isinstance(self.permit_id, str) or not self.permit_id.strip():
                raise OrchestrationContractError("active_guarded analysis requires a non-empty permit_id")


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Structured evidence bundle for multi-agent specialist analysis.

    All retrieved chunks are treated strictly as passive, untrusted data. Content
    inside chunks cannot mutate state machine transitions or system policies.
    """

    bundle_id: str
    request_id: str
    retrieval_query: str
    chunks: tuple[SourceChunk, ...]
    citations: tuple[CitationReference, ...]
    manifest_fingerprint: str
    approved_source_count: int
    retrieval_timestamp_utc: str = ""
    evidence_status: Literal["evidence_found", "no_approved_evidence"] = "evidence_found"

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.bundle_id, "bundle_id")
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.retrieval_query, "retrieval_query")
            _nonempty_text(self.manifest_fingerprint, "manifest_fingerprint")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.chunks, tuple):
            raise OrchestrationContractError("chunks must be a tuple of SourceChunk instances")
        if not isinstance(self.citations, tuple):
            raise OrchestrationContractError("citations must be a tuple of CitationReference instances")

        for c in self.chunks:
            if not isinstance(c, SourceChunk):
                raise OrchestrationContractError("chunks must contain only SourceChunk instances")
        for ref in self.citations:
            if not isinstance(ref, CitationReference):
                raise OrchestrationContractError("citations must contain only CitationReference instances")

        if isinstance(self.approved_source_count, bool) or not isinstance(self.approved_source_count, int) or self.approved_source_count < 0:
            raise OrchestrationContractError("approved_source_count must be a non-negative integer")

        if self.approved_source_count == 0:
            if len(self.chunks) > 0 or len(self.citations) > 0:
                raise OrchestrationContractError("evidence bundle cannot contain chunks or citations when approved_source_count is 0")
            if self.evidence_status != "no_approved_evidence":
                raise OrchestrationContractError("evidence_status must be 'no_approved_evidence' when approved_source_count is 0")

        # Provenance integrity: each CitationReference must match an existing chunk
        def get_source_id(c: SourceChunk) -> str:
            if hasattr(c, "provenance") and hasattr(c.provenance, "source_id"):
                return c.provenance.source_id
            return getattr(c, "source_id", "")

        chunk_keys = {(get_source_id(c), c.chunk_id) for c in self.chunks}
        for ref in self.citations:
            if (ref.source_id, ref.chunk_id) not in chunk_keys:
                raise OrchestrationContractError(
                    f"citation reference ({ref.source_id}, {ref.chunk_id}) does not match any chunk in evidence bundle"
                )

    @classmethod
    def from_retrieval_result(
        cls,
        bundle_id: str,
        request_id: str,
        result: EvidenceRetrievalResult,
        manifest_fingerprint: str,
        retrieval_timestamp_utc: str = "",
    ) -> EvidenceBundle:
        """Construct an EvidenceBundle from a completed EvidenceRetrievalResult."""
        if not isinstance(result, EvidenceRetrievalResult):
            raise OrchestrationContractError("result must be an EvidenceRetrievalResult instance")
        chunks = tuple(hit.chunk for hit in result.retrieval_result.hits)
        return cls(
            bundle_id=bundle_id,
            request_id=request_id,
            retrieval_query=result.query_text,
            chunks=chunks,
            citations=result.citations,
            manifest_fingerprint=manifest_fingerprint,
            approved_source_count=result.approved_source_count,
            retrieval_timestamp_utc=retrieval_timestamp_utc,
            evidence_status=result.status,
        )


@dataclass(frozen=True, slots=True)
class ClaimCitationRecord:
    """Explicit claim-to-chunk provenance association.

    Citation association confirms structural provenance only; factual support
    remains strictly 'not_evaluated' and does not claim semantic entailment.
    """

    claim_id: str
    citation: CitationReference
    cited_excerpt: str | None = None
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.claim_id, "claim_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.citation, CitationReference):
            raise OrchestrationContractError("citation must be a CitationReference instance")
        if self.cited_excerpt is not None:
            if not isinstance(self.cited_excerpt, str) or not self.cited_excerpt.strip():
                raise OrchestrationContractError("cited_excerpt must be a non-empty string")
            if "\x00" in self.cited_excerpt:
                raise OrchestrationContractError("cited_excerpt contains a forbidden null character")

        if self.factual_support != "not_evaluated":
            raise OrchestrationContractError("factual_support must be 'not_evaluated'")


@dataclass(frozen=True, slots=True)
class SpecialistFinding:
    """Proposed vulnerability finding emitted by a specialist role.

    A SpecialistFinding represents an analytical hypothesis, NOT a confirmed
    vulnerability. is_confirmed is always False and factual_support is 'not_evaluated'.
    """

    finding_id: str
    request_id: str
    specialist_role: str
    vulnerability_identified: bool
    severity: FindingSeverity
    summary: str
    proposed_claims: tuple[GeneratedClaim, ...]
    cwe_id: str | None = None
    claim_citations: tuple[ClaimCitationRecord, ...] = ()
    reasoning_notes: str = ""
    is_confirmed: Literal[False] = False
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.finding_id, "finding_id")
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.specialist_role, "specialist_role")
            _nonempty_text(self.summary, "summary")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.severity, FindingSeverity):
            raise OrchestrationContractError("severity must be a FindingSeverity enum instance")
        if not isinstance(self.proposed_claims, tuple):
            raise OrchestrationContractError("proposed_claims must be a tuple of GeneratedClaim instances")
        for claim in self.proposed_claims:
            if not isinstance(claim, GeneratedClaim):
                raise OrchestrationContractError("proposed_claims must contain only GeneratedClaim instances")

        if self.vulnerability_identified and len(self.proposed_claims) == 0:
            raise OrchestrationContractError("vulnerability_identified is True but proposed_claims is empty")

        if self.is_confirmed is not False:
            raise OrchestrationContractError("specialist finding is a proposed finding and cannot be marked confirmed")
        if self.factual_support != "not_evaluated":
            raise OrchestrationContractError("factual_support must be 'not_evaluated'")


@dataclass(frozen=True, slots=True)
class UncertaintyAssessment:
    """Assessment of evidence sufficiency and epistemic ambiguity.

    Model confidence scores are not interpreted as calibrated probabilities.
    confidence_is_calibrated is strictly False.
    """

    assessment_id: str
    request_id: str
    epistemic_uncertainty_detected: bool
    uncertainty_keywords: tuple[str, ...]
    evidence_sufficiency_score: float
    is_sufficient: bool
    abstention_recommended: bool
    justification: str
    confidence_is_calibrated: Literal[False] = False

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.assessment_id, "assessment_id")
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.justification, "justification")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if isinstance(self.evidence_sufficiency_score, bool) or not isinstance(self.evidence_sufficiency_score, (int, float)):
            raise OrchestrationContractError("evidence_sufficiency_score must be a numeric float")
        if not (0.0 <= float(self.evidence_sufficiency_score) <= 1.0):
            raise OrchestrationContractError("evidence_sufficiency_score must be bounded in [0.0, 1.0]")

        if not self.is_sufficient and not self.abstention_recommended:
            raise OrchestrationContractError("abstention_recommended must be True when evidence is insufficient")

        if self.confidence_is_calibrated is not False:
            raise OrchestrationContractError("confidence_is_calibrated must be strictly False (uncalibrated)")


@dataclass(frozen=True, slots=True)
class ConflictAssessment:
    """Explicit conflict marker analysis between evidence fragments or agent claims.

    Distinguishes explicit string/pattern conflict markers from general semantic
    contradictions (which are marked 'not_evaluated').
    """

    conflict_id: str
    request_id: str
    conflicts_detected: bool
    conflict_markers: tuple[str, ...]
    opposing_roles: tuple[str, ...] = ()
    resolution_strategy: Literal["fail_closed_abstain", "human_review_required", "none"] = "none"
    conflict_summary: str = ""
    semantic_contradiction_detected: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.conflict_id, "conflict_id")
            _nonempty_text(self.request_id, "request_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.conflict_markers, tuple):
            raise OrchestrationContractError("conflict_markers must be a tuple of strings")

        if self.conflicts_detected:
            if len(self.conflict_markers) == 0:
                raise OrchestrationContractError("conflict_markers cannot be empty when conflicts_detected is True")
            if self.resolution_strategy not in ("fail_closed_abstain", "human_review_required"):
                raise OrchestrationContractError("resolution_strategy must be fail_closed_abstain or human_review_required")
        else:
            if self.resolution_strategy not in ("none", "fail_closed_abstain"):
                raise OrchestrationContractError("resolution_strategy must be 'none' when no conflicts detected")

        if self.semantic_contradiction_detected != "not_evaluated":
            raise OrchestrationContractError("semantic_contradiction_detected must be 'not_evaluated'")


@dataclass(frozen=True, slots=True)
class AgentExecutionRecord:
    """Audit log entry for an individual agent invocation.

    Contains execution timing and reproducibility metadata. Explicitly forbids
    storing sensitive credentials, bearer tokens, or secrets.
    """

    execution_id: str
    request_id: str
    agent_role: str
    model_identifier: str
    prompt_template_hash: str
    input_tokens_est: int
    output_tokens_est: int
    latency_ms: float
    parsed_successfully: bool
    output_summary: str
    error_message: str | None = None

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.execution_id, "execution_id")
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.agent_role, "agent_role")
            _nonempty_text(self.model_identifier, "model_identifier")
            _nonempty_text(self.prompt_template_hash, "prompt_template_hash")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if isinstance(self.input_tokens_est, bool) or not isinstance(self.input_tokens_est, int) or self.input_tokens_est < 0:
            raise OrchestrationContractError("input_tokens_est must be a non-negative integer")
        if isinstance(self.output_tokens_est, bool) or not isinstance(self.output_tokens_est, int) or self.output_tokens_est < 0:
            raise OrchestrationContractError("output_tokens_est must be a non-negative integer")
        if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, (int, float)) or self.latency_ms < 0:
            raise OrchestrationContractError("latency_ms must be a non-negative float")

        # Secret / credential check
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.search(self.output_summary):
                raise OrchestrationContractError("output_summary contains prohibited credential pattern")


@dataclass(frozen=True, slots=True)
class FinalGatedAssessmentResult:
    """Final response emitted through the deterministic response gate.

    Ensures that invalid, unverified, or conflicting findings cannot bypass
    the response gate to produce a successful outcome.
    """

    result_id: str
    request_id: str
    decision: GatingDecision
    finding: SpecialistFinding | None = None
    validation_result: GatedGenerationResult | None = None
    uncertainty_summary: UncertaintyAssessment | None = None
    conflict_summary: ConflictAssessment | None = None
    abstention_reason: str | None = None
    execution_records: tuple[AgentExecutionRecord, ...] = ()
    generated_at_utc: str = ""
    uncertainty_aggregation: Any = None

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.result_id, "result_id")
            _nonempty_text(self.request_id, "request_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(self.decision, GatingDecision):
            raise OrchestrationContractError("decision must be a GatingDecision enum instance")

        if self.decision == GatingDecision.PROCEED:
            if self.finding is None:
                raise OrchestrationContractError("proceed decision requires a non-null finding")
            if self.validation_result is None:
                raise OrchestrationContractError("proceed decision requires a non-null validation_result")
            if self.validation_result.overall_classification != EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE:
                raise OrchestrationContractError(
                    f"cannot emit proceed decision when validation classification is {self.validation_result.overall_classification}"
                )
            if self.abstention_reason is not None:
                raise OrchestrationContractError("abstention_reason must be None for proceed decision")

        elif self.decision in (GatingDecision.ABSTAIN, GatingDecision.FLAG_FOR_REVIEW, GatingDecision.REJECT):
            if not self.abstention_reason or not self.abstention_reason.strip():
                raise OrchestrationContractError(
                    f"{self.decision.value} decision requires a non-empty abstention_reason"
                )

    @property
    def reason_codes(self) -> tuple[str, ...]:
        """Traceable reason codes from uncertainty aggregation, if present."""
        if self.uncertainty_aggregation is not None and hasattr(self.uncertainty_aggregation, "contributing_reason_codes"):
            return tuple(
                getattr(code, "value", str(code))
                for code in self.uncertainty_aggregation.contributing_reason_codes
            )
        return ()


# ---------------------------------------------------------------------------
# Deterministic Orchestration State Machine
# ---------------------------------------------------------------------------


class OrchestrationState(str, Enum):
    """Explicit lifecycle states for the multi-agent orchestration workflow."""

    REQUEST_RECEIVED = "request_received"
    REQUEST_VALIDATED = "request_validated"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    SPECIALIST_ANALYSIS_COMPLETED = "specialist_analysis_completed"
    EVIDENCE_REVIEW_COMPLETED = "evidence_review_completed"
    UNCERTAINTY_ASSESSED = "uncertainty_assessed"
    VALIDATION_COMPLETED = "validation_completed"
    # Terminal states
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    FAILED = "failed"


TERMINAL_STATES: frozenset[OrchestrationState] = frozenset({
    OrchestrationState.COMPLETED,
    OrchestrationState.ABSTAINED,
    OrchestrationState.REJECTED,
    OrchestrationState.FLAGGED_FOR_REVIEW,
    OrchestrationState.FAILED,
})

PERMITTED_TRANSITIONS: Mapping[OrchestrationState, frozenset[OrchestrationState]] = MappingProxyType({
    OrchestrationState.REQUEST_RECEIVED: frozenset({
        OrchestrationState.REQUEST_VALIDATED,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.REQUEST_VALIDATED: frozenset({
        OrchestrationState.RETRIEVAL_COMPLETED,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.RETRIEVAL_COMPLETED: frozenset({
        OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED,
        OrchestrationState.ABSTAINED,  # e.g., empty approved evidence bundle
        OrchestrationState.FAILED,
    }),
    OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED: frozenset({
        OrchestrationState.EVIDENCE_REVIEW_COMPLETED,
        OrchestrationState.ABSTAINED,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.EVIDENCE_REVIEW_COMPLETED: frozenset({
        OrchestrationState.UNCERTAINTY_ASSESSED,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.UNCERTAINTY_ASSESSED: frozenset({
        OrchestrationState.VALIDATION_COMPLETED,
        OrchestrationState.ABSTAINED,
        OrchestrationState.REJECTED,
        OrchestrationState.FLAGGED_FOR_REVIEW,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.VALIDATION_COMPLETED: frozenset({
        OrchestrationState.COMPLETED,
        OrchestrationState.ABSTAINED,
        OrchestrationState.REJECTED,
        OrchestrationState.FLAGGED_FOR_REVIEW,
        OrchestrationState.FAILED,
    }),
    OrchestrationState.COMPLETED: frozenset(),
    OrchestrationState.ABSTAINED: frozenset(),
    OrchestrationState.REJECTED: frozenset(),
    OrchestrationState.FLAGGED_FOR_REVIEW: frozenset(),
    OrchestrationState.FAILED: frozenset(),
})


class OrchestrationStateMachine:
    """Deterministic, fail-closed state machine for specialist agent orchestration.

    Guarantees strict forward progression through mandatory verification stages,
    prohibits stage bypass, blocks re-opening of terminal states, and propagates
    unexpected runtime errors without silently converting them to abstentions.
    """

    def __init__(self, request: AssessmentRequest) -> None:
        if not isinstance(request, AssessmentRequest):
            raise OrchestrationContractError("request must be an AssessmentRequest instance")
        self._request = request
        self._state = OrchestrationState.REQUEST_RECEIVED
        self._history: list[tuple[OrchestrationState, OrchestrationState, str | None]] = []
        self._evidence_bundle: EvidenceBundle | None = None
        self._specialist_finding: SpecialistFinding | None = None
        self._review_notes: str | None = None
        self._uncertainty_aggregation_result: Any = None
        self._uncertainty_assessment: UncertaintyAssessment | None = None
        self._conflict_assessment: ConflictAssessment | None = None
        self._validation_result: GatedGenerationResult | None = None
        self._final_result: FinalGatedAssessmentResult | None = None

    @property
    def request(self) -> AssessmentRequest:
        return self._request

    @property
    def current_state(self) -> OrchestrationState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def transition_history(self) -> tuple[tuple[OrchestrationState, OrchestrationState, str | None], ...]:
        return tuple(self._history)

    @property
    def evidence_bundle(self) -> EvidenceBundle | None:
        return self._evidence_bundle

    @property
    def specialist_finding(self) -> SpecialistFinding | None:
        return self._specialist_finding

    @property
    def review_notes(self) -> str | None:
        return self._review_notes

    @property
    def uncertainty_aggregation_result(self) -> Any:
        return self._uncertainty_aggregation_result

    @property
    def uncertainty_assessment(self) -> UncertaintyAssessment | None:
        return self._uncertainty_assessment

    @property
    def conflict_assessment(self) -> ConflictAssessment | None:
        return self._conflict_assessment

    @property
    def validation_result(self) -> GatedGenerationResult | None:
        return self._validation_result

    @property
    def final_result(self) -> FinalGatedAssessmentResult | None:
        return self._final_result

    def transition_to(self, next_state: OrchestrationState, reason: str | None = None) -> None:
        """Explicitly transition to the next state if permitted by the transition table."""
        if not isinstance(next_state, OrchestrationState):
            raise InvalidTransitionError(f"next_state must be an OrchestrationState enum instance, got {type(next_state)}")

        if self.is_terminal:
            raise TerminalStateError(
                f"Cannot transition from terminal state '{self._state.value}' to '{next_state.value}'"
            )

        permitted = PERMITTED_TRANSITIONS.get(self._state, frozenset())
        if next_state not in permitted:
            raise InvalidTransitionError(
                f"Illegal state transition from '{self._state.value}' to '{next_state.value}'"
            )

        prev_state = self._state
        self._state = next_state
        self._history.append((prev_state, next_state, reason))

    # -----------------------------------------------------------------------
    # Workflow Stage Methods (Enforcing Contracts & Invariants)
    # -----------------------------------------------------------------------

    def validate_request(self) -> None:
        """Validate request and advance to REQUEST_VALIDATED."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot validate request from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.REQUEST_RECEIVED:
            raise StageBypassError(
                f"Cannot execute validate_request() from state '{self._state.value}'; expected 'request_received'"
            )
        # Note: AssessmentRequest is pre-validated in __post_init__
        self.transition_to(OrchestrationState.REQUEST_VALIDATED, reason="scope_and_target_validated")

    def record_retrieval(self, bundle: EvidenceBundle) -> None:
        """Record completed evidence retrieval and advance state."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record retrieval from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.REQUEST_VALIDATED:
            raise StageBypassError(
                f"Cannot record retrieval from state '{self._state.value}'; expected 'request_validated'"
            )
        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")
        if bundle.request_id != self._request.request_id:
            raise OrchestrationContractError(
                f"bundle request_id '{bundle.request_id}' does not match state machine request_id '{self._request.request_id}'"
            )

        self._evidence_bundle = bundle
        self.transition_to(OrchestrationState.RETRIEVAL_COMPLETED, reason="evidence_retrieval_completed")

        # Automatic fail-closed abstention if no approved evidence exists
        if bundle.approved_source_count == 0 or len(bundle.chunks) == 0:
            self.transition_to(OrchestrationState.ABSTAINED, reason="no_approved_evidence")

    def execute_specialist_analysis(self, specialist: Any) -> SpecialistFinding:
        """Execute specialist analysis using a specialist adapter (e.g. GroundedSpecialistAdapter).

        Fails closed on any unexpected specialist error by transitioning to FAILED and re-raising.
        """
        if self.is_terminal:
            raise TerminalStateError(f"Cannot execute specialist analysis from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.RETRIEVAL_COMPLETED:
            raise StageBypassError(
                f"Cannot execute specialist analysis from state '{self._state.value}'; expected 'retrieval_completed'"
            )
        if self._evidence_bundle is None:
            raise OrchestrationContractError("evidence_bundle must be recorded before executing specialist analysis")

        try:
            finding = specialist.analyse(self._request.request_id, self._evidence_bundle)
        except Exception as exc:
            self.fail(f"Specialist analysis execution failed: {type(exc).__name__}: {str(exc)}")
            raise

        self.record_specialist_analysis(finding)
        return finding

    def record_specialist_analysis(self, finding: SpecialistFinding) -> None:
        """Record specialist analysis finding and advance state."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record specialist analysis from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.RETRIEVAL_COMPLETED:
            raise StageBypassError(
                f"Cannot record specialist analysis from state '{self._state.value}'; expected 'retrieval_completed'"
            )
        if not isinstance(finding, SpecialistFinding):
            raise OrchestrationContractError("finding must be a SpecialistFinding instance")
        if finding.request_id != self._request.request_id:
            raise OrchestrationContractError("finding request_id does not match state machine request_id")

        if finding.claim_citations and self._evidence_bundle is not None:
            for cc in finding.claim_citations:
                validate_citation_excerpt(cc, self._evidence_bundle)

        self._specialist_finding = finding
        self.transition_to(OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED, reason="specialist_analysis_completed")

    def record_evidence_review(self, review_notes: str) -> None:
        """Record adversarial evidence review and advance state."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record evidence review from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED:
            raise StageBypassError(
                f"Cannot record evidence review from state '{self._state.value}'; expected 'specialist_analysis_completed'"
            )
        try:
            _nonempty_text(review_notes, "review_notes")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        self._review_notes = review_notes
        self.transition_to(OrchestrationState.EVIDENCE_REVIEW_COMPLETED, reason="evidence_review_completed")

    def assess_uncertainty(
        self,
        engine: Any = None,
        *,
        secondary_findings: Sequence[SpecialistFinding] | None = None,
        force_sufficient: bool | None = None,
        force_conflict: bool | None = None,
        forced_conflict_markers: Sequence[str] | None = None,
    ) -> Any:
        """Execute deterministic uncertainty aggregation using UncertaintyAggregationEngine.

        Evaluates evidence sufficiency, specialist consensus, evidence reviewer verdicts,
        citation integrity, conflict patterns, and epistemic ambiguity.
        Advances the state machine deterministically based on the recommendation:
          - CONTINUE: advances to UNCERTAINTY_ASSESSED.
          - ABSTAIN: advances to UNCERTAINTY_ASSESSED, then immediately to ABSTAINED.
          - REJECT: advances to UNCERTAINTY_ASSESSED, then immediately to REJECTED.
          - FLAG_FOR_REVIEW: advances to UNCERTAINTY_ASSESSED, then immediately to FLAGGED_FOR_REVIEW.

        Fails closed on any unexpected engine error by transitioning to FAILED and re-raising.
        """
        if self.is_terminal:
            raise TerminalStateError(f"Cannot assess uncertainty from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.EVIDENCE_REVIEW_COMPLETED:
            raise StageBypassError(
                f"Cannot assess uncertainty from state '{self._state.value}'; expected 'evidence_review_completed'"
            )
        if self._evidence_bundle is None:
            raise OrchestrationContractError("evidence_bundle must be recorded before assessing uncertainty")

        from aegiscore.uncertainty_engine import UncertaintyAggregationEngine

        eng = engine if engine is not None else UncertaintyAggregationEngine()

        try:
            result = eng.aggregate(
                request_id=self._request.request_id,
                bundle=self._evidence_bundle,
                primary_finding=self._specialist_finding,
                secondary_findings=secondary_findings or (),
                review_notes=self._review_notes or "",
                force_sufficient=force_sufficient,
                force_conflict=force_conflict,
                forced_conflict_markers=forced_conflict_markers,
            )
        except Exception as exc:
            self.fail(f"Uncertainty aggregation failed: {type(exc).__name__}: {str(exc)}")
            raise

        self.record_uncertainty_aggregation(result)
        return result

    def record_uncertainty_aggregation(self, result: Any) -> None:
        """Record an UncertaintyAggregationResult and advance the state machine accordingly."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record aggregation from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.EVIDENCE_REVIEW_COMPLETED:
            raise StageBypassError(
                f"Cannot record aggregation from state '{self._state.value}'; expected 'evidence_review_completed'"
            )

        from aegiscore.uncertainty_engine import (
            AggregationRecommendation,
            UncertaintyAggregationResult,
        )

        if not isinstance(result, UncertaintyAggregationResult):
            raise OrchestrationContractError("result must be an UncertaintyAggregationResult instance")
        if result.request_id != self._request.request_id:
            raise OrchestrationContractError(
                f"result request_id '{result.request_id}' does not match state machine request_id '{self._request.request_id}'"
            )

        self._uncertainty_aggregation_result = result
        self._uncertainty_assessment = result.to_uncertainty_assessment()
        self._conflict_assessment = result.to_conflict_assessment()

        # Advance to intermediate state UNCERTAINTY_ASSESSED
        self.transition_to(
            OrchestrationState.UNCERTAINTY_ASSESSED,
            reason=f"uncertainty_aggregated:{result.primary_reason_code.value}",
        )

        # Map recommendation to explicit state machine behavior
        if result.recommendation == AggregationRecommendation.CONTINUE:
            # Remains in UNCERTAINTY_ASSESSED, cleared for validation stage
            pass
        elif result.recommendation == AggregationRecommendation.ABSTAIN:
            self.transition_to(
                OrchestrationState.ABSTAINED,
                reason=f"abstain:{result.primary_reason_code.value} - {result.justification}",
            )
        elif result.recommendation == AggregationRecommendation.REJECT:
            self.transition_to(
                OrchestrationState.REJECTED,
                reason=f"reject:{result.primary_reason_code.value} - {result.justification}",
            )
        elif result.recommendation == AggregationRecommendation.FLAG_FOR_REVIEW:
            self.transition_to(
                OrchestrationState.FLAGGED_FOR_REVIEW,
                reason=f"flag_for_review:{result.primary_reason_code.value} - {result.justification}",
            )

    def record_uncertainty_and_conflict(
        self,
        uncertainty: UncertaintyAssessment,
        conflict: ConflictAssessment,
    ) -> None:
        """Record uncertainty and conflict assessments and advance state."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record assessments from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.EVIDENCE_REVIEW_COMPLETED:
            raise StageBypassError(
                f"Cannot record assessments from state '{self._state.value}'; expected 'evidence_review_completed'"
            )
        if not isinstance(uncertainty, UncertaintyAssessment):
            raise OrchestrationContractError("uncertainty must be an UncertaintyAssessment instance")
        if not isinstance(conflict, ConflictAssessment):
            raise OrchestrationContractError("conflict must be a ConflictAssessment instance")
        if uncertainty.request_id != self._request.request_id or conflict.request_id != self._request.request_id:
            raise OrchestrationContractError("assessment request_id mismatch")

        self._uncertainty_assessment = uncertainty
        self._conflict_assessment = conflict
        self.transition_to(OrchestrationState.UNCERTAINTY_ASSESSED, reason="uncertainty_and_conflict_assessed")

        # Fast-track abstention or human review if assessments mandate it
        if conflict.conflicts_detected:
            if conflict.resolution_strategy == "human_review_required":
                self.transition_to(OrchestrationState.FLAGGED_FOR_REVIEW, reason="conflict_markers_detected")
            elif conflict.resolution_strategy == "fail_closed_abstain":
                self.transition_to(OrchestrationState.ABSTAINED, reason="conflict_markers_detected")
        elif uncertainty.abstention_recommended:
            self.transition_to(OrchestrationState.ABSTAINED, reason=uncertainty.justification)

    def record_validation(self, validation_result: GatedGenerationResult) -> None:
        """Record claim validation result and advance state."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot record validation from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.UNCERTAINTY_ASSESSED:
            raise StageBypassError(
                f"Cannot record validation from state '{self._state.value}'; expected 'uncertainty_assessed'"
            )
        if not isinstance(validation_result, GatedGenerationResult):
            raise OrchestrationContractError("validation_result must be a GatedGenerationResult instance")

        self._validation_result = validation_result
        self.transition_to(OrchestrationState.VALIDATION_COMPLETED, reason="claim_validation_completed")

    def finalize_result(self, result: FinalGatedAssessmentResult) -> FinalGatedAssessmentResult:
        """Finalize the workflow into a terminal state based on the gated result."""
        if self.is_terminal:
            raise TerminalStateError(f"Cannot finalize result from terminal state '{self._state.value}'")
        if self._state != OrchestrationState.VALIDATION_COMPLETED:
            raise StageBypassError(
                f"Cannot finalize result from state '{self._state.value}'; required prerequisite validation not completed"
            )
        if not isinstance(result, FinalGatedAssessmentResult):
            raise OrchestrationContractError("result must be a FinalGatedAssessmentResult instance")
        if result.request_id != self._request.request_id:
            raise OrchestrationContractError("result request_id does not match state machine request_id")

        self._final_result = result
        if result.decision == GatingDecision.PROCEED:
            self.transition_to(OrchestrationState.COMPLETED, reason="response_gated_proceed")
        elif result.decision == GatingDecision.ABSTAIN:
            self.transition_to(OrchestrationState.ABSTAINED, reason=result.abstention_reason)
        elif result.decision == GatingDecision.REJECT:
            self.transition_to(OrchestrationState.REJECTED, reason=result.abstention_reason)
        elif result.decision == GatingDecision.FLAG_FOR_REVIEW:
            self.transition_to(OrchestrationState.FLAGGED_FOR_REVIEW, reason=result.abstention_reason)

        return self._final_result

    def create_final_result(
        self,
        result_id: str,
        *,
        decision: GatingDecision | None = None,
        abstention_reason: str | None = None,
        execution_records: Sequence[AgentExecutionRecord] = (),
    ) -> FinalGatedAssessmentResult:
        """Convenience factory to construct a FinalGatedAssessmentResult consistent with current state."""
        from aegiscore.uncertainty_engine import AggregationRecommendation

        effective_decision: GatingDecision
        effective_reason: str | None = abstention_reason

        if decision is not None:
            effective_decision = decision
        elif self._uncertainty_aggregation_result is not None:
            rec = self._uncertainty_aggregation_result.recommendation
            if rec == AggregationRecommendation.CONTINUE:
                effective_decision = GatingDecision.PROCEED
            elif rec == AggregationRecommendation.REJECT:
                effective_decision = GatingDecision.REJECT
                effective_reason = effective_reason or f"rejected: {self._uncertainty_aggregation_result.primary_reason_code.value}"
            elif rec == AggregationRecommendation.FLAG_FOR_REVIEW:
                effective_decision = GatingDecision.FLAG_FOR_REVIEW
                effective_reason = effective_reason or f"flagged: {self._uncertainty_aggregation_result.primary_reason_code.value}"
            else:
                effective_decision = GatingDecision.ABSTAIN
                effective_reason = effective_reason or f"abstained: {self._uncertainty_aggregation_result.primary_reason_code.value}"
        else:
            effective_decision = GatingDecision.ABSTAIN
            effective_reason = effective_reason or "default_fail_closed_abstain"

        return FinalGatedAssessmentResult(
            result_id=result_id,
            request_id=self._request.request_id,
            decision=effective_decision,
            finding=self._specialist_finding,
            validation_result=self._validation_result,
            uncertainty_summary=self._uncertainty_assessment,
            conflict_summary=self._conflict_assessment,
            abstention_reason=effective_reason,
            execution_records=tuple(execution_records),
            uncertainty_aggregation=self._uncertainty_aggregation_result,
        )


    def fail(self, error_message: str) -> None:
        """Transition directly to FAILED state upon unrecoverable error."""
        try:
            _nonempty_text(error_message, "error_message")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc
        self.transition_to(OrchestrationState.FAILED, reason=error_message)
