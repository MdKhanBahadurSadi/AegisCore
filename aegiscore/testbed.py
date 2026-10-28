"""Offline benchmark testbed configuration and verification contracts for AEGISCORE AI.

Phase 8E.2B: File preparation and static review only.
Strictly prohibited: launching containers, pulling images, deploying benchmarks,
sending HTTP requests, running scanners, or integrating model providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re
from typing import Mapping
from urllib.parse import urlparse

from aegiscore.safety import ConfigurationError, ScopePolicy

__all__ = [
    "TestbedConfigError",
    "TestbedSecurityError",
    "ExecutionGuardError",
    "TestbedServiceConfig",
    "TestbedNetworkConfig",
    "TestbedSpecification",
    "HealthCheckTarget",
    "ResetOperation",
    "validate_compose_content",
    "validate_compose_file",
    "verify_target_allowlist",
    "get_standard_health_checks",
    "get_standard_reset_operations",
]


class TestbedConfigError(ConfigurationError):
    """Raised when testbed configuration is malformed, missing, or inconsistent."""
    __test__ = False


class TestbedSecurityError(TestbedConfigError):
    """Raised when a testbed configuration violates safety, isolation, or scope boundaries."""
    __test__ = False


class ExecutionGuardError(RuntimeError):
    """Raised when an operation attempts live execution in an offline-only phase."""


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TestbedServiceConfig:
    """Static configuration for a benchmark target service."""

    service_name: str
    image: str
    image_tag: str
    container_name: str
    restart: str
    port_bindings: tuple[str, ...]
    internal_ip: str
    security_opts: tuple[str, ...] = ()
    environment: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.service_name:
            raise TestbedConfigError("service_name cannot be empty")
        if not self.image:
            raise TestbedConfigError("image cannot be empty")
        if not self.image_tag:
            raise TestbedConfigError("image_tag cannot be empty")
        if self.image_tag == "latest":
            raise TestbedSecurityError("Image tag 'latest' is forbidden; benchmark images must be pinned to specific versions")
        if not self.container_name:
            raise TestbedConfigError("container_name cannot be empty")
        if self.restart in ("always", "unless-stopped"):
            raise TestbedSecurityError(f"Restart policy '{self.restart}' is forbidden; automatic restart must be disabled (restart: 'no')")
        for binding in self.port_bindings:
            if not binding.startswith("127.0.0.1:"):
                raise TestbedSecurityError(
                    f"Port binding '{binding}' violates security policy; all host ports must bind strictly to loopback '127.0.0.1:'"
                )
        try:
            ip = ipaddress.ip_address(self.internal_ip)
            if not ip.is_private:
                raise TestbedSecurityError(f"Internal IP '{self.internal_ip}' must be in private RFC1918 range")
        except ValueError as exc:
            raise TestbedConfigError(f"Invalid internal IP '{self.internal_ip}': {exc}") from exc


@dataclass(frozen=True, slots=True)
class TestbedNetworkConfig:
    """Static configuration for the isolated benchmark network."""

    network_name: str
    driver: str
    internal: bool
    subnet: str
    gateway: str

    def __post_init__(self) -> None:
        if not self.network_name:
            raise TestbedConfigError("network_name cannot be empty")
        if self.driver != "bridge":
            raise TestbedSecurityError(f"Network driver must be 'bridge', got '{self.driver}'")
        if not self.internal:
            raise TestbedSecurityError("Network must have 'internal: true' to enforce zero external internet egress")
        try:
            net = ipaddress.ip_network(self.subnet)
            if not net.is_private:
                raise TestbedSecurityError(f"Subnet '{self.subnet}' must be in private RFC1918 range")
            gw = ipaddress.ip_address(self.gateway)
            if gw not in net:
                raise TestbedConfigError(f"Gateway '{self.gateway}' is not in subnet '{self.subnet}'")
        except ValueError as exc:
            raise TestbedConfigError(f"Invalid network CIDR/gateway configuration: {exc}") from exc


@dataclass(frozen=True, slots=True)
class TestbedSpecification:
    """Complete static specification of the offline benchmark testbed."""

    version: str
    services: Mapping[str, TestbedServiceConfig]
    network: TestbedNetworkConfig


@dataclass(frozen=True, slots=True)
class HealthCheckTarget:
    """Pre-registered specification for target service health verification."""

    target_id: str
    service_name: str
    url: str
    timeout_seconds: float
    expected_status: int
    expected_substring: str

    def __post_init__(self) -> None:
        if not self.target_id:
            raise TestbedConfigError("target_id cannot be empty")
        if not self.service_name:
            raise TestbedConfigError("service_name cannot be empty")
        if not self.url.startswith("http://127.0.0.1:") and not self.url.startswith("http://localhost:"):
            raise TestbedSecurityError(f"Health-check URL '{self.url}' must target loopback (127.0.0.1)")
        if self.timeout_seconds <= 0.0 or self.timeout_seconds > 10.0:
            raise TestbedSecurityError(f"Health-check timeout {self.timeout_seconds}s must be bounded in (0.0, 10.0] seconds")
        if not (200 <= self.expected_status < 400):
            raise TestbedConfigError(f"expected_status must be 2xx/3xx, got {self.expected_status}")

    def execute_live(self) -> None:
        """Execute the health check against live target. Prohibited in Phase 8E.2B."""
        raise ExecutionGuardError(
            "Live health check execution is strictly prohibited in Phase 8E.2B (documentation-only / offline configuration). "
            "Supervisor approval and explicit deployment phase authorization required."
        )


@dataclass(frozen=True, slots=True)
class ResetOperation:
    """Pre-registered specification for deterministic benchmark state reset."""

    target_id: str
    service_name: str
    description: str
    reset_command: str
    requires_volume_wipe: bool = True

    def __post_init__(self) -> None:
        if not self.target_id:
            raise TestbedConfigError("target_id cannot be empty")
        if not self.service_name:
            raise TestbedConfigError("service_name cannot be empty")
        if not self.reset_command:
            raise TestbedConfigError("reset_command cannot be empty")

    def execute_live(self) -> None:
        """Execute state reset command. Prohibited in Phase 8E.2B."""
        raise ExecutionGuardError(
            "Live container state reset execution is strictly prohibited in Phase 8E.2B (documentation-only / offline configuration). "
            "Supervisor approval and explicit deployment phase authorization required."
        )


# ---------------------------------------------------------------------------
# Offline Static Parser and Validator (Zero External Dependencies)
# ---------------------------------------------------------------------------

_APPROVED_JUICE_SHOP_IMAGE = "bkimminich/juice-shop:v15.0.0"
_APPROVED_DVWA_IMAGE = "vulnerables/web-dvwa:1.10"
_APPROVED_NETWORK_NAME = "aegiscore-internal-net"
_APPROVED_SUBNET = "172.28.0.0/16"


def validate_compose_content(content: str) -> TestbedSpecification:
    """Statically parse and validate Docker Compose configuration for AEGISCORE AI.

    Parses the Compose structure without external dependencies (no PyYAML requirement)
    and verifies that all safety invariants, network isolation rules, and port
    bindings strictly comply with Phase 8E.2B requirements.
    """
    if not content or not content.strip():
        raise TestbedConfigError("Docker Compose content is empty")

    # Security check: Prohibit privileged mode, host networking, host socket mounts
    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"privileged\s*:\s*true", stripped, re.IGNORECASE):
            raise TestbedSecurityError(f"Line {line_num}: 'privileged: true' is strictly forbidden")
        if re.search(r"network_mode\s*:\s*[\"']?host[\"']?", stripped, re.IGNORECASE):
            raise TestbedSecurityError(f"Line {line_num}: 'network_mode: host' is strictly forbidden")
        if "/var/run/docker.sock" in stripped:
            raise TestbedSecurityError(f"Line {line_num}: Docker socket mount is strictly forbidden")
        if re.search(r"restart\s*:\s*[\"']?(always|unless-stopped)[\"']?", stripped, re.IGNORECASE):
            raise TestbedSecurityError(f"Line {line_num}: Automatic restart policy is forbidden; must be 'no'")

    # Extract version
    version_match = re.search(r"^version\s*:\s*[\"']([^\"']+)[\"']", content, re.MULTILINE)
    version = version_match.group(1) if version_match else "unknown"

    # Extract network block
    net_match = re.search(r"networks\s*:\s*\n\s+([a-zA-Z0-9_\-]+)\s*:", content)
    if not net_match:
        raise TestbedSecurityError("No top-level network definition found; isolated internal network is mandatory")
    net_key = net_match.group(1)
    if net_key != _APPROVED_NETWORK_NAME:
        raise TestbedSecurityError(f"Top-level network must be named '{_APPROVED_NETWORK_NAME}', found '{net_key}'")

    # Check network internal: true
    if not re.search(r"internal\s*:\s*true", content, re.IGNORECASE):
        raise TestbedSecurityError("Network definition must specify 'internal: true' to enforce zero egress")

    # Check network driver: bridge
    if not re.search(r"driver\s*:\s*bridge", content, re.IGNORECASE):
        raise TestbedSecurityError("Network driver must be 'bridge'")

    # Check subnet
    subnet_match = re.search(r"subnet\s*:\s*([0-9\.\/]+)", content)
    if not subnet_match:
        raise TestbedSecurityError("Network definition must specify an explicit subnet")
    subnet = subnet_match.group(1)
    if subnet != _APPROVED_SUBNET:
        raise TestbedSecurityError(f"Expected subnet '{_APPROVED_SUBNET}', found '{subnet}'")

    # Check gateway
    gw_match = re.search(r"gateway\s*:\s*([0-9\.]+)", content)
    gateway = gw_match.group(1) if gw_match else "172.28.0.1"

    network_config = TestbedNetworkConfig(
        network_name=_APPROVED_NETWORK_NAME,
        driver="bridge",
        internal=True,
        subnet=subnet,
        gateway=gateway,
    )

    # Extract services
    services: dict[str, TestbedServiceConfig] = {}

    # Extract juice-shop service block
    js_match = re.search(r"juice-shop\s*:\s*\n((?:\s{4,}.*\n*)+)", content)
    if not js_match:
        raise TestbedConfigError("Mandatory service 'juice-shop' is missing from docker-compose.yml")
    js_block = js_match.group(1)
    services["juice-shop"] = _parse_service_block("juice-shop", js_block, _APPROVED_JUICE_SHOP_IMAGE)

    # Extract dvwa service block
    dvwa_match = re.search(r"dvwa\s*:\s*\n((?:\s{4,}.*\n*)+)", content)
    if not dvwa_match:
        raise TestbedConfigError("Mandatory service 'dvwa' is missing from docker-compose.yml")
    dvwa_block = dvwa_match.group(1)
    services["dvwa"] = _parse_service_block("dvwa", dvwa_block, _APPROVED_DVWA_IMAGE)

    return TestbedSpecification(
        version=version,
        services=services,
        network=network_config,
    )


def _parse_service_block(service_name: str, block: str, expected_image: str) -> TestbedServiceConfig:
    """Parse and validate an individual service YAML block."""
    # Image
    img_match = re.search(r"image\s*:\s*([^\s]+)", block)
    if not img_match:
        raise TestbedConfigError(f"Service '{service_name}' has no image defined")
    image = img_match.group(1).strip("\"'")
    if image != expected_image:
        raise TestbedSecurityError(
            f"Service '{service_name}' specifies unapproved image '{image}'; expected '{expected_image}'"
        )
    image_tag = image.split(":")[-1] if ":" in image else ""

    # Container name
    cname_match = re.search(r"container_name\s*:\s*([^\s]+)", block)
    container_name = cname_match.group(1).strip("\"'") if cname_match else f"aegiscore-testbed-{service_name}"

    # Restart
    restart_match = re.search(r"restart\s*:\s*[\"']?([^\s\"']+)[\"']?", block)
    restart = restart_match.group(1) if restart_match else "no"

    # Ports
    port_matches = re.findall(r"-\s*[\"']([^\"']+)[\"']", block)
    # Filter port bindings (lines matching port patterns like host:container)
    port_bindings = tuple(p for p in port_matches if ":" in p)
    if not port_bindings:
        raise TestbedSecurityError(f"Service '{service_name}' has no port bindings defined")
    for binding in port_bindings:
        if not binding.startswith("127.0.0.1:"):
            raise TestbedSecurityError(
                f"Service '{service_name}' has insecure port binding '{binding}'; "
                f"must strictly bind to loopback '127.0.0.1:' to prevent external exposure"
            )

    # Internal IP
    ip_match = re.search(r"ipv4_address\s*:\s*([0-9\.]+)", block)
    if not ip_match:
        raise TestbedSecurityError(f"Service '{service_name}' must specify an explicit internal ipv4_address")
    internal_ip = ip_match.group(1)

    # Security options
    sec_opts = tuple(re.findall(r"-\s*(no-new-privileges:\s*true)", block, re.IGNORECASE))

    return TestbedServiceConfig(
        service_name=service_name,
        image=image,
        image_tag=image_tag,
        container_name=container_name,
        restart=restart,
        port_bindings=port_bindings,
        internal_ip=internal_ip,
        security_opts=sec_opts,
    )


def validate_compose_file(file_path: str) -> TestbedSpecification:
    """Read and validate a Docker Compose file from disk."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        raise TestbedConfigError(f"Failed to read Docker Compose file '{file_path}': {exc}") from exc
    return validate_compose_content(content)


# ---------------------------------------------------------------------------
# Scope and Allowlist Verification
# ---------------------------------------------------------------------------

def verify_target_allowlist(
    target_url: str,
    *,
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost"),
    allowed_ports: tuple[int, ...] = (3000, 8080),
    allowed_subnet: str = "172.28.0.0/16",
) -> bool:
    """Verify that a target URL falls strictly within the authorized testbed scope.

    Rejects public IP addresses, external domains, unauthorized ports, and non-HTTP schemes.
    """
    if not target_url or not isinstance(target_url, str):
        raise TestbedSecurityError("target_url must be a non-empty string")

    parsed = urlparse(target_url)
    if parsed.scheme != "http":
        raise TestbedSecurityError(f"Scheme '{parsed.scheme}' is forbidden; testbed targets use unencrypted internal 'http'")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise TestbedSecurityError("Target URL has no valid hostname")

    # Check port
    port = parsed.port or 80
    if port not in allowed_ports:
        raise TestbedSecurityError(f"Port {port} is not in the approved testbed port allowlist {allowed_ports}")

    # Check hostname: either loopback or private internal bridge subnet
    if hostname in allowed_hostnames:
        return True

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            return True
        allowed_net = ipaddress.ip_network(allowed_subnet)
        if ip in allowed_net:
            return True
    except ValueError:
        pass

    raise TestbedSecurityError(
        f"Target host '{hostname}' is not in the authorized testbed allowlist (loopback or {allowed_subnet})"
    )


# ---------------------------------------------------------------------------
# Pre-Registered Standard Specifications
# ---------------------------------------------------------------------------

def get_standard_health_checks() -> tuple[HealthCheckTarget, ...]:
    """Return pre-registered static health check specifications for benchmark targets."""
    return (
        HealthCheckTarget(
            target_id="tgt-juice-shop",
            service_name="juice-shop",
            url="http://127.0.0.1:3000/rest/admin/application-version",
            timeout_seconds=5.0,
            expected_status=200,
            expected_substring="version",
        ),
        HealthCheckTarget(
            target_id="tgt-dvwa",
            service_name="dvwa",
            url="http://127.0.0.1:8080/login.php",
            timeout_seconds=5.0,
            expected_status=200,
            expected_substring="login.php",
        ),
    )


def get_standard_reset_operations() -> tuple[ResetOperation, ...]:
    """Return pre-registered deterministic state reset operations for benchmark targets."""
    return (
        ResetOperation(
            target_id="tgt-juice-shop",
            service_name="juice-shop",
            description="Re-seed Juice Shop SQLite database by restarting container with clean volume",
            reset_command="docker compose -f testbed/docker-compose.yml down -v && docker compose -f testbed/docker-compose.yml up -d juice-shop",
            requires_volume_wipe=True,
        ),
        ResetOperation(
            target_id="tgt-dvwa",
            service_name="dvwa",
            description="Re-seed DVWA MySQL database by issuing automated setup trigger or volume recreation",
            reset_command="docker compose -f testbed/docker-compose.yml down -v && docker compose -f testbed/docker-compose.yml up -d dvwa",
            requires_volume_wipe=True,
        ),
    )
