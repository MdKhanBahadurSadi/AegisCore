# AEGISCORE AI — Phase 7C Candidate Knowledge Corpus

**Status:** 11 official-source artifacts were acquired on 2026-10-27 and recorded as `candidate`. No source has been submitted for human review or approved. The repository manifest is [source-review-manifest.json](source-review-manifest.json).

This is a bounded offline reference set for the selected XSS, SQL injection, and broken-access-control research scope. It is not ground truth, a test-case collection, an authorization record, or proof that a finding is correct. Source SHA-256 values identify the local acquired snapshot and detect later file changes; they do not authenticate a publisher or verify a digital signature.

## Acquired sources

| Source family | Acquired material | Version or immutable revision | Publisher and terms |
|---|---|---|---|
| OWASP WSTG | Framework chapter; input-validation index; authorization index | Stable WSTG v4.2 content under repository commit `f93fdf06416517f4fb3e70f6e3ded7c892ff79d8` (commit date 2026-10-23) | OWASP Foundation; CC BY-SA 4.0. The [official WSTG project page](https://owasp.org/projects/web-security-testing-guide) identifies v4.2 as the stable version and states its license. |
| OWASP ASVS | V1 Encoding and Sanitization; V2 Validation and Business Logic; V8 Authorization | ASVS 5.0.0, pinned to commit `5cf9b032440be53ce345ab3c130fda46ba1ce7a2` | OWASP Foundation; CC BY-SA 4.0. See the [official ASVS releases](https://github.com/OWASP/ASVS/releases). |
| OWASP Cheat Sheet Series | XSS Prevention Cheat Sheet; SQL Injection Prevention Cheat Sheet | Repository snapshot `9d41c054686e35fb56070b4b6271ae2829edea6a`, commit date 2026-10-26; no numbered release is claimed | OWASP Cheat Sheet Series; CC BY-SA 4.0 according to the [official project page](https://owasp.org/projects/cheat-sheet-series). The repository says its Markdown files are working sources; the manifest points to the published HTML pages for canonical citation. |
| MITRE CWE | CWE-79, CWE-89, CWE-862 pages | CWE 4.20 as shown by the entries. The CWE-79 and CWE-862 pages show 2026-04-30; the captured CWE-89 entry does not show a separate update date, which remains unknown. | MITRE CWE Terms of Use apply. The [terms](https://cwe.mitre.org/about/termsofuse.html) describe use rights and attribution conditions. The retained normalized extracts include MITRE's displayed copyright notice. |

The exact acquisition URL, canonical reference, publisher, version/revision, acquisition date, local raw and normalized paths, SHA-256 hashes, license reference, intended use, limitations, and topical tags are recorded per entry in the manifest. Missing publication dates and other metadata remain `null`; repository snapshot dates are not represented as publication dates.

## Local artifacts and normalization

Publisher-returned files are stored under `knowledge_base/raw/`. Retrieval-ready *candidate* text is kept separately under `knowledge_base/normalized/`. `scripts/normalize_security_corpus.py` is a standard-library-only offline transformation utility; it reads only explicitly listed manifest entries and verifies the raw hash before writing normalized text and its hash. It makes no network, DNS, target-transport, provider, or approval calls.

- Markdown normalization removes WSTG front matter/template directives, fenced and inline code, HTML code blocks, comments, link destinations, remaining markup, and whole lines containing a `javascript:alert(` executable example while retaining headings and other prose. Link labels stay in the text; the exact source/canonical links remain in the manifest and provenance preamble.
- CWE normalization extracts only `Description`, `Common Consequences`, and `Potential Mitigations`; it excludes demonstrative/observed examples, platform and reference sections, and `pre`/`code` content.
- Each normalized file begins with curator provenance, license/terms, review state, intended use, and limitations. The preamble is metadata added by this project, not publisher text.
- These transformations are lossy. Review the normalized file against its paired raw source before using any claim. The originals may contain publisher-authored illustrative examples; no payload was created or executed, and normalized files omit code blocks, inline-code content, and the noted executable inline example line.

Stable source IDs in the manifest are derived by the current local ingestion contract from each normalized relative path. Chunk IDs are derived from the normalized content hash and the existing deterministic chunking configuration. Re-ingestion of the same bytes/configuration is tested for stable IDs. A changed source revision must be re-registered in the in-memory review workflow; persistence across process restarts is not implemented.

## Review and retrieval status

All 11 records have `review_state: candidate`, `review_events: []`, and `retrieval_eligibility: excluded_until_explicit_approval`. The corpus-level `approval_status` is `no_sources_approved`. The Phase 7C tests exercise source registration as a candidate through `SourceReviewRegistry` and confirm that `approved_chunks()` remains empty. This is a test of the in-memory contract, not a persisted source-review event or a real reviewer action.

No publisher/license audit, source-by-source human review, source authority assessment, factual-support verification, or corpus release was completed. The registry remains in-memory; the manifest is a handoff record and is not loaded by the API or automatically wired into retrieval. `InMemoryTestRetriever` remains a lexical test double, and no semantic/vector retriever exists. Candidate references cannot be used as factual proof, and the corpus is not automatically trustworthy.

## Scope not acquired

The WSTG items are a framework chapter and topic indexes only. Detailed XSS, SQL injection, and authorization test-procedure pages were not acquired in this phase. No lab observations, synthetic fixture text, test payload collection, ground-truth labels, or third-party references were added to the corpus. The selected ASVS chapters and CWE entries are partial extracts of much larger standards/taxonomies, not complete copies.

No Docker, Juice Shop, ZAP, scanner, target, LLM, embedding service, ChromaDB, LangGraph, or external application runtime integration was used. Default-deny provider egress and all existing safety-policy/guarded-execution behavior are unchanged.

## Phase 7D human-review preparation

The [human review packet](SOURCE_REVIEW_PACKET.md) contains 11 indexed worksheets with manifest-derived source identity, available revision/acquisition metadata, raw/normalized paths and hashes, intended use, recorded limitations, transformation-loss notes, reviewer questions, and license/attribution unknowns. The [normalization fidelity audit](NORMALIZATION_FIDELITY_AUDIT.md) records the observed losses and provenance limits for each pair.

Packet generation is documentation preparation only. All entries remain `candidate`, have no review events, and remain excluded until explicit approval. Every decision, reviewer, timestamp, rationale, and corroboration field is unset. No source was approved or rejected, no publisher/license/authenticity/factual-support attestation was completed, and no raw or normalized publisher artifact was modified. Manifest digest matches establish local byte agreement with the recorded snapshot only.

The in-memory review registry still requires explicit submission and a decision for the exact current revision before selecting approved chunks. It does not authenticate reviewer references, persist decisions, or load the manifest into the API/runtime. The generated worksheets do not satisfy or bypass that gate.
