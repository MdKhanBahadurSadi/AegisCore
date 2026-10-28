"""CLI utility for human inspection and review decision submission of candidate sources.

This tool provides a read-only inspection interface for candidate sources in
``docs/source-review-manifest.json`` and an explicit decision application mechanism
using ``aegiscore.source_review.PersistentSourceReviewRegistry``.

Notice: Reviewer and actor references are unauthenticated labels; they do not
prove identity, supervisor authority, source authority, or legal/license compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    ReviewChecklist,
    ReviewDecision,
    ReviewSubmission,
    SourceReviewError,
    _timestamp,
    _required_text,
)


_UNAUTHENTICATED_LABEL_NOTICE = (
    "NOTICE: Reviewer and actor references are unauthenticated labels. "
    "They do not prove human identity, supervisor authority, source authority, "
    "or legal/license compliance."
)


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and basic-validate the JSON manifest."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("format") != "aegiscore-source-review-manifest":
        raise ValueError("Invalid manifest format")
    return data


def list_candidate_sources(manifest_data: dict[str, Any]) -> None:
    """Print a summary table of all candidate sources in the manifest."""
    entries = manifest_data.get("entries", [])
    print(f"Corpus status: {manifest_data.get('corpus_status')}")
    print(f"Approval status: {manifest_data.get('approval_status')}")
    print(f"Total entries: {len(entries)}\n")
    print(_UNAUTHENTICATED_LABEL_NOTICE)
    print("\n" + "=" * 100)
    print(f"{'#':<3} | {'Source ID':<68} | {'State':<10} | {'Title'}")
    print("=" * 100)

    for idx, entry in enumerate(entries, 1):
        source_id = entry.get("source_id", "UNKNOWN")
        state = entry.get("review_state", "candidate")
        title = entry.get("title", "Untitled")
        if len(title) > 40:
            title = title[:37] + "..."
        print(f"{idx:<3} | {source_id:<68} | {state:<10} | {title}")
    print("=" * 100)


def show_source_details(manifest_data: dict[str, Any], repo_root: Path, source_id: str) -> None:
    """Display comprehensive review worksheet details for a specific source ID."""
    entries = {entry.get("source_id"): entry for entry in manifest_data.get("entries", [])}
    entry = entries.get(source_id)
    if not entry:
        raise ValueError(f"Source ID not found in manifest: {source_id}")

    raw_rel = entry.get("raw_path")
    norm_rel = entry.get("normalized_path")
    raw_path = repo_root / raw_rel if raw_rel else None
    norm_path = repo_root / norm_rel if norm_rel else None

    raw_exists = raw_path and raw_path.is_file()
    norm_exists = norm_path and norm_path.is_file()

    actual_raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_exists else "FILE_MISSING"
    actual_norm_hash = hashlib.sha256(norm_path.read_bytes()).hexdigest() if norm_exists else "FILE_MISSING"

    print(_UNAUTHENTICATED_LABEL_NOTICE + "\n")
    print(f"=== SOURCE REVIEW WORKSHEET: {entry.get('title')} ===")
    print(f"Source ID               : {entry.get('source_id')}")
    print(f"Review state            : {entry.get('review_state')}")
    print(f"Publisher               : {entry.get('publisher')} (unauthenticated)")
    print(f"Version                 : {entry.get('version')}")
    print(f"Repository revision     : {entry.get('repository_revision')}")
    print(f"Revision date           : {entry.get('revision_date')}")
    print(f"Acquisition date        : {entry.get('acquired_date')}")
    print(f"Canonical reference     : {entry.get('canonical_reference')}")
    print(f"Source URL              : {entry.get('source_url')}")
    print(f"License                 : {entry.get('license')}")
    print(f"License reference       : {entry.get('license_reference')}")
    print(f"Raw file path           : {raw_rel}")
    print(f"Raw file SHA-256        : {entry.get('raw_sha256')} (actual: {actual_raw_hash})")
    print(f"Normalized file path    : {norm_rel}")
    print(f"Normalized file SHA-256 : {entry.get('normalized_sha256')} (actual: {actual_norm_hash})")
    print(f"Intended use            : {entry.get('intended_use')}")

    print("\nLimitations:")
    for limit in entry.get("limitations", []):
        print(f"  - {limit}")

    print("\nScope Tags:")
    for tag in entry.get("scope_tags", []):
        print(f"  - {tag}")

    print("\nRequired Human Review Questions & Checklist:")
    print("  [ ] 1. Publisher attribution confirmed?")
    print("  [ ] 2. Content traceable to retained raw artifact?")
    print("  [ ] 3. Scope relevant to thesis research?")
    print("  [ ] 4. Intended use documented?")
    print("  [ ] 5. Limitations documented?")
    print("  [ ] 6. Corroboration assessed?")
    print("  [ ] 7. Unknown metadata documented?")


def generate_decision_template(source_id: str, manifest_data: dict[str, Any], output_path: Path) -> None:
    """Generate a non-approving decision template JSON file for a human reviewer.

    The template leaves decisions unselected, review timestamps and identities
    blank, and all checklist items false (unattested). Generating a template
    creates zero review events and zero approvals.
    """
    entries = {entry.get("source_id"): entry for entry in manifest_data.get("entries", [])}
    entry = entries.get(source_id)
    if not entry:
        raise ValueError(f"Source ID not found in manifest: {source_id}")

    template = {
        "notice": _UNAUTHENTICATED_LABEL_NOTICE,
        "source_id": entry.get("source_id"),
        "expected_content_sha256": entry.get("normalized_sha256"),
        "actor_ref": "",
        "timestamp": "",
        "submitter_rationale": "",
        "decision": "",
        "reviewer_ref": "",
        "reviewer_rationale": "",
        "checklist": {
            "publisher_attribution_confirmed": False,
            "content_traceable": False,
            "scope_relevant": False,
            "intended_use_documented": False,
            "limitations_documented": False,
            "corroboration_assessed": False,
            "unknown_metadata_documented": False,
        },
        "intended_use": "",
        "limitations": "",
        "corroboration_notes": "",
        "unknown_metadata_notes": "",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    print(f"Generated non-approving decision template for {source_id} at: {output_path}")


def apply_human_decision(
    decision_path: Path, db_path: Path, manifest_path: Path, repo_root: Path
) -> None:
    """Apply a human decision payload to a persistent SQLite review database and manifest with strict validation."""
    if not decision_path.is_file():
        raise FileNotFoundError(f"Decision file not found: {decision_path}")

    try:
        payload = json.loads(decision_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceReviewError("Decision file is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise SourceReviewError("Decision payload must be a JSON object")

    required_fields = {
        "notice", "source_id", "expected_content_sha256", "actor_ref", "timestamp",
        "submitter_rationale", "decision", "reviewer_ref", "reviewer_rationale",
        "checklist", "intended_use", "limitations", "corroboration_notes", "unknown_metadata_notes"
    }
    payload_keys = set(payload.keys())
    if payload_keys != required_fields:
        unexpected = sorted(list(payload_keys - required_fields))
        missing = sorted(list(required_fields - payload_keys))
        raise SourceReviewError(f"Invalid decision payload fields. Missing: {missing}, Unexpected: {unexpected}")

    source_id = payload.get("source_id")
    expected_hash = payload.get("expected_content_sha256")
    actor_ref = payload.get("actor_ref")
    timestamp = payload.get("timestamp")
    sub_rationale = payload.get("submitter_rationale")
    dec_str = payload.get("decision")
    reviewer_ref = payload.get("reviewer_ref")
    rev_rationale = payload.get("reviewer_rationale")
    raw_checklist = payload.get("checklist")
    intended_use = payload.get("intended_use")
    limitations = payload.get("limitations")
    corroboration_notes = payload.get("corroboration_notes")
    unknown_notes = payload.get("unknown_metadata_notes")

    # Strict type and value validations
    if not isinstance(source_id, str) or not source_id.strip():
        raise SourceReviewError("source_id must be a non-empty string")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
        raise SourceReviewError("expected_content_sha256 must be a valid 64-character lowercase SHA-256 digest")
    if not isinstance(actor_ref, str) or not actor_ref.strip():
        raise SourceReviewError("actor_ref must be a non-empty string")
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise SourceReviewError("timestamp must be a non-empty string")
    _timestamp(timestamp, "timestamp")

    if not isinstance(sub_rationale, str) or not sub_rationale.strip():
        raise SourceReviewError("submitter_rationale must be a non-empty string")

    if type(dec_str) is not str or dec_str not in {"approve", "reject"}:
        raise SourceReviewError("decision must be an actual string with value exactly 'approve' or 'reject'")

    if not isinstance(reviewer_ref, str) or not reviewer_ref.strip():
        raise SourceReviewError("reviewer_ref must be a non-empty string")
    if not isinstance(rev_rationale, str) or not rev_rationale.strip():
        raise SourceReviewError("reviewer_rationale must be a non-empty string")
    if not isinstance(intended_use, str) or not intended_use.strip():
        raise SourceReviewError("intended_use must be a non-empty string")
    if not isinstance(limitations, str) or not limitations.strip():
        raise SourceReviewError("limitations must be a non-empty string")
    if not isinstance(corroboration_notes, str) or not corroboration_notes.strip():
        raise SourceReviewError("corroboration_notes must be a non-empty string")
    if not isinstance(unknown_notes, str) or not unknown_notes.strip():
        raise SourceReviewError("unknown_metadata_notes must be a non-empty string")

    if not isinstance(raw_checklist, dict):
        raise SourceReviewError("checklist must be a JSON object")

    checklist_keys = {
        "publisher_attribution_confirmed",
        "content_traceable",
        "scope_relevant",
        "intended_use_documented",
        "limitations_documented",
        "corroboration_assessed",
        "unknown_metadata_documented",
    }
    raw_checklist_keys = set(raw_checklist.keys())
    if raw_checklist_keys != checklist_keys:
        unexpected = sorted(list(raw_checklist_keys - checklist_keys))
        missing = sorted(list(checklist_keys - raw_checklist_keys))
        raise SourceReviewError(f"Invalid checklist fields. Missing: {missing}, Unexpected: {unexpected}")

    for key in checklist_keys:
        val = raw_checklist.get(key)
        if type(val) is not bool:
            raise SourceReviewError(f"Checklist item '{key}' must be an actual JSON boolean (received type {type(val).__name__})")

    checklist = ReviewChecklist(
        publisher_attribution_confirmed=raw_checklist["publisher_attribution_confirmed"],
        content_traceable=raw_checklist["content_traceable"],
        scope_relevant=raw_checklist["scope_relevant"],
        intended_use_documented=raw_checklist["intended_use_documented"],
        limitations_documented=raw_checklist["limitations_documented"],
        corroboration_assessed=raw_checklist["corroboration_assessed"],
        unknown_metadata_documented=raw_checklist["unknown_metadata_documented"],
    )

    submission = ReviewSubmission(
        submitter_ref=actor_ref,
        submitted_at=timestamp,
        rationale=sub_rationale,
    )

    decision = ReviewDecision(
        decision=dec_str,
        reviewer_ref=reviewer_ref,
        reviewed_at=timestamp,
        rationale=rev_rationale,
        checklist=checklist,
        intended_use=intended_use,
        limitations=limitations,
        corroboration_notes=corroboration_notes,
        unknown_metadata_notes=unknown_notes,
    )

    # Verify source entry and current content hash against disk files before confirmation or writing
    registry = PersistentSourceReviewRegistry(
        database_path=db_path,
        manifest_path=manifest_path,
        repository_root=repo_root,
    )

    manifest_data = load_manifest(manifest_path)
    entries = {e.get("source_id"): e for e in manifest_data.get("entries", [])}
    entry = entries.get(source_id)
    if not entry:
        raise SourceReviewError(f"Source ID {source_id} not found in manifest")

    ingestion = registry._manifest_ingestion(entry)
    verified_current_hash = ingestion.source.metadata.content_sha256

    if expected_hash != verified_current_hash:
        raise SourceReviewError(
            f"Decision payload expected content hash ({expected_hash}) does not match "
            f"verified current normalized content hash ({verified_current_hash}). Aborting."
        )

    # Interactive terminal safeguard enforcement
    if not sys.stdin.isatty():
        raise SourceReviewError("Non-interactive execution is forbidden for decision application.")

    print("\n" + "=" * 80)
    print("SECURITY SAFEGUARD: CORPUS REVIEW DECISION CONFIRMATION")
    print("=" * 80)
    print(f"Verified Source ID : {source_id}")
    print(f"Verified Disk Hash : {verified_current_hash}")
    print(f"Requested Decision : {dec_str}")
    print(_UNAUTHENTICATED_LABEL_NOTICE)
    print("=" * 80)

    expected_phrase = f"CONFIRM {dec_str.upper()} {source_id}"
    print(f"To apply this decision, you must type exactly: {expected_phrase}")
    try:
        confirmation = input("Confirmation input: ").strip()
    except (KeyboardInterrupt, EOFError) as exc:
        raise SourceReviewError("Decision confirmation interrupted or aborted.") from exc

    if confirmation != expected_phrase:
        raise SourceReviewError("Confirmation phrase mismatch. Decision application aborted.")

    # Apply atomically in a single transaction using apply_review_workflow
    registry.apply_review_workflow(ingestion, expected_hash, submission, decision)

    print(f"Successfully applied human decision ({dec_str}) for source: {source_id}")
    print(f"Persistent database: {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Human source-review inspection and decision submission CLI utility."
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1], help="Repository root path")
    parser.add_argument("--manifest", type=Path, help="Manifest file path (defaults to docs/source-review-manifest.json)")
    parser.add_argument("--list", action="store_true", help="List all candidate sources in the manifest")
    parser.add_argument("--show", type=str, metavar="SOURCE_ID", help="Show review worksheet details for a source ID")
    parser.add_argument("--template", type=Path, metavar="OUTPUT_PATH", help="Generate a decision template JSON file")
    parser.add_argument("--source-id", type=str, help="Source ID to use with --template")
    parser.add_argument("--apply-decision", type=Path, metavar="DECISION_FILE", help="Apply completed human review decision JSON")
    parser.add_argument("--db", type=Path, help="SQLite database path to use with --apply-decision")

    args = parser.parse_args()
    repo_root = args.root.resolve()
    manifest_path = (args.manifest or repo_root / "docs" / "source-review-manifest.json").resolve()

    manifest_data = load_manifest(manifest_path)

    if args.list:
        list_candidate_sources(manifest_data)
    elif args.show:
        show_source_details(manifest_data, repo_root, args.show)
    elif args.template:
        if not args.source_id:
            parser.error("--source-id is required when generating a template")
        generate_decision_template(args.source_id, manifest_data, args.template.resolve())
    elif args.apply_decision:
        if not args.db:
            parser.error("--db is required when applying a decision")
        apply_human_decision(
            args.apply_decision.resolve(), args.db.resolve(), manifest_path, repo_root
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
