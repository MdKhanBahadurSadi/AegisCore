"""Comprehensive unit & integration tests for POST /assessments creation API and security hardening (Task 05.2.3)."""

from __future__ import annotations

import os
import socket
import sqlite3
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import DEFAULT_PERMISSIONS, AuthSettings
from aegiscore.api.schemas import AssessmentResponse
from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.local_persistence import LocalRecordStore, LocalStoreUnavailableError
from aegiscore.model_adapter import DeterministicModelAdapter, UnauthorizedLiveModelAdapter
from aegiscore.orchestration import OrchestrationStateMachine
from aegiscore.safety import PolicyEngine
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    configured_test_app,
    create_bound_test_assessment,
    get_test_auth_settings,
    make_test_authorization_verifier,
    make_test_target_registry,
)


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_valid_loopback_target_creates_assessment(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        response = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["assessment_id"].startswith("asm_")
    assert len(data["assessment_id"]) == 36
    assert data["target_url"] == "http://127.0.0.1:3000/"
    assert data["target_id"] == "test-loopback-target"
    assert data["canonical_endpoint"] == data["target_url"]
    assert data["authorization_ref"] == "test-only-explicit-authorization-fixture"
    assert data["authorization_provenance"]["signature_valid"] is True
    assert data["authorization_provenance"]["revoked"] is False
    assert data["authorization_provenance"]["issuer_id"] == "synthetic-test-issuer-only"
    assert data["status"] == "created"
    assert isinstance(data["created_at"], str) and data["created_at"]


def test_loopback_address_alone_does_not_authorize_assessment_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AEGISCORE_AUTHORIZED_TARGETS_FILE", raising=False)
    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(
        local_store_path=db_path,
        auth_settings=get_test_auth_settings(),
    )) as client:
        headers = _login(client)
        response = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Authorization verification is unavailable."}


def test_unregistered_hostnames_and_non_loopback_targets_are_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    valid_targets = (
        "http://localhost:8080",
        "https://localhost:8443/api",
        "http://10.0.0.5:8000",
        "http://172.16.0.10:3000/rest",
        "http://192.168.1.100:8080",
    )
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        for target in valid_targets:
            res = client.post(
                "/assessments",
                json={"target_url": target},
                headers=headers,
            )
            assert res.status_code == 400
            assert res.json() == {"detail": "Target endpoint is not authorized."}


def test_registered_loopback_still_rejects_unapproved_port_and_path(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        for target in (
            "http://127.0.0.1:3001/",
            "http://127.0.0.1:3000/admin",
            "http://127.0.0.1:3000/?mode=1",
        ):
            response = client.post(
                "/assessments",
                json={"target_url": target},
                headers=headers,
            )
            assert response.status_code == 400
            assert response.json() == {"detail": "Target endpoint is not authorized."}


def test_created_assessment_persisted_and_retrievable(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/rest/products"},
            headers=headers,
        )
        assert create_res.status_code == 201
        created = create_res.json()
        asm_id = created["assessment_id"]

        # Fetch by ID
        get_res = client.get(f"/assessments/{asm_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json() == created

        # List assessments
        list_res = client.get("/assessments", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] == 1
        assert list_data["items"][0] == created


def test_missing_or_invalid_request_payload_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        missing_url = client.post("/assessments", json={}, headers=headers)
        empty_url = client.post("/assessments", json={"target_url": ""}, headers=headers)
        whitespace_url = client.post("/assessments", json={"target_url": "   "}, headers=headers)

    assert missing_url.status_code == 422
    assert empty_url.status_code in (400, 422)
    assert whitespace_url.status_code in (400, 422)


def test_out_of_scope_and_malformed_targets_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def network_bomb(*_args, **_kwargs):
        raise AssertionError("Target URL validation performed unexpected network or DNS dispatch!")

    monkeypatch.setattr(socket, "getaddrinfo", network_bomb)
    monkeypatch.setattr(socket, "create_connection", network_bomb)
    monkeypatch.setattr(urllib.request, "urlopen", network_bomb)

    db_path = tmp_path / "records.sqlite3"
    invalid_targets = (
        ("ftp://127.0.0.1:3000", "scheme"),
        ("file:///etc/passwd", "scheme"),
        ("http://8.8.8.8:8080", "private_ip"),
        ("http://1.1.1.1", "private_ip"),
        ("http://user:pass@127.0.0.1:3000", "credentials"),
        ("http://example.com:8080", "external_domain"),
        ("http://127.0.0.1#fragment", "fragment"),
        ("http://127.0.0.1:abc", "nonnumeric_port"),
        ("http://127.0.0.1:0", "port_zero"),
        ("http://127.0.0.1:65536", "port_out_of_bounds"),
        ("http://[invalid-ipv6]:8080", "malformed_ipv6"),
        ("http://:8080", "empty_host"),
        ("http://invalid_name:8080/", "invalid_authority_syntax"),
        ("gopher://127.0.0.1:8080", "unsupported_scheme"),
    )
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        for target, _reason in invalid_targets:
            res = client.post(
                "/assessments",
                json={"target_url": target},
                headers=headers,
            )
            assert res.status_code == 400
            assert "detail" in res.json()
            # Never returns server error 500
            assert res.status_code != 500


def test_unauthenticated_request_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"})

    assert res.status_code == 401
    assert res.json() == {"detail": "Authentication required or credentials are invalid."}


def test_assessment_creation_authorization_permission_boundary(tmp_path: Path) -> None:
    read_only_settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        permissions=frozenset({"records:read"}),
    )
    create_settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        permissions=frozenset({"records:read", "assessments:create"}),
    )
    db_path = tmp_path / "records.sqlite3"

    # 1. Read-only user (records:read only) cannot create assessment
    with TestClient(create_app(local_store_path=db_path, auth_settings=read_only_settings)) as client:
        headers = _login(client)
        create_denied = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        assert create_denied.status_code == 403
        assert create_denied.json() == {"detail": "The authenticated account lacks this permission."}

        # Read-only user CAN call GET endpoints
        assert client.get("/assessments", headers=headers).status_code == 200
        assert client.get("/sessions", headers=headers).status_code == 200

    # 2. Account with assessments:create permission succeeds
    with TestClient(create_app(
        local_store_path=db_path,
        auth_settings=create_settings,
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=make_test_authorization_verifier(),
    )) as client:
        headers = _login(client)
        create_ok = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        assert create_ok.status_code == 201
        assert create_ok.json()["status"] == "created"


def test_toml_auth_config_file_permission_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml_path = tmp_path / "auth.toml"
    toml_path.write_text(
        f"""
[auth]
username = "{TEST_USERNAME}"
password_hash = "{get_test_auth_settings().password_hash}"
permissions = ["records:read"]
session_ttl_seconds = 1800
""",
        encoding="utf-8",
    )

    monkeypatch.delenv("AEGISCORE_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("AEGISCORE_AUTH_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("AEGISCORE_AUTH_PERMISSIONS", raising=False)
    monkeypatch.setenv("AEGISCORE_AUTH_CONFIG_FILE", str(toml_path))

    settings = AuthSettings.load()
    assert settings is not None
    assert settings.username == TEST_USERNAME
    assert settings.permissions == frozenset({"records:read"})
    assert "assessments:create" not in settings.permissions

    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(
        local_store_path=db_path,
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=make_test_authorization_verifier(),
    )) as client:
        headers = _login(client)
        create_denied = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        assert create_denied.status_code == 403
        assert create_denied.json() == {"detail": "The authenticated account lacks this permission."}

        assert client.get("/assessments", headers=headers).status_code == 200
        assert client.get("/sessions", headers=headers).status_code == 200


def test_toml_auth_config_file_omitted_permissions_applies_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml_path = tmp_path / "auth_no_permissions.toml"
    toml_path.write_text(
        f"""
[auth]
username = "{TEST_USERNAME}"
password_hash = "{get_test_auth_settings().password_hash}"
session_ttl_seconds = 1800
""",
        encoding="utf-8",
    )

    monkeypatch.delenv("AEGISCORE_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("AEGISCORE_AUTH_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("AEGISCORE_AUTH_PERMISSIONS", raising=False)
    monkeypatch.setenv("AEGISCORE_AUTH_CONFIG_FILE", str(toml_path))

    settings = AuthSettings.load()
    assert settings is not None
    assert settings.username == TEST_USERNAME
    assert settings.permissions == DEFAULT_PERMISSIONS
    assert "assessments:create" in settings.permissions

    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(
        local_store_path=db_path,
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=make_test_authorization_verifier(),
    )) as client:
        headers = _login(client)
        create_ok = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        assert create_ok.status_code == 201
        assert create_ok.json()["status"] == "created"
        assert client.get("/assessments", headers=headers).status_code == 200
        assert client.get("/sessions", headers=headers).status_code == 200


def test_unconfigured_auth_fails_closed_for_assessment_creation(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(local_store_path=db_path)) as client:
        res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"})

    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_unconfigured_or_failing_storage_returns_503(tmp_path: Path) -> None:
    with TestClient(configured_test_app()) as client:
        headers = _login(client)
        unconfigured = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )

    assert unconfigured.status_code == 503
    assert "unavailable" in unconfigured.json()["detail"].lower()


def test_deterministic_persistence_failure_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    # 1. Create a database with 1 valid existing assessment
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        first = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/first"},
            headers=headers,
        )
        assert first.status_code == 201
        first_data = first.json()

        # Record baseline assessment count and existing record
        list_before = client.get("/assessments", headers=headers).json()
        assert list_before["total"] == 1
        assert list_before["items"][0] == first_data

        # Inject persistence failure on second creation attempt
        def mock_failing_create(*_args, **_kwargs):
            raise LocalStoreUnavailableError(
                "Failed to write database at /secret/internal/user/path/records.sqlite3"
            )

        monkeypatch.setattr(LocalRecordStore, "create_assessment", mock_failing_create)

        # 2. Attempt second creation
        second = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/second"},
            headers=headers,
        )

        # 3. Verify HTTP 503 and zero path leakage
        assert second.status_code == 503
        assert second.json() == {"detail": "Local persistence store is unavailable or inconsistent."}
        assert "/secret/internal/user/path" not in second.text

        # 4. Remove monkeypatch and verify original assessment remains intact and count is still 1
        monkeypatch.undo()
        list_after = client.get("/assessments", headers=headers).json()
        assert list_after["total"] == 1
        assert list_after["items"][0] == first_data

        get_first = client.get(f"/assessments/{first_data['assessment_id']}", headers=headers)
        assert get_first.status_code == 200
        assert get_first.json() == first_data


def test_legacy_sqlite_schema_v1_compatibility_and_data_preservation(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_v1.sqlite3"

    # Create a legacy schema v1 SQLite database file containing 1 report and 1 session
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
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
        PRAGMA user_version = 1;
        """
    )
    conn.execute(
        """INSERT INTO evaluation_reports VALUES (
            'report_legacy001', '2026-10-27T10:00:00Z', 'ds_legacy', '1.0',
            'proposed_multi_agent', 'runner_legacy', 'completed', 1, 0, 0, 0,
            '{"report_id": "report_legacy001", "manifest": {"fixture_dataset_id": "ds_legacy", "fixture_dataset_version": "1.0"}, "score_summary": {"total_cases": 1, "metrics": {}}, "trial_agreement": {}, "raw_trial_runs": [], "aggregated_outcomes": []}'
        )"""
    )
    conn.execute(
        """INSERT INTO offline_sessions VALUES (
            'session_legacy001', 'report_legacy001', 'run_legacy001', 'runner_legacy', 'case_legacy001',
            0, '2026-10-27T10:00:00Z', '2026-10-27T10:01:00Z', 'completed', 'verified',
            'ds_legacy', '1.0', 'offline_fixture', 1, 0,
            '{"session_id": "session_legacy001", "result": {"findings": []}, "case_context": {}}'
        )"""
    )
    conn.commit()
    conn.close()

    def _schema_inventory(path: Path) -> list[tuple[str, str, str]]:
        c = sqlite3.connect(path)
        rows = c.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        c.close()
        return rows

    # 1. Read-only open_existing on legacy database succeeds without DDL execution
    read_only_store = LocalRecordStore.open_existing(db_path)
    sessions_before, session_total_before = read_only_store.list_sessions()
    reports_before, report_total_before = read_only_store.list_reports()
    assert session_total_before == 1
    assert report_total_before == 1
    report_before_data = reports_before[0]
    session_before_data = sessions_before[0]
    assert session_before_data["session_id"] == "session_legacy001"
    assert report_before_data["report_id"] == "report_legacy001"

    # Reading assessments from legacy store returns empty list / None without DDL errors
    assessments_before, asm_total_before = read_only_store.list_assessments()
    assert asm_total_before == 0
    assert assessments_before == []
    assert read_only_store.get_assessment("asm_00000000000000000000000000000000") is None

    # 2. Writable open (create_or_open) on legacy database initializes assessments table safely and idempotently
    writable_store1 = LocalRecordStore.create_or_open(db_path)
    created = create_bound_test_assessment(writable_store1)
    assert created["assessment_id"].startswith("asm_")
    assert created["target_url"] == "http://127.0.0.1:3000/"

    schema_after_init1 = _schema_inventory(db_path)
    assert any(name == "assessments" for _type, name, _sql in schema_after_init1)

    writable_store2 = LocalRecordStore.create_or_open(db_path)
    schema_after_init2 = _schema_inventory(db_path)
    assert schema_after_init2 == schema_after_init1  # Proves 100% idempotency (zero duplicate schema objects)

    # Retrievable via store
    fetched = writable_store2.get_assessment(created["assessment_id"])
    assert fetched == created

    # Existing reports and sessions remain 100% dict-for-dict identical and unchanged
    sessions_after, session_total_after = writable_store2.list_sessions()
    reports_after, report_total_after = writable_store2.list_reports()
    assert session_total_after == 1
    assert report_total_after == 1
    assert sessions_after[0] == session_before_data
    assert reports_after[0] == report_before_data

    # 3. Test API GET endpoints against the legacy database
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        api_sessions = client.get("/sessions", headers=headers)
        api_assessments = client.get("/assessments", headers=headers)
        assert api_sessions.status_code == 200
        assert api_sessions.json()["total"] == 1
        assert api_assessments.status_code == 200
        assert api_assessments.json()["total"] == 1
        assert api_assessments.json()["items"][0] == AssessmentResponse(**created).model_dump()


def test_assessment_creation_does_not_execute_scanner_orchestration_or_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def assertion_bomb(*_args, **_kwargs):
        raise AssertionError("Assessment creation attempted execution workflow!")

    monkeypatch.setattr(socket, "getaddrinfo", assertion_bomb)
    monkeypatch.setattr(socket, "create_connection", assertion_bomb)
    monkeypatch.setattr(urllib.request, "urlopen", assertion_bomb)
    monkeypatch.setattr(PolicyEngine, "authorize_operation", assertion_bomb)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", assertion_bomb)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", assertion_bomb)
    monkeypatch.setattr(OrchestrationStateMachine, "__init__", assertion_bomb)
    monkeypatch.setattr(DeterministicModelAdapter, "complete", assertion_bomb)
    monkeypatch.setattr(UnauthorizedLiveModelAdapter, "complete", assertion_bomb)

    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )

    assert res.status_code == 201
    assert res.json()["target_url"] == "http://127.0.0.1:3000/"
