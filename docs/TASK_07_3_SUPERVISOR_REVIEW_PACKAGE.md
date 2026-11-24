# TASK 07.3 — Supervisor Review Package

- **Status:** Prepared for supervisor feedback; not submitted and not formatted as a final university document.
- **Institution identified for this draft:** North Western University, Khulna.
- **Student / department / programme / supervisor:** [Complete from confirmed records].

## 1. Review summary

The accompanying master draft documents the AEGISCORE implementation that can be supported by current source code and recorded evidence: a registered numeric-loopback passive HTTP `HEAD` workflow, deterministic security-header configuration observations linked to evidence IDs, an optional non-authoritative advisory reviewer, and SQLite lifecycle controls. The literature review and research-gap argument are limited to the selected sources audited in TASK 07.2. The evaluation reports fixture behavior and automated tests, not real-world detection accuracy.

The draft intentionally narrows the original proposal. A custom FSM and offline RAG-related code exist in the repository but do not orchestrate the passive assessment API. No live model provider, production authorization authority, authenticated browser-to-API assessment, or Debian 13 operating-system egress verification is claimed. TASK 06.4.4 remains deferred.

## 2. Proposed project framing for review

**Working title:** *AEGISCORE AI: A Bounded Passive Assessment Prototype with Evidence-Linked Findings and Advisory Review*

**Working aim:** document and evaluate the current local passive-assessment workflow, focusing on endpoint binding, deterministic evidence-linked observations, optional advisory constraints, and persistence lifecycle controls.

**Proposed contribution statement:** the project implements and evaluates a narrowly scoped integration of target binding, guarded passive HTTP observation, deterministic security-header configuration findings, evidence-reference checks, optional advisory interpretation, and lease-checked persistence/recovery. It makes no claim of a novel detection algorithm, calibrated uncertainty, improved accuracy, or superiority over existing tools.

**Current research questions:**

1. Does one fixed synthetic header observation produce the same normalized output and valid identifier links over 100 repeated detector calls?
2. Does the advisory validator accept/reject/abstain as expected for the represented reference, schema, unsupported-claim, and insufficient-evidence fixtures?
3. Do represented authorization, target-scope, lease, transaction, and recovery cases preserve their expected deny, rollback, or unchanged-state invariants?
4. What local processing time was measured for detector-only versus detector plus a fake reviewer adapter?

The questions are deliberately implementation-bounded. They do not ask about vulnerability detection accuracy, live model quality, or generalization to production targets.

## 3. Master draft map

| Section | Content prepared | Review focus |
|---|---|---|
| Preliminary pages | University and student placeholders; no fabricated approvals or declarations | Confirm actual front matter and forms required by the university |
| Abstract | Problem, implementation scope, fixture results, and limitations | Confirm expected abstract structure/length once official guidance is available |
| Chapter 1 | Background, problem, aim, objectives, questions, scope, terminology | Confirm the narrowed study matches the approved project and thesis requirements |
| Chapter 2 | Critical review of six research papers and four OWASP resources; qualified gap | Confirm sufficiency of literature coverage and whether additional primary sources are required |
| Chapter 3 | Artifact case-study design and E1–E4 protocols | Confirm the evaluation design is academically adequate for the programme |
| Chapter 4 | Source-aligned architecture diagrams and trust boundaries | Confirm diagrams distinguish the passive API route from the separate FSM/RAG subsystem |
| Chapter 5 | Authentication, authorization, execution, detector, reviewer, persistence | Confirm terminology and implementation detail are at the appropriate thesis level |
| Chapter 6 | Exact fixture, reviewer, timing, Python and historical Flutter results | Confirm results and limits are presented without unsupported generalization |
| Chapter 7 | Threat model summary, controls, residual risks, limitations, validity threats | Confirm the security discussion is sufficiently explicit about unverified deployment controls |
| Chapter 8 | Discussion, conclusion, future validation | Confirm contribution language and future research priorities |
| References and appendices | Provisional editorial numbering, project evidence registry, assembly plan | Confirm citation style only after official instructions; resolve flagged source metadata |

The separate `TASK_07_3_THESIS_EVIDENCE_TRACEABILITY.md` maps each significant technical and quantitative claim to its implementation, test/experiment, source, and limitation.

## 4. Feedback requested

Please advise on the following before the draft is typeset or treated as a submission copy:

1. **Study scope:** Is the implementation-bounded passive-assessment study acceptable, given that the original proposal's broader multi-agent, RAG, and active-testing objectives were not integrated into this API workflow?
2. **Title and contribution:** Does the working title and contribution statement accurately represent the completed thesis project without overstating novelty?
3. **Research questions:** Are the four fixture/test-based questions suitable, or should some be framed explicitly as engineering evaluation questions rather than research questions?
4. **Methodological sufficiency:** Is the current reproducibility and invariant-testing evidence sufficient for the degree requirements, or is an independently labeled dataset/other experiment required before submission?
5. **University requirements:** Please provide or identify the current official North Western University, Khulna thesis template and relevant department/programme instructions. The earlier TASK 07.2 reference to a North-West University (South Africa) template service is not applicable.
6. **Citation and source issues:** Please confirm the required citation style. The ACL 2026 seventh-author discrepancy (Sean Du in ACL metadata versus Xuefeng Du on the PDF title page) and PentestEval publisher metadata remain unresolved in the available audit.
7. **Preliminary pages and compliance:** Which title, declaration, approval, ethics/permission, acknowledgement, abstract, and appendix forms are required? No approval wording has been invented.
8. **Defense:** Confirm defense duration and whether a fixture test-output demonstration is appropriate. The current slide outline is timed to 10 minutes and labels the demonstration as fixture-based.
9. **Research ethics and permissions:** Confirm whether any additional ethics or owner-permission declaration is required for the synthetic fixtures and for any future live demonstration. No live target was used in the recorded evaluation.

## 5. Evidence snapshot for review

| Evidence item | Recorded result | Interpretation permitted |
|---|---:|---|
| One synthetic HTTPS observation, 100 detector calls | 1 normalized finding set; 5 findings/call | Repeatability for one fixed fixture |
| Finding/evidence identifier membership | 500/500 valid | Fixture ID linkage; not semantic proof or accuracy |
| Reviewer valid/invalid reference cases | 1/1 accepted; 3/3 rejected | Specific deterministic validator fixtures |
| Unsupported claim / abstention / schema fixtures | 2/2 rejected; 1/1 abstained; valid 1/1, invalid 2/2 | Selected local cases; not live model quality |
| Advisory failure isolation | 4/4 listed cases; repeated failures 5/5 | Represented failure paths preserved tested deterministic outputs |
| Local fake-adapter timing | Detector median 0.0233 ms; combined median 0.5087 ms; median increment 0.4854 ms | One local code-path timing run; not model or provider latency |
| Historical Python regression run | 863 collected, 863 passed, 0 failed, 0 skipped; 47.26 s | Historical automated suite result |
| Historical Flutter run | 60 collected, 59 passed, 0 failed, 1 skipped | Prior report only; not rerun for this draft |
| Live model / production-authorized target / Debian egress evidence | 0 samples / 0 runs / deferred | No quality, live authorization, or OS isolation claim |

Detailed sources and denominators are in the master draft and evidence traceability matrix. These are TASK 06.9/TASK 06.8 recorded results, not new tests run during this documentation assembly.

## 6. Items that remain open

### Academic decisions and external materials

- Current official North Western University, Khulna thesis template and department/supervisor instructions.
- Required chapter order, title-page language, declaration and approval forms, ethics forms, abstract limit, formatting, numbering, citation style, and submission procedure.
- ACL paper author identity correction and official PentestEval publisher metadata.
- Whether the candidate literature coverage needs additional primary sources or a formal systematic search.

### Technical evidence and deployment

- No independent labeled dataset supports accuracy, false-positive/negative, precision, recall, or F1 claims.
- No live AI provider samples support reviewer quality, calibration, or provider latency claims.
- No trusted production issuer/verifier, signed approval source, or revocation service is configured.
- No live authenticated browser-to-API workflow or production storage acceptance is recorded.
- Debian 13 OS-level egress verification remains deferred under TASK 06.4.4.

These items are not hidden behind the document's completeness. The draft remains conditional until the academic requirements are confirmed and any supervisor-required evidence is obtained.

## 7. Supervisor review checklist

- [ ] Approve the implementation-bounded scope and working title.
- [ ] Approve or revise the aim, objectives, and research questions.
- [ ] Confirm whether existing fixture/test evidence is sufficient for submission.
- [ ] Supply/confirm the correct North Western University, Khulna template and department requirements.
- [ ] Confirm citation style and how unresolved source records should be handled.
- [ ] Confirm required declarations, ethics/permission pages, and appendices.
- [ ] Review the evidence traceability matrix and all limitations.
- [ ] Confirm the 10-minute defense outline and fixture-only demo wording.
- [ ] Identify any required corrections before final typesetting.

