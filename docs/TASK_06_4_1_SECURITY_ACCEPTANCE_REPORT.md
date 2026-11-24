# TASK 06.4.1 — Production Guarded Execution & Target Authorization

**Audit date:** 2026-11-24  
**Verdict:** **CONDITIONAL PASS**

The production API now binds each assessment to an operator-configured loopback target, rechecks that binding after claiming its lease, and routes the single passive HTTP `HEAD` through a one-use `GuardedExecutionBoundary` permit. Exact scheme, numeric address, port, and path are constrained by the registration. The transport validates the connected socket address and port before sending the request. Evidence, findings, execution result, and terminal status remain one transaction. A running process retries stale-lease recovery in the background.

## Acceptance findings

| Requirement | Status | Evidence / limit |
|---|---|---|
| Production API cannot call the HTTP engine directly | **VERIFIED** | `POST /assessments/{id}/execute` dispatches through `AuthorizedAssessmentExecutor`; that adapter authorizes with `PolicyEngine`, consumes a permit through `GuardedExecutionBoundary`, and only then invokes the private transport. An API regression test asserts exactly one guarded `HEAD` dispatch. |
| Explicit target binding at creation and immediately before execution | **VERIFIED** | Assessment JSON persists target ID, canonical endpoint, authorization reference, and registration version. The route re-reads the assessment after the running lease claim; execution rejects missing, altered, disabled, or unknown bindings before transport. A loopback address without an explicit registry is denied. |
| Exact endpoint restrictions | **VERIFIED** | Creation and execution require the configured scheme, canonical numeric loopback address (`127.0.0.0/8` or `::1`), registered port, and permitted path. Hostnames, non-loopback destinations, credentials, query strings, fragments, malformed URLs, and unsupported numeric forms are rejected. Redirects are declined. |
| Connected-peer verification | **VERIFIED** | The socket peer address and port are checked before request bytes are sent. Tests cover wrong address and wrong port; a real ephemeral `127.0.0.1` HTTP fixture confirms the accepted peer. HTTPS retains Python's default certificate-verifying TLS context; no insecure TLS setting was introduced. |
| Passive request boundary | **VERIFIED** | One `HEAD`, five-second timeout, no redirect following, no response-body reads, and only allowlisted bounded response headers. No GET, crawling, scanning, payload, or arbitrary outbound target behavior was added. |
| Persistence failure recovery while process remains running | **VERIFIED** | A deterministic findings-write trigger makes the atomic result transaction fail. The API returns 503 and leaves the assessment running with its lease; after restoring writes, the in-process recovery worker marks it failed after expiry without restarting the app. Evidence/findings remain rolled back and no synthetic execution result is written. |
| Lease, evidence, findings, and transaction regressions | **VERIFIED** | Lifecycle, concurrency, result-preservation, lease ownership/expiry, transaction rollback, evidence-reference, and findings regressions pass in the focused and full suites. |
| OS/container/firewall egress isolation | **BLOCKED BY ENVIRONMENT** | Application checks are not an OS egress boundary. `Get-NetFirewallProfile` could not access its CIM resource, `netsh advfirewall` was unavailable in this shell, and Docker was not available to inspect. No OS-level isolation is claimed; deployment must verify and enforce outbound denial independently. |
| Authority behind an authorization reference | **NOT VERIFIED** | The registry is a trusted operator configuration and its reference/version are bound and rechecked. The current application does not validate the referenced approval against an external authority, identity, expiry, or revocation service. Configure only reviewed registrations and treat this as a deployment governance requirement. |

The code was compared with the requirements and threat model from Git `HEAD` because those documents were already deleted in the initial worktree. The implementation now covers exact endpoint binding, permit-gated dispatch, peer pinning, redirect rejection, and bounded requests. Independent egress isolation and verifiable authorization lifecycle remain open controls from that threat model, so the verdict is conditional pending deployment evidence.

## Test results

| Suite | Collected | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|---:|
| Focused creation, execution, lifecycle recovery, passive pipeline, safety policy, and guarded boundary tests | 229 | 229 | 0 | 0 | 17.19 s |
| Full Python regression suite | 767 | 767 | 0 | 0 | 36.16 s |

An earlier focused attempt collected 84 tests and reported 78 passed / 6 failed in 13.97 s. The failures were test fixtures trying to mutate databases opened in read-only mode; the fixtures were corrected to use the writable store, and the updated focused and full suites passed. No failures or skips remain in the final verification.

## Repository state

Initial and final `git status --short` were captured. The initial worktree already contained modified API, persistence, orchestration, and documentation files; deleted documents and IDE files; existing untracked reports, tests, and project artifacts; and a modified `uv.lock`. This task added the two expected execution modules and this report, and edited test modules already present as untracked at task start. The prior TASK 06.4 report was marked as a historical snapshot. No other new worktree path appeared. No Flutter file or `uv.lock` was edited, no Git staging or commit was performed, and no destructive Git command was used. No byte-for-byte preservation claim is made.
