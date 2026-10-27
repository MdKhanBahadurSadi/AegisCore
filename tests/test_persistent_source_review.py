"""SQLite source-review persistence and manifest-gate tests using temp fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import urllib.request

import pytest

from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.rag import ChunkingConfig, SourceDetails, SourceReviewState, ingest_local_file
from aegiscore.safety import PolicyEngine
from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    ReviewChecklist,
    ReviewDecision,
    ReviewSubmission,
    SourceReviewConsistencyError,
    SourceReviewError,
)


PROJECT_ROOT = Path(__file__).parents[1]
REAL_MANIFEST = PROJECT_ROOT / "docs" / "source-review-manifest.json"
TEST_SOURCE_TYPE = "official-security-reference-candidate"


def _fixture(tmp_path: Path, database_name: str = "review.sqlite3"):
    root = tmp_path / "project"
    raw_dir = root / "knowledge_base" / "raw"
    normalized_dir = root / "knowledge_base" / "normalized"
    docs_dir = root / "docs"
    raw_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    raw_path = raw_dir / "synthetic-source.md"
    normalized_path = normalized_dir / "synthetic-source.normalized.md"
    raw_bytes = b"# Synthetic offline reference\n\nBenign fixture text for persistence tests.\n"
    normalized_bytes = b"# Synthetic offline reference\n\nBenign normalized fixture text.\n"
    raw_path.write_bytes(raw_bytes)
    normalized_path.write_bytes(normalized_bytes)
    local_path = normalized_path.name
    source_id = "src_" + hashlib.sha256(local_path.encode("utf-8")).hexdigest()
    entry = {
        "acquisition_status": "acquired",
        "review_state": "candidate",
        "review_events": [],
        "retrieval_eligibility": "excluded_until_explicit_approval",
        "title": "Synthetic offline reference fixture",
        "publisher": "Synthetic test data",
        "source_url": "fixture:local-only",
        "canonical_reference": "fixture:synthetic-source-1",
        "version": "fixture-v1",
        "repository_revision": None,
        "revision_date": None,
        "publication_date": None,
        "acquired_date": "2026-10-27",
        "license": "Synthetic fixture; no external license claim",
        "license_reference": None,
        "intended_use": "Exercise persistent review contracts only.",
        "limitations": ["Synthetic fixture; not a real security source."],
        "scope_tags": ["offline-fixture"],
        "source_format": "markdown",
        "raw_path": "knowledge_base/raw/synthetic-source.md",
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "normalized_path": "knowledge_base/normalized/synthetic-source.normalized.md",
        "normalized_sha256": hashlib.sha256(normalized_bytes).hexdigest(),
        "normalized_bytes": len(normalized_bytes),
        "source_id": source_id,
        "ingested_local_path": local_path,
    }
    manifest = {
        "format": "aegiscore-source-review-manifest",
        "schema_version": 1,
        "corpus_status": "candidate_corpus",
        "default_review_state": "candidate",
        "approval_status": "no_sources_approved",
        "entries": [entry],
    }
    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    details = SourceDetails(
        title=entry["title"],
        publisher=entry["publisher"],
        canonical_reference=entry["canonical_reference"],
        publication_date=None,
        version=entry["version"],
        acquired_at=entry["acquired_date"],
        source_type=TEST_SOURCE_TYPE,
        scope_tags=tuple(entry["scope_tags"]),
    )
    ingestion = ingest_local_file(
        normalized_dir,
        local_path,
        chunking=ChunkingConfig(),
        details=details,
    )
    registry = PersistentSourceReviewRegistry(
        root / "data" / database_name,
        manifest_path=manifest_path,
        repository_root=root,
    )
    return root, manifest_path, registry, ingestion, entry


def _register(registry, ingestion):
    return registry.register(
        ingestion,
        registrar_ref="synthetic-registrar-label",
        registered_at="2026-10-27T01:00:00Z",
    )


def _submit(registry, ingestion):
    return registry.submit_for_review(
        ingestion.source.metadata.source_id,
        ingestion.source.metadata.content_sha256,
        ReviewSubmission(
            submitter_ref="synthetic-submitter-label",
            submitted_at="2026-10-27T02:00:00Z",
            rationale="Synthetic test-only submission.",
        ),
    )


def _decision(**changes):
    values = {
        "decision": "approve",
        "reviewer_ref": "synthetic-unverified-reviewer-label",
        "reviewed_at": "2026-10-27T03:00:00Z",
        "rationale": "Synthetic test-only decision.",
        "checklist": ReviewChecklist(True, True, True, True, True, True, True),
        "intended_use": "Synthetic test use only.",
        "limitations": "Not a real source or human review.",
        "corroboration_notes": "Synthetic fixture; no corroboration claimed.",
        "unknown_metadata_notes": "Synthetic fixture values only.",
    }
    values.update(changes)
    return ReviewDecision(**values)


def _change_fixture_revision(root: Path, manifest_path: Path, entry: dict, content: bytes) -> None:
    raw_path = root / entry["raw_path"]
    normalized_path = root / entry["normalized_path"]
    raw_path.write_bytes(content)
    normalized_path.write_bytes(content)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = manifest["entries"][0]
    current["raw_sha256"] = hashlib.sha256(content).hexdigest()
    current["normalized_sha256"] = hashlib.sha256(content).hexdigest()
    current["normalized_bytes"] = len(content)
    current["review_state"] = "candidate"
    current["review_events"] = []
    current["retrieval_eligibility"] = "excluded_until_explicit_approval"
    manifest["approval_status"] = "no_sources_approved"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_persistent_registry_survives_reload_and_candidate_stays_excluded(tmp_path) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    registered = _register(registry, ingestion)
    assert registered.metadata.review_state is SourceReviewState.CANDIDATE
    assert registry.approved_chunks() == ()

    reloaded = PersistentSourceReviewRegistry(
        registry.database_path,
        manifest_path=manifest_path,
        repository_root=manifest_path.parents[1],
    )
    persisted = reloaded.get(ingestion.source.metadata.source_id)
    assert persisted is not None
    assert persisted.events[0].action == "registered"
    assert persisted.events[0].actor_ref_authenticated is False
    pending = _submit(reloaded, ingestion)
    assert pending.metadata.review_state is SourceReviewState.PENDING_REVIEW

    after_restart = PersistentSourceReviewRegistry(
        registry.database_path,
        manifest_path=manifest_path,
        repository_root=manifest_path.parents[1],
    )
    assert after_restart.get(ingestion.source.metadata.source_id).metadata.review_state is SourceReviewState.PENDING_REVIEW
    assert after_restart.approved_chunks() == ()


def test_exact_explicit_decision_persists_and_enables_only_verified_chunks(tmp_path) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    _submit(registry, ingestion)
    approved = registry.decide(
        ingestion.source.metadata.source_id,
        ingestion.source.metadata.content_sha256,
        _decision(),
    )

    assert approved.metadata.review_state is SourceReviewState.APPROVED
    assert [event.action for event in approved.events] == ["registered", "submitted", "approved"]
    assert approved.events[-1].actor_ref == "synthetic-unverified-reviewer-label"
    assert approved.events[-1].actor_ref_authenticated is False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["approval_status"] == "all_sources_approved"
    selected = registry.approved_chunks()
    assert selected
    assert all(chunk.provenance.review_state is SourceReviewState.APPROVED for chunk in selected)
    assert registry.approved_chunks(ingestion.chunks) == selected


def test_invalid_transitions_and_old_revision_hash_are_rejected(tmp_path) -> None:
    root, manifest_path, registry, ingestion, entry = _fixture(tmp_path)
    _register(registry, ingestion)
    with pytest.raises(SourceReviewError, match="pending"):
        registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, _decision())

    new_content = b"# Synthetic changed revision\n\nBenign second revision.\n"
    _change_fixture_revision(root, manifest_path, entry, new_content)
    changed = ingest_local_file(
        root / "knowledge_base" / "normalized",
        entry["ingested_local_path"],
        details=SourceDetails(
            title=entry["title"], publisher=entry["publisher"],
            canonical_reference=entry["canonical_reference"], version=entry["version"],
            acquired_at=entry["acquired_date"], source_type=TEST_SOURCE_TYPE,
            scope_tags=tuple(entry["scope_tags"]),
        ),
    )
    new_record = registry.register(changed, registrar_ref="synthetic-registrar-label", registered_at="2026-10-27T04:00:00Z")
    old = registry.get(ingestion.source.metadata.source_id, revision=1)
    assert old is not None and old.metadata.review_state is SourceReviewState.STALE
    assert old.events[-1].action == "superseded"
    assert new_record.revision == 2
    assert registry.approved_chunks() == ()
    with pytest.raises(SourceReviewError, match="stale or does not match"):
        registry.submit_for_review(
            ingestion.source.metadata.source_id,
            ingestion.source.metadata.content_sha256,
            ReviewSubmission("old-label", "2026-10-27T05:00:00Z", "stale"),
        )


def test_incomplete_review_attestation_does_not_advance_or_select(tmp_path) -> None:
    _, _, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    pending = _submit(registry, ingestion)
    incomplete = _decision(checklist=ReviewChecklist(True, True, True, True, True, False, True))
    with pytest.raises(SourceReviewError, match="every review checklist item"):
        registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, incomplete)
    assert registry.get(ingestion.source.metadata.source_id).metadata.review_state is SourceReviewState.PENDING_REVIEW
    assert registry.approved_chunks() == ()
    assert pending.events[-1].actor_ref_authenticated is False


def test_manifest_hash_or_state_mismatch_fails_closed_and_reconciliation_is_explicit(tmp_path) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entries"][0]["review_state"] = "approved"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="differ from persistent registry"):
        registry.approved_chunks()
    assert registry.reconcile_manifest() == (ingestion.source.metadata.source_id,)
    assert registry.approved_chunks() == ()

    normalized_path = manifest_path.parents[1] / "knowledge_base" / "normalized" / "synthetic-source.normalized.md"
    normalized_path.write_text("changed without manifest update", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="hash differs"):
        registry.approved_chunks()


def test_unregistered_manifest_approval_and_provenance_edits_fail_closed(tmp_path) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entries"][0]["review_state"] = "approved"
    manifest["entries"][0]["review_events"] = [{"action": "approved", "reviewer_ref": "claimed"}]
    manifest["entries"][0]["retrieval_eligibility"] = "eligible_after_explicit_approval"
    manifest["approval_status"] = "all_sources_approved"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="without a persistent record"):
        registry.approved_chunks()
    with pytest.raises(SourceReviewConsistencyError, match="cannot import manifest review state"):
        registry.reconcile_manifest()

    # Start with an actual synthetic persistent decision, then change a
    # non-review provenance field without changing the chunk bytes.
    manifest["entries"][0]["review_state"] = "candidate"
    manifest["entries"][0]["review_events"] = []
    manifest["entries"][0]["retrieval_eligibility"] = "excluded_until_explicit_approval"
    manifest["approval_status"] = "no_sources_approved"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _register(registry, ingestion)
    _submit(registry, ingestion)
    registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, _decision())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entries"][0]["license"] = "changed after synthetic review"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="provenance differs"):
        registry.approved_chunks()


def test_changed_source_revision_stales_approved_content_before_selection(tmp_path) -> None:
    root, manifest_path, registry, ingestion, entry = _fixture(tmp_path)
    _register(registry, ingestion)
    _submit(registry, ingestion)
    registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, _decision())
    assert registry.approved_chunks()

    changed_bytes = b"# Changed approved revision\n\nA different benign fixture revision.\n"
    _change_fixture_revision(root, manifest_path, entry, changed_bytes)
    with pytest.raises(SourceReviewConsistencyError, match="differs from the source manifest"):
        registry.approved_chunks()

    changed_ingestion = ingest_local_file(
        root / "knowledge_base" / "normalized",
        entry["ingested_local_path"],
        details=SourceDetails(
            title=entry["title"], publisher=entry["publisher"],
            canonical_reference=entry["canonical_reference"], version=entry["version"],
            acquired_at=entry["acquired_date"], source_type=TEST_SOURCE_TYPE,
            scope_tags=tuple(entry["scope_tags"]),
        ),
    )
    current = registry.register(
        changed_ingestion,
        registrar_ref="synthetic-registrar-label",
        registered_at="2026-10-27T06:00:00Z",
    )
    assert current.revision == 2
    assert registry.get(current.metadata.source_id, revision=1).metadata.review_state is SourceReviewState.STALE
    assert registry.approved_chunks() == ()


def test_malformed_persistent_record_and_incompatible_schema_fail_closed(tmp_path) -> None:
    _, _, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    with sqlite3.connect(registry.database_path) as connection:
        connection.execute(
            "UPDATE source_revisions SET metadata_json = ? WHERE source_id = ?",
            ("not-json", ingestion.source.metadata.source_id),
        )
    with pytest.raises(SourceReviewConsistencyError, match="malformed or inconsistent"):
        registry.approved_chunks()

    bad_database = tmp_path / "bad.sqlite3"
    with sqlite3.connect(bad_database) as connection:
        connection.execute("PRAGMA user_version = 99")
    with pytest.raises(SourceReviewError, match="unsupported review database schema"):
        PersistentSourceReviewRegistry(
            bad_database,
            manifest_path=registry.manifest_path,
            repository_root=registry.repository_root,
        )


def test_malformed_persisted_approval_event_fails_closed(tmp_path) -> None:
    _, _, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    _submit(registry, ingestion)
    registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, _decision())
    with sqlite3.connect(registry.database_path) as connection:
        row = connection.execute(
            "SELECT event_json FROM review_events WHERE source_id = ? AND action = 'approved'",
            (ingestion.source.metadata.source_id,),
        ).fetchone()
        event = json.loads(row[0])
        event["actor_ref"] = None
        connection.execute(
            "UPDATE review_events SET event_json = ? WHERE source_id = ? AND action = 'approved'",
            (json.dumps(event), ingestion.source.metadata.source_id),
        )
    with pytest.raises(SourceReviewConsistencyError, match="malformed or inconsistent"):
        registry.approved_chunks()


def test_failed_event_transaction_rolls_back_and_can_be_retried(tmp_path) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    before = manifest_path.read_bytes()
    with sqlite3.connect(registry.database_path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_test_event BEFORE INSERT ON review_events "
            "WHEN NEW.action = 'submitted' BEGIN SELECT RAISE(ABORT, 'synthetic transaction failure'); END"
        )

    with pytest.raises(SourceReviewError, match="transaction failed and was rolled back"):
        _submit(registry, ingestion)
    assert manifest_path.read_bytes() == before
    assert registry.get(ingestion.source.metadata.source_id).metadata.review_state is SourceReviewState.CANDIDATE

    with sqlite3.connect(registry.database_path) as connection:
        connection.execute("DROP TRIGGER reject_test_event")
    assert _submit(registry, ingestion).metadata.review_state is SourceReviewState.PENDING_REVIEW


def test_concurrent_manifest_change_is_not_overwritten(tmp_path, monkeypatch) -> None:
    _, manifest_path, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    original_bytes = manifest_path.read_bytes()
    original_assert = registry._assert_approval_status

    def concurrent_manifest_update(manifest, entries):
        manifest_path.write_bytes(original_bytes + b"\n")
        original_assert(manifest, entries)

    monkeypatch.setattr(registry, "_assert_approval_status", concurrent_manifest_update)
    with pytest.raises(SourceReviewConsistencyError, match="manifest changed during the review transaction"):
        _submit(registry, ingestion)
    assert manifest_path.read_bytes() == original_bytes + b"\n"
    assert registry.get(ingestion.source.metadata.source_id).metadata.review_state is SourceReviewState.CANDIDATE

    manifest_path.write_bytes(original_bytes)
    monkeypatch.setattr(registry, "_assert_approval_status", original_assert)
    assert _submit(registry, ingestion).metadata.review_state is SourceReviewState.PENDING_REVIEW


def test_persistent_review_is_offline_and_never_changes_real_manifest(tmp_path, monkeypatch) -> None:
    original_manifest = REAL_MANIFEST.read_bytes()

    def unexpected(*_args, **_kwargs):
        raise AssertionError("persistent source review attempted network or target dispatch")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    _, _, registry, ingestion, _ = _fixture(tmp_path)
    _register(registry, ingestion)
    _submit(registry, ingestion)
    registry.decide(ingestion.source.metadata.source_id, ingestion.source.metadata.content_sha256, _decision())
    assert registry.approved_chunks()
    assert REAL_MANIFEST.read_bytes() == original_manifest
