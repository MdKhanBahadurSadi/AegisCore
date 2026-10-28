# Phase 8G.3 — Flutter–FastAPI Integration

This guide records the API and screen coverage at the end of Phase 8G.3. Phase 8G.4 subsequently adds the approved-evidence routes and Evidence & Provenance integration described in `docs/PHASE_8G4_READ_ONLY_API_EXPANSION.md`.

## Implementation checklist

- [x] Inspect the FastAPI routes and Flutter repository/provider/screen contracts.
- [x] Add explicit demo/live configuration and a typed client for existing routes.
- [x] Keep unsupported live features and backend failures visible without fixture fallback.
- [x] Add mocked transport, mode selection, screen, and duplicate-submission tests.
- [x] Record endpoint mapping, screen coverage, test results, and remaining capabilities.

## Existing API contracts

This phase reuses the two read-only routes in `aegiscore/api/routes.py`:

| Route | Response | Meaning |
| --- | --- | --- |
| `GET /health` | `{"status":"ok"}` | The API process answered an in-process request. It does not imply lab readiness or downstream service health. |
| `GET /capabilities` | `service`, `version`, `implemented`, `not_implemented` | Static inventory from `CapabilitiesResponse`; it does not indicate assessment readiness. |

There are no backend endpoints for assessment submission or history, findings, evidence/provenance, dashboard metrics, or evaluation reports. No endpoints were added in this phase. The live repository reports those contracts as unsupported and does not return fixture records for them.

### Dart field mapping

- Python `HealthResponse.status` maps to `BackendHealthResponse.status`.
- Python `CapabilitiesResponse.service`, `version`, `implemented`, and `not_implemented` map to `BackendCapabilitiesResponse.service`, `version`, `implemented`, and `notImplemented`.
- The parser requires the exact current response keys and value types. HTTP errors, timeouts, transport errors, and malformed payloads become safe user-facing states; response bodies and credentials are not logged or shown.

## Configure and run

Demo fixture mode is the default and makes no API requests:

```powershell
cd frontend
flutter run
```

Run the API on loopback and select live mode explicitly:

```powershell
python -m uvicorn aegiscore.api:app --host 127.0.0.1 --port 8000
cd frontend
flutter run --dart-define=AEGIS_MODE=live --dart-define=AEGIS_API_BASE_URL=http://127.0.0.1:8000/ --dart-define=AEGIS_CONNECT_TIMEOUT_SECONDS=5 --dart-define=AEGIS_REQUEST_TIMEOUT_SECONDS=15
```

`AEGIS_MODE` accepts `demo` or `live`. `AEGIS_API_BASE_URL` must be an HTTP(S) URL with no user information, query, or fragment. The endpoint shown in Settings is sanitized by that validation. `AEGIS_CONNECT_TIMEOUT_SECONDS` bounds waiting for response headers; `AEGIS_REQUEST_TIMEOUT_SECONDS` bounds reading the response body. Browser deployments must arrange same-origin routing or an explicitly configured CORS policy outside this client.

The persistent top banner identifies demo, live, connecting, or backend-unavailable state. Live request failures never change the selected mode or fall back to fixtures.

## Screen coverage

| Screen | Demo fixture mode | Live backend mode |
| --- | --- | --- |
| Dashboard | Existing synthetic findings and evaluation fixtures, labeled by the demo banner | Unsupported state; no assessment, finding, or metric endpoints exist |
| Assessment Setup | Local target validation and synthetic demo session only; no assessment is executed | Submission disabled; only the client-side localhost:3000/8080 scope check is available |
| Findings and Finding Details | Existing synthetic finding, claim, locus, review, and evidence-reference fixtures | Unsupported state; no finding endpoints exist |
| Evidence & Provenance | Existing demonstration fixtures with their fixture approval labels | Unsupported state; no evidence or provenance endpoint exists |
| Evaluation Reports | Existing synthetic fixture report remains clearly labeled | Unsupported state; no report endpoint exists |
| Settings | Shows fixture mode and that the configured backend URL is not contacted | Calls `/health` and `/capabilities`, displays safe endpoint information and backend-declared capabilities |

HTTP behavior is tested with mocked clients. No network test targets are contacted.

## Verification

- `flutter analyze` — passed with no issues.
- `flutter test` — 30 passed.
- `python -m pytest tests/` — 611 passed.

No backend route or schema was modified, so no new Python endpoint tests were needed. The existing API tests continue to assert the current read-only routes and unsupported-route behavior.

## Safety and remaining work

No execution endpoint was invented. Live assessment submission remains unavailable because the backend has no explicitly authorized offline execution API. The client-side lab URL check is form validation only and is not backend authorization or proof of network isolation. No target scanning, Docker activity, model downloads, provider calls, external inference, or evidence approval changes were introduced. Heuristic confidence remains uncalibrated; evaluation fixtures are not empirical results. Pending supervisor decisions DEC-01 through DEC-08 remain pending, and the source review manifest was not changed.

Further Live Mode integration still requires persistent assessment and finding records, an evaluation report repository, and an authorization design. The API remains unauthenticated and should stay loopback-only. Any execution contract must remain offline-compatible and preserve the existing safety gates; the current live UI continues to report unsupported capabilities until those records and endpoints exist.
