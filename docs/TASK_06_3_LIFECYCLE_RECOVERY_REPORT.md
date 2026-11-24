# TASK 06.3.3 — AEGISCORE AI: Strict Lease Validation & Final Acceptance

**Execution date:** 2026-11-24  
**Status:** Complete

## Completed changes

- Both terminal persistence methods now require a non-empty token that matches the stored lease and a non-empty ISO timestamp with a valid timezone offset. Missing, malformed, naive, timezone-invalid, or expired leases reject the transition with sanitized `LocalStoreConflictError` messages.
- Every terminal transition is lease-checked, including the legacy `pending` to `failed` path. The check runs after `BEGIN IMMEDIATE` acquires the write transaction, so a lease that expires while waiting for the database lock cannot authorize completion.
- Renewal verifies running status, token ownership, and an aware ISO expiry under the write transaction. It rejects missing, malformed, naive, timezone-invalid, and expired leases. It never extends an expired lease.
- Recovery uses only parseable, timezone-aware lease expiries and skips missing or unverifiable timestamps. Recovery metadata stays separate from `execution_result`; the two-assessment rollback regression remains intact.
- `stale_threshold_seconds` was removed from `recover_stale_assessments()` because it was unused: recovery is determined by `lease_expires_at`.
- Lease configuration is shared by the API and persistence defaults: a 5-second execution timeout plus a 25-second safety margin gives a 30-second default lease. The synchronous API execution completes within the 5-second budget, so it does not need runtime renewal.
- Execution exception handling continues to submit failure with the worker’s lease token. A new regression verifies that a stale worker cannot fail an assessment after ownership changes.

## Lifecycle test inventory

The prior TASK 06.3.2 report listed 14 lifecycle recovery tests. All 14 remain represented; none were replaced or removed. The existing two-assessment transaction rollback test is retained.

Retained tests:

- `test_missing_lease_token_cannot_complete_running_assessment`
- `test_wrong_lease_token_cannot_complete_assessment`
- `test_expired_lease_cannot_complete_even_before_recovery`
- `test_expired_lease_cannot_be_renewed`
- `test_valid_lease_can_be_renewed_before_expiry`
- `test_execution_failure_transition_requires_valid_lease_token`
- `test_assessment_with_no_lease_not_recovered_using_old_updated_at`
- `test_recovery_metadata_stored_under_recovery_metadata`
- `test_previously_committed_execution_result_remains_unchanged`
- `test_two_stale_assessments_rollback_on_trigger_failure`
- `test_recovery_preserves_all_previous_evidence_and_findings`
- `test_recovery_and_renewal_concurrent_safety`
- `test_startup_recovery_protects_active_leases`
- `test_invalid_timestamps_and_non_finite_config_rejection`

Six lifecycle test functions were added: `test_pending_failure_cannot_bypass_lease_ownership`, `test_terminal_persistence_rejects_missing_or_unverifiable_expiry`, `test_valid_future_lease_authorizes_terminal_transition`, `test_renewal_rejects_missing_or_unverifiable_expiry`, `test_recovery_skips_unverifiable_expiry`, and `test_concurrent_recovery_and_renewal_preserve_future_lease`. Parameterized cases cover both terminal methods and both serialized recovery/renewal outcomes. The previous negative-`stale_threshold_seconds` assertion was intentionally removed because that obsolete argument no longer exists; the configuration test now asserts the shared 5+25=30-second default.

The lifecycle module now collects 35 cases across 20 test functions. The execution API suite also retains the existing unexpected-exception failure test with stronger lease cleanup assertions and adds a stale-worker ownership regression.

## Final test results

Every final run completed with zero failed and zero skipped tests. Durations are the pytest-reported suite durations.

| Requested suite | Collected | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|---:|
| Lifecycle recovery | 35 | 35 | 0 | 0 | 3.96 s |
| Assessment execution and creation | 35 | 35 | 0 | 0 | 7.26 s |
| Persistence | 17 | 17 | 0 | 0 | 11.60 s |
| Passive pipeline | 40 | 40 | 0 | 0 | 5.53 s |
| Guarded execution and safety policy | 108 | 108 | 0 | 0 | 0.46 s |
| Full Python regression suite | 756 | 756 | 0 | 0 | 33.80 s |

The initial `uv run --frozen --no-sync` attempt stopped before test collection because `uv` could not write its interpreter cache under the user profile (`Access is denied`). No tests failed in that attempt. The suites above were run with the repository’s existing `.venv` Python 3.13.2 and pytest 8.4.2; `uv.lock` was not edited.

## Repository safety

- Initial and final `git status --short` snapshots were captured. The final status contains the same pre-existing modified, deleted, and untracked paths as the initial status; this task added no new paths.
- `uv.lock` was already modified at the start and remains marked modified. No Flutter files were touched.
- No destructive Git command, `git add`, or `git commit` was used.
- No byte-for-byte preservation claim is made; the pre-existing worktree was not baseline-hash verified.

## Remaining operational behavior

Running assessments with missing or unverifiable expiry timestamps remain running and are skipped by recovery. This is intentional fail-closed behavior: recovery does not infer lease validity from `updated_at` or silently convert corrupt lease state into an authorized terminal transition.

**TASK 06.3.3 acceptance criteria are met.**
