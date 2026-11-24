# TASK 06.8 — Reliability, Integration & Release Readiness

**Audit date:** 2026-11-24  
**Environment:** Windows workspace; Python virtual environment and Flutter SDK available. No live provider or trusted authorization source was configured.

## Release verdict

**NOT READY for a full-stack release.** The existing components pass their regression suites and the backend and web bundle start locally. A full browser-to-backend assessment could not be completed in the current runtime: authentication, durable storage, and the authoritative target verifier are not configured, and a real cross-origin browser preflight is rejected. These controls fail closed as designed. TASK 06.4.4 OS-level egress verification remains deferred.

The supported workflow is coherent under deterministic test fixtures. The current deployment configuration is not sufficient to run that workflow as an authenticated, authorized web application.

## Architecture and API audit

### Backend

- `aegiscore/api/app.py` constructs the FastAPI application, validates loopback API binding, loads optional local configuration, and owns lifespan startup/shutdown for periodic lease recovery.
- `aegiscore/api/auth.py` implements one locally provisioned Argon2id account, permission-scoped bearer sessions, and bounded session expiry. Sessions are held in process memory.
- `aegiscore/api/routes.py` implements health/capabilities, authentication, offline record reads, and passive assessment create/execute/read routes.
- `aegiscore/target_authorization.py` resolves a numeric loopback endpoint against a registered target. `aegiscore/authorization_verification.py` requires an injected authoritative verifier. `aegiscore/production_execution.py` binds the API execution path to the guarded boundary and checks the connected peer.
- `aegiscore/execution.py` makes one bounded passive HTTP `HEAD` request. The configured request budget is 5 seconds and the lease adds a 25-second safety margin. It does not read a response body or follow redirects.
- `aegiscore/passive_detector.py` derives deterministic configuration observations from persisted response-header evidence. `aegiscore/assessment_ai.py` is an optional advisory layer; it does not create authoritative findings.
- `aegiscore/local_persistence.py` stores assessments, evidence, findings, and results in SQLite. Terminal writes and recovery use transaction and lease checks; startup recovery is followed by a bounded periodic recovery worker while a store path is configured.
- The repository also contains separate offline evaluation, RAG, model-adapter, and custom FSM modules. Those modules are not needed to execute the narrow passive assessment route. No orchestration replacement was made.

### Flutter

- `frontend/lib/` uses Material 3, GoRouter, Riverpod, an injectable `http.Client`, a live/demo repository split, and platform secure storage for the bearer token.
- `ApiAegisCoreRepository` maps the assessment create, list, detail, execute, findings, and evidence endpoints. The client sends only `target_url` on create and sends a bodyless execute request.
- Assessment-specific finding/evidence details are separate from the app's offline fixture and evaluation screens. Advisory text is rendered separately as plain text and validated against loaded official finding/evidence references.
- During this audit, target choices and their default were aligned to `http://127.0.0.1:3000` / `http://127.0.0.1:8080`. The UI now rejects `localhost`, matching the backend's canonical numeric-loopback authorization contract.
- Client endpoint configuration is compile-time (`--dart-define`): `AEGIS_MODE` defaults to `demo`; `AEGIS_API_BASE_URL` defaults to `http://127.0.0.1:8000/`. Live mode only accepts a loopback host. Connect/request timeouts default to 5/15 seconds; API responses are limited to 2 MiB.

### API contract compatibility

| Operation | Backend contract | Flutter integration status |
| --- | --- | --- |
| Login/session/logout | `POST /auth/login`, `GET /auth/session`, `POST /auth/logout` | Uses the same local bearer-session contract; 401 expires the client session |
| Create | `POST /assessments` with `{ "target_url": "..." }` | Matches the schema; no client authorization claim is sent |
| History | `GET /assessments?offset=…&limit=…` | Loads the first 50; refresh is manual |
| Details | `GET /assessments/{id}` | Matches the persisted assessment response |
| Execute | `POST /assessments/{id}/execute`, empty body | Matches the route; backend owns execution and state transitions |
| Findings/evidence | `GET /assessments/{id}/findings` and `/evidence` | Loaded per assessment and rendered separately |
| Advisory | Optional `execution_result.ai_review` | Display-only; there is no per-assessment enable endpoint or request field |

The audit found and corrected one client/backend mismatch: the previous Flutter target list sent `localhost`, while the backend deliberately accepts only canonical numeric loopback literals. The target list, setup default, client-side lab validation, and assessment contract fixtures now use `127.0.0.1`; a regression test asserts that `localhost` is rejected by the client. This is an in-scope compatibility correction and does not relax backend authorization.

The root and frontend READMEs still describe Live Mode as supporting only health/capabilities and describe older unsupported assessment screens. That documentation is stale relative to the implementation and TASK 06.7 report. It was not changed in this audit because the task limits documentation changes to this report.

## End-to-end verification

### Local process probe

A local-only probe started the FastAPI ASGI server on an ephemeral `127.0.0.1` port with a temporary SQLite file, served the release web bundle on a second loopback port, fetched the health endpoint and web index, then shut both servers down. Results:

- Backend `/health`: **200**.
- Flutter release `index.html`: **200**, `text/html`.
- Backend graceful shutdown: **verified**; lifespan returned and the recovery worker stopped.
- All probe listeners were bound to `127.0.0.1`; the temporary database was outside the repository and removed afterward.
- A live login attempt in the current unconfigured runtime returned **503**.
- A browser-style `OPTIONS /auth/login` preflight from the separately served web origin returned **405** with no `Access-Control-Allow-Origin` header.

This was a process and static-asset probe, not a browser-driven authenticated assessment. The preflight result is direct evidence that the current separate-origin Flutter Web and API composition cannot authenticate in a browser without a same-origin serving/proxy arrangement or an explicitly configured CORS policy.

### Supported workflow steps

| Step | Result | Evidence / limitation |
| --- | --- | --- |
| Start backend | **Verified locally** | Uvicorn app answered `/health`; graceful shutdown completed |
| Start Flutter Web artifact | **Verified locally** | Release bundle served and returned its HTML entry point |
| Authenticate | **Blocked by current configuration** | No auth settings were present; `/auth/login` returned 503. Cross-origin preflight returned 405 |
| Create assessment | **Blocked in the live runtime; verified in tests** | No target registry or authoritative verifier is configured, so creation/execution are disabled. Tests inject explicit test-only registry/verifier fixtures |
| Execute authorized numeric loopback target | **Verified with controlled test fixture only** | Backend execution tests use a local `ThreadingHTTPServer` bound to `127.0.0.1`, including peer verification; no production authority was fabricated |
| Retrieve history/details | **Verified in API tests; unavailable in current runtime** | Tests persist and reload records. No `AEGISCORE_LOCAL_STORE_PATH` is configured in this runtime |
| Retrieve findings/evidence | **Verified in API and persistence tests; unavailable in current runtime** | Tests check transactional persistence, evidence references, and reload; live endpoints fail closed without configured storage |
| Render deterministic results | **Verified in Flutter widget/client tests** | Official severity/status and evidence references remain sourced from backend values |
| Display advisory when enabled | **Verified with deterministic fake adapter** | Reviewer integration tests verify separate advisory output and preserve official findings |
| Advisory disabled/unavailable | **Verified** | Current app has no reviewer adapter; reviewer failure tests preserve deterministic findings and terminal status |

The current imported runtime configuration was inspected without printing credentials or file contents:

```text
API host: 127.0.0.1
Authentication configured: false
Authorized target registry configured: false
Authorization verifier configured: false
Assessment executor enabled: false
SQLite path configured/available: false/false
Advisory reviewer enabled: false
```

These missing settings are release blockers, not reasons to bypass authorization. The full supported workflow is covered across API, local transport, persistence/restart, reviewer, and Flutter contract/widget tests, but there is no passing single browser-to-live-API run in this environment.

## Regression and release verification

Durations are wall-clock command times from this Windows environment. Focused backend tests are included in the full Python suite and should not be added to its total.

| Check | Collected | Passed | Failed | Skipped | Command duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Focused backend auth/authorization/execution/lifecycle/reviewer/persistence/security set | 285 | 285 | 0 | 0 | 35.8 s (pytest reported 33.10 s) |
| Full Python regression suite (`pytest -q`) | 840 | 840 | 0 | 0 | 47.1 s (pytest reported 44.99 s) |
| Full Flutter test suite after numeric-loopback correction | 60 | 59 | 0 | 1 | 21.6 s (runner displayed 18 s) |
| Flutter analyzer after numeric-loopback correction | — | clean | 0 issues | — | 10.0 s (analyzer reported 6.9 s) |
| Final live loopback release Web build | — | succeeded | — | — | 62.4 s (compiler reported 59.4 s) |
| Local backend/Web startup and shutdown probe | — | succeeded | — | — | 4.6 s |

The single skipped Flutter test is `phase_8g6_e2e_test.dart`; it skips unless `AEGISCORE_PHASE_8G6_E2E_BUNDLE` points to a fixture bundle. No bundle was supplied. That test covers the older offline persisted-session experience, not the new passive-assessment route. The Flutter workflow tests for this task use a controlled fake HTTP client; they do not exercise a real browser/API origin pair.

The two Web builds used these configurations:

```text
flutter build web --release --no-pub
flutter build web --release --no-pub --dart-define=AEGIS_MODE=live --dart-define=AEGIS_API_BASE_URL=http://127.0.0.1:8000/
```

The default/demo build also succeeded before the target-picker correction. The final build above was produced after that correction. Flutter emitted a non-fatal warning that a `packages/cupertino_icons/CupertinoIcons` font was expected but only `MaterialIcons` was found; the repository's Flutter source does not directly reference `CupertinoIcons`. The default build remains demo mode; the live build compiles to the loopback endpoint. Neither build configures a remote or same-origin production deployment.

### Failure and concurrency coverage

The passing focused and full Python suites include:

- Authentication configuration, missing configuration, permissions, session expiry, and loopback API enforcement.
- Authorization invalid/expired/revoked/unavailable cases; missing authority fails closed.
- Guarded boundary, endpoint binding, connected-peer mismatch, redirects, bounded HEAD timeout, and safe execution failure transitions.
- Duplicate/concurrent execution prevention; SQLite persistence failure recovery without restart; application restart retrieval; stale lease recovery; concurrent recovery/renewal; terminal lease ownership; transaction rollback.
- Advisory output schema, untrusted evidence, timeout/provider failure, repeated failure, reference validation, and deterministic-finding preservation.
- Flutter request/response parsing, live-mode auth expiry, errors, findings/evidence rendering, advisory separation, and assessment state transitions.

No regression test failed. No external target or provider was contacted. The production loopback workflow was intentionally not attempted because the current process has no valid authoritative approval configuration.

## Configuration, security, and privacy findings

### Verified application-level controls

- API listener defaults to `127.0.0.1`; configuration rejects a non-loopback API host. Request middleware also rejects non-loopback peers/hosts.
- Target creation/execution requires the registered target and injected authoritative verifier. A loopback IP by itself is insufficient. The production executor checks exact endpoint binding and connected peer.
- Execution remains one bounded `HEAD` request, with a 5-second budget and 25-second lease margin; redirect/body/GET/scanning behavior was not added.
- Authentication uses Argon2id password hashes, permission-scoped bearer sessions, and a bounded TTL. Backend session state is volatile; the Flutter client stores its token through platform secure storage and revalidates it with `/auth/session`.
- Deterministic findings remain authoritative. The optional reviewer is off by default, accepts an explicit in-process adapter, and cannot mutate official findings or lifecycle state.
- Flutter source/assets were searched for common Gemini/OpenAI/Anthropic key patterns; no matches were found. Flutter contains no provider SDK call in the assessment client.
- Login request schema bounds username to 128 characters and password to 1,024; target URL is bounded to 2,048. The client bounds response bodies to 2 MiB. SQLite operations use a 5-second busy timeout. Advisory prompt/response budgets are bounded in the reviewer code.
- API logging observed in the application logs generic startup/configuration messages; request bodies and password values are not deliberately logged. Login validation errors are redacted, and the password field is excluded from model repr.

### Configuration and integration gaps

- Relevant backend configuration is split across `AEGISCORE_API_HOST`/`AEGISCORE_API_PORT`, `AEGISCORE_AUTH_*` or a private auth TOML file, `AEGISCORE_LOCAL_STORE_PATH`, and `AEGISCORE_AUTHORIZED_TARGETS_FILE`. The authorization verifier is injected into `create_app`; there is no configured production issuer/verifier in this runtime.
- Missing auth or target-verification configuration leaves assessment creation/execution unavailable. Missing local store configuration leaves persisted-record endpoints unavailable. This is fail-closed and was observed in the runtime probe.
- The app enforces per-field sizes but has no application-level global HTTP request-body limit. The loopback-only binding reduces exposure but is not a substitute for a deployment request-size cap.
- The backend installs no CORS middleware. A cross-origin browser preflight was observed returning 405. Release must either serve/proxy the client and API from a same origin or establish a narrowly scoped CORS policy appropriate to the actual deployment.
- Live Flutter mode restricts the base URL to loopback. A static web app opened from another machine would resolve `127.0.0.1` to that user's machine. The API does not provide remote access, and the repository does not define a same-origin reverse proxy or production Web hosting profile.
- Browser session persistence uses `flutter_secure_storage`; the Web release compiled, but secure-store behavior was not exercised in a real browser. Backend session loss on restart is safe (client revalidation fails and requires sign-in) but needs user-facing deployment verification.

## Deployment security checklist

### Verified application-level controls

- [x] Loopback-only API configuration and request boundary.
- [x] Fail-closed target authorization and verifier interface.
- [x] Exact target endpoint binding and connected-peer verification in production execution path/tests.
- [x] Passive single-HEAD request scope and bounded execution timeout.
- [x] Lease ownership, expiry, transaction rollback, recovery, and duplicate-execution tests.
- [x] Advisory reviewer opt-in at backend configuration boundary; default disabled and failures isolated.

### Verified configuration-level controls

- [x] Missing auth, local database, authorization registry, or verifier does not authorize execution.
- [x] Backend host defaults to loopback; port is range-checked.
- [x] Flutter live mode accepts only loopback API hosts and uses bounded timeouts/response size.
- [x] Live web build compiles with the loopback API endpoint.

### Unverified operating-system-level controls

- [ ] No Linux namespace, firewall, container, or host-level outbound restriction was verified in this Windows environment.
- [ ] Do not treat the application loopback checks as OS-level egress isolation.
- [ ] TASK 06.4.4 remains deferred; this report makes no egress-isolation guarantee.

### Required Debian 13 live verification before deployment

1. Provision the documented Debian 13 runtime in a dedicated network namespace (or an equivalently enforceable isolated host/container) with no external route or DNS resolver.
2. Apply and inspect default-drop inbound and outbound firewall policy. Add only explicit loopback interface allowances and the exact local service ports required. Keep UI/API inbound access separate from the assessment executor's outbound permission. Do not add veth/external routes unless a separately reviewed access design requires them.
3. Start AEGISCORE inside the isolated boundary and make the isolation launcher fail if namespace/firewall checks are missing or inconsistent. Verify the policy remains installed for the entire service lifetime.
4. Run positive and negative connectivity checks from inside the service boundary: authorized local fixture succeeds; unauthorized loopback port fails; host-network, public IPv4, public IPv6, and external DNS fail. Capture actual namespace, route, and firewall state with the results.
5. Configure only an institution-approved, trusted authorization issuer/verifier and a real authorized numeric-loopback fixture. Verify issue/expiry/revocation behavior without storing fabricated approvals or signing keys in the repository.
6. Choose a browser composition that respects loopback-only policy. Verify the exact Web origin/API path and preflight behavior; use a same-origin local proxy or narrowly scoped CORS only after the deployment origin is known.
7. Configure a protected SQLite path and local Argon2id account, confirm backups/permissions, then rerun backend and Flutter suites plus the browser-driven create/execute/history/detail/findings/evidence/reviewer workflow.

## Release blockers and remaining limitations

1. **No production authorization authority is configured.** The verifier interface is present and fail-closed, but current process configuration has no trusted verifier or approval record source.
2. **No authenticated persistence runtime is configured.** The audit runtime has no auth settings or `AEGISCORE_LOCAL_STORE_PATH`; sign-in returns 503 and assessment reads/writes cannot operate.
3. **Flutter Web cannot currently authenticate cross-origin.** A real OPTIONS preflight returned 405 without CORS headers. A same-origin proxy/hosting arrangement is not included.
4. **No intended production Web origin/API deployment profile exists.** Live mode compiles only to a loopback endpoint; a remote browser would address its own loopback interface.
5. **No browser-driven real assessment run was completed.** Existing tests provide strong deterministic coverage but use TestClient, controlled local HTTP servers, fake reviewer adapters, or mocked Flutter HTTP clients.
6. **OS-level egress isolation is unverified.** Debian 13 live verification remains required under TASK 06.4.4.
7. **Global request-body size enforcement is absent in the app.** Configure it at the serving boundary or add a bounded middleware before release.
8. **Documentation is stale.** Root/frontend READMEs still describe a health/capabilities-only live client. The single environment-gated Flutter E2E test was skipped because its fixture bundle was not supplied.
9. **UI constraints remain:** first 50 assessments only, manual refresh, no demonstrated real-browser secure storage, and no live provider integration. These are documented MVP limits, not reasons to weaken backend controls.

## Recommended final thesis milestone

Run one evidence-backed **local deployment acceptance** milestone after a trusted authority and intended same-origin web composition are supplied: provision Debian 13 isolation, start the isolated backend plus live Flutter web client, perform the complete assessment lifecycle against an authorized local fixture, restart the process and recover state, exercise advisory enabled/disabled/failure modes with a deterministic adapter, and publish captured firewall state plus exact test/build results. Keep live model providers disabled unless separately approved.

## Repository safety and Git status

- Initial `git status --short`: **105 entries** — 35 deleted, 24 modified, 46 untracked. This was captured before any TASK 06.8 changes. It included the existing `uv.lock` modification, earlier backend/frontend work, previous reports, and unrelated user files.
- Final `git status --short`: **108 entries** — 35 deleted, 26 modified, 47 untracked. All 105 initial entries remained with the same status. The status delta is two newly modified paths (`frontend/lib/core/constants/app_constants.dart` and `frontend/lib/services/lab_scope.dart`) plus `?? docs/TASK_06_8_RELIABILITY_RELEASE_READINESS.md`.
- In-scope source/test edits were made to align Flutter target URLs and fixtures with numeric loopback enforcement: `frontend/lib/core/constants/app_constants.dart`, `frontend/lib/services/providers.dart`, `frontend/lib/services/lab_scope.dart`, `frontend/test/api_repository_test.dart`, `frontend/test/assessment_details_test.dart`, and `frontend/test/state_management_test.dart`. These paths were already modified at task start; the final short-status delta therefore remains the report only.
- No unrelated pre-existing file was edited. Flutter build output is ignored. `uv.lock` remains in its pre-existing modified state and was not edited by this task.
- No destructive Git commands, staging, or commits were used.
- Final `git diff --check`: **passed**. Git emitted non-fatal LF-to-CRLF working-copy warnings for modified files, including `uv.lock`.

