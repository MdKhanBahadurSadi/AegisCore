# AEGISCORE AI — Phase 8E.2A
# Evaluation Protocol Consistency Audit

**Document ID:** DOC-PHASE-8E2A-PROTOCOL-AUDIT  
**Status:** COMPLETE / DOCUMENTATION-ONLY  
**Date:** 2026-10-27  
**Project:** AEGISCORE AI  
**Thesis Title:** “An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment”  
**Context:** Comprehensive consistency and rigor audit of the thesis evaluation protocol established in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` prior to benchmark container installation or harness execution. Evaluated against `docs/REQUIREMENTS.md`, `docs/PHASE_8D1_MULTI_AGENT_DESIGN.md`, and the current Phase 8D.4 repository state.

---

## 1. Executive Findings

This audit evaluated the evaluation protocol and benchmark design (`docs/PHASE_8E1_EVALUATION_PROTOCOL.md`) across research question feasibility, statistical rigor, benchmark validity, metric soundess, and baseline fairness.

### Core Audit Findings
1. **Implementation vs. Research Capability Disconnect:**
   - The repository passes 351 unit and integration tests. These tests establish that the *deterministic contracts, orchestration state machine (`OrchestrationStateMachine`), structural citation provenance validator, verbatim citation excerpt validator (`validate_citation_excerpt`), and fail-closed response gating* function as designed.
   - However, real LLM specialist agents, live HTTP target execution, dynamic vector retrieval, and calibrated probabilistic uncertainty do **not** exist in the codebase. Deterministic fakes (`DeterministicVulnerabilityAnalystFake`, `DeterministicEvidenceReviewerFake`, `DeterministicUncertaintyAssessorFake`) use token heuristics and static keywords. They must **never** be cited as evidence of LLM vulnerability assessment performance.
2. **Dataset Size and Statistical Power Reality:**
   - The proposed sample size of $N \approx 36$ cases (18 positive, 18 negative) is adequate for an **exploratory academic prototype study**, but severely underpowered for confirmatory clinical-grade statistical inference.
   - Under McNemar's test for paired binary outcomes ($\alpha = 0.05, \beta = 0.20$), a sample size of $N = 36$ can only detect large effect sizes ($\Delta \ge 0.28\text{--}0.30$, odds ratios $\ge 6.0$). Subtle performance shifts between conditions will fail to reach statistical significance.
   - The thesis manuscript must frame its evaluation as an **exploratory proof-of-concept benchmark**, reporting exact effect sizes and bootstrap confidence intervals rather than relying solely on null-hypothesis $p$-values.
3. **Partitioning Flaw in Section 13 (Open Decision 3):**
   - Section 13 Item 3 of the Phase 8E.1 protocol proposed a split of "30% Validation (DVWA) / 70% Test (Juice Shop)".
   - **Audit Verdict: Methodologically Flawed.** DVWA (a classic PHP Multi-Page Application) and OWASP Juice Shop (a modern Node.js/Angular Single Page Application) have fundamentally different architectural paradigms, attack surfaces, and error distributions. Calibrating confidence thresholds or training conformal predictors on DVWA PHP form observations and evaluating them on Juice Shop JSON REST APIs introduces severe out-of-distribution domain shift.
   - **Correction:** Calibration and test splits must use **within-benchmark stratified partitioning** (e.g., partitioning Juice Shop endpoints into disjoint 40% validation / 60% test subsets, and evaluating DVWA as an independent parallel secondary benchmark).
4. **Unit of Analysis Disambiguation & Pseudo-Replication:**
   - The protocol must explicitly define the **Unit of Analysis** as the canonical test case locus: `(Target URI, Injection Parameter, CWE Class)`.
   - Repeated trials ($K = 3$ runs per case) capture stochastic run-to-run variance; they do **not** multiply the effective sample size from $N = 36$ to $N = 108$. Treating repeated trials as independent observations would constitute pseudo-replication.
5. **Abstention Metric Accounting:**
   - The protocol must provide dual accounting for abstentions:
     - Under **Standard Detection Metrics (Confusion Matrix):** An `ABSTAINED` decision on a vulnerable case counts as a non-detection (False Negative); on a non-vulnerable case, it is a non-report (clean).
     - Under **Selective Classification Metrics (Risk-Coverage):** Abstentions are excluded from the reporting denominator, directly measuring the trade-off between coverage ($\Phi$) and selective error risk ($R(\Phi)$).
6. **Probabilistic Calibration Constraints:**
   - Evaluating Expected Calibration Error ($ECE$) with $M = 10$ bins on $N = 36$ cases yields an average of only 3.6 observations per bin, rendering 10-bin ECE statistically noisy and biased.
   - Calibration assessment must be limited to Brier score or adaptive quantile binning with $M = 3$ bins, accompanied by bootstrap standard errors and labeled as exploratory.

---

## 2. RQ-by-RQ Feasibility Matrix

Table 1 audits each research question and hypothesis defined in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`.

### Table 1: Research Question Feasibility and Testability Audit

| RQ ID & Target Hypothesis | Independent Variable (IV) | Dependent Variables (DV) | Unit of Analysis | Baseline / Comparison Condition | Ground-Truth Requirement | Confounding Factors | Testability Status in Current Codebase |
|---|---|---|---|---|---|---|---|
| **RQ1 (False-Positive Reduction)**  <br>*H1: Abstention reduces FPR vs. B2* | Gating mechanism: Active uncertainty abstention ($P$) vs. Disabled ($B2$). | Precision, FPR, Number of False Positives ($FP$). | Canonical Case Locus `(URI, Param, CWE)`. | $B2$ (Multi-Agent + RAG without abstention). | Pre-registered binary ground truth (Vulnerable / Clean). | Token budget exhaustion; prompt sensitivity; non-deterministic tool errors. | **Future Experiment:** State machine contracts exist; requires LLM provider and validation threshold. |
| **RQ2 (Recall & Detection Coverage)**  <br>*H2: Abstention trade-off depends on vulnerability class* | Decision threshold $\theta_{\text{abstain}}$ calibrated on validation split. | Class-stratified Recall ($Recall_{XSS}$, $Recall_{SQLi}$, $Recall_{BAC}$). | Canonical Case Locus `(URI, Param, CWE)`. | $B2$ (Multi-Agent without abstention). | Pre-registered ground-truth instances across the 3 classes. | Imbalanced class difficulty (BAC is inherently more ambiguous than XSS). | **Future Experiment:** Requires benchmark runner and LLM provider. |
| **RQ3 (Confidence Calibration)**  <br>*H3: Calibrated probabilities achieve lower ECE than raw verbal scores* | Calibration method: Raw verbal confidence vs. Post-hoc calibration. | Brier Score, 3-bin ECE, Reliability diagrams. | Single finding prediction probability $p_i \in [0, 1]$. | Raw self-reported model verbal confidence. | Empirical binary correctness of candidate findings. | Small sample size ($N \approx 36$); temperature drift; discrete rating collapse. | **Future Experiment:** Requires validation split, calibration algorithm (Platt/Isotonic), and LLM provider. |
| **RQ4 (Traceability & Grounding)**  <br>*H4: Verbatim excerpt verification eliminates citation hallucinations* | Citation excerpt enforcement: Active `validate_citation_excerpt` ($P$) vs. Unverified baseline. | Citation Grounding Error Rate, Hallucinated Excerpt Count. | Proposed claim citation record `(chunk_id, excerpt)`. | Unverified generation output (raw LLM citations). | Verified lexical chunk content in approved RAG corpus. | Model verbatim copying ability vs paraphrasing; corpus chunk boundary artifacts. | **Verified Contracts:** Unit tests (`test_citation_excerpt_*`) prove contract; experimental validation requires live LLM. |
| **RQ5 (Ablations: RAG & Reviewer)**  <br>*H5: No-RAG ($A1$) lowers precision; No-Reviewer ($A2$) inflates benign FPs* | Architectural state: Full ($P$) vs. No-RAG ($A1$) vs. No-Reviewer ($A2$). | Precision, Recall, Evidence Completeness, FP Count on benign controls. | Canonical Case Locus `(URI, Param, CWE)`. | Full System ($P$) paired against $A1$ and $A2$. | Pre-registered ground truth with explicit benign defense controls. | Prompt length variations across ablations; LLM attention degradation. | **Future Experiment:** State machine supports empty bundle (`SCEN-MA-02`); requires LLM integration. |
| **RQ6 (Overhead & Efficiency)**  <br>*H6: Multi-agent overhead is offset by triage time saved* | System architecture: DAST ($B1$) vs. Single-Agent ($B3$) vs. Proposed ($P$). | Wall-clock latency (s), Total tokens, HTTP tool calls, Cost/TP. | Full scenario execution trace. | $B1$ (OWASP ZAP) and $B3$ (Single-Agent LLM). | Confirmed True Positives ($TP$) verified by ground truth. | Hardware network variance; provider rate limits; non-deterministic retries. | **Future Experiment:** Requires automated test harness and cost estimation model. |

---

## 3. Dataset and Statistical Design Audit

### 3.1 Disambiguation of Evaluation Units

To eliminate ambiguity and prevent invalid statistical pooling, the protocol strictly defines five distinct operational units:

1. **Vulnerability Instance:** The specific security defect residing in application code or server configuration (e.g., Juice Shop challenge `restPinLoginChallenge` at `POST /rest/user/login`).
2. **Individual Test Case (Assessment Instance):** The primary **Unit of Analysis ($N$)** evaluated by the framework. Defined by the canonical locus triple: `(Target URI, Injection Parameter / Input Vector, CWE Vulnerability Class)`. All detection metrics (TP, FP, FN, TN) are evaluated at this level.
3. **Repeated Run ($K = 3$ Trials):** A complete, isolated execution of a specific experimental condition ($B1, B2, B3, P, A1, A2$) against an individual test case.
   - *Aggregation Rule:* Repeated runs evaluate stochastic consistency. A test case outcome is aggregated across the $K = 3$ trials via majority vote ($2/3$ consensus) for primary hypothesis testing, or modeled using Generalized Estimating Equations (GEE) / Mixed-Effects Logistic Regression to account for within-case clustering.
   - *Statistical Warning:* Repeated trials do **not** increase sample size ($N = 36$, not $108$).
4. **Scanner Alert:** A raw warning emitted by OWASP ZAP or a candidate finding emitted by an agent. Multiple alerts may reference the same parameter.
5. **Unique Finding:** A deduplicated finding cluster representing one canonical triple within a test run. Multiple raw alerts for the same triple are collapsed into a single finding cluster before evaluation.

### 3.2 Sample Size and Statistical Power Analysis

The protocol proposes an evaluation set of $N \approx 36$ test cases (18 positive, 18 negative; balanced across XSS, SQLi, and BAC).

#### Power Calculation (McNemar's Paired Test)
For paired binary outcomes between the proposed system $P$ and baseline $B2$:
- Let $n_{10}$ be cases where $P$ is correct and $B2$ is incorrect (discordant pairs favoring $P$).
- Let $n_{01}$ be cases where $B2$ is correct and $P$ is incorrect.
- Under a two-tailed test with significance level $\alpha = 0.05$ and total sample size $N = 36$:
  - To achieve conventional statistical power ($1 - \beta = 0.80$), the number of discordant pairs must satisfy $n_{10} + n_{01} \ge 16$ with an odds ratio of $n_{10} / n_{01} \ge 5.0$.
  - This corresponds to a minimum detectable absolute performance difference of $\Delta \ge 0.28$ (e.g., an increase in accuracy from $60\%$ to $88\%$).

#### Audit Conclusion on Statistical Power
- **Small-Sample Reality:** With $N = 36$, the evaluation is powered to detect **only large, prominent effects**. It cannot reliably discern subtle improvements ($\Delta < 0.15$).
- **Methodological Recommendation:**
  1. The thesis must explicitly state this statistical boundary in the Methodology and Limitations sections.
  2. Null findings ($p > 0.05$) must be interpreted as "insufficient statistical power to rule out moderate effects," rather than proof that no difference exists.
  3. All metric reports must prioritize **effect sizes and 95% BCa Bootstrap Confidence Intervals** over bare $p$-values.

---

## 4. Benchmark and Data Leakage Risks

### 4.1 Audit of the 5 Leakage Vectors

### Table 2: Benchmark Data Leakage Assessment and Mitigations

| Leakage Vector | Risk Description | Audit Finding | Mandatory Mitigation |
|---|---|---|---|
| **Vector 1: Prompt Leakage** | System prompts or role instructions containing Juice Shop / DVWA challenge names, solution payloads, or endpoint paths. | High risk if developer incorporates benchmark solutions into prompt engineering. | All prompts must be generic security guidance only (e.g., standard OWASP WSTG methodologies). Zero benchmark-specific challenge keywords in prompts. |
| **Vector 2: Retrieval Corpus Leakage** | RAG corpus chunks containing walkthroughs, writeups, or specific exploit payloads for Juice Shop or DVWA. | Critical risk. Ingesting blogs or GitHub repositories could provide the exact exploit string. | The approved corpus must strictly contain official, general documentation: OWASP WSTG v4.2, ASVS v4.0.3, Top 10 (2021), and MITRE CWE text. Hash-verified manifest check (`validate_manifest_integrity`). |
| **Vector 3: Cross-Split Near-Duplicate Leakage** | Similar endpoints or identical parameters split across validation and test partitions (e.g., two search parameters on the same controller). | Moderate risk. Overfitting to specific controller quirks. | Stratified partitioning must occur at the **controller / service level**, ensuring no shared endpoints between validation and test splits. |
| **Vector 4: Cross-Benchmark Domain Shift** | Using DVWA for validation/calibration and Juice Shop for testing (as originally proposed in Section 13). | **Critical Flaw:** Severe domain mismatch. DVWA PHP forms do not represent Juice Shop Angular REST APIs; confidence calibration will not transfer. | **Mandatory Redesign:** Within-benchmark stratified partitioning for Juice Shop. DVWA evaluated as an independent parallel secondary benchmark. |
| **Vector 5: Ground-Truth State Leakage** | Automated agents reading target scoreboard or challenge status APIs (`/api/Challenges`) during assessment. | Critical risk. Framework could query the target to see if an exploit succeeded. | Network and tool isolation: The `GuardedExecutionBoundary` allowlist permits only the specific target endpoint under test; access to `/api/Challenges` or admin APIs is blocked fail-closed. |

### 4.2 Defensible Partitioning Scheme

The audit establishes the following defensible partitioning protocol:

1. **Primary Benchmark (OWASP Juice Shop):**
   - Total Pool: 24 curated test cases (12 positive, 12 negative).
   - **Validation Set (40% / 10 cases):** 5 positive, 5 negative cases used exclusively for:
     - Selecting and freezing the abstention decision threshold $\theta_{\text{abstain}}$.
     - Calibrating composite confidence score weights.
     - Estimating Platt scaling / Isotonic regression parameters.
   - **Test Set (60% / 14 cases):** 7 positive, 7 negative cases used exclusively for final frozen evaluation.
   - **Disjoint Partitioning Rule:** No endpoint or controller present in the Validation Set may appear in the Test Set.
2. **Secondary Benchmark (DVWA):**
   - Total Pool: 12 curated test cases (6 positive on Low/Med, 6 negative on Impossible).
   - Evaluated as an independent, frozen cross-validation suite to test whether the system's defensive rejection mechanisms generalize to classic PHP Multi-Page architectures without re-tuning.

---

## 5. Metric-Definition Audit

### Table 3: Metric Definition, Denominator, and Edge-Case Audit

| Metric | Mathematical Formula | Denominator Definition | Edge-Case Handling (Empty Denominators & Abstentions) | Audit Finding & Recommendation |
|---|---|---|---|---|
| **Precision** | $\frac{TP}{TP + FP}$ | Total verified reported findings ($TP + FP$). | If $TP + FP = 0$: Undefined. Set to $1.0$ if target contains 0 vulnerabilities; set to $0.0$ if target contains $>0$ vulnerabilities. | **Valid.** Must be paired with Recall to avoid reporting empty sets as 100% precision. |
| **Recall** | $\frac{TP}{TP + FN}$ | Total ground-truth vulnerable instances present in test suite ($N_{\text{pos}}$). | Fixed positive integer ($N_{\text{pos}} = 7$ on test set). Never empty. Abstentions on vulnerable cases count as $FN$. | **Valid.** Accurately penalizes excessive abstention. |
| **F1-Score** | $2 \cdot \frac{P \cdot R}{P + R}$ | Precision + Recall. | If $P + R = 0$, $F_1 = 0.0$. | **Valid.** Harmonic mean balances false alarms and missed detections. |
| **False-Positive Rate (FPR)** | $\frac{FP}{FP + TN}$ | Total ground-truth non-vulnerable instances ($N_{\text{neg}}$). | Fixed negative integer ($N_{\text{neg}} = 7$ on test set). Never empty. Abstentions on non-vulnerable cases count as clean non-reports ($TN$). | **Valid.** Measures rate of false alarms on benign targets. |
| **Coverage ($\Phi$)** | $\frac{N - N_{\text{abstain}}}{N}$ | Total test cases evaluated ($N$). | $N > 0$. $\Phi \in [0, 1]$. | **Valid.** Standard selective prediction formulation. |
| **Selective Risk ($R(\Phi)$)** | $\frac{FP}{TP + FP}$ | Total non-abstained reported findings. | If system abstains on all cases ($N_{\text{abstain}} = N$), risk is undefined. | **Valid.** Measures error rate specifically on the cases where the system chose to report. |
| **Abstention Rate ($AR$)** | $\frac{N_{\text{abstain}}}{N}$ | Total test cases evaluated ($N$). | $N > 0$. $AR = 1 - \Phi$. | **Valid.** Complements coverage. |
| **Verified Finding Rate ($VFR$)** | $\frac{N_{\text{verified}}}{N_{\text{candidate}}}$ | Total candidate findings generated by specialists. | If $N_{\text{candidate}} = 0$, $VFR = 0.0$. | **Valid.** Measures filtering selectivity of verifier/reviewer pipeline. |
| **Severity Agreement ($\kappa_w$)** | $1 - \frac{\sum w_{ij} O_{ij}}{\sum w_{ij} E_{ij}}$ | Expected chance agreement matrix. | If all findings share identical predicted and actual severity, $\kappa_w = 1.0$. | **Valid.** Evaluates CVSS severity tier calibration independently of detection. |
| **Brier Score** | $\frac{1}{N} \sum (p_i - y_i)^2$ | Total predictions evaluated ($N$). | $p_i \in [0, 1], y_i \in \{0, 1\}$. | **Valid.** Standard strictly proper scoring rule. |
| **Expected Calibration Error (ECE)** | $\sum_{m=1}^M \frac{\|B_m\|}{N} \|\text{acc}(B_m) - \text{conf}(B_m)\|$ | Total predictions ($N$). Partitioned into $M$ bins. | **Critical Caveat:** On $N = 14$ test cases, standard $M=10$ binning is invalid. Must use $M=3$ quantile bins with bootstrap error bars. | **Refined.** Flag as exploratory metric due to sample size. |
| **Operational Efficiency** | Mean wall-clock time, prompt/completion tokens, HTTP tool calls. | Total test cases ($N$). | Failed runs that time out are capped at 120s ceiling. | **Valid.** Measures computational overhead. |

### 5.1 Verification Boundary Clarification
- **Structural Citation Validity vs. Semantic Entailment:**  
  The audit confirms that `validate_citation_excerpt` (implemented in Phase 8D.4) verifies that the cited text is a **verbatim substring** of an approved source chunk.  
  Passing this check confirms *structural provenance and absence of hallucinated quotes*. It does **not** evaluate whether the source logically entails or proves the vulnerability claim. This boundary must remain explicitly documented.

---

## 6. Baseline Fairness Checklist

To ensure that performance differences are attributable to the proposed multi-agent architecture rather than confounding experimental artifacts, Table 4 audits baseline fairness.

### Table 4: Baseline Fairness Control Audit

| Experimental Dimension | OWASP ZAP Baseline ($B1$) | Multi-Agent w/o Abstention ($B2$) | Single-Agent Baseline ($B3$) | Proposed Multi-Agent ($P$) | Fairness Status / Verification Rule |
|---|---|---|---|---|---|
| **Endpoint Discovery** | Pre-mapped OpenAPI routes provided. | Pre-mapped OpenAPI routes provided. | Pre-mapped OpenAPI routes provided. | Pre-mapped OpenAPI routes provided. | **Fair.** Eliminates crawling disparities between SPA and traditional tools. |
| **Target Scope & Whitelist** | Exact target URL allowlist. | Exact target URL allowlist. | Exact target URL allowlist. | Exact target URL allowlist. | **Fair.** Identical target boundary enforced. |
| **HTTP Request Budget** | Max 50 requests per endpoint. | Max 50 requests per endpoint. | Max 50 requests per endpoint. | Max 50 requests per endpoint. | **Fair.** Prevents brute-force or scanner denial of service. |
| **Execution Timeout** | 120s wall-clock ceiling. | 120s wall-clock ceiling. | 120s wall-clock ceiling. | 120s wall-clock ceiling. | **Fair.** Bounded time limits. |
| **Target State Reset** | Fresh DB seed before every case. | Fresh DB seed before every case. | Fresh DB seed before every case. | Fresh DB seed before every case. | **Fair.** Eliminates state pollution from prior runs. |
| **LLM Model & Version** | N/A (Rule heuristics). | Fixed model digest (e.g. `gemini-1.5-pro-002`). | Fixed model digest (identical to $B2, P$). | Fixed model digest (identical to $B2, B3$). | **Fair.** Holds foundation model constant across all LLM conditions. |
| **Sampling Temperature** | N/A. | $\tau = 0.0$ (Greedy). | $\tau = 0.0$ (Greedy). | $\tau = 0.0$ (Greedy). | **Fair.** Minimizes stochastic variance. |
| **RAG Evidence Access** | None (Rule-based). | Approved RAG corpus snapshot. | Approved RAG corpus snapshot. | Approved RAG corpus snapshot. | **Fair.** Baselines $B2, B3, P$ receive identical retrieval context. |
| **Ground-Truth Visibility** | Zero ground-truth access. | Zero ground-truth access. | Zero ground-truth access. | Zero ground-truth access. | **Fair.** Benchmark solutions strictly excluded from all agents and scanners. |

---

## 7. Threats to Validity Audit

1. **Construct Validity:**
   - *Risk:* Automated ground-truth matching based on `(URI, Param, CWE)` might reject valid vulnerability findings that identify genuine secondary flaws not in the ground-truth key.
   - *Audit Verdict:* Mitigated by manual supervisor adjudication for unmapped candidate findings, tagging them as `SECONDARY_VALID` or `FALSE_POSITIVE`.
2. **Internal Validity:**
   - *Risk:* Prompt formatting variations between Single-Agent ($B3$) and Multi-Agent ($P$) might account for performance shifts rather than multi-agent specialization.
   - *Audit Verdict:* Single-agent prompt must incorporate the exact instructions and evidence verification checklists utilized across the individual specialist roles.
3. **External Validity:**
   - *Risk:* Generalizing claims from synthetic benchmarks (Juice Shop, DVWA) to complex enterprise web applications.
   - *Audit Verdict:* Claims must be strictly bounded to the evaluated benchmark classes: modern Single Page Applications and classic Multi-Page Applications running in isolated lab environments.
4. **Conclusion Validity:**
   - *Risk:* Over-interpreting differences with small sample sizes ($N \approx 36$).
   - *Audit Verdict:* Statistical conclusions must be framed as exploratory; effect sizes and bootstrap intervals are mandatory.

---

## 8. Prioritized Corrections to `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`

Based on this audit, the following five concrete updates must be applied to `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`:

1. **Correction 1 (Section 13, Item 3): Replace Cross-Benchmark Validation Split.**
   - *Original Text:* Suggested 30% Validation (DVWA) / 70% Test (Juice Shop).
   - *Correction:* Update to **Within-Benchmark Stratified Partitioning** on Juice Shop (40% Validation / 60% Test), designating DVWA as an independent parallel secondary benchmark to prevent domain mismatch.
2. **Correction 2 (Section 5 & 8): Formalize Unit of Analysis & Prevent Pseudo-Replication.**
   - *Original Text:* Implicitly treated test cases without formal distinction from repeated runs.
   - *Correction:* Explicitly define the primary unit of analysis as the canonical case locus `(URI, Param, CWE)`. Clarify that repeated runs ($K=3$) evaluate stochastic variance and are aggregated via consensus vote, maintaining $N$ as the true sample size.
3. **Correction 3 (Section 5.1 & 7.1): Formalize Dual Abstention Accounting.**
   - *Original Text:* Warned that abstentions are never TN, but did not formalize their role in standard confusion matrices.
   - *Correction:* Explicitly define dual accounting: (a) Standard confusion matrix counts abstentions on positive cases as False Negatives ($FN$); (b) Selective classification evaluates abstentions via the Coverage ($\Phi$) and Selective Risk ($R(\Phi)$) trade-off curve.
4. **Correction 4 (Section 7.1): Refine Calibration Metrics for Small Sample Size.**
   - *Original Text:* Standard 10-bin ECE formula.
   - *Correction:* Add explicit constraint restricting ECE to $M = 3$ quantile bins with bootstrap error bars, labeling calibration evaluation as exploratory due to sample size.
5. **Correction 5 (Section 1 & 5.1): Reiterate Structural vs. Semantic Entailment Boundary.**
   - *Original Text:* Defined citation excerpt verification.
   - *Correction:* Reiterate that excerpt validation proves lexical presence, not semantic entailment or factual truth.

---

## 9. Supervisor Decisions Required Before Implementation

Prior to commencing Phase 8E.2B (Isolated Benchmark Environment Setup), the thesis supervisor must review and approve:

1. **Adoption of Within-Benchmark Stratified Partitioning:** Approve the replacement of the cross-benchmark DVWA/Juice Shop split with within-benchmark partitioning.
2. **LLM Provider Architecture:** Confirm whether the study will use local models (e.g., Llama-3.1-70B via vLLM, zero-egress) or cloud APIs (e.g., Gemini 1.5 Pro via approved ADR 0002 egress exception).
3. **Evaluation Dataset Scope:** Confirm the 24-case Juice Shop + 12-case DVWA evaluation suite (total $N=36$ cases) as an exploratory academic sample.
4. **Statistical Framing:** Approve framing the empirical findings as an exploratory proof-of-concept study reporting effect sizes and bootstrap confidence intervals.

---

## 10. Go / No-Go Checklist for Phase 8E.2B

| Gate Item | Criteria | Status | Verdict |
|---|---|---|---|
| **Protocol Consistency** | All ambiguities and partitioning flaws in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` resolved. | Resolved via Phase 8E.2A audit. | **GO** |
| **Worktree Cleanliness** | All 351 unit/integration tests passing; zero git whitespace errors. | Verified (351 passed, git diff clean). | **GO** |
| **Corpus Governance** | Source review manifest remains candidate-only; zero unapproved chunks. | Verified (`no_sources_approved`). | **GO** |
| **Supervisor Review** | Open decisions formally submitted for supervisor review. | Documented in Section 9. | **PENDING SUPERVISOR REVIEW** |
| **Container & Lab Isolation** | Target containers must not be launched until harness design is finalized. | No containers created or run. | **HOLD (Phase 8E.2B)** |

**Overall Gate Assessment:** The evaluation protocol design is rigorous, consistent, and ready for supervisor review. No benchmark containers or scanners should be executed until supervisor decisions are rendered.
