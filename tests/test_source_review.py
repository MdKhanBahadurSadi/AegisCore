import hashlib
import json
import socket
import urllib.request
from dataclasses import replace
from pathlib import Path

import pytest

from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.rag import (
    ChunkingConfig,
    CitationReference,
    IngestionResult,
    SourceDetails,
    SourceDocument,
    SourceReviewState,
    chunk_document,
    ingest_local_file,
    validate_citation_references,
    InMemoryTestRetriever,
    RetrievalQuery,
)
from aegiscore.safety import PolicyEngine
from aegiscore.source_review import (
    ReviewChecklist,
    ReviewDecision,
    ReviewSubmission,
    SourceReviewError,
    SourceReviewRegistry,
)


REVIEWED_AT = "2026-10-27T08:30:00+06:00"
SUBMITTED_AT = "2026-10-27T08:00:00+06:00"


def _ingest(root, name: str, content: str, *, details: SourceDetails | None = None):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ingest_local_file(
        root,
        name,
        chunking=ChunkingConfig(chunk_size_chars=16, overlap_chars=3),
        details=details
        or SourceDetails(
            title="Synthetic review fixture",
            publisher="Synthetic test data",
            source_type="synthetic-test-fixture",
            scope_tags=("test-only",),
        ),
    )


def _checklist(**overrides) -> ReviewChecklist:
    values = {
        "publisher_attribution_confirmed": True,
        "content_traceable": True,
        "scope_relevant": True,
        "intended_use_documented": True,
        "limitations_documented": True,
        "corroboration_assessed": True,
        "unknown_metadata_documented": True,
    }
    values.update(overrides)
    return ReviewChecklist(**values)


def _decision(*, action="approve", reviewer_ref="fixture-reviewer", checklist=None, **overrides):
    values = {
        "decision": action,
        "reviewer_ref": reviewer_ref,
        "reviewed_at": REVIEWED_AT,
        "rationale": "Synthetic test-only review event.",
        "checklist": checklist or _checklist(),
        "intended_use": "Exercise source-review state transitions in unit tests.",
        "limitations": "Synthetic fixture; not an authentic security source.",
        "corroboration_notes": "No corroborating source; fixture does not make factual claims.",
        "unknown_metadata_notes": "Publication date and version are intentionally unknown.",
    }
    values.update(overrides)
    return ReviewDecision(**values)


def _register(registry: SourceReviewRegistry, ingestion):
    return registry.register(ingestion, registrar_ref="fixture-registrar", registered_at=SUBMITTED_AT)


def _submit(registry: SourceReviewRegistry, ingestion):
    return registry.submit_for_review(
        ingestion.source.metadata.source_id,
        ingestion.source.metadata.content_sha256,
        ReviewSubmission(
            submitter_ref="fixture-submitter",
            submitted_at=SUBMITTED_AT,
            rationale="Submit synthetic data to exercise the review workflow.",
        ),
    )


def _decide(registry: SourceReviewRegistry, ingestion, decision=None):
    return registry.decide(
        ingestion.source.metadata.source_id,
        ingestion.source.metadata.content_sha256,
        decision or _decision(),
    )


def test_explicit_review_events_are_required_for_approved_source_selection(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "Synthetic notes for state tests.")
    registry = SourceReviewRegistry()

    candidate = _register(registry, ingestion)
    assert candidate.metadata.review_state is SourceReviewState.CANDIDATE
    assert registry.approved_chunks() == ()

    pending = _submit(registry, ingestion)
    assert pending.metadata.review_state is SourceReviewState.PENDING_REVIEW
    approved = _decide(registry, ingestion)

    assert approved.metadata.review_state is SourceReviewState.APPROVED
    assert [event.action for event in approved.events] == ["registered", "submitted", "approved"]
    assert approved.events[-1].actor_ref == "fixture-reviewer"
    assert approved.events[-1].occurred_at == "2026-10-27T02:30:00.000000Z"
    assert approved.events[-1].checklist == _checklist()
    assert all(chunk.provenance.review_state is SourceReviewState.APPROVED for chunk in registry.approved_chunks())


def test_review_transitions_reject_skipped_repeated_and_stale_actions(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "first contents")
    registry = SourceReviewRegistry()
    _register(registry, ingestion)

    with pytest.raises(SourceReviewError, match="pending"):
        _decide(registry, ingestion)
    _submit(registry, ingestion)
    _decide(registry, ingestion, _decision(action="reject"))

    with pytest.raises(SourceReviewError, match="candidate"):
        _submit(registry, ingestion)
    with pytest.raises(SourceReviewError, match="pending"):
        _decide(registry, ingestion)

    changed = _ingest(root, "fixture.md", "changed contents")
    _register(registry, changed)
    with pytest.raises(SourceReviewError, match="stale"):
        registry.submit_for_review(
            ingestion.source.metadata.source_id,
            ingestion.source.metadata.content_sha256,
            ReviewSubmission("fixture-submitter", SUBMITTED_AT, "stale action"),
        )


def test_approval_requires_attribution_locator_all_checks_and_review_notes(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    registry = SourceReviewRegistry()

    no_attribution = _ingest(root, "no-attribution.md", "source text", details=SourceDetails())
    _register(registry, no_attribution)
    _submit(registry, no_attribution)
    with pytest.raises(SourceReviewError, match="title and publisher"):
        _decide(registry, no_attribution)

    no_locator_metadata = replace(
        no_attribution.source.metadata,
        title="Synthetic title",
        publisher="Synthetic publisher",
        local_path=None,
        canonical_reference=None,
    )
    no_locator_doc = SourceDocument(no_locator_metadata, no_attribution.source.content)
    no_locator = IngestionResult(
        source=no_locator_doc,
        chunks=chunk_document(no_locator_doc, no_attribution.chunking),
        chunking=no_attribution.chunking,
    )
    _register(registry, no_locator)
    _submit(registry, no_locator)
    with pytest.raises(SourceReviewError, match="source locator"):
        _decide(registry, no_locator)

    incomplete = _ingest(root, "incomplete.md", "another fixture")
    _register(registry, incomplete)
    _submit(registry, incomplete)
    with pytest.raises(SourceReviewError, match="checklist"):
        _decide(registry, incomplete, _decision(checklist=_checklist(corroboration_assessed=False)))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reviewer_ref": ""},
        {"reviewed_at": "2026-10-27T08:30:00"},
        {"rationale": ""},
        {"intended_use": ""},
        {"limitations": ""},
        {"corroboration_notes": ""},
        {"unknown_metadata_notes": ""},
    ],
)
def test_review_decision_requires_explicit_reviewer_time_and_rationale(kwargs) -> None:
    with pytest.raises(SourceReviewError):
        _decision(**kwargs)


def test_reviewer_reference_is_recorded_but_does_not_authenticate_identity(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "Synthetic source.")
    registry = SourceReviewRegistry()
    _register(registry, ingestion)
    _submit(registry, ingestion)

    approved = _decide(registry, ingestion, _decision(reviewer_ref="unverified-label-123"))

    assert approved.events[-1].actor_ref == "unverified-label-123"
    assert "authenticated" not in approved.events[-1].rationale.casefold()


def test_repository_source_review_manifest_contains_only_candidate_acquisitions() -> None:
    manifest_path = Path(__file__).parents[1] / "docs" / "source-review-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["format"] == "aegiscore-source-review-manifest"
    assert manifest["schema_version"] == 1
    assert manifest["corpus_status"] == "candidate_corpus"
    assert manifest["default_review_state"] == "candidate"
    assert manifest["approval_status"] == "no_sources_approved"
    assert len(manifest["entries"]) == 11
    assert all(entry["review_state"] == "candidate" for entry in manifest["entries"])
    assert all(entry["review_events"] == [] for entry in manifest["entries"])
    assert all(entry["retrieval_eligibility"] == "excluded_until_explicit_approval" for entry in manifest["entries"])


def test_directly_preapproved_ingestion_metadata_cannot_be_registered(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "source text")
    forged_metadata = replace(ingestion.source.metadata, review_state=SourceReviewState.APPROVED)
    forged_source = SourceDocument(forged_metadata, ingestion.source.content)
    forged = IngestionResult(
        source=forged_source,
        chunks=chunk_document(forged_source, ingestion.chunking),
        chunking=ingestion.chunking,
    )

    with pytest.raises(SourceReviewError, match="candidate"):
        _register(SourceReviewRegistry(), forged)


def test_reingestion_is_idempotent_for_same_revision_and_marks_changed_revision_stale(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    first = _ingest(root, "fixture.md", "first content revision")
    registry = SourceReviewRegistry()
    first_record = _register(registry, first)
    assert _register(registry, _ingest(root, "fixture.md", "first content revision")) == first_record
    _submit(registry, first)
    _decide(registry, first)

    changed = _ingest(root, "fixture.md", "second content revision")
    second_record = _register(registry, changed)

    historical = registry.get(first.source.metadata.source_id, revision=1)
    assert historical is not None
    assert historical.metadata.review_state is SourceReviewState.STALE
    assert historical.is_current is False
    assert historical.events[-2].action == "approved"
    assert historical.events[-1].action == "superseded"
    assert second_record.revision == 2
    assert second_record.metadata.review_state is SourceReviewState.CANDIDATE
    assert registry.approved_chunks() == ()
    assert registry.approved_chunks(first.chunks) == ()


def test_changed_provenance_also_creates_a_new_stale_revision(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    first = _ingest(root, "fixture.md", "same bytes")
    registry = SourceReviewRegistry()
    _register(registry, first)
    _submit(registry, first)
    _decide(registry, first)

    changed_metadata = _ingest(
        root,
        "fixture.md",
        "same bytes",
        details=SourceDetails(title="Updated supplied title", publisher="Synthetic test data"),
    )
    second = _register(registry, changed_metadata)
    assert second.revision == 2
    assert second.metadata.review_state is SourceReviewState.CANDIDATE
    assert registry.get(first.source.metadata.source_id, revision=1).metadata.review_state is SourceReviewState.STALE


def test_approved_selection_excludes_candidate_rejected_stale_unknown_and_altered_chunks(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    registry = SourceReviewRegistry()

    candidate = _ingest(root, "candidate.md", "candidate text")
    _register(registry, candidate)
    assert registry.approved_chunks(candidate.chunks) == ()

    rejected = _ingest(root, "rejected.md", "rejected text")
    _register(registry, rejected)
    _submit(registry, rejected)
    _decide(registry, rejected, _decision(action="reject"))
    assert registry.approved_chunks(rejected.chunks) == ()

    approved = _ingest(root, "approved.md", "approved test text with enough chars")
    _register(registry, approved)
    _submit(registry, approved)
    _decide(registry, approved)
    selected = registry.approved_chunks(approved.chunks)
    assert selected
    assert [chunk.chunk_id for chunk in selected] == [chunk.chunk_id for chunk in approved.chunks]

    unknown = replace(approved.chunks[0], chunk_id="chk_unknown_chunk")
    altered_text = approved.chunks[0].content[::-1]
    altered = replace(
        approved.chunks[0],
        content=altered_text,
        content_sha256=hashlib.sha256(altered_text.encode("utf-8")).hexdigest(),
    )
    altered_provenance = replace(
        approved.chunks[0],
        provenance=replace(approved.chunks[0].provenance, title="Altered caller title"),
    )
    assert registry.approved_chunks((unknown,)) == ()
    assert registry.approved_chunks((altered,)) == ()
    assert registry.approved_chunks((altered_provenance,)) == ()


def test_source_review_metadata_is_preserved_through_ingestion_and_chunks(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    details = SourceDetails(
        title="Synthetic provenance fixture",
        publisher="Synthetic test data",
        canonical_reference="fixture:source-1",
        publication_date=None,
        version=None,
        acquired_at="provided acquisition note",
        source_type="synthetic-test-fixture",
        scope_tags=("test-only", "provenance"),
    )

    ingestion = _ingest(root, "fixture.md", "preserve metadata in every chunk", details=details)

    assert ingestion.source.metadata.acquired_at == "provided acquisition note"
    assert ingestion.source.metadata.source_type == "synthetic-test-fixture"
    assert ingestion.source.metadata.scope_tags == ("test-only", "provenance")
    assert all(chunk.provenance == ingestion.source.metadata for chunk in ingestion.chunks)


def test_citation_membership_is_validated_separately_from_factual_support(tmp_path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "citation fixture text")
    registry = SourceReviewRegistry()
    _register(registry, ingestion)
    _submit(registry, ingestion)
    _decide(registry, ingestion)
    approved_chunks = registry.approved_chunks()
    retrieval = InMemoryTestRetriever(approved_chunks).retrieve(RetrievalQuery("citation"))
    chunk = retrieval.hits[0].chunk
    citation = CitationReference(chunk.provenance.source_id, chunk.chunk_id)

    validation = validate_citation_references((citation,), retrieval)

    assert validation.valid
    assert validation.factual_support == "not_evaluated"


def test_review_workflow_and_selection_do_not_use_network_or_target_dispatch(tmp_path, monkeypatch) -> None:
    def unexpected(*args, **kwargs):
        raise AssertionError("source review attempted network or target dispatch")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    root = tmp_path / "knowledge"
    root.mkdir()
    ingestion = _ingest(root, "fixture.md", "offline only source review")
    registry = SourceReviewRegistry()
    _register(registry, ingestion)
    _submit(registry, ingestion)
    _decide(registry, ingestion)
    assert registry.approved_chunks()
