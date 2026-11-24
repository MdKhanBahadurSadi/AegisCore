# TASK 06.4 — AEGISCORE AI MVP Acceptance Audit

> **Historical snapshot:** This report records the pre-TASK 06.4.1 audit. Its implementation findings and test totals are superseded by [TASK 06.4.1 Security Acceptance Report](TASK_06_4_1_SECURITY_ACCEPTANCE_REPORT.md).

**Audit date:** 2026-11-24  
**Verdict:** **CONDITIONAL PASS**

The narrow local MVP workflow is reproducible end to end: an authenticated user creates an assessment, one loopback HTTP `HEAD` observation is made, normalized header evidence and configuration findings are stored atomically with the terminal status, and the completed record remains readable after a fresh app instance opens the database. Expired running work is recovered on app startup. This verdict does not accept the broader proposed assessment security model or production deployment controls.

## Workflow trace and verified behavior

| Stage | Audit result |
|---|---|
| Creation and authentication | `POST /assessments` validates and stores a target; creation and execution require local bearer authentication and their respective permissions. Sessions are in memory and users authenticate again after app restart. |
| Execution boundary | The API revalidates the target as a numeric IPv4/IPv6 loopback address before execution. The engine sends one `HEAD`, uses a 5-second timeout, disables environment proxies, declines redirects, and does not read a response body. Only six named security headers are retained, with values bounded to 2,048 characters. |
| Passive detection | `PassiveHeaderDetector` emits deterministic security-configuration observations only for successfully collected 2xx responses. Findings reference the assessment’s persisted evidence; these are not confirmed vulnerability findings. |
| Persistence | Evidence, findings, execution result, and terminal status commit through one SQLite transaction. Evidence references are validated. The retained trigger-driven rollback test confirms none of the pipeline writes survive a failed transaction. |
| Lease and recovery | Terminal writes and renewal require the current token and a parseable, timezone-aware, unexpired lease under a write transaction. Recovery uses the lease expiry, preserves existing execution results and evidence/findings, and skips unverifiable leases. The synchronous execution budget is 5 seconds with a 25-second margin (30-second lease); no runtime renewal is needed. |
| Duplicate and concurrent work | A concurrent duplicate execution receives 409 while the first request proceeds; tests assert only one HEAD call and a single terminal result. Lease recovery/renewal tests cover both serialized outcomes. |
| Restart | The E2E test uses a real ephemeral HTTP server bound only to `127.0.0.1`, then opens a fresh app and verifies the terminal record, HEAD evidence, finding references, and exactly one received HEAD. A separate startup test verifies recovery of an expired lease after a fresh app instance starts. |

The added coverage is in `tests/test_assessment_execution_api.py::test_persistence_and_application_restart_retrieval` and `tests/test_assessment_lifecycle_recovery.py::test_process_restart_recovers_expired_assessment_lease`.

## Security requirements and remaining risks

The workflow meets the requested **numeric-loopback, passive HEAD** restriction in application behavior. The API rejects non-loopback execution targets before transport; redirects are not followed; proxy variables do not redirect the request; no GET, crawl, port sweep, payload, or response-body inspection occurs in this workflow.

The checked-in requirements and threat model describe stronger controls than this route currently supplies. Both files were already deleted in the initial worktree, so they were read from Git `HEAD` and left untouched. In particular:

- The assessment API calls `AssessmentExecutionEngine` directly; it does not route through the fake-only `GuardedExecutionBoundary` and its one-use, target/case/request-bound permit. Assessment creation also does not bind an explicit authorization record or a registered exact target/path. Numeric loopback is a useful boundary, but any loopback service, port, and path can be selected.
- No OS/container firewall or independent egress control, connected-peer verification, or durable execution audit event is verified here. Unit tests establish application-level URL and request behavior, not machine-level network isolation or target authorization.
- If a pipeline persistence failure rolls back after the assessment becomes running, the API returns a sanitized 503 and preserves transactional consistency. Recovery runs at app initialization, not as a background sweep, so the assessment may remain unavailable for retry in the still-running process until restart. Missing or corrupt lease timestamps are intentionally skipped and cannot authorize completion; such records may remain running until repaired.
- This workflow reports passive header configuration observations only. It does not implement the broader requirements for approved vulnerability cases, registered endpoint mapping, planning, retrieval, multi-agent analysis, or calibrated verification.

These are acceptance limits for broader threat-model compliance, not failures of the loopback HEAD workflow verified in this audit. The MVP is conditionally accepted only for the narrow local observation path and test fixture context.

## Test results

All final runs completed with zero failures and zero skips. Collected counts equal passed counts.

| Suite | Collected | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|---:|
| Lifecycle recovery | 36 | 36 | 0 | 0 | 4.20 s |
| Assessment execution and creation | 35 | 35 | 0 | 0 | 7.73 s |
| Persistence | 17 | 17 | 0 | 0 | 11.43 s |
| Passive pipeline | 40 | 40 | 0 | 0 | 5.08 s |
| Guarded execution and safety policy | 108 | 108 | 0 | 0 | 0.37 s |
| Full Python regression suite | 757 | 757 | 0 | 0 | 33.09 s |

An initial full-suite tool invocation returned before the final pytest summary was captured. It showed no failure at that point; the complete suite was rerun and the 757-pass result above was captured. A focused rerun of the two restart tests also passed (2 passed in 3.26 s).

## Repository state

Initial `git status --short` showed pre-existing modified API/persistence/orchestration files, a modified `uv.lock`, deleted documentation and IDE files, and numerous untracked project artifacts and test modules. The lifecycle, execution, creation, and pipeline test modules were already untracked. Final status contains those same existing entries plus this requested audit report; no other new worktree path appeared. The test edits are within those pre-existing untracked test modules. No Flutter file or `uv.lock` was edited. No Git staging or commit was performed, and no destructive Git command was used. No byte-for-byte preservation claim is made.
