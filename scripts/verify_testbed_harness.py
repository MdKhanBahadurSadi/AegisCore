#!/usr/bin/env python3
"""AEGISCORE AI — Offline Testbed Configuration Verifier.

Phase 8E.2B: Statically validates testbed/docker-compose.yml against isolation,
safety, and allowlist constraints without launching Docker or sending network packets.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aegiscore.testbed import (
    TestbedConfigError,
    TestbedSecurityError,
    validate_compose_file,
    verify_target_allowlist,
    get_standard_health_checks,
    get_standard_reset_operations,
)


def main() -> int:
    compose_path = os.path.join(REPO_ROOT, "testbed", "docker-compose.yml")
    print(f"[AEGISCORE AI] Verifying offline testbed configuration: {compose_path}")

    if not os.path.exists(compose_path):
        print(f"FAIL: Configuration file not found at '{compose_path}'", file=sys.stderr)
        return 1

    try:
        spec = validate_compose_file(compose_path)
    except TestbedSecurityError as exc:
        print(f"SECURITY VIOLATION: {exc}", file=sys.stderr)
        return 2
    except TestbedConfigError as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 3

    print(f"  [+] Network Name: {spec.network.network_name}")
    print(f"  [+] Network Driver: {spec.network.driver}")
    print(f"  [+] Network Internal (Zero Egress): {spec.network.internal}")
    print(f"  [+] Network Subnet: {spec.network.subnet}")
    print(f"  [+] Network Gateway: {spec.network.gateway}")
    print(f"  [+] Services Configured: {len(spec.services)}")

    for svc_name, svc in spec.services.items():
        print(f"      - {svc_name}:")
        print(f"          Image: {svc.image}")
        print(f"          Container: {svc.container_name}")
        print(f"          Internal IP: {svc.internal_ip}")
        print(f"          Restart Policy: {svc.restart}")
        print(f"          Port Bindings: {svc.port_bindings} (loopback only)")

    # Verify target allowlists
    print("\n[AEGISCORE AI] Verifying Pre-Registered Target Allowlist & Scope:")
    health_checks = get_standard_health_checks()
    for hc in health_checks:
        verify_target_allowlist(hc.url)
        print(f"  [+] Verified allowlist for {hc.service_name}: {hc.url} (timeout ceiling: {hc.timeout_seconds}s)")

    # Verify reset operations
    print("\n[AEGISCORE AI] Verifying State Reset Specifications:")
    resets = get_standard_reset_operations()
    for ro in resets:
        print(f"  [+] Reset specification registered for {ro.service_name}: {ro.description}")

    print("\n[AEGISCORE AI] RESULT: PASS — All static testbed safety constraints verified successfully.")
    print("  NOTE: Containers are NOT launched. Phase 8E.2B is documentation and configuration only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
