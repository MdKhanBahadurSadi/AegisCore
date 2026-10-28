# Phase 8G.7 — Authentication, Authorization & Deployment Security

## Inspection checklist

- [x] Reviewed FastAPI app construction, route groups, response models, configuration, and error paths.
- [x] Confirmed there was no existing authentication mechanism or password-hashing dependency to reuse.
- [x] Reviewed Flutter Live Mode configuration, repository/provider wiring, navigation, settings, and local persistence.
- [x] Preserved the SQLite schema and existing records; authentication state is not written to SQLite.
- [x] Added backend authorization checks, Flutter session handling, loopback safeguards, setup instructions, and security tests.

## Local account setup

The backend supports one locally provisioned account. There is no default username/password, administrator account, identity provider, or cloud dependency.

From the repository root, run:

```powershell
python scripts/setup_local_auth.py
```

The script prompts for a username and a password of at least 12 characters (twice). It writes an Argon2id password hash, a 30-minute session lifetime, and the read permissions to a per-user config file. It does not print the password or hash and refuses to overwrite an existing config.

- Windows default: `%LOCALAPPDATA%\AEGISCORE\auth.toml`; the file inherits the current user's Local App Data access control.
- Linux/macOS default: `$XDG_CONFIG_HOME/aegiscore/auth.toml`, or `~/.config/aegiscore/auth.toml`; the file is restricted to the owner (`0600`).
- For a custom path, pass `--config <path>` and set `AEGISCORE_AUTH_CONFIG_FILE` to that path before starting the API. Keep the file outside the repository and restrict it to the local user.

Argon2id hashes are verified with `argon2-cffi`. The API accepts environment overrides using `AEGISCORE_AUTH_USERNAME` and `AEGISCORE_AUTH_PASSWORD_HASH`; both must be set together. Optional `AEGISCORE_AUTH_SESSION_TTL_SECONDS` and `AEGISCORE_AUTH_PERMISSIONS` settings can reduce the session lifetime or permissions. Never put a plaintext password in an environment variable or source file.

`argon2-cffi` is declared in `pyproject.toml`. The checked-in Python lockfile could not be refreshed in this offline worktree because Argon2 package metadata is not present in the local `uv` cache. Regenerate `uv.lock` in a package-enabled environment before relying on `uv sync --locked` for a clean install; no package-index request was made for this phase.

Start the API through its loopback-validated launcher:

```powershell
python -m aegiscore.api
```

It binds to `127.0.0.1:8000` by default. `AEGISCORE_API_HOST` accepts only `127.0.0.1`, `::1`, or `localhost`; `AEGISCORE_API_PORT` selects a valid local port. `create_app()` rejects a non-loopback configured host. The ASGI boundary also rejects non-loopback peers and refuses requests when the server scope reports a non-loopback bind. Use the validated launcher rather than overriding the host through a separate server command.

If auth is not configured, `/auth/login` and every protected data route return HTTP 503. The Flutter app does not assume a session exists and Live Mode shows a setup/authentication error; it does not show demo fixtures.

## Authentication and authorization contract

- `POST /auth/login` accepts a username/password pair and returns an opaque, cryptographically random bearer token. Invalid usernames and passwords receive the same generic HTTP 401 response. Passwords and password hashes are not stored in application records.
- Tokens are represented server-side only by a SHA-256 digest. Session state lives in process memory, expires after 30 minutes by default, and is revoked at logout or process restart. No token migration or SQLite schema change was needed.
- `GET /auth/session` validates a bearer token and returns the local account name, permissions, and remaining lifetime. `POST /auth/logout` invalidates the presented session.
- Tokens are not written to application logs or error responses. Login and session responses use `Cache-Control: no-store`; invalid credentials and protected-route failures do not echo request values.
- Authenticated sessions receive permissions from local config. `records:read` covers persisted sessions, findings, reports, dashboard summaries, and storage details. `evidence:read` separately covers approved evidence list/detail endpoints. The setup script grants both; an operator may grant only the permissions needed.
- `GET /health`, `GET /capabilities`, and the limited `GET /storage/status` readiness summary do not disclose secrets or filesystem paths. These and all other API paths remain loopback-only.
- Missing, malformed, expired, or logged-out bearer tokens return HTTP 401. An authenticated account missing a route permission receives HTTP 403. An unavailable authentication service returns HTTP 503.

Protected data routes are:

| Permission | Routes |
|---|---|
| `records:read` | `GET /dashboard/summary`, `/sessions`, `/sessions/{session_id}`, `/sessions/{session_id}/findings`, `/findings`, `/findings/{finding_id}`, `/reports`, `/reports/{report_id}` |
| `evidence:read` | `GET /evidence/approved`, `/evidence/approved/{evidence_id}` |

The API remains read-only for assessment data. Authentication establishes a local identity; it does not authorize target selection or security testing. No source approval, supervisor-decision, assessment submission, or scan endpoint was introduced. Existing lab-scope validation, evidence grounding, citation checks, abstention behavior, and `confidence_is_calibrated=false` remain unchanged.

## Flutter Live Mode

- Live Mode opens a sign-in gate until it can validate a saved session through `GET /auth/session`.
- Passwords are sent only to the local backend and remain in the sign-in form's memory; the app stores only the bearer token through `flutter_secure_storage` platform storage, never ordinary preferences.
- Login verifies the newly returned token with `/auth/session` before treating the user as signed in. If secure storage is unavailable, the app revokes the just-created session where possible and stays signed out.
- Sign out calls `/auth/logout` and removes the local token. A 401 from a protected data request clears the saved session and returns to sign-in. A 403 is presented as an authorization error.
- Live Mode base URLs are restricted to `localhost`, `127.0.0.1`, or `::1`. Demo Fixture Mode does not read or use backend session state and remains a separate provider path.

The local bearer-session implementation is single-process: the default launcher runs one Uvicorn worker and sessions are not shared across worker processes. Restarting the API logs out all clients by design.

## Deployment boundaries and outstanding review

| Use | Status |
|---|---|
| Local development without auth config | Health, capabilities, and limited storage readiness only; protected routes fail closed with 503. |
| Authenticated local use | Supported for one local account over loopback after explicit setup. |
| Any broader/LAN/public deployment | Not supported. It requires a separate security review and deployment design. |

This phase does not establish production readiness. Before broader deployment, the project still needs independent review of TLS termination and proxy trust, network/firewall controls, credential/session lifecycle and rotation, account lifecycle, rate limiting, audit and retention, backups, platform secret-store behavior, and multi-process session storage. SQLite is not encrypted; operating-system file permissions remain its at-rest protection. No firewall was changed, no public service was launched, and no Docker, target, external provider, model download, source approval, or empirical benchmark was used. `docs/source-review-manifest.json` remains unchanged; DEC-01 through DEC-08 remain pending.

## Verification

The Phase 8G.7 regression run reported:

- `python -m pytest tests/` — 646 passed (22.04s).
- From `frontend/`, `flutter analyze` — no issues found (4.4s).
- From `frontend/`, `flutter test` — 48 passed, 1 skipped (the opt-in cross-stack widget test).
- `python scripts/verify_phase_8g6_e2e.py` — passed. FastAPI rejected missing and wrong credentials, served data only with the issued bearer, revoked the in-memory session on app recreation, and Flutter restored that session and sent its bearer on protected API reads while rendering actual FastAPI response bodies.
- `git diff --check` — passed after the final documentation update.
