# Normalization Fidelity Audit

**Scope:** all 11 local raw/normalized pairs in the source-review manifest. This is a technical review, not approval, source-authenticity verification, license advice, or a finding of semantic equivalence.

## Method and confirmed integrity

- Read the source manifest, corpus notes, normalizer, RAG/source-review contracts and tests, plus every raw and normalized artifact.
- Recomputed SHA-256 for all 11 raw and normalized artifacts; all match their manifest-recorded digests. This confirms byte agreement with the recorded local snapshot only. A digest is not a publisher signature and proves neither factual support nor license compliance.
- No raw publisher file was written during this audit. No network, DNS, target transport, Docker, scanner, external provider or LLM was used.

## Cross-cutting transformations

Markdown normalization removes leading bounded YAML front matter, fenced code, paired HTML script/style/pre/code blocks, comments, inline-code spans, link/image destinations (labels/alt text retained), reference-link definitions, template markup, remaining HTML tags, bold/italic markers, and whole lines matching a javascript-alert pattern. It normalizes line endings, HTML entities, horizontal whitespace and repeated blank lines. Headings/list markers/pipe table text often remain, but indentation and formatting are not guaranteed to preserve nesting or emphasis.

CWE normalization selects only Description, Common Consequences and Potential Mitigations. It omits all other page regions and suppresses script/style/pre/code/noscript/svg content. It emits text with new headings and whitespace separators; it does not retain DOM semantics, typed table cells/rows, list bullets/numbering, hyperlink destinations or offsets into raw HTML.

Each normalized file has a curator-added provenance preamble and repeated title. That preamble is not publisher content and does not replace the manifest/raw source.

## Per-artifact audit

### 1. The Web Security Testing Framework

- Source ID: src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c
- Pair: knowledge_base/raw/wstg-framework-v42.md → knowledge_base/normalized/wstg-framework-v42.normalized.md
- Observed transformation: Markdown: leading YAML front matter and one template directive removed; 3 link targets and 1 image target removed while link labels/image alt text remain. No fenced or inline code was detected. The 22 headings and 19 list markers remain. Whitespace and markup normalized.
- Fidelity risk/reviewer focus: Compare framework phases and figure context with raw; the image is unavailable in the extract, and link targets are needed to follow references.

### 2. 4.7 Input Validation Testing

- Source ID: src_404e2fae53fae835c0250989f23db5078219e3debeef51f5ab30475801a9b781
- Pair: knowledge_base/raw/wstg-input-validation-index-v42.md → knowledge_base/normalized/wstg-input-validation-index-v42.normalized.md
- Observed transformation: Markdown: leading YAML front matter and one template directive removed; 29 link targets removed while labels remain. No fenced/inline code detected. One heading and 10 list markers remain. This is an index.
- Fidelity risk/reviewer focus: Link destinations are important to identify the detailed procedures; labels alone do not preserve URLs/anchors. Detailed test pages were not acquired.

### 3. 4.5 Authorization Testing

- Source ID: src_0980c64a1c52686be37a3e0672b60142d283848765ad07fbfcae8739c9828129
- Pair: knowledge_base/raw/wstg-authorization-index-v42.md → knowledge_base/normalized/wstg-authorization-index-v42.normalized.md
- Observed transformation: Markdown: leading YAML front matter and one template directive removed; 4 link targets removed while labels remain. No fenced/inline code or list markers detected. One heading remains. This is an index.
- Fidelity risk/reviewer focus: Because the artifact is a short index, removed targets materially reduce traceability to detailed authorization procedures, which were not acquired.

### 4. V1 Encoding and Sanitization

- Source ID: src_01030961ca1b7253b828959b90fd51df6cf4d08c4c4882919de324995d2d5233
- Pair: knowledge_base/raw/asvs-v1-encoding-sanitization-v5.0.0.md → knowledge_base/normalized/asvs-v1-encoding-sanitization-v5.0.0.normalized.md
- Observed transformation: Markdown: 11 link targets removed. Eight headings, 11 list markers, and 40 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.
- Fidelity risk/reviewer focus: Verify requirement IDs, qualifiers and table row/cell associations; link labels do not retain the linked references or anchors.

### 5. V2 Validation and Business Logic

- Source ID: src_a2bda5d122243e3d1df846734d4be6f6f154d5a034192cad934198f80f40edf8
- Pair: knowledge_base/raw/asvs-v2-validation-business-logic-v5.0.0.md → knowledge_base/normalized/asvs-v2-validation-business-logic-v5.0.0.normalized.md
- Observed transformation: Markdown: 5 link targets removed. Seven headings, 12 list markers, and 21 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.
- Fidelity risk/reviewer focus: Verify requirement qualifiers and table row/cell associations; the partial chapter is context, not a runnable test case.

### 6. V8 Authorization

- Source ID: src_e97aa216e7ea78619706ded7f5780208c3a3b4b3ab7205f32ab3a922baa6f6a7
- Pair: knowledge_base/raw/asvs-v8-authorization-v5.0.0.md → knowledge_base/normalized/asvs-v8-authorization-v5.0.0.normalized.md
- Observed transformation: Markdown: 2 link targets removed. Seven headings, 4 list markers, and 21 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.
- Fidelity risk/reviewer focus: Verify operation-level authorization qualifiers and table row/cell associations; this is one chapter, not the complete standard.

### 7. Cross Site Scripting Prevention Cheat Sheet

- Source ID: src_f2d13cd05b0ee74cab83d8bc5d7f129f62130f89eebc61fcf3bb6b45b7f71b6d
- Pair: knowledge_base/raw/owasp-xss-prevention-cheat-sheet-2026-10-26.md → knowledge_base/normalized/owasp-xss-prevention-cheat-sheet.normalized.md
- Observed transformation: Markdown: 12 fenced code blocks (31 body lines) and 148 inline-code spans removed; 25 link targets removed; 1 whole line matching the javascript-alert pattern removed. Heading count remains 29; list-marker count changes from 24 to 23. The removed whole line may include surrounding explanation.
- Fidelity risk/reviewer focus: Code/context examples can qualify distinctions among output contexts and advice. Compare claims, exceptions and the removed line with raw; do not infer semantic equivalence from the retained prose.

### 8. SQL Injection Prevention Cheat Sheet

- Source ID: src_ad783cf5bb36c72296a15e4d984f9a0a2a82159e32b8e6a2dfada47990ef8c2e
- Pair: knowledge_base/raw/owasp-sql-injection-prevention-cheat-sheet-2026-10-26.md → knowledge_base/normalized/owasp-sql-injection-prevention-cheat-sheet.normalized.md
- Observed transformation: Markdown: 1 fenced code block (4 body lines) and 11 inline-code spans removed; 16 link targets removed. Fifteen headings and 3 list markers remain. Whitespace and formatting normalized.
- Fidelity risk/reviewer focus: Removed snippets and inline identifiers may distinguish recommended parameterization from discouraged escaping and carry qualifications; compare surrounding prose with raw.

### 9. CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')

- Source ID: src_76c3386ec7c60647970655d9695471d4578a98a6a0333947e2882c1ee5782b77
- Pair: knowledge_base/raw/mitre-cwe-79-v4.20.html → knowledge_base/normalized/mitre-cwe-79-v4.20.normalized.md
- Observed transformation: HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections are omitted, including examples and (where present) relationships, introduction, platform, detection and reference material. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 25 tables, 261 rows, 633 cells, 20 list tags and 200 links; counts include omitted sections. No pre/code tags detected.
- Fidelity risk/reviewer focus: Compare definition, consequence and mitigation text with raw. Omitted page sections and flattened enumerations/tables may change context or associations.

### 10. CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')

- Source ID: src_69c5561cee1655943440109db5893afea85031a3ec93edfb36fe1769a7f918d6
- Pair: knowledge_base/raw/mitre-cwe-89-v4.20.html → knowledge_base/normalized/mitre-cwe-89-v4.20.normalized.md
- Observed transformation: HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections, including examples and (where present) relationships, introduction, platform, likelihood, detection and references, are omitted. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 26 tables, 260 rows, 623 cells, 37 list tags and 180 links; counts include omitted sections. Entry-specific revision date is unknown.
- Fidelity risk/reviewer focus: Compare selected text and table/list associations with raw, and assess whether omitted likelihood/examples/references are material. Do not infer a revision date from other CWE pages.

### 11. CWE-862: Missing Authorization

- Source ID: src_25e8aeffe0ca973600cfe7dfe90d05bfa96faa626baf4d51a855432ad4f7db0b
- Pair: knowledge_base/raw/mitre-cwe-862-v4.20.html → knowledge_base/normalized/mitre-cwe-862-v4.20.normalized.md
- Observed transformation: HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections are omitted, including examples and (where present) relationships, introduction, platform, detection and references. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 25 tables, 172 rows, 406 cells, 26 list tags and 170 links; counts include omitted sections. No pre/code tags detected.
- Fidelity risk/reviewer focus: Compare definition and mitigation text and table/list associations with raw. CWE categorization alone does not prove that a particular application has an authorization defect.

## Provenance and chunk traceability

The manifest records source ID, title, publisher, acquisition/canonical locators and date, available version/revision/date, license statement/reference, raw and normalized paths/hashes, intended use, limitations and tags. The normalized preamble repeats some of these values. Current local RAG chunks carry normalized-source metadata, normalized-content hash, chunk ID/order, character offsets into the normalized artifact, and a section label inferred from normalized headings.

Chunk offsets are not raw publisher byte/line offsets. Chunk metadata does not itself carry the manifest repository revision, raw digest, license fields or publisher page anchor. Mapping a chunk to the original therefore depends on the manifest plus raw artifact. No source-level page/section correspondence was validated.

## Approval safeguard review

The manifest currently records 11 candidate entries, zero review events per entry, corpus approval status no_sources_approved, and retrieval excluded until explicit approval. The existing SourceReviewRegistry is in memory. It requires candidate registration, explicit submission, and then a decision against the exact current source revision; approval also requires attribution/locator metadata and all checklist and review-note fields. approved_chunks() selects only current registry-approved revisions.

This is not an authenticated or persistent human-review system. Submitter and reviewer references are caller-provided labels, not authenticated identities, and the manifest is not wired into the API/runtime. Generating worksheets does not submit, approve or reject a source. No source authority, license, authenticity or factual support was verified.

## Audit conclusion

The normalized extracts are lossy candidate text, not proven equivalent to their publisher files. Higher-risk losses include context examples in the OWASP cheat sheets; link targets across Markdown; most CWE page sections; and structure in CWE lists/tables. A human must compare each normalized claim and qualification with its raw pair before deciding whether a revision is appropriate for the thesis. No review decision is made here.
