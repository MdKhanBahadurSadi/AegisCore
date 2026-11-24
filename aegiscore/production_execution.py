"""Production adapter connecting trusted target policy to loopback HTTP HEAD."""

from __future__ import annotations

import ipaddress
import uuid
from urllib.parse import urlsplit

from aegiscore.execution import (
    DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    AssessmentExecutionEngine,
)
from aegiscore.guarded_execution import DispatchResult, GuardedExecutionBoundary
from aegiscore.safety import (
    ApprovedTargetRegistration,
    CaseProfilePolicy,
    EmergencyStop,
    OperationDataLimits,
    OperationIntent,
    OperationPermit,
    PolicyEngine,
    RequestBudget,
    SafetyConfiguration,
    ScopePolicy,
    TargetRegistry,
    TimeoutPolicy,
)
from aegiscore.authorization_verification import (
    AuthorizationFailureReason,
    AuthorizationVerifier,
    AuthorizationVerificationError,
    VerifiedAuthorizationEvidence,
    verify_authorization,
)
from aegiscore.target_authorization import (
    TargetAuthorizationError,
    canonicalize_registered_endpoint,
    validate_target_registry,
)


_CASE_ID = "passive-header-observation"
_PROFILE_ID = "head-only-v1"


class ProductionExecutionDenied(RuntimeError):
    """A policy or transport result did not authorize a production dispatch."""


class _LoopbackHTTPTransport:
    """Dispatch only a consumed permit for one exact, configured HEAD endpoint."""

    def __init__(
        self,
        registration: ApprovedTargetRegistration,
        canonical_endpoint: str,
        authorization_verifier: AuthorizationVerifier,
        expected_issuer_id: str,
        engine: AssessmentExecutionEngine | None = None,
    ) -> None:
        self._registration = registration
        self._canonical_endpoint = canonical_endpoint
        self._authorization_verifier = authorization_verifier
        self._expected_issuer_id = expected_issuer_id
        self._engine = engine or AssessmentExecutionEngine()

    def dispatch(self, operation, permit: OperationPermit) -> object:
        if (
            operation is not permit.operation
            or operation.target_id != self._registration.target_id
            or operation.target_registration_version != self._registration.registration_version
            or operation.method != "HEAD"
            or operation.path not in self._registration.permitted_paths
            or operation.parameters
            or operation.headers
            or operation.body is not None
        ):
            raise ProductionExecutionDenied("guarded operation does not match the authorized passive endpoint")
        parsed = urlsplit(self._canonical_endpoint)
        host = parsed.hostname
        if not host:
            raise ProductionExecutionDenied("authorized endpoint is malformed")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            raise ProductionExecutionDenied("authorized endpoint is not numeric loopback") from None
        if (
            not address.is_loopback
            or operation.origin != _canonical_origin(self._registration)
            or self._canonical_endpoint != f"{operation.origin}{operation.path}"
        ):
            raise ProductionExecutionDenied("guarded operation origin or path does not match authorization")
        # Authorization is rechecked after the guarded permit is consumed and
        # immediately before the HTTP engine can open a socket. The verifier also
        # refreshes the authoritative revocation state on every call.
        latest_evidence = verify_authorization(
            self._authorization_verifier,
            self._registration,
            self._canonical_endpoint,
        )
        if latest_evidence.issuer_id != self._expected_issuer_id:
            raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
        return self._engine.execute_connectivity_observation(self._canonical_endpoint)


def _canonical_origin(registration: ApprovedTargetRegistration) -> str:
    address = ipaddress.ip_address(registration.hostname)
    host = f"[{address.compressed}]" if address.version == 6 else address.compressed
    return f"{registration.scheme}://{host}:{registration.port}"


def _configuration_for(
    registration: ApprovedTargetRegistration,
    path: str,
) -> SafetyConfiguration:
    target_registry = TargetRegistry((registration,))
    scope = ScopePolicy(
        policy_id=f"assessment-{registration.target_id}",
        version=registration.registration_version,
        target_ids=frozenset({registration.target_id}),
        allowed_schemes=frozenset({registration.scheme}),
        allowed_hostnames=frozenset({registration.hostname}),
        allowed_ports=frozenset({registration.port}),
        permitted_paths_by_target={registration.target_id: frozenset({path})},
    )
    return SafetyConfiguration(
        registry=target_registry,
        scope=scope,
        request_budget=RequestBudget(max_requests=1, max_redirects=0),
        timeouts=TimeoutPolicy(
            per_request_seconds=DEFAULT_EXECUTION_TIMEOUT_SECONDS,
            max_run_seconds=DEFAULT_EXECUTION_TIMEOUT_SECONDS,
        ),
        emergency_stop=EmergencyStop(active=False),
        case_profiles=(CaseProfilePolicy(
            target_id=registration.target_id,
            case_id=_CASE_ID,
            profile_id=_PROFILE_ID,
            version=registration.registration_version,
            allowed_methods=frozenset({"HEAD"}),
            permitted_paths=frozenset({path}),
            permitted_parameter_names=frozenset(),
            permitted_header_names=frozenset(),
            allow_body=False,
        ),),
        operation_data_limits=OperationDataLimits(
            version="passive-head-v1",
            max_parameters=0,
            max_query_bytes=0,
            max_headers=0,
            max_header_bytes=0,
            max_body_bytes=0,
        ),
    )


class AuthorizedAssessmentExecutor:
    """Resolve persisted authorization and dispatch only through the guarded boundary."""

    def __init__(self, registry: TargetRegistry, verifier: AuthorizationVerifier) -> None:
        validate_target_registry(registry)
        if verifier is None or not callable(getattr(verifier, "verify", None)):
            raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)
        self._registry = registry
        self._verifier = verifier

    def validate_binding(
        self, assessment: dict[str, object]
    ) -> tuple[ApprovedTargetRegistration, str, VerifiedAuthorizationEvidence]:
        target_id = assessment.get("target_id")
        canonical_endpoint = assessment.get("canonical_endpoint")
        target_url = assessment.get("target_url")
        authorization_ref = assessment.get("authorization_ref")
        registration_version = assessment.get("registration_version")
        stored_provenance = assessment.get("authorization_provenance")
        if not all(isinstance(item, str) and item for item in (
            target_id, canonical_endpoint, target_url, authorization_ref, registration_version,
        )):
            raise TargetAuthorizationError("assessment has no complete authorized target binding")
        registration = self._registry.get(target_id)
        if registration is None or not registration.enabled:
            raise TargetAuthorizationError("assessment target is no longer authorized")
        if (
            authorization_ref != registration.authorization_ref
            or registration_version != registration.registration_version
        ):
            raise TargetAuthorizationError("assessment target authorization has changed")
        try:
            verified_endpoint = canonicalize_registered_endpoint(canonical_endpoint, registration)
        except TargetAuthorizationError:
            raise TargetAuthorizationError("assessment endpoint is no longer authorized") from None
        if verified_endpoint != canonical_endpoint or target_url != canonical_endpoint:
            raise TargetAuthorizationError("assessment endpoint binding does not match persisted target")
        if not isinstance(stored_provenance, dict):
            raise TargetAuthorizationError("assessment has no verified authorization provenance")
        if (
            stored_provenance.get("authorization_ref") != authorization_ref
            or stored_provenance.get("target_id") != target_id
            or stored_provenance.get("canonical_endpoint") != canonical_endpoint
            or stored_provenance.get("registration_version") != registration_version
            or stored_provenance.get("signature_valid") is not True
            or stored_provenance.get("revoked") is not False
        ):
            raise TargetAuthorizationError("persisted authorization provenance does not match its target binding")
        evidence = verify_authorization(self._verifier, registration, verified_endpoint)
        if stored_provenance.get("issuer_id") != evidence.issuer_id:
            raise AuthorizationVerificationError(
                AuthorizationFailureReason.INVALID_EVIDENCE
            )
        return registration, verified_endpoint, evidence

    def execute(self, assessment: dict[str, object]) -> dict[str, object]:
        registration, endpoint, evidence = self.validate_binding(assessment)
        parsed = urlsplit(endpoint)
        path = parsed.path or "/"
        configuration = _configuration_for(registration, path)
        policy_engine = PolicyEngine(configuration)
        transport = _LoopbackHTTPTransport(
            registration,
            endpoint,
            self._verifier,
            evidence.issuer_id,
        )
        boundary = GuardedExecutionBoundary(policy_engine, transport)
        intent = OperationIntent(
            operation_id=f"head-{uuid.uuid4().hex}",
            target_id=registration.target_id,
            method="HEAD",
            path=path,
            parameters=(),
            case_id=_CASE_ID,
            profile_id=_PROFILE_ID,
            headers=(),
            body=None,
        )
        authorization = boundary.authorize(intent)
        if not authorization.allowed:
            raise ProductionExecutionDenied("guarded policy denied the authorized endpoint")
        dispatched: DispatchResult = boundary.dispatch(authorization, intent)
        if not dispatched.allowed or not isinstance(dispatched.result, dict):
            raise ProductionExecutionDenied("guarded transport did not complete an authorized dispatch")
        if dispatched.result.get("connected_peer") != ipaddress.ip_address(parsed.hostname or "").compressed:
            # Connection failures remain a normal failed assessment; a response without
            # a verified peer can never be treated as reachable or analyzed.
            if dispatched.result.get("reachable"):
                raise ProductionExecutionDenied("connected peer did not match the authorized target")
        result = dict(dispatched.result)
        result["authorization_verification"] = evidence.to_record()
        return result
