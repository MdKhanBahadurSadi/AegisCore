# TASK 06.4.4 — Live Linux Egress Isolation Verification

## Verdict

**CONDITIONAL PASS.** The Windows-host regression tests pass and the Linux deployment includes a reproducible namespace/firewall probe. This environment has no Linux runtime, so no Debian namespace, active nftables rules, or live connectivity results were collected. OS-level isolation is **BLOCKED BY ENVIRONMENT** and is not claimed as verified. A production authorization authority is also not configured, so the real-authority assessment workflow cannot be enabled here.

## Environment discovery

| Check | Result |
|---|---|
| `cmd.exe /c ver` (exit 0) | Microsoft Windows `[Version 10.0.26320.10022]` |
| `wsl.exe --list --quiet` (exit 1) | WSL is not installed. |
| `Get-Command ip,nft,setpriv,docker,podman -ErrorAction SilentlyContinue` (exit 1) | No Linux namespace/firewall or container tools are available. |
| `python --version` (exit 0) | Python 3.13.2 |
| Debian/kernel version, namespace capabilities, active rules | Not observable from this Windows environment. |

`python deploy/linux-egress/run_isolated.py --config deploy/linux-egress/aegiscore-linux-egress.conf.example` exited 1 with `isolated deployment failed closed: Linux network isolation requires Linux; deployment was not started`. No namespace was created. No VM/container/WSL was installed, no host firewall was changed, and no external target was contacted.

## Deployment review

The existing deployment under `deploy/linux-egress/` requires Debian 13 amd64, root for namespace provisioning, `iproute2`, `nftables`, `procps`, `util-linux` (`setpriv`), systemd, and a prepared Python 3.13 environment. The runner refuses to start on non-Linux systems and refuses to reuse a namespace it did not create. It creates a namespace with only loopback, no veth or external route, disables forwarding, installs and validates a dedicated nftables ruleset, starts the API inside that namespace as a non-root user without capabilities, and checks the active policy and listener while running. Shutdown only removes the namespace created by this runner and fails cleanup if namespace processes remain.

The intended rules separate ingress and egress. Inbound permits established/related loopback traffic and new TCP connections to the API listener and enabled registered target ports. Outbound permits established/related loopback traffic and new TCP connections only to enabled registered target ports and explicitly configured local-client destination ports. Both directions default-drop; UDP/DNS, non-loopback destinations, other interfaces, and unlisted ports have no allow rule. The API listener port is not implicitly an outbound permission. An empty target registry permits no new outbound execution. These are configuration and source-review findings only; this report did not inspect an active Linux ruleset.

The startup probe uses a controlled local `HEAD`-only fixture. Its temporary test policy separately checks output drops and input drops: one fixture port is allowed by output but omitted from input, so input-drop counters can be tested independently. The temporary grants are removed before production policy is installed. These live probe steps were not run in this environment.

## Application security boundary review

Production API execution obtains a lease, reloads the assessment, then calls the authorized executor. The executor revalidates persisted target binding and authoritative authorization after lease acquisition. I added a second authorization/revocation check inside the production transport after the guarded permit is consumed and immediately before the HTTP engine call; it requires the issuer to match the checked issuer. Deterministic tests verify expired, revoked, and unavailable authorization prevents the HTTP engine from running at this dispatch boundary.

Regression tests also cover guarded API execution, exact registered endpoint binding, numeric loopback restrictions, connected-peer verification, redirect rejection, one `HEAD` request, no response-body processing, lease ownership/expiry, persistence rollback, evidence/findings persistence, and recovery. These tests ran on Windows with controlled local test fixtures; they do not prove those controls work inside a Linux namespace.

The deployment currently has no configured production authorization verifier or trusted issuer. No authority, approval, signing key, or production registration was invented for this audit. The verifier contract remains fail-closed; a real issuer, key provisioning, approval issue/renewal/expiry/revocation lifecycle, and deployment integration remain prerequisites for the authorized assessment workflow.

## Live connectivity evidence

No namespace identity, kernel version, interface listing, routing table, active nftables ruleset, firewall counters, or process-placement evidence was available. Therefore every live connectivity requirement below is **BLOCKED BY ENVIRONMENT**; configuration and unit tests are not substituted for those results.

| Required observation | Result | Evidence |
|---|---|---|
| Registered loopback TCP/HTTP service and authorized `HEAD` | BLOCKED BY ENVIRONMENT | No Linux namespace or production-authorized target was available. |
| Connected peer matches authorized loopback address and port | BLOCKED BY ENVIRONMENT | Application regression test exists; no in-namespace execution occurred. |
| Evidence/findings persisted and assessment reached terminal state | BLOCKED BY ENVIRONMENT | Windows application tests cover workflow persistence; Linux workflow not run. |
| Application restart and recovery inside namespace | BLOCKED BY ENVIRONMENT | Restart/recovery regression tests pass on Windows; no namespace deployment. |
| Unregistered loopback port and unauthorized inbound connections | BLOCKED BY ENVIRONMENT | Probe/counter checks are implemented, but no active firewall was available. |
| Public IPv4/IPv6, external DNS, and unauthorized destination ports blocked | BLOCKED BY ENVIRONMENT | No Linux route tables or firewall counters to correlate with connectivity attempts. No public connection was attempted. |
| No alternate interface, host route, or host-network fallback | BLOCKED BY ENVIRONMENT | Runner checks are implemented but could not be observed live. |
| Active firewall state persists while deployment runs | BLOCKED BY ENVIRONMENT | No service process or namespace was running. |

### Requirement classifications

| Requirement | Classification | Reason |
|---|---|---|
| Windows environment discovery and fail-closed runner preflight | NOT VERIFIED for Linux acceptance | The Windows refusal was directly observed, but it is not live Linux evidence. |
| Debian 13 namespace, active nftables rules, counters, and process placement | BLOCKED BY ENVIRONMENT | No Linux runtime or namespace capability is present. |
| Positive and negative network tests from inside the namespace | BLOCKED BY ENVIRONMENT | No Linux namespace was available to execute them. |
| API guarded boundary, authorization, endpoint, peer, HEAD-only, lease, persistence, and recovery behavior | NOT VERIFIED for the Linux deployment | Windows regression tests pass, but no live Linux workflow was exercised. |
| Production approval issuer and verifier integration | NOT VERIFIED | No trusted authority is configured; synthetic verifiers are test-only. |
| Security requirement failures observed in this task | None observed | One initial test assertion mismatch was corrected; see test history. |

## Test and verification results

The focused rows are separate, disjoint test modules and are not summed. The full-suite run overlaps those modules and is reported separately. Each run reports 0 failures and 0 skips.

| Command | Collected | Passed | Failed | Skipped | Pytest duration | Exit |
|---|---:|---:|---:|---:|---:|---:|
| `python -m pytest tests/test_linux_egress_deployment.py --durations=0 -q` | 11 | 11 | 0 | 0 | 0.18 s | 0 |
| `python -m pytest tests/test_guarded_execution.py --durations=0 -q` | 63 | 63 | 0 | 0 | 0.39 s | 0 |
| `python -m pytest tests/test_safety_policy.py --durations=0 -q` | 45 | 45 | 0 | 0 | 0.34 s | 0 |
| `python -m pytest tests/test_authorization_verification.py --durations=0 -q` | 21 | 21 | 0 | 0 | 6.94 s | 0 |
| `python -m pytest tests/test_assessment_lifecycle_recovery.py --durations=0 -q` | 36 | 36 | 0 | 0 | 6.03 s | 0 |
| `python -m pytest tests/test_assessment_execution_api.py --durations=0 -q` | 29 | 29 | 0 | 0 | 10.31 s | 0 |
| `python -m pytest tests/test_assessment_creation_api.py --durations=0 -q` | 16 | 16 | 0 | 0 | 8.21 s | 0 |
| `python -m pytest tests/test_local_persistence_api.py --durations=0 -q` | 17 | 17 | 0 | 0 | 14.60 s | 0 |
| `python -m pytest tests/test_passive_pipeline.py --durations=0 -q` | 41 | 41 | 0 | 0 | 9.01 s | 0 |
| `python -m pytest --durations=0 -q` | 800 | 800 | 0 | 0 | 40.57 s | 0 |

Other checks:

| Check | Result | Duration / exit |
|---|---|---|
| Compile `run_isolated.py`, `policy.py`, and `isolation_probe.py` with Python `compile()` | 3 scripts compiled | 1.27 s / exit 0 |
| `git diff --check` | No whitespace errors; Git printed existing LF-to-CRLF working-copy warnings | exit 0 |
| Linux runner preflight using the example config | Failed closed before deployment as required | about 1.15 s / exit 1 |

The first egress policy test iteration after adding the independent input-drop fixture had 11 collected, 10 passed, 1 failed, 0 skipped (0.47 s). The failure was a test expectation that omitted the temporary fixture port from the validator's expected port set. That assertion was corrected; the final focused egress run above passed all 11 tests. This was not a live firewall test.

## Reproduction on Debian 13

Use a dedicated Debian 13 amd64 VM or native Linux host with the prerequisites listed in [`deploy/linux-egress/README.md`](../deploy/linux-egress/README.md). Prepare dependencies through the approved artifact process; do not install or download them from the isolated runner. Configure the runner and systemd unit there, keep the production target registry empty until a real authorization verifier and approved registration are configured, then start the service. The runner runs the isolated connectivity probe before production startup. Capture the commands and outputs listed in the README (`ip netns exec ... ip -brief address`, IPv4/IPv6 route tables, `nft -a list ruleset`, namespace listener/process inspection, and service journal). Record counter deltas and the controlled probe's positive/negative results. Do not mark the live requirements verified until those observations come from the running namespace.

## Repository state

The initial `git status --short` was captured before task edits. It already contained user changes: modified and deleted tracked files, a pre-existing `uv.lock` modification, and untracked project artifacts, deployment files, tests, and prior reports. Those entries were preserved. The final status has the same pre-existing entries plus this report:

```text
?? docs/TASK_06_4_4_LIVE_LINUX_ISOLATION_REPORT.md
```

No `uv.lock` or Flutter files were edited by this task. Nothing was staged or committed, and no destructive Git command was run. No byte-for-byte preservation claim is made.
