# AEGISCORE AI — Phase 8E.7.1
# Supervisor Package Consistency & Statistical Claim Audit

**Document ID:** DOC-PHASE-8E7-1-AUDIT  
**Date:** 2026-10-28  
**Project:** AEGISCORE AI  
**Thesis Title:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Status:** COMPLETE / DOCUMENTATION-ONLY AUDIT  
**Scope:** Narrow, offline consistency audit and evidence traceability review of `docs/SUPERVISOR_REVIEW_PACKAGE.md` and `docs/SUPERVISOR_DECISION_REGISTER.md` prior to formal supervisor submission.

---

## 1. Executive Summary & Audit Objectives

Following the generation of the consolidated supervisor review package and formal decision register in Phase 8E.7, Phase 8E.7.1 executes a rigorous quality audit to ensure that:
1. **Statistical Claims are Rigorous and Reproducible:** All assertions regarding statistical power, sample sizes, and McNemar's paired tests strictly adhere to mathematical principles established in `docs/PHASE_8E2A1_STATISTICAL_REVIEW.md` and `docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md`. Unsupported numerical thresholds (e.g., claiming guaranteed power at $N=36$, fixed required odds ratios $OR \ge 3.0$, or unconditioned discordant counts $b-c \ge 8$) are removed.
2. **Equivalence Inferences are Prohibited:** The package explicitly specifies that failure to reject the null hypothesis ($p \ge 0.05$) under an exploratory sample size does **not** demonstrate equivalence, parity, or absence of an effect.
3. **Evidence Terminology is Epistemologically Layered:** Source-code observations, version-pinned support, testbed image confirmation, empirical runtime traces, and supervisor adjudication are explicitly distinguished. Negative controls and DVWA candidate cases are strictly classified according to these layers.
4. **Dataset Partition Decisions are Reconciled:** The pre-registered protocol proposal (Within-Benchmark Stratified 40% validation / 60% test on Juice Shop; DVWA secondary transfer) is clearly distinguished from alternative candidate proposals in `DEC-05`, confirming that all 36 records currently remain `UNASSIGNED`.
5. **Decision Register Integrity is Maintained:** All decisions (`DEC-01` through `DEC-08`) remain strictly `PENDING`, with zero fabricated reviewer identities, dates, or responses.

---

## 2. Audit of Statistical Claims

### 2.1 McNemar's Paired Test Mechanics and Power Collapse
In paired binary evaluations, the statistical power of McNemar's test is governed not by the total sample size ($N$), but exclusively by the **number of observed discordant pairs** ($n_{\text{disc}} = b + c$).
- In web application security assessment, automated tools and LLM agents frequently exhibit high concordance on obvious vulnerabilities (both detect blatant XSS or both fail on multi-step blind SQLi).
- When concordance is high ($a + d \gg b + c$), the effective sample size for McNemar's test collapses. For example, if two systems agree on 30 of 36 cases, only 6 discordant pairs remain. In such small discordant samples, even an overwhelming effect size (e.g., $b=5, c=1$) cannot achieve statistical significance at $\alpha = 0.05$ under an exact binomial test.

### 2.2 Numerical Thresholds Audited and Corrected
- **Audit Finding:** Early draft notes and summary text asserted that $N=36$ (or $N=24$) allows detecting differences with odds ratios $OR \ge 3.0$, or required discordant counts $b - c \ge 8 \text{ to } 12$. These specific numerical bounds were calculated under unstated, idealized concordance assumptions and represent unverified pseudo-precision.
- **Action Taken:**
  - Removed all specific numerical power bounds from `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§5) and `docs/SUPERVISOR_DECISION_REGISTER.md` (`DEC-01`).
  - Replaced them with the mathematically defensible principle: McNemar's test power depends strictly on the observed count of discordant pairs ($n_{\text{disc}} = b + c$), which cannot be determined a priori.
  - Formally mandated that exact binomial sign test $p$-values and empirical odds ratios be reported conditionally on the observed discordant sample.

### 2.3 Absence of Evidence vs. Evidence of Absence
- **Audit Finding:** In underpowered or exploratory benchmarks, a common inferential error is interpreting a non-significant result ($p \ge 0.05$) as proof that two systems perform identically (e.g., claiming "the multi-agent framework achieves parity with DAST").
- **Action Taken:** Enforced the explicit thesis invariant across both the review package (§5.2) and decision register (`DEC-01` Option A):
  > "A failure to reject the null hypothesis ($p \ge 0.05$) under this exploratory sample size must **never** be interpreted or reported as empirical evidence of equivalence, parity, or absence of an effect. It indicates only that the observed sample is insufficient to reject the null of equal marginal accuracy."

---

## 3. Five-Layer Evidence Hierarchy & Negative-Control Classification

To eliminate ambiguity between static source inspection, container configurations, and empirical findings, all evaluation loci are formally audited against five distinct epistemological layers:

```
┌────────────────────────────────────────────────────────┐
│ Layer 1: Source-Code Observation                       │
│ Static inspection of upstream GitHub code or literature│
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 2: Exact-Version Source Support                  │
│ Code verified against exact release tag (e.g. v15.0.0) │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 3: Testbed Image/Version Confirmation            │
│ Verifying running Docker container matches source      │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 4: Empirical Runtime Verification                │
│ Dynamic HTTP request/response trace captured in lab    │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 5: Supervisor-Adjudicated Ground Truth           │
│ Formal sign-off and approval by thesis supervisor      │
└────────────────────────────────────────────────────────┘
```

### 3.1 Classification of Candidate Negative Controls
Applying this 5-layer hierarchy to the proposed negative controls resolves prior ambiguities:

| Locus ID | Candidate Target | Layer 1 & 2: Source Support | Layer 3: Image Confirmation | Layer 4: Runtime Replay | Layer 5: Adjudication | Current Status |
|---|---|---|---|---|---|:---:|
| **`JS-BAC-02`** | `GET /rest/admin/application-version` | Supported in Juice Shop v15.0.0 (`routes/applicationVersion.ts` L17: `@RolesAllowed('admin')`) | Pending container launch | Pending HTTP 403 trace | `UNVERIFIED` (Pending `DEC-03`) | **Candidate Control** |
| **`DVWA-XSS-R-02`** | `GET /vulnerabilities/xss_r/` (Impossible) | Supported in upstream DVWA source (`htmlspecialchars`) | **VERSION_UNVERIFIED** against image `1.10` | Pending HTTP replay | `UNVERIFIED` (Pending `DEC-03`) | **Candidate Control** |
| **`DVWA-SQLI-02`** | `GET /vulnerabilities/sqli/` (Impossible) | Supported in upstream DVWA source (PDO prepared statement) | **VERSION_UNVERIFIED** against image `1.10` | Pending HTTP replay | `UNVERIFIED` (Pending `DEC-03`) | **Candidate Control** |
| **`JS-XSS-R-02`** | `GET /rest/products/search?q=...` | Contradicted at backend API (returns raw JSON; DOMPurify is client-only) | N/A | N/A | Excluded from primary matrix | **Defective (Ablation Probe Only)** |
| **`JS-SQLI-03`** | `POST /rest/user/login` (Parameterized) | **Contradicted by source** (Sequelize string interpolation) | N/A | N/A | Excluded from catalog | **Defective (Contradicted)** |
| **`JS-SQLI-04`** | `GET /rest/products/search` (Malformed 500) | Endpoint is vulnerable to UNION SQLi; 500 is input handling | N/A | N/A | Excluded from primary matrix | **Defective (Uncertainty Probe Only)** |

---

## 4. Dataset Partition Reconciliation

### 4.1 Reconciliation of Discrepancies
- **Pre-Registered Protocol Proposal:** In `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§13.3) and `docs/PHASE_8E2A_PROTOCOL_AUDIT.md`, the pre-registered strategy is a **Within-Benchmark Stratified Partitioning** on OWASP Juice Shop:
  - **Validation Set ($N_{\text{val}} \approx 10$ cases, 40%):** Disjoint subset at the controller route level, used for coarse prompt validation or threshold checking.
  - **Test Set ($N_{\text{test}} \approx 14$ cases, 60%):** Disjoint subset held out strictly for final reported performance.
  - **Secondary Benchmark:** DVWA held out in its entirety ($N = 12$ cases) as an independent parallel secondary transfer evaluation suite.
- **Alternative Candidate Proposals in Decision Register:** During audit reviews, alternative partition approaches were identified and structured under `DEC-05`:
  - *Option B (50/50 Split):* 12 validation / 12 test cases on Juice Shop for balanced split.
  - *Option C (Zero-Shot Direct Evaluation):* 100% test cases without validation split tuning.
  - *Option D (K-Fold Cross-Validation):* 5-fold cross-validation.
- **Audit Correction:** Updated `docs/SUPERVISOR_DECISION_REGISTER.md` (`DEC-05`) and `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§3.1) to explicitly identify Option A (40/60 split) as the **Pre-Registered Protocol Proposal**, labeling all other options as **Alternative Candidate Proposals** awaiting supervisor selection.
- **Zero Leakage Invariant:** Verified that all 36 records in `docs/partition_assignment_template.jsonl` currently have `partition_approval_status: "UNASSIGNED"` and `assigned_partition: "UNASSIGNED"`. Zero cases have been assigned, partitioned, or exposed to tuning.

---

## 5. Decision Register Integrity Verification

All 8 decisions in `docs/SUPERVISOR_DECISION_REGISTER.md` were audited:
- `DEC-01`: Approval of Exploratory Statistical Framing
- `DEC-02`: Acceptance or Revision of Proposed Evaluation Scope ($N=36$)
- `DEC-03`: Ground-Truth Review and Adjudication Procedure
- `DEC-04`: Case Inclusion/Exclusion & Negative-Control Resolution
- `DEC-05`: Approval of Validation / Test Partition Policy
- `DEC-06`: Benchmark Version and Immutable Image-Digest Policy
- `DEC-07`: Model-Provider Architecture Selection (Cloud vs. Local)
- `DEC-08`: Explicit Authorization for Container Startup & Live Execution

**Integrity Verification Results:**
1. All 8 decisions have status **`PENDING`**.
2. Zero supervisor identities, names, or signatures were fabricated.
3. Decision Date fields are all set to `[Pending Formal Adjudication]`.
4. Supervisor Rationale & Notes fields are all set to `[To be completed upon formal supervisor review]`.
5. Each decision record contains all required structural fields: Decision ID, Question, Available Options, Relevant Evidence, Risks & Trade-offs, Decision Owner, Status, Date, and Rationale.

---

## 6. Summary of Corrections Applied

1. **`docs/SUPERVISOR_REVIEW_PACKAGE.md`:**
   - Added Section 3.1: Partition Policy Reconciliation (Protocol 40/60 vs. Alternative Proposals).
   - Expanded Section 4.2: Five-layer evidence hierarchy for candidate negative controls (`JS-BAC-02`, `DVWA-XSS-R-02`, `DVWA-SQLI-02`).
   - Replaced Section 5: Removed unverified numerical power bounds ($b-c \ge 8..12$, fixed odds ratios); added explicit mandate that failure to reject $H_0$ ($p \ge 0.05$) does not prove equivalence.
2. **`docs/SUPERVISOR_DECISION_REGISTER.md`:**
   - Updated `DEC-01`: Explicitly incorporated exploratory framing principles, exact binomial sign tests, and equivalence disclaimers.
   - Updated `DEC-04`: Re-framed candidate negative controls under the 5-layer hierarchy, explicitly noting DVWA cases as version-unverified against image `1.10`.
   - Updated `DEC-05`: Formally designated the 40/60 within-benchmark split as the Pre-Registered Protocol Proposal, presenting 50/50, zero-shot, and K-fold as alternative candidate options.
3. **`PROJECT_STATUS.md`:**
   - Added entry for Phase 8E.7.1, recording the completion of this consistency audit and enforcement of the approval boundary.

---

## 7. Verification Results

| Check | Target / Command | Exit Code | Result |
| :--- | :--- | :---: | :--- |
| **Git diff syntax check** | `git diff --check` | `0` | Passed (no trailing whitespace or conflict markers) |
| **Source manifest integrity** | `git diff -- docs/source-review-manifest.json` | `0` | Clean (100% byte-unmodified) |
| **Database file check** | `Get-ChildItem -Recurse -Include *.db,*.sqlite,*.sqlite3` | `0` | Clean (zero database files exist in workspace) |
| **Full test suite** | `pytest -q -p no:cacheprovider` | `0` | **458 passed** in 7.04s |

---

## 8. Final Recommendation

### **GO for Supervisor Review Package Submission**
### **STRICT HOLD on Live Execution, Testbed Launch, Scanning, and Model Integration**

This audit confirms that the supervisor review package and decision register are internally consistent, statistically sound, traceable to upstream evidence, and free of unsupported assertions. 

The package is ready for thesis supervisor presentation. Live execution remains strictly blocked until formal adjudication of Decisions `DEC-01` through `DEC-08`.
