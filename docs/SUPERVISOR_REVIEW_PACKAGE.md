# AEGISCORE AI — Thesis Supervisor Review Package

## 1. Executive Summary & Thesis Context

**Project:** AEGISCORE AI  
**Thesis Title:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Document ID:** DOC-SUPERVISOR-REVIEW-PACKAGE  
**Author:** Antigravity AI Coding Assistant on behalf of Candidate  
**Date:** 2026-10-28  
**Status:** Awaiting Supervisor Review & Formal Decision Sign-Off  

---

### 1.1 Objective of this Package
This package consolidates all evaluation protocol specifications, testbed engineering artifacts, source-provenance audits, statistical constraints, and dataset governance contracts created across Phases 8E.1 through 8E.6.1. 

Its purpose is to present the thesis supervisor with a single, traceable, and intellectually honest assessment of the framework's current readiness, highlighting critical methodological limitations and formal decision gates that **must be adjudicated before any live container execution or benchmark scanning is authorized**.

---

### 1.2 Current Implementation Status

| Component / Layer | Module Path | Implementation Status | Test Coverage |
|---|---|---|---|
| **Safety Policy & Egress Guard** | `aegiscore/safety_policy.py` | In-memory RFC1918 / loopback allowlisting, domain constraints, verb restrictions | 100% verified (Phase 3) |
| **Guarded Execution Boundary** | `aegiscore/guarded_execution.py` | Signed permits, rate limiting (50 req/endpoint), fake transport test double | 100% verified (Phase 4B) |
| **Approved RAG Retrieval** | `aegiscore/rag_runtime.py` | Ingestion, chunking, SHA-256 verification, approved-only filtering | 100% verified (Phase 7–8B) |
| **Evidence Grounding & Claims** | `aegiscore/claim_validation.py` | Direct quotation validation, citation provenance matching, contradiction detection | 100% verified (Phase 8C) |
| **Specialist Roles & Orchestration** | `aegiscore/orchestration.py`, `specialist_roles.py` | Multi-agent state machine, epistemic uncertainty gating, abstention protocol | 100% verified (Phase 8D) |
| **Testbed Compose Engineering** | `testbed/docker-compose.yml`, `aegiscore/testbed.py` | Loopback port binding (`127.0.0.1`), internal bridge (`internal: true`), reset scripts | 100% verified (Phase 8E.2B) |
| **Evaluation Contracts & Scoring** | `aegiscore/evaluation.py` | Canonical locus contract, fail-closed JSONL parsers, abstention scoring invariants | 100% verified (Phase 8E.3) |
| **Runner Wrappers & Fixture Harness** | `aegiscore/evaluation_harness.py` | Condition registry, trial agreement analysis, majority-vote aggregation, run manifests | 100% verified (Phase 8E.4) |
| **Case Catalog & Multi-Dim Taxonomy** | `aegiscore/catalog.py` | 5-dimensional status taxonomy, extended SHA-256 config fingerprinting | 100% verified (Phases 8E.5–8E.6.1) |

---

## 2. Epistemological Boundary: What the Tests Establish vs. What They Do NOT Establish

The repository currently contains **458 automated unit and contract tests**, passing 100% offline with zero external network access, zero container executions, and zero database modifications.

### What the 458 Automated Tests Establish:
1. **Contract Invariants:** State machine transitions, JSONL schema validation, permit verification, citation quotation fidelity, and error-handling fail closed deterministically.
2. **Scoring Invariants:** Abstention accounting mathematically satisfies thesis invariants: abstaining on a vulnerable locus produces an empirical False Negative; abstaining on a benign control does not yield a True Negative; zero denominators yield `MetricStatus.UNDEFINED` rather than `0.0`.
3. **Determinism:** Given identical synthetic inputs or fixture responses, the generation fakes, harness orchestrator, and scoring calculations produce byte-for-byte identical output records.

### What the Automated Tests Do NOT Establish:
1. **No Evidence of Real Vulnerability Detection:** The framework has **never scanned a live web application**. All tests operate exclusively on static synthetic fixtures or in-memory test doubles.
2. **No Empirical Superiority over DAST (ZAP):** Baseline comparison claims remain hypothetical until live benchmark runs are executed.
3. **No Validation of LLM Reasoning Quality:** The multi-agent specialist roles have only run against deterministic mocked generators; LLM prompt effectiveness and hallucination mitigation on live targets remain unmeasured.
4. **No Confirmed Ground Truth:** Zero benchmark cases have been empirically verified or supervisor-adjudicated.

---

## 3. Seven-Category Dataset Accounting & Catalog Breakdown

The proposed exploratory evaluation scope comprises **36 proposed case slots**:
- **24 OWASP Juice Shop slots**
- **12 DVWA slots**

The candidate package strictly distinguishes protocol registrations from verified facts using the following mutually exclusive accounting counts:

```
┌───────────────────────────────────────────────────────────────────┬──────────┐
│ Accounting Dimension                                              │  Count   │
├───────────────────────────────────────────────────────────────────┼──────────┤
│ 1. Protocol-Registered Scenarios (Phase 8E.1 Table 6)             │    16    │
│ 2. Complete Canonical Locus Metadata (Non-null Triples)           │    13    │
│ 3. External Source-Reviewed Candidates                            │    13    │
│ 4. Exact-Version Source-Supported Candidates (Juice Shop v15.0.0) │     8    │
│ 5. Empirically Verified Cases (Live Testbed Replay)               │     0    │
│ 6. Adjudicated Ground-Truth Records (Supervisor Approved)         │     0    │
│ 7. Formally Approved Dataset Partitions                           │     0    │
└───────────────────────────────────────────────────────────────────┴──────────┘
```

### Key Catalog Findings:
- **Only 16 Scenarios are Documented in the Protocol:** The 20 remaining candidate slots (`JS-PROP-12`..`24` and `DVWA-PROP-06`..`12`) are unpopulated placeholders awaiting supervisor locus selection.
- **Zero Local Application Source:** Neither Juice Shop v15.0.0 nor DVWA source code is checked into the repository. All source-level citations represent external code reviews of upstream GitHub repositories.
- **DVWA Image-Version Mismatch:** `testbed/docker-compose.yml` specifies `vulnerables/web-dvwa:1.10`, whereas early catalog drafts referenced `2024.1`. All 5 DVWA cases are formally classified as `VERSION_UNVERIFIED` against the testbed container until the supervisor authorizes the version freeze.

### 3.1 Partition Policy Reconciliation (Protocol Proposal vs. Alternatives)
- **Pre-Registered Protocol Proposal:** In `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§13.3) and `docs/PHASE_8E2A_PROTOCOL_AUDIT.md`, the pre-registered design specifies a **Within-Benchmark Stratified Partitioning** on OWASP Juice Shop: 40% Validation ($N_{\text{val}} \approx 10$ disjoint cases at controller level) / 60% Test ($N_{\text{test}} \approx 14$ disjoint cases), with DVWA held out in its entirety as an independent secondary transfer evaluation partition to test cross-architecture generalization.
- **Alternative Candidate Proposals:** Alternative strategies (such as a 50/50 validation/test split, zero-shot direct evaluation on 100% test cases without validation tuning, or 5-fold cross-validation) were identified during evaluation planning. These are explicitly cataloged in `docs/SUPERVISOR_DECISION_REGISTER.md` under decision `DEC-05` for supervisor selection.
- **Zero Data Leakage Boundary:** Currently, all 36 catalog records have `partition_approval_status: UNASSIGNED` and `assigned_partition: UNASSIGNED`. No cases have been partitioned, tuned against, or assigned, guaranteeing strict test-set isolation until formal approval.

---

## 4. Negative-Control & Methodological Audit

In statistical evaluation, negative controls (benign / non-vulnerable loci) are required to measure **Specificity**, **False Positive Rate ($FPR$)**, and **Selective Risk**. Under strict scientific standards, **absence of a reported flaw in a trial is not proof of safety—benign controls must have positive proof of defensive controls**.

### 4.1 Defective Negative Controls in Early Drafts:
1. **`JS-XSS-R-02` (`GET /rest/products/search?q=<svg onload=...>`):**
   - *Protocol Assumption:* Assumed non-vulnerable because client-side Angular uses DOMPurify.
   - *Reality:* Juice Shop backend API (`routes/search.ts`) reflects the query parameter unencoded in raw JSON. An API-level scanner correctly flags reflection. Client DOMPurify does not render the backend safe.
   - *Status:* **UNSUITABLE as a backend negative control**.
2. **`JS-SQLI-03` (`POST /rest/user/login` Parameterized Query):**
   - *Protocol Assumption:* Assumed non-vulnerable via parameterized query defense.
   - *Reality:* Stock Juice Shop v15.0.0 (`routes/login.ts` L36) uses raw string interpolation into Sequelize. Parameterized login does not exist in stock v15.0.0. Sending `' OR 1=1 --` succeeds.
   - *Status:* **CONTRADICTED BY SOURCE**. Evaluating this on stock containers falsely scores correct detections as false positives.
3. **`JS-SQLI-04` (`GET /rest/products/search?q=test` Ambiguous 500 Error):**
   - *Protocol Assumption:* Assumed non-vulnerable edge case.
   - *Reality:* Malformed input yielding HTTP 500 does not make the endpoint non-vulnerable. `/rest/products/search` is genuinely vulnerable to UNION SQLi.
   - *Status:* **METHODOLOGICAL CONFLATION**. Suitable only as an epistemic uncertainty diagnostic probe, not an independent statistical locus.

### 4.2 Candidate Negative Controls & Five-Layer Evidence Audit:
To prevent equating static source review with empirical proof, all claims are tracked across five distinct epistemological layers:
1. *Source-Code Observation:* Static inspection of an upstream source file or commit.
2. *Exact-Version Source Support:* Code verified against the exact semantic version (e.g., Juice Shop v15.0.0).
3. *Testbed Image/Version Confirmation:* Verification that the executing container matches the audited source.
4. *Empirical Runtime Verification:* Live HTTP traces demonstrating defensive enforcement or vulnerability execution.
5. *Supervisor-Adjudicated Ground Truth:* Formal review and sign-off by the supervisor.

The candidate negative controls evaluated against these five layers are:
1. **`JS-BAC-02` (`GET /rest/admin/application-version`):**
   - *Source-Code Observation & Version Support:* Static review of Juice Shop v15.0.0 (`routes/applicationVersion.ts` L17) confirms `@RolesAllowed('admin')` authorization guard.
   - *Testbed / Runtime Status:* Testbed image confirmation pending container launch; empirical runtime verification pending (HTTP 403 replay trace not yet captured).
   - *Ground-Truth Status:* **Candidate only** (`UNVERIFIED`, awaiting supervisor adjudication).
2. **`DVWA-XSS-R-02` (`GET /vulnerabilities/xss_r/` Impossible Level):**
   - *Source-Code Observation:* Upstream PHP source inspection shows server-side `htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8')`.
   - *Version Support & Testbed Status:* **Version-unverified** against testbed container `vulnerables/web-dvwa:1.10`; runtime verification pending.
   - *Ground-Truth Status:* **Candidate only** (`UNVERIFIED`, awaiting supervisor adjudication).
3. **`DVWA-SQLI-02` (`GET /vulnerabilities/sqli/` Impossible Level):**
   - *Source-Code Observation:* Upstream PHP source inspection shows PDO prepared statement parameter binding (`$stmt->bindParam`).
   - *Version Support & Testbed Status:* **Version-unverified** against testbed container `vulnerables/web-dvwa:1.10`; runtime verification pending.
   - *Ground-Truth Status:* **Candidate only** (`UNVERIFIED`, awaiting supervisor adjudication).

---

## 5. Statistical Constraints & Exploratory Framing

As established in `docs/PHASE_8E2A1_STATISTICAL_REVIEW.md` and `docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md`:

1. **Exploratory, Non-Confirmatory Study:**  
   Given total proposed sample sizes of $N=24$ for Juice Shop and $N=12$ for DVWA, the study possesses limited statistical power for McNemar's paired tests. In paired binary testing, power is governed strictly by the observed number of discordant pairs ($n_{\text{disc}} = b + c$), which cannot be determined a priori. Under high concordance (common when baseline and proposed systems both succeed on obvious flaws or both fail on difficult ones), the effective discordant sample size collapses, severely restricting power to detect true differences. Specific a priori numerical power bounds (such as claiming guaranteed power at $N=36$ or asserting fixed minimum detectable odds ratios without conditioning assumptions) are methodologically unverified.
2. **Failure to Reject $H_0$ Does Not Prove Equivalence:**  
   Under small-sample exploratory conditions, a non-significant result ($p \ge 0.05$) indicates only that the empirical data are insufficient to reject the null of equal marginal accuracy. It **must never be interpreted or claimed as empirical proof of equivalence, parity, or absence of an effect**.
3. **Endpoint Clustering / Lack of Independence:**  
   In Juice Shop, 4 cases cluster on `/rest/products/search` (`q`) and 2 cases cluster on `/rest/user/login` (`email`). This violates the assumption of independent Bernoulli trials unless container state is strictly reset between runs.
4. **Abstention Gating Invariant:**  
   System performance must report both raw Precision/Recall and **Effective Selective Metrics** (coverage-adjusted performance accounting for the Abstention Rate $AR$).

---

## 6. Recommended Approval-Gated Next Steps

```
┌────────────────────────────────────────────────────────┐
│ Stage 1: Supervisor Decision Register Review           │
│ Adjudicate DEC-01 through DEC-08                       │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Target Scope & Negative Control Resolution    │
│ Select remaining 20 candidate loci; freeze DVWA tag    │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Stage 3: Testbed Validation & Image Digest Freeze      │
│ Resolve exact SHA-256 digests; run offline preflight   │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Stage 4: Live Target Replay & Adjudication Trace       │
│ Launch isolated containers; record HTTP replay traces  │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Stage 5: Empirical Benchmark Execution                 │
│ Execute pre-registered conditions (P, B1, B2, A1, A2) │
└────────────────────────────────────────────────────────┘
```

---

## 7. Supporting Document Index

- **Protocol & Design:** [`docs/PHASE_8E1_EVALUATION_PROTOCOL.md`](file:///s:/AegisCore/docs/PHASE_8E1_EVALUATION_PROTOCOL.md)
- **Statistical Audits:** [`docs/PHASE_8E2A1_STATISTICAL_REVIEW.md`](file:///s:/AegisCore/docs/PHASE_8E2A1_STATISTICAL_REVIEW.md), [`docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md`](file:///s:/AegisCore/docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md)
- **Testbed Engineering:** [`docs/PHASE_8E2B_OFFLINE_HARNESS.md`](file:///s:/AegisCore/docs/PHASE_8E2B_OFFLINE_HARNESS.md), [`testbed/docker-compose.yml`](file:///s:/AegisCore/testbed/docker-compose.yml)
- **Evaluation Framework:** [`docs/PHASE_8E3_EVALUATION_CONTRACTS.md`](file:///s:/AegisCore/docs/PHASE_8E3_EVALUATION_CONTRACTS.md), [`docs/PHASE_8E4_OFFLINE_EVALUATION_HARNESS.md`](file:///s:/AegisCore/docs/PHASE_8E4_OFFLINE_EVALUATION_HARNESS.md)
- **Provenance Audits:** [`docs/PHASE_8E6_CATALOG_PROVENANCE_AUDIT.md`](file:///s:/AegisCore/docs/PHASE_8E6_CATALOG_PROVENANCE_AUDIT.md), [`docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md`](file:///s:/AegisCore/docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md)
- **Draft Catalog & Templates:** [`docs/case_catalog_draft.jsonl`](file:///s:/AegisCore/docs/case_catalog_draft.jsonl), [`docs/ground_truth_review_template.jsonl`](file:///s:/AegisCore/docs/ground_truth_review_template.jsonl), [`docs/partition_assignment_template.jsonl`](file:///s:/AegisCore/docs/partition_assignment_template.jsonl)
- **Decision Register:** [`docs/SUPERVISOR_DECISION_REGISTER.md`](file:///s:/AegisCore/docs/SUPERVISOR_DECISION_REGISTER.md)
