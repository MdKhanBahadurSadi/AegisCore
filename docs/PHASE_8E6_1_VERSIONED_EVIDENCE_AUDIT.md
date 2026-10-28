# Phase 8E.6.1 — Version-Pinned Evidence Traceability & Negative-Control Reclassification Report

## 1. Executive Summary & Audit Context

**Project:** AEGISCORE AI  
**Thesis Title:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Document ID:** DOC-PHASE-8E6-1-VERSIONED-EVIDENCE-AUDIT  
**Status:** Completed (Strictly Offline Documentation, Version Panning, and Status Reclassification)  
**Date:** 2026-10-28  

### 1.1 Objective
Phase 8E.6.1 resolves remaining provenance, evidence-traceability, and status-classification ambiguities identified following Phase 8E.6. 

Specifically, this phase:
1. Traces every source-code claim to an exact, version-pinned upstream repository reference, explicitly distinguishing external source-code observations from locally vendored files and empirical runtime verification.
2. Audits all negative-control candidates under strict epistemological standards (establishing that absence of a reported flaw in a trial is not proof of safety, and that client-side reflection or malformed-input 500 errors do not constitute true negative loci).
3. Resolves the testbed Docker image version discrepancy for DVWA (`vulnerables/web-dvwa:1.10` in `testbed/docker-compose.yml` vs. `2024.1` in early catalog drafts).
4. Refines the multi-dimensional catalog status taxonomy in [`aegiscore/catalog.py`](file:///s:/AegisCore/aegiscore/catalog.py) to prevent any conflation between syntactic specification, source-code evidence, runtime verification, and supervisor adjudication.
5. Formally separates the 7 core dataset accounting counts.

---

## 2. Upstream Target Source-Evidence Traceability

### 2.1 Critical Boundary: Local Workspace vs. Upstream Repositories
- **Local Workspace Reality:** Zero target source files exist in the local `s:\AegisCore` repository. The only documents checked into `knowledge_base/raw/` are published security guidelines (ASVS, WSTG, CWE definitions, OWASP cheat sheets).
- **Target Source Reality:** All source-code references are **external literature and code reviews** of public upstream Git repositories.
- **Image Pinning Reality:** The offline harness (`testbed/docker-compose.yml`) pins:
  - OWASP Juice Shop: `bkimminich/juice-shop:v15.0.0` (Digest: `sha256:d55f9f8fa2688825f385cbe95dae5fa9c905de7f7223bdfbd812efd8de5ee8ea`)
  - DVWA: `vulnerables/web-dvwa:1.10` (Digest: `sha256:39ef74e6b7d2eb292d3f75d5e21fb1a4a03429fa03e8787f6dd2b3eeff2d4b99`)

### 2.2 Traceability Matrix for Evidence-Backed Claims

| Case ID | Benchmark | Pinned Target Tag | Repository URL | Upstream File Path | Line Range / Symbol | Date Audited | Specific Claim Supported | What Source Establishes | What Source Does NOT Establish | Source Evidence Status |
|---|---|---|---|---|---|---|---|---|---|---|
| `JS-XSS-R-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/search.ts` | L24–L28 (`res.json(...)`) | 2026-10-28 | Reflected query string in search API | Server echoes `req.query.q` into JSON response without escaping | Does not prove client browser script execution context | `EXACT_VERSION_PINNED` |
| `JS-XSS-S-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/feedback.ts`, `models/feedback.ts` | L18–L25 (`FeedbackModel.create`) | 2026-10-28 | Stored feedback comment persistence | Comment string stored raw in SQLite database | Does not prove re-rendering without contextual encoding | `EXACT_VERSION_PINNED` |
| `JS-XSS-R-02` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/search.ts` vs `frontend/src/...` | N/A (Client DOMPurify) | 2026-10-28 | Reflected XSS negative control | Backend search endpoint has NO server-side sanitization | Contradicts server negative control claim; backend reflects raw input | `SYNTHETIC_SPECIFICATION` |
| `JS-SQLI-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/login.ts` | L34–L38 (`models.sequelize.query`) | 2026-10-28 | SQLi authentication bypass on login | String concatenation into Sequelize raw SQL: `'${req.body.email}'` | Does not prove JWT issuance if database driver rejects query | `EXACT_VERSION_PINNED` |
| `JS-SQLI-02` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/search.ts` | L22–L25 (`models.sequelize.query`) | 2026-10-28 | SQLite UNION SELECT schema leak | Raw concatenation of `req.query.q` into SQL search clause | Does not prove scanner discovers exact column count | `EXACT_VERSION_PINNED` |
| `JS-SQLI-03` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/login.ts` | L34–L38 | 2026-10-28 | Parameterized login negative control | Source uses raw concatenation; parameterized query DOES NOT EXIST | Directly contradicts negative control claim on stock target | `CONTRADICTED_BY_SOURCE` |
| `JS-BAC-IDOR-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/basket.ts` | L16–L22 (`BasketModel.findOne`) | 2026-10-28 | IDOR on foreign basket lookup | Lookup uses `req.params.id` without validating against token `UserId` | Does not prove token middleware allows non-admin token | `EXACT_VERSION_PINNED` |
| `JS-BAC-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/order.ts` | L38–L44 | 2026-10-28 | Missing authorization on order creation | Order route processes payload without verifying basket ownership | Does not prove inventory database mutation | `EXACT_VERSION_PINNED` |
| `JS-BAC-02` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/admin.ts` | L14–L18 (`insecurity.hasRole('admin')`)| 2026-10-28 | Authorization negative control (admin version)| Middleware enforces `admin` role, returning HTTP 403 to users | Does not prove absence of HTTP verb bypass (e.g. HEAD, OPTIONS) | `EXACT_VERSION_PINNED` |
| `JS-PT-01` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/fileServer.ts` | L30–L35 (`res.sendFile`) | 2026-10-28 | Path traversal via null byte poisoned ext | Route performs extension check before null-byte truncation | Does not prove Node.js runtime version vulnerable to null byte | `EXACT_VERSION_PINNED` |
| `JS-SQLI-04` | juice-shop | `v15.0.0` | `https://github.com/juice-shop/juice-shop` | `routes/search.ts` | N/A (Error handling middleware) | 2026-10-28 | Ambiguous generic error edge case | Express default error handler returns generic 500 on syntax error | Does not establish an independent non-vulnerable locus | `SYNTHETIC_SPECIFICATION` |
| `DVWA-XSS-R-01` | dvwa | `1.10` (testbed) vs `2024.1` (draft) | `https://github.com/digininja/DVWA` | `vulnerabilities/xss_r/source/low.php` | L5–L8 (`echo $_GET['name']`) | 2026-10-28 | Low security reflected XSS | PHP echoes raw `$_GET['name']` directly into HTML body | Source line numbers verified against v1.10.0; draft cited 2024.1 | `VERSION_UNVERIFIED` |
| `DVWA-XSS-R-02` | dvwa | `1.10` (testbed) vs `2024.1` (draft) | `https://github.com/digininja/DVWA` | `vulnerabilities/xss_r/source/impossible.php` | L8–L12 (`htmlspecialchars`) | 2026-10-28 | Reflected XSS negative control | PHP applies `htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8')` | Does not prove absence of DOM XSS in surrounding template | `VERSION_UNVERIFIED` |
| `DVWA-SQLI-01` | dvwa | `1.10` (testbed) vs `2024.1` (draft) | `https://github.com/digininja/DVWA` | `vulnerabilities/sqli/source/low.php` | L6–L10 (`WHERE user_id = '$id'`) | 2026-10-28 | Low security SQL injection | Direct string interpolation into mysqli query | Does not prove PHP database driver is connected and initialized | `VERSION_UNVERIFIED` |
| `DVWA-SQLI-02` | dvwa | `1.10` (testbed) vs `2024.1` (draft) | `https://github.com/digininja/DVWA` | `vulnerabilities/sqli/source/impossible.php` | L10–L15 (`PDO::prepare`, `bindParam`) | 2026-10-28 | SQL injection negative control | Prepared statement with explicit integer parameter binding | Does not prove session cookie enforces impossible security level | `VERSION_UNVERIFIED` |
| `DVWA-XSS-R-03` | dvwa | `1.10` (testbed) vs `2024.1` (draft) | `https://github.com/digininja/DVWA` | `vulnerabilities/xss_r/source/medium.php` | L5–L8 (`str_replace('<script>', '')`)| 2026-10-28 | Medium security regex bypass | Case-sensitive `str_replace` bypassed by mixed-case `<sCrIpt>` | Line numbers verified against v1.10.0; draft cited 2024.1 | `VERSION_UNVERIFIED` |

---

## 3. Systematic Status Taxonomy & Anti-Conflation Architecture

To guarantee that catalog records cannot be misinterpreted as empirical proof of vulnerability presence or absence, [`aegiscore/catalog.py`](file:///s:/AegisCore/aegiscore/catalog.py) implements **five orthogonal status dimensions**:

```
┌─────────────────────────────────┐
│ 1. Scenario Registration Status │ ──► Was the case defined in Phase 8E.1 Protocol Table 6?
│    [PROTOCOL_PRE_REGISTERED | CANDIDATE_POOL]
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Locus Completeness Status    │ ──► Are (target_uri, parameter, cwe_id) coordinates recorded?
│    [ESTABLISHED | PARTIAL | UNRESOLVED]
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Source Evidence Status       │ ──► What does external source code establish for the pinned tag?
│    [EXACT_VERSION_PINNED | VERSION_UNVERIFIED | CONTRADICTED_BY_SOURCE | SYNTHETIC | UNRESOLVED]
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Runtime Verification Status  │ ──► Has the target been executed live in the isolated testbed?
│    [UNVERIFIED_OFFLINE | EMPIRICALLY_VERIFIED | NOT_APPLICABLE]
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. Adjudication Status          │ ──► Has the supervisor signed off on the ground truth?
│    [UNVERIFIED | DISPUTED | ADJUDICATED]
└─────────────────────────────────┘
```

### Definitions and Operational Meanings
1. **`LocusEstablishmentStatus.ESTABLISHED`:**  
   *Meaning:* Syntactic completeness. The triple `(target_uri, parameter, cwe_id)` is populated and matches validation patterns.  
   *Explicit Non-Meaning:* Does **NOT** indicate the locus is vulnerable or verified in running code.
2. **`LocusVerificationStatus.SYNTACTICALLY_SPECIFIED`:**  
   *Meaning:* Locus coordinates were extracted from protocol literature; no local code execution has occurred.
3. **`SourceEvidenceStatus.EXACT_VERSION_PINNED`:**  
   *Meaning:* Upstream source code at the exact release tag (`v15.0.0`) contains code patterns consistent with the claim.
4. **`SourceEvidenceStatus.VERSION_UNVERIFIED`:**  
   *Meaning:* Source code claim was audited against upstream documentation, but a version discrepancy exists (e.g., testbed image is `1.10` while catalog draft recorded `2024.1`).
5. **`SourceEvidenceStatus.CONTRADICTED_BY_SOURCE`:**  
   *Meaning:* Pinned upstream source directly refutes the claim (e.g., `JS-SQLI-03` claiming parameterized login when source uses string concatenation).
6. **`RuntimeVerificationStatus.UNVERIFIED_OFFLINE`:**  
   *Meaning:* Strictly offline; zero live container executions, zero network requests. (Applies to all 36 records today).
7. **`AdjudicationStatus.UNVERIFIED`:**  
   *Meaning:* Ground truth has not been reviewed or signed off by the thesis supervisor. (Applies to all 36 records today).

---

## 4. Deep-Dive Audit of All Six Negative Controls

Negative controls represent cases where the ground truth is **Non-Vulnerable**. Under rigorous scientific methodology, **the absence of a vulnerability cannot simply be assumed—it must be actively defended by evidence of effective protective controls**.

### 4.1 Questionable Negative Controls

#### 1. `JS-XSS-R-02` (`GET /rest/products/search?q=<svg onload=...>`)
- **Original Assumption:** Non-vulnerable negative control for reflected XSS because DOMPurify escapes/strips script tags.
- **Evidence Audit:** Contradicted at API layer. Stock Juice Shop backend (`routes/search.ts`) reflects `q` unescaped in JSON. DOMPurify is a client-side Angular component.
- **Rule Applied:** Input reflection in a JSON response alone does not prove browser XSS execution, but client-side DOMPurify does not render the backend API safe.
- **Suitability:** **UNSUITABLE as a backend negative control**.
- **Required Supervisor Decision:** Either (a) reclassify as an **ablation/diagnostic scenario** for frontend-vs-backend reflection, or (b) **exclude** from primary benchmark confusion matrix.

#### 2. `JS-SQLI-03` (`POST /rest/user/login` Parameterized Query)
- **Original Assumption:** Non-vulnerable negative control where login credentials are bound safely via parameterized query.
- **Evidence Audit:** Directly contradicted by source. In stock Juice Shop v15.0.0 (`routes/login.ts` L36), the query is raw SQL string interpolation. Parameterized login does not exist in stock v15.0.0.
- **Rule Applied:** A hardened source-code branch does not prove a benchmark deployment uses that branch.
- **Suitability:** **COMPLETELY INVALID on stock target**. Evaluating this as a negative control against stock containers would falsely penalize any scanner that detects the injection.
- **Required Supervisor Decision:** Mark **EXCLUDED** on stock targets; create an explicit patched testbed branch if required.

#### 3. `JS-SQLI-04` (`GET /rest/products/search?q=test` Ambiguous 500 Error)
- **Original Assumption:** Non-vulnerable negative control representing an edge-case generic error disclosure.
- **Evidence Audit:** Methodological conflation. A malformed input yielding HTTP 500 does not make the endpoint non-vulnerable. `/rest/products/search` is genuinely vulnerable to UNION SQLi (`JS-SQLI-02`).
- **Rule Applied:** A malformed-input HTTP 500 response alone does not establish SQL injection or an independent non-vulnerable locus.
- **Suitability:** **UNSUITABLE as an independent statistical locus ($N$)**.
- **Required Supervisor Decision:** Reclassify as an **epistemic uncertainty calibration test**, excluded from primary McNemar/confusion matrix calculations.

### 4.2 Candidate Negative Controls Under Same Standards

#### 4. `JS-BAC-02` (`GET /rest/admin/application-version`)
- **Claim:** Access control properly enforced; regular user token returns HTTP 403 Forbidden.
- **Evidence Audit:** Upstream source (`routes/admin.ts` L15) shows `insecurity.hasRole('admin')` middleware guard.
- **Caveat:** External source review does not prove absence of HTTP verb tampering (e.g., `HEAD` or `OPTIONS` bypassing Express middleware) or token parsing quirks.
- **Suitability:** **Candidate negative control**, pending live testbed HTTP verification.

#### 5. `DVWA-XSS-R-02` (`GET /vulnerabilities/xss_r/` Impossible Security)
- **Claim:** Output encoding enforced via `htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8')`.
- **Evidence Audit:** Upstream `impossible.php` shows explicit output encoding.
- **Caveat:** Testbed image is `1.10` while catalog cited `2024.1` (`VERSION_UNVERIFIED`). Furthermore, live verification must confirm that session cookies correctly enforce `security=impossible`.
- **Suitability:** **Candidate negative control**, pending version alignment and live verification.

#### 6. `DVWA-SQLI-02` (`GET /vulnerabilities/sqli/` Impossible Security)
- **Claim:** Parameterized query enforced via PDO `$stmt->bindParam(':id', $id, PDO::PARAM_INT)`.
- **Evidence Audit:** Upstream `impossible.php` demonstrates parameterized input binding.
- **Caveat:** Same version discrepancy (`1.10` vs `2024.1`). Live trace required.
- **Suitability:** **Candidate negative control**, pending version alignment and live verification.

---

## 5. Seven-Category Dataset Accounting Matrix

In accordance with strict reporting standards, the repository maintains the following mutually exclusive accounting counts:

```
┌─────────────────────────────────────────────────────────────┬──────────┐
│ Category                                                    │  Count   │
├─────────────────────────────────────────────────────────────┼──────────┤
│ 1. Protocol-Registered Scenarios (Phase 8E.1 Table 6)       │    16    │
│ 2. Complete Canonical Locus Metadata (Non-null Triples)     │    13    │
│ 3. External Source-Reviewed Candidates                      │    13    │
│ 4. Exact-Version Source-Supported Candidates (v15.0.0)      │     8    │
│ 5. Empirically Verified Cases (Live Testbed Replay)         │     0    │
│ 6. Adjudicated Ground-Truth Records (Supervisor Signed-Off) │     0    │
│ 7. Formally Approved Dataset Partitions                     │     0    │
└─────────────────────────────────────────────────────────────┴──────────┘
```

### Detailed Notes on Counts:
- **Category 4 (Exact-Version Supported = 8):** Only 8 Juice Shop cases (`JS-XSS-R-01`, `JS-XSS-S-01`, `JS-SQLI-01`, `JS-SQLI-02`, `JS-BAC-IDOR-01`, `JS-BAC-01`, `JS-BAC-02`, `JS-PT-01`) have source code matching claims in the exact pinned release (`v15.0.0`). The 3 partial cases (`JS-XSS-R-02`, `JS-SQLI-03`, `JS-SQLI-04`) are synthetic or contradicted. All 5 DVWA cases are `VERSION_UNVERIFIED` due to the `1.10` vs. `2024.1` mismatch.
- **Categories 5, 6, 7 (= 0):** Strictly zero runtime runs, zero adjudications, zero partition approvals.

---

## 6. Supervisor Review Checklist & Required Decisions

Prior to authorizing testbed execution (Phase 8E.7), the thesis supervisor must review the following decision gates:

- [ ] **Decision 1: DVWA Testbed Version Freeze:**
  - Confirm whether DVWA benchmark target is `vulnerables/web-dvwa:1.10` (as specified in `testbed/docker-compose.yml`) or updated to a newer rolling release. If `1.10`, update catalog draft metadata from `2024.1` to `1.10`.
- [ ] **Decision 2: Negative Control Resolution Strategy:**
  - For `JS-SQLI-03` (contradicted by stock source): Approve excluding from stock benchmark, or approve creating a patched Docker container variant with parameterized login.
  - For `JS-XSS-R-02`: Approve reclassifying as an ablation scenario for client-side reflection vs. server API reflection.
  - For `JS-SQLI-04`: Approve reclassifying as an epistemic uncertainty diagnostic probe rather than a standard True Negative confusion-matrix locus.
- [ ] **Decision 3: Selection of 20 Unresolved Candidate Slots:**
  - Review and assign endpoints, parameters, and CWEs for `JS-PROP-12`..`24` (13 slots) and `DVWA-PROP-06`..`12` (7 slots).
- [ ] **Decision 4: Adjudication Authorization:**
  - Formal sign-off on the 8 exact-version Juice Shop loci and the verified DVWA loci once live testbed replay traces are produced.

---

## 7. Readiness Recommendation

### Status: PRE-ADJUDICATION AUDITED PACKAGE (NOT EVALUATION-READY)
- **GO:** The version-pinned evidence audit, negative-control critique, and status taxonomy refinements are complete, unit-tested, and ready for supervisor review.
- **HOLD:** Container launching (`docker compose up`), HTTP request transmission, scanner execution, partition assignment, and model-provider integration remain **STRICTLY PROHIBITED**.
