from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from aegiscore.guarded_execution import (
    CancellationToken,
    GuardedExecutionBoundary,
)
from aegiscore.safety import (
    ApprovedTargetRegistration,
    CaseProfilePolicy,
    ConfigurationError,
    EmergencyStop,
    OperationAuthorization,
    OperationDataLimits,
    OperationIntent,
    OperationPermit,
    PolicyEngine,
    PolicyOutcome,
    PolicyReason,
    RequestBudget,
    SafetyConfiguration,
    ScopePolicy,
    TargetRegistry,
    TimeoutPolicy,
)


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingFakeTransport:
    """In-memory transport double; every invocation and accepted call is recorded."""

    def __init__(
        self,
        *,
        entered: threading.Event | None = None,
        release: threading.Event | None = None,
        fail: bool = False,
    ) -> None:
        self.attempts: list[tuple[object, object]] = []
        self.dispatches: list[tuple[object, object]] = []
        self.active = 0
        self.maximum_active = 0
        self.fail = fail
        self.entered = entered
        self.release = release
        self._lock = threading.Lock()

    def dispatch(self, operation: object, permit: object) -> object:
        with self._lock:
            self.attempts.append((operation, permit))
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        try:
            if self.entered is not None:
                self.entered.set()
            if self.release is not None and not self.release.wait(timeout=3):
                raise TimeoutError("fake transport release timed out")
            if self.fail:
                raise RuntimeError("synthetic fake transport failure")
            result = {"recorded": True, "operation_id": getattr(operation, "operation_id", None)}
            with self._lock:
                self.dispatches.append((operation, permit))
            return result
        finally:
            with self._lock:
                self.active -= 1


def make_boundary(
    *,
    max_requests: int = 5,
    max_redirects: int = 2,
    per_request_seconds: float = 5.0,
    max_run_seconds: float = 30.0,
    run_id: str = "phase4b-run",
    hostname: str = "127.0.0.1",
    stop: EmergencyStop | None = None,
    cancellation: CancellationToken | None = None,
    transport: RecordingFakeTransport | None = None,
) -> tuple[GuardedExecutionBoundary, PolicyEngine, RecordingFakeTransport, FakeClock, EmergencyStop]:
    registration = ApprovedTargetRegistration(
        target_id="juice-shop",
        scheme="http",
        hostname=hostname,
        port=3000,
        permitted_paths=("/", "/api/items"),
        authorization_ref="synthetic-test-fixture-only",
        network_zone_id="synthetic-test-zone",
        enabled=True,
        registration_version="registration-v1",
    )
    registry = TargetRegistry((registration,))
    scope = ScopePolicy(
        policy_id="unit-test-policy",
        version="scope-v1",
        target_ids=frozenset({registration.target_id}),
        allowed_schemes=frozenset({registration.scheme}),
        allowed_hostnames=frozenset({registration.hostname}),
        allowed_ports=frozenset({registration.port}),
        permitted_paths_by_target={registration.target_id: frozenset(registration.permitted_paths)},
    )
    emergency_stop = stop or EmergencyStop(active=False)
    configuration = SafetyConfiguration(
        registry=registry,
        scope=scope,
        request_budget=RequestBudget(max_requests=max_requests, max_redirects=max_redirects),
        timeouts=TimeoutPolicy(per_request_seconds, max_run_seconds),
        emergency_stop=emergency_stop,
        case_profiles=(
            CaseProfilePolicy(
                target_id=registration.target_id,
                case_id="fixture-case-1",
                profile_id="read-only-profile-v1",
                version="case-profile-v1",
                allowed_methods=frozenset({"GET", "HEAD"}),
                permitted_paths=frozenset(registration.permitted_paths),
                permitted_parameter_names=frozenset({"page", "sort", "filter"}),
                permitted_header_names=frozenset({"accept", "x-fixture", "x-extra"}),
                allow_body=True,
            ),
        ),
        operation_data_limits=OperationDataLimits(
            version="data-limits-v1",
            max_parameters=2,
            max_query_bytes=128,
            max_headers=2,
            max_header_bytes=128,
            max_body_bytes=16,
        ),
    )
    clock = FakeClock()
    engine = PolicyEngine(configuration, clock=clock, run_id=run_id)
    fake = transport or RecordingFakeTransport()
    boundary = GuardedExecutionBoundary(engine, fake, cancellation=cancellation)
    return boundary, engine, fake, clock, emergency_stop


def make_operation(
    operation_id: str = "op-1",
    *,
    target_id: str = "juice-shop",
    method: str = "GET",
    path: str = "/api/items",
    parameters: tuple[tuple[str, str], ...] = (("page", "1"),),
    case_id: str = "fixture-case-1",
    profile_id: str = "read-only-profile-v1",
    headers: tuple[tuple[str, str], ...] = (),
    body: bytes | None = None,
) -> OperationIntent:
    return OperationIntent(
        operation_id,
        target_id,
        method,
        path,
        parameters,
        case_id=case_id,
        profile_id=profile_id,
        headers=headers,
        body=body,
    )


def test_exact_engine_permit_dispatches_once_through_injected_fake() -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation(parameters=(("page", "1"), ("sort", "name")))

    authorization = boundary.authorize(operation)
    assert authorization.allowed
    assert authorization.permit is not None
    assert authorization.permit.run_id == "phase4b-run"
    assert authorization.permit.target_registration_version == "registration-v1"
    assert authorization.permit.scope_version == "scope-v1"
    assert authorization.permit.operation.parameters == (("page", "1"), ("sort", "name"))
    assert authorization.permit.operation.run_id == "phase4b-run"
    assert authorization.permit.operation.case_id == "fixture-case-1"
    assert authorization.permit.operation.profile_id == "read-only-profile-v1"
    assert authorization.permit.operation.origin == "http://127.0.0.1:3000"
    assert authorization.permit.operation.canonical_query == "page=1&sort=name"

    result = boundary.dispatch(authorization, operation)

    assert result.allowed
    assert result.transport_invoked
    assert len(fake.attempts) == 1
    assert len(fake.dispatches) == 1
    assert fake.attempts[0][0] == authorization.permit.operation


def test_canonical_headers_body_and_configured_data_boundaries_dispatch_once() -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation(
        "exact-data-limits",
        parameters=(("page", "x" * 123),),
        headers=(("Accept", "x" * 118),),
        body=b"b" * 16,
    )

    result = boundary.dispatch(boundary.authorize(operation), operation)

    assert result.allowed
    assert len(fake.attempts) == 1
    assert len(fake.dispatches) == 1
    canonical = fake.dispatches[0][0]
    assert canonical.parameters == operation.parameters
    assert canonical.canonical_query == "page=" + "x" * 123
    assert canonical.headers == (("accept", "x" * 118),)
    assert canonical.body == b"b" * 16


@pytest.mark.parametrize(
    "operation",
    [
        OperationIntent("bad target", "juice-shop", "GET", "/api/items"),
        OperationIntent("bad method", "juice-shop", "POST", "/api/items"),
        OperationIntent("bad path", "juice-shop", "GET", "/../api/items"),
        OperationIntent("bad params", "juice-shop", "GET", "/api/items", [("page", "1")]),
        OperationIntent("duplicate params", "juice-shop", "GET", "/api/items", (("page", "1"), ("page", "2"))),
        OperationIntent("url target", "http://127.0.0.1:3000", "GET", "/api/items"),
    ],
)
def test_malformed_operation_never_reaches_fake_transport(operation: OperationIntent) -> None:
    boundary, _, fake, _, _ = make_boundary()

    authorization = boundary.authorize(operation)
    result = boundary.dispatch(authorization, operation)

    assert not authorization.allowed
    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


def test_denied_target_is_terminal_and_later_valid_operation_cannot_dispatch() -> None:
    boundary, _, fake, _, _ = make_boundary()

    denied = boundary.authorize(make_operation("unknown-target", target_id="other-lab"))
    later = boundary.authorize(make_operation("later-valid"))
    result = boundary.dispatch(later, make_operation("later-valid"))

    assert denied.decision.reason is PolicyReason.UNKNOWN_TARGET
    assert later.decision.reason is PolicyReason.WORKFLOW_DENIED
    assert later.permit is None
    assert result.decision.reason is PolicyReason.WORKFLOW_DENIED
    assert not result.transport_invoked
    assert fake.attempts == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_id", "other-lab"),
        ("path", "/"),
        ("method", "HEAD"),
        ("parameters", (("page", "2"),)),
        ("operation_id", "different-op"),
    ],
)
def test_permit_cannot_authorize_altered_operation_fields(field: str, value: object) -> None:
    boundary, _, fake, _, _ = make_boundary()
    original = make_operation(parameters=(("page", "1"),))
    authorization = boundary.authorize(original)
    altered = replace(original, **{field: value})

    result = boundary.dispatch(authorization, altered)

    assert result.decision.reason is PolicyReason.PERMIT_INVALID
    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


@pytest.mark.parametrize(
    "operation",
    [
        make_operation("case-mismatch", case_id="other-case"),
        make_operation("profile-mismatch", profile_id="other-profile"),
    ],
)
def test_case_or_profile_mismatch_is_denied_without_fake_dispatch(operation: OperationIntent) -> None:
    boundary, _, fake, _, _ = make_boundary()

    authorization = boundary.authorize(operation)
    later_operation = make_operation("later-after-case-denial")
    later = boundary.authorize(later_operation)
    result = boundary.dispatch(later, later_operation)

    assert authorization.decision.reason is PolicyReason.CASE_PROFILE_NOT_PERMITTED
    assert later.decision.reason is PolicyReason.WORKFLOW_DENIED
    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "another-registered-case"),
        ("profile_id", "another-registered-profile"),
        ("path", "/"),
        ("method", "HEAD"),
        ("parameters", (("page", "2"),)),
        ("headers", (("accept", "text/plain"),)),
        ("body", b"altered-fixture"),
    ],
)
def test_permit_binds_case_and_all_request_data(field: str, value: object) -> None:
    boundary, _, fake, _, _ = make_boundary()
    original = make_operation(
        parameters=(("page", "1"),),
        headers=(("Accept", "application/json"),),
        body=b"fixture-body",
    )
    authorization = boundary.authorize(original)
    assert authorization.allowed
    altered = replace(original, **{field: value})

    result = boundary.dispatch(authorization, altered)

    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


def test_permit_binds_trusted_origin_and_registration_profile_context() -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)
    assert authorization.permit is not None

    altered_operation = replace(authorization.permit.operation, origin="http://127.0.0.2:3000")
    altered_permit = replace(authorization.permit, operation=altered_operation)
    altered_authorization = OperationAuthorization(authorization.decision, altered_permit)
    result = boundary.dispatch(altered_authorization, operation)

    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


def test_ipv6_origin_is_canonicalized_from_registered_address() -> None:
    boundary, _, fake, _, _ = make_boundary(hostname="0:0:0:0:0:0:0:1")
    operation = make_operation()

    result = boundary.dispatch(boundary.authorize(operation), operation)

    assert result.allowed
    assert fake.dispatches[0][0].origin == "http://[::1]:3000"


@pytest.mark.parametrize(
    "operation",
    [
        make_operation("unscoped-param", parameters=(("other", "1"),)),
        make_operation("duplicate-param", parameters=(("page", "1"), ("page", "2"))),
        make_operation("too-many-params", parameters=(("page", "1"), ("sort", "name"), ("filter", "x"))),
        make_operation("bad-header-name", headers=(("Bad Header", "x"),)),
        make_operation("duplicate-header", headers=(("Accept", "a"), ("accept", "b"))),
        make_operation("forbidden-header", headers=(("Host", "127.0.0.1"),)),
        make_operation("header-control", headers=(("accept", "json\r\nX-Injected: yes"),)),
        make_operation("header-surrounding-space", headers=(("accept", " json "),)),
        make_operation("too-many-headers", headers=(("accept", "a"), ("x-fixture", "b"), ("x-extra", "c"))),
        make_operation("oversized-query", parameters=(("page", "x" * 130),)),
        make_operation("oversized-header", headers=(("x-fixture", "x" * 130),)),
        make_operation("oversized-body", body=b"x" * 17),
        make_operation("mutable-body", body=bytearray(b"fixture")),
        OperationIntent("missing-case", "juice-shop", "GET", "/api/items", (("page", "1"),)),
        OperationIntent(
            "malformed-case", "juice-shop", "GET", "/api/items", (("page", "1"),),
            case_id=[], profile_id="read-only-profile-v1",
        ),
    ],
)
def test_malformed_unbounded_or_unscoped_case_data_never_dispatches(operation: OperationIntent) -> None:
    boundary, _, fake, _, _ = make_boundary()

    authorization = boundary.authorize(operation)
    result = boundary.dispatch(authorization, operation)

    assert not authorization.allowed
    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


def test_profile_without_body_permission_rejects_body_before_dispatch() -> None:
    registration = ApprovedTargetRegistration(
        "juice-shop", "http", "127.0.0.1", 3000, ("/", "/api/items"), "synthetic-fixture", "zone", True, "registration-v1"
    )
    registry = TargetRegistry((registration,))
    scope = ScopePolicy(
        "unit-test-policy", "scope-v1", frozenset({"juice-shop"}), frozenset({"http"}),
        frozenset({"127.0.0.1"}), frozenset({3000}),
        {"juice-shop": frozenset({"/", "/api/items"})},
    )
    config = SafetyConfiguration(
        registry, scope, RequestBudget(2, 1), TimeoutPolicy(5, 30), EmergencyStop(False),
        case_profiles=(CaseProfilePolicy(
            "juice-shop", "fixture-case-1", "read-only-profile-v1", "case-profile-v1",
            frozenset({"GET"}), frozenset({"/api/items"}), frozenset({"page"}), frozenset(), False,
        ),),
        operation_data_limits=OperationDataLimits("data-limits-v1", 2, 128, 0, 0, 16),
    )
    fake = RecordingFakeTransport()
    boundary = GuardedExecutionBoundary(PolicyEngine(config, clock=FakeClock()), fake)
    operation = OperationIntent(
        "body-not-permitted", "juice-shop", "GET", "/api/items", (("page", "1"),),
        case_id="fixture-case-1", profile_id="read-only-profile-v1", body=b"benign fixture",
    )

    authorization = boundary.authorize(operation)

    assert not authorization.allowed
    assert fake.attempts == []
    assert fake.dispatches == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_profile_version", "case-profile-v2"),
        ("operation_data_limits_version", "data-limits-v2"),
        ("target_registration_version", "registration-v2"),
        ("scope_version", "scope-v2"),
    ],
)
def test_changed_permit_context_version_never_dispatches(field: str, value: object) -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)
    assert authorization.permit is not None
    changed_permit = replace(authorization.permit, **{field: value})
    changed_authorization = OperationAuthorization(authorization.decision, changed_permit)

    result = boundary.dispatch(changed_authorization, operation)

    assert not result.transport_invoked
    assert fake.attempts == []
    assert fake.dispatches == []


def test_forged_or_modified_permit_and_model_shaped_data_are_rejected() -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)
    assert authorization.permit is not None

    altered_permit = replace(authorization.permit, target_registration_version="registration-v2")
    altered_authorization = OperationAuthorization(authorization.decision, altered_permit)
    forged_result = boundary.dispatch(altered_authorization, operation)
    assert forged_result.decision.reason is PolicyReason.PERMIT_INVALID
    assert not forged_result.transport_invoked

    other_boundary, _, other_fake, _, _ = make_boundary()
    shaped_model_data = {"outcome": "allow", "target_id": "juice-shop", "path": "/api/items"}
    model_result = other_boundary.dispatch(shaped_model_data, operation)
    assert model_result.decision.reason is PolicyReason.PERMIT_INVALID
    assert not model_result.transport_invoked
    assert fake.attempts == []
    assert other_fake.attempts == []


def test_expired_permit_is_stale_and_never_dispatched() -> None:
    boundary, _, fake, clock, _ = make_boundary(per_request_seconds=2.0, max_run_seconds=10.0)
    operation = make_operation()
    authorization = boundary.authorize(operation)
    clock.advance(2.0)

    result = boundary.dispatch(authorization, operation)

    assert result.decision.reason is PolicyReason.PERMIT_EXPIRED
    assert not result.transport_invoked
    assert fake.attempts == []


def test_permit_from_another_run_is_stale_and_never_dispatched() -> None:
    first_boundary, _, _, _, _ = make_boundary(run_id="run-one")
    second_boundary, _, second_fake, _, _ = make_boundary(run_id="run-two")
    operation = make_operation()
    authorization = first_boundary.authorize(operation)

    result = second_boundary.dispatch(authorization, operation)

    assert result.decision.reason is PolicyReason.PERMIT_INVALID
    assert not result.transport_invoked
    assert second_fake.attempts == []


def test_revoked_registration_invalidates_previously_issued_permit() -> None:
    boundary, engine, fake, _, _ = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)
    engine.revoke_registration("juice-shop", "registration-v1")

    result = boundary.dispatch(authorization, operation)

    assert result.decision.reason is PolicyReason.TARGET_REVOKED
    assert not result.transport_invoked
    assert fake.attempts == []


def test_replayed_permit_cannot_dispatch_twice() -> None:
    boundary, _, fake, _, _ = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)

    first = boundary.dispatch(authorization, operation)
    attempts_after_first = len(fake.attempts)
    replay = boundary.dispatch(authorization, operation)

    assert first.allowed
    assert replay.decision.reason is PolicyReason.PERMIT_REPLAYED
    assert not replay.transport_invoked
    assert attempts_after_first == 1
    assert len(fake.attempts) == attempts_after_first
    assert len(fake.dispatches) == 1


def test_operation_identity_cannot_be_reused_in_same_run() -> None:
    boundary, _, fake, _, _ = make_boundary()
    first = make_operation("same-id", path="/")
    second = make_operation("same-id", path="/api/items")

    assert boundary.dispatch(boundary.authorize(first), first).allowed
    repeated = boundary.authorize(second)

    assert repeated.decision.reason is PolicyReason.OPERATION_ID_REUSED
    assert len(fake.attempts) == 1


def test_request_budget_exhaustion_prevents_subsequent_dispatch() -> None:
    boundary, engine, fake, _, _ = make_boundary(max_requests=1)
    first = make_operation("first", path="/")
    second = make_operation("second", path="/api/items")

    assert boundary.dispatch(boundary.authorize(first), first).allowed
    denied = boundary.authorize(second)
    later = boundary.authorize(make_operation("third", path="/"))

    assert denied.decision.reason is PolicyReason.REQUEST_BUDGET_EXHAUSTED
    assert later.decision.reason is PolicyReason.WORKFLOW_DENIED
    assert engine.budget_usage.requests_used == 1
    assert len(fake.attempts) == 1


def test_redirect_budget_exhaustion_prevents_subsequent_redirect_dispatch() -> None:
    boundary, engine, fake, _, _ = make_boundary(max_requests=4, max_redirects=1)
    first = make_operation("redirect-one", path="/")
    second = make_operation("redirect-two", path="/api/items")

    first_result = boundary.dispatch(boundary.authorize_redirect(first), first)
    denied = boundary.authorize_redirect(second)

    assert first_result.allowed
    assert denied.decision.reason is PolicyReason.REDIRECT_BUDGET_EXHAUSTED
    assert engine.budget_usage.requests_used == 1
    assert engine.budget_usage.redirects_used == 1
    assert len(fake.attempts) == 1


def test_emergency_stop_between_authorize_and_dispatch_blocks_fake_call() -> None:
    boundary, _, fake, _, stop = make_boundary()
    operation = make_operation()
    authorization = boundary.authorize(operation)
    assert authorization.allowed
    stop.trigger()

    result = boundary.dispatch(authorization, operation)

    assert result.decision.reason is PolicyReason.EMERGENCY_STOP
    assert not result.transport_invoked
    assert fake.attempts == []


def test_cancellation_between_authorize_and_dispatch_blocks_fake_call() -> None:
    cancellation = CancellationToken()
    boundary, _, fake, _, _ = make_boundary(cancellation=cancellation)
    operation = make_operation()
    authorization = boundary.authorize(operation)
    cancellation.cancel()

    result = boundary.dispatch(authorization, operation)

    assert result.decision.reason is PolicyReason.RUN_CANCELLED
    assert not result.transport_invoked
    assert fake.attempts == []


def test_cancellation_after_dispatch_prevents_all_later_dispatches() -> None:
    cancellation = CancellationToken()
    boundary, _, fake, _, _ = make_boundary(cancellation=cancellation)
    first = make_operation("first", path="/")
    assert boundary.dispatch(boundary.authorize(first), first).allowed
    cancellation.cancel()

    later = boundary.authorize(make_operation("later", path="/api/items"))

    assert later.decision.reason is PolicyReason.RUN_CANCELLED
    assert fake.attempts and len(fake.attempts) == 1


def test_explicit_test_deadlines_are_bound_and_clipped_to_run_deadline() -> None:
    boundary, _, fake, clock, _ = make_boundary(per_request_seconds=5.0, max_run_seconds=7.0)
    clock.advance(5.0)
    operation = make_operation()

    authorization = boundary.authorize(operation)

    assert authorization.allowed
    assert authorization.permit is not None
    assert authorization.permit.request_timeout_seconds == 2.0
    assert authorization.permit.operation_deadline == 107.0
    assert authorization.permit.run_deadline == 107.0
    assert boundary.dispatch(authorization, operation).allowed
    assert len(fake.attempts) == 1


def test_guarded_boundary_serializes_fake_dispatches_to_one_concurrent_operation() -> None:
    entered = threading.Event()
    release = threading.Event()
    fake = RecordingFakeTransport(entered=entered, release=release)
    boundary, _, _, _, _ = make_boundary(max_requests=2, transport=fake)
    first = make_operation("first", path="/")
    second = make_operation("second", path="/api/items")
    first_auth = boundary.authorize(first)
    second_started = threading.Event()

    def dispatch_first() -> object:
        return boundary.dispatch(first_auth, first)

    def authorize_and_dispatch_second() -> object:
        second_started.set()
        authorization = boundary.authorize(second)
        return boundary.dispatch(authorization, second)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(dispatch_first)
        assert entered.wait(timeout=1)
        second_future = pool.submit(authorize_and_dispatch_second)
        assert second_started.wait(timeout=1)
        assert fake.maximum_active == 1
        release.set()
        first_result = first_future.result(timeout=2)
        second_result = second_future.result(timeout=2)

    assert first_result.allowed and second_result.allowed
    assert fake.maximum_active == 1
    assert len(fake.attempts) == 2
    assert len(fake.dispatches) == 2


def test_transport_exception_is_terminal_and_is_not_retried() -> None:
    fake = RecordingFakeTransport(fail=True)
    boundary, _, _, _, _ = make_boundary(transport=fake)
    operation = make_operation()
    authorization = boundary.authorize(operation)

    result = boundary.dispatch(authorization, operation)
    later = boundary.authorize(make_operation("later", path="/"))

    assert result.decision.reason is PolicyReason.TRANSPORT_FAILURE
    assert result.transport_invoked
    assert later.decision.reason is PolicyReason.WORKFLOW_DENIED
    assert len(fake.attempts) == 1
    assert fake.dispatches == []


def test_invalid_boundary_configuration_fails_closed() -> None:
    fake = RecordingFakeTransport()

    with pytest.raises(ConfigurationError):
        GuardedExecutionBoundary(None, fake)  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        GuardedExecutionBoundary(PolicyEngine(None), object())  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        GuardedExecutionBoundary(PolicyEngine(None), fake, cancellation=object())  # type: ignore[arg-type]


def test_operation_authorization_fails_closed_without_case_contract() -> None:
    boundary, engine, fake, _, _ = make_boundary()
    assert engine._configuration is not None
    config_without_case_contract = replace(
        engine._configuration,
        case_profiles=None,
        operation_data_limits=None,
    )
    no_case_engine = PolicyEngine(config_without_case_contract, clock=FakeClock())
    no_case_boundary = GuardedExecutionBoundary(no_case_engine, fake)

    authorization = no_case_boundary.authorize(make_operation())

    assert not authorization.allowed
    assert authorization.decision.reason is PolicyReason.MISSING_CONFIGURATION
    assert fake.attempts == []
    assert fake.dispatches == []


def test_contract_configuration_rejects_unsupported_methods_and_unbounded_limits() -> None:
    with pytest.raises(ConfigurationError, match="GET/HEAD"):
        CaseProfilePolicy(
            "juice-shop", "fixture-case-1", "profile", "v1", frozenset({"POST"}),
            frozenset({"/"}), frozenset(), frozenset(), False,
        )
    with pytest.raises(ConfigurationError, match="max_body_bytes"):
        OperationDataLimits("v1", 1, 1, 1, 1, 65537)


def test_registration_version_is_required_and_validated() -> None:
    with pytest.raises(ConfigurationError, match="registration_version"):
        ApprovedTargetRegistration(
            "juice-shop", "http", "127.0.0.1", 3000, ("/",), "fixture", "zone", True, ""
        )
