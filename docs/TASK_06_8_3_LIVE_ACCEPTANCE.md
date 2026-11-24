# TASK 06.8.3 — Provisioned Environment Live Acceptance

**Date:** 2026-11-24
**Environment:** Windows development workspace
**Verdict:** **NOT READY — live release acceptance was blocked by missing operator configuration and deployment integration.**

## Acceptance summary

The existing read-only preflight and prior reports were rechecked. No live backend/browser workflow was started because required operator credentials, persistent deployment storage, target registry, authoritative verifier, and browser configuration are unavailable. The production launcher also has no verifier integration; the Linux namespace runner does not forward the app's CORS setting and starts no Flutter web service. Supplying environment values alone would therefore not complete live acceptance.

No credentials, keys, trusted issuer, approval records, or external targets were created or used. No security checks were bypassed. TASK 06.4.4 Linux egress verification remains **DEFERRED**.

## Exact operator input checklist

Values below are derived from the current source and deployment artifacts. Placeholders are requirements, not supplied values. Do not send passwords, hashes, signing keys, bearer tokens, or approval records through this report or ordinary chat.

### Authentication

- **Provider:** AEGISCORE's built-in local username/password authentication. The backend verifies a locally provisioned Argon2id hash and issues an opaque bearer token tracked in process memory. There is no external OIDC/JWT provider in the current implementation.
- **Issuer/audience:** Not applicable to the current local opaque-token contract. No issuer or audience settings exist in the backend authentication configuration.
- Supply either:
  - `AEGISCORE_AUTH_USERNAME` and `AEGISCORE_AUTH_PASSWORD_HASH`; or
  - `AEGISCORE_AUTH_CONFIG_FILE` pointing to a TOML file containing `[auth]`, `username`, `password_hash`, and optional `session_ttl_seconds` / `permissions`.
- Optional exact names: `AEGISCORE_AUTH_SESSION_TTL_SECONDS` (1–86400; default 1800) and `AEGISCORE_AUTH_PERMISSIONS` (subset of `records:read`, `evidence:read`, `assessments:create`, `assessments:execute`). Defaults grant all four.
- The default config path is `%LOCALAPPDATA%\AEGISCORE\auth.toml` on Windows, or `$XDG_CONFIG_HOME/aegiscore/auth.toml` / `~/.config/aegiscore/auth.toml` on Linux. Linux deployment uses `AEGISCORE_AUTH_CONFIG_FILE` and requires the file to be owned by the service account with mode 0600 or stricter.
- The operator provisions the password and Argon2id hash out of band. Protect the secret source and parent directories; never commit credentials or print them. Test actual login and expiry without recording the bearer token. Frontend code sends it as an `Authorization: Bearer` header and uses its `FlutterSecureStorage` adapter for session storage; confirm the selected browser platform's storage behavior before deployment.
- **Current supplied state:** No usable authentication configuration is available. No login was attempted.

### Persistent database

- **Backend variable:** `AEGISCORE_LOCAL_STORE_PATH`.
- **Linux runner variable:** `AEGISCORE_STORE_PATH`, mapped to `AEGISCORE_LOCAL_STORE_PATH` for the child API process. The runner default is `/var/lib/aegiscore/records.sqlite3`.
- **Default deployment parent:** `/var/lib/aegiscore`; the existing deployment instructions create it for the dedicated `aegiscore` user/group with mode 0750. The runner validates/creates state for that service identity. SQLite files are created as 0600 on POSIX.
- Supply the actual durable absolute path, owning service identity/group, parent-directory mode, backup destination, retention, and restore owner. The repository has no configured backup/retention service or backup path. The operator must define an SQLite-consistent backup procedure, protect backups, and perform a restore test before acceptance.
- Verify database create, permissions, record write/read from a fresh process, backend restart/recovery, and inaccessible-path failure as the deployed identity. Invalid configured storage must fail startup; no in-memory fallback is allowed.
- **Current supplied state:** No `AEGISCORE_LOCAL_STORE_PATH` is configured. No deployment database was created or read.

### Target authorization

- **Backend variable:** `AEGISCORE_AUTHORIZED_TARGETS_FILE`.
- **Linux runner variable:** `AEGISCORE_TARGETS_FILE`, mapped to the backend variable. An empty value permits no target execution ports.
- The TOML file must contain one or more `[[targets]]` entries with exactly these fields: `target_id`, `scheme`, `hostname`, `port`, `permitted_paths`, `authorization_ref`, `network_zone_id`, `enabled`, `registration_version`.
- Provide only operator-approved numeric loopback endpoint registrations, exact paths and ports, and the matching registration version. A registry entry or `authorization_ref` is not proof of approval.
- **Authority inputs:** The authority must provide a real verifier integration, trusted issuer ID(s), pinned public verification key(s), signature format, signed claims binding reference + target ID + canonical endpoint + registration version + validity window, and a fresh authoritative revocation source with a defined freshness limit. Define who issues, renews, expires, and revokes grants.
- The verifier must check trust, signature, endpoint/version binding, timezone-aware `issued_at` / `expires_at`, and fresh revocation at dispatch. Its returned evidence must be consistent with the current `VerifiedAuthorizationEvidence` contract, including issuer/key IDs, verified/revocation-check times, validity window, signature digest, and revoked/signature flags. Unknown issuer, invalid signature/evidence, not-yet-valid/expired/revoked grant, stale revocation state, or unavailable verifier must deny execution.
- **Implementation blocker:** The repository defines an `AuthorizationVerifier` protocol and validates its result, but has no production verifier, issuer/key loader, revocation client, health contract, or environment-variable setting. The normal launcher imports the default app without injecting a verifier. This cannot be satisfied by supplying a string or adding undocumented environment variables; an approved production integration is required before an authorized live assessment can run.
- **Current supplied state:** No target registry or authority-backed verifier is configured. No approval was verified.

### Browser and API

- Supply the **actual frontend browser origin** (scheme, host, and port) and the loopback API base URL for the same supported browser/runtime topology.
- Backend CORS setting: `AEGISCORE_CORS_ALLOWED_ORIGINS`, a comma-separated exact origin list. Each origin must be HTTP(S), with no path, credentials, query, fragment, wildcard, or duplicate. CORS permits only `GET`, `POST`, `OPTIONS`; headers `Accept`, `Authorization`, and `Content-Type`; credentials are disabled; preflight max age is 300 seconds. Authentication remains bearer-token based.
- Flutter compile-time settings: `AEGIS_MODE=live` and `AEGIS_API_BASE_URL=<HTTP(S) loopback API URL>` using `--dart-define`. The current URL default is `http://127.0.0.1:8000/`, but mode defaults to demo; this default is not a provisioned deployment value. Live mode accepts only `localhost`, `127.0.0.1`, or `::1`, and rejects URL credentials, query, and fragment. Live mode must be explicitly selected.
- The API origin and browser origin are different values when cross-origin; CORS must contain the browser origin, not merely the API origin. Confirm browser mixed-content and secure-context behavior for the chosen exact pair. Do not place backend secrets or provider credentials in Flutter assets/build defines.
- **Deployment gap:** `deploy/linux-egress/run_isolated.py` accepts only its listed `_CONFIG_KEYS` and constructs a child environment that does not include `AEGISCORE_CORS_ALLOWED_ORIGINS`. It also starts only the API, not Flutter Web. Its namespace has only loopback and no veth/host route, so a browser running on the host cannot reach the namespace's `127.0.0.1`. The current deployment artifacts do not provision a browser/frontend inside that namespace or another reviewed access path. This must be resolved and verified without weakening the isolation policy before browser-to-API acceptance.
- **Current supplied state:** No CORS origin or `AEGIS_API_BASE_URL` was supplied; no frontend/API origin pair or browser was tested.

### Operating system and isolated deployment

- **Supported live egress baseline in the existing proposal:** patched Debian 13 (Trixie), amd64; systemd; Python 3.13 environment provisioned offline/through approved artifacts; kernel network namespaces; `iproute2`, `nftables`, `procps` (`sysctl`), and `util-linux` (`setpriv`). Root is required for the supervisor to create/check namespace and nftables policy. The API runs under a dedicated non-root `aegiscore` identity with capabilities dropped.
- Existing `/etc/aegiscore/linux-egress.conf` contract names: `AEGISCORE_NAMESPACE`, `AEGISCORE_API_PORT`, `AEGISCORE_TARGETS_FILE`, `AEGISCORE_LOCAL_CLIENT_PORTS`, `AEGISCORE_RUN_USER`, `AEGISCORE_RUN_GROUP`, `AEGISCORE_APP_ROOT`, `AEGISCORE_PYTHON`, `AEGISCORE_STORE_PATH`, `AEGISCORE_AUTH_CONFIG_FILE`. Do not add undocumented keys or run the provisioner outside the supported Debian 13 environment.
- Required policy: default-drop inbound and outbound; only `lo`; no veth, bridge, default/external route, DNS, UDP, or public egress. Outbound permits only registered loopback TCP target ports and explicitly reviewed local-client destination ports. Inbound service access is separately limited. Application policy further binds exact scheme, numeric address, port, and path and makes one passive HTTP HEAD request.
- Required evidence: OS release and architecture; service identity and file permissions; `ip netns` addresses/routes; active `nft` ruleset and counters; process/listener placement; controlled authorized loopback HEAD succeeds; unlisted loopback ports, external routes, UDP/DNS fail; rules remain active for service lifetime.
- **Current supplied state:** Host is Windows. No Debian 13 environment or live OS/firewall evidence is available. TASK 06.4.4 remains deferred.

## Configuration inventory and preflight

The existing preflight was run read-only. It did not start a server, authenticate, create storage, or contact any target. Its output contained no secret values.

| Result | Count | Finding |
|---|---:|---|
| PASS | 1 | API host/port configuration has loopback and range shape; no listener was probed. |
| BLOCKED | 4 | Authentication config missing; persistent SQLite path missing; target registry missing; production verifier unavailable. |
| WARNING | 1 | No browser CORS allowlist; same-origin configuration is possible but unverified. |
| NOT VERIFIED | 2 | Flutter compile-time API URL not supplied; OS egress isolation not inspected. |

The script returned exit code 2. The configured listener values use the supported defaults, but this is not evidence that a backend is running. No supplied authentication, target approval, issuer key, revocation data, database path, browser origin, or Linux security configuration was found by the preflight.

### Acceptance evidence

| Acceptance step | Result | Evidence / reason |
|---|---|---|
| Backend start with deployment settings | **Not attempted** | Required auth, storage, target, and verifier configuration absent. |
| Flutter Web from actual origin | **Not attempted** | No browser origin or live API base URL; the current isolated unit does not start Flutter Web. |
| OPTIONS/CORS | **Not performed live** | No browser-origin pair; isolated runner does not forward the CORS setting. Contract tests ran only. |
| Authentication | **Not performed live** | No configured local account/password hash. No credentials were generated. |
| Authoritative target verification | **Blocked** | No production verifier integration, trust material, or approval record. |
| Numeric loopback assessment | **Not attempted** | Would be unauthorized without the authority-backed verifier. No target request was sent. |
| Persisted history/findings/evidence | **Not performed against deployment DB** | No persistent path configured. Existing regression fixtures are not live acceptance evidence. |
| Backend restart/recovery | **Not performed against deployment** | No configured service or database. Fixture lifecycle and process-persistence tests passed. |
| Advisory behavior | **Not performed live** | Backend reviewer remains opt-in and no live workflow was available. Regression tests cover deterministic/fake adapters only. |
| Debian 13 permissions and egress | **NOT VERIFIED / DEFERRED** | Current host is Windows; no Debian 13 firewall/process evidence. |

## Regression results

| Run | Collected | Passed | Failed | Skipped | Pytest duration | Command wall time |
|---|---:|---:|---:|---:|---:|---:|
| Focused configuration/auth/API/CORS/authorization/persistence/recovery/advisory/Linux-policy suite | 175 | 175 | 0 | 0 | 21.53 s | 23.45 s |
| Full Python suite | 863 | 863 | 0 | 0 | 45.43 s | 47.58 s |

Focused files: `test_runtime_configuration.py`, `test_api.py`, `test_authorization_verification.py`, `test_assessment_lifecycle_recovery.py`, `test_assessment_creation_api.py`, `test_assessment_execution_api.py`, `test_assessment_ai_integration.py`, and `test_linux_egress_deployment.py`. These are deterministic tests using local fixtures; they do not replace live acceptance. Flutter files were not changed, so Flutter checks were not run.

`git diff --check` exited 0. It emitted existing LF-to-CRLF working-copy warnings for pre-existing modified files, including `uv.lock`, but no whitespace errors. No staging, commit, destructive Git command, `uv.lock` edit, or Flutter edit was performed.

## Exact unresolved release blockers

1. Operator has not provisioned the local API authentication account and protected configuration.
2. No persistent deployment database path, service identity, permissions, backup, or restore acceptance is configured.
3. No actual authorized target registry or approval from a real target owner is available.
4. No production verifier, pinned authority/key material, signed approval format, or fresh revocation integration is implemented or configured.
5. The isolated deployment launcher does not forward `AEGISCORE_CORS_ALLOWED_ORIGINS`, and it does not start a frontend. The no-veth namespace is unreachable from a host browser; there is no reviewed browser-to-API path in the current artifacts.
6. No actual browser origin/API URL pair has been configured or tested.
7. No Debian 13 live OS-level egress verification has been performed; TASK 06.4.4 remains deferred.

## Repository status

Initial status before this task: **113 entries** (**35 deleted, 26 modified, 52 untracked**). The pre-existing `uv.lock` modification and all other worktree entries were preserved.

Final status after this report: expected **114 entries** (**35 deleted, 26 modified, 53 untracked**); the only new status entry is `docs/TASK_06_8_3_LIVE_ACCEPTANCE.md`. This was verified after writing the report. No hash-based byte-preservation claim is made.

## Final verdict

**NOT READY.** Regression tests and configuration inspection passed, but the required genuine authentication, authoritative target authorization, persistent deployment execution, browser-to-API workflow, and Debian 13 security verification have not been completed. Do not grant live release acceptance until each blocker above is resolved with redacted runtime evidence.
