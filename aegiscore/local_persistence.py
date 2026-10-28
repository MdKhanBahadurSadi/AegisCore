"""Small SQLite store for outputs produced by the offline evaluation harness.

Only completed, synthetic offline reports are accepted. This module does not
create assessment records independently of a workflow and has no execution API.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1


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
            path.parent.mkdir(parents=True, exist_ok=True)
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
            CREATE INDEX offline_sessions_created_order ON offline_sessions(ended_at DESC, session_id);
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
            if tables != {"evaluation_reports", "offline_sessions"}:
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
            }
            for table, columns in expected.items():
                actual = {row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
                if actual != columns:
                    raise LocalStoreCorruptionError("local record store schema is malformed")
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
