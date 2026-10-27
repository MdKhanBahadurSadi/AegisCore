# ADR 0002: Proposed local-lab safety policy and provider-egress gate

- **Status:** Proposed for supervisor review; operational values and external-egress choice are not approved. Immediate posture remains deny-by-default for outbound provider/embedding traffic.
- **Date:** 2026-10-27
- **Decision owners:** Supervisor/project owner approval required; actual approver and target-registration authority are not identified in the repository.
- **Related:** [Requirements](../REQUIREMENTS.md), [Architecture](../ARCHITECTURE.md), [Threat model](../THREAT_MODEL.md), [Test plan](../TEST_PLAN.md), [ADR 0001](0001-technology-decisions.md).

## Context

Phase 3 introduced a deterministic, in-memory policy model. It validates a registered target ID, exact configured scheme/hostname/port/path, same-origin permitted redirect, request and aggregate redirect counters, run deadline, and emergency stop. Phase 4B adds an in-process, one-use permit bound to a run, target registration version, policy version, exact canonical read-only operation, reserved budget slots, and deadlines, plus a guarded boundary whose injected transport is exercised only with a recording fake. Phase 5B adds offline case/profile and request-data binding to that permit. These additions do not authenticate a target registrant, verify `authorization_ref`, establish real authorization expiry/revocation, resolve DNS, pin a destination address, inspect the connected peer, enforce a network boundary, or provide a production HTTP transport or persistent audit.

The proposal requires a controlled local lab and safety controls but does not supply numeric request, deadline, byte, or concurrency values. The project design has a default-deny outbound-network posture. The Master Prompt Pack selects Gemini API as a working project technology, but a Gemini or external embedding call requires egress and transfers data across an external-service boundary. These constraints cannot be reconciled by silently adding an exception.

No real target authorization record, authorized person, provider approval, DNS configuration, network isolation, or deployment limit has been supplied or verified. The synthetic reference `approval-record-1` in `tests/test_safety_policy.py` is fixture data only.

## Proposal (pending approval)

### Target registration and authorization evidence

1. The lab owner/custodian should request or create a target registration; the project supervisor should approve the research scope or explicitly delegate that authority. Which people/roles may register or revoke targets, how identity is authenticated, and who independently verifies the source record require supervisor decision.
2. Each enabled registration should bind an immutable registration version and unique `target_id` to a controlled written authorization record. Its scope should specify the authorizing party and date, exact target/lab identity and network zone, origin/address, allowed paths and methods or approved test profiles, permitted period, and constraints. The registry should reference the record and retain integrity metadata. Evidence format, record location, integrity mechanism, and retention are unresolved.
3. Run input and model output may select a registered ID but must never establish authorization by supplying a URL or reference string. Check registry/record status at run start and before every operation. Expired, revoked, missing, conflicting, ambiguous, unverifiable, stale, or unavailable authorization state—and an untrusted/unavailable clock—must deny new work. Revocation cancels future permits; an already in-flight operation must be cancelled where possible and audited.
4. No record is created or verified by this ADR. Until a real, supervisor-approved registration and verification process exists, the current fields in the in-memory model are placeholders and cannot authorize a real target.

### Discussion defaults for a controlled local experiment

These values are engineering proposals, not thesis-specified requirements, approved deployment values, or empirically validated limits.

| Control | Proposed default | Reasoning and accounting |
|---|---:|---|
| Maximum requests per run | 50 | Bounds local traffic; all redirect hops and retries consume this shared total. Baseline runs use the same cap. |
| Redirects per request chain | 3 | Bounds one redirect chain. Also cap the aggregate run at 10 redirects so many short chains cannot multiply traffic. Automatic redirect following stays disabled. |
| Connection deadline | 2 seconds | Bounds DNS/connect/TLS establishment time for the local service; future transport must define which phases are included precisely. |
| Total operation deadline | 10 seconds | Wall-clock deadline for connect through bounded response read; no extension for a retry or redirect. |
| Total run deadline | 300 seconds | Ends new dispatches after a bounded run window; in-flight cancellation is best-effort and separately capped by the operation deadline. |
| Maximum response bytes | 1 MiB / 1,048,576 bytes per operation | Count HTTP status, headers, framing, and body after TLS; also cap the decoded entity at 1 MiB to prevent compressed expansion. A truncated response is explicitly incomplete. |
| Maximum concurrent operations | 1 | Serializes local work for simpler emergency-stop, budget, and evidence accounting. |

Proposed values are intentionally conservative for a small lab, but that rationale is not evidence of safety or adequacy. Supervisor review and validation against the eventual frozen case protocol are required. A trusted, versioned policy snapshot should be loaded once per run. Run requests and LLM output cannot raise a cap. Configuration may lower the proposed ceiling; raising any cap requires an approved policy revision, risk review, and fresh boundary tests. Missing, invalid, stale, or contradictory policy must deny execution rather than substitute a permissive default. Phase 4B implements an in-process operation permit and fake-only dispatch gate. No real transport enforces the proposed connection, response-size, or per-chain redirect limits; the in-memory redirect counter is aggregate for the run, and the proposed concurrency default is not a deployment configuration.

### DNS and destination enforcement

Matching a registered hostname/origin does not prove the socket destination. DNS answers can point outside the lab or change between validation and connect; mixed A/AAAA answers, IPv4-mapped IPv6, aliases, proxy variables, resolver changes, routing, and host/container bridges can defeat name-only checks. Private IP classification is also insufficient: an RFC1918 address may identify an unrelated service.

The intended future policy is a positive allowlist of exact service addresses/ports on a dedicated local lab network. Loopback is allowed only for an explicitly registered loopback service. Deny public, metadata, link-local, multicast, unspecified, and unregistered addresses. A future transport must resolve A and AAAA using a defined resolver, canonicalize all answers, fail closed on any disallowed or ambiguous result, pin the chosen validated address to the socket without a second DNS lookup, and check the actual connected peer before sending application data. Preserve the registered hostname for TLS SNI/certificate checks. Disable automatic redirects; resolve and revalidate every redirect destination/path/address and consume request/redirect budget per hop. Disable ambient proxies unless a separately approved proxy is itself constrained. Independently enforce host/container/firewall egress so application policy is not the sole isolation control. This ADR does not implement resolution or make network requests. Address ranges, resolver, TLS behavior, proxy policy, and isolation mechanism remain open.

### External LLM and embedding egress

**No egress exception is approved.** Preserve default-deny for the execution environment and do not call Gemini or an external embedding provider until an explicit decision is recorded.

- **Local model/provider path:** best fits the current no-egress posture and minimizes data transfer; requires hardware/runtime feasibility, model and embedding version pinning, license review, quality evaluation, and reproducibility work.
- **Restricted remote provider path:** may improve availability or capability but adds external data processing, retention, credentials, service availability, cost, DNS, and network risks. It requires explicit supervisor approval of provider/model and data classes; minimal synthetic or redacted inputs; server-side secret storage; and a separate provider-only gateway/process with strict destination/egress controls, quotas, redacted audit, and tests proving the assessment Executor still has no provider or general Internet route.

The decision record must specify the selected path, provider/model versions if remote, allowed data, credential lifecycle, network topology, data-handling review, and acceptance evidence. If approval is absent, no live provider is used. A test/demo mock must be explicitly labeled and must never be presented as a real assessment result. Embedding egress follows the same decision.

## Phase 4B and Phase 5B fake-transport implementation record

The fake-only integration is implemented in `aegiscore/guarded_execution.py`; engine-issued operation-permit types and validation are in `aegiscore/safety.py`. Phase 5B adds typed `CaseProfilePolicy` and `OperationDataLimits` contracts. An operation must match one configured exact target/case/profile binding with allowed GET/HEAD method, path, query-parameter names, header names, and body-presence policy. The engine derives execution-run ID, registration version, and canonical origin from trusted in-memory registration data; user/model intent cannot supply an authorizing URL or origin. Query values use stable ordering and percent-encoding, header names are lowercased and sorted with ambiguous/forbidden forms rejected, and an optional immutable byte body is bound exactly.

The one-time permit is bound to the full canonical operation, target registration version, scope policy ID/version, case-profile version, operation-data-limit version, request/redirect budget slots and caps, and operation/run deadlines. It is rejected when stale, modified, replayed, revoked in the in-memory registry state, or used after terminal denial, stop, or cancellation. Missing operation-contract configuration fails closed. The method set remains GET/HEAD; no mutating method was introduced. Synthetic tests use explicit data limits of 2 parameters, 128 query bytes, 2 headers, 128 serialized header bytes, and 16 body bytes. The implementation also rejects configurations above its bounded in-memory contract ceilings: 32 parameters, 4096 query bytes, 32 headers, 8192 serialized header bytes, and 65536 body bytes. These are implementation limits only, not proposal requirements or approved deployment values. Case/profile fixtures are not actual test cases, ground truth, or proof of authorization.

This is an in-process capability boundary, not a cryptographic token or security boundary against arbitrary code running in the same trusted process. Tests use only a recording fake. They do not establish authorization evidence, real transport correctness, DNS, TLS, socket peer, firewall, container, provider egress, persistent audit, response-size limits, connection timeout, or real in-flight network cancellation. No deployment safety decision is resolved by these test results.

## Consequences and status

- Until supervisor review, the registration lifecycle and numeric values above remain proposals; do not label them resolved or validated.
- Default-deny provider egress remains in force. The local-versus-restricted-remote provider choice remains unresolved; no provider/network exception is made.
- Phase 4B fake-only operation-permit integration and Phase 5B offline case/profile/data-binding hardening are implemented and their tests pass as recorded in `docs/TEST_PLAN.md`; this ADR does not authorize subsequent engineering phases. Any future real transport/lab phase remains separate and is not proposal Month 2 approval.
- No supervisor decision changed: proposed deployment numeric limits and authorization lifecycle remain pending; default-deny provider/embedding egress remains in effect; DNS and network isolation remain unimplemented. Phase 5B adds only in-memory code and fake-transport tests, with no network configuration, authorization record, provider call, lab operation, research case, or experiment.
