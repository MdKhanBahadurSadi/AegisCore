# Phase 8G.5 — Local Persistence & Functional Backend Workflows

## Implemented workflow

EvaluationHarness remains offline-only. When constructed with record_store=LocalRecordStore.create_or_open(path), its execute() and execute_from_jsonl() methods persist the completed HarnessExecutionReport they actually produce. The optional store does not execute a workflow. It rejects non-harness objects and reports not marked as completed synthetic simulations.

Persistence uses a local SQLite file with schema version 1. A report and its raw per-case runs are committed in one transaction. Stable report IDs are derived from the report output with only wall-clock envelope fields excluded. Stable session IDs bind a report ID to the runner's run ID. Repeating an identical deterministic replay is idempotent; stored records are immutable. An error rolls back the report and all associated sessions.

Stored session records retain the report/run/case IDs, fixture dataset and version, runner, repeat index, start/end times, status, decision, full result, evidence reference IDs, and case locus/classification when supplied by the report. Reports retain the harness's full serialized output, calculated metrics, abstentions, incomplete/failure counts, and any error diagnostics actually produced. All records are marked is_synthetic=true, is_empirical=false, and execution_mode=offline_fixture. Abstentions remain findings-free when the workflow produces no findings.

The database is a separate store from the source-review registry. It should live outside the repository unless the operator explicitly intends to track it. Do not put credentials or unrelated files in this database.

## Configuration and local run

Set AEGISCORE_LOCAL_STORE_PATH to a local SQLite file path before starting the API. When set, create_app() initializes or validates this store and emits a generic startup diagnostic. API reads reopen the configured file in SQLite read-only mode. A missing/unconfigured store returns HTTP 503 from record routes; a configured empty store returns typed empty pages and zero dashboard counts. /storage/status distinguishes these cases without exposing a filesystem path.

An offline workflow writer can use the same path explicitly:

~~~python
import os
from aegiscore.evaluation_harness import EvaluationHarness
from aegiscore.local_persistence import LocalRecordStore

store = LocalRecordStore.create_or_open(os.environ["AEGISCORE_LOCAL_STORE_PATH"])
harness = EvaluationHarness(record_store=store)
# Execute only a permitted synthetic offline fixture workflow.
# This phase does not authorize an empirical benchmark or live assessment.
~~~

Evidence registry configuration is read from AEGISCORE_SOURCE_REVIEW_DB, AEGISCORE_SOURCE_REVIEW_MANIFEST, and AEGISCORE_REPOSITORY_ROOT. All three must point to an existing valid registry, manifest, and project root. The API opens the review registry without bootstrapping it and uses the existing approved-only selector. Missing or invalid configuration remains unavailable; no demo or candidate source is promoted. The source-review manifest is unchanged and currently has no approved source.

Start the unauthenticated API bound to loopback only:

~~~powershell
python -m uvicorn aegiscore.api:app --host 127.0.0.1 --port 8000
~~~

Loopback binding is a deployment instruction, not application-enforced authentication or authorization. Do not expose this service to other machines or a public network.

## Read-only API

All new record routes are read-only and use the configured database in read-only mode:

| Endpoint | Data returned |
| --- | --- |
| GET /storage/status | Configured/readable state and the record types supported by this store. |
| GET /dashboard/summary | Counts derived from persisted sessions/reports; empirical count is zero for this workflow. |
| GET /sessions?offset=0&limit=50 | Paginated offline replay sessions with status, timestamps, result, case ID and fixture provenance. |
| GET /sessions/{session_id} | One saved session, without rerunning the workflow. |
| GET /sessions/{session_id}/findings | Findings actually present in that session result; abstentions can return an empty page. |
| GET /findings?offset=0&limit=50 | Paginated findings derived from stored session results. |
| GET /findings/{finding_id} | One finding by a stable ID derived from the saved session and finding IDs. |
| GET /reports?offset=0&limit=50 | Persisted evaluation report metadata, typed calculated metrics and provenance. |
| GET /reports/{report_id} | Report metadata plus the full previously stored harness payload. |
| GET /evidence/approved and GET /evidence/approved/{evidence_id} | Phase 8G.4 approved-only evidence contracts; require an existing valid registry. |

List routes have bounded offset/limit pagination (limit 1–100), return empty pages for configured empty stores, and return 404 for a valid unknown detail ID. An unavailable or malformed store returns HTTP 503 with a generic error and no local path. /health still indicates only that the API process answered. /capabilities lists implemented contracts but does not imply a store is configured.

## Flutter

Live Mode now consumes:

- Dashboard summary and recent replay-session metadata/status/time.
- Persisted findings and finding detail with recorded evidence-reference IDs and replay provenance.
- Evaluation report lists and on-demand full report details, including calculated metrics, incomplete/failed counts, and recorded diagnostics.
- Storage availability from /storage/status.
- Existing approved evidence list/detail endpoints.

The UI shows an explicit synthetic offline fixture label, does not invent confidence values or decomposed claims when none were stored, and warns that replay evidence IDs do not prove current source approval. Empty records, storage errors, and malformed responses remain distinct; Live Mode never falls back to demo data. Assessment submission remains disabled.

## Boundaries and remaining blockers

- This work stores offline fixture replay outputs only. It does not provide live assessment execution, target scanning, exploitation, external LLM inference, or empirical findings.
- No approved repository evidence exists; evidence remains unavailable until an authorized review creates valid approval records. This phase does not alter docs/source-review-manifest.json.
- The API has no authentication or authorization. Keep the API loopback-only in the isolated local environment.
- Confidence remains uncalibrated (confidence_is_calibrated=false).
- Supervisor decisions DEC-01 through DEC-08 remain pending. No empirical benchmark was run.
- SQLite files are local research data. Back them up and protect them through operating-system permissions; they are not encrypted or authenticated by this application.

## Verification

Phase 8G.5 uses temporary SQLite files and synthetic fixture replays in tests. The final verification results are recorded in PROJECT_STATUS.md; no real source-review database or research record was written.
