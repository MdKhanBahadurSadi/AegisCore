# CWE-862: Missing Authorization

## Corpus provenance metadata

- Publisher: The MITRE Corporation (CWE program)
- Acquisition locator: https://cwe.mitre.org/data/definitions/862.html
- Published canonical reference: https://cwe.mitre.org/data/definitions/862.html
- Version: CWE 4.20
- Repository revision: Unknown / not stated
- Revision date: 2026-04-30
- License / terms: MITRE CWE Terms of Use; use is subject to the published terms and attribution notice.
- License information: https://cwe.mitre.org/about/termsofuse.html
- Copyright notice: Copyright © 2006-2026, The MITRE Corporation.
- Acquired: 2026-10-27
- Review state: candidate
- Retrieval eligibility: excluded_until_explicit_approval
- Intended use: Candidate taxonomy and high-level weakness description for authorization concepts.
- Limitations: Only Description, Common Consequences, and Potential Mitigations sections are included in normalized text. Demonstrative and observed examples, code, and the remainder of the HTML page are excluded from normalized retrieval text. CWE classification is not a test case, authorization record, or proof that an application has this weakness.

This file is a lossy normalized extract, not a verbatim copy of the publisher source. Use the linked raw source for review. It is a candidate reference, not approved guidance or proof.

## Normalized publisher content
## Description

Description

| The product does not perform an authorization check when an actor attempts to access a resource or perform an action.

|

## Common Consequences

Common Consequences

This table specifies different individual consequences
associated with the weakness. The Scope identifies the application security area that is
violated, while the Impact describes the negative technical impact that arises if an
adversary succeeds in exploiting this weakness. The Likelihood provides information about
how likely the specific consequence is expected to be seen relative to the other
consequences in the list. For example, there may be high likelihood that a weakness will be
exploited to achieve a certain impact, but a low likelihood that it will be exploited to
achieve a different impact.

| Impact

| Details

|

Read Application Data; Read Files or Directories

|

Scope: Confidentiality

An attacker could read sensitive data, either by reading the data directly from a data store that is not restricted, or by accessing insufficiently-protected, privileged functionality to read the data.

|

Modify Application Data; Modify Files or Directories

|

Scope: Integrity

An attacker could modify sensitive data, either by writing the data directly to a data store that is not restricted, or by accessing insufficiently-protected, privileged functionality to write the data.

|

Gain Privileges or Assume Identity; Bypass Protection Mechanism

|

Scope: Access Control

An attacker could gain privileges by modifying or reading critical data directly, or by accessing privileged functionality.

|

DoS: Crash, Exit, or Restart; DoS: Resource Consumption (CPU); DoS: Resource Consumption (Memory); DoS: Resource Consumption (Other)

|

Scope: Availability

An attacker could gain unauthorized access to resources on the system and excessively consume those resources, leading to a denial of service.

## Potential Mitigations

Potential Mitigations

| Phase(s)

| Mitigation

|

Architecture and Design

|

Divide the product into anonymous, normal, privileged, and administrative areas. Reduce the attack surface by carefully mapping roles with data and functionality. Use role-based access control (RBAC) [ REF-229 ] to enforce the roles at the appropriate boundaries.

Note that this approach may not protect against horizontal authorization, i.e., it will not protect a user from attacking others with the same role.

|

Architecture and Design

|

Ensure that access control checks are performed related to the business logic. These checks may be different than the access control checks that are applied to more generic resources such as files, connections, processes, memory, and database records. For example, a database may restrict access for medical records to a specific database user, but each record might only be intended to be accessible to the patient and the patient's doctor [ REF-7 ].

|

Architecture and Design

|

Strategy: Libraries or Frameworks

Use a vetted library or framework that does not allow this weakness to occur or provides constructs that make this weakness easier to avoid.

For example, consider using authorization frameworks such as the JAAS Authorization Framework [ REF-233 ] and the OWASP ESAPI Access Control feature [ REF-45 ].

|

Architecture and Design

|

For web applications, make sure that the access control mechanism is enforced correctly at the server side on every page. Users should not be able to access any unauthorized functionality or information by simply requesting direct access to that page.

One way to do this is to ensure that all pages containing sensitive information are not cached, and that all such pages restrict access to requests that are accompanied by an active and authenticated session token associated with a user who has the required permissions to access that page.

|

System Configuration; Installation

|

Use the access control capabilities of your operating system and server environment and define your access control lists accordingly. Use a "default deny" policy when defining these ACLs.
