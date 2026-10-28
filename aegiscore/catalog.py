"""Offline catalog validator for AEGISCORE AI Phase 8E.5 case catalog and ground-truth records.

Phase 8E.5: Canonical Case Catalog & Ground-Truth Preparation.
Validates catalog JSONL records, ground-truth review records, partition assignments,
and configuration fingerprint completeness.

STRICT RESTRICTION: Documentation, metadata, and offline validation only.
Zero container operations, zero network requests, zero LLM calls, zero scanner runs,
zero database creation. No benchmark cases are marked ADJUDICATED in this phase.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

__all__ = [
    # Enums
    "CatalogRecordStatus",
    "AdjudicationStatus",
    "PartitionAssignment",
    "LocusEstablishmentStatus",
    "IndependenceStatus",
    "ScenarioRegistrationStatus",
    "LocusVerificationStatus",
    "SourceEvidenceStatus",
    "RuntimeVerificationStatus",
    # Exceptions
    "CatalogError",
    "CatalogValidationError",
    # Data contracts
    "CatalogRecord",
    "GroundTruthReviewRecord",
    "PartitionAssignmentRecord",
    "IndependenceAuditRecord",
    "BenchmarkReadinessReport",
    # Validators
    "validate_catalog_jsonl",
    "validate_ground_truth_review_jsonl",
    "validate_partition_assignment_jsonl",
    "validate_independence_audit_jsonl",
    # Readiness Audits
    "audit_benchmark_readiness",
    "load_and_audit_repository_readiness",
    # Fingerprint
    "compute_extended_fingerprint",
    "FingerprintInputs",
]

# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class CatalogError(Exception):
    """Base exception for catalog validation errors."""
    __test__ = False


class CatalogValidationError(CatalogError):
    """Raised when a catalog record fails structural, integrity, or schema validation."""
    __test__ = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CatalogRecordStatus(str, Enum):
    """Lifecycle status of a proposed benchmark case in the catalog."""
    PROPOSED = "proposed"
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    EXCLUDED = "excluded"


class AdjudicationStatus(str, Enum):
    """Adjudication state of a ground-truth review record."""
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    ADJUDICATED = "adjudicated"


class PartitionAssignment(str, Enum):
    """Dataset partition membership for a confirmed case."""
    VALIDATION = "validation"
    TEST = "test"
    SECONDARY = "secondary"
    UNASSIGNED = "unassigned"


class LocusEstablishmentStatus(str, Enum):
    """Evidence strength for the canonical locus triple."""
    ESTABLISHED = "established"         # URI, parameter, and CWE coordinates fully specified
    PARTIAL = "partial"                 # Some locus elements synthetic, patched, or uncertain
    UNRESOLVED = "unresolved"          # Insufficient coordinates to establish locus
    NOT_APPLICABLE = "not_applicable"  # Excluded case


class ScenarioRegistrationStatus(str, Enum):
    """Status of scenario pre-registration in the thesis evaluation protocol."""
    PROTOCOL_PRE_REGISTERED = "protocol_pre_registered"  # Documented in Phase 8E.1 Protocol Table 6
    CANDIDATE_POOL = "candidate_pool"                    # Unregistered candidate slot awaiting selection


class LocusVerificationStatus(str, Enum):
    """Empirical and provenance verification level of the canonical locus."""
    SYNTACTICALLY_SPECIFIED = "syntactically_specified"  # Specified in protocol; target source uninspected/absent in repo
    PARTIALLY_SPECIFIED = "partially_specified"          # Synthetic or patched negative-control locus
    EMPIRICALLY_VERIFIED = "empirically_verified"        # Verified against running/source target in testbed lab
    UNRESOLVED = "unresolved"                            # Unpopulated locus coordinates


class SourceEvidenceStatus(str, Enum):
    """Status of benchmark source-code evidence supporting the catalog claim."""
    EXACT_VERSION_PINNED = "exact_version_pinned"        # Upstream source matches claim in exact pinned version (external review)
    VERSION_UNVERIFIED = "version_unverified"            # Claim cites unverified version, rolling branch, or testbed version mismatch
    CONTRADICTED_BY_SOURCE = "contradicted_by_source"    # Pinned benchmark source directly contradicts the claimed behavior
    SYNTHETIC_SPECIFICATION = "synthetic_specification"  # Synthetic scenario from protocol without direct target source basis
    UNRESOLVED = "unresolved"                            # Unpopulated slot awaiting source review


class RuntimeVerificationStatus(str, Enum):
    """Empirical runtime verification level in the isolated testbed."""
    UNVERIFIED_OFFLINE = "unverified_offline"            # Strictly offline; zero live container executions
    EMPIRICALLY_VERIFIED = "empirically_verified"        # Verified via live HTTP execution against running testbed target
    NOT_APPLICABLE = "not_applicable"                    # Excluded or non-executable slot


class IndependenceStatus(str, Enum):
    """Locus independence assessment status."""
    INDEPENDENT = "independent"
    POTENTIALLY_OVERLAPPING = "potentially_overlapping"
    CONFIRMED_DUPLICATE = "confirmed_duplicate"
    UNRESOLVED = "unresolved"


# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

_CWE_PATTERN = re.compile(r"^CWE-[0-9]+$")
_CASE_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-]{2,39}$")
_BENCHMARK_VERSION_PATTERN = re.compile(r"^[\w.\-]+$")

_PERMITTED_BENCHMARKS: frozenset[str] = frozenset({
    "juice-shop",
    "dvwa",
})

_PERMITTED_VULNERABILITY_CLASSES: frozenset[str] = frozenset({
    "XSS",
    "SQLi",
    "BAC",
    "IDOR",
    "PATH_TRAVERSAL",
})

_PERMITTED_CWES: frozenset[str] = frozenset({
    "CWE-22",    # Path Traversal
    "CWE-79",    # XSS
    "CWE-80",    # Basic XSS
    "CWE-89",    # SQLi
    "CWE-284",   # Improper Access Control
    "CWE-285",   # Improper Authorization
    "CWE-639",   # IDOR
    "CWE-862",   # Missing Authorization
    "CWE-863",   # Incorrect Authorization
})


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogValidationError(f"'{field_name}' must be a non-empty string")
    if value != value.strip():
        raise CatalogValidationError(f"'{field_name}' has leading/trailing whitespace")
    return value


def _require_enum(value: Any, enum_cls: type[Enum], field_name: str) -> Any:
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        raise CatalogValidationError(
            f"'{field_name}' value '{value}' is not valid for {enum_cls.__name__}. "
            f"Valid: {[e.value for e in enum_cls]}"
        )


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CatalogRecord:
    """Proposed or confirmed benchmark case entry in the evaluation case catalog."""

    case_id: str
    benchmark_name: str
    benchmark_version: str
    catalog_status: CatalogRecordStatus
    locus_status: LocusEstablishmentStatus

    # Locus (may be None when locus_status is UNRESOLVED/PARTIAL)
    target_uri: str | None
    parameter: str | None
    cwe_id: str | None

    vulnerability_class: str | None
    expected_label_proposal: str | None       # "vulnerable" | "non_vulnerable" | "unresolved"
    scenario_description: str
    evidence_reference: str
    evidence_source: str
    review_notes: str
    independence_status: IndependenceStatus

    # Refined provenance & verification taxonomy (defaults resolved in __post_init__)
    scenario_registration_status: ScenarioRegistrationStatus | None = None
    locus_verification_status: LocusVerificationStatus | None = None
    source_evidence_status: SourceEvidenceStatus | None = None
    runtime_verification_status: RuntimeVerificationStatus | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        if not _CASE_ID_PATTERN.fullmatch(self.case_id):
            raise CatalogValidationError(
                f"case_id '{self.case_id}' must match pattern [A-Z0-9][A-Z0-9-]{{2,39}}"
            )
        _require_nonempty(self.benchmark_name, "benchmark_name")
        if self.benchmark_name not in _PERMITTED_BENCHMARKS:
            raise CatalogValidationError(
                f"benchmark_name '{self.benchmark_name}' not in permitted set: {sorted(_PERMITTED_BENCHMARKS)}"
            )
        _require_nonempty(self.benchmark_version, "benchmark_version")
        _require_nonempty(self.scenario_description, "scenario_description")
        _require_nonempty(self.evidence_reference, "evidence_reference")
        _require_nonempty(self.evidence_source, "evidence_source")

        # Resolve scenario registration status
        if self.scenario_registration_status is None:
            s_status = (
                ScenarioRegistrationStatus.CANDIDATE_POOL
                if "-PROP-" in self.case_id
                else ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED
            )
            object.__setattr__(self, "scenario_registration_status", s_status)
        else:
            _require_enum(self.scenario_registration_status, ScenarioRegistrationStatus, "scenario_registration_status")

        # Resolve locus verification status
        if self.locus_verification_status is None:
            if self.locus_status == LocusEstablishmentStatus.UNRESOLVED:
                l_status = LocusVerificationStatus.UNRESOLVED
            elif self.locus_status == LocusEstablishmentStatus.PARTIAL:
                l_status = LocusVerificationStatus.PARTIALLY_SPECIFIED
            else:
                l_status = LocusVerificationStatus.SYNTACTICALLY_SPECIFIED
            object.__setattr__(self, "locus_verification_status", l_status)
        else:
            _require_enum(self.locus_verification_status, LocusVerificationStatus, "locus_verification_status")

        # Resolve runtime verification status (strictly offline during design/audit phases)
        if self.runtime_verification_status is None:
            object.__setattr__(self, "runtime_verification_status", RuntimeVerificationStatus.UNVERIFIED_OFFLINE)
        else:
            _require_enum(self.runtime_verification_status, RuntimeVerificationStatus, "runtime_verification_status")

        # Resolve source evidence status
        if self.source_evidence_status is None:
            if self.case_id == "JS-SQLI-03":
                se_status = SourceEvidenceStatus.CONTRADICTED_BY_SOURCE
            elif self.case_id in ("JS-XSS-R-02", "JS-SQLI-04"):
                se_status = SourceEvidenceStatus.SYNTHETIC_SPECIFICATION
            elif self.case_id.startswith("JS-") and "-PROP-" not in self.case_id:
                se_status = SourceEvidenceStatus.EXACT_VERSION_PINNED
            elif self.case_id.startswith("DVWA-") and "-PROP-" not in self.case_id:
                se_status = SourceEvidenceStatus.VERSION_UNVERIFIED
            else:
                se_status = SourceEvidenceStatus.UNRESOLVED
            object.__setattr__(self, "source_evidence_status", se_status)
        else:
            _require_enum(self.source_evidence_status, SourceEvidenceStatus, "source_evidence_status")

        # CWE validation only when locus is established
        if self.locus_status == LocusEstablishmentStatus.ESTABLISHED:
            if not self.target_uri:
                raise CatalogValidationError(
                    f"Case '{self.case_id}' has locus_status=ESTABLISHED but target_uri is empty"
                )
            if not self.parameter:
                raise CatalogValidationError(
                    f"Case '{self.case_id}' has locus_status=ESTABLISHED but parameter is empty"
                )
            if not self.cwe_id:
                raise CatalogValidationError(
                    f"Case '{self.case_id}' has locus_status=ESTABLISHED but cwe_id is empty"
                )
            if self.cwe_id not in _PERMITTED_CWES:
                raise CatalogValidationError(
                    f"Case '{self.case_id}' cwe_id '{self.cwe_id}' is not in permitted set: {sorted(_PERMITTED_CWES)}"
                )

        # expected_label_proposal must be one of the three allowed values
        allowed_labels = {"vulnerable", "non_vulnerable", "unresolved", None}
        if self.expected_label_proposal not in allowed_labels:
            raise CatalogValidationError(
                f"Case '{self.case_id}' expected_label_proposal '{self.expected_label_proposal}' "
                f"must be one of {sorted(v for v in allowed_labels if v is not None)} or null"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "benchmark_name": self.benchmark_name,
            "benchmark_version": self.benchmark_version,
            "catalog_status": self.catalog_status.value,
            "locus_status": self.locus_status.value,
            "target_uri": self.target_uri,
            "parameter": self.parameter,
            "cwe_id": self.cwe_id,
            "vulnerability_class": self.vulnerability_class,
            "expected_label_proposal": self.expected_label_proposal,
            "scenario_description": self.scenario_description,
            "evidence_reference": self.evidence_reference,
            "evidence_source": self.evidence_source,
            "review_notes": self.review_notes,
            "independence_status": self.independence_status.value,
            "scenario_registration_status": (
                self.scenario_registration_status.value
                if self.scenario_registration_status is not None
                else ScenarioRegistrationStatus.PROTOCOL_PRE_REGISTERED.value
            ),
            "locus_verification_status": (
                self.locus_verification_status.value
                if self.locus_verification_status is not None
                else LocusVerificationStatus.SYNTACTICALLY_SPECIFIED.value
            ),
            "source_evidence_status": (
                self.source_evidence_status.value
                if self.source_evidence_status is not None
                else SourceEvidenceStatus.UNRESOLVED.value
            ),
            "runtime_verification_status": (
                self.runtime_verification_status.value
                if self.runtime_verification_status is not None
                else RuntimeVerificationStatus.UNVERIFIED_OFFLINE.value
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CatalogRecord:
        try:
            return cls(
                case_id=data["case_id"],
                benchmark_name=data["benchmark_name"],
                benchmark_version=data["benchmark_version"],
                catalog_status=_require_enum(data["catalog_status"], CatalogRecordStatus, "catalog_status"),
                locus_status=_require_enum(data["locus_status"], LocusEstablishmentStatus, "locus_status"),
                target_uri=data.get("target_uri"),
                parameter=data.get("parameter"),
                cwe_id=data.get("cwe_id"),
                vulnerability_class=data.get("vulnerability_class"),
                expected_label_proposal=data.get("expected_label_proposal"),
                scenario_description=data["scenario_description"],
                evidence_reference=data["evidence_reference"],
                evidence_source=data["evidence_source"],
                review_notes=data.get("review_notes", ""),
                independence_status=_require_enum(
                    data.get("independence_status", "unresolved"),
                    IndependenceStatus,
                    "independence_status",
                ),
                scenario_registration_status=(
                    _require_enum(
                        data["scenario_registration_status"],
                        ScenarioRegistrationStatus,
                        "scenario_registration_status",
                    )
                    if "scenario_registration_status" in data
                    else None
                ),
                locus_verification_status=(
                    _require_enum(
                        data["locus_verification_status"],
                        LocusVerificationStatus,
                        "locus_verification_status",
                    )
                    if "locus_verification_status" in data
                    else None
                ),
                source_evidence_status=(
                    _require_enum(
                        data["source_evidence_status"],
                        SourceEvidenceStatus,
                        "source_evidence_status",
                    )
                    if "source_evidence_status" in data
                    else None
                ),
                runtime_verification_status=(
                    _require_enum(
                        data["runtime_verification_status"],
                        RuntimeVerificationStatus,
                        "runtime_verification_status",
                    )
                    if "runtime_verification_status" in data
                    else None
                ),
            )
        except KeyError as exc:
            raise CatalogValidationError(f"Missing required catalog field: {exc}") from exc


@dataclass(frozen=True, slots=True)
class GroundTruthReviewRecord:
    """Ground-truth review record for a proposed catalog case."""

    case_id: str
    adjudication_status: AdjudicationStatus
    proposed_label: str | None          # "vulnerable" | "non_vulnerable" | None if unresolved
    evidence_basis: str                 # Description of evidence supporting the label
    evidence_source: str                # Source artifact (e.g. "Juice Shop source code v15.0.0")
    evidence_source_version: str
    reviewer_identity: str | None       # "UNASSIGNED" until formally reviewed
    adjudication_date: str | None       # ISO date string or None
    adjudication_rationale: str
    unresolved_disagreements: str
    eligible_for_dataset: bool

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.evidence_basis, "evidence_basis")
        _require_nonempty(self.evidence_source, "evidence_source")
        _require_nonempty(self.evidence_source_version, "evidence_source_version")
        _require_nonempty(self.adjudication_rationale, "adjudication_rationale")

        # Strictly prohibit ADJUDICATED without reviewer and date
        if self.adjudication_status == AdjudicationStatus.ADJUDICATED:
            if not self.reviewer_identity or self.reviewer_identity == "UNASSIGNED":
                raise CatalogValidationError(
                    f"Ground-truth record '{self.case_id}' is marked ADJUDICATED "
                    f"but has no reviewer_identity"
                )
            if not self.adjudication_date:
                raise CatalogValidationError(
                    f"Ground-truth record '{self.case_id}' is marked ADJUDICATED "
                    f"but adjudication_date is missing"
                )

        allowed_labels = {"vulnerable", "non_vulnerable", None}
        if self.proposed_label not in allowed_labels:
            raise CatalogValidationError(
                f"Ground-truth record '{self.case_id}' proposed_label '{self.proposed_label}' "
                f"must be 'vulnerable', 'non_vulnerable', or null"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "adjudication_status": self.adjudication_status.value,
            "proposed_label": self.proposed_label,
            "evidence_basis": self.evidence_basis,
            "evidence_source": self.evidence_source,
            "evidence_source_version": self.evidence_source_version,
            "reviewer_identity": self.reviewer_identity,
            "adjudication_date": self.adjudication_date,
            "adjudication_rationale": self.adjudication_rationale,
            "unresolved_disagreements": self.unresolved_disagreements,
            "eligible_for_dataset": self.eligible_for_dataset,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GroundTruthReviewRecord:
        try:
            return cls(
                case_id=data["case_id"],
                adjudication_status=_require_enum(
                    data["adjudication_status"], AdjudicationStatus, "adjudication_status"
                ),
                proposed_label=data.get("proposed_label"),
                evidence_basis=data["evidence_basis"],
                evidence_source=data["evidence_source"],
                evidence_source_version=data["evidence_source_version"],
                reviewer_identity=data.get("reviewer_identity"),
                adjudication_date=data.get("adjudication_date"),
                adjudication_rationale=data["adjudication_rationale"],
                unresolved_disagreements=data.get("unresolved_disagreements", "none"),
                eligible_for_dataset=bool(data.get("eligible_for_dataset", False)),
            )
        except KeyError as exc:
            raise CatalogValidationError(f"Missing required ground-truth review field: {exc}") from exc


@dataclass(frozen=True, slots=True)
class PartitionAssignmentRecord:
    """Partition membership assignment for a confirmed evaluation case."""

    case_id: str
    benchmark_name: str
    partition: PartitionAssignment
    assignment_rationale: str
    approved_by: str | None    # None until formally approved
    approval_date: str | None  # None until formally approved
    notes: str

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.benchmark_name, "benchmark_name")
        _require_nonempty(self.assignment_rationale, "assignment_rationale")

        # No formal assignment without approval authority
        if self.partition != PartitionAssignment.UNASSIGNED:
            if not self.approved_by or self.approved_by == "UNASSIGNED":
                raise CatalogValidationError(
                    f"Partition record '{self.case_id}' has partition='{self.partition.value}' "
                    f"but no approved_by authority. Only UNASSIGNED status is permitted without approval."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "benchmark_name": self.benchmark_name,
            "partition": self.partition.value,
            "assignment_rationale": self.assignment_rationale,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PartitionAssignmentRecord:
        try:
            return cls(
                case_id=data["case_id"],
                benchmark_name=data["benchmark_name"],
                partition=_require_enum(data["partition"], PartitionAssignment, "partition"),
                assignment_rationale=data["assignment_rationale"],
                approved_by=data.get("approved_by"),
                approval_date=data.get("approval_date"),
                notes=data.get("notes", ""),
            )
        except KeyError as exc:
            raise CatalogValidationError(f"Missing required partition assignment field: {exc}") from exc


@dataclass(frozen=True, slots=True)
class IndependenceAuditRecord:
    """Independence and overlap audit record for a proposed catalog case."""

    case_id: str
    independence_status: IndependenceStatus
    overlap_candidates: tuple[str, ...]   # case_ids of potentially overlapping cases
    overlap_rationale: str
    leakage_risk_notes: str
    resolution: str

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.overlap_rationale, "overlap_rationale")

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "independence_status": self.independence_status.value,
            "overlap_candidates": list(self.overlap_candidates),
            "overlap_rationale": self.overlap_rationale,
            "leakage_risk_notes": self.leakage_risk_notes,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IndependenceAuditRecord:
        try:
            return cls(
                case_id=data["case_id"],
                independence_status=_require_enum(
                    data["independence_status"], IndependenceStatus, "independence_status"
                ),
                overlap_candidates=tuple(data.get("overlap_candidates", [])),
                overlap_rationale=data["overlap_rationale"],
                leakage_risk_notes=data.get("leakage_risk_notes", ""),
                resolution=data.get("resolution", "pending"),
            )
        except KeyError as exc:
            raise CatalogValidationError(f"Missing required independence audit field: {exc}") from exc


# ---------------------------------------------------------------------------
# JSONL Validators
# ---------------------------------------------------------------------------

def _parse_jsonl(content: str | Sequence[str]) -> list[dict[str, Any]]:
    if isinstance(content, str):
        lines = content.strip().splitlines()
    else:
        lines = list(content)
    records: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rec = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise CatalogValidationError(f"Line {idx}: invalid JSON: {exc}") from exc
        if not isinstance(rec, dict):
            raise CatalogValidationError(f"Line {idx}: expected JSON object, got {type(rec).__name__}")
        records.append(rec)
    return records


def validate_catalog_jsonl(content: str | Sequence[str]) -> tuple[CatalogRecord, ...]:
    """Parse and validate an evaluation case catalog JSONL stream.

    Enforces unique case IDs, non-duplicate loci for ESTABLISHED cases,
    and permitted enum values. Does not mark any case ADJUDICATED.
    """
    records = _parse_jsonl(content)
    seen_ids: set[str] = set()
    seen_loci: set[tuple[str | None, str | None, str | None]] = set()
    catalog: list[CatalogRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            cat_rec = CatalogRecord.from_dict(rec_dict)
        except CatalogValidationError as exc:
            raise CatalogValidationError(
                f"Catalog record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}"
            ) from exc

        if cat_rec.case_id in seen_ids:
            raise CatalogValidationError(
                f"Catalog record {idx}: duplicate case_id '{cat_rec.case_id}'"
            )
        seen_ids.add(cat_rec.case_id)

        if cat_rec.locus_status == LocusEstablishmentStatus.ESTABLISHED:
            locus_key = (cat_rec.benchmark_name, cat_rec.target_uri, cat_rec.parameter, cat_rec.cwe_id)
            if locus_key in seen_loci:
                raise CatalogValidationError(
                    f"Catalog record {idx}: duplicate canonical locus {locus_key} on case '{cat_rec.case_id}'"
                )
            seen_loci.add(locus_key)

        catalog.append(cat_rec)

    return tuple(catalog)


def validate_ground_truth_review_jsonl(
    content: str | Sequence[str],
    known_case_ids: set[str] | None = None,
) -> tuple[GroundTruthReviewRecord, ...]:
    """Parse and validate a ground-truth review JSONL stream.

    Rejects any record claiming ADJUDICATED status without reviewer_identity
    and adjudication_date. No cases are marked ADJUDICATED in Phase 8E.5.
    """
    records = _parse_jsonl(content)
    seen_ids: set[str] = set()
    gt_records: list[GroundTruthReviewRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            gt_rec = GroundTruthReviewRecord.from_dict(rec_dict)
        except CatalogValidationError as exc:
            raise CatalogValidationError(
                f"Ground-truth review record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}"
            ) from exc

        if gt_rec.case_id in seen_ids:
            raise CatalogValidationError(
                f"Ground-truth record {idx}: duplicate case_id '{gt_rec.case_id}'"
            )
        seen_ids.add(gt_rec.case_id)

        if known_case_ids is not None and gt_rec.case_id not in known_case_ids:
            raise CatalogValidationError(
                f"Ground-truth record {idx}: case_id '{gt_rec.case_id}' not in catalog"
            )

        gt_records.append(gt_rec)

    return tuple(gt_records)


def validate_partition_assignment_jsonl(
    content: str | Sequence[str],
    known_case_ids: set[str] | None = None,
) -> tuple[PartitionAssignmentRecord, ...]:
    """Parse and validate a partition assignment JSONL stream.

    Rejects any non-UNASSIGNED partition without an approval authority.
    """
    records = _parse_jsonl(content)
    seen_ids: set[str] = set()
    partition_records: list[PartitionAssignmentRecord] = []

    juice_shop_test: list[str] = []
    juice_shop_val: list[str] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            pa_rec = PartitionAssignmentRecord.from_dict(rec_dict)
        except CatalogValidationError as exc:
            raise CatalogValidationError(
                f"Partition assignment record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}"
            ) from exc

        if pa_rec.case_id in seen_ids:
            raise CatalogValidationError(
                f"Partition record {idx}: duplicate case_id '{pa_rec.case_id}'"
            )
        seen_ids.add(pa_rec.case_id)

        if known_case_ids is not None and pa_rec.case_id not in known_case_ids:
            raise CatalogValidationError(
                f"Partition record {idx}: case_id '{pa_rec.case_id}' not in catalog"
            )

        if pa_rec.benchmark_name == "juice-shop":
            if pa_rec.partition == PartitionAssignment.TEST:
                juice_shop_test.append(pa_rec.case_id)
            elif pa_rec.partition == PartitionAssignment.VALIDATION:
                juice_shop_val.append(pa_rec.case_id)

        partition_records.append(pa_rec)

    # Validate disjointness between validation and test for Juice Shop
    test_set = set(juice_shop_test)
    val_set = set(juice_shop_val)
    overlap = test_set & val_set
    if overlap:
        raise CatalogValidationError(
            f"Juice Shop cases appear in both VALIDATION and TEST partitions: {sorted(overlap)}"
        )

    return tuple(partition_records)


def validate_independence_audit_jsonl(
    content: str | Sequence[str],
    known_case_ids: set[str] | None = None,
) -> tuple[IndependenceAuditRecord, ...]:
    """Parse and validate an independence audit JSONL stream."""
    records = _parse_jsonl(content)
    seen_ids: set[str] = set()
    audit_records: list[IndependenceAuditRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            ia_rec = IndependenceAuditRecord.from_dict(rec_dict)
        except CatalogValidationError as exc:
            raise CatalogValidationError(
                f"Independence audit record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}"
            ) from exc

        if ia_rec.case_id in seen_ids:
            raise CatalogValidationError(
                f"Independence audit record {idx}: duplicate case_id '{ia_rec.case_id}'"
            )
        seen_ids.add(ia_rec.case_id)

        if known_case_ids is not None and ia_rec.case_id not in known_case_ids:
            raise CatalogValidationError(
                f"Independence audit record {idx}: case_id '{ia_rec.case_id}' not in catalog"
            )

        audit_records.append(ia_rec)

    return tuple(audit_records)


# ---------------------------------------------------------------------------
# Extended Configuration Fingerprint
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FingerprintInputs:
    """All deterministic inputs contributing to an evaluation run configuration fingerprint."""

    runner_condition: str
    adapter_version: str
    fixture_dataset_id: str
    fixture_dataset_version: str
    catalog_version: str
    scoring_protocol_version: str
    aggregation_policy: str      # e.g. "majority_vote_k3"
    repeat_count: int
    application_version: str
    case_ids: tuple[str, ...]
    # Model/prompt config supplied only when a real model is connected; omit if None
    model_identifier: str | None = None
    prompt_version: str | None = None
    # Deliberate exclusions
    _excluded_fields: str = (
        "Timestamps, hardware identifiers, and non-deterministic runtime metadata are excluded "
        "from the fingerprint to preserve content-addressable reproducibility."
    )

    def compute(self) -> str:
        """Compute deterministic SHA-256 fingerprint over all meaningful configuration inputs."""
        payload: dict[str, Any] = {
            "runner_condition": self.runner_condition,
            "adapter_version": self.adapter_version,
            "fixture_dataset_id": self.fixture_dataset_id,
            "fixture_dataset_version": self.fixture_dataset_version,
            "catalog_version": self.catalog_version,
            "scoring_protocol_version": self.scoring_protocol_version,
            "aggregation_policy": self.aggregation_policy,
            "repeat_count": self.repeat_count,
            "application_version": self.application_version,
            "case_ids": sorted(self.case_ids),  # stable order
        }
        if self.model_identifier is not None:
            payload["model_identifier"] = self.model_identifier
        if self.prompt_version is not None:
            payload["prompt_version"] = self.prompt_version

        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_extended_fingerprint(inputs: FingerprintInputs) -> str:
    """Compute a deterministic SHA-256 fingerprint capturing all meaningful config inputs."""
    return inputs.compute()


# ---------------------------------------------------------------------------
# Benchmark & Evaluation Readiness Audits
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BenchmarkReadinessReport:
    """Machine-checkable readiness audit of the benchmark evaluation suite.

    Audits catalog records, ground-truth review states, partition approvals,
    source-review manifest status, and supervisor decision gates.
    """

    total_catalog_cases: int
    cases_missing_locus_metadata: tuple[str, ...]
    cases_lacking_exact_source_support: tuple[str, ...]
    cases_awaiting_empirical_verification: tuple[str, ...]
    cases_without_adjudicated_ground_truth: tuple[str, ...]
    unapproved_partitions: tuple[str, ...]
    manifest_approved_sources_count: int
    is_ready_for_empirical_run: bool
    blocking_reasons: tuple[str, ...]
    pending_supervisor_decisions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_catalog_cases": self.total_catalog_cases,
            "cases_missing_locus_metadata": list(self.cases_missing_locus_metadata),
            "cases_lacking_exact_source_support": list(self.cases_lacking_exact_source_support),
            "cases_awaiting_empirical_verification": list(self.cases_awaiting_empirical_verification),
            "cases_without_adjudicated_ground_truth": list(self.cases_without_adjudicated_ground_truth),
            "unapproved_partitions": list(self.unapproved_partitions),
            "manifest_approved_sources_count": self.manifest_approved_sources_count,
            "is_ready_for_empirical_run": self.is_ready_for_empirical_run,
            "blocking_reasons": list(self.blocking_reasons),
            "pending_supervisor_decisions": list(self.pending_supervisor_decisions),
        }


def audit_benchmark_readiness(
    catalog: Sequence[CatalogRecord],
    ground_truth_reviews: Sequence[GroundTruthReviewRecord] | None = None,
    partition_assignments: Sequence[PartitionAssignmentRecord] | None = None,
    source_manifest_dict: Mapping[str, Any] | None = None,
    supervisor_decisions_status: Mapping[str, str] | None = None,
) -> BenchmarkReadinessReport:
    """Audit catalog, ground-truth, partition, source-review, and supervisor decision gates.

    Strictly offline, machine-checkable audit. Does not mutate files or approve gates.
    """
    total = len(catalog)

    missing_locus: list[str] = []
    lacking_exact_source: list[str] = []
    awaiting_verification: list[str] = []

    for c in catalog:
        # Check canonical locus metadata completeness
        if (
            c.locus_status != LocusEstablishmentStatus.ESTABLISHED
            or not c.target_uri
            or not c.parameter
            or not c.cwe_id
            or not c.vulnerability_class
        ):
            missing_locus.append(c.case_id)

        # Check exact-version source support
        if c.source_evidence_status != SourceEvidenceStatus.EXACT_VERSION_PINNED:
            lacking_exact_source.append(c.case_id)

        # Check empirical testbed verification
        if (
            c.runtime_verification_status != RuntimeVerificationStatus.EMPIRICALLY_VERIFIED
            or c.locus_verification_status != LocusVerificationStatus.EMPIRICALLY_VERIFIED
        ):
            awaiting_verification.append(c.case_id)

    # Check ground-truth reviews
    unadjudicated_gt: list[str] = []
    if ground_truth_reviews is not None:
        gt_map = {gt.case_id: gt for gt in ground_truth_reviews}
        for c in catalog:
            gt_rec = gt_map.get(c.case_id)
            if not gt_rec or gt_rec.adjudication_status != AdjudicationStatus.ADJUDICATED:
                unadjudicated_gt.append(c.case_id)
    else:
        unadjudicated_gt = [c.case_id for c in catalog]

    # Check partition approvals
    unapproved_partitions: list[str] = []
    if partition_assignments is not None:
        pa_map = {pa.case_id: pa for pa in partition_assignments}
        for c in catalog:
            pa_rec = pa_map.get(c.case_id)
            if (
                not pa_rec
                or pa_rec.partition == PartitionAssignment.UNASSIGNED
                or not pa_rec.approved_by
                or not pa_rec.approval_date
            ):
                unapproved_partitions.append(c.case_id)
    else:
        unapproved_partitions = [c.case_id for c in catalog]

    # Check manifest approved sources count
    approved_sources = 0
    if source_manifest_dict is not None:
        entries = source_manifest_dict.get("entries", [])
        if source_manifest_dict.get("approval_status") != "no_sources_approved":
            approved_sources = sum(
                1 for e in entries if isinstance(e, dict) and e.get("review_state") == "approved"
            )

    # Check supervisor decisions
    default_decisions = ("DEC-01", "DEC-02", "DEC-03", "DEC-04", "DEC-05", "DEC-06", "DEC-07", "DEC-08")
    pending_decisions: list[str] = []
    if supervisor_decisions_status is not None:
        for dec_id in sorted(supervisor_decisions_status.keys()):
            if supervisor_decisions_status[dec_id].upper() != "APPROVED":
                pending_decisions.append(dec_id)
    else:
        pending_decisions = list(default_decisions)

    # Compile blocking reasons
    reasons: list[str] = []
    if unadjudicated_gt:
        reasons.append(
            f"{len(unadjudicated_gt)}/{total} cases lack supervisor-adjudicated ground truth (DEC-03 pending)."
        )
    if unapproved_partitions:
        reasons.append(
            f"{len(unapproved_partitions)}/{total} cases are in unassigned or unapproved partitions (DEC-05 pending)."
        )
    if approved_sources == 0:
        reasons.append(
            "Source-review manifest contains 0 approved sources (approval_status='no_sources_approved')."
        )
    if missing_locus:
        reasons.append(
            f"{len(missing_locus)}/{total} cases missing established canonical locus coordinates (DEC-02 pending)."
        )
    if lacking_exact_source:
        reasons.append(
            f"{len(lacking_exact_source)}/{total} cases lack exact-version pinned source evidence."
        )
    if awaiting_verification:
        reasons.append(
            f"{len(awaiting_verification)}/{total} cases await live empirical testbed verification (DEC-08 pending)."
        )
    if pending_decisions:
        reasons.append(
            f"{len(pending_decisions)} supervisor decision gates remain pending: {', '.join(pending_decisions)}."
        )

    is_ready = (
        len(missing_locus) == 0
        and len(unadjudicated_gt) == 0
        and len(unapproved_partitions) == 0
        and approved_sources > 0
        and len(pending_decisions) == 0
    )

    return BenchmarkReadinessReport(
        total_catalog_cases=total,
        cases_missing_locus_metadata=tuple(missing_locus),
        cases_lacking_exact_source_support=tuple(lacking_exact_source),
        cases_awaiting_empirical_verification=tuple(awaiting_verification),
        cases_without_adjudicated_ground_truth=tuple(unadjudicated_gt),
        unapproved_partitions=tuple(unapproved_partitions),
        manifest_approved_sources_count=approved_sources,
        is_ready_for_empirical_run=is_ready,
        blocking_reasons=tuple(reasons),
        pending_supervisor_decisions=tuple(pending_decisions),
    )


def load_and_audit_repository_readiness(repo_root: str | Path = ".") -> BenchmarkReadinessReport:
    """Load canonical benchmark metadata artifacts from repository and audit readiness.

    Reads docs/case_catalog_draft.jsonl, docs/ground_truth_review_template.jsonl,
    docs/partition_assignment_template.jsonl, docs/source-review-manifest.json, and
    docs/SUPERVISOR_DECISION_REGISTER.md to produce a machine-checkable readiness audit.
    Zero network requests, zero container operations, zero file modifications.
    """
    root = Path(repo_root)

    # 1. Load catalog
    catalog_path = root / "docs" / "case_catalog_draft.jsonl"
    if not catalog_path.exists():
        raise CatalogValidationError(f"Missing case catalog artifact: {catalog_path}")
    catalog = validate_catalog_jsonl(catalog_path.read_text(encoding="utf-8"))

    # 2. Load ground-truth review template
    gt_path = root / "docs" / "ground_truth_review_template.jsonl"
    gt_reviews = None
    if gt_path.exists():
        gt_reviews = validate_ground_truth_review_jsonl(gt_path.read_text(encoding="utf-8"))

    # 3. Load partition assignment template
    pa_path = root / "docs" / "partition_assignment_template.jsonl"
    pa_records = None
    if pa_path.exists():
        pa_records = validate_partition_assignment_jsonl(pa_path.read_text(encoding="utf-8"))

    # 4. Load source review manifest (read-only)
    manifest_path = root / "docs" / "source-review-manifest.json"
    manifest_dict = None
    if manifest_path.exists():
        manifest_dict = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 5. Parse supervisor decision register
    reg_path = root / "docs" / "SUPERVISOR_DECISION_REGISTER.md"
    decision_statuses: dict[str, str] = {}
    if reg_path.exists():
        text = reg_path.read_text(encoding="utf-8")
        dec_matches = re.findall(r"\|\s*\*\*(DEC-\d{2})\*\*\s*\|[^|]*\|\s*`([^`]+)`\s*\|", text)
        for dec_id, status in dec_matches:
            decision_statuses[dec_id] = status

    return audit_benchmark_readiness(
        catalog=catalog,
        ground_truth_reviews=gt_reviews,
        partition_assignments=pa_records,
        source_manifest_dict=manifest_dict,
        supervisor_decisions_status=decision_statuses or None,
    )
