"""Unit tests for offline testbed harness configuration and static safety validation.

Phase 8E.2B: All tests are strictly offline and validate configuration parsing,
network isolation constraints, port binding boundaries, and fail-closed behavior
without launching Docker containers, pulling images, or making network requests.
"""

from __future__ import annotations

import os
import pytest

from aegiscore.testbed import (
    ExecutionGuardError,
    HealthCheckTarget,
    ResetOperation,
    TestbedConfigError,
    TestbedSecurityError,
    get_standard_health_checks,
    get_standard_reset_operations,
    validate_compose_content,
    validate_compose_file,
    verify_target_allowlist,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE_FILE_PATH = os.path.join(REPO_ROOT, "testbed", "docker-compose.yml")


# ---------------------------------------------------------------------------
# Test 1: Real testbed/docker-compose.yml validation
# ---------------------------------------------------------------------------

def test_repository_docker_compose_file_passes_all_safety_checks() -> None:
    """The repository's testbed/docker-compose.yml must parse cleanly and satisfy all safety rules."""
    assert os.path.exists(COMPOSE_FILE_PATH), f"Missing {COMPOSE_FILE_PATH}"
    spec = validate_compose_file(COMPOSE_FILE_PATH)

    # Verify network isolation
    assert spec.network.network_name == "aegiscore-internal-net"
    assert spec.network.driver == "bridge"
    assert spec.network.internal is True
    assert spec.network.subnet == "172.28.0.0/16"
    assert spec.network.gateway == "172.28.0.1"

    # Verify services
    assert "juice-shop" in spec.services
    assert "dvwa" in spec.services
    assert len(spec.services) == 2

    # Verify juice-shop service
    js = spec.services["juice-shop"]
    assert js.image == "bkimminich/juice-shop:v15.0.0"
    assert js.image_tag == "v15.0.0"
    assert js.container_name == "aegiscore-testbed-juice-shop"
    assert js.restart == "no"
    assert js.internal_ip == "172.28.0.10"
    assert js.port_bindings == ("127.0.0.1:3000:3000",)

    # Verify dvwa service
    dvwa = spec.services["dvwa"]
    assert dvwa.image == "vulnerables/web-dvwa:1.10"
    assert dvwa.image_tag == "1.10"
    assert dvwa.container_name == "aegiscore-testbed-dvwa"
    assert dvwa.restart == "no"
    assert dvwa.internal_ip == "172.28.0.20"
    assert dvwa.port_bindings == ("127.0.0.1:8080:80",)


# ---------------------------------------------------------------------------
# Test 2: Port binding isolation (fail-closed on 0.0.0.0 or non-loopback)
# ---------------------------------------------------------------------------

def test_insecure_0000_port_binding_fails_closed() -> None:
    """Publishing ports on 0.0.0.0 must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    insecure_content = valid_content.replace(
        '"127.0.0.1:3000:3000"',
        '"0.0.0.0:3000:3000"',
    )
    with pytest.raises(TestbedSecurityError, match="must strictly bind to loopback"):
        validate_compose_content(insecure_content)


def test_bare_port_binding_fails_closed() -> None:
    """Publishing bare ports (e.g. '3000:3000') without host IP must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    insecure_content = valid_content.replace(
        '"127.0.0.1:3000:3000"',
        '"3000:3000"',
    )
    with pytest.raises(TestbedSecurityError, match="must strictly bind to loopback"):
        validate_compose_content(insecure_content)


# ---------------------------------------------------------------------------
# Test 3: Network isolation rules (internal: true, bridge driver)
# ---------------------------------------------------------------------------

def test_missing_internal_true_fails_closed() -> None:
    """Docker network without internal: true must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    insecure_content = valid_content.replace("internal: true", "internal: false")
    with pytest.raises(TestbedSecurityError, match="internal: true"):
        validate_compose_content(insecure_content)


def test_unapproved_network_name_fails_closed() -> None:
    """Network with an unexpected name must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace("aegiscore-internal-net:", "external-bridge:")
    with pytest.raises(TestbedSecurityError, match="Top-level network must be named 'aegiscore-internal-net'"):
        validate_compose_content(tampered_content)


# ---------------------------------------------------------------------------
# Test 4: Container privilege and mount restrictions
# ---------------------------------------------------------------------------

def test_privileged_mode_fails_closed() -> None:
    """Adding 'privileged: true' must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace(
        "container_name: aegiscore-testbed-juice-shop",
        "container_name: aegiscore-testbed-juice-shop\n    privileged: true",
    )
    with pytest.raises(TestbedSecurityError, match="privileged: true"):
        validate_compose_content(tampered_content)


def test_docker_socket_mount_fails_closed() -> None:
    """Mounting docker.sock must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace(
        "container_name: aegiscore-testbed-juice-shop",
        "container_name: aegiscore-testbed-juice-shop\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock",
    )
    with pytest.raises(TestbedSecurityError, match="Docker socket mount"):
        validate_compose_content(tampered_content)


def test_host_network_mode_fails_closed() -> None:
    """Using network_mode: host must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace(
        "container_name: aegiscore-testbed-juice-shop",
        "container_name: aegiscore-testbed-juice-shop\n    network_mode: host",
    )
    with pytest.raises(TestbedSecurityError, match="network_mode: host"):
        validate_compose_content(tampered_content)


# ---------------------------------------------------------------------------
# Test 5: Automatic restart policy restrictions
# ---------------------------------------------------------------------------

def test_automatic_restart_always_fails_closed() -> None:
    """Setting restart: always must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace('restart: "no"', 'restart: always')
    with pytest.raises(TestbedSecurityError, match="Automatic restart policy"):
        validate_compose_content(tampered_content)


def test_automatic_restart_unless_stopped_fails_closed() -> None:
    """Setting restart: unless-stopped must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace('restart: "no"', 'restart: unless-stopped')
    with pytest.raises(TestbedSecurityError, match="Automatic restart policy"):
        validate_compose_content(tampered_content)


# ---------------------------------------------------------------------------
# Test 6: Image pinning restrictions
# ---------------------------------------------------------------------------

def test_unapproved_image_fails_closed() -> None:
    """Specifying an unapproved image must raise TestbedSecurityError."""
    with open(COMPOSE_FILE_PATH, "r", encoding="utf-8") as f:
        valid_content = f.read()

    tampered_content = valid_content.replace(
        "bkimminich/juice-shop:v15.0.0",
        "malicious/fake-juice-shop:v15.0.0",
    )
    with pytest.raises(TestbedSecurityError, match="unapproved image"):
        validate_compose_content(tampered_content)


# ---------------------------------------------------------------------------
# Test 7: Target allowlist and scope verification
# ---------------------------------------------------------------------------

def test_allowlist_accepts_valid_loopback_and_internal_subnet() -> None:
    """Allowlist verification must accept loopback (127.0.0.1) and internal subnet targets."""
    assert verify_target_allowlist("http://127.0.0.1:3000/rest/admin") is True
    assert verify_target_allowlist("http://127.0.0.1:8080/login.php") is True
    assert verify_target_allowlist("http://localhost:3000/") is True
    assert verify_target_allowlist("http://172.28.0.10:3000/rest/admin") is True
    assert verify_target_allowlist("http://172.28.0.20:8080/login.php") is True


def test_allowlist_rejects_public_ip_addresses() -> None:
    """Allowlist verification must reject public internet IP addresses."""
    with pytest.raises(TestbedSecurityError, match="not in the authorized testbed allowlist"):
        verify_target_allowlist("http://8.8.8.8:3000/rest/admin")

    with pytest.raises(TestbedSecurityError, match="not in the authorized testbed allowlist"):
        verify_target_allowlist("http://93.184.216.34:3000/")


def test_allowlist_rejects_external_domain_names() -> None:
    """Allowlist verification must reject external non-loopback domain names."""
    with pytest.raises(TestbedSecurityError, match="not in the authorized testbed allowlist"):
        verify_target_allowlist("http://example.com:3000/")


def test_allowlist_rejects_unauthorized_ports() -> None:
    """Allowlist verification must reject ports not in the approved allowlist (3000, 8080)."""
    with pytest.raises(TestbedSecurityError, match="not in the approved testbed port allowlist"):
        verify_target_allowlist("http://127.0.0.1:80/")

    with pytest.raises(TestbedSecurityError, match="not in the approved testbed port allowlist"):
        verify_target_allowlist("http://127.0.0.1:443/")

    with pytest.raises(TestbedSecurityError, match="not in the approved testbed port allowlist"):
        verify_target_allowlist("http://127.0.0.1:8000/")


def test_allowlist_rejects_non_http_schemes() -> None:
    """Allowlist verification must reject non-http schemes (https, ftp)."""
    with pytest.raises(TestbedSecurityError, match="Scheme 'https' is forbidden"):
        verify_target_allowlist("https://127.0.0.1:3000/")

    with pytest.raises(TestbedSecurityError, match="Scheme 'ftp' is forbidden"):
        verify_target_allowlist("ftp://127.0.0.1:3000/")


# ---------------------------------------------------------------------------
# Test 8: Health check and reset operation contracts & execution guards
# ---------------------------------------------------------------------------

def test_standard_health_checks_are_properly_bounded() -> None:
    """Pre-registered health checks must have bounded timeouts <= 10.0s and valid loopback URLs."""
    checks = get_standard_health_checks()
    assert len(checks) == 2
    for hc in checks:
        assert hc.timeout_seconds <= 5.0
        assert hc.url.startswith("http://127.0.0.1:")
        assert hc.expected_status == 200

    # Live execution must fail closed in Phase 8E.2B
    with pytest.raises(ExecutionGuardError, match="strictly prohibited in Phase 8E.2B"):
        checks[0].execute_live()


def test_excessive_health_check_timeout_fails_closed() -> None:
    """HealthCheckTarget with timeout > 10.0s must be rejected."""
    with pytest.raises(TestbedSecurityError, match="must be bounded in"):
        HealthCheckTarget(
            target_id="tgt-test",
            service_name="test",
            url="http://127.0.0.1:3000/health",
            timeout_seconds=30.0,
            expected_status=200,
            expected_substring="ok",
        )


def test_standard_reset_operations_fail_closed_on_live_execution() -> None:
    """Pre-registered reset operations must fail closed if execute_live() is called."""
    resets = get_standard_reset_operations()
    assert len(resets) == 2
    for ro in resets:
        assert "docker compose" in ro.reset_command
        with pytest.raises(ExecutionGuardError, match="strictly prohibited in Phase 8E.2B"):
            ro.execute_live()
