"""Deterministic tests for the authoritative authorization-verifier boundary."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import urllib.request
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.authorization_verification import (
    AuthorizationFailureReason,
    AuthorizationVerificationError,
    VerifiedAuthorizationEvidence,
    verify_authorization,
)
from aegiscore.local_persistence import LocalRecordStore
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    get_test_auth_settings,
    make_test_target_registry,
    mark_mock_loopback_peer,
)


class ScriptedVerifier:
    """Test double only; its synthetic issuer is not a real approval authority."""

    trusted_issuers = frozenset({"synthetic-test-issuer-only"})

    def __init__(self, states: list[str] | None = None) -> None:
        self.states = list(states or ["valid"])
        self.calls = 0

    def verify(self, registration, canonical_endpoint: str, *, now: datetime) -> VerifiedAuthorizationEvidence:
        state = self.states[min(self.calls, len(self.states) - 1)]
        self.calls += 1
        if state == "unavailable":
            raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)

        issued_at = now - timedelta(minutes=1)
        expires_at = now + timedelta(minutes=10)
        revoked = False
        signature_valid = True
        issuer_id = "synthetic-test-issuer-only"
        if state == "invalid_signature":
            signature_valid = False
        elif state == "unknown_issuer":
            issuer_id = "unknown-synthetic-issuer"
        elif state == "expired":
            expires_at = now - timedelta(seconds=1)
        elif state == "revoked":
            revoked = True
        elif state == "not_yet_valid":
            issued_at = now + timedelta(seconds=1)

        signature_digest = hashlib.sha256(
            f"synthetic-test-only:{registration.authorization_ref}:{state}".encode("utf-8")
        ).hexdigest()
        return VerifiedAuthorizationEvidence(
            authorization_ref=registration.authorization_ref,
            issuer_id=issuer_id,
            key_id="synthetic-test-key-only",
            target_id=registration.target_id,
            canonical_endpoint=canonical_endpoint,
            registration_version=registration.registration_version,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
            verified_at=now.isoformat(),
            revocation_checked_at=now.isoformat(),
            revocation_snapshot_expires_at=(now + timedelta(minutes=1)).isoformat(),
            signature_sha256=signature_digest,
            signature_valid=signature_valid,
            revoked=revoked,
        )


def _verify_state(state: str) -> None:
    registry = make_test_target_registry()
    registration = registry.registrations[0]
    now = datetime.now(timezone.utc)
    verify_authorization(
        ScriptedVerifier([state]),
        registration,
        "http://127.0.0.1:3000/",
        now=now,
    )


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        ("invalid_signature", AuthorizationFailureReason.INVALID_SIGNATURE),
        ("unknown_issuer", AuthorizationFailureReason.UNKNOWN_ISSUER),
        ("expired", AuthorizationFailureReason.EXPIRED),
        ("revoked", AuthorizationFailureReason.REVOKED),
        ("unavailable", AuthorizationFailureReason.UNAVAILABLE),
        ("not_yet_valid", AuthorizationFailureReason.NOT_YET_VALID),
    ],
)
def test_authorization_verification_rejects_untrusted_states(
    state: str, reason: AuthorizationFailureReason
) -> None:
    with pytest.raises(AuthorizationVerificationError) as raised:
        _verify_state(state)
    assert raised.value.reason is reason


def test_missing_verifier_fails_closed() -> None:
    registration = make_test_target_registry().registrations[0]
    with pytest.raises(AuthorizationVerificationError) as raised:
        verify_authorization(None, registration, "http://127.0.0.1:3000/")
    assert raised.value.reason is AuthorizationFailureReason.UNAVAILABLE


def test_verifier_configuration_fault_fails_closed() -> None:
    registration = make_test_target_registry().registrations[0]

    class BrokenVerifier(ScriptedVerifier):
        @property
        def trusted_issuers(self):
            raise RuntimeError("synthetic verifier configuration fault")

    with pytest.raises(AuthorizationVerificationError) as raised:
        verify_authorization(BrokenVerifier(), registration, "http://127.0.0.1:3000/")
    assert raised.value.reason is AuthorizationFailureReason.UNAVAILABLE


def test_expired_revocation_snapshot_fails_closed() -> None:
    registration = make_test_target_registry().registrations[0]
    now = datetime.now(timezone.utc)
    evidence = ScriptedVerifier().verify(registration, "http://127.0.0.1:3000/", now=now)
    stale = replace(evidence, revocation_snapshot_expires_at=(now - timedelta(seconds=1)).isoformat())

    class StaleSnapshotVerifier(ScriptedVerifier):
        def verify(self, registration, canonical_endpoint: str, *, now: datetime) -> VerifiedAuthorizationEvidence:
            self.calls += 1
            return stale

    with pytest.raises(AuthorizationVerificationError) as raised:
        verify_authorization(StaleSnapshotVerifier(), registration, "http://127.0.0.1:3000/", now=now)
    assert raised.value.reason is AuthorizationFailureReason.UNAVAILABLE


@pytest.mark.parametrize("expiry", ["not-an-iso-timestamp", "2030-01-01T00:00:00"])
def test_malformed_or_timezone_naive_authorization_expiry_fails_closed(expiry: str) -> None:
    registration = make_test_target_registry().registrations[0]
    now = datetime.now(timezone.utc)
    evidence = ScriptedVerifier().verify(registration, "http://127.0.0.1:3000/", now=now)
    invalid_evidence = replace(evidence, expires_at=expiry)

    class InvalidTimestampVerifier(ScriptedVerifier):
        def verify(self, registration, canonical_endpoint: str, *, now: datetime) -> VerifiedAuthorizationEvidence:
            self.calls += 1
            return invalid_evidence

    with pytest.raises(AuthorizationVerificationError) as raised:
        verify_authorization(
            InvalidTimestampVerifier(),
            registration,
            "http://127.0.0.1:3000/",
            now=now,
        )
    assert raised.value.reason is AuthorizationFailureReason.INVALID_EVIDENCE


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("state", ["invalid_signature", "unknown_issuer", "expired", "revoked"])
def test_api_creation_does_not_persist_unverified_approval(
    tmp_path: Path, state: str
) -> None:
    db_path = tmp_path / f"create-{state}.sqlite3"
    app = create_app(
        local_store_path=db_path,
        auth_settings=get_test_auth_settings(),
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=ScriptedVerifier([state]),
    )
    with TestClient(app) as client:
        headers = _login(client)
        response = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Target authorization could not be verified."}

    store = LocalRecordStore.open_existing(db_path)
    assert store.list_assessments(offset=0, limit=10) == ([], 0)


@pytest.mark.parametrize("state", ["expired", "revoked", "unavailable"])
def test_execution_rechecks_authorization_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    db_path = tmp_path / f"execute-{state}.sqlite3"
    verifier = ScriptedVerifier(["valid", "valid", state])
    network_calls: list[str] = []

    def forbidden_transport(opener, request, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, request)
        network_calls.append(request.full_url)
        raise AssertionError("Authorization was not revalidated before HTTP dispatch")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden_transport)
    app = create_app(
        local_store_path=db_path,
        auth_settings=get_test_auth_settings(),
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=verifier,
    )
    with TestClient(app) as client:
        headers = _login(client)
        created = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        )
        assert created.status_code == 201
        assessment_id = created.json()["assessment_id"]

        response = client.post(f"/assessments/{assessment_id}/execute", headers=headers)
        expected_status = 503 if state == "unavailable" else 409
        assert response.status_code == expected_status
        assert network_calls == []

    persisted = LocalRecordStore.open_existing(db_path).get_assessment(assessment_id)
    assert persisted["status"] == "failed"
    assert persisted["execution_result"]["reachable"] is False
    assert persisted["execution_result"]["outcome"] == (
        "Authorization verification failed before network execution"
    )


@pytest.mark.parametrize("state", ["expired", "revoked", "unavailable"])
def test_execution_rechecks_authorization_at_guarded_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    db_path = tmp_path / f"dispatch-{state}.sqlite3"
    # Creation, pre-lease API validation, and post-lease executor validation pass;
    # the final result represents the independent check inside guarded dispatch.
    verifier = ScriptedVerifier(["valid", "valid", "valid", state])
    network_calls: list[str] = []

    def forbidden_transport(opener, request, *_args, **_kwargs):
        mark_mock_loopback_peer(opener, request)
        network_calls.append(request.full_url)
        raise AssertionError("The HTTP engine ran after authorization was denied")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden_transport)
    app = create_app(
        local_store_path=db_path,
        auth_settings=get_test_auth_settings(),
        authorized_target_registry=make_test_target_registry(),
        authorization_verifier=verifier,
    )
    with TestClient(app) as client:
        headers = _login(client)
        created = client.post(
            "/assessments",
            json={"target_url": "http://127.0.0.1:3000/"},
            headers=headers,
        )
        assert created.status_code == 201
        assessment_id = created.json()["assessment_id"]

        response = client.post(f"/assessments/{assessment_id}/execute", headers=headers)
        assert response.status_code == 503
        assert network_calls == []
        assert verifier.calls == 4

    persisted = LocalRecordStore.open_existing(db_path).get_assessment(assessment_id)
    assert persisted["status"] == "failed"
