# Phase 8E.6 — Case Catalog Provenance Audit & Supervisor Review Package

## 1. Executive Summary

**Project:** AEGISCORE AI  
**Thesis:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Phase:** 8E.6 — Case Catalog Provenance Audit & Supervisor Review Package  
**Status:** Completed (Strictly Offline Audit, Metadata Verification, and Supervisor Review Package)  

### 1.1 Objective & Context
Phase 8E.5 created a 36-slot evaluation case catalog package (`docs/case_catalog_draft.jsonl`, `docs/ground_truth_review_template.jsonl`, `docs/partition_assignment_template.jsonl`, and `docs/independence_audit_template.jsonl`). 

The objective of Phase 8E.6 is to perform a rigorous provenance audit of every proposed evaluation case. Specifically, this audit examines whether each case labeled `ESTABLISHED` or `PARTIAL` is genuinely supported by verifiable, locally traceable evidence, or merely reflects pre-registered scenario metadata from the evaluation protocol (`docs/PHASE_8E1_EVALUATION_PROTOCOL.md` § 12 Table 6).

### 1.2 Core Audit Findings

1. **Zero Empirically Verified Cases in Repository:**  
   Neither OWASP Juice Shop v15.0.0 nor DVWA v2024.1 source repositories or runtime containers exist within the local `s:\AegisCore` repository. All cited evidence strings (such as `"routes/search.ts line 28"`) represent **documented benchmark metadata from external upstream repositories**, not locally verified source files.
2. **Conflation of Protocol Registration with Ground-Truth Verification:**  
   Phase 8E.5 labeled 13 cases as `locus_status: "established"`. This audit clarifies that `ESTABLISHED` in Phase 8E.5 signified only that the triple `(target_uri, parameter, cwe_id)` was **syntactically complete** in the protocol scenario definition. It did **not** indicate that the vulnerability had been empirically reproduced, commit-pinned, or adjudicated.
3. **Severe Validity Flaws in Stock Negative Controls:**  
   Two of the three `PARTIAL` negative-control scenarios (`JS-XSS-R-02` and `JS-SQLI-03`) cannot be evaluated against an unmodified stock OWASP Juice Shop container:
   - In stock Juice Shop, `/rest/products/search?q=` reflects raw payloads without server-side output encoding; the assumed DOMPurify sanitization is a client-side Angular detail invisible to API-level scanners.
   - In stock Juice Shop, `/rest/user/login` uses unparameterized raw SQL concatenation; sending `' OR 1=1 --` succeeds. Treating this as a negative control against a stock target would penalize any scanner that correctly discovers the vulnerability as a False Positive.
4. **Current Benchmark Readiness Status:**  
   The proposed 36-case exploratory benchmark is **NOT evaluation-ready**. It remains a structured candidate package awaiting supervisor case selection (20 slots), negative control resolution (3 cases), and formal ground-truth adjudication (all 36 cases).

### 1.3 Audit Summary Table

| Category | Proposed Total | Pre-Registered in Protocol | Candidate Pool Slots | Syntactically Complete Loci | Genuinely Verified in Repo | Adjudicated Ground Truth | Approved Partitions |
|---|---|---|---|---|---|---|---|
| **Juice Shop** | 24 | 11 | 13 | 8 established + 3 partial | 0 | 0 | 0 |
| **DVWA** | 12 | 5 | 7 | 5 established + 0 partial | 0 | 0 | 0 |
| **Total** | **36** | **16** | **20** | **13 established + 3 partial** | **0** | **0** | **0** |

---

## 2. Case-by-Case Provenance and Status Table

The following table documents the audited provenance, completeness, evidence basis, and recommended status for every one of the 36 proposed case slots.

### Legend
- **Reg. Status (Scenario Registration):** `PRE_REG` = Protocol Table 6 Pre-Registered; `POOL` = Candidate Pool Slot.
- **Locus Status:** `EST` = Established Coordinates; `PART` = Partial / Synthetic Coordinates; `UNRES` = Unresolved Coordinates.
- **Verif. Status (Locus Verification):** `SYN` = Syntactically Specified; `PART` = Partially Specified (Synthetic Control); `EMP` = Empirically Verified; `UNRES` = Unresolved.

| Case ID | Benchmark | Reg. Status | Locus Status | Verif. Status | Target URI | Parameter | CWE ID | Class | Proposed Label | Provenance Basis | Actual Repo Evidence | Leakage / Overlap Risk | Recommended Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `JS-XSS-R-01` | juice-shop | PRE_REG | EST | SYN | `/rest/products/search` | `q` | CWE-79 | XSS | vulnerable | Protocol Table 6 (SCEN-EVAL-01); upstream Juice Shop docs | None in repo | Overlaps `/rest/products/search` with SQLi and control cases | Retain as candidate; require commit-pinned hash & live trace |
| `JS-XSS-S-01` | juice-shop | PRE_REG | EST | SYN | `/api/Feedbacks` | `comment` | CWE-79 | XSS | vulnerable | Protocol Table 6 (SCEN-EVAL-02); upstream feedback schema | None in repo | Independent endpoint | Retain as candidate; verify persistence across test resets |
| `JS-XSS-R-02` | juice-shop | PRE_REG | PART | PART | `/rest/products/search` | `q` | CWE-79 | XSS | non_vulnerable | Protocol Table 6 (SCEN-EVAL-03); hypothetical client DOMPurify | None in repo | Invalid server negative control on stock target; overlaps JS-XSS-R-01 | **HOLD / REVISE:** Isolate to dedicated mock route or patched build |
| `JS-SQLI-01` | juice-shop | PRE_REG | EST | SYN | `/rest/user/login` | `email` | CWE-89 | SQLi | vulnerable | Protocol Table 6 (SCEN-EVAL-06); Sequelize raw query concat | None in repo | Overlaps login route with JS-SQLI-03 control | Retain as candidate; verify token issuance on bypass |
| `JS-SQLI-02` | juice-shop | PRE_REG | EST | SYN | `/rest/products/search` | `q` | CWE-89 | SQLi | vulnerable | Protocol Table 6 (SCEN-EVAL-07); SQLite UNION SELECT leak | None in repo | Overlaps search route with XSS cases | Retain as candidate; verify SQLite column count stability |
| `JS-SQLI-03` | juice-shop | PRE_REG | PART | PART | `/rest/user/login` | `email` | CWE-89 | SQLi | non_vulnerable | Protocol Table 6 (SCEN-EVAL-08); hypothetical parameterized login | None in repo | Invalid control on stock target; stock login is vulnerable | **HOLD / REVISE:** Must deploy patched handler or harness mock |
| `JS-BAC-IDOR-01` | juice-shop | PRE_REG | EST | SYN | `/rest/basket/{BasketId}` | `BasketId` | CWE-639 | IDOR | vulnerable | Protocol Table 6 (SCEN-EVAL-11); unauthenticated basket ID access | None in repo | Independent endpoint | Retain as candidate; verify multi-user session setup |
| `JS-BAC-01` | juice-shop | PRE_REG | EST | SYN | `/rest/basket/{BasketId}/order` | `quantity` | CWE-862 | BAC | vulnerable | Protocol Table 6 (SCEN-EVAL-12); missing order ownership check | None in repo | Independent endpoint | Retain as candidate; verify database mutation trace |
| `JS-BAC-02` | juice-shop | PRE_REG | EST | SYN | `/rest/admin/application-version` | `Authorization` | CWE-285 | BAC | non_vulnerable | Protocol Table 6 (SCEN-EVAL-13); `@RolesAllowed('admin')` guard | None in repo | Independent endpoint | **VALID CONTROL:** Verified stock 403 Forbidden response |
| `JS-PT-01` | juice-shop | PRE_REG | EST | SYN | `/ftp/legal.md%2500.pdf` | `path` | CWE-22 | PATH_TRAVERSAL | vulnerable | Protocol Table 6 (SCEN-EVAL-14); null-byte extension bypass | None in repo | Independent endpoint | Retain as candidate; verify Node.js runtime null-byte handling |
| `JS-SQLI-04` | juice-shop | PRE_REG | PART | PART | `/rest/products/search` | `q` | CWE-89 | SQLi | non_vulnerable | Protocol Table 6 (SCEN-EVAL-15); ambiguous generic 500 error | None in repo | Overlaps search endpoint; endpoint is actually vulnerable | **HOLD / REVISE:** Reposition as input-handling edge case, not TN locus |
| `DVWA-XSS-R-01` | dvwa | PRE_REG | EST | SYN | `/vulnerabilities/xss_r/` | `name (security=low)` | CWE-79 | XSS | vulnerable | Protocol Table 6 (SCEN-EVAL-04); PHP low security direct echo | None in repo | Independent security level | Retain as candidate; verify session cookie propagation |
| `DVWA-XSS-R-02` | dvwa | PRE_REG | EST | SYN | `/vulnerabilities/xss_r/` | `name (security=impossible)` | CWE-79 | XSS | non_vulnerable | Protocol Table 6 (SCEN-EVAL-05); `htmlspecialchars` with ENT_QUOTES | None in repo | Independent security level | **VALID CONTROL:** Verified server-side output encoding |
| `DVWA-SQLI-01` | dvwa | PRE_REG | EST | SYN | `/vulnerabilities/sqli/` | `id (security=low)` | CWE-89 | SQLi | vulnerable | Protocol Table 6 (SCEN-EVAL-09); PHP raw query concatenation | None in repo | Independent security level | Retain as candidate; verify SQL error display mode |
| `DVWA-SQLI-02` | dvwa | PRE_REG | EST | SYN | `/vulnerabilities/sqli/` | `id (security=impossible)` | CWE-89 | SQLi | non_vulnerable | Protocol Table 6 (SCEN-EVAL-10); PDO prepared statement | None in repo | Independent security level | **VALID CONTROL:** Verified parameterized query defense |
| `DVWA-XSS-R-03` | dvwa | PRE_REG | EST | SYN | `/vulnerabilities/xss_r/` | `name (security=medium)` | CWE-79 | XSS | vulnerable | Protocol Table 6 (SCEN-EVAL-16); case-sensitive regex filter bypass | None in repo | Independent security level | Retain as candidate; verify mixed-case payload reflection |
| `JS-PROP-12` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-13` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-14` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-15` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-16` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-17` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-18` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-19` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-20` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-21` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-22` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-23` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `JS-PROP-24` | juice-shop | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-06` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-07` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-08` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-09` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-10` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-11` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |
| `DVWA-PROP-12` | dvwa | POOL | UNRES | UNRES | `null` | `null` | `null` | `null` | unresolved | Placeholder candidate slot | None in repo | Unresolved | Supervisor must assign locus or remove slot |

---

## 3. Verification Evidence and Missing Information

### 3.1 Traceability Analysis of Cited Evidence
In Phase 8E.5, catalog records cited specific evidence references such as:
- `routes/search.ts line 28`
- `routes/login.ts line 36`
- `vulnerabilities/xss_r/source/low.php line 6`

**Audit Verification Result:**
- **Local Source Files:** Zero application source files exist in the AEGISCORE repository. The repository contains only guidance standards in `knowledge_base/raw/` (ASVS, WSTG, CWE definitions, OWASP cheat sheets).
- **Upstream Source Version Pinning:** The citations refer to the public upstream repositories (`bkimminich/juice-shop` v15.0.0 and `digininja/DVWA` v2024.1). However, the specific commit SHA-256 hashes, build tags, and submodule pointers have not been vendored into `s:\AegisCore`.
- **Finding:** These citations are **literature/metadata citations**, not repo-verifiable source assertions.

### 3.2 Information Required Before Adjudication Can Be Authorized
To transition any record from `UNVERIFIED` to `ADJUDICATED`, the following artifacts must be produced:
1. **Target Image Commit SHA:** Exact Git commit hash of the benchmark build (e.g., Docker image manifest digest).
2. **Deterministic Replay Trace:** A signed HTTP request/response log demonstrating vulnerability reproduction or defensive rejection.
3. **Defense Control Verification (for Negative Controls):** Source code snippet showing the active defense mechanism (e.g., parameterized query, HTML encoding, authorization interceptor).
4. **Adjudicator Signature:** Authenticated reviewer identifier and date.

---

## 4. Status Taxonomy Refinement

### 4.1 Identified Ambiguity in Phase 8E.5
In Phase 8E.5, `LocusEstablishmentStatus.ESTABLISHED` was assigned to 13 cases. This introduced a potential conflation:
- *Interpretation A (Syntactic):* The record contains non-null `target_uri`, `parameter`, and permitted `cwe_id`.
- *Interpretation B (Empirical):* The vulnerability at this locus has been verified and confirmed against the benchmark.

### 4.2 Three-Dimensional Taxonomy Implementation
To eliminate this ambiguity without breaking backward compatibility, `aegiscore/catalog.py` was updated in Phase 8E.6 to explicitly distinguish three orthogonal statuses:

```
┌────────────────────────────────┐     ┌────────────────────────────────┐     ┌────────────────────────────────┐
│  Scenario Registration Status  │     │   Locus Verification Status    │     │      Adjudication Status       │
│                                │     │                                │     │                                │
│ • protocol_pre_registered      │ ──► │ • syntactically_specified      │ ──► │ • unverified                   │
│ • candidate_pool               │     │ • partially_specified          │     │ • disputed                     │
│                                │     │ • empirically_verified         │     │ • adjudicated                  │
│                                │     │ • unresolved                   │     │                                │
└────────────────────────────────┘     └────────────────────────────────┘     └────────────────────────────────┘
```

1. **`scenario_registration_status` (`ScenarioRegistrationStatus`):**
   - `protocol_pre_registered`: Scenario was defined in Phase 8E.1 Protocol Table 6.
   - `candidate_pool`: Slot was added to reach target exploratory sample size ($N=36$).
2. **`locus_verification_status` (`LocusVerificationStatus`):**
   - `syntactically_specified`: Locus coordinates are completely recorded from protocol documentation, but target application has not been launched or audited locally.
   - `partially_specified`: Locus coordinates are recorded but represent a synthetic or patched negative control.
   - `empirically_verified`: Locus coordinates have been verified against running code in the isolated testbed.
   - `unresolved`: Locus coordinates are unpopulated (`null`).
3. **`adjudication_status` (`AdjudicationStatus`):**
   - `unverified`: Default state for all proposed cases (all 36 cases today).
   - `disputed`: Case under active review with unresolved evidence conflicts.
   - `adjudicated`: Formally approved by the thesis supervisor with timestamp.

---

## 5. Negative-Control Validity Audit

In statistical evaluation, negative controls (benign / non-vulnerable loci) are essential to measure **Specificity**, **False Positive Rate ($FPR$)**, and **Selective Risk**. However, treating the absence of a known vulnerability as proof of non-vulnerability is a critical methodological error.

### 5.1 Invalid Stock Negative Controls

#### 1. `JS-XSS-R-02` (Reflected XSS Negative Control)
- **Protocol Assumption:** Assumes search input with `<svg onload=...>` is non-vulnerable because client-side `DOMPurify.sanitize()` strips tags.
- **Flaw:** OWASP Juice Shop is a REST API backend with an Angular single-page frontend. When an assessment tool or DAST scanner queries `GET /rest/products/search?q=<svg onload=...>`, the Express backend returns the query parameter unencoded in the JSON response body. The backend does not sanitize the input.
- **Verdict:** **INVALID AS STOCK BENCHMARK CASE**. A backend vulnerability assessor querying the HTTP API would correctly detect reflection. Testing this on stock Juice Shop would produce an empirical True Positive that the benchmark falsely scores as a False Positive.

#### 2. `JS-SQLI-03` (SQL Injection Parameterized Login Control)
- **Protocol Assumption:** Assumes `/rest/user/login` safely binds credentials via parameterized queries and rejects `' OR 1=1 --` with HTTP 401.
- **Flaw:** In stock OWASP Juice Shop v15.0.0, `/rest/user/login` (`routes/login.ts`) uses raw string interpolation into Sequelize:
  ```javascript
  models.sequelize.query(`SELECT * FROM Users WHERE email = '${req.body.email || ''}' AND password = ...`)
  ```
  The endpoint is inherently vulnerable. It is impossible for stock Juice Shop to behave as a negative control on this route.
- **Verdict:** **INVALID AS STOCK BENCHMARK CASE**. Evaluating this against stock Juice Shop is technically impossible.

#### 3. `JS-SQLI-04` (Ambiguous Generic Error Disclosure Control)
- **Protocol Assumption:** Assumes generic HTTP 500 error on malformed search query is non-vulnerable.
- **Flaw:** While generic 500 errors should trigger epistemic uncertainty abstention, the underlying search route is genuinely vulnerable to UNION-based SQLi (`JS-SQLI-02`). Calling a vulnerable endpoint with a malformed payload does not transform the locus into a True Negative.
- **Verdict:** **METHODOLOGICAL CONFLATION**. Tests uncertainty calibration on malformed input, but cannot serve as an independent negative control locus in the confusion matrix.

### 5.2 Valid Stock Negative Controls

#### 1. `JS-BAC-02` (Admin Application Version)
- **Endpoint:** `GET /rest/admin/application-version`
- **Defense Mechanism:** Express router enforces role middleware: `insecurity.hasRole('admin')`. Regular user tokens receive an unambiguous HTTP 403 Forbidden.
- **Verdict:** **VALID GENUINE NEGATIVE CONTROL**.

#### 2. `DVWA-XSS-R-02` (Reflected XSS Impossible Security)
- **Endpoint:** `GET /vulnerabilities/xss_r/?name=<payload>` with cookie `security=impossible`
- **Defense Mechanism:** PHP code applies `htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8')`.
- **Verdict:** **VALID GENUINE NEGATIVE CONTROL**.

#### 3. `DVWA-SQLI-02` (SQLi Impossible Security)
- **Endpoint:** `GET /vulnerabilities/sqli/?id=<payload>&Submit=Submit` with cookie `security=impossible`
- **Defense Mechanism:** PHP code binds input via PDO prepared statement: `$stmt->bindParam(':id', $id, PDO::PARAM_INT)`.
- **Verdict:** **VALID GENUINE NEGATIVE CONTROL**.

---

## 6. Independence and Leakage Audit

### 6.1 Unit of Analysis Independence Invariant
The thesis evaluation protocol requires that every evaluation case represents an independent canonical locus: `(benchmark_name, target_uri, parameter, cwe_id)`.

### 6.2 Identified Overlaps & Leakage Hazards

1. **Juice Shop `/rest/products/search` Endpoint Concentration:**
   - 4 cases target the same search query parameter `q`:
     - `JS-XSS-R-01` (CWE-79, vulnerable)
     - `JS-XSS-R-02` (CWE-79, partial negative control)
     - `JS-SQLI-02` (CWE-89, vulnerable)
     - `JS-SQLI-04` (CWE-89, partial edge case)
   - *Leakage Risk:* High risk of state leakage, cache persistence, or database lock interference if executed sequentially without container reset.
   - *Statistical Concern:* High endpoint clustering violates the assumption of independent Bernouilli trials in paired tests.
2. **Juice Shop `/rest/user/login` Endpoint Concentration:**
   - 2 cases target the same login route:
     - `JS-SQLI-01` (CWE-89, vulnerable)
     - `JS-SQLI-03` (CWE-89, partial negative control)
   - *Leakage Risk:* Account lockout, failed-attempt counters, or session token persistence across trials.
3. **DVWA Security Level Parameterization:**
   - DVWA cases differentiate security levels via cookie/session state (`security=low`, `medium`, `impossible`).
   - *Leakage Risk:* If session cookies are not strictly reset between trials, tests intended for Impossible level may execute under Low level privileges, or vice versa.

---

## 7. Recommended Inclusion, Exclusion, and Revision Decisions

### 7.1 Tier 1: Recommended for Immediate Supervisor Review (11 Cases)
These cases possess documented upstream vulnerability or defensive implementations, complete loci, and distinct endpoints:
- **Juice Shop Vulnerable (7 cases):** `JS-XSS-R-01`, `JS-XSS-S-01`, `JS-SQLI-01`, `JS-SQLI-02`, `JS-BAC-IDOR-01`, `JS-BAC-01`, `JS-PT-01`
- **Juice Shop Benign Control (1 case):** `JS-BAC-02`
- **DVWA Vulnerable (2 cases):** `DVWA-XSS-R-01`, `DVWA-SQLI-01`, `DVWA-XSS-R-03`
- **DVWA Benign Control (2 cases):** `DVWA-XSS-R-02`, `DVWA-SQLI-02`
*(Total: 12 cases)*

### 7.2 Tier 2: Hold Pending Negative Control Strategy (3 Cases)
- `JS-XSS-R-02`: Requires decision on client-side DOMPurify vs. API-level negative control.
- `JS-SQLI-03`: Requires decision on patched testbed variant vs. synthetic harness mock.
- `JS-SQLI-04`: Recommend reclassifying as an ablation diagnostic scenario, not a primary benchmark locus.

### 7.3 Tier 3: Hold Pending Candidate Selection (20 Slots)
- `JS-PROP-12` through `JS-PROP-24` (13 slots)
- `DVWA-PROP-06` through `DVWA-PROP-12` (7 slots)
- Must be populated by supervisor selection from additional benchmark loci (e.g., Juice Shop JWT manipulation, NoSQL injection, XML external entity, SSRF, open redirect; DVWA command injection, file inclusion, CSRF).

---

## 8. Supervisor Decisions Required Prior to Phase 8E.7

The following formal decisions are required from the thesis supervisor:

1. **Negative Control Implementation Architecture:**
   - *Option A (Synthetic Fixture Mocks):* Keep benchmark containers strictly stock; evaluate negative controls through synthetic runner fixtures in the offline harness.
   - *Option B (Testbed Code Patches):* Fork Juice Shop to create a verified defensive branch with parameterized login and server-side sanitized search.
2. **Candidate Pool Selection:**
   - Review and select specific endpoints, parameters, and CWEs for the 20 unresolved candidate slots (`JS-PROP-12`..`24`, `DVWA-PROP-06`..`12`).
3. **Partition Allocation Sign-Off:**
   - Formally authorize the partition split: 40% validation (~10 cases) and 60% test (~14 cases) on Juice Shop; DVWA as secondary transfer evaluation.
4. **Adjudication Authorization:**
   - Authorize transition of the 12 Tier-1 candidate cases from `UNVERIFIED` to `ADJUDICATED` once live testbed traces are collected.

---

## 9. Readiness Recommendation

### Final Recommendation: HOLD on Live Execution; GO on Supervisor Review
- **HOLD:** Empirical evaluation, benchmark deployment, container launching, HTTP request transmission, scanner execution, and partition assignment remain **STRICTLY PROHIBITED**.
- **GO:** The case catalog provenance audit and supervisor review package are finalized, fully validated, and ready for supervisor inspection and decision-making.
