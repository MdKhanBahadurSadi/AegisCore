"""Comprehensive unit & integration tests for Evidence-Based Passive Assessment Pipeline MVP & Evidence Integrity (Task 06.2.3)."""

from __future__ import annotations

import io
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthSettings
from aegiscore.execution import AssessmentExecutionEngine, _extract_allowlisted_headers
from aegiscore.local_persistence import LocalRecordStore, LocalStoreError, LocalStoreUnavailableError
from aegiscore.passive_detector import PassiveHeaderDetector
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    configured_test_app,
    create_bound_test_assessment,
    get_test_auth_settings,
    mark_mock_loopback_peer,
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


# ---------------------------------------------------------------------------
# 1. Evidence Collection & Header Extraction Tests
# ---------------------------------------------------------------------------


def test_allowlisted_headers_captured() -> None:
    headers = {
        "Content-Security-Policy": "default-src 'self'",
        "Strict-Transport-Security": "max-age=31536000",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=()",
    }
    norm, flags = _extract_allowlisted_headers(headers)
    assert len(norm) == 6
    assert norm["content-security-policy"] == "default-src 'self'"
    assert norm["strict-transport-security"] == "max-age=31536000"
    assert norm["x-content-type-options"] == "nosniff"
    assert norm["x-frame-options"] == "DENY"
    assert norm["referrer-policy"] == "no-referrer"
    assert norm["permissions-policy"] == "geolocation=()"
    assert flags == {}


def test_header_names_normalized() -> None:
    headers = {"X-CONTENT-TYPE-OPTIONS": "NOSNIFF", "Content-Security-Policy": "default-src 'none'"}
    norm, _ = _extract_allowlisted_headers(headers)
    assert "x-content-type-options" in norm
    assert "content-security-policy" in norm


def test_disallowed_headers_excluded() -> None:
    headers = {
        "Set-Cookie": "session=secret_value; HttpOnly",
        "Cookie": "admin_session=123",
        "Authorization": "Bearer my_secret_token",
        "Server": "Apache/2.4.41 (Ubuntu)",
        "X-Powered-By": "Express",
        "Location": "http://127.0.0.1:4000/secret",
        "X-Content-Type-Options": "nosniff",
    }
    norm, _ = _extract_allowlisted_headers(headers)
    assert len(norm) == 1
    assert "x-content-type-options" in norm
    assert "set-cookie" not in norm
    assert "cookie" not in norm
    assert "authorization" not in norm
    assert "server" not in norm
    assert "location" not in norm


def test_oversized_header_handling() -> None:
    oversized_val = "default-src " + ("'self' " * 500)
    headers = {"Content-Security-Policy": oversized_val}
    norm, flags = _extract_allowlisted_headers(headers)
    assert "content-security-policy" in norm
    assert len(norm["content-security-policy"]) == 2048
    assert flags.get("content-security-policy") == "oversized"


def test_response_bodies_never_read(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = AssessmentExecutionEngine()

    class BodyReadingErrorResponse(_MockResponse):
        def read(self, *_args, **_kwargs):
            raise AssertionError("Execution engine attempted to read HTTP response body!")

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return BodyReadingErrorResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)
    res = engine.execute_connectivity_observation("http://127.0.0.1:3000")
    assert res["reachable"] is True


def test_redirects_not_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:3000",
            code=301,
            msg="Moved Permanently",
            hdrs={"Location": "http://127.0.0.1:3000/new_location"},
            fp=None,
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)
    engine = AssessmentExecutionEngine()
    res = engine.execute_connectivity_observation("http://127.0.0.1:3000")
    assert res["reachable"] is True
    assert res["http_status"] == 301
    assert res["redirect_detected"] is True


def test_redirect_location_never_persisted_or_exposed_in_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:3000",
            code=302,
            msg="Found",
            hdrs={"Location": "http://secret.internal/admin_portal_login"},
            fp=None,
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)

        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 200

        # Verify Location URL is NOT present in any API response or text body
        assert "secret.internal" not in exec_res.text
        assert "admin_portal_login" not in exec_res.text

        get_res = client.get(f"/assessments/{asm_id}", headers=headers)
        assert "secret.internal" not in get_res.text

        evi_res = client.get(f"/assessments/{asm_id}/evidence", headers=headers)
        assert "secret.internal" not in evi_res.text

        fnd_res = client.get(f"/assessments/{asm_id}/findings", headers=headers)
        assert "secret.internal" not in fnd_res.text

        # Verify redirect_detected flag IS preserved
        assert exec_res.json()["execution_result"]["redirect_detected"] is True


def test_exactly_one_head_request_occurs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"
    call_count = 0

    def mock_open(opener, req, *_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert exec_res.status_code == 200
        assert call_count == 1


# ---------------------------------------------------------------------------
# 2. Detector Rule & Evidence Binding Tests
# ---------------------------------------------------------------------------


def test_detector_evidence_and_assessment_binding_validation() -> None:
    valid_asm_id = "asm_00000000000000000000000000000001"
    valid_ev_id = "evi_00000000000000000000000000000001"

    # 1. Missing evidence_id -> 0 findings
    ev_no_id = {
        "assessment_id": valid_asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_no_id) == []

    # 2. Malformed evidence_id -> 0 findings
    ev_bad_id = {
        "evidence_id": "invalid_id_format",
        "assessment_id": valid_asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_bad_id) == []

    # 3. Missing assessment_id inside evidence -> 0 findings
    ev_no_asm = {
        "evidence_id": valid_ev_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_no_asm) == []

    # 4. Empty assessment_id inside evidence -> 0 findings
    ev_empty_asm = {
        "evidence_id": valid_ev_id,
        "assessment_id": "",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_empty_asm) == []

    # 5. Mismatched assessment ID -> 0 findings
    ev_other_asm = {
        "evidence_id": valid_ev_id,
        "assessment_id": "asm_different_assessment_id_12345",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_other_asm) == []

    # 6. Invalid assessment_id parameter -> 0 findings
    ev_valid = {
        "evidence_id": valid_ev_id,
        "assessment_id": valid_asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    assert PassiveHeaderDetector.analyze("invalid_asm_id", "http://127.0.0.1:3000", ev_valid) == []

    # 7. Valid assessment and evidence IDs -> produces findings with non-empty, valid evidence references
    findings = PassiveHeaderDetector.analyze(valid_asm_id, "http://127.0.0.1:3000", ev_valid)
    assert len(findings) > 0
    for f in findings:
        assert f["evidence_ids"] == (valid_ev_id,)


def test_missing_csp_observation() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {"x-content-type-options": "nosniff"},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-001" in rule_ids


def test_missing_x_content_type_options_observation() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {"content-security-policy": "default-src 'self'"},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-002" in rule_ids


def test_missing_framing_protection_observation() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-003" in rule_ids


def test_oversized_csp_with_frame_ancestors_beyond_truncation() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    # Build CSP exceeding 2,048 chars where frame-ancestors is located AFTER the 2048 boundary
    padding = "default-src 'self'; script-src 'self' " + ("'self' " * 350)
    raw_csp = padding + "; frame-ancestors 'none'"
    assert len(raw_csp) > 2048
    assert raw_csp.find("frame-ancestors") > 2048

    norm_headers, flags = _extract_allowlisted_headers({"Content-Security-Policy": raw_csp})
    assert len(norm_headers["content-security-policy"]) == 2048
    assert "frame-ancestors" not in norm_headers["content-security-policy"]
    assert flags.get("content-security-policy") == "oversized"

    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm_headers,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    # WEB-HEADER-003 framing protection finding must NOT be emitted (fail-closed, because frame-ancestors was truncated)
    assert "WEB-HEADER-003" not in rule_ids
    # WEB-HEADER-001 missing CSP must NOT be emitted (CSP is present, even if oversized)
    assert "WEB-HEADER-001" not in rule_ids


def test_oversized_x_frame_options() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    raw_xfo = "DENY " + ("SAMEORIGIN " * 300)
    norm_headers, flags = _extract_allowlisted_headers({"X-Frame-Options": raw_xfo})
    assert flags.get("x-frame-options") == "oversized"

    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm_headers,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-003" not in rule_ids


def test_oversized_hsts() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    raw_hsts = "max-age=31536000; " + ("includeSubDomains " * 300)
    norm_headers, flags = _extract_allowlisted_headers({"Strict-Transport-Security": raw_hsts})
    assert flags.get("strict-transport-security") == "oversized"

    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm_headers,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "https://127.0.0.1:8443", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-005" not in rule_ids


def test_oversized_x_content_type_options() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    raw_nosniff = "nosniff " + ("nosniff " * 300)
    norm_headers, flags = _extract_allowlisted_headers({"X-Content-Type-Options": raw_nosniff})
    assert flags.get("x-content-type-options") == "oversized"

    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm_headers,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-002" not in rule_ids


def test_combined_oversized_csp_and_x_frame_options() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    norm_headers, flags = _extract_allowlisted_headers({
        "Content-Security-Policy": "default-src " + ("'self' " * 300),
        "X-Frame-Options": "DENY " + ("SAMEORIGIN " * 300),
    })
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm_headers,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-001" not in rule_ids
    assert "WEB-HEADER-003" not in rule_ids


def test_normal_headers_produce_expected_findings() -> None:
    asm_id = "asm_00000000000000000000000000000001"
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze(asm_id, "https://127.0.0.1:8443", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert set(rule_ids) == {"WEB-HEADER-001", "WEB-HEADER-002", "WEB-HEADER-003", "WEB-HEADER-004", "WEB-HEADER-005"}


def test_existing_csp_frame_ancestors_prevents_framing_finding() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {"content-security-policy": "default-src 'self'; frame-ancestors 'none'"},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-003" not in rule_ids


def test_existing_x_frame_options_prevents_framing_finding() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {"x-frame-options": "DENY"},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-003" not in rule_ids


def test_missing_referrer_policy_observation() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-004" in rule_ids


def test_missing_hsts_on_https() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "https://127.0.0.1:8443", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-005" in rule_ids


def test_no_missing_hsts_finding_on_http() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-005" not in rule_ids


def test_no_findings_for_unreachable_targets() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "unreachable",
        "http_status": None,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    assert findings == []


def test_no_security_findings_for_non_2xx_responses() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 302,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    assert findings == []


def test_oversized_headers_not_misclassified_as_missing() -> None:
    oversized_csp = "default-src " + ("'self' " * 500)
    norm, flags = _extract_allowlisted_headers({"Content-Security-Policy": oversized_csp})
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": norm,
        "header_flags": flags,
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    rule_ids = [f["rule_id"] for f in findings]
    assert "WEB-HEADER-001" not in rule_ids


def test_findings_always_reference_valid_evidence() -> None:
    evidence = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": "asm_00000000000000000000000000000001",
        "collection_status": "observed",
        "http_status": 200,
        "normalized_headers": {},
    }
    findings = PassiveHeaderDetector.analyze("asm_00000000000000000000000000000001", "http://127.0.0.1:3000", evidence)
    assert len(findings) > 0
    for f in findings:
        assert f["evidence_ids"] == ("evi_00000000000000000000000000000001",)


# ---------------------------------------------------------------------------
# 3. Atomic Pipeline Persistence & Genuine SQLite Rollback Tests
# ---------------------------------------------------------------------------


def test_genuine_sqlite_transaction_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "rollback_test.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    asm = create_bound_test_assessment(store)
    asm_id = asm["assessment_id"]
    running_rec = store.update_assessment_status(asm_id, "running")
    token = running_rec["lease_token"]

    # Ensure pipeline tables exist before creating trigger
    conn = sqlite3.connect(db_path)
    store._ensure_pipeline_tables(conn)
    conn.execute(
        """
        CREATE TRIGGER fail_findings_insert
        BEFORE INSERT ON findings
        BEGIN
            SELECT RAISE(FAIL, 'Simulated SQLite transaction failure on findings insert at /secret/internal/db/path');
        END;
        """
    )
    conn.commit()
    conn.close()

    evidence_data = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "evidence_type": "http_security_headers",
        "source": "passive_head_observation",
        "observed_at": "2026-11-23T18:00:00Z",
        "http_status": 200,
        "normalized_headers": {},
        "collection_status": "observed",
    }
    finding_data = [{
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
    }]
    exec_result = {"reachable": True, "http_status": 200}

    # 1. Execute save_pipeline_result; SQLite trigger forces transaction failure
    with pytest.raises(LocalStoreUnavailableError):
        store.save_pipeline_result(
            assessment_id=asm_id,
            evidence=evidence_data,
            findings=finding_data,
            final_status="completed",
            execution_result=exec_result,
            lease_token=token,
        )

    # 2. Verify complete transaction rollback at database level
    assert store.list_evidence(asm_id) == []  # Evidence inserted earlier in transaction was rolled back!
    assert store.list_findings(asm_id) == []  # Zero findings persisted
    fetched_asm = store.get_assessment(asm_id)
    assert fetched_asm["status"] == "running"  # Status was NOT updated to 'completed'
    assert "execution_result" not in fetched_asm

    # 3. Test API endpoint behavior when SQLite trigger is installed
    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200, headers={})

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        # Create fresh assessment
        c2 = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm2_id = c2.json()["assessment_id"]

        exec_res = client.post(f"/assessments/{asm2_id}/execute", headers=headers)
        assert exec_res.status_code == 503
        assert exec_res.json() == {"detail": "Local persistence store is unavailable or inconsistent."}
        # Raw SQLite exception and file paths are NOT exposed
        assert "/secret/internal/db/path" not in exec_res.text
        assert "Simulated SQLite transaction failure" not in exec_res.text


def test_persistence_failure_recovers_without_application_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "in_process_recovery.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200, headers={})

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)
    monkeypatch.setattr("aegiscore.api.routes.DEFAULT_EXECUTION_LEASE_SECONDS", 0.5)

    with TestClient(configured_test_app(
        local_store_path=db_path,
        recovery_interval_seconds=0.01,
    )) as client:
        headers = _login(client)
        created = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        )
        assert created.status_code == 201
        assessment_id = created.json()["assessment_id"]

        store = LocalRecordStore.create_or_open(db_path)
        with store._connection() as connection:
            store._ensure_pipeline_tables(connection)
            connection.execute(
                """
                CREATE TRIGGER fail_integration_findings
                BEFORE INSERT ON findings
                BEGIN
                    SELECT RAISE(FAIL, 'temporary findings persistence failure');
                END;
                """
            )

        failed_persistence = client.post(
            f"/assessments/{assessment_id}/execute",
            headers=headers,
        )
        assert failed_persistence.status_code == 503
        persisted = store.get_assessment(assessment_id)
        assert persisted["status"] == "running"
        assert persisted["lease_token"]
        assert store.list_evidence(assessment_id) == []
        assert store.list_findings(assessment_id) == []
        assert "execution_result" not in persisted

        with store._connection() as connection:
            connection.execute("DROP TRIGGER fail_integration_findings")

        deadline = time.monotonic() + 3.0
        recovered = persisted
        while time.monotonic() < deadline:
            recovered = store.get_assessment(assessment_id)
            if recovered["status"] == "failed":
                break
            time.sleep(0.02)

        assert recovered["status"] == "failed"
        assert recovered["recovery_metadata"]["recovered"] is True
        assert "execution_result" not in recovered
        assert store.list_evidence(assessment_id) == []
        assert store.list_findings(assessment_id) == []


def test_atomic_pipeline_persistence_and_evidence_reference_validation(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    asm = create_bound_test_assessment(store)
    asm_id = asm["assessment_id"]
    running_rec = store.update_assessment_status(asm_id, "running")
    token = running_rec["lease_token"]

    evidence_data = {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "evidence_type": "http_security_headers",
        "source": "passive_head_observation",
        "observed_at": "2026-11-23T18:00:00Z",
        "http_status": 200,
        "normalized_headers": {"x-content-type-options": "nosniff"},
        "collection_status": "observed",
    }

    # Finding with valid evidence_id reference
    valid_finding = {
        "finding_id": "fnd_valid001",
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
    }

    # Finding with invalid/fabricated evidence_id reference
    fake_finding = {
        "finding_id": "fnd_fake001",
        "assessment_id": asm_id,
        "rule_id": "WEB-HEADER-002",
        "title": "Fake finding",
        "description": "Test description",
        "classification": "configuration_observation",
        "severity": "info",
        "confidence": "low",
        "status": "detected",
        "evidence_ids": ("evi_fabricated_nonexistent_id",),
        "remediation": "Test remediation",
        "created_at": "2026-11-23T18:00:01Z",
    }

    exec_result = {"reachable": True, "http_status": 200}

    # Save pipeline result atomically
    final_record = store.save_pipeline_result(
        assessment_id=asm_id,
        evidence=evidence_data,
        findings=[valid_finding, fake_finding],
        final_status="completed",
        execution_result=exec_result,
        lease_token=token,
    )
    assert final_record["status"] == "completed"

    listed_evi = store.list_evidence(asm_id)
    listed_fnd = store.list_findings(asm_id)
    assert len(listed_evi) == 1
    assert listed_evi[0]["evidence_id"] == "evi_00000000000000000000000000000001"

    # Only valid finding referencing actual persisted evidence was saved
    assert len(listed_fnd) == 1
    assert listed_fnd[0]["finding_id"] == "fnd_valid001"


def test_evidence_and_finding_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    asm = create_bound_test_assessment(store)
    asm_id = asm["assessment_id"]

    evidence_data = {
        "evidence_id": "evi_test001",
        "assessment_id": asm_id,
        "evidence_type": "http_security_headers",
        "source": "passive_head_observation",
        "observed_at": "2026-11-23T18:00:00Z",
        "http_status": 200,
        "normalized_headers": {"x-content-type-options": "nosniff"},
        "collection_status": "observed",
    }
    saved_evi = store.save_evidence(asm_id, evidence_data)
    assert saved_evi["evidence_id"] == "evi_test001"

    finding_data = [{
        "finding_id": "fnd_test001",
        "assessment_id": asm_id,
        "rule_id": "WEB-HEADER-001",
        "title": "CSP not observed",
        "description": "Test description",
        "classification": "configuration_observation",
        "severity": "info",
        "confidence": "low",
        "status": "detected",
        "evidence_ids": ("evi_test001",),
        "remediation": "Test remediation",
        "created_at": "2026-11-23T18:00:01Z",
    }]
    saved_fnd = store.save_findings(asm_id, finding_data)
    assert len(saved_fnd) == 1
    assert saved_fnd[0]["finding_id"] == "fnd_test001"

    listed_evi = store.list_evidence(asm_id)
    listed_fnd = store.list_findings(asm_id)
    assert len(listed_evi) == 1
    assert listed_evi[0]["evidence_id"] == "evi_test001"
    assert len(listed_fnd) == 1
    assert listed_fnd[0]["finding_id"] == "fnd_test001"


def test_application_restart_retrieval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200, headers={"Server": "Apache"})

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    # 1. First app instance creates and executes assessment
    with TestClient(configured_test_app(local_store_path=db_path)) as client1:
        headers = _login(client1)
        c_res = client1.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        e_res = client1.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert e_res.status_code == 200

    # 2. Fresh app instance reads evidence and findings from SQLite
    with TestClient(configured_test_app(local_store_path=db_path)) as client2:
        headers2 = _login(client2)
        evi_res = client2.get(f"/assessments/{asm_id}/evidence", headers=headers2)
        fnd_res = client2.get(f"/assessments/{asm_id}/findings", headers=headers2)

        assert evi_res.status_code == 200
        assert evi_res.json()["total"] == 1
        assert fnd_res.status_code == 200
        assert fnd_res.json()["total"] > 0


def test_duplicate_finding_prevention(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    store = LocalRecordStore.create_or_open(db_path)
    asm = create_bound_test_assessment(store)
    asm_id = asm["assessment_id"]

    ev = store.save_evidence(asm_id, {
        "evidence_id": "evi_00000000000000000000000000000001",
        "assessment_id": asm_id,
        "evidence_type": "http_security_headers",
        "source": "passive_head_observation",
        "observed_at": "2026-11-23T18:00:00Z",
    })

    finding_item = {
        "finding_id": "fnd_dup001",
        "assessment_id": asm_id,
        "rule_id": "WEB-HEADER-001",
        "title": "CSP not observed",
        "description": "Original description",
        "classification": "configuration_observation",
        "severity": "info",
        "confidence": "low",
        "status": "detected",
        "evidence_ids": ("evi_00000000000000000000000000000001",),
        "remediation": "Test remediation",
        "created_at": "2026-11-23T18:00:00Z",
    }

    # Save first time
    store.save_findings(asm_id, [finding_item])
    assert len(store.list_findings(asm_id)) == 1

    # Save updated finding with same rule_id
    finding_item["description"] = "Updated description"
    store.save_findings(asm_id, [finding_item])
    findings = store.list_findings(asm_id)
    assert len(findings) == 1
    assert findings[0]["description"] == "Updated description"


# ---------------------------------------------------------------------------
# 4. API, OpenAPI & Permission Verification Tests
# ---------------------------------------------------------------------------


def test_missing_assessment_returns_404(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    fake_id = "asm_00000000000000000000000000000000"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        evi = client.get(f"/assessments/{fake_id}/evidence", headers=headers)
        fnd = client.get(f"/assessments/{fake_id}/findings", headers=headers)
        assert evi.status_code == 404
        assert fnd.status_code == 404


def test_api_read_permission_and_openapi_exact_schema_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"

    # 1. Account without records:read permission receives 403 Forbidden
    no_read_settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        permissions=frozenset({"assessments:create"}),
    )
    with TestClient(create_app(local_store_path=db_path, auth_settings=no_read_settings)) as client:
        headers = _login(client)
        assert client.get("/assessments/asm_00000000000000000000000000000000/evidence", headers=headers).status_code == 403
        assert client.get("/assessments/asm_00000000000000000000000000000000/findings", headers=headers).status_code == 403

    # 2. Unauthenticated user receives 401 Unauthorized
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        assert client.get("/assessments/asm_00000000000000000000000000000000/evidence").status_code == 401
        assert client.get("/assessments/asm_00000000000000000000000000000000/findings").status_code == 401

    # 3. Authenticated user with records:read permission gets 200 OK
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        assert client.get(f"/assessments/{asm_id}/evidence", headers=headers).status_code == 200
        assert client.get(f"/assessments/{asm_id}/findings", headers=headers).status_code == 200

    # 4. Verify OpenAPI schema contains paths and EXACT $ref schema object references
    with TestClient(create_app()) as client:
        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        evi_schema_ref = paths["/assessments/{assessment_id}/evidence"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        fnd_schema_ref = paths["/assessments/{assessment_id}/findings"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

        assert evi_schema_ref == "#/components/schemas/AssessmentEvidenceListResponse"
        assert fnd_schema_ref == "#/components/schemas/AssessmentFindingListResponse"

        schemas = openapi.get("components", {}).get("schemas", {})
        assert "AssessmentEvidenceListResponse" in schemas
        assert "AssessmentFindingListResponse" in schemas


def test_api_read_endpoints_sqlite_failure_returns_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_failing_list_evidence(*_args, **_kwargs):
        raise LocalStoreUnavailableError("Simulated SQLite failure at /secret/db/path")

    def mock_failing_list_findings(*_args, **_kwargs):
        raise LocalStoreUnavailableError("Simulated SQLite failure at /secret/db/path")

    monkeypatch.setattr(LocalRecordStore, "list_evidence", mock_failing_list_evidence)
    monkeypatch.setattr(LocalRecordStore, "list_findings", mock_failing_list_findings)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        evi_res = client.get(f"/assessments/{asm_id}/evidence", headers=headers)
        fnd_res = client.get(f"/assessments/{asm_id}/findings", headers=headers)

        assert evi_res.status_code == 503
        assert evi_res.json() == {"detail": "Local persistence store is unavailable or inconsistent."}
        assert "/secret/db/path" not in evi_res.text

        assert fnd_res.status_code == 503
        assert fnd_res.json() == {"detail": "Local persistence store is unavailable or inconsistent."}
        assert "/secret/db/path" not in fnd_res.text


def test_empty_evidence_and_findings_responses(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        evi = client.get(f"/assessments/{asm_id}/evidence", headers=headers)
        fnd = client.get(f"/assessments/{asm_id}/findings", headers=headers)
        assert evi.status_code == 200
        assert evi.json() == {"items": [], "total": 0}
        assert fnd.status_code == 200
        assert fnd.json() == {"items": [], "total": 0}


# ---------------------------------------------------------------------------
# 5. Security & Pipeline Boundary Tests
# ---------------------------------------------------------------------------


def test_execution_remains_restricted_to_numeric_loopback(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://localhost:8080"}, headers=headers)
        assert c_res.status_code == 400


def test_rejected_targets_produce_no_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def network_bomb(*_args, **_kwargs):
        raise AssertionError("Network/DNS call performed for rejected target!")

    monkeypatch.setattr(socket, "getaddrinfo", network_bomb)
    monkeypatch.setattr(socket, "create_connection", network_bomb)

    db_path = tmp_path / "records.sqlite3"
    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://localhost:8080"}, headers=headers)
        assert c_res.status_code == 400


def test_no_sensitive_response_headers_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    sensitive_headers = {
        "Set-Cookie": "session=secret123; HttpOnly",
        "Authorization": "Bearer token123",
        "Server": "Apache/2.4.41",
        "Content-Security-Policy": "default-src 'self'",
    }

    def mock_open(opener, req, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, req)
        return _MockResponse(code=200, headers=sensitive_headers)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        e_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert e_res.status_code == 200

        evi_res = client.get(f"/assessments/{asm_id}/evidence", headers=headers)
        assert evi_res.status_code == 200
        evi_item = evi_res.json()["items"][0]
        headers_stored = evi_item["normalized_headers"]

        assert "content-security-policy" in headers_stored
        assert "set-cookie" not in headers_stored
        assert "cookie" not in headers_stored
        assert "authorization" not in headers_stored
        assert "server" not in headers_stored


def test_no_raw_exception_information_in_api_responses_or_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "records.sqlite3"

    def mock_failing_open(*_args, **_kwargs):
        raise urllib.error.URLError(ConnectionRefusedError(10061, "Connection refused at /secret/internal/path"))

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", mock_failing_open)

    with TestClient(configured_test_app(local_store_path=db_path)) as client:
        headers = _login(client)
        c_res = client.post("/assessments", json={"target_url": "http://127.0.0.1:3000"}, headers=headers)
        asm_id = c_res.json()["assessment_id"]

        e_res = client.post(f"/assessments/{asm_id}/execute", headers=headers)
        assert e_res.status_code == 200
        data = e_res.json()
        assert data["status"] == "failed"
        assert "/secret/internal/path" not in e_res.text

        fnd_res = client.get(f"/assessments/{asm_id}/findings", headers=headers)
        assert fnd_res.status_code == 200
        assert fnd_res.json()["total"] == 0
