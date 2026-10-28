"""Persistence/API tests use only synthetic offline replay cases and temp SQLite files."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.evaluation import (
    AdjudicationState,
    CanonicalLocus,
    EvaluationCaseManifestRecord,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    RunnerCondition,
)
from aegiscore.evaluation_harness import (
    EvaluationHarness,
    OrchestrationReplayAdapter,
    RunnerConditionRegistry,
    create_orchestration_case_fixture,
    create_orchestration_replay_adapter,
)
from aegiscore.local_persistence import (
    LocalRecordStore,
    LocalStoreConflictError,
    LocalStoreCorruptionError,
    LocalStoreUnavailableError,
)
from tests.auth_helpers import authenticated_client, configured_test_app


def _case_and_truth() -> tuple[EvaluationCaseManifestRecord, GroundTruthRecord]:
    locus = CanonicalLocus(
        target_uri="http://127.0.0.1:3000/fixture/item",
        parameter="item_id",
        cwe_id="CWE-89",
    )
    case = EvaluationCaseManifestRecord(
        case_id="CASE-PERSIST-01",
        locus=locus,
        benchmark_target="synthetic-persistence-fixture",
        benchmark_version="1.0",
        vulnerability_class="SQL injection",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="synthetic-test-only",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )
    truth = GroundTruthRecord(
        case_id=case.case_id,
        locus=locus,
        expected_status=GroundTruthStatus.VULNERABLE,
        vulnerability_class="SQL injection",
        evidence_reference="synthetic-fixture-ref",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="synthetic-test-only",
    )
    return case, truth


def _run(path: Path):
    case, truth = _case_and_truth()
    adapter = create_orchestration_replay_adapter("persist-test-runner", [case])
    registry = RunnerConditionRegistry()
    registry.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    writer = LocalRecordStore.create_or_open(path)
    harness = EvaluationHarness(registry=registry, record_store=writer)
    report = harness.execute(
        RunnerCondition.PROPOSED_MULTI_AGENT,
        [case],
        [truth],
        fixture_dataset_id="synthetic-persistence-fixture",
        fixture_dataset_version="1.0",
    )
    return report


def test_schema_creation_and_workflow_output_survives_store_reopen(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    report = _run(database)

    reopened = LocalRecordStore.open_existing(database)
    sessions, session_total = reopened.list_sessions()
    reports, report_total = reopened.list_reports()
    findings, finding_total = reopened.all_findings()
    summary = reopened.dashboard_summary()

    assert report.manifest.is_synthetic_simulation is True
    assert session_total == len(report.raw_trial_runs) == 1
    assert report_total == 1
    assert finding_total == len(report.raw_trial_runs[0].result.findings)
    assert sessions[0]["execution_mode"] == "offline_fixture"
    assert sessions[0]["status"] == "completed"
    assert findings[0]["evidence_refs"] == list(report.raw_trial_runs[0].result.findings[0].evidence_citations)
    assert findings[0]["is_synthetic"] is True
    assert findings[0]["is_empirical"] is False
    assert reports[0]["report_id"].startswith("report_")
    assert reports[0]["incomplete_case_count"] == 0
    assert summary["synthetic_offline_run_count"] == 1
    assert summary["empirical_run_count"] == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_same_completed_report_is_idempotent_and_duplicate_content_does_not_duplicate_rows(
    tmp_path: Path,
) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    _run(database)

    store = LocalRecordStore.open_existing(database)
    sessions, session_count = store.list_sessions()
    reports, report_count = store.list_reports()
    assert session_count == 1
    assert report_count == 1
    assert sessions[0]["report_id"] == reports[0]["report_id"]


def test_concurrent_duplicate_writes_and_reads_preserve_consistent_records(
    tmp_path: Path,
) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    case, truth = _case_and_truth()
    registry = RunnerConditionRegistry()
    registry.register_offline_replay_adapter(
        RunnerCondition.PROPOSED_MULTI_AGENT,
        create_orchestration_replay_adapter("parallel-writer", [case]),
    )
    report = EvaluationHarness(registry=registry).execute(
        RunnerCondition.PROPOSED_MULTI_AGENT,
        [case],
        [truth],
        fixture_dataset_id="parallel-write-fixture",
    )

    def write_duplicate() -> str:
        writer = LocalRecordStore.create_or_open(database)
        return writer.persist_evaluation_report(report)

    def read_snapshot() -> tuple[int, int, int]:
        summary = LocalRecordStore.open_existing(database).dashboard_summary()
        return (
            summary["session_count"],
            summary["report_count"],
            summary["finding_count"],
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        writes = [executor.submit(write_duplicate) for _ in range(4)]
        reads = [executor.submit(read_snapshot) for _ in range(4)]

    stored_report_id = LocalRecordStore.open_existing(database).list_reports()[0][0][
        "report_id"
    ]
    assert {future.result() for future in writes} == {stored_report_id}
    for future in reads:
        session_count, report_count, finding_count = future.result()
        assert (session_count, report_count) in {(1, 1), (2, 2)}
        assert finding_count == session_count

    final_summary = LocalRecordStore.open_existing(database).dashboard_summary()
    assert final_summary["session_count"] == 2
    assert final_summary["report_count"] == 2
    assert final_summary["finding_count"] == 2


def test_unavailable_and_unversioned_stores_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(LocalStoreUnavailableError):
        LocalRecordStore.open_existing(tmp_path / "missing.sqlite3")

    malformed = tmp_path / "unversioned.sqlite3"
    with sqlite3.connect(malformed) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    with pytest.raises(LocalStoreCorruptionError):
        LocalRecordStore.create_or_open(malformed)


def test_unsupported_schema_version_is_not_migrated_or_rewritten(tmp_path: Path) -> None:
    database = tmp_path / "future-version.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 99")
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    with pytest.raises(LocalStoreCorruptionError):
        LocalRecordStore.create_or_open(database)

    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_read_only_open_escapes_uri_special_characters_in_database_path(
    tmp_path: Path,
) -> None:
    database_directory = tmp_path / "local # records 100%"
    database_directory.mkdir()
    database = database_directory / "records #.sqlite3"
    _run(database)

    assert LocalRecordStore.open_existing(database).dashboard_summary()[
        "session_count"
    ] == 1
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        assert client.get("/sessions").status_code == 200


def test_malformed_persisted_json_is_reported_as_corruption(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    report_id = LocalRecordStore.open_existing(database).list_reports()[0][0]["report_id"]
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE evaluation_reports SET payload_json = '{' ")

    with pytest.raises(LocalStoreCorruptionError):
        LocalRecordStore.open_existing(database).get_report(report_id)


def test_incomplete_or_non_synthetic_reports_are_rejected(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    report = _run(database)
    store = LocalRecordStore.create_or_open(database)
    non_synthetic = replace(
        report,
        manifest=replace(report.manifest, is_synthetic_simulation=False),
    )

    with pytest.raises(LocalStoreCorruptionError):
        store.persist_evaluation_report(non_synthetic)


def test_abstention_is_persisted_without_inventing_findings(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    case, truth = _case_and_truth()
    fixture = create_orchestration_case_fixture(case, evidence_text="")
    adapter = OrchestrationReplayAdapter("abstain-test-runner", {case.case_id: fixture})
    registry = RunnerConditionRegistry()
    registry.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    report = EvaluationHarness(
        registry=registry,
        record_store=LocalRecordStore.create_or_open(database),
    ).execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [truth])

    store = LocalRecordStore.open_existing(database)
    sessions, _ = store.list_sessions()
    findings, finding_count = store.all_findings()
    assert report.raw_trial_runs[0].result.decision.value == "abstained"
    assert sessions[0]["disposition"] == "abstained"
    assert finding_count == 0
    assert findings == []
    assert store.dashboard_summary()["abstained_run_count"] == 1


def test_scope_failure_is_persisted_as_incomplete_with_actual_diagnostic(
    tmp_path: Path,
) -> None:
    database = tmp_path / "records.sqlite3"
    case, truth = _case_and_truth()
    fixture = create_orchestration_case_fixture(
        case,
        target_url="http://8.8.8.8/fixture",
    )
    adapter = OrchestrationReplayAdapter("failure-test-runner", {case.case_id: fixture})
    registry = RunnerConditionRegistry()
    registry.register_offline_replay_adapter(RunnerCondition.PROPOSED_MULTI_AGENT, adapter)
    report = EvaluationHarness(
        registry=registry,
        record_store=LocalRecordStore.create_or_open(database),
    ).execute(RunnerCondition.PROPOSED_MULTI_AGENT, [case], [truth])

    store = LocalRecordStore.open_existing(database)
    sessions, _ = store.list_sessions()
    detail = store.get_session(sessions[0]["session_id"])
    reports, _ = store.list_reports()
    assert report.raw_trial_runs[0].result.is_incomplete is True
    assert sessions[0]["status"] == "failed"
    assert "ScopeViolationError" in detail["payload"]["result"]["error_status"]
    assert reports[0]["failed_case_count"] == 1
    assert store.dashboard_summary()["failed_count"] == 1


def test_transaction_failure_rolls_back_report_and_sessions(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    report = _run(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TRIGGER reject_session BEFORE INSERT ON offline_sessions
               BEGIN SELECT RAISE(ABORT, 'synthetic transaction failure'); END"""
        )
        connection.commit()
    # Use a report with a different identity so the report insert is attempted.
    changed_report = replace(
        report,
        unique_case_loci_count=report.unique_case_loci_count + 1,
    )
    with pytest.raises(LocalStoreUnavailableError):
        LocalRecordStore.create_or_open(database).persist_evaluation_report(changed_report)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM evaluation_reports").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM offline_sessions").fetchone()[0] == 1


def test_api_empty_unconfigured_and_persisted_records(tmp_path: Path) -> None:
    with TestClient(create_app()) as unconfigured:
        unavailable = unconfigured.get("/sessions")
        storage = unconfigured.get("/storage/status")
    assert unavailable.status_code == 503
    assert storage.json()["status"] == "unavailable"
    assert storage.json()["reason"] == "not_configured"

    database = tmp_path / "records.sqlite3"
    with authenticated_client(configured_test_app(local_store_path=database)) as empty:
        assert empty.get("/sessions").json()["total"] == 0
        assert empty.get("findings").json()["items"] == []
        assert empty.get("reports").json()["items"] == []
        assert empty.get("dashboard/summary").json()["session_count"] == 0
        assert empty.get("storage/status").json()["status"] == "available"

    report = _run(database)
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        sessions = client.get("/sessions")
        reports = client.get("/reports")
        findings = client.get("/findings")
        summary = client.get("/dashboard/summary")
        detail = client.get(f"/reports/{reports.json()['items'][0]['report_id']}")
        finding = findings.json()["items"][0]
        finding_detail = client.get(f"/findings/{finding['finding_id']}")
        session_findings = client.get(f"/sessions/{sessions.json()['items'][0]['session_id']}/findings")

    assert sessions.status_code == reports.status_code == findings.status_code == summary.status_code == 200
    session = sessions.json()["items"][0]
    assert session["case_id"] == "CASE-PERSIST-01"
    assert session["is_synthetic"] is True and session["is_empirical"] is False
    assert session["execution_mode"] == "offline_fixture"
    assert reports.json()["total"] == 1
    assert detail.json()["payload"]["manifest"]["is_synthetic_simulation"] is True
    assert findings.json()["total"] == len(report.raw_trial_runs[0].result.findings)
    assert finding_detail.json() == finding
    assert session_findings.json()["total"] == 1
    assert summary.json()["finding_count"] == 1
    assert summary.json()["empirical_run_count"] == 0


def test_local_store_environment_configuration_is_opt_in_and_readable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("AEGISCORE_LOCAL_STORE_PATH", str(database))
    with TestClient(create_app()) as client:
        response = client.get("/storage/status")
    assert response.json()["status"] == "available"
    assert database.is_file()


def test_api_not_found_malformed_and_pagination_responses(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        missing_session = client.get("/sessions/session_00000000000000000000000000000000")
        missing_report = client.get("/reports/report_00000000000000000000000000000000")
        bad_id = client.get("/sessions/not-an-id")
        bad_offset = client.get("/reports?offset=-1")
    assert missing_session.status_code == missing_report.status_code == 404
    assert bad_id.status_code == bad_offset.status_code == 422

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE offline_sessions SET payload_json = '{' ")
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        malformed = client.get("/sessions")
    assert malformed.status_code == 503
    assert "payload" not in malformed.text


def test_api_maps_semantically_incomplete_report_payload_to_unavailable(
    tmp_path: Path,
) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    report_id = LocalRecordStore.open_existing(database).list_reports()[0][0][
        "report_id"
    ]
    incomplete_payload = (
        '{"manifest":{},"score_summary":{"total_cases":1,"metrics":{}},'
        '"trial_agreement":{},"raw_trial_runs":[],"aggregated_outcomes":[]}'
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE evaluation_reports SET payload_json = ?", (incomplete_payload,)
        )
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        response = client.get(f"/reports/{report_id}")

    assert response.status_code == 503
    assert "tp_count" not in response.text
    assert "payload" not in response.text


def test_api_reports_a_locked_store_as_unavailable_without_internal_details(
    tmp_path: Path,
) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        locker = sqlite3.connect(database, timeout=0)
        locker.execute("BEGIN EXCLUSIVE")
        try:
            response = client.get("/dashboard/summary")
        finally:
            locker.rollback()
            locker.close()

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]
    assert str(database) not in response.text


def test_persisted_read_routes_do_not_modify_database_bytes(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    _run(database)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    with authenticated_client(configured_test_app(local_store_path=database)) as client:
        session = client.get("/sessions").json()["items"][0]
        report = client.get("/reports").json()["items"][0]
        finding = client.get("/findings").json()["items"][0]
        assert client.get(f"/sessions/{session['session_id']}").status_code == 200
        assert client.get(f"/sessions/{session['session_id']}/findings").status_code == 200
        assert client.get(f"/findings/{finding['finding_id']}").status_code == 200
        assert client.get(f"/reports/{report['report_id']}").status_code == 200
        assert client.get("/dashboard/summary").status_code == 200
    after = hashlib.sha256(database.read_bytes()).hexdigest()
    assert after == before
