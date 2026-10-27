"""In-memory, deterministic contracts for target and request policy.

This module does not perform HTTP, DNS, shell, or other external I/O. A policy
engine instance represents one run and consumes its configured request budget
when it issues an allow decision. A future executor must re-check immediately
before dispatch and enforce the returned timeout at the transport boundary.
"""

from __future__ import annotations

import ipaddress
import math
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping
from urllib.parse import quote, unquote, urljoin, urlsplit


class ConfigurationError(ValueError):
    """Raised when security policy configuration is absent or inconsistent."""


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class PolicyReason(str, Enum):
    ALLOWED = "allowed"
    MISSING_CONFIGURATION = "missing_configuration"
    INVALID_CONFIGURATION = "invalid_configuration"
    EMERGENCY_STOP = "emergency_stop"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN_TARGET = "unknown_target"
    TARGET_NOT_ENABLED = "target_not_enabled"
    TARGET_OUT_OF_SCOPE = "target_out_of_scope"
    CASE_PROFILE_NOT_PERMITTED = "case_profile_not_permitted"
    INVALID_PATH = "invalid_path"
    PATH_NOT_PERMITTED = "path_not_permitted"
    REQUEST_BUDGET_EXHAUSTED = "request_budget_exhausted"
    REDIRECT_BUDGET_EXHAUSTED = "redirect_budget_exhausted"
    EXECUTION_TIMEOUT = "execution_timeout"
    CLOCK_FAILURE = "clock_failure"
    REDIRECT_INVALID = "redirect_invalid"
    REDIRECT_ORIGIN_MISMATCH = "redirect_origin_mismatch"
    NO_PRIOR_ALLOW = "no_prior_allow"
    WORKFLOW_DENIED = "workflow_denied"
    INVALID_OPERATION = "invalid_operation"
    OPERATION_ID_REUSED = "operation_id_reused"
    PERMIT_INVALID = "permit_invalid"
    PERMIT_EXPIRED = "permit_expired"
    PERMIT_REPLAYED = "permit_replayed"
    TARGET_REVOKED = "target_revoked"
    RUN_CANCELLED = "run_cancelled"
    TRANSPORT_FAILURE = "transport_failure"


_TARGET_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
_ENCODED_SEPARATOR = re.compile(r"%(?:2f|5c)", re.IGNORECASE)
_NESTED_DOT_OR_SEPARATOR = re.compile(r"%(?:2e|2f|5c)", re.IGNORECASE)
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_READ_ONLY_METHODS = frozenset({"GET", "HEAD"})
_OPERATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PARAMETER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.~-]{0,63}$")
_HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_FORBIDDEN_HEADERS = frozenset(
    {
        "authorization",
        "connection",
        "content-length",
        "cookie",
        "host",
        "proxy-authorization",
        "proxy-connection",
        "set-cookie",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
# Contract ceilings bound the in-memory request representation. They are not
# proposal requirements, approved deployment limits, or transport guarantees.
_CONTRACT_MAX_PARAMETERS = 32
_CONTRACT_MAX_QUERY_BYTES = 4096
_CONTRACT_MAX_HEADERS = 32
_CONTRACT_MAX_HEADER_BYTES = 8192
_CONTRACT_MAX_BODY_BYTES = 65536
_POLICY_ISSUER = object()


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ConfigurationError(f"{name} must be non-empty trimmed text")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ConfigurationError(f"{name} contains a control character")
    return value


def _validate_target_id(value: object, *, config: bool) -> bool:
    if type(value) is not str or _TARGET_ID.fullmatch(value) is None:
        if config:
            raise ConfigurationError("target_id has an invalid format")
        return False
    return True


def _validate_hostname(value: object, *, config: bool) -> bool:
    def invalid() -> bool:
        if config:
            raise ConfigurationError("hostname is invalid or non-canonical")
        return False

    if type(value) is not str or not value or value != value.strip():
        return invalid()
    if value != value.lower() or value.endswith(".") or "%" in value:
        return invalid()
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        if len(value) > 253 or not value.isascii():
            return invalid()
        labels = value.split(".")
        if any(_DNS_LABEL.fullmatch(label) is None for label in labels):
            return invalid()
        return True
    if address.is_loopback:
        return True
    local_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("fc00::/7"),
    )
    if any(address.version == network.version and address in network for network in local_networks):
        return True
    return invalid()


def _canonical_path(value: object, *, config: bool) -> str | None:
    def invalid() -> None:
        if config:
            raise ConfigurationError("permitted path is malformed or ambiguous")

    if type(value) is not str or not value or value != value.strip():
        invalid()
        return None
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        invalid()
        return None
    if "\\" in value or "?" in value or "#" in value or _BAD_PERCENT.search(value):
        invalid()
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        invalid()
        return None
    if (
        parts.scheme
        or parts.netloc
        or parts.fragment
        or not parts.path.startswith("/")
        or "//" in parts.path
        or "?" in value
        or "#" in value
    ):
        invalid()
        return None
    if _ENCODED_SEPARATOR.search(parts.path):
        invalid()
        return None
    try:
        decoded = unquote(parts.path, errors="strict")
    except (UnicodeDecodeError, ValueError):
        invalid()
        return None
    if "\\" in decoded or any(ord(character) < 0x20 or ord(character) == 0x7F for character in decoded):
        invalid()
        return None
    segments = decoded.split("/")
    if any(segment in {".", ".."} for segment in segments):
        invalid()
        return None
    if _NESTED_DOT_OR_SEPARATOR.search(decoded):
        invalid()
        return None
    return decoded


def _positive_finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ConfigurationError(f"{name} must be a positive finite number")
    return number


def _valid_port(value: object, name: str = "port") -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ConfigurationError(f"{name} must be an integer from 1 through 65535")
    return True


@dataclass(frozen=True, slots=True)
class ApprovedTargetRegistration:
    """Trusted, operator-supplied registration for one exact target origin."""

    target_id: str
    scheme: str
    hostname: str
    port: int
    permitted_paths: tuple[str, ...]
    authorization_ref: str
    network_zone_id: str
    enabled: bool
    registration_version: str

    def __post_init__(self) -> None:
        _validate_target_id(self.target_id, config=True)
        if not isinstance(self.scheme, str) or self.scheme not in _ALLOWED_SCHEMES:
            raise ConfigurationError("scheme must be exactly 'http' or 'https'")
        _validate_hostname(self.hostname, config=True)
        _valid_port(self.port)
        _require_text(self.authorization_ref, "authorization_ref")
        _require_text(self.network_zone_id, "network_zone_id")
        if not isinstance(self.registration_version, str) or _VERSION.fullmatch(self.registration_version) is None:
            raise ConfigurationError("registration_version has an invalid format")
        if not isinstance(self.enabled, bool):
            raise ConfigurationError("enabled must be an explicit boolean")
        if not isinstance(self.permitted_paths, tuple) or not self.permitted_paths:
            raise ConfigurationError("permitted_paths must be a non-empty tuple")
        canonical = tuple(_canonical_path(path, config=True) for path in self.permitted_paths)
        if len(set(canonical)) != len(canonical):
            raise ConfigurationError("permitted_paths must not contain duplicates")
        object.__setattr__(self, "permitted_paths", canonical)


@dataclass(frozen=True, slots=True)
class TargetRegistry:
    """Immutable registry loaded from a trusted configuration source."""

    registrations: tuple[ApprovedTargetRegistration, ...]
    _by_id: Mapping[str, ApprovedTargetRegistration] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.registrations, tuple) or not self.registrations:
            raise ConfigurationError("target registry must be a non-empty tuple")
        if any(not isinstance(item, ApprovedTargetRegistration) for item in self.registrations):
            raise ConfigurationError("target registry contains an invalid registration")
        by_id = {item.target_id: item for item in self.registrations}
        if len(by_id) != len(self.registrations):
            raise ConfigurationError("target registry contains duplicate target IDs")
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))

    def get(self, target_id: str) -> ApprovedTargetRegistration | None:
        return self._by_id.get(target_id)


@dataclass(frozen=True, slots=True)
class ScopePolicy:
    """Exact policy allowlists; path sets are per registered target."""

    policy_id: str
    version: str
    target_ids: frozenset[str]
    allowed_schemes: frozenset[str]
    allowed_hostnames: frozenset[str]
    allowed_ports: frozenset[int]
    permitted_paths_by_target: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        _require_text(self.policy_id, "policy_id")
        _require_text(self.version, "policy version")
        if not isinstance(self.target_ids, frozenset) or not self.target_ids:
            raise ConfigurationError("target_ids must be a non-empty frozenset")
        for target_id in self.target_ids:
            _validate_target_id(target_id, config=True)
        if not isinstance(self.allowed_schemes, frozenset) or not self.allowed_schemes:
            raise ConfigurationError("allowed_schemes must be a non-empty frozenset")
        if not self.allowed_schemes <= _ALLOWED_SCHEMES:
            raise ConfigurationError("allowed_schemes contains a forbidden scheme")
        if not isinstance(self.allowed_hostnames, frozenset) or not self.allowed_hostnames:
            raise ConfigurationError("allowed_hostnames must be a non-empty frozenset")
        for hostname in self.allowed_hostnames:
            _validate_hostname(hostname, config=True)
        if not isinstance(self.allowed_ports, frozenset) or not self.allowed_ports:
            raise ConfigurationError("allowed_ports must be a non-empty frozenset")
        for port in self.allowed_ports:
            _valid_port(port, "allowed port")
        if not isinstance(self.permitted_paths_by_target, Mapping):
            raise ConfigurationError("permitted_paths_by_target must be a mapping")
        if set(self.permitted_paths_by_target) != set(self.target_ids):
            raise ConfigurationError("every scoped target must have an explicit path set")
        paths: dict[str, frozenset[str]] = {}
        for target_id, target_paths in self.permitted_paths_by_target.items():
            if target_id not in self.target_ids or not isinstance(target_paths, (tuple, frozenset, set)) or not target_paths:
                raise ConfigurationError("per-target path set is missing or invalid")
            canonical = frozenset(_canonical_path(path, config=True) for path in target_paths)
            paths[target_id] = canonical
        object.__setattr__(self, "permitted_paths_by_target", MappingProxyType(paths))


@dataclass(frozen=True, slots=True)
class RequestBudget:
    """Per-run caps. Values are required; no permissive defaults are supplied."""

    max_requests: int
    max_redirects: int

    def __post_init__(self) -> None:
        if isinstance(self.max_requests, bool) or not isinstance(self.max_requests, int) or self.max_requests <= 0:
            raise ConfigurationError("max_requests must be a positive integer")
        if isinstance(self.max_redirects, bool) or not isinstance(self.max_redirects, int) or self.max_redirects < 0:
            raise ConfigurationError("max_redirects must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    """Explicit per-request timeout and overall run deadline, in seconds."""

    per_request_seconds: float
    max_run_seconds: float

    def __post_init__(self) -> None:
        request_timeout = _positive_finite(self.per_request_seconds, "per_request_seconds")
        run_timeout = _positive_finite(self.max_run_seconds, "max_run_seconds")
        if request_timeout > run_timeout:
            raise ConfigurationError("per-request timeout cannot exceed max run timeout")
        object.__setattr__(self, "per_request_seconds", request_timeout)
        object.__setattr__(self, "max_run_seconds", run_timeout)


@dataclass(frozen=True, slots=True)
class OperationDataLimits:
    """Versioned bounds for one canonical operation's in-memory data."""

    version: str
    max_parameters: int
    max_query_bytes: int
    max_headers: int
    max_header_bytes: int
    max_body_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or _VERSION.fullmatch(self.version) is None:
            raise ConfigurationError("operation data limit version has an invalid format")
        ceilings = {
            "max_parameters": _CONTRACT_MAX_PARAMETERS,
            "max_query_bytes": _CONTRACT_MAX_QUERY_BYTES,
            "max_headers": _CONTRACT_MAX_HEADERS,
            "max_header_bytes": _CONTRACT_MAX_HEADER_BYTES,
            "max_body_bytes": _CONTRACT_MAX_BODY_BYTES,
        }
        for name, ceiling in ceilings.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= ceiling:
                raise ConfigurationError(f"{name} must be an integer from 0 through {ceiling}")


@dataclass(frozen=True, slots=True)
class CaseProfilePolicy:
    """Trusted in-memory allowlist binding one synthetic/reviewed case to a profile."""

    target_id: str
    case_id: str
    profile_id: str
    version: str
    allowed_methods: frozenset[str]
    permitted_paths: frozenset[str]
    permitted_parameter_names: frozenset[str]
    permitted_header_names: frozenset[str]
    allow_body: bool

    def __post_init__(self) -> None:
        _validate_target_id(self.target_id, config=True)
        for name, value in (("case_id", self.case_id), ("profile_id", self.profile_id)):
            if not isinstance(value, str) or _OPERATION_ID.fullmatch(value) is None:
                raise ConfigurationError(f"{name} has an invalid format")
        if not isinstance(self.version, str) or _VERSION.fullmatch(self.version) is None:
            raise ConfigurationError("case profile version has an invalid format")
        if not isinstance(self.allowed_methods, frozenset) or not self.allowed_methods:
            raise ConfigurationError("allowed_methods must be a non-empty frozenset")
        if not self.allowed_methods <= _READ_ONLY_METHODS:
            raise ConfigurationError("case profile contains a method outside the existing GET/HEAD policy")
        if not isinstance(self.permitted_paths, frozenset) or not self.permitted_paths:
            raise ConfigurationError("case profile permitted_paths must be a non-empty frozenset")
        canonical_paths = frozenset(_canonical_path(path, config=True) for path in self.permitted_paths)
        if len(canonical_paths) != len(self.permitted_paths):
            raise ConfigurationError("case profile paths must be unique after canonicalization")
        object.__setattr__(self, "permitted_paths", canonical_paths)
        if not isinstance(self.permitted_parameter_names, frozenset):
            raise ConfigurationError("permitted_parameter_names must be a frozenset")
        for name in self.permitted_parameter_names:
            if not isinstance(name, str) or _PARAMETER_NAME.fullmatch(name) is None:
                raise ConfigurationError("case profile has an invalid query parameter name")
        if not isinstance(self.permitted_header_names, frozenset):
            raise ConfigurationError("permitted_header_names must be a frozenset")
        normalized_headers: set[str] = set()
        for name in self.permitted_header_names:
            if not isinstance(name, str) or not name.isascii() or _HEADER_NAME.fullmatch(name) is None:
                raise ConfigurationError("case profile has an invalid header name")
            normalized = name.lower()
            if normalized in _FORBIDDEN_HEADERS or normalized in normalized_headers:
                raise ConfigurationError("case profile contains a forbidden or duplicate header name")
            normalized_headers.add(normalized)
        object.__setattr__(self, "permitted_header_names", frozenset(normalized_headers))
        if not isinstance(self.allow_body, bool):
            raise ConfigurationError("allow_body must be an explicit boolean")


class EmergencyStop:
    """Irreversible, thread-safe stop latch; there is intentionally no reset API."""

    def __init__(self, active: bool) -> None:
        if not isinstance(active, bool):
            raise ConfigurationError("emergency stop state must be an explicit boolean")
        self._lock = threading.Lock()
        self._active = active

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    def trigger(self) -> None:
        with self._lock:
            self._active = True


@dataclass(frozen=True, slots=True)
class SafetyConfiguration:
    registry: TargetRegistry
    scope: ScopePolicy
    request_budget: RequestBudget
    timeouts: TimeoutPolicy
    emergency_stop: EmergencyStop
    case_profiles: tuple[CaseProfilePolicy, ...] | None = None
    operation_data_limits: OperationDataLimits | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.registry, TargetRegistry):
            raise ConfigurationError("registry is missing or invalid")
        if not isinstance(self.scope, ScopePolicy):
            raise ConfigurationError("scope policy is missing or invalid")
        if not isinstance(self.request_budget, RequestBudget):
            raise ConfigurationError("request budget is missing or invalid")
        if not isinstance(self.timeouts, TimeoutPolicy):
            raise ConfigurationError("timeout policy is missing or invalid")
        if not isinstance(self.emergency_stop, EmergencyStop):
            raise ConfigurationError("emergency stop state is missing or invalid")
        if (self.case_profiles is None) != (self.operation_data_limits is None):
            raise ConfigurationError("case profile policies and operation data limits must be configured together")
        if self.case_profiles is not None:
            if not isinstance(self.case_profiles, tuple) or not self.case_profiles:
                raise ConfigurationError("case_profiles must be a non-empty tuple")
            if not isinstance(self.operation_data_limits, OperationDataLimits):
                raise ConfigurationError("operation data limits are missing or invalid")
            if any(not isinstance(item, CaseProfilePolicy) for item in self.case_profiles):
                raise ConfigurationError("case_profiles contains an invalid policy")
            profile_keys = [(item.target_id, item.case_id, item.profile_id) for item in self.case_profiles]
            if len(set(profile_keys)) != len(profile_keys):
                raise ConfigurationError("case_profiles contains duplicate target/case/profile bindings")

        registrations = {item.target_id: item for item in self.registry.registrations}
        if not self.scope.target_ids <= registrations.keys():
            raise ConfigurationError("scope references an unregistered target ID")
        scoped = [registrations[target_id] for target_id in self.scope.target_ids]
        if self.scope.allowed_schemes != frozenset(item.scheme for item in scoped):
            raise ConfigurationError("scheme allowlist does not exactly match scoped registrations")
        if self.scope.allowed_hostnames != frozenset(item.hostname for item in scoped):
            raise ConfigurationError("hostname allowlist does not exactly match scoped registrations")
        if self.scope.allowed_ports != frozenset(item.port for item in scoped):
            raise ConfigurationError("port allowlist does not exactly match scoped registrations")
        for item in scoped:
            policy_paths = self.scope.permitted_paths_by_target[item.target_id]
            if not policy_paths or not policy_paths <= frozenset(item.permitted_paths):
                raise ConfigurationError("scope paths exceed registered target paths")
        if self.case_profiles is not None:
            for profile in self.case_profiles:
                registration = registrations.get(profile.target_id)
                if registration is None or profile.target_id not in self.scope.target_ids:
                    raise ConfigurationError("case profile references an unregistered or unscoped target")
                scoped_paths = self.scope.permitted_paths_by_target[profile.target_id]
                if not profile.permitted_paths <= frozenset(registration.permitted_paths):
                    raise ConfigurationError("case profile paths exceed registered target paths")
                if not profile.permitted_paths <= scoped_paths:
                    raise ConfigurationError("case profile paths exceed the active scope policy")


@dataclass(frozen=True, slots=True)
class RequestIntent:
    """Untrusted request intent. It carries a target ID and relative path, never an authorizing URL."""

    target_id: object
    path: object


@dataclass(frozen=True, slots=True)
class OperationIntent:
    """Untrusted, data-only operation request; it never carries a permit or URL."""

    operation_id: object
    target_id: object
    method: object
    path: object
    parameters: object = ()
    case_id: object = None
    profile_id: object = None
    headers: object = ()
    body: object = None


@dataclass(frozen=True, slots=True)
class CanonicalOperation:
    """Validated operation plus trusted execution, registration and scope context."""

    run_id: str
    operation_id: str
    target_id: str
    target_registration_version: str
    case_id: str
    profile_id: str
    case_profile_version: str
    origin: str
    method: str
    path: str
    parameters: tuple[tuple[str, str], ...]
    headers: tuple[tuple[str, str], ...]
    body: bytes | None = field(repr=False)

    @property
    def canonical_query(self) -> str:
        """RFC 3986-style query serialization derived only from canonical pairs."""
        return "&".join(
            f"{quote(name, safe='-._~')}={quote(value, safe='-._~')}"
            for name, value in self.parameters
        )


def _canonical_origin(registration: ApprovedTargetRegistration) -> str:
    try:
        address = ipaddress.ip_address(registration.hostname)
    except ValueError:
        host = registration.hostname
    else:
        canonical_address = address.compressed
        host = f"[{canonical_address}]" if address.version == 6 else canonical_address
    return f"{registration.scheme}://{host}:{registration.port}"


def _canonical_operation(
    value: object,
    *,
    run_id: str,
    registration: ApprovedTargetRegistration,
    profile: CaseProfilePolicy,
    limits: OperationDataLimits,
) -> CanonicalOperation | None:
    if not isinstance(value, OperationIntent):
        return None
    if type(value.operation_id) is not str or _OPERATION_ID.fullmatch(value.operation_id) is None:
        return None
    if not _validate_target_id(value.target_id, config=False) or value.target_id != registration.target_id:
        return None
    if (
        type(value.case_id) is not str
        or _OPERATION_ID.fullmatch(value.case_id) is None
        or type(value.profile_id) is not str
        or _OPERATION_ID.fullmatch(value.profile_id) is None
        or value.case_id != profile.case_id
        or value.profile_id != profile.profile_id
    ):
        return None
    if type(value.method) is not str or value.method not in _READ_ONLY_METHODS or value.method not in profile.allowed_methods:
        return None
    path = _canonical_path(value.path, config=False)
    if path is None or path not in profile.permitted_paths:
        return None
    if type(value.parameters) is not tuple or len(value.parameters) > limits.max_parameters:
        return None
    parameters: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for pair in value.parameters:
        if type(pair) is not tuple or len(pair) != 2:
            return None
        name, parameter_value = pair
        if (
            type(name) is not str
            or _PARAMETER_NAME.fullmatch(name) is None
            or name not in profile.permitted_parameter_names
        ):
            return None
        if name in seen_names or type(parameter_value) is not str:
            return None
        if any(ord(character) < 0x20 or ord(character) == 0x7F for character in parameter_value):
            return None
        try:
            parameter_value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return None
        seen_names.add(name)
        parameters.append((name, parameter_value))
    parameters.sort(key=lambda item: item[0])
    canonical_parameters = tuple(parameters)
    canonical_query = "&".join(
        f"{quote(name, safe='-._~')}={quote(parameter_value, safe='-._~')}"
        for name, parameter_value in canonical_parameters
    )
    if len(canonical_query.encode("ascii")) > limits.max_query_bytes:
        return None

    if type(value.headers) is not tuple or len(value.headers) > limits.max_headers:
        return None
    canonical_headers: list[tuple[str, str]] = []
    seen_headers: set[str] = set()
    for pair in value.headers:
        if type(pair) is not tuple or len(pair) != 2:
            return None
        name, header_value = pair
        if (
            type(name) is not str
            or not name.isascii()
            or _HEADER_NAME.fullmatch(name) is None
            or type(header_value) is not str
            or not header_value.isascii()
            or header_value != header_value.strip(" ")
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in header_value)
        ):
            return None
        canonical_name = name.lower()
        if (
            canonical_name in seen_headers
            or canonical_name in _FORBIDDEN_HEADERS
            or canonical_name not in profile.permitted_header_names
        ):
            return None
        seen_headers.add(canonical_name)
        canonical_headers.append((canonical_name, header_value))
    canonical_headers.sort(key=lambda item: item[0])
    header_bytes = sum(len(name) + 2 + len(header_value) + 2 for name, header_value in canonical_headers)
    if header_bytes > limits.max_header_bytes:
        return None

    if value.body is not None and type(value.body) is not bytes:
        return None
    if value.body is not None and (not profile.allow_body or len(value.body) > limits.max_body_bytes):
        return None
    return CanonicalOperation(
        run_id=run_id,
        operation_id=value.operation_id,
        target_id=registration.target_id,
        target_registration_version=registration.registration_version,
        case_id=profile.case_id,
        profile_id=profile.profile_id,
        case_profile_version=profile.version,
        origin=_canonical_origin(registration),
        method=value.method,
        path=path,
        parameters=canonical_parameters,
        headers=tuple(canonical_headers),
        body=value.body,
    )


@dataclass(frozen=True, slots=True)
class OperationPermit:
    """Engine-issued, one-use capability for one canonical operation in one run."""

    run_id: str
    operation: CanonicalOperation
    target_registration_version: str
    scope_policy_id: str
    scope_version: str
    case_profile_version: str
    operation_data_limits_version: str
    request_slot: int
    request_budget_limit: int
    redirect_slot: int | None
    redirect_budget_limit: int
    issued_at: float
    operation_deadline: float
    run_deadline: float
    request_timeout_seconds: float
    _nonce: str = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class OperationAuthorization:
    """Policy decision plus an optional permit; only the engine creates allowed pairs."""

    decision: PolicyDecision
    permit: OperationPermit | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, PolicyDecision):
            raise ValueError("operation authorization requires a policy decision")
        if self.decision.allowed != (self.permit is not None):
            raise ValueError("only an allowed operation authorization may carry a permit")
        if self.permit is not None and not isinstance(self.permit, OperationPermit):
            raise ValueError("operation permit has an invalid type")

    @property
    def allowed(self) -> bool:
        return self.decision.allowed and self.permit is not None


@dataclass(slots=True)
class _IssuedPermit:
    authorization: OperationAuthorization
    operation: CanonicalOperation
    is_redirect: bool
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class BudgetUsage:
    requests_used: int
    redirects_used: int
    elapsed_seconds: float | None


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    outcome: PolicyOutcome
    reason: PolicyReason
    target_id: str | None
    policy_id: str | None
    policy_version: str | None
    request_timeout_seconds: float | None = None
    authorized_path: str | None = None
    _authority: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, PolicyOutcome) or not isinstance(self.reason, PolicyReason):
            raise ValueError("policy outcome and reason must use their typed enums")
        if self.target_id is not None and not _validate_target_id(self.target_id, config=False):
            raise ValueError("policy decision has an invalid target ID")
        if self.policy_id is not None and (not isinstance(self.policy_id, str) or not self.policy_id.strip()):
            raise ValueError("policy decision has an invalid policy ID")
        if self.policy_version is not None and (not isinstance(self.policy_version, str) or not self.policy_version.strip()):
            raise ValueError("policy decision has an invalid policy version")
        if self.outcome is PolicyOutcome.ALLOW:
            if self.reason is not PolicyReason.ALLOWED or self.target_id is None:
                raise ValueError("allow decisions require an allowed reason and target ID")
            if self._authority is not _POLICY_ISSUER:
                raise ValueError("allow decisions may only be issued by the deterministic policy engine")
            if self.policy_id is None or self.policy_version is None or self.authorized_path is None:
                raise ValueError("allow decisions require policy provenance and a canonical path")
            if _canonical_path(self.authorized_path, config=False) != self.authorized_path:
                raise ValueError("allow decision path must be canonical")
            if self.request_timeout_seconds is None:
                raise ValueError("allow decisions require an explicit request timeout")
            _positive_finite(self.request_timeout_seconds, "decision request timeout")
        elif (
            self.reason is PolicyReason.ALLOWED
            or self.request_timeout_seconds is not None
            or self.authorized_path is not None
            or self._authority is not None
        ):
            raise ValueError("deny decisions cannot carry allow-only authority fields")

    @property
    def allowed(self) -> bool:
        return self.outcome is PolicyOutcome.ALLOW


@dataclass(frozen=True, slots=True)
class RedirectDecision:
    decision: PolicyDecision
    destination_target_id: str | None
    destination_path: str | None

    @property
    def allowed(self) -> bool:
        return self.decision.allowed


class PolicyEngine:
    """Fail-closed deterministic policy evaluator with a per-instance run budget."""

    def __init__(
        self,
        configuration: SafetyConfiguration | None,
        *,
        clock: Callable[[], float] = time.monotonic,
        run_id: str | None = None,
    ) -> None:
        self._configuration = configuration if isinstance(configuration, SafetyConfiguration) else None
        self._configuration_error: PolicyReason | None = None
        if configuration is None:
            self._configuration_error = PolicyReason.MISSING_CONFIGURATION
        elif self._configuration is None:
            self._configuration_error = PolicyReason.INVALID_CONFIGURATION
        self._lock = threading.RLock()
        self._clock = clock if callable(clock) else None
        self.run_id = uuid.uuid4().hex if run_id is None else run_id
        if not isinstance(self.run_id, str) or _VERSION.fullmatch(self.run_id) is None:
            self._configuration_error = PolicyReason.INVALID_CONFIGURATION
        self._permit_issuer = object()
        self._permits: dict[str, _IssuedPermit] = {}
        self._operation_ids: set[str] = set()
        self._revoked_registrations: set[tuple[str, str]] = set()
        self._operation_denial: PolicyDecision | None = None
        self._started_at: float | None = None
        self._requests_used = 0
        self._redirects_used = 0
        if self._configuration is not None and self._configuration_error is None:
            if self._clock is None:
                self._configuration_error = PolicyReason.INVALID_CONFIGURATION
            else:
                try:
                    started = self._clock()
                    if isinstance(started, bool) or not isinstance(started, (int, float)) or not math.isfinite(float(started)):
                        raise ValueError("clock value is invalid")
                    self._started_at = float(started)
                except Exception:
                    self._configuration_error = PolicyReason.CLOCK_FAILURE

    @property
    def budget_usage(self) -> BudgetUsage:
        elapsed = self._elapsed()
        with self._lock:
            return BudgetUsage(self._requests_used, self._redirects_used, elapsed)

    def revoke_registration(self, target_id: str, registration_version: str) -> None:
        """Revoke one in-memory registration version; this does not verify real authorization."""
        if not _validate_target_id(target_id, config=False):
            raise ConfigurationError("target_id has an invalid format")
        if not isinstance(registration_version, str) or _VERSION.fullmatch(registration_version) is None:
            raise ConfigurationError("registration_version has an invalid format")
        with self._lock:
            configuration, failure = self._ready_configuration()
            if failure is not None or configuration is None:
                raise ConfigurationError("cannot revoke a target under invalid safety configuration")
            registration = configuration.registry.get(target_id)
            if registration is None or registration.registration_version != registration_version:
                raise ConfigurationError("revocation must identify a registered target version")
            self._revoked_registrations.add((target_id, registration_version))

    def latch_operation_denial(self, reason: PolicyReason, target_id: str | None = None) -> PolicyDecision:
        """Permanently deny operation execution for this run context."""
        if not isinstance(reason, PolicyReason) or reason is PolicyReason.ALLOWED:
            reason = PolicyReason.INVALID_OPERATION
        if target_id is not None and not _validate_target_id(target_id, config=False):
            target_id = None
        with self._lock:
            return self._latch_operation_denial(reason, target_id)

    def workflow_denial(self, target_id: str | None = None) -> PolicyDecision:
        """Return a non-authorizing denial carrying current policy provenance when available."""
        if target_id is not None and not _validate_target_id(target_id, config=False):
            target_id = None
        configuration = self._configuration
        return PolicyDecision(
            PolicyOutcome.DENY,
            PolicyReason.WORKFLOW_DENIED,
            target_id,
            configuration.scope.policy_id if configuration is not None else None,
            configuration.scope.version if configuration is not None else None,
        )

    def authorize_operation(
        self, intent: OperationIntent, *, is_redirect: bool = False
    ) -> OperationAuthorization:
        """Validate and reserve one exact read-only operation, then issue a run-bound permit."""
        with self._lock:
            if self._operation_denial is not None:
                return OperationAuthorization(self._workflow_denial(self._operation_denial.target_id), None)
            target_id = self._target_id_or_none(getattr(intent, "target_id", None))
            if not isinstance(is_redirect, bool):
                decision = self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
                return OperationAuthorization(decision, None)
            configuration, failure = self._ready_configuration()
            if failure is not None or configuration is None:
                decision = self._latch_operation_denial(failure or PolicyReason.INVALID_CONFIGURATION, target_id)
                return OperationAuthorization(decision, None)
            if configuration.emergency_stop.active:
                decision = self._latch_operation_denial(PolicyReason.EMERGENCY_STOP, target_id)
                return OperationAuthorization(decision, None)
            if configuration.case_profiles is None or configuration.operation_data_limits is None:
                decision = self._latch_operation_denial(PolicyReason.MISSING_CONFIGURATION, target_id)
                return OperationAuthorization(decision, None)
            if not isinstance(intent, OperationIntent) or not _validate_target_id(intent.target_id, config=False):
                decision = self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
                return OperationAuthorization(decision, None)
            if (
                type(intent.case_id) is not str
                or _OPERATION_ID.fullmatch(intent.case_id) is None
                or type(intent.profile_id) is not str
                or _OPERATION_ID.fullmatch(intent.profile_id) is None
            ):
                decision = self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
                return OperationAuthorization(decision, None)
            target_id = intent.target_id
            registration, reason = self._registration_for(configuration, target_id)
            if reason is not None or registration is None:
                decision = self._latch_operation_denial(reason or PolicyReason.UNKNOWN_TARGET, target_id)
                return OperationAuthorization(decision, None)
            profile = next(
                (
                    item
                    for item in configuration.case_profiles
                    if item.target_id == target_id
                    and item.case_id == intent.case_id
                    and item.profile_id == intent.profile_id
                ),
                None,
            )
            if profile is None:
                decision = self._latch_operation_denial(PolicyReason.CASE_PROFILE_NOT_PERMITTED, target_id)
                return OperationAuthorization(decision, None)
            operation = _canonical_operation(
                intent,
                run_id=self.run_id,
                registration=registration,
                profile=profile,
                limits=configuration.operation_data_limits,
            )
            if operation is None:
                decision = self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
                return OperationAuthorization(decision, None)
            if operation.path not in registration.permitted_paths or operation.path not in configuration.scope.permitted_paths_by_target[target_id]:
                decision = self._latch_operation_denial(PolicyReason.PATH_NOT_PERMITTED, target_id)
                return OperationAuthorization(decision, None)
            if (target_id, registration.registration_version) in self._revoked_registrations:
                decision = self._latch_operation_denial(PolicyReason.TARGET_REVOKED, target_id)
                return OperationAuthorization(decision, None)
            if operation.operation_id in self._operation_ids:
                decision = self._latch_operation_denial(PolicyReason.OPERATION_ID_REUSED, target_id)
                return OperationAuthorization(decision, None)
            elapsed = self._elapsed()
            if elapsed is None or self._started_at is None:
                decision = self._latch_operation_denial(PolicyReason.CLOCK_FAILURE, target_id)
                return OperationAuthorization(decision, None)
            if elapsed >= configuration.timeouts.max_run_seconds:
                decision = self._latch_operation_denial(PolicyReason.EXECUTION_TIMEOUT, target_id)
                return OperationAuthorization(decision, None)
            if self._requests_used >= configuration.request_budget.max_requests:
                decision = self._latch_operation_denial(PolicyReason.REQUEST_BUDGET_EXHAUSTED, target_id)
                return OperationAuthorization(decision, None)
            if is_redirect and self._redirects_used >= configuration.request_budget.max_redirects:
                decision = self._latch_operation_denial(PolicyReason.REDIRECT_BUDGET_EXHAUSTED, target_id)
                return OperationAuthorization(decision, None)

            self._requests_used += 1
            self._operation_ids.add(operation.operation_id)
            if is_redirect:
                self._redirects_used += 1
            issued_at = self._started_at + elapsed
            run_deadline = self._started_at + configuration.timeouts.max_run_seconds
            operation_deadline = min(
                issued_at + configuration.timeouts.per_request_seconds,
                run_deadline,
            )
            timeout_seconds = operation_deadline - issued_at
            decision = self._allow(configuration, target_id, operation.path)
            permit = OperationPermit(
                run_id=self.run_id,
                operation=operation,
                target_registration_version=registration.registration_version,
                scope_policy_id=configuration.scope.policy_id,
                scope_version=configuration.scope.version,
                case_profile_version=profile.version,
                operation_data_limits_version=configuration.operation_data_limits.version,
                request_slot=self._requests_used,
                request_budget_limit=configuration.request_budget.max_requests,
                redirect_slot=self._redirects_used if is_redirect else None,
                redirect_budget_limit=configuration.request_budget.max_redirects,
                issued_at=issued_at,
                operation_deadline=operation_deadline,
                run_deadline=run_deadline,
                request_timeout_seconds=timeout_seconds,
                _nonce=uuid.uuid4().hex,
                _authority=self._permit_issuer,
            )
            authorization = OperationAuthorization(decision, permit)
            self._permits[permit._nonce] = _IssuedPermit(authorization, operation, is_redirect)
            return authorization

    def consume_operation_permit(
        self, authorization: object, intent: object
    ) -> PolicyDecision:
        """Validate the exact issued authorization and consume it once immediately before dispatch."""
        with self._lock:
            if self._operation_denial is not None:
                return self._workflow_denial(self._operation_denial.target_id)
            if not isinstance(authorization, OperationAuthorization) or authorization.permit is None:
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, None)
            permit = authorization.permit
            if not isinstance(permit, OperationPermit) or not isinstance(permit.operation, CanonicalOperation):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, None)
            if not isinstance(permit._nonce, str):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, None)
            target_id = permit.operation.target_id
            if not _validate_target_id(target_id, config=False):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, None)
            issued = self._permits.get(permit._nonce)
            if (
                permit._authority is not self._permit_issuer
                or issued is None
                or issued.authorization is not authorization
            ):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            if issued.consumed:
                return self._latch_operation_denial(PolicyReason.PERMIT_REPLAYED, target_id)
            configuration, failure = self._ready_configuration()
            if failure is not None or configuration is None:
                return self._latch_operation_denial(failure or PolicyReason.INVALID_CONFIGURATION, target_id)
            if configuration.case_profiles is None or configuration.operation_data_limits is None:
                return self._latch_operation_denial(PolicyReason.MISSING_CONFIGURATION, target_id)
            registration = configuration.registry.get(target_id)
            if registration is None or not registration.enabled:
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            if not isinstance(intent, OperationIntent):
                return self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
            if (
                type(intent.case_id) is not str
                or _OPERATION_ID.fullmatch(intent.case_id) is None
                or type(intent.profile_id) is not str
                or _OPERATION_ID.fullmatch(intent.profile_id) is None
            ):
                return self._latch_operation_denial(PolicyReason.INVALID_OPERATION, target_id)
            profile = next(
                (
                    item
                    for item in configuration.case_profiles
                    if item.target_id == target_id
                    and item.case_id == intent.case_id
                    and item.profile_id == intent.profile_id
                ),
                None,
            )
            if profile is None:
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            operation = _canonical_operation(
                intent,
                run_id=self.run_id,
                registration=registration,
                profile=profile,
                limits=configuration.operation_data_limits,
            )
            if operation is None or issued.operation != operation or permit.operation != operation:
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            if (
                permit.run_id != self.run_id
                or registration.registration_version != permit.target_registration_version
                or configuration.scope.policy_id != permit.scope_policy_id
                or configuration.scope.version != permit.scope_version
                or profile.version != permit.case_profile_version
                or configuration.operation_data_limits.version != permit.operation_data_limits_version
                or permit.request_budget_limit != configuration.request_budget.max_requests
                or permit.redirect_budget_limit != configuration.request_budget.max_redirects
                or isinstance(permit.request_slot, bool)
                or not isinstance(permit.request_slot, int)
                or permit.request_slot < 1
                or permit.request_slot > permit.request_budget_limit
                or (
                    issued.is_redirect
                    and (
                        isinstance(permit.redirect_slot, bool)
                        or not isinstance(permit.redirect_slot, int)
                        or permit.redirect_slot < 1
                        or permit.redirect_slot > permit.redirect_budget_limit
                    )
                )
                or (not issued.is_redirect and permit.redirect_slot is not None)
                or not math.isfinite(permit.issued_at)
                or not math.isfinite(permit.operation_deadline)
                or not math.isfinite(permit.run_deadline)
                or not math.isfinite(permit.request_timeout_seconds)
            ):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            if (target_id, registration.registration_version) in self._revoked_registrations:
                return self._latch_operation_denial(PolicyReason.TARGET_REVOKED, target_id)
            if configuration.emergency_stop.active:
                return self._latch_operation_denial(PolicyReason.EMERGENCY_STOP, target_id)
            elapsed = self._elapsed()
            if elapsed is None or self._started_at is None:
                return self._latch_operation_denial(PolicyReason.CLOCK_FAILURE, target_id)
            now = self._started_at + elapsed
            if now >= permit.run_deadline:
                return self._latch_operation_denial(PolicyReason.EXECUTION_TIMEOUT, target_id)
            if now >= permit.operation_deadline:
                return self._latch_operation_denial(PolicyReason.PERMIT_EXPIRED, target_id)
            if permit.run_deadline != self._started_at + configuration.timeouts.max_run_seconds:
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            expected_deadline = min(
                permit.issued_at + configuration.timeouts.per_request_seconds,
                permit.run_deadline,
            )
            if (
                permit.issued_at > now
                or permit.operation_deadline != expected_deadline
                or permit.operation_deadline > permit.run_deadline
                or permit.request_timeout_seconds != permit.operation_deadline - permit.issued_at
                or permit.request_timeout_seconds <= 0
            ):
                return self._latch_operation_denial(PolicyReason.PERMIT_INVALID, target_id)
            issued.consumed = True
            return issued.authorization.decision

    def _latch_operation_denial(self, reason: PolicyReason, target_id: str | None) -> PolicyDecision:
        if self._operation_denial is not None:
            return self._workflow_denial(self._operation_denial.target_id)
        decision = self._deny(reason, target_id)
        self._operation_denial = decision
        return decision

    @staticmethod
    def _workflow_denial(target_id: str | None) -> PolicyDecision:
        return PolicyDecision(PolicyOutcome.DENY, PolicyReason.WORKFLOW_DENIED, target_id, None, None)

    def evaluate_request(self, intent: RequestIntent) -> PolicyDecision:
        configuration, failure = self._ready_configuration()
        if failure is not None:
            return self._deny(failure, self._target_id_or_none(intent))
        assert configuration is not None
        if configuration.emergency_stop.active:
            return self._deny(PolicyReason.EMERGENCY_STOP, self._target_id_or_none(intent))
        if not isinstance(intent, RequestIntent) or not _validate_target_id(intent.target_id, config=False):
            return self._deny(PolicyReason.INVALID_REQUEST, self._target_id_or_none(intent))
        target_id = intent.target_id
        registration, reason = self._registration_for(configuration, target_id)
        if reason is not None:
            return self._deny(reason, target_id)
        assert registration is not None
        path = _canonical_path(intent.path, config=False)
        if path is None:
            return self._deny(PolicyReason.INVALID_PATH, target_id)
        if path not in registration.permitted_paths or path not in configuration.scope.permitted_paths_by_target[target_id]:
            return self._deny(PolicyReason.PATH_NOT_PERMITTED, target_id)
        return self._consume(configuration, target_id, is_redirect=False, authorized_path=path)

    def evaluate_redirect(self, target_id: object, current_path: object, location: object) -> RedirectDecision:
        configuration, failure = self._ready_configuration()
        if failure is not None:
            decision = self._deny(failure, self._target_id_or_none(target_id))
            return RedirectDecision(decision, None, None)
        assert configuration is not None
        if configuration.emergency_stop.active:
            decision = self._deny(PolicyReason.EMERGENCY_STOP, self._target_id_or_none(target_id))
            return RedirectDecision(decision, None, None)
        if not _validate_target_id(target_id, config=False):
            decision = self._deny(PolicyReason.INVALID_REQUEST, None)
            return RedirectDecision(decision, None, None)
        registration, reason = self._registration_for(configuration, target_id)
        if reason is not None:
            decision = self._deny(reason, target_id)
            return RedirectDecision(decision, None, None)
        assert registration is not None
        source_path = _canonical_path(current_path, config=False)
        if source_path is None:
            decision = self._deny(PolicyReason.REDIRECT_INVALID, target_id)
            return RedirectDecision(decision, None, None)
        if source_path not in registration.permitted_paths or source_path not in configuration.scope.permitted_paths_by_target[target_id]:
            decision = self._deny(PolicyReason.PATH_NOT_PERMITTED, target_id)
            return RedirectDecision(decision, None, None)
        destination_path, origin_ok = self._resolve_redirect(registration, source_path, location)
        if destination_path is None:
            decision = self._deny(PolicyReason.REDIRECT_INVALID, target_id)
            return RedirectDecision(decision, None, None)
        if not origin_ok:
            decision = self._deny(PolicyReason.REDIRECT_ORIGIN_MISMATCH, target_id)
            return RedirectDecision(decision, None, destination_path)
        if destination_path not in registration.permitted_paths or destination_path not in configuration.scope.permitted_paths_by_target[target_id]:
            decision = self._deny(PolicyReason.PATH_NOT_PERMITTED, target_id)
            return RedirectDecision(decision, None, destination_path)
        decision = self._consume(configuration, target_id, is_redirect=True, authorized_path=destination_path)
        return RedirectDecision(decision, target_id if decision.allowed else None, destination_path)

    def _ready_configuration(self) -> tuple[SafetyConfiguration | None, PolicyReason | None]:
        if self._configuration_error is not None:
            return None, self._configuration_error
        if self._configuration is None:
            return None, PolicyReason.MISSING_CONFIGURATION
        return self._configuration, None

    def _registration_for(
        self, configuration: SafetyConfiguration, target_id: str
    ) -> tuple[ApprovedTargetRegistration | None, PolicyReason | None]:
        registration = configuration.registry.get(target_id)
        if registration is None:
            return None, PolicyReason.UNKNOWN_TARGET
        if not registration.enabled:
            return None, PolicyReason.TARGET_NOT_ENABLED
        scope = configuration.scope
        if (
            target_id not in scope.target_ids
            or registration.scheme not in scope.allowed_schemes
            or registration.hostname not in scope.allowed_hostnames
            or registration.port not in scope.allowed_ports
        ):
            return None, PolicyReason.TARGET_OUT_OF_SCOPE
        return registration, None

    def _consume(
        self,
        configuration: SafetyConfiguration,
        target_id: str,
        *,
        is_redirect: bool,
        authorized_path: str,
    ) -> PolicyDecision:
        with self._lock:
            if configuration.emergency_stop.active:
                return self._deny(PolicyReason.EMERGENCY_STOP, target_id)
            elapsed = self._elapsed()
            if elapsed is None:
                return self._deny(PolicyReason.CLOCK_FAILURE, target_id)
            if elapsed >= configuration.timeouts.max_run_seconds:
                return self._deny(PolicyReason.EXECUTION_TIMEOUT, target_id)
            if self._requests_used >= configuration.request_budget.max_requests:
                return self._deny(PolicyReason.REQUEST_BUDGET_EXHAUSTED, target_id)
            if is_redirect and self._redirects_used >= configuration.request_budget.max_redirects:
                return self._deny(PolicyReason.REDIRECT_BUDGET_EXHAUSTED, target_id)
            self._requests_used += 1
            if is_redirect:
                self._redirects_used += 1
            return self._allow(configuration, target_id, authorized_path)

    def _elapsed(self) -> float | None:
        if self._clock is None or self._started_at is None:
            return None
        try:
            now = self._clock()
        except Exception:
            return None
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(float(now)):
            return None
        elapsed = float(now) - self._started_at
        if elapsed < 0 or not math.isfinite(elapsed):
            return None
        return elapsed

    def _allow(self, configuration: SafetyConfiguration, target_id: str, authorized_path: str) -> PolicyDecision:
        return PolicyDecision(
            PolicyOutcome.ALLOW,
            PolicyReason.ALLOWED,
            target_id,
            configuration.scope.policy_id,
            configuration.scope.version,
            configuration.timeouts.per_request_seconds,
            authorized_path,
            _POLICY_ISSUER,
        )

    def _deny(self, reason: PolicyReason, target_id: str | None) -> PolicyDecision:
        configuration = self._configuration
        return PolicyDecision(
            PolicyOutcome.DENY,
            reason,
            target_id,
            configuration.scope.policy_id if configuration else None,
            configuration.scope.version if configuration else None,
        )

    @staticmethod
    def _target_id_or_none(value: object) -> str | None:
        return value if _validate_target_id(value, config=False) else None

    @staticmethod
    def _resolve_redirect(
        registration: ApprovedTargetRegistration, current_path: str, location: object
    ) -> tuple[str | None, bool]:
        if not isinstance(location, str) or not location or location != location.strip():
            return None, False
        if "\\" in location or "?" in location or "#" in location or _BAD_PERCENT.search(location):
            return None, False
        if any(ord(character) < 0x20 or ord(character) == 0x7F for character in location):
            return None, False
        try:
            parts = urlsplit(location)
            raw_path = parts.path
            if _ENCODED_SEPARATOR.search(raw_path):
                return None, False
            decoded_raw_path = unquote(raw_path, errors="strict")
        except (ValueError, UnicodeDecodeError):
            return None, False
        if "\\" in decoded_raw_path or any(segment in {".", ".."} for segment in decoded_raw_path.split("/")):
            return None, False
        if _NESTED_DOT_OR_SEPARATOR.search(decoded_raw_path):
            return None, False
        authority_host = f"[{registration.hostname}]" if ":" in registration.hostname else registration.hostname
        base = f"{registration.scheme}://{authority_host}:{registration.port}{current_path}"
        try:
            resolved = urljoin(base, location)
            dest = urlsplit(resolved)
            hostname = dest.hostname
            if hostname is None or dest.username is not None or dest.password is not None or dest.fragment:
                return None, False
            scheme = dest.scheme.lower()
            if scheme not in _ALLOWED_SCHEMES:
                return None, False
            try:
                port = dest.port
            except ValueError:
                return None, False
            if port is None:
                port = 80 if scheme == "http" else 443
            path = _canonical_path(dest.path or "/", config=False)
            if path is None:
                return None, False
            same_origin = (
                scheme == registration.scheme
                and hostname.lower() == registration.hostname
                and port == registration.port
            )
            return path, same_origin
        except (ValueError, UnicodeError):
            return None, False


class WorkflowSafetyGate:
    """Monotonic run gate: a denial is terminal and later allows cannot clear it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_allow: PolicyDecision | None = None
        self._allow_available = False
        self._denial: PolicyDecision | None = None

    def record(self, decision: PolicyDecision) -> PolicyDecision:
        with self._lock:
            if self._denial is not None:
                return self._workflow_denial(self._denial.target_id)
            if not isinstance(decision, PolicyDecision):
                self._denial = PolicyDecision(
                    PolicyOutcome.DENY, PolicyReason.INVALID_REQUEST, None, None, None
                )
                return self._denial
            if decision.allowed and decision._authority is not _POLICY_ISSUER:
                self._denial = PolicyDecision(
                    PolicyOutcome.DENY, PolicyReason.INVALID_REQUEST, decision.target_id, None, None
                )
                return self._denial
            if not decision.allowed:
                self._denial = decision
                return decision
            self._last_allow = decision
            self._allow_available = True
            return decision

    def authorize_next_step(self, intent: RequestIntent) -> PolicyDecision:
        with self._lock:
            if self._denial is not None:
                return self._workflow_denial(self._denial.target_id)
            if self._last_allow is None or not self._allow_available:
                return PolicyDecision(PolicyOutcome.DENY, PolicyReason.NO_PRIOR_ALLOW, None, None, None)
            if not isinstance(intent, RequestIntent):
                self._denial = PolicyDecision(PolicyOutcome.DENY, PolicyReason.INVALID_REQUEST, None, None, None)
                return self._denial
            path = _canonical_path(intent.path, config=False)
            if (
                intent.target_id != self._last_allow.target_id
                or path is None
                or path != self._last_allow.authorized_path
            ):
                self._denial = self._workflow_denial(self._last_allow.target_id)
                return self._denial
            self._allow_available = False
            return self._last_allow

    @staticmethod
    def _workflow_denial(target_id: str | None) -> PolicyDecision:
        return PolicyDecision(PolicyOutcome.DENY, PolicyReason.WORKFLOW_DENIED, target_id, None, None)

