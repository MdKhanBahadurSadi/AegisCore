"""Provider-neutral evidence-grounded generation contracts and deterministic offline fake.

This module provides the generation boundary for AEGISCORE AI. It consumes completed
EvidenceRetrievalResult bundles from approved-only retrieval, preserves provenance and
claim-level citation references, represents answers and abstentions explicitly, and
enforces that claims cite only evidence returned in the retrieval bundle.

This module contains NO external LLM calls, NO network egress, NO API keys, and NO
agent orchestration. Retrieved text is treated strictly as passive, untrusted data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Protocol

from aegiscore.rag import (
    CitationReference,
    RagContractError,
    validate_citation_references,
    _nonempty_text,
)
from aegiscore.rag_runtime import EvidenceRetrievalResult


class GenerationError(Exception):
    """Base exception for all generation-related errors."""


class GenerationContractError(GenerationError, RagContractError):
    """A generation request, response, or claim violates contractual invariants."""


class CitationGroundingError(GenerationContractError):
    """A claim references citations that do not belong to the supplied evidence or violate integrity."""


class GenerationResponseValidationError(GenerationContractError):
    """A generated response violates structural, claim, or abstention invariants."""


GenerationStatus = Literal["answered", "abstained"]
AbstentionReason = Literal[
    "no_approved_sources",
    "no_retrieved_chunks",
    "insufficient_evidence",
    "conflicting_evidence",
]

_VALID_ABSTENTION_REASONS: frozenset[str] = frozenset({
    "no_approved_sources",
    "no_retrieved_chunks",
    "insufficient_evidence",
    "conflicting_evidence",
})


@dataclass(frozen=True, slots=True)
class GeneratedClaim:
    """A single factual statement grounded in specific retrieved citations.

    Citation membership confirms only that the referenced chunk was retrieved and
    has matching provenance; it does not constitute proof that the claim is factually true.
    """

    text: str
    citations: tuple[CitationReference, ...]
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.text, "claim text")
        except RagContractError as exc:
            raise GenerationContractError(str(exc)) from exc

        if not isinstance(self.citations, tuple):
            raise GenerationContractError("claim citations must be a tuple")
        if len(self.citations) == 0:
            raise GenerationContractError("claim citations must be a non-empty tuple")
        for ref in self.citations:
            if not isinstance(ref, CitationReference):
                raise GenerationContractError("every claim citation must be a CitationReference instance")

        # Duplicate reference check within claim
        keys = [(ref.source_id, ref.chunk_id) for ref in self.citations]
        if len(keys) != len(set(keys)):
            raise GenerationContractError("claim citations must not contain duplicate references")

        if self.factual_support != "not_evaluated":
            raise GenerationContractError("factual_support cannot be marked verified or evaluated during generation")


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Request contract for evidence-grounded generation."""

    evidence: EvidenceRetrievalResult
    task_prompt: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceRetrievalResult):
            raise GenerationContractError("evidence must be an EvidenceRetrievalResult instance")
        if self.task_prompt is not None:
            try:
                _nonempty_text(self.task_prompt, "task_prompt")
            except RagContractError as exc:
                raise GenerationContractError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Typed result of evidence-grounded generation: structured answer or explicit abstention."""

    status: GenerationStatus
    claims: tuple[GeneratedClaim, ...]
    abstention_reason: AbstentionReason | None = None
    query_text: str | None = None
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        if self.status not in {"answered", "abstained"}:
            raise GenerationResponseValidationError("status must be 'answered' or 'abstained'")

        if not isinstance(self.claims, tuple):
            raise GenerationResponseValidationError("claims must be a tuple")

        if self.factual_support != "not_evaluated":
            raise GenerationContractError("factual_support must be 'not_evaluated'")

        if self.query_text is not None:
            try:
                _nonempty_text(self.query_text, "query_text")
            except RagContractError as exc:
                raise GenerationContractError(str(exc)) from exc

        if self.status == "answered":
            if len(self.claims) == 0:
                raise GenerationResponseValidationError("answered status requires at least one generated claim")
            for claim in self.claims:
                if not isinstance(claim, GeneratedClaim):
                    raise GenerationResponseValidationError("every claim must be a GeneratedClaim instance")
            if self.abstention_reason is not None:
                raise GenerationResponseValidationError("answered status must have abstention_reason=None")
        elif self.status == "abstained":
            if len(self.claims) > 0:
                raise GenerationResponseValidationError("abstained status requires empty claims")
            if self.abstention_reason not in _VALID_ABSTENTION_REASONS:
                raise GenerationResponseValidationError(
                    f"abstained status requires a valid abstention_reason ({', '.join(sorted(_VALID_ABSTENTION_REASONS))})"
                )

    @property
    def all_citations(self) -> tuple[CitationReference, ...]:
        """Unique citation references attached to any claim in this result."""
        refs: list[CitationReference] = []
        seen: set[tuple[str, str]] = set()
        for claim in self.claims:
            for ref in claim.citations:
                key = (ref.source_id, ref.chunk_id)
                if key not in seen:
                    seen.add(key)
                    refs.append(ref)
        return tuple(refs)


def validate_generation_result(result: GenerationResult, evidence: EvidenceRetrievalResult) -> None:
    """Validate that a generation result satisfies all integrity and grounding invariants.

    Enforces that:
    1. Result and evidence are instances of their respective types.
    2. Abstained status matches evidence conditions when evidence is missing.
    3. Answered status cannot be produced from empty evidence.
    4. Every cited chunk belongs to the supplied retrieval result hits with matching source_id.
    5. Factual support remains explicitly unverified / not_evaluated.
    """
    if not isinstance(result, GenerationResult):
        raise GenerationContractError("result must be a GenerationResult instance")
    if not isinstance(evidence, EvidenceRetrievalResult):
        raise GenerationContractError("evidence must be an EvidenceRetrievalResult instance")

    if result.status == "abstained":
        if evidence.status == "no_approved_evidence":
            expected_reason = "no_approved_sources" if evidence.approved_source_count == 0 else "no_retrieved_chunks"
            if result.abstention_reason not in _VALID_ABSTENTION_REASONS:
                raise GenerationResponseValidationError(f"Invalid abstention reason: {result.abstention_reason}")
            if result.abstention_reason not in {"no_approved_sources", "no_retrieved_chunks", "insufficient_evidence"}:
                raise GenerationResponseValidationError(
                    f"Abstention reason '{result.abstention_reason}' does not match empty evidence state (expected '{expected_reason}')"
                )
        return

    # Status is "answered"
    if evidence.status == "no_approved_evidence":
        raise GenerationResponseValidationError("Cannot produce answered result when evidence status is 'no_approved_evidence'")

    hit_map = {hit.chunk.chunk_id: hit.chunk for hit in evidence.retrieval_result.hits}

    for claim_idx, claim in enumerate(result.claims):
        if not isinstance(claim, GeneratedClaim):
            raise GenerationResponseValidationError(f"Claim at index {claim_idx} is not a GeneratedClaim")
        if len(claim.citations) == 0:
            raise GenerationResponseValidationError(f"Claim at index {claim_idx} has zero citations")

        # Validate citation references against retrieval result
        validation = validate_citation_references(claim.citations, evidence.retrieval_result)
        if not validation.valid:
            first_issue = validation.rejected[0]
            if first_issue.reason == "chunk_not_retrieved":
                raise CitationGroundingError(
                    f"Claim references chunk '{first_issue.reference.chunk_id}' not found in retrieval result hits"
                )
            elif first_issue.reason == "source_id_mismatch":
                actual_chunk = hit_map.get(first_issue.reference.chunk_id)
                actual_source = actual_chunk.provenance.source_id if actual_chunk else "unknown"
                raise CitationGroundingError(
                    f"Claim citation source '{first_issue.reference.source_id}' mismatches retrieved chunk source '{actual_source}'"
                )
            else:
                raise CitationGroundingError(f"Claim citation rejected: {first_issue.reason}")

        # Check source_id against hit_map directly
        for ref in claim.citations:
            hit_chunk = hit_map.get(ref.chunk_id)
            if hit_chunk is None:
                raise CitationGroundingError(f"Citation chunk '{ref.chunk_id}' was not retrieved in evidence")
            if hit_chunk.provenance.source_id != ref.source_id:
                raise CitationGroundingError(
                    f"Citation source_id '{ref.source_id}' does not match chunk's source_id '{hit_chunk.provenance.source_id}'"
                )


@dataclass(frozen=True, slots=True)
class ConflictRule:
    """Explicit pair of strings that, when found in distinct chunks, indicate conflicting evidence."""

    first: str
    second: str

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.first, "first marker")
            _nonempty_text(self.second, "second marker")
        except RagContractError as exc:
            raise GenerationContractError(str(exc)) from exc


DEFAULT_CONFLICT_RULES: tuple[ConflictRule, ...] = (
    ConflictRule("vulnerability:confirmed", "vulnerability:disproved"),
    ConflictRule("requires authentication", "does not require authentication"),
    ConflictRule("[DIRECTIVE:ALLOW]", "[DIRECTIVE:DENY]"),
)


class Generator(Protocol):
    """Provider-neutral evidence-grounded generator protocol."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate an answer or abstention grounded in the supplied request."""


def generate_grounded_response(
    generator: Generator,
    request: GenerationRequest | EvidenceRetrievalResult,
    *,
    conflict_rules: tuple[ConflictRule, ...] = DEFAULT_CONFLICT_RULES,
    min_evidence_score: float = 0.0,
) -> GenerationResult:
    """Generate an evidence-grounded response using a provider-neutral generator.

    If the supplied evidence has no approved evidence (status == 'no_approved_evidence'),
    this function short-circuits immediately without invoking the generator seam,
    preventing any potential fabrication or reliance on pre-trained bias.

    When evidence is present, delegates to generator.generate(request) and validates
    all claims and citations against the supplied evidence, failing closed on any
    insufficient or conflicting claim.
    """
    from aegiscore.claim_validation import validate_and_gate_generation

    return validate_and_gate_generation(
        request,
        generator,
        conflict_rules=conflict_rules,
        min_evidence_score=min_evidence_score,
    )


class DeterministicFakeGenerator:
    """Deterministic offline fake generator.

    Produces repeatable outputs for identical inputs with zero network activity,
    no API keys, and no external dependencies. Treats retrieved chunk text as untrusted
    passive data, not executable instructions or policy overrides.
    """

    def __init__(
        self,
        *,
        conflict_rules: Iterable[ConflictRule] = DEFAULT_CONFLICT_RULES,
        min_evidence_score: float = 0.0,
        canned_claims: tuple[GeneratedClaim, ...] | None = None,
        validate_output: bool = True,
    ) -> None:
        try:
            rules_tuple = tuple(conflict_rules)
        except TypeError as exc:
            raise GenerationContractError("conflict_rules must be an iterable") from exc
        for rule in rules_tuple:
            if not isinstance(rule, ConflictRule):
                raise GenerationContractError("every item in conflict_rules must be a ConflictRule")
        self._conflict_rules = rules_tuple
        self._min_evidence_score = float(min_evidence_score)
        if canned_claims is not None:
            if not isinstance(canned_claims, tuple) or any(not isinstance(c, GeneratedClaim) for c in canned_claims):
                raise GenerationContractError("canned_claims must be a tuple of GeneratedClaim")
        self._canned_claims = canned_claims
        self._validate_output = validate_output

    def generate(self, request: GenerationRequest | EvidenceRetrievalResult) -> GenerationResult:
        """Produce deterministic response or abstention from the supplied request."""
        if isinstance(request, EvidenceRetrievalResult):
            request = GenerationRequest(evidence=request)
        elif not isinstance(request, GenerationRequest):
            raise GenerationContractError("request must be GenerationRequest or EvidenceRetrievalResult")

        evidence = request.evidence
        if not isinstance(evidence, EvidenceRetrievalResult):
            raise GenerationContractError("evidence must be an EvidenceRetrievalResult instance")

        # 1. Empty evidence check
        if evidence.status == "no_approved_evidence":
            reason: AbstentionReason = (
                "no_approved_sources" if evidence.approved_source_count == 0 else "no_retrieved_chunks"
            )
            return GenerationResult(
                status="abstained",
                claims=(),
                abstention_reason=reason,
                query_text=evidence.query_text,
                factual_support="not_evaluated",
            )

        hits = evidence.retrieval_result.hits
        if len(hits) == 0:
            return GenerationResult(
                status="abstained",
                claims=(),
                abstention_reason="no_retrieved_chunks",
                query_text=evidence.query_text,
                factual_support="not_evaluated",
            )

        # 2. Check for explicit conflicting evidence based on documented explicit rules
        if self._detect_conflicts(hits):
            return GenerationResult(
                status="abstained",
                claims=(),
                abstention_reason="conflicting_evidence",
                query_text=evidence.query_text,
                factual_support="not_evaluated",
            )

        # 3. Check for insufficient evidence
        if self._detect_insufficiency(hits):
            return GenerationResult(
                status="abstained",
                claims=(),
                abstention_reason="insufficient_evidence",
                query_text=evidence.query_text,
                factual_support="not_evaluated",
            )

        # 4. Generate grounded claims
        if self._canned_claims is not None:
            claims = self._canned_claims
        else:
            generated: list[GeneratedClaim] = []
            for hit in hits:
                chunk = hit.chunk
                source_id = chunk.provenance.source_id
                citation = CitationReference(source_id=source_id, chunk_id=chunk.chunk_id)
                if chunk.section:
                    claim_text = (
                        f"According to section '{chunk.section}', guidance applies to the assessed scope."
                    )
                else:
                    claim_text = (
                        f"Retrieved source '{source_id}' documents security requirements for the assessed scope."
                    )
                generated.append(GeneratedClaim(text=claim_text, citations=(citation,)))
            claims = tuple(generated)

        result = GenerationResult(
            status="answered",
            claims=claims,
            abstention_reason=None,
            query_text=evidence.query_text,
            factual_support="not_evaluated",
        )

        if self._validate_output:
            validate_generation_result(result, evidence)

        return result

    def _detect_conflicts(self, hits: tuple) -> bool:
        """Check if hits exhibit conflicting markers across distinct chunks or conflicting scope tags."""
        # Check conflict rules across chunks
        for rule in self._conflict_rules:
            has_first = any(rule.first.casefold() in hit.chunk.content.casefold() for hit in hits)
            has_second = any(rule.second.casefold() in hit.chunk.content.casefold() for hit in hits)
            if has_first and has_second:
                first_chunks = {
                    hit.chunk.chunk_id for hit in hits if rule.first.casefold() in hit.chunk.content.casefold()
                }
                second_chunks = {
                    hit.chunk.chunk_id for hit in hits if rule.second.casefold() in hit.chunk.content.casefold()
                }
                if first_chunks != second_chunks or len(first_chunks) > 1:
                    return True

        # Check scope_tags for conflicting indicators
        tags = set()
        for hit in hits:
            if hit.chunk.provenance.scope_tags:
                tags.update(hit.chunk.provenance.scope_tags)
        if "conflict" in tags or ("variant_a" in tags and "variant_b" in tags):
            return True

        return False

    def _detect_insufficiency(self, hits: tuple) -> bool:
        """Check if retrieved evidence is insufficient according to explicit rules."""
        # Explicit insufficiency marker in chunk text
        if any("[INSUFFICIENT_EVIDENCE]" in hit.chunk.content for hit in hits):
            return True

        # Score threshold check: if all hits are below min_evidence_score
        if self._min_evidence_score > 0.0:
            if all(hit.score is not None and hit.score < self._min_evidence_score for hit in hits):
                return True

        return False
