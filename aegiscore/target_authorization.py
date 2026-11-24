"""Trusted, exact loopback target authorization for passive assessment execution."""

from __future__ import annotations

import ipaddress
import os
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from aegiscore.safety import ApprovedTargetRegistration, ConfigurationError, TargetRegistry


AUTHORIZED_TARGETS_ENV = "AEGISCORE_AUTHORIZED_TARGETS_FILE"


class TargetAuthorizationError(ValueError):
    """Raised when a request cannot be bound to one trusted loopback registration."""


def _loopback_address(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if not isinstance(hostname, str) or "%" in hostname:
        raise TargetAuthorizationError("authorized target must use a numeric loopback address")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        raise TargetAuthorizationError("authorized target must use a numeric loopback address") from None
    if not address.is_loopback or address.compressed != hostname:
        raise TargetAuthorizationError("authorized target must use a canonical numeric loopback address")
    return address


def validate_target_registry(registry: TargetRegistry) -> None:
    if not isinstance(registry, TargetRegistry):
        raise TargetAuthorizationError("authorized target registry is unavailable")
    for registration in registry.registrations:
        _loopback_address(registration.hostname)


def canonicalize_registered_endpoint(
    target_url: str,
    registration: ApprovedTargetRegistration,
) -> str:
    """Match an input URL to an enabled target's exact authorized origin and path."""
    try:
        if not isinstance(target_url, str) or target_url != target_url.strip():
            raise ValueError
        parsed = urlsplit(target_url)
        hostname = parsed.hostname
        supplied_port = parsed.port
    except (TypeError, ValueError):
        raise TargetAuthorizationError("target endpoint is malformed or unauthorized") from None

    if (
        not registration.enabled
        or not hostname
        or "@" in parsed.netloc
        or "#" in target_url
        or "?" in target_url
        or parsed.query
        or parsed.fragment
        or "%" in hostname
        or "\\" in parsed.path
    ):
        raise TargetAuthorizationError("target endpoint is malformed or unauthorized")

    try:
        address = _loopback_address(hostname)
        registered_address = _loopback_address(registration.hostname)
    except TargetAuthorizationError:
        raise TargetAuthorizationError("target endpoint is unauthorized") from None

    port = supplied_port if supplied_port is not None else (80 if parsed.scheme == "http" else 443)
    path = parsed.path or "/"
    if (
        parsed.scheme != registration.scheme
        or address != registered_address
        or port != registration.port
        or path not in registration.permitted_paths
    ):
        raise TargetAuthorizationError("target endpoint does not match an authorized target endpoint")

    host = address.compressed
    if address.version == 6:
        host = f"[{host}]"
    return f"{registration.scheme}://{host}:{registration.port}{path}"


def resolve_authorized_endpoint(
    registry: TargetRegistry | None,
    target_url: str,
) -> tuple[ApprovedTargetRegistration, str]:
    """Resolve an input URL to exactly one trusted registration and canonical endpoint."""
    if registry is None:
        raise TargetAuthorizationError("authorized target registry is not configured")
    validate_target_registry(registry)
    matches: list[tuple[ApprovedTargetRegistration, str]] = []
    for registration in registry.registrations:
        try:
            canonical_endpoint = canonicalize_registered_endpoint(target_url, registration)
        except TargetAuthorizationError:
            continue
        matches.append((registration, canonical_endpoint))
    if len(matches) != 1:
        raise TargetAuthorizationError("target endpoint is not uniquely authorized")
    return matches[0]


def load_target_registry(path: str | os.PathLike[str] | None = None) -> TargetRegistry | None:
    """Load operator-approved loopback registrations from a TOML configuration file."""
    configured_path = path
    if configured_path is None:
        configured_path = os.environ.get(AUTHORIZED_TARGETS_ENV)
    if configured_path is None or not os.fspath(configured_path).strip():
        return None

    try:
        with Path(configured_path).expanduser().open("rb") as config_file:
            raw: Any = tomllib.load(config_file)
        entries = raw.get("targets")
        if not isinstance(entries, list) or not entries:
            raise TargetAuthorizationError("authorized target configuration has no targets")
        allowed_keys = {
            "target_id", "scheme", "hostname", "port", "permitted_paths",
            "authorization_ref", "network_zone_id", "enabled", "registration_version",
        }
        registrations: list[ApprovedTargetRegistration] = []
        for item in entries:
            if not isinstance(item, dict) or set(item) != allowed_keys:
                raise TargetAuthorizationError("authorized target configuration has an invalid entry")
            if not isinstance(item["permitted_paths"], list):
                raise TargetAuthorizationError("authorized target paths are invalid")
            registrations.append(ApprovedTargetRegistration(
                target_id=item["target_id"],
                scheme=item["scheme"],
                hostname=item["hostname"],
                port=item["port"],
                permitted_paths=tuple(item["permitted_paths"]),
                authorization_ref=item["authorization_ref"],
                network_zone_id=item["network_zone_id"],
                enabled=item["enabled"],
                registration_version=item["registration_version"],
            ))
        registry = TargetRegistry(tuple(registrations))
        validate_target_registry(registry)
        return registry
    except TargetAuthorizationError:
        raise
    except (OSError, tomllib.TOMLDecodeError, ConfigurationError, TypeError, ValueError):
        raise TargetAuthorizationError("authorized target configuration is invalid or unavailable") from None
