# AEGISCORE AI Project Status

**Updated:** 2026-10-28
**Current phase:** Phase 8G.5 local persistence and read-only workflow APIs completed. The offline evaluation harness can persist its completed synthetic fixture report and per-case replay outputs to an opt-in SQLite store. FastAPI exposes stored session, finding, report, dashboard-summary, and storage-status reads; Flutter Live Mode consumes those records without demo fallback. The evidence registry remains unconfigured by default and has no approved repository source. Authentication is absent; service use remains loopback-only.
**Phase 1:** Proposal/repository requirements inspection and traceability documented.  
**Phase 2:** Architecture, threat model, verification plan, and technology ADR documented; this was not proposal Month 2.  
**Phase 3:** Deterministic in-memory safety policy contracts implemented and unit-tested.  
**Phase 4B:** Exact-operation permit and injected fake-transport boundary implemented and tested. Phase 4B did not authorize lab setup, scanning, test-case creation, or ground-truth preparation.
**Phase 5A:** Read-only environment and lab-readiness audit completed. The audit did not change code or environment configuration; a factual stale statement in ADR 0002 was corrected.
**Phase 6A:** Project-local Python dependency configuration and minimal in-process-testable FastAPI foundation completed. Existing safety policy and guarded-execution source/tests were not changed.
**Phase 7A:** Offline-only source/chunk contracts, local text/Markdown ingestion, deterministic chunking, retrieval interface, lexical in-memory test double, citation-reference validation, and tests completed. No external service, dependency, approved corpus, semantic retrieval, or production RAG workflow was added.
**Phase 7B:** In-memory source-review lifecycle, current-approved-chunk selector, stale-on-reingestion behavior, citation/reference distinction, empty manifest at that phase, and offline tests completed. Reviewer references are not authenticated and the manifest is not runtime-persisted.
**Phase 7C:** 11 official OWASP/MITRE source artifacts acquired, raw bytes preserved and hash-matched to official HTTPS responses, deterministic normalized copies generated offline, candidate manifest expanded, and provenance/governance tests completed. At the end of Phase 7C, no source had review events or approval and the manifest was not runtime-connected; Phase 7E adds an optional caller-configured persistent selector, without creating a real-corpus registry or decision.
**Phase 7E:** SQLite persistence and fail-closed manifest mirror implemented and verified against temporary test fixtures.
**Phase 8B:** Approved-only evidence retrieval runtime implemented and verified.
**Phase 8C.1:** Provider-neutral evidence-grounded generation contracts and deterministic offline fake implemented and verified.
**Phase 8C.2:** Evidence sufficiency, claim-level validation, and conflict handling design specification completed.
**Phase 8C.3:** Deterministic evidence and claim validation layer implemented and verified.
**Phase 8D.1:** Multi-agent specialist role synthesis, evidence integration, uncertainty assessment, and fail-closed response gating architecture design completed.
**Phase 8D.2:** Typed multi-agent data contracts and deterministic orchestration state machine implemented and verified.
**Phase 8D.3:** Provider-neutral specialist role contracts and deterministic multi-agent workflow tests implemented and verified.
**Phase 8D.4:** Citation excerpt integrity verification and source manifest integrity failure integration completed.
**Phase 8E.1:** Thesis evaluation protocol and benchmark design completed (design-only; no experiments executed).
**Phase 8E.2A:** Evaluation protocol consistency audit completed (documentation-only; protocol refined; supervisor decision gates prepared).
**Phase 8E.2A.1:** Statistical claims and evaluation feasibility review completed (documentation-only; audit doc created; 4 protocol corrections applied).
**Phase 8E.2A.2:** Statistical review corrections and evidence traceability completed (documentation-only; audit doc created; 3 protocol corrections applied).
**Phase 8E.2B:** Offline testbed harness engineering completed (static Compose configuration, isolation contracts, validation scripts, 19 tests added).
**Phase 8E.3:** Evaluation contracts and offline scoring framework completed (typed schemas, strict JSONL validators, offline scoring pipeline, runner interfaces, 26 tests added).
**Phase 8E.4:** Offline runner wrappers and fixture-based evaluation harness completed (runner registry, condition taxonomy, harness orchestrator, run manifests, trial agreement analysis, 21 tests added).
**Phase 8E.5:** Canonical case catalog and ground-truth preparation completed (offline metadata, review workflow, partition governance, extended configuration fingerprinting, 34 tests added).
**Phase 8E.6:** Case catalog provenance audit and supervisor review package completed (provenance audit, negative-control validity review, orthogonal status taxonomy, 4 tests added).
**Phase 8E.6.1:** Version-pinned evidence traceability and negative-control reclassification completed (version audit, negative-control critique, 7-category accounting, 3 tests added).
**Phase 8E.7:** Consolidated supervisor review package and formal decision register completed (documentation consolidation, 8 formal pending decision gates, approval boundary enforced).
**Phase 8E.7.1:** Supervisor package consistency & statistical claim audit completed (audited review package and decision register, removed unsupported numerical power bounds, clarified non-significance does not prove equivalence, enforced 5-layer evidence distinction, reconciled 40/60 protocol partition proposal vs candidate alternatives).
**Phase 8F.1:** Core uncertainty aggregation engine completed (deterministic, transparent uncertainty aggregation engine, signal auditing, uncalibrated heuristic scores, 34 tests added).
**Phase 8F.2:** Uncertainty engine integration & end-to-end workflow completed (integrated `UncertaintyAggregationEngine` into `OrchestrationStateMachine`, wired `assess_uncertainty` and `record_uncertainty_aggregation`, mapped recommendations to state transitions, preserved reason codes in `FinalGatedAssessmentResult`, added `OrchestrationState.REJECTED` and `GatingDecision.REJECT`, added 16 end-to-end tests, 508 passed tests).
**Phase 8F.3:** Evaluation harness integration & offline replay completed (implemented `OrchestrationReplayAdapter`, `OrchestrationCaseFixture`, `ConditionStatus.OFFLINE_REPLAY_IMPLEMENTED`, runner registry registration, and configuration fingerprinting; verified genuine state machine execution, fail-closed handling, uncertainty engine impact, repeated trials aggregation without loci inflation, and reason-code audit traceability; 14 replay tests added; 522 passed tests).
**Phase 8F.4:** Provider-neutral LLM adapter & evidence-grounded specialist completed (implemented `ModelAdapterInterface`, `ModelProviderConfig`, `DeterministicModelAdapter`, `UnauthorizedLiveModelAdapter`, and `GroundedSpecialistAdapter`; enforced output schema, citation grounding, verbatim excerpt matching, and fail-closed handling of errors without silent fake fallback; 23 tests added; 545 passed tests).
**Phase 8F.5:** Grounded specialist integration & end-to-end offline replay completed (connected `GroundedSpecialistAdapter` to `OrchestrationStateMachine.execute_specialist_analysis` and `OrchestrationReplayAdapter`; verified fail-closed empty-evidence abstention without model invocation, excerpt verbatim validation, citation grounding, error traceability, deterministic replay stability, and calibration invariants; 12 integration tests added; 557 passed tests).
**Phase 8F.6:** Multi-specialist consensus & adversarial reviewer integration completed (exercised multi-specialist consensus, adversarial reviewer challenge/rejection, citation grounding, fail-closed handling of conflicting findings, and offline evaluation replay; 35 integration tests added; 592 passed tests).
**Phase 8G.1:** Empirical evaluation readiness & metrics integration completed (implemented specificity, evidence-grounding rate, citation-validation rate, incomplete rate, reviewer-rejection rate, specialist-disagreement rate, Wilson score confidence intervals, per-category scoring, and machine-checkable repository readiness audit; 19 tests added; 611 passed tests).
**Phase 8G.2:** AEGISCORE AI Flutter UI/UX Foundation completed (implemented dark cybersecurity Material 3 Flutter application in frontend/ with Riverpod, GoRouter, 6 core screens, repository abstraction, demo fixture mode, and 17 passed widget/state tests; flutter analyze clean; 611 python tests passing).
**Phase 8G.3:** Flutter–FastAPI read-only integration completed (configurable typed client for `GET /health` and `GET /capabilities`, demo/live repository selection, honest unsupported states for missing APIs, live submission disabled, 30 Flutter tests passed, and 611 Python tests passed). No backend route, schema, evidence approval, or supervisor decision was changed.
**Phase 8G.4:** Added paginated approved-evidence list/detail endpoints backed by the existing fail-closed persistent source-review selector; no configured store returns 503 and an explicitly configured empty store returns an empty collection. Flutter Evidence & Provenance is integrated with backend-only evidence and preserves loading, empty, and error states. Assessment/finding/evaluation APIs remain unsupported because no corresponding persistent record stores exist. `python -m pytest tests/` passed (617); from `frontend/`, `flutter analyze` found no issues and `flutter test` passed (36). No repository source approvals, supervisor decisions, empirical benchmark, or unsafe execution were added.

## Completed in Phase 8G.2 — AEGISCORE AI Flutter UI/UX Foundation

- **Modular Flutter Frontend Architecture (`frontend/`):**
  - Scoped standalone application without touching existing Python backend contracts or dependencies.
  - State management powered by Flutter Riverpod (`flutter_riverpod: ^2.6.1`).
  - Declarative routing via GoRouter (`go_router: ^14.8.1`) with nested stateful navigation shell.
  - Cybersecurity theme (`lib/core/theme/app_theme.dart`): Material 3 dark palette with deep terminal slate background (`#0B0F19`), surface containers (`#111827`), cyber cyan accents (`#06B6D4`), amber abstention indicators (`#F59E0B`), emerald verification highlights (`#10B981`), and ruby critical severity badges (`#EF4444`).
- **Responsive Layout & Navigation Shell (`lib/core/navigation/`):**
  - Implemented `AppScaffold`: automatically adapts between desktop/tablet navigation rail (expanded when width $\ge 1100\text{px}$) and mobile bottom navigation bar.
  - Integrated `DemoModeBanner`: constant visual indicator with status chips distinguishing offline mock fixture execution from live backend APIs.
  - Calibrated confidence and status badges with fail-safe overflow handling (`Wrap`, `Flexible`, `FittedBox`).
- **Core Screen Implementations:**
  - **Dashboard (`lib/features/dashboard/screens/dashboard_screen.dart`):** High-level security posture summary, 4 primary KPI cards (Total Findings, Verified Loci, Abstentions, Grounding Rate), recent assessment findings, and target catalog cards.
  - **Assessment Setup (`lib/features/assessment_setup/screens/assessment_setup_screen.dart`):** Strict lab scope boundary notice, authorized target selector (Juice Shop on port 3000, DVWA on port 8080), specialist team selection (minimum 2 specialists enforced), explicit lab authorization confirmation checkbox, and assessment queue action.
  - **Findings & Details (`lib/features/findings/screens/`):** Severity/status filter bar, findings card list with locus parameters and Wilson confidence intervals, and full inspection view (`FindingDetailsScreen`) detailing canonical coordinates, specialist consensus, adversarial reviewer challenge dissent, and verbatim grounded claims.
  - **Evidence Explorer (`lib/features/evidence/screens/evidence_explorer_screen.dart`):** Approved evidence corpus browser, SHA-256 provenance digest verification badges, exact version tags, chunk inspector with line ranges, and citation mapping.
  - **Reports & Benchmark Metrics (`lib/features/reports/screens/reports_screen.dart`):** Confusion matrix grid (Precision, Recall, Specificity, F1, Coverage, Abstention Rate, Evidence Grounding Rate), per-category score breakdown, and evaluation integrity & limitation banner documenting uncalibrated heuristic scores and bootstrap CI requirements.
  - **Settings & Status (`lib/features/settings/screens/settings_screen.dart`):** Backend health connection checker, offline synthetic demo status display, backend capabilities inventory, and security contract specifications.
- **Repository Abstraction & Demo Fixtures (`lib/services/`):**
  - Abstract interface `AegisCoreRepository` ensuring clean separation between UI components and backend communication.
  - `DemoAegisCoreRepository` providing realistic, offline cybersecurity assessment data adhering to canonical backend case schemas without network dependencies.
- **Frontend Test Suite & Static Verification (`frontend/test/`):**
  - `test/state_management_test.dart`: 9 tests verifying contract enforcement, lab scope boundaries (strictly localhost/127.0.0.1 on ports 3000/8080), confirmation requirements, and Riverpod notifier state transitions.
  - `test/findings_widget_test.dart`: 2 tests verifying finding card rendering, status filtering, and locus inspection.
  - `test/assessment_and_reports_test.dart`: 3 tests verifying lab boundary warnings, confirmation requirement, reports calculation, and settings status.
  - `test/app_navigation_test.dart`: 3 tests verifying desktop shell rendering, responsive navigation rail taps, and screen transitions.
  - Total: **17 tests passed (0 failures, 0 errors)** in `flutter test`.
  - Static analysis: **0 issues found** in `flutter analyze`.

## Completed in Phase 8G.1 — Empirical Evaluation Readiness & Metrics Integration

- **Evaluation Metrics Foundation & Extensions (`aegiscore/evaluation.py`):**
  - Added `specificity` metric: measures true negative rate on control cases ($TN / \text{Total Negatives}$).
  - Added `evidence_grounding_rate`: proportion of candidate findings with non-empty evidence citations.
  - Added `citation_validation_rate`: proportion of cited chunks validated against evidence bundles.
  - Added `incomplete_rate`: proportion of cases that encountered execution errors or incomplete processing.
  - Added `reviewer_rejection_rate` and `specialist_disagreement_rate`: explicit tallies of reviewer challenges and specialist conflicts.
  - Implemented `compute_wilson_score_interval()`: computes exact Wilson score confidence intervals for single binomial proportions (Recall, Specificity, Abstention Rate, Coverage, FPR, Precision), bounded within $[0.0, 1.0]$.
  - Preserved statistical review invariant: `f1_score` explicitly marks `ci_lower=None, ci_upper=None, ci_method="not_applicable"` and documents non-linear limitation requiring percentile bootstrap.
  - Added `calculate_per_category_scores()`: groups outcomes by `vulnerability_class` to produce partitioned `EvaluationScoreSummary` records alongside the aggregate, preventing cross-category sample inflation and handling zero denominators rigorously.
  - Enhanced `CaseEvaluationOutcome`: records `vulnerability_class`, `is_incomplete`, `error_status`, `evidence_citations_count`, `uncited_findings_count`, `reviewer_rejection`, `specialist_disagreement`, and `adjudication_state`.
  - Fail-closed incomplete execution invariant: incomplete runs (`is_incomplete=True`) are excluded from covered predictions (`is_covered=False`) and never counted as True Negatives or verified findings.
  - Enhanced `aggregate_repeated_runs()`: preserves `is_incomplete` and `error_status` across repeated trials without silent erasure.
- **Machine-Checkable Benchmark Readiness Audit (`aegiscore/catalog.py`):**
  - Implemented `BenchmarkReadinessReport` and `audit_benchmark_readiness()`: audits catalog records, ground-truth review states, partition approvals, source-review manifest status, and supervisor decision gates.
  - Implemented `load_and_audit_repository_readiness()`: loads actual canonical artifacts (`docs/case_catalog_draft.jsonl`, `docs/ground_truth_review_template.jsonl`, `docs/partition_assignment_template.jsonl`, `docs/source-review-manifest.json`, `docs/SUPERVISOR_DECISION_REGISTER.md`) in a read-only, offline manner.
  - Machine-checked results over actual repository data:
    - 36 total proposed catalog cases ($N=36$, 24 OWASP Juice Shop, 12 DVWA).
    - 23 cases missing established locus coordinates (20 candidate pool slots + 3 partial negative controls).
    - 28 cases lacking exact-version pinned source evidence.
    - 36 cases awaiting empirical testbed verification (all currently `unverified_offline`).
    - 36 cases without supervisor-adjudicated ground truth (all currently `unverified`).
    - 36 cases in unassigned/unapproved partitions.
    - 0 approved sources in source review manifest (`approval_status="no_sources_approved"`).
    - 8 supervisor decision gates pending (`DEC-01` through `DEC-08`).
    - `is_ready_for_empirical_run=False` confirmed honestly without mock fabrication.
- **Verification & Test Coverage (`tests/test_evaluation_metrics_and_readiness.py`):**
  - Added 19 comprehensive tests covering confusion matrix accounting, zero-denominator edge cases, incomplete fail-closed handling, Wilson intervals, operational reliability metrics, per-category scoring, repeated trial aggregation, and repository readiness audits.
  - Total test suite grew from 592 to 611 passed tests (0 failures, 0 skipped). Zero network calls, zero external LLM provider calls, zero database creation.

## Completed in Phase 8F.6 — Multi-Specialist Consensus & Adversarial Reviewer Integration

- **Adversarial Evidence Reviewer Implementation (`aegiscore/specialist_roles.py`):**
  - Enhanced `DeterministicEvidenceReviewerFake.review()` to accept `secondary_findings: Sequence[SpecialistFinding] | None`.
  - Implemented deterministic citation auditing: verifies citation chunk existence and source identity against evidence bundle, emitting explicit `REJECT` markers for invalid or unknown chunks.
  - Implemented claim challenge detection: checks proposed claim text for `[UNSUPPORTED]` and `[INSUFFICIENT_EVIDENCE]` tokens, emitting `CHALLENGE` markers.
  - Implemented multi-specialist consensus checks: detects conflicting conclusions across primary and secondary specialist findings and emits `CONFLICT_MARKER` notes.
- **Uncertainty Engine Proposed Claim Citation Grounding (`aegiscore/uncertainty_engine.py`):**
  - Augmented `UncertaintyAggregationEngine.aggregate()` to validate citations in `primary_finding.proposed_claims` against the bundle chunk map.
  - Enforced citation mismatch and missing chunk detection: sets `citation_checks_passed=False`, increments `signals.citation_checks_failed`, emits `CITATION_INVALID` reason code, and forces non-proceeding recommendation.
- **Multi-Specialist & Reviewer Integration Tests (`tests/test_multi_specialist_consensus.py`):**
  - Added 35 comprehensive end-to-end tests exercising all 6 scenario families and reviewer integration:
    - `SC-MS-01`: Specialists agree on evidence-supported hypothesis -> `CONTINUE` recommendation with `unanimous` consensus.
    - `SC-MS-02`: Contradictory specialist conclusions -> `disagreement` consensus, `SPECIALIST_DISAGREEMENT` reason code, forces `ABSTAIN`/`FLAG_FOR_REVIEW`.
    - `SC-MS-03`: One specialist abstains, one identifies vulnerability -> preserved specialist roles and abstention status, categorized as disagreement.
    - `SC-MS-04`: Unknown evidence ID or mismatched citation source -> flagged `CITATION_INVALID` / reviewer rejection, fails closed.
    - `SC-MS-05`: Specialist failure -> state machine transitions to `FAILED` with error traceable in history, zero fabricated findings; marked `is_incomplete=True` in replay.
    - `SC-MS-06`: Conflicting findings with insufficient evidence to resolve -> flagged `FLAG_FOR_REVIEW`, requires human review.
    - `SC-REV-01` to `SC-REV-06`: Adversarial reviewer challenges unsupported claims, rejects invalid citations, flags conflicting sanitization markers, recommends epistemic abstention, and ensures reviewer rejection cannot be bypassed by specialist consensus.
    - Replay & Compatibility: Full audit trail preserved in replay adapter; verified backward-compatibility for single-specialist configurations and empty evidence bundles.
  - Test suite grew from 557 to 592 passed tests (0 failures, 0 skipped). Zero network calls, zero external LLM provider calls, zero database creation.

## Completed in Phase 8F.5 — Grounded Specialist Integration & End-to-End Offline Replay

- **State Machine Dynamic Specialist Execution (`aegiscore/orchestration.py`):**
  - Added `execute_specialist_analysis(self, specialist: Any) -> SpecialistFinding`: safely executes dynamic specialist adapters (such as `GroundedSpecialistAdapter`) within the `RETRIEVAL_COMPLETED` state.
  - Fail-closed error isolation: catches unhandled specialist errors or model failures, transitions state machine to `FAILED`, and prevents state machine progression.
  - Maintains strict state sequencing: raises `StageBypassError` if invoked before `record_retrieval()`.
- **Harness & Offline Replay Integration (`aegiscore/evaluation_harness.py`):**
  - Extended `OrchestrationCaseFixture` and `OrchestrationReplayAdapter` to accept dynamic `specialist_adapter: Any = None`.
  - When configured, `OrchestrationReplayAdapter.run_case()` invokes `sm.execute_specialist_analysis(adapter)` in-flight during offline replay, directly feeding grounded findings into adversarial evidence review, uncertainty engine aggregation, claim validation, and response gating.
  - Preserved backward compatibility: falls back to static `specialist_finding` when no adapter is configured.
  - Empty evidence and zero approved sources short-circuit immediately in `record_retrieval()` before specialist or model adapter invocation.
  - Replay configuration payload and reproducibility fingerprint capture active specialist adapter class.
- **Verification & Test Coverage (`tests/test_grounded_specialist_replay.py`):**
  - Added 12 comprehensive end-to-end integration tests verifying:
    - In-flight specialist execution through both `OrchestrationStateMachine` and `OrchestrationReplayAdapter`.
    - Empty evidence bundle abstains without calling model adapter (guaranteed by assertion bomb).
    - Zero approved sources bundle abstains without calling model adapter (guaranteed by assertion bomb).
    - Exact verbatim excerpt matching succeeds; mismatched excerpts fail closed.
    - Unknown evidence IDs and mismatched source IDs are rejected with `CitationGroundingError`.
    - Contradictory output (vulnerable=True with is_abstained=True) fails closed with `is_incomplete=True`.
    - Specialist abstention routes deterministically to terminal `ABSTAINED` with `AggregationRecommendation.ABSTAIN`.
    - Specialist errors remain traceable in `error_status` with zero fabricated findings.
    - Repeated replay of offline fixtures produces byte-identical run IDs, finding IDs, and trajectory records.
    - Live provider execution in replay raises `LiveProviderExecutionUnavailableError` citing `DEC-07` without silent mock substitution.
    - State-machine safety guards prohibit stage bypass.
  - Total test suite expanded from 545 to 557 tests (all passing). Zero database files created. Zero network calls made.

## Completed in Phase 8F.4 — Provider-Neutral LLM Adapter & Evidence-Grounded Specialist

- **Provider-Neutral Model Adapter Foundation (`aegiscore/model_adapter.py`):**
  - Defined minimal typed data contracts: `ModelRequest`, `ModelResponse`, `TokenUsage`, `ModelProviderConfig`, and `ProviderMode` (`DETERMINISTIC_FAKE`, `LIVE_UNAUTHORIZED`).
  - Implemented typed error hierarchy: `ModelAdapterError`, `ModelConfigurationError`, `ModelProviderError`, `ModelTimeoutError`, `LiveProviderExecutionUnavailableError`, `ModelResponseValidationError`, and `ContradictoryOutputError`.
  - Implemented `DeterministicModelAdapter(ModelAdapterInterface)`: produces repeatable, deterministic responses for offline test fixtures and evaluation replay with zero network activity.
  - Implemented `UnauthorizedLiveModelAdapter(ModelAdapterInterface)`: fails closed with `LiveProviderExecutionUnavailableError` whenever live execution is requested, explicitly referencing `DEC-07` status `PENDING` and ADR 0002 default-deny network egress.
  - Enforced strict prohibition of silent fallback: provider failures, timeouts, and authorization errors propagate directly and are NEVER silently replaced with fake model outputs.
  - Implemented bounded response size limits (65,536 characters) and secret/credential redaction (`redact_sensitive_text`).
- **Evidence-Grounded Specialist Adapter (`GroundedSpecialistAdapter`):**
  - Implements the existing `VulnerabilityAnalystFakeProtocol` contract behind a model adapter: `analyse(request_id: str, bundle: EvidenceBundle) -> SpecialistFinding`.
  - Supplies strictly bounded assessment scope and retrieved evidence chunks to the model adapter; never sends arbitrary queries or live targets.
  - Enforces fail-closed output validation:
    - Rejects malformed JSON, invalid schemas, and unrecognized severity enums.
    - Rejects unknown chunk IDs and mismatched source IDs against the evidence bundle (`CitationGroundingError`).
    - Enforces verbatim substring matching on cited excerpts (`validate_citation_excerpt`).
    - Fails closed on contradictory output (e.g., `vulnerability_identified=True` with `is_abstained=True` or zero claims).
    - Automatically abstains without model invocation when evidence bundle is empty or has zero approved sources.
  - Preserves core safety invariants: `is_confirmed = False` and `factual_support = 'not_evaluated'`.
- **Verification & Test Coverage (`tests/test_model_adapter.py`):**
  - Added 23 unit tests verifying: valid structured responses, code-fence unwrapping, missing schema fields rejection, malformed JSON rejection, invalid severity enums, unknown evidence IDs rejection, source ID mismatches rejection, verbatim excerpt verification, immediate empty-bundle abstention, explicit abstention handling, contradictory output rejection, provider timeout fail-closed behavior, unauthorized live provider error enforcement, prohibition of silent fallback, zero unapproved network calls (patched socket verification), deterministic repeatability, bounded response sizing, secret redaction, factory routing, OrchestrationStateMachine compatibility, and evaluation replay compatibility.
  - Total test suite expanded from 522 to 545 tests (all passing). Zero database files created. Zero network calls made.

## Completed in Phase 8F.3 — Evaluation Harness Integration & Offline Replay

- **Offline Replay Adapter (`aegiscore/evaluation_harness.py`):**
  - Implemented `OrchestrationReplayAdapter(EvaluationRunnerInterface)`: executes the genuine `OrchestrationStateMachine` end-to-end against typed `OrchestrationCaseFixture` inputs, including retrieval, primary specialist, evidence review, uncertainty engine aggregation (`UncertaintyAggregationEngine`), and claim validation / gating.
  - Implemented `OrchestrationCaseFixture`: typed frozen dataclass bundling case identity, target locus, synthetic retrieval evidence bundle, primary and secondary specialist findings, evidence review verdict/notes, and optional claim validation and generation results.
  - Added `ConditionStatus.OFFLINE_REPLAY_IMPLEMENTED = "offline_replay_implemented"` to distinguish genuine orchestration replay from static stub fixtures.
  - Added `RunnerConditionRegistry.register_offline_replay_adapter()` and updated `get_adapter()` to support offline replay adapters.
  - Updated configuration fingerprinting in `create_configuration_fingerprint()` to capture `runner_id` and optional `adapter_config`.
  - Added convenience builders: `create_orchestration_case_fixture()` and `create_orchestration_replay_adapter()`.
  - Preserved core safety and scientific invariants: `confidence_is_calibrated = False`, factual support remains `"not_evaluated"` offline, and run record metadata includes uncertainty recommendation, heuristic scores, reason codes, and trajectory.
  - Fail-closed error handling: catches unexpected execution exceptions, transitions state machine to `FAILED`, and records incomplete run records with `ABSTAINED` decision.
- **Verification & Test Coverage (`tests/test_evaluation_replay.py`):**
  - Added 14 comprehensive tests verifying:
    - Genuine orchestration state machine invocation (not stub output).
    - Uncertainty engine directly influences harness results (recommendation mapped to gating).
    - Evidence-supported cases proceed to positive verification when criteria are satisfied.
    - Insufficient evidence triggers fail-closed abstention (`ABSTAINED_POSITIVE`).
    - Reviewer rejection produces rejected terminal outcome (`REJECTED` / `TN`).
    - Specialist disagreement triggers fail-closed abstention and preserves `SPECIALIST_DISAGREEMENT` reason codes.
    - Citation/excerpt invalidity blocks verified positive results.
    - Run records correspond precisely to case IDs and repeat indices.
    - Repeated trials ($k$ repeats) are preserved individually and aggregated with locus-level consistency without inflating $N$.
    - Score summaries trace back deterministically to case-level outcomes.
    - Unknown or unavailable conditions fail closed (`HarnessValidationError`).
    - Unexpected internal exceptions fail closed into safe abstention/failure records.
    - Determinism: identical fixture inputs produce byte-identical run records and fingerprints.
    - Strict adjudication: unadjudicated ground truth records fail closed under strict mode.
  - Total test suite expanded from 508 to 522 tests (all passing). Zero database files created.

## Completed in Phase 8F.2 — Uncertainty Engine Integration & End-to-End Workflow

- **Orchestration State Machine Engine Integration (`aegiscore/orchestration.py`):**
  - Added `assess_uncertainty(self, engine, secondary_findings, ...)` to `OrchestrationStateMachine`: invokes `UncertaintyAggregationEngine` directly from `EVIDENCE_REVIEW_COMPLETED`, maps recommendations deterministically, and fails closed on unhandled engine exceptions by transitioning to `FAILED`.
  - Added `record_uncertainty_aggregation(self, result)`: validates request matching, records the audit object, derives standard `UncertaintyAssessment` and `ConflictAssessment` objects, and executes deterministic transitions:
    - `CONTINUE`: advances to `UNCERTAINTY_ASSESSED`, permitting claim validation.
    - `ABSTAIN`: transitions to `UNCERTAINTY_ASSESSED` then immediately halts at terminal `ABSTAINED` with machine-readable justification.
    - `REJECT`: transitions to `UNCERTAINTY_ASSESSED` then immediately halts at terminal `REJECTED` with rejection justification.
    - `FLAG_FOR_REVIEW`: transitions to `UNCERTAINTY_ASSESSED` then immediately halts at terminal `FLAGGED_FOR_REVIEW`.
  - Added terminal state `OrchestrationState.REJECTED` and gating outcome `GatingDecision.REJECT`.
  - Extended `FinalGatedAssessmentResult` with `uncertainty_aggregation: Any = None` and `reason_codes: tuple[str, ...]` property for audit traceability.
  - Added `create_final_result` convenience builder on `OrchestrationStateMachine` aligning final decision with aggregation recommendation.
  - Updated `UncertaintyAggregationEngine.aggregate()` in `aegiscore/uncertainty_engine.py` to handle `secondary_findings=None` gracefully.
- **End-to-End Test Suite (`tests/test_uncertainty_workflow_e2e.py`):**
  - Added 16 tests covering: direct engine invocation, complete happy-path forward execution, specialist disagreement fail-closed abstention, missing evidence blocking, insufficient chunk thresholds, citation mismatches, excerpt mismatches, reviewer rejections, contradictory evidence abstention, flag-for-review routing, reason code traceability, deterministic repeatability, fail-closed handling of unexpected engine errors, scope violation guards, stage bypass prohibitions, and calibration invariants.
  - Total test suite expanded from 492 to 508 tests (all passing). Zero database files created.


## Completed in Phase 8F.1 — Core Uncertainty Aggregation Engine

- **Typed Deterministic Uncertainty Aggregation Engine (`aegiscore/uncertainty_engine.py`):**
  - Implemented `UncertaintyAggregationEngine`, integrating multiple analytical signals across the multi-agent pipeline:
    - Evidence sufficiency (chunk counts, approved source verification, minimum chunk thresholds).
    - Specialist consensus (unanimous agreement, majority agreement, split/disagreement, single finding, or no findings).
    - Evidence reviewer verdicts (uncontested, challenged, mitigated, or rejected).
    - Citation and verbatim excerpt integrity (chunk existence in evidence bundle, excerpt exact presence in source chunk content).
    - Conflict markers and category-specific contradictory patterns (e.g., prepared statement vs. raw concatenation, sanitization vs. reflected payload, rate-limiting vs. brute force).
    - Epistemic uncertainty terminology detection in specialist outputs (`unclear`, `possible`, `unconfirmed`, `plausible`, etc.).
    - Source provenance integrity (verification against approved chunk fingerprints).
  - Produces structured `UncertaintyAggregationResult` containing:
    - `recommendation`: Enum `AggregationRecommendation` (`CONTINUE`, `REJECT`, `ABSTAIN`, `FLAG_FOR_REVIEW`).
    - `overall_heuristic_score`: Deterministic continuous float $[0.0, 1.0]$ synthesizing all active signals.
    - `is_sufficient`: Boolean gating flag for evidence sufficiency.
    - `abstention_recommended`: Boolean fail-closed abstention flag.
    - `primary_reason_code` and `contributing_reason_codes`: Explicit machine-readable `UncertaintyReasonCode`s (`EVIDENCE_ABSENT`, `EVIDENCE_INSUFFICIENT`, `CITATION_INVALID`, `EXCERPT_MISMATCH`, `REVIEWER_REJECTION`, `REVIEWER_CHALLENGE`, `CONFLICT_MARKERS_PRESENT`, `SPECIALIST_DISAGREEMENT`, `EPISTEMIC_AMBIGUITY`, `SUFFICIENT_AND_CONSISTENT`).
    - `signals`: Typed, granular `SignalAuditRecord` detailing all evaluated signals.
    - `confidence_is_calibrated`: Invariant `Literal[False] = False`, explicitly distinguishing heuristic scoring from calibrated probabilities.
  - Provided bidirectional conversion adapters: `to_uncertainty_assessment()` and `to_conflict_assessment()`, allowing drop-in integration with existing orchestration contracts.
- **Verification & Test Coverage (`tests/test_uncertainty_engine.py`):**
  - Added 34 unit tests covering:
    - Normal evidence-supported path returning `CONTINUE` with `SUFFICIENT_AND_CONSISTENT`.
    - Fail-closed behavior on missing evidence (`EVIDENCE_ABSENT`), insufficient chunks (`EVIDENCE_INSUFFICIENT`), invalid citations (`CITATION_INVALID`), and excerpt mismatches (`EXCERPT_MISMATCH`).
    - Reviewer rejection (`REVIEWER_REJECTION`) and reviewer challenge handling.
    - Specialist finding disagreements (`SPECIALIST_DISAGREEMENT`) and conflict markers.
    - Epistemic uncertainty keyword detection triggering abstention.
    - Override flags (`force_sufficient`, `force_conflict`).
    - Determinism guarantees (identical inputs produce byte-identical SHA-256 IDs, scores, and reason codes).
    - Full conversion compatibility to `UncertaintyAssessment` and `ConflictAssessment`.
    - Type and contract enforcement (rejection of malformed requests, mismatched IDs, and out-of-range scores).
  - Total test suite expanded from 458 to 492 tests (all passing). Zero database files created.


## Completed in Phase 8E.7.1 — Supervisor Package Consistency & Statistical Claim Audit

- **Audit of Statistical Claims:**
  - Audited numerical power assertions: eliminated unverified claims of fixed detectable odds ratios ($OR \ge 3.0$) and fixed required discordant pairs ($b-c \ge 8..12$) across `docs/SUPERVISOR_REVIEW_PACKAGE.md` and `docs/SUPERVISOR_DECISION_REGISTER.md`.
  - Grounded McNemar's paired test power strictly in the observed discordant total ($n_{\text{disc}} = b + c$), explaining that high concordance between LLM and baseline tools collapses effective sample size and prevents a priori power determination.
  - Formally mandated that failure to reject $H_0$ ($p \ge 0.05$) under this exploratory sample must NEVER be interpreted or reported as proof of equivalence, parity, or absence of an effect.
- **Evidence Hierarchy & Terminology Alignment:**
  - Formally articulated the 5-layer epistemological hierarchy: (1) Source-code observation, (2) Exact-version source support, (3) Testbed image/version confirmation, (4) Empirical runtime verification, (5) Supervisor-adjudicated ground truth.
  - Re-classified candidate negative controls under this hierarchy: `JS-BAC-02` (exact-version source supported on Juice Shop v15.0.0; runtime unverified; unadjudicated), `DVWA-XSS-R-02` and `DVWA-SQLI-02` (upstream source reviewed; version-unverified against testbed image `1.10`; runtime unverified; unadjudicated).
- **Partition Policy Reconciliation:**
  - Reconciled the pre-registered protocol proposal (Within-Benchmark Stratified 40% validation / 60% test split on Juice Shop with secondary DVWA transfer) against candidate alternative proposals (50/50 split, zero-shot 100% test, K-fold cross-validation) in `DEC-05` and review package §3.1.
  - Confirmed all 36 catalog records currently remain `UNASSIGNED` with zero data leakage.
- **Documentation Artifacts:**
  - Created `docs/PHASE_8E7_1_PACKAGE_CONSISTENCY_AUDIT.md`.
  - Corrected `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§3.1, §4.2, §5) and `docs/SUPERVISOR_DECISION_REGISTER.md` (DEC-01, DEC-04, DEC-05).
  - All 458 full-suite tests pass. Live execution remains on strict HOLD.

## Completed in Phase 8E.7 — Supervisor Review Package & Decision Register

- **Consolidated Supervisor Review Package (`docs/SUPERVISOR_REVIEW_PACKAGE.md`):**
  - Consolidated thesis objectives, current implementation status, and exact capabilities across all 9 prior modules.
  - Formally articulated the epistemological boundary: automated tests prove internal contract invariants, fail-closed mechanics, and scoring determinism, but do NOT prove real vulnerability detection or live LLM accuracy.
  - Summarized the 36-case benchmark scope, documenting that only 16 scenarios are protocol-registered while 20 slots remain unpopulated candidate placeholders.
  - Recorded exact 7-category accounting counts (16 protocol-registered, 13 complete loci, 13 external source-reviewed, 8 exact-version Juice Shop v15.0.0 supported, 0 empirically verified, 0 ground-truth adjudicated, 0 partitions approved).
  - Highlighted DVWA image-version mismatch (`testbed/docker-compose.yml` pins `vulnerables/web-dvwa:1.10`, early drafts cited `2024.1`).
  - Outlined statistical constraints of small sample sizes ($N=36$), paired McNemar's test power limitations, endpoint clustering on search/login, and mandatory exploratory proof-of-concept framing.
  - Documented negative-control critiques: stock login SQLi is unparameterized (contradicted by source), search reflection is client-only DOMPurify (invalid API control), and malformed 500 error is an epistemic uncertainty input probe rather than an independent non-vulnerable locus.
  - Formulated a recommended 6-stage approval-gated sequence for future work.
- **Formal Supervisor Decision Register (`docs/SUPERVISOR_DECISION_REGISTER.md`):**
  - Created structured decision tables for 8 required governance gates:
    - `DEC-01`: Approval of Exploratory Statistical Framing (McNemar's test, discordant pairs, exploratory disclaimer)
    - `DEC-02`: Acceptance or Revision of Proposed Evaluation Scope ($N=36$; resolution of 20 candidate slots)
    - `DEC-03`: Ground-Truth Review and Adjudication Procedure (3-part verification artifact requirement)
    - `DEC-04`: Case Inclusion/Exclusion & Negative-Control Decisions (`JS-SQLI-03`, `JS-XSS-R-02`, `JS-SQLI-04` resolution)
    - `DEC-05`: Approval of Validation/Test Partition Policy (40/60 Juice Shop split, secondary DVWA transfer)
    - `DEC-06`: Benchmark Version and Immutable Image-Digest Policy (DVWA 1.10 vs 2024.1 freeze; SHA-256 digest pinning)
    - `DEC-07`: Model-Provider Architecture Selection (Cloud Gemini 1.5 Pro via narrow ADR 0002 exemption vs Local Ollama/vLLM)
    - `DEC-08`: Explicit Authorization for Container Startup & Live Execution (Strict offline HOLD gate)
  - All 8 decisions initialized strictly to `PENDING`. Zero supervisor identities, dates, or decisions were fabricated.
- **Enforcement of the Strict Approval Boundary:**
  - Preserved all catalog records in `UNVERIFIED` adjudication status and all partition records in `UNASSIGNED` status.
  - Explicitly confirmed that no supervisor approval may be inferred from any prepared package.
  - Full test suite passes completely offline with 458 tests (0 failed, 0 skipped).

## Completed in Phase 8E.6.1 — Version-Pinned Evidence Traceability & Negative-Control Reclassification

- **Version-Pinned Upstream Traceability Matrix (`docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md`):**
  - Traced all evidence claims to specific upstream repositories, exact release tags (`v15.0.0` for Juice Shop, `1.10` for DVWA), file paths, line ranges, and symbols.
  - Identified DVWA testbed version discrepancy (`vulnerables/web-dvwa:1.10` in `testbed/docker-compose.yml` vs `2024.1` in early catalog drafts). Classified DVWA claims as `VERSION_UNVERIFIED` against the testbed image.
  - Confirmed zero target application source files are vendored in the local workspace; all source claims represent external literature and code reviews.
- **Deep-Dive Negative-Control Methodology Audit:**
  - Audited all 6 negative controls under strict epistemological standards (absence of reported flaw is not proof of safety):
    - `JS-XSS-R-02`: Client DOMPurify does not render server API non-vulnerable; reflection in JSON alone does not establish XSS.
    - `JS-SQLI-03`: Parameterized login claim directly contradicted by stock v15.0.0 source (raw SQL concatenation).
    - `JS-SQLI-04`: Generic 500 error on malformed input does not establish an independent non-vulnerable locus. Reclassified as epistemic uncertainty diagnostic scenario.
    - `JS-BAC-02`: Verified `@RolesAllowed('admin')` guard in v15.0.0 source; candidate negative control pending live HTTP replay.
    - `DVWA-XSS-R-02`: Verified server-side `htmlspecialchars` in impossible level; version-unverified against 1.10 testbed image.
    - `DVWA-SQLI-02`: Verified PDO prepared statement in impossible level; version-unverified against 1.10 testbed image.
- **Multi-Dimensional Status Taxonomy Expansion (`aegiscore/catalog.py`):**
  - Added `SourceEvidenceStatus` (`EXACT_VERSION_PINNED`, `VERSION_UNVERIFIED`, `CONTRADICTED_BY_SOURCE`, `SYNTHETIC_SPECIFICATION`, `UNRESOLVED`) and `RuntimeVerificationStatus` (`UNVERIFIED_OFFLINE`, `EMPIRICALLY_VERIFIED`, `NOT_APPLICABLE`).
  - Integrated into `CatalogRecord` with backward-compatible defaults in `__post_init__`, `to_dict()`, and `from_dict()`.
  - Re-serialized `docs/case_catalog_draft.jsonl` with all 5 status dimensions.
- **Strict Seven-Category Dataset Accounting:**
  - (1) Protocol-registered scenarios: 16
  - (2) Complete canonical locus metadata: 13
  - (3) External source-reviewed candidates: 13
  - (4) Exact-version source-supported candidates: 8 (Juice Shop v15.0.0)
  - (5) Empirically verified cases: 0
  - (6) Adjudicated ground-truth records: 0 (all 36 remain `UNVERIFIED`)
  - (7) Approved dataset partitions: 0 (all 36 remain `UNASSIGNED`)
- **Unit Test Coverage (`tests/test_catalog.py`):**
  - Added 3 unit tests verifying source evidence status defaults, contradicted handling, version unverified status, and invalid enum rejection.
  - 41 catalog tests pass; full test suite passes with 458 tests (0 failed, 0 skipped).

## Completed in Phase 8E.6 — Case Catalog Provenance Audit & Supervisor Review Package

- **Exhaustive Case Provenance Audit (`docs/PHASE_8E6_CATALOG_PROVENANCE_AUDIT.md`):**
  - Audited all 36 proposed case slots: 13 complete loci, 3 partial loci, 20 unresolved candidate slots.
  - Confirmed 0 cases have locally traceable application source in `s:\AegisCore` (benchmark targets have never been cloned or launched).
  - Categorized evidence basis: literature and protocol metadata citations vs. repo-verifiable files.
  - Exactly 0 ground-truth records are adjudicated (all 36 remain `UNVERIFIED`).
  - Exactly 0 partitions are approved (all 36 remain `UNASSIGNED`).
- **Negative-Control Validity & Methodology Audit:**
  - Audited the 3 PARTIAL negative controls:
    - `JS-XSS-R-02`: Identified that DOMPurify sanitization is client-side only; backend API reflects payload raw. Invalid server-side control on stock target.
    - `JS-SQLI-03`: Identified that stock Juice Shop login uses raw SQL string concatenation; parameterized login does not exist in stock v15.0.0. Invalid control on stock target.
    - `JS-SQLI-04`: Reclassified generic 500 error as an input-handling uncertainty test, not an independent negative locus.
  - Verified 3 genuine stock negative controls: `JS-BAC-02` (403 Forbidden via `@RolesAllowed`), `DVWA-XSS-R-02` (server-side `htmlspecialchars`), `DVWA-SQLI-02` (server-side PDO prepared statement).
- **Status Taxonomy Refinement (`aegiscore/catalog.py`):**
  - Implemented `ScenarioRegistrationStatus` (`PROTOCOL_PRE_REGISTERED`, `CANDIDATE_POOL`) and `LocusVerificationStatus` (`SYNTACTICALLY_SPECIFIED`, `PARTIALLY_SPECIFIED`, `EMPIRICALLY_VERIFIED`, `UNRESOLVED`).
  - Integrated into `CatalogRecord` with backward-compatible defaults in `__post_init__`, `to_dict()`, and `from_dict()`.
  - Re-serialized `docs/case_catalog_draft.jsonl` with explicit provenance attributes.
- **Supervisor Review Package & Decision Checklist:**
  - Formulated Tier-1 candidate pool (12 cases ready for review upon testbed execution).
  - Documented Tier-2 hold (3 negative controls requiring testbed patching vs. fixture mock decision).
  - Documented Tier-3 hold (20 unresolved slots requiring supervisor locus selection).
  - Formulated 4 critical supervisor decision gates.
- **Unit Test Coverage (`tests/test_catalog.py`):**
  - Added 4 unit tests covering taxonomy defaults, partial handling, explicit roundtrips, and invalid enum rejection.
  - Test suite passes with 455 tests (417 regression + 38 catalog tests; 0 failed, 0 skipped).

## Completed in Phase 8E.5 — Canonical Case Catalog & Ground-Truth Preparation

- **Catalog Data Contracts & Validators (`aegiscore/catalog.py`):**
  - Implemented `CatalogRecord`, `GroundTruthReviewRecord`, `PartitionAssignmentRecord`, `IndependenceAuditRecord`.
  - Implemented strict fail-closed JSONL stream parsers and validators: `validate_catalog_jsonl`, `validate_ground_truth_review_jsonl`, `validate_partition_assignment_jsonl`, `validate_independence_audit_jsonl`.
  - Enforced strict invariants:
    - Zero cases may be marked `ADJUDICATED` without an authenticated `reviewer_identity` and ISO `adjudication_date`.
    - No case may be assigned to any partition other than `UNASSIGNED` without formal `approved_by` supervisor authority.
    - Strict disjointness rule between `validation` and `test` partitions for Juice Shop cases.
    - Non-duplicate case IDs and non-duplicate canonical loci `(benchmark_name, target_uri, parameter, cwe_id)` across all ESTABLISHED catalog records.
    - Supported optional locus attributes for `UNRESOLVED` and `PARTIAL` records without schema bypass.
- **Extended Configuration Fingerprinting (`aegiscore/catalog.py`):**
  - Created `FingerprintInputs` and `compute_extended_fingerprint()`.
  - Expanded Phase 8E.4 fingerprint from 6 to 12 configuration dimensions, adding `adapter_version`, `catalog_version`, `scoring_protocol_version`, `aggregation_policy`, `model_identifier`, and `prompt_version`.
  - Guaranteed permutation-invariance via `sorted(case_ids)` and strictly excluded non-deterministic runtime metadata (timestamps, hardware identifiers).
- **Generated Review & Adjudication Package (`docs/`):**
  - `docs/case_catalog_draft.jsonl`: 36 proposed case slots (16 evidence-backed from Protocol Table 6: 13 established, 3 partial; 20 unresolved candidate slots: 13 Juice Shop, 7 DVWA).
  - `docs/ground_truth_review_template.jsonl`: 36 review templates (all 36 `UNVERIFIED`, `reviewer_identity: "UNASSIGNED"`, `eligible_for_dataset: false`).
  - `docs/partition_assignment_template.jsonl`: 36 partition templates (all 36 `UNASSIGNED`, `approved_by: null`).
  - `docs/independence_audit_template.jsonl`: 4 identified locus overlap and leakage risk records (`/rest/products/search` shared route, login parameterized negative control).
- **Comprehensive Phase Report (`docs/PHASE_8E5_CASE_CATALOG_AND_GROUND_TRUTH.md`):**
  - Documented schema reference, pre-registered scenario mapping, unresolved candidate slots, ground-truth review workflow, independence and leakage audit, partition governance rules, configuration fingerprint comparison, known limitations, supervisor decision gates, and GO/HOLD recommendations.
- **Unit Test Coverage (`tests/test_catalog.py`):**
  - 34 comprehensive unit tests: catalog record roundtrip, unresolved record handling, missing/invalid locus rejection, invalid case IDs and benchmarks, duplicate case IDs and loci, partial locus duplicate tolerance, ground-truth adjudication gates, unassigned partition restrictions, approval gates, partition overlap detection, independence audit validation, extended fingerprint determinism and order-invariance, and static schema validation of all four generated draft JSONL files.
  - Test suite passes with 451 tests (0 failed, 0 skipped).

## Completed in Phase 8E.4 — Offline Runner Wrappers & Fixture-Based Evaluation Harness

- **Runner Condition Registry (`aegiscore/evaluation_harness.py`):**
  - Implemented `RunnerConditionRegistry` with three exclusive operational statuses: `FIXTURE_IMPLEMENTED`, `PLANNED_UNAVAILABLE`, and `LIVE_PROHIBITED`.
  - `BASELINE_DAST_ZAP` permanently marked `LIVE_PROHIBITED`; cannot be fetched or invoked.
  - All other conditions (`PROPOSED_MULTI_AGENT`, `BASELINE_SINGLE_AGENT`, `BASELINE_MA_NO_ABSTENTION`, `ABLATION_NO_RAG`, `ABLATION_NO_REVIEWER`) default to `PLANNED_UNAVAILABLE` in the default registry until an explicit fixture adapter is bound.
  - No silent fallback: missing adapter raises `ConditionUnavailableError` or `LiveExecutionProhibitedError`.
  - Friendly string aliases (`MULTI_AGENT_FULL`, `SINGLE_AGENT_BASELINE`, `RAG_DISABLED_ABLATION`, etc.) normalized to canonical `RunnerCondition` enums.
- **Evaluation Harness Orchestrator (`aegiscore/evaluation_harness.py`):**
  - Implemented `EvaluationHarness` with `execute()` and `execute_from_jsonl()` methods.
  - `execution_mode` guard: raises `LiveExecutionProhibitedError` on any non-`"offline_fixture"` mode string.
  - Validates manifests (duplicate `case_id`, duplicate canonical loci), ground truth (missing, duplicate, foreign key, adjudication state).
  - Executes $K$ repeated trials per locus and validates: correct `case_id`, correct `repeat_index`, unique `run_id`, adapter consistency.
  - Computes `TrialAgreementSummary` (unanimous vs. split, agreement rate labeled as fixture determinism).
  - Aggregates using `aggregate_repeated_runs` (majority vote $\ge 2/3$; splits fail closed to `ABSTAINED`).
  - Scores outcomes with `calculate_evaluation_scores`; all Phase 8E.3 abstention and zero-denominator invariants enforced.
  - Produces cryptographically fingerprinted `EvaluationRunManifest` (SHA-256 configuration fingerprint).
- **Structured Output Contracts (`aegiscore/evaluation_harness.py`):**
  - `EvaluationRunManifest`: fixture dataset ID/version, condition, config fingerprint, timestamps, validation errors, synthetic disclaimer.
  - `TrialAgreementSummary`: case-level decision stability analysis with explicit deterministic-fixture attribution.
  - `HarnessExecutionReport`: complete execution trace (manifest + raw trials + aggregated outcomes + trial agreement + score summary), serializable via `to_dict()` and `to_json()` with stable ordering.
- **Synthetic Fixture Helper (`aegiscore/evaluation_harness.py`):**
  - `create_synthetic_fixture_adapter()` generates `FixtureBackedRunnerAdapter` instances from case manifests with customizable per-case decision overrides.
- **Documentation (`docs/PHASE_8E4_OFFLINE_EVALUATION_HARNESS.md`):**
  - Architecture workflow diagram, condition registry taxonomy, input/output schemas, metric invariants, safety restrictions, and supervisor approval gates.
- **Test Coverage (`tests/test_evaluation_harness.py`):**
  - 21 unit tests: default registry status, alias normalization, live prohibition, planned unavailability, adapter registration, live execution mode rejection, empty inputs, duplicate loci, missing ground truth, unadjudicated ground truth, 4-case E2E with confusion matrix verification, K=3 repeated trial preservation and agreement, abstention invariants and selective risk, JSONL roundtrip, deterministic JSON serialization, split-decision majority voting fail-closed, duplicate run IDs, inconsistent case IDs from adapters, malformed JSONL, zero network access guarantee.



- **Canonical Evaluation Contracts (`aegiscore/evaluation.py`):**
  - Created versioned, typed dataclass contracts: `CanonicalLocus` (Unit of Analysis `(URI, Param, CWE)`), `EvaluationCaseManifestRecord` (benchmark scenario manifest), `AssessmentFindingRecord` (specialist findings), `AssessmentResultRecord` (terminal assessment outcome), `EvaluationRunRecord` (trial execution episode), `GroundTruthRecord` (adjudicated ground truth), and `MetricOutputRecord` (metric output with explicit denominator audit).
  - Enforced schema versioning (`1.0.0`) and non-empty trimmed string invariants on all identifiers.
- **Strict JSONL Stream Validators (`aegiscore/evaluation.py`):**
  - Implemented `validate_manifest_jsonl`, `validate_ground_truth_jsonl`, and `validate_runs_jsonl`.
  - Enforced duplicate detection: rejects duplicate `case_id`s, duplicate canonical loci, duplicate `run_id`s, and duplicate `(runner_id, case_id, repeat_index)` tuples.
  - Enforced foreign key integrity: rejects ground truth or run records referencing unknown case IDs.
  - Fail-closed parsing: rejects malformed JSON, unmapped enum values, and incomplete evidence references without silent repair.
- **Deterministic Offline Scoring Pipeline (`aegiscore/evaluation.py`):**
  - Implemented `evaluate_case_outcome` and `calculate_evaluation_scores`.
  - Enforced core abstention invariants:
    - Abstaining on a ground-truth VULNERABLE target counts as an empirical False Negative ($FN$) in standard detection recall.
    - Abstaining on a ground-truth NON-VULNERABLE target is an Abstention, NEVER a True Negative ($TN$).
    - Abstentions decrease coverage ($\Phi = 1 - AR$) and are excluded from the covered prediction set for selective risk ($R(\Phi) = 1 - \text{Precision}$).
  - Zero-denominator safety: reports `MetricStatus.UNDEFINED` with `value = None` when denominators are zero (e.g. Precision when 0 findings reported), preventing fabricated 0.0 or 1.0 scores.
  - Calibration metrics (`brier_score`, `expected_calibration_error`) explicitly marked `NOT_SUPPORTED` on categorical/discrete outputs.
  - Implemented `aggregate_repeated_runs`: majority consensus voting ($\ge 2/3$) collapses repeated trials back to canonical case loci without inflating sample size. Split decisions fail closed to `ABSTAINED`.
- **Runner Interfaces & Offline Fixture Adapter (`aegiscore/evaluation.py`):**
  - Defined abstract `EvaluationRunnerInterface` and `RunnerCondition` enum covering all proposed conditions ($P, B1, B2, B3, A1, A2$).
  - Implemented `FixtureBackedRunnerAdapter` enabling offline synthetic test replay without external calls.
- **Documentation & Test Coverage:**
  - Authored comprehensive documentation in `docs/PHASE_8E3_EVALUATION_CONTRACTS.md`.
  - Added 26 unit tests in `tests/test_evaluation_contracts.py` covering locus validation, JSONL parsing, duplicate detection, confusion matrix math, abstention accounting, zero denominators, repeated-run voting, and fixture runners. Total test suite expanded to 396 passed tests. Zero database files created.

## Completed in Phase 8E.2B — Offline Benchmark Testbed Harness Engineering

- **Isolated Testbed Configuration (`testbed/docker-compose.yml`):**
  - Configured pinned benchmark targets: OWASP Juice Shop (`bkimminich/juice-shop:v15.0.0`) and DVWA (`vulnerables/web-dvwa:1.10`).
  - Attached targets exclusively to an internal bridge network (`aegiscore-internal-net`, `internal: true`) with private subnet `172.28.0.0/16` and gateway `172.28.0.1`.
  - Bound published ports exclusively to host loopback (`127.0.0.1:3000:3000` and `127.0.0.1:8080:80`) to allow local harness interaction while preventing external LAN/WAN exposure.
  - Disabled automatic restarts (`restart: "no"`) and enforced `security_opt: [no-new-privileges:true]`. Prohibited privileged mode, host networking, host filesystem mounts, and Docker socket mounts.
- **Zero-Dependency Testbed Validation Layer (`aegiscore/testbed.py`):**
  - Authored typed data contracts (`TestbedServiceConfig`, `TestbedNetworkConfig`, `TestbedSpecification`, `HealthCheckTarget`, `ResetOperation`).
  - Implemented static Compose parser and validator (`validate_compose_content`, `validate_compose_file`) verifying network isolation, loopback port binding, image pinning, and non-privileged constraints without third-party dependencies (no PyYAML).
  - Implemented target allowlist scope verification (`verify_target_allowlist`) rejecting public IPs, external domains, and unauthorized ports.
  - Implemented fail-closed execution guards (`ExecutionGuardError`) preventing live container commands or network requests in Phase 8E.2B.
- **Supporting Scripts in `scripts/`:**
  - `scripts/verify_testbed_harness.py`: Statically verifies `testbed/docker-compose.yml`, allowlists, and reset contracts from CLI.
  - `scripts/testbed_reset.py`: Documents deterministic state reset procedures; fails closed on `--execute`.
  - `scripts/testbed_health.py`: Documents bounded health-check endpoints and expected responses; fails closed on `--execute`.
- **Safety Documentation (`docs/PHASE_8E2B_OFFLINE_HARNESS.md`):**
  - Documented network architecture, loopback port decisions, image-tag limitations, state reset procedures, allowlisting invariants, unverified items, and supervisor approval gates.
- **Preflight Statistical Protocol Terminology Correction:**
  - Corrected terminology in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` and `docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md`: Clopper-Pearson is exact binomial; Wilson score is score-based inversion.
- **Verification & Test Suite Expansion:**
  - Added 19 unit tests in `tests/test_testbed_harness.py` covering valid parsing, tamper detection (`0.0.0.0` ports, missing `internal: true`, `privileged: true`, Docker socket mounts, restart policies, `:latest` tags), allowlist scope checks, and execution guards.
  - Total test count expanded from 351 to 370 tests (all passing). Zero database files created.

## Completed in Phase 8E.2A.2 — Statistical Review Corrections & Evidence Traceability

- **Statistical Review Corrections & Evidence Traceability (`docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md`):**
  - **Audit of Previous Claims (Table 1):** Audited 12 methodological claims, classifying each as Retained with Justification, Corrected, Marked Unverified, or Deferred until Implementation.
  - **Task 1 — Statistical Power Claim Traceability:** Formally classified prior numerical power bounds ($80\%$ at $\Delta \ge 0.28\text{--}0.30$, and power $< 0.40$ at $n_{\text{disc}} \le 8$) as unverified pseudo-precision. Replaced with exact qualitative formulation: McNemar's power depends strictly on the observed discordant pair total ($n_{\text{disc}} = b + c$), which cannot be assumed a priori. Mandated explicit rule: failure to reject $H_0$ ($p \ge 0.05$) under small-sample constraints does not prove equivalence.
  - **Task 2 — Confidence Interval Formulations:** Corrected earlier statistical recommendation regarding F1. Proved that exact Wilson Score / Clopper-Pearson intervals are valid only for single binomial proportions (Recall, FPR, Abstention Rate), and are methodologically invalid for F1 (a non-linear harmonic mean of two proportions). Established reporting strategy: empirical point estimate of F1 reported alongside constituent Wilson intervals, with optional case-resampled Percentile Bootstrap intervals ($B = 2{,}000$). Paired Percentile Bootstrap specified for comparative differences.
  - **Task 3 — Threshold & Calibration Feasibility:** Inspected `aegiscore/orchestration.py:370` and `aegiscore/specialist_roles.py:653`. Verified that `UncertaintyAssessment` outputs discrete states and boolean `abstention_recommended`, with `confidence_is_calibrated: Literal[False] = False`. Confirmed that no continuous score or threshold parameter $\theta$ exists in the state machine today. Formally deferred numerical threshold grid ($\theta \in \{0.50, 0.70, 0.85\}$) as a future feature conditional on continuous scoring. Maintained ECE/Brier as future-only and labeled $N > 100$ sample size as a literature heuristic.
  - **Task 4 — Metric Feasibility Terminology (Table 2):** Restructured metric feasibility into three rigorous operational categories: Category 1 (Contract-Level Computable: Abstention Rate, Coverage, VFR, Tool Invocations), Category 2 (Benchmark Measurable: Precision, Recall, F1, FPR, Selective Risk, Severity Kappa, Latency, Token Usage, Ablation Comparisons), and Category 3 (Not Currently Supported: Brier Score, ECE).
  - **Task 5 — Repeated-Trial Guarantees:** Audited unit test assertions (SCEN-MA-16 in `tests/test_specialist_roles.py` and `tests/test_generation.py`). Verified that dataclass equality (`assert finding1 == finding2`) is tested on static fixtures. Established that Python fakes are pure functions with zero runtime variance. Confirmed that repeated runs ($K=3$) do not inflate sample size beyond canonical loci ($N \approx 36$).
  - **Targeted Protocol Corrections:** Updated `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§8.2, §8.3, §13 Item 3).
  - **Decision:** Conditional GO for offline testbed configuration files only (Phase 8E.2B); HOLD on container startup, benchmark runs, and LLM integration.

- **Statistical Claims & Evaluation Feasibility Review (`docs/PHASE_8E2A1_STATISTICAL_REVIEW.md`):**
  - **Executive Summary:** Delivered evidence-based review of statistical claims and practical feasibility before supervisor sign-off.
  - **Statistical Claims Audit:** Audited McNemar's test power constraints under high concordance scenarios, demonstrating power collapse when discordant pairs $n_{\text{disc}} \le 8$. Addressed BCa bootstrap degeneracy on small binary samples and specified exact Clopper-Pearson / Wilson score intervals for single proportions and Percentile Bootstrap for difference metrics.
  - **Validation/Test Feasibility:** Audited the $N_{\text{val}} = 10$ validation split on Juice Shop. Demonstrated that continuous threshold tuning on 10 cases produces severe overfitting (1 case shift = 20% change in sensitivity/specificity). Mandated discrete 3-point grid ($\theta \in \{0.50, 0.70, 0.85\}$). Identified structural pre-requisite gap for ECE (current system outputs discrete states, not continuous probabilities).
  - **Unit of Analysis & Definitional Hierarchy:** Formalized 5-tier definitional hierarchy: Target Environment -> Application Architecture -> Canonical Vulnerability Locus (Primary Unit of Analysis, $N \approx 36$) -> Test Execution Episode -> Finding / Alert Record. Reaffirmed that repeated trials ($K=3$) of deterministic fakes produce identical outputs and do not measure LLM variance.
  - **Metric-to-Implementation Feasibility Matrix (Table 2):** Classified all evaluation metrics into Tier 1 (Supported by deterministic contracts today: Abstention Rate, Coverage, VFR, HTTP tool-call counts), Tier 2 (Supported after LLM harness engineering: Precision, Recall, F1, FPR, Selective Risk, Severity Kappa, Latency, Token counts), and Tier 3 (Exploratory / Aspirational: Brier Score, ECE).
  - **Citation & Evidence Audit:** Documented precise verification boundary: deterministic contracts verify structural excerpt presence in retrieved chunks; semantic entailment verification remains an open research problem.
  - **Prioritized Protocol Corrections:** Implemented 4 concrete corrections in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (exploratory McNemar framing, Tier 3 calibration classification, academic proof-of-concept dataset framing, discrete validation threshold grid).
  - **Supervisor Decision Questions:** Formulated 4 focused decisions on statistical framing, calibration metric status, discrete threshold selection, and compute constraints.
  - **GO / HOLD Recommendation:** Conditional GO for offline evaluation harness engineering (Phase 8E.2B); HOLD on benchmark container launch and LLM provider integration pending supervisor sign-off.

## Completed in Phase 8E.2A — Evaluation Protocol Consistency Audit

- **Evaluation Protocol Consistency Audit (`docs/PHASE_8E2A_PROTOCOL_AUDIT.md`):**
  - **Executive Findings:** Documented core findings including implementation vs. capability disconnect (reiterating that 351 tests verify deterministic contracts, not LLM performance), sample size reality ($N \approx 36$ suitable for exploratory study but underpowered for confirmatory tests), partitioning domain shift, unit of analysis disambiguation, dual abstention accounting, and ECE binning constraints.
  - **RQ-by-RQ Feasibility Matrix:** Mapped RQ1–RQ6 and H1–H6 against IV, DV, Unit of Analysis, comparison condition, ground-truth requirement, confounders, and current vs. future testability.
  - **Dataset & Unit-of-Analysis Disambiguation:** Disambiguated vulnerability instances, individual test cases, repeated runs ($K=3$), scanner alerts, and unique findings. Formalized repeated run aggregation via majority consensus vote to prevent pseudo-replication.
  - **Leakage & Partitioning Audit:** Audited prompt leakage, corpus leakage, cross-split near-duplicate leakage, cross-benchmark domain shift, and ground-truth API accessibility. Mandated within-benchmark stratified partitioning for Juice Shop (40% validation / 60% test at controller level) and parallel independent evaluation for DVWA.
  - **Metric Formulations & Denominators:** Audited all metrics (Precision, Recall, F1, FPR, Coverage, Selective Risk, Abstention Rate, VFR, Severity Kappa, Brier, ECE). Refined ECE to $M=3$ quantile bins with bootstrap error bars.
  - **Baseline Fairness Checklist:** Audited fairness across B1 (ZAP), B2 (MA w/o abstention), B3 (Single-Agent), and P (Proposed), enforcing pre-mapped OpenAPI routes, identical 50-request budgets, 120s timeouts, clean DB resets, fixed base model, $\tau=0.0$, and seed=42.
  - **Threats to Validity Audit:** Evaluated construct, internal, external, and conclusion validity.
  - **Protocol Refinements Applied:** Updated `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` to resolve concrete ambiguities in Section 5.1, Section 8.3, and Section 13 Item 3.
  - **Go/No-Go Checklist for Phase 8E.2B:** Established gating conditions; holding Phase 8E.2B benchmark setup pending supervisor decisions.

## Completed in Phase 8E.1 — Thesis Evaluation Protocol & Benchmark Design

- **Design-Only Thesis Evaluation Protocol Specification (`docs/PHASE_8E1_EVALUATION_PROTOCOL.md`):**
  - **Implementation Status vs. Proposed Research Capabilities:** Mapped implemented deterministic contracts (351 passing tests) vs. stubs/fakes vs. future capabilities. Explicitly disclaimed deterministic fakes as evidence of LLM capability.
  - **Research Questions & Hypotheses (RQ1–RQ6, H1–H6):** Defined precise research questions and hypotheses addressing false-positive reduction via abstention, recall impact across vulnerability classes, post-hoc confidence calibration, deterministic citation grounding, RAG/role ablations, and operational latency/token overhead. Defined independent, dependent, and controlled variables and limitations for each.
  - **Benchmark Evaluation & Selection:** Evaluated OWASP Juice Shop, DVWA, and OWASP WebGoat across 8 criteria. Recommended OWASP Juice Shop (v15.0.0 pinned container) as Primary Benchmark for architectural realism and API challenge verification. Recommended DVWA (v1.10 pinned container) as Secondary Benchmark for source-level ground-truth clarity and negative-control calibration (Impossible tier). Documented explicit trade-offs.
  - **Ground-Truth Annotation Protocol:** Defined canonical matching triple `(URI, Param, CWE)`. Specified strict rules for TP, FP, FN, and explicit TN. Enforced rule that **abstentions are never counted as true negatives**. Defined duplicate finding clustering, CVSS severity agreement scoring ($\kappa_w$), candidate vs. confirmed finding boundaries, and anti-leakage protections (excluding benchmark writeups from RAG corpus and prompts).
  - **Baselines & Ablation Matrix:** Defined B1 (OWASP ZAP v2.15.0), B2 (Multi-Agent without abstention), B3 (Single-Agent+RAG), P (Proposed full system), A1 (No-RAG ablation), and A2 (No-Reviewer ablation). Specified controlled parameters and labeled future experimental conditions.
  - **Metrics & Calculation Rules:** Formulated Precision, Recall, F1, False-Positive Rate ($FPR$), Abstention Rate, Selective Risk ($R(\Phi)$), Selective Coverage ($\Phi$), Verified Finding Rate, and Quadratic Weighted Kappa ($\kappa_w$). Documented Brier score and Expected Calibration Error ($ECE$) formulation with explicit small-sample bias warnings.
  - **Statistical Analysis Plan:** Paired experimental design using McNemar's test for binary detection outcomes, Wilcoxon signed-rank test for continuous metrics, and 95% BCa bootstrap confidence intervals. Documented statistical power limitations for $N \approx 36$ cases.
  - **Reproducibility & Safety Requirements:** Defined pinned container image digests, seed=42 / temp=0.0 LLM settings, target database reset protocol, and structured JSONL audit logs. Established safety checklist enforcing RFC1918/loopback allowlist, non-destructive payloads, request/time ceilings, and emergency stop circuit breaker.
  - **16 Pre-Registered Evaluation Scenarios:** Created detailed evaluation scenario matrix spanning Reflected XSS, Stored XSS, Non-Destructive SQLi, and Broken Access Control (horizontal IDOR, vertical privilege escalation, path traversal) balanced across positive and negative controls.
  - **Supervisor Decision Gates & Roadmap:** Documented 5 open decisions requiring supervisor approval (LLM model selection, dataset size, validation/test split, human review panel, ablation priorities) and a 5-stage implementation roadmap (Phases 8E.2–8E.6).


- **SCEN-MA-07 Citation Excerpt Integrity Implementation:**
  - Implemented `validate_citation_excerpt` in `aegiscore/claim_validation.py`:
    - Resolves target chunk from `SourceChunk`, `RetrievalResult`, `EvidenceRetrievalResult`, `EvidenceBundle`, or mapping.
    - Rejects chunk_id not present in retrieval evidence (`CitationGroundingError`).
    - Rejects source_id mismatch against chunk provenance (`CitationGroundingError`).
    - Verifies verbatim substring presence of `cited_excerpt` in `chunk.content`.
    - Does NOT search unrelated chunks to make an invalid citation pass.
    - Absent (`None`) or empty (`""`) excerpts pass cleanly without breaking existing citations.
    - Preserves Unicode text exactly without case-folding, lossy accent stripping, or normalization differences.
    - Enforces exact whitespace and newline boundaries without silent normalization or whitespace collapsing.
    - Preserves structural provenance separate from semantic entailment: `factual_support` remains strictly `not_evaluated`.
  - Integrated with claim-validation gate:
    - Updated `evaluate_individual_claim`, `validate_claims_and_evidence`, and `validate_and_gate_generation` to accept optional `claim_citations`.
    - Integrated with `OrchestrationStateMachine.record_specialist_analysis` in `aegiscore/orchestration.py`: validates all finding citation records against `self._evidence_bundle` fail-closed.
    - Updated `ClaimCitationRecord` contract in `aegiscore/orchestration.py` to allow verbatim multiline excerpts while rejecting empty strings, non-strings, and null bytes (`\x00`).
    - Updated `DeterministicVulnerabilityAnalystFake` in `aegiscore/specialist_roles.py` to preserve verbatim chunk content slices.
  - Added 10 regression tests in `tests/test_claim_validation.py` covering exact valid excerpt, excerpt from another chunk, absent/hallucinated excerpt, mismatched source ID, mismatched chunk ID, empty/missing excerpt, Unicode boundaries, newline boundaries, `factual_support` invariant, and claim validation gate integration.
  - Resolved `test_scen_ma_07_hallucinated_citation_excerpt_rejected` in `tests/test_multi_agent_workflow.py` (0 skipped).

- **SCEN-MA-14 Source Manifest Failure Integration:**
  - Created `tests/test_manifest_integrity.py` with 14 isolated integration tests using temporary environments (`tmp_path`):
    - Valid temporary manifest accepted under standard contract.
    - Tampered `raw_sha256` in manifest entry rejected fail-closed (`SourceReviewConsistencyError`).
    - Tampered `normalized_sha256` in manifest entry rejected fail-closed (`SourceReviewConsistencyError`).
    - Tampered source file content on disk rejected (`SourceReviewConsistencyError`).
    - Tampered manifest metadata against persisted SQLite ledger rejected (`SourceReviewConsistencyError`).
    - Missing manifest file produces documented typed error (`SourceReviewError`).
    - Manifest deleted after initialization fails closed (`SourceReviewConsistencyError`).
    - Malformed JSON manifest rejected clearly (`SourceReviewConsistencyError`).
    - Unsupported format string or unsupported schema version rejected (`SourceReviewConsistencyError`).
    - Duplicate source IDs in manifest entries rejected (`SourceReviewConsistencyError`).
    - Manifest failure never silently falls back to unverified source records; `retrieve_approved_evidence` raises `RagRuntimeError`.
    - Manifest failure leaves SQLite review history and approval state unmodified.
    - Reliable temporary file cleanup within `tmp_path`.
    - Documented architectural baseline and boundary limitations.
  - Resolved `test_scen_ma_14_corrupted_manifest_fails_closed_integration` in `tests/test_multi_agent_workflow.py` (0 skipped).

### Phase 8D.4 — SCEN-MA Scenario Mapping (All 16 Scenarios Passing)

| Scenario | Status | Test(s) | Notes |
|---|---|---|---|
| SCEN-MA-01 | ✅ PASS | `test_scen_ma_01_*` | External URL and public IP rejected at `AssessmentRequest` construction |
| SCEN-MA-02 | ✅ PASS | `test_scen_ma_02_empty_corpus_gating` | Empty bundle → auto-ABSTAINED at RETRIEVAL_COMPLETED |
| SCEN-MA-03 | ✅ PASS | `test_scen_ma_03_full_happy_path_workflow`, `test_xss_analyst_fake_*` | Full forward workflow to COMPLETED |
| SCEN-MA-04 | ✅ PASS | `test_scen_ma_04_adversarial_benign_defense_to_abstained` | Sanitization in evidence → CONFLICT_MARKER → ABSTAINED |
| SCEN-MA-05 | ✅ PASS | `test_scen_ma_05_citation_chunk_mismatch` | Ghost chunk_id rejected by `EvidenceBundle.__post_init__` |
| SCEN-MA-06 | ✅ PASS | `test_scen_ma_06_citation_source_id_spoof` | Spoofed source_id rejected by `EvidenceBundle` provenance check |
| SCEN-MA-07 | ✅ PASS | `test_scen_ma_07_hallucinated_citation_excerpt_rejected`, `test_citation_excerpt_*` | Verbatim excerpt substring check; hallucinated excerpt rejected fail-closed |
| SCEN-MA-08 | ✅ PASS | `test_scen_ma_08_explicit_conflict_marker_detection` | `CONFLICT_MARKER:` in notes → `ConflictAssessment.conflicts_detected=True` → ABSTAINED |
| SCEN-MA-09 | ✅ PASS | `test_uncertainty_assessor_detects_epistemic_keywords` | Epistemic keywords → `is_sufficient=False`, `abstention_recommended=True` |
| SCEN-MA-10 | ✅ PASS | `test_scen_ma_10_unsupported_severity_gating` (via MA-10 variant) | CRITICAL severity with `proposed_claims=()` raises `OrchestrationContractError` |
| SCEN-MA-11 | ✅ PASS | `test_scen_ma_11_indirect_prompt_injection_defense` | Adversarial instructions in evidence are inert passive data |
| SCEN-MA-12 | ✅ PASS | `test_scen_ma_12_active_testing_without_permit` | `active_guarded` without `permit_id` raises `OrchestrationContractError` |
| SCEN-MA-13 | ✅ PASS | `test_scen_ma_13_*` | Stage bypass, illegal transition, terminal state protection |
| SCEN-MA-14 | ✅ PASS | `test_scen_ma_14_corrupted_manifest_fails_closed_integration`, `test_manifest_integrity.py` | Corrupted manifest hash rejected fail-closed before evidence reaches pipeline |
| SCEN-MA-15 | ✅ PASS | `test_scen_ma_15_*` | Invalid finding rejected, null-finding propagates error, explicit `fail()` terminal |
| SCEN-MA-16 | ✅ PASS | `test_scen_ma_16_reproducible_full_workflow_audit_trace`, `test_identical_inputs_yield_identical_outputs` | Identical inputs → identical findings and execution records |

### Phase 8D.4 Verification

All verification commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache writes disabled.

| Command | Exit Code | Actual Result |
|---|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_claim_validation.py` | 0 | **28 passed in 0.31s** |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_manifest_integrity.py` | 0 | **14 passed in 0.60s** |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_specialist_roles.py tests/test_multi_agent_workflow.py` | 0 | **49 passed in 0.38s** (0 skipped) |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (full suite) | 0 | **351 passed in 6.72s** (0 skipped, 0 failed) |
| `git diff --check` | 0 | Clean; no whitespace errors. |
| `git diff -- docs/source-review-manifest.json` | 0 | Empty diff; manifest untouched. |
| Corpus inspection | 0 | 11 entries, all empty `review_events`, `approval_status=no_sources_approved`. |
| SQLite audit | 0 | Zero `.db`, `.sqlite`, or `.sqlite3` files exist. |

### Phase 8D.4 Corpus and Environment Integrity

- Manifest: 11 entries, all `candidate`, all `review_events: []`, `approval_status=no_sources_approved`.
- No SQLite database files created or modified.
- `pyproject.toml` and `uv.lock` unchanged; zero new external dependencies.
- All pre-existing worktree modifications and untracked files preserved unchanged.
- No git commit was made.

### Phase 8D.3 Known Limitations

1. **SCEN-MA-07 (Hallucinated Citation Excerpt):** `cited_excerpt` in `ClaimCitationRecord` is an informational annotation. No validator checks it against actual chunk content. Adding excerpt-level substring validation requires a design change in `claim_validation.py` and is deferred.
2. **SCEN-MA-14 (Corrupted Manifest):** SHA-256 manifest integrity enforcement lives in `source_review.py` at corpus-load time. Testing it end-to-end requires an integration test against the manifest loader / SQLite mirror, which is outside Phase 8D.3 scope.
3. **Review notes newlines:** `OrchestrationStateMachine.record_evidence_review()` uses `_nonempty_text()` which rejects `\n`. Multi-line review notes must be normalized (replace `\n` → space) before passing to the state machine. This is a friction point between the reviewer fake's output and the state machine contract.

- Implemented `aegiscore/orchestration.py` (offline-only, no external dependencies):
  - **Exception Hierarchy:** `OrchestrationError`, `OrchestrationContractError`, `ScopeViolationError`, `InvalidTransitionError`, `TerminalStateError`, `StageBypassError`.
  - **Scope Validation:** `_validate_lab_target_url()` enforcing loopback (127.x, `::1`, `localhost`), RFC1918 private lab (`10.x`, `172.16-31.x`, `192.168.x`), and `*.local`/`*.internal` lab domains. Rejects embedded credentials, URL fragments, forbidden schemes, and unapproved public hosts.
  - **Data Contracts (all frozen dataclasses):**
    1. `AssessmentRequest` — authorized scope, vulnerability category, target lab URL, analysis mode (`passive_rag_only` | `active_guarded`). Requires explicit `permit_id` for active mode.
    2. `EvidenceBundle` — wraps `EvidenceRetrievalResult` chunks as passive untrusted data; validates citation provenance against actual chunk keys via `provenance.source_id`; enforces empty-bundle invariant for zero approved sources.
    3. `ClaimCitationRecord` — preserves claim→chunk provenance with `factual_support='not_evaluated'` invariant.
    4. `SpecialistFinding` — proposed finding (never confirmed); `is_confirmed=False` and `factual_support='not_evaluated'` are enforced.
    5. `UncertaintyAssessment` — sufficiency score bounded `[0.0, 1.0]`; `abstention_recommended=True` required when `is_sufficient=False`; `confidence_is_calibrated=False` invariant.
    6. `ConflictAssessment` — distinguishes explicit conflict markers from un-evaluated semantic contradictions via `semantic_contradiction_detected='not_evaluated'`.
    7. `AgentExecutionRecord` — execution audit fields with credential/token pattern detection in `output_summary`.
    8. `FinalGatedAssessmentResult` — enforces that `PROCEED` requires `SUFFICIENT_EVIDENCE` classification; `ABSTAIN`/`FLAG_FOR_REVIEW` require non-empty `abstention_reason`.
  - **Orchestration State Machine (`OrchestrationStateMachine`):**
    - States: `REQUEST_RECEIVED → REQUEST_VALIDATED → RETRIEVAL_COMPLETED → SPECIALIST_ANALYSIS_COMPLETED → EVIDENCE_REVIEW_COMPLETED → UNCERTAINTY_ASSESSED → VALIDATION_COMPLETED → {COMPLETED | ABSTAINED | FLAGGED_FOR_REVIEW | FAILED}`.
    - Explicit `PERMITTED_TRANSITIONS` map enforcing forward-only progression.
    - Terminal states (`COMPLETED`, `ABSTAINED`, `FLAGGED_FOR_REVIEW`, `FAILED`) cannot be re-opened.
    - Automatic fail-closed abstention from `RETRIEVAL_COMPLETED` to `ABSTAINED` when `approved_source_count == 0`.
    - Automatic fast-track to `FLAGGED_FOR_REVIEW` or `ABSTAINED` when conflict or uncertainty assessments mandate it.
    - All workflow methods (`validate_request`, `record_retrieval`, `record_specialist_analysis`, `record_evidence_review`, `record_uncertainty_and_conflict`, `record_validation`, `finalize_result`, `fail`) check `is_terminal` first and raise `TerminalStateError` if already terminal.
    - Unexpected runtime errors propagate directly; never caught or masked as abstentions.
    - `EvidenceBundle.from_retrieval_result()` factory for integration with existing `EvidenceRetrievalResult` bundles.
- Created `tests/test_orchestration_contracts.py` — 10 tests verifying all data contract invariants.
- Created `tests/test_orchestration_state_machine.py` — 11 tests covering end-to-end valid workflow, illegal transitions, terminal state protection, stage bypass prevention, empty evidence abstention, invalid citation gating, scope violation, error propagation, repeated-stage protection, adversarial evidence inertness, and existing component compatibility.
- No new runtime LLM agent logic, external API connections, database files, or framework dependencies were added.

### Phase 8D.2 Verification

All verification commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache writes disabled.

| Command | Exit Code | Actual Result |
|---|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_orchestration_contracts.py tests/test_orchestration_state_machine.py` | 0 | **25 passed in 0.19s** |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (full suite) | 0 | **278 passed in 5.35s** |
| `git diff --check` | 0 | Clean; no whitespace errors. |
| `git diff -- docs/source-review-manifest.json` | 0 | Empty diff; manifest untouched. |
| Corpus inspection | 0 | 11 entries, all empty `review_events`, `approval_status=no_sources_approved`. |
| SQLite audit | 0 | Zero `.db`, `.sqlite`, or `.sqlite3` files exist. |

### Phase 8D.2 Corpus and Environment Integrity

- Manifest: 11 entries, all `candidate`, all `review_events: []`, `approval_status=no_sources_approved`.
- No SQLite database files created or modified.
- `pyproject.toml` and `uv.lock` unchanged; zero new external dependencies.
- All 26 `REQ-*` identifiers remain unchanged. No git commit was made.

- Authored comprehensive, implementation-ready architecture specification `docs/PHASE_8D1_MULTI_AGENT_DESIGN.md`:
  - Defined purpose, explicit non-goals (no runtime orchestration, no external LLM APIs, no LangGraph/CrewAI, no consensus-as-truth fallacy, no live scanning, no auto-approval of sources).
  - Verified existing architectural baseline: `MOD-01` (Safety), `MOD-04` (Guarded Execution), `MOD-05` (Offline RAG Runtime & Source Review), Provider-Neutral Generation (`aegiscore/generation.py`), and Deterministic Claim Validation / Response Gating (`aegiscore/claim_validation.py`).
  - Evaluated 6 candidate roles and recommended the minimum justified set:
    1. Orchestrator (Deterministic Python State Machine)
    2. Retrieval Specialist (Deterministic Query Adapter wrapping `retrieve_approved_evidence()`)
    3. Vulnerability Analysis Specialist (Profile-Specific Prompts on Shared Base Model: XSS, SQLi, BAC)
    4. Evidence Review Specialist (Adversarial Challenge Prompt on Shared Base Model)
    5. Uncertainty & Conflict Assessor (Hybrid: Deterministic Aggregator + Signal Extractor)
    6. Final Response Gate (Deterministic Code in `aegiscore/claim_validation.py`)
  - Detailed modality trade-off analysis comparing separate LLMs, shared-model role prompts, and deterministic code across latency, cost, reproducibility, attack surface, and research validity.
  - Clearly separated LLM analysis from deterministic policy enforcement, provenance validation, semantic verification (non-claim), and human adjudication.
  - Specified end-to-end workflow with complete Mermaid architecture diagram and 8-step execution trace from request ingestion to immutable audit trail.
  - Defined typed, provider-neutral data contracts: `AssessmentRequest`, `EvidenceBundle`, `SpecialistFinding`, `ClaimCitationRecord`, `UncertaintyAssessment`, `ConflictAssessment`, `AgentExecutionRecord`, and `FinalGatedAssessmentResult`.
  - Formulated explicit uncertainty taxonomy (retrieval uncertainty, epistemic uncertainty, conflicting evidence, execution failure) and decision matrix, rejecting uncalibrated confidence scores and consensus-as-truth claims.
  - Mapped threat boundaries and safety controls to `THR-01` through `THR-20`, treating retrieved evidence strictly as untrusted data (`<UNTRUSTED_EVIDENCE>` tags).
  - Designed thesis evaluation methodology with 4 comparative conditions (B1 Baseline Scanner, B2 Single-Agent, B3 Multi-Agent without abstention, P Proposed System), defining formal metrics (Precision, Recall, F1, FPR, Abstention Rate, Verified Finding Rate, Brier score, ECE).
  - Specified 16 comprehensive test scenarios (`SCEN-MA-01` to `SCEN-MA-16`) covering scope enforcement, empty corpus gating, citation provenance checks, adversarial defense, prompt injection defense, and audit reproducibility.
  - Outlined open research questions requiring supervisor review and a phased implementation roadmap (Phase 8D.2 Typed Contracts, Phase 8D.3 Role Prompts & Test Scenarios, Phase 8E Thesis Evaluation).
- Strictly design-only: no runtime orchestration code, dependencies, or LLM integrations were added.

### Phase 8D.1 Verification

All verification commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache writes disabled.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 253 passed in 5.16s. |
| `git diff --check` | 0; no whitespace or formatting errors. |
| `git diff -- docs/source-review-manifest.json` | 0; empty diff (manifest untouched). |

### Phase 8D.1 Corpus and Environment Integrity

- Manifest check confirms 11 entries, all `candidate`, all `review_events` empty, and `approval_status=no_sources_approved`.
- No SQLite database files exist in the repository tree.
- `pyproject.toml` and `uv.lock` are unchanged; zero new dependencies, external APIs, or network calls.
- All 26 `REQ-*` identifiers remain unchanged. No git commit was made.


## Completed in Phase 8C.3 — Deterministic Evidence and Claim Validation Implementation

- Implemented `aegiscore/claim_validation.py` realizing the specification from `docs/PHASE_8C2_DESIGN.md`:
  - `EvidenceSufficiencyClassification` (`NO_APPROVED_EVIDENCE`, `SUFFICIENT_EVIDENCE`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`, `UNCERTAIN_INDETERMINATE`).
  - Structured validation result types: `ClaimValidationResult` and `GatedGenerationResult`, preserving `factual_support="not_evaluated"`.
  - Claim-level citation grounding and rule-based sufficiency evaluation via `evaluate_individual_claim()` and `is_claim_supported_by_chunks()`.
  - Conflict detection via `has_explicit_conflicts()` checking `ConflictRule` string pairs, opposing directives, and conflicting scope tags across distinct chunks.
  - Global evidence insufficiency checking via `is_globally_insufficient()`.
  - Comprehensive gating pipeline in `validate_and_gate_generation()` and structured analysis via `validate_claims_and_evidence()`.
  - Seamless integration: `generate_grounded_response()` in `aegiscore/generation.py` delegates to `validate_and_gate_generation()` maintaining 100% backward compatibility.
- Precedence Decision Enforced:
  - Input request contract validation occurs first; malformed inputs raise `GenerationContractError` immediately and are never silently converted into or masked by an abstention.
  - Operational gating follows `NO_APPROVED_EVIDENCE > CONFLICTING_EVIDENCE > INSUFFICIENT_EVIDENCE > SUFFICIENT_EVIDENCE`.
  - Fail-closed response gating: if any claim fails sufficiency in a multi-claim response, the entire response abstains with `insufficient_evidence` (no partial ungrounded answers).
  - Unhandled implementation defects (such as injected `RuntimeError`s) propagate directly and are never caught or converted to abstentions.
- Added `tests/test_claim_validation.py` containing 18 comprehensive unit and integration tests covering all 14 scenarios from `docs/PHASE_8C2_DESIGN.md`, input precondition precedence, detailed structured evaluation records, scope limitations, and end-to-end integration from persistent registry to retrieval to validation gating.

### Phase 8C.3 Verification

All commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache writes disabled.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_claim_validation.py` | 0; 18 passed in 0.21s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_claim_validation.py tests/test_generation.py tests/test_rag.py tests/test_rag_runtime.py tests/test_persistent_source_review.py tests/test_source_review_cli.py tests/test_safety_policy.py tests/test_guarded_execution.py` | 0; 222 passed in 3.58s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 253 passed in 5.23s. |

### Phase 8C.3 Corpus and Environment Integrity

- `git diff -- docs/source-review-manifest.json` is empty.
- Manifest check confirms 11 entries, all `candidate`, all `review_events` empty, and `approval_status=no_sources_approved`.
- No SQLite database files exist in the repository tree.
- `pyproject.toml` and `uv.lock` are unchanged; no external packages, dependencies, API keys, or network calls were added.
- All 26 `REQ-*` identifiers remain unchanged; `HEAD` remains `263f367ce96daddf52e5bf79e9504768049dcf7d`. No git commit was made.

## Completed in Phase 8C.2 — Evidence Sufficiency and Claim Validation Design

- Created `docs/PHASE_8C2_DESIGN.md` as the design-only specification for claim-level validation and evidence sufficiency evaluation over `EvidenceRetrievalResult` and `GenerationResult`.
- Key specifications defined:
  - Clear architectural boundary between citation membership validation (structural/lexical) and semantic factual support (`factual_support="not_evaluated"` preserved).
  - Explicit 5-state evidence sufficiency model: `NO_APPROVED_EVIDENCE`, `SUFFICIENT_EVIDENCE`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`, and `UNCERTAIN_INDETERMINATE`, with strict fail-closed precedence.
  - Claim-level validation decision rules covering all 9 required claim conditions (valid citations, missing citations, unretrieved chunk IDs, source ID mismatches, topic relevance without claim support, extrapolation beyond source scope, mixed support fail-closed policy, shared chunk citations, and ambiguous evidence).
  - Conflict taxonomy and deterministic abstention policy distinguishing explicit keyword conflicts, scope/version differences, apparent reconcilable disputes, and undetected semantic conflicts.
  - Formal decision pseudocode mapping input evidence to gated responses without masking defects as ordinary abstentions.
  - 14 concrete test scenarios grounded in defensive web application vulnerability assessment (e.g. reflected XSS context-aware encoding, SQL injection defenses).
  - Preserved all 26 existing `REQ-*` identifiers with complete traceability; proposed no new requirement IDs.
  - Documented open research questions (`OPEN-RES-01` through `OPEN-RES-04`) and proposed an implementation and evaluation plan for Phase 8C.3.
- Design-only boundary: No runtime code or tests were modified; no network calls, API keys, or external LLM providers were added; the 11 manifest entries remain unapproved candidates with empty review histories.

## Completed in Phase 8C.1 — Provider-Neutral Generation Contract and Deterministic Fake

- Added `aegiscore/generation.py` containing provider-neutral generation request and response contracts (`GenerationRequest`, `GenerationResult`, `GeneratedClaim`), custom error hierarchy (`GenerationError`, `GenerationContractError`, `CitationGroundingError`, `GenerationResponseValidationError`), generator protocol `Generator`, coordination function `generate_grounded_response`, output validator `validate_generation_result`, and deterministic offline fake `DeterministicFakeGenerator`.
- Invariants enforced:
  - Generation consumes `EvidenceRetrievalResult` directly or via `GenerationRequest(evidence=...)`, strictly maintaining the approved-source retrieval boundary.
  - If evidence status is `no_approved_evidence`, generation short-circuits immediately without invoking the generator seam, preventing hallucinations or prior-knowledge bias.
  - Answers require at least one claim, and each claim must cite one or more valid `CitationReference`s that belong to the supplied retrieval result hits with matching source and chunk IDs.
  - Abstentions require empty claims and an explicit reason from `{"no_approved_sources", "no_retrieved_chunks", "insufficient_evidence", "conflicting_evidence"}`.
  - `factual_support` is explicitly `not_evaluated` on both `GeneratedClaim` and `GenerationResult`; citation membership is not treated as proof of factual support.
  - Retrieved text is treated strictly as passive, untrusted data; prompt-injection attempts cannot change safety policy, grant permits, or dispatch operations.
  - Conflicting evidence is detected via explicit, documented `ConflictRule` pairs or conflict scope tags across distinct chunks; the current retrieval contract does not pretend to perform automated semantic contradiction detection.
  - Unexpected implementation defects (such as injected `RuntimeError`s) propagate directly and are never silently converted into ordinary abstentions.
- Added `tests/test_generation.py` containing 17 comprehensive unit and integration tests covering repeatability, citation preservation, empty-evidence short-circuiting, malformed input and response validation, citation membership verification, prompt injection isolation, explicit conflict handling, insufficiency detection, defect propagation, and end-to-end integration from persistent registry to retrieval to generation.

### Phase 8C.1 Verification

All commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache writes disabled.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_generation.py` | 0; 17 passed in 0.25s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_generation.py tests/test_rag.py tests/test_rag_runtime.py tests/test_persistent_source_review.py tests/test_source_review_cli.py tests/test_safety_policy.py tests/test_guarded_execution.py` | 0; 204 passed in 3.96s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 235 passed in 5.96s. |

### Phase 8C.1 Corpus and Environment Integrity

- `git diff -- docs/source-review-manifest.json` is empty.
- Manifest check confirms 11 entries, all `candidate`, all `review_events` empty, and `approval_status=no_sources_approved`.
- No SQLite database files exist in the repository tree.
- `pyproject.toml` and `uv.lock` are unchanged; no external packages, dependencies, API keys, or network calls were added.
- All 26 `REQ-*` identifiers remain unchanged; `HEAD` remains `263f367ce96daddf52e5bf79e9504768049dcf7d`. No git commit was made.


- Hardened `scripts/review_source_corpus.py` decision templates to be non-approving by default (empty decisions, blank identities/timestamps, and all checklist items set to `false`).
- Added pre-confirmation disk hash verification: before prompting for interactive confirmation or writing to persistent storage, the CLI reads the source entry from the manifest, verifies raw and normalized source files against recorded hashes (`_manifest_ingestion`), and validates that the expected content hash matches the verified current disk hash.
- Completed strict payload and checklist key validation: payload keys and checklist keys must match required schemas exactly, rejecting unexpected/extra keys and unlisted fields. Decision values must be actual strings with exact value `"approve"` or `"reject"`.
- Added unit tests proving that generated templates cannot approve anything without completion, stale/mismatched hashes abort before prompting/writing, unexpected keys/types are rejected cleanly, non-interactive execution is blocked, and failure injection rolls back atomically without partial writes.
- Confirmed that the real corpus manifest remains strictly byte-identical to HEAD, all 11 sources remain candidates with empty review histories, and no real-corpus SQLite database has been created.
- Reviewer authentication and supervisor authorization remain clearly marked as unauthenticated labels/unresolved decisions.

### Historical Test-Count Reconciliation

- The preserved `263f367` release commit's project status records a 172-test Phase 7E run. Collecting tests from an archive of that commit also exited 0 and reported **172 tests collected**. The repository does not preserve the original raw pytest log.
- `git fsck` also found six unreachable source-tree snapshots from Phases 6A–7D. Their archived test collections were 113, 134, 153, 157, 160, and 160 tests (the Phase 7D collection of 160 appears in two snapshots); none is a Phase 8B snapshot. These collection counts do not establish historical pass counts.
- The previously reported totals **185, 193, 196, 198, and 199 are NOT VERIFIED**. Before this audit update, the working status recorded 185 and 199, but neither has a preserved Phase 8B commit, source-tree snapshot, or raw pytest log. No matching prior run record for 193, 196, or 198 was found.
- Reachable Git history contains only the initial commit and `263f367`; the reflog has no later phase commits, and `git fsck` found no unreachable commits. The available source snapshots do not reconstruct the test-by-test changes between the reported Phase 8B totals, so additions, edits, renames, or removals in that interval remain unverified. This audit added focused coverage and removed or weakened no tests.

### Phase 8B.2.2 Verification

Commands ran from `S:\AegisCore` using the project-local Python, with bytecode and pytest cache writes disabled.

| Command | Exit code and actual output |
|---|---|
| Focused command, first attempt | 1; 55 passed, 1 failed in 4.00s. A misplaced missing-database assertion caused a `NameError`; it was moved into its original test. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_rag_runtime.py tests/test_persistent_source_review.py tests/test_source_review_cli.py` (final retry) | 0; 57 passed in 4.08s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 217 passed in 6.17s. |

The final checks found an empty `git diff -- docs/source-review-manifest.json`, 11/11 real-corpus sources still `candidate` with empty review histories and `approval_status=no_sources_approved`, and no SQLite/database files in the repository. `pyproject.toml` and `uv.lock` are unchanged. The 26 `REQ-*` identifiers match the preserved release snapshot; the current HEAD remains `263f367`. Tests used synthetic files and temporary manifests/databases; no network operation was added or used in this audit.

### Phase 8B.2.3 Read-Only Access Provenance Hardening

- Retrieval uses the supplied registry only to obtain its database, manifest, and repository paths. It opens a fresh registry through `PersistentSourceReviewRegistry.open_existing()` and selects approved chunks from that instance; the caller-supplied `_is_read_only` value no longer determines the retrieval connection mode. Missing or disappearing databases fail closed through the explicit read-only open path, which does not bootstrap them.
- Added regressions showing that a constructor-created registry with `_is_read_only=True` is not used directly, and that changing `_is_read_only` to `False` on an `open_existing()` registry still results in read-only retrieval connections that reject writes. Approved-source retrieval and writer workflow tests pass; expected registry errors retain their causes, while an injected `RuntimeError` propagates without being mislabeled.
- An initial focused run exited 1 with 57 passed and 1 failed because its error injection still patched the caller instance, which retrieval no longer uses. The injection was moved to the class method so the expected-error cause and unexpected-error propagation assertions exercise the actual fresh retrieval instance. The former direct-instance rejection test now asserts that explicit reopening is used and the caller instance is never used for selection.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_rag_runtime.py tests/test_persistent_source_review.py tests/test_source_review_cli.py` (final run) | 0; 58 passed in 4.81s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 218 passed in 6.54s. |

`git diff -- docs/source-review-manifest.json` was empty. The manifest contains 11 candidate sources, all with empty review histories and `approval_status=no_sources_approved`; no repository SQLite/database file was found. `pyproject.toml` and `uv.lock` have no diff, no network operation or network behavior was added, all 26 `REQ-*` identifiers match `HEAD`, and `HEAD` remains `263f367ce96daddf52e5bf79e9504768049dcf7d`. No commit was made. Phase 8C and Phase 9 have not started.

## Phase 8C design-only plan

- Created `docs/PHASE_8C_PLAN.md` as a provider-neutral design and verification plan for future evidence-grounded generation. The plan preserves the existing requirements and roadmap, proposes no new `REQ-*` identifiers, and explicitly separates reference membership from claim-level factual support.
- The worktree was already unclean at inspection (`HEAD` `263f367ce96daddf52e5bf79e9504768049dcf7d`); this plan is based on the inspected working-tree files. The recorded 58 focused / 218 full-suite result is not a test run from this planning task.
- Read-only verification during planning: `git diff -- docs/source-review-manifest.json` was empty; manifest inspection found 11 entries, all `candidate`, all review histories empty, and `approval_status=no_sources_approved`; a repository scan found no `.sqlite`, `.sqlite3`, or `.db` files.
- No runtime, requirements, dependency, network, corpus, or review-decision changes were made. No tests were run because this task changed documentation only. No commit was made. Provider egress remains unresolved and unapproved; Phase 8C implementation and Phase 9 have not started.

## Completed in Phase 7E

- Added `PersistentSourceReviewRegistry` to `aegiscore/source_review.py` using Python's standard-library SQLite. Version-2 storage records source revision metadata, a digest of the full non-review manifest entry, current/historical revision state, and ordered review events. The manifest revision digest includes raw and normalized hashes, paths, and other per-source provenance fields; only the mutable review projection (`review_state`, `review_events`, `retrieval_eligibility`) is excluded.
- Added explicit candidate registration, submission, and decision transitions for the exact current manifest revision. The selector rereads raw and normalized files, checks hashes and the manifest revision digest, verifies SQLite event replay plus entry/corpus-level manifest projections, and rebuilds chunks from the verified normalized file. Candidate rows remain excluded. Manifest-only decisions are rejected. `reconcile_manifest()` can restore the review projection only from valid database history and only while immutable provenance and file hashes still match.
- Added deterministic corpus summary reconciliation (`no_sources_approved`, `some_sources_approved`, `all_sources_approved`). Manifest/runtime disagreement fails closed. Writers compare current manifest bytes with the read snapshot before replacement, so a detected concurrent edit is not overwritten. Handled SQLite transaction errors roll back and restore manifest bytes; a process failure between the separate database and manifest writes can still leave a mismatch, which selection rejects.
- Reviewer and actor references are stored as unauthenticated caller-provided labels. A persisted decision is not proof of human identity, reviewer authority, source authenticity, license compliance, factual correctness, or tamper-proof audit. No database was initialized for the real corpus and no review event was written to the project manifest.
- Added `tests/test_persistent_source_review.py` with temporary SQLite/manifest fixtures. Synthetic approvals exist only in those disposable fixtures. Tests cover persistence/reload, current-revision approval, stale content/provenance, invalid transitions, candidate/manifest-only exclusion, mismatches and explicit reconciliation, malformed records/schema, rollback/retry, concurrent-manifest-change refusal, unauthenticated reviewer labels, and no-network/no-target-dispatch guards.
- Updated `docs/ARCHITECTURE.md` and `docs/TEST_PLAN.md`. Existing `REQ-*` identifiers, the real manifest, raw and normalized corpus artifacts, provider-egress defaults, and safety/transport modules were not changed.

### Phase 7E files

Modified: `aegiscore/source_review.py`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `PROJECT_STATUS.md`.

Created: `tests/test_persistent_source_review.py`.

Unchanged: `docs/source-review-manifest.json`, all raw and normalized corpus artifacts, `pyproject.toml`, `uv.lock`, safety/guarded-execution modules, and all `REQ-*` identifiers. SQLite databases used by the tests were temporary files outside the project corpus.

### Phase 7E baseline and verification

All commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python. `-B` disables bytecode writes and `-p no:cacheprovider` disables pytest cache writes.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (pre-edit baseline) | 0; 160 passed in 2.86s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_persistent_source_review.py tests\test_source_review.py tests\test_source_review_packet.py tests\test_corpus_acquisition.py` (focused final run) | 0; 38 passed in 2.51s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (full final suite) | 0; 172 passed in 4.29s. |
| Project-local Python read-only manifest check | 0; 11 entries, all candidate, zero review events, zero eligible entries, summary `no_sources_approved`; no project-local SQLite files found. |
| `& .\.venv\Scripts\python.exe -B -c "import tempfile; from pathlib import Path; from aegiscore.source_review import PersistentSourceReviewRegistry as R; root=Path.cwd(); manifest=root/'docs/source-review-manifest.json'; before=manifest.read_bytes(); temp=tempfile.TemporaryDirectory(); selected=R(Path(temp.name)/'review.sqlite3', manifest_path=manifest, repository_root=root).approved_chunks(); print(f'selected_chunks={len(selected)}; manifest_unchanged={manifest.read_bytes() == before}'); temp.cleanup()"` | 0; empty temporary registry selected 0 chunks against the real manifest; manifest bytes were unchanged. |
| `git diff --check` | 0; no whitespace errors. Git warned that modified Markdown files may be normalized from LF to CRLF on a later Git operation. |

The tests use local temporary files and an in-memory test harness around a temporary SQLite database; no network/DNS, Docker, scanner, target dispatch, LLM, embedding provider, API credential, or real human approval was used. They verify the tested application-level persistence and fail-closed rules only. They do not prove identity authentication, storage integrity against a privileged editor, cross-file crash atomicity, network isolation, source authority/truth, license compliance, or production retrieval integration.

### Phase 7E real corpus state and limitations

- Confirmed project corpus status: all 11 manifest entries remain `candidate`, each has an empty `review_events` list, each remains `excluded_until_explicit_approval`, and the manifest summary remains `no_sources_approved`. No real source is approved or rejected and no human review decision is recorded.
- An empty registry in a temporary SQLite database was checked against the actual manifest; the persistent selector returned zero chunks, and the manifest remained byte-identical. No project-scoped review database or decision exists, and all manifest entries remain candidate. The class is not integrated with an API or production retriever.
- SQLite events and the JSON manifest are separate files. The implementation uses a SQLite transaction and atomic manifest replacement with compensating rollback on caught errors; it is not a distributed atomic transaction, authenticated log, signed ledger, or tamper-proof audit system. Explicit identity/authentication, role authorization, concurrent multi-process coordination, crash-recovery operations, schema migration, and production retention/backup policy remain future decisions.
- Approval checklists and reviewer strings are application inputs, not independently verified attestations. A future user-facing review workflow must establish an authenticated human decision source before treating these persisted events as human approvals.

## Completed in Phase 7D

- Created `docs/NORMALIZATION_FIDELITY_AUDIT.md` with per-artifact transformation/loss findings and provenance limitations, and `docs/SOURCE_REVIEW_PACKET.md` with 11 manifest-derived worksheets. Review decision, reviewer, review timestamp, rationale, corroboration, and unknown-metadata fields are explicitly unset for every worksheet.
- Added `tests/test_source_review_packet.py`; updated `docs/KNOWLEDGE_CORPUS.md` and `docs/TEST_PLAN.md`. No application code, source-review workflow, normalizer, manifest, raw artifact, or normalized artifact was changed in this phase.
- The post-preparation SHA-256 for every raw and normalized file matches the digest already recorded in the manifest. This confirms byte agreement with the local recorded snapshot only; it does not establish source authenticity, factual accuracy, semantic equivalence, or license compliance.
- Confirmed at the end of Phase 7D that the in-memory workflow required candidate registration, explicit submission, and a decision for the exact current revision before approval selection. Reviewer/submitter references were unauthenticated labels; the registry was not persistent and was not connected to the manifest/API at that phase. Packet creation did not submit, approve, or reject any source.

### Phase 7D verification

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (pre-edit baseline) | 0; 157 passed in 2.45s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_source_review_packet.py tests\test_source_review.py tests\test_corpus_acquisition.py` | 0; 26 passed in 0.59s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (final run after Phase 7D documentation updates) | 0; 160 passed in 2.58s. |
| `git diff --check` | 0; no whitespace errors. Git emitted line-ending conversion warnings for already tracked files. |

All Phase 7D tests used the project-local `.venv`, local manifest/artifacts, and offline fixtures. No network, DNS, Docker, scanner, target dispatch, LLM, embedding service, or approval event was used. The tests validate packet-to-manifest consistency and existing local candidate-gate behavior; they do not authenticate reviewers, verify licenses/source authenticity, establish semantic equivalence, or prove network isolation.

### Phase 7D remaining limitations

- No human review, source approval/rejection, source-authenticity attestation, license determination, or factual corroboration has occurred.
- Normalized chunk offsets refer to normalized files, not raw source positions; the in-memory chunk metadata does not itself carry all manifest fields such as repository revision, raw digest, license, or page anchor.
- At the end of Phase 7D, the review gate had no persistence and the manifest was disconnected from runtime retrieval. Phase 7E adds persistence and manifest checking, but still no authenticated human identity or production retrieval wiring. No RAG synthesis, LLM, vector retrieval, lab, scanning, test-case execution, or ground-truth preparation was started.

**Git state checked read-only in Phase 6A:** `git rev-parse --show-toplevel` reports `S:/AegisCore`; `HEAD` is `222ec77` (`Initial commit of AegisCore`). `git status --short --untracked-files=all` reports only `PROJECT_STATUS.md` modified. No Git mutation command was run in Phase 6A. The earlier Phase 5A audit had reported that Git metadata was absent; that finding does not describe the current workspace state.

## Completed in Phase 7C

- Acquired 11 public artifacts from official OWASP/MITRE publisher sites or official repositories: three WSTG v4.2 pages, three selected ASVS 5.0.0 chapters, two OWASP prevention cheat sheets pinned to repository commit `9d41c054686e35fb56070b4b6271ae2829edea6a`, and CWE-79/CWE-89/CWE-862 pages showing CWE 4.20. Exact versions/revisions, missing metadata, URLs, canonical references, licenses/terms, acquisition dates, raw/normalized paths and SHA-256 hashes, intended uses, scope tags, and limitations are recorded in `docs/source-review-manifest.json` and summarized in `docs/KNOWLEDGE_CORPUS.md`.
- Preserved all 11 acquired publisher responses under `knowledge_base/raw/`. A PowerShell check fetched each exact official source URL without following redirects; all returned HTTP 200, and each response-body SHA-256 matched the local raw file and manifest. This checks snapshot byte integrity only; no source signature, factual claim, authority, or legal compliance was independently verified.
- Added and ran `scripts/normalize_security_corpus.py`. It is standard-library-only and offline; it verifies raw hashes before producing normalized Markdown in `knowledge_base/normalized/`. Markdown code blocks, inline code, and a whole inline executable-example line are excluded. CWE normalization retains only Description, Common Consequences, and Potential Mitigations. The lossy transformation and source limitations appear in normalized preambles. Raw publisher files remain unmodified and may contain publisher-authored illustrative examples; no payload was created or executed.
- All manifest entries are `candidate`, have no review events, and are marked `excluded_until_explicit_approval`; corpus approval status is `no_sources_approved`. The new test ingests all normalized files and registers them in the in-memory source-review registry; `approved_chunks()` returns empty. This is not a persistent review record or human source approval.
- No application runtime source, safety/guarded-execution behavior, dependency manifest, lockfile, provider-egress policy, or REQ-* identifier changed. No provider, embedding, vector store, lab, scanner, or target integration was used. The corpus is ready for human review only, not retrieval as verified knowledge.

### Phase 7C files

Created: `docs/KNOWLEDGE_CORPUS.md`, `scripts/normalize_security_corpus.py`, `tests/test_corpus_acquisition.py`; 11 raw source files and 11 normalized source files under `knowledge_base/`.

Modified: `docs/source-review-manifest.json`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, `tests/test_source_review.py`, and `PROJECT_STATUS.md`.

No runtime application module or dependency file was changed. Existing `REQ-*` identifiers are unchanged.

### Phase 7C commands and verification

Commands ran in PowerShell from `S:\AegisCore`. Tests used the project-local `.venv`, with bytecode generation and pytest cache disabled.

| Command or action | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (before edits) | 0; 153 passed in 2.23s. |
| Official-source HTTPS response verification for 11 exact manifest URLs (redirects disabled) | 0; 11 responses returned HTTP 200; remote response-byte hashes matched local raw files and manifest hashes. |
| `& .\.venv\Scripts\python.exe -B scripts\normalize_security_corpus.py --root S:\AegisCore` | 0; normalized 11 candidate sources; no source approved. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_corpus_acquisition.py tests\test_rag.py tests\test_source_review.py` | 0; 44 passed in 0.76s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 157 passed in 2.52s. |

Tests use local files and in-memory records. They cover manifest/raw/normalized digest consistency, metadata, deterministic IDs, candidate-only registration and approved-source exclusion, deterministic/lossy transforms, a missing-raw-source failure before output, and patched network/DNS/target-dispatch entry points. They do not authenticate a publisher or reviewer, prove content truth or source authority, complete license review, persist source-review history, establish OS-level egress isolation, or validate semantic retrieval.

### Remaining Phase 7C limitations

- No authentic source was explicitly approved or submitted for human review. `review_events` is empty; the in-memory registry and manifest are not persistently connected.
- The repository snapshot hashes are integrity markers, not publisher signatures. MITRE CWE-89's captured page displays version 4.20 but has no entry-specific update date; the manifest leaves that date unknown rather than borrowing another entry's date.
- OWASP terms are recorded as CC BY-SA 4.0 and MITRE's terms-of-use link/copyright notice are recorded, but no legal/license review was performed. The cheat-sheet repository calls its Markdown files working sources; the manifest separately records the official published HTML URLs for citation.
- Normalized text is intentionally lossy. Human review must compare it with raw content before any future approval. The selected corpus is partial; detailed WSTG test procedures, validated observations, vulnerability cases, ground truth, and experiment data are absent.
- Semantic/vector retrieval, ChromaDB, embeddings, LLM generation, LangGraph, source authority/factual-support verification, persistent review records, and all lab/scanner activities remain unimplemented or separately gated.

## Completed in Phase 7B

- Added `aegiscore/source_review.py`, a standard-library in-memory source review registry with `candidate`, `pending_review`, `approved`, `rejected`, and `stale` states. Registration accepts only candidate ingestion metadata. Submission and review decisions require explicit actor/reviewer references, timezone-aware timestamps, and rationale. Approval additionally requires title and publisher attribution, a source locator, all checklist attestations, and recorded intended use, limitations, corroboration, and unknown-metadata notes. These are workflow records, not authenticated identities or source-authority proofs.
- Re-ingestion under the same stable source ID with changed content or provenance marks the former revision stale, appends a superseded event, and starts a new candidate revision. Re-ingesting an unchanged revision is idempotent. `approved_chunks` returns only exact chunks held by the registry for the current approved revision and stamps them from registry metadata; candidate, rejected, stale, unknown, or altered chunks are excluded.
- `CitationValidation.factual_support` is explicitly `not_evaluated`. Citation membership and source locator presence still do not establish source authority or claim support. `InMemoryTestRetriever` remains a lexical test double and accepts arbitrary chunks if called directly; future production retrieval must consume the approved selector output.
- Added `docs/source-review-manifest.json` with schema version 1 and an empty `entries` list. Repository inspection found no authentic security reference corpus to register. Corpus acquisition and actual source approval remain blocked; no fictional reference, publisher, reviewer, or approval record was added.
- Added `tests/test_source_review.py` and updated the Phase 7A RAG tests for the candidate review state. No runtime dependency, external provider, network transport, or safety/guarded-execution behavior was added or changed. Existing `REQ-*` IDs are unchanged.
- Updated `docs/ARCHITECTURE.md` and `docs/TEST_PLAN.md` only to document the implemented in-memory workflow, test coverage, and remaining limitations.

### Phase 7B files

Created: `aegiscore/source_review.py`, `tests/test_source_review.py`, `docs/source-review-manifest.json`.

Modified: `aegiscore/rag.py`, `tests/test_rag.py`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `PROJECT_STATUS.md`.

Unchanged: `pyproject.toml`, `uv.lock`, external-service configuration, safety-policy and guarded-execution modules/tests, API routes/schemas, and all `REQ-*` identifiers.

### Phase 7B verification

All commands ran in PowerShell from `S:\AegisCore` using the project-local `.venv` Python with bytecode and pytest cache generation disabled.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (before edits) | 0; 134 passed in 2.02s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_rag.py tests/test_source_review.py` | 0; 40 passed in 0.59s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (after edits) | 0; 153 passed in 2.24s. |

The tests use synthetic fixtures and temporary local files only. Socket/DNS entry points, URL opening, policy permit methods, and guarded dispatch are patched to fail if called in the offline governance test. This does not authenticate a reviewer or source, prove publisher attribution or factual correctness, persist an audit log, establish an approved knowledge corpus, connect a production retriever, or verify OS-level network isolation. No network, DNS, Docker, scanner, vulnerability payload, LLM, embedding service, or target execution was used.

## Completed in Phase 7A

- Added `aegiscore/rag.py` using only the Python standard library. Typed contracts represent source metadata/documents, chunks, chunking settings, ingestion results, retrieval query/result/hit metadata, and citation references/validation results.
- Added explicit local ingestion of one named UTF-8 `.txt`, `.md`, or `.markdown` file below a caller-designated root. Resolved paths must remain inside the root. Empty, whitespace-only, malformed, unsupported, inaccessible, traversal/absolute, and over-limit sources fail with clear typed errors. Ingestion does not enumerate directories, download, scrape, call a provider, perform DNS, or make target requests.
- Source IDs are deterministic from canonical root-relative paths. Source digests and chunk digests use SHA-256. Chunk IDs incorporate source ID/digest, chunk size/overlap/source-byte configuration, ordinal, and offsets. Chunking is deterministic character-window splitting with half-open offsets and the nearest preceding Markdown heading when present. Unknown title, publisher, canonical reference, publication date, and version remain `None`.
- Every ingested source is marked `candidate`. Caller-provided descriptive metadata is recorded as supplied and is not independently authenticated. No security-source corpus was added; no source is treated as approved guidance or ground truth.
- Added the provider-neutral `Retriever` protocol and `InMemoryTestRetriever`, which uses lexical token-overlap ranking with deterministic tie-breaking. This is explicitly a test double, not semantic or production retrieval. Citation validation checks membership in the supplied result, source-ID match, and presence of a local path or canonical reference; it does not prove source authority, correctness, or factual support.
- Added `tests/test_rag.py` with temporary local files and in-memory records. Existing `aegiscore/safety.py`, `aegiscore/guarded_execution.py`, API routes/schemas, and safety/guarded-execution tests were not modified. No new dependencies or lock changes were made.
- Updated `docs/ARCHITECTURE.md` and `docs/TEST_PLAN.md` for the implemented offline subset and its limits. Existing REQ-* IDs are unchanged. The API continues to report the overall `backend.rag` capability as not implemented because no production retriever or RAG Analyst is integrated.

### Phase 7A files

Created: `aegiscore/rag.py`, `tests/test_rag.py`.

Modified: `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `PROJECT_STATUS.md`.

Unchanged: `pyproject.toml`, `uv.lock`, safety-policy and guarded-execution source/tests, API source/tests, and all REQ-* identifiers.

### Phase 7A verification

All commands ran in PowerShell from `S:\AegisCore` using project-local `.venv` Python with bytecode and pytest cache generation disabled.

| Command | Exit code and actual result |
|---|---|
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (before edits) | 0; 113 passed in 1.76s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_rag.py` | 0; 21 passed in 0.35s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` (after edits) | 0; 134 passed in 2.11s. |

No network, DNS, Docker, Juice Shop, ZAP, scanner, vulnerability payload, LLM, embedding service, or target-operation dispatch occurred. Network and dispatch entry points were patched to fail if called in one offline test; that test is not an OS-level network-isolation verification.

### Phase 7A limitations and pending work

- The review lifecycle and approved-chunk selector exist only in memory. Reviewer references, checklist attestations, supplied publisher metadata, and manifest entries are not authenticated. The current candidate manifest is not loaded or persisted by the runtime registry; no source licensing review or persistent ingestion/audit store exists.
- No semantic/vector retrieval, embeddings, ChromaDB, approved-release production retrieval wiring, RAG synthesis, LLM, LangGraph, or claim-support verification exists. The lexical double tests interface behavior only; its score is not semantic relevance or vulnerability confidence. A direct caller can instantiate that test double with arbitrary chunks; production wiring must use the registry selector.
- Citation validation checks only retrieval-result membership and locator/digest provenance availability. It cannot establish source authority or factual correctness.
- The initial chunking defaults (1,200 characters, 150 overlap, 1 MiB source) and implementation ceilings (65,536 characters/chunk; 16 MiB/source) are configurable implementation values, not proposal requirements, approved deployment limits, or experimentally selected settings.
- At the end of Phase 7A, no real corpus, security finding, vulnerability test case, ground-truth label, lab setup, or experiment had been created and no source had been downloaded. Phase 7C records the later source acquisition.

## Completed in Phase 6A

- Added `pyproject.toml` with project metadata, Python `>=3.13,<3.14`, explicit runtime dependencies (`fastapi`, `pydantic`, `uvicorn`) and a `dev` group (`pytest`, `httpx2`). Added `.python-version` selecting the inspected Python 3.13.2 interpreter, generated `uv.lock` in the project, and created `.venv` locally. The project uses `uv` because it was available and supports a project-local environment and lockfile; this is a Phase 6A implementation choice, not a thesis or Master Prompt technology requirement.
- The resolved versions are FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1, Uvicorn 0.54.0, pytest 8.4.2, and httpx2 2.16.0. FastAPI and Pydantic provide the minimal API/schema foundation, Uvicorn is the selected ASGI server (not launched), pytest is the existing test framework, and httpx2 is the current Starlette-recommended in-process test-client dependency. Starlette's guidance says plain httpx is deprecated for this role; the final test run has no warning.
- Added `.gitignore` for `.venv`, Python bytecode/caches, test/coverage caches, local env files/secrets, and generated local SQLite/data files.
- Added `aegiscore/api/` with `create_app()` and an ASGI `app`, typed response schemas, and only `GET /health` and `GET /capabilities`. Health reports only that the API process responds. Capabilities lists existing in-memory safety/fake-boundary contracts and unimplemented target transport, RAG, orchestration, vulnerability workflow, external LLM, and persistent storage. The API has no target-operation endpoint and does not import or call the safety policy or guarded transport.
- Added five in-process API tests for app construction, health response, capability accuracy, 404/405 error responses, and absence of policy/transport calls. The existing safety policy and guarded-execution tests run as part of the full suite.
- Updated `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `docs/ADRs/0001-technology-decisions.md` only for the implemented environment/API slice and its exact verification scope. Existing REQ-* identifiers remain unchanged.

### Phase 6A files

Created: `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, `aegiscore/api/__init__.py`, `aegiscore/api/app.py`, `aegiscore/api/routes.py`, `aegiscore/api/schemas.py`, and `tests/test_api.py`. The project-local `.venv/` was generated by `uv sync --locked` and is ignored.

Modified: `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, `docs/ADRs/0001-technology-decisions.md`, and `PROJECT_STATUS.md`. `aegiscore/safety.py`, `aegiscore/guarded_execution.py`, and their tests were not modified.

### Phase 6A setup and verification

Commands were executed in PowerShell from `S:\AegisCore`; all test invocations used `.venv` Python with bytecode and pytest caching disabled.

| Command | Exit code and result |
|---|---|
| `uv lock` (final dependency configuration) | 0; resolved and wrote the 25-package lock. |
| `uv sync --locked` | 0; created/synchronized `.venv`. uv warned that hardlinks were unavailable across cache/workspace filesystems and copied files instead; package installation completed. |
| `uv lock --check` | 0; lock consistent with `pyproject.toml`. |
| `uv pip check --python .\.venv\Scripts\python.exe` | 0; 23 installed distributions checked, all compatible. |
| `.venv\Scripts\python.exe -B -` environment inventory | 0; Python 3.13.2, executable under `S:\AegisCore\.venv`, `sys.prefix != sys.base_prefix`; direct package versions listed above. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_api.py` | 0; 5 passed in 1.43s. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | 0; 113 passed in 1.79s, including all existing safety/guarded-execution tests and the new API tests. |

Two non-blocking tooling observations: uv's environment does not include `pip`, so `& .\.venv\Scripts\python.exe -B -m pip check` exited 1 with `No module named pip`; `uv pip check` was used successfully instead. An initial guessed `httpx2>=1,<2` constraint could not resolve because the package index offered no version in that range; the invalid range was removed, and the lock resolved httpx2 2.16.0. No global Python packages were installed or upgraded. Package-index access was used only for dependency resolution/download; no application target, external LLM, embedding provider, or other service was contacted.

### Phase 6A limitations

- This is a minimal foundation, not a production-ready backend. Authentication, local binding, CORS/CSRF, persistence, target registration administration, operational API routes, audit storage, and authorization workflows remain unresolved or unimplemented.
- No server was launched. `GET /health` and `GET /capabilities` were tested only in process; no network request or DNS lookup occurred.
- The new capability inventory is static; it does not claim lab readiness or operational target execution. Existing fake-only policy tests remain software-boundary tests, not real transport/network security evidence.
- The lock was resolved/tested on Windows with Python 3.13.2. Other operating systems and other Python versions allowed by the declared range were not exercised. The lockfile carries resolved hashes, but no cross-platform installation was verified.
- No RAG, LangGraph, vulnerability scanning, lab setup, ground-truth preparation, external model/provider, embedding service, or database was implemented.

## Completed in Phase 5B

- Extended `aegiscore/safety.py` with typed `CaseProfilePolicy` and `OperationDataLimits`. Operation permits now bind a configured target/case/profile tuple, engine-derived run ID and canonical origin, target-registration version, scope/profile/data-limit versions, exact canonical method/path/query/header/body data, budget slots and caps, and deadlines.
- Kept authorization independent from model output. `OperationIntent` contains no URL, origin, or permit; case/profile identifiers only select a trusted in-memory configuration entry. Missing operation-contract configuration fails closed. The supported method set remains GET/HEAD.
- Added deterministic query, header, and body validation. Query names are profile-allowlisted and sorted before percent-encoding; headers are checked against profile allowlists, lowercased/sorted, size-bounded, and ambiguous/forbidden forms are denied; optional body is immutable bytes and bound byte-for-byte.
- Added in-memory tests for case/profile mismatch, target and policy-context changes, origin/method/path/parameter/header/body alteration, malformed or oversized data, configured size boundaries, expiry, replay, terminal denial, revocation, budget exhaustion, stop, and cancellation. Tests use synthetic policy fixtures, benign data, and the existing recording fake only.
- Phase 5B reproducibility checkpoint (historical): at the end of Phase 5B, no dependency was installed/upgraded and no virtual environment, dependency manifest/lockfile, or `.gitignore` had been added. Phase 6A subsequently established those project-local files and environment. No Git metadata was initialized in either phase.

### Phase 5B verification

| Command | Actual outcome |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider tests/test_safety_policy.py tests/test_guarded_execution.py` | Exit code 0; 108 passed in 0.37s. |
| `python -B -m pytest -q -p no:cacheprovider` | Exit code 0; 108 passed in 0.37s. |

The tests establish only the exercised in-process policy and fake-dispatch behavior. They do not validate authorization records, DNS, sockets, network isolation, HTTP behavior, credential handling, production transport, persistent audit, or in-flight network cancellation. No Docker, lab service, scanner, vulnerability payload, provider, embedding service, network call, or experimental case was used.

### Phase 5B contract limits and remaining decisions

- Test configuration uses 2 parameters/128 query bytes, 2 headers/128 serialized header bytes, and 16 body bytes. The code also bounds configuration to implementation ceilings of 32 parameters/4096 query bytes, 32 headers/8192 serialized header bytes, and 65536 body bytes. These are offline contract limits, not proposal requirements, approved deployment values, or verified transport limits.
- Only GET and HEAD remain supported. Future case method semantics, especially any state-changing operation or use of a body with GET/HEAD, need an explicit policy decision before transport integration.
- Authorization, cookie, host, and hop-by-hop/framing headers are rejected. Any future authentication-header support or value-level query/header allowlisting needs an explicit profile policy and review; no real credentials are represented.
- Synthetic case/profile bindings do not constitute an approved case catalog or target authorization. Authorization lifecycle, DNS/address validation, network egress isolation, redirect transport validation, response/time limits, persistent audit, cancellation of in-flight I/O, and provider-egress decision remain unresolved.
- Provider/embedding egress remains default-deny. No Gemini or external embedding call occurred.

## Completed in Phase 4B

- Added exact-operation permit contracts and validation in `aegiscore/safety.py`. Permits are engine-issued, one-use, run-bound, target-registration-version-bound, policy-version-bound, operation-identity-bound, and bound to exact canonical read-only method/path/parameters, reserved budget slots, and deadlines.
- Added `aegiscore/guarded_execution.py` with an injected transport protocol and guarded workflow boundary. The boundary consumes authorization before invoking the injected transport, latches denials, and blocks later dispatch after denial, cancellation, emergency stop, expiry, revocation, budget exhaustion, or transport failure.
- Added `tests/test_guarded_execution.py` with in-memory fixtures, a fake monotonic clock, and a recording fake transport. The tests cover allowed-once dispatch, zero dispatch for denied/malformed/altered/stale/revoked/replayed permits, operation-field binding, model-shaped input rejection, terminal denial, request/redirect budgets, deadlines, emergency stop, cancellation, serialized fake calls, and no retry after a fake transport exception.
- Updated `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md`, `docs/TEST_PLAN.md`, `docs/ADRs/0002-safety-policy-and-provider-egress.md`, and `docs/REQUIREMENTS.md` so the documented status and limits match this implementation. Existing REQ-* IDs are preserved. Proposed operational limits and supervisor decisions remain unapproved.

## Verification performed

Commands run in the current Python environment:

| Command | Actual outcome |
|---|---|
| `python -m pytest -q tests/test_safety_policy.py tests/test_guarded_execution.py` | Exit code 0; 74 passed in 0.33s. |
| `python -m pytest -q` | Exit code 0; 74 passed in 0.18s. |

An inline PowerShell traceability consistency check exited 0: it found 26 requirement IDs, no duplicate requirement rows, and no requirement IDs missing from the architecture or test plan. This is a documentation consistency check only, not evidence of runtime security.

The Phase 4B tests used only in-memory fixtures and the recording fake transport. No HTTP client, socket, DNS lookup, network request, Docker, OWASP Juice Shop, OWASP ZAP, vulnerability payload, Gemini call, embedding service, or API credential was used. The tests prove only the tested software call-gating behavior; they do not validate real target authorization, DNS/network isolation, response-byte enforcement, connect timeouts, persistent audit, or production transport behavior.

Historical Phase 3 environment check (not a new Phase 4B check): Python 3.13.2 and pytest 8.2.2 were present; tests then reported 45 passed. The current Phase 4B pytest commands above are the actual test results for this phase. No dependency was installed or upgraded.

## Phase 5A read-only environment and lab-readiness audit

### Confirmed environment facts

- `python --version` and Python runtime inspection: Python 3.13.2 at `C:\Users\Md Khan Bahadur Sadi\AppData\Local\Programs\Python\Python313\python.exe`; `sys.prefix == sys.base_prefix`, so this is not a virtual environment.
- `python -m pip --version`: pip 26.0.1. A read-only `importlib.metadata` inventory found pytest 8.2.2, FastAPI 0.135.3, ChromaDB 0.5.0, Pydantic 2.11.10, Uvicorn 0.30.1, httpx 0.27.0, and requests 2.32.4. LangGraph, LangChain, Gemini SDKs, pytest-asyncio, Ruff, mypy, and the Docker Python package were not installed. These are ambient packages; the repository has no Python dependency manifest or lockfile.
- `python -m pip check` exited 1: `render-cli` requires `rich<13` but 14.3.3 is installed; `sklearn-compat` requires `scikit-learn<1.9` but 1.9.0 is installed; `streamlit` requires `pandas<3` but 3.0.3 is installed. Pip also warned about an invalid `~lotly` distribution. These are ambient environment conflicts; the Phase 4B code uses the Python standard library and pytest.
- Read-only Flutter SDK Git metadata inspection: Flutter tag 3.32.8, revision `edada7c56ed`; cached Dart SDK version 3.8.1. Flutter and Dart commands are on PATH, but no `pubspec.yaml` or Flutter application exists in the repository, so project dependency/API compatibility is not established.
- Historical Phase 5A check: `git --version` reported 2.48.1.windows.1 and `git -C S:\AegisCore rev-parse --show-toplevel` exited 128 with “not a git repository.” A later read-only Phase 6A check found the Git repository and initial commit documented at the top of this file; no history mutation was performed in Phase 6A.
- `Get-Command docker` reported Docker unavailable on PATH. Checks of conventional Docker Desktop executable paths, matching uninstall entries, and `com.docker.service` found none. The daemon was not queried because no local Docker CLI/installation was found. Docker Compose and container network availability are therefore unavailable/unverified. Podman was not on PATH.
- `wsl --status` reported that WSL is not installed. Windows reports Microsoft Windows 11 Enterprise Insider Preview, version 10.0.26220, 64-bit, with `HypervisorPresent=True`; `vmcompute` is stopped. Windows optional-feature checks for Hyper-V, Containers, VirtualMachinePlatform, and WSL required elevation, so their feature states remain unknown.
- `Get-NetFirewallProfile -PolicyStore ActiveStore` showed Domain, Private, and Public profiles enabled, with effective default inbound action Block and default outbound action Allow. This is not an outbound-deny lab isolation policy.
- Repository inventory (`rg --files`) contains the Phase 3/4B Python modules and tests plus proposal/docs only. No Python/Dart dependency manifest, Dockerfile/Compose file, frontend, API, agent graph, RAG store, database, or lab definition was found.

### Tests run during this audit

| Command | Exit and result |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider` | Exit code 0; 74 passed in 0.20s. |

The test sources use in-memory policy fixtures and a recording fake transport. No HTTP client, socket, DNS, external API, Docker, scanner, or target traffic was invoked. The test outcome does not validate the environment’s network isolation.

### Lab-readiness conclusion

The proposed isolated Juice Shop lab is **not ready to proceed**. Docker/Compose and an existing isolated lab network are unavailable; the effective Windows Firewall default outbound action is Allow; and target authorization, exact destination-address policy, DNS-to-connection pinning, peer validation, real redirect handling, transport response/deadline enforcement, persistent pre-dispatch audit, and in-flight cancellation remain unresolved or unimplemented. Hypervisor presence alone does not establish a usable or isolated container runtime. This conclusion is based on the inspected state and is not a claim that future isolation is impossible.

The only documentation correction made during Phase 5A was in ADR 0002: it now distinguishes the implemented in-process operation-permit gate from the still-absent real transport enforcement of connection, response-size, concurrency, and per-chain redirect limits. No REQ-* ID or supervisor decision changed.

## Remaining limitations and unresolved decisions

- **Authorization:** Registration-version and revocation state are in-memory checks only. There is no authenticated registration authority, verified authorization record, expiry source, persistent revocation registry, or authorized target in the repository. Test fixture references are not evidence of authorization.
- **Transport permit boundary:** The permit is an in-process capability marker, not a cryptographic or cross-process token. It does not protect against arbitrary code executing inside the trusted Python process. The offline contract now binds synthetic configured case/profile IDs, exact canonical query/header/body data, and trusted target/run context. These profile fixtures are not an approved research case catalog or authorization evidence; there is no real transport.
- **Network isolation:** There is no real transport, DNS resolution/address pinning, connected-peer check, TLS check, proxy control, firewall/container isolation, or outbound-network verification. Hostname/origin policy is not proof of network isolation.
- **Numeric limits:** Phase 5B tests use explicit offline data limits of 2 parameters/128 query bytes, 2 headers/128 serialized header bytes, and 16 body bytes. Code-level in-memory contract ceilings are 32 parameters/4096 query bytes, 32 headers/8192 serialized header bytes, and 65536 body bytes. These are not approved deployment limits. The separate proposed ADR 0002 defaults (50 requests/run; 3 redirects/chain and 10/run; 2-second connection; 10-second operation; 300-second run; 1 MiB response; one concurrent operation) also remain unapproved; response-size and connection-timeout enforcement are not implemented.
- **Cancellation/audit:** Cancellation prevents later fake dispatches; in-flight network cancellation and persistent audit-before-dispatch are not implemented.
- **Provider egress:** Gemini and embedding-provider use remain unresolved and unapproved. Default-deny outbound-network posture remains in effect; no provider call or exception was introduced.
- **Other application features:** No frontend, LangGraph agents, semantic/vector RAG store, production retriever, evaluator, report workflow, lab, dataset, or experimental result is implemented or validated. A minimal API and a source-review SQLite registry exist, but the source-review registry is not wired into API authentication or a production retrieval path; no project review database is initialized.

## Files changed in Phase 4B

- `aegiscore/safety.py`
- `aegiscore/guarded_execution.py` (new)
- `tests/test_safety_policy.py`
- `tests/test_guarded_execution.py` (new)
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/THREAT_MODEL.md`
- `docs/TEST_PLAN.md`
- `docs/ADRs/0002-safety-policy-and-provider-egress.md`
- `PROJECT_STATUS.md`

## Files changed in Phase 5B

- `aegiscore/safety.py`
- `tests/test_guarded_execution.py`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/THREAT_MODEL.md`
- `docs/TEST_PLAN.md`
- `docs/ADRs/0002-safety-policy-and-provider-egress.md`
- `PROJECT_STATUS.md`

No Git metadata was present in the previously inspected workspace; a Git diff is not available as a verification artifact.

## Phase gate

Phase 4B is complete at the fake-transport boundary only. Phase 5A is complete as a read-only readiness audit; Phase 5B is complete at the offline case/profile contract and fake boundary only. Lab setup is not ready and was not started. Do not proceed to Docker/OWASP Juice Shop, real transport, scanning, research vulnerability-case execution, ground-truth preparation, or LLM integration without the next explicit phase approval and resolution of the authorization and network-isolation prerequisites.

## Completed in Phase 8G.3 — Flutter–FastAPI Integration

- Added configurable demo/live selection, a typed asynchronous HTTP repository, sanitized endpoint display, timeout and error handling, and reusable unsupported/error states.
- Wired the existing `GET /health` and `GET /capabilities` contracts. No assessment submission, findings, evidence/provenance, dashboard metrics, or evaluation report endpoints exist; those live views disclose the gap and never substitute fixture data.
- Kept synthetic records and demo sessions in demo mode, with an explicit mode banner. Live assessment submission is disabled because no authorized offline execution endpoint exists.
- Added mocked API, timeout, parsing, provider selection, live-screen, and duplicate-submission tests.
- Verification: `flutter analyze` passed; `flutter test` reported 30 passed; `python -m pytest tests/` reported 611 passed.
- Configuration, endpoint field mapping, screen coverage, limitations, and next-phase requirements are documented in `docs/PHASE_8G3_API_INTEGRATION.md`.

## Completed in Phase 8G.4 — Read-Only Backend API Expansion

- Added `GET /evidence/approved` with bounded offset/limit pagination and `GET /evidence/approved/{evidence_id}` for stable chunk IDs. Both use the existing persistent source-review selector, which is reopened in read-only mode and validates registry, manifest, and source-file integrity. Responses contain approved source metadata, exact chunk excerpts and hashes, offsets, and supported source/chunk citation IDs; local paths and reviewer labels are omitted.
- The default app has no configured registry and returns HTTP 503. A valid configured store with no approvals returns a typed empty page. The current checkout has no source-review database, and `docs/source-review-manifest.json` still reports `no_sources_approved`.
- Flutter Evidence & Provenance consumes the typed list/detail responses, paginates all chunks, and shows backend loading, empty, and error states without demo fallback. It shows recorded review metadata and warns that approval does not prove claim support. Dashboard metrics, assessments, findings/details, and evaluation reports remain unsupported in Live Mode because no persistent records/repositories exist; submission remains disabled.
- Tests: `python -m pytest tests/` — 617 passed; from `frontend/`, `flutter analyze` — no issues; `flutter test` — 36 passed. New endpoint tests use temporary local registries and verify empty/unconfigured states, approval enforcement, paging, detail/not-found, malformed inputs, stable serialization, integrity failure, no path/reviewer disclosure, and no writes.
- The API still has no authentication or authorization layer and must remain in an isolated loopback deployment. No repository source was approved (approval tests used only a temporary synthetic fixture), `DEC-01` through `DEC-08` remain pending, no empirical benchmark was run, and no target execution/scanning or external provider activity was introduced.
- API and integration details are documented in `docs/PHASE_8G4_READ_ONLY_API_EXPANSION.md` and `docs/ARCHITECTURE.md`.

## Completed in Phase 8G.5 — Local Persistence & Functional Backend Workflows

- Added schema-versioned local SQLite persistence for completed synthetic offline-harness reports and their actual per-case replay outputs. Report/session IDs are stable; repeated identical report output is idempotent; report plus sessions commit in one transaction. Rejected or unavailable storage does not silently downgrade to fixture data.
- Marked all persisted replay records explicitly `is_synthetic=true`, `is_empirical=false`, and `execution_mode=offline_fixture`. Stored findings, evidence reference IDs, statuses, timestamps, metrics, abstentions, incomplete/failure counts, and diagnostics come from the harness output. Abstention without findings remains empty.
- Added read-only `/storage/status`, `/dashboard/summary`, paged `/sessions`, `/findings`, and `/reports` endpoints plus supported detail routes. A configured empty store returns empty pages/zero counts; missing or inconsistent storage returns 503; unknown valid detail IDs return 404. No assessment execution endpoint was added.
- Configured the local DB through `AEGISCORE_LOCAL_STORE_PATH`; source-review registry settings are `AEGISCORE_SOURCE_REVIEW_DB`, `AEGISCORE_SOURCE_REVIEW_MANIFEST`, and `AEGISCORE_REPOSITORY_ROOT`. Invalid/missing registry settings remain unavailable. The source-review manifest was not modified, and no repository approval was created.
- Flutter Live Mode now displays persisted dashboard counts and recent session status/time, actual saved findings and evidence references, persisted report summaries/details and diagnostic counts, and storage status. It labels fixture replay synthetic and does not fill missing confidence/claims with invented values. Demo Mode remains separate; submission remains disabled.
- Local SQLite is not encrypted and relies on OS file permissions. The API still has no authentication or authorization; launch it only on loopback. No target scanning/exploitation, Docker, external provider call, or empirical benchmark was performed; DEC-01 through DEC-08 remain pending.
- Guide/API details: `docs/PHASE_8G5_LOCAL_PERSISTENCE.md`, with current API architecture in `docs/ARCHITECTURE.md`.
- Verification:
  - `python -m pytest tests/` — 630 passed (9.84s).
  - From `frontend/`, `flutter analyze` — no issues found (6.9s).
  - From `frontend/`, `flutter test` — 38 passed.
- Persistence/API tests used temporary SQLite files and synthetic fixture replays, including empty stores, reopen/restart reads, idempotency, rollback, malformed data, unavailable stores, abstention, scope-failure diagnostics, env configuration, API not-found/pagination, correct dashboard counts, and unchanged database bytes on read routes. No repository evidence approvals, real assessment records, or empirical benchmark data were written or run.

## Completed in Phase 8G.6 — End-to-End Integration, Data Integrity & Operational Hardening

- Exercised one actual synthetic orchestration replay through temporary SQLite persistence, FastAPI `TestClient` serialization, API app recreation/re-read, and Flutter's real API repository plus Live screens. The integration widget rendered the persisted session/detail, finding/detail, report/detail, and storage status using the exact response JSON returned by FastAPI. The integration uses local test clients; no Uvicorn socket, target, or external service was involved.
- Added Live session-detail navigation from recent dashboard sessions. Detail preserves the API session ID and shows stored report/run/case IDs, fixture provenance, result, and actual diagnostic text. Finding and report detail identifiers are also exercised end to end.
- Fixed read-only SQLite URI path escaping for valid filesystem paths containing spaces, `#`, and `%`. Wrapped multi-query pages and dashboard aggregates in a read transaction so concurrent writes cannot produce mixed snapshots. Locked stores and malformed/incomplete data return generic unavailable errors without local path disclosure.
- Added regressions for schema-version rejection without rewriting, URI-special database paths, concurrent duplicate writes/reads, semantically incomplete report payloads, locked database behavior, session detail parsing/not-found, Live retry, and unavailable storage state. Schema v1 initializes on an empty database; no in-place migration beyond v1 is supported.
- Full integration and automated contract results are distinguished in [PHASE_8G6_END_TO_END_HARDENING.md](docs/PHASE_8G6_END_TO_END_HARDENING.md).
- Verification from `S:\AegisCore`:
  - `python -m pytest tests/` — 635 passed (18.09s).
  - From `frontend/`, `flutter analyze` — no issues (5.0s).
  - From `frontend/`, `flutter test` — 41 passed, 1 skipped; the opt-in cross-stack widget test is run by the integration script.
  - `python scripts/verify_phase_8g6_e2e.py` — passed; one Flutter widget integration test passed using actual FastAPI response bodies from the temporary synthetic run.
  - `git diff --check` — passed; Git reported only its existing LF-to-CRLF working-copy notices.
- Authentication remains absent; deployment remains loopback-only. No live scans, Docker, provider/model calls or downloads, source approvals, or empirical benchmarks were performed. `docs/source-review-manifest.json` is unchanged and DEC-01 through DEC-08 remain pending. No real-world detection readiness is claimed.

## Completed in Phase 8G.7 — Authentication, Authorization & Deployment Security

- Added a single-account local auth service using Argon2id password hashes and opaque, random, 30-minute bearer sessions. Only SHA-256 token digests and permissions are held in process memory; logout and process recreation revoke sessions. No password, password hash, or raw token is written to SQLite.
- Added an explicit per-user local setup utility (`python scripts/setup_local_auth.py`) with no default credentials. Config is stored outside the repository, refuses overwrite, and reports neither password nor hash. Auth unconfigured/partial behavior is fail-closed.
- Protected persisted sessions, findings, reports, dashboard data with `records:read`; approved evidence uses the separate `evidence:read` permission. Health, static capabilities, and the limited storage-readiness summary remain loopback-only. Authentication does not add assessment, source-approval, supervisor-decision, or scan APIs.
- Added validated loopback host configuration, an official single-worker local launcher (`python -m aegiscore.api`), ASGI peer/server-scope guards, and Flutter Live Mode loopback URL validation. Live Mode now gates navigation on `/auth/session`, uses platform secure storage for bearer tokens, supports sign-out, and clears expired sessions. Demo Fixture Mode remains separate with no auth-failure fallback.
- Added backend tests for login, wrong credentials, missing/malformed/expired/invalidated sessions, permission denials, generic secret-safe errors, config validation, and unsafe/remote bind scopes. Updated persistence/evidence tests and the Phase 8G.6 integration script to perform actual FastAPI authentication before protected reads. Flutter tests cover secure token storage abstraction, expiry/sign-out, 401 handling, auth failure without demo fallback, route gate, and bearer headers.
- No SQLite schema migration or application-record modification was made. Existing local persistence and source-review rules remain unchanged.
- Verification:
  - `python -m pytest tests/` — 646 passed (22.04s).
  - From `frontend/`, `flutter analyze` — no issues found.
  - From `frontend/`, `flutter test` — 48 passed, 1 skipped (the opt-in cross-stack widget test).
  - `python scripts/verify_phase_8g6_e2e.py` — passed; actual backend missing/wrong credential denials, authenticated reads, session revocation on app recreation, and Flutter bearer restoration/rendering passed.
  - `git diff --check` — passed after the final documentation update.
- Setup, route permissions, local-only operation, tests, and remaining deployment review requirements are documented in `docs/PHASE_8G7_AUTHENTICATION_AND_DEPLOYMENT_SECURITY.md`. This implementation is for authenticated local use only, not production or public deployment. `docs/source-review-manifest.json` remains unchanged, DEC-01 through DEC-08 remain pending, and no live assessment, Docker startup, external provider/model activity, or empirical benchmark was run.
- `uv.lock` could not be refreshed offline because the new Argon2 package metadata was not cached. Regenerate it in an approved package-enabled environment before using `uv sync --locked` for a clean install.
