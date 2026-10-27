# Candidate Security Corpus — Human Review Packet

**State:** prepared for human review only. All 11 entries remain candidate and retrieval-excluded. No review was submitted; no source was approved or rejected.

**Packet preparation date:** 2026-10-27. This is not a human review timestamp.

See [Normalization Fidelity Audit](NORMALIZATION_FIDELITY_AUDIT.md) for methods, per-artifact losses, provenance limits and approval-gate findings. Values below are reproduced from the local manifest and are not independently verified.

## Index

| # | Source ID | Exact title | State |
|---:|---|---|---|
| 1 | src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c | The Web Security Testing Framework | candidate |
| 2 | src_404e2fae53fae835c0250989f23db5078219e3debeef51f5ab30475801a9b781 | 4.7 Input Validation Testing | candidate |
| 3 | src_0980c64a1c52686be37a3e0672b60142d283848765ad07fbfcae8739c9828129 | 4.5 Authorization Testing | candidate |
| 4 | src_01030961ca1b7253b828959b90fd51df6cf4d08c4c4882919de324995d2d5233 | V1 Encoding and Sanitization | candidate |
| 5 | src_a2bda5d122243e3d1df846734d4be6f6f154d5a034192cad934198f80f40edf8 | V2 Validation and Business Logic | candidate |
| 6 | src_e97aa216e7ea78619706ded7f5780208c3a3b4b3ab7205f32ab3a922baa6f6a7 | V8 Authorization | candidate |
| 7 | src_f2d13cd05b0ee74cab83d8bc5d7f129f62130f89eebc61fcf3bb6b45b7f71b6d | Cross Site Scripting Prevention Cheat Sheet | candidate |
| 8 | src_ad783cf5bb36c72296a15e4d984f9a0a2a82159e32b8e6a2dfada47990ef8c2e | SQL Injection Prevention Cheat Sheet | candidate |
| 9 | src_76c3386ec7c60647970655d9695471d4578a98a6a0333947e2882c1ee5782b77 | CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting') | candidate |
| 10 | src_69c5561cee1655943440109db5893afea85031a3ec93edfb36fe1769a7f918d6 | CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection') | candidate |
| 11 | src_25e8aeffe0ca973600cfe7dfe90d05bfa96faa626baf4d51a855432ad4f7db0b | CWE-862: Missing Authorization | candidate |

## Worksheet instructions

Compare each normalized file to its retained raw pair. Assess attribution, source revision, transformations, intended use, limitations, license terms and corroboration. Hashes identify recorded local bytes only. Leave every review field unset until a human makes and records a decision.

## Worksheets

### Worksheet 1

#### The Web Security Testing Framework

- Source ID: src_845d5fcb98a43072a4d842894eeeee34530aa88200b2c16e9694b14d65bf733c
- Exact artifact title: The Web Security Testing Framework
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: WSTG v4.2
- Repository revision: f93fdf06416517f4fb3e70f6e3ded7c892ff79d8
- Revision date: 2026-10-23
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://owasp.org/www-project-web-security-testing-guide/v42/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework
- Acquisition locator: https://raw.githubusercontent.com/OWASP/www-project-web-security-testing-guide/f93fdf06416517f4fb3e70f6e3ded7c892ff79d8/v42/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: framework, research-governance
- Raw-file path: knowledge_base/raw/wstg-framework-v42.md
- Raw-file SHA-256: af2473ec4db060b121a89f83650f0bc929d811639e20ce20b6ec12834a9834f6
- Normalized-file path: knowledge_base/normalized/wstg-framework-v42.normalized.md
- Normalized-file SHA-256: 5e9b57aff29c43e0ea494195299f3ae77f6ddf86805e72cde1cdb4b431b4f30f
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate background on OWASP's general web-security testing framework for the thesis workflow.
- Known limitations recorded in manifest:
  - This is one framework chapter, not a complete WSTG corpus or an authorization to test any target.
  - The versioned v4.2 content is pinned to the recorded repository snapshot.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: leading YAML front matter and one template directive removed; 3 link targets and 1 image target removed while link labels/image alt text remain. No fenced or inline code was detected. The 22 headings and 19 list markers remain. Whitespace and markup normalized.

**Potential interpretive effect for human assessment:** Compare framework phases and figure context with raw; the image is unavailable in the extract, and link targets are needed to follow references.

**Reviewer questions:**
- [ ] Does the chapter support the intended thesis use without implying a target authorization or detailed procedure?
- [ ] Does the removed diagram or its context affect interpretation?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 2

#### 4.7 Input Validation Testing

- Source ID: src_404e2fae53fae835c0250989f23db5078219e3debeef51f5ab30475801a9b781
- Exact artifact title: 4.7 Input Validation Testing
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: WSTG v4.2
- Repository revision: f93fdf06416517f4fb3e70f6e3ded7c892ff79d8
- Revision date: 2026-10-23
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/07-Input_Validation_Testing/
- Acquisition locator: https://raw.githubusercontent.com/OWASP/www-project-web-security-testing-guide/f93fdf06416517f4fb3e70f6e3ded7c892ff79d8/v42/4-Web_Application_Security_Testing/07-Input_Validation_Testing/README.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: xss, sql-injection, input-validation
- Raw-file path: knowledge_base/raw/wstg-input-validation-index-v42.md
- Raw-file SHA-256: ba6d1b788806c6ace8af09316b4a8edb764713897e3ff6b1ce5b4874fcb56918
- Normalized-file path: knowledge_base/normalized/wstg-input-validation-index-v42.normalized.md
- Normalized-file SHA-256: 920ec784426822a640605545f08348edf316ee5f3d7e3e1bb7a38cb60fc2624a
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate index of the WSTG input-validation testing topic relevant to selected XSS and SQL injection research scope.
- Known limitations recorded in manifest:
  - This is an index page only; detailed test procedures were not acquired in this phase.
  - An index is not a test case, payload, target authorization, or proof of a vulnerability.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: leading YAML front matter and one template directive removed; 29 link targets removed while labels remain. No fenced/inline code detected. One heading and 10 list markers remain. This is an index.

**Potential interpretive effect for human assessment:** Link destinations are important to identify the detailed procedures; labels alone do not preserve URLs/anchors. Detailed test pages were not acquired.

**Reviewer questions:**
- [ ] Do retained labels identify the intended procedures after link targets were removed?
- [ ] Are the missing detailed procedure pages an acceptable limitation?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 3

#### 4.5 Authorization Testing

- Source ID: src_0980c64a1c52686be37a3e0672b60142d283848765ad07fbfcae8739c9828129
- Exact artifact title: 4.5 Authorization Testing
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: WSTG v4.2
- Repository revision: f93fdf06416517f4fb3e70f6e3ded7c892ff79d8
- Revision date: 2026-10-23
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/05-Authorization_Testing/
- Acquisition locator: https://raw.githubusercontent.com/OWASP/www-project-web-security-testing-guide/f93fdf06416517f4fb3e70f6e3ded7c892ff79d8/v42/4-Web_Application_Security_Testing/05-Authorization_Testing/README.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: broken-access-control, authorization
- Raw-file path: knowledge_base/raw/wstg-authorization-index-v42.md
- Raw-file SHA-256: 1fe27e118da076ddd2741e0921fd028640f4c9fbab7969fd2f145fee84cfab7c
- Normalized-file path: knowledge_base/normalized/wstg-authorization-index-v42.normalized.md
- Normalized-file SHA-256: 1d044102704499ab123cf8f6ef65bf3ee27670729fa6780c7978789da59e6a9e
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate index of the WSTG authorization-testing topic relevant to the selected broken-access-control research scope.
- Known limitations recorded in manifest:
  - This is an index page only; detailed test procedures were not acquired in this phase.
  - An index is not a test case, authorization record, or proof of a vulnerability.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: leading YAML front matter and one template directive removed; 4 link targets removed while labels remain. No fenced/inline code or list markers detected. One heading remains. This is an index.

**Potential interpretive effect for human assessment:** Because the artifact is a short index, removed targets materially reduce traceability to detailed authorization procedures, which were not acquired.

**Reviewer questions:**
- [ ] Do retained labels identify the intended authorization pages after link targets were removed?
- [ ] Are missing detailed procedures an acceptable limitation?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 4

#### V1 Encoding and Sanitization

- Source ID: src_01030961ca1b7253b828959b90fd51df6cf4d08c4c4882919de324995d2d5233
- Exact artifact title: V1 Encoding and Sanitization
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: OWASP ASVS 5.0.0
- Repository revision: 5cf9b032440be53ce345ab3c130fda46ba1ce7a2
- Revision date: Unknown (not recorded in manifest)
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://github.com/OWASP/ASVS/blob/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x10-V1-Encoding-and-Sanitization.md
- Acquisition locator: https://raw.githubusercontent.com/OWASP/ASVS/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x10-V1-Encoding-and-Sanitization.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: xss, encoding, sanitization
- Raw-file path: knowledge_base/raw/asvs-v1-encoding-sanitization-v5.0.0.md
- Raw-file SHA-256: 8c0e36a42c3cbf711e2579eb68e1fea8090f52301cac7c400d7c392207b24ee7
- Normalized-file path: knowledge_base/normalized/asvs-v1-encoding-sanitization-v5.0.0.normalized.md
- Normalized-file SHA-256: a42a911b2048101d1969c3747eb06753444616e6bc7dc9779cc575ac07768ec4
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate verification requirements for encoding and sanitization concepts related to the selected XSS scope.
- Known limitations recorded in manifest:
  - This is one ASVS chapter, not the complete verification standard or a runnable test case.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.
  - ASVS verification requirements do not authorize testing a target or establish that an application is vulnerable.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: 11 link targets removed. Eight headings, 11 list markers, and 40 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.

**Potential interpretive effect for human assessment:** Verify requirement IDs, qualifiers and table row/cell associations; link labels do not retain the linked references or anchors.

**Reviewer questions:**
- [ ] Do requirement IDs, table associations, and qualifiers remain unambiguous?
- [ ] Are linked reference targets required for interpretation?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 5

#### V2 Validation and Business Logic

- Source ID: src_a2bda5d122243e3d1df846734d4be6f6f154d5a034192cad934198f80f40edf8
- Exact artifact title: V2 Validation and Business Logic
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: OWASP ASVS 5.0.0
- Repository revision: 5cf9b032440be53ce345ab3c130fda46ba1ce7a2
- Revision date: Unknown (not recorded in manifest)
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://github.com/OWASP/ASVS/blob/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x11-V2-Validation-and-Business-Logic.md
- Acquisition locator: https://raw.githubusercontent.com/OWASP/ASVS/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x11-V2-Validation-and-Business-Logic.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: input-validation, business-logic
- Raw-file path: knowledge_base/raw/asvs-v2-validation-business-logic-v5.0.0.md
- Raw-file SHA-256: 70ad0f68df22ddd825c2837e74999fa026851e75a3128372307685e2bb526969
- Normalized-file path: knowledge_base/normalized/asvs-v2-validation-business-logic-v5.0.0.normalized.md
- Normalized-file SHA-256: 3789106de83537d6ba16be267bf54c47496c586abcf9d11f2d03dfb60040d2bc
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate verification requirements for input validation and business logic context relevant to the thesis scope.
- Known limitations recorded in manifest:
  - This is one ASVS chapter, not the complete verification standard or a runnable test case.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.
  - ASVS verification requirements do not authorize testing a target or establish that an application is vulnerable.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: 5 link targets removed. Seven headings, 12 list markers, and 21 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.

**Potential interpretive effect for human assessment:** Verify requirement qualifiers and table row/cell associations; the partial chapter is context, not a runnable test case.

**Reviewer questions:**
- [ ] Do table associations and validation/business-logic qualifiers remain unambiguous?
- [ ] Are the omitted chapter references necessary?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 6

#### V8 Authorization

- Source ID: src_e97aa216e7ea78619706ded7f5780208c3a3b4b3ab7205f32ab3a922baa6f6a7
- Exact artifact title: V8 Authorization
- Publisher as recorded: OWASP Foundation (not independently authenticated)
- Version: OWASP ASVS 5.0.0
- Repository revision: 5cf9b032440be53ce345ab3c130fda46ba1ce7a2
- Revision date: Unknown (not recorded in manifest)
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://github.com/OWASP/ASVS/blob/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x17-V8-Authorization.md
- Acquisition locator: https://raw.githubusercontent.com/OWASP/ASVS/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en/0x17-V8-Authorization.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: broken-access-control, authorization
- Raw-file path: knowledge_base/raw/asvs-v8-authorization-v5.0.0.md
- Raw-file SHA-256: 60c188b1703cab2086841d8f1b4adc0ededf66ed38c676a11bb92347646b5330
- Normalized-file path: knowledge_base/normalized/asvs-v8-authorization-v5.0.0.normalized.md
- Normalized-file SHA-256: 99b5234b4540da3fdaa433a47975d5c5e79cada7dd626913710430e338dbfbf0
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- License/terms reference as recorded: https://creativecommons.org/licenses/by-sa/4.0/
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate verification requirements for authorization concepts relevant to broken access control.
- Known limitations recorded in manifest:
  - This is one ASVS chapter, not the complete verification standard or a runnable test case.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.
  - ASVS verification requirements do not authorize testing a target or establish that an application is vulnerable.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: 2 link targets removed. Seven headings, 4 list markers, and 21 pipe/table-like lines remain. No fenced/inline code detected. Emphasis/HTML formatting and redundant whitespace normalized.

**Potential interpretive effect for human assessment:** Verify operation-level authorization qualifiers and table row/cell associations; this is one chapter, not the complete standard.

**Reviewer questions:**
- [ ] Do table associations and authorization qualifiers remain unambiguous?
- [ ] Does the intended use avoid treating requirements as proof of a finding?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 7

#### Cross Site Scripting Prevention Cheat Sheet

- Source ID: src_f2d13cd05b0ee74cab83d8bc5d7f129f62130f89eebc61fcf3bb6b45b7f71b6d
- Exact artifact title: Cross Site Scripting Prevention Cheat Sheet
- Publisher as recorded: OWASP Cheat Sheet Series (not independently authenticated)
- Version: Unknown (not recorded in manifest)
- Repository revision: 9d41c054686e35fb56070b4b6271ae2829edea6a
- Revision date: 2026-10-26
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- Acquisition locator: https://raw.githubusercontent.com/OWASP/CheatSheetSeries/9d41c054686e35fb56070b4b6271ae2829edea6a/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: xss, prevention
- Raw-file path: knowledge_base/raw/owasp-xss-prevention-cheat-sheet-2026-10-26.md
- Raw-file SHA-256: 199c484557a3d2e6732daec1d2b8d683645163ce1d7dd58f7e5590d93f5a2719
- Normalized-file path: knowledge_base/normalized/owasp-xss-prevention-cheat-sheet.normalized.md
- Normalized-file SHA-256: 6e70b1789e82daa21054c96badc5c2528b0c20dc0c0cdb536a579472b30c83b9
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0; repository-level notice)
- License/terms reference as recorded: https://owasp.org/projects/cheat-sheet-series
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate defensive guidance for preventing or limiting cross-site scripting in application development.
- Known limitations recorded in manifest:
  - This is developer-oriented guidance, not a test procedure, target authorization, or proof of a vulnerability.
  - The repository has no numbered release selected here; the exact repository commit is recorded instead. The official repository describes Markdown files as working sources, so use the published canonical page for external citation.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: 12 fenced code blocks (31 body lines) and 148 inline-code spans removed; 25 link targets removed; 1 whole line matching the javascript-alert pattern removed. Heading count remains 29; list-marker count changes from 24 to 23. The removed whole line may include surrounding explanation.

**Potential interpretive effect for human assessment:** Code/context examples can qualify distinctions among output contexts and advice. Compare claims, exceptions and the removed line with raw; do not infer semantic equivalence from the retained prose.

**Reviewer questions:**
- [ ] Do removed code examples carry essential context distinctions, exceptions, or limitations?
- [ ] Did the removed whole line contain a needed qualification?
- [ ] Can retained claims be safely interpreted without the removed snippets?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 8

#### SQL Injection Prevention Cheat Sheet

- Source ID: src_ad783cf5bb36c72296a15e4d984f9a0a2a82159e32b8e6a2dfada47990ef8c2e
- Exact artifact title: SQL Injection Prevention Cheat Sheet
- Publisher as recorded: OWASP Cheat Sheet Series (not independently authenticated)
- Version: Unknown (not recorded in manifest)
- Repository revision: 9d41c054686e35fb56070b4b6271ae2829edea6a
- Revision date: 2026-10-26
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- Acquisition locator: https://raw.githubusercontent.com/OWASP/CheatSheetSeries/9d41c054686e35fb56070b4b6271ae2829edea6a/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: markdown
- Scope tags: sql-injection, prevention
- Raw-file path: knowledge_base/raw/owasp-sql-injection-prevention-cheat-sheet-2026-10-26.md
- Raw-file SHA-256: 5597b04e2a6f280e1b33a3a01c1f01884fa04fd9679168e2606fab22b6a6058b
- Normalized-file path: knowledge_base/normalized/owasp-sql-injection-prevention-cheat-sheet.normalized.md
- Normalized-file SHA-256: 24e872bbfea19acddc761309c2215802ecdbc6f40ff225d4a2b08afcb2a942b0
- License/terms as recorded: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0; repository-level notice)
- License/terms reference as recorded: https://owasp.org/projects/cheat-sheet-series
- Copyright notice as recorded: Unknown (not recorded in manifest)
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate defensive guidance for preventing SQL injection in application development.
- Known limitations recorded in manifest:
  - This is developer-oriented guidance, not a test procedure, target authorization, or proof of a vulnerability.
  - The repository has no numbered release selected here; the exact repository commit is recorded instead. The official repository describes Markdown files as working sources, so use the published canonical page for external citation.
  - The normalized text omits code and inline-code content and must be reviewed against the retained raw source.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** Markdown: 1 fenced code block (4 body lines) and 11 inline-code spans removed; 16 link targets removed. Fifteen headings and 3 list markers remain. Whitespace and formatting normalized.

**Potential interpretive effect for human assessment:** Removed snippets and inline identifiers may distinguish recommended parameterization from discouraged escaping and carry qualifications; compare surrounding prose with raw.

**Reviewer questions:**
- [ ] Do removed snippets preserve the distinction between recommended and discouraged options?
- [ ] Are language-specific conditions or caveats lost?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 9

#### CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')

- Source ID: src_76c3386ec7c60647970655d9695471d4578a98a6a0333947e2882c1ee5782b77
- Exact artifact title: CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')
- Publisher as recorded: The MITRE Corporation (CWE program) (not independently authenticated)
- Version: CWE 4.20
- Repository revision: Unknown (not recorded in manifest)
- Revision date: 2026-04-30
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://cwe.mitre.org/data/definitions/79.html
- Acquisition locator: https://cwe.mitre.org/data/definitions/79.html
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: mitre-cwe-html
- Scope tags: xss, weakness-taxonomy
- Raw-file path: knowledge_base/raw/mitre-cwe-79-v4.20.html
- Raw-file SHA-256: 6f47a9f0c46442a2320325d929ffc3856986216bbf517399d77fcde3b511302b
- Normalized-file path: knowledge_base/normalized/mitre-cwe-79-v4.20.normalized.md
- Normalized-file SHA-256: c42917c0a4a1ab69a62c8bd2f5624ea9f416d40faa3c1238da5836e68bf875bb
- License/terms as recorded: MITRE CWE Terms of Use; use is subject to the published terms and attribution notice.
- License/terms reference as recorded: https://cwe.mitre.org/about/termsofuse.html
- Copyright notice as recorded: Copyright © 2006-2026, The MITRE Corporation.
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate taxonomy and high-level weakness description for cross-site scripting concepts.
- Known limitations recorded in manifest:
  - Only Description, Common Consequences, and Potential Mitigations sections are included in normalized text.
  - Demonstrative and observed examples, code, and the remainder of the HTML page are excluded from normalized retrieval text.
  - CWE classification is not a test case, target authorization, or proof that an application has this weakness.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections are omitted, including examples and (where present) relationships, introduction, platform, detection and reference material. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 25 tables, 261 rows, 633 cells, 20 list tags and 200 links; counts include omitted sections. No pre/code tags detected.

**Potential interpretive effect for human assessment:** Compare definition, consequence and mitigation text with raw. Omitted page sections and flattened enumerations/tables may change context or associations.

**Reviewer questions:**
- [ ] Are the selected sections sufficient, or are omitted sections needed?
- [ ] Do flattened lists/tables retain the intended associations?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 10

#### CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')

- Source ID: src_69c5561cee1655943440109db5893afea85031a3ec93edfb36fe1769a7f918d6
- Exact artifact title: CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')
- Publisher as recorded: The MITRE Corporation (CWE program) (not independently authenticated)
- Version: CWE 4.20
- Repository revision: Unknown (not recorded in manifest)
- Revision date: Unknown (not recorded in manifest)
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://cwe.mitre.org/data/definitions/89.html
- Acquisition locator: https://cwe.mitre.org/data/definitions/89.html
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: mitre-cwe-html
- Scope tags: sql-injection, weakness-taxonomy
- Raw-file path: knowledge_base/raw/mitre-cwe-89-v4.20.html
- Raw-file SHA-256: 3cf28df2d89ea0d81a009fd7b4a0ba197495c560d001fbed8640b9adb66bc5e9
- Normalized-file path: knowledge_base/normalized/mitre-cwe-89-v4.20.normalized.md
- Normalized-file SHA-256: 20608c0b2e16e1fa64c0934edc6eff12b19c9915d3d0e852a7dbdf17348bd995
- License/terms as recorded: MITRE CWE Terms of Use; use is subject to the published terms and attribution notice.
- License/terms reference as recorded: https://cwe.mitre.org/about/termsofuse.html
- Copyright notice as recorded: Copyright © 2006-2026, The MITRE Corporation.
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate taxonomy and high-level weakness description for SQL injection concepts.
- Known limitations recorded in manifest:
  - Only Description, Common Consequences, and Potential Mitigations sections are included in normalized text.
  - The captured CWE-89 entry displays version 4.20 but no entry-specific update date; no date is inferred from other CWE entries.
  - Demonstrative and observed examples, code, and the remainder of the HTML page are excluded from normalized retrieval text.
  - CWE classification is not a test case, target authorization, or proof that an application has this weakness.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections, including examples and (where present) relationships, introduction, platform, likelihood, detection and references, are omitted. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 26 tables, 260 rows, 623 cells, 37 list tags and 180 links; counts include omitted sections. Entry-specific revision date is unknown.

**Potential interpretive effect for human assessment:** Compare selected text and table/list associations with raw, and assess whether omitted likelihood/examples/references are material. Do not infer a revision date from other CWE pages.

**Reviewer questions:**
- [ ] Are omitted likelihood/examples/references material?
- [ ] How should the unknown entry-specific update date be handled?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---

### Worksheet 11

#### CWE-862: Missing Authorization

- Source ID: src_25e8aeffe0ca973600cfe7dfe90d05bfa96faa626baf4d51a855432ad4f7db0b
- Exact artifact title: CWE-862: Missing Authorization
- Publisher as recorded: The MITRE Corporation (CWE program) (not independently authenticated)
- Version: CWE 4.20
- Repository revision: Unknown (not recorded in manifest)
- Revision date: 2026-04-30
- Publication date: Unknown (not recorded in manifest)
- Canonical source locator: https://cwe.mitre.org/data/definitions/862.html
- Acquisition locator: https://cwe.mitre.org/data/definitions/862.html
- Acquired date: 2026-10-27
- Acquisition status in manifest: acquired
- Source format: mitre-cwe-html
- Scope tags: broken-access-control, authorization, weakness-taxonomy
- Raw-file path: knowledge_base/raw/mitre-cwe-862-v4.20.html
- Raw-file SHA-256: 7da442ff99698617b6842ca640fdc37d76559bf2e6a48dbfc358f3564777264f
- Normalized-file path: knowledge_base/normalized/mitre-cwe-862-v4.20.normalized.md
- Normalized-file SHA-256: 056e54e5be29a4926c7d753632e0c39c0e32ae9b50bc6c713765cbdccb236294
- License/terms as recorded: MITRE CWE Terms of Use; use is subject to the published terms and attribution notice.
- License/terms reference as recorded: https://cwe.mitre.org/about/termsofuse.html
- Copyright notice as recorded: Copyright © 2006-2026, The MITRE Corporation.
- License applicability/compliance verification: UNKNOWN / NOT REVIEWED
- Attribution verification: UNKNOWN / NOT REVIEWED
- Intended thesis use as recorded: Candidate taxonomy and high-level weakness description for authorization concepts.
- Known limitations recorded in manifest:
  - Only Description, Common Consequences, and Potential Mitigations sections are included in normalized text.
  - Demonstrative and observed examples, code, and the remainder of the HTML page are excluded from normalized retrieval text.
  - CWE classification is not a test case, authorization record, or proof that an application has this weakness.

**Acquisition caveat:** the recorded acquisition status/date/locators do not prove publisher origin, authenticity, freshness or authorization.

**Transformation-loss summary:** HTML: only Description, Common Consequences and Potential Mitigations selected. Other page sections are omitted, including examples and (where present) relationships, introduction, platform, detection and references. Selected text is reflowed; list markers, table structure, HTML semantics and link targets are not preserved. Whole-page counts: 25 tables, 172 rows, 406 cells, 26 list tags and 170 links; counts include omitted sections. No pre/code tags detected.

**Potential interpretive effect for human assessment:** Compare definition and mitigation text and table/list associations with raw. CWE categorization alone does not prove that a particular application has an authorization defect.

**Reviewer questions:**
- [ ] Are omitted relationships/examples necessary to interpret the definition?
- [ ] Does the proposed use avoid treating a classification as application-specific proof?
- [ ] Verify publisher attribution through the approved review process.
- [ ] Compare normalized claims and qualifications with the retained raw artifact.
- [ ] Assess license terms and attribution obligations for intended use.
- [ ] Assess corroboration and record unknown metadata.

**State at packet preparation:** candidate; zero review events; excluded until explicit approval.

**Human review fields — unset:**

- Review decision: UNSET
- Reviewer reference: UNSET
- Review timestamp: UNSET
- Rationale: UNSET
- Corroboration/supporting references: UNSET
- Unknown-metadata notes: UNSET

---
