# AEGISCORE AI Requirements and Traceability

**Status:** Phase 6A adds a locked Python environment and a minimal read-only FastAPI foundation. Real transport, authorization verification, DNS/network isolation, and research workflow features remain unimplemented.  
**Source date:** Thesis proposal says online sources were reviewed through 24 October 2026.  
**Inspection date:** 27 October 2026

## 1. Sources and interpretation

This document consolidates the user-provided Master Prompt Pack and `docs/Thesis_Proposal.pdf`. They have different authority: the proposal defines the research scope and explicitly permits some technology alternatives; the Master Prompt Pack selects a working implementation stack and adds engineering constraints. A Master Prompt Pack selection is mandatory for this project unless changed by the user, but it is not thereby a thesis requirement.

The 14-page proposal is in Bengali and English. The PDF opens and renders; its text extraction corrupts some Bengali glyphs and spacing. The requirements below are English summaries of readable content and headings, not claimed verbatim translations. If a fine-grained Bengali passage is material and cannot be confirmed from the rendered page, it remains an open item rather than an assumed requirement. Page references below refer to the proposal’s printed page numbers.

Requirement classes used here:

- **Mandatory — Master Prompt:** explicitly required by the user’s project brief.
- **Mandatory — Proposal:** in the proposal’s stated scope, core architecture, or evaluation design.
- **Optional — Proposal:** explicitly conditional or deferred by the proposal.
- **Working project decision — Master Prompt:** selected for this implementation, but not required by the thesis proposal.
- **Proposal-permitted option:** named as one of multiple acceptable choices by the proposal; not uniquely required.
- **Implementation assumption:** a proposed engineering interpretation that still needs validation; it is not a research result or a user-approved design decision.

## 2. Research aim, objectives, questions, and hypotheses

### Overall aim

Design and evaluate a controlled, RAG-supported multi-agent prototype for evidence-based web application vulnerability assessment, focusing on whether evidence verification and uncertainty-aware decisions affect reporting reliability and safe behavior. The proposal does not claim in advance that false positives will fall or that the system will match human testers (pp. 3–4, 11, 13).

### Research objectives

The proposal’s six objectives, rendered here as concise English summaries (pp. 4–5), are:

1. Define a limited test scope and safe execution policy for approved local web applications.
2. Design a modular workflow for reconnaissance/observation, planning, guarded execution, retrieval, evidence verification, and reporting.
3. Supply relevant context retrieved from security documentation and previously validated lab findings.
4. Define verification, abstention, and human-review decisions using evidence quality and uncertainty.
5. Compare the proposed system with OWASP ZAP and an uncertainty-disabled multi-agent-plus-RAG baseline; run a no-RAG ablation if feasible.
6. Evaluate precision, recall, F1, false-positive rate, confidence calibration, abstention, and safety metrics.

### Research questions

The proposal states five research questions (p. 5):

- **RQ1:** Does RAG-supported uncertainty-aware verification reduce false-positive vulnerability reports versus the same Multi-Agent+RAG baseline without uncertainty-based abstention?
- **RQ2:** What effect does adding uncertainty awareness have on recall or detection coverage?
- **RQ3:** How well do confidence scores reflect finding reliability, and how well calibrated are they?
- **RQ4:** How effectively do low-confidence abstention and safety guardrails preserve scope compliance and limit risky actions?
- **RQ5:** What changes when RAG is removed, including report quality, tool-call count, runtime, and evidence completeness?

### Hypotheses (not results)

- **H1:** Under the same cases and execution budget, uncertainty-aware verification will reduce false-positive rate versus the baseline.
- **H2:** Reducing false positives through abstention or added verification may trade off against recall or runtime.
- **H3:** Confidence calibrated on a validation set will reflect reliability better than uncalibrated, self-reported model confidence.

These are hypotheses to test, not findings. No benchmark scores or experimental outcomes exist at this inspection phase.

## 3. Scope and limitations

### In scope

- Testing only a self-owned or explicitly authorized, isolated local lab; no live third-party target.
- Three selected vulnerability classes: reflected/stored XSS, non-destructive SQL injection cases, and selected Broken Access Control cases.
- OWASP Juice Shop as the primary local target; the proposal specifies a local Docker instance (p. 9). Docker Compose is selected by the Master Prompt Pack, not specified by the proposal. Selected labeled OWASP Benchmark cases may also be used; the proposal says the two sources must be tagged separately and their ground truth must not be treated as interchangeable (pp. 5, 9).
- RAG material from relevant OWASP Web Security Testing Guide guidance, official documentation for selected tools, sanitized previously validated lab observations, synthetic test cases, and evidence criteria. Each item needs source, version/date, and provenance metadata; retrieval relevance is context, not vulnerability proof (p. 9).
- A controlled comparative evaluation, with ground-truth adjudication and error analysis (pp. 9–11).

### Out of scope

- Unauthorized testing or scanning of live third-party websites.
- WAF evasion, stealth/masking, credential theft, denial of service, destructive payloads, data exfiltration, unrestricted exploit chaining, or autonomous IP-to-root penetration testing.
- Automatic remediation, source-code modification, or production deployment. Remediation advice, if later included, is non-executing and optional (pp. 5–6, 8).

### Safety and trust boundaries

- Deterministic policy code is the enforcement boundary. LLM roles may propose analysis or plans, but may not bypass the controller or issue unrestricted HTTP requests.
- Enforce an exact target/endpoint allowlist, DNS/IP and redirect revalidation, bounded request budgets, timeouts, and an emergency stop. Deny requests outside scope. The Master Prompt additionally requires default-deny outbound network access in the experiment environment.
- Treat LLM output, retrieved documents, web content, and tool output as untrusted input.
- Use synthetic/test data; do not put real credentials or personal data in the RAG corpus.
- Keep API keys out of frontend bundles, source control, and logs. Use a provider abstraction on the backend; do not silently replace a real provider with mock findings.
- Record target, policy decisions, request identifiers, tool output, evidence, and final decisions for audit. Record model/configuration/version, prompt, retrieval sources, and timestamps for experimental reproducibility.
- Require human review on policy exceptions and uncertainty below the frozen decision threshold; an agent must not continue automatically through an exception.

## 4. Required modules and finding states

The proposal first presents an eight-stage workflow (p. 6), then expands it into a 12-role implementation-priority table (pp. 7–8). The Master Prompt explicitly requests the corresponding modules, except the explicitly optional remediation advisor. The proposal calls roles 1–7 and 9/11 “Must-have,” role 8 a “Core research addition,” role 10 “Included, lightweight,” and role 12 “Optional after core experiment.” Those labels describe proposal priority; they do not validate a particular class or process boundary.

| ID | Module | Required responsibility and authority limit | Status |
|---|---|---|---|
| MOD-01 | Scope and Safety Controller | Deterministically enforce target/endpoint allowlists, request limits, timeouts, redirect checks, egress policy, emergency stop, policy decisions, and audit events. | Mandatory |
| MOD-02 | API and Endpoint Mapping Agent | Inventory pages, forms, routes, API endpoints, and parameter metadata using bounded tools; do not scan unsupported routes on its own. | Mandatory |
| MOD-03 | Test Planning Agent | Propose reviewable cases for selected vulnerability profiles and pre-check budget/policy; planning does not authorize execution. | Mandatory |
| MOD-04 | Guarded Test Executor | Deterministic wrapper for only approved, non-destructive requests to allowlisted lab targets; capture request/response and tool logs. | Mandatory |
| MOD-05 | RAG Analyst | Retrieve and synthesize source-attributed security guidance and validated lab records; retrieval is not proof. A vector-store implementation is a technology choice, not this module’s research requirement. | Mandatory |
| MOD-06 | Vulnerability Specialist | Reusable analysis role with distinct XSS, SQL Injection, and Broken Access Control profiles; output candidate findings and evidence needed. | Mandatory |
| MOD-07 | Evidence Verifier | Check pre-defined evidence such as expected markers, response differences, tool evidence, and repeatability; return checklist/state. | Mandatory |
| MOD-08 | False-Positive Reviewer | Independently find counter-evidence, benign explanations, duplicates, and unsupported inference; it recommends, but does not make the final policy decision. | Mandatory core research addition |
| MOD-09 | Uncertainty and Abstention Gate | Use evidence quality and validation-set calibration to choose report, bounded re-check, abstention, or human review, with rationale/logging. | Mandatory |
| MOD-10 | Report Quality Reviewer | Check evidence references/citations, duplicates, severity wording, and contradictions; flags cannot confirm a finding. | Mandatory, lightweight |
| MOD-11 | Evaluator and Reporter | Deterministically map findings to ground truth and produce metrics, machine-readable logs, and a human-readable report. | Mandatory |
| MOD-12 | Remediation Advisor | Offer OWASP-aligned mitigation and retest advice only; no code changes or production action. | Optional after core experiment |

The proposal’s finding states are **Candidate**, **Verified**, **Uncertain**, and **Rejected / Not Reproduced**. Candidate is not confirmed. Verified requires the predefined evidence checklist and ground-truth protocol. Uncertain leads only to bounded re-check, abstention, or human review. Rejected/Not Reproduced is not reported as confirmed, but remains in the audit trail (pp. 6–9).

## 5. Experimental design and evaluation

### Dataset and run protocol

- The proposal’s initial target is approximately **30–45 curated cases**, ideally balanced across positive and negative cases and the three vulnerability classes. This is a target, not a fixed count; final count depends on lab setup and supervisor agreement (p. 9).
- Freeze each case’s expected status, category, evidence checklist, and adjudication decision before evaluation. Keep development/validation cases separate from the final test set; where possible, do not split the same endpoint or vulnerability instance across partitions (pp. 9–10).
- Run B1, B2, and P on the same approved target/scope and comparable request/resource budgets. Repeat each case, initially three times if feasible. Preserve model/configuration/version, prompt, retrieval source, tool logs, and timestamps (p. 10).
- Adjudicate each reported finding against ground truth and assign TP/FP/FN/TN. Track abstentions separately; do not count them as true negatives. Define the mapping from findings to cases and duplicate-report handling before computing metrics (pp. 10–11).
- Report baseline differences; use paired comparison and bootstrap confidence intervals where appropriate. Analyze false positives, missed findings, incorrect confidence, and guardrail violations qualitatively (p. 10).
- Do not tune thresholds on the final test set. Set composite-score weights and abstention threshold using development/validation data, then freeze them for the final test (p. 9).

### Baselines and ablation

| ID | Configuration | Purpose and limitation | Status |
|---|---|---|---|
| B1 | OWASP ZAP on the same approved target with a suitable recorded scan policy. | Conventional DAST comparison. Active scan may send attack-like requests; lab isolation, configuration, and request budget must be recorded. ZAP is not assumed to be a perfect Broken Access Control baseline. | Required proposal baseline |
| B2 | Multi-Agent+RAG with uncertainty-based abstention disabled. | Isolates the incremental effect of uncertainty handling. | Required proposal baseline |
| P | Multi-Agent+RAG with evidence verification, calibrated uncertainty, and abstention. | Full proposed method. | Required |
| A1 | Proposed system with RAG retrieval disabled while other components remain fixed. | Estimates the independent contribution of RAG. | Optional if time permits |

### Metrics

| Metric | Proposal definition / interpretation |
|---|---|
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| F1 | Harmonic mean: 2 × Precision × Recall / (Precision + Recall) |
| False-positive rate | FP / (FP + TN) |
| Brier score | Mean squared probability error: N⁻¹ Σ(pᵢ − yᵢ)²; lower is generally better probabilistic accuracy. |
| Expected Calibration Error (ECE) | Weighted gap between confidence and accuracy across confidence bins; report binning and small-sample limitations. |
| Verified Finding Rate | Findings passing the predefined evidence checklist / all candidate findings. |
| Abstention Rate | Abstained decisions / cases requiring an uncertainty decision. Keep abstentions separate from TN. |
| Safety Compliance | Policy-compliant runs / total runs; include scope, request budget, timeout, and outbound-traffic policy. |
| Runtime / Tool Calls | Per-case time and tool-call count. |

Definitions and denominators must be frozen before evaluation. Ground-truth labels and duplicate handling affect the metrics and are not yet specified at case level.

## 6. Technology classification and implementation assumptions

**Correction to the Phase 1 draft:** the earlier heading “Mandatory technology baseline from the Master Prompt Pack” and `REQ-023` label blurred project instructions with thesis requirements. The stack remains the working project decision, but is no longer classified as a mandatory thesis technology. Related wording for `REQ-003` (local Docker versus Compose), `REQ-010` (RAG store), and `REQ-017` (SQLite storage) is clarified below. Existing `REQ-*` identifiers are preserved.

### Technology explicitly permitted or named by the proposal

- **Workflow orchestration:** LangGraph or an equivalent stateful workflow framework (proposal §7, p. 6).
- **Vector store:** ChromaDB or a similar vector store (proposal §7, p. 6). The proposal also mentions ChromaDB retrieval in its Month 5 plan (p. 12); this does not make ChromaDB the only permitted store.
- **LLM:** a local or otherwise authorized LLM, subject to feasibility (proposal §6.1 and §7, pp. 5–6). The proposal does not name Gemini or a provider SDK.
- **Lab:** OWASP Juice Shop, with a local Docker instance specified for the primary target (proposal §8.4, p. 9). Compose is not named.
- **Evaluation output:** JSON/CSV/SQLite are listed as possible finding/log output forms in the architecture table (proposal §7, p. 6); SQLite is not specified there as the mandatory metadata database.
- **Explicit exclusions:** the proposal does not specify Flutter, FastAPI, Python, Gemini API, Docker Compose, pytest, `flutter test`, or `flutter analyze` as thesis requirements.

### Working implementation stack selected by the Master Prompt Pack

The following choices are project-level implementation decisions required by the Master Prompt Pack. They are not presented as thesis requirements. Phase 6A verified only the minimal Python/FastAPI dependency set and read-only API behavior in one local Python 3.13.2 environment; compatibility and operational suitability for the remaining stack still require verification before those components are implemented.

| Technology / tool | Project decision | Relationship to proposal |
|---|---|---|
| Flutter Web | Frontend | UI technology is not specified by the proposal. |
| Python + FastAPI | Backend | Backend language/framework is not specified by the proposal. |
| LangGraph | Orchestration | One explicitly permitted option; proposal also allows an equivalent stateful framework. |
| SQLite | Initial metadata/run/finding/audit store | Proposal mentions SQLite as one output option, not as a required database design. |
| ChromaDB | Retrieval store | One explicitly permitted vector-store option; proposal allows a similar store. |
| Gemini API via provider abstraction | LLM provider | Proposal allows local or authorized LLMs and does not select Gemini. External egress and provider data handling remain unresolved. |
| Docker Compose + OWASP Juice Shop | Local lab packaging/target | Proposal specifies a local Docker Juice Shop instance; Compose is the project’s packaging choice. |
| pytest; `flutter test`; `flutter analyze` | Test tools | Required by the Master Prompt Pack; not specified by the proposal. |

Phase 6A selected `uv` as a project implementation choice and added a Python 3.13.2 local environment with `uv.lock`. The locked runtime dependencies are FastAPI 0.162.0, Pydantic 2.14.1, and Uvicorn 0.54.0; the locked development dependencies are pytest 8.4.2 and httpx2 2.16.0. These versions resolved and installed in the project-local environment and the tests ran there. This verifies compatibility only for the inspected Windows/Python 3.13.2 environment; it is not a proposal requirement, a production compatibility claim, or a substitute for rechecking when the lock changes. Current [Starlette test-client guidance](https://starlette.dev/testclient/) recommends httpx2 for its in-process test client.

### Implementation details and assumptions requiring confirmation during a later phase

1. “Exact target allowlist” will likely require canonical scheme, host, port, and approved path/endpoint checks, plus redirect destination validation. The exact representation and DNS/IP rules are not set here.
2. Agent roles can be modeled as bounded LangGraph nodes with structured typed inputs/outputs; “multi-agent” does not by itself decide whether roles use separate model calls.
3. Assigning metadata/run/finding/audit records to SQLite and retrieval vectors to ChromaDB follows the Master Prompt Pack’s working stack selection. Exact schema, migrations, retention, and access control remain open implementation details, not thesis requirements.
4. The Master Prompt Pack requires a real integration when configured and an explicitly labeled mock in tests/demo; it forbids silent mock substitution. Provider-mode UX and test/demo labeling remain implementation details.
5. Flutter Web UI content, authentication model, deployment shape, and user approval interactions are not specified by the proposal.

Items 1, 2, and 5 are assumptions or open design choices; items 3 and 4 restate Master Prompt Pack decisions/constraints while identifying unresolved implementation details.

## 7. Requirements traceability

Planned verification methods below are future acceptance evidence. None were run in Phase 1.

| ID | Class / source | Requirement | Corresponding module(s) | Planned verification method |
|---|---|---|---|---|
| REQ-001 | Mandatory — Proposal | Assess only the stated research aim: controlled, evidence-based, RAG-enabled multi-agent vulnerability assessment and comparative evaluation; do not claim expected results in advance. | System; Evaluator/Reporter | Review experiment protocol and final reports for scope and evidence; no-result claims before runs. |
| REQ-002 | Mandatory — Proposal + Master Prompt | Restrict targets to an explicitly approved, isolated local lab; exclude unauthorized third-party targets. | Scope/Safety Controller; Guarded Executor | Policy tests for approved local target, unapproved host, and scope mismatch; isolated lab integration test. |
| REQ-003 | Mandatory — Proposal | Limit core cases to reflected/stored XSS, non-destructive SQLi, and selected Broken Access Control; keep Juice Shop and OWASP Benchmark cases/ground truth separately tagged. Proposal specifies local Docker Juice Shop, not Compose. | Test Planner; Specialist profiles; Evaluator | Review frozen case manifest, labels, source tags, and evidence checklist before runs. |
| REQ-004 | Mandatory — Master Prompt + Proposal | Keep deterministic controls outside LLM reasoning; untrusted model/retrieval/web/tool content cannot grant authority or bypass the controller. | Scope/Safety Controller; all agent/tool boundaries | Adversarial input and malformed-output tests; prove execution requires a deterministic allow decision. |
| REQ-005 | Mandatory — Master Prompt + Proposal | Enforce exact target/endpoint allowlists, DNS/IP validation, redirect re-validation, request budgets, timeouts, egress policy, and emergency stop. | Scope/Safety Controller | Unit/integration tests for each allow/deny condition, redirects, exhausted budget, timeout, and stop. |
| REQ-006 | Mandatory — Master Prompt + Proposal | Deny out-of-scope, destructive, stealth/evasion, credential-theft, DoS, exfiltration, and unrestricted-chain behavior; default-deny outbound traffic in experiment execution. | Scope/Safety Controller; Guarded Executor; deployment configuration | Policy tests plus isolated network/egress verification; record all blocked actions. |
| REQ-007 | Mandatory — Proposal | Map only bounded application observations into an endpoint inventory; do not autonomously expand scope or scan unsupported routes. | API/Endpoint Mapping Agent | Tool-contract tests and local fixture run showing inventory stays within approved route set. |
| REQ-008 | Mandatory — Proposal | Produce reviewable, budget-checked plans for selected vulnerability profiles; a plan alone cannot authorize a request. | Test Planning Agent; Scope/Safety Controller | Schema and budget validation tests; verify executor separately requires controller authorization. |
| REQ-009 | Mandatory — Proposal | Execute only allowlisted, non-destructive requests and record request/response and tool evidence. | Guarded Test Executor | Local-lab integration tests, request-budget assertions, and audit-record checks. |
| REQ-010 | Mandatory — Proposal | Retrieve only approved guidance/validated lab sources with version/date/source provenance; retrieval relevance is not proof. | RAG Analyst; retrieval store (ChromaDB is the working project choice) | Ingestion/retrieval tests for source metadata, filtering, citations, and explicit non-evidence behavior. |
| REQ-011 | Mandatory — Proposal | Provide distinct XSS, SQL Injection, and Broken Access Control specialist profiles that generate candidate findings and required-evidence lists. | Vulnerability Specialist | Typed-output and profile-specific fixture tests; candidates remain unconfirmed. |
| REQ-012 | Mandatory — Proposal | Verify candidates against predefined evidence, including expected marker/response difference/tool output/repeatability as applicable. | Evidence Verifier | Checklist tests for pass, fail, conflicting, and incomplete evidence. |
| REQ-013 | Mandatory — Proposal | Independently review counter-evidence, benign explanations, duplicates, and unsupported inferences without granting final policy authority. | False-Positive Reviewer; Scope/Safety Controller | Reviewer-output tests and authority-boundary tests. |
| REQ-014 | Mandatory — Proposal + Master Prompt | Calculate uncertainty from evidence-related signals, not solely model self-reported confidence or RAG similarity; calibrate/choose threshold on validation data and freeze before final test. | Uncertainty/Abstention Gate; Evaluator | Calibration data-flow audit, Brier/ECE calculations, threshold-freeze record, and low-confidence abstention tests. |
| REQ-015 | Mandatory — Proposal | Apply candidate/verified/uncertain/rejected states; uncertain cases get only bounded re-check, abstention, or human review. | Evidence Verifier; Uncertainty Gate; workflow | State-transition tests including no automatic continuation on low confidence or policy exception. |
| REQ-016 | Mandatory — Proposal | Check report citations/evidence references, duplicates, severity wording, and contradictions; quality checks cannot independently confirm findings. | Report Quality Reviewer | Report fixtures with missing citations, duplicate, contradictory, and unsupported claims. |
| REQ-017 | Mandatory — Proposal; SQLite is a working project choice | Persist auditable target, policy decision, request identifier, tool output, evidence, final decision, and experiment configuration/provenance. The proposal requires these records but does not require SQLite as the metadata database. | Controller; Executor; RAG; Evaluator; metadata store | Persistence tests, required-field checks, reproducibility-log review, and secret-redaction tests. |
| REQ-018 | Mandatory — Proposal | Map findings to pre-recorded ground truth and report TP/FP/FN/TN; define duplicate rules; abstentions remain separate and are not TN by default. | Evaluator and Reporter | Hand-calculated known-answer metric fixtures and adjudication/duplicate-rule review. |
| REQ-019 | Mandatory — Proposal | Compare B1 OWASP ZAP, B2 Multi-Agent+RAG without uncertainty abstention, and P using comparable target/scope/budget; document ZAP’s logical-flaw limitations. | Evaluator and Reporter; lab protocol | Frozen run matrix and baseline configuration records; paired result audit. |
| REQ-020 | Mandatory — Proposal | Report precision, recall, F1, false-positive rate, Brier, ECE, verified finding rate, abstention rate, safety compliance, runtime, and tool calls. | Evaluator and Reporter | Unit tests using hand-calculated fixtures; metric definitions and denominators reviewed before test-set access. |
| REQ-021 | Mandatory — Proposal | Freeze ground truth/evidence checklists before evaluation, keep validation separate from final test, repeat runs (target three if feasible), and preserve versions/prompts/sources/logs/timestamps. | Evaluator; experiment protocol | Protocol review and run-manifest audit; confirm no threshold tuning on final test. |
| REQ-022 | Optional — Proposal | Run A1 no-RAG ablation only if time/resources permit, keeping other system components fixed. | RAG Analyst; Evaluator | Paired ablation run record if approved; otherwise document as not run. |
| REQ-023 | Working project decision — Master Prompt; not a thesis requirement | Use the selected project stack: Flutter Web, FastAPI/Python, LangGraph, SQLite, ChromaDB, Gemini provider abstraction, Docker Compose/Juice Shop, pytest, and Flutter test/analyze. Proposal permits LangGraph/Chroma alternatives and a local or authorized LLM; it does not prescribe the rest of this stack. | Frontend; API; orchestration; persistence; retrieval; provider; lab | Phase 6A verifies the locked Python/FastAPI foundation and read-only in-process API contract only. Flutter, orchestration, persistence, retrieval, providers, and lab remain for later explicitly requested phases. |
| REQ-024 | Mandatory — Master Prompt | Keep API keys out of frontend/source/logs; use real integrations when configured and explicitly labeled mocks in tests/demo; never silently substitute mock security findings. | Gemini provider; backend; UI; logging | Secret scan and bundle/log inspection; provider-mode tests with absent/present credentials. |
| REQ-025 | Optional — Proposal | Provide non-executing, advisory remediation only after the core experiment; never modify code or production systems automatically. | Remediation Advisor | Verify advice-only output and absence of source/deployment mutation capability if feature is later approved. |
| REQ-026 | Mandatory — Master Prompt | Implement only an explicitly requested phase; maintain completed/pending/blocked/unverified status and report actual verification evidence. | Project documentation and delivery process | Review status against files/commands actually inspected; phase-gate review before proceeding. |

## 8. Unresolved questions and constraints

These items need answers or a documented decision before the affected implementation or experiment:

| ID | Unresolved item | Why it matters / safe handling |
|---|---|---|
| OPEN-01 | Exact Juice Shop version/image digest, local host/port, approved paths, and Docker network design. | Needed to make the allowlist and lab reproducible. Docker is not currently available in the inspected environment. Do not start a target until approved and isolated. |
| OPEN-02 | Which OWASP Benchmark cases, if any, are included and how they are run alongside Juice Shop. | The proposal only says selected suitable labeled cases; preserve source-specific labels and ground truth. |
| OPEN-03 | Final test-case count, case IDs, labels, evidence checklist, adjudication owner, and duplicate-finding rule. | The proposal’s 30–45 is approximate and final count is to be agreed with the supervisor. No test cases or labels are created in Phase 1. |
| OPEN-04 | Request budgets, timeout values, redirect policy, DNS/IP policy, emergency-stop mechanism, and outbound-deny implementation. | Required controls are named, but numeric limits and deployment mechanics are not specified. `docs/ADRs/0002-safety-policy-and-provider-egress.md` proposes conservative discussion defaults; they are not approved or validated. Set a versioned trusted configuration before execution; a run may lower but must not raise its approved limits. |
| OPEN-05 | Development/validation/test split sizes and validation sample adequacy. | Thresholds must be selected on validation data and frozen; the proposal warns calibration estimates may be uncertain on small sets. |
| OPEN-06 | Composite confidence signal weights, calibration method, binning for ECE, threshold, and bounded re-check count. | Proposal identifies evidence completeness, repeatability, independent corroboration, and response consistency, but gives no weights or numeric policy. Decide using development/validation only. |
| OPEN-07 | Embedding provider/model and document chunking/version strategy. | The proposal permits ChromaDB or a similar vector store; the Master Prompt selects ChromaDB and an unspecified appropriate embedding provider. No embedding provider/model is chosen. |
| OPEN-08 | Gemini model/API version, provider configuration, rate/cost budgets, and credential provisioning method. | Gemini is a Master Prompt project decision, not a thesis selection. No SDK/model/credential is configured in the current environment. Verify official current APIs before implementation. |
| OPEN-09 | Flutter Web screens, local authentication/authorization needs, and human-review interaction. | The proposal does not specify product UI behavior; do not invent product features beyond a minimal research interface. |
| OPEN-10 | SQLite schema/retention, Chroma persistence, evidence redaction/retention, and export format details. | SQLite and auditability are specified, but lifecycle and schema decisions are not. |
| OPEN-11 | ZAP version/configuration and a safe, comparable request cap. | ZAP active scanning may send attack-like requests; it must run only against an isolated authorized target and its limitations must be reported. |
| OPEN-12 | Exact English translation of fine-grained Bengali prose where glyph extraction was corrupted. | The PDF is available and legible, but extracted Bengali text has character errors. Material ambiguity must be resolved from a checked rendering or with the proposal author; this document does not invent wording. |
| OPEN-13 | Whether any narrowly allowlisted external LLM or embedding-provider egress is permitted while the experiment environment is default-deny. | The Master Prompt selects Gemini API as a working project choice, while the proposal permits a local or authorized LLM and the project design is default-deny for outbound traffic. No provider exception is active or approved. Follow the explicit decision gate in ADR 0002 before any provider call. |
| OPEN-14 | Who may create/revoke target registrations and what authorization evidence is authoritative. | A proposed lifecycle is documented in ADR 0002, but no authorizing person, actual approval record, authentication mechanism, or verification procedure has been supplied. Never treat the current string-valued `authorization_ref` or test fixture values as verified authorization. |
| OPEN-15 | Exact allowed lab address ranges and DNS-to-connection pinning implementation. | Hostname/origin matching does not prove a local destination. The future transport must resolve and validate addresses, pin the selected validated address to connection, check the peer address, and independently enforce a lab-only network boundary. Phase 4B did not perform DNS or network operations. |
| OPEN-16 | Real-transport integration and transport-specific checks. | Phase 4B initially bound an in-memory one-use permit to run, target registration/scope versions, operation ID, method/path/parameters, budget slots, and deadlines. Phase 5B adds an in-memory trusted case/profile policy, registration-derived origin, canonical query/header data, exact optional body bytes, explicit data bounds, and profile/data-policy versions. The case/profile fixtures are synthetic contracts, not approved cases or authorization evidence. Real authorization, network/DNS, response, and transport controls remain unresolved; no real transport is authorized or implemented. |

## 9. Proposal timeline (nine months)

The following is the proposal’s schedule, not a claim about work already completed (p. 12):

| Proposal month | Planned work | Deliverable |
|---|---|---|
| 1 | Literature review, research-gap validation, supervisor feedback, and draft test protocol. | Revised proposal and protocol. |
| 2 | Lab setup, target/test-case selection, ground-truth labeling, and baseline configuration. | Isolated testbed and labeled test set v1. |
| 3 | Scope controller, observer, and test-planning component. | Core workflow prototype. |
| 4 | Guarded executor, logs, and safety-policy enforcement. | Controlled execution pipeline. |
| 5 | RAG corpus, ChromaDB retrieval, and provenance logging. | RAG-enabled analysis module. |
| 6 | Evidence verifier, confidence score, and abstention policy; select thresholds on validation set. | Uncertainty-aware prototype. |
| 7 | B1/B2/P experiments, repeated runs, and optional ablation. | Experiment logs and preliminary metrics. |
| 8 | Statistical analysis, error analysis, limitations, and figures/tables. | Results and discussion draft. |
| 9 | Thesis writing, supervisor revision, final validation, and defense preparation. | Final thesis, reproducible protocol, and presentation. |

Phase 1 is repository/requirements inspection requested by the user; it does not claim to have completed the proposal’s Month 1 literature review or any later milestone.

## 10. Recommended phase plan

Project phase numbers are this project’s delivery gates; they are not the proposal’s nine calendar-month numbers. Month 1–9 remain separately listed in §9. Project Phase 2 was architecture documentation only; project Phase 3 was the deterministic policy-contract phase. Neither phase is the proposal’s Month 2 lab/test-case milestone. This plan does not authorize work beyond the completed Phase 6A gate.

| Suggested phase | Scope | Exit evidence |
|---|---|---|
| Phase 1 — Repository and requirements inspection | Inspect sources/environment, record requirements, traceability, risks, and status. | Complete: requirements and status documentation; no feature implementation. |
| Phase 2 — Architecture documentation | Define component boundaries, data flow, threat model, planned tests, and technology decisions. This project phase is not proposal Month 2. | Complete after these documents are reviewed; no lab, test-case, ground-truth, or application implementation. |
| Phase 3 — Deterministic safety core | Implement typed safety/target-policy contracts and configuration validation with in-memory unit tests only. No network executor, lab, research case set, or real provider calls in this phase. | Completed as an in-memory policy contract and unit-test suite (`aegiscore/safety.py`, `tests/test_safety_policy.py`); no request can be emitted by the safety core alone. Authorization source, DNS/network boundary, numeric deployment values, and executor integration remain unresolved. |
| Phase 4B — Fake-transport-only safety integration | Add an engine-issued, one-use exact-operation permit and a guarded boundary with injected transport; run only a recording in-memory fake. No Docker/Juice Shop, test cases, ground truth, scanner, DNS, or network. This is not proposal Month 2. | Completed for the implemented in-memory subset: T-SAFE-06 is partial, T-SAFE-08/09 are exercised, and T-SAFE-10 is partial. T-SAFE-07 (DNS/peer validation) remains planned. Denied, altered, stale, revoked, replayed, exhausted, stopped, and cancelled operations are prevented from reaching the fake transport in the tested cases. Tests establish software call gating only. Real authorization, DNS, network, and egress controls remain unverified. |
| Phase 5B — Offline test-case contract and permit-binding hardening | Bind fake-only operations to trusted target registration, case/profile, canonical origin/path/query/header/body, budget and deadline context. Use only benign in-memory fixtures; no lab, transport, network, external provider, or ground-truth cases. | Completed for the in-memory contract and tests. T-SAFE-08/09 are expanded to case/profile and request-data binding. Fixture profiles are not authorized research cases. Real authorization, DNS, network isolation, and transport behavior remain unverified. |
| Phase 6A — Reproducible environment and minimal backend foundation | Lock only the minimal Python/FastAPI/test dependencies and add a read-only, in-process-testable API foundation. Do not start a listener or connect API routes to the safety executor. | Completed: project-local Python 3.13.2 environment, lockfile, `.gitignore`, FastAPI app factory, health/capabilities routes, and in-process tests. This does not authorize target execution, a lab, providers, or later research modules. |
| Later phase — Approved lab and protocol preparation | Separately prepare the isolated local target, ground-truth protocol, selected cases, and baseline settings, aligning with proposal Month 2. Requires explicit scope approval and Docker/network readiness. | Approved isolated target and egress boundary; source-separated case manifest and adjudication protocol; documented budgets/configuration. This remains outside Phases 2–5B and requires its own approval. |
| Later phase — Guarded execution, mapping, and planning | Add bounded observation and request execution after safety core and lab authorization. | Local-only integration evidence, redirects/budgets/timeouts/cancel/audit verified. |
| Later phase — RAG, specialist, evidence, uncertainty, and reporting | Add corpus/retrieval, specialist profiles, verifier/reviewer, calibrated gate, and reports in proposal order. | Provenance/state/abstention checks and validation threshold frozen before final test. |
| Later phase — Controlled evaluation and analysis | Run B1/B2/P and optional A1, repeats, metrics, qualitative analysis, and reproducible reporting. | Audited run set, ground-truth adjudication, metrics, safety records, and limitations. |

**Phase 3 / Phase 4B / Phase 5B / Phase 6A status:** The in-memory deterministic policy contract and fake-only guarded boundary are implemented and tested, including offline case/profile and request-data binding. Phase 6A adds only a read-only API foundation and reproducible Python environment. No real transport, lab setup, scanning, research test-case execution, or ground-truth preparation has started. These later activities remain separate and require their own approval; none of these project phases is proposal Month 2.
