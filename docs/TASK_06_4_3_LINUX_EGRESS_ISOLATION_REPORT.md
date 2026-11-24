# TASK 06.4.3 — Linux Egress Isolation Report

## Verdict

**CONDITIONAL PASS.** A reproducible Debian 13 deployment configuration and deterministic in-namespace verification procedure are implemented. The Python regression suite passes. The host for this task is Windows and has no WSL, Docker, or Podman, so no Linux namespace or nftables rules were actually created or exercised. OS-level isolation is therefore **not verified in this environment** and this report does not claim it is enforced here.

## Deployment implementation

Files added under `deploy/linux-egress/`:

- `run_isolated.py` provisions a fresh named network namespace, enables only `lo`, disables IPv4/IPv6 forwarding, installs and audits nftables policy, starts the API under a non-root identity with all capabilities dropped, verifies the API listener, and checks the namespace and firewall once per second. Drift or process failure stops the deployment. Shutdown stops the API before namespace cleanup; if a namespace process remains, cleanup refuses to remove the namespace.
- `policy.py` renders and validates the complete expected nftables table. Unexpected chains, declarations, rules, or policy changes fail validation.
- `isolation_probe.py` hosts a local fixture that implements only `HEAD`, verifies allowed IPv4/IPv6 loopback access, checks blocked loopback ports through nftables drop counters, and checks that reserved test and DNS addresses have no route.
- `aegiscore-isolated.service`, `aegiscore-linux-egress.conf.example`, and `README.md` document and configure the systemd deployment.

The runner requires Debian 13 amd64, root, systemd, Python 3.13, `iproute2`, `nftables`, `procps`, and `util-linux`. It refuses an existing namespace rather than reusing unknown state. No package download, network interface, veth, bridge, external route, or public DNS resolver is configured. The systemd unit limits socket families to IPv4, IPv6, and netlink and omits Unix-domain sockets. The API process is bound to `127.0.0.1`, runs without capabilities, and has no-new-privileges.

## Exact packet policy

The namespace has only `lo` with `127.0.0.1/8` and `::1/128`; its main IPv4 and IPv6 tables must contain no default or non-loopback route. nftables has exactly one `inet aegiscore` table and two base chains:

| Direction | Explicitly permitted | Default action |
|---|---|---|
| Inbound | Established/related traffic on `lo`; new TCP traffic arriving on `lo` to the API listener port or enabled registered target ports, addressed to `127.0.0.0/8` or `::1` | Drop all other inbound packets |
| Outbound | Established/related traffic on `lo`; new TCP traffic leaving on `lo` to enabled registered target ports and explicitly configured local-client ports, addressed to `127.0.0.0/8` or `::1` | Drop all other outbound packets |

UDP, DNS, unlisted TCP ports, non-loopback addresses, other interfaces, and external routes are not allowed. The API listener port is not an outbound execution permission. An empty target registry produces no new outbound permission. During startup only, a deterministic temporary fixture port and API-client permission are added to run the checks; the runner then replaces that policy with the production allowlist and validates the active ruleset before declaring startup successful. nftables limits this network policy by IP address and TCP port; the application authorization layer remains responsible for the exact scheme, endpoint, and path.

## Verification results

| Verification | Result | Duration |
|---|---:|---:|
| Focused deployment policy tests (`tests/test_linux_egress_deployment.py`) | 10 passed, 0 failed, 0 skipped | 0.11 s |
| Full Python regression suite | 796 collected; 796 passed, 0 failed, 0 skipped | 43.30 s |
| Deployment script syntax compilation | 3 scripts compiled | 1.09 s |
| Linux runner preflight on this host | Failed closed before deployment, as required | 1.19 s |
| Live Linux namespace, nftables, and connectivity checks | Not run | Blocked by environment |

The runner preflight reported: `Linux network isolation requires Linux; deployment was not started`. `wsl.exe --list --quiet` reported that WSL is not installed; Docker and Podman were not present. Thus the probe's positive and negative connectivity checks are implemented but have no live pass/fail results from this host. In particular, host-network separation, IPv4/IPv6 egress denial, DNS denial, firewall lifetime monitoring, and application operation inside the namespace remain **BLOCKED BY ENVIRONMENT**. The API's isolated startup check currently verifies a TCP listener/handshake only; it does not perform an HTTP API workflow.

The full-suite run included the existing assessment, lease, authorization, guarded execution, passive pipeline, persistence, safety-policy, and transaction tests. Earlier focused policy-test iterations found fixture/assertion mismatches (2 failures, then 1 failure); those assertions were corrected, and the final focused and full-suite runs passed. No live Linux test failed because none could be run.

## Authorization and trust status

The existing verifier contract remains fail-closed. This deployment creates no signing keys, approval records, issuer, or authority. The application has no production verifier loader configured here, so verified authorization from a trusted external authority remains **NOT VERIFIED**. Assessment creation and execution must remain disabled until a real verifier and trusted issuer are provisioned. That integration must verify signed target, endpoint, registration version, validity window, issuer/key, and fresh revocation status; define issuance, renewal, expiration, and revocation; and deny on unknown issuer, invalid signature, expired/revoked approval, stale revocation information, or verifier outage.

## Requirement classification

### VERIFIED

- Static policy generation produces default-drop input and output chains and exact configured loopback TCP port rules.
- Static regression tests reject unexpected rules/declarations and verify that API ingress and target egress are separate.
- The Linux runner has a non-Linux fail-closed preflight; that behavior was observed on Windows.
- The systemd unit and runner configuration keep target authorization fail-closed and do not configure an approval authority.
- Full Python suite: 796 passed, 0 failed, 0 skipped.

### NOT VERIFIED

- OS-level isolation in a running Debian deployment.
- Actual positive and negative IPv4/IPv6 loopback, public-route, DNS, and host-network connectivity outcomes.
- Firewall persistence and application workflow behavior while running inside the namespace.
- Integration with a real approval issuer, signature verifier, and revocation service.

### BLOCKED BY ENVIRONMENT

- Creating a Linux network namespace and applying/inspecting nftables: WSL is absent and no Docker/Podman runtime is installed on the Windows host.
- Testing the Debian 13 systemd deployment and its live connectivity probes.

## Git status preservation

The initial `git status --short` was already dirty: it contained pre-existing modifications and deletions across API, persistence, documentation, tests, and `uv.lock`, plus untracked audit reports and project artifacts. Those pre-existing entries were preserved. `uv.lock` remains in its pre-existing modified state; no Flutter files, staging, commits, or destructive Git operations were used.

The final status contains those existing entries plus these task files:

- `deploy/linux-egress/README.md`
- `deploy/linux-egress/aegiscore-isolated.service`
- `deploy/linux-egress/aegiscore-linux-egress.conf.example`
- `deploy/linux-egress/isolation_probe.py`
- `deploy/linux-egress/policy.py`
- `deploy/linux-egress/run_isolated.py`
- `docs/TASK_06_4_3_LINUX_EGRESS_ISOLATION_REPORT.md`
- `tests/test_linux_egress_deployment.py`

`git diff --check` completed without whitespace errors. The only unresolved deployment acceptance item is live Linux verification; until that is run on the proposed baseline, egress isolation must not be represented as verified.
