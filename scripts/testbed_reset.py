#!/usr/bin/env python3
"""AEGISCORE AI — Offline Testbed State Reset Specification Script.

Phase 8E.2B: Statically documents deterministic database and container reset
procedures for OWASP Juice Shop and DVWA.

STRICT SAFETY RESTRICTION:
This script performs static verification and planning ONLY. It will fail closed
if live execution is attempted in Phase 8E.2B.
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
    get_standard_reset_operations,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AEGISCORE AI Testbed State Reset Specification (Phase 8E.2B Offline Review)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Attempt live execution (PROHIBITED in Phase 8E.2B)",
    )
    parser.add_argument(
        "--target",
        choices=["all", "juice-shop", "dvwa"],
        default="all",
        help="Specify target benchmark to reset",
    )
    args = parser.parse_args()

    print("[AEGISCORE AI] Offline Testbed Reset Specification (Phase 8E.2B)")

    if args.execute:
        print(
            "ERROR: Live execution of container reset commands is strictly prohibited in Phase 8E.2B. "
            "Phase 8E.2B authorizes offline configuration and static review only. "
            "Execution requires formal supervisor approval in a subsequent deployment phase.",
            file=sys.stderr,
        )
        return 4

    resets = get_standard_reset_operations()
    for ro in resets:
        if args.target not in ("all", ro.service_name):
            continue
        print(f"\n--- Target: {ro.service_name} ({ro.target_id}) ---")
        print(f"  Description: {ro.description}")
        print(f"  Volume Wipe Required: {ro.requires_volume_wipe}")
        print(f"  Deterministic Reset Command: {ro.reset_command}")
        print("  Status: STATIC PLAN ONLY — No commands executed.")

    print("\n[AEGISCORE AI] Reset procedure verification complete (Dry-Run / Offline Mode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
