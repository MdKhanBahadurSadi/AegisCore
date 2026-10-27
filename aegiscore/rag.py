"""Offline source, chunk, retrieval, and citation contracts for the RAG core.

This module performs local file reads only. It has no network, DNS, target
transport, embedding, vector-store, LLM, or agent integration.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Literal, Protocol


class RagContractError(ValueError):
    """A source, chunk, retrieval, or citation contract is invalid."""


class SourceIngestionError(RagContractError):
    """A local source could not be safely ingested."""


class SourcePathError(SourceIngestionError):
    """A source path is invalid or escapes the designated root."""


class UnsupportedSourceError(SourceIngestionError):
    """The source file type is not supported by offline ingestion."""


class EmptySourceError(SourceIngestionError):
    """The source is empty or contains only whitespace."""


class MalformedSourceError(SourceIngestionError):
    """The source file is not valid UTF-8 text."""


class SourceTooLargeError(SourceIngestionError):
    """The source exceeds the configured byte limit."""


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MARKDOWN_HEADING = re.compile(r"(?m)^#{1,6}[ \t]+([^\r\n]+)")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_MAX_CHUNK_SIZE_CHARS = 65_536
_MAX_SOURCE_BYTES = 16 * 1024 * 1024


class SourceReviewState(str, Enum):
    """Registry state for one exact source-content revision."""

    CANDIDATE = "candidate"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"


def _nonempty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RagContractError(f"{field} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise RagContractError(f"{field} contains a forbidden control character")
    return value


def _identifier(value: object, field: str) -> str:
    text = _nonempty_text(value, field)
    if not _IDENTIFIER.fullmatch(text):
        raise RagContractError(f"{field} has an invalid identifier format")
    return text


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise RagContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty_text(value, field)


@dataclass(frozen=True, slots=True)
class SourceDetails:
    """Caller-supplied descriptive metadata; no field is inferred or verified."""

    title: str | None = None
    publisher: str | None = None
    canonical_reference: str | None = None
    publication_date: str | None = None
    version: str | None = None
    acquired_at: str | None = None
    source_type: str | None = None
    scope_tags: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for field in (
            "title",
            "publisher",
            "canonical_reference",
            "publication_date",
            "version",
            "acquired_at",
            "source_type",
        ):
            _optional_text(getattr(self, field), field)
        _scope_tags(self.scope_tags)


def _scope_tags(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, tuple):
        raise RagContractError("scope_tags must be a tuple when provided")
    for tag in value:
        _identifier(tag, "scope tag")
    if len(set(value)) != len(value):
        raise RagContractError("scope_tags must not contain duplicates")
    return value


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Provenance recorded for one source; absent descriptive facts stay unknown."""

    source_id: str
    content_sha256: str
    local_path: str | None = None
    canonical_reference: str | None = None
    title: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    version: str | None = None
    acquired_at: str | None = None
    source_type: str | None = None
    scope_tags: tuple[str, ...] | None = None
    review_state: SourceReviewState = SourceReviewState.CANDIDATE

    def __post_init__(self) -> None:
        _identifier(self.source_id, "source_id")
        _digest(self.content_sha256, "content_sha256")
        for field in (
            "canonical_reference",
            "title",
            "publisher",
            "publication_date",
            "version",
            "acquired_at",
            "source_type",
        ):
            _optional_text(getattr(self, field), field)
        _scope_tags(self.scope_tags)
        if self.local_path is not None:
            local_path = _nonempty_text(self.local_path, "local_path")
            canonical_path = PurePosixPath(local_path)
            if (
                canonical_path.is_absolute()
                or any(part in {".", ".."} for part in canonical_path.parts)
                or canonical_path.as_posix() != local_path
                or "\\" in local_path
            ):
                raise RagContractError("local_path must be a canonical relative POSIX path")
        if not isinstance(self.review_state, SourceReviewState):
            raise RagContractError("review_state must be SourceReviewState")


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Decoded UTF-8 source text paired with its content digest and provenance."""

    metadata: SourceMetadata
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, SourceMetadata):
            raise RagContractError("metadata must be SourceMetadata")
        if not isinstance(self.content, str) or not self.content.strip():
            raise RagContractError("source content must be non-empty text")
        actual = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if actual != self.metadata.content_sha256:
            raise RagContractError("source content does not match its recorded digest")


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Deterministic character-window settings and local source-file bound."""

    chunk_size_chars: int = 1_200
    overlap_chars: int = 150
    max_source_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        for field in ("chunk_size_chars", "overlap_chars", "max_source_bytes"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int):
                raise RagContractError(f"{field} must be an integer")
        if not 1 <= self.chunk_size_chars <= _MAX_CHUNK_SIZE_CHARS:
            raise RagContractError("chunk_size_chars is outside the supported range")
        if not 0 <= self.overlap_chars < self.chunk_size_chars:
            raise RagContractError("overlap_chars must be non-negative and smaller than chunk size")
        if not 1 <= self.max_source_bytes <= _MAX_SOURCE_BYTES:
            raise RagContractError("max_source_bytes is outside the supported range")


@dataclass(frozen=True, slots=True)
class SourceChunk:
    """One deterministic text window with source and positional provenance."""

    chunk_id: str
    provenance: SourceMetadata
    ordinal: int
    start_offset: int
    end_offset: int
    content: str
    content_sha256: str
    section: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.chunk_id, "chunk_id")
        if not isinstance(self.provenance, SourceMetadata):
            raise RagContractError("provenance must be SourceMetadata")
        for field in ("ordinal", "start_offset", "end_offset"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RagContractError(f"{field} must be a non-negative integer")
        if self.end_offset <= self.start_offset:
            raise RagContractError("chunk end_offset must be greater than start_offset")
        if not isinstance(self.content, str) or len(self.content) != self.end_offset - self.start_offset:
            raise RagContractError("chunk content length must match its character offsets")
        _digest(self.content_sha256, "content_sha256")
        if hashlib.sha256(self.content.encode("utf-8")).hexdigest() != self.content_sha256:
            raise RagContractError("chunk content does not match its recorded digest")
        _optional_text(self.section, "section")


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """A source plus its ordered chunks and the configuration used to create them."""

    source: SourceDocument
    chunks: tuple[SourceChunk, ...]
    chunking: ChunkingConfig

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceDocument):
            raise RagContractError("source must be SourceDocument")
        if not isinstance(self.chunking, ChunkingConfig):
            raise RagContractError("chunking must be ChunkingConfig")
        if not isinstance(self.chunks, tuple) or not self.chunks:
            raise RagContractError("chunks must be a non-empty tuple")
        seen: set[str] = set()
        for index, chunk in enumerate(self.chunks):
            if not isinstance(chunk, SourceChunk):
                raise RagContractError("every chunk must be SourceChunk")
            if chunk.ordinal != index or chunk.chunk_id in seen:
                raise RagContractError("chunk order or identity is invalid")
            if chunk.provenance != self.source.metadata:
                raise RagContractError("chunk provenance does not match its source")
            if self.source.content[chunk.start_offset : chunk.end_offset] != chunk.content:
                raise RagContractError("chunk content does not match its source offsets")
            seen.add(chunk.chunk_id)


def _canonical_local_path(source_root: str | os.PathLike[str], relative_path: str | os.PathLike[str]) -> tuple[Path, str]:
    try:
        root = Path(source_root).resolve(strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise SourcePathError("knowledge-base source root is missing or invalid") from exc
    if not root.is_dir():
        raise SourcePathError("knowledge-base source root must be a directory")

    try:
        raw_path = os.fspath(relative_path)
    except (TypeError, ValueError) as exc:
        raise SourcePathError("source path must be a relative path") from exc
    if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
        raise SourcePathError("source path must be a non-empty relative path")
    windows_path = PureWindowsPath(raw_path)
    if Path(raw_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise SourcePathError("absolute source paths are not accepted")

    portable_path = PurePosixPath(raw_path.replace("\\", "/"))
    if not portable_path.parts or any(part == ".." for part in portable_path.parts):
        raise SourcePathError("source path traversal is not accepted")
    candidate = root.joinpath(*portable_path.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SourcePathError("source file does not exist or cannot be resolved") from exc
    try:
        local_path = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise SourcePathError("resolved source path escapes the designated root") from exc
    if local_path in {"", "."}:
        raise SourcePathError("source path must name a file inside the designated root")
    return resolved, local_path


def _section_for_offset(content: str, offset: int) -> str | None:
    section: str | None = None
    for match in _MARKDOWN_HEADING.finditer(content):
        if match.start() > offset:
            break
        candidate = match.group(1).strip().rstrip("#").strip()
        section = candidate or None
    return section


def chunk_document(document: SourceDocument, config: ChunkingConfig) -> tuple[SourceChunk, ...]:
    """Split a source into reproducible character windows with half-open offsets."""

    if not isinstance(document, SourceDocument) or not isinstance(config, ChunkingConfig):
        raise RagContractError("document and chunking config are required")
    content = document.content
    step = config.chunk_size_chars - config.overlap_chars
    chunks: list[SourceChunk] = []
    start = 0
    ordinal = 0
    while start < len(content):
        end = min(start + config.chunk_size_chars, len(content))
        piece = content[start:end]
        identity_material = "\0".join(
            (
                document.metadata.source_id,
                document.metadata.content_sha256,
                str(config.chunk_size_chars),
                str(config.overlap_chars),
                str(config.max_source_bytes),
                str(ordinal),
                str(start),
                str(end),
            )
        )
        chunk_id = "chk_" + hashlib.sha256(identity_material.encode("utf-8")).hexdigest()
        chunks.append(
            SourceChunk(
                chunk_id=chunk_id,
                provenance=document.metadata,
                ordinal=ordinal,
                start_offset=start,
                end_offset=end,
                content=piece,
                content_sha256=hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                section=_section_for_offset(content, start),
            )
        )
        if end == len(content):
            break
        start += step
        ordinal += 1
    return tuple(chunks)


def ingest_local_file(
    source_root: str | os.PathLike[str],
    relative_path: str | os.PathLike[str],
    *,
    chunking: ChunkingConfig = ChunkingConfig(),
    details: SourceDetails | None = None,
) -> IngestionResult:
    """Read one explicitly named UTF-8 text/Markdown file below source_root.

    This function does not enumerate directories, download sources, or assign
    approval. The returned metadata always marks the source as a review candidate.
    """

    if not isinstance(chunking, ChunkingConfig):
        raise SourceIngestionError("chunking config is missing or invalid")
    if details is not None and not isinstance(details, SourceDetails):
        raise SourceIngestionError("details must be SourceDetails when provided")
    path, local_path = _canonical_local_path(source_root, relative_path)
    if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
        raise UnsupportedSourceError("only UTF-8 .txt, .md, and .markdown files are supported")
    if not path.is_file():
        raise SourcePathError("source path must refer to a regular file")
    try:
        with path.open("rb") as source_file:
            raw_content = source_file.read(chunking.max_source_bytes + 1)
    except OSError as exc:
        raise SourceIngestionError("source file could not be read") from exc
    if len(raw_content) > chunking.max_source_bytes:
        raise SourceTooLargeError("source exceeds the configured max_source_bytes")
    try:
        content = raw_content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise MalformedSourceError("source file must be valid UTF-8") from exc
    if not content.strip():
        raise EmptySourceError("source file is empty or whitespace-only")

    source_id = "src_" + hashlib.sha256(local_path.encode("utf-8")).hexdigest()
    supplied = details or SourceDetails()
    metadata = SourceMetadata(
        source_id=source_id,
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        local_path=local_path,
        canonical_reference=supplied.canonical_reference,
        title=supplied.title,
        publisher=supplied.publisher,
        publication_date=supplied.publication_date,
        version=supplied.version,
        acquired_at=supplied.acquired_at,
        source_type=supplied.source_type,
        scope_tags=supplied.scope_tags,
    )
    document = SourceDocument(metadata=metadata, content=content)
    chunks = chunk_document(document, chunking)
    return IngestionResult(source=document, chunks=chunks, chunking=chunking)


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Provider-neutral request for ranked chunks; no authorization semantics."""

    text: str
    top_k: int = 5
    source_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        _nonempty_text(self.text, "query text")
        if isinstance(self.top_k, bool) or not isinstance(self.top_k, int) or not 1 <= self.top_k <= 100:
            raise RagContractError("top_k must be an integer from 1 through 100")
        if self.source_ids is not None:
            if not isinstance(self.source_ids, tuple):
                raise RagContractError("source_ids must be a tuple when provided")
            for source_id in self.source_ids:
                _identifier(source_id, "source_id")
            if len(set(self.source_ids)) != len(self.source_ids):
                raise RagContractError("source_ids must not contain duplicates")


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    """Provider-neutral retrieval provenance, not a truth or confidence score."""

    retriever_id: str
    query_sha256: str
    candidate_count: int

    def __post_init__(self) -> None:
        _identifier(self.retriever_id, "retriever_id")
        _digest(self.query_sha256, "query_sha256")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int) or self.candidate_count < 0:
            raise RagContractError("candidate_count must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """One ranked chunk and retriever-specific relevance metadata."""

    chunk: SourceChunk
    rank: int
    score: float | None = None
    score_kind: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.chunk, SourceChunk):
            raise RagContractError("retrieval hit chunk must be SourceChunk")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 1:
            raise RagContractError("retrieval rank must be a positive integer")
        if self.score is not None and (
            isinstance(self.score, bool) or not isinstance(self.score, (int, float)) or not math.isfinite(self.score)
        ):
            raise RagContractError("retrieval score must be a finite number or None")
        _optional_text(self.score_kind, "score_kind")


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Stable ordered hits plus metadata describing how retrieval was performed."""

    metadata: RetrievalMetadata
    hits: tuple[RetrievalHit, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, RetrievalMetadata):
            raise RagContractError("retrieval metadata is required")
        if not isinstance(self.hits, tuple):
            raise RagContractError("retrieval hits must be a tuple")
        identifiers: set[str] = set()
        for expected_rank, hit in enumerate(self.hits, 1):
            if not isinstance(hit, RetrievalHit) or hit.rank != expected_rank:
                raise RagContractError("retrieval hits must have contiguous ranks starting at one")
            if hit.chunk.chunk_id in identifiers:
                raise RagContractError("retrieval result contains duplicate chunk IDs")
            identifiers.add(hit.chunk.chunk_id)


class Retriever(Protocol):
    """Provider-neutral retrieval interface; implementations may be injected."""

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Return ranked chunks with source provenance and retrieval metadata."""


class InMemoryTestRetriever:
    """Deterministic lexical test double; this is not semantic or production RAG."""

    retriever_id = "in_memory_lexical_test_double"

    def __init__(self, chunks: Iterable[SourceChunk]) -> None:
        try:
            items = tuple(chunks)
        except TypeError as exc:
            raise RagContractError("chunks must be an iterable of SourceChunk") from exc
        if any(not isinstance(chunk, SourceChunk) for chunk in items):
            raise RagContractError("chunks must contain only SourceChunk values")
        identifiers = [chunk.chunk_id for chunk in items]
        if len(identifiers) != len(set(identifiers)):
            raise RagContractError("test retriever chunks must have unique IDs")
        self._chunks = tuple(sorted(items, key=lambda chunk: chunk.chunk_id))

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        if not isinstance(query, RetrievalQuery):
            raise RagContractError("query must be RetrievalQuery")
        allowed_sources = set(query.source_ids) if query.source_ids is not None else None
        query_terms = {token.casefold() for token in _TOKEN.findall(query.text)}
        scored: list[tuple[int, SourceChunk]] = []
        candidates = [
            chunk
            for chunk in self._chunks
            if allowed_sources is None or chunk.provenance.source_id in allowed_sources
        ]
        for chunk in candidates:
            overlap = len(query_terms & {token.casefold() for token in _TOKEN.findall(chunk.content)})
            if overlap:
                scored.append((overlap, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        hits = tuple(
            RetrievalHit(chunk=chunk, rank=rank, score=float(score), score_kind="token_overlap_count")
            for rank, (score, chunk) in enumerate(scored[: query.top_k], 1)
        )
        metadata = RetrievalMetadata(
            retriever_id=self.retriever_id,
            query_sha256=hashlib.sha256(query.text.encode("utf-8")).hexdigest(),
            candidate_count=len(candidates),
        )
        return RetrievalResult(metadata=metadata, hits=hits)


@dataclass(frozen=True, slots=True)
class CitationReference:
    """A claimed source/chunk pair to validate against one retrieval result."""

    source_id: str
    chunk_id: str

    def __post_init__(self) -> None:
        _identifier(self.source_id, "source_id")
        _identifier(self.chunk_id, "chunk_id")


CitationIssueReason = Literal["chunk_not_retrieved", "source_id_mismatch", "provenance_unavailable"]


@dataclass(frozen=True, slots=True)
class CitationIssue:
    reference: CitationReference
    reason: CitationIssueReason


@dataclass(frozen=True, slots=True)
class CitationValidation:
    """Reference membership/provenance result; it does not verify factual claims."""

    references_supplied: int
    accepted: tuple[CitationReference, ...]
    rejected: tuple[CitationIssue, ...]
    factual_support: Literal["not_evaluated"] = "not_evaluated"

    def __post_init__(self) -> None:
        if self.factual_support != "not_evaluated":
            raise RagContractError("citation validation cannot establish factual support")

    @property
    def valid(self) -> bool:
        return self.references_supplied > 0 and len(self.accepted) == self.references_supplied and not self.rejected


def validate_citation_references(
    references: Iterable[CitationReference], retrieval: RetrievalResult
) -> CitationValidation:
    """Accept only references found in retrieval with a source path or reference.

    Passing this check establishes reference membership and recorded provenance
    availability only. It does not establish source authority or factual support.
    """

    if not isinstance(retrieval, RetrievalResult):
        raise RagContractError("retrieval must be RetrievalResult")
    try:
        supplied = tuple(references)
    except TypeError as exc:
        raise RagContractError("references must be iterable") from exc
    if any(not isinstance(reference, CitationReference) for reference in supplied):
        raise RagContractError("references must contain only CitationReference values")
    by_chunk = {hit.chunk.chunk_id: hit.chunk for hit in retrieval.hits}
    accepted: list[CitationReference] = []
    rejected: list[CitationIssue] = []
    for reference in supplied:
        chunk = by_chunk.get(reference.chunk_id)
        if chunk is None:
            rejected.append(CitationIssue(reference, "chunk_not_retrieved"))
        elif reference.source_id != chunk.provenance.source_id:
            rejected.append(CitationIssue(reference, "source_id_mismatch"))
        elif not (chunk.provenance.local_path or chunk.provenance.canonical_reference):
            rejected.append(CitationIssue(reference, "provenance_unavailable"))
        else:
            accepted.append(reference)
    return CitationValidation(len(supplied), tuple(accepted), tuple(rejected))
