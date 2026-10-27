# AEGISCORE AI — Verification and Evaluation Test Plan

**Status:** Phase 3 policy contracts, Phase 4B fake-only boundary, Phase 5B offline case/profile/data-binding tests, and Phase 6A read-only API tests have been executed. No vulnerability research test cases or experiment data have been created.  
**Review phase:** Phase 6A reproducible environment and minimal backend foundation; not proposal Month 2, lab setup, scanning, or dataset preparation.

## 1. Purpose and boundaries

This plan defines verification for the proposed requirements and architecture. Test identifiers are not vulnerability test cases, ground-truth labels, or experimental results. The Phase 3 tests in `tests/test_safety_policy.py` are unit tests of pure in-memory policy behavior only.

Testing must use schema/unit fixtures or an explicitly approved isolated local lab. No live third-party target, arbitrary Internet endpoint, destructive payload, credential theft, denial of service, data exfiltration, stealth, WAF evasion, or unrestricted shell/network capability is allowed. Do not prepare a vulnerability dataset or label cases under this phase.

## 2. Verification layers

| Layer | Scope | Future acceptance evidence | Current status |
|---|---|---|---|
| Documentation/design review | Requirement classification, component contracts, threat boundaries, decisions | Each REQ has a component and planned verification reference; conflicts/open choices are visible. | This documentation was reviewed; not an implementation validation. |
| Unit/contract | Typed inputs/outputs, policy decisions, operation permits, workflow dispatch gating | Deterministic tests for valid/invalid config, scope decisions, exact operation binding, one-time permits, terminal denial, budgets, stop, cancellation, expiry, and revocation state. | Phase 5B full run: 108 passed. Phase 6A full local-environment run: 113 passed. Pure in-memory/fake-only; no real transport. |
| Safety boundary | Target registry, allowlist, canonical operation, budgets, deadline, emergency stop, cancellation | In-memory policy and guarded seam deny malformed/out-of-scope or invalid permits before the injected transport is invoked; every fake invocation is recorded. | Tested using recording fake transport and explicit fixture limits. DNS/IP resolution, real authorization, network controls, response-size cap, and persistent audit are not implemented. |
| Agent boundary | Planner/mapping/specialist/reviewer output cannot grant permissions or directly call tools | Invalid/hostile output is rejected or remains advisory; executor requires a controller-created approval object. | Not run; no agents or graph exist. |
| RAG | Source ingestion, metadata, filtering, retrieval provenance, prompt-injection handling | Every returned chunk points to an approved source/version; retrieved text cannot alter policy or prove a finding. | Not run; no corpus or vector store configured. |
| Persistence/audit/secrets | Required event fields, redaction, persistence failure, provider modes | Required records persist; secret values never appear in logs/UI; audit failure stops execution; mock mode is explicit. | Not run; no application storage/provider exists. |
| API/UI contract | Frontend/backend schema, target ID only, auth, output encoding, cancellation | UI cannot submit arbitrary target URLs or secrets; access-control and rendering checks pass. | Phase 6A read-only API foundation tested in process (5 API tests). No Flutter UI, operational run/API routes, authentication, target registration, or cancellation API exists. |
| Local-lab integration | Approved Compose target and Executor network restriction | Only registered lab routes are reachable; no external egress; controller/executor failures fail closed. | Blocked: Docker is not found; lab setup is outside the current phase. |
| Research experiment | B1/B2/P and optional A1, ground-truth adjudication, repeats, metrics | Frozen protocol, comparable budgets, sealed labels, reproducible logs, independently checked calculations. | Not run; no case set, labels, or experiment exists. |

## 3. Planned software verification identifiers

These are future test purposes; no individual payloads or vulnerability cases are specified here.

| Test ID | Planned verification | Requirements | Safe test method / acceptance |
|---|---|---|---|
| T-SAFE-01 | Invalid/missing registry, policy, or safety config fails closed. | REQ-002, 004–006 | **Implemented and run (subset):** invalid registry/config constructors and missing/invalid engine config fail closed in in-memory tests. Persistent policy-store failure remains future work. |
| T-SAFE-02 | Target/endpoint and redirect validation reject unknown/out-of-scope destinations. | REQ-002, 005, 006 | **Implemented and run (subset):** exact target/path checks and same-origin redirect parsing; no resolver or transport. DNS pinning and actual network boundary remain untested. |
| T-SAFE-03 | Request budget and deadline cannot be exceeded; planner cannot raise limits. | REQ-005, 006, 008, 009 | **Implemented and run (subset):** locked in-memory request/redirect counters and fake monotonic clock, including concurrent budget checks. Planner integration remains future work. |
| T-SAFE-04 | Emergency stop and cancellation stop future dispatch and preserve partial state. | REQ-005, 006, 009, 015 | **Implemented and run (subset):** active/triggered emergency stop denies later decisions. Cancellation, in-flight transport, partial-state persistence remain future work. |
| T-SAFE-05 | Only controller-approved typed operations reach Executor; no shell or arbitrary HTTP path exists. | REQ-004–009 | **Implemented and run (subset):** Phase 3 decision/gate binds target/path; Phase 4B additionally validates an engine-issued one-time permit against the exact canonical read-only operation before the injected fake is called. No unrestricted HTTP or shell transport exists, and no real Executor exists to test capability isolation. |
| T-SAFE-06 | Target registration is tied to current, verifiable authorization; expired, revoked, missing, conflicting, or ambiguous evidence fails closed. | REQ-002, 005, 006, 017 | **Partial in-memory subset implemented and run:** registration version is required/validated and revoking a version invalidates an issued permit. No authorization evidence, expiry/ambiguity lifecycle, identity, or real record is verified. |
| T-SAFE-07 | DNS answers and actual connected peer remain within the exact approved lab-address set; redirects are resolved and revalidated per hop. | REQ-002, 005, 006 | Future resolver/socket adapter contract tests with injected A/AAAA sets, mixed/public/private/link-local/mapped-address results, rebinding, proxies, peer mismatch, and redirects. No DNS lookup or network request has been made. |
| T-SAFE-08 | Fake transport dispatch requires a fresh engine-issued permit bound to the exact operation, trusted case/profile policy, and registration/scope/data context. | REQ-004, 005, 008, 009 | **Implemented and run (in-memory only):** permit binds engine-derived run ID, target ID/registration version/origin, case/profile/version, scope policy/version, exact GET/HEAD method/path/query parameters/canonical headers/body bytes, data-limit version, budget slots/caps, and deadlines. Tests cover case/profile mismatch; altered target/path/method/parameters/headers/body/origin/permit versions; unregistered parameters/headers; malformed or oversized data; canonical serialization; allowed once; stale/cross-run; revoked; replayed; and model-shaped authority. Synthetic profile fixtures are not real authorization or approved research cases. |
| T-SAFE-09 | Denial is terminal; budget exhaustion, emergency stop, expiry, revocation, or cancellation prevents every subsequent fake dispatch. | REQ-004–006, 009, 015 | **Implemented and run:** tests assert no later fake invocation after target or case/profile denial, altered permit, request/redirect budget exhaustion, stop, cancellation, permit expiry, or revocation. A fake transport exception is terminal and is not retried. No in-flight network cancellation or persistent audit is tested. |
| T-SAFE-10 | Proposed operation deadlines, redirect/request caps, response-size cap, and concurrency cap are enforced at the transport boundary. | REQ-005, 006, 009, 017 | **Partial in-memory subset implemented and run:** explicitly configured fixture request/redirect caps and operation/run deadlines are bound and checked; boundary serializes fake calls (max active 1). Fixtures include 1 request, 1 redirect, 2/5-second operation and 10/30-second run values. These are test values, not approved deployment defaults. Proposed response-byte and connection limits are not implemented or tested. |
| T-AGENT-01 | Mapping output contains only bounded observations and marks newly seen endpoints unapproved. | REQ-007 | Synthetic page/route fixtures; assert no autonomous follow-up request. |
| T-AGENT-02 | Planner output is reviewable, typed, profile-bound, budget-checked, and non-authoritative. | REQ-008 | Schema fixtures; assert the plan cannot invoke the Executor. |
| T-AGENT-03 | Specialist output is a candidate with evidence requirements, not a confirmed finding. | REQ-011 | Mock provider fixture with explicit mock label; verify candidate status and schema validation. |
| T-AGENT-04 | False-positive reviewer reports counter-evidence/benign alternatives but cannot decide policy or execute. | REQ-013 | Synthetic finding fixture and capability checks. |
| T-WF-01 | Run and finding state transitions reject illegal transitions. | REQ-007, 008, 015 | State-machine contract tests; include denial, failure, cancellation, abstention, and terminal states. |
| T-WF-02 | Policy exception/low confidence routes to human review or abstention, never silent continuation. | REQ-014, 015 | Fixed score/evidence fixtures; no model-generated score accepted as sole confidence. |
| T-RAG-01 | Corpus ingestion/retrieval retains source, version/date, digest, corpus release, and chunk provenance. | REQ-010 | Curated synthetic/document fixtures; no web download. |
| T-RAG-02 | Retrieved prompt injection is treated as data; it cannot alter policy, target, or tool permissions. | REQ-004, 010 | Adversarial document fixture in an isolated LLM test harness; assert unchanged controller policy. |
| T-EVID-01 | Evidence checklist distinguishes pass, fail, incomplete, contradictory, and not-reproduced evidence. | REQ-012, 015 | Synthetic evidence records; evidence source IDs required for every claim. |
| T-EVID-02 | RAG similarity/self-reported confidence cannot make a finding `Verified`. | REQ-010, 012, 014 | Fixed retrieval/confidence values with missing checklist evidence; assert non-verified state. |
| T-UNC-01 | Composite score uses only frozen approved features and validation-selected calibration. | REQ-014, 020, 021 | Known-answer development/validation fixtures; verify versioned weights/threshold and final-test lock. |
| T-UNC-02 | Low-confidence or insufficient evidence yields bounded re-check, abstain, or human review. | REQ-014, 015 | Decision table fixtures; assert finite policy actions and no budget increase. |
| T-UNC-03 | Re-check counts/provider retries obey configured caps; unavailable provider never silently falls back to mock. | REQ-014, 024 | Inject timeouts/rate limits; verify explicit provider mode and audit outcomes. |
| T-REPORT-01 | Report quality flags missing evidence/source, duplicate, contradiction, or unsupported severity without confirming a finding. | REQ-016 | Synthetic report fixtures with expected flags. |
| T-AUDIT-01 | Allowed and blocked decisions, requests, evidence, cancellation, errors, and final state have linked audit records. | REQ-005, 009, 015, 017 | Persistence fixtures; assert run/policy/request/evidence IDs and timestamps. |
| T-AUDIT-02 | Audit-store failure prevents further execution; API keys and sensitive values are redacted. | REQ-017, 024 | Fault-injected store and sentinel secret strings; inspect stored and returned records. |
| T-API-01 | API accepts registered target IDs only and enforces auth, validation, cancellation, and safe error responses. | REQ-002, 023, 024 | **Phase 6A foundation subset implemented and run:** in-process app initialization, typed health/capabilities responses, exact capability inventory, safe 404/405 responses, and no call into policy or dispatch methods. No endpoint accepts target IDs or operations yet; authentication, authorization, request validation for future operational routes, and cancellation remain pending design and tests. |
| T-UI-01 | Flutter UI cannot hold provider secrets, render target HTML as active content, or bypass API policy. | REQ-023, 024 | Flutter tests/analyze, bundle scan, encoded-output fixtures, and API boundary review. |
| T-SECRET-01 | Provider secrets are backend-only, absent from bundle/logs, and real/mock modes are explicit. | REQ-024 | Secret sentinel and provider-mode tests; do not use a live key. |
| T-EVAL-01 | Final labels are partitioned/sealed and not available to runtime graph or RAG. | REQ-018, 021 | Access-boundary and manifest review using synthetic partitions; not a real dataset now. |
| T-EVAL-02 | TP/FP/FN/TN, abstention, duplicate mapping, Brier/ECE, and other metrics match hand calculations. | REQ-018, 020 | Small synthetic metric fixtures; test denominators and abstention handling. |
| T-EVAL-03 | B1/B2/P use same target/scope/comparable budgets; record ZAP limitations; A1 is optional. | REQ-019, 021, 022 | Frozen run matrix and config comparison; actual scanning only after separate authorization and isolated lab readiness. |
| T-EVAL-04 | Run reproducibility metadata includes model/provider/prompt/corpus/tool versions, timestamp, budget, and evidence references. | REQ-017, 021 | Manifest completeness check and replay metadata review; does not assert identical stochastic outputs. |
| T-INT-01 | Full path from API through controller and Executor reaches only an approved lab destination and stops on safety failure. | REQ-002, 005, 006, 009 | Future local integration in approved isolated Docker network only; currently blocked by Docker absence and not authorized. |
| T-OPTIONAL-01 | Optional remediation output is advice-only and cannot mutate source or deploy. | REQ-025 | Capability test with no write/deploy tool. Run only if feature is approved. |

## 4. Research evaluation checks (not prepared in this phase)

When separately approved and after a ground-truth protocol exists:

1. Freeze case IDs, class, source, labels, evidence criteria, duplicate mapping, and adjudication before runs.
2. Keep development/validation/final partitions separate; where possible, keep the same endpoint/vulnerability instance out of more than one partition.
3. Run B1 OWASP ZAP, B2 Multi-Agent+RAG without uncertainty abstention, and P on the same approved scope and comparable request/resource budget. A1 no-RAG is optional.
4. Repeat each case initially three times if feasible and preserve complete provenance. Do not invent substitute runs if a dependency is unavailable.
5. Compute proposal metrics and baseline differences; use paired comparison/bootstrap intervals where suitable. Track abstentions separately from TN.
6. Perform qualitative review of false positives, missed findings, incorrect confidence, and guardrail violations. Report sample size, calibration uncertainty, and limitations.

This list is an experimental protocol outline only. It does not create, select, label, or execute any vulnerability test case.

## 5. Test environment and execution gates

- Python: `.python-version` selects Python 3.13.2; `pyproject.toml` requires Python `>=3.13,<3.14`; `uv.lock` pins the dependency resolution. `uv sync --locked` creates/synchronizes the ignored project-local `.venv`. Phase 6A tests use only `.venv\Scripts\python.exe`; no global package is used by the test commands.
- FastAPI API tests use its synchronous in-process test client. Starlette 1.10.0 deprecates the older `httpx` client fallback and recommends `httpx2`; the locked dev dependency is httpx2 2.16.0. No listener or real target request is used.
- Flutter: run `flutter analyze` and `flutter test` after a Flutter project exists. Edge is present as a web device; Chrome is not.
- Docker: Compose checks and any target integration remain blocked until Docker/Compose and the daemon are available and an isolated network is approved.
- Gemini: use only explicit mock fixtures for unit tests. A real integration test requires an approved egress/data-handling decision, SDK/model selection, and credentials; never log the key.
- ZAP: no scan until its version/profile/budget is recorded and the lab is approved. Active scans can send attack-like traffic.
- Tests must be deterministic where possible, scoped to synthetic/in-memory fixtures unless a later phase explicitly authorizes the local lab, and must not use the public Internet.

## 6. Requirements traceability index

| Requirement IDs | Planned test IDs |
|---|---|
| REQ-001 | T-EVAL-01..04 |
| REQ-002..006 | T-SAFE-01..10; T-INT-01 |
| REQ-007 | T-AGENT-01; T-WF-01 |
| REQ-008 | T-AGENT-02; T-SAFE-03; T-WF-01 |
| REQ-009 | T-SAFE-03..05, T-SAFE-08..10; T-AUDIT-01; T-INT-01 |
| REQ-010 | T-RAG-01/02; T-EVID-02 |
| REQ-011..013 | T-AGENT-03/04; T-EVID-01 |
| REQ-014..015 | T-WF-02; T-EVID-01/02; T-UNC-01..03 |
| REQ-016 | T-REPORT-01 |
| REQ-017 | T-AUDIT-01/02; T-EVAL-04 |
| REQ-018..022 | T-EVAL-01..04 |
| REQ-023 | T-API-01; T-UI-01; T-INT-01 |
| REQ-024 | T-API-01; T-UI-01; T-SECRET-01; T-AUDIT-02; T-UNC-03 |
| REQ-025 | T-OPTIONAL-01 |
| REQ-026 | Phase/status documentation review; no runtime test |

## 7. Executed verification and boundaries

Commands run for Phase 5B (in the current Python environment):

| Command | Actual outcome |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider tests/test_safety_policy.py tests/test_guarded_execution.py` | Exit 0; 108 passed in 0.37s. |
| `python -B -m pytest -q -p no:cacheprovider` | Exit 0; 108 passed in 0.37s. |

These tests use in-memory synthetic registrations and case-profile policies, benign request data, a fake clock, and a recording fake transport. The configured test values are 2 parameters/128 query bytes/2 headers/128 serialized header bytes/16 body bytes; the implementation-level contract ceilings (32/4096/32/8192/65536) are not deployment values. Tests establish only the tested in-process call-gating and data-contract behavior. They do not establish authorization validity, DNS/address behavior, TLS/socket peer checks, firewall/container/egress isolation, provider handling, response-size or connect-timeout enforcement, persistent audit, or actual cancellation of an in-flight network operation. No vulnerability test case, lab request, Docker/ZAP operation, Gemini/embedding call, ground-truth preparation, or benchmark run occurred.

## 8. Phase 6A executed verification

The following commands were run after creating the locked project-local environment:

| Command | Actual outcome |
|---|---|
| `uv lock` | Exit 0; final lock resolution succeeded with 25 locked packages. |
| `uv sync --locked` | Exit 0; project-local `.venv` created/synchronized. uv reported a hardlink fallback and copied files instead; installation completed. |
| `uv lock --check` | Exit 0; lock remains consistent with `pyproject.toml`. |
| `uv pip check --python .\.venv\Scripts\python.exe` | Exit 0; checked 23 installed distributions, all compatible. |
| Project-local Python inventory script (`.venv\Scripts\python.exe -B -`) | Exit 0; Python 3.13.2, isolated `sys.prefix`, FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1, Uvicorn 0.54.0, pytest 8.4.2, httpx2 2.16.0. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_api.py` | Exit 0; 5 passed in 1.43s, no warnings after using httpx2. |
| `& .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | Exit 0; 113 passed in 1.79s. |

An earlier attempt to use the absent `pip` module inside uv's environment exited 1 (`No module named pip`); no package was added for that check. `uv pip check` was used instead. During dependency selection, an initial guessed `httpx2>=1,<2` constraint could not resolve because the index offered no versions in that range; the range was removed and the final lock selected 2.16.0. These checks establish dependency resolution and in-process tests only. No ASGI listening server, target HTTP request, DNS query, Docker process, scanner, vulnerability workflow, or provider call was started.

## 9. Next gated phase

Any future real transport or lab phase requires separate approval and must first resolve authorization evidence, network isolation, DNS/address pinning, provider egress, operational limits, audit persistence, and transport-specific response/deadline controls. Phase 6A does not authorize proposal Month 2, Docker/Juice Shop, scanning, research vulnerability-case creation, or ground-truth preparation. T-SAFE-07 and the remaining network/integration checks stay planned and unvalidated.
