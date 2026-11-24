"""Helpers for tests that exercise the real local login endpoint."""

from contextlib import contextmanager
from functools import lru_cache
from datetime import datetime, timedelta, timezone
import hashlib
from ipaddress import ip_address
from typing import Iterator
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthSettings, DEFAULT_PERMISSIONS
from aegiscore.authorization_verification import VerifiedAuthorizationEvidence
from aegiscore.local_persistence import LocalRecordStore
from aegiscore.safety import ApprovedTargetRegistration, TargetRegistry
from aegiscore.target_authorization import resolve_authorized_endpoint


TEST_USERNAME = "phase8g7-test-user"
TEST_PASSWORD = "phase8g7-local-test-password"
TEST_TARGET_ID = "test-loopback-target"


class SyntheticTestAuthorizationVerifier:
    """Explicit test-only verifier; it represents no real issuer or approval."""

    trusted_issuers = frozenset({"synthetic-test-issuer-only"})

    def verify(self, registration, canonical_endpoint: str, *, now: datetime) -> VerifiedAuthorizationEvidence:
        issued_at = now - timedelta(seconds=1)
        expires_at = now + timedelta(hours=1)
        revocation_snapshot_expires_at = now + timedelta(minutes=1)
        signed_fields = "\0".join((
            registration.authorization_ref,
            registration.target_id,
            canonical_endpoint,
            registration.registration_version,
            issued_at.isoformat(),
            expires_at.isoformat(),
        ))
        return VerifiedAuthorizationEvidence(
            authorization_ref=registration.authorization_ref,
            issuer_id="synthetic-test-issuer-only",
            key_id="synthetic-test-key-only",
            target_id=registration.target_id,
            canonical_endpoint=canonical_endpoint,
            registration_version=registration.registration_version,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
            verified_at=now.isoformat(),
            revocation_checked_at=now.isoformat(),
            revocation_snapshot_expires_at=revocation_snapshot_expires_at.isoformat(),
            signature_sha256=hashlib.sha256(signed_fields.encode("utf-8")).hexdigest(),
            signature_valid=True,
            revoked=False,
        )


def make_test_authorization_verifier() -> SyntheticTestAuthorizationVerifier:
    return SyntheticTestAuthorizationVerifier()


@lru_cache(maxsize=1)
def get_test_auth_settings() -> AuthSettings:
    return AuthSettings(
        username=TEST_USERNAME,
        password_hash=PasswordHasher().hash(TEST_PASSWORD),
        permissions=DEFAULT_PERMISSIONS,
    )


def make_test_target_registry(
    target_url: str = "http://127.0.0.1:3000/",
    *,
    target_id: str = TEST_TARGET_ID,
    permitted_paths: tuple[str, ...] = ("/", "/first", "/second", "/rest/products"),
) -> TargetRegistry:
    parsed = urlsplit(target_url)
    if parsed.hostname is None:
        raise ValueError("test target URL must include a numeric host")
    address = ip_address(parsed.hostname)
    port = parsed.port or (80 if parsed.scheme == "http" else 443)
    path = parsed.path or "/"
    paths = permitted_paths if path in permitted_paths else (path,)
    registration = ApprovedTargetRegistration(
        target_id=target_id,
        scheme=parsed.scheme,
        hostname=address.compressed,
        port=port,
        permitted_paths=paths,
        authorization_ref="test-only-explicit-authorization-fixture",
        network_zone_id="test-loopback-only",
        enabled=True,
        registration_version="test-registration-v1",
    )
    return TargetRegistry((registration,))


def create_bound_test_assessment(store: LocalRecordStore, target_url: str = "http://127.0.0.1:3000/") -> dict:
    registry = make_test_target_registry(target_url)
    registration, canonical_endpoint = resolve_authorized_endpoint(registry, target_url)
    now = datetime.now(timezone.utc)
    provenance = make_test_authorization_verifier().verify(
        registration, canonical_endpoint, now=now
    ).to_record()
    return store.create_assessment(
        target_url=canonical_endpoint,
        target_id=registration.target_id,
        canonical_endpoint=canonical_endpoint,
        authorization_ref=registration.authorization_ref,
        registration_version=registration.registration_version,
        authorization_provenance=provenance,
    )


def mark_mock_loopback_peer(opener: object, request: object) -> None:
    """Give a fake opener an explicit peer result for deterministic transport tests."""
    full_url = getattr(request, "full_url", None)
    if not isinstance(full_url, str):
        return
    parsed = urlsplit(full_url)
    if parsed.hostname is None:
        return
    try:
        peer = ip_address(parsed.hostname).compressed
    except ValueError:
        return
    for handler in getattr(opener, "handlers", ()):
        if hasattr(handler, "connected_peer"):
            handler.connected_peer = peer


def configured_test_app(**kwargs) -> FastAPI:
    kwargs.setdefault("auth_settings", get_test_auth_settings())
    kwargs.setdefault("authorized_target_registry", make_test_target_registry())
    kwargs.setdefault("authorization_verifier", make_test_authorization_verifier())
    return create_app(**kwargs)


@contextmanager
def authenticated_client(app: FastAPI) -> Iterator[TestClient]:
    """Log in through /auth/login and add its returned bearer to this client."""

    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client

