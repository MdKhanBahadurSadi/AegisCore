"""Local password authentication and short-lived in-memory bearer sessions."""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import re
import secrets
import threading
import time
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


KNOWN_PERMISSIONS = frozenset({"records:read", "evidence:read"})
DEFAULT_PERMISSIONS = frozenset({"records:read", "evidence:read"})
DEFAULT_SESSION_TTL_SECONDS = 1800
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,64}$")
_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return PasswordHasher().hash(secrets.token_urlsafe(24))


class AuthConfigurationError(ValueError):
    """The local authentication configuration is incomplete or invalid."""


def default_auth_config_path() -> Path:
    """Return a per-user config path outside the repository workspace."""

    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        if root:
            return Path(root) / "AEGISCORE" / "auth.toml"
    root = os.environ.get("XDG_CONFIG_HOME")
    return (Path(root) if root else Path.home() / ".config") / "aegiscore" / "auth.toml"


@dataclass(frozen=True)
class AuthSettings:
    username: str
    password_hash: str = field(repr=False)
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    permissions: frozenset[str] = DEFAULT_PERMISSIONS

    def __post_init__(self) -> None:
        if not self.username or self.username.strip() != self.username or len(self.username) > 128:
            raise AuthConfigurationError("Authentication username is invalid.")
        if not isinstance(self.password_hash, str) or not self.password_hash.startswith("$argon2id$"):
            raise AuthConfigurationError("Authentication password hash must use Argon2id.")
        try:
            extract_parameters(self.password_hash)
        except (InvalidHashError, ValueError, TypeError):
            raise AuthConfigurationError("Authentication password hash is invalid.") from None
        if not 1 <= self.session_ttl_seconds <= 86400:
            raise AuthConfigurationError("Authentication session lifetime is out of range.")
        if not self.permissions or not self.permissions <= KNOWN_PERMISSIONS:
            raise AuthConfigurationError("Authentication permissions are invalid.")

    @classmethod
    def load(cls) -> AuthSettings | None:
        """Load settings from environment variables or a private per-user TOML file."""

        env_username = os.environ.get("AEGISCORE_AUTH_USERNAME")
        env_hash = os.environ.get("AEGISCORE_AUTH_PASSWORD_HASH")
        env_ttl = os.environ.get("AEGISCORE_AUTH_SESSION_TTL_SECONDS")
        env_permissions = os.environ.get("AEGISCORE_AUTH_PERMISSIONS")
        if any(value is not None for value in (env_username, env_hash, env_ttl, env_permissions)):
            if not env_username or not env_hash:
                raise AuthConfigurationError(
                    "Set both AEGISCORE_AUTH_USERNAME and AEGISCORE_AUTH_PASSWORD_HASH."
                )
            try:
                ttl = int(env_ttl) if env_ttl is not None else DEFAULT_SESSION_TTL_SECONDS
            except ValueError:
                raise AuthConfigurationError("Authentication session lifetime is invalid.") from None
            permissions = (
                frozenset(item.strip() for item in env_permissions.split(",") if item.strip())
                if env_permissions is not None
                else DEFAULT_PERMISSIONS
            )
            return cls(env_username, env_hash, ttl, permissions)

        configured_path = os.environ.get("AEGISCORE_AUTH_CONFIG_FILE")
        path = Path(configured_path).expanduser() if configured_path else default_auth_config_path()
        if not path.is_file():
            return None
        try:
            if os.name != "nt" and path.stat().st_mode & 0o077:
                raise AuthConfigurationError(
                    "Authentication config permissions are too broad; restrict the file to its owner."
                )
            with path.open("rb") as config_file:
                config = tomllib.load(config_file)
            auth = config.get("auth")
            if not isinstance(auth, dict):
                raise AuthConfigurationError("Authentication config is invalid.")
            username = auth.get("username")
            password_hash = auth.get("password_hash")
            ttl = auth.get("session_ttl_seconds", DEFAULT_SESSION_TTL_SECONDS)
            permissions_value = auth.get("permissions", sorted(DEFAULT_PERMISSIONS))
            if (
                not isinstance(username, str)
                or not isinstance(password_hash, str)
                or not isinstance(ttl, int)
                or not isinstance(permissions_value, list)
                or any(not isinstance(item, str) for item in permissions_value)
            ):
                raise AuthConfigurationError("Authentication config is invalid.")
            return cls(username, password_hash, ttl, frozenset(permissions_value))
        except AuthConfigurationError:
            raise
        except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
            raise AuthConfigurationError("Authentication config is unavailable or invalid.") from None


@dataclass(frozen=True)
class AuthenticatedSession:
    username: str
    permissions: frozenset[str]
    expires_at: float
    token_digest: str

    @property
    def expires_in(self) -> int:
        return max(0, math.ceil(self.expires_at - time.monotonic()))


class LocalAuthService:
    """Verifies one locally provisioned Argon2id account and tracks volatile sessions."""

    def __init__(self, settings: AuthSettings):
        self.settings = settings
        self._hasher = PasswordHasher()
        self._dummy_hash = _dummy_password_hash()
        self._sessions: dict[str, AuthenticatedSession] = {}
        self._lock = threading.Lock()

    @property
    def ttl_seconds(self) -> int:
        return self.settings.session_ttl_seconds

    def login(self, username: str, password: str) -> tuple[str, AuthenticatedSession] | None:
        username_matches = hmac.compare_digest(username, self.settings.username)
        password_hash = self.settings.password_hash if username_matches else self._dummy_hash
        try:
            password_matches = self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            password_matches = False
        if not username_matches or not password_matches:
            return None

        token = secrets.token_urlsafe(32)
        digest = self._token_digest(token)
        session = AuthenticatedSession(
            username=self.settings.username,
            permissions=self.settings.permissions,
            expires_at=time.monotonic() + self.settings.session_ttl_seconds,
            token_digest=digest,
        )
        with self._lock:
            self._purge_expired_locked()
            self._sessions[digest] = session
        return token, session

    def resolve(self, token: str | None) -> AuthenticatedSession | None:
        if token is None or not _TOKEN_PATTERN.fullmatch(token):
            return None
        digest = self._token_digest(token)
        now = time.monotonic()
        with self._lock:
            session = self._sessions.get(digest)
            if session is None:
                return None
            if session.expires_at <= now:
                self._sessions.pop(digest, None)
                return None
            return session

    def invalidate(self, session: AuthenticatedSession) -> None:
        with self._lock:
            self._sessions.pop(session.token_digest, None)

    def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        for digest, session in tuple(self._sessions.items()):
            if session.expires_at <= now:
                self._sessions.pop(digest, None)

    @staticmethod
    def _token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()


def authentication_not_configured() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Backend authentication is not configured. Complete local authentication setup.",
    )


def invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Authentication required or credentials are invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedSession:
    service: LocalAuthService | None = getattr(request.app.state, "auth_service", None)
    if service is None:
        raise authentication_not_configured()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise invalid_credentials()
    session = service.resolve(credentials.credentials)
    if session is None:
        raise invalid_credentials()
    return session


def require_permission(permission: str):
    def check_permission(
        session: Annotated[AuthenticatedSession, Depends(require_session)],
    ) -> AuthenticatedSession:
        if permission not in session.permissions:
            raise HTTPException(status_code=403, detail="The authenticated account lacks this permission.")
        return session

    return check_permission

