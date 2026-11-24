"""Application factory and ASGI entry point for the minimal backend."""

import logging
import ipaddress
import math
import os
import threading
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator, Sequence
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from aegiscore.assessment_ai import PassiveAssessmentAIReviewer
from aegiscore.api.auth import AuthSettings, LocalAuthService
from aegiscore.api.routes import auth_router, router
from aegiscore.authorization_verification import AuthorizationVerifier, AuthorizationVerificationError
from aegiscore.local_persistence import LocalRecordStore, LocalStoreError
from aegiscore.model_adapter import ModelConfigurationError
from aegiscore.production_execution import AuthorizedAssessmentExecutor
from aegiscore.safety import TargetRegistry
from aegiscore.source_review import PersistentSourceReviewRegistry, SourceReviewError
from aegiscore.target_authorization import TargetAuthorizationError, load_target_registry, validate_target_registry


_logger = logging.getLogger(__name__)
_TEST_HOSTS = frozenset({"testclient", "testserver"})


def _lease_recovery_loop(app: FastAPI, configured_path: str | os.PathLike[str], interval: float,
                         stop_event: threading.Event) -> None:
    while not stop_event.wait(interval):
        try:
            store = LocalRecordStore.create_or_open(configured_path)
            store.recover_stale_assessments()
            app.state.local_store_path = configured_path
        except (LocalStoreError, OSError, TypeError, ValueError):
            _logger.debug("Lease recovery retry deferred because local persistence is unavailable.")


@asynccontextmanager
async def _app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    configured_path = getattr(app.state, "local_store_configured_path", None)
    interval = getattr(app.state, "recovery_interval_seconds", 1.0)
    stop_event = threading.Event()
    worker: threading.Thread | None = None
    if configured_path is not None:
        worker = threading.Thread(
            target=_lease_recovery_loop,
            args=(app, configured_path, interval, stop_event),
            name="aegiscore-lease-recovery",
            daemon=True,
        )
        worker.start()
    try:
        yield
    finally:
        stop_event.set()
        if worker is not None:
            worker.join(timeout=max(1.0, interval * 2.0))


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_loopback


def _configured_api_host(value: str | None = None) -> str:
    host = value if value is not None else os.environ.get("AEGISCORE_API_HOST", "127.0.0.1")
    if not isinstance(host, str) or not _is_loopback_host(host):
        raise RuntimeError("AEGISCORE_API_HOST must be a loopback address (127.0.0.1, ::1, or localhost).")
    return host


def _normalize_cors_origin(value: object) -> str:
    """Validate one exact browser origin and return its serialized form."""
    if not isinstance(value, str) or not value or value.strip() != value or "*" in value:
        raise ValueError("CORS origins must be explicit HTTP(S) origins.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("CORS origin is malformed.") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.netloc.endswith(":")
        or "%" in parsed.netloc
    ):
        raise ValueError("CORS origins must not contain paths, credentials, queries, or fragments.")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("CORS origin port is invalid.")
    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    except (UnicodeError, AttributeError):
        raise ValueError("CORS origin hostname is invalid.") from None
    if not hostname or hostname.endswith("."):
        raise ValueError("CORS origin hostname is not canonical.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        labels = hostname.split(".")
        if any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or any(not (char.isascii() and (char.isalnum() or char == "-")) for char in label)
            for label in labels
        ):
            raise ValueError("CORS origin hostname is invalid.") from None
    scheme = parsed.scheme.lower()
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and port != (80 if scheme == "http" else 443):
        host = f"{host}:{port}"
    return f"{scheme}://{host}"


def _configured_cors_origins(value: Sequence[str] | None = None) -> tuple[str, ...]:
    """Load an exact origin allowlist; an absent value disables cross-origin access."""
    if value is None:
        raw = os.environ.get("AEGISCORE_CORS_ALLOWED_ORIGINS")
        if raw is None:
            return ()
        if not raw.strip():
            raise ValueError("AEGISCORE_CORS_ALLOWED_ORIGINS must not be empty when set.")
        candidates = raw.split(",")
    else:
        if isinstance(value, str):
            raise ValueError("cors_allowed_origins must be a sequence of exact origins.")
        candidates = list(value)
        if not candidates:
            return ()

    origins = tuple(_normalize_cors_origin(origin) for origin in candidates)
    if len(set(origins)) != len(origins):
        raise ValueError("CORS origin allowlist contains duplicate origins.")
    return origins


def create_app(
    *,
    source_review_registry: PersistentSourceReviewRegistry | None = None,
    authorized_target_registry: TargetRegistry | None = None,
    authorization_verifier: AuthorizationVerifier | None = None,
    local_store_path: str | os.PathLike[str] | None = None,
    auth_settings: AuthSettings | None = None,
    api_host: str | None = None,
    recovery_interval_seconds: float = 1.0,
    assessment_ai_model_adapter: object | None = None,
    cors_allowed_origins: Sequence[str] | None = None,
) -> FastAPI:
    """Build the API with optional, explicitly configured local stores.

    ``AEGISCORE_LOCAL_STORE_PATH`` opts into initializing the local records
    database. Offline workflows may use the same configured path to persist
    completed fixture reports. API read routes reopen it read-only.

    Evidence configuration uses ``AEGISCORE_SOURCE_REVIEW_DB``,
    ``AEGISCORE_SOURCE_REVIEW_MANIFEST``, and ``AEGISCORE_REPOSITORY_ROOT``.
    Invalid or incomplete configuration is logged and remains unavailable; it
    never falls back to demo or unreviewed sources.

    ``assessment_ai_model_adapter`` is an explicit in-process opt-in. When omitted,
    assessment execution performs no model requests. Live provider modes remain
    blocked until the existing provider authorization gate is approved.
    """

    safe_host = _configured_api_host(api_host)
    allowed_origins = _configured_cors_origins(cors_allowed_origins)
    settings = auth_settings if auth_settings is not None else AuthSettings.load()
    if (
        isinstance(recovery_interval_seconds, bool)
        or not isinstance(recovery_interval_seconds, (int, float))
        or not math.isfinite(float(recovery_interval_seconds))
        or not 0.01 <= float(recovery_interval_seconds) <= 60.0
    ):
        raise ValueError("recovery_interval_seconds must be between 0.01 and 60 seconds")

    app = FastAPI(title="AEGISCORE AI Backend", version="0.1.0", lifespan=_app_lifespan)
    app.state.api_host = safe_host
    app.state.cors_allowed_origins = allowed_origins
    app.state.auth_service = LocalAuthService(settings) if settings is not None else None
    app.state.recovery_interval_seconds = float(recovery_interval_seconds)
    app.state.assessment_ai_reviewer = None
    app.state.assessment_ai_configuration_invalid = False
    if assessment_ai_model_adapter is not None:
        try:
            app.state.assessment_ai_reviewer = PassiveAssessmentAIReviewer(assessment_ai_model_adapter)
        except ModelConfigurationError:
            # AI setup errors must not disable deterministic assessment execution.
            app.state.assessment_ai_configuration_invalid = True
            _logger.warning("Assessment AI review configuration is invalid; deterministic assessment remains available.")

    target_registry = authorized_target_registry
    if target_registry is None:
        try:
            target_registry = load_target_registry()
        except TargetAuthorizationError:
            _logger.warning("Authorized target configuration is invalid or unavailable; assessment execution is disabled.")
            target_registry = None
    if target_registry is not None:
        try:
            validate_target_registry(target_registry)
        except TargetAuthorizationError:
            _logger.warning("Authorized target registry is invalid; assessment execution is disabled.")
            target_registry = None
    app.state.authorized_target_registry = target_registry
    app.state.authorization_verifier = authorization_verifier
    if target_registry is not None and authorization_verifier is None:
        _logger.warning(
            "No authoritative authorization verifier is configured; assessment creation and execution are disabled."
        )
    try:
        app.state.assessment_executor = (
            AuthorizedAssessmentExecutor(target_registry, authorization_verifier)
            if target_registry is not None and authorization_verifier is not None
            else None
        )
    except AuthorizationVerificationError:
        _logger.warning("Authorization verification is invalid or unavailable; assessment execution is disabled.")
        app.state.assessment_executor = None

    @app.exception_handler(RequestValidationError)
    async def redact_auth_validation_errors(
        request: Request, exc: RequestValidationError
    ):
        if request.url.path == "/auth/login":
            # FastAPI's default validation body includes the rejected input;
            # login inputs can contain a password and must never be echoed.
            return JSONResponse(
                status_code=422,
                content={"detail": "Invalid authentication request."},
            )
        return await request_validation_exception_handler(request, exc)

    @app.middleware("http")
    async def enforce_loopback_access(request: Request, call_next):
        # TestClient uses these synthetic peer/host labels; no network listener
        # can produce them. Real requests must arrive over a loopback interface.
        client = request.scope.get("client")
        client_host = client[0] if client else None
        if client_host and client_host not in _TEST_HOSTS and not _is_loopback_host(client_host):
            return JSONResponse(status_code=403, content={"detail": "Loopback access only."})
        server = request.scope.get("server")
        server_host = server[0] if server else None
        if server_host and server_host not in _TEST_HOSTS and not _is_loopback_host(server_host):
            return JSONResponse(status_code=503, content={"detail": "Service is configured for loopback access only."})
        return await call_next(request)

    # CORS is an explicit browser response policy. Authentication and authorization
    # remain enforced by the route dependencies for every actual request.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
        allow_credentials=False,
        max_age=300,
    )
    registry = source_review_registry
    if registry is None:
        db_path = os.environ.get("AEGISCORE_SOURCE_REVIEW_DB")
        manifest_path = os.environ.get("AEGISCORE_SOURCE_REVIEW_MANIFEST")
        repository_root = os.environ.get("AEGISCORE_REPOSITORY_ROOT")
        if any((db_path, manifest_path, repository_root)):
            try:
                if not all((db_path, manifest_path, repository_root)):
                    raise SourceReviewError("incomplete source-review registry configuration")
                registry = PersistentSourceReviewRegistry.open_existing(
                    db_path,
                    manifest_path=manifest_path,
                    repository_root=repository_root,
                )
            except (SourceReviewError, OSError, ValueError):
                _logger.warning(
                    "Approved evidence registry configuration is invalid or unavailable; evidence reads will return 503."
                )
                registry = None

    configured_path = local_store_path
    if configured_path is None and "AEGISCORE_LOCAL_STORE_PATH" in os.environ:
        configured_path = os.environ["AEGISCORE_LOCAL_STORE_PATH"]
    local_store_configured = configured_path is not None
    if local_store_configured and (
        not isinstance(configured_path, (str, os.PathLike))
        or not os.fspath(configured_path).strip()
    ):
        raise RuntimeError("Configured local persistence path is invalid.")
    local_store_available = False
    if local_store_configured:
        try:
            store = LocalRecordStore.create_or_open(configured_path)
            store.recover_stale_assessments()
            local_store_available = True
            _logger.info("Local persistence store initialized for offline workflow records.")
        except (LocalStoreError, OSError, ValueError, TypeError):
            _logger.error("Configured local persistence could not be initialized; startup is aborted.")
            raise RuntimeError("Configured local persistence could not be initialized.") from None

    app.state.source_review_registry = registry
    app.state.local_store_path = configured_path if local_store_available else None
    app.state.local_store_configured = local_store_configured
    app.state.local_store_configured_path = configured_path if local_store_configured else None
    app.include_router(auth_router)
    app.include_router(router)
    return app


app = create_app()
