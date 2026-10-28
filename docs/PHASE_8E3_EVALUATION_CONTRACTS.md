# AEGISCORE AI — Phase 8E.3
# Evaluation Contracts & Offline Scoring Framework

**Document ID:** DOC-PHASE-8E3-EVAL-CONTRACTS  
**Status:** COMPLETE / IMPLEMENTED CONTRACTS & TESTS  
**Date:** 2026-10-27  
**Project:** AEGISCORE AI  
**Thesis Title:** “An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment”  
**Context:** Canonical evaluation schemas, versioned JSONL validation, deterministic offline scoring pipeline, and runner interface specifications.

---

## 1. Executive Summary

Phase 8E.3 delivers the offline evaluation framework and typed data contracts for the AEGISCORE AI thesis evaluation.

> [!IMPORTANT]
> **Strict Offline Boundary:** All implementations in this phase are strictly offline and dependency-free:
> - **Zero benchmark deployments:** No Docker containers were launched; no benchmark applications were executed.
> - **Zero network requests:** No HTTP calls or vulnerability payloads were transmitted.
> - **Zero scanner execution:** OWASP ZAP and external scanners were not executed.
> - **Zero LLM provider calls:** No API calls were made to Gemini, OpenAI, or local model servers.
> - **Synthetic Fixtures Only:** All 26 unit tests operate on clearly labeled, deterministic synthetic fixtures.

The framework provides typed record definitions, versioned JSONL parsers with duplicate-detection, an offline confusion-matrix scoring pipeline, and abstract runner interfaces.

---

## 2. Canonical Evaluation Contracts & Record Schemas

All contracts are defined in [`aegiscore/evaluation.py`](file:///s:/AegisCore/aegiscore/evaluation.py) as frozen, slotted Python dataclasses with runtime schema versioning (`schema_version = "1.0.0"`).

### 2.1 Canonical Case Locus (Unit of Analysis)
The foundational unit of analysis for all evaluation metrics is the **Canonical Locus**:

$$\text{Canonical Locus} = (\text{Target URI}, \text{Parameter}, \text{CWE ID})$$

```python
@dataclass(frozen=True, slots=True)
class CanonicalLocus:
    target_uri: str    # e.g., "/rest/products/search"
    parameter: str     # e.g., "q"
    cwe_id: str        # e.g., "CWE-79" (must match ^CWE-[0-9]+$)
```

- **Invariant:** Repeated executions ($K=3$) against the same locus capture run-to-run variance, but **never** inflate sample size $N$. Evaluating 36 loci across 3 runs yields $N = 36$ independent units, not $108$.

### 2.2 Case Manifest Records
[`EvaluationCaseManifestRecord`](file:///s:/AegisCore/aegiscore/evaluation.py#L125) defines the pre-registered benchmark test suite:
- `schema_version`: String (`"1.0.0"`).
- `case_id`: Stable identifier (e.g., `"CASE-JS-XSS-01"`).
- `locus`: `CanonicalLocus` instance.
- `benchmark_target`: Pinned benchmark name (`"juice-shop"`, `"dvwa"`).
- `benchmark_version`: Pinned version tag (`"v15.0.0"`, `"1.10"`).
- `vulnerability_class`: Standardized CWE identifier.
- `expected_label`: `GroundTruthStatus` (`VULNERABLE` or `NON_VULNERABLE`).
- `ground_truth_provenance`: Source document / challenge writeup reference.
- `review_status`: `AdjudicationState` (`UNVERIFIED`, `REVIEWED`, `ADJUDICATED`, `DISPUTED`).
- `inclusion_status`: `InclusionStatus` (`INCLUDED`, `EXCLUDED`, `CANDIDATE`).

### 2.3 Assessment Finding & Result Records
- [`AssessmentFindingRecord`](file:///s:/AegisCore/aegiscore/evaluation.py#L170): Represents an individual candidate finding emitted by a specialist role.
- [`AssessmentResultRecord`](file:///s:/AegisCore/aegiscore/evaluation.py#L210): Represents the terminal evaluation outcome for a test case:
  - `decision`: `FindingDecision` (`VERIFIED`, `REJECTED`, `ABSTAINED`).
  - `primary_severity`: `FindingSeverity | None` (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `evidence_citations`: Tuple of citation references used in the decision.
  - `error_status`: Trace text if assessment encountered an internal exception.
  - `is_incomplete`: Boolean flag for aborted runs.

### 2.4 Evaluation Run Records
[`EvaluationRunRecord`](file:///s:/AegisCore/aegiscore/evaluation.py#L255) captures a single execution episode:
- `run_id`: Unique execution identifier (e.g., `"run-proposed-CASE-01-rep0"`).
- `runner_id`: Identifier of condition (`proposed-multi-agent`, `baseline-single-agent`, etc.).
- `case_id`: Matching manifest case.
- `repeat_index`: Non-negative integer trial index ($0, 1, \dots, K-1$).
- `result`: Embedded `AssessmentResultRecord`.
- `reproducibility_metadata`: Immutable mapping of prompt hashes, model identifiers, temperatures, and seeds.

### 2.5 Ground-Truth Records
[`GroundTruthRecord`](file:///s:/AegisCore/aegiscore/evaluation.py#L305) captures pre-registered ground truth for scoring:
- `case_id`: Case reference.
- `expected_status`: `GroundTruthStatus` (`VULNERABLE` or `NON_VULNERABLE`).
- `expected_severity`: Adjudicated CVSS severity tier.
- `evidence_reference`: Concrete verification proof (e.g., exploit payload trace, source code sanitization locus).
- `adjudication_state`: Adjudication status.

---

## 3. Strict JSONL Validation & Invariant Enforcement

The module implements three strict JSONL stream validators:
- [`validate_manifest_jsonl`](file:///s:/AegisCore/aegiscore/evaluation.py#L390)
- [`validate_ground_truth_jsonl`](file:///s:/AegisCore/aegiscore/evaluation.py#L420)
- [`validate_runs_jsonl`](file:///s:/AegisCore/aegiscore/evaluation.py#L445)

### Enforcement Rules
1. **Duplicate Detection:**
   - Manifest validator rejects duplicate `case_id`s or duplicate canonical loci (`(URI, Param, CWE)`).
   - Run validator rejects duplicate `run_id`s and duplicate `(runner_id, case_id, repeat_index)` tuples.
2. **Foreign Key Integrity:**
   - Ground-truth and run records referencing a `case_id` absent from the approved manifest raise `EvaluationValidationError`.
3. **No Silent Repair:**
   - Malformed JSON, extra whitespace, or unmapped enum values fail immediately without guessing or inferring missing attributes.

---

## 4. Deterministic Offline Scoring Pipeline

The scoring pipeline operates in two stages: per-case adjudication followed by metric calculation.

### 4.1 Case Adjudication Logic ([`evaluate_case_outcome`](file:///s:/AegisCore/aegiscore/evaluation.py#L490))

| Ground-Truth Status | System Decision | Case Classification | Covered in Selective Prediction ($\Phi$)? | Role in Standard Detection |
|---|---|---|:---:|---|
| **Vulnerable** | `VERIFIED` | `TP` | Yes | True Positive |
| **Vulnerable** | `REJECTED` | `FN` | Yes | False Negative |
| **Vulnerable** | `ABSTAINED` | `ABSTAINED_POSITIVE` | **No** | **False Negative (Penalizes Recall)** |
| **Non-Vulnerable** | `VERIFIED` | `FP` | Yes | False Positive |
| **Non-Vulnerable** | `REJECTED` | `TN` | Yes | True Negative |
| **Non-Vulnerable** | `ABSTAINED` | `ABSTAINED_NEGATIVE` | **No** | **Abstention (NEVER a True Negative)** |

### Core Architectural Invariants
1. **Abstentions on Positive Cases Penalize Recall:** If a vulnerability exists and the system abstains from reporting it, the vulnerability is missed in deployment. It is counted in $FN_\text{total} = FN_\text{rejected} + N_\text{abstained\_positive}$.
2. **Abstentions on Negative Cases are NEVER True Negatives:** Withholding judgment on a non-vulnerable target does not demonstrate that the system recognized it as safe. It is counted as an abstention, leaving $TN_\text{count}$ to reflect only explicit rejections.
3. **Selective Risk Denominator:** Selective risk is evaluated exclusively on the covered non-abstained predictions:
   $$R(\Phi) = \frac{FP_\text{covered}}{TP_\text{covered} + FP_\text{covered}} = 1 - \text{Precision}$$

### 4.2 Handling Zero Denominators & Undefined Metrics
Standard scoring pipelines often fabricate `0.0` or `1.0` when denominators are zero. AEGISCORE AI explicitly handles zero denominators by reporting `MetricStatus.UNDEFINED` with `value = None`:
- When system reports 0 findings ($TP + FP = 0$): **Precision and F1 are UNDEFINED**, not $0.0$.
- When benchmark subset has 0 positive cases ($TP + FN = 0$): **Recall is UNDEFINED**.
- When benchmark subset has 0 negative controls ($FP + TN = 0$): **FPR is UNDEFINED**.

### 4.3 Unsupported Calibration Metrics
- **Brier Score** and **Expected Calibration Error (ECE)** are explicitly marked `MetricStatus.NOT_SUPPORTED`.
- *Rationale:* AEGISCORE AI outputs categorical states and discrete heuristics; computing continuous probability metrics from uncalibrated discrete values is scientifically invalid.

### 4.4 Repeated-Trial Aggregation ([`aggregate_repeated_runs`](file:///s:/AegisCore/aegiscore/evaluation.py#L540))
For trials $K = 3$:
- Decisions across trials are aggregated using **Majority Consensus Voting** ($\ge 2/3$ agreement).
- If decisions are split without majority (e.g., 1 verified, 1 rejected, 1 abstained), the system fails closed to `ABSTAINED`.
- The aggregated result collapses back to the canonical locus, preserving the Unit of Analysis ($N$).

---

## 5. Runner Interfaces (Specification Only)

[`EvaluationRunnerInterface`](file:///s:/AegisCore/aegiscore/evaluation.py#L710) defines the provider-neutral execution contract:

```python
class EvaluationRunnerInterface:
    @property
    def runner_id(self) -> str:
        raise NotImplementedError

    def run_case(self, case: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
        raise NotImplementedError
```

### Pre-Registered Experimental Conditions
1. `proposed-multi-agent`: Proposed uncertainty-aware multi-agent architecture ($P$).
2. `baseline-single-agent`: Single-agent prompt-driven baseline ($B3$).
3. `baseline-ma-no-abstention`: Multi-agent system without uncertainty gating ($B2$).
4. `baseline-dast-zap`: OWASP ZAP automated scanner baseline ($B1$).
5. `ablation-no-rag`: Proposed workflow with empty retrieval bundle ($A1$).
6. `ablation-no-reviewer`: Proposed workflow bypassing adversarial review ($A2$).

### Offline Fixture Adapter ([`FixtureBackedRunnerAdapter`](file:///s:/AegisCore/aegiscore/evaluation.py#L720))
- Connects pre-recorded synthetic fixtures to the evaluation runner interface.
- Executes completely offline; strictly prevents live network or model calls.

---

## 6. Synthetic-Fixture Limitations

All unit tests in [`tests/test_evaluation_contracts.py`](file:///s:/AegisCore/tests/test_evaluation_contracts.py) use synthetic data.
- **Limitation:** Passing tests prove the correctness of JSONL deserialization, duplicate checks, confusion-matrix math, and abstention invariants.
- **Disclaimer:** Synthetic fixture scores do **not** represent empirical benchmark performance or vulnerability detection capabilities. Real benchmark performance can only be evaluated once live runners are authorized and executed.

---

## 7. Supervisor Approval Gates Remaining

Before benchmark execution or model connection can occur:
1. **Gate 1:** Approval of exploratory proof-of-concept framing ($N \approx 36$).
2. **Gate 2:** Formal selection of LLM provider (Cloud Gemini 1.5 Pro vs. Local Llama-3.1-70B).
3. **Gate 3:** Approval of Within-Benchmark Stratified Partitioning scheme.
4. **Gate 4:** Authorization to build live runner implementations and execute against local containers.

---

## 8. Verification Results

All checks passed cleanly:
- Full test suite: **396 passed in 6.97s** (0 failed, 0 skipped).
- `git diff --check`: Clean (0 errors).
- Source manifest integrity: 0 bytes modified.
- Database audit: Zero database files created.

**Recommendation:** CONDITIONAL GO for offline baseline runner wrapper design (Phase 8E.4). Live benchmark execution, scanning, and model API integration remain **STRICTLY ON HOLD**.
