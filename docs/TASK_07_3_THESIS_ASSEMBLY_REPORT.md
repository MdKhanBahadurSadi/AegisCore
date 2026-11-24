# TASK 07.3 — Thesis Assembly Report

**Date:** 2026-11-24

**Outcome:** **Supervisor-review draft prepared; final academic submission readiness remains CONDITIONAL.**

## 1. Scope and result

This task assembled a source-grounded thesis master draft from the current implementation and existing TASK 07.0, 07.1, 07.2, and 06.9 materials. It also prepared a claim-to-evidence matrix and a supervisor review package, and updated the existing defense preparation document with a timed 10-minute outline. No backend, frontend, tests, deployment configuration, lockfiles, or product scope were changed.

The documents present AEGISCORE as the narrow passive assessment prototype supported by current code: registered numeric-loopback endpoint binding; a guarded single HTTP `HEAD`; deterministic header-configuration observations; optional non-authoritative advisory review; and lease-checked SQLite persistence and recovery in tested paths. The offline custom FSM/RAG subsystem is explicitly separated from the passive API route.

## 2. Source and implementation audit

### Sources reviewed

- `docs/TASK_07_0_THESIS_FINALIZATION.md` and `docs/TASK_07_0_THESIS_OUTLINE_AND_DEFENSE.md`.
- `docs/TASK_07_1_ACADEMIC_COMPLIANCE_AND_REFERENCE_AUDIT.md`.
- `docs/TASK_07_2_LITERATURE_REVIEW_AND_RESEARCH_GAP.md`.
- `docs/TASK_06_9_THESIS_EVALUATION.md` and `scripts/task_06_9_fixture_experiments.py`.
- TASK 06.7/06.8/06.8.3 Flutter and live-acceptance reports.
- Current API route, auth, target registry, authorization verifier, production execution, guarded execution, HTTP execution, detector, reviewer, SQLite persistence, and recovery worker code.
- Current tests for authorization, guarded execution, passive pipeline, assessment API, advisory review, leases, transactions, and recovery.
- Read-only committed versions of `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, and `docs/THREAT_MODEL.md` using Git object reads because those paths are deleted in the current worktree as pre-existing changes. No files were restored.

### Key architecture corrections

- The passive assessment API directly composes the authorized executor, evidence normalization, deterministic header detector, optional reviewer, and persistence layer. The custom FSM and RAG-related workflow are separate and are not the passive API orchestrator.
- The API verifies a registered exact endpoint and verifier evidence at creation and again around execution. The repository defines a verifier contract, but the evaluated normal launcher has no real trusted issuer/verifier integration. Synthetic verifier tests are not live authorization evidence.
- Target execution is numeric loopback only and uses a single passive HTTP `HEAD`, bounded timeout, disabled redirect following, allowlisted headers, no response-body read, and connected-peer checking. These are application controls, not OS-level egress isolation.
- The advisory reviewer is opt-in through backend configuration/injection, not a client-side per-assessment toggle in the existing Flutter API contract. It remains separate from official deterministic findings and cannot alter severity or terminal status.
- SQLite tests cover transaction rollback, a genuine two-assessment recovery rollback, lease validation, restart recovery, and recovery without restarting after storage availability returns. These tests do not establish production volume durability or backup/restore behavior.

## 3. Literature and citation audit

The TASK 07.2 review of 12 candidate bibliography entries was carried forward, separating its combined OWASP entry into two distinct sources, for 13 records total. The master draft cites only candidate records [1]–[10] that support its claims. Candidate [11] (ZAP Active Scan) was not retrieved in TASK 07.2 and is not cited; [12] LangGraph and [13] Chroma are not used in the implemented passive route and are omitted from the thesis bibliography. They remain accounted for in the evidence traceability file.

Two source issues remain explicit:

1. The ACL 2026 paper's seventh author is “Sean Du” in ACL metadata and “Xuefeng Du” on the PDF title page. The discrepancy is unresolved; the draft does not select a name.
2. PentestEval is cited to the verified arXiv record. The PDF formatting suggests an IEEE TIFS manuscript, but the publisher landing metadata was not verified in TASK 07.2; no unverified publisher DOI is used.

The numeric citation IDs are editorial cross-references, not a chosen citation style. All used in-text references match the provisional bibliography; no unused candidate source is listed as cited. The reference metadata and source links remain subject to final publisher/source verification and the university's required style.

### University identity correction

The correct institution for this draft is **North Western University, Khulna**. TASK 07.2 included a template-service note for **North-West University in South Africa**. That template service is not applicable and does not establish any requirement for North Western University, Khulna. No official North Western University, Khulna thesis template, department handbook, or supervisor instruction was present in the inspected repository. Formatting, chapter order, declarations, abstract limits, citation style, layout, numbering, and appendices therefore remain **NOT VERIFIED**.

## 4. Quantitative evidence handling

The master draft and traceability matrix preserve the historical TASK 06.9 figures with denominators and limitations:

- One synthetic HTTPS observation called 100 times: one normalized finding set, five findings per call, and 500/500 finding/evidence identifier-membership checks.
- Reviewer fixture metrics: valid references 1/1; invalid references 3/3; unsupported-claim cases 2/2; insufficient-evidence abstention 1/1; valid schema 1/1; invalid schemas 2/2; API failure isolation 4/4; repeated failure isolation 5/5.
- Local timing with a scripted fake adapter: detector median 0.0233 ms; combined median 0.5087 ms; median difference 0.4854 ms after 20 warmups and 250 paired samples.
- Historical TASK 06.9 focused Python run: 175 collected/passed, 0 failed/skipped, 21.53 seconds. Full run: 863 collected/passed, 0 failed/skipped, 47.26 seconds. Six-test fixture demonstration: 6 passed, 0 failed/skipped, 3.56 seconds.
- Historical TASK 06.8 Flutter result: 60 collected, 59 passed, 0 failed, 1 skipped; analyzer reported zero issues and Web build succeeded. It was not rerun for TASK 07.3. A TASK 07.1 Flutter attempt did not yield a completed result and is not treated as passing.
- Live model-generated samples: zero. Production-authorized target runs: zero. Debian 13 live egress runs: zero/deferred.

No tests were run for TASK 07.3. This milestone changed academic Markdown documents only, and the historical test results are presented as prior evidence, not new verification. Fixture repeatability is not real-world detection accuracy; the 500 links are not independent evidence cases; fake-adapter timing is not model latency.

## 5. Deliverables created or updated

| File | Result |
|---|---|
| `docs/AEGISCORE_THESIS_MASTER_DRAFT.md` | Complete supervisor-review draft with preliminary placeholders, eight coherent chapters, current architecture diagrams, experimental methods/results, limitations, provisional bibliography, and appendix plan. |
| `docs/TASK_07_3_THESIS_EVIDENCE_TRACEABILITY.md` | Claim-to-code/test/source/limitation matrix, quantitative ledger, reference consistency audit, unused candidate disposition, and university identity correction. |
| `docs/TASK_07_3_SUPERVISOR_REVIEW_PACKAGE.md` | Scope summary, proposed contribution/questions, chapter map, feedback requests, open decisions, evidence snapshot, and supervisor checklist. |
| `docs/TASK_07_0_THESIS_OUTLINE_AND_DEFENSE.md` | Updated with exactly 10 minutes of timed slides and a fixture-only demo note. Existing likely examiner questions remain evidence-qualified. |
| `docs/TASK_07_3_THESIS_ASSEMBLY_REPORT.md` | This audit and repository-status record. |

No PDF/typeset final submission was generated because the correct official template and supervisor/department requirements are unavailable.

## 6. Prioritized correction checklist

### P0 — Before claiming academic compliance

- Obtain the current official North Western University, Khulna template and department/programme/supervisor requirements.
- Confirm title, chapter structure, preliminary pages, abstract format/limit, citation style, numbering, layout, ethics/permission statements, appendix requirements, and defense duration.
- Obtain supervisor decisions on the narrowed research framing, objectives, research questions, and whether current fixture/test evidence is academically sufficient.
- Resolve the ACL author discrepancy and verify final PentestEval publisher metadata through authoritative channels.

### P1 — Before finalizing thesis claims

- Apply the approved citation style and regenerate bibliography/cross-references.
- Remove or qualify any statement not supported by the traceability matrix.
- If the supervisor requires empirical detection-performance claims, create a permissioned, independently adjudicated response dataset and define a protocol before collecting results.
- Keep live authority, model, browser deployment, persistent storage, and Debian egress limitations explicit until actual acceptance evidence exists.

### P2 — Before submission and defense

- Typeset using the correct university template only after it is supplied.
- Verify figure/table numbering, contents, abbreviations, citations, and page references in the rendered output.
- Re-run and archive any test, analyzer, or build result that will be described as current at submission time.
- Rehearse the 10-minute outline and keep any demonstration clearly labeled as fixture-based unless a genuinely authorized live deployment is later accepted.

## 7. Repository safety and verification

### Initial status

Initial `git status --short` was captured before document edits: **120 entries** — 35 deleted, 26 modified, and 59 untracked. The pre-existing worktree included source, frontend, tests, reports, deletions, and an existing `uv.lock` modification. These items were preserved. `uv.lock` was not edited.

### Final status

Final `git status --short`: **124 entries** — 35 deleted, 26 modified, and 63 untracked. Four new untracked documents were added for this task: the master draft, evidence traceability matrix, supervisor review package, and assembly report. The existing untracked defense outline was updated in place. No other worktree path was intentionally changed.

### Checks

- `git diff --check`: passed with only the repository's existing non-fatal LF-to-CRLF working-copy notices for pre-existing modified files, including `uv.lock`.
- Newly created Markdown files were scanned for trailing whitespace; the pre-existing defense outline contains old trailing spaces outside the new timed-outline section, which were left untouched.
- Backend and Flutter tests were not rerun for this documentation-only task. Historical results are labeled as historical throughout.
- No destructive Git commands, staging, commits, source-code edits, Flutter edits, or lockfile edits were made.

## 8. Readiness verdict

**CONDITIONAL — supervisor review draft ready, final submission readiness not verified.** The thesis content is organized around implemented behavior and traceable evidence, and its claim language preserves limitations. It cannot be called formatted or submission-ready until North Western University, Khulna requirements are supplied, the outstanding citation discrepancies are resolved or dispositioned by the supervisor, and any additional academic evidence the supervisor requires is completed. Debian 13 egress verification remains deferred, and no live deployment or real-world accuracy claim is made.

