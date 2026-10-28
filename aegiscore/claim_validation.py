"""Deterministic offline evidence sufficiency and claim validation for AEGISCORE AI.

This module implements the evidence sufficiency, claim validation, conflict detection,
and fail-closed response gating framework designed in docs/PHASE_8C2_DESIGN.md.

It operates entirely offline with zero external dependencies, no API keys, and no
external LLM calls. Passing validation confirms only that claims satisfy the defined
structural and provenance contracts; it does NOT claim to prove semantic entailment
or factual truth (factual_support remains strictly 'not_evaluated').
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal, Sequence

from aegiscore.generation import (
    CitationGroundingError,
    ConflictRule,
    DEFAULT_CONFLICT_RULES,
    GeneratedClaim,
    GenerationContractError,
    GenerationRequest,
    GenerationResponseValidationError,
    GenerationResult,
    Generator,
    validate_generation_result,
)
from aegiscore.rag import (
    CitationReference,
    RagContractError,
    RetrievalHit,
    RetrievalResult,
    SourceChunk,
    _nonempty_text,
    validate_citation_references,
)
from aegiscore.rag_runtime import EvidenceRetrievalResult


class EvidenceSufficiencyClassification(str, Enum):
    """Classification states for evidence sufficiency and claim validation."""

    NO_APPROVED_EVIDENCE = "no_approved_evidence"
    SUFFICIENT_EVIDENCE = "sufficient_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNCERTAIN_INDETERMINATE = "uncertain_indeterminate"


@dataclass(frozen=True, slots=True)
class ClaimValidationResult:
    """Outcome of validating an individual claim against its cited evidence."""

    claim: GeneratedClaim
    classification: EvidenceSufficiencyClassification
    is_valid: bool
    citations_validated: tuple[CitationReference, ...]
    reason: str | None = None
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        if not isinstance(self.claim, GeneratedClaim):
            raise GenerationContractError("claim must be a GeneratedClaim instance")
        if not isinstance(self.classification, EvidenceSufficiencyClassification):
            raise GenerationContractError("classification must be EvidenceSufficiencyClassification")
        if not isinstance(self.is_valid, bool):
            raise GenerationContractError("is_valid must be a boolean")
        if not isinstance(self.citations_validated, tuple):
            raise GenerationContractError("citations_validated must be a tuple")
        for ref in self.citations_validated:
            if not isinstance(ref, CitationReference):
                raise GenerationContractError("citations_validated must contain only CitationReference instances")
        if self.reason is not None:
            try:
                _nonempty_text(self.reason, "reason")
            except RagContractError as exc:
                raise GenerationContractError(str(exc)) from exc
        if self.factual_support != "not_evaluated":
            raise GenerationContractError("factual_support must be 'not_evaluated'")


@dataclass(frozen=True, slots=True)
class GatedGenerationResult:
    """Outcome of validating and gating a generation result against evidence."""

    generation_result: GenerationResult
    overall_classification: EvidenceSufficiencyClassification
    claim_validations: tuple[ClaimValidationResult, ...]
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        if not isinstance(self.generation_result, GenerationResult):
            raise GenerationContractError("generation_result must be a GenerationResult instance")
        if not isinstance(self.overall_classification, EvidenceSufficiencyClassification):
            raise GenerationContractError("overall_classification must be EvidenceSufficiencyClassification")
        if not isinstance(self.claim_validations, tuple):
            raise GenerationContractError("claim_validations must be a tuple")
        for cv in self.claim_validations:
            if not isinstance(cv, ClaimValidationResult):
                raise GenerationContractError("claim_validations must contain only ClaimValidationResult instances")
        if self.factual_support != "not_evaluated":
            raise GenerationContractError("factual_support must be 'not_evaluated'")


def has_explicit_conflicts(
    hits: tuple[RetrievalHit, ...],
    conflict_rules: tuple[ConflictRule, ...] = DEFAULT_CONFLICT_RULES,
) -> bool:
    """Detect whether retrieved hits contain explicitly defined conflicting statements or tags."""
    # 1. Opposing string markers across distinct chunks
    for rule in conflict_rules:
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

    # 2. Conflicting scope tags across retrieved chunks
    tags: set[str] = set()
    for hit in hits:
        if hit.chunk.provenance.scope_tags:
            tags.update(hit.chunk.provenance.scope_tags)
    if "conflict" in tags or ("variant_a" in tags and "variant_b" in tags):
        return True

    return False


def is_globally_insufficient(
    hits: tuple[RetrievalHit, ...],
    min_evidence_score: float = 0.0,
) -> bool:
    """Determine whether the evidence bundle is globally insufficient under explicit rules."""
    if len(hits) == 0:
        return True

    # Explicit insufficiency marker in chunk text
    if any("[INSUFFICIENT_EVIDENCE]" in hit.chunk.content for hit in hits):
        return True

    # Score threshold check: all hits below minimum required score
    if min_evidence_score > 0.0:
        if all(hit.score is not None and hit.score < min_evidence_score for hit in hits):
            return True

    return False


def is_claim_supported_by_chunks(
    claim: GeneratedClaim,
    hit_map: dict[str, SourceChunk],
    *,
    unsupported_markers: tuple[str, ...] = (
        "automatically sanitize",
        "unsupported_claim",
        "[UNSUPPORTED]",
    ),
) -> bool:
    """Evaluate whether an individual claim is supported by its cited chunks under explicit rules.

    This is an explicit rule-based check, not an entailment solver. A claim fails if:
    - Any cited chunk contains explicit insufficiency markers ([INSUFFICIENT_EVIDENCE]).
    - The claim asserts known unsupported statements (e.g. ungrounded browser auto-sanitization).
    - The chunk contains explicit scope limitations violated by the claim (e.g. [SCOPE:PHP_ONLY] vs universal).
    """
    # 1. Check if cited chunks carry insufficiency markers
    for ref in claim.citations:
        chunk = hit_map.get(ref.chunk_id)
        if chunk is None:
            return False
        if "[INSUFFICIENT_EVIDENCE]" in chunk.content:
            return False
        # Check scope mismatch if chunk is tagged with scope limits
        if "[SCOPE:PHP_ONLY]" in chunk.content and (
            "all runtimes" in claim.text.lower() or "[SCOPE:UNIVERSAL]" in claim.text
        ):
            return False

    # 2. Check if claim asserts explicitly unsupported statements
    claim_lower = claim.text.lower()
    for marker in unsupported_markers:
        if marker.lower() in claim_lower:
            return False

    return True


def validate_citation_excerpt(
    citation: CitationReference | object,
    chunk_or_evidence: SourceChunk | RetrievalResult | EvidenceRetrievalResult | dict[str, SourceChunk] | Sequence[SourceChunk] | object,
    *,
    cited_excerpt: str | None = None,
) -> None:
    """Verify that a cited excerpt occurs verbatim within the corresponding chunk text.

    Enforces:
    1. The citation reference must resolve to a retrieved chunk in the supplied evidence.
    2. The citation reference source_id must match the chunk's provenance source_id.
    3. When a non-empty cited_excerpt is supplied, it must be an exact verbatim substring
       of the corresponding chunk's content.
    4. Unrelated chunks are not searched to satisfy an invalid citation.
    5. Absent or empty excerpts (None or "") pass structural validation without error.
    6. Unicode text is preserved exactly (no case folding, transliteration, or normalization).
    7. Whitespace and newlines must match exactly; no silent normalization is performed.
    8. factual_support is strictly 'not_evaluated'. A matching excerpt confirms ONLY
       verbatim structural grounding in the chunk text, NOT semantic entailment or factual truth.

    Raises:
        GenerationContractError: If citation, chunk, or excerpt parameters violate types or invariants.
        CitationGroundingError: If chunk_id or source_id mismatches, or if the excerpt
                                does not occur verbatim in the chunk content.
    """
    # 1. Extract CitationReference and optional excerpt from citation object
    ref: CitationReference
    if hasattr(citation, "citation") and hasattr(citation, "claim_id"):
        # ClaimCitationRecord instance
        ref = getattr(citation, "citation")
        if cited_excerpt is None:
            cited_excerpt = getattr(citation, "cited_excerpt")
        if getattr(citation, "factual_support", None) != "not_evaluated":
            raise GenerationContractError("factual_support must be 'not_evaluated'")
    elif isinstance(citation, CitationReference):
        ref = citation
    else:
        raise GenerationContractError("citation must be a CitationReference or ClaimCitationRecord instance")

    if not isinstance(ref, CitationReference):
        raise GenerationContractError("citation reference must be a CitationReference instance")

    # 2. Resolve target chunk from chunk_or_evidence
    chunk: SourceChunk | None = None
    if isinstance(chunk_or_evidence, SourceChunk):
        if chunk_or_evidence.chunk_id != ref.chunk_id:
            raise CitationGroundingError(
                f"Citation chunk_id '{ref.chunk_id}' does not match chunk '{chunk_or_evidence.chunk_id}'"
            )
        chunk = chunk_or_evidence
    elif isinstance(chunk_or_evidence, EvidenceRetrievalResult):
        hit_map = {hit.chunk.chunk_id: hit.chunk for hit in chunk_or_evidence.retrieval_result.hits}
        chunk = hit_map.get(ref.chunk_id)
        if chunk is None:
            raise CitationGroundingError(
                f"Claim references chunk '{ref.chunk_id}' not found in retrieval result hits"
            )
    elif isinstance(chunk_or_evidence, RetrievalResult):
        hit_map = {hit.chunk.chunk_id: hit.chunk for hit in chunk_or_evidence.hits}
        chunk = hit_map.get(ref.chunk_id)
        if chunk is None:
            raise CitationGroundingError(
                f"Claim references chunk '{ref.chunk_id}' not found in retrieval result hits"
            )
    elif isinstance(chunk_or_evidence, dict):
        chunk = chunk_or_evidence.get(ref.chunk_id)
        if chunk is None:
            raise CitationGroundingError(
                f"Claim references chunk '{ref.chunk_id}' not found in evidence chunks"
            )
    elif hasattr(chunk_or_evidence, "chunks") and isinstance(getattr(chunk_or_evidence, "chunks"), tuple):
        chunk_map = {c.chunk_id: c for c in getattr(chunk_or_evidence, "chunks") if isinstance(c, SourceChunk)}
        chunk = chunk_map.get(ref.chunk_id)
        if chunk is None:
            raise CitationGroundingError(
                f"Claim references chunk '{ref.chunk_id}' not found in evidence bundle chunks"
            )
    elif isinstance(chunk_or_evidence, (tuple, list)):
        chunk_map = {c.chunk_id: c for c in chunk_or_evidence if isinstance(c, SourceChunk)}
        chunk = chunk_map.get(ref.chunk_id)
        if chunk is None:
            raise CitationGroundingError(
                f"Claim references chunk '{ref.chunk_id}' not found in evidence chunks"
            )
    else:
        raise GenerationContractError(
            "chunk_or_evidence must be a SourceChunk, RetrievalResult, EvidenceRetrievalResult, EvidenceBundle, or chunk mapping"
        )

    # 3. Verify source_id matches chunk provenance
    chunk_source_id = ""
    if hasattr(chunk, "provenance") and hasattr(chunk.provenance, "source_id"):
        chunk_source_id = chunk.provenance.source_id
    elif hasattr(chunk, "source_id"):
        chunk_source_id = getattr(chunk, "source_id")

    if ref.source_id != chunk_source_id:
        raise CitationGroundingError(
            f"Citation source_id '{ref.source_id}' does not match chunk's source_id '{chunk_source_id}'"
        )

    # 4. Check cited_excerpt
    if cited_excerpt is None or cited_excerpt == "":
        return

    if not isinstance(cited_excerpt, str):
        raise GenerationContractError("cited_excerpt must be a string or None")

    # Verbatim substring match without silent normalization
    if cited_excerpt not in chunk.content:
        raise CitationGroundingError(
            f"Cited excerpt does not occur verbatim in chunk '{chunk.chunk_id}' content"
        )


def evaluate_individual_claim(
    claim: GeneratedClaim,
    hit_map: dict[str, SourceChunk],
    retrieval_result: RetrievalResult,
    *,
    unsupported_markers: tuple[str, ...] = (
        "automatically sanitize",
        "unsupported_claim",
        "[UNSUPPORTED]",
    ),
    claim_citations: tuple[object, ...] | None = None,
) -> ClaimValidationResult:
    """Validate claim-level citations and evaluate explicit evidence sufficiency."""
    # Structural citation checks
    if len(claim.citations) == 0:
        raise GenerationContractError("claim citations must be a non-empty tuple")

    # Check duplicates within claim
    keys = [(ref.source_id, ref.chunk_id) for ref in claim.citations]
    if len(keys) != len(set(keys)):
        raise GenerationContractError("claim citations must not contain duplicate references")

    validation = validate_citation_references(claim.citations, retrieval_result)
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
                f"Citation source_id '{first_issue.reference.source_id}' does not match chunk's source_id '{actual_source}'"
            )
        else:
            raise CitationGroundingError(f"Claim citation rejected: {first_issue.reason}")

    # Excerpt validation if claim_citations are provided
    if claim_citations:
        for cc in claim_citations:
            validate_citation_excerpt(cc, hit_map)

    # Explicit sufficiency evaluation
    supported = is_claim_supported_by_chunks(claim, hit_map, unsupported_markers=unsupported_markers)
    if not supported:
        return ClaimValidationResult(
            claim=claim,
            classification=EvidenceSufficiencyClassification.INSUFFICIENT_EVIDENCE,
            is_valid=False,
            citations_validated=claim.citations,
            reason="Claim lacks sufficient evidentiary support in cited chunk(s)",
            factual_support="not_evaluated",
        )

    return ClaimValidationResult(
        claim=claim,
        classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
        is_valid=True,
        citations_validated=claim.citations,
        reason=None,
        factual_support="not_evaluated",
    )


def validate_claims_and_evidence(
    request: GenerationRequest | EvidenceRetrievalResult,
    result: GenerationResult,
    *,
    conflict_rules: tuple[ConflictRule, ...] = DEFAULT_CONFLICT_RULES,
    min_evidence_score: float = 0.0,
    unsupported_markers: tuple[str, ...] = (
        "automatically sanitize",
        "unsupported_claim",
        "[UNSUPPORTED]",
    ),
    claim_citations: tuple[object, ...] | None = None,
) -> GatedGenerationResult:
    """Evaluate evidence and claim-level validations, returning a structured GatedGenerationResult."""
    # 1. Input Contract Precondition Validation
    if isinstance(request, EvidenceRetrievalResult):
        request = GenerationRequest(evidence=request)
    elif not isinstance(request, GenerationRequest):
        raise GenerationContractError("request must be GenerationRequest or EvidenceRetrievalResult")

    if not isinstance(request.evidence, EvidenceRetrievalResult):
        raise GenerationContractError("evidence must be an EvidenceRetrievalResult instance")

    if not isinstance(result, GenerationResult):
        raise GenerationContractError("result must be a GenerationResult instance")

    evidence = request.evidence

    # Check NO_APPROVED_EVIDENCE state
    if evidence.status == "no_approved_evidence":
        validate_generation_result(result, evidence)
        return GatedGenerationResult(
            generation_result=result,
            overall_classification=EvidenceSufficiencyClassification.NO_APPROVED_EVIDENCE,
            claim_validations=(),
            factual_support="not_evaluated",
        )

    hits = evidence.retrieval_result.hits
    if len(hits) == 0:
        validate_generation_result(result, evidence)
        return GatedGenerationResult(
            generation_result=result,
            overall_classification=EvidenceSufficiencyClassification.NO_APPROVED_EVIDENCE,
            claim_validations=(),
            factual_support="not_evaluated",
        )

    # Check CONFLICTING_EVIDENCE state
    if has_explicit_conflicts(hits, conflict_rules):
        return GatedGenerationResult(
            generation_result=result,
            overall_classification=EvidenceSufficiencyClassification.CONFLICTING_EVIDENCE,
            claim_validations=(),
            factual_support="not_evaluated",
        )

    # Check GLOBAL INSUFFICIENT_EVIDENCE state
    if is_globally_insufficient(hits, min_evidence_score):
        return GatedGenerationResult(
            generation_result=result,
            overall_classification=EvidenceSufficiencyClassification.INSUFFICIENT_EVIDENCE,
            claim_validations=(),
            factual_support="not_evaluated",
        )

    # Structural response validation
    validate_generation_result(result, evidence)

    if result.status == "abstained":
        classification = (
            EvidenceSufficiencyClassification.CONFLICTING_EVIDENCE
            if result.abstention_reason == "conflicting_evidence"
            else EvidenceSufficiencyClassification.INSUFFICIENT_EVIDENCE
        )
        return GatedGenerationResult(
            generation_result=result,
            overall_classification=classification,
            claim_validations=(),
            factual_support="not_evaluated",
        )

    # Evaluate each claim individually
    hit_map = {hit.chunk.chunk_id: hit.chunk for hit in hits}
    claim_results: list[ClaimValidationResult] = []
    has_insufficient = False

    for claim in result.claims:
        c_res = evaluate_individual_claim(
            claim,
            hit_map,
            evidence.retrieval_result,
            unsupported_markers=unsupported_markers,
            claim_citations=claim_citations,
        )
        claim_results.append(c_res)
        if not c_res.is_valid:
            has_insufficient = True

    overall = (
        EvidenceSufficiencyClassification.INSUFFICIENT_EVIDENCE
        if has_insufficient
        else EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE
    )

    return GatedGenerationResult(
        generation_result=result,
        overall_classification=overall,
        claim_validations=tuple(claim_results),
        factual_support="not_evaluated",
    )


def validate_and_gate_generation(
    request: GenerationRequest | EvidenceRetrievalResult,
    generator: Generator,
    *,
    conflict_rules: tuple[ConflictRule, ...] = DEFAULT_CONFLICT_RULES,
    min_evidence_score: float = 0.0,
    unsupported_markers: tuple[str, ...] = (
        "automatically sanitize",
        "unsupported_claim",
        "[UNSUPPORTED]",
    ),
    claim_citations: tuple[object, ...] | None = None,
) -> GenerationResult:
    """Execute provider-neutral generation with deterministic evidence and claim validation gating.

    Precedence order:
    1. Input Contract Preconditions: Malformed requests immediately raise GenerationContractError.
    2. Gate 1 (NO_APPROVED_EVIDENCE): Short-circuits without calling generator seam.
    3. Gate 2 (CONFLICTING_EVIDENCE): Abstains with 'conflicting_evidence' without calling generator.
    4. Gate 3 (INSUFFICIENT_EVIDENCE): Abstains with 'insufficient_evidence' if hits fail criteria.
    5. Generator Invocation: Unhandled exceptions propagate unconverted.
    6. Gate 4 (OUTPUT_CONTRACT_VALIDATION): Structural response validation.
    7. Gate 5 (CLAIM_SUFFICIENCY_GATING): Fail-closed response gating if any claim lacks sufficiency.
    8. Gate 6 (SUFFICIENT_EVIDENCE): Returns answered result.
    """
    # 1. Input Contract Precondition Validation
    if isinstance(request, EvidenceRetrievalResult):
        request = GenerationRequest(evidence=request)
    elif not isinstance(request, GenerationRequest):
        raise GenerationContractError("request must be GenerationRequest or EvidenceRetrievalResult")

    if not isinstance(request.evidence, EvidenceRetrievalResult):
        raise GenerationContractError("evidence must be an EvidenceRetrievalResult instance")

    evidence = request.evidence

    # 2. Gate 1: Check for Empty / Unapproved Evidence (Short-Circuit)
    if evidence.status == "no_approved_evidence":
        reason = "no_approved_sources" if evidence.approved_source_count == 0 else "no_retrieved_chunks"
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

    # 3. Gate 2: Detect Explicit Evidence Conflicts
    if has_explicit_conflicts(hits, conflict_rules):
        return GenerationResult(
            status="abstained",
            claims=(),
            abstention_reason="conflicting_evidence",
            query_text=evidence.query_text,
            factual_support="not_evaluated",
        )

    # 4. Gate 3: Detect Global Evidence Insufficiency
    if is_globally_insufficient(hits, min_evidence_score):
        return GenerationResult(
            status="abstained",
            claims=(),
            abstention_reason="insufficient_evidence",
            query_text=evidence.query_text,
            factual_support="not_evaluated",
        )

    # 5. Generator Invocation (Exceptions propagate unconverted)
    raw_result = generator.generate(request)

    # 6. Gate 4: Structural Response Validation
    validate_generation_result(raw_result, evidence)

    # If generator explicitly chose to abstain, return validated abstention
    if raw_result.status == "abstained":
        return raw_result

    # 7. Gate 5: Claim-Level Citation Grounding & Sufficiency (Fail-Closed)
    hit_map = {hit.chunk.chunk_id: hit.chunk for hit in hits}

    for claim in raw_result.claims:
        c_res = evaluate_individual_claim(
            claim,
            hit_map,
            evidence.retrieval_result,
            unsupported_markers=unsupported_markers,
            claim_citations=claim_citations,
        )
        if not c_res.is_valid:
            # Fail closed: even if other claims are supported, one unsupported claim forces response abstention
            return GenerationResult(
                status="abstained",
                claims=(),
                abstention_reason="insufficient_evidence",
                query_text=evidence.query_text,
                factual_support="not_evaluated",
            )

    # 8. All gates passed: return answered result
    return raw_result
