from __future__ import annotations

from argon2 import PasswordHasher

from scripts import deployment_preflight


_ENV_KEYS = (
    "AEGISCORE_AUTH_USERNAME",
    "AEGISCORE_AUTH_PASSWORD_HASH",
    "AEGISCORE_AUTH_SESSION_TTL_SECONDS",
    "AEGISCORE_AUTH_PERMISSIONS",
    "AEGISCORE_AUTH_CONFIG_FILE",
    "AEGISCORE_API_HOST",
    "AEGISCORE_API_PORT",
    "AEGISCORE_CORS_ALLOWED_ORIGINS",
    "AEGISCORE_LOCAL_STORE_PATH",
    "AEGISCORE_AUTHORIZED_TARGETS_FILE",
)


def _clear_preflight_env(monkeypatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_preflight_does_not_create_missing_database(monkeypatch, tmp_path) -> None:
    _clear_preflight_env(monkeypatch)
    database = tmp_path / "state" / "records.sqlite3"
    database.parent.mkdir()
    monkeypatch.setenv("AEGISCORE_LOCAL_STORE_PATH", str(database))

    findings = deployment_preflight._database_findings()

    assert any(item.status == "WARNING" and "did not create it" in item.detail for item in findings)
    assert not database.exists()


def test_preflight_opens_existing_store_read_only(monkeypatch, tmp_path) -> None:
    _clear_preflight_env(monkeypatch)
    from aegiscore.local_persistence import LocalRecordStore

    database = tmp_path / "records.sqlite3"
    LocalRecordStore.create_or_open(database)
    before = database.stat().st_mtime_ns
    monkeypatch.setenv("AEGISCORE_LOCAL_STORE_PATH", str(database))

    findings = deployment_preflight._database_findings()

    assert any(item.status == "PASS" and "Existing database schema" in item.detail for item in findings)
    assert database.stat().st_mtime_ns == before


def test_preflight_redacts_auth_cors_target_and_frontend_values(monkeypatch, capsys, tmp_path) -> None:
    _clear_preflight_env(monkeypatch)
    marker = "DO_NOT_PRINT_SECRET_06_8_2"
    monkeypatch.setenv("AEGISCORE_AUTH_USERNAME", marker)
    monkeypatch.setenv("AEGISCORE_AUTH_PASSWORD_HASH", "not-a-real-hash")
    monkeypatch.setenv("AEGISCORE_CORS_ALLOWED_ORIGINS", f"https://user:{marker}@browser.example")
    monkeypatch.setenv("AEGISCORE_LOCAL_STORE_PATH", ":memory:")
    monkeypatch.setenv("AEGISCORE_AUTHORIZED_TARGETS_FILE", str(tmp_path / f"{marker}.toml"))

    exit_code = deployment_preflight.main(["--frontend-api-base-url", f"http://{marker}/"])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert marker not in output
    assert "PRECHECK ONLY" in output
    assert "Authoritative target verifier: [BLOCKED]" not in output
    assert "[BLOCKED] Authoritative target verifier" in output


def test_valid_auth_configuration_is_shape_checked_without_printing_values(monkeypatch, capsys) -> None:
    _clear_preflight_env(monkeypatch)
    username = "operator-private-name"
    password_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("private-test-password")
    monkeypatch.setenv("AEGISCORE_AUTH_USERNAME", username)
    monkeypatch.setenv("AEGISCORE_AUTH_PASSWORD_HASH", password_hash)

    findings = deployment_preflight._auth_findings()
    printed = capsys.readouterr().out

    assert findings[0].status == "PASS"
    assert username not in printed
    assert password_hash not in printed


def test_frontend_api_url_validation_is_loopback_only() -> None:
    assert deployment_preflight._frontend_api_finding("http://127.0.0.1:8000/").status == "PASS"
    assert deployment_preflight._frontend_api_finding("http://[::1]:8000/").status == "PASS"
    assert deployment_preflight._frontend_api_finding("https://example.com/").status == "BLOCKED"
    assert deployment_preflight._frontend_api_finding("http://user:pass@127.0.0.1/").status == "BLOCKED"


def test_configured_reference_does_not_pass_authoritative_verifier(monkeypatch, tmp_path) -> None:
    _clear_preflight_env(monkeypatch)
    target_file = tmp_path / "targets.toml"
    target_file.write_text(
        """[[targets]]
target_id = \"local-fixture\"
scheme = \"http\"
hostname = \"127.0.0.1\"
port = 8080
permitted_paths = [\"/\"]
authorization_ref = \"operator-reference-only\"
network_zone_id = \"local-zone\"
enabled = true
registration_version = \"v1\"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("AEGISCORE_AUTHORIZED_TARGETS_FILE", str(target_file))

    findings = deployment_preflight.collect_findings()

    registry = next(item for item in findings if item.name == "Authorized target registry")
    verifier = next(item for item in findings if item.name == "Authoritative target verifier")
    egress = next(item for item in findings if item.name == "OS-level egress isolation")
    assert registry.status == "WARNING"
    assert "does not establish approval authority" in registry.detail
    assert verifier.status == "BLOCKED"
    assert "not proof" in verifier.detail
    assert egress.status == "NOT VERIFIED"
