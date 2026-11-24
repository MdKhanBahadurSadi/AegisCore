# TASK 06.8.1 — Runtime Configuration, Authentication & Browser Integration Remediation

**Date:** 2026-11-24  
**Repository:** `C:\AegisCore`  
**Verdict:** **CONDITIONAL PASS for code remediation; NOT READY for live release acceptance.**

The application now has a configurable exact-origin CORS policy, stricter startup validation for explicitly configured authentication and SQLite paths, and owner-only SQLite permissions on POSIX. Focused and full Python regressions pass. A live authenticated browser assessment is still unverified because this runtime has no real authentication configuration, authorized-target registry, or trusted authorization verifier. The current host is Windows, so Linux permissions and deployment egress policy were not verified.

## Changes

| File | Change |
| --- | --- |
| `aegiscore/api/app.py` | Added `AEGISCORE_CORS_ALLOWED_ORIGINS` and an optional factory argument for explicit origins. Origins are normalized and validated; wildcards, paths, credentials, queries, fragments, malformed ports, blank values, and duplicates fail configuration. CORS permits only `GET`, `POST`, and preflight `OPTIONS`, with `Accept`, `Authorization`, and `Content-Type` request headers. Credentialed cookies are disabled. Actual route authentication and authorization dependencies remain in place. A configured SQLite path that is blank, invalid, inaccessible, or has an unsupported schema now aborts app startup with a sanitized error. An absent path remains health-only: persistence routes report unavailable and no in-memory or temporary database is selected. |
| `aegiscore/api/auth.py` | An explicitly configured missing, blank, or malformed auth TOML path now fails configuration loading instead of silently behaving like an absent auth source. With no auth source configured, protected operations still fail closed. |
| `aegiscore/local_persistence.py` | Creates missing database parent components with mode `0700` on POSIX, creates SQLite files with mode `0600`, and tightens existing POSIX database files to `0600`. `:memory:` remains rejected. |
| `tests/test_runtime_configuration.py` | Added exact-origin/preflight and auth-boundary tests, unsafe CORS configuration tests, SQLite startup and permission tests, and a two-process persistence test. |
| `docs/TASK_06_8_1_RUNTIME_CONFIGURATION_REMEDIATION.md` | This audit and deployment configuration record. |

The three modified backend files already had uncommitted work before this task. Their earlier changes were inspected before editing and retained. No Flutter files or `uv.lock` were changed. No files were staged or committed.

## Configuration and Runtime Contracts

### Browser origins and CORS

Set `AEGISCORE_CORS_ALLOWED_ORIGINS` to a comma-separated list of the browser's serialized origins, without trailing slashes or paths. For example, `http://127.0.0.1:8080` is used only as a local test/example origin; deployments must use the actual Flutter Web origin. A production origin must be supplied by the deployment owner and configured exactly. There is no built-in development or production allowlist, and absence of the setting disables cross-origin access. Wildcards are rejected.

The CORS policy does not authorize users. An allowed-origin preflight succeeds, while an actual protected request without a bearer token remains `401`. A disallowed origin receives no `Access-Control-Allow-Origin` header; its unauthenticated protected request also remains `401`. The client uses the existing `AEGIS_API_BASE_URL` compile-time setting. CORS is relevant only when the UI and API use different origins; same-origin hosting does not need it.

The current runtime probe found no CORS origin allowlist. The repository does not identify the actual production Web origin, so no production origin was invented or enabled.

### SQLite runtime persistence

Use `AEGISCORE_LOCAL_STORE_PATH` to select the persistent SQLite file. Missing path configuration leaves health/capability endpoints available, reports `/storage/status` as `not_configured`, and leaves persistence-backed functions unavailable. It never falls back to a temporary file or in-memory database. A blank setting, invalid path, inaccessible database, or unsupported schema now aborts startup rather than starting in a partially configured state.

Missing parent directories are created. On POSIX, new directories are owner-only (`0700`) and the database is owner read/write (`0600`). Existing POSIX database files are tightened to `0600`. This Windows run cannot verify POSIX mode enforcement. Windows ACLs are inherited from the parent and are not inspected by this implementation; deployment administrators must secure the parent directory ACL. Local process-restart persistence was verified with a writer process exiting and a fresh Python process reading the assessment record. Existing API lifecycle tests also verify persistence across app recreation and recovery.

### Authentication setup

The existing authentication loader supports either these environment variables or a TOML file:

| Setting | Contract |
| --- | --- |
| `AEGISCORE_AUTH_USERNAME` | Non-empty username, at most 128 characters. |
| `AEGISCORE_AUTH_PASSWORD_HASH` | Argon2id hash; plaintext passwords are not accepted as configuration. |
| `AEGISCORE_AUTH_SESSION_TTL_SECONDS` | Optional integer from 1 through 86,400; default is 1,800 seconds. |
| `AEGISCORE_AUTH_PERMISSIONS` | Optional comma-separated subset of `records:read`, `evidence:read`, `assessments:create`, and `assessments:execute`. Omitted permissions use the existing default set. |
| `AEGISCORE_AUTH_CONFIG_FILE` | Optional path to a private TOML file containing `[auth]`, `username`, `password_hash`, and optional `session_ttl_seconds` and `permissions`. |

When any credential environment variable is present, both username and Argon2id hash are required; partial configuration fails. An explicitly selected missing or blank TOML path now fails startup. If no authentication source is configured at all, login and protected APIs remain unavailable; no anonymous access is enabled. On POSIX, the TOML file must be owner-only. On Windows, file ACLs are not checked by the current loader and remain an administrator responsibility. Sessions are held in memory, so a backend restart requires users to sign in again.

Without `AEGISCORE_AUTH_CONFIG_FILE`, the loader checks `%LOCALAPPDATA%\AEGISCORE\auth.toml` on Windows or `$XDG_CONFIG_HOME/aegiscore/auth.toml` (falling back to `~/.config/aegiscore/auth.toml`) on Unix-like systems. An administrator can create an Argon2id hash through an interactive hidden prompt, then put that hash in a protected secret store or private config file:

```powershell
python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Password: ')))"
```

No real credential or password hash was supplied or used here. Tests use synthetic test-only settings.

### Authoritative target authorization

The existing boundary is `AuthorizationVerifier` in `aegiscore/authorization_verification.py`. It requires a trusted issuer set and verified evidence bound to the authorization reference, issuer/key IDs, target ID, canonical endpoint, registration version, signature digest, validity timestamps, and a fresh revocation snapshot. Missing, invalid, unknown-issuer, expired, revoked, stale, or unavailable verification fails closed.

Target registrations are read from `AEGISCORE_AUTHORIZED_TARGETS_FILE`, a TOML file containing one or more `[[targets]]` tables. Each table must contain exactly `target_id`, `scheme`, `hostname`, `port`, `permitted_paths`, `authorization_ref`, `network_zone_id`, `enabled`, and `registration_version`. The hostname must be a canonical numeric loopback address. This file binds an endpoint to an approval reference; the reference string is not proof of authorization.

There is no production verifier implementation, issuer/key configuration variable, trusted key material, or approval source configured in this repository runtime. `create_app` receives the verifier as an injected dependency, but the production `aegiscore.api.__main__` entry point constructs the app without one. A production verifier integration therefore still needs a deployment-owned implementation and a supported injection/configuration path. The authority must supply the real approval reference and signed claims, pinned public issuer keys/key IDs, and an authoritative revocation source with freshness limits. The synthetic verifier used in tests is explicitly test-only. A real authority integration and a real approval were not fabricated; target assessment remains disabled in the current runtime.

## Verification Results

| Run | Collected | Passed | Failed | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Focused runtime configuration, auth, authorization, creation/execution, lifecycle recovery, persistence, passive pipeline, and advisory reviewer tests | 228 | 228 | 0 | 0 | 38.13 s |
| Full Python regression suite | 857 | 857 | 0 | 0 | 46.15 s |

The focused suite includes CORS allow/deny preflight behavior, rejection of unapproved methods and headers, proof that CORS does not bypass authentication, malformed allowlist rejection, fail-closed missing auth-file behavior, invalid SQLite startup behavior, SQLite file/parent handling, real subprocess restart persistence, existing lease recovery, transactional rollback, evidence/findings persistence, and advisory failure isolation. The full suite also passed. An earlier full run before the last two tests collected 855 and passed 855 in 42.82 seconds; final figures above are from the completed code state. No test failure was observed.

`git diff --check` is recorded in the final status below. Flutter files were not changed, so Flutter analyzer, widget tests, and release build were not rerun for this backend-only remediation. No real browser-to-production-API flow was run: the required real auth and trusted authorization source are absent. CORS behavior was exercised through FastAPI's HTTP test client, not a browser engine.

## Runtime Evidence and Readiness

The runtime probe reports:

| Prerequisite | Runtime state |
| --- | --- |
| Authentication configuration | Not configured |
| SQLite path / available store | Not configured / unavailable |
| Authorized-target registry | Not configured |
| Authoritative verifier | Not configured |
| Assessment executor | Disabled |
| CORS origin allowlist | Not configured |

The runtime therefore cannot authenticate a real user, resolve a real authorized target, execute a live assessment, or demonstrate a full browser workflow. Unit and integration tests establish code behavior with synthetic fixtures only. The full release acceptance condition is not met.

## Requirement Classification

| Requirement | Status | Evidence / limitation |
| --- | --- | --- |
| Exact configured CORS origins and successful valid preflight | **VERIFIED** | Explicit and environment-based allowlists pass test-client preflight. |
| Unapproved origin rejection and protected actual requests | **VERIFIED** | Unapproved preflight has no allow-origin header; protected request remains `401`. |
| Authentication settings validation and fail-closed absence | **VERIFIED** | Argon2id validation and session tests pass; explicit missing auth-file path fails; absent auth yields unavailable protected APIs. |
| Configured SQLite path initialization and invalid-path startup failure | **VERIFIED** | Tests cover nested directory creation, unusable directory target, blank setting, and `:memory:` rejection. |
| SQLite persistence after a fresh process starts | **VERIFIED** | A second Python process reads the record written by the first process. The record uses a test-only fixture. |
| POSIX database mode `0600` and newly created directory mode `0700` on deployment Linux | **BLOCKED BY ENVIRONMENT** | Code and conditional test assertions are present, but this task ran on Windows. |
| Windows auth-file ACL privacy | **NOT VERIFIED** | Auth TOML loader checks POSIX mode only; Windows ACL inspection is not implemented. |
| Real authenticated browser assessment | **BLOCKED BY ENVIRONMENT** | No real auth configuration, target registry, approval source, or production browser origin was supplied. |
| Real issuer signature, pinned key, expiration, and revocation integration | **BLOCKED BY ENVIRONMENT** | The verifier contract and fail-closed tests exist; no trusted production issuer or key material is configured. |
| OS/container egress isolation | **BLOCKED BY ENVIRONMENT** | TASK 06.4.4 remains deferred; this remediation does not claim operating-system enforcement. |

## Required Deployment Steps

1. Choose the actual Flutter Web origin and set `AEGISCORE_CORS_ALLOWED_ORIGINS` to that exact origin. Use the actual browser `window.location.origin`; do not include a path, trailing slash, or wildcard.
2. Provision `AEGISCORE_LOCAL_STORE_PATH` on persistent local storage. On Debian/Linux, confirm the parent directory is private and the database file is mode `0600`; on Windows, set and verify restrictive ACLs.
3. Provision one real local user through an approved secret-handling process. Supply the username and an Argon2id password hash, or a private `[auth]` TOML file with appropriate ACLs. Do not use test credentials.
4. Obtain an institution-approved target approval and configure a real `AuthorizationVerifier` adapter with pinned public issuer keys and an authoritative revocation source. The current app has no environment-variable verifier loader; deployment integration is still required.
5. With those real settings, perform a browser-driven login, assessment creation/execution against the exact authorized numeric-loopback endpoint, retrieval, backend restart, and retrieval again. Capture the actual origin, API results, persisted record, and verifier evidence without exposing secrets.
6. Separately complete TASK 06.4.4 with live Linux egress/firewall evidence. Application loopback validation is not OS-level isolation.

## Worktree Safety

Initial status was captured before changes: **108 entries** (35 deleted, 26 modified, 47 untracked). The final status is **110 entries** (35 deleted, 26 modified, 49 untracked); all initial paths remain represented, with only the two task deliverables added as untracked paths. Existing modified `uv.lock`, backend, frontend, documentation, and untracked user files were preserved. No destructive Git command, staging, or commit was used.

Final new paths:

- `docs/TASK_06_8_1_RUNTIME_CONFIGURATION_REMEDIATION.md`
- `tests/test_runtime_configuration.py`

`git diff --check` completed with exit code 0. Git emitted only existing line-ending normalization warnings for modified files.

## Final Verdict

**CONDITIONAL PASS for code remediation; NOT READY for production/full-stack acceptance.** Code-level CORS, startup validation, and persistence changes pass the Python regressions. Release acceptance remains blocked until an actual frontend origin, real authentication configuration, persistent deployment database, and trusted authorization issuer/verifier are supplied and exercised together. Linux permission and egress isolation evidence must be collected on the intended Linux deployment environment.
