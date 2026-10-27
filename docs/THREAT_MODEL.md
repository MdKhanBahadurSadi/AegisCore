# AEGISCORE AI — Threat Model

**Status:** Proposed threat model. `aegiscore/safety.py` and `aegiscore/guarded_execution.py` implement in-memory policy and fake-only dispatch-gating subsets covered by unit tests; authorization verification, real transport, and network isolation remain unverified.  
**Scope:** Authorized isolated local web-application assessment, selected XSS/SQLi/Broken Access Control cases, and the proposed RAG/multi-agent workflow.

## 1. Security goals

1. Requests reach only explicitly registered and authorized local lab targets and endpoints.
2. Deterministic controls, not LLM judgment, enforce scope, request limits, timeouts, redirects, cancellation, and emergency stop.
3. The Executor cannot access arbitrary network destinations or shell commands.
4. Findings require evidence; insufficient or conflicting evidence produces bounded re-check, abstention, or human review.
5. Secrets, real credentials, personal data, and held-out labels do not leak to the browser, logs, RAG corpus, or an unapproved external provider.
6. Run actions and decisions remain auditable and experimental data remain reproducible.

### Phase 3, Phase 4B and Phase 5B evidence boundary

Phase 3 tests cover in-memory target/scope/path/redirect decisions, budget/deadline state, and an emergency-stop latch. Phase 4B added an engine-issued, one-use permit and recording fake boundary. Phase 5B binds the canonical operation to an exact configured target/case/profile tuple, engine-derived run ID, target-registration version and origin, method/path/query parameters, normalized headers, exact optional body bytes, scope/profile/data-limit versions, budgets and deadlines. Request data is checked against explicit trusted-profile allowlists and versioned size bounds. Synthetic fixture registrations and case profiles are not real authorization or approved experimental cases. Retrieved documents and model output remain untrusted and cannot issue or override a policy decision.

Tests assert zero fake attempts on denied, malformed, altered, stale, revoked, replayed, stopped, cancelled, expired, or budget-exhausted operations, including data and case/profile mismatches. Revocation and expiry remain in-memory state checks. The code does not resolve DNS, verify authorization evidence, open sockets, enforce host/container/firewall boundaries, persist audit events, or implement a real transport. Public DNS resolution, DNS rebinding, proxy routing, race-free connect pinning, real response/deadline controls, and actual egress restriction remain residual risks. Passing tests support only the software behavior represented by those in-memory fixtures.

## 2. Assets and trust boundaries

| Asset | Security property |
|---|---|
| Target registry and policy | Integrity; only explicit authorized local targets and constraints are active. |
| Lab target and synthetic records | Availability and integrity; remain isolated from host/Internet and unrelated services. |
| Request budget, deadline, and stop state | Integrity; cannot be increased or disabled by an agent. |
| API key/provider configuration | Confidentiality; backend-only and redacted from logs/UI. |
| Observations, responses, evidence, findings | Confidentiality, provenance, integrity, and correct attribution to run/target. |
| RAG source corpus and metadata | Integrity/provenance; content is untrusted data, not executable instruction. |
| Ground-truth and partition labels | Confidentiality/integrity; final labels stay unavailable to runtime agents. |
| Audit records and experiment configuration | Integrity and traceability; capture blocked as well as allowed actions. |
| Human review decisions | Authenticity and accountability; reviewer identity/authorization model remains unresolved. |

### Trust boundaries

- **Browser ↔ API:** user input and rendered output are untrusted; no API key or direct target access in the browser.
- **API/orchestrator ↔ LLM provider:** external service boundary if Gemini is enabled. Only a provider adapter may hold credentials and send minimized, synthetic observations.
- **Orchestrator ↔ deterministic controller:** LLM suggestions are untrusted data. Only a typed request can be evaluated; policy output is authoritative.
- **Controller/Executor ↔ target network:** highest-risk boundary. Revalidate destination and budget at dispatch; enforce an independent network egress rule.
- **RAG corpus ↔ agent prompts:** retrieved text may contain prompt injection or false guidance. Delimit as quoted context and never grant it authority.
- **Runtime ↔ evaluator:** ground-truth labels are sealed from runtime agents and RAG; evaluator joins labels only after outputs are fixed.
- **Host/container boundary:** future Compose isolation is a proposed control only. No Docker installation or container configuration has been checked in this phase.

## 3. Threats, mitigations, residual risk, and planned verification

| ID | Threat / failure mode | Proposed controls | Residual risk / planned verification |
|---|---|---|---|
| THR-01 | LLM proposes an arbitrary URL, endpoint, method, or action outside scope. | Run input uses registered `target_id`; planner cannot authorize; deterministic allowlist, operation permit, and budget checks precede fake dispatch; no unrestricted HTTP or shell tool exists. | No real transport exists. A policy/adapter defect could pass an unsafe operation later. T-SAFE-01..05 and T-SAFE-08..10 cover only in-memory/fake behavior. |
| THR-02 | Redirect, DNS rebinding, IPv4/IPv6 alias, proxy, or address parsing bypass reaches a non-lab host. | Disable automatic redirects; resolve and validate the complete A/AAAA set; canonicalize mapped addresses; pin the selected validated address to the socket; check peer address before sending data; preserve TLS hostname checks; independently restrict egress to the registered lab network. | None of these controls is implemented or network-tested. DNS/connect race, proxy, routing, and host-network flaws remain. T-SAFE-07 and T-INT-01. |
| THR-03 | Invalid/missing policy is interpreted permissively. | Fail closed on absent/invalid config, registry, budget, policy service, or audit persistence. | Fail-closed behavior may reduce availability; configuration and recovery tests required. T-SAFE-01/T-AUDIT-01. |
| THR-04 | LLM/retrieved document/tool output contains prompt injection or false instructions. | Mark all such content untrusted; no tools from prompt text; use typed output validation; deterministic controller remains sole policy authority; RAG is not proof. | Prompt injection may bias analysis even without direct tool access. Adversarial fixture tests T-RAG-02/T-AGENT-03. |
| THR-05 | Unsafe or repetitive requests damage the lab or consume excessive resources. | Restrict profiles and request types; deterministic per-run/case budget and deadline; no DoS/destructive tests; stop and cancellation; no automatic Executor retry. Numeric limits unresolved. | A permitted “non-destructive” case may still have side effects. Case-level review and sandbox monitoring required. T-SAFE-03..05. |
| THR-06 | Gemini/provider call leaks credentials, personal data, or sensitive response content. | Backend-only secret; provider adapter only; minimize/redact; synthetic data; no secrets in logs or frontend; provider egress and processing approval required. | Remote provider retention/processing, network endpoint, and egress exception are unresolved. T-SECRET-01; provider use gated on ARCH-OPEN-01/04. |
| THR-07 | RAG source poisoning, stale docs, or incorrect provenance affects findings. | Curated/versioned corpus; source IDs, dates, digest, and corpus release; ingestion separated from runs; retrieved content not treated as proof. | Curator error/licensing/version mismatch; retrieval may still bias reasoning. Provenance tests T-RAG-01. |
| THR-08 | False-positive or unsupported vulnerability is reported as verified. | Predefined evidence checklist; independent false-positive review; report-quality flags; deterministic uncertainty/abstention gate; evidence citations. | Checklist/ground truth may be wrong, and LLM reviewers may share biases. Validate against frozen labeled cases later. T-EVID-01/02, T-UNC-01..03, T-REPORT-01. |
| THR-09 | Validation/final-test leakage inflates measured performance or calibration. | Seal final labels from runtime agents/RAG; separate partitions; freeze score/threshold before test; evaluator-only join after output is fixed. | Small dataset or duplicate endpoint leakage may remain. Protocol review T-EVAL-01/02. |
| THR-10 | Browser/API misuse, CSRF, unauthorized run/cancel/review, or unsafe target registration. | API accepts IDs not arbitrary URLs; bind locally by default as a proposed deployment posture; authorize target registration and human actions; strict schema and output encoding. | Authentication, CORS/CSRF, local binding, and role model are unresolved; no exposed deployment until specified. T-API-01/T-UI-01. |
| THR-11 | Lab container reaches host, Docker socket, other containers, or public Internet. | Future lab network should be isolated, non-privileged, without host mounts/Docker socket, and egress-denied except the lab path. | These controls are not configured or verified; Docker is unavailable in the inspected environment. T-INT-01 is blocked pending approved setup. |
| THR-12 | API key, target data, or raw responses appear in logs, UI, exports, or source control. | Central redaction; synthetic data; no client secrets; secret scanning; data minimization and access controls. | SQLite/audit retention and response redaction are undecided; log integrity is not guaranteed. T-SECRET-01/T-AUDIT-02. |
| THR-13 | Audit DB is unavailable or altered, hiding unsafe actions. | Stop execution if audit writes fail; include policy/request/evidence references and timestamps; restrict DB write access. | SQLite alone is mutable; tamper-evident storage, backup, and retention are unresolved. T-AUDIT-01/02. |
| THR-14 | Runtime/cost exhaustion from agent loops or provider retries. | Graph step limits, request budgets, deadline, cancellation, provider-call accounting, bounded retries. | Numeric graph/provider limits and retry/backoff are unresolved. T-SAFE-03/T-UNC-03. |
| THR-15 | XSS-like content in target output is rendered unsafely in the Flutter UI. | Treat response/report content as text; escape/encode output; avoid executing remote HTML; restrict Markdown/HTML rendering. | UI renderer and sanitization library are not selected. T-UI-01. |
| THR-16 | ZAP baseline produces higher-impact traffic than expected. | Use only isolated authorized target, recorded configuration, conservative approved budget, and emergency stop; report its Broken Access Control limitations. | Exact ZAP version/profile and safe cap unresolved; no ZAP scan has run. T-EVAL-03 is gated on lab approval. |
| THR-17 | Target is registered using an unverifiable, expired, revoked, ambiguous, or fabricated authorization reference. | Bind a versioned target ID and exact scope to controlled written authorization from an identified lab owner/custodian and supervisor-approved scope; check status/expiry at run start and before dispatch; fail closed on missing, stale, conflicting, unverifiable, or revoked records. | No authority, real authorization record, authentication, revocation source, or verification procedure is configured. Current string fields and synthetic unit-test references prove nothing. T-SAFE-06. |
| THR-18 | A model, planner, replayed result, or workflow step forges or reuses an allow decision for a different operation, case/profile, or request-data value. | The fake-only guarded boundary requires a one-use engine-issued permit bound to the trusted run, target registration/version/origin, scope version, exact target/case/profile binding, canonical method/path/query/header/body data, data-policy version, budgets, and deadlines. Denial is terminal; model-shaped objects cannot issue authority. | Tested in-process with synthetic policy fixtures only. It does not authenticate real authorization or protect against arbitrary code in the trusted Python process; it is not cryptographic/cross-process authority and does not authorize a real transport. T-SAFE-08/09. |
| THR-19 | Slow, oversized, concurrent, or repeated responses exhaust memory, runtime, or the local lab. | Proposed, unapproved defaults: 50 requests/run, 3 redirects/chain and 10/run, 2-second connection, 10-second operation, 300-second run, 1 MiB response, one concurrent operation. Fake boundary tests use smaller explicit fixture request/redirect/deadline limits and serialize calls. | Proposed values are not deployment values. Response-byte and connection limits are not implemented; fixture checks do not validate real timing, in-flight cancellation, or network behavior. T-SAFE-03/10. |
| THR-20 | Provider/embedding connection leaks observations or bypasses default-deny egress. | Maintain default-deny; no live call before supervisor-approved provider/data/network decision. If approved, isolate a provider-only gateway from Executor, minimize synthetic/redacted data, keep credentials server-side, and verify Executor egress remains denied. | No provider or embedding egress exception is approved. Provider retention, endpoint/address policy, and gateway design are unresolved. T-SECRET-01/T-INT-01. |

## 4. Explicit prohibited actions

The architecture must not enable unauthorized scanning, unrestricted target discovery, shell execution, destructive payloads, denial of service, credential theft, secret collection, data exfiltration, stealth, WAF evasion, unrestricted exploit chaining, or automatic production remediation. A refusal/deny is recorded; the LLM cannot override it.

## 5. Important conflicts and residual risks

- **External model vs default-deny egress:** Gemini is a working project choice, while the current execution posture is default-deny. No separated, explicitly allowlisted provider path is approved or validated. Preserve the deny rule until the decision gate in ADR 0002 is satisfied; do not call Gemini.
- **External embeddings:** provider is unresolved and may create the same egress/data exposure issue.
- **Authorization evidence:** a proposed owner/supervisor authorization lifecycle is documented in `docs/ARCHITECTURE.md`, but actual registration authority, identity, evidence verification, expiry and revocation mechanisms are not approved or implemented. No target authorization has been verified.
- **Isolation is not proven:** no Docker command is available, and no firewall/container network exists to inspect.
- **Model and evidence limits:** prompt injection can still distort analysis; weak checklists or noisy labels can create false decisions; small test sets yield uncertain calibration.
- **Audit and privacy:** data retention, raw response handling, integrity protection, and external provider processing remain open.
- **Availability:** fail-closed behavior, provider outage, or audit-store failure may stop a run; this is an accepted design consequence, not yet operationally tested.

## 6. Security verification linkage

See `docs/TEST_PLAN.md` for `T-SAFE-*`, `T-RAG-*`, `T-EVID-*`, `T-UNC-*`, `T-API-*`, `T-AUDIT-*`, `T-INT-*`, and `T-SECRET-*`. Phase 3/4B/5B in-memory subsets of T-SAFE-01..06 and T-SAFE-08..10 have been exercised; T-SAFE-07, real authorization lifecycle, production transport, and all network mitigations remain unimplemented or unvalidated. Test success does not establish that these threats are mitigated in a running assessment system.
