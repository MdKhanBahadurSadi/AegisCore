# TASK 06.8.2 — Deployment Provisioning & Acceptance

**Date:** 2026-11-24
**Environment:** Windows development workspace
**Verdict:** **CONDITIONAL PASS for provisioning preparation only; live release acceptance is BLOCKED.**

This task adds a safe configuration reference and a read-only local preflight. It does not create credentials, approval records, signing material, or a verifier. The active environment lacks the external configuration needed for a genuine authenticated assessment, and it cannot establish Debian egress isolation.

## Configuration inventory

| Dependency | Current contract | Classification | Current state / operator action |
|---|---|---|---|
| API authentication | Local username plus Argon2id password hash, supplied either by `AEGISCORE_AUTH_USERNAME` and `AEGISCORE_AUTH_PASSWORD_HASH`, or a private TOML file selected by `AEGISCORE_AUTH_CONFIG_FILE` | Implemented, externally provisioned | Not configured here. Provision the account through an operator-controlled secret process. Never commit the password or hash. |
| Authentication lifetime and permissions | Optional `AEGISCORE_AUTH_SESSION_TTL_SECONDS` (1–86400, default 1800) and `AEGISCORE_AUTH_PERMISSIONS` (comma-separated known permissions; default all four) | Implemented, optional | No live login was performed. Session state is process-local and must be treated as expired after restart. |
| Auth TOML | `[auth]` with `username`, `password_hash`, optional `session_ttl_seconds`, optional `permissions` | Implemented, externally provisioned | Default lookup is `%LOCALAPPDATA%\AEGISCORE\auth.toml` on Windows, or `$XDG_CONFIG_HOME/aegiscore/auth.toml` / `~/.config/aegiscore/auth.toml` on Linux. A configured missing or invalid file fails closed. |
| SQLite persistence | `AEGISCORE_LOCAL_STORE_PATH` | Implemented, not configured | No database path is configured in this workspace. There is no in-memory or temporary production fallback. Set a durable local path and run persistence acceptance as the service identity. |
| Authorized target registry | `AEGISCORE_AUTHORIZED_TARGETS_FILE`; TOML `[[targets]]` records with exactly `target_id`, `scheme`, `hostname`, `port`, `permitted_paths`, `authorization_ref`, `network_zone_id`, `enabled`, `registration_version` | Implemented, externally provisioned | Not configured. Only explicit numeric loopback targets can be registered. A valid registry and `authorization_ref` do not establish approval. |
| Trusted authorization verifier | `AuthorizationVerifier` contract injected into the API factory | Contract implemented; production adapter/wiring not implemented | No production verifier health/configuration interface exists. Production API startup does not establish a trusted authority. Missing verifier must continue to block assessment authorization/execution. |
| Issuer and verification material | Pinned issuer identity/key, signature verification, signed target/endpoint/version and validity claims, fresh revocation check | Externally provisioned and not implemented in production | None is supplied. Do not invent values or treat local registry strings as trust material. Unknown issuer, invalid signature, expiry, revocation, stale revocation state, or verifier outage must deny execution. |
| API listener | `AEGISCORE_API_HOST` defaults to `127.0.0.1`; `AEGISCORE_API_PORT` defaults to `8000` and must be 1–65535 | Implemented, default configured | Preflight confirms only the configured value shape. It does not inspect a listening process. Keep the listener on numeric loopback. |
| Browser origin / CORS | Optional comma-separated `AEGISCORE_CORS_ALLOWED_ORIGINS`; exact HTTP(S) origins only, with no path, credentials, query, fragment, wildcard, or duplicate | Implemented, not configured | No origin is configured. Cross-origin access is unavailable until the operator supplies the exact browser origin. Same-origin behavior was not tested. |
| Flutter API base URL | Compile-time `--dart-define=AEGIS_API_BASE_URL=<loopback API URL>` | Implemented, not supplied | The preflight cannot read a Flutter build's compile-time value unless `--frontend-api-base-url` is passed. No browser build or request was made. |
| Windows file ACLs | Auth, database, and registry access must be limited to the service/operator identities | Requires operator verification | The application and preflight do not validate effective Windows ACLs. Inspect the file and parent-directory ACLs under the actual service identity; do not rely on `chmod` semantics on Windows. |
| Linux file/directory permissions | Auth file owner-only (0600); SQLite file owner-only (0600); private state/config directories; no group/other write access | Application behavior partly implemented; operator verification required | The app creates missing SQLite parent directories privately (0700) and prepares its DB file with 0600 on POSIX. Verify pre-existing directories and file ownership/modes independently. |
| Linux egress | Debian 13 amd64 namespace/firewall policy described under `deploy/linux-egress/` | Proposed configuration; not verified | TASK 06.4.4 remains deferred. This Windows host cannot establish OS-level isolation. |

### Supported variable set

- Required for persistent assessment data: `AEGISCORE_LOCAL_STORE_PATH`.
- Required for configured API authentication: both `AEGISCORE_AUTH_USERNAME` and `AEGISCORE_AUTH_PASSWORD_HASH`, or a valid `AEGISCORE_AUTH_CONFIG_FILE`.
- Optional authentication controls: `AEGISCORE_AUTH_SESSION_TTL_SECONDS`, `AEGISCORE_AUTH_PERMISSIONS`.
- Required for authorized assessment targeting: `AEGISCORE_AUTHORIZED_TARGETS_FILE`, plus a real production verifier supplied through trusted application wiring. The verifier currently has no production loader or environment variable.
- Optional depending on deployment topology: `AEGISCORE_CORS_ALLOWED_ORIGINS`; absence disables cross-origin browser access.
- Optional listener values: `AEGISCORE_API_HOST`, `AEGISCORE_API_PORT`; keep host loopback-only.
- Flutter build input: `AEGIS_API_BASE_URL` Dart define; it is not a backend environment variable.
- Linux namespace runner has a separate configuration contract in `deploy/linux-egress/aegiscore-linux-egress.conf.example`. Its `AEGISCORE_TARGETS_FILE` maps to the backend's `AEGISCORE_AUTHORIZED_TARGETS_FILE`; runner `AEGISCORE_STORE_PATH` maps to backend `AEGISCORE_LOCAL_STORE_PATH`. Do not conflate these contracts.

## Safe configuration template

Added [runtime-config.06-8-2.example](../deploy/runtime-config.06-8-2.example). It is explicitly reference-only and intentionally contains placeholders, not usable credentials or approvals. Provision secrets through an approved secret manager or protected operator-managed file. Do not source or deploy the template unchanged. It does not define a verifier, key, issuer, or approval reference.

For a separate browser origin, configure the exact origin only, for example the operator's actual `https://<approved-browser-host>` origin without a path. Do not use `*`. The API CORS configuration is not authentication: protected routes still require a valid bearer session. No origin was supplied in this workspace.

Required settings fail closed at their trust boundaries: absent authentication leaves protected routes unavailable; an explicitly configured invalid auth file or invalid configured database path aborts app setup; a missing registry or production verifier denies authorized assessment execution. No in-memory database fallback is used.

## Read-only preflight

Added [deployment_preflight.py](../scripts/deployment_preflight.py). It checks configuration shape, existing SQLite schema, supported registry format, and permission conditions where the platform exposes POSIX modes. Optional `--frontend-api-base-url` validates the Flutter compile-time endpoint without displaying it.

The command does not create files/directories, open network connections, start the API, exercise login, ask a verifier, or modify SQLite. It redacts configured values and always reports verifier trust as blocked because no production verifier integration exists. Its output is a precheck only; a PASS cannot establish release acceptance.

Observed command result on this Windows workspace:

| Status | Count | Finding |
|---|---:|---|
| PASS | 1 | API listener values have the loopback/range shape; no listener was probed. |
| BLOCKED | 4 | No auth config, persistent DB path, target registry, or production authorization verifier. |
| WARNING | 1 | No CORS origin is configured; same-origin use is possible but unverified. |
| NOT VERIFIED | 2 | Flutter compile-time API URL not supplied; OS-level egress policy not inspected. |

The Python command returned exit code 2 because blocked prerequisites exist. It printed no secret values. Current host is Windows; Debian 13 verification is still required.

## Authentication and authorization provisioning

### Authentication

1. An operator provisions a unique username and password through the organization's approved secret process.
2. Generate an Argon2id hash locally or through an approved credential-provisioning tool; never place the plaintext password or hash in source control, command history, support logs, or this report.
3. Choose exactly one configuration method: the username/hash environment pair or a protected TOML file. On Linux, protect the TOML as owner-only (0600), with a private parent directory. On Windows, grant access only to the service identity and authorized administrators, including on parent directories.
4. Choose only the permissions required. Verify login and protected-route behavior in a deployment test that does not record the bearer token. Confirm expired sessions are rejected; restart invalidates process-local sessions.

No account or credential was created and no live login was tested.

### Target authorization

1. The target operator supplies the exact registry entries, including numeric loopback hostname, scheme, port, exact paths, registration version, and an authority-issued reference.
2. The responsible approval authority must define issuance, renewal, expiry, and revocation and provide a trusted verifier adapter, pinned issuer/key distribution, signature format, and authoritative fresh revocation source.
3. The verifier must bind the signature to the reference, target ID, exact canonical endpoint, and registration version; validate the signed time window; and perform a fresh revocation check at dispatch.
4. Test invalid signature, unknown issuer, not-yet-valid/expired grant, revoked grant, stale revocation state, and verifier outage. Each must deny execution before the HTTP request.

No authority, signing key, approval record, or synthetic production grant was created. An `authorization_ref` in a local registry is an identifier only.

## Persistence acceptance

The preflight found no configured `AEGISCORE_LOCAL_STORE_PATH`; it did not initialize a deployment database. The passing runtime-configuration tests exercised a temporary SQLite file: create a bound assessment, reopen and read it, retrieve it through an authenticated API fixture, and create/read it from two separate Python processes. On POSIX, those tests also assert the SQLite file and created parent-directory modes. Another test confirms an invalid configured database path aborts startup without falling back. Lifecycle recovery tests also ran in the focused and full suites. The new preflight tests prove that an absent database remains absent during inspection and that an existing temporary fixture database can be opened through `open_existing` without changing its modification time.

These are fixture/test results, not deployment acceptance. A real persistent path was unavailable, so this task did **not** verify permissions under the actual service identity, a running backend's restart/recovery behavior, or inaccessible-database behavior in the configured deployment. Run those after the operator provisions the path. The configured invalid/unavailable database path must abort startup; do not add an in-memory fallback.

## Browser-to-API acceptance evidence

**Not performed; blocked by missing configuration.** Authentication, persistent DB, target registry, authoritative verifier, browser origin, and Flutter API base URL are not all available. No backend/Flutter live workflow or HTTP request was attempted. Therefore there is no evidence for OPTIONS preflight, login, assessment creation/execution, persisted history, findings/evidence display, restart readback, or advisory rendering. Do not represent fixture tests as browser-to-API acceptance.

## Debian 13 deployment verification checklist

The existing `deploy/linux-egress/` proposal describes Debian 13 amd64, systemd, a named network namespace containing only loopback, nftables default-drop input/output chains, no veth/default route, a dedicated unprivileged API worker, and a supervisor that checks policy drift. Its deployment behavior was not run or modified in this task.

Before deployment acceptance, use a suitable Debian 13 host and record command output/evidence for all of these:

1. Verify Debian 13 amd64, required kernel namespace support, and required preinstalled tools. Install dependencies only through the approved package/artifact process.
2. Verify service account ownership and state/config directory modes; verify SQLite and auth file owner, mode, and writability as the actual API identity. Require auth TOML 0600, DB 0600, and private state/config directories.
3. Start only through the isolated systemd unit. Confirm namespace contains `lo` only, no veth/bridge, no default or non-loopback IPv4/IPv6 routes, and no external route.
4. Inspect the active nftables ruleset. Input and output base chains must each have default drop. Keep inbound API access and outbound target execution as separate allow rules.
5. Permit only explicitly registered loopback TCP ports: IPv4 `127.0.0.0/8`, IPv6 `::1`. The API listener is inbound only unless an explicitly reviewed same-namespace client port is needed. Outbound execution is limited to exact target-registration ports. Application policy still binds scheme, numeric address, port, and path.
6. Confirm no public DNS, UDP, non-loopback traffic, host route, or arbitrary outbound access. Use controlled local fixture checks only; verify firewall counters and policy persistence for the deployment lifetime.
7. Confirm API process identity, dropped capabilities, listener bound to numeric loopback, and that service shutdown removes its namespace only after the API exits.
8. Repeat persistence and end-to-end acceptance with real operator credentials and an authority-backed verifier. Keep the assessment request within the current passive HTTP HEAD policy.

Until these live checks complete, OS-level isolation is **NOT VERIFIED**. TASK 06.4.4 remains deferred.

## Verification results

| Run | Collected | Passed | Failed | Skipped | Pytest duration | Command wall time |
|---|---:|---:|---:|---:|---:|---:|
| Focused config/auth/lifecycle/API tests, including new preflight tests | 130 | 130 | 0 | 0 | 18.31 s | 20.45 s |
| Full Python suite | 863 | 863 | 0 | 0 | 44.80 s | 46.94 s |

The focused command covered `test_runtime_configuration.py`, `test_deployment_preflight.py`, `test_authorization_verification.py`, `test_assessment_lifecycle_recovery.py`, `test_api.py`, `test_assessment_creation_api.py`, and `test_assessment_execution_api.py`. The full suite was rerun after the final preflight/test edits. No Flutter files changed, so Flutter checks were not run.

`git diff --check` exited 0. Git emitted existing LF-to-CRLF working-copy warnings for modified files, including pre-existing `uv.lock`; it reported no whitespace errors. No Git staging/commit or destructive Git command was used. `uv.lock` and Flutter files were not edited by this task.

## Release blockers and verdict

- **BLOCKED:** No operator-provisioned authentication configuration or live authentication test.
- **BLOCKED:** No persistent database path or actual persistence/restart acceptance.
- **BLOCKED:** No target registry backed by real target-owner approval.
- **BLOCKED:** No production trusted issuer/verifier/key/revocation integration.
- **BLOCKED:** No browser origin/API URL pair and no browser-to-API acceptance.
- **NOT VERIFIED:** Windows ACLs and Debian 13 OS-level network isolation.

**Verdict: CONDITIONAL PASS for provisioning preparation only. Live release acceptance is BLOCKED.** Release acceptance can be granted only after genuine authentication, authoritative target authorization, persistent assessment execution, browser-to-API verification, and Debian egress verification have all succeeded with recorded evidence.

## Repository status

Initial `git status --short` was captured before task edits: **110 entries** (**35 deleted, 26 modified, 49 untracked**). The initial state already included modified `uv.lock`, extensive deleted/modified documentation and source files, and untracked `deploy/`, test, backend, and Flutter artifacts. These were preserved; no existing file was edited by this task.

Final `git status --short` after task edits: **113 entries** (**35 deleted, 26 modified, 52 untracked**). The only new status entries outside the already-untracked `deploy/` directory are this report, `scripts/deployment_preflight.py`, and `tests/test_deployment_preflight.py`. The new template is inside the pre-existing untracked `deploy/` directory. Existing `uv.lock` and Flutter status are unchanged.

The exact status snapshots were compared by path/status count. Final status output and focused/full test results were captured after implementation; no hash-based byte-preservation claim is made.
