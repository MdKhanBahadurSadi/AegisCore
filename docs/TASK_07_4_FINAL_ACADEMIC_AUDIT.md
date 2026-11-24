# TASK 07.4 — Final Academic Audit

**Audit date:** 24 November 2026<br>
**Target institution:** North Western University, Khulna, Bangladesh<br>
**Baseline:** `docs/AEGISCORE_THESIS_MASTER_DRAFT.md` and the TASK 07.3 assembly, review, and evidence-traceability documents<br>
**Result:** Content and evidence are consolidated in `docs/AEGISCORE_THESIS_FINAL.md`; university formatting and administrative submission readiness remain unverified.

## 1. Approval record and baseline

The user has confirmed that the thesis work has supervisor approval. This audit records that approval as **communicated by the user**. It does not add a supervisor's name, comments, signature, approval date, or written record. No university, department, ethics, or examination-board approval is represented as complete.

The latest assembled thesis baseline is the TASK 07.3 master draft, which contained eight chapters, a bounded research contribution, historical experimental results, and explicit deployment limitations. The supervisor-review package and traceability matrix were used to preserve its approved research scope, objectives, questions, title, and contribution framing. The final manuscript is a focused preparation of that draft; it does not expand the product or research scope.

## 2. Institutional identity and requirements check

The target was checked against the official [North Western University Department of CSE page](https://www.nwu.ac.bd/dept_cse.php) and [Faculty of Science and Technology page](https://www.nwu.ac.bd/faculty_st.php), which identify the university in Khulna and its undergraduate CSE programme. The official [Forms and Downloads page](https://www.nwu.ac.bd/form_n_download.php) lists general academic forms. The official [Research page](https://www.nwu.ac.bd/research.php) gives broad research information. None of the inspected pages provided an applicable undergraduate CSE thesis template or a detailed submission guide.

The university's separate [Journal Guidelines for Authors](https://www.nwu.ac.bd/pdf/journal/Guidelines%20for%20Authors.pdf) describe journal-manuscript rules. They are **not applied** to this undergraduate thesis and do not establish thesis requirements. The South African North-West University template service previously mentioned in Task 07.2 is not applicable to the target institution.

| Requirement area | Verification result | Audit treatment |
|---|---|---|
| Approved undergraduate CSE thesis template | **Not verified** | Request the current template from the NWU Khulna CSE department. |
| Title page wording and layout | **Not verified** | Title preserved; personal, degree, supervisor, and date fields remain placeholders. |
| Declaration and certification pages | **Not verified** | No institutional wording, signature, or certification is invented. |
| Abstract length, typography, and keywords | **Not verified** | A final content abstract and seven keywords are supplied; apply the official rule when obtained. |
| Chapter structure and numbering | **Not verified** | Existing eight-chapter structure preserved as a content baseline. |
| Font, margins, line spacing, and page numbering | **Not verified** | No layout values are claimed; page numbering must be generated in the official template. |
| Figure and table styles | **Not verified** | Captions and chapter-based numbering are supplied for transfer; visual rules remain pending. |
| Citation and bibliography style | **Not verified** | Use provisional bracketed numeric citations for consistency; this is not claimed as NWU style. |
| Appendices | **Not verified** | Appendices A–G are prepared as content; department requirements may change selection/order. |
| Ethics, permission, AI-use statement | **Not verified** | No human-subject or target-owner approval is claimed; insert genuine required statements only. |
| Submission, copies, binding, signatures, and deadline | **Not verified** | Obtain the current department/administrative checklist. |

## 3. Reference verification and disposition

### ACL 2026 author discrepancy

The [ACL Anthology landing metadata](https://aclanthology.org/2026.acl-long.738/) gives the seventh author as “Sean Du.” The published [ACL proceedings PDF](https://aclanthology.org/2026.acl-long.738.pdf) title page gives “Xuefeng Du.” Following the task instruction, the bibliography now uses **Xuefeng Du**, as printed in the published paper PDF. The mismatch remains documented as a publisher-metadata correction issue; no claim is made that ACL has amended its record.

### PentestEval publisher status

The [current arXiv record for PentestEval](https://arxiv.org/abs/2512.14233) verifies the versioned preprint and author list. The version 2 manuscript is styled for *IEEE Transactions on Information Forensics and Security*, and the [first author's page](https://richael-y.github.io/) and [coauthor publication listings](https://mingfeicheng.github.io/publications) report acceptance by that journal. An official IEEE bibliographic landing record could not be verified through the available publisher search/open path. Secondary search results surfaced publication metadata, but that metadata was not promoted into the bibliography without an authoritative record. The thesis therefore cites the verified arXiv record and does not assert an IEEE DOI, volume, issue, or page range. **Publisher verification remains pending.**

### Remaining reference audit

- The final thesis uses ten scholarly/documentary records: PentestGPT; two arXiv preprints; PentestEval's verified arXiv record; PENTESTLLMAGENT's official IJCAI proceedings record; ACL 2026; and four separate OWASP sources.
- PentestGPT is tied to the [USENIX proceedings record](https://www.usenix.org/conference/usenixsecurity24/presentation/deng). PENTESTLLMAGENT is tied to the [official IJCAI proceedings record](https://ijcai.org/proceedings/2026/725).
- OWASP records distinguish the versioned [WSTG 4.2 release](https://wstg.owasp.org/downloads/) from the [living WSTG project page](https://owasp.org/projects/web-security-testing-guide). OWASP Benchmark and Juice Shop are separate sources, not conflated entries.
- Bracketed references [1]–[10] in the final thesis match bibliography entries [1]–[10]. Internal project evidence IDs `[P1]`–`[P9]` are tracked separately and are not bibliography entries.
- Candidate ZAP, LangGraph, and Chroma records are excluded from the thesis bibliography because the final thesis does not rely on them. They remain recorded as unused candidates in Task 07.2.
- No DOI has been added where the cited authoritative record did not supply or verify one. No author, venue, finding, or publication detail has been fabricated.

## 4. Thesis quality assurance

### Research scope and claims

The final thesis preserves the approved title and bounded scope: a registered numeric-loopback passive HTTP-header workflow, one guarded `HEAD` request, deterministic configuration observations, optional non-authoritative advisory review, and tested SQLite lifecycle controls. The offline FSM/RAG subsystem is identified as separate from the passive API route. The literature gap is limited to the reviewed candidate set and is not framed as global novelty.

The final claim boundary excludes real-world accuracy, precision/recall, live Gemini or other provider quality, production authorization acceptance, browser-to-live deployment acceptance, and Debian 13 OS-level egress isolation. Evidence-ID membership is explicitly distinguished from semantic proof. Test counts are described as historical results, not security probabilities.

### Objective and result consistency

| Research question | Thesis result | Claim boundary |
|---|---|---|
| RQ1: repeated normalized output and identifier membership | One normalized set over 100 calls, five findings per call, 500/500 reference-membership checks | One synthetic observation; not accuracy or 500 independent cases |
| RQ2: advisory validator behavior | Represented valid/invalid references, claims, schemas, abstention, and failure-isolation cases behaved as recorded | Scripted fake adapter; small constructed denominators; no model-quality estimate |
| RQ3: authorization/execution/lifecycle invariants | Recorded tests exercised selected deny, rollback, lease, and recovery cases | Injected verifiers, controlled transports, and temporary SQLite; not production acceptance |
| RQ4: local reviewer-path processing time | Fake-adapter median was 0.5087 ms versus 0.0233 ms detector-only; median difference 0.4854 ms | One Windows run; excludes model and network latency |

The abstract, conclusions, discussion, limitations, defense outline, and examiner answers use these same results and limitations. No unsupported novelty or effectiveness claim was found in the final manuscript.

### Structure, language, and navigation

- Eight chapter headings and numbering are consistent with the current content baseline; institutional approval of the structure is still required.
- Figures are numbered Figures 4.1–4.2, have captions, and appear in the list of figures.
- Tables are numbered Tables 4.1, 6.1–6.4, and 7.1, have captions, and appear in the list of tables.
- The abbreviation list expands terms used in the text. The final formatted copy should regenerate the contents and page numbers.
- Appendices A–G now contain the protocol, fixture-case summary, historical results, data boundary, security/deployment state, traceability crosswalk, and document insertion rule. Their final selection/order is institution-dependent.
- Terminology distinguishes target authentication from target authorization, deterministic findings from advisory text, application restrictions from operating-system isolation, and evidence-ID membership from semantic entailment.
- No duplicate or contradictory quantitative claim was found in the final copy. Final proofing is still required after typesetting because Markdown has no final page layout or page-numbered cross-references.

## 5. Experimental evidence integrity

The final manuscript retains the requested evidence as historical:

| Evidence | Recorded result | Required interpretation |
|---|---|---|
| Python full regression | 863 passed, 0 failed, 0 skipped | Historical TASK 06.9 run; not rerun for TASK 07.4 |
| Fixture experiment | 100 calls; one normalized finding set | One synthetic HTTPS observation |
| Finding/evidence membership | 500/500 | Identifier membership, not semantic entailment or independent cases |
| Flutter regression | 59 passed, 1 skipped, 0 failed | Historical TASK 06.8 run |

No test, analyzer, or build result was rerun for this documentation task. No results are described as current execution evidence.

## 6. Required technical limitations retained

The final thesis and submission checklist retain these open matters: genuine authentication provisioning; an authoritative target-authorization verifier; persistent deployment configuration/storage; accepted browser-to-live API operation; a live model provider integration; Debian 13 operating-system egress verification; and Windows ACL/Linux permission verification. Supervisor approval does not close any of these deployment controls.

## 7. Final readiness verdict

| Readiness dimension | Verdict | Reason |
|---|---|---|
| Supervisor approval | **Confirmed as communicated by the user** | No supervisor document, date, or comments were provided. |
| Academic document content | **Prepared; final typeset proof pending** | Scope, results, references, appendices, figures/tables, and defense materials are aligned. |
| University formatting compliance | **Not verified** | Applicable undergraduate NWU Khulna CSE requirements/template were not found in official public materials inspected. |
| Administrative submission readiness | **Not ready / not verified** | Required forms, signatures, policies, binding, and submission procedure remain unknown. |
| Live product deployment readiness | **Not ready** | Authentication, authority, deployment, browser acceptance, provider, OS egress, and permission checks remain open. |

**Final verdict: CONDITIONAL ACADEMIC CONTENT READY; NOT FINAL SUBMISSION READY.** Do not mark the thesis as submission-ready until the official NWU Khulna CSE requirements and all applicable administrative items are verified and applied.

## 8. Repository record

The initial `git status --short --branch` was captured before edits: 124 entries (35 deleted, 26 modified, 63 untracked), consistent with the TASK 07.3 end-state. It included pre-existing source, frontend, tests, and documentation changes, plus an existing modified `uv.lock`. The final snapshot contains 128 entries (35 deleted, 26 modified, 67 untracked); the four additional untracked paths are the requested final thesis, academic audit, submission checklist, and defense package. The existing traceability document was updated in place and was already untracked. No pre-existing status entry was intentionally changed. Source code, tests, deployment files, and `uv.lock` were not changed; nothing was staged or committed.

`git diff --check` exited 0. Git emitted only existing LF-to-CRLF working-copy notices for pre-existing modified files, including `uv.lock`. A separate trailing-whitespace scan found no trailing whitespace in the four new deliverables or the updated traceability file. No automated tests were run.
