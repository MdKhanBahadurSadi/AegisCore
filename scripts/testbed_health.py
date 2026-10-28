#!/usr/bin/env python3
"""AEGISCORE AI — Offline Testbed Health Check Specification Script.

Phase 8E.2B: Statically documents bounded health-check endpoints, expected HTTP
responses, and scope allowlist validation for OWASP Juice Shop and DVWA.

STRICT SAFETY RESTRICTION:
This script performs static verification and planning ONLY. It will fail closed
if live HTTP requests are attempted in Phase 8E.2B.
"""

from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aegiscore.testbed import (
    ExecutionGuardError,
    get_standard_health_checks,
    verify_target_allowlist,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AEGISCORE AI Testbed Health Check Specification (Phase 8E.2B Offline Review)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Attempt live HTTP health checks (PROHIBITED in Phase 8E.2B)",
    )
    parser.add_argument(
        "--target",
        choices=["all", "juice-shop", "dvwa"],
        default="all",
        help="Specify target benchmark for health check",
    )
    args = parser.parse_args()

    print("[AEGISCORE AI] Offline Testbed Health Check Specification (Phase 8E.2B)")

    if args.execute:
        print(
            "ERROR: Live execution of HTTP health check requests is strictly prohibited in Phase 8E.2B. "
            "Phase 8E.2B authorizes offline configuration and static review only. "
            "Execution requires formal supervisor approval in a subsequent deployment phase.",
            file=sys.stderr,
        )
        return 4

    health_checks = get_standard_health_checks()
    for hc in health_checks:
        if args.target not in ("all", hc.service_name):
            continue
        print(f"\n--- Target: {hc.service_name} ({hc.target_id}) ---")
        print(f"  Target URL: {hc.url}")
        print(f"  Timeout Ceiling: {hc.timeout_seconds}s (Hard bounded <= 10.0s)")
        print(f"  Expected HTTP Status: {hc.expected_status}")
        print(f"  Expected Response Substring: '{hc.expected_substring}'")

        # Static scope verification
        try:
            verify_target_allowlist(hc.url)
            print("  Scope Validation: PASS (Verified loopback RFC1918 / 127.0.0.1)")
        except Exception as exc:
            print(f"  Scope Validation: FAIL ({exc})", file=sys.stderr)
            return 1

        print("  Status: STATIC SPECIFICATION ONLY — No network traffic emitted.")

    print("\n[AEGISCORE AI] Health check specification verification complete (Dry-Run / Offline Mode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
