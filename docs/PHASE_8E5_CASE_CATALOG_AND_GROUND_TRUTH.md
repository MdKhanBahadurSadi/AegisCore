# Phase 8E.5 — Canonical Case Catalog & Ground-Truth Preparation Report

## 1. Executive Summary & Phase Objective

**Project:** AEGISCORE AI  
**Thesis:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Phase:** 8E.5 — Canonical Case Catalog & Ground-Truth Preparation  
**Status:** Completed (Offline Metadata, Contracts, Validators, Templates, and Test Suite)  

### Objective
Prepare a traceable, reviewable evaluation case catalog and ground-truth adjudication package for the proposed 36-case exploratory benchmark:
- **24 OWASP Juice Shop proposed cases**
- **12 DVWA proposed cases**

### Critical Thesis Constraint
The 24 + 12 = 36 distribution represents **proposed candidate targets**, not an established empirical finding that 36 verified, independent, validated cases exist today. In strict accordance with scientific integrity and the pre-registration requirements established in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md`, **missing or unverified case metadata has NOT been fabricated**. 

Only the **16 pre-registered scenarios** from Phase 8E.1 Protocol § 12 (Table 6) are evidence-backed. The remaining 20 proposed slots are explicitly cataloged with `locus_status: "unresolved"` and `expected_label_proposal: "unresolved"`, awaiting formal supervisor selection and locus establishment.

Furthermore, **zero cases are marked `ADJUDICATED`** in Phase 8E.5. This phase constructs the audit contracts, fail-closed JSONL validators, draft catalog, review templates, and partition governance to prepare the adjudication package for the thesis supervisor.

---

## 2. Case Catalog Summary Table

The catalog comprises 36 proposed case slots across OWASP Juice Shop v15.0.0 and DVWA v2024.1.

### 2.1 Summary by Benchmark Target & Locus Status

| Benchmark Target | Established Loci | Partial Loci (Controls/Edges) | Unresolved Slots | Total Proposed Slots |
|---|---|---|---|---|
| **OWASP Juice Shop** (v15.0.0) | 8 | 3 | 13 | **24** |
| **DVWA** (v2024.1) | 5 | 0 | 7 | **12** |
| **Total** | **13** | **3** | **20** | **36** |

### 2.2 Pre-Registered Evaluation Scenarios (16 Evidence-Backed Cases)

All 16 scenarios originate directly from `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` Table 6:

| Case ID | Benchmark | Locus Status | Target URI | Parameter | CWE ID | Class | Proposed Label | Protocol Ref | Overlap / Independence |
|---|---|---|---|---|---|---|---|---|---|
| `JS-XSS-R-01` | juice-shop | ESTABLISHED | `/rest/products/search` | `q` | CWE-79 | XSS | vulnerable | SCEN-EVAL-01 | Potentially overlapping (`/rest/products/search`) |
| `JS-XSS-S-01` | juice-shop | ESTABLISHED | `/api/Feedbacks` | `comment` | CWE-79 | XSS | vulnerable | SCEN-EVAL-02 | Independent |
| `JS-XSS-R-02` | juice-shop | PARTIAL | `/rest/products/search` | `q` | CWE-79 | XSS | non_vulnerable | SCEN-EVAL-03 | Negative control; shares endpoint with JS-XSS-R-01 |
| `JS-SQLI-01` | juice-shop | ESTABLISHED | `/rest/user/login` | `email` | CWE-89 | SQLi | vulnerable | SCEN-EVAL-06 | Independent (auth bypass) |
| `JS-SQLI-02` | juice-shop | ESTABLISHED | `/rest/products/search` | `q` | CWE-89 | SQLi | vulnerable | SCEN-EVAL-07 | Distinct CWE locus on search endpoint |
| `JS-SQLI-03` | juice-shop | PARTIAL | `/rest/user/login` | `email` | CWE-89 | SQLi | non_vulnerable | SCEN-EVAL-08 | Negative control; stock login unparameterized |
| `JS-BAC-IDOR-01` | juice-shop | ESTABLISHED | `/rest/basket/{BasketId}` | `BasketId` | CWE-639 | IDOR | vulnerable | SCEN-EVAL-11 | Independent (IDOR) |
| `JS-BAC-01` | juice-shop | ESTABLISHED | `/rest/basket/{BasketId}/order` | `quantity` | CWE-862 | BAC | vulnerable | SCEN-EVAL-12 | Independent (missing auth) |
| `JS-BAC-02` | juice-shop | ESTABLISHED | `/rest/admin/application-version` | `Authorization` | CWE-285 | BAC | non_vulnerable | SCEN-EVAL-13 | Independent (verified 403 control) |
| `JS-PT-01` | juice-shop | ESTABLISHED | `/ftp/legal.md%2500.pdf` | `path` | CWE-22 | PATH_TRAVERSAL | vulnerable | SCEN-EVAL-14 | Independent (null byte traversal) |
| `JS-SQLI-04` | juice-shop | PARTIAL | `/rest/products/search` | `q` | CWE-89 | SQLi | non_vulnerable | SCEN-EVAL-15 | Ambiguous edge case; uncertainty abstention target |
| `DVWA-XSS-R-01` | dvwa | ESTABLISHED | `/vulnerabilities/xss_r/` | `name (security=low)` | CWE-79 | XSS | vulnerable | SCEN-EVAL-04 | Independent (low security) |
| `DVWA-XSS-R-02` | dvwa | ESTABLISHED | `/vulnerabilities/xss_r/` | `name (security=impossible)` | CWE-79 | XSS | non_vulnerable | SCEN-EVAL-05 | Independent (impossible security control) |
| `DVWA-SQLI-01` | dvwa | ESTABLISHED | `/vulnerabilities/sqli/` | `id (security=low)` | CWE-89 | SQLi | vulnerable | SCEN-EVAL-09 | Independent (low security) |
| `DVWA-SQLI-02` | dvwa | ESTABLISHED | `/vulnerabilities/sqli/` | `id (security=impossible)` | CWE-89 | SQLi | non_vulnerable | SCEN-EVAL-10 | Independent (impossible security control) |
| `DVWA-XSS-R-03` | dvwa | ESTABLISHED | `/vulnerabilities/xss_r/` | `name (security=medium)` | CWE-79 | XSS | vulnerable | SCEN-EVAL-16 | Independent (medium security bypass) |

### 2.3 Unresolved Candidate Slots (20 Slots Awaiting Adjudication)

- **OWASP Juice Shop Slots (13 slots):** `JS-PROP-12` through `JS-PROP-24`
  - `catalog_status`: `proposed`
  - `locus_status`: `unresolved`
  - `target_uri`: `null`, `parameter`: `null`, `cwe_id`: `null`, `vulnerability_class`: `null`
  - `expected_label_proposal`: `unresolved`
  - `evidence_reference`: `"UNRESOLVED_PENDING_SUPERVISOR_REVIEW"`
  - `independence_status`: `unresolved`
- **DVWA Slots (7 slots):** `DVWA-PROP-06` through `DVWA-PROP-12`
  - `catalog_status`: `proposed`
  - `locus_status`: `unresolved`
  - `target_uri`: `null`, `parameter`: `null`, `cwe_id`: `null`, `vulnerability_class`: `null`
  - `expected_label_proposal`: `unresolved`
  - `evidence_reference`: `"UNRESOLVED_PENDING_SUPERVISOR_REVIEW"`
  - `independence_status`: `unresolved`

---

## 3. Catalog Data Contracts & Schema Reference

Implemented in `aegiscore/catalog.py`:

### 3.1 `CatalogRecord`
```python
@dataclass(frozen=True, slots=True)
class CatalogRecord:
    case_id: str                          # Matches ^[A-Z0-9][A-Z0-9\-]{2,39}$
    benchmark_name: str                   # "juice-shop" | "dvwa"
    benchmark_version: str                # e.g. "15.0.0", "2024.1"
    catalog_status: CatalogRecordStatus   # PROPOSED | CANDIDATE | CONFIRMED | EXCLUDED
    locus_status: LocusEstablishmentStatus # ESTABLISHED | PARTIAL | UNRESOLVED | NOT_APPLICABLE
    target_uri: str | None                # Required if ESTABLISHED
    parameter: str | None                 # Required if ESTABLISHED
    cwe_id: str | None                    # Required if ESTABLISHED; must match permitted CWE set
    vulnerability_class: str | None       # "XSS" | "SQLi" | "BAC" | "IDOR" | "PATH_TRAVERSAL"
    expected_label_proposal: str | None   # "vulnerable" | "non_vulnerable" | "unresolved" | None
    scenario_description: str             # Non-empty description
    evidence_reference: str               # Source code line or file reference
    evidence_source: str                  # Originating repository/document
    review_notes: str                     # Context for reviewer
    independence_status: IndependenceStatus # INDEPENDENT | POTENTIALLY_OVERLAPPING | CONFIRMED_DUPLICATE | UNRESOLVED
```

### 3.2 Permitted Values
- **Permitted Benchmarks:** `juice-shop`, `dvwa`
- **Permitted CWEs:**
  - `CWE-22`: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
  - `CWE-79`: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')
  - `CWE-80`: Improper Neutralization of Script-Related HTML Tags in a Web Page (Basic XSS)
  - `CWE-89`: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')
  - `CWE-284`: Improper Access Control
  - `CWE-285`: Improper Authorization
  - `CWE-639`: Authorization Bypass Through User-Controlled Key (IDOR)
  - `CWE-862`: Missing Authorization
  - `CWE-863`: Incorrect Authorization

---

## 4. Ground-Truth Review Workflow & Governance

### 4.1 State Machine
```
UNVERIFIED ───────► DISPUTED
    │                    ▲
    │                    │
    ▼                    ▼
[Reviewer Sign-off] ──► ADJUDICATED
```

### 4.2 Invariant Enforcement in `GroundTruthReviewRecord`
1. **Adjudication Gate:** A record may **never** have `adjudication_status = "adjudicated"` unless:
   - `reviewer_identity` is non-empty and **not** `"UNASSIGNED"`
   - `adjudication_date` is a valid date string
2. **Dataset Eligibility Gate:** `eligible_for_dataset` is strictly `False` for all `UNVERIFIED` and `DISPUTED` records.
3. **Current Catalog State:**
   - Adjudicated records: **0**
   - Unverified records: **36**
   - Disputed records: **0**
   - Eligible for dataset: **0**

---

## 5. Independence and Leakage Audit

### 5.1 Canonical Unit of Analysis ($N$)
The canonical locus is defined as `(benchmark_name, target_uri, parameter, cwe_id)`.
In statistical testing (McNemar's paired test, odds ratios), each locus represents an independent observation.

### 5.2 Identified Overlaps & Leakage Risks
1. **Juice Shop Search Route (`/rest/products/search`):**
   - `JS-XSS-R-01` (Reflected XSS, `q`, CWE-79)
   - `JS-SQLI-02` (SQLi, `q`, CWE-89)
   - `JS-XSS-R-02` (Negative Control, `q`, CWE-79)
   - `JS-SQLI-04` (Ambiguous SQLi, `q`, CWE-89)
   - *Risk:* While `CWE-79` and `CWE-89` constitute distinct canonical loci, they execute through the same Node.js route handler (`routes/search.ts`). Cache or persistent state mutations could leak between test runs.
   - *Resolution:* Requires container state reset (`testbed/juice-shop-reset.sh`) between distinct locus evaluations.
2. **Negative Controls on Monolithic Targets:**
   - In stock Juice Shop, `/rest/user/login` is vulnerable to SQL injection. A true negative control (`JS-SQLI-03`) cannot be evaluated against the unpatched server because the endpoint is inherently vulnerable.
   - *Resolution:* Marked as `locus_status: "partial"`. Supervisor must choose between deploying a patched variant branch or evaluating negative controls via synthetic fixture mocking in the harness.
3. **Cross-Application Independence:**
   - Juice Shop (Node.js/Express) and DVWA (PHP/Apache) are isolated containers on separate loopback port bindings. Cross-application leakage is strictly impossible under the network boundary rules.

---

## 6. Partition Governance Rules

### 6.1 Proposed Partition Allocation
- **Juice Shop (24 cases):**
  - **Validation Partition:** 40% (~10 cases) for prompt tuning, few-shot prompt selection, and specialist threshold calibration.
  - **Test Partition:** 60% (~14 cases) held out exclusively for final reported benchmark evaluation.
- **DVWA (12 cases):**
  - Secondary / out-of-distribution transfer partition. Evaluates cross-framework generalization from Express/Node.js to PHP/Apache without in-distribution prompt tuning.

### 6.2 Partition Invariants in `PartitionAssignmentRecord`
1. **Approval Gate:** Any record with `partition != "unassigned"` requires an explicit `approved_by` supervisor identity.
2. **Disjointness Rule:** No Juice Shop case ID may appear in both `validation` and `test` partitions.
3. **Current State:**
   - Assigned partitions: **0**
   - Unassigned partitions: **36**
   - Approved by: **null** (awaiting supervisor sign-off)

---

## 7. Extended Configuration Fingerprint Analysis

### 7.1 Comparison: Phase 8E.4 vs Phase 8E.5
In Phase 8E.4, `configuration_fingerprint` captured:
- `runner_condition`
- `repeat_count`
- `case_ids`
- `fixture_dataset_id`
- `fixture_dataset_version`
- `application_version`

### 7.2 Deficiencies Addressed in Phase 8E.5
Phase 8E.4 omitted critical configuration dimensions that determine evaluation reproducibility. The new `FingerprintInputs` dataclass and `compute_extended_fingerprint()` function in `aegiscore/catalog.py` capture:
1. `adapter_version`: Version of runner wrapper adapter
2. `catalog_version`: Version of the evaluation case catalog
3. `scoring_protocol_version`: Version of the scoring computation rules
4. `aggregation_policy`: Policy for repeated-run vote aggregation (e.g. `majority_vote_k3`)
5. `model_identifier` *(optional)*: LLM model ID when a live provider is attached
6. `prompt_version` *(optional)*: System prompt hash/version when prompts are active
7. **Order-invariant Case IDs:** `sorted(case_ids)` ensures permutations produce identical SHA-256 hashes.
8. **Deliberate Exclusions:** Timestamps, host hardware identifiers, and OS-specific paths are excluded to guarantee deterministic content-addressable execution hashes.

---

## 8. Known Limitations & Integrity Audit

1. **Empirical Evidence Gap:** Only 16 cases have source-level evidence from Phase 8E.1 Table 6. The thesis benchmark target of 36 cases has 20 unpopulated slots.
2. **Zero Adjudicated Ground Truth:** No supervisor review has occurred yet. All labels are strictly proposals.
3. **Unassigned Partitioning:** No cases are assigned to train/validation/test sets because ground truth is unverified.
4. **Offline Mocking Requirement:** Negative control scenarios on vulnerable routes require supervisor guidance on whether to implement patched code branches in the testbed or rely on fixture-backed runner responses.

---

## 9. Supervisor Decisions Required Prior to Phase 8E.6

1. **Case Selection for 20 Unresolved Slots:**
   - Select 13 additional Juice Shop loci (e.g., JWT manipulation, NoSQL injection, file upload, SSRF)
   - Select 7 additional DVWA loci (e.g., Command Injection, File Inclusion, CSRF, Brute Force)
2. **Adjudication Review:**
   - Review and sign off on `docs/ground_truth_review_template.jsonl` for the 16 pre-registered cases
3. **Partition Approval:**
   - Formally authorize the 40% validation / 60% test split on Juice Shop cases
4. **Negative Control Strategy:**
   - Decide whether negative control endpoints will be served by container source code patches or synthetic offline mocks

---

## 10. GO / HOLD Recommendation

- **GO** for Phase 8E.5 deliverables:
  - `aegiscore/catalog.py`: contracts, validators, fingerprinting
  - `tests/test_catalog.py`: 34 unit tests, all passing (451 total in suite)
  - `docs/case_catalog_draft.jsonl`: 36 draft records
  - `docs/ground_truth_review_template.jsonl`: 36 review templates
  - `docs/partition_assignment_template.jsonl`: 36 unassigned partition records
  - `docs/independence_audit_template.jsonl`: 4 overlap records
  - `docs/PHASE_8E5_CASE_CATALOG_AND_GROUND_TRUTH.md`: this comprehensive report
- **HOLD** on live benchmark deployment, container execution, or LLM evaluation runs until the thesis supervisor formally adjudicates the catalog and approves partition assignments.
