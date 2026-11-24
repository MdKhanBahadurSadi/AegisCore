#!/usr/bin/env python3
"""Read-only deployment preflight for AEGISCORE.

This command validates local configuration shape and existing SQLite state. It
does not create files, start the API, authenticate, verify target approval,
open network connections, or establish deployment acceptance.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import platform
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class Finding:
    status: str
    name: str
    detail: str


_KNOWN_PERMISSIONS = {
    "records:read",
    "evidence:read",
    "assessments:create",
    "assessments:execute",
}
_DEFAULT_PERMISSIONS = _KNOWN_PERMISSIONS
_AUTH_ENV_KEYS = (
    "AEGISCORE_AUTH_USERNAME",
    "AEGISCORE_AUTH_PASSWORD_HASH",
    "AEGISCORE_AUTH_SESSION_TTL_SECONDS",
    "AEGISCORE_AUTH_PERMISSIONS",
)


def _auth_config_path() -> Path:
    configured = os.environ.get("AEGISCORE_AUTH_CONFIG_FILE")
    if configured is not None:
        if not configured.strip():
            raise ValueError
        return Path(configured).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AEGISCORE" / "auth.toml"
    root = os.environ.get("XDG_CONFIG_HOME")
    return (Path(root) if root else Path.home() / ".config") / "aegiscore" / "auth.toml"


def _validate_auth_values(username: object, password_hash: object, ttl: object, permissions: object) -> None:
    if not isinstance(username, str) or not username or username.strip() != username or len(username) > 128:
        raise ValueError
    if not isinstance(password_hash, str) or not password_hash.startswith("$argon2id$"):
        raise ValueError
    try:
        extract_parameters(password_hash)
    except (InvalidHashError, ValueError, TypeError):
        raise ValueError from None
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 86400:
        raise ValueError
    if not isinstance(permissions, (set, frozenset)) or not permissions or not permissions <= _KNOWN_PERMISSIONS:
        raise ValueError


def _auth_findings() -> list[Finding]:
    env_values = [os.environ.get(key) for key in _AUTH_ENV_KEYS]
    if any(value is not None for value in env_values):
        username = os.environ.get("AEGISCORE_AUTH_USERNAME")
        password_hash = os.environ.get("AEGISCORE_AUTH_PASSWORD_HASH")
        ttl_text = os.environ.get("AEGISCORE_AUTH_SESSION_TTL_SECONDS")
        permissions_text = os.environ.get("AEGISCORE_AUTH_PERMISSIONS")
        try:
            ttl = int(ttl_text) if ttl_text is not None else 1800
            permissions = (
                frozenset(part.strip() for part in permissions_text.split(",") if part.strip())
                if permissions_text is not None
                else _DEFAULT_PERMISSIONS
            )
            _validate_auth_values(username, password_hash, ttl, permissions)
        except (ValueError, TypeError):
            return [Finding("BLOCKED", "API authentication", "Authentication configuration is incomplete or invalid; values were redacted.")]
        return [Finding("PASS", "API authentication", "Credential configuration is structurally valid; login has not been exercised and values were redacted.")]

    try:
        path = _auth_config_path()
        if not path.is_file():
            return [Finding("BLOCKED", "API authentication", "No authentication configuration is available.")]
        if os.name != "nt" and path.stat().st_mode & 0o077:
            return [Finding("BLOCKED", "API authentication", "Authentication file permissions allow group or other access.")]
        if os.name != "nt" and path.parent.stat().st_mode & 0o022:
            return [Finding("BLOCKED", "Authentication directory permissions", "Authentication directory is writable by group or other identities.")]
        with path.open("rb") as stream:
            config = tomllib.load(stream)
        auth = config.get("auth")
        if not isinstance(auth, dict):
            raise ValueError
        username = auth.get("username")
        password_hash = auth.get("password_hash")
        ttl = auth.get("session_ttl_seconds", 1800)
        permissions_value = auth.get("permissions", sorted(_DEFAULT_PERMISSIONS))
        if not isinstance(permissions_value, list) or any(not isinstance(item, str) for item in permissions_value):
            raise ValueError
        _validate_auth_values(username, password_hash, ttl, frozenset(permissions_value))
        findings = [Finding("PASS", "API authentication", "Authentication file is structurally valid; login has not been exercised and values were redacted.")]
        if os.name == "nt":
            findings.append(Finding("NOT VERIFIED", "Authentication file ACL", "Windows effective ACLs are not validated by this preflight."))
        return findings
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
        return [Finding("BLOCKED", "API authentication", "Authentication configuration is unavailable or invalid; values were redacted.")]


def _api_listener_finding() -> Finding:
    host = os.environ.get("AEGISCORE_API_HOST", "127.0.0.1")
    try:
        if host == "localhost":
            pass
        elif not ipaddress.ip_address(host).is_loopback:
            raise ValueError
        port = int(os.environ.get("AEGISCORE_API_PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, TypeError):
        return Finding("BLOCKED", "API listener configuration", "API host or port is invalid or not loopback-only.")
    return Finding("PASS", "API listener configuration", "Configured host is loopback-only and port is in range; listener state was not probed.")


def _cors_findings() -> list[Finding]:
    raw = os.environ.get("AEGISCORE_CORS_ALLOWED_ORIGINS")
    if raw is None:
        return [Finding("WARNING", "Browser origin allowlist", "No cross-origin browser origin is configured; same-origin use may still apply.")]
    if not raw.strip():
        return [Finding("BLOCKED", "Browser origin allowlist", "Configured browser origin allowlist is empty.")]
    try:
        normalized: list[str] = []
        for origin in raw.split(","):
            if not origin or origin.strip() != origin or "*" in origin:
                raise ValueError
            parsed = urlsplit(origin)
            port = parsed.port
            hostname = parsed.hostname
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.netloc
                or not hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.netloc.endswith(":")
                or "%" in parsed.netloc
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise ValueError
            host = hostname.encode("idna").decode("ascii").lower()
            if host.endswith("."):
                raise ValueError
            try:
                ipaddress.ip_address(host)
            except ValueError:
                labels = host.split(".")
                if any(
                    not label
                    or len(label) > 63
                    or label.startswith("-")
                    or label.endswith("-")
                    or any(not (char.isascii() and (char.isalnum() or char == "-")) for char in label)
                    for label in labels
                ):
                    raise ValueError
            scheme = parsed.scheme.lower()
            display_host = f"[{host}]" if ":" in host else host
            if port is not None and port != (80 if scheme == "http" else 443):
                display_host = f"{display_host}:{port}"
            normalized.append(f"{scheme}://{display_host}")
        if len(set(normalized)) != len(normalized):
            raise ValueError
    except (UnicodeError, AttributeError, ValueError):
        return [Finding("BLOCKED", "Browser origin allowlist", "Browser origin allowlist is malformed; configured values were redacted.")]
    return [Finding("PASS", "Browser origin allowlist", "One or more exact origins are configured; browser reachability and intended-origin matching were not tested.")]


def _frontend_api_finding(value: str | None) -> Finding:
    if value is None:
        return Finding("NOT VERIFIED", "Flutter API base URL", "Compile-time AEGIS_API_BASE_URL was not supplied to this preflight.")
    try:
        parsed = urlsplit(value)
        if (
            not value
            or value.strip() != value
            or parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
        host = parsed.hostname
        if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
    except (ValueError, TypeError):
        return Finding("BLOCKED", "Flutter API base URL", "Supplied API base URL is malformed or not loopback-only; value was redacted.")
    return Finding("PASS", "Flutter API base URL", "Supplied API base URL is structurally loopback-only; no browser request was made.")


def _database_findings() -> list[Finding]:
    raw_path = os.environ.get("AEGISCORE_LOCAL_STORE_PATH")
    if raw_path is None or not raw_path.strip() or raw_path == ":memory:":
        return [Finding("BLOCKED", "Persistent SQLite store", "A persistent local SQLite path is not configured.")]
    try:
        path = Path(raw_path).expanduser().resolve(strict=False)
        if not path.parent.is_dir():
            return [Finding("BLOCKED", "Persistent SQLite store", "Database parent directory is unavailable; path was redacted.")]
        if not os.access(path.parent, os.W_OK | os.X_OK):
            return [Finding("BLOCKED", "Persistent SQLite store", "Database parent directory is not writable by this process; path was redacted.")]
        if not path.exists():
            findings = [Finding("WARNING", "Persistent SQLite store", "Database is absent; preflight did not create it, so persistence and restart recovery are unverified.")]
        else:
            if not path.is_file() or not os.access(path, os.R_OK | os.W_OK):
                return [Finding("BLOCKED", "Persistent SQLite store", "Database file is not a readable and writable regular file; path was redacted.")]
            if os.name != "nt" and path.stat().st_mode & 0o077:
                return [Finding("BLOCKED", "Persistent SQLite store", "Database file permissions allow group or other access.")]
            from aegiscore.local_persistence import LocalRecordStore

            LocalRecordStore.open_existing(path)
            findings = [Finding("PASS", "Persistent SQLite store", "Existing database schema is readable and writable by this process; record persistence and fresh-process recovery were not exercised.")]
        if os.name == "nt":
            findings.append(Finding("NOT VERIFIED", "SQLite and parent ACLs", "Windows effective ACLs are not validated by this preflight."))
        else:
            try:
                if path.parent.stat().st_mode & 0o022:
                    findings.append(Finding("BLOCKED", "SQLite parent permissions", "Database parent is writable by group or other identities."))
                else:
                    findings.append(Finding("PASS", "SQLite parent permissions", "Database parent is not group/world writable."))
            except OSError:
                findings.append(Finding("NOT VERIFIED", "SQLite parent permissions", "Database parent permissions could not be inspected."))
        return findings
    except Exception:
        # Avoid exposing local paths, SQLite contents, or implementation exceptions.
        return [Finding("BLOCKED", "Persistent SQLite store", "Database is unavailable or has an invalid schema; path and exception details were redacted.")]


def _target_findings() -> list[Finding]:
    path = os.environ.get("AEGISCORE_AUTHORIZED_TARGETS_FILE")
    if path is None or not path.strip():
        return [Finding("BLOCKED", "Authorized target registry", "No target registry is configured.")]
    try:
        from aegiscore.target_authorization import load_target_registry

        registry = load_target_registry(path)
        if registry is None:
            raise ValueError
        if os.name == "nt":
            acl = Finding("NOT VERIFIED", "Target registry ACL", "Windows effective ACLs are not validated by this preflight.")
        elif Path(path).expanduser().stat().st_mode & 0o022:
            acl = Finding("BLOCKED", "Target registry permissions", "Target registry is writable by group or other identities.")
        else:
            acl = Finding("PASS", "Target registry permissions", "Target registry is not group/world writable.")
        return [
            Finding("WARNING", "Authorized target registry", f"Registry syntax is valid for {len(registry.registrations)} registration(s); this does not establish approval authority or trust."),
            acl,
        ]
    except Exception:
        return [Finding("BLOCKED", "Authorized target registry", "Target registry is unavailable or invalid; path and contents were redacted.")]


def collect_findings(frontend_api_base_url: str | None = None) -> list[Finding]:
    """Collect read-only local checks; never claim full acceptance."""
    findings: list[Finding] = []
    findings.extend(_auth_findings())
    findings.append(_api_listener_finding())
    findings.extend(_cors_findings())
    findings.append(_frontend_api_finding(frontend_api_base_url))
    findings.extend(_database_findings())
    findings.extend(_target_findings())
    findings.append(Finding("BLOCKED", "Authoritative target verifier", "No production verifier/issuer integration is configured; configured reference strings are not proof of authorization."))
    findings.append(Finding("NOT VERIFIED", "OS-level egress isolation", f"Preflight does not inspect firewall enforcement; current host platform is {platform.system()} and Debian 13 live verification remains required."))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-api-base-url",
        help="optional Flutter compile-time API base URL to validate (the value is never printed)",
    )
    args = parser.parse_args(argv)
    findings = collect_findings(args.frontend_api_base_url)
    for finding in findings:
        print(f"[{finding.status}] {finding.name}: {finding.detail}")
    counts = {status: sum(item.status == status for item in findings) for status in ("BLOCKED", "WARNING", "NOT VERIFIED", "PASS")}
    print(
        "PRECHECK ONLY - not release acceptance. "
        + ", ".join(f"{status}={count}" for status, count in counts.items())
    )
    if counts["BLOCKED"]:
        return 2
    if counts["WARNING"] or counts["NOT VERIFIED"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
