# AEGISCORE AI — Phase 8E.2A.2
# Statistical Review Corrections & Evidence Traceability

**Document ID:** DOC-PHASE-8E2A2-STAT-CORRECTIONS  
**Status:** COMPLETE / DOCUMENTATION-ONLY  
**Date:** 2026-10-27  
**Project:** AEGISCORE AI  
**Thesis Title:** “An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment”  
**Context:** Methodological reconciliation and evidence traceability review following Phase 8E.2A.1. Resolves remaining statistical inconsistencies in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` and `docs/PHASE_8E2A1_STATISTICAL_REVIEW.md` prior to authorizing offline testbed harness configuration.

---

## 1. Executive Summary

### Core Resolutions
1. **Statistical Power Claims Traceability:** Specific numerical power bounds (such as "power collapses below 0.40 at $b+c \le 8$") and prior sample size power assertions are formally classified as **unverified pseudo-precision**. They are replaced with a mathematically grounded qualitative limitation: McNemar's test power is governed strictly by the observed number of discordant pairs ($n_{\text{disc}} = b + c$), which cannot be determined a priori. Under high concordance, power to detect true differences is severely limited. Crucially, a non-significant result ($p \ge 0.05$) under small-sample constraints **does not demonstrate equivalence** or absence of effect.
2. **Confidence Interval Formulations:** Corrected an invalid statistical recommendation in earlier reviews. Exact **Clopper–Pearson** intervals (or score-based **Wilson Score** intervals) are strictly applicable to **single binomial proportions** with fixed or conditional trial denominators (Recall, FPR, Abstention Rate). They are **methodologically invalid for F1-Score**, which is a non-linear harmonic mean of two distinct random proportions. For F1 and comparative paired differences, case-resampled **Percentile Bootstrap** intervals must be reported alongside constituent proportion intervals.
3. **Threshold and Calibration Feasibility:** Inspection of the actual codebase confirms that `UncertaintyAssessment` (`aegiscore/orchestration.py:370`) and `DeterministicUncertaintyAssessorFake` (`aegiscore/specialist_roles.py:620`) emit discrete states and heuristic flags, enforcing `confidence_is_calibrated: Literal[False] = False`. No continuous probability score exists, and the state machine evaluates boolean `abstention_recommended` rather than a numerical threshold $\theta$. Proposing a continuous threshold grid ($\theta \in \{0.50, 0.70, 0.85\}$) in the current executable protocol is therefore **unimplementable in existing code** and is deferred as a future feature conditional on a score-producing model. Brier Score and ECE remain future-only.
4. **Metric Feasibility Taxonomy:** Replaced ambiguous feasibility labels with a 3-tier taxonomy:
   - *Contract-Level Computable:* Data structures and transition logic exist in the codebase and execute on synthetic/deterministic inputs.
   - *Benchmark Measurable:* Requires live target execution, ground-truth label keys, and Ground-Truth Evaluator (MOD-11).
   - *Not Currently Supported:* Required model outputs or mathematical structures do not exist in the codebase today.
5. **Repeated-Trial Guarantees:** Confirmed that unit tests (`tests/test_specialist_roles.py`, `tests/test_generation.py`) verify dataclass equality (`assert finding1 == finding2`) for synthetic fixtures. Python fakes are pure functions with zero runtime variance. Repeated trials ($K=3$) capture stochastic variance only when non-deterministic LLMs are evaluated, and they **never** inflate sample size beyond the canonical locus ($N \approx 36$).

---

## 2. Audit of Previous Methodological Claims

Table 1 audits all previous methodological claims across Phase 8E.1, 8E.2A, and 8E.2A.1, classifying each as Retained with Justification, Corrected, Marked Unverified, or Deferred until Implementation.

### Table 1: Comprehensive Claim Traceability Matrix

| Claim ID | Original Claim Text | Source Document | Audit Disposition | Rationale and Action Taken |
|---|---|---|---|---|
| **CLM-01** | "$N = 36$ provides 80% power to detect effect sizes of $\Delta \ge 0.28\text{--}0.30$ under McNemar’s test ($\alpha = 0.05$)." | `PHASE_8E1_EVALUATION_PROTOCOL.md` (§8.3) | **Marked Unverified & Corrected** | Made an unstated assumption of high discordance ($n_{\text{disc}} \ge 18$). Replaced with qualitative statement that power depends on $b + c$ and cannot be guaranteed a priori. |
| **CLM-02** | "If concordance is high ($b + c \le 8$), power collapses below 0.40 even for true odds ratios exceeding 4.0." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§2.1) | **Marked Unverified (Numerical Bound)** | While exact conditional binomial power at $n_{\text{disc}}=8$ for $\psi=0.8$ is $\approx 0.168$, stating a single hard power bound without full conditioning specifications creates unverified pseudo-precision. Replaced with exact qualitative formulation. |
| **CLM-03** | "A non-significant $p$-value cannot be interpreted as evidence of equivalence." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§2.1) | **Retained with Justification** | Core statistical principle: failure to reject $H_0$ in an underpowered study reflects insufficient evidence, not proof of identical performance. |
| **CLM-04** | "Apply exact Clopper-Pearson or Wilson Score intervals to Precision, Recall, and F1." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§2.2) | **Corrected** | Methodologically invalid for F1. Wilson/Clopper-Pearson applies only to binomial proportions (Recall, FPR, AR). F1 is a non-binomial ratio; it must be estimated via Percentile Bootstrap or reported as constituent intervals. |
| **CLM-05** | "BCa bootstrap intervals suffer from degeneracy on small discrete samples ($N \le 20$)." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§2.2) | **Retained with Justification** | Jackknife acceleration calculation frequently breaks down or produces extreme endpoint distortion when resampling sparse binary events. |
| **CLM-06** | "Threshold tuning on $N_{\text{val}} = 10$ cases must use a discrete 3-point grid $\theta \in \{0.50, 0.70, 0.85\}$." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§3.1) | **Deferred until Implementation** | Code inspection confirms `UncertaintyAssessment` emits discrete states and boolean `abstention_recommended`. The state machine has no numerical threshold $\theta$ parameter. Grid is future-only. |
| **CLM-07** | "ECE and Brier Score require $N > 100$ to avoid empirical bin noise." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§3.3) | **Marked Unverified (Heuristic Rule)** | $N > 100$ is a literature rule-of-thumb heuristic (e.g., Niculescu-Mizil & Caruana 2005), not a proven mathematical bound. Explicitly relabeled as a literature heuristic. |
| **CLM-08** | "Current code outputs categorical states, not continuous calibrated probabilities; `confidence_is_calibrated: Literal[False]`." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§3.3) | **Retained with Justification** | Verified directly in `aegiscore/orchestration.py:385` and `specialist_roles.py:682`. Calibration metrics are impossible today. |
| **CLM-09** | "The primary Unit of Analysis is the Canonical Case Locus `(URI, Param, CWE)` ($N \approx 36$)." | `PHASE_8E2A_PROTOCOL_AUDIT.md` (§3.1) | **Retained with Justification** | Essential safeguard against pseudo-replication. Repeated runs ($K=3$) and raw scanner alerts aggregate to this level. |
| **CLM-10** | "Running $K=3$ trials of deterministic fakes produces byte-for-byte identical outputs." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§4.2) | **Retained with Justification** | Verified by unit tests `test_identical_inputs_yield_identical_outputs` (SCEN-MA-16) and `test_deterministic_output_for_identical_inputs`. Fakes are pure functions. |
| **CLM-11** | "Citation excerpt validation proves structural presence, not semantic truth." | `PHASE_8E2A1_STATISTICAL_REVIEW.md` (§6.1) | **Retained with Justification** | Verified in `aegiscore/claim_validation.py:270`. Validates exact substring match in approved chunk; does not evaluate semantic entailment. |
| **CLM-12** | "Abstentions are never counted as true negatives." | `PHASE_8E1_EVALUATION_PROTOCOL.md` (§5.1) | **Retained with Justification** | Foundational thesis invariant. Abstaining on a vulnerable target is a False Negative ($FN$); abstaining on non-vulnerable target is an abstention, not a True Negative ($TN$). |

---

## 3. Task 1 — Statistical Power Claim Traceability

### 3.1 McNemar’s Test Power Mechanics
McNemar’s test evaluates paired nominal data under the null hypothesis of marginal homogeneity:
$$H_0: p_{10} = p_{01} \iff \psi = \frac{p_{10}}{p_{01}} = 1.0$$
where $b$ is the count of loci where System A is correct and System B is incorrect, and $c$ is the reverse. The total sample size $N$ is partitioned into concordant pairs $n_{\text{conc}} = a + d$ and discordant pairs $n_{\text{disc}} = b + c$.

Under the conditional approach, conditional on the observed discordant total $n_{\text{disc}} = b + c$, the distribution of $b$ follows a binomial distribution:
$$b \mid n_{\text{disc}} \sim \text{Binomial}\left(n_{\text{disc}}, \frac{\psi}{1 + \psi}\right)$$
Under $H_0$, $\frac{\psi}{1 + \psi} = 0.5$.

### 3.2 Audit of Power Numbers
- **Prior Claim 1 (8E.1):** "80% power to detect $\Delta \ge 0.28\text{--}0.30$ at $N = 36$."  
  *Audit:* Unsubstantiated. In paired designs, $\Delta = (b - c)/N$. Achieving $\Delta = 0.28$ on $N = 36$ implies $b - c \approx 10$. If $b = 10, c = 0$, $n_{\text{disc}} = 10$. If $b = 15, c = 5$, $n_{\text{disc}} = 20$. Statistical power varies drastically between these two cases despite identical $\Delta$.
- **Prior Claim 2 (8E.2A.1):** "Power collapses below 0.40 when $b + c \le 8$."  
  *Audit:* While an exact two-sided binomial test with $n_{\text{disc}} = 8$ at $\alpha = 0.05$ has rejection region $\{0, 8\}$ (giving power $0.168$ at $\text{OR}=4$ and $0.344$ at $\text{OR}=7$), presenting a single hard number ("$<0.40$") without fully documenting the test type, continuity correction, and parameter space conveys false precision.

### 3.3 Methodological Directive
1. All specific numerical power claims are removed from the evaluation protocol.
2. The protocol must state qualitatively:
   > "McNemar’s test power depends strictly on the count of discordant pairs ($n_{\text{disc}} = b + c$), which cannot be determined prior to empirical execution. In security benchmarking, high concordance on obvious cases is common, which restricts the effective discordant sample size and severely limits power to detect true differences."
3. **No Proof of Equivalence Rule:** The protocol must explicitly state:
   > "A failure to reject the null hypothesis ($p \ge 0.05$) under this exploratory sample size must not be interpreted as empirical evidence of equivalence or parity between systems. It indicates only that the observed sample is insufficient to reject the null of equal marginal accuracy."

---

## 4. Task 2 — Confidence Intervals & Estimation Strategy

### 4.1 Single-Proportion Metrics vs. Ratio Metrics
In Phase 8E.2A.1, the review recommended using Clopper-Pearson or Wilson Score intervals for "Precision, Recall, and F1". This recommendation contains a serious statistical flaw:

1. **Binomial Proportions (Clopper–Pearson / Wilson Score Valid):**
   - **Recall (Sensitivity):** $\text{Recall} = \frac{TP}{TP + FN}$. The denominator $TP + FN = N_{\text{vulnerable}}$ is fixed by the pre-registered benchmark test suite. Each vulnerable locus represents an independent Bernoulli trial. Therefore, Recall is a true single binomial proportion. Exact **Clopper–Pearson Intervals** (or score-based **Wilson Score Intervals**) are methodologically sound and recommended.
   - **False Positive Rate ($FPR$):** $\text{FPR} = \frac{FP}{FP + TN}$. The denominator $FP + TN = N_{\text{non-vulnerable}}$ is fixed by the pre-registered negative controls. This is a true single binomial proportion. Exact **Clopper–Pearson** or score-based **Wilson Score** intervals are valid.
   - **Abstention Rate ($AR$):** $AR = \frac{N_{\text{abstained}}}{N_{\text{total}}}$. The denominator $N_{\text{total}}$ is fixed. Exact **Clopper–Pearson** or score-based **Wilson Score** intervals are valid.
   - **Precision (Conditional Proportion):** $\text{Precision} = \frac{TP}{TP + FP}$. The denominator $TP + FP = N_{\text{reported}}$ is a random variable dependent on the system's prediction threshold. When $N_{\text{reported}} > 0$, the interval can be conditioned on the observed denominator, but standard binomial assumptions are only an approximation.

2. **Non-Binomial Derived Metrics (Single-Proportion Intervals Invalid):**
   - **F1-Score:**
     $$F_1 = \frac{2 \cdot TP}{2 \cdot TP + FP + FN} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
     $F_1$ is a non-linear harmonic mean of two random proportions. Its numerator and denominator are dependent linear combinations of multinomial confusion matrix cells. It is **not** a binomial proportion $k/n$. Applying Clopper-Pearson or Wilson Score intervals to $F_1$ is **statistically invalid**.
   - **Comparative Differences ($\Delta\text{Precision}, \Delta\text{Recall}, \Delta F_1$):**
     Paired differences take values in $[-1.0, +1.0]$ and cannot be bounded by single-proportion intervals.

### 4.2 Approved Thesis Reporting Strategy
To maintain mathematical rigor under small-sample constraints:
- **Primary Reporting for Constituent Metrics:** Report point estimates accompanied by **95% Clopper–Pearson (exact)** or **Wilson Score (score-based)** confidence intervals for Recall, FPR, and Abstention Rate.
- **Reporting for F1-Score:**
  1. Report the empirical point estimate of $F_1$.
  2. Report $F_1$ alongside the constituent single-proportion intervals (Clopper–Pearson or Wilson) of its components (Precision and Recall).
  3. Where an interval on $F_1$ itself is required, compute a **Case-Resampled Non-Parametric Percentile Bootstrap Interval** ($B = 2{,}000$ resamples of canonical loci $(Y_i, \hat{Y}_i)$), accompanied by an explicit disclosure of bootstrap lattice granularity on $N \approx 36$ cases.
- **Reporting for Paired Differences:** Compute **Paired Percentile Bootstrap Intervals** on differences between systems ($\Delta = \text{Metric}_P - \text{Metric}_{\text{baseline}}$).

---

## 5. Task 3 — Threshold and Calibration Feasibility

### 5.1 Code Inspection of Current Uncertainty Contracts
A detailed inspection of the current repository code reveals the exact boundary of implemented capabilities:

1. **`UncertaintyAssessment` Contract (`aegiscore/orchestration.py:370`):**
   ```python
   @dataclass(frozen=True, slots=True)
   class UncertaintyAssessment:
       assessment_id: str
       request_id: str
       epistemic_uncertainty_detected: bool
       uncertainty_keywords: tuple[str, ...]
       evidence_sufficiency_score: float
       is_sufficient: bool
       abstention_recommended: bool
       justification: str
       confidence_is_calibrated: Literal[False] = False
   ```
   - `confidence_is_calibrated` is hardcoded to `Literal[False] = False`. Line 403 explicitly enforces:
     ```python
     if self.confidence_is_calibrated is not False:
         raise OrchestrationContractError("confidence_is_calibrated must be strictly False (uncalibrated)")
     ```
2. **`DeterministicUncertaintyAssessorFake` Implementation (`aegiscore/specialist_roles.py:653`):**
   - The field `evidence_sufficiency_score` takes only discrete values based on chunk count and keyword heuristics:
     - 0 chunks $\to 0.0$
     - $\ge 2$ chunks without epistemic keywords $\to 1.0$
     - $\ge 2$ chunks with epistemic keywords $\to 0.4$
   - `is_sufficient` is evaluated as `score >= 0.5`.
   - `abstention_recommended = not is_sufficient`.
3. **`OrchestrationStateMachine` Gating Logic (`aegiscore/orchestration.py:767`):**
   - The state machine evaluates a boolean check:
     ```python
     elif uncertainty.abstention_recommended:
         self.transition_to(OrchestrationState.ABSTAINED, reason=uncertainty.justification)
     ```
   - There is **no continuous threshold parameter $\theta_{\text{abstain}}$** in the state machine or orchestration engine.

### 5.2 Feasibility Findings
1. **Numerical Threshold Tuning is Unimplementable Today:**
   - Proposing to tune $\theta \in \{0.50, 0.70, 0.85\}$ in the executable protocol is misleading because the current contracts evaluate a boolean recommendation (`abstention_recommended: bool`), not a continuous parameter.
   - **Resolution:** The threshold grid $\theta \in \{0.50, 0.70, 0.85\}$ is formally marked as **future-only / conditional on a score-producing model**. For the currently executable state machine contracts, gating is purely boolean and discrete.
2. **Calibration Metrics (ECE / Brier Score) are Future-Only:**
   - Because no continuous probability output exists and `confidence_is_calibrated` is strictly `False`, ECE and Brier Score cannot be executed on current contracts. They remain future-only.
3. **Sample Size Recommendation Status:**
   - Any suggestion that calibration requires $N > 100$ cases is classified as an **empirical rule-of-thumb heuristic** cited from calibration literature (e.g., Niculescu-Mizil & Caruana, 2005; Guo et al., 2017), not a formal mathematical theorem.

---

## 6. Task 4 — Metric Feasibility Terminology & Revised Audit Matrix

To eliminate confusion between what contracts define and what benchmarks measure, evaluation metrics are classified across three rigorous operational categories:

1. **Category 1: Contract-Level Computable**  
   Data structures, typed schemas, and transition logic exist in `aegiscore/`. The metric can be evaluated on synthetic/deterministic inputs today.
2. **Category 2: Benchmark Measurable**  
   Requires live target environments, ground-truth label keys, case-level execution outputs, and the Ground-Truth Evaluator (MOD-11).
3. **Category 3: Not Currently Supported**  
   Required model outputs (e.g., continuous calibrated probabilities) or system features do not exist in the repository.

### Table 2: Revised Metric Feasibility Matrix

| Metric Name | Required Inputs | Unit of Analysis | Feasibility Category | Code Status & Operational Pre-requisites |
|---|---|---|---|---|
| **Abstention Rate ($AR$)** | Terminal `ABSTAINED` state counts, total cases. | Canonical Case Locus | **Category 1 (Contract Computable)** | Supported in `OrchestrationStateMachine` (`SCEN-MA-02`, `SCEN-MA-04`). Computable on synthetic inputs today; becomes Benchmark Measurable when harness collects live run decisions. |
| **Coverage ($\Phi$)** | Non-abstained reporting decisions, total cases. | Canonical Case Locus | **Category 1 (Contract Computable)** | $\Phi = 1 - AR$. Formally evaluated in state machine contract tests. |
| **Verified Finding Rate ($VFR$)** | Count of findings reaching `VERIFIED` vs `CANDIDATE`. | Finding Cluster | **Category 1 (Contract Computable)** | State machine tracks candidate-to-verified transition (`SCEN-MA-01`). |
| **HTTP Tool Invocations** | Guarded request permits emitted by boundary. | Scenario Run | **Category 1 (Contract Computable)** | `GuardedExecutionBoundary` tracks permit counts against budget. (Note: currently tested with fake transport; live HTTP execution has NOT occurred). |
| **Precision** | Verified findings reported, ground-truth label key. | Canonical Case Locus | **Category 2 (Benchmark Measurable)** | Requires live benchmark execution and Ground-Truth Evaluator (MOD-11). Undefined when $TP + FP = 0$. |
| **Recall (Sensitivity)** | Verified true positives, ground-truth positive cases. | Canonical Case Locus | **Category 2 (Benchmark Measurable)** | Requires live benchmark execution and Ground-Truth Evaluator (MOD-11). Abstentions on positive cases penalize Recall as $FN$. |
| **F1-Score** | Precision and Recall. | Canonical Case Locus | **Category 2 (Benchmark Measurable)** | Harmonic mean of Precision and Recall. Non-binomial ratio metric. |
| **False-Positive Rate ($FPR$)** | False positives, ground-truth negative controls. | Canonical Case Locus | **Category 2 (Benchmark Measurable)** | Requires pre-registered negative controls (e.g., hardened endpoints in Juice Shop / DVWA Impossible). |
| **Selective Risk ($R(\Phi)$)** | False positives among reported non-abstained cases. | Canonical Case Locus | **Category 2 (Benchmark Measurable)** | $R(\Phi) = 1 - \text{Precision}$. Measures error rate on covered subset. |
| **Severity Agreement ($\kappa_w$)** | Predicted severity vs ground-truth CVSS severity. | Verified Finding | **Category 2 (Benchmark Measurable)** | Schema enum exists (`FindingSeverity`). Requires Ground-Truth Evaluator to score quadratic weighted kappa. |
| **Wall-Clock Latency** | Execution start and end timestamps. | Scenario Run | **Category 2 (Benchmark Measurable)** | Requires live execution runner and real network timers. |
| **Token Consumption** | Prompt tokens, completion tokens. | Scenario Run | **Category 2 (Benchmark Measurable)** | Requires token metadata from live LLM provider responses. |
| **Ablation Comparisons ($A1, A2, B2, B3$)** | Metric deltas across experimental conditions. | Paired Comparison | **Category 2 (Benchmark Measurable)** | State machine contract supports empty bundle ($A1$) and bypass paths ($A2$), but comparative measurements require live execution. |
| **Brier Score** | Predicted probability $p_i \in [0, 1]$, binary outcome $y_i$. | Single Prediction | **Category 3 (Not Currently Supported)** | **Codebase Gap:** `UncertaintyAssessment` enforces `confidence_is_calibrated: Literal[False]`. Continuous probabilities do not exist. |
| **Expected Calibration Error ($ECE$)** | Binned probabilities and empirical accuracies. | Binned Predictions | **Category 3 (Not Currently Supported)** | **Codebase Gap & Statistical Gap:** Requires continuous probabilities (not present) and large sample size ($N \approx 14$ test cases causes severe binning noise). |

---

## 7. Task 5 — Repeated-Trial Guarantees

### 7.1 What Current Code Tests Actually Guarantee
In the current repository:
- `tests/test_specialist_roles.py` (SCEN-MA-16, line 267):
  ```python
  def test_identical_inputs_yield_identical_outputs() -> None:
      bundle = _bundle("chk-rep", "src-rep", "Identical input content for repeatability test.")
      fixture = FixturedSpecialistOutput(vulnerability_identified=True, ...)
      fake = DeterministicVulnerabilityAnalystFake(ROLE_XSS_ANALYST, fixture=fixture)
      finding1 = fake.analyse("req-repeat", bundle)
      finding2 = fake.analyse("req-repeat", bundle)
      assert finding1 == finding2
  ```
- `tests/test_generation.py` (line 103):
  ```python
  def test_deterministic_output_for_identical_inputs():
      ...
      res1 = generator.generate(evidence)
      res2 = generator.generate(evidence)
      assert res1 == res2
  ```
- `aegiscore/orchestration.py`: Identifiers are generated using deterministic SHA-256 hashes (`_stable_id(prefix, *seeds)`).

### 7.2 Inferred Determinism vs. Executable Verification
- **Verified by Executable Test:** For the specific unit test fixtures evaluated in the test suite, calling fake specialist methods with identical arguments produces structurally equal Python dataclass instances (`assert finding1 == finding2`).
- **Inferred from Implementation:** Because the fake classes (`DeterministicVulnerabilityAnalystFake`, `DeterministicEvidenceReviewerFake`, `DeterministicUncertaintyAssessorFake`) are pure Python functions containing no random number generators, system clock calls, global mutable state, or external I/O, their outputs are deterministically repeatable for any given input.
- **Empirical Variance Irrelevance:** Executing $K = 3$ repeated runs of these deterministic fakes produces byte-for-byte identical results and **zero variance information**.
- **LLM Stochasticity Boundary:** Repeated trials ($K = 3$) become methodologically meaningful only when real LLMs are evaluated, where cluster-level floating-point variations and network timeouts introduce stochasticity.
- **Anti-Pseudo-Replication Invariant:** Under no circumstances may repeated trials ($K = 3$) be treated as independent sample points. $K = 3$ trials across 36 loci yield $N = 36$ independent loci, not $108$.

---

## 8. Documented Corrections to `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`

The following targeted adjustments are justified and incorporated into `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`:

1. **Section 8.2 (Confidence Intervals):**
   - Corrected interval reporting strategy: Wilson Score intervals are specified for single binomial proportions (Recall, FPR, Abstention Rate).
   - F1-Score is explicitly distinguished as a non-binomial derived metric; reporting mandates empirical point estimates alongside constituent proportion intervals, with optional Percentile Bootstrap intervals.
   - Comparative differences ($\Delta\text{Precision}, \Delta\text{Recall}, \Delta F_1$) are specified as Paired Percentile Bootstrap intervals.
2. **Section 8.3 (Statistical Power & Equivalence):**
   - Removed unverified numerical power bounds.
   - Added explicit statement: failure to reject the null hypothesis ($p \ge 0.05$) under exploratory small-sample constraints does not prove equivalence.
3. **Section 13, Item 3 (Threshold Selection):**
   - Clarified that the discrete threshold grid ($\theta \in \{0.50, 0.70, 0.85\}$) is a **future design specification** conditional on implementing continuous confidence scores.
   - Stated that current state machine contracts enforce boolean abstention gating (`abstention_recommended: bool`).

---

## 9. Verification & Integrity Results

| Verification Check | Target / Command | Result |
|---|---|---|
| **Full Pytest Suite** | `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | **351 passed in 6.87s** (0 failed, 0 skipped) |
| **Git Whitespace & Formatting** | `git diff --check` | **Clean** (0 errors; LF/CRLF warnings only) |
| **Source Manifest Integrity** | `git diff -- docs/source-review-manifest.json` | **Clean** (0 changes; exact 0-byte diff) |
| **Working Tree State** | `git status --short --untracked-files=all` | All existing untracked/modified files preserved intact |
| **Database Audit** | `Get-ChildItem -Recurse -Include *.db,*.sqlite,*.sqlite3` | **Zero databases found** (0 bytes created) |

---

## 10. Final Decision & Recommendation

### Decision: **CONDITIONAL GO FOR OFFLINE HARNESS CONFIGURATION ONLY**

- **Authorized Work (Phase 8E.2B):**
  - Authoring offline Docker Compose configuration files (`docker-compose.yml`) for OWASP Juice Shop (v15.0.0) and DVWA (v1.10).
  - Configuring isolated, internal Docker bridge networks (`172.28.0.0/16`) with `internal: true` (strictly zero outbound internet egress).
  - Authoring deterministic target database reset scripts and offline health-check scripts.
- **Strictly Prohibited Actions (Holding on Supervisor Approval):**
  - **No container launches or image pulls:** `docker compose up` or `docker pull` must NOT be executed.
  - **No benchmark deployments or scanner runs:** Zero HTTP requests or vulnerability payloads.
  - **No LLM provider integration:** Zero API calls to external or cloud model providers.
