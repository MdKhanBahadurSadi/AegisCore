"""Small SQLite store for outputs produced by the offline evaluation harness.

Only completed, synthetic offline reports are accepted. This module does not
create assessment records independently of a workflow and has no execution API.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from aegiscore.execution import DEFAULT_EXECUTION_LEASE_SECONDS


SCHEMA_VERSION = 1


def _validate_positive_finite_number(value: Any, param_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{param_name} must be a positive numeric float")
    val_float = float(value)
    if math.isnan(val_float) or math.isinf(val_float) or val_float <= 0.0:
        raise ValueError(f"{param_name} must be a positive finite number")
    return val_float


def _parse_aware_iso_timestamp(value: Any) -> datetime:
    """Parse a non-empty ISO timestamp that carries a usable UTC offset."""
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("timestamp must be a non-empty ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("timestamp must be a valid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a valid timezone")
    return parsed


def _require_active_lease(record: dict[str, Any], lease_token: Any, now_dt: datetime) -> None:
    """Reject terminal writes unless the current worker owns a verifiable lease."""
    if not isinstance(lease_token, str) or not lease_token.strip():
        raise LocalStoreConflictError("execution lease token is missing; terminal transition rejected")
    if record.get("lease_token") != lease_token:
        raise LocalStoreConflictError("execution lease token mismatch; terminal transition rejected")
    try:
        exp_dt = _parse_aware_iso_timestamp(record.get("lease_expires_at"))
    except ValueError:
        raise LocalStoreConflictError(
            "execution lease expiry is missing or unverifiable; terminal transition rejected"
        ) from None
    if now_dt >= exp_dt:
        raise LocalStoreConflictError("execution lease has expired; terminal transition rejected")


class LocalStoreError(RuntimeError):
    """Base class for persistence failures safe to map to an unavailable state."""


class LocalStoreUnavailableError(LocalStoreError):
    """The configured database cannot be opened or written."""


class LocalStoreCorruptionError(LocalStoreError):
    """The database schema or stored JSON is malformed or unsupported."""


class LocalStoreConflictError(LocalStoreError):
    """A stable record identifier already exists with different content."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise LocalStoreCorruptionError("record is not JSON serializable") from exc


def _report_identity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove only wall-clock envelope fields so retries deduplicate reliably."""
    stable = json.loads(_canonical_json(payload))
    manifest = stable.get("manifest")
    if isinstance(manifest, dict):
        manifest.pop("start_time_iso", None)
        manifest.pop("end_time_iso", None)
    return stable


def _decode_json(raw: str, expected: type = dict) -> Any:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LocalStoreCorruptionError("stored record is malformed") from exc
    if not isinstance(value, expected):
        raise LocalStoreCorruptionError("stored record has an unexpected shape")
    return value


def _session_payload(raw: str) -> dict[str, Any]:
    payload = _decode_json(raw)
    result = payload.get("result")
    context = payload.get("case_context")
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("findings"), list)
        or context is not None and not isinstance(context, dict)
        or any(not isinstance(finding, dict) for finding in result["findings"])
    ):
        raise LocalStoreCorruptionError("stored offline session is malformed")
    return payload


def _report_payload(raw: str) -> dict[str, Any]:
    payload = _decode_json(raw)
    score = payload.get("score_summary")
    if (
        not isinstance(payload.get("manifest"), dict)
        or not isinstance(score, dict)
        or not isinstance(score.get("metrics"), dict)
        or not isinstance(payload.get("trial_agreement"), dict)
        or not isinstance(payload.get("raw_trial_runs"), list)
        or not isinstance(payload.get("aggregated_outcomes"), list)
        or not isinstance(score.get("total_cases"), int)
        or score["total_cases"] < 0
    ):
        raise LocalStoreCorruptionError("stored evaluation report is malformed")
    return payload


class LocalRecordStore:
    """Persistent storage for real offline-harness outputs.

    Construct with ``create_or_open`` for a workflow writer and
    ``open_existing`` for read-only API access. Read-only opens never create or
    alter database files.
    """

    def __init__(self, database_path: Path, *, read_only: bool) -> None:
        self.database_path = database_path
        self._read_only = read_only

    @staticmethod
    def _create_parent_directories(parent: Path) -> None:
        """Create only missing path components, privately on POSIX systems."""
        missing: list[Path] = []
        current = parent
        while not current.exists():
            missing.append(current)
            next_parent = current.parent
            if next_parent == current:
                raise LocalStoreUnavailableError("local record store parent is unavailable")
            current = next_parent
        if not current.is_dir():
            raise LocalStoreUnavailableError("local record store parent is not a directory")
        for directory in reversed(missing):
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                pass
            if not directory.is_dir():
                raise LocalStoreUnavailableError("local record store parent is not a directory")

    @staticmethod
    def _prepare_database_file(path: Path) -> None:
        """Ensure a SQLite file exists with owner-only POSIX permissions."""
        if path.exists():
            if not path.is_file():
                raise LocalStoreUnavailableError("local record store path is not a file")
            if os.name != "nt":
                os.chmod(path, 0o600)
            return
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            if not path.is_file():
                raise LocalStoreUnavailableError("local record store path is not a file") from None
            if os.name != "nt":
                os.chmod(path, 0o600)
        else:
            os.close(descriptor)

    @classmethod
    def create_or_open(cls, database_path: str | os.PathLike[str]) -> LocalRecordStore:
        if not isinstance(database_path, (str, os.PathLike)):
            raise LocalStoreUnavailableError("database path is invalid")
        raw = os.fspath(database_path)
        if not isinstance(raw, str) or not raw.strip() or raw == ":memory:":
            raise LocalStoreUnavailableError("database path must name a local SQLite file")
        connection: sqlite3.Connection | None = None
        try:
            path = Path(raw).expanduser().resolve(strict=False)
            cls._create_parent_directories(path.parent)
            cls._prepare_database_file(path)
            connection = sqlite3.connect(path, timeout=5.0, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA foreign_keys = ON")
            cls._initialize_schema(connection)
        except LocalStoreError:
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            raise LocalStoreUnavailableError("local record store is unavailable") from exc
        finally:
            if connection is not None:
                connection.close()
        return cls(path, read_only=False)

    @classmethod
    def open_existing(cls, database_path: str | os.PathLike[str]) -> LocalRecordStore:
        if not isinstance(database_path, (str, os.PathLike)):
            raise LocalStoreUnavailableError("database path is invalid")
        raw = os.fspath(database_path)
        if not isinstance(raw, str) or not raw.strip() or raw == ":memory:":
            raise LocalStoreUnavailableError("database path must name a local SQLite file")
        try:
            path = Path(raw).expanduser().resolve(strict=False)
            if not path.is_file():
                raise LocalStoreUnavailableError("local record store is not configured or unavailable")
            store = cls(path, read_only=True)
            with store._connection() as connection:
                store._validate_schema(connection)
            return store
        except LocalStoreError:
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            raise LocalStoreUnavailableError("local record store is unavailable") from exc

    @staticmethod
    def _initialize_schema(connection: sqlite3.Connection) -> None:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == SCHEMA_VERSION:
            LocalRecordStore._validate_schema(connection)
            return
        if version != 0:
            raise LocalStoreCorruptionError("unsupported local record store schema")
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if existing:
            raise LocalStoreCorruptionError("unversioned non-empty SQLite database cannot be initialized")
        connection.executescript(
            """
            BEGIN IMMEDIATE;
            CREATE TABLE evaluation_reports (
                report_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                fixture_dataset_id TEXT NOT NULL,
                fixture_dataset_version TEXT NOT NULL,
                runner_condition TEXT NOT NULL,
                runner_id TEXT NOT NULL,
                execution_status TEXT NOT NULL CHECK (execution_status = 'completed'),
                is_synthetic INTEGER NOT NULL CHECK (is_synthetic = 1),
                is_empirical INTEGER NOT NULL CHECK (is_empirical = 0),
                incomplete_case_count INTEGER NOT NULL CHECK (incomplete_case_count >= 0),
                failed_case_count INTEGER NOT NULL CHECK (failed_case_count >= 0),
                payload_json TEXT NOT NULL
            );
            CREATE TABLE offline_sessions (
                session_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL REFERENCES evaluation_reports(report_id) ON DELETE RESTRICT,
                run_id TEXT NOT NULL,
                runner_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                repeat_index INTEGER NOT NULL CHECK (repeat_index >= 0),
                started_at TEXT,
                ended_at TEXT,
                status TEXT NOT NULL CHECK (status IN ('completed', 'incomplete', 'failed')),
                disposition TEXT NOT NULL,
                fixture_dataset_id TEXT NOT NULL,
                fixture_dataset_version TEXT NOT NULL,
                execution_mode TEXT NOT NULL CHECK (execution_mode = 'offline_fixture'),
                is_synthetic INTEGER NOT NULL CHECK (is_synthetic = 1),
                is_empirical INTEGER NOT NULL CHECK (is_empirical = 0),
                payload_json TEXT NOT NULL,
                UNIQUE(report_id, run_id)
            );
            CREATE TABLE IF NOT EXISTS assessments (
                assessment_id TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('created', 'pending', 'running', 'completed', 'failed')),
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS offline_sessions_created_order ON offline_sessions(ended_at DESC, session_id);
            CREATE INDEX IF NOT EXISTS assessments_created_order ON assessments(created_at DESC, assessment_id);
            PRAGMA user_version = 1;
            COMMIT;
            """
        )
        LocalRecordStore._validate_schema(connection)

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version != SCHEMA_VERSION:
                raise LocalStoreCorruptionError("unsupported local record store schema")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            if not {"evaluation_reports", "offline_sessions"}.issubset(tables):
                raise LocalStoreCorruptionError("local record store schema is incomplete")
            expected = {
                "evaluation_reports": {
                    "report_id", "created_at", "fixture_dataset_id", "fixture_dataset_version",
                    "runner_condition", "runner_id", "execution_status", "is_synthetic",
                    "is_empirical", "incomplete_case_count", "failed_case_count", "payload_json",
                },
                "offline_sessions": {
                    "session_id", "report_id", "run_id", "runner_id", "case_id", "repeat_index",
                    "started_at", "ended_at", "status", "disposition", "fixture_dataset_id",
                    "fixture_dataset_version", "execution_mode", "is_synthetic", "is_empirical", "payload_json",
                },
                "assessments": {
                    "assessment_id", "target_url", "status", "created_at", "payload_json",
                },
            }
            for table in tables:
                if table in expected:
                    actual = {row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
                    if actual != expected[table]:
                        raise LocalStoreCorruptionError(f"local record store table {table} schema is malformed")
        except sqlite3.Error as exc:
            raise LocalStoreCorruptionError("local record store schema is malformed") from exc

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        try:
            if self._read_only:
                # as_uri percent-encodes URI-significant characters in valid
                # filesystem paths (for example '#', '?', and spaces). Without
                # this, read-only API opens can target the wrong filename.
                uri = f"{self.database_path.as_uri()}?mode=ro"
                connection = sqlite3.connect(uri, uri=True, timeout=5.0, isolation_level=None)
            else:
                connection = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("local record store is unavailable") from exc
        try:
            yield connection
        except LocalStoreError:
            raise
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("local record store is unavailable") from exc
        finally:
            connection.close()

    def persist_evaluation_report(self, report: Any) -> str:
        """Atomically persist one completed offline fixture harness report."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")
        # Import lazily to keep the harness and store modules acyclic at import time.
        from aegiscore.evaluation_harness import HarnessExecutionReport

        if not isinstance(report, HarnessExecutionReport):
            raise LocalStoreCorruptionError("only completed harness reports may be persisted")
        manifest = report.manifest
        if (
            manifest.execution_status != "completed"
            or not manifest.is_synthetic_simulation
            or not report.raw_trial_runs
        ):
            raise LocalStoreCorruptionError("only completed synthetic offline reports may be persisted")
        payload = report.to_dict()
        stable_payload = _report_identity_payload(payload)
        identity_digest = hashlib.sha256(_canonical_json(stable_payload).encode("utf-8")).hexdigest()
        report_id = f"report_{identity_digest[:32]}"
        created_at = manifest.end_time_iso
        if not isinstance(created_at, str) or not created_at:
            created_at = datetime.now(timezone.utc).isoformat()
        incomplete_count = sum(1 for outcome in report.aggregated_outcomes if outcome.is_incomplete)
        failed_count = sum(1 for outcome in report.aggregated_outcomes if outcome.error_status is not None)
        runner_id = report.raw_trial_runs[0].runner_id
        if any(run.runner_id != runner_id for run in report.raw_trial_runs):
            raise LocalStoreCorruptionError("evaluation report contains inconsistent runners")
        report_json = _canonical_json(payload)
        run_context = {outcome.case_id: outcome for outcome in report.aggregated_outcomes}

        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT payload_json FROM evaluation_reports WHERE report_id = ?", (report_id,)
                ).fetchone()
                if row is None:
                    connection.execute(
                        """INSERT INTO evaluation_reports (
                            report_id, created_at, fixture_dataset_id, fixture_dataset_version,
                            runner_condition, runner_id, execution_status, is_synthetic, is_empirical,
                            incomplete_case_count, failed_case_count, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, 'completed', 1, 0, ?, ?, ?)""",
                        (
                            report_id, created_at, manifest.fixture_dataset_id,
                            manifest.fixture_dataset_version, manifest.runner_condition, runner_id,
                            incomplete_count, failed_count, report_json,
                        ),
                    )
                else:
                    previous = _decode_json(row["payload_json"])
                    if _canonical_json(_report_identity_payload(previous)) != _canonical_json(stable_payload):
                        raise LocalStoreConflictError("report idempotency key conflicts with stored content")

                for run in report.raw_trial_runs:
                    session_id = "session_" + hashlib.sha256(
                        f"{report_id}\0{run.run_id}".encode("utf-8")
                    ).hexdigest()[:32]
                    case_outcome = run_context.get(run.case_id)
                    run_payload = run.to_dict()
                    run_payload["case_context"] = (
                        {
                            "locus": {
                                "target_uri": case_outcome.locus.target_uri,
                                "parameter": case_outcome.locus.parameter,
                                "cwe_id": case_outcome.locus.cwe_id,
                            },
                            "vulnerability_class": case_outcome.vulnerability_class,
                            "classification": case_outcome.classification,
                            "is_incomplete": case_outcome.is_incomplete,
                            "error_status": case_outcome.error_status,
                        }
                        if case_outcome is not None else None
                    )
                    run_json = _canonical_json(run_payload)
                    result_json = _canonical_json(run_payload.get("result"))
                    previous_session = connection.execute(
                        "SELECT payload_json, report_id FROM offline_sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()
                    if previous_session is not None:
                        previous_payload = _decode_json(previous_session["payload_json"])
                        if (
                            previous_session["report_id"] != report_id
                            or _canonical_json(previous_payload.get("result")) != result_json
                            or previous_payload.get("case_id") != run.case_id
                        ):
                            raise LocalStoreConflictError("session idempotency key conflicts with stored content")
                        continue
                    status = "failed" if run.result.error_status else (
                        "incomplete" if run.result.is_incomplete else "completed"
                    )
                    connection.execute(
                        """INSERT INTO offline_sessions (
                            session_id, report_id, run_id, runner_id, case_id, repeat_index,
                            started_at, ended_at, status, disposition, fixture_dataset_id,
                            fixture_dataset_version, execution_mode, is_synthetic, is_empirical, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'offline_fixture', 1, 0, ?)""",
                        (
                            session_id, report_id, run.run_id, run.runner_id, run.case_id,
                            run.repeat_index, run.start_time_utc, run.end_time_utc, status,
                            run.result.decision.value, manifest.fixture_dataset_id,
                            manifest.fixture_dataset_version, run_json,
                        ),
                    )
                connection.commit()
        except LocalStoreError:
            raise
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("local record store transaction failed") from exc
        return report_id

    @staticmethod
    def _page_args(offset: int, limit: int) -> None:
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("offset must be non-negative and limit must be between 1 and 100")

    def list_sessions(self, *, offset: int = 0, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        self._page_args(offset, limit)
        with self._connection() as connection:
            connection.execute("BEGIN")
            self._validate_schema(connection)
            total = connection.execute("SELECT COUNT(*) FROM offline_sessions").fetchone()[0]
            rows = connection.execute(
                """SELECT session_id, report_id, run_id, runner_id, case_id, repeat_index,
                    started_at, ended_at, status, disposition, fixture_dataset_id,
                    fixture_dataset_version, execution_mode, is_synthetic, is_empirical
                   FROM offline_sessions ORDER BY ended_at DESC, session_id LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
            connection.commit()
        return [dict(row) for row in rows], total

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            self._validate_schema(connection)
            row = connection.execute("SELECT * FROM offline_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = _session_payload(record.pop("payload_json"))
        return record

    def list_reports(self, *, offset: int = 0, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        self._page_args(offset, limit)
        with self._connection() as connection:
            connection.execute("BEGIN")
            self._validate_schema(connection)
            total = connection.execute("SELECT COUNT(*) FROM evaluation_reports").fetchone()[0]
            rows = connection.execute(
                """SELECT report_id, created_at, fixture_dataset_id, fixture_dataset_version,
                    runner_condition, runner_id, execution_status, is_synthetic, is_empirical,
                    incomplete_case_count, failed_case_count, payload_json
                   FROM evaluation_reports ORDER BY created_at DESC, report_id LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
            connection.commit()
        records: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            payload = _report_payload(record.pop("payload_json"))
            record["summary"] = payload["score_summary"]
            record["total_cases"] = payload["score_summary"]["total_cases"]
            record["trial_agreement"] = payload.get("trial_agreement")
            records.append(record)
        return records, total

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            self._validate_schema(connection)
            row = connection.execute("SELECT * FROM evaluation_reports WHERE report_id = ?", (report_id,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = _report_payload(record.pop("payload_json"))
        return record

    def dashboard_summary(self) -> dict[str, int]:
        with self._connection() as connection:
            # Keep all aggregate queries on one SQLite snapshot so a concurrent
            # report+session commit cannot produce mixed dashboard counts.
            connection.execute("BEGIN")
            self._validate_schema(connection)
            row = connection.execute(
                """SELECT COUNT(*) AS session_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
                    SUM(CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END) AS incomplete_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                    SUM(CASE WHEN disposition = 'verified' THEN 1 ELSE 0 END) AS verified_count,
                    SUM(CASE WHEN disposition = 'abstained' THEN 1 ELSE 0 END) AS abstained_count
                   FROM offline_sessions"""
            ).fetchone()
            payload_rows = connection.execute("SELECT payload_json FROM offline_sessions").fetchall()
            reports = connection.execute("SELECT COUNT(*) FROM evaluation_reports").fetchone()[0]
            connection.commit()
        findings = 0
        for payload_row in payload_rows:
            findings += len(_session_payload(payload_row["payload_json"])["result"]["findings"])
        return {
            "session_count": row["session_count"] or 0,
            "completed_count": row["completed_count"] or 0,
            "incomplete_count": row["incomplete_count"] or 0,
            "failed_count": row["failed_count"] or 0,
            "verified_run_count": row["verified_count"] or 0,
            "abstained_run_count": row["abstained_count"] or 0,
            "finding_count": findings,
            "report_count": reports,
            "synthetic_offline_run_count": row["session_count"] or 0,
            "empirical_run_count": 0,
        }

    def all_findings(self, *, offset: int = 0, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        self._page_args(offset, limit)
        with self._connection() as connection:
            self._validate_schema(connection)
            rows = connection.execute(
                "SELECT session_id, report_id, case_id, ended_at, payload_json FROM offline_sessions ORDER BY ended_at DESC, session_id"
            ).fetchall()
        findings: list[dict[str, Any]] = []
        for row in rows:
            findings.extend(self._findings_from_session(row))
        total = len(findings)
        return findings[offset : offset + limit], total

    def findings_for_session(
        self, session_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[dict[str, Any]], int]:
        self._page_args(offset, limit)
        with self._connection() as connection:
            self._validate_schema(connection)
            row = connection.execute(
                """SELECT session_id, report_id, case_id, ended_at, payload_json
                   FROM offline_sessions WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
        if row is None:
            return [], 0
        findings = self._findings_from_session(row)
        return findings[offset : offset + limit], len(findings)

    @staticmethod
    def _findings_from_session(row: sqlite3.Row) -> list[dict[str, Any]]:
        payload = _session_payload(row["payload_json"])
        context = payload.get("case_context") or {}
        findings: list[dict[str, Any]] = []
        for finding in payload["result"]["findings"]:
            original_id = finding.get("finding_id")
            if not isinstance(original_id, str):
                raise LocalStoreCorruptionError("stored finding is malformed")
            finding_id = "finding_" + hashlib.sha256(
                f"{row['session_id']}\0{original_id}".encode("utf-8")
            ).hexdigest()[:32]
            findings.append({
                "finding_id": finding_id,
                "source_finding_id": original_id,
                "session_id": row["session_id"],
                "report_id": row["report_id"],
                "case_id": row["case_id"],
                "recorded_at": row["ended_at"],
                "specialist_role": finding.get("specialist_role"),
                "vulnerability_identified": finding.get("vulnerability_identified"),
                "cwe_id": finding.get("cwe_id"),
                "severity": finding.get("severity"),
                "decision": finding.get("decision"),
                "evidence_refs": finding.get("evidence_citations", []),
                "rationale": finding.get("rationale", ""),
                "locus": context.get("locus"),
                "vulnerability_class": context.get("vulnerability_class"),
                "is_synthetic": True,
                "is_empirical": False,
                "execution_mode": "offline_fixture",
            })
        return findings

    def get_finding(self, finding_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            self._validate_schema(connection)
            rows = connection.execute(
                "SELECT session_id, report_id, case_id, ended_at, payload_json FROM offline_sessions"
            ).fetchall()
        for row in rows:
            for finding in self._findings_from_session(row):
                if finding["finding_id"] == finding_id:
                    return finding
        return None

    def _ensure_assessments_table(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS assessments (
                assessment_id TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('created', 'pending', 'running', 'completed', 'failed')),
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS assessments_created_order ON assessments(created_at DESC, assessment_id)"
        )

    def create_assessment(
        self,
        target_url: str,
        *,
        target_id: str,
        canonical_endpoint: str,
        authorization_ref: str,
        registration_version: str,
        authorization_provenance: dict[str, Any],
        status: str = "created",
        assessment_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Atomically persist one new assessment record."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")
        if not isinstance(target_url, str) or not target_url.strip():
            raise LocalStoreCorruptionError("target_url must be non-empty string")
        binding_fields = (target_id, canonical_endpoint, authorization_ref, registration_version)
        if any(not isinstance(value, str) or not value.strip() for value in binding_fields):
            raise LocalStoreCorruptionError("assessment requires a complete authorized target binding")
        provenance_fields = {
            "authorization_ref", "issuer_id", "key_id", "target_id", "canonical_endpoint",
            "registration_version", "issued_at", "expires_at", "verified_at",
            "revocation_checked_at", "revocation_snapshot_expires_at", "signature_sha256",
        }
        if (
            not isinstance(authorization_provenance, dict)
            or not provenance_fields.issubset(authorization_provenance)
            or any(
                not isinstance(authorization_provenance.get(key), str)
                or not authorization_provenance[key].strip()
                for key in provenance_fields
            )
            or authorization_provenance.get("signature_valid") is not True
            or authorization_provenance.get("revoked") is not False
        ):
            raise LocalStoreCorruptionError("assessment requires verified authorization provenance")
        if (
            authorization_provenance["authorization_ref"] != authorization_ref
            or authorization_provenance["target_id"] != target_id
            or authorization_provenance["canonical_endpoint"] != canonical_endpoint
            or authorization_provenance["registration_version"] != registration_version
        ):
            raise LocalStoreCorruptionError("authorization provenance does not match target binding")
        if target_url != canonical_endpoint:
            raise LocalStoreCorruptionError("target_url must equal its canonical authorized endpoint")

        valid_statuses = {"created", "pending", "running", "completed", "failed"}
        if status not in valid_statuses:
            raise LocalStoreCorruptionError(f"status must be one of {sorted(valid_statuses)}")

        now_iso = datetime.now(timezone.utc).isoformat()
        final_created_at = created_at if (isinstance(created_at, str) and created_at.strip()) else now_iso

        if assessment_id is None:
            random_token = os.urandom(16).hex()
            raw_hash = hashlib.sha256(
                f"{target_url}\0{final_created_at}\0{random_token}".encode("utf-8")
            ).hexdigest()[:32]
            assessment_id = f"asm_{raw_hash}"
        elif not isinstance(assessment_id, str) or not assessment_id.startswith("asm_"):
            raise LocalStoreCorruptionError("assessment_id must start with asm_")

        record = {
            "assessment_id": assessment_id,
            "target_url": canonical_endpoint,
            "target_id": target_id,
            "canonical_endpoint": canonical_endpoint,
            "authorization_ref": authorization_ref,
            "registration_version": registration_version,
            "authorization_provenance": authorization_provenance,
            "status": status,
            "created_at": final_created_at,
        }
        payload_json = _canonical_json(record)

        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_assessments_table(connection)
                connection.execute(
                    """INSERT INTO assessments (assessment_id, target_url, status, created_at, payload_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (assessment_id, canonical_endpoint, status, final_created_at, payload_json),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise LocalStoreConflictError(f"assessment {assessment_id} already exists") from exc
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("failed to create assessment record") from exc

        return record

    def update_assessment_status(
        self,
        assessment_id: str,
        new_status: str,
        execution_result: dict[str, Any] | None = None,
        lease_token: str | None = None,
        lease_duration_seconds: float = DEFAULT_EXECUTION_LEASE_SECONDS,
    ) -> dict[str, Any]:
        """Atomically transition assessment status and update payload JSON."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")

        valid_statuses = {"created", "pending", "running", "completed", "failed"}
        if new_status not in valid_statuses:
            raise LocalStoreCorruptionError(f"new_status must be one of {sorted(valid_statuses)}")

        ALLOWED_TRANSITIONS: dict[str, set[str]] = {
            "created": {"pending", "running"},
            "pending": {"running", "failed"},
            "running": {"completed", "failed"},
            "completed": set(),
            "failed": set(),
        }

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_assessments_table(connection)
            now_dt = datetime.now(timezone.utc)
            now_iso = now_dt.isoformat()

            row = connection.execute(
                "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
            ).fetchone()
            if row is None:
                raise LocalStoreCorruptionError(f"assessment {assessment_id} not found")

            record = _decode_json(row["payload_json"])
            current_status = record.get("status")

            if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
                raise LocalStoreConflictError(
                    f"invalid status transition from '{current_status}' to '{new_status}'"
                )

            # Every terminal transition needs a current, verifiable lease.
            if new_status in ("completed", "failed"):
                _require_active_lease(record, lease_token, now_dt)

            # Generate lease when transitioning to running
            if new_status == "running":
                lease_s = _validate_positive_finite_number(lease_duration_seconds, "lease_duration_seconds")
                new_lease = f"lease_{os.urandom(16).hex()}"
                lease_exp = (now_dt + timedelta(seconds=lease_s)).isoformat()
                record["lease_token"] = new_lease
                record["lease_expires_at"] = lease_exp

            # Clear lease on terminal states
            if new_status in ("completed", "failed"):
                record.pop("lease_token", None)
                record.pop("lease_expires_at", None)

            record["status"] = new_status
            record["updated_at"] = now_iso
            if execution_result is not None:
                record["execution_result"] = execution_result

            payload_json = _canonical_json(record)
            connection.execute(
                "UPDATE assessments SET status = ?, payload_json = ? WHERE assessment_id = ?",
                (new_status, payload_json, assessment_id),
            )
            connection.commit()

        return record

    def get_assessment(self, assessment_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            self._validate_schema(connection)
            has_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'"
            ).fetchone()
            if not has_table:
                return None
            row = connection.execute(
                "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
            ).fetchone()
        if row is None:
            return None
        return _decode_json(row["payload_json"])

    def list_assessments(self, *, offset: int = 0, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
        self._page_args(offset, limit)
        with self._connection() as connection:
            connection.execute("BEGIN")
            self._validate_schema(connection)
            has_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'"
            ).fetchone()
            if not has_table:
                connection.commit()
                return [], 0
            total = connection.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
            rows = connection.execute(
                """SELECT payload_json FROM assessments ORDER BY created_at DESC, assessment_id LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
            connection.commit()
        records = [_decode_json(row["payload_json"]) for row in rows]
        return records, total

    def _ensure_pipeline_tables(self, connection: sqlite3.Connection) -> None:
        self._ensure_assessments_table(connection)
        connection.execute(
            """CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
                evidence_type TEXT NOT NULL,
                source TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS evidence_asm_order ON evidence(assessment_id, observed_at DESC)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS findings (
                finding_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(assessment_id, rule_id)
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS findings_asm_order ON findings(assessment_id, created_at DESC)"
        )

    def save_evidence(self, assessment_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        """Atomically persist normalized evidence for an assessment."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")

        evidence_id = evidence.get("evidence_id")
        if not evidence_id:
            raw_hash = hashlib.sha256(f"{assessment_id}\0{os.urandom(16).hex()}".encode("utf-8")).hexdigest()[:32]
            evidence_id = f"evi_{raw_hash}"
            evidence["evidence_id"] = evidence_id

        evidence["assessment_id"] = assessment_id
        payload_json = _canonical_json(evidence)

        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_pipeline_tables(connection)
                connection.execute(
                    """INSERT OR REPLACE INTO evidence (evidence_id, assessment_id, evidence_type, source, observed_at, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        evidence_id,
                        assessment_id,
                        evidence.get("evidence_type", "http_security_headers"),
                        evidence.get("source", "passive_head_observation"),
                        evidence.get("observed_at", datetime.now(timezone.utc).isoformat()),
                        payload_json,
                    ),
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("failed to persist evidence record") from exc

        return evidence

    def save_findings(self, assessment_id: str, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Atomically persist generated security findings for an assessment."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")

        if not findings:
            return []

        saved: list[dict[str, Any]] = []
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_pipeline_tables(connection)
                for f in findings:
                    f_id = f.get("finding_id")
                    rule_id = f.get("rule_id", "UNKNOWN")
                    if not f_id:
                        raw_hash = hashlib.sha256(f"{assessment_id}\0{rule_id}".encode("utf-8")).hexdigest()[:32]
                        f_id = f"fnd_{raw_hash}"
                        f["finding_id"] = f_id

                    f["assessment_id"] = assessment_id

                    # Verify evidence references belong to assessment
                    ev_ids = f.get("evidence_ids", ())
                    valid_ev_ids = [
                        e_id for e_id in ev_ids
                        if connection.execute(
                            "SELECT 1 FROM evidence WHERE evidence_id = ? AND assessment_id = ?", (e_id, assessment_id)
                        ).fetchone() is not None
                    ]
                    if not valid_ev_ids:
                        continue

                    f["evidence_ids"] = tuple(valid_ev_ids)
                    payload_json = _canonical_json(f)
                    connection.execute(
                        """INSERT OR REPLACE INTO findings (finding_id, assessment_id, rule_id, severity, confidence, created_at, payload_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            f_id,
                            assessment_id,
                            rule_id,
                            f.get("severity", "info"),
                            f.get("confidence", "low"),
                            f.get("created_at", datetime.now(timezone.utc).isoformat()),
                            payload_json,
                        ),
                    )
                    saved.append(f)
                connection.commit()
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("failed to persist finding records") from exc

        return saved

    def save_pipeline_result(
        self,
        assessment_id: str,
        evidence: dict[str, Any],
        findings: list[dict[str, Any]],
        final_status: str,
        execution_result: dict[str, Any],
        lease_token: str | None = None,
    ) -> dict[str, Any]:
        """Atomically persist evidence, findings, execution result, and assessment status transition."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")

        valid_statuses = {"created", "pending", "running", "completed", "failed"}
        if final_status not in valid_statuses:
            raise LocalStoreCorruptionError(f"final_status must be one of {sorted(valid_statuses)}")

        ALLOWED_TRANSITIONS: dict[str, set[str]] = {
            "created": {"pending", "running"},
            "pending": {"running", "failed"},
            "running": {"completed", "failed"},
            "completed": set(),
            "failed": set(),
        }

        evidence_id = evidence.get("evidence_id")
        if not evidence_id:
            raw_hash = hashlib.sha256(f"{assessment_id}\0{os.urandom(16).hex()}".encode("utf-8")).hexdigest()[:32]
            evidence_id = f"evi_{raw_hash}"
            evidence["evidence_id"] = evidence_id

        evidence["assessment_id"] = assessment_id
        evidence_json = _canonical_json(evidence)

        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_pipeline_tables(connection)
                now_dt = datetime.now(timezone.utc)
                now_iso = now_dt.isoformat()

                row = connection.execute(
                    "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
                ).fetchone()
                if row is None:
                    raise LocalStoreCorruptionError(f"assessment {assessment_id} not found")

                record = _decode_json(row["payload_json"])
                current_status = record.get("status")

                if final_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
                    raise LocalStoreConflictError(
                        f"invalid status transition from '{current_status}' to '{final_status}'"
                    )

                # Lease validation also covers pending -> failed if that legacy transition is requested.
                if final_status in ("completed", "failed"):
                    _require_active_lease(record, lease_token, now_dt)

                # Clear lease fields upon completion/failure
                record.pop("lease_token", None)
                record.pop("lease_expires_at", None)

                # Persist Evidence
                connection.execute(
                    """INSERT OR REPLACE INTO evidence (evidence_id, assessment_id, evidence_type, source, observed_at, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        evidence_id,
                        assessment_id,
                        evidence.get("evidence_type", "http_security_headers"),
                        evidence.get("source", "passive_head_observation"),
                        evidence.get("observed_at", now_iso),
                        evidence_json,
                    ),
                )

                # Persist Findings (verifying evidence references belong to this assessment)
                for f in findings:
                    f_id = f.get("finding_id")
                    rule_id = f.get("rule_id", "UNKNOWN")
                    if not f_id:
                        raw_hash = hashlib.sha256(f"{assessment_id}\0{rule_id}".encode("utf-8")).hexdigest()[:32]
                        f_id = f"fnd_{raw_hash}"
                        f["finding_id"] = f_id

                    f["assessment_id"] = assessment_id

                    ev_ids = f.get("evidence_ids", ())
                    valid_ev_ids = [
                        e_id for e_id in ev_ids
                        if connection.execute(
                            "SELECT 1 FROM evidence WHERE evidence_id = ? AND assessment_id = ?", (e_id, assessment_id)
                        ).fetchone() is not None
                    ]
                    if not valid_ev_ids:
                        continue

                    f["evidence_ids"] = tuple(valid_ev_ids)
                    finding_json = _canonical_json(f)

                    connection.execute(
                        """INSERT OR REPLACE INTO findings (finding_id, assessment_id, rule_id, severity, confidence, created_at, payload_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            f_id,
                            assessment_id,
                            rule_id,
                            f.get("severity", "info"),
                            f.get("confidence", "low"),
                            f.get("created_at", now_iso),
                            finding_json,
                        ),
                    )

                record["status"] = final_status
                record["updated_at"] = now_iso
                record["execution_result"] = execution_result

                payload_json = _canonical_json(record)
                connection.execute(
                    "UPDATE assessments SET status = ?, payload_json = ? WHERE assessment_id = ?",
                    (final_status, payload_json, assessment_id),
                )

                connection.commit()

        except (LocalStoreConflictError, LocalStoreCorruptionError):
            raise
        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("failed to persist pipeline transaction") from exc

        return record

    def renew_execution_lease(
        self,
        assessment_id: str,
        lease_token: str,
        extension_seconds: float = DEFAULT_EXECUTION_LEASE_SECONDS,
    ) -> dict[str, Any]:
        """Renew and extend an active execution lease for a running assessment."""
        if self._read_only:
            raise LocalStoreUnavailableError("local record store is read-only")

        if not lease_token or not isinstance(lease_token, str) or not lease_token.strip():
            raise LocalStoreConflictError("mandatory lease_token missing or invalid")

        ext_s = _validate_positive_finite_number(extension_seconds, "extension_seconds")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_pipeline_tables(connection)
            now_dt = datetime.now(timezone.utc)
            now_iso = now_dt.isoformat()

            row = connection.execute(
                "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
            ).fetchone()
            if row is None:
                raise LocalStoreCorruptionError(f"assessment {assessment_id} not found")

            record = _decode_json(row["payload_json"])
            if record.get("status") != "running":
                raise LocalStoreConflictError(f"cannot renew lease: assessment status is '{record.get('status')}', not 'running'")

            if record.get("lease_token") != lease_token:
                raise LocalStoreConflictError("cannot renew lease: lease token mismatch or lease expired")

            lease_exp_str = record.get("lease_expires_at")
            try:
                exp_dt = _parse_aware_iso_timestamp(lease_exp_str)
            except ValueError:
                raise LocalStoreConflictError(
                    "cannot renew lease: expiry is missing or unverifiable"
                ) from None

            if now_dt >= exp_dt:
                raise LocalStoreConflictError("cannot renew lease: current lease has already expired")

            new_expires_at = (now_dt + timedelta(seconds=ext_s)).isoformat()
            record["lease_expires_at"] = new_expires_at
            record["updated_at"] = now_iso

            payload_json = _canonical_json(record)
            connection.execute(
                "UPDATE assessments SET payload_json = ? WHERE assessment_id = ?",
                (payload_json, assessment_id),
            )
            connection.commit()

        return record

    def recover_stale_assessments(self) -> list[dict[str, Any]]:
        """Identify and recover assessments stuck in 'running' state past their lease expiration.

        Transitions genuinely expired assessments atomically to 'failed' status with sanitized recovery metadata.
        Returns the list of recovered assessment records.
        """
        if self._read_only:
            return []

        # Read-only check for running assessments before starting a write transaction
        with self._connection() as conn:
            self._validate_schema(conn)
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='assessments'"
            ).fetchone()
            if not has_table:
                return []
            has_running = conn.execute(
                "SELECT 1 FROM assessments WHERE status = 'running'"
            ).fetchone()
            if not has_running:
                return []

        recovered_records: list[dict[str, Any]] = []

        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_pipeline_tables(connection)
                now_dt = datetime.now(timezone.utc)
                now_iso = now_dt.isoformat()

                rows = connection.execute(
                    "SELECT assessment_id, payload_json FROM assessments WHERE status = 'running'"
                ).fetchall()

                for row in rows:
                    assessment_id, payload_raw = row[0], row[1]
                    record = _decode_json(payload_raw)

                    lease_exp_str = record.get("lease_expires_at")
                    try:
                        exp_dt = _parse_aware_iso_timestamp(lease_exp_str)
                    except ValueError:
                        # Missing or unverifiable expiries never qualify for recovery.
                        continue
                    if now_dt >= exp_dt:
                        record["status"] = "failed"
                        record["updated_at"] = now_iso
                        record.pop("lease_token", None)
                        record.pop("lease_expires_at", None)
                        record["recovery_metadata"] = {
                            "recovered": True,
                            "recovered_at": now_iso,
                            "reason": "Execution lease expired and assessment was recovered",
                        }

                        payload_json = _canonical_json(record)
                        connection.execute(
                            "UPDATE assessments SET status = 'failed', payload_json = ? WHERE assessment_id = ? AND status = 'running'",
                            (payload_json, assessment_id),
                        )
                        recovered_records.append(record)

                connection.commit()

        except sqlite3.Error as exc:
            raise LocalStoreUnavailableError("failed to execute stale assessment recovery") from exc

        return recovered_records

    def list_evidence(self, assessment_id: str) -> list[dict[str, Any]]:
        """List all evidence records for a given assessment."""
        with self._connection() as connection:
            self._validate_schema(connection)
            has_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence'"
            ).fetchone()
            if not has_table:
                return []
            rows = connection.execute(
                "SELECT payload_json FROM evidence WHERE assessment_id = ? ORDER BY observed_at DESC",
                (assessment_id,),
            ).fetchall()
        return [_decode_json(r["payload_json"]) for r in rows]
    def list_findings(self, assessment_id: str) -> list[dict[str, Any]]:
        """List all generated findings for a given assessment."""
        with self._connection() as connection:
            self._validate_schema(connection)
            has_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='findings'"
            ).fetchone()
            if not has_table:
                return []
            rows = connection.execute(
                "SELECT payload_json FROM findings WHERE assessment_id = ? ORDER BY created_at DESC",
                (assessment_id,),
            ).fetchall()
        return [_decode_json(r["payload_json"]) for r in rows]
