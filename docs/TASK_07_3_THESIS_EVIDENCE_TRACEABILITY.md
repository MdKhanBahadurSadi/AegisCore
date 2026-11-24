# TASK 07.3 — Thesis Evidence Traceability

**Purpose:** map significant claims in `AEGISCORE_THESIS_FINAL.md` to implementation, experiment/test evidence, source records, and limitations. This matrix was updated for TASK 07.4. Internal project reports are evidence artifacts, not scholarly references.

## 1. Evidence source register

| ID | Evidence source | Evidence type | Relevant boundary |
|---|---|---|---|
| P1 | `docs/TASK_07_0_THESIS_OUTLINE_AND_DEFENSE.md` | Prior claim audit and thesis outline | Read as prior task evidence; superseded university identity is corrected in this task |
| P2 | `docs/TASK_07_2_LITERATURE_REVIEW_AND_RESEARCH_GAP.md` | Full-paper synthesis, candidate reference audit, and provisional bibliography | Not a systematic review; PentestEval publisher record remains pending; ACL bibliography now follows the published PDF and records metadata discrepancy |
| P3 | `docs/TASK_06_9_THESIS_EVALUATION.md`; `scripts/task_06_9_fixture_experiments.py` | Primary recorded fixture and regression evaluation | Historical run; no TASK 07.3 rerun |
| P4 | `aegiscore/api/routes.py`; `aegiscore/production_execution.py`; `aegiscore/guarded_execution.py`; `aegiscore/execution.py` | Source implementation | Application-level behavior; not proof of production authority/firewall |
| P5 | `aegiscore/passive_detector.py`; `aegiscore/assessment_ai.py` | Detector and advisory implementation | Deterministic rules and local output checks; not semantic truth or model quality |
| P6 | `aegiscore/local_persistence.py`; `aegiscore/api/app.py` | SQLite transaction, lease, and periodic recovery implementation | Production disk, backup, filesystem, and long-duration behavior not demonstrated |
| P7 | `aegiscore/target_authorization.py`; `aegiscore/authorization_verification.py`; `tests/test_authorization_verification.py` | Target binding and verifier contract/tests | Test verifiers are injected; no trusted issuer configured |
| P8 | `tests/test_passive_pipeline.py`; `tests/test_assessment_lifecycle_recovery.py`; `tests/test_assessment_ai_integration.py`; `tests/test_assessment_execution_api.py` | Regression tests summarized in P3 | Selected cases and fixtures, not formal verification |
| P9 | `docs/TASK_06_7_FLUTTER_PRODUCT_INTEGRATION.md`; `docs/TASK_06_8_RELIABILITY_RELEASE_READINESS.md`; `docs/TASK_06_8_3_LIVE_ACCEPTANCE.md` | Historical Flutter/build and deployment audit | No live authenticated browser-to-API acceptance |
| P10 | `git show HEAD:docs/ARCHITECTURE.md`; `git show HEAD:docs/REQUIREMENTS.md`; `git show HEAD:docs/THREAT_MODEL.md` | Read-only historical proposal/design records | These files are deleted in the current worktree as pre-existing status; their proposed design is not implementation evidence |

## 2. Claim-to-evidence matrix

| Thesis claim or quantitative statement | Implementation / source support | Experiment or test support | Evidence source | Permitted wording / status | Limitation or correction |
|---|---|---|---|---|---|
| AEGISCORE's current integrated assessment route is a narrow passive HTTP-header workflow. | API route delegates to `AuthorizedAssessmentExecutor`, normalizes one observation, then calls `PassiveHeaderDetector`. | Passive pipeline and execution tests in the recorded suite. | P3, P4, P5, P8 | **SUPPORTED WITH QUALIFICATION.** Describe only the implemented route. | Do not characterize the route as broad vulnerability scanning. |
| The assessment API is protected by local bearer authentication and permissions. | `api/auth.py`, permission dependencies in `api/routes.py`. | API/auth tests included in the historical Python suite. | P3, P4, P9 | **SUPPORTED WITH QUALIFICATION.** State the implemented mechanism. | Live credentials and a deployed browser/API session were unavailable; auth does not grant target-owner authority. |
| Target binding records a target ID, canonical endpoint, registration version, and verifier provenance. | Assessment creation stores those fields; executor compares them against the registry before execution. | Target-binding, authorization, and execution tests. | P4, P7, P8 | **SUPPORTED WITH QUALIFICATION.** This is an application implementation claim. | No trusted production issuer or verifier is configured in the normal launcher. |
| A loopback IP address alone establishes authorization. | No: the code requires registered binding and verifier validation. | Missing/unavailable/invalid verifier cases deny in tests. | P7, P8 | **UNSUPPORTED — DO NOT CLAIM.** | Actual authority approval is absent. |
| The verifier contract handles invalid, expired, revoked, unknown-issuer, and unavailable states. | `authorization_verification.py` validates verifier evidence and target claims. | Synthetic verifier tests exercise represented cases. | P3, P7, P8 | **SUPPORTED WITH QUALIFICATION.** “Tested with injected verifier.” | Does not establish an operational trusted authority or production signature/revocation integration. |
| Every accepted target request is bound to a numeric loopback address and exact registered endpoint. | Registry canonicalization, endpoint binding checks, executor and guarded transport checks. | Hostname, non-loopback, port/path, changed binding, peer mismatch cases. | P3, P4, P7, P8 | **SUPPORTED WITH QUALIFICATION.** Application policy/test claim only. | Cannot be presented as kernel/network namespace isolation. |
| Execution issues one passive HTTP `HEAD`. | `execution.py` constructs `HEAD`; executor dispatches one operation. | One-HEAD tests. | P3, P4, P8 | **SUPPORTED.** State that target execution uses one `HEAD`. | API `GET` history/detail reads are separate and must not be conflated with target execution. |
| Execution follows redirects or reads response bodies. | Redirect handler denies redirects; code captures headers and does not call body read. | Redirect rejection, no-body-read tests. | P3, P4, P8 | **SUPPORTED NEGATIVE CLAIM** for this implementation path. | Tests do not prove all deployment/proxy behaviors; configured transport is still an application boundary. |
| Connected-peer validation is implemented. | Peer-checking socket connection verifies the actual connected IP against authorized numeric destination before treating response as reachable. | Connected-peer mismatch test. | P3, P4, P8 | **SUPPORTED WITH QUALIFICATION.** Implementation and controlled-test evidence. | No claim of OS firewall isolation; no external live deployment evidence. |
| Default execution budget is 5 seconds with a 25-second lease safety margin. | `execution.py` constants; lease duration is derived from those values. | Timing/lease configuration regression tests. | P3, P4, P6, P8 | **SUPPORTED.** Values describe configured defaults. | Transport maximum may be configurable up to 30 seconds; do not conflate the default with all possible injected settings. |
| Runtime lease renewal is needed for the default execution budget. | Bounded request budget is 5 seconds; lease provides 25 seconds additional margin. | No normal runtime renewal is required by the configured budget. | P3, P4, P6 | **UNSUPPORTED — DO NOT CLAIM.** | Do not say runtime renewal is part of ordinary execution unless code/config changes. |
| Detector has five security-header rules. | CSP, X-Content-Type-Options, framing protection, Referrer Policy, and HTTPS HSTS. | One synthetic empty-header HTTPS fixture emits five findings. | P3, P5, P8 | **SUPPORTED.** Use “configuration observations.” | The rules do not prove exploitable vulnerabilities or inspect all header semantics. |
| Detector output is repeatable over 100 runs. | Fixed rule logic and stable finding IDs. | 100 repeated calls on one fixed synthetic HTTPS observation produced one normalized complete set. | P3; fixture script | **SUPPORTED WITH QUALIFICATION.** “One normalized set over 100 calls on one fixture.” | `created_at` excluded; this is not 100 independent targets or real-world accuracy. |
| There were five findings per E1 call. | Five rules applied to the selected empty-header HTTPS input. | Fixture result: 5 per call. | P3 | **SUPPORTED WITH QUALIFICATION.** Only for that input. | A different header observation may produce another number. |
| All 500 E1 finding/evidence ID links were valid. | Findings reference the fixture evidence ID and assessment ID. | 100 runs × five findings yielded 500/500 membership checks. | P3; fixture script | **SUPPORTED WITH QUALIFICATION.** “Identifier membership passed.” | Repeated links are not independent evidence; membership is not semantic entailment or factual correctness. |
| The reviewer remains advisory and cannot create official findings or alter severity/status. | `assessment_ai.py` returns advisory metadata; route stores it under a distinct result field; deterministic findings/status come from backend logic. | API failure-isolation, response-validation, and frontend separation tests. | P3, P4, P5, P8, P9 | **SUPPORTED WITH QUALIFICATION.** State the tested design boundary. | No live provider output was evaluated. |
| Reviewer is disabled by default / enabled by server configuration. | App initializes reviewer only when an adapter/config is injected; Flutter API has no per-assessment opt-in field. | Disabled/unavailable/success fixture cases. | P3, P5, P8, P9 | **SUPPORTED WITH QUALIFICATION.** “Opt-in at backend configuration.” | Do not imply a client-side per-assessment toggle exists. |
| Reviewer valid reference acceptance was 1/1. | Strict output validation matches returned finding/evidence IDs to input map. | One valid scripted response accepted. | P3, P5, P8 | **SUPPORTED AS FIXTURE METRIC.** | Not model accuracy or an estimate of correct real output. |
| Reviewer invalid reference rejection was 3/3. | Unknown finding, unknown evidence, and cross-finding evidence are rejected. | Three constructed invalid cases rejected. | P3, P5, P8 | **SUPPORTED AS FIXTURE METRIC.** | Small engineered sample; not a general rejection rate. |
| Unsupported claim fixtures were rejected 2/2. | Local claim/output validation. | Two constructed unsupported/unqualified examples rejected. | P3, P5, P8 | **SUPPORTED AS FIXTURE METRIC.** | Lexical checks do not prove semantic support; avoid “all hallucinations rejected.” |
| Insufficient-evidence abstention occurred 1/1. | Reviewer checks evidence/findings before invoking adapter. | One constructed insufficient-evidence fixture abstained. | P3, P5, P8 | **SUPPORTED AS FIXTURE METRIC.** | Does not estimate real model abstention or calibration. |
| Valid schema was accepted 1/1 and invalid schemas rejected 2/2. | Strict schema and output bounds. | One valid and two invalid scripted responses. | P3, P5, P8 | **SUPPORTED AS FIXTURE METRIC.** | Do not state general provider compliance. |
| Reviewer failure isolation was 4/4 and repeated failure isolation 5/5. | Route stores safe advisory failure state without replacing deterministic output. | Listed API and repeated scripted failure cases. | P3, P4, P5, P8 | **SUPPORTED AS TEST-CASE RESULT.** | These counts describe represented paths, not a failure probability. |
| Advisory validation adds 0.4854 ms local median time. | Detector and fake reviewer local code paths. | 20 warmups and 250 paired samples; detector median 0.0233 ms, combined 0.5087 ms. | P3; fixture script | **SUPPORTED WITH QUALIFICATION.** “Measured local median increment in one run.” | Fake adapter only; excludes model/network/API/deployment and is not an SLO. |
| Full Python suite passed 863 tests. | Historical repository implementation/test snapshot. | TASK 06.9 full run: 863 collected, 863 passed, 0 failed, 0 skipped, 47.26 s. | P3 | **SUPPORTED AS HISTORICAL RUN.** Exact date/report and no current rerun must be stated. | Do not imply Task07.3 reran it or that tests prove universal security. |
| Focused Python suite passed 175 tests. | Historical suite. | 175 collected/passed, 0 failed/skipped, 21.53 s. | P3 | **SUPPORTED AS HISTORICAL RUN.** | Overlaps the full suite. |
| Six fixture demo tests passed. | Creation, HEAD, advisory failure, recovery, restart, verifier cases. | 6 passed, 0 failed/skipped, 3.56 s. | P3 | **SUPPORTED AS HISTORICAL SCRIPTED SELECTION.** | Not a continuous browser demo, live target, or live provider call. |
| Flutter tests/build/analyzer passed historically. | Flutter integration artifacts and report. | TASK 06.8: 60 collected, 59 passed, 0 failed, 1 skipped; analyzer 0 issues; Web build succeeded. | P9 | **SUPPORTED AS HISTORICAL REPORT ONLY.** | Not rerun for this task. TASK 07.1 Flutter attempt had no completed result; do not count it as a pass. |
| SQLite evidence/findings/result/status write is transactional. | `save_pipeline_result` transaction and lease validation. | Genuine two-assessment recovery rollback and pipeline transaction rollback tests. | P3, P6, P8 | **SUPPORTED FOR TESTED TRANSACTIONS.** | Temporary SQLite; no production storage durability/backup guarantee. |
| Persistence failure can recover without an application restart. | Periodic bounded recovery worker retries while process remains active. | Same-process recovery after storage failure is resolved and lease expires. | P3, P6, P8 | **SUPPORTED WITH QUALIFICATION.** | Recovery waits for storage availability and expiry; not immediate during outage. |
| Process restart recovery is tested. | Startup/recovery logic checks expired leases. | Fresh-app/restart fixture recovers an expired assessment. | P3, P6, P8 | **SUPPORTED FOR TEST FIXTURE.** | Not a production service restart with configured deployment volume. |
| Two-assessment recovery transaction rollback is retained. | `recover_stale_assessments` runs under a write transaction. | `test_two_stale_assessments_rollback_on_trigger_failure` verifies both records remain running if a later update fails. | P3, P6, P8 | **SUPPORTED.** Name the exact invariant. | Test does not measure high-concurrency production load. |
| Deployment uses secure production SQLite storage. | No evidence of configured live storage, permissions, backup, or restore. | TASK 06.8.3 did not create/read a deployment DB. | P9 | **UNSUPPORTED — DO NOT CLAIM.** | Keep deployment storage as a blocker. |
| Flutter supports assessment create/history/detail and separated finding/advisory presentation. | Assessment setup/details screens, repository/models, router. | TASK 06.7 and 06.8 Flutter tests/build. | P9 | **SUPPORTED WITH QUALIFICATION.** UI contract is implemented. | No authenticated browser-to-live-backend workflow was accepted. Advisory state is server-configured. |
| The custom FSM orchestrates the passive assessment route. | No call from the assessment route to `orchestration.py`; route calls executor/detector directly. | Source trace in TASK 07.0/07.2; no FSM evidence for this route. | P1, P2, P4, P10 | **UNSUPPORTED — DO NOT CLAIM.** | State that FSM/RAG are separate subsystems. |
| RAG improves the passive detector. | Passive API route does not invoke RAG. | No RAG ablation or detector comparison. | P1–P4, P10 | **UNSUPPORTED — DO NOT CLAIM.** | Not evaluated in this thesis. |
| AEGISCORE improves vulnerability accuracy or is better than ZAP. | No comparative implementation/evaluation evidence. | No labeled benchmark or ZAP run. | P2, P3 | **UNSUPPORTED — DO NOT CLAIM.** | No false-positive/negative, precision, recall, F1, or accuracy estimate. |
| AI reviewer has calibrated confidence or known model quality. | No live model and `confidence_calibrated=false` / factual support not evaluated. | Zero provider-generated samples. | P3, P5 | **UNSUPPORTED — DO NOT CLAIM.** | Keep calibration and live model quality as future work. |
| AEGISCORE has a production authorization authority configured. | Interface exists; standard app has no trusted verifier injection/config. | Synthetic verifier tests only; no live authorized execution. | P3, P7, P9 | **UNSUPPORTED — DO NOT CLAIM.** | State that authority-backed live assessment is unavailable. |
| AEGISCORE has operating-system-level egress isolation. | No live Debian namespace/firewall inspection or test. | TASK 06.4.4 explicitly deferred; zero live egress runs. | P3, P9, P10 | **UNSUPPORTED — DO NOT CLAIM.** | Mark Debian 13 egress verification as deferred/unverified. |
| The draft complies with the university template/citation rules. | No official North Western University, Khulna document or department instruction in repository. | No formatting audit against a supplied template possible. | P1, P2, repository inspection | **NOT VERIFIED.** | Do not use South Africa’s North-West University template; obtain the correct institution's current instructions. |
| PentestGPT benchmark contains 13 targets, 182 subtasks, 26 categories, and 18 CWE items; it uses Reasoning, Generation, and Parsing modules with human execution. | Not AEGISCORE implementation evidence. | Full-paper analysis in TASK 07.2. | Scholarly source [1]; P2 | **CITED LITERATURE CLAIM.** | Attribute the counts/architecture to Deng et al.; do not present them as AEGISCORE results. |
| Isozaki et al. enumerate 13 VulnHub systems and 152 tasks in the primary paper's Table 1. | Not AEGISCORE implementation evidence. | Full-paper comparison in TASK 07.2. | Scholarly source [2]; P2 | **CITED LITERATURE CLAIM.** | Happe and Cito's review reports 162; preserve and explain the discrepancy, using the primary table for the quoted 152. |
| Happe and Cito review 19 papers representing 18 prototypes and identify benchmark-design variation. | Not AEGISCORE implementation evidence. | Full-paper review described in TASK 07.2. | Scholarly source [3]; P2 | **CITED LITERATURE CLAIM.** | Attribute review scope and recommendations to the authors; do not imply a systematic review by this thesis. |
| PentestEval reports 346 tasks/12 scenarios, >3,000 stage evaluations, 180 end-to-end tests, and nine evaluated LLMs. | Not AEGISCORE implementation evidence. | Full-paper analysis in TASK 07.2. | Scholarly source [4]; P2 | **CITED LITERATURE CLAIM.** | Benchmark-specific counts/outcomes; arXiv record cited while publisher metadata remains unresolved. |
| PENTESTLLMAGENT studies 13 targets/93 subtasks, 130 logs/10 configurations, and reports best 77% end-to-end / 88% subtask completion. | Not AEGISCORE implementation evidence. | Full-paper analysis in TASK 07.2. | Scholarly source [5]; P2 | **CITED LITERATURE CLAIM.** | Results are specific to that paper's framework and benchmark; not comparable to AEGISCORE fixture metrics. |
| The ACL uncertainty paper analyzes trajectory uncertainty using τ²-bench and GPT-4.1/Kimi-K2.5 without turn-level labels. | Not AEGISCORE implementation evidence. | Full-paper analysis in TASK 07.2. | Scholarly source [6]; P2 | **CITED LITERATURE CLAIM.** | Author seventh given name unresolved; do not claim this study calibrates the AEGISCORE reviewer. |

## 3. Quantitative claim ledger

| Value | Definition and denominator | Source/date | Use rule |
|---|---|---|---|
| 100 | Calls to detector using one fixed synthetic HTTPS observation | TASK 06.9, 2026-11-24 | Say “100 repetitions on one fixture,” never “100 assessments.” |
| 1 | Distinct complete normalized finding set after excluding `created_at` | TASK 06.9 | Say “one normalized set for this fixture.” |
| 5 | Findings returned per call for the empty-header HTTPS fixture | TASK 06.9 | Do not generalize to other headers/targets. |
| 500/500 | Identifier membership links across the five findings in 100 runs | TASK 06.9 | Say “link membership,” not truth or semantic evidence sufficiency. |
| 1/1, 3/3, 2/2, 1/1, 1/1, 2/2 | Valid refs, invalid refs, unsupported claims, abstention, valid schema, invalid schemas, respectively | TASK 06.9 reviewer fixture metrics | Keep category labels and small denominators beside results. |
| 4/4; 5/5 | API reviewer failure isolation and repeated failure cases | TASK 06.9 | Represented cases only; not reliability rate. |
| 0.0233/0.0236/0.0267 ms | Detector-only median/mean/P95 | TASK 06.9; 250 paired samples after warmups | One-run local timing. |
| 0.5087/0.5100/0.5256 ms | Detector + fake reviewer median/mean/P95 | TASK 06.9 | Excludes live model/network. |
| 0.4854 ms | Difference between local path medians | TASK 06.9 | Not provider latency or end-to-end service cost. |
| 863/863; 0/0 | Full suite collected/passed; failed/skipped | TASK 06.9 historical run, 47.26 s | Not a TASK 07.3 rerun; no security probability. |
| 175/175; 0/0 | Focused suite collected/passed; failed/skipped | TASK 06.9 historical run, 21.53 s | Overlaps full suite. |
| 6/6; 0/0 | Fixture demonstration selection passed; failed/skipped | TASK 06.9 historical run, 3.56 s | Scripted test selection, not live demo. |
| 60/59/0/1 | Historical Flutter collected/passed/failed/skipped | TASK 06.8 report | Historical only; analyzer/Web build also historical. |
| 0 | Live provider-generated evaluation samples | TASK 06.9 | Do not infer model quality or calibration. |
| 0 | Production-authorized target assessments or live Debian isolation runs | TASK 06.9 and TASK 06.8.3 | No live target or OS-level security claim. |

## 4. Citation-to-bibliography audit

### 4.1 Sources cited in the final thesis

| Thesis citation | Source | Bibliography status | Open issue |
|---|---|---|---|
| [1] | PentestGPT, USENIX Security 24 (2024) | Included; publisher proceedings record verified in TASK 07.2 | USENIX record lists no DOI; none invented |
| [2] | Isozaki et al., arXiv:2410.17141 v4 | Included as preprint | No proceedings/journal venue recorded |
| [3] | Happe and Cito, arXiv:2504.10112 v2 | Included as preprint | No proceedings/journal venue recorded |
| [4] | Yang et al., PentestEval, arXiv:2512.14233 v2 | Included as verified arXiv record | Author-maintained pages report IEEE TIFS acceptance, but official IEEE bibliographic record was not verified; do not assert an IEEE DOI or final volume/pages |
| [5] | PENTESTLLMAGENT, IJCAI-26 | Included; DOI and official record verified in TASK 07.2 | Use official publisher record |
| [6] | ACL 2026 uncertainty paper | Included as Xuefeng Du, following published PDF | ACL metadata says Sean Du; published PDF says Xuefeng Du; disclose publisher metadata discrepancy, no correction to ACL record is claimed |
| [7] | OWASP WSTG v4.2 | Included as separately versioned 2020 release | Practitioner guide, not empirical paper |
| [8] | OWASP WSTG project page | Included as separate living page | Do not conflate with fixed v4.2 release |
| [9] | OWASP Benchmark project page | Included as living page | No AEGISCORE Benchmark experiment |
| [10] | OWASP Juice Shop project page | Included as living page | Not the synthetic E1 fixture |

All formal in-text identifiers [1]–[10] have bibliography entries. The bibliography entries [1]–[10] each have at least one in-text use. Internal project evidence [P1]–[P10] is not included as scholarly literature.

### 4.2 Candidate records not cited

| Candidate ID from TASK 07.2 | Record | Disposition |
|---|---|---|
| [11] | OWASP ZAP “Active Scan” documentation | Not cited. Retrieval failed in TASK 07.2; no ZAP comparison is claimed. Reverify from official docs if later needed. |
| [12] | LangChain “LangGraph overview” | Not cited. It is not evidence for AEGISCORE's custom FSM or passive route. |
| [13] | Chroma “Introduction” | Not cited. Chroma is not used on the supported passive assessment route. |

The candidate bibliography had 12 numbered entries, with its original [7] combining the versioned WSTG and a separate current project page. Splitting that entry gives 13 source records. No candidate is represented as cited merely to inflate the thesis reference list.

### 4.3 University identity/source correction

TASK 07.2 contains a note about a public template service for “NWU” that refers to South Africa's North-West University. TASK 07.3 identifies the institution as **North Western University, Khulna**. That earlier template-service finding is inapplicable to this thesis and does not verify the correct university's requirements. TASK 07.4 checked the official [NWU Khulna CSE page](https://www.nwu.ac.bd/dept_cse.php), [official forms page](https://www.nwu.ac.bd/form_n_download.php), and [research page](https://www.nwu.ac.bd/research.php); the inspected pages did not provide an undergraduate CSE thesis template or detailed submission rules. The separate [journal author guidelines](https://www.nwu.ac.bd/pdf/journal/Guidelines%20for%20Authors.pdf) were excluded because journal instructions do not establish undergraduate thesis requirements. Formatting compliance remains **NOT VERIFIED** pending department requirements.

## 5. Change control for thesis claims

Before release of any later thesis version:

1. Re-run the source-to-claim check for all new technical statements.
2. Record whether a number comes from a fixture, test suite, rerun, live provider, or deployment artifact.
3. Keep the exact denominator and date adjacent to every numeric result.
4. Verify the official PentestEval publisher record before changing its arXiv citation; retain the ACL discrepancy note and PDF-based “Xuefeng Du” author form unless ACL issues a correction.
5. Remove bibliography items with no supported in-text use.
6. Obtain the North Western University, Khulna template before claiming format compliance.
7. Do not convert application tests into OS egress, authority, production durability, or accuracy claims.

## 6. TASK 07.4 final thesis update

### User-communicated supervisor approval

The user confirmed that supervisor approval has been communicated. This fact is recorded in the final academic audit without a date, name, comments, signature, or written document. It does not represent administrative approval by the university, department, ethics body, or examination board.

### Final manuscript changes

- `AEGISCORE_THESIS_FINAL.md` is based on the TASK 07.3 thesis master draft and preserves its eight-chapter scope, research questions, objectives, and contribution boundary.
- The manuscript adds a content-only front-matter plan, contents, figure/table lists, abbreviations, numbered/captioned figures and tables, and substantive appendices A–G. The university template must still control final page order and formatting.
- The abstract, results, conclusion, and defense package retain the requested historical Python, fixture, evidence-link, and Flutter values. No task-local tests were rerun.
- Reference [6] uses “Xuefeng Du” per the published ACL PDF. The discrepancy with the ACL landing metadata (“Sean Du”) is documented in `TASK_07_4_FINAL_ACADEMIC_AUDIT.md`.
- Reference [4] remains the verified arXiv version. Publisher acceptance is reported on author-maintained pages, but official IEEE bibliographic metadata could not be verified; no publisher DOI is asserted.
- The final thesis uses a provisional bracketed numeric citation convention solely for internal consistency pending the university's required style. It is not represented as an NWU-approved style.

### Additional verification sources

| ID | Source | Use and limitation |
|---|---|---|
| P11 | Official [NWU Khulna CSE page](https://www.nwu.ac.bd/dept_cse.php), [Forms and Downloads](https://www.nwu.ac.bd/form_n_download.php), [Research page](https://www.nwu.ac.bd/research.php), and [journal guidelines PDF](https://www.nwu.ac.bd/pdf/journal/Guidelines%20for%20Authors.pdf) | Confirms target institution/program context and what public pages were inspected; journal guidelines are explicitly not applied as thesis rules. No undergraduate thesis template was verified. |
| P12 | [ACL metadata](https://aclanthology.org/2026.acl-long.738/) and [published ACL PDF](https://aclanthology.org/2026.acl-long.738.pdf) | Establishes the “Sean Du” versus “Xuefeng Du” discrepancy; use published PDF for bibliography per task instruction. |
| P13 | [PentestEval arXiv record](https://arxiv.org/abs/2512.14233), [first author's page](https://richael-y.github.io/), and [coauthor publications page](https://mingfeicheng.github.io/publications) | Supports versioned arXiv metadata and author-reported IEEE TIFS acceptance; official IEEE publication metadata remains unverified. |

### Readiness state

| Dimension | Status |
|---|---|
| Supervisor approval | Confirmed as communicated by user; no documentary approval record supplied |
| Academic content | Prepared; final typeset proof pending |
| NWU Khulna undergraduate formatting | Not verified |
| Administrative submission | Not ready/not verified |
| Live product deployment | Not ready |

The final thesis, checklist, defense package, and audit must stay synchronized with this matrix. Do not mark the work **FINAL SUBMISSION READY** until institutional requirements are verified and applied.

