import hashlib
import socket
import urllib.request
from dataclasses import replace

import pytest

from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.rag import (
    ChunkingConfig,
    CitationReference,
    InMemoryTestRetriever,
    MalformedSourceError,
    RagContractError,
    RetrievalHit,
    RetrievalMetadata,
    RetrievalQuery,
    RetrievalResult,
    SourceChunk,
    SourceDetails,
    SourceIngestionError,
    SourceMetadata,
    SourceReviewState,
    SourcePathError,
    SourceTooLargeError,
    SourceDocument,
    EmptySourceError,
    UnsupportedSourceError,
    chunk_document,
    ingest_local_file,
    validate_citation_references,
)
from aegiscore.safety import PolicyEngine


def _document(content: str, *, source_id: str = "src_fixture", local_path: str | None = "fixture.md") -> SourceDocument:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    metadata = SourceMetadata(
        source_id=source_id,
        content_sha256=digest,
        local_path=local_path,
    )
    return SourceDocument(metadata=metadata, content=content)


def _ingest(root, name: str, content: str, *, config: ChunkingConfig | None = None, details=None):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ingest_local_file(root, name, chunking=config or ChunkingConfig(), details=details)


def test_source_and_chunk_contracts_validate_digests_and_unknown_metadata() -> None:
    document = _document("evidence stays contextual")
    chunks = chunk_document(document, ChunkingConfig(chunk_size_chars=8, overlap_chars=2))

    assert document.metadata.title is None
    assert document.metadata.publisher is None
    assert document.metadata.canonical_reference is None
    assert document.metadata.publication_date is None
    assert document.metadata.version is None
    assert chunks[0].provenance.source_id == document.metadata.source_id
    assert chunks[0].content_sha256 == hashlib.sha256(chunks[0].content.encode("utf-8")).hexdigest()

    with pytest.raises(RagContractError, match="source_id"):
        SourceMetadata(source_id="bad id", content_sha256=document.metadata.content_sha256)
    with pytest.raises(RagContractError, match="digest"):
        SourceDocument(metadata=document.metadata, content=document.content + " changed")
    with pytest.raises(RagContractError, match="chunk content"):
        replace(chunks[0], content_sha256="0" * 64)
    with pytest.raises(RagContractError, match="overlap"):
        ChunkingConfig(chunk_size_chars=4, overlap_chars=4)


def test_chunking_boundaries_overlap_offsets_and_markdown_section_metadata() -> None:
    config = ChunkingConfig(chunk_size_chars=5, overlap_chars=2)
    chunks = chunk_document(_document("abcdefghijk"), config)

    assert [chunk.content for chunk in chunks] == ["abcde", "defgh", "ghijk"]
    assert [(chunk.start_offset, chunk.end_offset) for chunk in chunks] == [(0, 5), (3, 8), (6, 11)]
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]

    markdown = _document("# Alpha\nabc\n# Beta\ndef")
    section_chunks = chunk_document(markdown, ChunkingConfig(chunk_size_chars=3, overlap_chars=0))
    assert "Alpha" in {chunk.section for chunk in section_chunks}
    assert "Beta" in {chunk.section for chunk in section_chunks}


def test_ingestion_is_stable_for_unchanged_content_and_changes_ids_when_source_changes(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    config = ChunkingConfig(chunk_size_chars=9, overlap_chars=2)
    first = _ingest(root, "guide/notes.md", "alpha beta gamma delta", config=config)
    unchanged = ingest_local_file(root, "guide/notes.md", chunking=config)

    assert first == unchanged
    changed = _ingest(root, "guide/notes.md", "alpha beta gamma delta!", config=config)
    assert changed.source.metadata.source_id == first.source.metadata.source_id
    assert changed.source.metadata.content_sha256 != first.source.metadata.content_sha256
    assert {chunk.chunk_id for chunk in changed.chunks}.isdisjoint({chunk.chunk_id for chunk in first.chunks})
    assert first.source.metadata.local_path == "guide/notes.md"
    assert first.source.metadata.review_state is SourceReviewState.CANDIDATE


def test_ingestion_preserves_only_caller_supplied_source_metadata(tmp_path) -> None:
    root = tmp_path / "kb"
    root.mkdir()
    result = _ingest(root, "reference.txt", "plain local text", details=SourceDetails(title="Provided title"))

    assert result.source.metadata.title == "Provided title"
    assert result.source.metadata.publisher is None
    assert result.source.metadata.canonical_reference is None
    assert result.source.metadata.publication_date is None
    assert result.source.metadata.version is None
    assert result.source.metadata.local_path == "reference.txt"
    assert result.source.metadata.review_state is SourceReviewState.CANDIDATE


@pytest.mark.parametrize(
    ("name", "data", "error"),
    [
        ("empty.txt", b"", EmptySourceError),
        ("spaces.md", b" \r\n\t", EmptySourceError),
        ("binary.md", b"\xff\xfe", MalformedSourceError),
        ("archive.pdf", b"text", UnsupportedSourceError),
    ],
)
def test_empty_malformed_and_unsupported_sources_fail_clearly(tmp_path, name, data, error) -> None:
    root = tmp_path / "kb"
    root.mkdir()
    (root / name).write_bytes(data)

    with pytest.raises(error):
        ingest_local_file(root, name)


def test_oversized_sources_are_rejected_using_configured_byte_limit(tmp_path) -> None:
    root = tmp_path / "kb"
    root.mkdir()
    (root / "large.txt").write_bytes(b"12345")

    with pytest.raises(SourceTooLargeError, match="max_source_bytes"):
        ingest_local_file(root, "large.txt", chunking=ChunkingConfig(max_source_bytes=4))


@pytest.mark.parametrize("relative_path", ["../outside.txt", "sub/../../outside.txt", "C:/outside.txt", "\\\\server\\share\\file.md"])
def test_absolute_and_traversal_paths_are_rejected(tmp_path, relative_path) -> None:
    root = tmp_path / "kb"
    root.mkdir()

    with pytest.raises(SourcePathError):
        ingest_local_file(root, relative_path)


def test_missing_root_and_missing_file_fail_closed(tmp_path) -> None:
    with pytest.raises(SourcePathError):
        ingest_local_file(tmp_path / "missing", "notes.md")

    root = tmp_path / "kb"
    root.mkdir()
    with pytest.raises(SourcePathError, match="does not exist"):
        ingest_local_file(root, "missing.md")


def test_provider_neutral_retrieval_interface_returns_ranked_chunks_and_metadata() -> None:
    alpha_chunks = chunk_document(_document("alpha beta alpha", source_id="src_alpha", local_path="alpha.md"), ChunkingConfig())
    beta_chunks = chunk_document(_document("alpha gamma", source_id="src_beta", local_path="beta.md"), ChunkingConfig())
    retriever = InMemoryTestRetriever((*alpha_chunks, *beta_chunks))
    query = RetrievalQuery("alpha beta", top_k=2)

    first = retriever.retrieve(query)
    second = retriever.retrieve(query)

    assert first == second
    assert first.metadata.retriever_id == "in_memory_lexical_test_double"
    assert first.metadata.candidate_count == 2
    assert first.hits[0].chunk.provenance.source_id == "src_alpha"
    assert first.hits[0].rank == 1
    assert first.hits[0].score_kind == "token_overlap_count"
    assert first.hits[0].score == 2.0
    assert all(isinstance(hit, RetrievalHit) for hit in first.hits)


def test_retrieval_filters_by_source_and_handles_no_match_deterministically() -> None:
    chunks = (
        *chunk_document(_document("calm local reference", source_id="src_one", local_path="one.txt"), ChunkingConfig()),
        *chunk_document(_document("another plain source", source_id="src_two", local_path="two.txt"), ChunkingConfig()),
    )
    retriever = InMemoryTestRetriever(chunks)

    only_one = retriever.retrieve(RetrievalQuery("local", source_ids=("src_one",)))
    no_match = retriever.retrieve(RetrievalQuery("not present"))

    assert only_one.metadata.candidate_count == 1
    assert [hit.chunk.provenance.source_id for hit in only_one.hits] == ["src_one"]
    assert no_match.hits == ()
    assert no_match.metadata.candidate_count == 2


def test_retrieval_contract_rejects_invalid_query_and_duplicate_chunks() -> None:
    chunk = chunk_document(_document("small fixture", local_path="fixture.txt"), ChunkingConfig())[0]
    with pytest.raises(RagContractError, match="top_k"):
        RetrievalQuery("query", top_k=0)
    with pytest.raises(RagContractError, match="source_ids"):
        RetrievalQuery("query", source_ids=("src_fixture", "src_fixture"))
    with pytest.raises(RagContractError, match="unique IDs"):
        InMemoryTestRetriever((chunk, chunk))


def test_citation_validator_accepts_only_retrieved_chunk_with_recorded_provenance() -> None:
    chunks = chunk_document(_document("local provenance", source_id="src_known", local_path="known.md"), ChunkingConfig())
    result = InMemoryTestRetriever(chunks).retrieve(RetrievalQuery("provenance"))
    known = chunks[0]
    valid = CitationReference(source_id=known.provenance.source_id, chunk_id=known.chunk_id)
    fabricated = CitationReference(source_id="src_known", chunk_id="chk_fabricated")
    wrong_source = CitationReference(source_id="src_other", chunk_id=known.chunk_id)

    validation = validate_citation_references((valid, fabricated, wrong_source), result)

    assert not validation.valid
    assert validation.accepted == (valid,)
    assert [issue.reason for issue in validation.rejected] == ["chunk_not_retrieved", "source_id_mismatch"]
    assert validate_citation_references((valid,), result).valid
    assert not validate_citation_references((), result).valid


def test_citation_reference_must_be_in_this_retrieval_result_and_have_provenance() -> None:
    first = chunk_document(_document("first alpha", source_id="src_first", local_path="first.txt"), ChunkingConfig())[0]
    second = chunk_document(_document("second beta", source_id="src_second", local_path="second.txt"), ChunkingConfig())[0]
    partial_result = InMemoryTestRetriever((first, second)).retrieve(RetrievalQuery("alpha"))
    not_returned = CitationReference(source_id="src_second", chunk_id=second.chunk_id)

    absent_result = validate_citation_references((not_returned,), partial_result)
    assert absent_result.rejected[0].reason == "chunk_not_retrieved"

    no_location = _document("reference without source locator", source_id="src_unlocated", local_path=None)
    unlocated_chunk = chunk_document(no_location, ChunkingConfig())[0]
    unlocated_retrieval = RetrievalResult(
        metadata=RetrievalMetadata(
            retriever_id="fixture_retriever",
            query_sha256=hashlib.sha256(b"reference").hexdigest(),
            candidate_count=1,
        ),
        hits=(RetrievalHit(unlocated_chunk, rank=1),),
    )
    unlocated_citation = CitationReference("src_unlocated", unlocated_chunk.chunk_id)
    unlocated_validation = validate_citation_references((unlocated_citation,), unlocated_retrieval)
    assert unlocated_validation.rejected[0].reason == "provenance_unavailable"


def test_offline_rag_operations_do_not_use_network_or_target_dispatch(tmp_path, monkeypatch) -> None:
    def unexpected(*args, **kwargs):
        raise AssertionError("offline RAG operation attempted network or target dispatch")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    root = tmp_path / "kb"
    root.mkdir()
    ingested = _ingest(root, "fixture.md", "offline context only")
    retrieval = InMemoryTestRetriever(ingested.chunks).retrieve(RetrievalQuery("context"))
    citation = CitationReference(ingested.source.metadata.source_id, ingested.chunks[0].chunk_id)

    assert retrieval.hits
    assert validate_citation_references((citation,), retrieval).valid


def test_source_ingestion_rejects_invalid_details_type(tmp_path) -> None:
    root = tmp_path / "kb"
    root.mkdir()
    (root / "notes.txt").write_text("text", encoding="utf-8")

    with pytest.raises(SourceIngestionError, match="SourceDetails"):
        ingest_local_file(root, "notes.txt", details={"publisher": "not typed"})
