# TASK 06.4.2 — Authorization Provenance & Deployment Security Readiness

**Audit date:** 2026-11-24  
**Verdict:** **CONDITIONAL PASS**

## Acceptance summary

The application now treats `authorization_ref` as an identifier, not proof. Assessment creation and execution require an injected authoritative verifier. A verifier must establish a trusted issuer signature for the exact target, endpoint, registration version, and validity window, and check revocation against a fresh authoritative source. Missing verifiers, unknown issuers, invalid evidence, expired or revoked approvals, stale revocation data, and verifier errors all fail closed. The same authorization is checked during creation, before lease acquisition, and again after claiming the lease immediately before guarded network dispatch.

No issuer, approval, signing key, signature format, or production verifier has been invented or configured. Consequently, this checkout does not authorize production assessments until an organization supplies and reviews a real verifier adapter and its trust configuration. The test-only synthetic verifier is not suitable for deployment.

Application-level endpoint, connected-peer, guarded-dispatch, passive `HEAD`, lease, and transaction controls remain covered by the regression suite. OS-level egress isolation was not enforceable or inspectable in this Windows execution environment, so deployment isolation remains blocked pending deployment-side evidence.

## Authorization trust and lifecycle

The current target registry stores an `authorization_ref` string. A string in local configuration or the assessment database cannot prove that an approval was issued, signed, is still valid, or has not been revoked. The trust boundary is the `AuthorizationVerifier` protocol in `aegiscore/authorization_verification.py`; the deployment must inject an implementation backed by an actual approval authority and pinned issuer public keys.

The authoritative approval must bind at least:

- a unique authorization reference;
- issuer ID and signing key ID;
- target ID, canonical scheme/host/port/path, and target registration version;
- issue/validity-start time and expiry time;
- a signature over all approval claims.

The verifier must reject unknown or disabled issuer/key IDs, invalid signatures, claim mismatches, not-yet-valid or expired approvals, and revoked approvals. Revocation must be checked on every verification call. If it uses a signed cached revocation snapshot, the snapshot must be signature-verified and have a short explicit freshness limit; an expired snapshot or unavailable authority is an `UNAVAILABLE` denial. The application independently checks the verifier's returned identity, claim bindings, signature-valid flag, revocation flag, timezone-aware timestamps, expiry, and revocation freshness.

Lifecycle:

1. **Issue:** the real approval authority issues and signs a target-specific, endpoint-specific, version-specific approval. AEGISCORE does not issue approvals.
2. **Register:** an operator installs a target registration that references that approval. The registration remains constrained to numeric loopback and exact configured endpoint rules.
3. **Validate on creation:** AEGISCORE asks the injected verifier to validate signature, claims, current validity, and revocation before persisting the assessment and the verifier metadata.
4. **Revalidate on execution:** AEGISCORE validates before acquiring a lease and again immediately before guarded dispatch. A changed registration or endpoint also fails before the HTTP request.
5. **Renew:** the authority issues a new signed approval or an updated signed validity grant. If its reference or scope changes, the operator updates the target registration and increments its version. Existing assessments bound to the previous version stop executing. The verifier returns current claims on the next request. AEGISCORE does not extend authorization expiry itself.
6. **Expire/revoke:** expiry denies automatically. Revocation denies on the next pre-execution check. If authorization status cannot be checked, execution is denied.

Persisted verification metadata is an audit record, not a substitute for re-verification. The verifier implementation and trusted issuer configuration are deployment dependencies; their cryptographic correctness cannot be established by tests against the synthetic test double.

## Deployment environment and egress policy

### Required baseline

Use a dedicated Linux network namespace on **Debian GNU/Linux 13 (Trixie), amd64**, with current Debian security updates, a kernel built with `CONFIG_NET_NS`, and nftables available. Run the API and its explicitly authorized local target fixture in the same dedicated namespace. The namespace must have only `lo` brought up: no veth pair, bridged interface, host networking, default route, DNS route, or other network device. Do not run unrelated or untrusted workloads in this namespace. A container is acceptable only when it has a private network namespace equivalent to `--network=none`; host networking is prohibited. Ensure its loopback device is up and enforce the rules below inside the namespace. Run any local UI in the same namespace or connect it through a Unix domain socket; do not publish an API TCP port onto the host network.

The exact Debian point release is expected to advance through security updates; pin the deployed image/package manifest by digest/version and record it with the release evidence. Debian identifies 13 (Trixie) as the current stable release; network namespaces isolate network devices, routing tables, firewall rules, and sockets when supported by the kernel. See [Debian stable releases](https://www.debian.org/releases/) and [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html).

The current Windows host could not be inspected for effective firewall policy, and Docker was unavailable in this shell. Windows Defender Firewall's documented default outbound behavior allows traffic unless a matching rule blocks it, so an application loopback check cannot be treated as host egress isolation. See [Windows Firewall best practices](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-firewall/best-practices-configuring) and [Set-NetFirewallProfile](https://learn.microsoft.com/en-us/powershell/module/netsecurity/set-netfirewallprofile).

### Required firewall policy

Inbound and outbound policy are separate:

| Direction | Default | Allowed traffic |
|---|---|---|
| Inbound to the namespace | Drop | TCP on loopback only to the API listener port and the specifically registered local target listener ports; return traffic for allowed loopback connections. |
| Outbound from the namespace | Drop | TCP on `lo` only to the API listener port, the explicitly registered local target listener ports, and a local authorization verifier port only if that verifier is deployed in the same namespace. Return traffic for allowed loopback connections. |

No DNS, UDP, non-loopback IPv4/IPv6, or other ports are allowed. The listener port set below is an example; deployment must replace it with the API port and the exact reviewed registered target ports. Firewall rules constrain addresses, protocols, and ports; exact URL scheme/path and no-redirect behavior remain application controls. Keep the API authorization verifier local (same namespace over a Unix socket or a separately reviewed loopback-only listener). A remote approval service would violate this deployment's loopback-only egress requirement. A cached approval/revocation bundle must be signed by the trusted authority and rejected when stale.

Example nftables ruleset for an API on TCP 8000 and one approved local target on TCP 18080:

```nft
table inet aegiscore {
  chain input {
    type filter hook input priority filter; policy drop;
    iifname "lo" ct state established,related accept
    iifname "lo" ip daddr 127.0.0.0/8 tcp dport { 8000, 18080 } ct state new accept
    iifname "lo" ip6 daddr ::1 tcp dport { 8000, 18080 } ct state new accept
  }

  chain output {
    type filter hook output priority filter; policy drop;
    oifname "lo" ct state established,related accept
    oifname "lo" ip daddr 127.0.0.0/8 tcp dport { 8000, 18080 } ct state new accept
    oifname "lo" ip6 daddr ::1 tcp dport { 8000, 18080 } ct state new accept
  }
}
```

Load this policy only in the dedicated namespace. A minimal namespace setup is:

```sh
sudo ip netns add aegiscore
sudo ip -n aegiscore link set lo up
sudo ip netns exec aegiscore nft -c -f /etc/aegiscore/egress.nft
sudo ip netns exec aegiscore nft -f /etc/aegiscore/egress.nft
sudo ip netns exec aegiscore nft -a list ruleset
```

Start the API and the approved local target processes with `ip netns exec aegiscore ...`, bind listeners only to `127.0.0.1` or `::1`, and run both as a dedicated unprivileged service identity. Add every authorized target port explicitly and remove ports when registrations are revoked. The ruleset must not be applied to the host's primary namespace.

### Reproducible deployment verification

Run these checks from the deployment host after namespace and firewall setup. They inspect local configuration and send no packet to a public or external destination:

```sh
ip netns exec aegiscore ip -brief address
ip netns exec aegiscore ip route show
ip netns exec aegiscore ip -6 route show
ip netns exec aegiscore nft -a list ruleset
ip netns exec aegiscore ss -lntup
ip netns exec aegiscore ip route get 192.0.2.1   # must report unreachable/no route
ip netns exec aegiscore ip -6 route get 2001:db8::1 # must report unreachable/no route
```

Acceptance evidence must show only `lo`, no IPv4/IPv6 default route, input/output base chains with drop policies, only the expected loopback TCP ports allowed, and listeners only on numeric loopback addresses. Confirm a request against the authorized local fixture uses one `HEAD` and succeeds; confirm application tests deny a different port/path, hostname, redirect, non-loopback address, expired/revoked approval, and missing verifier. Do not probe a public destination. Preserve the ruleset, command output, package/image digest, kernel version/configuration, target registration, and test report with deployment evidence. Re-run these checks after image, kernel, firewall, or listener changes.

These deployment steps were **not run** in this task environment. The ruleset is a required deployment control and an example policy, not evidence that egress isolation currently exists.

## Security acceptance matrix

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Authorization reference is not treated as proof | **VERIFIED** | Assessment creation requires an injected `AuthorizationVerifier`; no verifier means a sanitized unavailable denial. |
| Signature, trusted issuer/key, claim binding, expiry, and revocation contract | **VERIFIED** | Explicit verifier protocol and independent returned-evidence validation; deterministic tests cover invalid signature, unknown issuer, expired, revoked, stale revocation snapshot, malformed/missing verifier outcomes. |
| Real authoritative verifier and issuer trust roots | **NOT VERIFIED** | No real authority, key provisioning, signature format, verifier adapter, or approval record is present. Production creation/execution stays disabled until an actual reviewed verifier is injected. |
| Authorization lifecycle rules for issue, renewal, expiry, and revocation | **VERIFIED** | Application contract is defined above; renewal is authority-issued and never locally extended. Expiry/revocation/outage fail closed at creation and pre-dispatch. Actual authority-side lifecycle operations remain **NOT VERIFIED** because no authority integration is configured. |
| Recheck authorization immediately before network execution | **VERIFIED** | Route preflight plus executor revalidation after lease claim; tests force expiry, revocation, and verifier outage at the final pre-dispatch check and assert no transport request. |
| Guarded boundary, exact endpoint, connected peer, redirects, and passive HEAD | **VERIFIED** | Existing focused regression suites pass; the executor uses a one-use guarded permit, numeric loopback and exact registration, checks peer address/port, rejects redirects, and sends a single bounded `HEAD`. |
| Lease ownership, recovery, rollback, evidence, and findings invariants | **VERIFIED** | Existing lifecycle and pipeline regressions included in the focused and full suites. |
| OS/container egress isolation in this environment | **BLOCKED BY ENVIRONMENT** | Windows firewall state could not be queried, Docker was unavailable, and no Linux namespace was provisioned. No OS-level isolation is claimed. |
| Deployment egress policy is specified and reproducible | **VERIFIED** | Debian 13 network namespace baseline, separated inbound/outbound rules, nftables example, and local-only verification commands are documented above. Deployment-side enforcement evidence remains required. |

## Verification record

| Suite | Collected | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|---:|
| Focused creation, execution, lifecycle recovery, passive pipeline, safety policy, guarded boundary, and authorization tests | 248 | 248 | 0 | 0 | 16.64 s |
| Authorization verifier tests (included in the focused suite above) | 18 | 18 | 0 | 0 | 2.96 s |
| Full Python regression suite | 786 | 786 | 0 | 0 | 37.96 s |

The authorization-only row is a separately timed subset and is not additional to the 245 focused tests. All final runs completed without intermediate failures. Tests use synthetic authorization evidence only; they validate fail-closed application behavior, not production issuer cryptography.

## Repository state

The initial and final `git status --short` snapshots were captured. At path level, the only new untracked paths are `aegiscore/authorization_verification.py`, `tests/test_authorization_verification.py`, and this report. All other modified, deleted, and untracked paths were already present in the initial snapshot. The pre-existing `uv.lock` modification remains present; this task did not edit it. No Flutter files were changed, and no path was staged or committed. No destructive Git operation or byte-for-byte preservation claim is made.
