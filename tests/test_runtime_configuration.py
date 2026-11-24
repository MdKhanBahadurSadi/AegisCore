"""Runtime browser-origin and SQLite configuration boundary tests."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthConfigurationError, AuthSettings
from aegiscore.local_persistence import LocalRecordStore, LocalStoreUnavailableError
from tests.auth_helpers import (
    authenticated_client,
    create_bound_test_assessment,
    get_test_auth_settings,
)


def test_explicit_cors_origin_allows_preflight_without_bypassing_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AEGISCORE_CORS_ALLOWED_ORIGINS", raising=False)
    origin = "http://127.0.0.1:8080"
    app = create_app(auth_settings=get_test_auth_settings(), cors_allowed_origins=[origin])

    with TestClient(app) as client:
        preflight = client.options(
            "/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        protected_request = client.get("/assessments", headers={"Origin": origin})

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "content-type" in preflight.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in preflight.headers
    assert protected_request.status_code == 401
    assert protected_request.headers["access-control-allow-origin"] == origin


def test_cors_environment_allowlist_is_exact_and_rejects_other_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = "http://127.0.0.1:8080"
    denied = "http://localhost:8080"
    monkeypatch.setenv("AEGISCORE_CORS_ALLOWED_ORIGINS", allowed)
    app = create_app(auth_settings=get_test_auth_settings())

    with TestClient(app) as client:
        allowed_preflight = client.options(
            "/auth/login",
            headers={
                "Origin": allowed,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        disallowed_method = client.options(
            "/auth/login",
            headers={
                "Origin": allowed,
                "Access-Control-Request-Method": "DELETE",
            },
        )
        disallowed_header = client.options(
            "/auth/login",
            headers={
                "Origin": allowed,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-unapproved-header",
            },
        )
        denied_preflight = client.options(
            "/auth/login",
            headers={
                "Origin": denied,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        denied_actual_request = client.get("/assessments", headers={"Origin": denied})

    assert allowed_preflight.status_code == 200
    assert allowed_preflight.headers["access-control-allow-origin"] == allowed
    assert disallowed_method.status_code == 400
    assert disallowed_header.status_code == 400
    assert denied_preflight.status_code == 400
    assert "access-control-allow-origin" not in denied_preflight.headers
    assert denied_actual_request.status_code == 401
    assert "access-control-allow-origin" not in denied_actual_request.headers


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "http://example.test/path",
        "https://user:password@example.test",
        "https://example.test?next=/",
        "https://example.test#fragment",
        "https://example.test:99999",
        "https://example.test:",
    ],
)
def test_cors_configuration_rejects_non_origin_values(origin: str) -> None:
    with pytest.raises(ValueError):
        create_app(auth_settings=get_test_auth_settings(), cors_allowed_origins=[origin])


def test_cors_configuration_rejects_empty_and_duplicate_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AEGISCORE_CORS_ALLOWED_ORIGINS", " ")
    with pytest.raises(ValueError, match="must not be empty"):
        create_app(auth_settings=get_test_auth_settings())

    monkeypatch.setenv(
        "AEGISCORE_CORS_ALLOWED_ORIGINS",
        "https://example.test,https://EXAMPLE.test",
    )
    with pytest.raises(ValueError, match="duplicate"):
        create_app(auth_settings=get_test_auth_settings())


def test_cors_is_disabled_when_no_origin_allowlist_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AEGISCORE_CORS_ALLOWED_ORIGINS", raising=False)
    app = create_app(auth_settings=get_test_auth_settings())

    with TestClient(app) as client:
        preflight = client.options(
            "/auth/login",
            headers={
                "Origin": "http://127.0.0.1:8080",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


def test_sqlite_path_creates_private_parent_and_persists_assessment_after_reopen(
    tmp_path: Path,
) -> None:
    database = tmp_path / "private" / "runtime" / "records.sqlite3"
    store = LocalRecordStore.create_or_open(database)
    record = create_bound_test_assessment(store)

    reopened = LocalRecordStore.open_existing(database)
    assert reopened.get_assessment(record["assessment_id"]) == record
    assert database.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(database.stat().st_mode) == 0o600
        assert stat.S_IMODE(database.parent.stat().st_mode) & 0o077 == 0
        assert stat.S_IMODE(database.parent.parent.stat().st_mode) & 0o077 == 0

    app = create_app(local_store_path=database, auth_settings=get_test_auth_settings())
    with authenticated_client(app) as client:
        response = client.get(f"/assessments/{record['assessment_id']}")
    assert response.status_code == 200
    assert response.json()["assessment_id"] == record["assessment_id"]


def test_sqlite_assessment_survives_a_real_python_process_restart(tmp_path: Path) -> None:
    database = tmp_path / "restart" / "records.sqlite3"
    repository_root = Path(__file__).resolve().parents[1]
    child_environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AEGISCORE_")
    }
    create_script = """
import sys
from aegiscore.local_persistence import LocalRecordStore
from tests.auth_helpers import create_bound_test_assessment
store = LocalRecordStore.create_or_open(sys.argv[1])
record = create_bound_test_assessment(store)
print(record['assessment_id'])
"""
    read_script = """
import json
import sys
from aegiscore.local_persistence import LocalRecordStore
record = LocalRecordStore.open_existing(sys.argv[1]).get_assessment(sys.argv[2])
print(json.dumps(record, sort_keys=True))
"""

    created = subprocess.run(
        [sys.executable, "-c", create_script, str(database)],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
        env=child_environment,
    )
    assessment_id = created.stdout.strip()
    reopened = subprocess.run(
        [sys.executable, "-c", read_script, str(database), assessment_id],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
        env=child_environment,
    )

    persisted = json.loads(reopened.stdout)
    assert persisted["assessment_id"] == assessment_id
    assert persisted["status"] == "created"
    assert persisted["target_id"] == "test-loopback-target"


def test_configured_invalid_database_path_aborts_startup_without_fallback(
    tmp_path: Path,
) -> None:
    database_directory = tmp_path / "is-a-directory.sqlite3"
    database_directory.mkdir()

    with pytest.raises(RuntimeError, match="Configured local persistence could not be initialized") as error:
        create_app(local_store_path=database_directory, auth_settings=get_test_auth_settings())

    assert str(tmp_path) not in str(error.value)
    with pytest.raises(LocalStoreUnavailableError):
        LocalRecordStore.create_or_open(":memory:")


def test_blank_configured_database_environment_aborts_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AEGISCORE_LOCAL_STORE_PATH", " ")

    with pytest.raises(RuntimeError, match="Configured local persistence path is invalid"):
        create_app(auth_settings=get_test_auth_settings())


def test_explicit_missing_auth_file_aborts_startup_without_disabling_auth_silently(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in (
        "AEGISCORE_AUTH_USERNAME",
        "AEGISCORE_AUTH_PASSWORD_HASH",
        "AEGISCORE_AUTH_SESSION_TTL_SECONDS",
        "AEGISCORE_AUTH_PERMISSIONS",
    ):
        monkeypatch.delenv(name, raising=False)
    missing_file = tmp_path / "missing-auth.toml"
    monkeypatch.setenv("AEGISCORE_AUTH_CONFIG_FILE", str(missing_file))

    with pytest.raises(AuthConfigurationError, match="Configured authentication file is unavailable"):
        AuthSettings.load()
    with pytest.raises(AuthConfigurationError, match="Configured authentication file is unavailable"):
        create_app()
