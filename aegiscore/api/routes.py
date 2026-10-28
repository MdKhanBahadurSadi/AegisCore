"""Read-only system and approved-evidence routes."""

import sqlite3
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from aegiscore.api.auth import (
    AuthenticatedSession,
    LocalAuthService,
    authentication_not_configured,
    invalid_credentials,
    require_permission,
    require_session,
)
from aegiscore.local_persistence import LocalRecordStore, LocalStoreError
from aegiscore.api.schemas import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthSessionResponse,
    ApprovedEvidenceListResponse,
    ApprovedEvidenceResponse,
    CapabilitiesResponse,
    DashboardSummaryResponse,
    EvidenceChunkResponse,
    EvidenceSourceResponse,
    EvaluationReportListResponse,
    EvaluationReportResponse,
    FindingListResponse,
    FindingResponse,
    HealthResponse,
    OfflineSessionListResponse,
    OfflineSessionResponse,
    StorageStatusResponse,
)
from aegiscore.rag import SourceChunk
from aegiscore.source_review import (
    PersistentSourceReviewRegistry,
    SourceReviewError,
    SourceReviewRecord,
)


router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest, request: Request, response: Response) -> AuthLoginResponse:
    """Exchange locally configured credentials for a volatile bearer session."""

    service: LocalAuthService | None = getattr(request.app.state, "auth_service", None)
    if service is None:
        raise authentication_not_configured()
    result = service.login(payload.username, payload.password)
    if result is None:
        raise invalid_credentials()
    token, session = result
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return AuthLoginResponse(access_token=token, expires_in=session.expires_in)


@auth_router.get("/session", response_model=AuthSessionResponse)
def current_session(
    session: Annotated[AuthenticatedSession, Depends(require_session)],
    response: Response,
) -> AuthSessionResponse:
    response.headers["Cache-Control"] = "no-store"
    return AuthSessionResponse(
        username=session.username,
        permissions=tuple(sorted(session.permissions)),
        expires_in=session.expires_in,
    )


@auth_router.post("/logout", response_model=AuthLogoutResponse)
def logout(
    request: Request,
    session: Annotated[AuthenticatedSession, Depends(require_session)],
) -> AuthLogoutResponse:
    service: LocalAuthService | None = getattr(request.app.state, "auth_service", None)
    if service is not None:
        service.invalidate(session)
    return AuthLogoutResponse()


def _local_store(request: Request) -> LocalRecordStore:
    configured_path = getattr(request.app.state, "local_store_path", None)
    if configured_path is None:
        raise HTTPException(
            status_code=503,
            detail="Local persistence store is not configured or is unavailable.",
        )
    try:
        return LocalRecordStore.open_existing(configured_path)
    except LocalStoreError:
        raise HTTPException(
            status_code=503,
            detail="Local persistence store is not configured or is unavailable.",
        ) from None


def _store_failure() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Local persistence store is unavailable or inconsistent.",
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report that the API process is answering; no downstream checks are implied."""

    return HealthResponse()


@router.get("/capabilities", response_model=CapabilitiesResponse, tags=["system"])
def capabilities() -> CapabilitiesResponse:
    """Return the static, implemented-versus-unimplemented backend inventory."""

    return CapabilitiesResponse()


@router.get(
    "/storage/status",
    response_model=StorageStatusResponse,
    tags=["system"],
)
def storage_status(request: Request) -> StorageStatusResponse:
    """Report whether configured local record storage is currently readable."""

    configured = bool(getattr(request.app.state, "local_store_configured", False))
    path = getattr(request.app.state, "local_store_path", None)
    if not configured:
        return StorageStatusResponse(
            status="unavailable",
            reason="not_configured",
            supported_record_types=("offline_fixture_sessions", "synthetic_evaluation_reports"),
        )
    if path is not None:
        try:
            LocalRecordStore.open_existing(path)
            return StorageStatusResponse(
                status="available",
                reason="ready",
                supported_record_types=("offline_fixture_sessions", "synthetic_evaluation_reports"),
            )
        except LocalStoreError:
            pass
    return StorageStatusResponse(
        status="unavailable",
        reason="unavailable",
        supported_record_types=("offline_fixture_sessions", "synthetic_evaluation_reports"),
    )


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def dashboard_summary(request: Request) -> DashboardSummaryResponse:
    """Aggregate counts from persisted offline runs, not demo fixtures."""

    store = _local_store(request)
    try:
        return DashboardSummaryResponse(**store.dashboard_summary())
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/sessions",
    response_model=OfflineSessionListResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def list_sessions(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> OfflineSessionListResponse:
    """List persisted offline fixture runs in stable, bounded pages."""

    store = _local_store(request)
    try:
        rows, total = store.list_sessions(offset=offset, limit=limit)
        items: list[OfflineSessionResponse] = []
        for row in rows:
            detail = store.get_session(row["session_id"])
            if detail is None:
                raise LocalStoreError("session disappeared during read")
            payload = detail["payload"]
            items.append(
                OfflineSessionResponse(
                    **{
                        **row,
                        "is_synthetic": bool(row["is_synthetic"]),
                        "is_empirical": bool(row["is_empirical"]),
                    },
                    result=payload.get("result", {}),
                    case_context=payload.get("case_context"),
                )
            )
        return OfflineSessionListResponse(items=tuple(items), total=total, offset=offset, limit=limit)
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/sessions/{session_id}",
    response_model=OfflineSessionResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_session(
    request: Request,
    session_id: Annotated[str, Path(pattern=r"^session_[0-9a-f]{32}$")],
) -> OfflineSessionResponse:
    store = _local_store(request)
    try:
        row = store.get_session(session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Stored offline session was not found.")
        payload = row["payload"]
        return OfflineSessionResponse(
            session_id=row["session_id"],
            report_id=row["report_id"],
            run_id=row["run_id"],
            runner_id=row["runner_id"],
            case_id=row["case_id"],
            repeat_index=row["repeat_index"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            disposition=row["disposition"],
            fixture_dataset_id=row["fixture_dataset_id"],
            fixture_dataset_version=row["fixture_dataset_version"],
            execution_mode=row["execution_mode"],
            is_synthetic=bool(row["is_synthetic"]),
            is_empirical=bool(row["is_empirical"]),
            result=payload.get("result", {}),
            case_context=payload.get("case_context"),
        )
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


def _finding_list(
    request: Request,
    *,
    offset: int,
    limit: int,
    session_id: str | None = None,
) -> FindingListResponse:
    store = _local_store(request)
    try:
        if session_id is None:
            rows, total = store.all_findings(offset=offset, limit=limit)
        else:
            rows, total = store.findings_for_session(
                session_id, offset=offset, limit=limit
            )
        return FindingListResponse(
            items=tuple(
                FindingResponse(**{**row, "evidence_refs": tuple(row["evidence_refs"])})
                for row in rows
            ),
            total=total,
            offset=offset,
            limit=limit,
        )
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/findings",
    response_model=FindingListResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def list_findings(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FindingListResponse:
    return _finding_list(request, offset=offset, limit=limit)


@router.get(
    "/sessions/{session_id}/findings",
    response_model=FindingListResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def list_session_findings(
    request: Request,
    session_id: Annotated[str, Path(pattern=r"^session_[0-9a-f]{32}$")],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FindingListResponse:
    try:
        if _local_store(request).get_session(session_id) is None:
            raise HTTPException(status_code=404, detail="Stored offline session was not found.")
        return _finding_list(request, offset=offset, limit=limit, session_id=session_id)
    except HTTPException:
        raise
    except LocalStoreError:
        raise _store_failure() from None


@router.get(
    "/findings/{finding_id}",
    response_model=FindingResponse,
    tags=["records"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_finding(
    request: Request,
    finding_id: Annotated[str, Path(pattern=r"^finding_[0-9a-f]{32}$")],
) -> FindingResponse:
    store = _local_store(request)
    try:
        row = store.get_finding(finding_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Stored finding was not found.")
        row["evidence_refs"] = tuple(row["evidence_refs"])
        return FindingResponse(**row)
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/reports",
    response_model=EvaluationReportListResponse,
    tags=["reports"],
    dependencies=[Depends(require_permission("records:read"))],
)
def list_reports(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EvaluationReportListResponse:
    store = _local_store(request)
    try:
        rows, total = store.list_reports(offset=offset, limit=limit)
        items = tuple(
            EvaluationReportResponse(
                **{
                    **row,
                    "is_synthetic": bool(row["is_synthetic"]),
                    "is_empirical": bool(row["is_empirical"]),
                }
            )
            for row in rows
        )
        return EvaluationReportListResponse(items=items, total=total, offset=offset, limit=limit)
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/reports/{report_id}",
    response_model=EvaluationReportResponse,
    tags=["reports"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_report(
    request: Request,
    report_id: Annotated[str, Path(pattern=r"^report_[0-9a-f]{32}$")],
) -> EvaluationReportResponse:
    store = _local_store(request)
    try:
        row = store.get_report(report_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Stored evaluation report was not found.")
        payload = row["payload"]
        score_summary = payload.get("score_summary", {})
        if not isinstance(score_summary, dict):
            raise LocalStoreError("stored report summary is malformed")
        return EvaluationReportResponse(
            report_id=row["report_id"],
            created_at=row["created_at"],
            fixture_dataset_id=row["fixture_dataset_id"],
            fixture_dataset_version=row["fixture_dataset_version"],
            runner_condition=row["runner_condition"],
            runner_id=row["runner_id"],
            execution_status=row["execution_status"],
            is_synthetic=bool(row["is_synthetic"]),
            is_empirical=bool(row["is_empirical"]),
            incomplete_case_count=row["incomplete_case_count"],
            failed_case_count=row["failed_case_count"],
            total_cases=score_summary.get("total_cases", 0),
            summary=score_summary,
            trial_agreement=payload.get("trial_agreement", {}),
            payload=payload,
        )
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


def _approved_evidence(request: Request) -> tuple[ApprovedEvidenceResponse, ...]:
    """Read evidence through an explicitly supplied, existing review registry."""

    configured = getattr(request.app.state, "source_review_registry", None)
    if not isinstance(configured, PersistentSourceReviewRegistry):
        raise HTTPException(
            status_code=503,
            detail="Approved evidence registry is not configured.",
        )

    try:
        # Do not trust a caller-supplied instance's writable connection mode.
        # Reopen its paths through the non-bootstrapping, read-only constructor.
        registry = PersistentSourceReviewRegistry.open_existing(
            configured.database_path,
            manifest_path=configured.manifest_path,
            repository_root=configured.repository_root,
        )
        chunks = registry.approved_chunks()
        records = registry.records()
    except (SourceReviewError, sqlite3.Error, OSError):
        # Internal paths and database diagnostics can reveal local filesystem
        # information. Keep API failures generic and fail closed.
        raise HTTPException(
            status_code=503,
            detail="Approved evidence registry is unavailable or inconsistent.",
        ) from None

    current_records = {
        record.metadata.source_id: record
        for record in records
        if record.is_current and record.metadata.review_state.value == "approved"
    }
    result: list[ApprovedEvidenceResponse] = []
    for chunk in chunks:
        record = current_records.get(chunk.provenance.source_id)
        if record is None:
            # A selector/record disagreement is an integrity failure, never a
            # reason to return a partial response.
            raise HTTPException(
                status_code=503,
                detail="Approved evidence registry is unavailable or inconsistent.",
            )
        result.append(_evidence_response(chunk, record))
    return tuple(result)


def _evidence_response(
    chunk: SourceChunk, record: SourceReviewRecord
) -> ApprovedEvidenceResponse:
    metadata = record.metadata
    approved_event = next(
        (event for event in reversed(record.events) if event.action == "approved"),
        None,
    )
    return ApprovedEvidenceResponse(
        source=EvidenceSourceResponse(
            source_id=metadata.source_id,
            review_state="approved",
            revision=record.revision,
            content_sha256=metadata.content_sha256,
            title=metadata.title,
            publisher=metadata.publisher,
            canonical_reference=_safe_canonical_reference(metadata.canonical_reference),
            publication_date=metadata.publication_date,
            version=metadata.version,
            acquired_at=metadata.acquired_at,
            source_type=metadata.source_type,
            scope_tags=metadata.scope_tags,
            review_event_count=len(record.events),
            approved_at=approved_event.occurred_at if approved_event else None,
        ),
        chunk=EvidenceChunkResponse(
            evidence_id=chunk.chunk_id,
            ordinal=chunk.ordinal,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            section=chunk.section,
            excerpt=chunk.content,
            content_sha256=chunk.content_sha256,
            citation_source_id=metadata.source_id,
            citation_chunk_id=chunk.chunk_id,
        ),
    )


def _safe_canonical_reference(value: str | None) -> str | None:
    """Return only a credential-free HTTPS locator without query parameters."""

    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        if (
            parsed.scheme.lower() != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
        ):
            return None
        # Fragments can also contain private tokens; the source's stable URL
        # remains useful without them.
        return urlunsplit(("https", parsed.netloc, parsed.path, "", ""))
    except ValueError:
        return None


@router.get(
    "/evidence/approved",
    response_model=ApprovedEvidenceListResponse,
    tags=["evidence"],
    dependencies=[Depends(require_permission("evidence:read"))],
)
def list_approved_evidence(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApprovedEvidenceListResponse:
    """Return a deterministic page of chunks verified as approved by the registry."""

    items = _approved_evidence(request)
    source_count = len({item.source.source_id for item in items})
    return ApprovedEvidenceListResponse(
        items=items[offset : offset + limit],
        total=len(items),
        approved_source_count=source_count,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/evidence/approved/{evidence_id}",
    response_model=ApprovedEvidenceResponse,
    tags=["evidence"],
    dependencies=[Depends(require_permission("evidence:read"))],
)
def get_approved_evidence(
    request: Request,
    evidence_id: Annotated[
        str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    ],
) -> ApprovedEvidenceResponse:
    """Return one approved chunk by its stable registry chunk identifier."""

    for item in _approved_evidence(request):
        if item.chunk.evidence_id == evidence_id:
            return item
    raise HTTPException(status_code=404, detail="Approved evidence was not found.")
