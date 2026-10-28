"""Read-only API tests backed by temporary source-review registries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aegiscore.rag import ChunkingConfig, SourceDetails, ingest_local_file
from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    ReviewChecklist,
    ReviewDecision,
    ReviewSubmission,
)
from tests.auth_helpers import authenticated_client, configured_test_app


def _registry(tmp_path: Path) -> tuple[PersistentSourceReviewRegistry, dict[str, object]]:
    root = tmp_path / "project"
    raw_dir = root / "knowledge_base" / "raw"
    normalized_dir = root / "knowledge_base" / "normalized"
    docs_dir = root / "docs"
    raw_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    raw = (
        "# Approved guidance\n\n"
        + "Use parameterized queries for SQL access. Never concatenate query text.\n\n" * 40
    ).encode("utf-8")
    normalized = raw
    (raw_dir / "approved.md").write_bytes(raw)
    (normalized_dir / "approved.normalized.md").write_bytes(normalized)
    source_id = "src_" + hashlib.sha256(b"approved.normalized.md").hexdigest()
    entry: dict[str, object] = {
        "acquisition_status": "acquired",
        "review_state": "candidate",
        "review_events": [],
        "retrieval_eligibility": "excluded_until_explicit_approval",
        "title": "Synthetic API test guidance",
        "publisher": "Synthetic test publisher",
        "source_url": "fixture:approved.md",
        "canonical_reference": "https://reviewer:secret@example.invalid/guide?token=hidden#private",
        "version": "fixture-v1",
        "repository_revision": None,
        "revision_date": None,
        "publication_date": None,
        "acquired_date": "2026-10-27",
        "license": "Synthetic fixture",
        "license_reference": None,
        "intended_use": "API tests only.",
        "limitations": ["Synthetic test fixture."],
        "scope_tags": ["security", "test"],
        "source_format": "markdown",
        "raw_path": "knowledge_base/raw/approved.md",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_path": "knowledge_base/normalized/approved.normalized.md",
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
        "normalized_bytes": len(normalized),
        "source_id": source_id,
        "ingested_local_path": "approved.normalized.md",
    }
    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "format": "aegiscore-source-review-manifest",
                "schema_version": 1,
                "corpus_status": "candidate_corpus",
                "default_review_state": "candidate",
                "approval_status": "no_sources_approved",
                "entries": [entry],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    database_path = tmp_path / "review.sqlite3"
    writer = PersistentSourceReviewRegistry(
        database_path,
        manifest_path=manifest_path,
        repository_root=root,
    )
    return (
        PersistentSourceReviewRegistry.open_existing(
            database_path,
            manifest_path=manifest_path,
            repository_root=root,
        ),
        entry,
    )


def _approve(
    registry: PersistentSourceReviewRegistry, entry: dict[str, object]
) -> None:
    ingestion = ingest_local_file(
        registry.repository_root / "knowledge_base" / "normalized",
        str(entry["ingested_local_path"]),
        chunking=ChunkingConfig(chunk_size_chars=30, overlap_chars=0),
        details=SourceDetails(
            title=str(entry["title"]),
            publisher=str(entry["publisher"]),
            canonical_reference=str(entry["canonical_reference"]),
            version=str(entry["version"]),
            acquired_at=str(entry["acquired_date"]),
            source_type="official-security-reference-candidate",
            scope_tags=("security", "test"),
        ),
    )
    registry.apply_review_workflow(
        ingestion,
        str(entry["normalized_sha256"]),
        ReviewSubmission("submitter-label", "2026-10-27T10:00:00Z", "test"),
        ReviewDecision(
            decision="approve",
            reviewer_ref="reviewer-label",
            reviewed_at="2026-10-27T11:00:00Z",
            rationale="Synthetic fixture approval for API tests.",
            checklist=ReviewChecklist(True, True, True, True, True, True, True),
            intended_use="Testing only.",
            limitations="Synthetic fixture.",
            corroboration_notes="Synthetic fixture.",
            unknown_metadata_notes="Synthetic fixture.",
        ),
    )


def test_default_app_reports_unconfigured_registry() -> None:
    with authenticated_client(configured_test_app()) as client:
        response = client.get("/evidence/approved")

    assert response.status_code == 503
    assert response.json() == {"detail": "Approved evidence registry is not configured."}


def test_registry_environment_configuration_opens_existing_registry_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    registry, _ = _registry(tmp_path)
    monkeypatch.setenv("AEGISCORE_SOURCE_REVIEW_DB", str(registry.database_path))
    monkeypatch.setenv("AEGISCORE_SOURCE_REVIEW_MANIFEST", str(registry.manifest_path))
    monkeypatch.setenv("AEGISCORE_REPOSITORY_ROOT", str(registry.repository_root))

    with authenticated_client(configured_test_app()) as client:
        response = client.get("/evidence/approved")

    assert response.status_code == 200
    assert response.json()["items"] == []

    monkeypatch.setenv(
        "AEGISCORE_SOURCE_REVIEW_MANIFEST",
        str(tmp_path / "missing-manifest.json"),
    )
    with authenticated_client(configured_test_app()) as invalid_client:
        invalid = invalid_client.get("/evidence/approved")
    assert invalid.status_code == 503
    assert str(tmp_path) not in invalid.text


def test_missing_configured_database_fails_without_bootstrapping(
    tmp_path: Path,
) -> None:
    registry, _ = _registry(tmp_path)
    registry.database_path.unlink()

    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        response = client.get("/evidence/approved")

    assert response.status_code == 503
    assert not registry.database_path.exists()


def test_empty_persistent_registry_returns_a_typed_empty_collection(
    tmp_path: Path,
) -> None:
    registry, _ = _registry(tmp_path)

    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        response = client.get("/evidence/approved")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "approved_source_count": 0,
        "offset": 0,
        "limit": 50,
    }


def test_approved_evidence_is_stable_paginated_and_contains_no_local_paths(
    tmp_path: Path,
) -> None:
    registry, entry = _registry(tmp_path)
    writer = PersistentSourceReviewRegistry(
        registry.database_path,
        manifest_path=registry.manifest_path,
        repository_root=registry.repository_root,
    )
    _approve(writer, entry)
    database_before = hashlib.sha256(registry.database_path.read_bytes()).hexdigest()
    manifest_before = hashlib.sha256(registry.manifest_path.read_bytes()).hexdigest()

    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        first = client.get("/evidence/approved?limit=2")
        repeated = client.get("/evidence/approved?limit=2")
        next_page = client.get("/evidence/approved?offset=2&limit=2")

    assert first.status_code == 200
    assert first.content == repeated.content
    body = first.json()
    assert body["total"] > 2
    assert body["approved_source_count"] == 1
    assert body["offset"] == 0
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    item = body["items"][0]
    assert item["source"]["source_id"] == entry["source_id"]
    assert item["source"]["review_state"] == "approved"
    assert item["source"]["revision"] == 1
    assert item["source"]["review_event_count"] == 3
    assert item["source"]["approved_at"] == "2026-10-27T11:00:00.000000Z"
    assert item["source"]["canonical_reference"] is None
    assert item["chunk"]["citation_source_id"] == entry["source_id"]
    assert item["chunk"]["citation_chunk_id"] == item["chunk"]["evidence_id"]
    assert "local_path" not in item["source"]
    assert "reviewer-label" not in first.text
    assert "secret" not in first.text
    assert "hidden" not in first.text
    assert str(registry.repository_root) not in first.text
    assert next_page.status_code == 200
    assert next_page.json()["offset"] == 2
    assert next_page.json()["items"][0]["chunk"]["evidence_id"] != item["chunk"]["evidence_id"]
    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        detail = client.get(f"/evidence/approved/{item['chunk']['evidence_id']}")
    assert detail.status_code == 200
    assert detail.json() == item
    assert hashlib.sha256(registry.database_path.read_bytes()).hexdigest() == database_before
    assert hashlib.sha256(registry.manifest_path.read_bytes()).hexdigest() == manifest_before


def test_evidence_detail_not_found_and_malformed_inputs_are_explicit(
    tmp_path: Path,
) -> None:
    registry, _ = _registry(tmp_path)

    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        missing = client.get("/evidence/approved/src-unknown-chunk")
        malformed = client.get("/evidence/approved/not%20an%20id")
        bad_limit = client.get("/evidence/approved?limit=101")
        bad_offset = client.get("/evidence/approved?offset=-1")

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Approved evidence was not found."}
    assert malformed.status_code == 422
    assert bad_limit.status_code == 422
    assert bad_offset.status_code == 422


def test_registry_manifest_disagreement_fails_closed_without_path_disclosure(
    tmp_path: Path,
) -> None:
    registry, entry = _registry(tmp_path)
    writer = PersistentSourceReviewRegistry(
        registry.database_path,
        manifest_path=registry.manifest_path,
        repository_root=registry.repository_root,
    )
    _approve(writer, entry)
    registry.manifest_path.write_text("{}\n", encoding="utf-8")

    with authenticated_client(configured_test_app(source_review_registry=registry)) as client:
        response = client.get("/evidence/approved")

    assert response.status_code == 503
    assert "manifest" not in response.text.lower()
    assert str(registry.repository_root) not in response.text
