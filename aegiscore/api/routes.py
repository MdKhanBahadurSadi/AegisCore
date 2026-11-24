import hashlib
import sqlite3
from datetime import datetime, timezone
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
from aegiscore.authorization_verification import (
    AuthorizationFailureReason,
    AuthorizationVerificationError,
    verify_authorization,
)
from aegiscore.execution import (
    DEFAULT_EXECUTION_LEASE_SECONDS,
)
from aegiscore.local_persistence import LocalRecordStore, LocalStoreConflictError, LocalStoreError
from aegiscore.passive_detector import PassiveHeaderDetector
from aegiscore.target_authorization import TargetAuthorizationError, resolve_authorized_endpoint
from aegiscore.api.schemas import (
    ApprovedEvidenceListResponse,
    ApprovedEvidenceResponse,
    AssessmentCreateRequest,
    AssessmentEvidenceListResponse,
    AssessmentEvidenceResponse,
    AssessmentFindingItemResponse,
    AssessmentFindingListResponse,
    AssessmentListResponse,
    AssessmentResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthSessionResponse,
    CapabilitiesResponse,
    DashboardSummaryResponse,
    EvaluationReportListResponse,
    EvaluationReportResponse,
    EvidenceChunkResponse,
    EvidenceSourceResponse,
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


def _writable_local_store(request: Request) -> LocalRecordStore:
    configured_path = getattr(request.app.state, "local_store_path", None)
    if configured_path is None:
        raise HTTPException(
            status_code=503,
            detail="Local persistence store is not configured or is unavailable.",
        )
    try:
        return LocalRecordStore.create_or_open(configured_path)
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


def _authorization_failure(exc: AuthorizationVerificationError, *, creating: bool = False) -> HTTPException:
    if exc.reason is AuthorizationFailureReason.UNAVAILABLE:
        return HTTPException(status_code=503, detail="Authorization verification is unavailable.")
    if creating:
        return HTTPException(status_code=403, detail="Target authorization could not be verified.")
    return HTTPException(status_code=409, detail="Target authorization is invalid, expired, or revoked.")


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


@router.post(
    "/assessments",
    response_model=AssessmentResponse,
    status_code=201,
    tags=["assessments"],
    dependencies=[Depends(require_permission("assessments:create"))],
    responses={
        201: {"description": "Assessment successfully created and persisted."},
        400: {"description": "Target URL violates lab scope, scheme, credentials, or port rules."},
        401: {"description": "Authentication required or credentials are invalid."},
        403: {"description": "Authenticated account lacks 'assessments:create' permission."},
        422: {"description": "Request payload validation error."},
        503: {"description": "Authentication or local persistence store is not configured or unavailable."},
    },
)
def create_assessment(
    request: Request,
    payload: AssessmentCreateRequest,
    session: Annotated[AuthenticatedSession, Depends(require_session)],
) -> AssessmentResponse:
    """Validate target URL scope and persist a new target assessment record.

    Authentication:
        Bearer token required (Authorization: Bearer <token>).

    Required Permission:
        'assessments:create' (Read-only 'records:read' permission is insufficient).

    Responses:
        201: Assessment successfully created and persisted.
        400: Target URL violates lab scope, scheme, credentials, or port rules.
        401: Unauthenticated request or invalid credentials.
        403: Authenticated account lacks 'assessments:create' permission.
        422: Request payload validation error.
        503: Authentication or local persistence store is not configured or unavailable.
    """

    registry = getattr(request.app.state, "authorized_target_registry", None)
    verifier = getattr(request.app.state, "authorization_verifier", None)
    if registry is None or verifier is None:
        raise HTTPException(status_code=503, detail="Authorization verification is unavailable.")
    try:
        registration, canonical_endpoint = resolve_authorized_endpoint(registry, payload.target_url)
    except TargetAuthorizationError:
        raise HTTPException(status_code=400, detail="Target endpoint is not authorized.") from None
    try:
        authorization_evidence = verify_authorization(verifier, registration, canonical_endpoint)
    except AuthorizationVerificationError as exc:
        raise _authorization_failure(exc, creating=True) from None

    store = _writable_local_store(request)
    try:
        record = store.create_assessment(
            target_url=canonical_endpoint,
            target_id=registration.target_id,
            canonical_endpoint=canonical_endpoint,
            authorization_ref=registration.authorization_ref,
            registration_version=registration.registration_version,
            authorization_provenance=authorization_evidence.to_record(),
        )
        return AssessmentResponse(**record)
    except LocalStoreError:
        raise _store_failure() from None


@router.get(
    "/assessments",
    response_model=AssessmentListResponse,
    tags=["assessments"],
    dependencies=[Depends(require_permission("records:read"))],
)
def list_assessments(
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AssessmentListResponse:
    """List persisted assessment records in stable, bounded pages."""

    store = _local_store(request)
    try:
        rows, total = store.list_assessments(offset=offset, limit=limit)
        items = [AssessmentResponse(**row) for row in rows]
        return AssessmentListResponse(items=tuple(items), total=total, offset=offset, limit=limit)
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResponse,
    tags=["assessments"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_assessment(
    request: Request,
    assessment_id: Annotated[str, Path(pattern=r"^asm_[0-9a-f]{32}$")],
) -> AssessmentResponse:
    """Fetch a single persisted assessment record by its unique identifier."""

    store = _local_store(request)
    try:
        row = store.get_assessment(assessment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Stored assessment was not found.")
        return AssessmentResponse(**row)
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.post(
    "/assessments/{assessment_id}/execute",
    response_model=AssessmentResponse,
    status_code=200,
    tags=["assessments"],
    dependencies=[Depends(require_permission("assessments:execute"))],
    responses={
        200: {"description": "Assessment execution completed successfully."},
        400: {"description": "Assessment is not eligible for execution or target URL is invalid."},
        401: {"description": "Authentication required or credentials are invalid."},
        403: {"description": "Authenticated account lacks 'assessments:execute' permission."},
        404: {"description": "Target assessment was not found."},
        409: {"description": "Assessment is currently executing or already terminal."},
        503: {"description": "Authentication or local persistence store is not configured or unavailable."},
    },
)
def execute_assessment(
    request: Request,
    assessment_id: Annotated[str, Path(pattern=r"^asm_[0-9a-f]{32}$")],
    session: Annotated[AuthenticatedSession, Depends(require_session)],
) -> AssessmentResponse:
    """Execute a passive HTTP HEAD connectivity observation for a persisted assessment.

    Authentication:
        Bearer token required (Authorization: Bearer <token>).

    Required Permission:
        'assessments:execute' (Read-only 'records:read' permission is insufficient).

    Responses:
        200: Bounded passive observation completed and persisted.
        400: Target URL violates lab scope or validation rules.
        401: Unauthenticated request or invalid credentials.
        403: Authenticated account lacks 'assessments:execute' permission.
        404: Target assessment ID was not found.
        409: Assessment is currently executing or has already completed execution.
        503: Authentication or local persistence store is not configured or unavailable.
    """

    store = _writable_local_store(request)
    lease_token: str | None = None
    try:
        assessment = store.get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="Target assessment was not found.")

        executor = getattr(request.app.state, "assessment_executor", None)
        if executor is None:
            raise HTTPException(status_code=503, detail="Authorized target configuration is unavailable.")
        try:
            executor.validate_binding(assessment)
        except TargetAuthorizationError:
            raise HTTPException(status_code=409, detail="Assessment target authorization is missing or no longer valid.") from None
        except AuthorizationVerificationError as exc:
            raise _authorization_failure(exc) from None

        try:
            running_record = store.update_assessment_status(
                assessment_id=assessment_id,
                new_status="running",
                lease_duration_seconds=DEFAULT_EXECUTION_LEASE_SECONDS,
            )
            lease_token = running_record.get("lease_token")
        except LocalStoreConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail="Assessment is currently executing or has already completed.",
            ) from exc

        # The API has no direct HTTP-engine access. The production executor revalidates
        # the persisted binding, obtains a one-use policy permit, then dispatches via
        # GuardedExecutionBoundary to the peer-checking loopback transport.
        execution_assessment = store.get_assessment(assessment_id)
        if execution_assessment is None:
            raise HTTPException(status_code=404, detail="Target assessment was not found.")
        result = executor.execute(execution_assessment)
        target_url = execution_assessment["target_url"]

        # Normalize evidence and run passive rule detector engine
        raw_hash = hashlib.sha256(f"{assessment_id}\0{result.get('executed_at')}".encode("utf-8")).hexdigest()[:32]
        collection_status = "observed" if result["reachable"] else ("unreachable" if "unreachable" in result["outcome"].lower() else "failed")
        evidence_record = {
            "evidence_id": f"evi_{raw_hash}",
            "assessment_id": assessment_id,
            "evidence_type": "http_security_headers",
            "source": "passive_head_observation",
            "observed_at": result.get("executed_at", datetime.now(timezone.utc).isoformat()),
            "http_method": "HEAD",
            "http_status": result.get("http_status"),
            "normalized_headers": result.get("captured_headers", {}),
            "header_flags": result.get("header_flags", {}),
            "collection_status": collection_status,
            "provenance": {
                "duration_ms": result.get("duration_ms"),
                "redirect_detected": result.get("redirect_detected", False),
                "outcome": result.get("outcome"),
            },
        }

        findings = PassiveHeaderDetector.analyze(assessment_id, target_url, evidence_record)
        reviewer = getattr(request.app.state, "assessment_ai_reviewer", None)
        if reviewer is None:
            if getattr(request.app.state, "assessment_ai_configuration_invalid", False):
                ai_review = {
                    "status": "unavailable",
                    "analysis_type": "advisory_inference",
                    "confidence_calibrated": False,
                    "factual_support": "not_evaluated",
                    "failure_code": "invalid_configuration",
                    "reviews": [],
                }
            else:
                ai_review = {
                    "status": "disabled",
                    "analysis_type": "advisory_inference",
                    "confidence_calibrated": False,
                    "factual_support": "not_evaluated",
                    "reviews": [],
                }
        else:
            try:
                ai_review = reviewer.review_safely(evidence_record, findings)
            except Exception:
                # An unexpected AI integration fault cannot alter deterministic findings
                # or the assessment's network-derived terminal status.
                ai_review = {
                    "status": "unavailable",
                    "analysis_type": "advisory_inference",
                    "confidence_calibrated": False,
                    "factual_support": "not_evaluated",
                    "failure_code": "analysis_unavailable",
                    "reviews": [],
                }
        result["ai_review"] = ai_review
        final_status = "completed" if result["reachable"] else "failed"

        # Atomically save evidence, findings, and status transition in a single SQLite transaction with lease validation
        final_record = store.save_pipeline_result(
            assessment_id=assessment_id,
            evidence=evidence_record,
            findings=findings,
            final_status=final_status,
            execution_result=result,
            lease_token=lease_token,
        )
        return AssessmentResponse(**final_record)

    except HTTPException:
        raise
    except LocalStoreError:
        raise _store_failure() from None
    except AuthorizationVerificationError as exc:
        if lease_token:
            try:
                store.update_assessment_status(
                    assessment_id=assessment_id,
                    new_status="failed",
                    execution_result={
                        "reachable": False,
                        "outcome": "Authorization verification failed before network execution",
                    },
                    lease_token=lease_token,
                )
            except LocalStoreError:
                raise _store_failure() from None
        raise _authorization_failure(exc) from None
    except Exception:
        if lease_token:
            try:
                store.update_assessment_status(
                    assessment_id=assessment_id,
                    new_status="failed",
                    execution_result={
                        "reachable": False,
                        "outcome": "Execution failed due to an internal execution error",
                    },
                    lease_token=lease_token,
                )
            except LocalStoreError:
                pass
        raise _store_failure() from None


@router.get(
    "/assessments/{assessment_id}/evidence",
    response_model=AssessmentEvidenceListResponse,
    tags=["assessments"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_assessment_evidence(
    request: Request,
    assessment_id: Annotated[str, Path(pattern=r"^asm_[0-9a-f]{32}$")],
) -> AssessmentEvidenceListResponse:
    """List normalized evidence records collected during assessment execution."""

    store = _local_store(request)
    try:
        assessment = store.get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="Target assessment was not found.")
        rows = store.list_evidence(assessment_id)
        items = [AssessmentEvidenceResponse(**r) for r in rows]
        return AssessmentEvidenceListResponse(items=tuple(items), total=len(items))
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None


@router.get(
    "/assessments/{assessment_id}/findings",
    response_model=AssessmentFindingListResponse,
    tags=["assessments"],
    dependencies=[Depends(require_permission("records:read"))],
)
def get_assessment_findings(
    request: Request,
    assessment_id: Annotated[str, Path(pattern=r"^asm_[0-9a-f]{32}$")],
) -> AssessmentFindingListResponse:
    """List security configuration observations emitted by rule detectors for an assessment."""

    store = _local_store(request)
    try:
        assessment = store.get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="Target assessment was not found.")
        rows = store.list_findings(assessment_id)
        items = [AssessmentFindingItemResponse(**r) for r in rows]
        return AssessmentFindingListResponse(items=tuple(items), total=len(items))
    except HTTPException:
        raise
    except (LocalStoreError, ValueError, TypeError):
        raise _store_failure() from None
