"""Application factory and ASGI entry point for the minimal backend."""

import logging
import ipaddress
import os

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aegiscore.api.auth import AuthSettings, LocalAuthService
from aegiscore.api.routes import auth_router, router
from aegiscore.local_persistence import LocalRecordStore, LocalStoreError
from aegiscore.source_review import PersistentSourceReviewRegistry, SourceReviewError


_logger = logging.getLogger(__name__)
_TEST_HOSTS = frozenset({"testclient", "testserver"})


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


def create_app(
    *,
    source_review_registry: PersistentSourceReviewRegistry | None = None,
    local_store_path: str | os.PathLike[str] | None = None,
    auth_settings: AuthSettings | None = None,
    api_host: str | None = None,
) -> FastAPI:
    """Build the API with optional, explicitly configured local stores.

    ``AEGISCORE_LOCAL_STORE_PATH`` opts into initializing the local records
    database. Offline workflows may use the same configured path to persist
    completed fixture reports. API read routes reopen it read-only.

    Evidence configuration uses ``AEGISCORE_SOURCE_REVIEW_DB``,
    ``AEGISCORE_SOURCE_REVIEW_MANIFEST``, and ``AEGISCORE_REPOSITORY_ROOT``.
    Invalid or incomplete configuration is logged and remains unavailable; it
    never falls back to demo or unreviewed sources.
    """

    safe_host = _configured_api_host(api_host)
    settings = auth_settings if auth_settings is not None else AuthSettings.load()
    app = FastAPI(title="AEGISCORE AI Backend", version="0.1.0")
    app.state.api_host = safe_host
    app.state.auth_service = LocalAuthService(settings) if settings is not None else None

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
    if configured_path is None:
        configured_path = os.environ.get("AEGISCORE_LOCAL_STORE_PATH")
    local_store_configured = configured_path is not None and str(configured_path).strip() != ""
    local_store_available = False
    if local_store_configured:
        try:
            LocalRecordStore.create_or_open(configured_path)
            local_store_available = True
            _logger.info("Local persistence store initialized for offline workflow records.")
        except (LocalStoreError, OSError, ValueError, TypeError):
            _logger.warning(
                "Local persistence configuration is invalid or unavailable; persisted-record reads will return 503."
            )

    app.state.source_review_registry = registry
    app.state.local_store_path = configured_path if local_store_available else None
    app.state.local_store_configured = local_store_configured
    app.include_router(auth_router)
    app.include_router(router)
    return app


app = create_app()
