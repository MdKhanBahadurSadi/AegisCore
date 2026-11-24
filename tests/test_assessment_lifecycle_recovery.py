"""Comprehensive unit & integration tests for Lease-Based Assessment Lifecycle Recovery & Safety (Task 06.3.2)."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aegiscore.execution import (
    DEFAULT_EXECUTION_LEASE_SECONDS,
    DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    EXECUTION_LEASE_SAFETY_MARGIN_SECONDS,
)
from aegiscore.local_persistence import (
    LocalRecordStore,
    LocalStoreConflictError,
    LocalStoreUnavailableError,
    _canonical_json,
    _validate_positive_finite_number,
)
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    configured_test_app,
    create_bound_test_assessment,
)


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _insert_running_assessment(
    db_path: Path,
    assessment_id: str,
    target_url: str = "http://127.0.0.1:3000/",
    updated_at_dt: datetime | None = None,
    lease_expires_at_dt: datetime | None = None,
    lease_token: str | None = None,
    status: str = "running",
    execution_result: dict[str, Any] | None = None,
) -> tuple[LocalRecordStore, str]:
    store = LocalRecordStore.create_or_open(db_path)
    updated_iso = (updated_at_dt or datetime.now(timezone.utc)).isoformat()
    token = lease_token or (f"lease_{os.urandom(16).hex()}" if status == "running" else None)

    record = {
        "assessment_id": assessment_id,
        "target_url": target_url,
        "target_id": "test-loopback-target",
        "canonical_endpoint": target_url,
        "authorization_ref": "test-only-explicit-authorization-fixture",
        "registration_version": "test-registration-v1",
        "status": status,
        "created_at": updated_iso,
        "updated_at": updated_iso,
    }
    if token:
        record["lease_token"] = token
    if lease_expires_at_dt:
        record["lease_expires_at"] = lease_expires_at_dt.isoformat()
    if execution_result:
        record["execution_result"] = execution_result

    payload_json = _canonical_json(record)
    with store._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        store._ensure_pipeline_tables(conn)
        conn.execute(
            "INSERT INTO assessments (assessment_id, target_url, status, created_at, payload_json) VALUES (?, ?, ?, ?, ?)",
            (assessment_id, target_url, status, updated_iso, payload_json),
        )
        conn.commit()

    return store, token or ""


def _set_lease_expiry(store: LocalRecordStore, assessment_id: str, expiry: str | None) -> None:
    """Set or remove the persisted expiry to exercise malformed-record paths."""
    with store._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
        ).fetchone()
        assert row is not None
        record = json.loads(row["payload_json"])
        if expiry is None:
            record.pop("lease_expires_at", None)
        else:
            record["lease_expires_at"] = expiry
        conn.execute(
            "UPDATE assessments SET payload_json = ? WHERE assessment_id = ?",
            (_canonical_json(record), assessment_id),
        )
        conn.commit()


def _submit_terminal_result(
    store: LocalRecordStore,
    assessment_id: str,
    lease_token: str,
    method: str,
) -> dict[str, Any]:
    if method == "status":
        return store.update_assessment_status(
            assessment_id,
            "completed",
            execution_result={"reachable": True},
            lease_token=lease_token,
        )
    return store.save_pipeline_result(
        assessment_id=assessment_id,
        evidence={"evidence_id": "evi_terminal_test", "collection_status": "observed"},
        findings=[],
        final_status="completed",
        execution_result={"reachable": True},
        lease_token=lease_token,
    )


def test_missing_lease_token_cannot_complete_running_assessment(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000001"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=300)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)

    # Missing lease token raises LocalStoreConflictError
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm_id, "completed", lease_token=None)

    with pytest.raises(LocalStoreConflictError):
        store.save_pipeline_result(
            assessment_id=asm_id,
            evidence={"evidence_id": "evi_001", "collection_status": "observed"},
            findings=[],
            final_status="completed",
            execution_result={"reachable": True},
            lease_token=None,
        )


def test_pending_failure_cannot_bypass_lease_ownership(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    assessment = create_bound_test_assessment(store)
    asm_id = assessment["assessment_id"]
    store.update_assessment_status(asm_id, "pending")

    with pytest.raises(LocalStoreConflictError, match="lease token"):
        store.update_assessment_status(asm_id, "failed")

    with pytest.raises(LocalStoreConflictError, match="lease token"):
        store.save_pipeline_result(
            assessment_id=asm_id,
            evidence={"evidence_id": "evi_pending_failure", "collection_status": "failed"},
            findings=[],
            final_status="failed",
            execution_result={"reachable": False},
        )

    persisted = store.get_assessment(asm_id)
    assert persisted["status"] == "pending"
    assert "execution_result" not in persisted
    assert not store.list_evidence(asm_id)


@pytest.mark.parametrize("terminal_method", ["status", "pipeline"])
def test_wrong_lease_token_cannot_complete_assessment(tmp_path: Path, terminal_method: str) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000002"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=300)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)

    with pytest.raises(LocalStoreConflictError):
        _submit_terminal_result(store, asm_id, "wrong_token_123", terminal_method)


@pytest.mark.parametrize("terminal_method", ["status", "pipeline"])
@pytest.mark.parametrize(
    ("expiry", "case_id"),
    [
        (None, "missing"),
        ("not-an-iso-timestamp", "malformed"),
        ("2999-01-01T00:00:00", "timezone-naive"),
        ("2999-01-01T00:00:00+25:00", "timezone-invalid"),
    ],
    ids=["missing", "malformed", "timezone-naive", "timezone-invalid"],
)
def test_terminal_persistence_rejects_missing_or_unverifiable_expiry(
    tmp_path: Path, terminal_method: str, expiry: str | None, case_id: str
) -> None:
    db_path = tmp_path / f"{terminal_method}-{case_id}.sqlite3"
    asm_id = "asm_00000000000000000000000000000015"
    store, token = _insert_running_assessment(
        db_path, asm_id, lease_expires_at_dt=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    _set_lease_expiry(store, asm_id, expiry)

    with pytest.raises(LocalStoreConflictError, match="missing or unverifiable"):
        _submit_terminal_result(store, asm_id, token, terminal_method)

    persisted = store.get_assessment(asm_id)
    assert persisted["status"] == "running"
    assert persisted["lease_token"] == token
    assert not store.list_evidence(asm_id)


@pytest.mark.parametrize("terminal_method", ["status", "pipeline"])
def test_valid_future_lease_authorizes_terminal_transition(
    tmp_path: Path, terminal_method: str
) -> None:
    db_path = tmp_path / f"valid-{terminal_method}.sqlite3"
    asm_id = "asm_00000000000000000000000000000016"
    store, token = _insert_running_assessment(
        db_path, asm_id, lease_expires_at_dt=datetime.now(timezone.utc) + timedelta(minutes=5)
    )

    completed = _submit_terminal_result(store, asm_id, token, terminal_method)

    assert completed["status"] == "completed"
    assert completed["execution_result"] == {"reachable": True}
    assert "lease_token" not in completed
    assert "lease_expires_at" not in completed


@pytest.mark.parametrize("terminal_method", ["status", "pipeline"])
def test_expired_lease_cannot_complete_even_before_recovery(
    tmp_path: Path, terminal_method: str
) -> None:
    db_path = tmp_path / f"expired-{terminal_method}.sqlite3"
    asm_id = "asm_00000000000000000000000000000003"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)

    # The token is correct, but expiration blocks either terminal persistence path.
    with pytest.raises(LocalStoreConflictError, match="expired"):
        _submit_terminal_result(store, asm_id, token, terminal_method)
    assert store.get_assessment(asm_id)["status"] == "running"
    assert not store.list_evidence(asm_id)


@pytest.mark.parametrize(
    ("expiry", "case_id"),
    [
        (None, "missing"),
        ("not-an-iso-timestamp", "malformed"),
        ("2999-01-01T00:00:00", "timezone-naive"),
        ("2999-01-01T00:00:00+25:00", "timezone-invalid"),
    ],
    ids=["missing", "malformed", "timezone-naive", "timezone-invalid"],
)
def test_renewal_rejects_missing_or_unverifiable_expiry(
    tmp_path: Path, expiry: str | None, case_id: str
) -> None:
    db_path = tmp_path / f"renew-{case_id}.sqlite3"
    asm_id = "asm_00000000000000000000000000000018"
    store, token = _insert_running_assessment(
        db_path, asm_id, lease_expires_at_dt=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    _set_lease_expiry(store, asm_id, expiry)

    with pytest.raises(LocalStoreConflictError, match="missing or unverifiable"):
        store.renew_execution_lease(asm_id, lease_token=token, extension_seconds=30.0)

    persisted = store.get_assessment(asm_id)
    assert persisted["status"] == "running"
    assert persisted["lease_token"] == token


def test_expired_lease_cannot_be_renewed(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000004"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)

    with pytest.raises(LocalStoreConflictError):
        store.renew_execution_lease(asm_id, lease_token=token, extension_seconds=30.0)


def test_valid_lease_can_be_renewed_before_expiry(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000005"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=10)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)

    renewed = store.renew_execution_lease(asm_id, lease_token=token)
    assert renewed["status"] == "running"
    exp_dt = datetime.fromisoformat(renewed["lease_expires_at"])
    assert (exp_dt - datetime.now(timezone.utc)).total_seconds() > 20.0


def test_execution_failure_transition_requires_valid_lease_token(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000006"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=300)
    store, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)

    # Missing lease token raises LocalStoreConflictError for failure transition
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm_id, "failed", lease_token=None)

    # Valid lease token succeeds
    failed = store.update_assessment_status(asm_id, "failed", lease_token=token)
    assert failed["status"] == "failed"


def test_assessment_with_no_lease_not_recovered_using_old_updated_at(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000007"
    old_time = datetime.now(timezone.utc) - timedelta(seconds=600)
    # Assessment without lease_expires_at
    store, _ = _insert_running_assessment(db_path, asm_id, updated_at_dt=old_time, lease_expires_at_dt=None)

    # Recovery skips records without valid lease_expires_at
    recovered = store.recover_stale_assessments()
    assert recovered == []
    assert store.get_assessment(asm_id)["status"] == "running"


@pytest.mark.parametrize(
    ("expiry", "case_id"),
    [
        ("not-an-iso-timestamp", "malformed"),
        ("2999-01-01T00:00:00", "timezone-naive"),
        ("2999-01-01T00:00:00+25:00", "timezone-invalid"),
    ],
    ids=["malformed", "timezone-naive", "timezone-invalid"],
)
def test_recovery_skips_unverifiable_expiry(
    tmp_path: Path, expiry: str, case_id: str
) -> None:
    db_path = tmp_path / f"recovery-{case_id}.sqlite3"
    asm_id = "asm_00000000000000000000000000000020"
    store, token = _insert_running_assessment(
        db_path,
        asm_id,
        updated_at_dt=datetime.now(timezone.utc) - timedelta(minutes=10),
        lease_expires_at_dt=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    _set_lease_expiry(store, asm_id, expiry)

    assert store.recover_stale_assessments() == []
    persisted = store.get_assessment(asm_id)
    assert persisted["status"] == "running"
    assert persisted["lease_token"] == token
    assert "recovery_metadata" not in persisted


def test_recovery_metadata_stored_under_recovery_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000008"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    store, _ = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)

    recovered = store.recover_stale_assessments()
    assert len(recovered) == 1
    rec_item = recovered[0]

    assert rec_item["status"] == "failed"
    assert rec_item["recovery_metadata"]["recovered"] is True
    assert "reason" in rec_item["recovery_metadata"]
    # Does NOT store synthetic facts in execution_result
    assert "execution_result" not in rec_item


def test_previously_committed_execution_result_remains_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000009"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    prev_result = {"reachable": True, "http_status": 200, "outcome": "Valid observation"}
    store, _ = _insert_running_assessment(
        db_path, asm_id, lease_expires_at_dt=past_lease, execution_result=prev_result
    )

    recovered = store.recover_stale_assessments()
    assert len(recovered) == 1
    fetched = store.get_assessment(asm_id)

    # Previously committed execution_result remains 100% unchanged
    assert fetched["execution_result"] == prev_result
    assert fetched["recovery_metadata"]["recovered"] is True


def test_two_stale_assessments_rollback_on_trigger_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm1_id = "asm_00000000000000000000000000000010"
    asm2_id = "asm_00000000000000000000000000000011"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)

    _insert_running_assessment(db_path, asm1_id, lease_expires_at_dt=past_lease)
    _insert_running_assessment(db_path, asm2_id, lease_expires_at_dt=past_lease)

    store = LocalRecordStore.create_or_open(db_path)

    # Install trigger that fails on second assessment update
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"""
        CREATE TRIGGER fail_second_recovery
        BEFORE UPDATE ON assessments
        WHEN OLD.assessment_id = '{asm2_id}'
        BEGIN
            SELECT RAISE(FAIL, 'Simulated SQLite failure on second assessment recovery');
        END;
        """
    )
    conn.commit()
    conn.close()

    with pytest.raises(LocalStoreUnavailableError):
        store.recover_stale_assessments()

    # Entire transaction rolled back: both assessments remain in 'running' status
    assert store.get_assessment(asm1_id)["status"] == "running"
    assert store.get_assessment(asm2_id)["status"] == "running"


def test_recovery_preserves_all_previous_evidence_and_findings(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000012"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    store, _ = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)

    # Save evidence and finding
    ev = store.save_evidence(asm_id, {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "evidence_type": "http_security_headers",
        "source": "passive_head_observation",
        "observed_at": "2026-11-23T18:00:00Z",
    })
    store.save_findings(asm_id, [{
        "finding_id": "fnd_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "rule_id": "WEB-HEADER-001",
        "title": "CSP not observed",
        "description": "Test description",
        "classification": "configuration_observation",
        "severity": "info",
        "confidence": "low",
        "status": "detected",
        "evidence_ids": ("evi_00000000000000000000000000000001",),
        "remediation": "Test remediation",
        "created_at": "2026-11-23T18:00:01Z",
    }])

    store.recover_stale_assessments()

    assert len(store.list_evidence(asm_id)) == 1
    assert len(store.list_findings(asm_id)) == 1
    assert store.get_assessment(asm_id)["status"] == "failed"


def test_recovery_and_renewal_concurrent_safety(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000013"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    store1, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)
    store2 = LocalRecordStore.create_or_open(db_path)

    barrier = threading.Barrier(2)
    results = [None, None]

    def worker_recovery():
        barrier.wait()
        results[0] = store1.recover_stale_assessments()

    def worker_renewal():
        barrier.wait()
        try:
            results[1] = store2.renew_execution_lease(asm_id, lease_token=token, extension_seconds=30.0)
        except LocalStoreConflictError as exc:
            results[1] = exc

    t1 = threading.Thread(target=worker_recovery)
    t2 = threading.Thread(target=worker_renewal)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert isinstance(results[0], list)
    assert len(results[0]) == 1
    assert isinstance(results[1], LocalStoreConflictError)
    persisted = store1.get_assessment(asm_id)
    assert persisted["status"] == "failed"
    assert persisted["recovery_metadata"]["recovered"] is True
    assert "lease_token" not in persisted
    assert "lease_expires_at" not in persisted
    assert "execution_result" not in persisted


def test_concurrent_recovery_and_renewal_preserve_future_lease(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000019"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=10)
    store1, token = _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)
    store2 = LocalRecordStore.create_or_open(db_path)

    barrier = threading.Barrier(2)
    results: list[Any] = [None, None]

    def worker_recovery() -> None:
        barrier.wait()
        results[0] = store1.recover_stale_assessments()

    def worker_renewal() -> None:
        barrier.wait()
        try:
            results[1] = store2.renew_execution_lease(asm_id, lease_token=token, extension_seconds=30.0)
        except LocalStoreConflictError as exc:
            results[1] = exc

    threads = [threading.Thread(target=worker_recovery), threading.Thread(target=worker_renewal)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    assert results[0] == []
    assert isinstance(results[1], dict)
    persisted = store1.get_assessment(asm_id)
    assert persisted["status"] == "running"
    assert persisted["lease_token"] == token
    assert datetime.fromisoformat(persisted["lease_expires_at"]) > datetime.now(timezone.utc)
    assert "recovery_metadata" not in persisted
    assert "execution_result" not in persisted


def test_startup_recovery_protects_active_leases(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000014"
    future_lease = datetime.now(timezone.utc) + timedelta(seconds=300)
    _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=future_lease)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        res = client.get(f"/assessments/{asm_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "running"


def test_process_restart_recovers_expired_assessment_lease(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    asm_id = "asm_00000000000000000000000000000021"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=10)
    _insert_running_assessment(db_path, asm_id, lease_expires_at_dt=past_lease)

    # Constructing a fresh app instance runs the same recovery path as process startup.
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        res = client.get(f"/assessments/{asm_id}", headers=headers)

    assert res.status_code == 200
    assert res.json()["status"] == "failed"
    persisted = LocalRecordStore.open_existing(db_path).get_assessment(asm_id)
    assert persisted["status"] == "failed"
    assert persisted["recovery_metadata"]["recovered"] is True
    assert "lease_token" not in persisted
    assert "lease_expires_at" not in persisted
    assert "execution_result" not in persisted


def test_invalid_timestamps_and_non_finite_config_rejection(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    asm = create_bound_test_assessment(store)
    asm_id = asm["assessment_id"]

    # Non-finite and negative configs raise ValueError
    with pytest.raises(ValueError):
        _validate_positive_finite_number(0.0, "test")
    with pytest.raises(ValueError):
        _validate_positive_finite_number(-5.0, "test")
    with pytest.raises(ValueError):
        _validate_positive_finite_number(float("nan"), "test")
    with pytest.raises(ValueError):
        _validate_positive_finite_number(float("inf"), "test")

    with pytest.raises(ValueError):
        store.update_assessment_status(asm_id, "running", lease_duration_seconds=0.0)
    with pytest.raises(ValueError):
        store.renew_execution_lease(asm_id, "lease_token", extension_seconds=float("nan"))

    assert DEFAULT_EXECUTION_TIMEOUT_SECONDS == 5.0
    assert EXECUTION_LEASE_SAFETY_MARGIN_SECONDS == 25.0
    assert DEFAULT_EXECUTION_LEASE_SECONDS == (
        DEFAULT_EXECUTION_TIMEOUT_SECONDS + EXECUTION_LEASE_SAFETY_MARGIN_SECONDS
    )
    running = store.update_assessment_status(asm_id, "running")
    expiry = datetime.fromisoformat(running["lease_expires_at"])
    updated = datetime.fromisoformat(running["updated_at"])
    assert 29.0 < (expiry - updated).total_seconds() <= DEFAULT_EXECUTION_LEASE_SECONDS
