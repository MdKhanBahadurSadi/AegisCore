"""Comprehensive unit & integration tests for MVP Assessment Execution Engine & Security Boundaries (Task 06.1.1.1)."""

from __future__ import annotations

import json
import ipaddress
import os
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthSettings
from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.execution import (
    AssessmentExecutionEngine,
    ConnectedPeerMismatchError,
    _PeerCheckedHTTPHandler,
    _PeerCheckedHTTPSHandler,
    _verify_connected_peer,
    _validate_execution_target_url,
)
from aegiscore.local_persistence import LocalRecordStore, LocalStoreConflictError, _canonical_json
from aegiscore.orchestration import ScopeViolationError
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    configured_test_app,
    create_bound_test_assessment,
    get_test_auth_settings,
    mark_mock_loopback_peer,
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


class _MockResponse:
    def __init__(self, code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.code = code
        self._code = code
        self.msg = "OK"
        self.headers = headers or {}

    def getcode(self) -> int:
        return self.code

    def info(self) -> dict[str, str]:
        return self.headers

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, *_args) -> None:
        pass


def test_ipv4_and_ipv6_numeric_loopback_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    def dns_bomb(*_args, **_kwargs):
        raise AssertionError("DNS resolution attempted on numeric loopback target!")

    monkeypatch.setattr(socket, "getaddrinfo", dns_bomb)

    valid_loopbacks = (
        "http://127.0.0.1:3000",
        "http://127.0.0.2:8080/path",
        "http://[::1]:8080/test",
    )
    for target in valid_loopbacks:
        _validate_execution_target_url(target)


def test_strict_execution_target_boundary_rejections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def dns_bomb(*_args, **_kwargs):
        raise AssertionError("DNS resolution attempted during execution target validation!")

    monkeypatch.setattr(socket, "getaddrinfo", dns_bomb)

    prohibited_targets = (
        ("http://8.8.8.8:8080", "public_ip"),
        ("http://10.0.0.1:8000", "rfc1918_private_ip"),
        ("http://192.168.1.1:8080", "rfc1918_private_ip"),
        ("http://localhost:8080", "localhost_hostname"),
        ("http://lab.local:8080", "dot_local_hostname"),
        ("http://service.internal:8080", "dot_internal_hostname"),
        ("http://example.com:8080", "arbitrary_hostname"),
    )
    for target, _reason in prohibited_targets:
        with pytest.raises(ScopeViolationError):
            _validate_execution_target_url(target)


def test_environment_proxy_bypass_http_and_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("http_proxy", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("https_proxy", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("ALL_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("all_proxy", "http://malicious-proxy.local:8080")

    def mock_http_open(self, req):
        assert req.host == "127.0.0.1:3000"
        mark_mock_loopback_peer(type("FakeOpener", (), {"handlers": (self,)})(), req)
        return _MockResponse(code=200)

    monkeypatch.setattr(_PeerCheckedHTTPHandler, "http_open", mock_http_open)

    engine = AssessmentExecutionEngine()
    res = engine.execute_connectivity_observation("http://127.0.0.1:3000")
    assert res["reachable"] is True
    assert res["http_status"] == 200


def test_https_proxy_environment_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("http_proxy", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("https_proxy", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("ALL_PROXY", "http://malicious-proxy.local:8080")
    monkeypatch.setenv("all_proxy", "http://malicious-proxy.local:8080")

    https_open_called = False

    def mock_https_open(self, req):
        nonlocal https_open_called
        https_open_called = True
        assert req.host == "127.0.0.1:8443"
        mark_mock_loopback_peer(type("FakeOpener", (), {"handlers": (self,)})(), req)
        return _MockResponse(code=200)

    monkeypatch.setattr(_PeerCheckedHTTPSHandler, "https_open", mock_https_open)

    engine = AssessmentExecutionEngine()
    res = engine.execute_connectivity_observation("https://127.0.0.1:8443")
    assert https_open_called is True
    assert res["reachable"] is True
    assert res["http_status"] == 200


def test_invalid_and_valid_state_transitions(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)

    # 1. Valid created -> pending
    asm1 = create_bound_test_assessment(store)
    asm1_id = asm1["assessment_id"]
    p1 = store.update_assessment_status(asm1_id, "pending")
    assert p1["status"] == "pending"

    # 2. Valid pending -> running (generates lease_token)
    r1 = store.update_assessment_status(asm1_id, "running")
    assert r1["status"] == "running"
    token1 = r1["lease_token"]

    # 3. Valid running -> completed with valid lease_token
    c1 = store.update_assessment_status(asm1_id, "completed", execution_result={"reachable": True}, lease_token=token1)
    assert c1["status"] == "completed"

    # 4. Valid created -> pending -> running -> failed with valid lease_token
    asm2 = create_bound_test_assessment(store)
    asm2_id = asm2["assessment_id"]
    store.update_assessment_status(asm2_id, "pending")
    r2 = store.update_assessment_status(asm2_id, "running")
    token2 = r2["lease_token"]
    f2 = store.update_assessment_status(asm2_id, "failed", execution_result={"reachable": False}, lease_token=token2)
    assert f2["status"] == "failed"

    # 5. Invalid transition rejections
    asm3 = create_bound_test_assessment(store)
    asm3_id = asm3["assessment_id"]

    # created -> completed / failed (invalid)
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "completed")
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "failed")

    # created -> running -> running / created / pending (invalid)
    r3 = store.update_assessment_status(asm3_id, "running")
    token3 = r3["lease_token"]
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "created", lease_token=token3)
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "pending", lease_token=token3)
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "running", lease_token=token3)

    # running -> completed -> running (invalid)
    # running -> completed -> running / completed (invalid)
    store.update_assessment_status(asm3_id, "completed", lease_token=token3)
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "running")
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm3_id, "completed")

    # failed -> running (invalid)
    with pytest.raises(LocalStoreConflictError):
        store.update_assessment_status(asm2_id, "running")


def test_concurrent_duplicate_execution_prevention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"
    head_call_count = 0
    head_lock = threading.Lock()
    exec_started_event = threading.Event()
    release_exec_event = threading.Event()

    def mock_open(opener, req, *_args, **_kwargs):
        nonlocal head_call_count
        mark_mock_loopback_peer(opener, req)
        with head_lock:
            head_call_count += 1
        exec_started_event.set()
        assert release_exec_event.wait(timeout=10.0) is True
        return _MockResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        first_res_container = []

        def worker():
            res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
            first_res_container.append(res)

        t1 = threading.Thread(target=worker)
        t1.start()

        # Wait until first thread enters mock_open (first assessment is confirmed 'running')
        assert exec_started_event.wait(timeout=10.0) is True

        # Submit second request while first assessment is confirmed 'running'
        second_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)

        # Assert second request is rejected with 409 Conflict
        assert second_res.status_code == 409
        assert "already" in second_res.json()["detail"].lower()

        # Release first execution thread
        release_exec_event.set()
        t1.join(timeout=10.0)

        # Assert first request returns 200 OK
        assert len(first_res_container) == 1
        assert first_res_container[0].status_code == 200
        assert first_res_container[0].json()["status"] == "completed"

        # Assert exactly 1 HEAD request occurred and 1 persisted result exists with completed execution details
        assert head_call_count == 1
        listed = client.get("/assessments", headers=headers).json()
        assert listed["total"] == 1
        record = listed["items"][0]
        assert record["status"] == "completed"
        assert record["execution_result"] is not None
        assert record["execution_result"]["reachable"] is True
        assert record["execution_result"]["http_status"] == 200
        assert record["execution_result"]["method"] == "HEAD"
        assert "200" in record["execution_result"]["outcome"]


def test_unexpected_execution_failure_safely_persists_failed_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_failing_observation(*_args, **_kwargs):
        raise RuntimeError("Simulated internal transport exception with /secret/path/info")

    monkeypatch.setattr(
        AssessmentExecutionEngine,
        "execute_connectivity_observation",
        mock_failing_observation,
    )

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 503

        # Assessment must NOT remain stuck in 'running'
        get_res = client.get(f"/assessments/{asm_id}", headers=headers)
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["status"] == "failed"
        assert "/secret/path" not in exec_res.text
        assert "internal execution error" in data["execution_result"]["outcome"].lower()
        stored = LocalRecordStore.open_existing(db_path).get_assessment(asm_id)
        assert stored["status"] == "failed"
        assert "lease_token" not in stored
        assert "lease_expires_at" not in stored


def test_execution_exception_cannot_fail_assessment_after_lease_ownership_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_stale_worker_failure(*_args, **_kwargs):
        store = LocalRecordStore.create_or_open(db_path)
        records, total = store.list_assessments()
        assert total == 1
        record = records[0]
        record["lease_token"] = "lease_reassigned_to_another_worker"
        with store._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE assessments SET payload_json = ? WHERE assessment_id = ?",
                (_canonical_json(record), record["assessment_id"]),
            )
            connection.commit()
        raise RuntimeError("secret transport details from stale worker")

    monkeypatch.setattr(
        AssessmentExecutionEngine,
        "execute_connectivity_observation",
        mock_stale_worker_failure,
    )

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 503
        assert "secret transport details" not in exec_res.text

    stored = LocalRecordStore.open_existing(db_path).get_assessment(asm_id)
    assert stored["status"] == "running"
    assert stored["lease_token"] == "lease_reassigned_to_another_worker"
    assert "execution_result" not in stored


def test_successful_local_loopback_head_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)
    boundary_dispatches: list[str] = []
    original_dispatch = GuardedExecutionBoundary.dispatch

    def guarded_dispatch(self, authorization, intent):
        boundary_dispatches.append(intent.method)
        return original_dispatch(self, authorization, intent)

    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", guarded_dispatch)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(
            f"/assessments/{asm_id}/execute",
            headers=headers,
        )
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["assessment_id"] == asm_id
        assert data["status"] == "completed"
        assert data["updated_at"] is not None

        result = data["execution_result"]
        assert result["reachable"] is True
        assert result["http_status"] == 200
        assert result["method"] == "HEAD"
        assert result["redirect_detected"] is False
        assert result["connected_peer"] == "127.0.0.1"
        assert result["authorization_verification"]["signature_valid"] is True
        assert result["authorization_verification"]["revoked"] is False
        assert boundary_dispatches == ["HEAD"]


@pytest.mark.parametrize(
    "binding_field",
    [
        "target_id", "unknown_target_id", "canonical_endpoint", "target_url",
        "authorization_ref", "authorization_provenance",
    ],
)
def test_execution_rejects_missing_or_changed_authorized_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, binding_field: str
) -> None:
    db_path = tmp_path / "records.sqlite3"
    transport_calls: list[str] = []

    def mock_open(_opener, req, *_args, **_kwargs):
        transport_calls.append(req.full_url)
        return _MockResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        created = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        ).json()
        asm_id = created["assessment_id"]

        store = LocalRecordStore.create_or_open(db_path)
        with store._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM assessments WHERE assessment_id = ?", (asm_id,)
            ).fetchone()
            payload = json.loads(row["payload_json"])
            if binding_field == "unknown_target_id":
                payload["target_id"] = "unauthorized-target"
            elif binding_field == "canonical_endpoint":
                payload[binding_field] = "http://127.0.0.1:3000/other"
            elif binding_field == "target_url":
                payload[binding_field] = "http://127.0.0.1:3000/other"
            elif binding_field == "authorization_ref":
                payload[binding_field] = "revoked-authorization"
            else:
                payload.pop(binding_field)
            connection.execute(
                "UPDATE assessments SET payload_json = ? WHERE assessment_id = ?",
                (json.dumps(payload, sort_keys=True, separators=(",", ":")), asm_id),
            )

        response = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert response.status_code == 409
        assert response.json() == {
            "detail": "Assessment target authorization is missing or no longer valid."
        }

    persisted = LocalRecordStore.open_existing(db_path).get_assessment(asm_id)
    assert persisted["status"] == "created"
    assert transport_calls == []


def test_target_binding_is_rechecked_after_lease_claim_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"
    network_calls: list[str] = []
    original_update = LocalRecordStore.update_assessment_status

    def change_binding_after_running(self, assessment_id, new_status, *args, **kwargs):
        record = original_update(self, assessment_id, new_status, *args, **kwargs)
        if new_status == "running":
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT payload_json FROM assessments WHERE assessment_id = ?", (assessment_id,)
                ).fetchone()
                payload = json.loads(row["payload_json"])
                payload["canonical_endpoint"] = "http://127.0.0.1:3000/changed"
                connection.execute(
                    "UPDATE assessments SET payload_json = ? WHERE assessment_id = ?",
                    (json.dumps(payload, sort_keys=True, separators=(",", ":")), assessment_id),
                )
        return record

    def forbidden_network(opener, req, *_args, **_kwargs):
        network_calls.append(req.full_url)
        raise AssertionError("A changed authorization binding reached the transport")

    monkeypatch.setattr(LocalRecordStore, "update_assessment_status", change_binding_after_running)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden_network)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        created = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        ).json()
        response = client.post(f"/assessments/{created['assessment_id']}/execute", headers=headers)
        assert response.status_code == 503

    persisted = LocalRecordStore.open_existing(db_path).get_assessment(created["assessment_id"])
    assert persisted["status"] == "failed"
    assert persisted["execution_result"]["reachable"] is False
    assert network_calls == []


def test_connected_peer_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    class WrongPeerSocket:
        def __init__(self) -> None:
            self.sent: list[bytes] = []

        def getpeername(self):
            return ("127.0.0.2", 3000)

        def close(self) -> None:
            pass

        def sendall(self, data: bytes) -> None:
            self.sent.append(data)

    mismatched_socket = WrongPeerSocket()
    with pytest.raises(ConnectedPeerMismatchError, match="does not match"):
        _verify_connected_peer(mismatched_socket, ipaddress.ip_address("127.0.0.1"), 3000)

    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: mismatched_socket)
    result = AssessmentExecutionEngine().execute_connectivity_observation("http://127.0.0.1:3000/")
    assert result["reachable"] is False
    assert result["connected_peer"] is None
    assert mismatched_socket.sent == []

    class WrongPortSocket(WrongPeerSocket):
        def getpeername(self):
            return ("127.0.0.1", 3001)

    with pytest.raises(ConnectedPeerMismatchError, match="authorized target endpoint"):
        _verify_connected_peer(WrongPortSocket(), ipaddress.ip_address("127.0.0.1"), 3000)


def test_nonexistent_assessment_id_returns_404(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        fake_id = "asm_00000000000000000000000000000000"
        res = client.post(f"/assessments/{fake_id}/execute", headers=headers)
        assert res.status_code == 404
        assert res.json() == {"detail": "Target assessment was not found."}


def test_unauthenticated_request_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        fake_id = "asm_00000000000000000000000000000000"
        res = client.post(f"/assessments/{fake_id}/execute")
        assert res.status_code == 401


def test_missing_assessments_execute_permission_returns_403(tmp_path: Path) -> None:
    restricted_settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        permissions=frozenset({"records:read", "assessments:create"}),
    )
    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(local_store_path=db_path, auth_settings=restricted_settings)) as client:
        headers = _login(client)
        res = client.post(
            "/assessments/asm_00000000000000000000000000000000/execute",
            headers=headers,
        )
        assert res.status_code == 403


def test_explicit_read_only_toml_permission_config_returns_403(
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

    db_path = tmp_path / "records.sqlite3"
    with TestClient(create_app(local_store_path=db_path)) as client:
        headers = _login(client)
        res = client.post(
            "/assessments/asm_00000000000000000000000000000000/execute",
            headers=headers,
        )
        assert res.status_code == 403


def test_redirect_rejection_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:3000",
            code=302,
            msg="Found",
            hdrs={"Location": "http://127.0.0.1:4000/login"},
            fp=None,
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["status"] == "completed"

        result = data["execution_result"]
        assert result["reachable"] is True
        assert result["http_status"] == 302
        assert result["redirect_detected"] is True


def test_connection_timeout_handled_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(_opener, _req, *_args, **_kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["status"] == "failed"

        result = data["execution_result"]
        assert result["reachable"] is False


def test_unsupported_head_response_handled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:3000",
            code=405,
            msg="Method Not Allowed",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        asm_id = create_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["status"] == "completed"
        assert data["execution_result"]["http_status"] == 405


def test_persistence_and_application_restart_retrieval(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "records.sqlite3"
    requests_seen: list[tuple[str, str]] = []

    class LocalLabHandler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            requests_seen.append(("HEAD", self.path))
            self.send_response(200)
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()

        def do_GET(self) -> None:
            requests_seen.append(("GET", self.path))
            self.send_error(405)

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalLabHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    target_url = f"http://127.0.0.1:{server.server_port}/"

    try:
        # 1. Run app instance, create & execute against a real loopback-only HTTP fixture.
        target_registry = make_test_target_registry(target_url)
        with TestClient(configured_test_app(
            local_store_path=db_path,
            authorized_target_registry=target_registry,
        )) as client1:
            headers = _login(client1)
            create_res = client1.post(
                "/assessments",
                json={"target_url": target_url},
                headers=headers,
            )
            assert create_res.status_code == 201
            asm_id = create_res.json()["assessment_id"]

            exec_res = client1.post(f"/assessments/{asm_id}/execute", headers=headers)
            assert exec_res.status_code == 200
            completed_data = exec_res.json()

        # 2. Simulate application restart with a fresh app and authenticate again.
        with TestClient(configured_test_app(
            local_store_path=db_path,
            authorized_target_registry=target_registry,
        )) as client2:
            headers2 = _login(client2)
            get_res = client2.get(f"/assessments/{asm_id}", headers=headers2)
            assert get_res.status_code == 200
            restarted_data = get_res.json()
            assert restarted_data == completed_data
            assert restarted_data["status"] == "completed"

            evidence_res = client2.get(f"/assessments/{asm_id}/evidence", headers=headers2)
            findings_res = client2.get(f"/assessments/{asm_id}/findings", headers=headers2)
            assert evidence_res.status_code == 200
            assert findings_res.status_code == 200

            evidence_items = evidence_res.json()["items"]
            finding_items = findings_res.json()["items"]
            assert evidence_res.json()["total"] == 1
            assert len(evidence_items) == 1
            persisted_evidence_id = evidence_items[0]["evidence_id"]
            assert evidence_items[0]["assessment_id"] == asm_id
            assert evidence_items[0]["http_method"] == "HEAD"
            assert evidence_items[0]["normalized_headers"]["content-security-policy"] == (
                "default-src 'self'; frame-ancestors 'none'"
            )
            assert findings_res.json()["total"] == len(finding_items) > 0
            assert all(
                persisted_evidence_id in finding["evidence_ids"]
                for finding in finding_items
            )

        assert requests_seen == [("HEAD", "/")]
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        assert not server_thread.is_alive()


def test_no_response_body_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = AssessmentExecutionEngine()

    class _BodyCheckResponse(_MockResponse):
        def read(self, *_args, **_kwargs):
            raise AssertionError("Execution engine attempted to read HTTP response body!")

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _BodyCheckResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    result = engine.execute_connectivity_observation("http://127.0.0.1:3000")
    assert result["reachable"] is True


def test_no_unintended_network_access_across_api_and_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def network_bomb(*_args, **_kwargs):
        raise AssertionError("Unexpected network or DNS call performed!")

    monkeypatch.setattr(socket, "getaddrinfo", network_bomb)
    monkeypatch.setattr(socket, "create_connection", network_bomb)

    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        # Static assessment creation does not issue network calls
        create_res = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=headers,
        )
        assert create_res.status_code == 201

        # Unregistered hostnames are rejected before an assessment can be persisted.
        create_hostname_res = client.post(
            "/assessments",
            json={"target_url": "http://localhost:8080"},
            headers=headers,
        )
        assert create_hostname_res.status_code == 400


def test_timeout_configuration_validation() -> None:
    with pytest.raises(ValueError):
        AssessmentExecutionEngine(timeout_seconds=0.0)
    with pytest.raises(ValueError):
        AssessmentExecutionEngine(timeout_seconds=-5.0)
    with pytest.raises(ValueError):
        AssessmentExecutionEngine(timeout_seconds=60.0)
    with pytest.raises(ValueError):
        AssessmentExecutionEngine(timeout_seconds="invalid")  # type: ignore


def test_sanitized_error_outcomes_on_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = AssessmentExecutionEngine()

    def mock_url_error(*_args, **_kwargs):
        raise urllib.error.URLError(ConnectionRefusedError(10061, "Connection refused"))

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_url_error)

    res = engine.execute_connectivity_observation("http://127.0.0.1:3000")
    assert res["reachable"] is False
    assert res["outcome"] == "Target unreachable: Connection refused"
    assert "/secret" not in res["outcome"]
