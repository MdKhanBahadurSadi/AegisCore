# TASK 05.1 — AEGISCORE AI: Assessment API Security & Compatibility Hardening Report

**Execution Date:** 2026-11-23  
**Auditor/Engineer:** Senior Software Architect & Backend Security Engineer  
**Status:** API Hardening Completed & Test Suite 100% Passing (658/658 tests passed)

---

## 1. Authorization Changes (Fix A)

- **Dedicated Permission Introduced:** Introduced `"assessments:create"` in [`aegiscore/api/auth.py`](file:///C:/AegisCore/aegiscore/api/auth.py) (`KNOWN_PERMISSIONS` and `DEFAULT_PERMISSIONS`) to separate write operations from read-only permission (`"records:read"`).
- **Route Authorization Boundary:** Updated `POST /assessments` in [`aegiscore/api/routes.py`](file:///C:/AegisCore/aegiscore/api/routes.py) to require `dependencies=[Depends(require_permission("assessments:create"))]`.
- **Read-Only Access Preservation:** GET endpoints (`GET /assessments`, `GET /sessions`, `GET /dashboard/summary`) continue requiring `"records:read"`.
- **Permission Enforcement:** Accounts with only `permissions=frozenset({"records:read"})` attempting to call `POST /assessments` are rejected with `HTTP 403 Forbidden` (`{"detail": "The authenticated account lacks this permission."}`).
- **Schema Update:** Updated `AuthSessionResponse` in [`aegiscore/api/schemas.py`](file:///C:/AegisCore/aegiscore/api/schemas.py) to include `"assessments:create"` in permission literals.

---

## 2. URL-Validation Improvements (Fix B)

- **Target Scope Function Hardened:** Enhanced [`_validate_lab_target_url()`](file:///C:/AegisCore/aegiscore/orchestration.py#L90) in [`aegiscore/orchestration.py`](file:///C:/AegisCore/aegiscore/orchestration.py) to parse ports safely and catch standard library `urlsplit` / `ipaddress` `ValueError` exceptions:
  - Validates `1 <= port <= 65535` explicitly.
  - Safely handles nonnumeric ports (`http://127.0.0.1:abc`), port 0 (`http://127.0.0.1:0`), and port 65536 (`http://127.0.0.1:65536`).
  - Safely handles malformed IPv6 brackets (`http://[invalid-ipv6]:8080`).
  - Catches invalid hostname syntax (`http://invalid_name:8080/`) and empty hostnames (`http://:8080`).
  - Rejects unsupported schemes (`ftp://`, `file://`, `gopher://`), embedded credentials (`http://user:pass@127.0.0.1`), fragments, and out-of-scope public IPs (`http://8.8.8.8`).
- **Error Response:** All validation failures raise `ScopeViolationError` and return clean `HTTP 400 Bad Request` responses without unhandled HTTP 500 exceptions, DNS lookups, or outbound network calls.

---

## 3. Database Migration & Legacy Compatibility (Fix C)

- **Read-Only DDL Prohibition:** Updated `get_assessment()` and `list_assessments()` in [`aegiscore/local_persistence.py`](file:///C:/AegisCore/aegiscore/local_persistence.py) so they do **NOT** attempt DDL (`CREATE TABLE`) operations during read-only opens (`open_existing()`).
- **Legacy Schema v1 Read Compatibility:** When a legacy database (schema v1 with `evaluation_reports` and `offline_sessions` tables, but NO `assessments` table) is opened read-only:
  - `_validate_schema` passes validation (`{"evaluation_reports", "offline_sessions"}.issubset(tables)`).
  - `list_assessments()` returns `([], 0)` without raising DDL errors or corrupting the database file.
  - `get_assessment()` returns `None` without DDL errors.
- **Dynamic Writable Table Initialization:** When opened for writing via `LocalRecordStore.create_or_open()`, `create_assessment()` executes `_ensure_assessments_table(connection)` in a `BEGIN IMMEDIATE` writable transaction, initializing the `assessments` table on-demand.

---

## 4. Persistence Failure Handling (Fix D)

- **Deterministic Failure Test:** Simulated `LocalStoreUnavailableError` during `create_assessment()` in [`tests/test_assessment_creation_api.py`](file:///C:/AegisCore/tests/test_assessment_creation_api.py).
- **HTTP 503 Response:** The API returns `HTTP 503 Service Unavailable` (`{"detail": "Local persistence store is unavailable or inconsistent."}`).
- **Path Sanitization:** Confirmed internal filesystem paths (`/secret/internal/user/path`) are completely redacted and NOT leaked in API error responses or logs.

---

## 5. Files Changed

| File Path | Nature of Modification |
|---|---|
| [`aegiscore/api/auth.py`](file:///C:/AegisCore/aegiscore/api/auth.py) | Added `"assessments:create"` to `KNOWN_PERMISSIONS` and `DEFAULT_PERMISSIONS`. |
| [`aegiscore/api/schemas.py`](file:///C:/AegisCore/aegiscore/api/schemas.py) | Updated `AuthSessionResponse` permission literals. |
| [`aegiscore/api/routes.py`](file:///C:/AegisCore/aegiscore/api/routes.py) | Protected `POST /assessments` with `dependencies=[Depends(require_permission("assessments:create"))]`. |
| [`aegiscore/orchestration.py`](file:///C:/AegisCore/aegiscore/orchestration.py) | Added port bounds checking (`1 <= port <= 65535`) and `ValueError` catching in `_validate_lab_target_url()`. |
| [`aegiscore/local_persistence.py`](file:///C:/AegisCore/aegiscore/local_persistence.py) | Modified `_validate_schema()` to check subset compatibility; made `get_assessment()` and `list_assessments()` read-only without DDL. |
| [`tests/test_api.py`](file:///C:/AegisCore/tests/test_api.py) | Updated capabilities test schema expectations. |
| [`tests/test_assessment_creation_api.py`](file:///C:/AegisCore/tests/test_assessment_creation_api.py) | Added 3 new tests: authorization boundary, edge case URL validation, and legacy schema v1 compatibility (total 12 tests). |

---

## 6. Test Execution Results

### Focused Test Suite
```powershell
uv run pytest tests/test_assessment_creation_api.py tests/test_authentication.py tests/test_local_persistence_api.py -o pythonpath=.
```
**Result:** **40 passed in 14.05s (0 failed)**

### Full Regression Test Suite
```powershell
uv run --frozen --no-sync pytest -o pythonpath=.
```
**Result:** **658 passed in 21.56s (0 failed, 0 skipped)**

---

## 7. OpenAPI Verification

OpenAPI schema (`GET /openapi.json`) verified:
- `POST /assessments` registered with `201 Created` response.
- `GET /assessments` and `GET /assessments/{assessment_id}` registered.
- Authorization and validation requirements documented.

---

## 8. Remaining Limitations

- **Scan Execution:** `POST /assessments` persists the record only; no automated scanning or FSM workflow execution occurs.
- **Target Scope:** Restricted to loopback (`127.0.0.1`, `localhost`, `::1`) and private RFC1918 networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`).

---

## 9. Recommended Next Task

**TASK 06 — Flutter Live Assessment Submission Integration:**  
Connect the Flutter frontend (`frontend/lib/features/assessment_setup/screens/assessment_setup_screen.dart` and `ApiAegisCoreRepository`) to invoke `POST /assessments` in Live Mode when an authorized target URL is submitted.

---

## STOP CONDITION MET

Task 05.1 hardening is complete. **658 out of 658 Python tests pass.** 

*Standing by for your next instruction.*
