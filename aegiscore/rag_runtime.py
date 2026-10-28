"""Approved-only evidence retrieval runtime for AegisCore.

This module provides provider-neutral, deterministic evidence retrieval using
only verified chunks returned by the PersistentSourceReviewRegistry approved-source
selector. It performs offline lexical retrieval and returns structured evidence
bundles with source provenance, strict threshold validation, and strict citation
representation, failing closed on any registry inconsistency or integrity violation.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Literal

from aegiscore.rag import (
    CitationReference,
    InMemoryTestRetriever,
    RetrievalHit,
    RetrievalMetadata,
    RetrievalQuery,
    RetrievalResult,
    SourceChunk,
    _nonempty_text,
    RagContractError,
)
from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    SourceReviewError,
)


class RagRuntimeError(RagContractError):
    """The RAG runtime encountered an invalid configuration, state, or query."""


RetrievalStatus = Literal["evidence_found", "no_approved_evidence"]


@dataclass(frozen=True, slots=True)
class EvidenceRetrievalResult:
    """Structured evidence bundle for downstream answer-generation components."""

    query_text: str
    status: RetrievalStatus
    retrieval_result: RetrievalResult
    approved_source_count: int
    citations: tuple[CitationReference, ...]

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.query_text, "query_text")
        except RagContractError as exc:
            raise RagRuntimeError(str(exc)) from exc
        if self.status not in {"evidence_found", "no_approved_evidence"}:
            raise RagRuntimeError("status must be evidence_found or no_approved_evidence")
        if not isinstance(self.retrieval_result, RetrievalResult):
            raise RagRuntimeError("retrieval_result must be RetrievalResult")
        if isinstance(self.approved_source_count, bool) or not isinstance(self.approved_source_count, int) or self.approved_source_count < 0:
            raise RagRuntimeError("approved_source_count must be a non-negative integer")
        if not isinstance(self.citations, tuple) or any(not isinstance(c, CitationReference) for c in self.citations):
            raise RagRuntimeError("citations must be a tuple of CitationReference")

        # Invariant checks
        if self.status == "no_approved_evidence":
            if len(self.retrieval_result.hits) > 0 or len(self.citations) > 0:
                raise RagRuntimeError("no_approved_evidence status must have zero hits and zero citations")
        elif self.status == "evidence_found":
            if len(self.retrieval_result.hits) == 0:
                raise RagRuntimeError("evidence_found status requires at least one retrieval hit")
            if len(self.citations) == 0:
                raise RagRuntimeError("evidence_found status requires at least one citation reference")

            # Check duplicate citations
            if len(self.citations) != len(set((c.source_id, c.chunk_id) for c in self.citations)):
                raise RagRuntimeError("citations must not contain duplicate references")

            hit_map = {hit.chunk.chunk_id: hit.chunk for hit in self.retrieval_result.hits}
            for ref in self.citations:
                hit_chunk = hit_map.get(ref.chunk_id)
                if hit_chunk is None or hit_chunk.provenance.source_id != ref.source_id:
                    raise RagRuntimeError("citation reference must match a retrieved chunk and source ID in the evidence bundle")


def validate_min_score(min_score: float) -> float:
    """Validate min_score to be a finite numeric value within a bounded range."""
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)):
        raise RagRuntimeError("min_score must be a finite numeric value")
    if not math.isfinite(min_score):
        raise RagRuntimeError("min_score must be finite (cannot be NaN or infinity)")
    if not 0.0 <= min_score <= 1000.0:
        raise RagRuntimeError("min_score must be between 0.0 and 1000.0")
    return float(min_score)


def retrieve_approved_evidence(
    query_text: str,
    registry: PersistentSourceReviewRegistry,
    *,
    top_k: int = 5,
    min_score: float = 1.0,
    source_ids: tuple[str, ...] | None = None,
) -> EvidenceRetrievalResult:
    """Retrieve ranked evidence chunks exclusively from verified approved sources.

    Validates min_score and query parameters before touching the registry.
    Requires an explicit read-only registry opened via PersistentSourceReviewRegistry.open_existing().
    Fails closed if the registry is unavailable, the manifest/database is inconsistent,
    source integrity checks fail, or the registry database file does not exist.
    Abstains (returning no_approved_evidence) if no approved sources exist or no chunks
    meet the relevance threshold.
    """
    # 1. Validate configuration and query parameters before touching registry
    validated_min_score = validate_min_score(min_score)

    try:
        query = RetrievalQuery(text=query_text, top_k=top_k, source_ids=source_ids)
    except (RagContractError, ValueError, TypeError) as exc:
        raise RagRuntimeError(f"Invalid retrieval query parameters: {exc}") from exc

    if not isinstance(registry, PersistentSourceReviewRegistry):
        raise RagRuntimeError("registry must be PersistentSourceReviewRegistry")

    try:
        # Never use the supplied instance as proof of read-only provenance. Reopen
        # its paths through the explicit non-bootstrapping API so a caller-mutated
        # `_is_read_only` flag cannot select a writable connection here.
        read_only_registry = PersistentSourceReviewRegistry.open_existing(
            registry.database_path,
            manifest_path=registry.manifest_path,
            repository_root=registry.repository_root,
        )
    except (SourceReviewError, sqlite3.Error, OSError) as exc:
        raise RagRuntimeError(f"Read-only registry open failed: {exc}") from exc

    try:
        approved_chunks = read_only_registry.approved_chunks()
    except (SourceReviewError, sqlite3.Error) as exc:
        raise RagRuntimeError("Approved-source selection failed closed") from exc

    approved_source_ids = {chunk.provenance.source_id for chunk in approved_chunks}
    approved_source_count = len(approved_source_ids)

    if not approved_chunks:
        empty_retriever = InMemoryTestRetriever(())
        empty_result = empty_retriever.retrieve(query)
        return EvidenceRetrievalResult(
            query_text=query.text,
            status="no_approved_evidence",
            retrieval_result=empty_result,
            approved_source_count=0,
            citations=(),
        )

    eligible_chunks = approved_chunks
    if query.source_ids is not None:
        allowed = set(query.source_ids)
        unapproved_requested = allowed - approved_source_ids
        if unapproved_requested:
            raise RagRuntimeError("Requested source_ids include unapproved or candidate sources")
        eligible_chunks = tuple(chunk for chunk in approved_chunks if chunk.provenance.source_id in allowed)

    retriever = InMemoryTestRetriever(eligible_chunks)
    try:
        result = retriever.retrieve(query)
    except (RagContractError, ValueError, TypeError) as exc:
        raise RagRuntimeError(f"Retrieval execution failed: {exc}") from exc

    filtered_hits = tuple(hit for hit in result.hits if hit.score is not None and hit.score >= validated_min_score)

    if filtered_hits:
        reranked_hits = tuple(
            RetrievalHit(
                chunk=hit.chunk,
                rank=new_rank,
                score=hit.score,
                score_kind=hit.score_kind,
            )
            for new_rank, hit in enumerate(filtered_hits, 1)
        )
        final_result = RetrievalResult(metadata=result.metadata, hits=reranked_hits)
        citations = tuple(
            CitationReference(source_id=hit.chunk.provenance.source_id, chunk_id=hit.chunk.chunk_id)
            for hit in reranked_hits
        )
        status: RetrievalStatus = "evidence_found"
    else:
        metadata = RetrievalMetadata(
            retriever_id=result.metadata.retriever_id,
            query_sha256=result.metadata.query_sha256,
            candidate_count=result.metadata.candidate_count,
        )
        final_result = RetrievalResult(metadata=metadata, hits=())
        citations = ()
        status = "no_approved_evidence"

    return EvidenceRetrievalResult(
        query_text=query.text,
        status=status,
        retrieval_result=final_result,
        approved_source_count=approved_source_count,
        citations=citations,
    )
