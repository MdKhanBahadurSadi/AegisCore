# TASK 06.6 — Advisory Reviewer Evaluation & Reliability Hardening

## Outcome

**PASS for offline advisory reliability hardening.** The opt-in reviewer now enforces bounded output size, stricter evidence references, explicit uncertainty, modal risk language, and a local elapsed-time deadline check. API tests show that reviewer failures preserve deterministic findings and the assessment terminal state. This is a fixture result only; it is not a measurement of real model quality or calibration.

Live model providers remain disabled. TASK 06.4.4 Linux egress verification remains deferred. No Gemini, new agent, assessment-scope change, or dependency was added.

## Evaluation methodology

The existing evaluation harness scores fixture-driven vulnerability predictions from the offline FSM against adjudicated vulnerability labels. Its inputs and outcome schema do not match this reviewer, which comments on passive HTTP-header findings and does not issue vulnerability predictions. Forcing the harness into this workflow would produce misleading metrics, so evaluation uses small deterministic response fixtures against the actual `PassiveAssessmentAIReviewer` and API route.

Each fixture is replayable through the offline fake adapter. Cases cover valid references, fabricated finding IDs, fabricated evidence IDs, evidence belonging to another finding, unsupported vulnerability claims, absent uncertainty language, schema violations, abstention, provider errors, timeout, malformed JSON, oversized raw and structured output, and repeated failures. No external provider is contacted.

## Hardening changes

- The reviewer caps raw and serialized structured output at 16,384 characters. Each generated text field is limited to 600 characters; review count and reference arrays are bounded.
- Output remains strict-schema only. Unexpected fields, including proposed severity or terminal-state fields, invalidate the entire advisory response.
- A review must reference an existing deterministic finding and only the evidence IDs retained for that finding. The reviewer constructs fresh prompt objects and does not pass mutable official finding records to the adapter.
- Risk text must contain modal/inferential language and rejects explicit unsupported conclusions and vulnerability classes unrelated to the header finding. The uncertainty text must contain an explicit limitation marker; contradictory phrases such as “no uncertainty” are rejected. Recommendations are checked for unsupported vulnerability claims too.
- Accepted advisory text is passed through the existing secret redactor. Provider error messages and raw responses are not included in sanitized failure metadata or logged by the assessment route.
- The request timeout is still capped at two seconds. The reviewer now measures elapsed adapter-call time locally and rejects results returned after the configured deadline. A request that times out or fails maps to a bounded advisory failure code.
- The reviewer stays opt-in. AI failure does not change official finding rows, severity, or terminal status. Deterministic persistence remains authoritative.

## Fixture metrics

| Metric | Fixture result | Interpretation |
|---|---:|---|
| Valid evidence-reference acceptance | 1/1 (100%) | Known finding and its attached evidence accepted. |
| Invalid-reference rejection | 3/3 (100%) | Unknown finding, unknown evidence, and cross-finding evidence reference rejected. |
| Unsupported or unqualified claim rejection | 2/2 (100%) | Direct vulnerability assertion and missing uncertainty rejected. Additional claim variants are covered by focused parameterized tests. |
| Insufficient-evidence abstention | 1/1 (100%) | Failed observation abstains without calling the adapter. |
| Valid output-schema acceptance | 1/1 (100%) | The valid fixture satisfies the complete required schema. |
| Invalid output-schema rejection | 2/2 (100%) | Missing fields and unexpected fields are rejected. |
| API failure isolation | 4/4 (100%) | Timeout, unexpected adapter exception, invalid claim, and oversized response leave the assessment completed with unchanged deterministic findings. |
| Repeated provider failure isolation | 5/5 (100%) | Five repeated timeout failures return the same bounded unavailable result without leaking the provider message. |

These are deterministic fixture pass rates, not estimates of production model accuracy, factual entailment, or calibration. The fixtures are intentionally narrow and do not establish that lexical claim checks catch every misleading sentence.

## Adversarial and security results

- Prompt-injection text in allowlisted header values and finding descriptions remains data in the user prompt. The system instruction independently labels both as untrusted and forbids policy changes or new findings.
- Fabricated finding IDs, fabricated evidence IDs, and evidence attached to a different finding fail closed with `invalid_output`.
- Direct claims such as confirmed XSS or SQL injection, assertive claims without modal language, missing uncertainty, severity/status fields, and unexpected review fields are rejected.
- Malformed JSON, missing schema fields, raw responses above the cap, and oversized structured responses fail safely.
- API failure-path tests assert four deterministic findings retain their original rule IDs, severities, classification, and detected status while assessment status remains completed. AI commentary is never merged into official findings.
- Provider error text is absent from API output and captured logs. Reviewer failure records include only bounded status codes.
- AI remains disabled unless an adapter is explicitly injected. Live provider mode remains blocked before adapter invocation.

## Test results

Final runs:

| Run | Collected | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|---:|
| `python -m pytest tests/test_assessment_ai_integration.py --durations=0 -q` | 40 | 40 | 0 | 0 | 4.67 s |
| `python -m pytest --durations=0 -q` | 840 | 840 | 0 | 0 | 42.55 s |

An earlier focused run found four failures (31 passed, 4 failed; 5.37 s): the explicit-uncertainty matcher did not recognize the existing “does not show … or prove” fixture phrasing, and the first insufficiency metric incorrectly expected a provider abstention to happen without invocation. The matcher was corrected to recognize bounded non-assertive limitation phrasing, and the metric now models insufficient evidence before provider invocation. The focused and full suites were rerun after the fixes and pass with the counts above.

## Duration and timeout limits

The deterministic fixture adapter reports a one-millisecond synthetic duration; the reviewer now reports its measured local adapter-call duration instead of trusting that adapter field. A focused test uses a 10 ms configured timeout and a 20 ms delayed fake adapter; the late result is rejected as `timeout`. Default request timeout passed to an injected adapter is capped at 2.0 seconds.

The model-adapter interface is synchronous. The post-call deadline check prevents acceptance of a late result but cannot forcibly interrupt an adapter that blocks forever; any future provider adapter must enforce its own transport timeout and return control. No live-provider deadline or provider-generated quality result is claimed.

## Known limitations

- Lexical checks reduce obvious unsupported claims, but cannot prove semantic grounding. Reference membership proves that an ID exists, not that a sentence is factually entailed by the observation.
- Confidence remains uncalibrated and factual support remains `not_evaluated`.
- There is no live provider, global provider rate limiter, or provider-level cancellation contract. Live access remains unauthorized.
- Linux/container egress isolation was not tested or changed; TASK 06.4.4 remains deferred.
- The offline specialist/RAG/FSM evaluation suite remains separate because its source-code vulnerability prediction contract does not fit passive header advisory review.

## Recommended next milestone

Before enabling any provider, define an adapter contract with enforceable transport deadlines, cancellation, bounded retries/rate limits, and sanitized observability. Then expand a reviewed header-observation fixture set with human-adjudicated expected advisory/abstention outcomes. Keep the real provider disabled until both provider authorization and deployment egress controls are verified.

## Repository safety and status

The initial worktree was already dirty. Initial `git status --short` contained **88 entries: 35 deletions, 12 modifications, and 41 untracked paths**. It included the user’s existing deletions and modifications under `.idea/`, `aegiscore/api/`, `aegiscore/local_persistence.py`, `aegiscore/orchestration.py`, multiple documentation paths, tests, and `uv.lock`; numerous PDFs, copied code, deployment assets, task reports, Python modules, and tests were already untracked.

Final `git status --short` contains **89 entries: 35 deletions, 12 modifications, and 42 untracked paths**. The only status-inventory addition is `?? docs/TASK_06_6_ADVISORY_REVIEWER_EVALUATION.md`. `aegiscore/assessment_ai.py` and `tests/test_assessment_ai_integration.py` were already untracked at task start; this task edited their contents without staging them.

Task-specific file changes:

| File | Status at task start | Task 06.6 change |
|---|---|---|
| `aegiscore/assessment_ai.py` | Pre-existing untracked | Added response bounds, claim/uncertainty checks, secret redaction on output, and measured elapsed-time rejection. |
| `tests/test_assessment_ai_integration.py` | Pre-existing untracked | Added adversarial, repeated-failure, timeout, API isolation, and reproducible fixture-metric coverage. |
| `docs/TASK_06_6_ADVISORY_REVIEWER_EVALUATION.md` | Not present | Created this report. |

`uv.lock` remains pre-existing modified state and was not edited. Flutter files were not touched. `git diff --check` exited successfully; Git printed only existing LF-to-CRLF working-copy warnings for previously modified tracked files. A separate whitespace scan of the two edited untracked files and this report found no trailing whitespace. Nothing was staged or committed, and no destructive Git command was run. Byte-for-byte preservation is not claimed.
