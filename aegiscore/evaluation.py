"""Canonical evaluation contracts, strict JSONL validators, and offline scoring framework for AEGISCORE AI.

Phase 8E.3: Offline evaluation foundation for reproducible vulnerability-assessment experiments.
Strictly prohibited: launching containers, pulling images, deploying benchmarks,
sending HTTP requests, running scanners, or integrating model providers.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from aegiscore.orchestration import FindingSeverity

__all__ = [
    # Enums
    "GroundTruthStatus",
    "AdjudicationState",
    "InclusionStatus",
    "FindingDecision",
    "MetricStatus",
    # Contracts
    "CanonicalLocus",
    "EvaluationCaseManifestRecord",
    "AssessmentFindingRecord",
    "AssessmentResultRecord",
    "EvaluationRunRecord",
    "GroundTruthRecord",
    "MetricOutputRecord",
    "CaseEvaluationOutcome",
    "EvaluationScoreSummary",
    # Exceptions
    "EvaluationError",
    "EvaluationContractError",
    "EvaluationValidationError",
    "ScoringCalculationError",
    # Validators & JSONL
    "validate_manifest_jsonl",
    "validate_ground_truth_jsonl",
    "validate_runs_jsonl",
    # Scoring
    "compute_wilson_score_interval",
    "evaluate_case_outcome",
    "aggregate_repeated_runs",
    "calculate_evaluation_scores",
    "calculate_per_category_scores",
    # Runner interfaces
    "EvaluationRunnerInterface",
    "RunnerCondition",
    "FixtureBackedRunnerAdapter",
]


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class EvaluationError(Exception):
    """Base exception for evaluation contract, validation, or scoring errors."""
    __test__ = False


class EvaluationContractError(EvaluationError):
    """Raised when an evaluation record violates structural or typed invariants."""
    __test__ = False


class EvaluationValidationError(EvaluationError):
    """Raised when JSONL content is malformed, inconsistent, or contains duplicate records."""
    __test__ = False


class ScoringCalculationError(EvaluationError):
    """Raised when scoring computation encounters irreconcilable state."""
    __test__ = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GroundTruthStatus(str, Enum):
    """Standard ground-truth state for an evaluation case locus."""

    VULNERABLE = "vulnerable"
    NON_VULNERABLE = "non_vulnerable"


class AdjudicationState(str, Enum):
    """State of ground-truth review and human adjudication."""

    UNVERIFIED = "unverified"
    REVIEWED = "reviewed"
    ADJUDICATED = "adjudicated"
    DISPUTED = "disputed"


class InclusionStatus(str, Enum):
    """Status of an evaluation scenario within the benchmark suite."""

    INCLUDED = "included"
    EXCLUDED = "excluded"
    CANDIDATE = "candidate"


class FindingDecision(str, Enum):
    """Final system decision for a test scenario or candidate finding."""

    VERIFIED = "verified"
    REJECTED = "rejected"
    ABSTAINED = "abstained"


class MetricStatus(str, Enum):
    """Computation status of an evaluation metric."""

    COMPUTED = "computed"
    UNDEFINED = "undefined"
    NOT_SUPPORTED = "not_supported"
    INSUFFICIENT_DATA = "insufficient_data"


class RunnerCondition(str, Enum):
    """Pre-registered evaluation baseline or experimental ablation condition."""

    PROPOSED_MULTI_AGENT = "proposed-multi-agent"
    BASELINE_SINGLE_AGENT = "baseline-single-agent"
    BASELINE_MA_NO_ABSTENTION = "baseline-ma-no-abstention"
    BASELINE_DAST_ZAP = "baseline-dast-zap"
    ABLATION_NO_RAG = "ablation-no-rag"
    ABLATION_NO_REVIEWER = "ablation-no-reviewer"


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

_CWE_PATTERN = re.compile(r"^CWE-[0-9]+$")
_SCHEMA_VERSION = "1.0.0"


def _require_clean_text(value: Any, field_name: str) -> str:
    """Validate that value is non-empty trimmed text without leading/trailing whitespace."""
    if not isinstance(value, str) or not value.strip():
        raise EvaluationContractError(f"{field_name} must be non-empty text")
    if value != value.strip():
        raise EvaluationContractError(f"{field_name} contains un-trimmed leading or trailing whitespace")
    return value


@dataclass(frozen=True, slots=True)
class CanonicalLocus:
    """Canonical test case locus: (target_uri, parameter, cwe_id).

    This defines the immutable Unit of Analysis ($N$) for all evaluation comparisons.
    """

    target_uri: str
    parameter: str
    cwe_id: str

    def __post_init__(self) -> None:
        _require_clean_text(self.target_uri, "target_uri")
        _require_clean_text(self.parameter, "parameter")
        _require_clean_text(self.cwe_id, "cwe_id")
        if not _CWE_PATTERN.fullmatch(self.cwe_id):
            raise EvaluationContractError(f"cwe_id '{self.cwe_id}' must match format CWE-<number>")

    @property
    def locus_key(self) -> str:
        """Normalized string representation of the canonical locus."""
        return f"{self.target_uri}:{self.parameter}:{self.cwe_id}"


@dataclass(frozen=True, slots=True)
class EvaluationCaseManifestRecord:
    """Canonical case manifest record defining an evaluation benchmark scenario."""

    case_id: str
    locus: CanonicalLocus
    benchmark_target: str
    benchmark_version: str
    vulnerability_class: str
    expected_label: GroundTruthStatus
    ground_truth_provenance: str
    review_status: AdjudicationState
    inclusion_status: InclusionStatus
    schema_version: str = _SCHEMA_VERSION
    description: str = ""

    def __post_init__(self) -> None:
        _require_clean_text(self.case_id, "case_id")
        _require_clean_text(self.benchmark_target, "benchmark_target")
        _require_clean_text(self.benchmark_version, "benchmark_version")
        _require_clean_text(self.vulnerability_class, "vulnerability_class")
        _require_clean_text(self.ground_truth_provenance, "ground_truth_provenance")

        if not isinstance(self.locus, CanonicalLocus):
            raise EvaluationContractError("locus must be an instance of CanonicalLocus")
        if not isinstance(self.expected_label, GroundTruthStatus):
            raise EvaluationContractError("expected_label must be a GroundTruthStatus enum")
        if not isinstance(self.review_status, AdjudicationState):
            raise EvaluationContractError("review_status must be an AdjudicationState enum")
        if not isinstance(self.inclusion_status, InclusionStatus):
            raise EvaluationContractError("inclusion_status must be an InclusionStatus enum")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "locus": {
                "target_uri": self.locus.target_uri,
                "parameter": self.locus.parameter,
                "cwe_id": self.locus.cwe_id,
            },
            "benchmark_target": self.benchmark_target,
            "benchmark_version": self.benchmark_version,
            "vulnerability_class": self.vulnerability_class,
            "expected_label": self.expected_label.value,
            "ground_truth_provenance": self.ground_truth_provenance,
            "review_status": self.review_status.value,
            "inclusion_status": self.inclusion_status.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvaluationCaseManifestRecord:
        try:
            locus_data = data["locus"]
            locus = CanonicalLocus(
                target_uri=locus_data["target_uri"],
                parameter=locus_data["parameter"],
                cwe_id=locus_data["cwe_id"],
            )
            return cls(
                schema_version=data.get("schema_version", _SCHEMA_VERSION),
                case_id=data["case_id"],
                locus=locus,
                benchmark_target=data["benchmark_target"],
                benchmark_version=data["benchmark_version"],
                vulnerability_class=data["vulnerability_class"],
                expected_label=GroundTruthStatus(data["expected_label"]),
                ground_truth_provenance=data["ground_truth_provenance"],
                review_status=AdjudicationState(data["review_status"]),
                inclusion_status=InclusionStatus(data["inclusion_status"]),
                description=data.get("description", ""),
            )
        except KeyError as exc:
            raise EvaluationContractError(f"Missing required manifest field: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise EvaluationContractError(f"Invalid manifest data: {exc}") from exc


@dataclass(frozen=True, slots=True)
class AssessmentFindingRecord:
    """Record of an individual vulnerability finding produced during assessment."""

    finding_id: str
    specialist_role: str
    vulnerability_identified: bool
    cwe_id: str
    severity: FindingSeverity
    decision: FindingDecision
    evidence_citations: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        _require_clean_text(self.finding_id, "finding_id")
        _require_clean_text(self.specialist_role, "specialist_role")
        _require_clean_text(self.cwe_id, "cwe_id")
        if not isinstance(self.vulnerability_identified, bool):
            raise EvaluationContractError("vulnerability_identified must be a boolean")
        if not isinstance(self.severity, FindingSeverity):
            raise EvaluationContractError("severity must be a FindingSeverity enum")
        if not isinstance(self.decision, FindingDecision):
            raise EvaluationContractError("decision must be a FindingDecision enum")
        if not isinstance(self.evidence_citations, tuple):
            raise EvaluationContractError("evidence_citations must be a tuple of citation IDs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "specialist_role": self.specialist_role,
            "vulnerability_identified": self.vulnerability_identified,
            "cwe_id": self.cwe_id,
            "severity": self.severity.value,
            "decision": self.decision.value,
            "evidence_citations": list(self.evidence_citations),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssessmentFindingRecord:
        try:
            return cls(
                finding_id=data["finding_id"],
                specialist_role=data["specialist_role"],
                vulnerability_identified=bool(data["vulnerability_identified"]),
                cwe_id=data["cwe_id"],
                severity=FindingSeverity(data["severity"]),
                decision=FindingDecision(data["decision"]),
                evidence_citations=tuple(data.get("evidence_citations", ())),
                rationale=data.get("rationale", ""),
            )
        except KeyError as exc:
            raise EvaluationContractError(f"Missing required finding field: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise EvaluationContractError(f"Invalid finding data: {exc}") from exc


@dataclass(frozen=True, slots=True)
class AssessmentResultRecord:
    """Outcome of an assessment execution on a single case locus."""

    case_id: str
    run_id: str
    decision: FindingDecision
    findings: tuple[AssessmentFindingRecord, ...] = ()
    primary_severity: FindingSeverity | None = None
    evidence_citations: tuple[str, ...] = ()
    error_status: str | None = None
    is_incomplete: bool = False
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_clean_text(self.case_id, "case_id")
        _require_clean_text(self.run_id, "run_id")
        if not isinstance(self.decision, FindingDecision):
            raise EvaluationContractError("decision must be a FindingDecision enum")
        if not isinstance(self.findings, tuple):
            raise EvaluationContractError("findings must be a tuple")
        if self.primary_severity is not None and not isinstance(self.primary_severity, FindingSeverity):
            raise EvaluationContractError("primary_severity must be a FindingSeverity enum or None")
        if not isinstance(self.evidence_citations, tuple):
            raise EvaluationContractError("evidence_citations must be a tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "run_id": self.run_id,
            "decision": self.decision.value,
            "findings": [f.to_dict() for f in self.findings],
            "primary_severity": self.primary_severity.value if self.primary_severity else None,
            "evidence_citations": list(self.evidence_citations),
            "error_status": self.error_status,
            "is_incomplete": self.is_incomplete,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssessmentResultRecord:
        try:
            findings = tuple(AssessmentFindingRecord.from_dict(f) for f in data.get("findings", ()))
            sev = FindingSeverity(data["primary_severity"]) if data.get("primary_severity") else None
            return cls(
                schema_version=data.get("schema_version", _SCHEMA_VERSION),
                case_id=data["case_id"],
                run_id=data["run_id"],
                decision=FindingDecision(data["decision"]),
                findings=findings,
                primary_severity=sev,
                evidence_citations=tuple(data.get("evidence_citations", ())),
                error_status=data.get("error_status"),
                is_incomplete=bool(data.get("is_incomplete", False)),
            )
        except KeyError as exc:
            raise EvaluationContractError(f"Missing required assessment result field: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise EvaluationContractError(f"Invalid assessment result data: {exc}") from exc


@dataclass(frozen=True, slots=True)
class EvaluationRunRecord:
    """Record of a single execution episode of a runner on an evaluation case."""

    run_id: str
    runner_id: str
    case_id: str
    repeat_index: int
    result: AssessmentResultRecord
    reproducibility_metadata: Mapping[str, str] = field(default_factory=dict)
    start_time_utc: str | None = None
    end_time_utc: str | None = None
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_clean_text(self.run_id, "run_id")
        _require_clean_text(self.runner_id, "runner_id")
        _require_clean_text(self.case_id, "case_id")
        if not isinstance(self.repeat_index, int) or self.repeat_index < 0:
            raise EvaluationContractError("repeat_index must be a non-negative integer")
        if not isinstance(self.result, AssessmentResultRecord):
            raise EvaluationContractError("result must be an instance of AssessmentResultRecord")
        if self.result.case_id != self.case_id:
            raise EvaluationContractError(f"case_id mismatch between run '{self.case_id}' and result '{self.result.case_id}'")
        if self.result.run_id != self.run_id:
            raise EvaluationContractError(f"run_id mismatch between run '{self.run_id}' and result '{self.result.run_id}'")

        # Freeze metadata
        object.__setattr__(self, "reproducibility_metadata", MappingProxyType(dict(self.reproducibility_metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "runner_id": self.runner_id,
            "case_id": self.case_id,
            "repeat_index": self.repeat_index,
            "start_time_utc": self.start_time_utc,
            "end_time_utc": self.end_time_utc,
            "result": self.result.to_dict(),
            "reproducibility_metadata": dict(self.reproducibility_metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvaluationRunRecord:
        try:
            result = AssessmentResultRecord.from_dict(data["result"])
            return cls(
                schema_version=data.get("schema_version", _SCHEMA_VERSION),
                run_id=data["run_id"],
                runner_id=data["runner_id"],
                case_id=data["case_id"],
                repeat_index=int(data["repeat_index"]),
                result=result,
                reproducibility_metadata=data.get("reproducibility_metadata", {}),
                start_time_utc=data.get("start_time_utc"),
                end_time_utc=data.get("end_time_utc"),
            )
        except KeyError as exc:
            raise EvaluationContractError(f"Missing required run field: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise EvaluationContractError(f"Invalid run data: {exc}") from exc


@dataclass(frozen=True, slots=True)
class GroundTruthRecord:
    """Canonical adjudicated ground-truth specification for an evaluation case."""

    case_id: str
    locus: CanonicalLocus
    expected_status: GroundTruthStatus
    vulnerability_class: str
    evidence_reference: str
    adjudication_state: AdjudicationState
    provenance: str
    expected_severity: FindingSeverity | None = None
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_clean_text(self.case_id, "case_id")
        _require_clean_text(self.vulnerability_class, "vulnerability_class")
        _require_clean_text(self.evidence_reference, "evidence_reference")
        _require_clean_text(self.provenance, "provenance")

        if not isinstance(self.locus, CanonicalLocus):
            raise EvaluationContractError("locus must be an instance of CanonicalLocus")
        if not isinstance(self.expected_status, GroundTruthStatus):
            raise EvaluationContractError("expected_status must be a GroundTruthStatus enum")
        if not isinstance(self.adjudication_state, AdjudicationState):
            raise EvaluationContractError("adjudication_state must be an AdjudicationState enum")
        if self.expected_severity is not None and not isinstance(self.expected_severity, FindingSeverity):
            raise EvaluationContractError("expected_severity must be a FindingSeverity enum or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "locus": {
                "target_uri": self.locus.target_uri,
                "parameter": self.locus.parameter,
                "cwe_id": self.locus.cwe_id,
            },
            "expected_status": self.expected_status.value,
            "vulnerability_class": self.vulnerability_class,
            "expected_severity": self.expected_severity.value if self.expected_severity else None,
            "evidence_reference": self.evidence_reference,
            "adjudication_state": self.adjudication_state.value,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GroundTruthRecord:
        try:
            locus_data = data["locus"]
            locus = CanonicalLocus(
                target_uri=locus_data["target_uri"],
                parameter=locus_data["parameter"],
                cwe_id=locus_data["cwe_id"],
            )
            sev = FindingSeverity(data["expected_severity"]) if data.get("expected_severity") else None
            return cls(
                schema_version=data.get("schema_version", _SCHEMA_VERSION),
                case_id=data["case_id"],
                locus=locus,
                expected_status=GroundTruthStatus(data["expected_status"]),
                vulnerability_class=data["vulnerability_class"],
                expected_severity=sev,
                evidence_reference=data["evidence_reference"],
                adjudication_state=AdjudicationState(data["adjudication_state"]),
                provenance=data["provenance"],
            )
        except KeyError as exc:
            raise EvaluationContractError(f"Missing required ground truth field: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise EvaluationContractError(f"Invalid ground truth data: {exc}") from exc


def compute_wilson_score_interval(
    k: int,
    n: int,
    confidence: float = 0.95,
) -> tuple[float | None, float | None]:
    """Compute the Wilson score confidence interval for a single binomial proportion.

    Exact for small sample sizes; avoids normal-approximation degeneracies at boundaries.
    Returns (None, None) when n <= 0.
    """
    if n <= 0 or k < 0 or k > n:
        return (None, None)
    z = 1.959963984540054  # 95% two-sided normal quantile
    p = k / n
    n_tilde = n + z * z
    p_tilde = (k + (z * z) / 2.0) / n_tilde
    margin = (z / n_tilde) * math.sqrt((k * (n - k) / n + (z * z) / 4.0))
    lower = max(0.0, p_tilde - margin)
    upper = min(1.0, p_tilde + margin)
    return (round(lower, 4), round(upper, 4))


@dataclass(frozen=True, slots=True)
class MetricOutputRecord:
    """Standardized record of a calculated evaluation metric with explicit denominator audit."""

    metric_name: str
    value: float | None
    definition: str
    numerator: float | int | None
    denominator: float | int | None
    aggregation_unit: str = "canonical_case_locus"
    included_cases: int = 0
    excluded_cases: int = 0
    abstained_cases: int = 0
    status: MetricStatus = MetricStatus.COMPUTED
    limitations: tuple[str, ...] = ()
    ci_lower: float | None = None
    ci_upper: float | None = None
    ci_method: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "definition": self.definition,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "aggregation_unit": self.aggregation_unit,
            "included_cases": self.included_cases,
            "excluded_cases": self.excluded_cases,
            "abstained_cases": self.abstained_cases,
            "status": self.status.value,
            "limitations": list(self.limitations),
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "ci_method": self.ci_method,
        }


# ---------------------------------------------------------------------------
# Strict JSONL Validation
# ---------------------------------------------------------------------------

def _parse_jsonl_lines(content_or_lines: str | Sequence[str]) -> list[dict[str, Any]]:
    """Parse JSONL content into raw JSON dictionaries, rejecting malformed lines."""
    if isinstance(content_or_lines, str):
        raw_lines = content_or_lines.strip().splitlines()
    else:
        raw_lines = list(content_or_lines)

    parsed = []
    for line_idx, line in enumerate(raw_lines, 1):
        stripped = line.strip() if isinstance(line, str) else ""
        if not stripped or stripped.startswith("#"):
            continue
        try:
            record_dict = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise EvaluationValidationError(f"Line {line_idx}: Malformed JSON in JSONL stream: {exc.msg}") from exc
        if not isinstance(record_dict, dict):
            raise EvaluationValidationError(f"Line {line_idx}: JSONL record must be a JSON object")
        parsed.append(record_dict)

    if not parsed:
        raise EvaluationValidationError("JSONL stream is empty or contains no valid records")
    return parsed


def validate_manifest_jsonl(content_or_lines: str | Sequence[str]) -> tuple[EvaluationCaseManifestRecord, ...]:
    """Statically parse and validate an evaluation case manifest JSONL stream.

    Detects duplicate case IDs and enforces schema versioning and canonical locus rules.
    """
    records = _parse_jsonl_lines(content_or_lines)
    seen_case_ids: set[str] = set()
    seen_loci: set[str] = set()
    manifest_records: list[EvaluationCaseManifestRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            manifest_rec = EvaluationCaseManifestRecord.from_dict(rec_dict)
        except EvaluationContractError as exc:
            raise EvaluationValidationError(f"Record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}") from exc

        if manifest_rec.case_id in seen_case_ids:
            raise EvaluationValidationError(f"Duplicate case_id '{manifest_rec.case_id}' detected at record {idx}")
        seen_case_ids.add(manifest_rec.case_id)

        locus_key = manifest_rec.locus.locus_key
        if locus_key in seen_loci:
            raise EvaluationValidationError(
                f"Duplicate canonical locus '{locus_key}' detected for case '{manifest_rec.case_id}' at record {idx}"
            )
        seen_loci.add(locus_key)

        manifest_records.append(manifest_rec)

    return tuple(manifest_records)


def validate_ground_truth_jsonl(
    content_or_lines: str | Sequence[str],
    known_manifest_cases: set[str] | None = None,
) -> tuple[GroundTruthRecord, ...]:
    """Statically parse and validate a ground-truth JSONL stream.

    Enforces adjudication completeness and checks foreign keys against manifest cases.
    """
    records = _parse_jsonl_lines(content_or_lines)
    seen_case_ids: set[str] = set()
    gt_records: list[GroundTruthRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            gt_rec = GroundTruthRecord.from_dict(rec_dict)
        except EvaluationContractError as exc:
            raise EvaluationValidationError(f"Record {idx} ({rec_dict.get('case_id', 'unknown')}): {exc}") from exc

        if gt_rec.case_id in seen_case_ids:
            raise EvaluationValidationError(f"Duplicate ground-truth case_id '{gt_rec.case_id}' at record {idx}")
        seen_case_ids.add(gt_rec.case_id)

        if known_manifest_cases is not None and gt_rec.case_id not in known_manifest_cases:
            raise EvaluationValidationError(
                f"Ground-truth case_id '{gt_rec.case_id}' is not in the approved manifest cases"
            )

        gt_records.append(gt_rec)

    return tuple(gt_records)


def validate_runs_jsonl(
    content_or_lines: str | Sequence[str],
    known_manifest_cases: set[str] | None = None,
) -> tuple[EvaluationRunRecord, ...]:
    """Statically parse and validate an evaluation run log JSONL stream.

    Validates schema types, detects duplicate run IDs, and verifies that repeated
    trials (repeat_index) do not introduce conflicting records.
    """
    records = _parse_jsonl_lines(content_or_lines)
    seen_run_ids: set[str] = set()
    seen_runner_case_repeats: set[tuple[str, str, int]] = set()
    run_records: list[EvaluationRunRecord] = []

    for idx, rec_dict in enumerate(records, 1):
        try:
            run_rec = EvaluationRunRecord.from_dict(rec_dict)
        except EvaluationContractError as exc:
            raise EvaluationValidationError(f"Record {idx} ({rec_dict.get('run_id', 'unknown')}): {exc}") from exc

        if run_rec.run_id in seen_run_ids:
            raise EvaluationValidationError(f"Duplicate run_id '{run_rec.run_id}' detected at record {idx}")
        seen_run_ids.add(run_rec.run_id)

        key = (run_rec.runner_id, run_rec.case_id, run_rec.repeat_index)
        if key in seen_runner_case_repeats:
            raise EvaluationValidationError(
                f"Duplicate run episode for runner '{run_rec.runner_id}', case '{run_rec.case_id}', "
                f"repeat_index {run_rec.repeat_index} at record {idx}"
            )
        seen_runner_case_repeats.add(key)

        if known_manifest_cases is not None and run_rec.case_id not in known_manifest_cases:
            raise EvaluationValidationError(
                f"Run record '{run_rec.run_id}' references unknown case_id '{run_rec.case_id}'"
            )

        run_records.append(run_rec)

    return tuple(run_records)


# ---------------------------------------------------------------------------
# Offline Scoring Pipeline
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CaseEvaluationOutcome:
    """Per-case adjudication outcome for transparent auditing and confusion matrix construction."""

    case_id: str
    locus: CanonicalLocus
    ground_truth: GroundTruthStatus
    system_decision: FindingDecision
    classification: str  # "TP", "FP", "FN", "TN", "ABSTAINED_POSITIVE", "ABSTAINED_NEGATIVE"
    is_covered: bool
    predicted_severity: FindingSeverity | None = None
    expected_severity: FindingSeverity | None = None
    severity_match: bool | None = None
    vulnerability_class: str = ""
    is_incomplete: bool = False
    error_status: str | None = None
    evidence_citations_count: int = 0
    uncited_findings_count: int = 0
    reviewer_rejection: bool = False
    specialist_disagreement: bool = False
    adjudication_state: AdjudicationState = AdjudicationState.ADJUDICATED


def evaluate_case_outcome(
    result: AssessmentResultRecord,
    ground_truth: GroundTruthRecord,
) -> CaseEvaluationOutcome:
    """Evaluate an assessment result against ground truth for a single canonical locus.

    INVARIANTS:
    1. Abstaining on a ground-truth VULNERABLE target counts as an empirical False Negative (FN).
    2. Abstaining on a ground-truth NON-VULNERABLE target is an ABSTENTION, NOT a True Negative (TN).
    3. Abstentions are excluded from covered predictions (is_covered=False).
    4. Incomplete executions (is_incomplete=True) fail closed: excluded from covered,
       never counted as True Negatives or verified findings.
    """
    if result.case_id != ground_truth.case_id:
        raise ScoringCalculationError(
            f"Case ID mismatch: result='{result.case_id}' vs ground_truth='{ground_truth.case_id}'"
        )

    decision = result.decision
    gt = ground_truth.expected_status
    is_inc = result.is_incomplete

    if is_inc:
        # Incomplete execution fails closed: never covered, never a True Negative
        is_covered = False
        if gt == GroundTruthStatus.VULNERABLE:
            classification = "FN"
        else:
            classification = "ABSTAINED_NEGATIVE"
    elif gt == GroundTruthStatus.VULNERABLE:
        if decision == FindingDecision.VERIFIED:
            classification = "TP"
            is_covered = True
        elif decision == FindingDecision.REJECTED:
            classification = "FN"
            is_covered = True
        elif decision == FindingDecision.ABSTAINED:
            classification = "ABSTAINED_POSITIVE"
            is_covered = False
        else:
            raise ScoringCalculationError(f"Unexpected decision '{decision}'")
    else:  # NON_VULNERABLE
        if decision == FindingDecision.VERIFIED:
            classification = "FP"
            is_covered = True
        elif decision == FindingDecision.REJECTED:
            classification = "TN"
            is_covered = True
        elif decision == FindingDecision.ABSTAINED:
            classification = "ABSTAINED_NEGATIVE"
            is_covered = False
        else:
            raise ScoringCalculationError(f"Unexpected decision '{decision}'")

    # Severity matching
    pred_sev = result.primary_severity
    exp_sev = ground_truth.expected_severity
    sev_match = (pred_sev == exp_sev) if (pred_sev is not None and exp_sev is not None) else None

    # Audit evidence citations and findings
    total_citations = len(result.evidence_citations)
    uncited_findings = sum(1 for f in result.findings if not f.evidence_citations)

    # Detect reviewer rejection and specialist disagreement signals
    err_str = (result.error_status or "").lower()
    reviewer_rejection = (
        decision == FindingDecision.REJECTED or
        "reviewer_rejection" in err_str or
        "rejection" in err_str
    )
    specialist_disagreement = (
        "specialist_disagreement" in err_str or
        "disagree" in err_str
    )

    return CaseEvaluationOutcome(
        case_id=result.case_id,
        locus=ground_truth.locus,
        ground_truth=gt,
        system_decision=decision,
        classification=classification,
        is_covered=is_covered,
        predicted_severity=pred_sev,
        expected_severity=exp_sev,
        severity_match=sev_match,
        vulnerability_class=ground_truth.vulnerability_class,
        is_incomplete=is_inc,
        error_status=result.error_status,
        evidence_citations_count=total_citations,
        uncited_findings_count=uncited_findings,
        reviewer_rejection=reviewer_rejection,
        specialist_disagreement=specialist_disagreement,
        adjudication_state=ground_truth.adjudication_state,
    )


def aggregate_repeated_runs(
    runs: Sequence[EvaluationRunRecord],
    *,
    strategy: str = "majority_vote",
) -> tuple[AssessmentResultRecord, ...]:
    """Aggregate repeated trial runs (K=3) across canonical case loci without inflating sample size.

    Majority voting requires >= 2/3 agreement across trials.
    If outcomes are split without majority, the system fails closed to ABSTAINED.
    Preserves incomplete status and error diagnostics from trial runs.
    """
    if not runs:
        raise ScoringCalculationError("No runs provided for aggregation")

    # Group runs by case_id
    runs_by_case: dict[str, list[EvaluationRunRecord]] = {}
    for r in runs:
        runs_by_case.setdefault(r.case_id, []).append(r)

    aggregated: list[AssessmentResultRecord] = []
    for case_id, case_runs in sorted(runs_by_case.items()):
        if strategy == "majority_vote":
            # Tally decisions
            decision_counts: dict[FindingDecision, int] = {}
            for cr in case_runs:
                decision_counts[cr.result.decision] = decision_counts.get(cr.result.decision, 0) + 1

            total_runs = len(case_runs)
            threshold = (total_runs // 2) + 1  # >= 2 for K=3

            majority_decision: FindingDecision = FindingDecision.ABSTAINED
            for dec, count in decision_counts.items():
                if count >= threshold:
                    majority_decision = dec
                    break

            # Find representative run matching majority decision
            rep_run = next((cr for cr in case_runs if cr.result.decision == majority_decision), case_runs[0])

            # Preserve incomplete status and error diagnostics if any trial encountered failure
            agg_incomplete = any(cr.result.is_incomplete for cr in case_runs)
            agg_error = rep_run.result.error_status or next(
                (cr.result.error_status for cr in case_runs if cr.result.error_status), None
            )

            agg_result = AssessmentResultRecord(
                case_id=case_id,
                run_id=f"agg-{case_id}",
                decision=majority_decision,
                findings=rep_run.result.findings,
                primary_severity=rep_run.result.primary_severity,
                evidence_citations=rep_run.result.evidence_citations,
                error_status=agg_error,
                is_incomplete=agg_incomplete,
            )
            aggregated.append(agg_result)
        else:
            raise ScoringCalculationError(f"Unsupported aggregation strategy '{strategy}'")

    return tuple(aggregated)


@dataclass(frozen=True, slots=True)
class EvaluationScoreSummary:
    """Complete confusion matrix and metric outputs from an offline scoring run."""

    # Confusion matrix counts
    tp_count: int
    fp_count: int
    fn_count: int  # Includes explicit misses and abstained positives
    tn_count: int  # Explicit non-vulnerable rejections only
    abstained_positive_count: int
    abstained_negative_count: int
    total_cases: int

    # Candidate finding counts for VFR
    total_candidate_findings: int
    verified_candidate_findings: int

    # Calculated metrics
    metrics: Mapping[str, MetricOutputRecord]
    case_outcomes: tuple[CaseEvaluationOutcome, ...]

    # Extended operational counts
    incomplete_cases_count: int = 0
    failed_cases_count: int = 0
    reviewer_rejections_count: int = 0
    specialist_disagreements_count: int = 0


def calculate_evaluation_scores(
    outcomes: Sequence[CaseEvaluationOutcome],
    *,
    total_raw_candidates: int | None = None,
) -> EvaluationScoreSummary:
    """Calculate standard and selective evaluation metrics from case evaluation outcomes.

    Handles zero denominators rigorously by reporting MetricStatus.UNDEFINED rather
    than fabricating 0.0 or 1.0 values. Computes Wilson score intervals for binomial proportions.
    """
    if not outcomes:
        raise ScoringCalculationError("Cannot calculate evaluation scores on empty outcomes")

    tp = 0
    fp = 0
    fn_explicit = 0
    tn = 0
    abs_pos = 0
    abs_neg = 0

    for out in outcomes:
        c = out.classification
        if c == "TP":
            tp += 1
        elif c == "FP":
            fp += 1
        elif c == "FN":
            fn_explicit += 1
        elif c == "TN":
            tn += 1
        elif c == "ABSTAINED_POSITIVE":
            abs_pos += 1
        elif c == "ABSTAINED_NEGATIVE":
            abs_neg += 1
        else:
            raise ScoringCalculationError(f"Unknown outcome classification '{c}'")

    total_cases = len(outcomes)
    # Total FN in standard detection includes positive abstentions (abstaining on a vulnerability misses it)
    total_fn = fn_explicit + abs_pos
    total_abstained = abs_pos + abs_neg
    covered_cases = total_cases - total_abstained

    # Extended operational tallies
    incomplete_count = sum(1 for out in outcomes if getattr(out, "is_incomplete", False))
    failed_count = sum(1 for out in outcomes if getattr(out, "error_status", None) is not None)
    reviewer_rejections = sum(1 for out in outcomes if getattr(out, "reviewer_rejection", False))
    specialist_disagreements = sum(1 for out in outcomes if getattr(out, "specialist_disagreement", False))
    total_citations = sum(getattr(out, "evidence_citations_count", 0) for out in outcomes)
    uncited_findings = sum(getattr(out, "uncited_findings_count", 0) for out in outcomes)

    metrics_map: dict[str, MetricOutputRecord] = {}

    # 1. Precision = TP / (TP + FP)
    prec_denom = tp + fp
    if prec_denom > 0:
        prec_val = tp / prec_denom
        prec_status = MetricStatus.COMPUTED
        p_ci_l, p_ci_u = compute_wilson_score_interval(tp, prec_denom)
        p_ci_m = "wilson_score"
    else:
        prec_val = None
        prec_status = MetricStatus.UNDEFINED
        p_ci_l, p_ci_u, p_ci_m = None, None, None

    metrics_map["precision"] = MetricOutputRecord(
        metric_name="precision",
        value=prec_val,
        definition="Proportion of verified vulnerability findings that are genuine (TP / (TP + FP))",
        numerator=tp,
        denominator=prec_denom,
        status=prec_status,
        included_cases=prec_denom,
        limitations=(
            "Undefined when system reports zero positive findings.",
            "Conditioned on the non-abstained positive predictions denominator (TP + FP).",
        ),
        ci_lower=p_ci_l,
        ci_upper=p_ci_u,
        ci_method=p_ci_m,
    )

    # 2. Recall = TP / (TP + FN)
    rec_denom = tp + total_fn
    if rec_denom > 0:
        rec_val = tp / rec_denom
        rec_status = MetricStatus.COMPUTED
        r_ci_l, r_ci_u = compute_wilson_score_interval(tp, rec_denom)
        r_ci_m = "wilson_score"
    else:
        rec_val = None
        rec_status = MetricStatus.UNDEFINED
        r_ci_l, r_ci_u, r_ci_m = None, None, None

    metrics_map["recall"] = MetricOutputRecord(
        metric_name="recall",
        value=rec_val,
        definition="Proportion of genuine vulnerabilities detected and verified (TP / (TP + FN))",
        numerator=tp,
        denominator=rec_denom,
        status=rec_status,
        included_cases=rec_denom,
        limitations=("Abstentions on positive cases penalize recall as FN.",),
        ci_lower=r_ci_l,
        ci_upper=r_ci_u,
        ci_method=r_ci_m,
    )

    # 3. F1-Score = 2 * (P * R) / (P + R)
    if prec_val is not None and rec_val is not None and (prec_val + rec_val) > 0:
        f1_val = 2.0 * (prec_val * rec_val) / (prec_val + rec_val)
        f1_status = MetricStatus.COMPUTED
    else:
        f1_val = None
        f1_status = MetricStatus.UNDEFINED

    metrics_map["f1_score"] = MetricOutputRecord(
        metric_name="f1_score",
        value=f1_val,
        definition="Harmonic mean of precision and recall",
        numerator=None,
        denominator=None,
        status=f1_status,
        limitations=(
            "Non-linear derived metric; binomial single-proportion intervals do not apply.",
            "Report constituent intervals (Precision and Recall) or case-resampled percentile bootstrap.",
        ),
        ci_lower=None,
        ci_upper=None,
        ci_method="not_applicable",
    )

    # 4. False-Positive Rate = FP / (FP + TN_explicit)
    # Denominator: total negative control cases evaluated
    fpr_denom = fp + tn + abs_neg
    if fpr_denom > 0:
        fpr_val = fp / fpr_denom
        fpr_status = MetricStatus.COMPUTED
        fpr_ci_l, fpr_ci_u = compute_wilson_score_interval(fp, fpr_denom)
        fpr_ci_m = "wilson_score"
    else:
        fpr_val = None
        fpr_status = MetricStatus.UNDEFINED
        fpr_ci_l, fpr_ci_u, fpr_ci_m = None, None, None

    metrics_map["false_positive_rate"] = MetricOutputRecord(
        metric_name="false_positive_rate",
        value=fpr_val,
        definition="Proportion of negative controls incorrectly flagged as vulnerable (FP / Total Negatives)",
        numerator=fp,
        denominator=fpr_denom,
        status=fpr_status,
        included_cases=fpr_denom,
        ci_lower=fpr_ci_l,
        ci_upper=fpr_ci_u,
        ci_method=fpr_ci_m,
    )

    # 5. Specificity = TN / (FP + TN + abs_neg)
    if fpr_denom > 0:
        spec_val = tn / fpr_denom
        spec_status = MetricStatus.COMPUTED
        spec_ci_l, spec_ci_u = compute_wilson_score_interval(tn, fpr_denom)
        spec_ci_m = "wilson_score"
    else:
        spec_val = None
        spec_status = MetricStatus.UNDEFINED
        spec_ci_l, spec_ci_u, spec_ci_m = None, None, None

    metrics_map["specificity"] = MetricOutputRecord(
        metric_name="specificity",
        value=spec_val,
        definition="Proportion of negative controls correctly identified and rejected without false alarms (TN / Total Negatives)",
        numerator=tn,
        denominator=fpr_denom,
        status=spec_status,
        included_cases=fpr_denom,
        limitations=("Undefined when evaluation includes zero negative control cases.",),
        ci_lower=spec_ci_l,
        ci_upper=spec_ci_u,
        ci_method=spec_ci_m,
    )

    # 6. Abstention Rate = Total Abstained / Total Cases
    if total_cases > 0:
        ar_val = total_abstained / total_cases
        ar_status = MetricStatus.COMPUTED
        ar_ci_l, ar_ci_u = compute_wilson_score_interval(total_abstained, total_cases)
        ar_ci_m = "wilson_score"
    else:
        ar_val = None
        ar_status = MetricStatus.UNDEFINED
        ar_ci_l, ar_ci_u, ar_ci_m = None, None, None

    metrics_map["abstention_rate"] = MetricOutputRecord(
        metric_name="abstention_rate",
        value=ar_val,
        definition="Fraction of cases where system withheld judgment (Total Abstained / Total Cases)",
        numerator=total_abstained,
        denominator=total_cases,
        status=ar_status,
        abstained_cases=total_abstained,
        ci_lower=ar_ci_l,
        ci_upper=ar_ci_u,
        ci_method=ar_ci_m,
    )

    # 7. Coverage = Covered Cases / Total Cases
    if total_cases > 0:
        cov_val = covered_cases / total_cases
        cov_status = MetricStatus.COMPUTED
        cov_ci_l, cov_ci_u = compute_wilson_score_interval(covered_cases, total_cases)
        cov_ci_m = "wilson_score"
    else:
        cov_val = None
        cov_status = MetricStatus.UNDEFINED
        cov_ci_l, cov_ci_u, cov_ci_m = None, None, None

    metrics_map["coverage"] = MetricOutputRecord(
        metric_name="coverage",
        value=cov_val,
        definition="Fraction of cases receiving definitive reporting decisions (Covered / Total Cases)",
        numerator=covered_cases,
        denominator=total_cases,
        status=cov_status,
        ci_lower=cov_ci_l,
        ci_upper=cov_ci_u,
        ci_method=cov_ci_m,
    )

    # 8. Selective Risk R(Phi) = FP_covered / (TP_covered + FP_covered) = 1 - Precision
    if prec_val is not None:
        sel_risk_val = 1.0 - prec_val
        sel_risk_status = MetricStatus.COMPUTED
        sr_ci_l, sr_ci_u = compute_wilson_score_interval(fp, prec_denom)
        sr_ci_m = "wilson_score"
    else:
        sel_risk_val = None
        sel_risk_status = MetricStatus.UNDEFINED
        sr_ci_l, sr_ci_u, sr_ci_m = None, None, None

    metrics_map["selective_risk"] = MetricOutputRecord(
        metric_name="selective_risk",
        value=sel_risk_val,
        definition="Empirical error rate on the covered non-abstained predictions (1 - Precision)",
        numerator=fp,
        denominator=prec_denom,
        status=sel_risk_status,
        limitations=("Explicitly evaluated over the non-abstained covered subset only.",),
        ci_lower=sr_ci_l,
        ci_upper=sr_ci_u,
        ci_method=sr_ci_m,
    )

    # 9. Verified Finding Rate = Verified Findings / Total Candidate Findings
    cand_count = total_raw_candidates if total_raw_candidates is not None else tp
    vfr_denom = cand_count
    if vfr_denom > 0:
        vfr_val = tp / vfr_denom
        vfr_status = MetricStatus.COMPUTED
        vfr_ci_l, vfr_ci_u = compute_wilson_score_interval(tp, vfr_denom)
        vfr_ci_m = "wilson_score"
    else:
        vfr_val = None
        vfr_status = MetricStatus.UNDEFINED
        vfr_ci_l, vfr_ci_u, vfr_ci_m = None, None, None

    metrics_map["verified_finding_rate"] = MetricOutputRecord(
        metric_name="verified_finding_rate",
        value=vfr_val,
        definition="Ratio of verified candidate findings to total generated candidate findings",
        numerator=tp,
        denominator=vfr_denom,
        status=vfr_status,
        ci_lower=vfr_ci_l,
        ci_upper=vfr_ci_u,
        ci_method=vfr_ci_m,
    )

    # 10. Evidence Grounding Rate = Grounded Candidate Findings / Total Candidate Findings
    if vfr_denom > 0:
        grounded_count = max(0, vfr_denom - uncited_findings)
        egr_val = grounded_count / vfr_denom
        egr_status = MetricStatus.COMPUTED
        egr_ci_l, egr_ci_u = compute_wilson_score_interval(grounded_count, vfr_denom)
        egr_ci_m = "wilson_score"
    else:
        grounded_count = 0
        egr_val = None
        egr_status = MetricStatus.UNDEFINED
        egr_ci_l, egr_ci_u, egr_ci_m = None, None, None

    metrics_map["evidence_grounding_rate"] = MetricOutputRecord(
        metric_name="evidence_grounding_rate",
        value=egr_val,
        definition="Proportion of candidate findings supported by non-empty evidence citations",
        numerator=grounded_count,
        denominator=vfr_denom,
        status=egr_status,
        limitations=("Undefined when system produces zero candidate findings.",),
        ci_lower=egr_ci_l,
        ci_upper=egr_ci_u,
        ci_method=egr_ci_m,
    )

    # 11. Citation Validation Rate = Valid Citations / Total Citations
    citation_denom = total_citations + uncited_findings
    if citation_denom > 0:
        cvr_val = total_citations / citation_denom
        cvr_status = MetricStatus.COMPUTED
        cvr_ci_l, cvr_ci_u = compute_wilson_score_interval(total_citations, citation_denom)
        cvr_ci_m = "wilson_score"
    else:
        cvr_val = None
        cvr_status = MetricStatus.UNDEFINED
        cvr_ci_l, cvr_ci_u, cvr_ci_m = None, None, None

    metrics_map["citation_validation_rate"] = MetricOutputRecord(
        metric_name="citation_validation_rate",
        value=cvr_val,
        definition="Proportion of candidate findings with verified citations against evidence bundle",
        numerator=total_citations,
        denominator=citation_denom,
        status=cvr_status,
        limitations=("Undefined when zero citations or findings are present in the evaluation run.",),
        ci_lower=cvr_ci_l,
        ci_upper=cvr_ci_u,
        ci_method=cvr_ci_m,
    )

    # 12. Incomplete Rate = Incomplete Cases / Total Cases
    if total_cases > 0:
        inc_val = incomplete_count / total_cases
        inc_status = MetricStatus.COMPUTED
        inc_ci_l, inc_ci_u = compute_wilson_score_interval(incomplete_count, total_cases)
        inc_ci_m = "wilson_score"
    else:
        inc_val = None
        inc_status = MetricStatus.UNDEFINED
        inc_ci_l, inc_ci_u, inc_ci_m = None, None, None

    metrics_map["incomplete_rate"] = MetricOutputRecord(
        metric_name="incomplete_rate",
        value=inc_val,
        definition="Fraction of evaluation cases that encountered execution errors or incomplete processing",
        numerator=incomplete_count,
        denominator=total_cases,
        status=inc_status,
        limitations=("Incomplete cases fail closed and are never counted as covered predictions.",),
        ci_lower=inc_ci_l,
        ci_upper=inc_ci_u,
        ci_method=inc_ci_m,
    )

    # 13. Reviewer Rejection Rate = Reviewer Rejections / Total Cases
    if total_cases > 0:
        rr_val = reviewer_rejections / total_cases
        rr_status = MetricStatus.COMPUTED
        rr_ci_l, rr_ci_u = compute_wilson_score_interval(reviewer_rejections, total_cases)
        rr_ci_m = "wilson_score"
    else:
        rr_val = None
        rr_status = MetricStatus.UNDEFINED
        rr_ci_l, rr_ci_u, rr_ci_m = None, None, None

    metrics_map["reviewer_rejection_rate"] = MetricOutputRecord(
        metric_name="reviewer_rejection_rate",
        value=rr_val,
        definition="Fraction of cases where adversarial evidence reviewer challenged or rejected findings",
        numerator=reviewer_rejections,
        denominator=total_cases,
        status=rr_status,
        ci_lower=rr_ci_l,
        ci_upper=rr_ci_u,
        ci_method=rr_ci_m,
    )

    # 14. Specialist Disagreement Rate = Disagreements / Total Cases
    if total_cases > 0:
        sd_val = specialist_disagreements / total_cases
        sd_status = MetricStatus.COMPUTED
        sd_ci_l, sd_ci_u = compute_wilson_score_interval(specialist_disagreements, total_cases)
        sd_ci_m = "wilson_score"
    else:
        sd_val = None
        sd_status = MetricStatus.UNDEFINED
        sd_ci_l, sd_ci_u, sd_ci_m = None, None, None

    metrics_map["specialist_disagreement_rate"] = MetricOutputRecord(
        metric_name="specialist_disagreement_rate",
        value=sd_val,
        definition="Fraction of cases exhibiting conflicting specialist findings",
        numerator=specialist_disagreements,
        denominator=total_cases,
        status=sd_status,
        ci_lower=sd_ci_l,
        ci_upper=sd_ci_u,
        ci_method=sd_ci_m,
    )

    # 15. Calibration Metrics: Explicitly Not Supported on Categorical Labels
    metrics_map["brier_score"] = MetricOutputRecord(
        metric_name="brier_score",
        value=None,
        definition="Mean squared error of probabilistic predictions against binary ground-truth outcomes",
        numerator=None,
        denominator=None,
        status=MetricStatus.NOT_SUPPORTED,
        limitations=(
            "Categorical outputs and discrete assessment heuristics cannot yield continuous probabilities.",
            "Requires future continuous scoring model with post-hoc calibration pipeline.",
        ),
    )
    metrics_map["expected_calibration_error"] = MetricOutputRecord(
        metric_name="expected_calibration_error",
        value=None,
        definition="Weighted difference between confidence and accuracy across partitioned confidence bins",
        numerator=None,
        denominator=None,
        status=MetricStatus.NOT_SUPPORTED,
        limitations=(
            "Requires continuous probability scores and larger sample size (N > 100) to avoid empirical bin noise.",
            "Not computable on current discrete contracts.",
        ),
    )

    return EvaluationScoreSummary(
        tp_count=tp,
        fp_count=fp,
        fn_count=total_fn,
        tn_count=tn,
        abstained_positive_count=abs_pos,
        abstained_negative_count=abs_neg,
        total_cases=total_cases,
        total_candidate_findings=vfr_denom,
        verified_candidate_findings=tp,
        metrics=MappingProxyType(metrics_map),
        case_outcomes=tuple(outcomes),
        incomplete_cases_count=incomplete_count,
        failed_cases_count=failed_count,
        reviewer_rejections_count=reviewer_rejections,
        specialist_disagreements_count=specialist_disagreements,
    )


def calculate_per_category_scores(
    outcomes: Sequence[CaseEvaluationOutcome],
    *,
    total_raw_candidates: int | None = None,
) -> dict[str, EvaluationScoreSummary]:
    """Calculate evaluation scores partitioned by vulnerability category.

    Enforces that each category's metrics are evaluated over its own locus population.
    Handles zero denominators for per-category metrics rigorously without fabricating scores.
    Also includes an 'AGGREGATE' entry covering all outcomes.
    """
    if not outcomes:
        raise ScoringCalculationError("Cannot calculate per-category scores on empty outcomes")

    by_category: dict[str, list[CaseEvaluationOutcome]] = {}
    for out in outcomes:
        cat = out.vulnerability_class.strip() if out.vulnerability_class else "UNSPECIFIED"
        by_category.setdefault(cat, []).append(out)

    summaries: dict[str, EvaluationScoreSummary] = {}
    for cat, cat_outcomes in sorted(by_category.items()):
        summaries[cat] = calculate_evaluation_scores(cat_outcomes)

    summaries["AGGREGATE"] = calculate_evaluation_scores(
        outcomes, total_raw_candidates=total_raw_candidates
    )
    return summaries


# ---------------------------------------------------------------------------
# Runner Interfaces
# ---------------------------------------------------------------------------

class EvaluationRunnerInterface:
    """Abstract interface defining the execution contract for an evaluation condition."""

    @property
    def runner_id(self) -> str:
        """Unique identifier of the runner/baseline."""
        raise NotImplementedError

    def run_case(self, case: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
        """Execute assessment for a single benchmark case locus and return an immutable run record."""
        raise NotImplementedError


class FixtureBackedRunnerAdapter(EvaluationRunnerInterface):
    """Offline test adapter that replays synthetic assessment fixtures without external calls."""

    def __init__(
        self,
        runner_id: str,
        fixture_results_by_case: Mapping[str, AssessmentResultRecord],
        reproducibility_metadata: Mapping[str, str] | None = None,
    ) -> None:
        self._runner_id = runner_id
        self._fixtures = dict(fixture_results_by_case)
        self._metadata = dict(reproducibility_metadata or {"mode": "synthetic_fixture"})

    @property
    def runner_id(self) -> str:
        return self._runner_id

    def run_case(self, case: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
        if case.case_id not in self._fixtures:
            raise EvaluationContractError(
                f"No synthetic fixture configured for case_id '{case.case_id}' in runner '{self._runner_id}'"
            )

        base_res = self._fixtures[case.case_id]
        run_id = f"run-{self._runner_id}-{case.case_id}-rep{repeat_index}"

        # Produce consistent run record with matching run_id
        result = AssessmentResultRecord(
            case_id=case.case_id,
            run_id=run_id,
            decision=base_res.decision,
            findings=base_res.findings,
            primary_severity=base_res.primary_severity,
            evidence_citations=base_res.evidence_citations,
            error_status=base_res.error_status,
            is_incomplete=base_res.is_incomplete,
        )

        return EvaluationRunRecord(
            run_id=run_id,
            runner_id=self._runner_id,
            case_id=case.case_id,
            repeat_index=repeat_index,
            result=result,
            reproducibility_metadata=self._metadata,
        )
