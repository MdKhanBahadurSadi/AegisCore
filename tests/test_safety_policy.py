from concurrent.futures import ThreadPoolExecutor

import pytest

from aegiscore.safety import (
    ApprovedTargetRegistration,
    ConfigurationError,
    EmergencyStop,
    PolicyEngine,
    PolicyOutcome,
    PolicyDecision,
    PolicyReason,
    RequestBudget,
    RequestIntent,
    SafetyConfiguration,
    ScopePolicy,
    TargetRegistry,
    TimeoutPolicy,
    WorkflowSafetyGate,
)


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_configuration(
    *,
    max_requests: int = 5,
    max_redirects: int = 2,
    per_request_seconds: float = 2.0,
    max_run_seconds: float = 30.0,
    emergency_stop: EmergencyStop | None = None,
    registration: ApprovedTargetRegistration | None = None,
) -> SafetyConfiguration:
    target = registration or ApprovedTargetRegistration(
        target_id="juice-shop",
        scheme="http",
        hostname="127.0.0.1",
        port=3000,
        permitted_paths=("/", "/api/items"),
        authorization_ref="approval-record-1",
        network_zone_id="local-lab-net",
        enabled=True,
        registration_version="reg-v1",
    )
    registry = TargetRegistry((target,))
    scope = ScopePolicy(
        policy_id="lab-policy",
        version="v1",
        target_ids=frozenset({target.target_id}),
        allowed_schemes=frozenset({target.scheme}),
        allowed_hostnames=frozenset({target.hostname}),
        allowed_ports=frozenset({target.port}),
        permitted_paths_by_target={target.target_id: frozenset(target.permitted_paths)},
    )
    return SafetyConfiguration(
        registry=registry,
        scope=scope,
        request_budget=RequestBudget(max_requests, max_redirects),
        timeouts=TimeoutPolicy(per_request_seconds, max_run_seconds),
        emergency_stop=emergency_stop or EmergencyStop(active=False),
    )


def make_engine(**kwargs: object) -> tuple[PolicyEngine, FakeClock]:
    clock = FakeClock()
    return PolicyEngine(make_configuration(**kwargs), clock=clock), clock


def test_registered_target_and_exact_permitted_path_are_allowed() -> None:
    engine, _ = make_engine()

    decision = engine.evaluate_request(RequestIntent("juice-shop", "/api/items"))

    assert decision.outcome is PolicyOutcome.ALLOW
    assert decision.reason is PolicyReason.ALLOWED
    assert decision.request_timeout_seconds == 2.0
    assert decision.authorized_path == "/api/items"
    assert engine.budget_usage.requests_used == 1


@pytest.mark.parametrize(
    "intent",
    [
        RequestIntent("unknown", "/"),
        RequestIntent("http://127.0.0.1:3000", "/"),
        RequestIntent("juice-shop", "http://127.0.0.1:3000/"),
        RequestIntent("juice-shop", "//example.test/"),
        RequestIntent(None, "/"),
    ],
)
def test_unknown_or_url_shaped_request_intent_is_denied(intent: RequestIntent) -> None:
    engine, _ = make_engine()

    decision = engine.evaluate_request(intent)

    assert not decision.allowed
    assert decision.reason in {PolicyReason.UNKNOWN_TARGET, PolicyReason.INVALID_REQUEST, PolicyReason.INVALID_PATH}
    assert engine.budget_usage.requests_used == 0


@pytest.mark.parametrize(
    "path",
    ["/private", "/../api/items", "/%2e%2e/api/items", "/%252e%252e/api/items", "/a%2fb", "/a\\b", "/bad%ZZ", "/?query=value"],
)
def test_out_of_scope_or_ambiguous_paths_are_denied(path: str) -> None:
    engine, _ = make_engine()

    decision = engine.evaluate_request(RequestIntent("juice-shop", path))

    assert not decision.allowed
    assert decision.reason in {PolicyReason.INVALID_PATH, PolicyReason.PATH_NOT_PERMITTED}
    assert engine.budget_usage.requests_used == 0


def test_missing_or_wrong_configuration_fails_closed() -> None:
    missing = PolicyEngine(None)
    invalid = PolicyEngine(object())  # type: ignore[arg-type]

    assert missing.evaluate_request(RequestIntent("juice-shop", "/")).reason is PolicyReason.MISSING_CONFIGURATION
    assert invalid.evaluate_request(RequestIntent("juice-shop", "/")).reason is PolicyReason.INVALID_CONFIGURATION


def test_malformed_policy_decision_cannot_claim_allow() -> None:
    with pytest.raises(ValueError):
        PolicyDecision(
            PolicyOutcome.ALLOW,
            PolicyReason.UNKNOWN_TARGET,
            "juice-shop",
            "lab-policy",
            "v1",
            1.0,
            "/",
        )
    with pytest.raises(ValueError, match="only be issued"):
        PolicyDecision(
            PolicyOutcome.ALLOW,
            PolicyReason.ALLOWED,
            "juice-shop",
            "lab-policy",
            "v1",
            1.0,
            "/",
        )


def test_invalid_registry_and_scope_configurations_are_rejected() -> None:
    with pytest.raises(ConfigurationError):
        TargetRegistry(())
    with pytest.raises(ConfigurationError):
        ApprovedTargetRegistration(
            "juice-shop", "ftp", "127.0.0.1", 3000, ("/",), "approval", "lab", True, "reg-v1"
        )
    with pytest.raises(ConfigurationError):
        ApprovedTargetRegistration(
            "juice-shop", "http", "203.0.113.9", 3000, ("/",), "approval", "lab", True, "reg-v1"
        )
    for hostname in ("LOCALHOST", "*.localhost", "bad_host"):
        with pytest.raises(ConfigurationError):
            ApprovedTargetRegistration(
                "juice-shop", "http", hostname, 3000, ("/",), "approval", "lab", True, "reg-v1"
            )
    with pytest.raises(ConfigurationError):
        ApprovedTargetRegistration(
            "juice-shop", "http", "127.0.0.1", True, ("/",), "approval", "lab", True, "reg-v1"
        )
    with pytest.raises(ConfigurationError):
        RequestBudget(True, 0)
    with pytest.raises(ConfigurationError):
        TimeoutPolicy(3.0, 2.0)


def test_scope_origin_must_match_registered_scheme_host_and_port() -> None:
    target = ApprovedTargetRegistration(
        "juice-shop", "http", "127.0.0.1", 3000, ("/",), "approval", "lab", True, "reg-v1"
    )
    bad_scope = ScopePolicy(
        "policy",
        "v1",
        frozenset({"juice-shop"}),
        frozenset({"https"}),
        frozenset({"127.0.0.1"}),
        frozenset({3000}),
        {"juice-shop": frozenset({"/"})},
    )

    with pytest.raises(ConfigurationError):
        SafetyConfiguration(
            TargetRegistry((target,)),
            bad_scope,
            RequestBudget(1, 0),
            TimeoutPolicy(1.0, 1.0),
            EmergencyStop(False),
        )


@pytest.mark.parametrize("port", [1, 65535])
def test_lowest_and_highest_ports_are_valid_when_explicitly_registered(port: int) -> None:
    target = ApprovedTargetRegistration(
        "juice-shop", "https", "localhost", port, ("/",), "approval", "lab", True, "reg-v1"
    )
    engine = PolicyEngine(make_configuration(registration=target), clock=FakeClock())

    assert engine.evaluate_request(RequestIntent("juice-shop", "/")).allowed


def test_ipv6_loopback_registration_and_relative_redirect_are_supported() -> None:
    target = ApprovedTargetRegistration(
        "ipv6-lab", "http", "::1", 3000, ("/", "/api/items"), "approval", "lab", True, "reg-v1"
    )
    engine = PolicyEngine(make_configuration(registration=target), clock=FakeClock())

    assert engine.evaluate_request(RequestIntent("ipv6-lab", "/")).allowed
    redirect = engine.evaluate_redirect("ipv6-lab", "/", "/api/items")
    assert redirect.allowed
    assert redirect.destination_target_id == "ipv6-lab"


@pytest.mark.parametrize("port", [0, 65536])
def test_ports_outside_valid_range_fail_configuration(port: int) -> None:
    with pytest.raises(ConfigurationError):
        ApprovedTargetRegistration(
            "juice-shop", "http", "localhost", port, ("/",), "approval", "lab", True, "reg-v1"
        )


def test_request_budget_allows_final_available_slot_then_denies() -> None:
    engine, _ = make_engine(max_requests=2)

    first = engine.evaluate_request(RequestIntent("juice-shop", "/"))
    second = engine.evaluate_request(RequestIntent("juice-shop", "/"))
    exhausted = engine.evaluate_request(RequestIntent("juice-shop", "/"))

    assert first.allowed and second.allowed
    assert exhausted.reason is PolicyReason.REQUEST_BUDGET_EXHAUSTED
    assert engine.budget_usage.requests_used == 2


def test_budget_reservation_is_atomic_for_concurrent_policy_checks() -> None:
    engine, _ = make_engine(max_requests=3)

    with ThreadPoolExecutor(max_workers=12) as pool:
        decisions = list(pool.map(lambda _: engine.evaluate_request(RequestIntent("juice-shop", "/")), range(12)))

    assert sum(decision.allowed for decision in decisions) == 3
    assert engine.budget_usage.requests_used == 3


def test_execution_timeout_boundary_is_denied() -> None:
    engine, clock = make_engine(max_run_seconds=4.0)
    clock.advance(4.0)

    decision = engine.evaluate_request(RequestIntent("juice-shop", "/"))

    assert decision.reason is PolicyReason.EXECUTION_TIMEOUT
    assert engine.budget_usage.requests_used == 0


def test_clock_failure_fails_closed() -> None:
    class BrokenClock:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self) -> float:
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("clock unavailable")
            return 1.0

    engine = PolicyEngine(make_configuration(), clock=BrokenClock())

    assert engine.evaluate_request(RequestIntent("juice-shop", "/")).reason is PolicyReason.CLOCK_FAILURE


def test_same_origin_permitted_redirect_is_allowed_and_counted() -> None:
    engine, _ = make_engine()

    result = engine.evaluate_redirect("juice-shop", "/", "/api/items")

    assert result.allowed
    assert result.destination_target_id == "juice-shop"
    assert result.destination_path == "/api/items"
    assert engine.budget_usage.requests_used == 1
    assert engine.budget_usage.redirects_used == 1


def test_absolute_same_origin_redirect_is_allowed() -> None:
    engine, _ = make_engine()

    result = engine.evaluate_redirect("juice-shop", "/", "http://127.0.0.1:3000/api/items")

    assert result.allowed
    assert result.destination_path == "/api/items"


@pytest.mark.parametrize(
    "location,reason",
    [
        ("https://example.test/", PolicyReason.REDIRECT_ORIGIN_MISMATCH),
        ("http://127.0.0.1:3001/", PolicyReason.REDIRECT_ORIGIN_MISMATCH),
        ("https://127.0.0.1:3000/", PolicyReason.REDIRECT_ORIGIN_MISMATCH),
        ("//example.test/", PolicyReason.REDIRECT_ORIGIN_MISMATCH),
        ("/not-registered", PolicyReason.PATH_NOT_PERMITTED),
        ("/../api/items", PolicyReason.REDIRECT_INVALID),
        ("/bad%ZZ", PolicyReason.REDIRECT_INVALID),
        ("/api/items?query=value", PolicyReason.REDIRECT_INVALID),
        ("http://user@127.0.0.1:3000/", PolicyReason.REDIRECT_INVALID),
        ("http://127.0.0.1:bad/", PolicyReason.REDIRECT_INVALID),
    ],
)
def test_invalid_or_out_of_scope_redirect_is_denied(location: str, reason: PolicyReason) -> None:
    engine, _ = make_engine()

    result = engine.evaluate_redirect("juice-shop", "/", location)

    assert not result.allowed
    assert result.decision.reason is reason
    assert engine.budget_usage.requests_used == 0


def test_redirect_limit_and_request_limit_are_enforced() -> None:
    engine, _ = make_engine(max_requests=4, max_redirects=1)
    first = engine.evaluate_redirect("juice-shop", "/", "/api/items")
    second = engine.evaluate_redirect("juice-shop", "/", "/api/items")

    assert first.allowed
    assert second.decision.reason is PolicyReason.REDIRECT_BUDGET_EXHAUSTED
    assert engine.budget_usage.redirects_used == 1

    one_request_engine, _ = make_engine(max_requests=1, max_redirects=1)
    assert one_request_engine.evaluate_request(RequestIntent("juice-shop", "/")).allowed
    denied = one_request_engine.evaluate_redirect("juice-shop", "/", "/api/items")
    assert denied.decision.reason is PolicyReason.REQUEST_BUDGET_EXHAUSTED


def test_zero_redirect_budget_denies_redirect() -> None:
    engine, _ = make_engine(max_redirects=0)

    result = engine.evaluate_redirect("juice-shop", "/", "/api/items")

    assert result.decision.reason is PolicyReason.REDIRECT_BUDGET_EXHAUSTED


def test_emergency_stop_denies_before_and_after_run_start() -> None:
    stopped_engine, _ = make_engine(emergency_stop=EmergencyStop(active=True))
    assert stopped_engine.evaluate_request(RequestIntent("juice-shop", "/")).reason is PolicyReason.EMERGENCY_STOP

    stop = EmergencyStop(active=False)
    engine, _ = make_engine(emergency_stop=stop)
    assert engine.evaluate_request(RequestIntent("juice-shop", "/")).allowed
    stop.trigger()
    assert engine.evaluate_request(RequestIntent("juice-shop", "/")).reason is PolicyReason.EMERGENCY_STOP
    assert engine.budget_usage.requests_used == 1


def test_denied_decision_cannot_be_bypassed_by_later_workflow_allow() -> None:
    engine, _ = make_engine()
    gate = WorkflowSafetyGate()
    denied = engine.evaluate_request(RequestIntent("unknown", "/"))
    later_allow = PolicyEngine(make_configuration()).evaluate_request(RequestIntent("juice-shop", "/"))

    assert gate.record(denied).reason is PolicyReason.UNKNOWN_TARGET
    assert gate.record(later_allow).reason is PolicyReason.WORKFLOW_DENIED
    assert gate.authorize_next_step(RequestIntent("juice-shop", "/")).reason is PolicyReason.WORKFLOW_DENIED


def test_workflow_gate_requires_allow_and_latches_later_denial() -> None:
    engine, _ = make_engine()
    gate = WorkflowSafetyGate()
    assert gate.authorize_next_step(RequestIntent("juice-shop", "/")).reason is PolicyReason.NO_PRIOR_ALLOW

    assert gate.record(engine.evaluate_request(RequestIntent("juice-shop", "/"))).allowed
    assert gate.record(engine.evaluate_request(RequestIntent("unknown", "/"))).reason is PolicyReason.UNKNOWN_TARGET
    assert gate.authorize_next_step(RequestIntent("juice-shop", "/")).reason is PolicyReason.WORKFLOW_DENIED


def test_workflow_allow_is_bound_to_one_target_path_and_one_step() -> None:
    engine, _ = make_engine()
    gate = WorkflowSafetyGate()
    intent = RequestIntent("juice-shop", "/")
    assert gate.record(engine.evaluate_request(intent)).allowed

    mismatch = gate.authorize_next_step(RequestIntent("juice-shop", "/api/items"))
    assert mismatch.reason is PolicyReason.WORKFLOW_DENIED
    assert gate.authorize_next_step(intent).reason is PolicyReason.WORKFLOW_DENIED

    another_gate = WorkflowSafetyGate()
    assert another_gate.record(engine.evaluate_request(intent)).allowed
    assert another_gate.authorize_next_step(intent).allowed
    assert another_gate.authorize_next_step(intent).reason is PolicyReason.NO_PRIOR_ALLOW

