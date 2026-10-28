# AEGISCORE AI — Phase 8E.2A.1
# Statistical Claims & Evaluation Feasibility Review

**Document ID:** DOC-PHASE-8E2A1-STAT-REVIEW  
**Status:** COMPLETE / DOCUMENTATION-ONLY  
**Date:** 2026-10-27  
**Project:** AEGISCORE AI  
**Thesis Title:** “An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment”  
**Context:** In-depth evidence-based review of the statistical claims, sample size constraints, calibration feasibility, and metric-to-implementation mappings in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` and `docs/PHASE_8E2A_PROTOCOL_AUDIT.md`. Designed to eliminate unsupported statistical assertions, prevent invalid inferences, and establish realistic academic boundaries prior to supervisor sign-off.

---

## 1. Executive Summary

This review provides a critical methodological and statistical audit of the proposed thesis evaluation protocol. Its purpose is to ensure that every statistical claim, sample size justification, and metric definition in AEGISCORE AI rests on verified assumptions and reproducible mathematics rather than wishful thinking.

### Core Review Conclusions
1. **Unverified Statistical Power Claims:**
   - The assertion in prior drafts that a sample size of $N \approx 36$ cases provides $80\%$ statistical power to detect effect sizes of $\Delta \ge 0.25\text{--}0.30$ under McNemar’s test is **unverified and contingent on unstated assumptions**.
   - In paired binary testing, statistical power is governed not by the total sample size $N$, but by the **number of discordant pairs** ($n_{\text{disc}} = b + c$). If baseline and proposed systems agree on most cases (high concordance), the effective sample size for McNemar’s test collapses, reducing power dramatically.
   - **Mandatory Correction:** The thesis must abandon any claim of confirmatory statistical power. The evaluation must be explicitly designated and reported as an **exploratory proof-of-concept benchmark study**.
2. **Small-Sample Calibration Limitations:**
   - On the primary benchmark test split ($N = 14$ cases), Expected Calibration Error ($ECE$) cannot provide reliable probabilistic calibration measurement. Dividing 14 cases into bins yields severe small-sample bias where individual misclassifications dominate the metric.
   - Furthermore, AEGISCORE AI currently possesses **no continuous probabilistic confidence engine**; its uncertainty assessor relies on deterministic keyword heuristics. Therefore, calibration cannot be empirically measured until a real post-hoc calibration pipeline (e.g., Platt scaling or conformal prediction) is implemented.
   - **Mandatory Correction:** Brier score and adaptive 3-bin ECE must be classified as *Tier 2/3 exploratory metrics*, subordinate to direct detection metrics (Precision, Recall, Selective Risk).
3. **Validation / Test Partition Sensitivity:**
   - Tuning an abstention threshold $\theta_{\text{abstain}}$ on only 10 validation cases (5 positive, 5 negative) means that each validation case shifts empirical precision or recall by $10\text{--}20\%$. Threshold optimization on such a small sample is vulnerable to high variance and noise fitting.
   - **Mandatory Correction:** Threshold selection must use conservative, coarse-grained grid search (e.g., evaluating only 3 candidate operational thresholds: $\theta \in \{0.5, 0.7, 0.85\}$) rather than fine-grained continuous optimization.
4. **Implementation Reality Check:**
   - The current repository successfully passes 351 unit and integration tests. These tests prove the correctness of **deterministic state machine transitions, typed schema contracts, structural citation provenance checks, and fail-closed safety boundaries**.
   - They do **not** demonstrate real-world LLM vulnerability detection, live DAST scanning, semantic entailment, or probability calibration. Deterministic fake agents output synthetic strings from static fixtures.
5. **Concrete Recommendation:**
   - **GO** for Phase 8E.2B container harness engineering and Docker Compose scripting (offline engineering).
   - **STRICT HOLD** on launching containers, executing scanners, or running benchmark evaluations until the thesis supervisor formally reviews the open decisions and approves the exploratory framing.

---

## 2. Statistical Claims and Power Audit

### 2.1 McNemar’s Paired Test Mechanics and Power Collapse

In `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§8.1) and `docs/PHASE_8E2A_PROTOCOL_AUDIT.md` (§3.2), the protocol proposes using McNemar’s test with continuity correction to evaluate binary differences in detection success ($TP$ vs. $FP/FN$) between the proposed workflow ($P$) and the baseline ($B2$).

#### Mathematical Formulation
Let each of the $N$ canonical evaluation cases be classified as 1 (Correct: TP on positive, TN on negative) or 0 (Incorrect: FP or FN). The paired outcomes across $P$ and $B2$ form a $2 \times 2$ table:

| Condition | $B2$ Correct (1) | $B2$ Incorrect (0) | Total |
|---|---|---|---|
| **$P$ Correct (1)** | $a$ (Concordant Correct) | $b$ (Discordant: $P$ wins) | $a + b$ |
| **$P$ Incorrect (0)** | $c$ (Discordant: $B2$ wins) | $d$ (Concordant Incorrect) | $c + d$ |
| **Total** | $a + c$ | $b + d$ | $N$ |

The continuity-corrected McNemar test statistic is:
$$\chi^2 = \frac{(|b - c| - 1)^2}{b + c}$$
Under $H_0$, $P(b) = P(c) = 0.5$. The critical value for $\alpha = 0.05$ (1 degree of freedom) is $\chi^2_{\text{crit}} = 3.841$.

#### Why the Prior Power Claim is Unverified
Statistical power for McNemar’s test is a function of the **discordant pair total** $n_{\text{disc}} = b + c$ and the discordance ratio $\psi = b / c$, **not** $N$ alone:
1. **Scenario 1 (High Concordance, $n_{\text{disc}} = 8$):**  
   Suppose baseline and proposed systems agree on 28 out of 36 cases ($a + d = 28$), leaving only 8 discordant cases ($b + c = 8$).  
   Even in the extreme case where $P$ outperforms $B2$ on 7 out of 8 discordant cases ($b = 7, c = 1$):
   $$\chi^2 = \frac{(|7 - 1| - 1)^2}{7 + 1} = \frac{25}{8} = 3.125 < 3.841 \implies p \approx 0.077 \quad (\text{Not Significant!})$$
   Despite an overwhelming odds ratio ($7:1$), the test fails to reject $H_0$ because discordant pairs are too few.
2. **Scenario 2 (Moderate Concordance, $n_{\text{disc}} = 14$):**  
   If $b = 11, c = 3$:
   $$\chi^2 = \frac{(|11 - 3| - 1)^2}{14} = \frac{49}{14} = 3.500 < 3.841 \implies p \approx 0.061 \quad (\text{Not Significant!})$$
3. **Scenario 3 (High Discordance Required for Significance, $n_{\text{disc}} \ge 12$):**  
   To achieve statistical significance ($\chi^2 \ge 3.841$), the test requires at least $b = 10, c = 1$ ($\chi^2 = 5.82, p = 0.016$) or $b = 11, c = 2$ ($\chi^2 = 4.92, p = 0.026$).

#### Audit Finding
- The claim that $N = 36$ provides $80\%$ power to detect an effect size of $\Delta = 0.25$ made an implicit, unstated assumption that almost all cases would be discordant ($n_{\text{disc}} \ge 18$). In web application security assessments, baseline scanners and LLMs frequently agree on obvious cases (e.g., both easily detect blatant reflected XSS, or both fail on complex blind SQLi).
- **Status:** **UNVERIFIED AND METHODOLOGICALLY FLAWED.**
- **Remedy:** The thesis must remove claims of guaranteed statistical power. It must state that McNemar’s test is evaluated conditionally on the observed discordant sample, reporting exact binomial sign test $p$-values alongside effect sizes.

---

### 2.2 Bootstrap Resampling Constraints on Small Samples

The protocol proposes computing 95% Bias-Corrected and Accelerated (BCa) Bootstrap Confidence Intervals using $B = 2{,}000$ resamples.

#### Methodological Reality
1. **Sample Granularity:** When bootstrapping on the test partition ($N = 14$ cases), each observation represents $1/14 \approx 7.14\%$ of the sample.
2. **BCa Degeneracy Risk:** The acceleration parameter ($a$) in BCa estimation relies on the skewness of the jackknife distribution. For $N < 20$, jackknife replicates with discrete binary outcomes frequently produce undefined acceleration or extreme boundary distortion when resampling rare events (e.g., zero false positives in a bootstrap sample).
3. **Remedy:**
   - For single proportions (e.g., Precision, Recall), report exact **Clopper-Pearson** or **Wilson Score** intervals, which are mathematically guaranteed to cover the true parameter under small samples.
   - For comparative differences ($\Delta \text{Precision}, \Delta \text{Recall}$), use **Percentile Bootstrap** with explicit warnings regarding small-sample granularity.

---

## 3. Validation, Test Isolation, and Calibration Feasibility

### 3.1 Feasibility of Threshold Tuning on 10 Validation Cases

The protocol proposes partitioning OWASP Juice Shop into a **Validation Set of 10 cases** (5 positive, 5 negative) and a **Test Set of 14 cases** (7 positive, 7 negative).

#### Critique of Threshold Tuning on $N_{\text{val}} = 10$
- In a sample of 5 positive cases, a single case misclassification shifts sensitivity by $20\%$. In 5 negative cases, a single false alarm shifts specificity by $20\%$.
- Attempting continuous optimization of the abstention threshold $\theta_{\text{abstain}} \in [0.0, 1.0]$ on 10 cases is susceptible to **severe sample variance and overfitting**. A threshold chosen to maximize $F_1$ on these 10 cases will overfit to the idiosyncratic evidence quality of those specific endpoints.
- **Protocol Correction:**
  1. $\theta_{\text{abstain}}$ must **not** be continuously tuned.
  2. The research design must pre-register a small, discrete set of conservative operational thresholds:
     - $\theta_{\text{permissive}} = 0.50$ (Report if more likely than not)
     - $\theta_{\text{standard}} = 0.70$ (Require substantial evidence completeness)
     - $\theta_{\text{conservative}} = 0.85$ (High confidence; default to abstention under ambiguity)
  3. The validation set is used solely to verify that $\theta_{\text{standard}}$ prevents false positives on the 5 negative validation cases without suppressing all 5 positive cases.

### 3.2 Test Set Isolation and Leakage Audit

To prevent subtle data leakage between validation and test partitions:
1. **Controller-Level Segregation:** The partition must not split parameters of the same controller across splits. For example, `/rest/products/search` (search controller) cannot be in validation while `/rest/products/{id}/reviews` is in test.
2. **Session / State Decoupling:** Validation cases must not rely on database state mutated during test case execution.
3. **RAG Corpus Snapshot Isolation:** The RAG retrieval corpus must be frozen *before* validation begins. No document chunking, metadata updates, or source additions may occur based on validation observations.

### 3.3 Calibration and Adaptive 3-Bin ECE

Expected Calibration Error ($ECE$) measures the weighted average difference between confidence and accuracy across confidence bins:
$$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} |\text{acc}(B_m) - \text{conf}(B_m)|$$

#### Feasibility on $N_{\text{test}} = 14$ Cases
- Dividing $N = 14$ into $M = 3$ bins yields an average of only $4.6$ cases per bin.
- If Bin 1 has 4 cases, the empirical accuracy $\text{acc}(B_1)$ can take only 5 discrete values: $\{0.0, 0.25, 0.50, 0.75, 1.0\}$.
- Such small bin populations mean that ECE measures **binomial discretization noise** rather than true model miscalibration.
- **Critical Architectural Pre-requisite:** AEGISCORE AI currently outputs categorical states (`DecisionOutcome.VERIFIED`, `DecisionOutcome.ABSTAINED`) and heuristic keyword counts. It does **not** output continuous probabilities $p_i \in [0, 1]$.
- **Conclusion:** ECE is **completely unmeasurable** in the current codebase and cannot be evaluated until a continuous calibration function (e.g., logistic calibration of evidence features) is implemented and validated.

---

## 4. Unit of Analysis and Repeated Trials

### 4.1 Definitional Hierarchy

Table 1 establishes the strict operational hierarchy of evaluation units, eliminating all risk of pseudo-replication.

### Table 1: Operational Evaluation Hierarchy

| Level | Entity | Definition | Sample Size Contribution | Handling in Analysis |
|---|---|---|---|---|
| **Level 1** | **Vulnerability Instance** | The concrete source code flaw or architectural weakness. | Contextual descriptor. | One vulnerability instance may expose multiple loci (e.g., multiple injection parameters). |
| **Level 2** | **Canonical Case Locus** | Unique tuple: `(Target URI, Injection Parameter, CWE Class)`. | **The Unit of Analysis ($N = 14$ Test, $N = 10$ Val, $N = 12$ DVWA).** | All confusion matrix entries ($TP, FP, FN, TN$) are tallied strictly at this level. |
| **Level 3** | **Repeated Run (Trial)** | One execution of an experimental condition against a locus ($K = 3$ trials). | **$0$ (Does NOT increase $N$).** | Evaluates stochastic run-to-run variance. Aggregated to Level 2 via majority vote ($2/3$). |
| **Level 4** | **Specialist Candidate Finding** | Unverified hypothesis emitted by Vulnerability Specialist. | Intermediate artifact. | Subject to deduplication and verification gating; never directly scored against ground truth. |
| **Level 5** | **Scanner Alert / Finding Cluster** | Deduplicated finding cluster matching a canonical locus. | Evaluated against Level 2. | Multiple raw alerts for the same locus collapse to 1 report before scoring. |

### 4.2 Repeated Runs of Deterministic Fakes vs. LLMs
- In the current repository, running $K = 3$ repeated trials of `DeterministicVulnerabilityAnalystFake` or `DeterministicUncertaintyAssessorFake` yields **identical byte-for-byte outputs** across all 3 runs. It provides zero empirical variance information.
- For future LLM evaluations ($\tau = 0.0$): Repeated runs capture floating-point nondeterminism across hardware server clusters and network timeouts. Majority voting ($2/3$ agreement across the 3 runs) yields the definitive decision for that locus.

---

## 5. Metric-to-Implementation Feasibility Matrix

Table 2 classifies every metric proposed in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` into one of three feasibility tiers based on the actual Phase 8D.4 repository code.

### Table 2: Metric-to-Implementation Feasibility Matrix

| Metric Name | Required Inputs | Unit of Analysis | Feasibility Tier | Implementation Pre-requisites & Key Limitations |
|---|---|---|---|---|
| **Precision** | Reported verified findings, ground-truth label key. | Canonical Case Locus | **Tier 2: Measurable after LLM harness** | Orchestration contracts exist (`OrchestrationStateMachine`). Requires real LLM output and benchmark execution. Undefined if $TP + FP = 0$. |
| **Recall (Sensitivity)** | Verified true positives, ground-truth positive cases. | Canonical Case Locus | **Tier 2: Measurable after LLM harness** | Requires executing test cases against live target. Abstentions on positive cases penalize recall as $FN$. |
| **F1-Score** | Precision and Recall. | Canonical Case Locus | **Tier 2: Measurable after LLM harness** | Harmonic mean. Subject to small-sample granularity. |
| **False-Positive Rate (FPR)** | False positives, ground-truth negative cases. | Canonical Case Locus | **Tier 2: Measurable after LLM harness** | Requires pre-registered negative controls (e.g., hardened endpoints). |
| **Abstention Rate ($AR$)** | Terminal `ABSTAINED` state counts, total cases. | Canonical Case Locus | **Tier 1: Currently measurable on contracts** | State machine supports `TERMINAL_ABSTAINED` (`SCEN-MA-02`, `04`, `08`). Evaluated against fakes today; requires live LLM for research claims. |
| **Coverage ($\Phi$)** | Non-abstained reporting decisions, total cases. | Canonical Case Locus | **Tier 1: Currently measurable on contracts** | $\Phi = 1 - AR$. Measures selective decision willingness. |
| **Selective Risk ($R(\Phi)$)** | False positives among reported cases. | Canonical Case Locus | **Tier 2: Measurable after LLM harness** | $R(\Phi) = 1 - \text{Precision}$. Measures error rate on covered subset. |
| **Verified Finding Rate ($VFR$)** | Count of findings reaching `VERIFIED` vs `CANDIDATE`. | Finding Cluster | **Tier 1: Currently measurable on contracts** | State machine enforces candidate-to-verified transition. Currently exercised in unit test doubles. |
| **Severity Agreement ($\kappa_w$)** | Predicted CVSS severity vs Ground-truth severity. | Verified Finding | **Tier 2: Measurable after LLM harness** | Severity enum exists (`FindingSeverity`). Requires LLM severity reasoning against test cases. |
| **Brier Score** | Predicted probability $p_i \in [0, 1]$, binary outcome $y_i$. | Prediction | **Tier 3: NOT currently supported** | **Codebase Gap:** Uncertainty assessor outputs discrete heuristics, not continuous calibrated probabilities. Requires post-hoc calibration pipeline. |
| **Expected Calibration Error (ECE)** | Binned continuous probabilities and accuracies. | Binned Predictions | **Tier 3: NOT justified by study design** | **Statistically Invalid:** $N = 14$ test cases cannot support calibration binning. ECE is dominated by small-sample binomial noise. |
| **Wall-Clock Latency** | Execution start and end timestamps. | Scenario Run | **Tier 2: Measurable after live harness** | Requires live HTTP transport and real network timers. |
| **Token Consumption** | Prompt tokens, completion tokens. | Scenario Run | **Tier 2: Measurable after LLM harness** | Requires token accounting from real LLM provider API responses. |
| **Tool / HTTP Count** | Guarded request permits emitted by boundary. | Scenario Run | **Tier 1: Currently measurable on permits** | `GuardedExecutionBoundary` tracks request counts against budget (`SCEN-MA-12`). |
| **Component Ablation Impact** | Metrics across conditions $P, A1, A2$. | Comparative Metric | **Tier 2: Measurable after LLM harness** | Empty bundle state path exists (`SCEN-MA-02`); requires real LLM to measure impact of RAG removal. |

---

## 6. Citation and Evidence Claims Audit

### 6.1 Structural Excerpt Matching vs. Semantic Truth

To prevent misleading claims in the thesis:
- **What Phase 8D.4 Implements:** `validate_citation_excerpt` (in `aegiscore/claim_validation.py`) verifies that `cited_excerpt` is an exact, verbatim substring within the approved `chunk.content` identified by `chunk_id`. It confirms lexical presence and structural provenance.
- **What Phase 8D.4 Does NOT Implement:** It does **not** evaluate semantic entailment (whether the text logically supports the claim), natural language inference (NLI), or empirical vulnerability truth.
- **Thesis Reporting Invariant:** Passing citation validation proves that the model cited genuine text from approved security guidance without hallucinating quotes; it does **not** prove that the reported vulnerability actually exists in the target web application.

---

## 7. Prioritized Protocol Corrections

The following four concrete corrections must be applied to `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`:

1. **Correction 1 (Section 8.3 — Statistical Limitations):**  
   Replace all claims of guaranteed 80% power with an explicit **exploratory study framing**. State that McNemar’s test power depends on the number of discordant pairs ($n_{\text{disc}}$), which cannot be assumed in advance. Mandate reporting exact effect sizes and bootstrap intervals.
2. **Correction 2 (Section 7.1 — Calibration Metrics):**  
   Reclassify Expected Calibration Error ($ECE$) and Brier Score as **Tier 3 Exploratory Metrics**, noting that AEGISCORE AI currently implements heuristic uncertainty gating, and that $N = 14$ test cases cannot support confirmatory calibration measurement.
3. **Correction 3 (Section 13, Item 2 — Dataset Framing):**  
   Explicitly label the 24-case Juice Shop + 12-case DVWA suite as an **exploratory academic proof-of-concept dataset**, rather than a high-power confirmatory sample.
4. **Correction 4 (Section 13, Item 3 — Threshold Selection):**  
   Update the within-benchmark validation strategy to specify coarse-grained discrete threshold selection ($\theta \in \{0.50, 0.70, 0.85\}$) to prevent overfitting on $N_{\text{val}} = 10$ cases.

---

## 8. Questions Requiring Supervisor Decisions

The following concrete questions are formally submitted for supervisor review:

1. **Statistical Framing:** Does the supervisor approve framing the thesis evaluation as an **exploratory proof-of-concept benchmark** focusing on effect sizes, selective prediction trade-offs (Coverage vs. Risk), and qualitative error analyses, rather than confirmatory hypothesis testing?
2. **Calibration Scope:** Given that $N_{\text{test}} = 14$ cases cannot yield statistically meaningful ECE bins, does the supervisor approve treating probabilistic calibration as a secondary, exploratory objective subordinate to discrete abstention gating?
3. **Threshold Selection Grid:** Does the supervisor approve restricting threshold selection on the 10 validation cases to a discrete 3-point grid ($\theta \in \{0.50, 0.70, 0.85\}$) to prevent overfitting?
4. **LLM Provider Choice:** Does the supervisor select Cloud-based Gemini 1.5 Pro (via approved ADR 0002 egress exception) or a Local Open-Weights Model (e.g., Llama-3.1-70B on local GPU, strictly zero-egress)?

---

## 9. Concrete GO / HOLD Recommendation for Phase 8E.2B

### Phase Gate Recommendation: **CONDITIONAL GO / SPLIT DECISION**

| Subsystem / Task | Recommendation | Operational Boundary |
|---|---|---|
| **Phase 8E.2B Docker Harness Engineering** | **GO** | Authorized to construct isolated Docker Compose files, network bridge configurations, and target reset scripts. Strictly offline engineering. |
| **Benchmark Installation & Container Launch** | **HOLD** | Do NOT launch containers, start background services, or deploy benchmarks until supervisor decisions in Section 8 are signed off. |
| **Scanner Execution & Target Payloads** | **HOLD** | Absolutely no scanning, payload delivery, or test execution against targets. |
| **LLM Provider Egress** | **HOLD** | No external API calls or provider connections until supervisor formally selects Provider Option A or B. |

**Rationale:** Container architecture, network isolation configs, and testbed scripting can be safely developed offline without executing attacks or spending API budgets. Live execution must remain on hold until supervisor governance is complete.
