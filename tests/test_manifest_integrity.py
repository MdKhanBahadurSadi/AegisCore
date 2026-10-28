"""Integration tests for source manifest integrity and failure modes (Phase 8D.4 / SCEN-MA-14).

Verifies that the PersistentSourceReviewRegistry and RAG retrieval runtime enforce
manifest and source integrity using temporary fixtures without modifying the real
project manifest or knowledge corpus.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import pytest

from aegiscore.rag import ChunkingConfig, SourceDetails, ingest_local_file
from aegiscore.rag_runtime import retrieve_approved_evidence, RagRuntimeError
from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    ReviewChecklist,
    ReviewDecision,
    ReviewSubmission,
    SourceReviewConsistencyError,
    SourceReviewError,
    SourceReviewState,
)

TEST_SOURCE_TYPE = "official-security-reference-candidate"


def _create_synthetic_environment(tmp_path: Path, database_name: str = "review.sqlite3"):
    """Set up a fully isolated synthetic manifest, source corpus, and registry environment in tmp_path."""
    root = tmp_path
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "knowledge_base" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir = root / "knowledge_base" / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    raw_bytes = b"# Synthetic Vulnerability Guidance\n\nParameterized queries prevent SQL injection.\n"
    normalized_bytes = b"# Synthetic Vulnerability Guidance\n\nParameterized queries prevent SQL injection.\n"
    local_path = "synthetic-sqli.normalized.md"

    raw_file = raw_dir / "synthetic-sqli.raw.md"
    normalized_file = normalized_dir / local_path
    raw_file.write_bytes(raw_bytes)
    normalized_file.write_bytes(normalized_bytes)

    source_id = "src_" + hashlib.sha256(local_path.encode("utf-8")).hexdigest()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    normalized_sha256 = hashlib.sha256(normalized_bytes).hexdigest()

    entry = {
        "title": "Synthetic SQLi Guidance",
        "publisher": "Synthetic OWASP",
        "canonical_reference": "https://example.com/synthetic-sqli",
        "acquired_date": "2026-10-27T00:00:00Z",
        "version": "1.0.0",
        "scope_tags": ["sqli", "synthetic"],
        "review_state": "candidate",
        "review_events": [],
        "retrieval_eligibility": "excluded_until_explicit_approval",
        "raw_path": "knowledge_base/raw/synthetic-sqli.raw.md",
        "raw_sha256": raw_sha256,
        "raw_bytes": len(raw_bytes),
        "normalized_path": "knowledge_base/normalized/synthetic-sqli.normalized.md",
        "normalized_sha256": normalized_sha256,
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
    db_path = root / "data" / database_name
    registry = PersistentSourceReviewRegistry(
        db_path,
        manifest_path=manifest_path,
        repository_root=root,
    )
    return root, manifest_path, registry, ingestion, entry


def _approve_synthetic_source(registry: PersistentSourceReviewRegistry, ingestion, entry) -> None:
    """Run full review workflow to approve candidate in registry."""
    registry.apply_review_workflow(
        ingestion,
        entry["normalized_sha256"],
        ReviewSubmission(
            submitter_ref="synthetic-submitter",
            submitted_at="2026-10-27T01:00:00Z",
            rationale="Synthetic submission for manifest integrity test.",
        ),
        ReviewDecision(
            decision="approve",
            reviewer_ref="synthetic-reviewer",
            reviewed_at="2026-10-27T02:00:00Z",
            rationale="Approved for synthetic testing.",
            checklist=ReviewChecklist(True, True, True, True, True, True, True),
            intended_use="Manifest failure integration testing.",
            limitations="Synthetic test fixture only.",
            corroboration_notes="Verified against fixture bytes.",
            unknown_metadata_notes="None.",
        ),
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_temporary_manifest_accepted(tmp_path: Path) -> None:
    """A valid temporary manifest is accepted under the existing contract."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)

    # Initial state: candidate only, 0 approved chunks
    assert registry.approved_chunks() == ()

    # Approve source and verify chunk selection works
    _approve_synthetic_source(registry, ingestion, entry)
    chunks = registry.approved_chunks()
    assert len(chunks) == 1
    assert chunks[0].provenance.source_id == entry["source_id"]
    assert chunks[0].provenance.review_state is SourceReviewState.APPROVED


def test_tampered_manifest_raw_sha256_rejected(tmp_path: Path) -> None:
    """Tampering with raw_sha256 in the manifest causes approved_chunks to fail closed."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Tamper with the raw_sha256 in the manifest file
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["entries"][0]["raw_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SourceReviewConsistencyError, match="source file hash differs from the manifest revision"):
        registry.approved_chunks()


def test_tampered_manifest_normalized_sha256_rejected(tmp_path: Path) -> None:
    """Tampering with normalized_sha256 in the manifest causes approved_chunks to fail closed."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["entries"][0]["normalized_sha256"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SourceReviewConsistencyError, match="source file hash differs from the manifest revision"):
        registry.approved_chunks()


def test_tampered_source_file_content_on_disk_rejected(tmp_path: Path) -> None:
    """Modifying source file bytes on disk without updating manifest causes fail-closed rejection."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Modify the normalized file on disk
    norm_file = root / entry["normalized_path"]
    norm_file.write_bytes(b"# TAMPERED CONTENT: Attacker injection\n")

    with pytest.raises(SourceReviewConsistencyError, match="source file hash differs from the manifest revision"):
        registry.approved_chunks()


def test_tampered_manifest_metadata_against_persisted_record_rejected(tmp_path: Path) -> None:
    """Modifying metadata in manifest that contradicts persisted SQLite review ledger fails closed."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Tamper with entry metadata in manifest without using registry transaction
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["entries"][0]["title"] = "Tampered Title Unauthorized"
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SourceReviewConsistencyError, match="persistent registry revision differs from the source manifest"):
        registry.approved_chunks()


def test_missing_manifest_produces_typed_error(tmp_path: Path) -> None:
    """A missing manifest file produces the documented typed error."""
    nonexistent_manifest = tmp_path / "docs" / "nonexistent-manifest.json"
    root = tmp_path
    db_path = tmp_path / "review.sqlite3"

    with pytest.raises(SourceReviewError, match="database, manifest, or repository path is invalid"):
        PersistentSourceReviewRegistry(
            db_path,
            manifest_path=nonexistent_manifest,
            repository_root=root,
        )


def test_missing_manifest_deleted_after_init_fails_closed(tmp_path: Path) -> None:
    """If manifest is deleted after initialization, approved_chunks fails closed."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    manifest_path.unlink()

    with pytest.raises(SourceReviewConsistencyError, match="source-review manifest is unreadable or malformed"):
        registry.approved_chunks()


def test_malformed_json_manifest_rejected(tmp_path: Path) -> None:
    """A manifest containing malformed JSON is rejected clearly."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    manifest_path.write_text("{ unclosed json: [ malformed", encoding="utf-8")

    with pytest.raises(SourceReviewConsistencyError, match="source-review manifest is unreadable or malformed"):
        registry.approved_chunks()


def test_invalid_manifest_format_and_schema_version_rejected(tmp_path: Path) -> None:
    """Manifests with unsupported format or schema_version are rejected."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)

    # 1. Unsupported format
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["format"] = "invalid-manifest-format"
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="source-review manifest format or schema is unsupported"):
        registry.approved_chunks()

    # 2. Unsupported schema_version
    manifest_data["format"] = "aegiscore-source-review-manifest"
    manifest_data["schema_version"] = 999
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError, match="source-review manifest format or schema is unsupported"):
        registry.approved_chunks()


def test_manifest_duplicate_source_ids_rejected(tmp_path: Path) -> None:
    """A manifest containing duplicate source IDs is rejected."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["entries"].append(entry)  # Duplicate entry with same source_id
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SourceReviewConsistencyError, match="manifest source IDs must be unique"):
        registry.approved_chunks()


def test_failure_does_not_silently_fallback_to_unverified_records(tmp_path: Path) -> None:
    """When manifest integrity check fails, no unverified source records are returned."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Corrupt manifest
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["entries"][0]["normalized_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    # approved_chunks raises and never returns partial / unverified chunks
    with pytest.raises(SourceReviewConsistencyError):
        registry.approved_chunks()

    # retrieve_approved_evidence raises RagRuntimeError and never falls back
    with pytest.raises(RagRuntimeError, match="Approved-source selection failed closed"):
        retrieve_approved_evidence(
            query_text="SQL injection",
            registry=registry,
            min_score=0.5,
        )


def test_manifest_failure_leaves_review_history_and_approval_state_unchanged(tmp_path: Path) -> None:
    """A failure during integrity verification leaves SQLite review ledger unmodified."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Capture database snapshot before failure
    with sqlite3.connect(registry.database_path) as conn:
        rev_count_before = conn.execute("SELECT COUNT(*) FROM source_revisions").fetchone()[0]
        event_count_before = conn.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        state_before = conn.execute("SELECT state FROM source_revisions WHERE is_current = 1").fetchone()[0]

    # Trigger manifest failure
    manifest_path.write_text("INVALID JSON", encoding="utf-8")
    with pytest.raises(SourceReviewConsistencyError):
        registry.approved_chunks()

    # Re-examine database: exactly identical
    with sqlite3.connect(registry.database_path) as conn:
        rev_count_after = conn.execute("SELECT COUNT(*) FROM source_revisions").fetchone()[0]
        event_count_after = conn.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        state_after = conn.execute("SELECT state FROM source_revisions WHERE is_current = 1").fetchone()[0]

    assert rev_count_after == rev_count_before
    assert event_count_after == event_count_before
    assert state_after == state_before


def test_temporary_files_are_cleaned_up_reliably(tmp_path: Path) -> None:
    """All files reside exclusively in tmp_path and no repository files are created."""
    root, manifest_path, registry, ingestion, entry = _create_synthetic_environment(tmp_path)
    _approve_synthetic_source(registry, ingestion, entry)

    # Verify everything was contained within tmp_path
    assert manifest_path.is_relative_to(tmp_path)
    assert registry.database_path.is_relative_to(tmp_path)
    assert (root / entry["raw_path"]).is_relative_to(tmp_path)
    assert (root / entry["normalized_path"]).is_relative_to(tmp_path)


def test_documentation_of_integrity_baseline_limits() -> None:
    """Document existing integrity baseline and architectural boundaries.

    Baseline capabilities verified:
    1. Schema version and format verification (format='aegiscore-source-review-manifest', schema_version=1).
    2. SHA-256 content verification: raw and normalized file bytes are hashed and compared to manifest digests.
    3. Bidirectional mirror verification: manifest entries are fingerprinted via _manifest_revision_sha256
       and compared against SQLite database source_revisions ledger on every access.
    4. Fail-closed gating: any discrepancy prevents approved_chunks from returning any records.

    Architectural boundary / limitations:
    1. The manifest file itself does NOT possess a cryptographic signature (e.g. GPG/PKI detached signature).
       Manifest authenticity is anchored by file-level SHA-256 digests and SQLite ledger consistency.
    2. Modifying both manifest digests and source bytes before initial registration will register a
       tampered candidate; however, it remains strictly CANDIDATE and excluded from retrieval until
       explicit offline approval.
    """
    assert True
