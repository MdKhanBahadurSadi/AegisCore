# AEGISCORE AI — Supervisor Decision Register

**Project:** AEGISCORE AI  
**Thesis Title:** *An Uncertainty-Aware Multi-Agent LLM Framework with Retrieval-Augmented Generation for Evidence-Based Web Application Vulnerability Assessment*  
**Document ID:** DOC-SUPERVISOR-DECISION-REGISTER  
**Date:** 2026-10-28  
**Governance Directive:** Every decision in this register governs a critical methodological, safety, or empirical boundary. All decisions are initialized to **`PENDING`**. No container startup, benchmark execution, partition assignment, or external model provider calls may be executed until the relevant decision has been formally reviewed, approved, and signed by the thesis supervisor.

---

## Decision Index

| Decision ID | Decision Title | Status | Impact Area |
|---|---|:---:|---|
| **DEC-01** | Approval of Exploratory Statistical Framing | `PENDING` | Statistical Claims & Power Framing |
| **DEC-02** | Acceptance or Revision of Proposed Evaluation Scope ($N=36$) | `PENDING` | Benchmark Case Population & Size |
| **DEC-03** | Ground-Truth Review and Adjudication Procedure | `PENDING` | Ground-Truth Governance |
| **DEC-04** | Case Inclusion/Exclusion & Negative-Control Resolution | `PENDING` | Confusion Matrix Validity |
| **DEC-05** | Approval of Validation / Test Partition Policy | `PENDING` | Data Leakage & Evaluation Partitioning |
| **DEC-06** | Benchmark Version and Immutable Image-Digest Policy | `PENDING` | Target Reproducibility & Digest Pinning |
| **DEC-07** | Model-Provider Architecture Selection (Cloud vs. Local) | `PENDING` | Egress Boundary & Hardware Requirements |
| **DEC-08** | Explicit Authorization for Container Startup & Live Execution | `PENDING` | Testbed Safety & Egress Release |

---

## Detailed Decision Records

### DEC-01: Approval of Exploratory Statistical Framing

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-01` |
| **Decision Question** | Should the benchmark evaluation be formally framed as an **exploratory feasibility study** with pre-registered hypotheses and descriptive statistics, rather than a confirmatory hypothesis test claiming population generalization? |
| **Available Options** | **Option A (Recommended — Exploratory Framing):** Formally frame as an exploratory proof-of-concept study ($N=36$). Report McNemar's paired test with exact binomial p-values, empirical odds ratios, selective risk, and coverage curves. Explicitly disclose that statistical power is governed by the observed count of discordant pairs ($n_{\text{disc}} = b + c$) which cannot be determined a priori, and that failure to reject $H_0$ ($p \ge 0.05$) under this exploratory sample does **not** prove equivalence or absence of an effect.<br>**Option B (Confirmatory Study Expansion):** Substantially expand benchmark scope across multiple additional target applications to assemble a large independent case population (e.g., $N \gg 80$), establishing a priori statistical power via formal prospective power analysis conditioned on expected concordance. |
| **Relevant Evidence** | - `docs/PHASE_8E2A1_STATISTICAL_REVIEW.md` (§ 2–§ 4)<br>- `docs/PHASE_8E2A2_STATISTICAL_CORRECTIONS.md` (§ 1, § 3)<br>- `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§ 5) |
| **Risks & Trade-offs** | - *Option A Risk:* Reviewers may note limited sample size; thesis claims must strictly avoid claiming generalizable population superiority.<br>- *Option B Risk:* Substantially increases manual curation and adjudication overhead; delays evaluation timeline significantly. |
| **Decision Owner** | Thesis Supervisor & Candidate |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-02: Acceptance or Revision of Proposed Evaluation Scope ($N=36$)

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-02` |
| **Decision Question** | Does the supervisor approve the proposed target scope of 36 evaluation cases (24 OWASP Juice Shop, 12 DVWA), and how should the 20 unpopulated candidate slots (`JS-PROP-12`..`24`, `DVWA-PROP-06`..`12`) be populated or pruned? |
| **Available Options** | **Option A:** Approve the target $N=36$ scope. Select and assign 13 additional Juice Shop loci (e.g., JWT manipulation, NoSQL injection, file upload, SSRF) and 7 additional DVWA loci (e.g., Command Injection, File Inclusion, CSRF).<br>**Option B:** Restrict the formal benchmark scope to the 16 pre-registered protocol scenarios from Table 6 (pruning the 20 unresolved slots).<br>**Option C:** Focus evaluation exclusively on OWASP Juice Shop ($N=24$), eliminating DVWA. |
| **Relevant Evidence** | - `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (Table 6)<br>- `docs/case_catalog_draft.jsonl`<br>- `docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md` (§ 2, § 5) |
| **Risks & Trade-offs** | - *Option A Risk:* Requires curating and adjudicating 20 new loci before evaluation.<br>- *Option B Risk:* Reduces sample size to $N=16$, further reducing statistical power.<br>- *Option C Risk:* Eliminates cross-framework generalization (Node.js vs. PHP). |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-03: Ground-Truth Review and Adjudication Procedure

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-03` |
| **Decision Question** | What formal criteria and review procedure must be satisfied before ground-truth records are marked `ADJUDICATED` in `docs/ground_truth_review_template.jsonl`? |
| **Available Options** | **Option A (Recommended):** Mandate a 3-part verification artifact for each case: (1) exact source code commit SHA and line range; (2) deterministic HTTP replay trace showing vulnerability exploit or defensive rejection; (3) independent supervisor sign-off with timestamp.<br>**Option B:** Rely on upstream benchmark documentation (e.g., Pwning Juice Shop book and DVWA help pages) without requiring live HTTP replay traces.<br>**Option C:** Form an external 2-reviewer panel to adjudicate ambiguous edge cases. |
| **Relevant Evidence** | - `docs/ground_truth_review_template.jsonl`<br>- `aegiscore/catalog.py` (`GroundTruthReviewRecord`)<br>- `docs/PHASE_8E5_CASE_CATALOG_AND_GROUND_TRUTH.md` (§ 4) |
| **Risks & Trade-offs** | - *Option A Risk:* Requires running the testbed in a preliminary trace-recording mode prior to evaluation.<br>- *Option B Risk:* Relies on literature claims that may diverge from container runtime behavior.<br>- *Option C Risk:* Organizational coordination overhead. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-04: Case Inclusion/Exclusion & Negative-Control Resolution

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-04` |
| **Decision Question** | How should the three defective negative controls (`JS-XSS-R-02`, `JS-SQLI-03`, `JS-SQLI-04`) be resolved in the benchmark catalog? |
| **Available Options** | **Option A (Recommended):**<br>  - Exclude `JS-SQLI-03` from stock benchmark (contradicted by stock source).<br>  - Reclassify `JS-XSS-R-02` as an ablation diagnostic scenario (client vs. server reflection), removing it from primary confusion matrix.<br>  - Reclassify `JS-SQLI-04` as an epistemic uncertainty diagnostic probe (generic 500 error on malformed input), not an independent negative locus.<br>  - Retain `JS-BAC-02` (exact-version source-reviewed on Juice Shop v15.0.0) alongside candidate controls `DVWA-XSS-R-02` and `DVWA-SQLI-02` (source-reviewed from upstream DVWA, version-unverified against testbed container `vulnerables/web-dvwa:1.10`) as candidate negative controls, strictly subject to live runtime verification and supervisor adjudication.<br>**Option B:** Create a customized, patched Docker build of Juice Shop that introduces parameterized login and server-side DOMPurify sanitization.<br>**Option C:** Implement negative controls solely via synthetic fixture mocking in the harness. |
| **Relevant Evidence** | - `docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md` (§ 4)<br>- `docs/independence_audit_template.jsonl`<br>- `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§ 4.2)<br>- `aegiscore/catalog.py` |
| **Risks & Trade-offs** | - *Option A Risk:* Reduces the count of benign control loci on Juice Shop.<br>- *Option B Risk:* Deviates from vanilla off-the-shelf benchmark images, reducing direct comparability with other literature.<br>- *Option C Risk:* Does not evaluate live target interaction on negative controls. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-05: Approval of Validation / Test Partition Policy

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-05` |
| **Decision Question** | Which dataset partition policy should be approved for validation tuning and test evaluation across OWASP Juice Shop and DVWA? |
| **Available Options** | **Option A (Pre-Registered Protocol Proposal — Recommended):** Formally approve the within-benchmark stratified 40% validation (~10 cases) / 60% test (~14 cases) partition on OWASP Juice Shop as pre-registered in `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§13.3) and `docs/PHASE_8E2A_PROTOCOL_AUDIT.md`, with DVWA held out in its entirety as an independent secondary transfer evaluation partition. Enforce strict controller-level zero-leakage disjointness.<br>**Option B (Alternative Candidate Proposal: 50/50 Split):** Partition Juice Shop into 50% validation (~12 cases) and 50% test (~12 cases) to provide equal balancing between calibration and test sets.<br>**Option C (Alternative Candidate Proposal: Zero-Shot Direct Evaluation):** Eliminate validation split tuning entirely; evaluate 100% of cases as a test set without prompt or threshold optimization.<br>**Option D (Alternative Candidate Proposal: K-Fold Cross-Validation):** Adopt $K$-fold cross-validation ($K=5$) across all cases. |
| **Relevant Evidence** | - `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§13.3)<br>- `docs/partition_assignment_template.jsonl`<br>- `aegiscore/catalog.py` (`validate_partition_assignment_jsonl`)<br>- `docs/PHASE_8E5_CASE_CATALOG_AND_GROUND_TRUTH.md` (§ 6)<br>- `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§ 3.1) |
| **Risks & Trade-offs** | - *Option A Risk:* Leaves only ~14 test cases on Juice Shop for final reported performance; small validation set ($N_{\text{val}} \approx 10$) precludes fine-grained continuous threshold tuning.<br>- *Option B Risk:* Reduces test partition size further to ~12 cases.<br>- *Option C Risk:* Precludes tuning specialist confidence thresholds or few-shot exemplars.<br>- *Option D Risk:* High prompt-tuning variance across folds on small sample size; increases evaluation run count by $5\times$. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-06: Benchmark Version and Immutable Image-Digest Policy

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-06` |
| **Decision Question** | Which exact version and immutable SHA-256 image digest policy should be enforced for DVWA and OWASP Juice Shop? |
| **Available Options** | **Option A (Recommended):** Freeze DVWA to `vulnerables/web-dvwa:1.10` (matching `testbed/docker-compose.yml`) and Juice Shop to `bkimminich/juice-shop:v15.0.0`. Pin exact immutable SHA-256 digests in Docker Compose.<br>**Option B:** Upgrade DVWA to current rolling tag `2024.1` on GitHub, updating Compose configuration and re-auditing PHP source line references.<br>**Option C:** Pin only semantic tags without cryptographic SHA-256 digest pinning. |
| **Relevant Evidence** | - `testbed/docker-compose.yml` (L15, L29)<br>- `docs/PHASE_8E2B_OFFLINE_HARNESS.md` (§ 3)<br>- `docs/PHASE_8E6_1_VERSIONED_EVIDENCE_AUDIT.md` (§ 2, § 5) |
| **Risks & Trade-offs** | - *Option A Risk:* DVWA 1.10 is an older PHP 5/7 release; must ensure modern Docker engines run it cleanly.<br>- *Option B Risk:* Modifies existing verified Phase 8E.2B Compose contracts and requires re-auditing source lines.<br>- *Option C Risk:* Unpinned tags allow upstream image mutations, violating thesis reproducibility. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-07: Model-Provider Architecture Selection (Cloud vs. Local)

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-07` |
| **Decision Question** | Which LLM inference architecture should be approved for experimental multi-agent execution? |
| **Available Options** | **Option A (Cloud API):** Google AI Gemini 1.5 Pro via Python SDK. Requires approving narrow outbound egress exemption in ADR 0002 exclusively for API endpoints (`generativelanguage.googleapis.com`).<br>**Option B (Local Open Weights):** Local Ollama / vLLM runtime running `Llama-3.1-70B-Instruct` or `Qwen-2.5-Coder-32B` on local workstation GPUs. Preserves strict zero-egress network boundary.<br>**Option C (Hybrid):** Local open-weights for Specialist / Reviewer roles; Cloud Gemini for final response synthesis. |
| **Relevant Evidence** | - `docs/ADRs/ADR-0002-PYTHON-LOCAL-FIRST-ARCHITECTURE.md`<br>- `docs/PHASE_8E1_EVALUATION_PROTOCOL.md` (§ 13)<br>- `aegiscore/safety_policy.py` |
| **Risks & Trade-offs** | - *Option A Risk:* Requires egress hole in isolation sandbox; API rate limits, costs, and non-deterministic cloud updates.<br>- *Option B Risk:* Requires substantial local GPU hardware (VRAM $\ge 48\text{ GB}$ for 70B quantization); slower inference speed.<br>- *Option C Risk:* Engineering complexity of supporting two separate runner backends. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING`** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |

---

### DEC-08: Explicit Authorization for Container Startup & Live Execution

| Field | Detail |
|---|---|
| **Decision ID** | `DEC-08` |
| **Decision Question** | Does the supervisor authorize transitioning AEGISCORE AI from offline static validation to live container deployment, testbed health checks, and active HTTP assessment execution? |
| **Available Options** | **Option A (HOLD - Recommended):** Maintain strict offline boundary. Live container startup (`docker compose up`) and live HTTP scanning remain **STRICTLY PROHIBITED** until Decisions DEC-01 through DEC-07 are formally adjudicated.<br>**Option B (Authorized):** Grant formal approval to launch isolated containers on `127.0.0.1` and execute benchmark test scenarios under pre-registered safety permits. |
| **Relevant Evidence** | - `PROJECT_STATUS.md`<br>- `testbed/docker-compose.yml`<br>- `docs/SUPERVISOR_REVIEW_PACKAGE.md` (§ 6) |
| **Risks & Trade-offs** | - *Option A Benefit:* Prevents premature execution against unverified ground truth or misconfigured testbed versions.<br>- *Option B Risk:* Authorizes live container execution; must ensure host port bindings remain strictly on `127.0.0.1`. |
| **Decision Owner** | Thesis Supervisor |
| **Decision Status** | **`PENDING` (HOLD ENFORCED)** |
| **Decision Date** | *[Pending Formal Adjudication]* |
| **Supervisor Rationale & Notes** | *[To be completed upon formal supervisor review]* |
