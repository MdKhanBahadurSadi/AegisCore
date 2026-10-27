from fastapi import FastAPI
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.guarded_execution import GuardedExecutionBoundary
from aegiscore.safety import PolicyEngine


def test_application_factory_returns_fastapi_application() -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "AEGISCORE AI Backend"
    assert app.version == "0.1.0"


def test_health_endpoint_returns_typed_process_health() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capabilities_endpoint_reports_only_implemented_and_unimplemented_features() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "service": "aegiscore-api",
        "version": "0.1.0",
        "implemented": [
            "api.health_endpoint",
            "api.capabilities_endpoint",
            "safety.in_memory_policy_contracts",
            "safety.fake_transport_only_guarded_execution_contract",
        ],
        "not_implemented": [
            "backend.real_target_transport",
            "backend.rag",
            "backend.multi_agent_orchestration",
            "backend.vulnerability_assessment_workflow",
            "backend.external_llm_provider",
            "backend.persistent_application_storage",
        ],
    }


def test_unsupported_methods_and_routes_return_safe_http_errors() -> None:
    with TestClient(create_app()) as client:
        method_error = client.post("/health", json={"target_url": "http://example.invalid"})
        route_error = client.get("/not-a-route")

    assert method_error.status_code == 405
    assert method_error.json() == {"detail": "Method Not Allowed"}
    assert route_error.status_code == 404
    assert route_error.json() == {"detail": "Not Found"}
    assert "Traceback" not in method_error.text + route_error.text


def test_health_and_capabilities_never_enter_policy_or_dispatch_workflow(monkeypatch) -> None:
    def unexpected_execution(*args, **kwargs):
        raise AssertionError("read-only system endpoint entered the execution workflow")

    monkeypatch.setattr(PolicyEngine, "authorize_operation", unexpected_execution)
    monkeypatch.setattr(PolicyEngine, "consume_operation_permit", unexpected_execution)
    monkeypatch.setattr(GuardedExecutionBoundary, "dispatch", unexpected_execution)

    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/capabilities").status_code == 200
