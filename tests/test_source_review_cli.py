"""Unit tests for the human source-review CLI utility (scripts/review_source_corpus.py) and strict hardening validations."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aegiscore.source_review import SourceReviewError
from scripts.review_source_corpus import (
    _UNAUTHENTICATED_LABEL_NOTICE,
    apply_human_decision,
    generate_decision_template,
    list_candidate_sources,
    load_manifest,
    show_source_details,
)


PROJECT_ROOT = Path(__file__).parents[1]
REAL_MANIFEST = PROJECT_ROOT / "docs" / "source-review-manifest.json"


def test_load_real_manifest() -> None:
    manifest = load_manifest(REAL_MANIFEST)
    assert manifest["format"] == "aegiscore-source-review-manifest"
    assert manifest["corpus_status"] == "candidate_corpus"
    assert len(manifest["entries"]) == 11


def test_list_candidate_sources(capsys: pytest.CaptureFixture[str]) -> None:
    manifest = load_manifest(REAL_MANIFEST)
    list_candidate_sources(manifest)
    captured = capsys.readouterr().out
    assert _UNAUTHENTICATED_LABEL_NOTICE in captured
    assert "src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c" in captured
    assert "The Web Security Testing Framework" in captured


def test_show_source_details(capsys: pytest.CaptureFixture[str]) -> None:
    manifest = load_manifest(REAL_MANIFEST)
    source_id = "src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c"
    show_source_details(manifest, PROJECT_ROOT, source_id)
    captured = capsys.readouterr().out
    assert source_id in captured
    assert "The Web Security Testing Framework" in captured
    assert "OWASP Foundation" in captured
    assert "Required Human Review Questions & Checklist:" in captured


def test_generate_decision_template_non_approving(tmp_path: Path) -> None:
    manifest = load_manifest(REAL_MANIFEST)
    source_id = "src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c"
    output_path = tmp_path / "template.json"
    generate_decision_template(source_id, manifest, output_path)

    assert output_path.is_file()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["source_id"] == source_id
    assert data["decision"] == ""
    assert data["actor_ref"] == ""
    assert data["timestamp"] == ""
    for k, v in data["checklist"].items():
        assert v is False


def test_template_cannot_approve_without_completion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    template_path = tmp_path / "template.json"
    generate_decision_template(source_id, real_data, template_path)

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    # Generated template has empty decision and false checklist items, should fail validation
    with pytest.raises(SourceReviewError):
        apply_human_decision(template_path, db_path, manifest_path, proj_dir)


def test_strict_decision_validation_checklist_types(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"

    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["decision"] = "approve"
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"

    payload["checklist"]["publisher_attribution_confirmed"] = "false"
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: f"CONFIRM APPROVE {source_id}")

    with pytest.raises(SourceReviewError, match="must be an actual JSON boolean"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_strict_decision_validation_invalid_decision_string(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"

    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"
    for k in payload["checklist"]:
        payload["checklist"][k] = True

    payload["decision"] = ["approve"]  # List instead of string
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    with pytest.raises(SourceReviewError, match="decision must be an actual string"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_unexpected_payload_keys_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"

    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["unexpected_field"] = "malicious"
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    with pytest.raises(SourceReviewError, match="Invalid decision payload fields"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_hash_mismatch_aborts_before_prompting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"

    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["decision"] = "approve"
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"
    for k in payload["checklist"]:
        payload["checklist"][k] = True

    # Inject mismatched expected hash
    payload["expected_content_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    # Should abort due to hash mismatch before input() prompt is called
    with pytest.raises(SourceReviewError, match="does not match verified current normalized content hash"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_non_interactive_execution_forbidden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    raw_dir = proj_dir / "knowledge_base" / "raw"
    norm_dir = proj_dir / "knowledge_base" / "normalized"
    docs_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    norm_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"
    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"
    payload["decision"] = "approve"
    for k in payload["checklist"]:
        payload["checklist"][k] = True
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with pytest.raises(SourceReviewError, match="Non-interactive execution is forbidden"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_confirmation_phrase_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"

    generate_decision_template(source_id, real_data, decision_path)
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["decision"] = "approve"
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"
    for k in payload["checklist"]:
        payload["checklist"][k] = True
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "WRONG CONFIRMATION")

    with pytest.raises(SourceReviewError, match="Confirmation phrase mismatch"):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)


def test_atomic_failure_injection_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj_dir = tmp_path / "project"
    docs_dir = proj_dir / "docs"
    docs_dir.mkdir(parents=True)

    real_data = load_manifest(REAL_MANIFEST)
    source_id = real_data["entries"][0]["source_id"]
    raw_rel = real_data["entries"][0]["raw_path"]
    norm_rel = real_data["entries"][0]["normalized_path"]

    (proj_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / norm_rel).parent.mkdir(parents=True, exist_ok=True)
    (proj_dir / raw_rel).write_bytes((PROJECT_ROOT / raw_rel).read_bytes())
    (proj_dir / norm_rel).write_bytes((PROJECT_ROOT / norm_rel).read_bytes())

    manifest_path = docs_dir / "source-review-manifest.json"
    manifest_path.write_text(json.dumps(real_data, indent=2) + "\n", encoding="utf-8")
    before_bytes = manifest_path.read_bytes()

    db_path = tmp_path / "review.sqlite3"
    decision_path = tmp_path / "decision.json"
    generate_decision_template(source_id, real_data, decision_path)

    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    payload["decision"] = "approve"
    payload["actor_ref"] = "Reviewer"
    payload["timestamp"] = "2026-10-27T12:00:00Z"
    payload["submitter_rationale"] = "Valid rationale"
    payload["reviewer_ref"] = "Reviewer"
    payload["reviewer_rationale"] = "Valid review rationale"
    payload["intended_use"] = "Valid intended use"
    payload["limitations"] = "Valid limitations"
    payload["corroboration_notes"] = "Valid notes"
    payload["unknown_metadata_notes"] = "Valid notes"
    # Leave one checklist item False to trigger failure during approval check
    for k in payload["checklist"]:
        payload["checklist"][k] = True
    payload["checklist"]["publisher_attribution_confirmed"] = False
    decision_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: f"CONFIRM APPROVE {source_id}")

    with pytest.raises(SourceReviewError):
        apply_human_decision(decision_path, db_path, manifest_path, proj_dir)

    assert manifest_path.read_bytes() == before_bytes


def test_real_manifest_unmodified_by_tests() -> None:
    manifest = load_manifest(REAL_MANIFEST)
    assert manifest["approval_status"] == "no_sources_approved"
    for entry in manifest["entries"]:
        assert entry["review_state"] == "candidate"
        assert entry["review_events"] == []
