"""Read-only system routes. These routes do not enter the safety workflow."""

from fastapi import APIRouter

from aegiscore.api.schemas import CapabilitiesResponse, HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report that the API process is answering; no downstream checks are implied."""

    return HealthResponse()


@router.get("/capabilities", response_model=CapabilitiesResponse, tags=["system"])
def capabilities() -> CapabilitiesResponse:
    """Return the static, implemented-versus-unimplemented backend inventory."""

    return CapabilitiesResponse()
