from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthConfigurationError, AuthSettings, DEFAULT_PERMISSIONS
from tests.auth_helpers import (
    TEST_PASSWORD,
    TEST_USERNAME,
    configured_test_app,
    get_test_auth_settings,
)


def _login(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert isinstance(token, str) and token
    return token


def test_login_protects_records_and_logout_invalidates_session(tmp_path) -> None:
    with TestClient(
        configured_test_app(local_store_path=tmp_path / "records.sqlite3")
    ) as client:
        assert client.get("/sessions").status_code == 401
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        session = client.get("/auth/session", headers=headers)
        assert session.status_code == 200
        assert session.json()["authenticated"] is True
        assert session.json()["username"] == TEST_USERNAME
        assert set(session.json()["permissions"]) == DEFAULT_PERMISSIONS
        assert client.get("/sessions", headers=headers).status_code == 200
        assert client.post("/auth/logout", headers=headers).json() == {
            "status": "signed_out"
        }
        assert client.get("/sessions", headers=headers).status_code == 401


def test_missing_malformed_and_invalid_tokens_are_rejected_consistently() -> None:
    with TestClient(configured_test_app()) as client:
        missing = client.get("/sessions")
        malformed = client.get("/sessions", headers={"Authorization": "Bearer !!!"})
        invalid = client.get("/sessions", headers={"Authorization": "Bearer " + "x" * 43})

    assert missing.status_code == malformed.status_code == invalid.status_code == 401
    assert missing.json() == malformed.json() == invalid.json()


def test_all_persisted_and_evidence_routes_require_authentication() -> None:
    protected_paths = (
        "/dashboard/summary",
        "/sessions",
        "/sessions/session_00000000000000000000000000000000",
        "/sessions/session_00000000000000000000000000000000/findings",
        "/findings",
        "/findings/finding_00000000000000000000000000000000",
        "/reports",
        "/reports/report_00000000000000000000000000000000",
        "/evidence/approved",
        "/evidence/approved/source-chunk",
    )
    with TestClient(configured_test_app()) as client:
        statuses = [client.get(path).status_code for path in protected_paths]

    assert statuses == [401] * len(protected_paths)


def test_bad_credentials_are_generic_and_do_not_leak_secrets(caplog: pytest.LogCaptureFixture) -> None:
    password_hash = get_test_auth_settings().password_hash
    with TestClient(configured_test_app()) as client:
        response = client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": "wrong-secret-test"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required or credentials are invalid."}
    assert "wrong-secret-test" not in response.text
    assert password_hash not in response.text
    assert "wrong-secret-test" not in caplog.text
    assert password_hash not in caplog.text


def test_invalid_login_payload_never_echoes_password_input() -> None:
    secret = "private-password-that-is-far-too-long-" + "x" * 1100
    with TestClient(configured_test_app()) as client:
        response = client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": secret},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid authentication request."}
    assert secret not in response.text


def test_expired_sessions_are_rejected() -> None:
    settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        session_ttl_seconds=1,
    )
    with TestClient(create_app(auth_settings=settings)) as client:
        token = _login(client)
        time.sleep(1.05)
        expired = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})

    assert expired.status_code == 401


def test_record_permission_does_not_imply_evidence_permission() -> None:
    settings = AuthSettings(
        username=TEST_USERNAME,
        password_hash=get_test_auth_settings().password_hash,
        permissions=frozenset({"records:read"}),
    )
    with TestClient(create_app(auth_settings=settings)) as client:
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/dashboard/summary", headers=headers).status_code == 503
        denied = client.get("/evidence/approved", headers=headers)

    assert denied.status_code == 403
    assert denied.json() == {"detail": "The authenticated account lacks this permission."}


def test_unconfigured_auth_fails_closed_for_protected_routes() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/auth/login",
            json={"username": "local", "password": "not-a-real-password"},
        )
        records = client.get("/sessions")
        assert client.get("/health").status_code == 200
        assert client.get("/capabilities").status_code == 200

    assert login.status_code == records.status_code == 503
    assert "not configured" in login.json()["detail"].lower()


def test_auth_configuration_requires_a_valid_hash_and_complete_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AEGISCORE_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("AEGISCORE_AUTH_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("AEGISCORE_AUTH_USERNAME", TEST_USERNAME)
    with pytest.raises(AuthConfigurationError):
        AuthSettings.load()
    with pytest.raises(AuthConfigurationError):
        AuthSettings(username=TEST_USERNAME, password_hash="plaintext-is-not-a-hash")


def test_non_loopback_bind_is_rejected_and_remote_peers_are_blocked() -> None:
    assert create_app().state.api_host == "127.0.0.1"
    with pytest.raises(RuntimeError, match="loopback"):
        create_app(api_host="0.0.0.0")

    app = configured_test_app()
    try:
        client = TestClient(app, client=("198.51.100.7", 50000))
    except TypeError:
        pytest.skip("Installed Starlette TestClient cannot simulate a remote peer.")
    with client:
        response = client.get("/health")
    assert response.status_code == 403
    assert response.json() == {"detail": "Loopback access only."}

    with TestClient(app, base_url="http://0.0.0.0") as wildcard_bound:
        rejected_bind = wildcard_bound.get("/health")
    assert rejected_bind.status_code == 503
    assert rejected_bind.json() == {
        "detail": "Service is configured for loopback access only."
    }


def test_authentication_config_loader_reads_private_toml(tmp_path, monkeypatch) -> None:
    config = tmp_path / "auth.toml"
    config.write_text(
        '[auth]\nusername = "local-user"\npassword_hash = '
        f'"{get_test_auth_settings().password_hash}"\nsession_ttl_seconds = 1800\n'
        'permissions = ["records:read"]\n',
        encoding="utf-8",
    )
    if config.stat().st_mode & 0o077:
        config.chmod(0o600)
    for key in (
        "AEGISCORE_AUTH_USERNAME",
        "AEGISCORE_AUTH_PASSWORD_HASH",
        "AEGISCORE_AUTH_SESSION_TTL_SECONDS",
        "AEGISCORE_AUTH_PERMISSIONS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AEGISCORE_AUTH_CONFIG_FILE", str(config))
    settings = AuthSettings.load()

    assert settings is not None
    assert settings.username == "local-user"
    assert settings.permissions == frozenset({"records:read"})

