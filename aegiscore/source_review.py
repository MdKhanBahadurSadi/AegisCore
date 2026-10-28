"""Offline source-review lifecycle and approved-chunk selection.

The registry is an in-process workflow contract. Reviewer references are
recorded for traceability but are not authenticated identities or proof of
source authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import sqlite3
import tempfile
from threading import RLock
from contextlib import contextmanager
from typing import Iterable, Literal

from aegiscore.rag import (
    ChunkingConfig,
    IngestionResult,
    SourceDetails,
    SourceChunk,
    SourceMetadata,
    SourceReviewState,
    ingest_local_file,
)


class SourceReviewError(ValueError):
    """A source-review action or registry operation is invalid."""


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceReviewError(f"{field} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise SourceReviewError(f"{field} contains a forbidden control character")
    return value.strip()


def _timestamp(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceReviewError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceReviewError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceReviewError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ReviewChecklist:
    """Reviewer-recorded checks; booleans are attestations, not verification."""

    publisher_attribution_confirmed: bool
    content_traceable: bool
    scope_relevant: bool
    intended_use_documented: bool
    limitations_documented: bool
    corroboration_assessed: bool
    unknown_metadata_documented: bool

    def __post_init__(self) -> None:
        for field in (
            "publisher_attribution_confirmed",
            "content_traceable",
            "scope_relevant",
            "intended_use_documented",
            "limitations_documented",
            "corroboration_assessed",
            "unknown_metadata_documented",
        ):
            if type(getattr(self, field)) is not bool:
                raise SourceReviewError(f"{field} must be a boolean")

    @property
    def all_checks_pass(self) -> bool:
        return all(
            getattr(self, field)
            for field in (
                "publisher_attribution_confirmed",
                "content_traceable",
                "scope_relevant",
                "intended_use_documented",
                "limitations_documented",
                "corroboration_assessed",
                "unknown_metadata_documented",
            )
        )


@dataclass(frozen=True, slots=True)
class ReviewSubmission:
    """Explicit action placing a candidate revision into review."""

    submitter_ref: str
    submitted_at: str
    rationale: str

    def __post_init__(self) -> None:
        _required_text(self.submitter_ref, "submitter_ref")
        _timestamp(self.submitted_at, "submitted_at")
        _required_text(self.rationale, "rationale")


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """Explicit reviewer action; reviewer_ref is recorded but not authenticated."""

    decision: Literal["approve", "reject"]
    reviewer_ref: str
    reviewed_at: str
    rationale: str
    checklist: ReviewChecklist
    intended_use: str
    limitations: str
    corroboration_notes: str
    unknown_metadata_notes: str

    def __post_init__(self) -> None:
        if self.decision not in {"approve", "reject"}:
            raise SourceReviewError("decision must be approve or reject")
        _required_text(self.reviewer_ref, "reviewer_ref")
        _timestamp(self.reviewed_at, "reviewed_at")
        _required_text(self.rationale, "rationale")
        if not isinstance(self.checklist, ReviewChecklist):
            raise SourceReviewError("checklist must be ReviewChecklist")
        for field in ("intended_use", "limitations", "corroboration_notes", "unknown_metadata_notes"):
            _required_text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class ReviewEvent:
    """Append-only event; actor references are explicitly unauthenticated labels."""

    action: Literal["registered", "submitted", "approved", "rejected", "superseded"]
    occurred_at: str
    rationale: str
    actor_ref: str | None = None
    actor_ref_authenticated: bool = False
    checklist: ReviewChecklist | None = None
    intended_use: str | None = None
    limitations: str | None = None
    corroboration_notes: str | None = None
    unknown_metadata_notes: str | None = None

    def __post_init__(self) -> None:
        if self.action not in {"registered", "submitted", "approved", "rejected", "superseded"}:
            raise SourceReviewError("unknown review event action")
        _timestamp(self.occurred_at, "occurred_at")
        _required_text(self.rationale, "rationale")
        if self.actor_ref is not None:
            _required_text(self.actor_ref, "actor_ref")
        if type(self.actor_ref_authenticated) is not bool or self.actor_ref_authenticated:
            raise SourceReviewError("actor references are unauthenticated; authenticated reviewer identity is unsupported")
        if self.checklist is not None and not isinstance(self.checklist, ReviewChecklist):
            raise SourceReviewError("checklist must be ReviewChecklist when provided")
        for field in ("intended_use", "limitations", "corroboration_notes", "unknown_metadata_notes"):
            value = getattr(self, field)
            if value is not None:
                _required_text(value, field)


@dataclass(frozen=True, slots=True)
class SourceReviewRecord:
    """Current or historical state of one exact source metadata/content revision."""

    metadata: SourceMetadata
    revision: int
    is_current: bool
    events: tuple[ReviewEvent, ...]
    manifest_revision_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, SourceMetadata):
            raise SourceReviewError("metadata must be SourceMetadata")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise SourceReviewError("revision must be a positive integer")
        if type(self.is_current) is not bool:
            raise SourceReviewError("is_current must be a boolean")
        if not isinstance(self.events, tuple) or any(not isinstance(event, ReviewEvent) for event in self.events):
            raise SourceReviewError("events must be a tuple of ReviewEvent")
        if self.manifest_revision_sha256 is not None and (
            not isinstance(self.manifest_revision_sha256, str)
            or len(self.manifest_revision_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.manifest_revision_sha256)
        ):
            raise SourceReviewError("manifest_revision_sha256 must be a lowercase SHA-256 digest when provided")


class SourceReviewRegistry:
    """In-memory, deterministic review registry; it performs no external checks."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, int], SourceReviewRecord] = {}
        self._current_revision: dict[str, int] = {}
        self._chunks: dict[tuple[str, int], tuple[SourceChunk, ...]] = {}

    def register(self, ingestion: IngestionResult, *, registrar_ref: str, registered_at: str) -> SourceReviewRecord:
        """Register an ingested candidate; caller-supplied refs are not authenticated."""

        if not isinstance(ingestion, IngestionResult):
            raise SourceReviewError("ingestion must be IngestionResult")
        _required_text(registrar_ref, "registrar_ref")
        timestamp = _timestamp(registered_at, "registered_at")
        incoming = ingestion.source.metadata
        if incoming.review_state is not SourceReviewState.CANDIDATE:
            raise SourceReviewError("only candidate ingestion metadata may be registered")

        source_id = incoming.source_id
        current_revision = self._current_revision.get(source_id)
        if current_revision is not None:
            current_key = (source_id, current_revision)
            current = self._records[current_key]
            comparable = replace(current.metadata, review_state=SourceReviewState.CANDIDATE)
            if comparable == incoming:
                self._chunks[current_key] = ingestion.chunks
                return current

            stale_metadata = replace(current.metadata, review_state=SourceReviewState.STALE)
            superseded = ReviewEvent(
                action="superseded",
                occurred_at=timestamp,
                rationale="A different source content or provenance revision was registered.",
            )
            self._records[current_key] = replace(
                current,
                metadata=stale_metadata,
                is_current=False,
                events=current.events + (superseded,),
            )
            revision = current_revision + 1
        else:
            revision = 1

        record = SourceReviewRecord(
            metadata=incoming,
            revision=revision,
            is_current=True,
            events=(
                ReviewEvent(
                    action="registered",
                    occurred_at=timestamp,
                    actor_ref=registrar_ref,
                    rationale="Source revision registered as a candidate; no approval is implied.",
                ),
            ),
        )
        key = (source_id, revision)
        self._records[key] = record
        self._current_revision[source_id] = revision
        self._chunks[key] = ingestion.chunks
        return record

    def submit_for_review(
        self, source_id: str, content_sha256: str, submission: ReviewSubmission
    ) -> SourceReviewRecord:
        """Move the exact current candidate revision to pending review."""

        record, key = self._current(source_id, content_sha256)
        if record.metadata.review_state is not SourceReviewState.CANDIDATE:
            raise SourceReviewError("only a current candidate may be submitted for review")
        if not isinstance(submission, ReviewSubmission):
            raise SourceReviewError("submission must be ReviewSubmission")
        event = ReviewEvent(
            action="submitted",
            occurred_at=_timestamp(submission.submitted_at, "submitted_at"),
            actor_ref=_required_text(submission.submitter_ref, "submitter_ref"),
            rationale=_required_text(submission.rationale, "rationale"),
        )
        updated = replace(
            record,
            metadata=replace(record.metadata, review_state=SourceReviewState.PENDING_REVIEW),
            events=record.events + (event,),
        )
        self._records[key] = updated
        return updated

    def decide(self, source_id: str, content_sha256: str, decision: ReviewDecision) -> SourceReviewRecord:
        """Approve or reject a pending exact revision after checklist validation."""

        record, key = self._current(source_id, content_sha256)
        if record.metadata.review_state is not SourceReviewState.PENDING_REVIEW:
            raise SourceReviewError("only a pending current revision may be decided")
        if not isinstance(decision, ReviewDecision):
            raise SourceReviewError("decision must be ReviewDecision")
        if decision.decision == "approve":
            metadata = record.metadata
            if not (metadata.title and metadata.publisher):
                raise SourceReviewError("approval requires supplied title and publisher attribution")
            if not (metadata.local_path or metadata.canonical_reference):
                raise SourceReviewError("approval requires a source locator")
            if not decision.checklist.all_checks_pass:
                raise SourceReviewError("approval requires every review checklist item to pass")
            state = SourceReviewState.APPROVED
            action: Literal["approved", "rejected"] = "approved"
        else:
            state = SourceReviewState.REJECTED
            action = "rejected"
        event = ReviewEvent(
            action=action,
            occurred_at=_timestamp(decision.reviewed_at, "reviewed_at"),
            actor_ref=_required_text(decision.reviewer_ref, "reviewer_ref"),
            rationale=_required_text(decision.rationale, "rationale"),
            checklist=decision.checklist,
            intended_use=decision.intended_use,
            limitations=decision.limitations,
            corroboration_notes=decision.corroboration_notes,
            unknown_metadata_notes=decision.unknown_metadata_notes,
        )
        updated = replace(record, metadata=replace(record.metadata, review_state=state), events=record.events + (event,))
        self._records[key] = updated
        return updated

    def get(self, source_id: str, revision: int | None = None) -> SourceReviewRecord | None:
        """Return one current or historical revision without changing its state."""

        if revision is None:
            revision = self._current_revision.get(source_id)
        if revision is None:
            return None
        return self._records.get((source_id, revision))

    def records(self) -> tuple[SourceReviewRecord, ...]:
        """Return all records in stable source/revision order."""

        return tuple(self._records[key] for key in sorted(self._records))

    def approved_chunks(self, candidates: Iterable[SourceChunk] | None = None) -> tuple[SourceChunk, ...]:
        """Select only exact chunks from current registry-approved revisions.

        Candidate chunks are treated as untrusted. Altered, unknown, stale,
        rejected, or unreviewed chunks are excluded. Returned provenance uses
        the registry's approved metadata, never caller-supplied status.
        """

        if candidates is None:
            candidate_items = tuple(
                chunk
                for key, record in self._records.items()
                if record.is_current and record.metadata.review_state is SourceReviewState.APPROVED
                for chunk in self._chunks.get(key, ())
            )
        else:
            try:
                candidate_items = tuple(candidates)
            except TypeError as exc:
                raise SourceReviewError("candidates must be an iterable of SourceChunk") from exc
        if any(not isinstance(chunk, SourceChunk) for chunk in candidate_items):
            raise SourceReviewError("candidates must contain only SourceChunk values")
        if len({chunk.chunk_id for chunk in candidate_items}) != len(candidate_items):
            raise SourceReviewError("candidate chunks must have unique IDs")

        accepted: list[SourceChunk] = []
        for candidate in candidate_items:
            source_id = candidate.provenance.source_id
            revision = self._current_revision.get(source_id)
            if revision is None:
                continue
            key = (source_id, revision)
            record = self._records[key]
            if not record.is_current or record.metadata.review_state is not SourceReviewState.APPROVED:
                continue
            if candidate.provenance.content_sha256 != record.metadata.content_sha256:
                continue
            stored = next((item for item in self._chunks.get(key, ()) if item.chunk_id == candidate.chunk_id), None)
            if stored is None:
                continue
            candidate_provenance = replace(candidate.provenance, review_state=SourceReviewState.CANDIDATE)
            stored_provenance = replace(stored.provenance, review_state=SourceReviewState.CANDIDATE)
            if candidate_provenance != stored_provenance:
                continue
            if replace(candidate, provenance=stored.provenance) != stored:
                continue
            accepted.append(replace(stored, provenance=record.metadata))
        accepted.sort(key=lambda chunk: (chunk.provenance.source_id, chunk.ordinal, chunk.chunk_id))
        return tuple(accepted)

    def _current(self, source_id: str, content_sha256: str) -> tuple[SourceReviewRecord, tuple[str, int]]:
        try:
            source_id = _required_text(source_id, "source_id")
            content_sha256 = _required_text(content_sha256, "content_sha256")
        except SourceReviewError:
            raise
        if len(content_sha256) != 64 or any(char not in "0123456789abcdef" for char in content_sha256):
            raise SourceReviewError("content_sha256 must be a lowercase SHA-256 digest")
        revision = self._current_revision.get(source_id)
        if revision is None:
            raise SourceReviewError("source is not registered")
        key = (source_id, revision)
        record = self._records[key]
        if not record.is_current or record.metadata.content_sha256 != content_sha256:
            raise SourceReviewError("source revision is stale or does not match the current content")
        return record, key


class SourceReviewConsistencyError(SourceReviewError):
    """The manifest, source files, and persistent review ledger disagree."""


class PersistentSourceReviewRegistry:
    """SQLite-backed review history with a fail-closed manifest projection.

    Reviewer references are stored as unauthenticated labels. SQLite is a
    durable application record, not a signed or tamper-proof audit log. The
    manifest and database mirror each persisted event; selector calls reject
    disagreement instead of choosing one silently. ``reconcile_manifest``
    explicitly projects database events onto manifest state after verifying
    that the immutable source identity and current file hashes still match.
    """

    SCHEMA_VERSION = 2
    _SOURCE_TYPE = "official-security-reference-candidate"
    # These are every per-source manifest value except the workflow projection
    # fields, which change as review events are appended.
    _REVIEW_PROJECTION_FIELDS = {"review_state", "review_events", "retrieval_eligibility"}
    _EVENT_TRANSITIONS = {
        "registered": (None, "candidate"),
        "submitted": ("candidate", "pending_review"),
        "approved": ("pending_review", "approved"),
        "rejected": ("pending_review", "rejected"),
        "superseded": ("*", "stale"),
    }

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        *,
        manifest_path: str | os.PathLike[str],
        repository_root: str | os.PathLike[str],
    ) -> None:
        if not isinstance(database_path, (str, os.PathLike)):
            raise SourceReviewError("database_path must name a persistent SQLite file")
        raw_database_path = os.fspath(database_path)
        if not isinstance(raw_database_path, str) or not raw_database_path.strip() or raw_database_path == ":memory:":
            raise SourceReviewError("database_path must name a persistent SQLite file")
        try:
            self.database_path = Path(raw_database_path).resolve(strict=False)
            self.manifest_path = Path(manifest_path).resolve(strict=True)
            self.repository_root = Path(repository_root).resolve(strict=True)
        except (OSError, TypeError, ValueError) as exc:
            raise SourceReviewError("database, manifest, or repository path is invalid") from exc
        if not self.manifest_path.is_file() or not self.repository_root.is_dir():
            raise SourceReviewError("manifest file and repository root directory are required")
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SourceReviewError("SQLite database directory is unavailable") from exc
        self._lock = RLock()
        self._initialize_schema()

    @classmethod
    def open_existing(
        cls,
        database_path: str | os.PathLike[str],
        *,
        manifest_path: str | os.PathLike[str],
        repository_root: str | os.PathLike[str],
    ) -> PersistentSourceReviewRegistry:
        """Open an existing persistent review registry without creating or bootstrapping a missing database."""
        if not isinstance(database_path, (str, os.PathLike)):
            raise SourceReviewError("database_path must name a persistent SQLite file")
        raw_database_path = os.fspath(database_path)
        if not isinstance(raw_database_path, str) or not raw_database_path.strip() or raw_database_path == ":memory:":
            raise SourceReviewError("database_path must name a persistent SQLite file")
        try:
            db = Path(raw_database_path).resolve(strict=False)
            manifest = Path(manifest_path).resolve(strict=True)
            root = Path(repository_root).resolve(strict=True)
        except (OSError, TypeError, ValueError) as exc:
            raise SourceReviewError("database, manifest, or repository path is invalid") from exc

        if not db.is_file():
            raise SourceReviewError("Persistent review database file does not exist; opening existing registry requires a valid existing database file")
        if not manifest.is_file() or not root.is_dir():
            raise SourceReviewError("manifest file and repository root directory are required")

        instance = cls.__new__(cls)
        instance.database_path = db
        instance.manifest_path = manifest
        instance.repository_root = root
        instance._lock = RLock()
        instance._is_read_only = True

        connection = instance._connect(read_only=True)
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version != cls.SCHEMA_VERSION:
                raise SourceReviewError(f"unsupported or uninitialized review database schema version: {version}")
            cls._validate_schema(connection)
        except SourceReviewError:
            raise
        except sqlite3.Error as exc:
            raise SourceReviewError("review database schema is malformed or unavailable") from exc
        finally:
            connection.close()

        return instance

    def _connect(self, *, read_only: bool = False) -> sqlite3.Connection:
        try:
            if read_only:
                db_uri = f"file:{self.database_path.as_posix()}?mode=ro"
                connection = sqlite3.connect(db_uri, uri=True, timeout=5.0, isolation_level=None)
            else:
                connection = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            return connection
        except sqlite3.Error as exc:
            raise SourceReviewError("persistent review database is unavailable") from exc

    @contextmanager
    def _connection(self):
        connection = self._connect(read_only=getattr(self, "_is_read_only", False))
        try:
            yield connection
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        connection = self._connect()
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                existing = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if existing:
                    raise SourceReviewError("unversioned non-empty SQLite database cannot be initialized safely")
                connection.executescript(
                    """
                    BEGIN IMMEDIATE;
                    CREATE TABLE source_revisions (
                        source_id TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK (revision > 0),
                        content_sha256 TEXT NOT NULL,
                        manifest_revision_sha256 TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        state TEXT NOT NULL CHECK (state IN ('candidate','pending_review','approved','rejected','stale')),
                        is_current INTEGER NOT NULL CHECK (is_current IN (0,1)),
                        previous_revision INTEGER,
                        PRIMARY KEY (source_id, revision),
                        CHECK (previous_revision IS NULL OR previous_revision > 0)
                    );
                    CREATE UNIQUE INDEX one_current_source_revision
                    ON source_revisions(source_id) WHERE is_current = 1;
                    CREATE TABLE review_events (
                        source_id TEXT NOT NULL,
                        revision INTEGER NOT NULL,
                        event_index INTEGER NOT NULL CHECK (event_index >= 0),
                        action TEXT NOT NULL CHECK (action IN ('registered','submitted','approved','rejected','superseded')),
                        occurred_at TEXT NOT NULL,
                        resulting_state TEXT NOT NULL CHECK (resulting_state IN ('candidate','pending_review','approved','rejected','stale')),
                        event_json TEXT NOT NULL,
                        PRIMARY KEY (source_id, revision, event_index),
                        FOREIGN KEY (source_id, revision) REFERENCES source_revisions(source_id, revision)
                            ON DELETE RESTRICT
                    );
                    PRAGMA user_version = 2;
                    COMMIT;
                    """
                )
            elif version != self.SCHEMA_VERSION:
                raise SourceReviewError(f"unsupported review database schema version: {version}")
            self._validate_schema(connection)
        except SourceReviewError:
            if connection.in_transaction:
                connection.rollback()
            raise
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.rollback()
            raise SourceReviewError("review database schema is malformed or unavailable") from exc
        finally:
            connection.close()

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        expected = {
            "source_revisions": {
                "source_id", "revision", "content_sha256", "manifest_revision_sha256", "metadata_json",
                "state", "is_current", "previous_revision"
            },
            "review_events": {
                "source_id", "revision", "event_index", "action", "occurred_at", "resulting_state", "event_json"
            },
        }
        for table, columns in expected.items():
            rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
            if not rows or {row["name"] for row in rows} != columns:
                raise SourceReviewError(f"review database table {table} is missing or malformed")
        indexes = connection.execute("PRAGMA index_list(source_revisions)").fetchall()
        if not any(row["name"] == "one_current_source_revision" and row["unique"] for row in indexes):
            raise SourceReviewError("review database current-revision constraint is missing")

    @staticmethod
    def _json(value: object) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise SourceReviewError("review record contains non-serializable data") from exc

    @classmethod
    def _metadata_json(cls, metadata: SourceMetadata) -> str:
        value = asdict(metadata)
        value["review_state"] = metadata.review_state.value
        return cls._json(value)

    @classmethod
    def _event_dict(cls, event: ReviewEvent) -> dict[str, object]:
        if not isinstance(event, ReviewEvent):
            raise SourceReviewError("event must be ReviewEvent")
        return asdict(event)

    @classmethod
    def _event_json(cls, event: ReviewEvent) -> str:
        return cls._json(cls._event_dict(event))

    @staticmethod
    def _eligibility(state: SourceReviewState) -> str:
        return {
            SourceReviewState.CANDIDATE: "excluded_until_explicit_approval",
            SourceReviewState.PENDING_REVIEW: "excluded_until_explicit_approval",
            SourceReviewState.APPROVED: "eligible_after_explicit_approval",
            SourceReviewState.REJECTED: "excluded_after_rejection",
            SourceReviewState.STALE: "excluded_stale_revision",
        }[state]

    def _read_manifest(self) -> tuple[dict[str, object], bytes, dict[str, dict[str, object]]]:
        try:
            payload = self.manifest_path.read_bytes()
            manifest = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceReviewConsistencyError("source-review manifest is unreadable or malformed") from exc
        if (
            not isinstance(manifest, dict)
            or manifest.get("format") != "aegiscore-source-review-manifest"
            or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("entries"), list)
        ):
            raise SourceReviewConsistencyError("source-review manifest format or schema is unsupported")
        entries: dict[str, dict[str, object]] = {}
        for entry in manifest["entries"]:
            if not isinstance(entry, dict):
                raise SourceReviewConsistencyError("manifest entry must be an object")
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id or source_id in entries:
                raise SourceReviewConsistencyError("manifest source IDs must be unique non-empty strings")
            if entry.get("review_state") not in {state.value for state in SourceReviewState}:
                raise SourceReviewConsistencyError(f"manifest review state is invalid for {source_id}")
            if not isinstance(entry.get("review_events"), list):
                raise SourceReviewConsistencyError(f"manifest review events are malformed for {source_id}")
            entries[source_id] = entry
        return manifest, payload, entries

    def _resolve_manifest_file(self, value: object, expected_directory: str) -> tuple[Path, str]:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise SourceReviewConsistencyError("manifest source path is missing or invalid")
        posix = PurePosixPath(value.replace("\\", "/"))
        windows = PureWindowsPath(value)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or any(part in {".", ".."} for part in posix.parts):
            raise SourceReviewConsistencyError("manifest source path must be a contained relative path")
        try:
            path = (self.repository_root.joinpath(*posix.parts)).resolve(strict=True)
            base = (self.repository_root / expected_directory).resolve(strict=True)
            relative = path.relative_to(base).as_posix()
        except (OSError, RuntimeError, ValueError) as exc:
            raise SourceReviewConsistencyError("manifest source path is missing or escapes its designated directory") from exc
        if not path.is_file() or relative in {"", "."}:
            raise SourceReviewConsistencyError("manifest source path must name a file")
        return path, relative

    def _manifest_ingestion(self, entry: dict[str, object]) -> IngestionResult:
        raw_path, _ = self._resolve_manifest_file(entry.get("raw_path"), "knowledge_base/raw")
        normalized_path, normalized_relative = self._resolve_manifest_file(
            entry.get("normalized_path"), "knowledge_base/normalized"
        )
        expected_local_path = entry.get("ingested_local_path")
        if expected_local_path != normalized_relative:
            raise SourceReviewConsistencyError("manifest normalized path and ingestion path disagree")
        try:
            raw_digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            normalized_digest = hashlib.sha256(normalized_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise SourceReviewConsistencyError("manifest source bytes could not be read") from exc
        if raw_digest != entry.get("raw_sha256") or normalized_digest != entry.get("normalized_sha256"):
            raise SourceReviewConsistencyError("source file hash differs from the manifest revision")
        tags = entry.get("scope_tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise SourceReviewConsistencyError("manifest scope tags are missing or malformed")
        details = SourceDetails(
            title=entry.get("title"),
            publisher=entry.get("publisher"),
            canonical_reference=entry.get("canonical_reference"),
            publication_date=entry.get("publication_date"),
            version=entry.get("version"),
            acquired_at=entry.get("acquired_date"),
            source_type=self._SOURCE_TYPE,
            scope_tags=tuple(tags),
        )
        try:
            ingestion = ingest_local_file(
                self.repository_root / "knowledge_base" / "normalized",
                normalized_relative,
                chunking=ChunkingConfig(),
                details=details,
            )
        except (OSError, ValueError, TypeError) as exc:
            raise SourceReviewConsistencyError("manifest normalized source cannot be ingested") from exc
        if ingestion.source.metadata.source_id != entry.get("source_id"):
            raise SourceReviewConsistencyError("manifest source ID does not match the normalized path")
        if ingestion.source.metadata.content_sha256 != entry.get("normalized_sha256"):
            raise SourceReviewConsistencyError("ingested source hash differs from the manifest revision")
        return ingestion

    @staticmethod
    def _metadata_matches_manifest(metadata: SourceMetadata, entry: dict[str, object]) -> bool:
        return all(
            (
                metadata.source_id == entry.get("source_id"),
                metadata.content_sha256 == entry.get("normalized_sha256"),
                metadata.local_path == entry.get("ingested_local_path"),
                metadata.title == entry.get("title"),
                metadata.publisher == entry.get("publisher"),
                metadata.canonical_reference == entry.get("canonical_reference"),
                metadata.publication_date == entry.get("publication_date"),
                metadata.version == entry.get("version"),
                metadata.acquired_at == entry.get("acquired_date"),
                metadata.scope_tags == tuple(entry.get("scope_tags", ())),
                metadata.source_type == PersistentSourceReviewRegistry._SOURCE_TYPE,
            )
        )

    @classmethod
    def _manifest_revision_sha256(cls, entry: dict[str, object]) -> str:
        """Fingerprint source identity, bytes, and all non-review manifest metadata."""

        snapshot = {key: value for key, value in entry.items() if key not in cls._REVIEW_PROJECTION_FIELDS}
        return hashlib.sha256(cls._json(snapshot).encode("utf-8")).hexdigest()

    @staticmethod
    def _expected_approval_status(entries: dict[str, dict[str, object]]) -> str:
        approved = sum(entry.get("review_state") == SourceReviewState.APPROVED.value for entry in entries.values())
        if approved == 0:
            return "no_sources_approved"
        if approved == len(entries):
            return "all_sources_approved"
        return "some_sources_approved"

    @classmethod
    def _sync_approval_status(cls, manifest: dict[str, object], entries: dict[str, dict[str, object]]) -> None:
        manifest["approval_status"] = cls._expected_approval_status(entries)

    @classmethod
    def _assert_approval_status(cls, manifest: dict[str, object], entries: dict[str, dict[str, object]]) -> None:
        if manifest.get("approval_status") != cls._expected_approval_status(entries):
            raise SourceReviewConsistencyError("manifest corpus approval summary disagrees with per-source review states")

    @staticmethod
    def _eligibility_from_text(state: str) -> str:
        try:
            return PersistentSourceReviewRegistry._eligibility(SourceReviewState(state))
        except ValueError as exc:
            raise SourceReviewConsistencyError("persistent review state is invalid") from exc

    def _decode_record(self, connection: sqlite3.Connection, row: sqlite3.Row) -> SourceReviewRecord:
        try:
            metadata_value = json.loads(row["metadata_json"])
            if not isinstance(metadata_value, dict):
                raise ValueError("metadata must be an object")
            metadata_value["review_state"] = SourceReviewState(metadata_value["review_state"])
            if metadata_value.get("scope_tags") is not None:
                metadata_value["scope_tags"] = tuple(metadata_value["scope_tags"])
            metadata = SourceMetadata(**metadata_value)
            if metadata.source_id != row["source_id"] or metadata.content_sha256 != row["content_sha256"]:
                raise ValueError("metadata identity differs from its row")
            manifest_revision_sha256 = row["manifest_revision_sha256"]
            if (
                not isinstance(manifest_revision_sha256, str)
                or len(manifest_revision_sha256) != 64
                or any(char not in "0123456789abcdef" for char in manifest_revision_sha256)
            ):
                raise ValueError("manifest revision digest is malformed")
            if metadata.review_state.value != row["state"]:
                raise ValueError("metadata state differs from its row")
            if row["revision"] == 1 and row["previous_revision"] is not None:
                raise ValueError("first revision has a previous revision")
            if row["revision"] > 1 and row["previous_revision"] != row["revision"] - 1:
                raise ValueError("revision predecessor is inconsistent")
            event_rows = connection.execute(
                "SELECT event_index, action, occurred_at, resulting_state, event_json "
                "FROM review_events WHERE source_id = ? AND revision = ? ORDER BY event_index",
                (row["source_id"], row["revision"]),
            ).fetchall()
            events: list[ReviewEvent] = []
            state_before: str | None = None
            for expected_index, event_row in enumerate(event_rows):
                if event_row["event_index"] != expected_index:
                    raise ValueError("event indices are not contiguous")
                event_data = json.loads(event_row["event_json"])
                if not isinstance(event_data, dict):
                    raise ValueError("event payload must be an object")
                checklist = event_data.get("checklist")
                if checklist is not None:
                    if not isinstance(checklist, dict):
                        raise ValueError("event checklist must be an object")
                    event_data["checklist"] = ReviewChecklist(**checklist)
                event = ReviewEvent(**event_data)
                if event.action != event_row["action"] or event.occurred_at != event_row["occurred_at"]:
                    raise ValueError("event columns differ from event payload")
                if event.action in {"registered", "submitted", "approved", "rejected"} and not event.actor_ref:
                    raise ValueError("review event lacks its required unauthenticated actor reference")
                required_before, resulting = self._EVENT_TRANSITIONS[event.action]
                if expected_index == 0:
                    if event.action != "registered" or required_before is not None:
                        raise ValueError("event history must start with registration")
                elif required_before == "*":
                    if state_before not in {"candidate", "pending_review", "approved", "rejected"}:
                        raise ValueError("event history contains an invalid supersession")
                elif state_before != required_before:
                    raise ValueError("event history contains an invalid transition")
                if event_row["resulting_state"] != resulting:
                    raise ValueError("event resulting state is inconsistent")
                if event.action in {"approved", "rejected"}:
                    if event.checklist is None:
                        raise ValueError("decision event lacks its review checklist")
                    if event.action == "approved" and not event.checklist.all_checks_pass:
                        raise ValueError("approval event lacks complete attestations")
                    for field in ("intended_use", "limitations", "corroboration_notes", "unknown_metadata_notes"):
                        _required_text(getattr(event, field), field)
                state_before = resulting
                events.append(event)
            if not events or state_before != row["state"]:
                raise ValueError("event history does not explain current revision state")
            if row["is_current"] not in {0, 1}:
                raise ValueError("current revision marker is malformed")
            is_current = bool(row["is_current"])
            if is_current and row["state"] == SourceReviewState.STALE.value:
                raise ValueError("stale revision cannot be current")
            if not is_current and (row["state"] != SourceReviewState.STALE.value or events[-1].action != "superseded"):
                raise ValueError("historical revision must end with superseded state")
            if is_current and events[-1].action == "superseded":
                raise ValueError("current revision cannot end with superseded event")
            return SourceReviewRecord(
                metadata, row["revision"], is_current, tuple(events), manifest_revision_sha256
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, SourceReviewError) as exc:
            raise SourceReviewConsistencyError("persistent source-review record is malformed or inconsistent") from exc

    def _current_record(self, connection: sqlite3.Connection, source_id: str) -> SourceReviewRecord | None:
        rows = connection.execute(
            "SELECT * FROM source_revisions WHERE source_id = ? AND is_current = 1", (source_id,)
        ).fetchall()
        if len(rows) > 1:
            raise SourceReviewConsistencyError("multiple current source revisions exist")
        return self._decode_record(connection, rows[0]) if rows else None

    def _all_records(self, connection: sqlite3.Connection) -> tuple[SourceReviewRecord, ...]:
        rows = connection.execute(
            "SELECT * FROM source_revisions ORDER BY source_id, revision"
        ).fetchall()
        return tuple(self._decode_record(connection, row) for row in rows)

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        source_id: str,
        revision: int,
        event: ReviewEvent,
        resulting_state: SourceReviewState,
    ) -> None:
        row = connection.execute(
            "SELECT COALESCE(MAX(event_index), -1) + 1 FROM review_events WHERE source_id = ? AND revision = ?",
            (source_id, revision),
        ).fetchone()
        connection.execute(
            "INSERT INTO review_events(source_id,revision,event_index,action,occurred_at,resulting_state,event_json) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                source_id,
                revision,
                row[0],
                event.action,
                event.occurred_at,
                resulting_state.value,
                self._event_json(event),
            ),
        )

    def _write_manifest(self, manifest: dict[str, object]) -> None:
        payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self._atomic_write(self.manifest_path, payload)

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except OSError as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise SourceReviewConsistencyError("atomic manifest update failed") from exc

    def _transaction(self, mutate):
        with self._lock:
            manifest, original_manifest, entries = self._read_manifest()
            connection = self._connect()
            manifest_written = False
            try:
                connection.execute("BEGIN IMMEDIATE")
                result, changed = mutate(connection, manifest, entries)
                if changed:
                    try:
                        current_manifest = self.manifest_path.read_bytes()
                    except OSError as exc:
                        raise SourceReviewConsistencyError(
                            "manifest became unavailable during the review transaction"
                        ) from exc
                    if current_manifest != original_manifest:
                        raise SourceReviewConsistencyError(
                            "manifest changed during the review transaction; retry or reconcile explicitly"
                        )
                    self._write_manifest(manifest)
                    manifest_written = True
                connection.commit()
                return result
            except Exception as exc:
                if connection.in_transaction:
                    connection.rollback()
                if manifest_written:
                    try:
                        self._atomic_write(self.manifest_path, original_manifest)
                    except SourceReviewConsistencyError as restore_exc:
                        raise SourceReviewConsistencyError(
                            "review transaction failed and manifest rollback failed; explicit reconciliation is required"
                        ) from restore_exc
                if isinstance(exc, SourceReviewError):
                    raise
                if isinstance(exc, sqlite3.Error):
                    raise SourceReviewError("persistent review transaction failed and was rolled back") from exc
                raise
            finally:
                connection.close()

    def _mirror_record(self, entry: dict[str, object], record: SourceReviewRecord) -> None:
        entry["review_state"] = record.metadata.review_state.value
        entry["review_events"] = [self._event_dict(event) for event in record.events]
        entry["retrieval_eligibility"] = self._eligibility(record.metadata.review_state)

    def _assert_mirror(self, entry: dict[str, object], record: SourceReviewRecord) -> None:
        if not self._metadata_matches_manifest(record.metadata, entry):
            raise SourceReviewConsistencyError("persisted review record refers to a different manifest revision")
        if record.manifest_revision_sha256 != self._manifest_revision_sha256(entry):
            raise SourceReviewConsistencyError("persisted review record provenance differs from the manifest revision")
        expected_events = [self._event_dict(event) for event in record.events]
        if (
            entry.get("review_state") != record.metadata.review_state.value
            or entry.get("review_events") != expected_events
            or entry.get("retrieval_eligibility") != self._eligibility(record.metadata.review_state)
        ):
            raise SourceReviewConsistencyError("manifest review state/events differ from persistent registry; reconcile explicitly")

    def register(
        self, ingestion: IngestionResult, *, registrar_ref: str, registered_at: str
    ) -> SourceReviewRecord:
        if not isinstance(ingestion, IngestionResult):
            raise SourceReviewError("ingestion must be IngestionResult")
        actor = _required_text(registrar_ref, "registrar_ref")
        timestamp = _timestamp(registered_at, "registered_at")
        incoming = ingestion.source.metadata
        if incoming.review_state is not SourceReviewState.CANDIDATE:
            raise SourceReviewError("only candidate source revisions may be registered")

        def mutate(connection, manifest, entries):
            self._assert_approval_status(manifest, entries)
            entry = entries.get(incoming.source_id)
            if entry is None:
                raise SourceReviewConsistencyError("source is not present in the approved manifest catalog")
            canonical = self._manifest_ingestion(entry)
            if canonical.source.metadata != incoming:
                raise SourceReviewConsistencyError("registration does not match the current manifest source bytes/metadata")
            if not self._metadata_matches_manifest(incoming, entry):
                raise SourceReviewConsistencyError("registration metadata differs from the manifest")
            current = self._current_record(connection, incoming.source_id)
            manifest_revision_sha256 = self._manifest_revision_sha256(entry)
            if current is not None:
                if (
                    replace(current.metadata, review_state=SourceReviewState.CANDIDATE) == incoming
                    and current.manifest_revision_sha256 == manifest_revision_sha256
                ):
                    self._assert_mirror(entry, current)
                    return current, False
                if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                    raise SourceReviewConsistencyError(
                        "changed content requires a candidate manifest revision with an empty review history"
                    )
                prior = current.metadata.review_state
                superseded_event = ReviewEvent(
                    action="superseded",
                    occurred_at=timestamp,
                    rationale="A new source content or provenance revision was registered.",
                )
                stale = replace(current.metadata, review_state=SourceReviewState.STALE)
                connection.execute(
                    "UPDATE source_revisions SET state = ?, metadata_json = ?, is_current = 0 "
                    "WHERE source_id = ? AND revision = ? AND is_current = 1",
                    (SourceReviewState.STALE.value, self._metadata_json(stale), incoming.source_id, current.revision),
                )
                self._insert_event(connection, incoming.source_id, current.revision, superseded_event, SourceReviewState.STALE)
                revision = current.revision + 1
                previous_revision = current.revision
            else:
                if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                    raise SourceReviewConsistencyError("manifest claims a review state without a persistent event history")
                revision = 1
                previous_revision = None
            registered_event = ReviewEvent(
                action="registered",
                occurred_at=timestamp,
                rationale="Source revision registered as a candidate; no approval is implied.",
                actor_ref=actor,
            )
            connection.execute(
                "INSERT INTO source_revisions(source_id,revision,content_sha256,manifest_revision_sha256,metadata_json,state,is_current,previous_revision) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    incoming.source_id,
                    revision,
                    incoming.content_sha256,
                    manifest_revision_sha256,
                    self._metadata_json(incoming),
                    SourceReviewState.CANDIDATE.value,
                    1,
                    previous_revision,
                ),
            )
            self._insert_event(connection, incoming.source_id, revision, registered_event, SourceReviewState.CANDIDATE)
            record = SourceReviewRecord(
                incoming, revision, True, (registered_event,), manifest_revision_sha256
            )
            self._mirror_record(entry, record)
            self._sync_approval_status(manifest, entries)
            return record, True

        return self._transaction(mutate)

    def submit_for_review(
        self, source_id: str, content_sha256: str, submission: ReviewSubmission
    ) -> SourceReviewRecord:
        source_id = _required_text(source_id, "source_id")
        content_sha256 = _required_text(content_sha256, "content_sha256")
        if not isinstance(submission, ReviewSubmission):
            raise SourceReviewError("submission must be ReviewSubmission")

        def mutate(connection, manifest, entries):
            self._assert_approval_status(manifest, entries)
            entry = entries.get(source_id)
            current = self._current_record(connection, source_id)
            if entry is None or current is None:
                raise SourceReviewError("source is not registered in the persistent review registry")
            self._assert_mirror(entry, current)
            canonical = self._manifest_ingestion(entry)
            if canonical.source.metadata.content_sha256 != content_sha256 or current.metadata.content_sha256 != content_sha256:
                raise SourceReviewError("source revision is stale or does not match current manifest bytes")
            if current.metadata.review_state is not SourceReviewState.CANDIDATE:
                raise SourceReviewError("only a current candidate may be submitted for review")
            event = ReviewEvent(
                action="submitted",
                occurred_at=_timestamp(submission.submitted_at, "submitted_at"),
                actor_ref=_required_text(submission.submitter_ref, "submitter_ref"),
                rationale=_required_text(submission.rationale, "rationale"),
            )
            state = SourceReviewState.PENDING_REVIEW
            metadata = replace(current.metadata, review_state=state)
            connection.execute(
                "UPDATE source_revisions SET state = ?, metadata_json = ? WHERE source_id = ? AND revision = ?",
                (state.value, self._metadata_json(metadata), source_id, current.revision),
            )
            self._insert_event(connection, source_id, current.revision, event, state)
            record = SourceReviewRecord(
                metadata, current.revision, True, current.events + (event,), current.manifest_revision_sha256
            )
            self._mirror_record(entry, record)
            self._sync_approval_status(manifest, entries)
            return record, True

        return self._transaction(mutate)

    def decide(self, source_id: str, content_sha256: str, decision: ReviewDecision) -> SourceReviewRecord:
        source_id = _required_text(source_id, "source_id")
        content_sha256 = _required_text(content_sha256, "content_sha256")
        if not isinstance(decision, ReviewDecision):
            raise SourceReviewError("decision must be ReviewDecision")

        def mutate(connection, manifest, entries):
            self._assert_approval_status(manifest, entries)
            entry = entries.get(source_id)
            current = self._current_record(connection, source_id)
            if entry is None or current is None:
                raise SourceReviewError("source is not registered in the persistent review registry")
            self._assert_mirror(entry, current)
            canonical = self._manifest_ingestion(entry)
            if canonical.source.metadata.content_sha256 != content_sha256 or current.metadata.content_sha256 != content_sha256:
                raise SourceReviewError("source revision is stale or does not match current manifest bytes")
            if current.metadata.review_state is not SourceReviewState.PENDING_REVIEW:
                raise SourceReviewError("only a pending current revision may be decided")
            if decision.decision == "approve":
                if not (current.metadata.title and current.metadata.publisher):
                    raise SourceReviewError("approval requires supplied title and publisher attribution")
                if not (current.metadata.local_path or current.metadata.canonical_reference):
                    raise SourceReviewError("approval requires a source locator")
                if not decision.checklist.all_checks_pass:
                    raise SourceReviewError("approval requires every review checklist item to pass")
                state = SourceReviewState.APPROVED
            else:
                state = SourceReviewState.REJECTED
            event = ReviewEvent(
                action="approved" if state is SourceReviewState.APPROVED else "rejected",
                occurred_at=_timestamp(decision.reviewed_at, "reviewed_at"),
                actor_ref=_required_text(decision.reviewer_ref, "reviewer_ref"),
                rationale=_required_text(decision.rationale, "rationale"),
                checklist=decision.checklist,
                intended_use=_required_text(decision.intended_use, "intended_use"),
                limitations=_required_text(decision.limitations, "limitations"),
                corroboration_notes=_required_text(decision.corroboration_notes, "corroboration_notes"),
                unknown_metadata_notes=_required_text(decision.unknown_metadata_notes, "unknown_metadata_notes"),
            )
            metadata = replace(current.metadata, review_state=state)
            connection.execute(
                "UPDATE source_revisions SET state = ?, metadata_json = ? WHERE source_id = ? AND revision = ?",
                (state.value, self._metadata_json(metadata), source_id, current.revision),
            )
            self._insert_event(connection, source_id, current.revision, event, state)
            record = SourceReviewRecord(
                metadata, current.revision, True, current.events + (event,), current.manifest_revision_sha256
            )
            self._mirror_record(entry, record)
            self._sync_approval_status(manifest, entries)
            return record, True

        return self._transaction(mutate)

    def apply_review_workflow(
        self,
        ingestion: IngestionResult,
        content_sha256: str,
        submission: ReviewSubmission,
        decision: ReviewDecision,
    ) -> SourceReviewRecord:
        """Atomically register, submit, and decide a source revision in a single transaction."""
        if not isinstance(ingestion, IngestionResult):
            raise SourceReviewError("ingestion must be IngestionResult")
        content_sha256 = _required_text(content_sha256, "content_sha256")
        if not isinstance(submission, ReviewSubmission):
            raise SourceReviewError("submission must be ReviewSubmission")
        if not isinstance(decision, ReviewDecision):
            raise SourceReviewError("decision must be ReviewDecision")

        def mutate(connection, manifest, entries):
            self._assert_approval_status(manifest, entries)
            incoming = ingestion.source.metadata
            if incoming.review_state is not SourceReviewState.CANDIDATE:
                raise SourceReviewError("only candidate source revisions may be registered")
            entry = entries.get(incoming.source_id)
            if entry is None:
                raise SourceReviewConsistencyError("source is not present in the approved manifest catalog")
            canonical = self._manifest_ingestion(entry)
            if canonical.source.metadata != incoming:
                raise SourceReviewConsistencyError("registration does not match the current manifest source bytes/metadata")
            if not self._metadata_matches_manifest(incoming, entry):
                raise SourceReviewConsistencyError("registration metadata differs from the manifest")
            current = self._current_record(connection, incoming.source_id)
            manifest_revision_sha256 = self._manifest_revision_sha256(entry)
            if current is not None:
                if (
                    replace(current.metadata, review_state=SourceReviewState.CANDIDATE) == incoming
                    and current.manifest_revision_sha256 == manifest_revision_sha256
                ):
                    pass
                else:
                    if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                        raise SourceReviewConsistencyError(
                            "changed content requires a candidate manifest revision with an empty review history"
                        )
                    superseded_event = ReviewEvent(
                        action="superseded",
                        occurred_at=submission.submitted_at,
                        rationale="A new source content or provenance revision was registered.",
                    )
                    stale = replace(current.metadata, review_state=SourceReviewState.STALE)
                    connection.execute(
                        "UPDATE source_revisions SET state = ?, metadata_json = ?, is_current = 0 "
                        "WHERE source_id = ? AND revision = ? AND is_current = 1",
                        (SourceReviewState.STALE.value, self._metadata_json(stale), incoming.source_id, current.revision),
                    )
                    self._insert_event(connection, incoming.source_id, current.revision, superseded_event, SourceReviewState.STALE)
                    revision = current.revision + 1
                    previous_revision = current.revision
                    registered_event = ReviewEvent(
                        action="registered",
                        occurred_at=submission.submitted_at,
                        rationale="Source revision registered as a candidate; no approval is implied.",
                        actor_ref=submission.submitter_ref,
                    )
                    connection.execute(
                        "INSERT INTO source_revisions(source_id,revision,content_sha256,manifest_revision_sha256,metadata_json,state,is_current,previous_revision) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (
                            incoming.source_id,
                            revision,
                            incoming.content_sha256,
                            manifest_revision_sha256,
                            self._metadata_json(incoming),
                            SourceReviewState.CANDIDATE.value,
                            1,
                            previous_revision,
                        ),
                    )
                    self._insert_event(connection, incoming.source_id, revision, registered_event, SourceReviewState.CANDIDATE)
            else:
                if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                    raise SourceReviewConsistencyError("manifest claims a review state without a persistent event history")
                revision = 1
                previous_revision = None
                registered_event = ReviewEvent(
                    action="registered",
                    occurred_at=submission.submitted_at,
                    rationale="Source revision registered as a candidate; no approval is implied.",
                    actor_ref=submission.submitter_ref,
                )
                connection.execute(
                    "INSERT INTO source_revisions(source_id,revision,content_sha256,manifest_revision_sha256,metadata_json,state,is_current,previous_revision) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (
                        incoming.source_id,
                        revision,
                        incoming.content_sha256,
                        manifest_revision_sha256,
                        self._metadata_json(incoming),
                        SourceReviewState.CANDIDATE.value,
                        1,
                        previous_revision,
                    ),
                )
                self._insert_event(connection, incoming.source_id, revision, registered_event, SourceReviewState.CANDIDATE)

            current = self._current_record(connection, incoming.source_id)
            self._mirror_record(entry, current)
            self._assert_mirror(entry, current)
            if current.metadata.content_sha256 != content_sha256:
                raise SourceReviewError("source revision is stale or does not match current manifest bytes")

            # Submit for review
            if current.metadata.review_state is SourceReviewState.CANDIDATE:
                sub_event = ReviewEvent(
                    action="submitted",
                    occurred_at=_timestamp(submission.submitted_at, "submitted_at"),
                    actor_ref=_required_text(submission.submitter_ref, "submitter_ref"),
                    rationale=_required_text(submission.rationale, "rationale"),
                )
                state = SourceReviewState.PENDING_REVIEW
                metadata = replace(current.metadata, review_state=state)
                connection.execute(
                    "UPDATE source_revisions SET state = ?, metadata_json = ? WHERE source_id = ? AND revision = ?",
                    (state.value, self._metadata_json(metadata), incoming.source_id, current.revision),
                )
                self._insert_event(connection, incoming.source_id, current.revision, sub_event, state)
                current = SourceReviewRecord(
                    metadata, current.revision, True, current.events + (sub_event,), current.manifest_revision_sha256
                )
                self._mirror_record(entry, current)

            # Decide
            if current.metadata.review_state is not SourceReviewState.PENDING_REVIEW:
                raise SourceReviewError("only a pending revision may be decided")
            if decision.decision == "approve":
                if not (current.metadata.title and current.metadata.publisher):
                    raise SourceReviewError("approval requires supplied title and publisher attribution")
                if not (current.metadata.local_path or current.metadata.canonical_reference):
                    raise SourceReviewError("approval requires a source locator")
                if not decision.checklist.all_checks_pass:
                    raise SourceReviewError("approval requires every review checklist item to pass")
                state = SourceReviewState.APPROVED
            else:
                state = SourceReviewState.REJECTED

            dec_event = ReviewEvent(
                action="approved" if state is SourceReviewState.APPROVED else "rejected",
                occurred_at=_timestamp(decision.reviewed_at, "reviewed_at"),
                actor_ref=_required_text(decision.reviewer_ref, "reviewer_ref"),
                rationale=_required_text(decision.rationale, "rationale"),
                checklist=decision.checklist,
                intended_use=_required_text(decision.intended_use, "intended_use"),
                limitations=_required_text(decision.limitations, "limitations"),
                corroboration_notes=_required_text(decision.corroboration_notes, "corroboration_notes"),
                unknown_metadata_notes=_required_text(decision.unknown_metadata_notes, "unknown_metadata_notes"),
            )
            metadata = replace(current.metadata, review_state=state)
            connection.execute(
                "UPDATE source_revisions SET state = ?, metadata_json = ? WHERE source_id = ? AND revision = ?",
                (state.value, self._metadata_json(metadata), incoming.source_id, current.revision),
            )
            self._insert_event(connection, incoming.source_id, current.revision, dec_event, state)
            final_record = SourceReviewRecord(
                metadata, current.revision, True, current.events + (dec_event,), current.manifest_revision_sha256
            )
            self._mirror_record(entry, final_record)
            self._sync_approval_status(manifest, entries)
            return final_record, True

        return self._transaction(mutate)

    def get(self, source_id: str, revision: int | None = None) -> SourceReviewRecord | None:
        try:
            with self._lock, self._connection() as connection:
                if revision is None:
                    record = self._current_record(connection, source_id)
                    return record
                row = connection.execute(
                    "SELECT * FROM source_revisions WHERE source_id = ? AND revision = ?", (source_id, revision)
                ).fetchone()
                return self._decode_record(connection, row) if row is not None else None
        except sqlite3.Error as exc:
            raise SourceReviewError("persistent review record could not be read") from exc

    def records(self) -> tuple[SourceReviewRecord, ...]:
        try:
            with self._lock, self._connection() as connection:
                return self._all_records(connection)
        except sqlite3.Error as exc:
            raise SourceReviewError("persistent review records could not be read") from exc

    def _checked_manifest_records(
        self, connection: sqlite3.Connection, *, allow_mirror_mismatch: bool = False
    ) -> tuple[dict[str, object], dict[str, dict[str, object]], dict[str, SourceReviewRecord], dict[str, IngestionResult]]:
        manifest, _, entries = self._read_manifest()
        currents = {
            record.metadata.source_id: record
            for record in self._all_records(connection)
            if record.is_current
        }
        ingestions: dict[str, IngestionResult] = {}
        if set(currents) - set(entries):
            raise SourceReviewConsistencyError("persistent registry contains source IDs missing from the manifest")
        for source_id, entry in entries.items():
            ingestion = self._manifest_ingestion(entry)
            ingestions[source_id] = ingestion
            record = currents.get(source_id)
            if record is None:
                if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                    raise SourceReviewConsistencyError("manifest claims review activity without a persistent record")
                if entry.get("retrieval_eligibility") != self._eligibility(SourceReviewState.CANDIDATE):
                    raise SourceReviewConsistencyError("unregistered candidate has inconsistent retrieval eligibility")
                continue
            if not self._metadata_matches_manifest(record.metadata, entry):
                raise SourceReviewConsistencyError("persistent registry revision differs from the source manifest")
            if not allow_mirror_mismatch:
                self._assert_mirror(entry, record)
        self._assert_approval_status(manifest, entries)
        return manifest, entries, currents, ingestions

    def approved_chunks(self, candidates: Iterable[SourceChunk] | None = None) -> tuple[SourceChunk, ...]:
        """Return only chunks re-read from manifest files and approved in SQLite.

        The manifest is checked against the persistent event projection on each
        call. Unregistered candidate rows are valid but excluded. A mismatch,
        changed file hash, malformed record, or claimed approval without an
        event history raises and returns no partial result.
        """

        try:
            candidate_items = None if candidates is None else tuple(candidates)
        except TypeError as exc:
            raise SourceReviewError("candidates must be an iterable of SourceChunk") from exc
        if candidate_items is not None:
            if any(not isinstance(chunk, SourceChunk) for chunk in candidate_items):
                raise SourceReviewError("candidates must contain only SourceChunk values")
            if len({chunk.chunk_id for chunk in candidate_items}) != len(candidate_items):
                raise SourceReviewError("candidate chunks must have unique IDs")
        try:
            with self._lock, self._connection() as connection:
                _, entries, currents, ingestions = self._checked_manifest_records(connection)
        except sqlite3.Error as exc:
            raise SourceReviewError("approved-source selection failed closed") from exc
        approved: list[SourceChunk] = []
        for source_id, record in currents.items():
            if record.metadata.review_state is not SourceReviewState.APPROVED:
                continue
            entry = entries[source_id]
            if entry.get("review_state") != SourceReviewState.APPROVED.value:
                raise SourceReviewConsistencyError("approved registry record is not mirrored by the manifest")
            for chunk in ingestions[source_id].chunks:
                approved.append(replace(chunk, provenance=record.metadata))
        approved.sort(key=lambda chunk: (chunk.provenance.source_id, chunk.ordinal, chunk.chunk_id))
        if candidate_items is None:
            return tuple(approved)
        supplied = {chunk.chunk_id: chunk for chunk in candidate_items}
        accepted: list[SourceChunk] = []
        for chunk in approved:
            candidate = supplied.get(chunk.chunk_id)
            if candidate is None:
                continue
            normalized_candidate = replace(
                candidate,
                provenance=replace(candidate.provenance, review_state=SourceReviewState.CANDIDATE),
            )
            canonical_candidate = replace(
                chunk,
                provenance=replace(chunk.provenance, review_state=SourceReviewState.CANDIDATE),
            )
            if normalized_candidate == canonical_candidate:
                accepted.append(chunk)
        return tuple(accepted)

    def reconcile_manifest(self) -> tuple[str, ...]:
        """Explicitly repair the manifest projection from valid SQLite events.

        Immutable source IDs, metadata and file hashes must still match. A
        manifest-only approval with no persistent event history is rejected,
        never imported as an approval.
        """

        def mutate(connection, manifest, entries):
            currents = {
                record.metadata.source_id: record
                for record in self._all_records(connection)
                if record.is_current
            }
            if set(currents) - set(entries):
                raise SourceReviewConsistencyError("persistent registry contains source IDs missing from the manifest")
            changed: list[str] = []
            for source_id, entry in entries.items():
                ingestion = self._manifest_ingestion(entry)
                record = currents.get(source_id)
                if record is None:
                    if entry.get("review_state") != SourceReviewState.CANDIDATE.value or entry.get("review_events") != []:
                        raise SourceReviewConsistencyError(
                            "cannot import manifest review state without persistent event history"
                        )
                    continue
                if not self._metadata_matches_manifest(record.metadata, entry):
                    raise SourceReviewConsistencyError("persistent revision does not match manifest source bytes/metadata")
                if record.manifest_revision_sha256 != self._manifest_revision_sha256(entry):
                    raise SourceReviewConsistencyError(
                        "persistent revision provenance does not match manifest source revision"
                    )
                if ingestion.source.metadata != replace(record.metadata, review_state=SourceReviewState.CANDIDATE):
                    raise SourceReviewConsistencyError("persistent revision differs from current ingested source")
                before = (entry.get("review_state"), entry.get("review_events"), entry.get("retrieval_eligibility"))
                self._mirror_record(entry, record)
                after = (entry.get("review_state"), entry.get("review_events"), entry.get("retrieval_eligibility"))
                if before != after:
                    changed.append(source_id)
            prior_approval_status = manifest.get("approval_status")
            self._sync_approval_status(manifest, entries)
            summary_changed = prior_approval_status != manifest.get("approval_status")
            return tuple(sorted(changed)), bool(changed or summary_changed)

        return self._transaction(mutate)
