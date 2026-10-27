"""Offline integrity and candidate-governance checks for the Phase 7C corpus."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import urllib.request

import pytest

from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.rag import (
    ChunkingConfig,
    SourceDetails,
    SourceReviewState,
    ingest_local_file,
)
from aegiscore.safety import PolicyEngine
from aegiscore.source_review import SourceReviewRegistry
from scripts.normalize_security_corpus import normalize_cwe_html, normalize_entries, normalize_markdown


PROJECT_ROOT = Path(__file__).parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "source-review-manifest.json"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_official_sources_are_traceable_candidates_and_excluded_from_approval(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("offline corpus review attempted network or target dispatch")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    manifest = _manifest()
    assert manifest["corpus_status"] == "candidate_corpus"
    assert manifest["default_review_state"] == "candidate"
    assert manifest["approval_status"] == "no_sources_approved"
    assert len(manifest["entries"]) == 11

    registry = SourceReviewRegistry()
    for entry in manifest["entries"]:
        assert entry["acquisition_status"] == "acquired"
        assert entry["review_state"] == "candidate"
        assert entry["review_events"] == []
        assert entry["retrieval_eligibility"] == "excluded_until_explicit_approval"
        assert entry["source_url"].startswith("https://")
        assert entry["canonical_reference"].startswith("https://")
        assert entry["license"]
        assert entry["license_reference"].startswith("https://")
        assert entry["intended_use"]
        assert entry["limitations"]

        raw_path = PROJECT_ROOT / Path(entry["raw_path"])
        normalized_path = PROJECT_ROOT / Path(entry["normalized_path"])
        raw = raw_path.read_bytes()
        normalized = normalized_path.read_bytes()
        assert raw_path != normalized_path
        assert _sha256(raw) == entry["raw_sha256"]
        assert _sha256(normalized) == entry["normalized_sha256"]
        assert len(normalized) == entry["normalized_bytes"]

        # Normalized corpus files are retrieval candidates; raw publisher files
        # remain available for provenance and human review.
        normalized_text = normalized.decode("utf-8")
        assert "## Corpus provenance metadata" in normalized_text
        assert "## Normalized publisher content" in normalized_text
        assert "```" not in normalized_text
        assert "<script" not in normalized_text.casefold()
        assert "javascript:alert(" not in normalized_text.casefold()

        details = SourceDetails(
            title=entry["title"],
            publisher=entry["publisher"],
            canonical_reference=entry["canonical_reference"],
            publication_date=entry["publication_date"],
            version=entry["version"],
            acquired_at=entry["acquired_date"],
            source_type="official-security-reference-candidate",
            scope_tags=tuple(entry["scope_tags"]),
        )
        source_root = PROJECT_ROOT / "knowledge_base" / "normalized"
        first = ingest_local_file(
            source_root,
            entry["ingested_local_path"],
            chunking=ChunkingConfig(),
            details=details,
        )
        again = ingest_local_file(
            source_root,
            entry["ingested_local_path"],
            chunking=ChunkingConfig(),
            details=details,
        )
        assert first.source.metadata.source_id == entry["source_id"]
        assert first.source.metadata.content_sha256 == entry["normalized_sha256"]
        assert first.source.metadata.review_state is SourceReviewState.CANDIDATE
        assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in again.chunks]

        registered = registry.register(
            first,
            registrar_ref="phase-7c offline corpus test harness",
            registered_at=datetime.now(timezone.utc).isoformat(),
        )
        assert registered.metadata.review_state is SourceReviewState.CANDIDATE

    # Registration in this in-memory workflow is not approval, and no explicit
    # approval action occurred for any acquired source.
    assert registry.approved_chunks() == ()


def test_markdown_normalization_is_stable_and_removes_code_examples(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("normalization must not access a network or target")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    fixture = """---
title: Synthetic test fixture
---
# Benign fixture heading

Keep this explanatory prose and [the visible link label](https://example.invalid).

```text
print('synthetic example')
```

The inline marker `synthetic_identifier` is removed.
"""
    first = normalize_markdown(fixture)
    second = normalize_markdown(fixture)

    assert first == second
    assert "# Benign fixture heading" in first
    assert "Keep this explanatory prose" in first
    assert "visible link label" in first
    assert "example.invalid" not in first
    assert "synthetic example" not in first
    assert "synthetic_identifier" not in first


def test_cwe_normalization_keeps_only_selected_sections_and_drops_code(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("normalization must not access a network or target")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    fixture = """<html><body>
<div id="Description"><div><h3>Description</h3><p>Benign descriptive fixture.</p></div></div>
<div id="Common_Consequences"><p>Consequences fixture.</p></div>
<div id="Potential_Mitigations"><p>Use a safe, reviewed design.</p><pre>synthetic code</pre></div>
<div id="Demonstrative_Examples"><p>EXAMPLE_SECTION_SENTINEL</p></div>
</body></html>"""
    first = normalize_cwe_html(fixture)
    second = normalize_cwe_html(fixture)

    assert first == second
    assert "## Description" in first
    assert "## Common Consequences" in first
    assert "## Potential Mitigations" in first
    assert "safe, reviewed design" in first
    assert "synthetic code" not in first
    assert "EXAMPLE_SECTION_SENTINEL" not in first


def test_partial_acquisition_fails_before_writing_any_normalized_output(tmp_path) -> None:
    root = tmp_path / "project"
    raw = root / "knowledge_base" / "raw"
    normalized = root / "knowledge_base" / "normalized"
    raw.mkdir(parents=True)
    normalized.mkdir(parents=True)
    missing = {
        "acquisition_status": "acquired",
        "title": "Missing-source test fixture",
        "source_format": "markdown",
        "raw_path": "knowledge_base/raw/missing.md",
        "raw_sha256": "0" * 64,
        "normalized_path": "knowledge_base/normalized/missing.normalized.md",
        "review_state": "candidate",
    }

    with pytest.raises(FileNotFoundError, match="acquired raw source is missing"):
        normalize_entries([missing], root)

    assert list(normalized.iterdir()) == []
