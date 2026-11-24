# TASK 06.9 — Thesis Evaluation, Experimental Validation & Final Demonstration

**Evaluation date:** 2026-11-24
**Environment:** Windows workspace, repository `.venv`, Python test suite
**Evaluation mode:** Source audit, automated regressions, and controlled local fixtures. No live approval authority, assessment target, or model provider was configured or contacted.

## Evaluation outcome

The implementation supports a narrow, testable prototype: a target-bound passive HTTP `HEAD` workflow, deterministic security-header observations, SQLite persistence and lease recovery, and an opt-in evidence-referenced advisory reviewer. The tests and fixture experiments below support claims about those implemented behaviors under their tested conditions.

The evidence does **not** establish a novel detection algorithm, real-world precision or recall, model quality, improved security accuracy, or production deployment readiness. The authorized live path is not available in this environment because the normal launcher has no trusted authorization verifier configured, and the deployment authentication, persistent storage, and target registry are absent. TASK 06.4.4 Debian 13 egress verification remains deferred. The final demonstration is therefore a reproducible **fixture demonstration**, not a live deployment.

## Research problem and contribution audit

| Area | Implemented and observed in source/tests | Incomplete or not established |
|---|---|---|
| Research problem | Safely produce a small set of explainable observations from a narrowly scoped passive response, retain their evidence, and optionally add bounded commentary without giving that commentary authority. | This is an engineering problem framing, not a claim that the problem or solution is novel. |
| Deterministic detection | `PassiveHeaderDetector` applies fixed rules to normalized response headers and emits `configuration_observation` findings with deterministic IDs and evidence references. The current rules cover missing CSP, MIME sniffing protection, framing protection, Referrer Policy, and HTTPS HSTS. | This is not general vulnerability detection. There is no independent labeled real-world benchmark, so false-positive rate, false-negative rate, precision, recall, and accuracy are unknown. |
| Evidence-grounded advisory | The opt-in reviewer receives bounded allowlisted evidence and deterministic findings, validates a strict response schema and finding/evidence membership, rejects tested unsupported claims, and abstains when evidence is insufficient. It cannot write official findings or alter severity/status. | Live providers are disabled. Reference membership is not semantic entailment; lexical claim checks cannot prove factual grounding. No provider-generated quality or calibration result exists. |
| Execution security | Production execution is routed through a guarded execution adapter. Code and tests cover registered numeric loopback endpoint binding, one `HEAD`, no body read, no redirect following, and connected-peer checks. Target approval is a fail-closed verifier contract. | Tests inject synthetic authorization fixtures. A production authority/verifier is not integrated into the normal launcher, so no live assessment was authorized or attempted. OS-level egress isolation was not verified. |
| Lifecycle and persistence | SQLite persists assessment/evidence/findings. Terminal transitions require current lease ownership and a valid unexpired lease. Recovery is transactional and runs at startup and periodically while the application is running. | This task did not validate a production database volume, backup/restore policy, or Linux process permissions. The current configured runtime has no persistent store path. |
| Product integration | Flutter includes assessment creation/history/details and displays deterministic findings separately from advisory text through the existing API contract. | A live browser-to-API workflow is not demonstrated. The previous TASK 06.8 audit recorded a rejected cross-origin preflight and no configured production browser/API composition. |
| Broader AI/FSM evaluation | A separate offline FSM/specialist/RAG evaluation harness exists in the repository. | Its task and label contract is different from the passive header reviewer. Its results are not used as evidence for this workflow. |

The defensible contribution is an implemented integration of a tightly constrained passive workflow, provenance checks, fail-closed lifecycle controls, and a non-authoritative advisory seam, plus reproducible fixture evaluation. The evaluation does not make a novelty claim about any individual technique.

## Research questions and experiments

### E1 — Deterministic output repeatability

| Item | Specification |
|---|---|
| Research question | Does the deterministic detector emit an identical normalized finding set for identical validated evidence? |
| Hypothesis | Repeated analysis gives the same rule, finding IDs, and evidence links; only `created_at` varies. |
| Fixture / sample | One synthetic HTTPS observation: HTTP 200, empty normalized security headers, fixed valid assessment/evidence IDs; 100 calls. |
| Procedure / baseline | Call `PassiveHeaderDetector.analyze` 100 times. Remove only `created_at`, sort serialized findings, and compare each complete set with the others. The first complete set is the within-run baseline. |
| Metric | Number of distinct normalized complete finding sets; finding count per call; valid finding-to-evidence links; elapsed detector time. |
| Observed result | **1** distinct normalized set across 100 calls; **5** findings per call; **500/500** finding evidence links matched the supplied assessment/evidence IDs. The reproducible script measured total **9.099 ms**, or **0.091 ms/call**, in the recorded run. |
| Limitation | A single synthetic missing-header case establishes repeatability for that input, not detection correctness, coverage, or production latency. Timestamp was deliberately excluded. |

### E2 — Advisory reference, schema, claim, and abstention checks

| Item | Specification |
|---|---|
| Research question | Does the reviewer accept a valid fixture response while rejecting the tested fabricated references, malformed schema, and unsupported claims, and abstain before provider invocation when evidence is insufficient? |
| Hypothesis | The strict local validator rejects each represented invalid case and preserves the boundary that commentary is advisory. |
| Fixture / sample | Fixed synthetic evidence/findings and `_ScriptedAdapter` responses in `tests/test_assessment_ai_integration.py`; no external model. The reproducible metrics test contains one valid acceptance, three invalid-reference variants, two unsupported/unqualified claims, one insufficient-evidence abstention, one valid schema, and two invalid schema variants. |
| Procedure / baseline | Run `test_reliability_fixture_metrics_are_reproducible`; compare result status/reference membership with the fixture's expected result. Deterministic finding records are the authority baseline. |
| Metrics and observed result | Valid reference acceptance **1/1**; invalid-reference rejection **3/3** (unknown finding, unknown evidence, cross-finding evidence); unsupported/unqualified claim rejection **2/2**; insufficient-evidence abstention without adapter invocation **1/1**; valid schema acceptance **1/1**; invalid schema rejection **2/2**. Separate API failure-isolation fixtures cover **4/4** failure types and repeated failures **5/5**, preserving deterministic findings and completed status. |
| Limitation | These are engineered unit/API fixtures with small, selected sample sizes. They are not model accuracy, calibrated reliability, semantic entailment, or a statistically representative rejection rate. |

### E3 — Local advisory processing overhead

| Item | Specification |
|---|---|
| Research question | What is the measured local processing cost of adding the reviewer validator when the adapter returns a deterministic in-memory fixture? |
| Hypothesis | The advisory path costs more local time than detector-only execution because it builds/validates the bounded request and output. |
| Fixture / sample | Same fixed synthetic HTTPS observation, five detector findings, and the actual `PassiveAssessmentAIReviewer` with the test suite's `_ScriptedAdapter(_valid_response)`. No network or provider call. |
| Procedure / baseline | 20 warmups for each path, then 250 paired measurements in this order: detector only; detector plus reviewer and successful local schema/reference validation. `perf_counter` surrounds each path. P95 is the empirical sorted sample at index `floor(0.95 * (n-1))`. |
| Metric | Median, mean, and empirical P95 per path; difference between path medians. |
| Observed result | Detector-only: median **0.0233 ms**, mean **0.0236 ms**, P95 **0.0267 ms**. Detector plus local fake reviewer: median **0.5087 ms**, mean **0.5100 ms**, P95 **0.5256 ms**. Median local increment: **0.4854 ms** in this run. |
| Limitation | This compares local Python validation with a fake adapter, not an AI model, provider transport, timeout, or end-to-end API latency. It is one run on this Windows workspace and is not a deployment SLO. Do not interpret the increment as the cost of live AI. |

### E4 — Authorization, execution, and lifecycle integrity

| Item | Specification |
|---|---|
| Research question | Do tested authorization, target-scope, lease, transaction, and recovery failure paths deny or preserve state as required? |
| Dataset / procedure | Assertion-based tests in the authorization, execution, lifecycle, persistence, and passive-pipeline suites. These use synthetic verifier outcomes, mocked transports, and temporary SQLite databases. The test outcomes are binary invariants, not an accuracy benchmark. |
| Observed results | Test cases exercise invalid signature, unknown issuer, expired, revoked, not-yet-valid, unavailable, invalid timestamps, and stale revocation evidence; API tests assert no transport call on tested expired/revoked/unavailable dispatch failures. Execution tests cover numeric loopback versus hostname/non-loopback and unauthorized endpoint cases, connected-peer mismatch, redirect rejection, one `HEAD`, and no response-body read. Lifecycle tests cover missing/wrong/expired/unverifiable leases, recovery skipping unverifiable leases, active lease renewal/recovery concurrency, process restart, in-process recovery after persistence is restored, preservation of prior evidence/findings/results, and rollback across the genuine two-assessment trigger failure test. |
| Baseline / metric | The required invariant is the expected deny, rollback, or unchanged persisted state for each test case. The focused and full-suite pass counts are reported below; they are not converted into security percentages. |
| Limitation | Passing tests establish behavior for the represented local cases only. They do not prove absence of all bypasses, deployment firewall behavior, authority correctness, or production database durability. |

## False-positive / false-negative and baseline comparison

No independently adjudicated response dataset is present for this narrow detector. Therefore **false positives, false negatives, precision, recall, and detection accuracy were not measured**. The header fixtures establish rule behavior and repeatability only.

The deterministic-only versus advisory comparison in E3 measures local processing time using a fake response adapter. It does not compare security outcomes or diagnostic accuracy. The advisory layer may add interpretation, but there is no measured evidence that it improves detection accuracy. No live-provider result exists for comparison.

## Security and lifecycle evidence

- **Passive request scope:** execution constructs a single HTTP `HEAD`, disables redirects, applies a bounded timeout, captures only allowlisted security headers, and does not call a response-body read. The applicable execution and passive-pipeline tests verify these restrictions using controlled local fixtures.
- **Target authorization:** numeric loopback policy and exact registered endpoint binding are tested independently from authority provenance. A loopback address alone does not authorize an assessment. The injected verifier contract tests fail closed for absent/untrusted authorization and stale/invalid evidence. The normal launcher still lacks a configured production verifier, so test verifier success is not live authority evidence.
- **Advisory isolation:** AI remains opt-in. Unknown references, cross-finding evidence, unexpected fields, missing fields, oversized/malformed output, tested unsupported claims, timeout, and adapter failure are rejected or marked unavailable. API tests assert deterministic findings and terminal status survive reviewer failures. Commentary is stored/displayed separately from official findings.
- **Persistence integrity:** SQLite pipeline writes are atomic. `test_two_stale_assessments_rollback_on_trigger_failure` forces the second recovery update to fail and verifies both stale assessments remain running after rollback. The separate `test_genuine_sqlite_transaction_rollback` forces a findings insert failure and verifies evidence, findings, status, and execution result are not partially committed.
- **Recovery:** tests verify restart recovery of expired leases and in-process recovery after a persistence error when the trigger is removed. The latter recovers the expired running assessment to `failed` with recovery metadata and without synthesizing execution results, evidence, or findings.
- **Lease ownership:** terminal persistence and renewal reject missing, mismatched, expired, malformed, timezone-naive, or timezone-invalid lease expiry states. Tests cover valid future lease acceptance and a concurrent recovery/renewal outcome in which the active future lease remains running and owned.
- **Sensitive data:** tests assert raw provider error text, redirect destinations, and unallowlisted headers are not exposed through result responses/logs. This is test evidence for listed paths, not a full privacy audit of every deployment log sink.

## Test results

The commands below were run against the unchanged backend/test source for this evaluation. The six-test demonstration selection is a subset of the focused/full suites.

| Run | Collected | Passed | Failed | Skipped | Pytest duration |
|---|---:|---:|---:|---:|---:|---:|
| Focused configuration, API, authorization, lifecycle, creation/execution, reviewer, and Linux deployment tests | 175 | 175 | 0 | 0 | 21.53 s |
| Full Python regression suite (final worktree run) | 863 | 863 | 0 | 0 | 47.26 s |
| Fixture demonstration selection | 6 | 6 | 0 | 0 | 3.56 s |

Reproduction commands from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.task_06_9_fixture_experiments
.\.venv\Scripts\python.exe -m pytest -q tests/test_assessment_ai_integration.py::test_reliability_fixture_metrics_are_reproducible

.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_runtime_configuration.py tests/test_api.py `
  tests/test_authorization_verification.py `
  tests/test_assessment_lifecycle_recovery.py `
  tests/test_assessment_creation_api.py `
  tests/test_assessment_execution_api.py `
  tests/test_assessment_ai_integration.py `
  tests/test_linux_egress_deployment.py

.\.venv\Scripts\python.exe -m pytest -q
```

## Reproducible fixture demonstration

This sequence exercises the supported workflow pieces without presenting them as a live production deployment. The test fixtures inject local authentication, a synthetic verifier, and a controlled or mocked loopback transport; they do not require public targets or a real approval record.

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_assessment_creation_api.py::test_valid_loopback_target_creates_assessment `
  tests/test_passive_pipeline.py::test_exactly_one_head_request_occurs `
  tests/test_assessment_ai_integration.py::test_api_provider_failure_keeps_assessment_and_deterministic_findings `
  tests/test_passive_pipeline.py::test_persistence_failure_recovers_without_application_restart `
  tests/test_assessment_lifecycle_recovery.py::test_process_restart_recovers_expired_assessment_lease `
  tests/test_authorization_verification.py::test_missing_verifier_fails_closed
```

The sequence covers assessment creation, one bounded `HEAD`, deterministic result preservation when advisory review fails, persistence recovery while the app is running, expired-lease recovery after constructing a fresh app, and fail-closed behavior when no verifier exists. Expected result in this evaluation: **6 passed**. The production-style demonstration step “execute against a genuinely authorized target” is intentionally not performed because no real authority-backed approval is configured.

## Deployment and research limitations

| Requirement | Status in this evaluation |
|---|---|
| Live authentication provisioning | **Not configured.** Tests inject test credentials; no live operator account was used. |
| Persistent deployment storage | **Not configured.** Tests use temporary SQLite files; no production volume, backup, or restore was exercised. |
| Authoritative target verifier | **Not implemented/configured in the normal launcher.** The protocol and fail-closed validation exist; test verifiers are synthetic. No approval was invented or used. |
| Browser-to-API runtime | **Not verified live.** TASK 06.8 records the separate-origin preflight as rejected and no complete browser workflow. |
| Gemini / live model provider | **Disabled / not integrated.** All reviewer outputs in this evaluation use a deterministic fake adapter. |
| Synchronous adapter interruption | **Limited.** The reviewer rejects a result returned after its elapsed-time limit, but cannot forcibly interrupt an adapter that blocks indefinitely. A future adapter must enforce its own transport deadline/cancellation. |
| Debian 13 OS-level egress | **Deferred / not verified.** Current evaluation host is Windows. Application-level loopback and guarded execution tests do not establish host/container firewall isolation. TASK 06.4.4 remains deferred. |
| Linux permissions / firewall | **Not verified.** No Linux environment or actual firewall evidence was available for this task. |
| Real-world benchmark and human adjudication | **Absent.** No supported false-positive/false-negative or generalization claim can be made. |
| Statistical confidence / model calibration | **Not measured.** Fixture counts are small and selected; reviewer metadata explicitly does not claim calibrated confidence or evaluated factual support. |

### Recommended next thesis milestone

After an actual trusted issuer/verifier, operator authentication, durable storage, and intended browser/API composition are configured, perform a witnessed local deployment acceptance on the proposed Debian 13 baseline. Capture the actual firewall and process permissions, demonstrate an authority-approved loopback target, restart and recover the service, and exercise advisory disabled/success/failure cases with provider egress still disabled. Separately create a human-reviewed, versioned header-response dataset before estimating false-positive/false-negative behavior. Keep model-quality claims out until real provider-generated and independently adjudicated evaluation data exists.

## Repository safety and worktree record

Initial `git status --short` was captured before this report and experiment script were created: **114 entries** — 35 deleted, 26 modified, and 53 untracked. The pre-existing modified set included `uv.lock`, backend/API, Flutter, tests, and documentation; the untracked set included prior task reports, deployment assets, and source/test files. These existing changes were preserved. This task added only the in-scope evaluation report and offline fixture experiment script; it did not edit product source, tests, Flutter files, or `uv.lock`.

Final `git status --short` contains the same pre-existing entries plus `?? docs/TASK_06_9_THESIS_EVALUATION.md` and `?? scripts/task_06_9_fixture_experiments.py`: **116 entries** — 35 deleted, 26 modified, and 55 untracked. No destructive Git command, staging, or commit was used. No byte-for-byte preservation claim is made.
