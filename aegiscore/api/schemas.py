"""Typed response models for the read-only backend foundation."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CapabilityId = Literal[
    "api.health_endpoint",
    "api.capabilities_endpoint",
    "api.approved_evidence_endpoints",
    "api.persisted_workflow_read_endpoints",
    "api.dashboard_summary_endpoint",
    "api.local_authentication",
    "api.read_permission_authorization",
    "api.loopback_access_boundary",
    "safety.in_memory_policy_contracts",
    "safety.fake_transport_only_guarded_execution_contract",
    "backend.real_target_transport",
    "backend.rag",
    "backend.multi_agent_orchestration",
    "backend.vulnerability_assessment_workflow",
    "backend.external_llm_provider",
    "backend.persistent_application_storage",
]


class HealthResponse(BaseModel):
    """Confirms only that this API process can answer an in-process request."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class AuthLoginRequest(BaseModel):
    """Credentials for the one locally provisioned account."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024, repr=False)


class AuthLoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(ge=1, le=86400)


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: Literal[True] = True
    username: str
    permissions: tuple[Literal["records:read", "evidence:read"], ...]
    expires_in: int = Field(ge=0, le=86400)


class AuthLogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["signed_out"] = "signed_out"


class CapabilitiesResponse(BaseModel):
    """Static implementation inventory; it does not report lab readiness."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["aegiscore-api"] = "aegiscore-api"
    version: Literal["0.1.0"] = "0.1.0"
    implemented: tuple[CapabilityId, ...] = (
        "api.health_endpoint",
        "api.capabilities_endpoint",
        "api.approved_evidence_endpoints",
        "api.persisted_workflow_read_endpoints",
        "api.dashboard_summary_endpoint",
        "api.local_authentication",
        "api.read_permission_authorization",
        "api.loopback_access_boundary",
        "safety.in_memory_policy_contracts",
        "safety.fake_transport_only_guarded_execution_contract",
        "backend.persistent_application_storage",
    )
    not_implemented: tuple[CapabilityId, ...] = (
        "backend.real_target_transport",
        "backend.rag",
        "backend.multi_agent_orchestration",
        "backend.vulnerability_assessment_workflow",
        "backend.external_llm_provider",
    )


class EvidenceSourceResponse(BaseModel):
    """Approved source metadata without local filesystem paths or reviewer labels."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    review_state: Literal["approved"]
    revision: int = Field(ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    title: str | None
    publisher: str | None
    canonical_reference: str | None
    publication_date: str | None
    version: str | None
    acquired_at: str | None
    source_type: str | None
    scope_tags: tuple[str, ...] | None
    review_event_count: int = Field(ge=0)
    approved_at: str | None


class EvidenceChunkResponse(BaseModel):
    """An exact approved chunk and the citation pair supported by the registry."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    ordinal: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    section: str | None
    excerpt: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    citation_source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    citation_chunk_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

    @model_validator(mode="after")
    def validate_excerpt_integrity(self) -> EvidenceChunkResponse:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        if self.end_offset - self.start_offset != len(self.excerpt):
            raise ValueError("excerpt length must match its character offsets")
        if hashlib.sha256(self.excerpt.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("excerpt digest does not match its exact text")
        return self


class ApprovedEvidenceResponse(BaseModel):
    """Approved source provenance and one unchanged source chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source: EvidenceSourceResponse
    chunk: EvidenceChunkResponse

    @model_validator(mode="after")
    def validate_citation_identity(self) -> ApprovedEvidenceResponse:
        if (
            self.source.source_id != self.chunk.citation_source_id
            or self.chunk.evidence_id != self.chunk.citation_chunk_id
        ):
            raise ValueError("citation identity must match the approved source and chunk")
        return self


class ApprovedEvidenceListResponse(BaseModel):
    """Stable page of approved evidence chunks from the persistent registry."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    items: tuple[ApprovedEvidenceResponse, ...]
    total: int = Field(ge=0)
    approved_source_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)


class PageResponse(BaseModel):
    """Shared pagination envelope for persisted records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)


class OfflineSessionResponse(BaseModel):
    """One actual offline harness run, explicitly marked synthetic."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    session_id: str
    report_id: str
    run_id: str
    runner_id: str
    case_id: str
    repeat_index: int = Field(ge=0)
    started_at: str | None
    ended_at: str | None
    status: Literal["completed", "incomplete", "failed"]
    disposition: Literal["verified", "rejected", "abstained"]
    fixture_dataset_id: str
    fixture_dataset_version: str
    execution_mode: Literal["offline_fixture"]
    is_synthetic: bool
    is_empirical: bool
    result: dict[str, Any]
    case_context: dict[str, Any] | None


class OfflineSessionListResponse(PageResponse):
    items: tuple[OfflineSessionResponse, ...]


class FindingResponse(BaseModel):
    """A finding actually emitted by an offline replay run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    finding_id: str
    source_finding_id: str
    session_id: str
    report_id: str
    case_id: str
    recorded_at: str | None
    specialist_role: str
    vulnerability_identified: bool
    cwe_id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    decision: Literal["verified", "rejected", "abstained"]
    evidence_refs: tuple[str, ...]
    rationale: str
    locus: dict[str, Any] | None
    vulnerability_class: str | None
    is_synthetic: bool
    is_empirical: bool
    execution_mode: Literal["offline_fixture"]


class FindingListResponse(PageResponse):
    items: tuple[FindingResponse, ...]


class EvaluationMetricResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    value: float | None
    definition: str
    numerator: float | int | None
    denominator: float | int | None
    aggregation_unit: str
    included_cases: int = Field(ge=0)
    excluded_cases: int = Field(ge=0)
    abstained_cases: int = Field(ge=0)
    status: Literal["computed", "undefined", "not_supported", "insufficient_data"]
    limitations: tuple[str, ...]
    ci_lower: float | None
    ci_upper: float | None
    ci_method: str | None


class EvaluationScoreSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tp_count: int = Field(ge=0)
    fp_count: int = Field(ge=0)
    fn_count: int = Field(ge=0)
    tn_count: int = Field(ge=0)
    abstained_positive_count: int = Field(ge=0)
    abstained_negative_count: int = Field(ge=0)
    total_cases: int = Field(ge=0)
    total_candidate_findings: int = Field(ge=0)
    verified_candidate_findings: int = Field(ge=0)
    metrics: dict[str, EvaluationMetricResponse]


class TrialAgreementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(ge=0)
    unanimous_cases_count: int = Field(ge=0)
    split_decision_cases_count: int = Field(ge=0)
    trial_agreement_rate: float = Field(ge=0, le=1)
    per_case_decisions: dict[str, tuple[str, ...]]
    is_deterministic_fixture_behavior: bool
    notes: str


class EvaluationReportResponse(BaseModel):
    """Metadata and real calculated metrics for a completed fixture report."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    report_id: str
    created_at: str
    fixture_dataset_id: str
    fixture_dataset_version: str
    runner_condition: str
    runner_id: str
    execution_status: Literal["completed"]
    is_synthetic: bool
    is_empirical: bool
    incomplete_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    total_cases: int = Field(ge=0)
    summary: EvaluationScoreSummaryResponse
    trial_agreement: TrialAgreementResponse
    payload: dict[str, Any] | None = None


class EvaluationReportListResponse(PageResponse):
    items: tuple[EvaluationReportResponse, ...]


class DashboardSummaryResponse(BaseModel):
    """Counts derived only from stored offline records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    session_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    incomplete_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    verified_run_count: int = Field(ge=0)
    abstained_run_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    report_count: int = Field(ge=0)
    synthetic_offline_run_count: int = Field(ge=0)
    empirical_run_count: int = Field(ge=0)


class StorageStatusResponse(BaseModel):
    """Configuration and availability of local persistence without path disclosure."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: Literal["available", "unavailable"]
    reason: Literal["ready", "not_configured", "unavailable"]
    supported_record_types: tuple[str, ...]
