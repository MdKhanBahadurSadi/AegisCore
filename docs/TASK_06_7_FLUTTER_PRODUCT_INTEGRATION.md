# TASK 06.7 — Flutter Product Integration & Advisory UX

## Pre-implementation architecture and contract audit

### Existing Flutter architecture

- Flutter Web app in `frontend/`, using Material 3, GoRouter, Riverpod, and an injectable `http.Client`.
- `AuthenticatedShell` gates live mode behind the existing authentication provider. `ApiAegisCoreRepository` adds the current bearer token and reports expired sessions through that provider.
- The assessment setup screen was an offline demo form. Its specialist, grounding, reviewer, and model-budget controls did not correspond to fields in the live assessment create API.
- Existing findings, evidence, and reports screens consume separate offline fixture or persisted offline-evaluation APIs. They are not the passive assessment findings contract and should remain separate.

### Backend contract map

| Workflow step | Existing API contract | Authentication / behavior |
| --- | --- | --- |
| Create assessment | `POST /assessments`, JSON `{ "target_url": "..." }` | `assessments:create`; server validates registered authorization and persists a target binding |
| List persisted assessments | `GET /assessments?offset=…&limit=…` | `records:read` |
| Retrieve assessment | `GET /assessments/{assessment_id}` | `records:read` |
| Execute | `POST /assessments/{assessment_id}/execute`, no request body | `assessments:execute`; server rechecks authorization, lease ownership, and guarded execution policy |
| Retrieve deterministic findings | `GET /assessments/{assessment_id}/findings` | `records:read` |
| Retrieve evidence | `GET /assessments/{assessment_id}/evidence` | `records:read` |
| Advisory result | Optional `execution_result.ai_review` in assessment response | No client-side opt-in endpoint or request field exists; reviewer remains disabled by default in backend configuration |

### Contract gaps documented before UI implementation

1. The backend has no API field or endpoint to enable advisory review per assessment. Flutter must not offer an opt-in switch or send invented fields. It can display only an advisory result already returned by the backend.
2. `POST /assessments` accepts only a target URL. It does not accept a client authorization reference, specialist list, grounding option, reviewer option, or model settings. Server-side target registration and authorization remain authoritative.
3. The pre-existing live Flutter repository implemented read APIs but reported assessment submission as unsupported. The supported assessment routes need typed repository methods.
4. The existing global findings and evidence views belong to other stored evaluation contracts. Passive assessment findings and evidence must be loaded by assessment ID rather than merged into those views.

## Implemented workflow

- The existing assessment setup page now selects one of the existing local test endpoints, requires a user confirmation, and sends only the supported `target_url` request field. The confirmation is explicitly described as an acknowledgment, not authorization.
- Live mode loads the first 50 persisted assessments, supports refresh, and links each record to its detail screen. Demo mode remains synthetic and is labeled as such.
- The detail screen shows the backend status and persisted outcome. Created or pending records expose an explicit execute action. Running records offer refresh; terminal state and severity are read from the backend response and are not editable in the client.
- Deterministic findings and evidence are loaded from their assessment-specific APIs. Empty, loading, error, missing-reference, and not-found states are handled separately.
- Advisory commentary has a visually distinct non-authoritative panel. The client does not provide an opt-in control because there is no per-assessment API contract. Returned review output is capped and shape checked; finding and evidence references must match loaded records. A rejected advisory result does not suppress findings.
- Advisory content is displayed with Flutter `Text`; no HTML or Markdown renderer is used. Existing authentication and loopback-only backend URL validation remain in place.

## Security boundary verification

- Live authentication still gates the application shell. Repository requests retain the bearer token and expire the session on HTTP 401; HTTP 403 remains an authorization failure.
- Creation sends `POST /assessments` with exactly `target_url`. Execution sends a bodyless `POST /assessments/{id}/execute`. The browser does not call a model provider or underlying HTTP engine.
- The client only presents the pre-existing HTTP loopback lab choices on ports 3000 and 8080. This is a user-interface restriction; the backend remains responsible for registered target authorization, endpoint binding, execution boundary, peer checks, and lease lifecycle.
- Advisory parse limits are 16 KiB for the nested review and 600 characters per review text field. HTTP API responses above 2 MiB are rejected. Finding and evidence references are checked against the actual assessment result before advisory text is shown.
- Official findings retain the backend severity, title, description, and references. Advisory text cannot alter those fields or the terminal state.

## Files changed

Modified:

- `frontend/lib/core/constants/route_constants.dart`
- `frontend/lib/core/navigation/app_router.dart`
- `frontend/lib/features/assessment_setup/models/assessment_setup_model.dart`
- `frontend/lib/features/assessment_setup/screens/assessment_setup_screen.dart`
- `frontend/lib/services/aegiscore_repository.dart`
- `frontend/lib/services/api_aegiscore_repository.dart`
- `frontend/lib/services/backend_errors.dart`
- `frontend/lib/services/providers.dart`
- `frontend/test/api_repository_test.dart`
- `frontend/test/assessment_and_reports_test.dart`
- `frontend/test/live_mode_integration_test.dart`
- `frontend/test/state_management_test.dart`

Added:

- `frontend/lib/features/assessment_setup/screens/assessment_details_screen.dart`
- `frontend/lib/services/backend_assessment_models.dart`
- `frontend/test/assessment_details_test.dart`
- `docs/TASK_06_7_FLUTTER_PRODUCT_INTEGRATION.md`

No backend code, `uv.lock`, or Flutter dependency lockfile was changed for this task.

## Verification results

| Verification | Collected | Passed | Failed | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: | --- |
| Focused assessment/API/widget tests | 49 | 49 | 0 | 0 | 17.5 s command wall time; Flutter runner reported 14 s |
| Full Flutter test suite | 60 | 59 | 0 | 1 | 27.6 s command wall time; Flutter runner reported 13 s |
| `flutter analyze --no-pub` | — | clean | 0 issues | — | Flutter reported 5.2 s; command wall time 11.7 s |
| `git diff --check` | — | clean | 0 | — | 1.2 s |

The full test suite includes existing authentication, navigation, findings, evidence, reports, and state-management tests. The single skipped test is reported by Flutter's test runner as skipped; no new test was skipped.

Two focused runs failed before the final passing runs and were corrected:

1. The first run collected 47 tests: 44 passed, 3 failed, 0 skipped (23.7 s command elapsed). One new invalid-reference fixture accidentally used the valid finding ID, and two existing UI assertions expected the old generic HTTP 503 message after the client began showing a safe, actionable unavailable-service message.
2. The next run collected 48 tests: 47 passed, 1 failed, 0 skipped (20.4 s command elapsed). The new execution-state widget test's fake server returned 404 for its execute request instead of a completed assessment response.

The fixtures and assertions were corrected. The final focused run and full suite both passed. Flutter commands initially waited on the SDK cache lock outside the workspace; analyzer and tests completed after using the SDK's required cache access. No Flutter dependency update was run.

## Intentional test coverage change

The old assessment setup state test for toggling specialist roles was removed with those controls. The backend create contract accepts no specialist list, reviewer flag, grounding option, or model budget; retaining client controls would have presented unsupported behavior. The remaining setup tests cover target scope, confirmation reset, demo behavior, live create request shape, persisted retrieval, execution transition, and advisory separation. Existing unrelated Flutter tests remained in the full passing suite.

## Known limitations

- The backend must have a valid authorized target registration and verifier configuration. Flutter cannot create or renew approval records. An unauthorized or unavailable authorization source is rejected by the backend.
- Advisory review has no per-assessment opt-in contract. It remains disabled unless the backend is explicitly configured to enable it; no live provider integration is added here.
- Assessment history currently loads only the first 50 records. Pagination controls are not present.
- A running assessment is refreshed manually; the screen does not poll. Backend execution and lease recovery behavior were not modified by this frontend task.
- TASK 06.4.4 Linux egress verification remains deferred. This task does not claim environment-level isolation.

## Git status capture

Initial status before this task: **89 entries** (35 deleted, 12 modified, 42 untracked). These were pre-existing worktree changes, including backend/API work, previous task reports, generated/untracked content, and a pre-existing `uv.lock` modification. The full initial `git status --short` output is included in Appendix A.

Final status: **105 entries** (35 deleted, 24 modified, 46 untracked). The 89 initial entries remained present with the same status. The final status consists of that initial snapshot plus these 16 task entries:

```text
 M frontend/lib/core/constants/route_constants.dart
 M frontend/lib/core/navigation/app_router.dart
 M frontend/lib/features/assessment_setup/models/assessment_setup_model.dart
 M frontend/lib/features/assessment_setup/screens/assessment_setup_screen.dart
 M frontend/lib/services/aegiscore_repository.dart
 M frontend/lib/services/api_aegiscore_repository.dart
 M frontend/lib/services/backend_errors.dart
 M frontend/lib/services/providers.dart
 M frontend/test/api_repository_test.dart
 M frontend/test/assessment_and_reports_test.dart
 M frontend/test/live_mode_integration_test.dart
 M frontend/test/state_management_test.dart
?? docs/TASK_06_7_FLUTTER_PRODUCT_INTEGRATION.md
?? frontend/lib/features/assessment_setup/screens/assessment_details_screen.dart
?? frontend/lib/services/backend_assessment_models.dart
?? frontend/test/assessment_details_test.dart
```

No staging or commit was performed. `git diff --check` exited successfully; Git printed only non-fatal LF-to-CRLF working-copy warnings. `uv.lock` remains in its pre-existing modified state.

### Appendix A — Initial `git status --short`

```text
 D .idea/.gitignore
 D .idea/AegisCore.iml
 D .idea/misc.xml
 D .idea/modules.xml
 M aegiscore/api/app.py
 M aegiscore/api/auth.py
 M aegiscore/api/routes.py
 M aegiscore/api/schemas.py
 M aegiscore/local_persistence.py
 M aegiscore/orchestration.py
 D docs/ADRs/0001-technology-decisions.md
 D docs/ADRs/0002-safety-policy-and-provider-egress.md
 D docs/ARCHITECTURE.md
 D docs/KNOWLEDGE_CORPUS.md
 M docs/NORMALIZATION_FIDELITY_AUDIT.md
 D docs/PHASE_8C2_DESIGN.md
 D docs/PHASE_8C_PLAN.md
 D docs/PHASE_8D1_MULTI_AGENT_DESIGN.md
 D docs/PHASE_8E1_EVALUATION_PROTOCOL.md
 D docs/PHASE_8E2A1_STATISTICAL_REVIEW.md
 D docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md
 D docs/PHASE_8E2A_PROTOCOL_AUDIT.md
 D docs/PHASE_8E2B_OFFLINE_HARNESS.md
 D docs/PHASE_8E3_EVALUATION_CONTRACTS.md
 D docs/PHASE_8E4_OFFLINE_EVALUATION_HARNESS.md
 D docs/PHASE_8E5_CASE_CATALOG_AND_GROUND_TRUTH.md
 D docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md
 D docs/PHASE_8E6_CATALOG_PROVENANCE_AUDIT.md
 D docs/PHASE_8E7_1_PACKAGE_CONSISTENCY_AUDIT.md
 D docs/PHASE_8G3_API_INTEGRATION.md
 D docs/PHASE_8G4_READ_ONLY_API_EXPANSION.md
 D docs/PHASE_8G5_LOCAL_PERSISTENCE.md
 D docs/PHASE_8G6_END_TO_END_HARDENING.md
 D docs/PHASE_8G7_AUTHENTICATION_AND_DEPLOYMENT_SECURITY.md
 D docs/REQUIREMENTS.md
 M docs/SOURCE_REVIEW_PACKET.md
 D docs/SUPERVISOR_DECISION_REGISTER.md
 D docs/SUPERVISOR_REVIEW_PACKAGE.md
 D docs/TEST_PLAN.md
 D docs/THREAT_MODEL.md
 D docs/ground_truth_review_template.jsonl
 D docs/independence_audit_template.jsonl
 D docs/partition_assignment_template.jsonl
 M docs/source-review-manifest.json
 M tests/auth_helpers.py
 M tests/test_api.py
 M uv.lock
?? AEGISCORE_AI_MASTER_STUDY_BOOK.pdf
?? "aegiscore - Copy/"
?? aegiscore/assessment_ai.py
?? aegiscore/authorization_verification.py
?? aegiscore/execution.py
?? aegiscore/passive_detector.py
?? aegiscore/production_execution.py
?? aegiscore/target_authorization.py
?? deploy/
?? docs/FINAL_PROJECT_AUDIT.md
?? docs/TASK_02_RECOVERY_ANALYSIS.md
?? docs/TASK_03_MINIMAL_RECOVERY_SET.md
?? docs/TASK_04_1_GIT_STATE_DIAGNOSTIC.md
?? docs/TASK_04_2_GIT_STAT_CACHE_VERIFICATION.md
?? docs/TASK_04_3_POST_AUDIT_INDEX_STATE_CHECK.md
?? docs/TASK_04_SELECTIVE_RECOVERY_REPORT.md
?? docs/TASK_05_1_ASSESSMENT_API_HARDENING_REPORT.md
?? docs/TASK_05_2_1_EVIDENCE_AUDIT_REPORT.md
?? docs/TASK_05_2_2_OPENAPI_PERMISSION_CLOSURE_REPORT.md
?? docs/TASK_05_2_3_FINAL_EVIDENCE_CLOSURE_REPORT.md
?? docs/TASK_05_2_FINAL_VERIFICATION_REPORT.md
?? docs/TASK_05_ASSESSMENT_CREATION_API_REPORT.md
?? docs/TASK_06_1_EXECUTION_ENGINE_MVP_REPORT.md
?? docs/TASK_06_2_1_PIPELINE_HARDENING_REPORT.md
?? docs/TASK_06_2_PASSIVE_ASSESSMENT_PIPELINE_REPORT.md
?? docs/TASK_06_3_LIFECYCLE_RECOVERY_REPORT.md
?? docs/TASK_06_4_1_SECURITY_ACCEPTANCE_REPORT.md
?? docs/TASK_06_4_2_AUTHORIZATION_AND_DEPLOYMENT_SECURITY.md
?? docs/TASK_06_4_3_LINUX_EGRESS_ISOLATION_REPORT.md
?? docs/TASK_06_4_4_LIVE_LINUX_ISOLATION_REPORT.md
?? docs/TASK_06_4_MVP_ACCEPTANCE_AUDIT.md
?? docs/TASK_06_5_AI_ENGINE_INTEGRATION_AUDIT.md
?? docs/TASK_06_6_ADVISORY_REVIEWER_EVALUATION.md
?? scripts/build_full_study_book.py
?? scripts/pdf_builder/
?? tests/test_assessment_ai_integration.py
?? tests/test_assessment_creation_api.py
?? tests/test_assessment_execution_api.py
?? tests/test_assessment_lifecycle_recovery.py
?? tests/test_authorization_verification.py
?? tests/test_linux_egress_deployment.py
?? tests/test_passive_pipeline.py
```
