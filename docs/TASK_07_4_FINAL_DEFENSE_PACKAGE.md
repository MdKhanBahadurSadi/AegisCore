# TASK 07.4 — Final Defense Package

**Source of truth:** `docs/AEGISCORE_THESIS_FINAL.md`<br>
**Timing assumption:** 10 minutes of speaking time; confirm the department's actual limit.<br>
**Demonstration mode:** prepared fixture/test evidence only. No live target or provider demonstration is claimed.

## 1. Defense narrative

1. Broad AI-assisted penetration testing was the project context, but the integrated route that can be evaluated is narrower.
2. AEGISCORE binds an assessment to a registered numeric-loopback endpoint and makes one bounded passive HTTP `HEAD` request.
3. Deterministic rules produce five security-header configuration observations for the selected synthetic response, linked to evidence identifiers.
4. An optional advisory reviewer is constrained and non-authoritative; it cannot create official findings or change severity or lifecycle state.
5. Lease checks and transactions protect tested persistence and recovery paths.
6. The recorded evidence establishes repeatability and selected invariants for fixtures. It does not establish real-world accuracy, live model quality, authority acceptance, or deployment security.

## 2. Timed presentation outline

| Time | Running total | Slide | Content and evidence |
|---:|---:|---|---|
| 0:25 | 0:25 | 1. Title and scope | Present the approved title with confirmed student/programme fields. Frame AEGISCORE as a bounded passive-assessment prototype. |
| 0:50 | 1:15 | 2. Problem and motivation | Explain the need to control both the request made and the claim recorded. Introduce evidence-linked findings and target authorization as boundaries. |
| 0:50 | 2:05 | 3. Questions and contribution | State RQ1–RQ4. Contribution is an implementation and fixture-based evaluation of the integrated workflow, not a novel detector or comparative-superiority claim. |
| 1:10 | 3:15 | 4. Implemented architecture | Show Flutter → authenticated FastAPI → registered target/verifier interface → guarded `HEAD` → normalized evidence/detector → optional advisory → SQLite. Show the offline FSM/RAG subsystem separately. |
| 1:00 | 4:15 | 5. Method | Describe the synthetic HTTPS observation, 100 repeated calls, scripted reviewer adapter, controlled local transports, and temporary SQLite. State the methods do not use a live target or model provider. |
| 1:15 | 5:30 | 6. Main fixture results | Present one normalized finding set across 100 calls, five findings per call, and 500/500 finding/evidence identifier-membership checks. Say this is repeatability on one input, not detection accuracy. |
| 1:00 | 6:30 | 7. Regression evidence | Give the historical Python result (863 passed, 0 failed, 0 skipped) and Flutter result (59 passed, 1 skipped, 0 failed). Mark both as historical; include reviewer fixture denominators only as selected test cases. |
| 1:15 | 7:45 | 8. Safety and lifecycle | Explain numeric loopback, exact endpoint binding, peer check, no redirects/body read, verifier contract, advisory separation, leases, and transactional writes. Distinguish application checks from OS-level egress isolation. |
| 1:00 | 8:45 | 9. Limitations | State no real-world accuracy dataset, no live provider samples, no trusted production verifier, no authenticated browser-to-live acceptance, no accepted persistent deployment configuration, and no Debian 13 egress or filesystem-permission verification. |
| 1:15 | 10:00 | 10. Conclusion and next work | Summarize the controlled-fixture conclusion. List the next evidence: official template, final publisher metadata, genuine authority/deployment configuration, browser acceptance, OS controls, and independently adjudicated data if accuracy is to be studied. |

**Total: exactly 10:00.** If the department gives a different time limit, reallocate the durations while preserving the same claims and limitations.

## 3. Prepared demonstration plan

Use one prepared output excerpt from the historical TASK 06.9 fixture run, or show the relevant output already embedded in the thesis. Label it **synthetic fixture / historical test evidence**. Explain that the 100 calls use one fixed input and that the 500/500 value is identifier membership only. The separate six-test fixture selection recorded in TASK 06.9 was 6 passed in 3.56 seconds; it used test authentication, an injected synthetic verifier, controlled or fake transport, a fake reviewer, and temporary SQLite.

Do not call this an interactive browser session, an authorized live assessment, a real-world benchmark, or a live AI demonstration. Do not show credentials, signing keys, private target data, or fabricated authorization artifacts.

## 4. Examiner questions and evidence-based answers

### What is the thesis contribution?

The work documents and evaluates a narrow integration: exact registered numeric-loopback binding, one passive `HEAD` request, deterministic header-configuration observations with evidence identifiers, optional separate advisory output, and lease-checked SQLite lifecycle behavior. It does not claim a novel detector, global novelty, or better detection than existing tools.

### Does 100 repeated runs mean 100 independent successful assessments?

No. It is one synthetic HTTPS observation passed to the deterministic detector 100 times. It demonstrates repeatability for that input, not coverage, independent targets, or accuracy.

### What does 500/500 prove?

The 500 generated finding/evidence links in the fixture matched the supplied identifiers under the membership check. The links are repeated references from one fixture. They do not establish 500 independent cases, semantic entailment, or that the finding text is factually correct.

### Did the advisory AI improve detection?

That was not measured. The evaluation used a scripted fake adapter, not a live Gemini or other provider. The reviewer is advisory and cannot create official findings, change severity, or alter lifecycle state.

### What does the advisory test matrix establish?

It shows that selected constructed responses passed or failed the implemented schema, identifier/reference, claim-check, abstention, and failure-isolation rules. The denominators are small by design. They are not model accuracy, a rejection rate for a population, semantic proof, or calibrated confidence.

### How is target authorization established?

The application binds an assessment to a registered endpoint and checks a verifier response contract. Tests inject synthetic verifiers and cover selected denial cases. A trusted production issuer/verifier, real key lifecycle, and live approval source were not configured, so no production-authorized target run is claimed.

### Why is execution limited to a loopback `HEAD` request?

That is the implemented and evaluated safety scope: one exact registered endpoint, one bounded passive request, selected headers, no redirect following, and no response-body read. Active scanning or expansion to other targets would require separate authorization, threat analysis, and evaluation.

### Do the 863 passing Python tests prove that the product is secure?

No. The 863 passed, zero failed, zero skipped result is a historical regression run. It supports the tested code paths and cases; it is not a formal proof, a security probability, or evidence of production firewall behavior. The historical Flutter run recorded 59 passed and one skipped.

### Why does the thesis cite PentestEval as an arXiv paper?

The versioned arXiv record was verifiable, and author-maintained pages report acceptance by IEEE Transactions on Information Forensics and Security. The official publisher bibliographic record could not be verified for this audit. The thesis therefore avoids an unverified publisher DOI and final volume/page data until that record is confirmed.

### Why does the ACL reference use “Xuefeng Du” when the landing page says “Sean Du”?

The published ACL proceedings PDF title page lists Xuefeng Du, while the ACL landing metadata lists Sean Du. The citation follows the published PDF as the authoritative author source for this manuscript, and the discrepancy is disclosed in the academic audit. No correction to the ACL metadata is claimed.

### Is the thesis administratively ready because supervisor approval was received?

Supervisor approval of the thesis work has been communicated, but it does not establish university formatting compliance or administrative submission completion. The official undergraduate CSE template, required declaration/certification, submission/binding instructions, and other applicable administrative items still need confirmation.

### What is needed before making detection-accuracy claims?

A permissioned, versioned set of representative HTTP-header observations with independently adjudicated labels, a frozen evaluation protocol, and per-rule results with uncertainty estimates. The single synthetic fixture is not sufficient for such a claim.

## 5. Defense consistency checklist

- [ ] Use the final thesis title and confirm every personal/programme field.
- [ ] Keep the result figures exactly as reported in the thesis and label them historical.
- [ ] Call the 100-call run a repeated single-fixture experiment.
- [ ] Explain that 500/500 is identifier membership, not semantic entailment.
- [ ] Say the reviewer used scripted fake responses; no live model was evaluated.
- [ ] Distinguish user authentication from target-owner authorization.
- [ ] Distinguish application loopback checks from Debian OS-level egress isolation.
- [ ] Keep the offline FSM/RAG subsystem separate from the passive API route.
- [ ] Do not imply production authorization, browser-to-live acceptance, persistent deployment acceptance, or a live target demo.
- [ ] Match all claims to `AEGISCORE_THESIS_FINAL.md`; update the thesis first if a defense claim changes.
