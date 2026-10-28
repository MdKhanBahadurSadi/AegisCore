"""Unit tests for AEGISCORE AI Phase 8E.5 catalog validators, data contracts, and fingerprinting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegiscore.catalog import (
    # Enums
    CatalogRecordStatus,
    AdjudicationStatus,
    PartitionAssignment,
    LocusEstablishmentStatus,
    IndependenceStatus,
    ScenarioRegistrationStatus,
    LocusVerificationStatus,
    SourceEvidenceStatus,
    RuntimeVerificationStatus,
    # Exceptions
    CatalogError,
    CatalogValidationError,
    # Contracts
    CatalogRecord,
    GroundTruthReviewRecord,
    PartitionAssignmentRecord,
    IndependenceAuditRecord,
    # Validators
    validate_catalog_jsonl,
    validate_ground_truth_review_jsonl,
    validate_partition_assignment_jsonl,
    validate_independence_audit_jsonl,
    # Fingerprint
    compute_extended_fingerprint,
    FingerprintInputs,
)


# ---------------------------------------------------------------------------
# CatalogRecord Contract Tests
# ---------------------------------------------------------------------------

def test_valid_established_catalog_record_roundtrip() -> None:
    record = CatalogRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.ESTABLISHED,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="vulnerable",
        scenario_description="Reflected XSS via search",
        evidence_reference="routes/search.ts line 28",
        evidence_source="OWASP Juice Shop v15.0.0 source",
        review_notes="SCEN-EVAL-01",
        independence_status=IndependenceStatus.INDEPENDENT,
    )
    data = record.to_dict()
    restored = CatalogRecord.from_dict(data)
    assert restored.case_id == "JS-XSS-R-01"
    assert restored.locus_status == LocusEstablishmentStatus.ESTABLISHED
    assert restored.cwe_id == "CWE-79"
    assert restored.target_uri == "/rest/products/search"
    assert restored.parameter == "q"


def test_unresolved_catalog_record_accepted() -> None:
    record = CatalogRecord(
        case_id="JS-PROP-12",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.UNRESOLVED,
        target_uri=None,
        parameter=None,
        cwe_id=None,
        vulnerability_class=None,
        expected_label_proposal="unresolved",
        scenario_description="Unresolved candidate slot",
        evidence_reference="PENDING_REVIEW",
        evidence_source="Candidate pool",
        review_notes="Awaiting supervisor adjudication",
        independence_status=IndependenceStatus.UNRESOLVED,
    )
    assert record.target_uri is None
    assert record.parameter is None
    assert record.cwe_id is None
    data = record.to_dict()
    restored = CatalogRecord.from_dict(data)
    assert restored.case_id == "JS-PROP-12"
    assert restored.locus_status == LocusEstablishmentStatus.UNRESOLVED
    assert restored.scenario_registration_status == ScenarioRegistrationStatus.CANDIDATE_POOL
    assert restored.locus_verification_status == LocusVerificationStatus.UNRESOLVED


def test_provenance_taxonomy_defaults_established() -> None:
    record = CatalogRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.ESTABLISHED,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="vulnerable",
        scenario_description="Reflected XSS",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.INDEPENDENT,
    )
    assert record.scenario_registration_status == ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED
    assert record.locus_verification_status == LocusVerificationStatus.SYNTACTICALLY_SPECIFIED


def test_provenance_taxonomy_defaults_partial() -> None:
    record = CatalogRecord(
        case_id="JS-XSS-R-02",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.PARTIAL,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="non_vulnerable",
        scenario_description="Sanitized negative control",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.POTENTIALLY_OVERLAPPING,
    )
    assert record.scenario_registration_status == ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED
    assert record.locus_verification_status == LocusVerificationStatus.PARTIALLY_SPECIFIED


def test_provenance_taxonomy_explicit_roundtrip() -> None:
    record = CatalogRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.ESTABLISHED,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="vulnerable",
        scenario_description="Reflected XSS",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.INDEPENDENT,
        scenario_registration_status=ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED,
        locus_verification_status=LocusVerificationStatus.SYNTACTICALLY_SPECIFIED,
    )
    data = record.to_dict()
    assert data["scenario_registration_status"] == "protocol_pre_registered"
    assert data["locus_verification_status"] == "syntactically_specified"
    restored = CatalogRecord.from_dict(data)
    assert restored.scenario_registration_status == ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED
    assert restored.locus_verification_status == LocusVerificationStatus.SYNTACTICALLY_SPECIFIED


def test_provenance_taxonomy_invalid_enum_raises() -> None:
    data = {
        "case_id": "JS-XSS-R-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "established",
        "target_uri": "/rest/products/search",
        "parameter": "q",
        "cwe_id": "CWE-79",
        "scenario_description": "Reflected XSS",
        "evidence_reference": "ref",
        "evidence_source": "src",
        "scenario_registration_status": "invalid_status",
    }
    with pytest.raises(CatalogValidationError, match="not valid for ScenarioRegistrationStatus"):
        CatalogRecord.from_dict(data)


def test_source_evidence_status_defaults() -> None:
    # Contradicted by source: JS-SQLI-03 (login is unparameterized in stock Juice Shop)
    r_contradicted = CatalogRecord(
        case_id="JS-SQLI-03",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.PARTIAL,
        target_uri="/rest/user/login",
        parameter="email",
        cwe_id="CWE-89",
        vulnerability_class="SQLi",
        expected_label_proposal="non_vulnerable",
        scenario_description="Parameterized login control",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.POTENTIALLY_OVERLAPPING,
    )
    assert r_contradicted.source_evidence_status == SourceEvidenceStatus.CONTRADICTED_BY_SOURCE
    assert r_contradicted.runtime_verification_status == RuntimeVerificationStatus.UNVERIFIED_OFFLINE

    # Synthetic specification: JS-XSS-R-02
    r_synthetic = CatalogRecord(
        case_id="JS-XSS-R-02",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.PARTIAL,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="non_vulnerable",
        scenario_description="DOMPurify negative control",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.POTENTIALLY_OVERLAPPING,
    )
    assert r_synthetic.source_evidence_status == SourceEvidenceStatus.SYNTHETIC_SPECIFICATION

    # Exact version pinned: JS-XSS-R-01 (Juice Shop v15.0.0)
    r_pinned = CatalogRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.ESTABLISHED,
        target_uri="/rest/products/search",
        parameter="q",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="vulnerable",
        scenario_description="Reflected XSS",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.POTENTIALLY_OVERLAPPING,
    )
    assert r_pinned.source_evidence_status == SourceEvidenceStatus.EXACT_VERSION_PINNED

    # Version unverified: DVWA cases (catalog cited 2024.1 but testbed uses 1.10)
    r_dvwa = CatalogRecord(
        case_id="DVWA-XSS-R-01",
        benchmark_name="dvwa",
        benchmark_version="2024.1",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.ESTABLISHED,
        target_uri="/vulnerabilities/xss_r/",
        parameter="name (security=low)",
        cwe_id="CWE-79",
        vulnerability_class="XSS",
        expected_label_proposal="vulnerable",
        scenario_description="Low XSS",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.INDEPENDENT,
    )
    assert r_dvwa.source_evidence_status == SourceEvidenceStatus.VERSION_UNVERIFIED

    # Unresolved: JS-PROP-12
    r_unresolved = CatalogRecord(
        case_id="JS-PROP-12",
        benchmark_name="juice-shop",
        benchmark_version="15.0.0",
        catalog_status=CatalogRecordStatus.PROPOSED,
        locus_status=LocusEstablishmentStatus.UNRESOLVED,
        target_uri=None,
        parameter=None,
        cwe_id=None,
        vulnerability_class=None,
        expected_label_proposal="unresolved",
        scenario_description="Slot 12",
        evidence_reference="ref",
        evidence_source="src",
        review_notes="",
        independence_status=IndependenceStatus.UNRESOLVED,
    )
    assert r_unresolved.source_evidence_status == SourceEvidenceStatus.UNRESOLVED


def test_source_evidence_status_invalid_enum_raises() -> None:
    data = {
        "case_id": "JS-XSS-R-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "established",
        "target_uri": "/rest/products/search",
        "parameter": "q",
        "cwe_id": "CWE-79",
        "scenario_description": "Reflected XSS",
        "evidence_reference": "ref",
        "evidence_source": "src",
        "source_evidence_status": "invalid_status",
    }
    with pytest.raises(CatalogValidationError, match="not valid for SourceEvidenceStatus"):
        CatalogRecord.from_dict(data)


def test_runtime_verification_status_invalid_enum_raises() -> None:
    data = {
        "case_id": "JS-XSS-R-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "established",
        "target_uri": "/rest/products/search",
        "parameter": "q",
        "cwe_id": "CWE-79",
        "scenario_description": "Reflected XSS",
        "evidence_reference": "ref",
        "evidence_source": "src",
        "runtime_verification_status": "invalid_status",
    }
    with pytest.raises(CatalogValidationError, match="not valid for RuntimeVerificationStatus"):
        CatalogRecord.from_dict(data)


def test_established_missing_target_uri_raises() -> None:
    with pytest.raises(CatalogValidationError, match="target_uri is empty"):
        CatalogRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.ESTABLISHED,
            target_uri=None,
            parameter="q",
            cwe_id="CWE-79",
            vulnerability_class="XSS",
            expected_label_proposal="vulnerable",
            scenario_description="Reflected XSS",
            evidence_reference="routes/search.ts",
            evidence_source="OWASP Juice Shop",
            review_notes="",
            independence_status=IndependenceStatus.INDEPENDENT,
        )


def test_established_missing_parameter_raises() -> None:
    with pytest.raises(CatalogValidationError, match="parameter is empty"):
        CatalogRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.ESTABLISHED,
            target_uri="/rest/products/search",
            parameter=None,
            cwe_id="CWE-79",
            vulnerability_class="XSS",
            expected_label_proposal="vulnerable",
            scenario_description="Reflected XSS",
            evidence_reference="routes/search.ts",
            evidence_source="OWASP Juice Shop",
            review_notes="",
            independence_status=IndependenceStatus.INDEPENDENT,
        )


def test_established_missing_cwe_raises() -> None:
    with pytest.raises(CatalogValidationError, match="cwe_id is empty"):
        CatalogRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.ESTABLISHED,
            target_uri="/rest/products/search",
            parameter="q",
            cwe_id=None,
            vulnerability_class="XSS",
            expected_label_proposal="vulnerable",
            scenario_description="Reflected XSS",
            evidence_reference="routes/search.ts",
            evidence_source="OWASP Juice Shop",
            review_notes="",
            independence_status=IndependenceStatus.INDEPENDENT,
        )


def test_established_unpermitted_cwe_raises() -> None:
    with pytest.raises(CatalogValidationError, match="not in permitted set"):
        CatalogRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.ESTABLISHED,
            target_uri="/rest/products/search",
            parameter="q",
            cwe_id="CWE-9999",
            vulnerability_class="XSS",
            expected_label_proposal="vulnerable",
            scenario_description="Reflected XSS",
            evidence_reference="routes/search.ts",
            evidence_source="OWASP Juice Shop",
            review_notes="",
            independence_status=IndependenceStatus.INDEPENDENT,
        )


def test_invalid_case_id_pattern_raises() -> None:
    with pytest.raises(CatalogValidationError, match="must match pattern"):
        CatalogRecord(
            case_id="js_lowercase_invalid",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.UNRESOLVED,
            target_uri=None,
            parameter=None,
            cwe_id=None,
            vulnerability_class=None,
            expected_label_proposal="unresolved",
            scenario_description="Invalid case",
            evidence_reference="ref",
            evidence_source="src",
            review_notes="",
            independence_status=IndependenceStatus.UNRESOLVED,
        )


def test_unpermitted_benchmark_name_raises() -> None:
    with pytest.raises(CatalogValidationError, match="not in permitted set"):
        CatalogRecord(
            case_id="TEST-01",
            benchmark_name="arbitrary-target",
            benchmark_version="1.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.UNRESOLVED,
            target_uri=None,
            parameter=None,
            cwe_id=None,
            vulnerability_class=None,
            expected_label_proposal="unresolved",
            scenario_description="Invalid target",
            evidence_reference="ref",
            evidence_source="src",
            review_notes="",
            independence_status=IndependenceStatus.UNRESOLVED,
        )


def test_invalid_expected_label_proposal_raises() -> None:
    with pytest.raises(CatalogValidationError, match="expected_label_proposal"):
        CatalogRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            benchmark_version="15.0.0",
            catalog_status=CatalogRecordStatus.PROPOSED,
            locus_status=LocusEstablishmentStatus.UNRESOLVED,
            target_uri=None,
            parameter=None,
            cwe_id=None,
            vulnerability_class=None,
            expected_label_proposal="maybe_vulnerable",
            scenario_description="Invalid label",
            evidence_reference="ref",
            evidence_source="src",
            review_notes="",
            independence_status=IndependenceStatus.UNRESOLVED,
        )


# ---------------------------------------------------------------------------
# Catalog JSONL Validator Tests
# ---------------------------------------------------------------------------

def test_validate_catalog_jsonl_duplicate_case_id_raises() -> None:
    rec1 = {
        "case_id": "JS-XSS-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "unresolved",
        "scenario_description": "First",
        "evidence_reference": "ref",
        "evidence_source": "src",
    }
    rec2 = dict(rec1)
    rec2["scenario_description"] = "Second duplicate"
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}"
    with pytest.raises(CatalogValidationError, match="duplicate case_id 'JS-XSS-01'"):
        validate_catalog_jsonl(content)


def test_validate_catalog_jsonl_duplicate_canonical_locus_raises() -> None:
    rec1 = {
        "case_id": "JS-XSS-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "established",
        "target_uri": "/rest/products/search",
        "parameter": "q",
        "cwe_id": "CWE-79",
        "scenario_description": "First",
        "evidence_reference": "ref",
        "evidence_source": "src",
    }
    rec2 = dict(rec1)
    rec2["case_id"] = "JS-XSS-02"
    rec2["scenario_description"] = "Second with same locus"
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}"
    with pytest.raises(CatalogValidationError, match="duplicate canonical locus"):
        validate_catalog_jsonl(content)


def test_validate_catalog_jsonl_partial_duplicate_locus_allowed() -> None:
    rec1 = {
        "case_id": "JS-XSS-01",
        "benchmark_name": "juice-shop",
        "benchmark_version": "15.0.0",
        "catalog_status": "proposed",
        "locus_status": "established",
        "target_uri": "/rest/products/search",
        "parameter": "q",
        "cwe_id": "CWE-79",
        "scenario_description": "Established case",
        "evidence_reference": "ref",
        "evidence_source": "src",
    }
    rec2 = dict(rec1)
    rec2["case_id"] = "JS-XSS-02"
    rec2["locus_status"] = "partial"  # Partial locus doesn't trigger duplicate error
    rec2["scenario_description"] = "Partial negative control"
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}"
    catalog = validate_catalog_jsonl(content)
    assert len(catalog) == 2


# ---------------------------------------------------------------------------
# GroundTruthReviewRecord Contract & Validator Tests
# ---------------------------------------------------------------------------

def test_ground_truth_review_valid_roundtrip() -> None:
    record = GroundTruthReviewRecord(
        case_id="JS-XSS-R-01",
        adjudication_status=AdjudicationStatus.UNVERIFIED,
        proposed_label="vulnerable",
        evidence_basis="routes/search.ts reflection",
        evidence_source="OWASP Juice Shop",
        evidence_source_version="15.0.0",
        reviewer_identity="UNASSIGNED",
        adjudication_date=None,
        adjudication_rationale="Awaiting review",
        unresolved_disagreements="none",
        eligible_for_dataset=False,
    )
    data = record.to_dict()
    restored = GroundTruthReviewRecord.from_dict(data)
    assert restored.case_id == "JS-XSS-R-01"
    assert restored.adjudication_status == AdjudicationStatus.UNVERIFIED
    assert restored.eligible_for_dataset is False


def test_ground_truth_adjudicated_without_reviewer_raises() -> None:
    with pytest.raises(CatalogValidationError, match="marked ADJUDICATED but has no reviewer_identity"):
        GroundTruthReviewRecord(
            case_id="JS-XSS-R-01",
            adjudication_status=AdjudicationStatus.ADJUDICATED,
            proposed_label="vulnerable",
            evidence_basis="Evidence text",
            evidence_source="Source",
            evidence_source_version="1.0",
            reviewer_identity="UNASSIGNED",  # UNASSIGNED is rejected
            adjudication_date="2026-10-27",
            adjudication_rationale="Rationale",
            unresolved_disagreements="none",
            eligible_for_dataset=True,
        )


def test_ground_truth_adjudicated_without_date_raises() -> None:
    with pytest.raises(CatalogValidationError, match="adjudication_date is missing"):
        GroundTruthReviewRecord(
            case_id="JS-XSS-R-01",
            adjudication_status=AdjudicationStatus.ADJUDICATED,
            proposed_label="vulnerable",
            evidence_basis="Evidence text",
            evidence_source="Source",
            evidence_source_version="1.0",
            reviewer_identity="Prof. Supervisor",
            adjudication_date=None,  # missing date
            adjudication_rationale="Rationale",
            unresolved_disagreements="none",
            eligible_for_dataset=True,
        )


def test_ground_truth_adjudicated_with_reviewer_and_date_succeeds() -> None:
    record = GroundTruthReviewRecord(
        case_id="JS-XSS-R-01",
        adjudication_status=AdjudicationStatus.ADJUDICATED,
        proposed_label="vulnerable",
        evidence_basis="Evidence text",
        evidence_source="Source",
        evidence_source_version="1.0",
        reviewer_identity="Prof. Supervisor",
        adjudication_date="2026-10-27",
        adjudication_rationale="Rationale",
        unresolved_disagreements="none",
        eligible_for_dataset=True,
    )
    assert record.adjudication_status == AdjudicationStatus.ADJUDICATED
    assert record.reviewer_identity == "Prof. Supervisor"


def test_validate_ground_truth_review_unknown_case_id_raises() -> None:
    rec = {
        "case_id": "UNKNOWN-CASE-99",
        "adjudication_status": "unverified",
        "evidence_basis": "basis",
        "evidence_source": "src",
        "evidence_source_version": "1.0",
        "adjudication_rationale": "rationale",
    }
    with pytest.raises(CatalogValidationError, match="not in catalog"):
        validate_ground_truth_review_jsonl(json.dumps(rec), known_case_ids={"JS-XSS-R-01"})


def test_validate_ground_truth_review_duplicate_case_id_raises() -> None:
    rec1 = {
        "case_id": "JS-XSS-01",
        "adjudication_status": "unverified",
        "evidence_basis": "basis 1",
        "evidence_source": "src",
        "evidence_source_version": "1.0",
        "adjudication_rationale": "rationale 1",
    }
    rec2 = dict(rec1)
    rec2["evidence_basis"] = "basis 2"
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}"
    with pytest.raises(CatalogValidationError, match="duplicate case_id 'JS-XSS-01'"):
        validate_ground_truth_review_jsonl(content)


# ---------------------------------------------------------------------------
# PartitionAssignmentRecord Contract & Validator Tests
# ---------------------------------------------------------------------------

def test_partition_assignment_unassigned_roundtrip() -> None:
    record = PartitionAssignmentRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        partition=PartitionAssignment.UNASSIGNED,
        assignment_rationale="Phase 8E.5 unassigned",
        approved_by=None,
        approval_date=None,
        notes="Proposed test",
    )
    data = record.to_dict()
    restored = PartitionAssignmentRecord.from_dict(data)
    assert restored.case_id == "JS-XSS-R-01"
    assert restored.partition == PartitionAssignment.UNASSIGNED
    assert restored.approved_by is None


def test_partition_assignment_test_without_approved_by_raises() -> None:
    with pytest.raises(CatalogValidationError, match="no approved_by authority"):
        PartitionAssignmentRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            partition=PartitionAssignment.TEST,
            assignment_rationale="Assigned to test",
            approved_by=None,
            approval_date=None,
            notes="",
        )


def test_partition_assignment_validation_with_unassigned_approved_by_raises() -> None:
    with pytest.raises(CatalogValidationError, match="no approved_by authority"):
        PartitionAssignmentRecord(
            case_id="JS-XSS-R-01",
            benchmark_name="juice-shop",
            partition=PartitionAssignment.VALIDATION,
            assignment_rationale="Assigned to validation",
            approved_by="UNASSIGNED",
            approval_date=None,
            notes="",
        )


def test_partition_assignment_approved_succeeds() -> None:
    record = PartitionAssignmentRecord(
        case_id="JS-XSS-R-01",
        benchmark_name="juice-shop",
        partition=PartitionAssignment.TEST,
        assignment_rationale="Formally approved partition",
        approved_by="Prof. Supervisor",
        approval_date="2026-10-27",
        notes="",
    )
    assert record.partition == PartitionAssignment.TEST
    assert record.approved_by == "Prof. Supervisor"


def test_partition_assignment_juice_shop_overlap_raises() -> None:
    rec1 = {
        "case_id": "JS-XSS-R-01",
        "benchmark_name": "juice-shop",
        "partition": "test",
        "assignment_rationale": "rationale",
        "approved_by": "Prof. Supervisor",
        "approval_date": "2026-10-27",
    }
    # In separate lines with duplicate case_id in different partitions
    # First: duplicate case_id check will catch same case_id
    rec2 = dict(rec1)
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}"
    with pytest.raises(CatalogValidationError, match="duplicate case_id"):
        validate_partition_assignment_jsonl(content)


def test_partition_assignment_unknown_case_id_raises() -> None:
    rec = {
        "case_id": "UNKNOWN-99",
        "benchmark_name": "juice-shop",
        "partition": "unassigned",
        "assignment_rationale": "rationale",
    }
    with pytest.raises(CatalogValidationError, match="not in catalog"):
        validate_partition_assignment_jsonl(json.dumps(rec), known_case_ids={"JS-XSS-R-01"})


# ---------------------------------------------------------------------------
# IndependenceAuditRecord Contract & Validator Tests
# ---------------------------------------------------------------------------

def test_independence_audit_valid_roundtrip() -> None:
    record = IndependenceAuditRecord(
        case_id="JS-XSS-R-01",
        independence_status=IndependenceStatus.POTENTIALLY_OVERLAPPING,
        overlap_candidates=("JS-XSS-R-02", "JS-SQLI-02"),
        overlap_rationale="Shares /rest/products/search URI",
        leakage_risk_notes="Must isolate query parameters",
        resolution="pending_supervisor_review",
    )
    data = record.to_dict()
    restored = IndependenceAuditRecord.from_dict(data)
    assert restored.case_id == "JS-XSS-R-01"
    assert restored.independence_status == IndependenceStatus.POTENTIALLY_OVERLAPPING
    assert restored.overlap_candidates == ("JS-XSS-R-02", "JS-SQLI-02")


def test_validate_independence_audit_unknown_case_id_raises() -> None:
    rec = {
        "case_id": "UNKNOWN-CASE",
        "independence_status": "independent",
        "overlap_rationale": "No overlap",
    }
    with pytest.raises(CatalogValidationError, match="not in catalog"):
        validate_independence_audit_jsonl(json.dumps(rec), known_case_ids={"JS-XSS-R-01"})


# ---------------------------------------------------------------------------
# Configuration Fingerprint Tests
# ---------------------------------------------------------------------------

def _make_sample_fingerprint_inputs(
    runner_condition: str = "proposed-multi-agent",
    adapter_version: str = "1.0.0",
    catalog_version: str = "0.5.0-draft",
    scoring_protocol_version: str = "1.0.0",
    repeat_count: int = 3,
    case_ids: tuple[str, ...] = ("JS-XSS-R-01", "JS-SQLI-01"),
    model_identifier: str | None = None,
    prompt_version: str | None = None,
) -> FingerprintInputs:
    return FingerprintInputs(
        runner_condition=runner_condition,
        adapter_version=adapter_version,
        fixture_dataset_id="benchmark-eval-v1",
        fixture_dataset_version="1.0.0",
        catalog_version=catalog_version,
        scoring_protocol_version=scoring_protocol_version,
        aggregation_policy="majority_vote_k3",
        repeat_count=repeat_count,
        application_version="15.0.0",
        case_ids=case_ids,
        model_identifier=model_identifier,
        prompt_version=prompt_version,
    )


def test_fingerprint_is_deterministic() -> None:
    inputs1 = _make_sample_fingerprint_inputs()
    inputs2 = _make_sample_fingerprint_inputs()
    fp1 = compute_extended_fingerprint(inputs1)
    fp2 = compute_extended_fingerprint(inputs2)
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex string


def test_fingerprint_changes_on_condition_change() -> None:
    fp_prop = compute_extended_fingerprint(_make_sample_fingerprint_inputs(runner_condition="proposed-multi-agent"))
    fp_base = compute_extended_fingerprint(_make_sample_fingerprint_inputs(runner_condition="baseline-single-agent"))
    assert fp_prop != fp_base


def test_fingerprint_changes_on_catalog_version_change() -> None:
    fp1 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(catalog_version="0.5.0-draft"))
    fp2 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(catalog_version="1.0.0"))
    assert fp1 != fp2


def test_fingerprint_changes_on_repeat_count_change() -> None:
    fp_k3 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(repeat_count=3))
    fp_k5 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(repeat_count=5))
    assert fp_k3 != fp_k5


def test_fingerprint_changes_on_adapter_version_change() -> None:
    fp1 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(adapter_version="1.0.0"))
    fp2 = compute_extended_fingerprint(_make_sample_fingerprint_inputs(adapter_version="1.1.0"))
    assert fp1 != fp2


def test_fingerprint_sorts_case_ids_for_order_invariance() -> None:
    inputs_ab = _make_sample_fingerprint_inputs(case_ids=("JS-XSS-R-01", "JS-SQLI-01"))
    inputs_ba = _make_sample_fingerprint_inputs(case_ids=("JS-SQLI-01", "JS-XSS-R-01"))
    assert inputs_ab.compute() == inputs_ba.compute()


def test_fingerprint_with_model_differs_from_none() -> None:
    fp_no_model = compute_extended_fingerprint(_make_sample_fingerprint_inputs(model_identifier=None))
    fp_model = compute_extended_fingerprint(_make_sample_fingerprint_inputs(model_identifier="gemini-1.5-pro"))
    assert fp_no_model != fp_model


# ---------------------------------------------------------------------------
# Generated Draft Files Static Validation Test
# ---------------------------------------------------------------------------

def test_generated_draft_files_validate_cleanly() -> None:
    docs_dir = Path("s:/AegisCore/docs")
    catalog_path = docs_dir / "case_catalog_draft.jsonl"
    gt_path = docs_dir / "ground_truth_review_template.jsonl"
    part_path = docs_dir / "partition_assignment_template.jsonl"
    ia_path = docs_dir / "independence_audit_template.jsonl"

    assert catalog_path.is_file(), f"Missing {catalog_path}"
    assert gt_path.is_file(), f"Missing {gt_path}"
    assert part_path.is_file(), f"Missing {part_path}"
    assert ia_path.is_file(), f"Missing {ia_path}"

    catalog = validate_catalog_jsonl(catalog_path.read_text(encoding="utf-8"))
    assert len(catalog) == 36

    # Verify counts
    established_count = sum(1 for c in catalog if c.locus_status == LocusEstablishmentStatus.ESTABLISHED)
    partial_count = sum(1 for c in catalog if c.locus_status == LocusEstablishmentStatus.PARTIAL)
    unresolved_count = sum(1 for c in catalog if c.locus_status == LocusEstablishmentStatus.UNRESOLVED)

    assert established_count == 13
    assert partial_count == 3
    assert unresolved_count == 20
    assert established_count + partial_count + unresolved_count == 36

    known_ids = {c.case_id for c in catalog}

    gt_records = validate_ground_truth_review_jsonl(gt_path.read_text(encoding="utf-8"), known_case_ids=known_ids)
    assert len(gt_records) == 36
    # Invariant: ZERO cases are ADJUDICATED in Phase 8E.5
    for gt in gt_records:
        assert gt.adjudication_status != AdjudicationStatus.ADJUDICATED
        assert gt.adjudication_status == AdjudicationStatus.UNVERIFIED
        assert gt.eligible_for_dataset is False

    part_records = validate_partition_assignment_jsonl(part_path.read_text(encoding="utf-8"), known_case_ids=known_ids)
    assert len(part_records) == 36
    # Invariant: ALL cases are UNASSIGNED in Phase 8E.5
    for p in part_records:
        assert p.partition == PartitionAssignment.UNASSIGNED
        assert p.approved_by is None

    ia_records = validate_independence_audit_jsonl(ia_path.read_text(encoding="utf-8"), known_case_ids=known_ids)
    assert len(ia_records) == 4
