# Phase 8G.4 — Read-Only Backend API Expansion

> Historical Phase 8G.4 snapshot. Phase 8G.5 adds opt-in persistence-backed session, finding, dashboard, and report reads. See [PHASE_8G5_LOCAL_PERSISTENCE.md](PHASE_8G5_LOCAL_PERSISTENCE.md) for the current backend record contracts. The approved-evidence behavior below remains applicable.

## Outcome

Phase 8G.4 adds two read-only approved-evidence endpoints backed by the existing persistent source-review registry. The API does not create a registry, bootstrap its SQLite schema, approve sources, edit the source-review manifest, expose local source paths, or use the evaluation harness as a report store.

The checkout has no persistent assessment, finding, or evaluation-report repository. Those APIs remain unsupported. The current source-review manifest still reports `no_sources_approved`, and no persistent source-review database is present in the checkout. The default ASGI application therefore returns HTTP 503 for evidence requests until an existing registry is supplied. A configured valid registry with zero approved sources returns a typed empty collection.

## Endpoints

| Method and path | Response | Data source and behavior |
| --- | --- | --- |
| `GET /evidence/approved?offset=0&limit=50` | `ApprovedEvidenceListResponse` | A deterministic page of chunks selected by `PersistentSourceReviewRegistry.approved_chunks()`, plus total chunk and approved-source counts. `offset` must be nonnegative; `limit` is 1–100. |
| `GET /evidence/approved/{evidence_id}` | `ApprovedEvidenceResponse` | One chunk by its stable chunk ID, returned only if selected as approved. A valid unknown or unapproved ID returns 404; a malformed ID returns 422. |

Each item includes recorded source metadata, source-review revision and event count, approval timestamp, exact chunk text and SHA-256, character offsets, section label when recorded, and the supported `(source_id, chunk_id)` citation pair. The API omits `local_path`, reviewer labels, review rationale, and other nonessential review details. It returns a canonical reference only when it is HTTPS and has no user credentials or query string; URL fragments are stripped. Recorded source version and descriptive metadata are caller-supplied registry values; they are not independently verified facts. Source approval does not establish that an excerpt entails or supports a particular claim.

The endpoint reopens the injected registry with `PersistentSourceReviewRegistry.open_existing()` on every request. The existing selector checks the SQLite event history against the unchanged manifest and current local source bytes. Any missing database, schema problem, integrity mismatch, or selector failure returns a generic HTTP 503 response; local paths and internal database errors are not included in the response. No partial results are returned after an integrity failure.

### App configuration

`create_app()` has no default registry. An application owner can explicitly open an existing database read-only and pass that registry to the factory:

```python
registry = PersistentSourceReviewRegistry.open_existing(
    database_path,
    manifest_path=manifest_path,
    repository_root=repository_root,
)
app = create_app(source_review_registry=registry)
```

This is configuration only; it does not initialize a database or change approval state. The tracked app object is created with no registry, and the current checkout contains no registry file. The read-only evidence response can only return genuine records when the operator supplies a valid existing store.

## Flutter integration

`ApiAegisCoreRepository` parses the strict nested source/chunk schema and fetches pages until the API-reported total is reached. It preserves an empty result, maps an unknown evidence ID to `null`, and keeps non-404 API failures as errors. The Evidence & Provenance screen now displays backend-returned approved chunks, recorded provenance, review revision/event count, source offsets, and both source and excerpt digests. It does not display local filesystem paths, infer related findings, or label source approval as claim validation. The empty state explicitly says missing evidence does not establish that a vulnerability is absent.

Assessment and finding screens remain unsupported in Live Mode. Dashboard metrics and evaluation reports remain unsupported. Assessment submission remains disabled. Demo Mode continues to use labeled synthetic fixtures; Live Mode does not fall back to them.

## Persistence and evaluation boundaries

- `orchestration.py` exposes in-memory state-machine/result contracts but no assessment or finding repository or stable saved record identifiers.
- `EvaluationHarness.execute()` returns in-memory harness reports. No report repository or saved report files are present. The harness is not queried by this API, and no empirical benchmark is run here.
- No evaluation report list/detail routes were added. Synthetic replay output is not presented as empirical evaluation.
- `backend.rag` remains unimplemented as a production semantic retrieval system. The new endpoints expose only approved source chunks selected by the existing offline registry contract.

## Authentication and deployment

The API has no authentication or authorization layer. These read routes are not authenticated. Run the service only in the intended isolated local environment and bind it to loopback (for example, `127.0.0.1`). A loopback launch convention is not an API-enforced access control; do not expose this service to other hosts or a public network. No target execution, scanning, exploitation, external model/provider call, Docker startup, or arbitrary network request was added.

## Verification

Commands executed and observed results:

- `python -m pytest tests/` — 617 passed.
- From `frontend/`, `flutter analyze` — no issues found.
- From `frontend/`, `flutter test` — 36 passed.

The added tests use temporary local manifests and SQLite registries only. They verify typed and stable serialization, paging, valid detail and not-found behavior, malformed inputs, unconfigured and empty stores, approved-only selection, no local-path/reviewer-label disclosure, integrity-failure handling, and unchanged database/manifest bytes during reads.

## Governance state

`docs/source-review-manifest.json` was not modified. No repository source was approved; approval tests used only a temporary synthetic fixture registry. No DEC-01 through DEC-08 decision was marked approved, and no empirical benchmark or live vulnerability assessment was run.
