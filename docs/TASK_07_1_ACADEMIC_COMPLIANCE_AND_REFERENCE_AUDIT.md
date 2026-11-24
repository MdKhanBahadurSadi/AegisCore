# TASK 07.1 — Academic Compliance, Citation Verification & Final Submission Audit

**Audit date:** 2026-11-24
**Starting documents:** `docs/TASK_07_0_THESIS_FINALIZATION.md` and `docs/TASK_07_0_THESIS_OUTLINE_AND_DEFENSE.md`
**External-source access date:** 2026-11-24
**Scope:** University requirements, proposal bibliography metadata, technical claim support, experiment traceability, and readiness gaps. No source or test files were changed.

## Readiness verdict

**CONDITIONAL — NOT READY FOR FINAL SUBMISSION.** The current documents provide a technically bounded thesis outline and defense plan, but they are not a formatted final thesis and contain no finished in-text citations or bibliography. No official university thesis guide, template, supervisor formatting instruction, or submission checklist was available in the repository. The proposal bibliography is a candidate list, not a validated thesis reference list. One ACL Anthology author-name discrepancy remains unresolved. The university's actual requirements and clarification of that source discrepancy are external dependencies.

The implementation and measurement claims are substantially traceable to current source files, tests, and the TASK 06.9 report. A new Python suite run and fixture rerun in this audit reproduced the recorded counts. The Flutter result remains historical: the current Flutter command did not return output or a result, so it was not verified again.

## 1. University requirements audit

Repository searches found the project proposal and a project-authored study/defense manual, but no institution-issued handbook, thesis template, supervisor instruction, or submission checklist. Neither project PDF is treated as an official university rule. No submission-format draft was made.

| Requirement | Current evidence | Audit status |
|---|---|---|
| Required chapter order and research structure | TASK 07.0 outline covers the 18 requested content areas. No institution-specific order was found. | **NOT VERIFIED** against university rules |
| Title page, declaration, approval, ethics/permission pages | Suggested as preliminary pages in the outline; no official wording, approvals, or signed materials are available. | **NOT VERIFIED**; do not invent approvals |
| Acknowledgements | Not drafted; whether required and its placement are unknown. | **NOT VERIFIED** |
| Abstract format and word limit | A draft abstract exists. No university word limit or required structured/unstructured format is available. | **NOT VERIFIED** |
| Table of contents and lists | The outline names these preliminary pages but contains no generated contents or lists. | **NOT VERIFIED** |
| Figure/table numbering and cross-references | Markdown tables and Mermaid diagrams are unnumbered. No official numbering/caption convention is known. | **NOT VERIFIED** |
| Heading hierarchy | Markdown heading levels are internally readable. Equivalence to the required chapter/section numbering is unknown. | **NOT VERIFIED** |
| Page numbering, margins, fonts, line spacing | Markdown source does not encode or evidence final page layout. No template is available. | **NOT VERIFIED** |
| Citation and bibliography style | The proposal shows a numbered candidate list; that does not establish the required style. The 07.0 documents have no completed bibliography or in-text citation system. | **NOT VERIFIED** |
| Appendices | TASK 07.0 proposes evidence, experiment, test, and security appendices. No university rules establish which are mandatory or how they must be formatted. | **NOT VERIFIED** |

**External dependency required:** provide the university's current thesis handbook or official template, plus any department/supervisor instructions for chapter order, required front matter, word limits, formatting, citations, appendices, and defense/submission rules. Until that is provided, no formatting-compliance claim is made.

## 2. Reference integrity audit

### Current thesis documents

The two TASK 07.0 Markdown documents contain a references-chapter placeholder and instructions to verify sources, but no final bibliography and no in-text scholarly citations. Their internal technical claims point to implementation and task-report artifacts. Therefore citation-to-bibliography consistency is **not assessable** for a submitted thesis, and all proposal bibliography entries are currently unused by these thesis documents.

The proposal PDF has 12 numbered entries; entry [7] combines two distinct OWASP sources and must be split. There are no exact duplicate titles among the numbered entries. The candidate list contains 13 underlying source records after splitting [7]. The list is not a final bibliography: publication details, document versions, and citation relevance need to be completed according to the university style. None of the 12 numbered candidates has an in-text citation in the TASK 07.0 thesis materials.

### Candidate bibliography records [1]–[12]

Publisher and primary-document pages were checked. “Verified” below means the cited metadata was compared with the linked publisher/project record; it does not mean that the source has been read and synthesized into a literature review.

| No. | Metadata audit | Correction or final-thesis action | Status |
|---:|---|---|---|
| 1 | Deng et al., “PentestGPT: Evaluating and Harnessing Large Language Models for Automated Penetration Testing,” 33rd USENIX Security Symposium (USENIX Security 24), 2024, pp. 847–864. The official USENIX record supplies the complete ten-author list, ISBN and publisher. No DOI is listed in that record. | Existing title/year/pages are correct. Use the official USENIX citation record; do not add a DOI unless independently verified. [USENIX record](https://www.usenix.org/conference/usenixsecurity24/presentation/deng) | **VERIFIED metadata** |
| 2 | Isozaki, Shrestha, Console, and Kim, “Towards Automated Penetration Testing: Introducing LLM Benchmark, Analysis, and Improvements,” arXiv:2410.17141. arXiv records v1 on 2024-10-22 and current v4 on 2025-02-21, and an arXiv-issued DOI. No journal or conference venue is listed on the record. | Cite as an arXiv preprint, identify version/access date if needed, and do not imply peer-reviewed proceedings without a separate publication record. [arXiv record](https://arxiv.org/abs/2410.17141) | **VERIFIED metadata** |
| 3 | Happe and Cito, “Benchmarking Practices in LLM-driven Offensive Security: Testbeds, Metrics, and Experiment Design,” arXiv:2504.10112. arXiv records v1 on 2025-04-14 and v2 on 2025-06-16, with an arXiv-issued DOI. No journal or conference venue is listed on the record. | Cite as a preprint and add its current version/DOI where the required style allows. [arXiv record](https://arxiv.org/abs/2504.10112) | **VERIFIED metadata** |
| 4 | Yang, Cheng, Deng, Zhang, Wang, and Xie, “PentestEval: Benchmarking LLM-based Penetration Testing with Modular and Stage-Level Design,” arXiv:2512.14233. The current arXiv record is v2, revised 2026-11-02, and provides an arXiv-issued DOI. No conference/journal venue is listed. | Existing title, author order, year and arXiv identifier are supported. Mark as a preprint, not a conference publication. [arXiv record](https://arxiv.org/abs/2512.14233) | **VERIFIED metadata** |
| 5 | Sheng, Zhang, Yang, Cheng, and Qin, “PENTESTLLMAGENT: A Task Dependency Graph Planning-Based Multi-Agent Framework for Automated Penetration Testing,” IJCAI-26, AI4Tech special track, 2026, pp. 6518–6527, DOI 10.24963/ijcai.2026/725. | Existing title, year, venue and page range are correct; add the DOI and full author list. [IJCAI record](https://ijcai.org/proceedings/2026/725) | **VERIFIED metadata** |
| 6 | “Uncertainty Quantification in LLM Agents: Foundations, Emerging Challenges, and Opportunities,” ACL 2026, pp. 16219–16250, DOI 10.18653/v1/2026.acl-long.738. ACL Anthology landing metadata lists Changdae Oh, Seongheon Park, To Eun Kim, Jiatong Li, Wendi Li, Samuel Yeh, **Sean Du**, Hamed Hassani, Paul Bogdan, Dawn Song, and Sharon Li. Searchable text for the attached paper PDF gives **Xuefeng Du** instead. The Anthology says its PDF is authoritative, so this author identity is unresolved. | Do not silently normalize the author name. Check the PDF image/author correction or obtain clarification from the publisher/authors before finalizing this entry. The title, venue, year, pages and DOI are otherwise recorded by ACL. [ACL Anthology record](https://aclanthology.org/2026.acl-long.738/), [paper PDF](https://aclanthology.org/2026.acl-long.738.pdf) | **CORRECTION REQUIRED** |
| 7a | OWASP Foundation, *Web Security Testing Guide*, version 4.2. OWASP's release page dates v4.2 to 2020-12-03. The proposal combines this with “current project documentation” in one entry. | Split into a versioned v4.2 citation and a separate project-page citation only if the latest guide is also used. Avoid citing the moving “latest” page when making a version-specific statement. [OWASP release history](https://wstg.owasp.org/downloads/) | **CORRECTION REQUIRED: split entry** |
| 7b | OWASP Foundation, *Web Security Testing Guide* project page. The current project page says v5.0 is in development and lists v4.2 among versioned releases. No individual author/year/volume/page metadata is supplied as for a paper. | Treat as a living web document; include retrieval date and a stable version URL when supporting a version-specific claim. [OWASP project page](https://owasp.org/projects/web-security-testing-guide) | **VERIFIED as a separate web source** |
| 8 | OWASP Foundation, OWASP Benchmark project page. The current page describes a Java/Python test suite for vulnerability-detector speed and accuracy; the proposal does not provide a publication year, version, or specific source document. | Cite as an undated project webpage with access date and version/release if the thesis refers to a particular benchmark snapshot. No Benchmark experiment was run for AEGISCORE. [OWASP Benchmark](https://owasp.org/projects/benchmark) | **CORRECTION REQUIRED: identify snapshot/use** |
| 9 | OWASP Foundation, *OWASP Juice Shop* project page. It describes a deliberately insecure training application. The page is a live project page with changing release metadata, not a fixed scholarly publication. | Add access date and exact release only if a particular version is part of a method or fixture. Do not imply the TASK 06.9 synthetic header fixture was a Juice Shop response. [OWASP Juice Shop](https://owasp.org/projects/juice-shop) | **CORRECTION REQUIRED: version/use** |
| 10 | OWASP ZAP, “Active Scan” documentation. The official page states that active scanning sends known attacks, should only target systems owned/authorized by the operator, and has limited vulnerability coverage. It has no journal/conference metadata. | Cite the exact documentation page as a living software document with retrieval date; remove “by Checkmarx” unless the selected source explicitly supports that publisher attribution. No ZAP baseline was run for this thesis. [ZAP Active Scan docs](https://www.zaproxy.org/docs/desktop/start/features/ascan/) | **CORRECTION REQUIRED: normalize source/title** |
| 11 | LangChain documentation, “LangGraph overview.” The current official page describes graph/state orchestration, durable execution, streaming and human-in-the-loop features; no publication year or version is presented. | Use as an undated documentation page with an access date only for a comparison/background claim. AEGISCORE's custom FSM is not LangGraph and this page is not implementation evidence. [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) | **VERIFIED metadata; unused** |
| 12 | Chroma documentation, “Introduction.” The official page describes document/metadata storage, embeddings and vector search. No named author, publication year or version is presented. | Cite as an undated software-documentation page with access date if relevant. The current assessment path does not use Chroma; do not imply it is an implemented assessment dependency. [Chroma docs](https://docs.trychroma.com/) | **VERIFIED metadata; unused** |

### Citation/reference findings

- **In-text citations missing from bibliography:** no formal in-text citations appear in the TASK 07.0 outline/audit; therefore a citation-to-reference match cannot be performed yet.
- **Bibliography entries not cited in thesis:** all 12 numbered proposal entries are unused in the TASK 07.0 thesis documents. Their future relevance is undecided.
- **Missing references:** the thesis has no finished bibliography. A source-based literature review must be built before stating a literature gap or making external research claims.
- **Duplicate entries:** no exact duplicate among the 12 numbered candidate items. Entry [7] contains two different records and should be split; overlap in topic is not duplication.
- **Claims needing primary sources:** literature claims about LLM security testing, benchmark validity, prompt injection, passive security-header interpretation, and uncertainty measurement need cited primary studies/standards after the relevant works have been read. This audit does not infer a literature gap from the candidate list.
- **Unsupported field-wide claims:** none should be added. The TASK 07.0 documents correctly state that a systematic literature review has not established a field-wide research gap.

## 3. Technical claim verification

| Thesis claim | Implementation | Experiment/test | Evidence source | Limitation |
|---|---|---|---|---|
| A custom FSM exists, but does not orchestrate passive API assessments. | `aegiscore/orchestration.py` defines `OrchestrationStateMachine`; `aegiscore/api/routes.py` calls the passive detector/executor directly. | Full Python suite; separate offline workflow tests are not evidence for passive API behavior. | TASK 06.9 evaluation and source trace. | Describe FSM/RAG as a separate subsystem; do not connect it to the passive API diagram. |
| Assessment target requests are numeric-loopback, endpoint-bound, and one passive `HEAD`. | `aegiscore/target_authorization.py`, `production_execution.py`, and `execution.py` enforce registration, exact endpoint/method constraints, connected-peer verification, bounded timeout, no redirect following, and no body read. | Passive pipeline, authorization, and guarded execution tests. | TASK 06.9 evaluation; `tests/test_passive_pipeline.py`, `tests/test_assessment_execution_api.py`, `tests/test_authorization_verification.py`. | This is application-level behavior in represented tests, not OS-level egress isolation. The API also has read-only `GET` history/detail routes; the HEAD-only restriction applies to target execution. |
| Target authorization is checked fail-closed. | An `AuthorizationVerifier` protocol validates verifier evidence; the executor rechecks the binding around dispatch. | Synthetic verifier cases cover invalid, expired, revoked, unknown-issuer, unavailable, and malformed states. | `aegiscore/authorization_verification.py`, `aegiscore/production_execution.py`, TASK 06.9 evaluation. | No trusted authority/issuer or production verifier is configured in the standard launcher. Say “tested with injected verifier,” not “production authorization is operational.” |
| Detector findings are deterministic header-configuration observations. | `aegiscore/passive_detector.py` applies fixed rules for CSP, MIME-sniffing protection, framing, Referrer Policy, and HTTPS HSTS. | One synthetic fixture, 100 calls; 1 normalized set and 5 observations per call. | `scripts/task_06_9_fixture_experiments.py`, TASK 06.9 evaluation. | No independent labeled dataset; no general vulnerability accuracy claim. |
| Evidence links are valid for the measured fixture. | Findings carry assessment/evidence IDs derived from normalized response evidence. | Audit rerun: 500/500 reference-membership checks passed. | Current audit rerun and TASK 06.9 evaluation. | Membership proves identifier linkage only, not semantic truth or sufficient evidence. |
| AI review is advisory and constrained. | `aegiscore/assessment_ai.py` validates output shape, IDs, evidence ownership, claim language and size; route stores advisory separately. Reviewer injection is opt-in. | Reviewer fixtures: valid ref 1/1; invalid refs 3/3; unsupported/unqualified claims 2/2; abstention 1/1; schema valid 1/1/invalid 2/2; API failures 4/4 and repeated failures 5/5. | `tests/test_assessment_ai_integration.py`, `docs/TASK_06_6_ADVISORY_REVIEWER_EVALUATION.md`, TASK 06.9 evaluation. | Fake adapter only; lexical checks do not prove semantic grounding, complete prompt-injection resistance, or model quality. |
| Authentication and assessment permission checks exist. | `aegiscore/api/auth.py` uses Argon2id password hashes and in-memory bearer sessions; routes separately check session permissions for assessment create/execute/read. | API/auth tests in historical and current Python suites. | `aegiscore/api/auth.py`, `aegiscore/api/routes.py`, TASK 06.8/06.9 reports. | Deployment credentials/session configuration and browser runtime are not live-accepted; user authentication does not replace target authorization. |
| SQLite persistence protects terminal state and results. | `aegiscore/local_persistence.py` uses SQLite transactions for result persistence, lease ownership/expiry, renewal and recovery. | Transaction rollback, genuine two-assessment rollback, lease, restart and in-process recovery tests. | TASK 06.3/06.9 reports; `tests/test_assessment_lifecycle_recovery.py`, `tests/test_passive_pipeline.py`. | Temporary test databases are not production volume, backup, restore, permissions, or durability evidence. |
| Prompt-injection risks from evidence are bounded but not eliminated. | Evidence is untrusted, allowlisted/redacted and passed under policy; reviewer responses undergo schema/reference/claim validation. | Adversarial evidence/prompt-injection and failure fixtures in reviewer tests. | `aegiscore/assessment_ai.py`, `tests/test_assessment_ai_integration.py`, TASK 06.6 report. | No live model was evaluated; no semantic immunity claim is supported. |
| Recovery is available without application restart after storage returns. | `aegiscore/api/app.py` starts a bounded periodic recovery worker; `LocalRecordStore` rechecks stale leases transactionally. | Persistence failure followed by in-process recovery test. | TASK 06.9 evaluation and `tests/test_passive_pipeline.py`. | Recovery depends on storage availability and lease expiry; it is bounded, not immediate after every database failure. |
| OS-level outbound isolation is enforced. | No live Linux namespace/firewall rule execution is evidenced in this environment. | TASK 06.4.4 remains deferred; no Debian 13 firewall test was run. | `docs/TASK_06_4_4_LIVE_LINUX_ISOLATION_REPORT.md`, TASK 06.9 evaluation. | **Not verified.** Do not claim OS/container egress isolation. |

### Wording correction to carry into the final thesis

The TASK 07.0 readiness document says the system “accepts a registered, explicitly authorized numeric loopback endpoint.” This needs to be read together with its adjacent limitation: the normal launcher has no production verifier. Prefer the precise formulation “the tested execution path permits the registered endpoint when a verifier is injected and its evidence passes validation.” This is a qualification, not a change to the implementation claim.

## 4. Experimental evidence audit

| Claim | Original evidence | Audit rerun | Correct interpretation |
|---|---|---|---|
| 100 fixture calls produced one normalized complete finding set, with 5 findings per call. | TASK 06.9 report and reproducible script. | **100 calls; 1 distinct normalized set; 5 findings/call.** | Repeatability for one synthetic input, not 100 independent targets. |
| 500/500 finding evidence references were valid. | TASK 06.9 report. | **500/500** identifier-membership checks passed. | Reference membership only, not factual correctness or semantic support. |
| Fixture processing elapsed time. | TASK 06.9 recorded 9.099 ms total / 0.091 ms per call. | **9.273 ms total / 0.093 ms per call** in this run. | Local script timing; run-to-run variation is expected. Not network, target, or model latency. |
| Fake-adapter timing comparison. | TASK 06.9: 20 warmups/path, 250 paired samples; detector-only median/mean/P95 0.0233/0.0236/0.0267 ms; detector plus fake reviewer 0.5087/0.5100/0.5256 ms; median increment 0.4854 ms. | This audit: 20 warmups/path, 250 paired samples; detector-only 0.0235/0.0239/0.0268 ms; detector plus fake reviewer 0.5111/0.5118/0.5265 ms; median increment 0.4876 ms. | Fake-adapter local Python cost only. Do not state a live model/provider latency or calibrated performance claim. |
| TASK 06.9 full Python regression result. | TASK 06.9 report: **863 collected, 863 passed, 0 failed, 0 skipped; 47.26 s pytest time.** TASK 06.8.3 records another 863-test run at 45.43 s pytest / 47.58 s wall. | **863 passed, 0 failed, 0 skipped; 44.66 s pytest time and 46.85 s command wall time** (`python -m pytest -q`, 2026-11-24). | Counts agree. Durations are separate runs and must not be merged. This audit rerun is current-worktree evidence, not a historical 06.9 duration. |
| Flutter suite result. | TASK 06.8 report: **60 collected, 59 passed, 0 failed, 1 skipped**; the skip was an environment-gated older E2E test without its fixture bundle. | Not completed. `flutter test --reporter compact` returned no output/result; `flutter --version` also did not return output. Both probes were interrupted. | Keep 59/1 as historical only. Current Flutter tests, analyzer, and build are **NOT VERIFIED** in this audit. |
| Live model, authorized target, and Linux isolation. | TASK 06.9 records no provider, production approval, or Debian 13 isolation run. | Not run. | Zero provider-generated evaluation samples; no live authorization or OS-isolation evidence. |

The fixture script prints results to stdout and does not save a raw JSON artifact. The TASK 06.9 report contains the historical values; this audit records the actual rerun values above. Do not describe 100 repetitions of one fixture as a benchmark, population sample, detection rate, precision, recall, false-positive rate, or accuracy estimate.

## 5. Final submission content review

- **Structure:** all 18 requested content areas are represented in the outline. The outline is a content plan, not proof that the final thesis contains complete chapters.
- **Transitions:** the proposed order is coherent; the final thesis must connect the narrowed problem, implementation-bounded questions, methods, results, and limitations after a literature review is written.
- **Figures/tables:** current diagrams and markdown tables are unnumbered. Add institution-compliant captions, numbering, and in-text references only after obtaining the template.
- **Terminology:** keep “deterministic finding/configuration observation,” “evidence-reference membership,” “AI advisory,” “injected verifier,” and “OS-level egress isolation” distinct. Do not use “vulnerability detection accuracy” for fixture repeatability.
- **Abbreviations:** provide a glossary and expand abbreviations at first use, including API, FSM, HTTP, LLM, RAG, and SQLite where applicable. The requested abbreviation policy is not known.
- **Citations:** the final literature review is not yet present. Cite each external research/standards claim at the point of use and make the reference list match the chosen style. The project’s internal test reports belong in methodology/appendices as project evidence, not as peer-reviewed literature.
- **Results and limitations:** retain clear labels for synthetic fixture, automated tests, historical Flutter run, current audit rerun, live model evaluation, and deployment evidence. No live model results, benchmark comparison, real-world detection accuracy, or Debian 13 egress evidence exist.
- **Grammar and consistency:** no broad stylistic rewrite is required. Correct only the verifier-availability ambiguity above, the source metadata issues in [6]/[7], and the publication metadata/source type issues in the candidate bibliography.

## 6. Prioritized correction checklist

### P0 — Required before claiming submission compliance

- [ ] Obtain the current official university thesis handbook/template and supervisor/department instructions. Confirm front matter, chapter order, abstract word count/format, citation style, page layout, numbering, appendices, and defense/submission rules.
- [ ] Resolve the ACL Anthology [6] author-name discrepancy using the publisher/author correction process. Do not choose between “Sean Du” and “Xuefeng Du” without confirmation.
- [ ] Build an actual literature review and in-text citation system; verify that every cited source appears in the bibliography and every bibliography item is used or justified.
- [ ] Do not claim the original proposal's broad multi-agent/RAG research gap as established. Keep the gap conditional on a source-based review.

### P1 — Required for reference and claim integrity

- [ ] Split proposal entry [7] into versioned WSTG v4.2 and the current WSTG project page, if both are needed.
- [ ] Complete entries [2]–[6] with authoritative current versions/DOIs and the appropriate source type (conference proceedings versus arXiv preprint).
- [ ] Normalize web-document entries [8]–[12] with organization/title, exact version when relevant, URL, and access date; remove unused product documentation from the final bibliography.
- [ ] Insert the injected-verifier qualification wherever the thesis describes target authorization; distinguish test fixtures from production authority.
- [ ] Keep the evidence-link, reviewer, and timing claims tied to their denominators and explicitly limit them to the selected fixtures.
- [ ] Add the claim-to-evidence matrix to the final thesis appendix or retain it as an audit artifact.

### P2 — Required after template is supplied

- [ ] Map the outline to official heading and chapter numbering; format title, approval/declaration, acknowledgements, abstract, contents, and appendices only as prescribed.
- [ ] Apply required margins, font, line spacing, page numbering, caption style, table/figure numbering, and cross-references.
- [ ] Add abbreviation definitions and check terminology consistency after typesetting.
- [ ] Proofread the final rendered PDF, verify references/links and contents page numbers, then freeze the exact submitted copy.
- [ ] If updated implementation or Flutter verification is claimed, rerun and archive the exact test/analyzer/build output; do not reuse historical results as current evidence.

## Repository safety and verification record

Initial `git status --short` before this audit's document was created: **118 entries** — 35 deleted, 26 modified, 57 untracked. This included pre-existing user changes, including `uv.lock`, backend/frontend files, tests and documentation. The audit added only this Markdown document; no source, test, Flutter, or lockfile content was changed. No destructive Git command, staging, or commit was used. No byte-for-byte preservation claim is made.

The full Python suite and fixture script were rerun as recorded above. Flutter testing did not complete. Final `git status --short`: **119 entries** — 35 deleted, 26 modified, 58 untracked; the only task-created untracked path is this audit document. `git diff --check` exited 0 and emitted only pre-existing LF-to-CRLF notices for modified files; the new untracked audit document was separately checked and has no trailing whitespace. Temporary PDF preview files were removed. No destructive Git command, staging, or commit was used.
