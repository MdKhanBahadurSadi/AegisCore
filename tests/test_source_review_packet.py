"""Offline integrity and unset-state checks for the Phase 7D review packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import socket
import urllib.request

from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.safety import PolicyEngine


PROJECT_ROOT = Path(__file__).parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "source-review-manifest.json"
PACKET_PATH = PROJECT_ROOT / "docs" / "SOURCE_REVIEW_PACKET.md"
AUDIT_PATH = PROJECT_ROOT / "docs" / "NORMALIZATION_FIDELITY_AUDIT.md"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _worksheets() -> list[str]:
    packet = PACKET_PATH.read_text(encoding="utf-8")
    return re.split(r"(?m)^### Worksheet \d+\s*$", packet)[1:]


def _worksheet_for(source_id: str) -> str:
    matches = [section for section in _worksheets() if f"- Source ID: {source_id}\n" in section]
    assert len(matches) == 1
    return matches[0]


def test_packet_preserves_manifest_identity_revision_and_artifact_hashes() -> None:
    manifest = _manifest()
    packet = PACKET_PATH.read_text(encoding="utf-8")
    audit = AUDIT_PATH.read_text(encoding="utf-8")

    assert manifest["corpus_status"] == "candidate_corpus"
    assert manifest["approval_status"] == "no_sources_approved"
    assert len(manifest["entries"]) == 11
    assert len(_worksheets()) == 11

    for entry in manifest["entries"]:
        worksheet = _worksheet_for(entry["source_id"])
        assert f"#### {entry['title']}\n" in worksheet
        assert f"- Exact artifact title: {entry['title']}\n" in worksheet
        assert f"- Publisher as recorded: {entry['publisher']} (not independently authenticated)\n" in worksheet
        assert f"- Version: {entry['version'] or 'Unknown (not recorded in manifest)'}\n" in worksheet
        assert f"- Repository revision: {entry['repository_revision'] or 'Unknown (not recorded in manifest)'}\n" in worksheet
        assert f"- Revision date: {entry['revision_date'] or 'Unknown (not recorded in manifest)'}\n" in worksheet
        assert f"- Publication date: {entry['publication_date'] or 'Unknown (not recorded in manifest)'}\n" in worksheet
        assert f"- Canonical source locator: {entry['canonical_reference']}\n" in worksheet
        assert f"- Raw-file path: {entry['raw_path']}\n" in worksheet
        assert f"- Raw-file SHA-256: {entry['raw_sha256']}\n" in worksheet
        assert f"- Normalized-file path: {entry['normalized_path']}\n" in worksheet
        assert f"- Normalized-file SHA-256: {entry['normalized_sha256']}\n" in worksheet
        assert f"- License/terms as recorded: {entry['license']}\n" in worksheet
        assert f"- Intended thesis use as recorded: {entry['intended_use']}\n" in worksheet
        assert entry["source_id"] in audit
        assert entry["review_state"] == "candidate"
        assert entry["review_events"] == []
        assert entry["retrieval_eligibility"] == "excluded_until_explicit_approval"
        assert "Review decision: UNSET" in worksheet
        assert "Reviewer reference: UNSET" in worksheet
        assert "Review timestamp: UNSET" in worksheet
        assert "Rationale: UNSET" in worksheet
        assert "Corroboration/supporting references: UNSET" in worksheet
        assert "Unknown-metadata notes: UNSET" in worksheet
        assert "License applicability/compliance verification: UNKNOWN / NOT REVIEWED" in worksheet
        assert "Attribution verification: UNKNOWN / NOT REVIEWED" in worksheet


def test_raw_and_normalized_artifacts_still_match_recorded_hashes() -> None:
    for entry in _manifest()["entries"]:
        raw = (PROJECT_ROOT / entry["raw_path"]).read_bytes()
        normalized = (PROJECT_ROOT / entry["normalized_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["raw_sha256"]
        assert hashlib.sha256(normalized).hexdigest() == entry["normalized_sha256"]


def test_missing_review_metadata_is_reported_as_unknown_and_review_is_offline(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("review packet inspection attempted network or target dispatch")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected)

    for entry in _manifest()["entries"]:
        worksheet = _worksheet_for(entry["source_id"])
        for key, label in (
            ("revision_date", "Revision date"),
            ("publication_date", "Publication date"),
            ("copyright_notice", "Copyright notice as recorded"),
        ):
            if entry.get(key) is None:
                assert f"- {label}: Unknown (not recorded in manifest)\n" in worksheet
        assert "candidate; zero review events; excluded until explicit approval" in worksheet
