"""Typed response models for the read-only backend foundation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


CapabilityId = Literal[
    "api.health_endpoint",
    "api.capabilities_endpoint",
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


class CapabilitiesResponse(BaseModel):
    """Static implementation inventory; it does not report lab readiness."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["aegiscore-api"] = "aegiscore-api"
    version: Literal["0.1.0"] = "0.1.0"
    implemented: tuple[CapabilityId, ...] = (
        "api.health_endpoint",
        "api.capabilities_endpoint",
        "safety.in_memory_policy_contracts",
        "safety.fake_transport_only_guarded_execution_contract",
    )
    not_implemented: tuple[CapabilityId, ...] = (
        "backend.real_target_transport",
        "backend.rag",
        "backend.multi_agent_orchestration",
        "backend.vulnerability_assessment_workflow",
        "backend.external_llm_provider",
        "backend.persistent_application_storage",
    )
