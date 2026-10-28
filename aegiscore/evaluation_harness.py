"""Reproducible offline evaluation harness and runner registry for AEGISCORE AI.

Phase 8E.4: Offline Runner Wrappers & Fixture-Based Evaluation Harness.
Provides a provider-neutral orchestration layer to load and validate fixtures,
select registered evaluation conditions, execute offline fixture adapters,
aggregate repeated trials with majority voting, score outcomes, and produce
structured, reproducible run manifests and execution reports.

STRICT RESTRICTION: Fully offline only. Zero network requests, zero container
operations, zero LLM provider calls, zero scanner executions. All fixture results
are explicitly marked as synthetic simulations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from aegiscore.orchestration import (
    AnalysisMode,
    AssessmentRequest,
    ClaimCitationRecord,
    EvidenceBundle,
    FindingSeverity,
    GatingDecision,
    OrchestrationContractError,
    OrchestrationError,
    OrchestrationState,
    OrchestrationStateMachine,
    SpecialistFinding,
)
from aegiscore.claim_validation import (
    ClaimValidationResult,
    EvidenceSufficiencyClassification,
    GatedGenerationResult,
)
from aegiscore.generation import (
    CitationGroundingError,
    GeneratedClaim,
    GenerationResult,
)
from aegiscore.rag import (
    CitationReference,
    SourceChunk,
    SourceMetadata,
    SourceReviewState,
)
from aegiscore.uncertainty_engine import (
    AggregationRecommendation,
    UncertaintyAggregationEngine,
    UncertaintyAggregationResult,
    UncertaintyReasonCode,
)

from aegiscore.evaluation import (
    AdjudicationState,
    AssessmentFindingRecord,
    AssessmentResultRecord,
    CaseEvaluationOutcome,
    EvaluationCaseManifestRecord,
    EvaluationContractError,
    EvaluationError,
    EvaluationRunRecord,
    EvaluationScoreSummary,
    EvaluationValidationError,
    FindingDecision,
    GroundTruthRecord,
    GroundTruthStatus,
    MetricOutputRecord,
    MetricStatus,
    RunnerCondition,
    aggregate_repeated_runs,
    calculate_evaluation_scores,
    evaluate_case_outcome,
    validate_ground_truth_jsonl,
    validate_manifest_jsonl,
    validate_runs_jsonl,
    EvaluationRunnerInterface,
    FixtureBackedRunnerAdapter,
)

__all__ = [
    # Exceptions
    "HarnessError",
    "ConditionNotRegisteredError",
    "ConditionUnavailableError",
    "LiveExecutionProhibitedError",
    "HarnessValidationError",
    # Enums
    "ConditionStatus",
    # Contracts
    "EvaluationRunManifest",
    "TrialAgreementSummary",
    "HarnessExecutionReport",
    "OrchestrationCaseFixture",
    # Registry & Harness
    "RunnerConditionRegistry",
    "EvaluationHarness",
    # Adapters & Helpers
    "OrchestrationReplayAdapter",
    "create_synthetic_fixture_adapter",
    "create_orchestration_case_fixture",
    "create_orchestration_replay_adapter",
]


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class HarnessError(EvaluationError):
    """Base exception for evaluation harness errors."""
    __test__ = False


class ConditionNotRegisteredError(HarnessError):
    """Raised when an evaluation condition has not been registered."""
    __test__ = False


class ConditionUnavailableError(HarnessError):
    """Raised when a condition is planned but currently unavailable (no fake fabricated)."""
    __test__ = False


class LiveExecutionProhibitedError(HarnessError):
    """Raised when live execution, live model calls, or target scanning is requested."""
    __test__ = False


class HarnessValidationError(HarnessError):
    """Raised when input records, ground truth, or run collections fail validation."""
    __test__ = False


# ---------------------------------------------------------------------------
# Condition Status & Registry
# ---------------------------------------------------------------------------

class ConditionStatus(str, Enum):
    """Status of an evaluation condition in the harness registry."""

    OFFLINE_REPLAY_IMPLEMENTED = "offline_replay_implemented"
    FIXTURE_IMPLEMENTED = "fixture_implemented"
    PLANNED_UNAVAILABLE = "planned_unavailable"
    LIVE_PROHIBITED = "live_prohibited"


_CONDITION_ALIASES: dict[str, RunnerCondition] = {
    # Direct Enum values
    "proposed-multi-agent": RunnerCondition.PROPOSED_MULTI_AGENT,
    "baseline-single-agent": RunnerCondition.BASELINE_SINGLE_AGENT,
    "baseline-ma-no-abstention": RunnerCondition.BASELINE_MA_NO_ABSTENTION,
    "baseline-dast-zap": RunnerCondition.BASELINE_DAST_ZAP,
    "ablation-no-rag": RunnerCondition.ABLATION_NO_RAG,
    "ablation-no-reviewer": RunnerCondition.ABLATION_NO_REVIEWER,
    # Friendly upper-case aliases
    "PROPOSED_MULTI_AGENT": RunnerCondition.PROPOSED_MULTI_AGENT,
    "MULTI_AGENT_FULL": RunnerCondition.PROPOSED_MULTI_AGENT,
    "BASELINE_SINGLE_AGENT": RunnerCondition.BASELINE_SINGLE_AGENT,
    "SINGLE_AGENT_BASELINE": RunnerCondition.BASELINE_SINGLE_AGENT,
    "BASELINE_MA_NO_ABSTENTION": RunnerCondition.BASELINE_MA_NO_ABSTENTION,
    "MULTI_AGENT_NO_ABSTENTION": RunnerCondition.BASELINE_MA_NO_ABSTENTION,
    "BASELINE_DAST_ZAP": RunnerCondition.BASELINE_DAST_ZAP,
    "DAST_ZAP": RunnerCondition.BASELINE_DAST_ZAP,
    "ABLATION_NO_RAG": RunnerCondition.ABLATION_NO_RAG,
    "RAG_DISABLED_ABLATION": RunnerCondition.ABLATION_NO_RAG,
    "ABLATION_NO_REVIEWER": RunnerCondition.ABLATION_NO_REVIEWER,
    "EVIDENCE_REVIEWER_DISABLED_ABLATION": RunnerCondition.ABLATION_NO_REVIEWER,
}


def normalize_condition(condition: RunnerCondition | str) -> RunnerCondition:
    """Normalize a condition string or enum to a canonical RunnerCondition."""
    if isinstance(condition, RunnerCondition):
        return condition
    if isinstance(condition, str):
        trimmed = condition.strip()
        if trimmed in _CONDITION_ALIASES:
            return _CONDITION_ALIASES[trimmed]
        # Check by name
        try:
            return RunnerCondition[trimmed]
        except KeyError:
            pass
        # Check by value
        try:
            return RunnerCondition(trimmed)
        except ValueError:
            pass
    raise ConditionNotRegisteredError(
        f"Unknown or unmapped evaluation condition: '{condition}'. "
        f"Valid conditions are: {[c.value for c in RunnerCondition]}"
    )


class RunnerConditionRegistry:
    """Registry managing runner conditions, status, and adapter bindings."""

    def __init__(self) -> None:
        self._adapters: dict[RunnerCondition, EvaluationRunnerInterface] = {}
        self._statuses: dict[RunnerCondition, ConditionStatus] = {}
        self._descriptions: dict[RunnerCondition, str] = {}

    @classmethod
    def create_default_registry(cls) -> RunnerConditionRegistry:
        """Create a default registry with baseline/ablation conditions configured."""
        reg = cls()
        # DAST / ZAP requires live scanning and container infrastructure: strictly prohibited offline
        reg.register_live_prohibited(
            RunnerCondition.BASELINE_DAST_ZAP,
            reason="Requires active OWASP ZAP scanner and live benchmark target; strictly prohibited in offline harness.",
        )
        # Other conditions are planned but unavailable until an explicit fixture or replay adapter is bound
        reg.register_planned_condition(
            RunnerCondition.PROPOSED_MULTI_AGENT,
            reason="Full multi-agent condition with uncertainty and gating. Requires offline replay or fixture adapter.",
        )
        reg.register_planned_condition(
            RunnerCondition.BASELINE_SINGLE_AGENT,
            reason="Single-agent prompt baseline. Requires fixture adapter in offline mode.",
        )
        reg.register_planned_condition(
            RunnerCondition.BASELINE_MA_NO_ABSTENTION,
            reason="Multi-agent without abstention baseline. Requires fixture adapter in offline mode.",
        )
        reg.register_planned_condition(
            RunnerCondition.ABLATION_NO_RAG,
            reason="RAG-disabled ablation condition. Requires fixture adapter in offline mode.",
        )
        reg.register_planned_condition(
            RunnerCondition.ABLATION_NO_REVIEWER,
            reason="Evidence-reviewer-disabled ablation condition. Requires fixture adapter in offline mode.",
        )
        return reg

    def register_offline_replay_adapter(
        self,
        condition: RunnerCondition | str,
        adapter: EvaluationRunnerInterface,
        description: str = "",
    ) -> None:
        """Bind an offline replay adapter executing the genuine orchestration workflow."""
        canonical = normalize_condition(condition)
        if not isinstance(adapter, EvaluationRunnerInterface):
            raise HarnessValidationError(
                f"Adapter for condition '{canonical.value}' must implement EvaluationRunnerInterface"
            )
        self._adapters[canonical] = adapter
        self._statuses[canonical] = ConditionStatus.OFFLINE_REPLAY_IMPLEMENTED
        self._descriptions[canonical] = (
            description or f"Offline orchestration replay adapter for condition '{canonical.value}'"
        )

    def register_fixture_adapter(
        self,
        condition: RunnerCondition | str,
        adapter: EvaluationRunnerInterface,
        description: str = "",
    ) -> None:
        """Bind an offline fixture adapter to an evaluation condition."""
        canonical = normalize_condition(condition)
        if not isinstance(adapter, EvaluationRunnerInterface):
            raise HarnessValidationError(
                f"Adapter for condition '{canonical.value}' must implement EvaluationRunnerInterface"
            )
        self._adapters[canonical] = adapter
        self._statuses[canonical] = ConditionStatus.FIXTURE_IMPLEMENTED
        self._descriptions[canonical] = (
            description or f"Synthetic fixture adapter for condition '{canonical.value}'"
        )

    def register_planned_condition(
        self,
        condition: RunnerCondition | str,
        reason: str = "",
    ) -> None:
        """Register a planned condition that has no implemented adapter (fails closed on call)."""
        canonical = normalize_condition(condition)
        self._adapters.pop(canonical, None)
        self._statuses[canonical] = ConditionStatus.PLANNED_UNAVAILABLE
        self._descriptions[canonical] = (
            reason or f"Condition '{canonical.value}' is planned but currently unavailable."
        )

    def register_live_prohibited(
        self,
        condition: RunnerCondition | str,
        reason: str = "",
    ) -> None:
        """Register a condition that requires live execution, which is strictly prohibited offline."""
        canonical = normalize_condition(condition)
        self._adapters.pop(canonical, None)
        self._statuses[canonical] = ConditionStatus.LIVE_PROHIBITED
        self._descriptions[canonical] = (
            reason or f"Condition '{canonical.value}' requires live execution and is prohibited offline."
        )

    def get_adapter(self, condition: RunnerCondition | str) -> EvaluationRunnerInterface:
        """Retrieve the adapter for a condition, failing closed if unavailable or prohibited."""
        canonical = normalize_condition(condition)
        if canonical not in self._statuses:
            raise ConditionNotRegisteredError(
                f"Condition '{canonical.value}' is not registered in the runner registry."
            )
        status = self._statuses[canonical]
        if status == ConditionStatus.LIVE_PROHIBITED:
            raise LiveExecutionProhibitedError(
                f"Condition '{canonical.value}' is marked LIVE_PROHIBITED: "
                f"{self._descriptions.get(canonical, 'Live execution is strictly prohibited.')}"
            )
        if status == ConditionStatus.PLANNED_UNAVAILABLE:
            raise ConditionUnavailableError(
                f"Condition '{canonical.value}' is PLANNED_UNAVAILABLE: "
                f"{self._descriptions.get(canonical, 'No fixture adapter registered; behavior must not be fabricated.')}"
            )
        if status in (ConditionStatus.FIXTURE_IMPLEMENTED, ConditionStatus.OFFLINE_REPLAY_IMPLEMENTED):
            adapter = self._adapters.get(canonical)
            if adapter is None:
                raise ConditionNotRegisteredError(
                    f"Condition '{canonical.value}' is marked {status.value} but adapter is missing."
                )
            return adapter

        raise ConditionNotRegisteredError(f"Unexpected status '{status}' for condition '{canonical.value}'")

    def get_status(self, condition: RunnerCondition | str) -> ConditionStatus:
        """Return the registration status for a condition."""
        canonical = normalize_condition(condition)
        if canonical not in self._statuses:
            raise ConditionNotRegisteredError(
                f"Condition '{canonical.value}' is not registered in the runner registry."
            )
        return self._statuses[canonical]

    def list_conditions(self) -> Mapping[RunnerCondition, ConditionStatus]:
        """Return a mapping of all registered conditions and their statuses."""
        return MappingProxyType(dict(self._statuses))


# ---------------------------------------------------------------------------
# Output Data Contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvaluationRunManifest:
    """Provenance and reproducibility manifest for an evaluation harness execution."""

    manifest_id: str
    fixture_dataset_id: str
    fixture_dataset_version: str
    runner_condition: str
    configuration_fingerprint: str
    repeat_count: int
    application_version: str
    input_case_ids: tuple[str, ...]
    start_time_iso: str | None
    end_time_iso: str | None
    execution_status: str
    validation_errors: tuple[str, ...] = field(default_factory=tuple)
    is_synthetic_simulation: bool = True
    reproducibility_notes: str = (
        "SYNTHETIC FIXTURE REPLAY ONLY: All outputs derived from deterministic test fixtures. "
        "Does not demonstrate real-world vulnerability detection accuracy or live LLM performance. "
        "Deterministic fixture repeats produce identical outputs by design."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "fixture_dataset_id": self.fixture_dataset_id,
            "fixture_dataset_version": self.fixture_dataset_version,
            "runner_condition": self.runner_condition,
            "configuration_fingerprint": self.configuration_fingerprint,
            "repeat_count": self.repeat_count,
            "application_version": self.application_version,
            "input_case_ids": list(self.input_case_ids),
            "start_time_iso": self.start_time_iso,
            "end_time_iso": self.end_time_iso,
            "execution_status": self.execution_status,
            "validation_errors": list(self.validation_errors),
            "is_synthetic_simulation": self.is_synthetic_simulation,
            "reproducibility_notes": self.reproducibility_notes,
        }


@dataclass(frozen=True, slots=True)
class TrialAgreementSummary:
    """Summary of decision stability across repeated runs."""

    total_cases: int
    unanimous_cases_count: int
    split_decision_cases_count: int
    trial_agreement_rate: float
    per_case_decisions: Mapping[str, tuple[str, ...]]
    is_deterministic_fixture_behavior: bool = True
    notes: str = (
        "Agreement rate reflects fixture determinism across repeated trials, "
        "not empirical LLM reliability."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "unanimous_cases_count": self.unanimous_cases_count,
            "split_decision_cases_count": self.split_decision_cases_count,
            "trial_agreement_rate": self.trial_agreement_rate,
            "per_case_decisions": {k: list(v) for k, v in self.per_case_decisions.items()},
            "is_deterministic_fixture_behavior": self.is_deterministic_fixture_behavior,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class HarnessExecutionReport:
    """Comprehensive, machine-readable report of an evaluation harness execution."""

    manifest: EvaluationRunManifest
    raw_trial_runs: tuple[EvaluationRunRecord, ...]
    aggregated_outcomes: tuple[CaseEvaluationOutcome, ...]
    trial_agreement: TrialAgreementSummary
    score_summary: EvaluationScoreSummary
    unique_case_loci_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert entire execution report to a deterministic JSON-serializable dictionary."""
        metrics_dict: dict[str, Any] = {}
        for name, m in self.score_summary.metrics.items():
            metrics_dict[name] = m.to_dict()

        outcomes_list: list[dict[str, Any]] = []
        for o in self.aggregated_outcomes:
            outcomes_list.append({
                "case_id": o.case_id,
                "locus": {
                    "target_uri": o.locus.target_uri,
                    "parameter": o.locus.parameter,
                    "cwe_id": o.locus.cwe_id,
                },
                "ground_truth": o.ground_truth.value,
                "system_decision": o.system_decision.value,
                "classification": o.classification,
                "is_covered": o.is_covered,
                "predicted_severity": o.predicted_severity.value if o.predicted_severity else None,
                "expected_severity": o.expected_severity.value if o.expected_severity else None,
                "severity_match": o.severity_match,
                "vulnerability_class": o.vulnerability_class,
                "is_incomplete": o.is_incomplete,
                "error_status": o.error_status,
            })

        runs_list: list[dict[str, Any]] = []
        for r in self.raw_trial_runs:
            runs_list.append({
                "run_id": r.run_id,
                "runner_id": r.runner_id,
                "case_id": r.case_id,
                "repeat_index": r.repeat_index,
                "result": {
                    "case_id": r.result.case_id,
                    "run_id": r.result.run_id,
                    "decision": r.result.decision.value,
                    "primary_severity": r.result.primary_severity.value if r.result.primary_severity else None,
                    "evidence_citations": list(r.result.evidence_citations),
                    "error_status": r.result.error_status,
                    "is_incomplete": r.result.is_incomplete,
                },
                "reproducibility_metadata": dict(r.reproducibility_metadata),
            })

        return {
            "manifest": self.manifest.to_dict(),
            "trial_agreement": self.trial_agreement.to_dict(),
            "score_summary": {
                "tp_count": self.score_summary.tp_count,
                "fp_count": self.score_summary.fp_count,
                "fn_count": self.score_summary.fn_count,
                "tn_count": self.score_summary.tn_count,
                "abstained_positive_count": self.score_summary.abstained_positive_count,
                "abstained_negative_count": self.score_summary.abstained_negative_count,
                "total_cases": self.score_summary.total_cases,
                "total_candidate_findings": self.score_summary.total_candidate_findings,
                "verified_candidate_findings": self.score_summary.verified_candidate_findings,
                "metrics": metrics_dict,
            },
            "unique_case_loci_count": self.unique_case_loci_count,
            "aggregated_outcomes": outcomes_list,
            "raw_trial_runs": runs_list,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize report to a deterministic JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ---------------------------------------------------------------------------
# Evaluation Harness Orchestrator
# ---------------------------------------------------------------------------

class EvaluationHarness:
    """Orchestrates offline, reproducible evaluation workflows."""

    def __init__(
        self,
        registry: RunnerConditionRegistry | None = None,
        execution_mode: str = "offline_fixture",
        record_store: Any = None,
    ) -> None:
        if execution_mode != "offline_fixture":
            raise LiveExecutionProhibitedError(
                f"Execution mode must be 'offline_fixture', got '{execution_mode}'. "
                f"Live execution, container startup, and scanner runs are strictly prohibited."
            )
        self._registry = registry or RunnerConditionRegistry.create_default_registry()
        self._execution_mode = execution_mode
        self._record_store = record_store

    @property
    def registry(self) -> RunnerConditionRegistry:
        return self._registry

    def execute(
        self,
        condition: RunnerCondition | str,
        manifest_records: Sequence[EvaluationCaseManifestRecord],
        ground_truth_records: Sequence[GroundTruthRecord],
        repeat_count: int = 1,
        fixture_dataset_id: str = "synthetic-testbed-fixtures",
        fixture_dataset_version: str = "1.0.0",
        application_version: str = "0.1.0",
        strict_adjudication: bool = True,
    ) -> HarnessExecutionReport:
        """Execute evaluation over specified cases for K repeats and compute deterministic scores."""
        start_time_iso = datetime.now(timezone.utc).isoformat()

        # 1. Input Validation
        if not manifest_records:
            raise HarnessValidationError("Evaluation manifest records sequence must not be empty.")
        if not ground_truth_records:
            raise HarnessValidationError("Ground truth records sequence must not be empty.")
        if not isinstance(repeat_count, int) or repeat_count < 1:
            raise HarnessValidationError(f"repeat_count must be an integer >= 1, got {repeat_count}")

        # Check manifest duplicate case_ids and canonical loci
        seen_case_ids: set[str] = set()
        seen_loci: set[tuple[str, str, str, str]] = set()
        for case in manifest_records:
            if case.case_id in seen_case_ids:
                raise HarnessValidationError(f"Duplicate case_id '{case.case_id}' in evaluation manifest")
            seen_case_ids.add(case.case_id)
            locus_key = (
                case.locus.target_uri,
                case.locus.parameter,
                case.locus.cwe_id,
            )
            if locus_key in seen_loci:
                raise HarnessValidationError(
                    f"Duplicate canonical locus in manifest: {locus_key} on case '{case.case_id}'"
                )
            seen_loci.add(locus_key)

        # Index ground truth and check integrity
        gt_by_case: dict[str, GroundTruthRecord] = {}
        for gt in ground_truth_records:
            if gt.case_id not in seen_case_ids:
                raise HarnessValidationError(
                    f"Ground truth references unknown case_id '{gt.case_id}' not in manifest."
                )
            if gt.case_id in gt_by_case:
                raise HarnessValidationError(f"Duplicate ground truth record for case_id '{gt.case_id}'")
            if strict_adjudication and gt.adjudication_state != AdjudicationState.ADJUDICATED:
                raise HarnessValidationError(
                    f"Case '{gt.case_id}' has ground-truth adjudication_state '{gt.adjudication_state.value}', "
                    f"but strict_adjudication requires 'adjudicated'."
                )
            gt_by_case[gt.case_id] = gt

        # Ensure all manifest cases have ground truth
        missing_gt = seen_case_ids - set(gt_by_case.keys())
        if missing_gt:
            raise HarnessValidationError(
                f"Missing ground truth for cases: {sorted(missing_gt)}"
            )

        # 2. Resolve runner adapter
        canonical_cond = normalize_condition(condition)
        adapter = self._registry.get_adapter(canonical_cond)

        # 3. Execute runs across trials
        all_runs: list[EvaluationRunRecord] = []
        seen_run_ids: set[str] = set()
        for rep in range(repeat_count):
            for case in manifest_records:
                run_rec = adapter.run_case(case, repeat_index=rep)
                # Invariant checks on run_rec
                if run_rec.case_id != case.case_id:
                    raise HarnessValidationError(
                        f"Run record case_id '{run_rec.case_id}' does not match target case '{case.case_id}'"
                    )
                if run_rec.repeat_index != rep:
                    raise HarnessValidationError(
                        f"Run record repeat_index '{run_rec.repeat_index}' does not match expected '{rep}'"
                    )
                if run_rec.run_id in seen_run_ids:
                    raise HarnessValidationError(f"Duplicate run_id '{run_rec.run_id}' encountered")
                seen_run_ids.add(run_rec.run_id)
                all_runs.append(run_rec)

        # 4. Analyze trial agreement and aggregate
        per_case_decisions: dict[str, list[str]] = {c.case_id: [] for c in manifest_records}
        runs_by_case: dict[str, list[EvaluationRunRecord]] = {c.case_id: [] for c in manifest_records}
        for r in all_runs:
            per_case_decisions[r.case_id].append(r.result.decision.value)
            runs_by_case[r.case_id].append(r.result)

        unanimous_count = 0
        split_count = 0
        for decisions in per_case_decisions.values():
            if all(d == decisions[0] for d in decisions):
                unanimous_count += 1
            else:
                split_count += 1

        total_cases = len(manifest_records)
        agreement_rate = (unanimous_count / total_cases) if total_cases > 0 else 1.0

        trial_agreement = TrialAgreementSummary(
            total_cases=total_cases,
            unanimous_cases_count=unanimous_count,
            split_decision_cases_count=split_count,
            trial_agreement_rate=agreement_rate,
            per_case_decisions=MappingProxyType({k: tuple(v) for k, v in per_case_decisions.items()}),
            is_deterministic_fixture_behavior=True,
        )

        # 5. Aggregate repeated runs and evaluate outcomes
        aggregated_results = aggregate_repeated_runs(all_runs)
        outcomes: list[CaseEvaluationOutcome] = []
        for agg_res in aggregated_results:
            gt_rec = gt_by_case[agg_res.case_id]
            outcome = evaluate_case_outcome(agg_res, gt_rec)
            outcomes.append(outcome)

        # 6. Calculate deterministic evaluation scores
        score_summary = calculate_evaluation_scores(outcomes)

        # 7. Compute configuration fingerprint
        config_payload: dict[str, Any] = {
            "condition": canonical_cond.value,
            "repeat_count": repeat_count,
            "case_ids": [c.case_id for c in manifest_records],
            "fixture_dataset_id": fixture_dataset_id,
            "fixture_dataset_version": fixture_dataset_version,
            "application_version": application_version,
            "runner_id": adapter.runner_id,
        }
        if hasattr(adapter, "configuration_payload"):
            config_payload["adapter_config"] = getattr(adapter, "configuration_payload")
        config_fp = hashlib.sha256(json.dumps(config_payload, sort_keys=True).encode("utf-8")).hexdigest()

        end_time_iso = datetime.now(timezone.utc).isoformat()
        manifest_id = f"manifest-{canonical_cond.value}-{config_fp[:12]}"

        manifest = EvaluationRunManifest(
            manifest_id=manifest_id,
            fixture_dataset_id=fixture_dataset_id,
            fixture_dataset_version=fixture_dataset_version,
            runner_condition=canonical_cond.value,
            configuration_fingerprint=config_fp,
            repeat_count=repeat_count,
            application_version=application_version,
            input_case_ids=tuple(c.case_id for c in manifest_records),
            start_time_iso=start_time_iso,
            end_time_iso=end_time_iso,
            execution_status="completed",
            validation_errors=(),
            is_synthetic_simulation=True,
        )

        report = HarnessExecutionReport(
            manifest=manifest,
            raw_trial_runs=tuple(all_runs),
            aggregated_outcomes=tuple(outcomes),
            trial_agreement=trial_agreement,
            score_summary=score_summary,
            unique_case_loci_count=total_cases,
        )
        # Persistence is opt-in. It records only this already-completed offline
        # fixture execution; no execution is triggered by the storage layer.
        if self._record_store is not None:
            self._record_store.persist_evaluation_report(report)
        return report

    def execute_from_jsonl(
        self,
        condition: RunnerCondition | str,
        manifest_jsonl: str,
        ground_truth_jsonl: str,
        repeat_count: int = 1,
        fixture_dataset_id: str = "synthetic-testbed-fixtures",
        fixture_dataset_version: str = "1.0.0",
        application_version: str = "0.1.0",
        strict_adjudication: bool = True,
    ) -> HarnessExecutionReport:
        """Parse, validate, and execute evaluation from raw JSONL manifest and ground-truth streams."""
        manifest_records = validate_manifest_jsonl(manifest_jsonl)
        known_case_ids = {c.case_id for c in manifest_records}
        gt_records = validate_ground_truth_jsonl(
            ground_truth_jsonl,
            known_manifest_cases=known_case_ids,
        )
        return self.execute(
            condition=condition,
            manifest_records=manifest_records,
            ground_truth_records=gt_records,
            repeat_count=repeat_count,
            fixture_dataset_id=fixture_dataset_id,
            fixture_dataset_version=fixture_dataset_version,
            application_version=application_version,
            strict_adjudication=strict_adjudication,
        )


# ---------------------------------------------------------------------------
# Fixture Creation Helpers
# ---------------------------------------------------------------------------

def create_synthetic_fixture_adapter(
    runner_id: str,
    case_manifests: Sequence[EvaluationCaseManifestRecord],
    default_decision: FindingDecision = FindingDecision.VERIFIED,
    custom_decisions: Mapping[str, FindingDecision] | None = None,
    reproducibility_metadata: Mapping[str, str] | None = None,
) -> FixtureBackedRunnerAdapter:
    """Helper to generate a deterministic synthetic fixture adapter for offline evaluation testing."""
    custom = custom_decisions or {}
    fixtures: dict[str, AssessmentResultRecord] = {}

    for case in case_manifests:
        decision = custom.get(case.case_id, default_decision)
        findings = ()
        if decision == FindingDecision.VERIFIED:
            findings = (
                AssessmentFindingRecord(
                    finding_id=f"FIND-{case.case_id}-01",
                    specialist_role="vulnerability_specialist:xss",
                    vulnerability_identified=True,
                    cwe_id=case.locus.cwe_id,
                    severity=FindingSeverity.HIGH,
                    decision=decision,
                    evidence_citations=("CIT-EVAL-001",),
                    rationale="Synthetic verified finding for testbed replay",
                ),
            )

        fixtures[case.case_id] = AssessmentResultRecord(
            case_id=case.case_id,
            run_id=f"fixture-run-{case.case_id}",
            decision=decision,
            findings=findings,
            primary_severity=None,
            evidence_citations=("CIT-EVAL-001",) if decision == FindingDecision.VERIFIED else (),
            error_status=None,
            is_incomplete=False,
        )

    metadata = dict(reproducibility_metadata or {
        "mode": "synthetic_fixture",
        "description": "Deterministic synthetic test replay adapter.",
    })

    return FixtureBackedRunnerAdapter(
        runner_id=runner_id,
        fixture_results_by_case=fixtures,
        reproducibility_metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Offline Orchestration Replay Adapter & Fixtures (Phase 8F.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OrchestrationCaseFixture:
    """Fixture inputs driving the genuine OrchestrationStateMachine during replay."""

    case_id: str
    target_url: str
    authorized_scope: tuple[str, ...]
    vulnerability_category: str
    evidence_bundle: EvidenceBundle
    specialist_finding: SpecialistFinding | None
    review_notes: str
    secondary_findings: tuple[SpecialistFinding, ...] = ()
    validation_result: GatedGenerationResult | None = None
    force_sufficient: bool | None = None
    force_conflict: bool | None = None
    forced_conflict_markers: tuple[str, ...] | None = None
    specialist_adapter: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise HarnessValidationError("case_id must be non-empty text")
        if not isinstance(self.target_url, str) or not self.target_url.strip():
            raise HarnessValidationError("target_url must be non-empty text")
        if not isinstance(self.authorized_scope, tuple):
            raise HarnessValidationError("authorized_scope must be a tuple")
        if not isinstance(self.vulnerability_category, str) or not self.vulnerability_category.strip():
            raise HarnessValidationError("vulnerability_category must be non-empty text")
        if not isinstance(self.evidence_bundle, EvidenceBundle):
            raise HarnessValidationError("evidence_bundle must be an EvidenceBundle instance")
        if self.specialist_finding is not None and not isinstance(self.specialist_finding, SpecialistFinding):
            raise HarnessValidationError("specialist_finding must be a SpecialistFinding or None")
        if not isinstance(self.review_notes, str):
            raise HarnessValidationError("review_notes must be a string")
        if not isinstance(self.secondary_findings, tuple):
            raise HarnessValidationError("secondary_findings must be a tuple")
        for sec in self.secondary_findings:
            if not isinstance(sec, SpecialistFinding):
                raise HarnessValidationError("every secondary finding must be a SpecialistFinding instance")
        if self.validation_result is not None and not isinstance(self.validation_result, GatedGenerationResult):
            raise HarnessValidationError("validation_result must be a GatedGenerationResult or None")


class OrchestrationReplayAdapter(EvaluationRunnerInterface):
    """Offline adapter executing the genuine OrchestrationStateMachine and UncertaintyAggregationEngine.

    Translates evaluation benchmark cases into genuine orchestration executions, executing
    scope validation, evidence retrieval recording, specialist finding validation,
    adversarial evidence review, uncertainty engine aggregation, claim validation gating,
    and fail-closed response finalization.
    """

    def __init__(
        self,
        runner_id: str,
        case_fixtures: Mapping[str, OrchestrationCaseFixture],
        *,
        specialist_adapter: Any = None,
        reproducibility_metadata: Mapping[str, str] | None = None,
        propagate_exceptions: bool = False,
    ) -> None:
        if not isinstance(runner_id, str) or not runner_id.strip():
            raise HarnessValidationError("runner_id must be non-empty text")
        self._runner_id = runner_id
        self._case_fixtures = dict(case_fixtures)
        self._specialist_adapter = specialist_adapter
        self._metadata = dict(reproducibility_metadata or {
            "mode": "offline_orchestration_replay",
            "description": "Genuine orchestration state machine and uncertainty engine replay.",
        })
        self._propagate_exceptions = propagate_exceptions

    @property
    def runner_id(self) -> str:
        return self._runner_id

    @property
    def configuration_payload(self) -> dict[str, Any]:
        payload = {
            "adapter_type": "OrchestrationReplayAdapter",
            "adapter_runner_id": self._runner_id,
            "propagate_exceptions": self._propagate_exceptions,
            "cases_configured_count": len(self._case_fixtures),
            "confidence_is_calibrated": False,
        }
        if self._specialist_adapter is not None:
            payload["specialist_adapter"] = type(self._specialist_adapter).__name__
        return payload

    def run_case(self, case: EvaluationCaseManifestRecord, repeat_index: int = 0) -> EvaluationRunRecord:
        """Execute the real orchestration state machine workflow for a single case locus."""
        if case.case_id not in self._case_fixtures:
            raise HarnessValidationError(
                f"No orchestration fixture configured for case_id '{case.case_id}' in runner '{self._runner_id}'"
            )

        fixture = self._case_fixtures[case.case_id]
        run_id = f"replay-{self._runner_id}-{case.case_id}-rep{repeat_index}"
        req_id = f"req-{self._runner_id}-{case.case_id}-rep{repeat_index}"
        start_time_utc = datetime.now(timezone.utc).isoformat()
        sm: OrchestrationStateMachine | None = None

        try:
            req = AssessmentRequest(
                request_id=req_id,
                target_url=fixture.target_url,
                vulnerability_category=fixture.vulnerability_category,
                authorized_scope=fixture.authorized_scope,
                analysis_mode="passive_rag_only",
            )
            sm = OrchestrationStateMachine(req)
            sm.validate_request()

            # Align bundle and findings with the execution request_id
            bundle = (
                replace(fixture.evidence_bundle, request_id=req_id)
                if fixture.evidence_bundle.request_id != req_id
                else fixture.evidence_bundle
            )
            sm.record_retrieval(bundle)

            # If evidence bundle has 0 approved sources or is empty, record_retrieval transitions to ABSTAINED
            if not sm.is_terminal:
                adapter_to_run = fixture.specialist_adapter or self._specialist_adapter
                if adapter_to_run is not None:
                    sm.execute_specialist_analysis(adapter_to_run)
                elif fixture.specialist_finding is not None:
                    finding = (
                        replace(fixture.specialist_finding, request_id=req_id)
                        if fixture.specialist_finding.request_id != req_id
                        else fixture.specialist_finding
                    )
                    sm.record_specialist_analysis(finding)

            if not sm.is_terminal:
                sm.record_evidence_review(fixture.review_notes)

            if not sm.is_terminal:
                secondary = tuple(
                    replace(sec, request_id=req_id) if sec.request_id != req_id else sec
                    for sec in fixture.secondary_findings
                )
                sm.assess_uncertainty(
                    secondary_findings=secondary,
                    force_sufficient=fixture.force_sufficient,
                    force_conflict=fixture.force_conflict,
                    forced_conflict_markers=fixture.forced_conflict_markers,
                )

            # If uncertainty aggregation recommended CONTINUE, state machine is in UNCERTAINTY_ASSESSED
            if not sm.is_terminal and sm.current_state == OrchestrationState.UNCERTAINTY_ASSESSED:
                val_res = fixture.validation_result
                if val_res is None:
                    # Construct default validation from the specialist finding claims
                    fnd = sm.specialist_finding
                    claims = fnd.proposed_claims if fnd else ()
                    val_res = GatedGenerationResult(
                        generation_result=GenerationResult(
                            status="answered" if claims else "abstained",
                            claims=claims,
                            abstention_reason=None if claims else "insufficient_evidence",
                        ),
                        overall_classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
                        claim_validations=tuple(
                            ClaimValidationResult(
                                claim=c,
                                classification=EvidenceSufficiencyClassification.SUFFICIENT_EVIDENCE,
                                is_valid=True,
                                citations_validated=c.citations,
                            )
                            for c in claims
                        ),
                    )
                sm.record_validation(val_res)

            # Finalize result if validation completed
            if not sm.is_terminal and sm.current_state == OrchestrationState.VALIDATION_COMPLETED:
                final_res = sm.create_final_result(f"final-{self._runner_id}-{case.case_id}-rep{repeat_index}")
                sm.finalize_result(final_res)

        except Exception as exc:
            if self._propagate_exceptions:
                raise
            if sm is not None and not sm.is_terminal:
                try:
                    sm.fail(f"{type(exc).__name__}: {str(exc)}")
                except Exception:
                    pass

            error_msg = f"{type(exc).__name__}: {str(exc)}"
            result = AssessmentResultRecord(
                case_id=case.case_id,
                run_id=run_id,
                decision=FindingDecision.ABSTAINED,
                findings=(),
                primary_severity=None,
                evidence_citations=(),
                error_status=error_msg,
                is_incomplete=True,
            )
            end_time_utc = datetime.now(timezone.utc).isoformat()
            metadata = dict(self._metadata)
            metadata.update({
                "runner_id": self._runner_id,
                "adapter_type": "OrchestrationReplayAdapter",
                "case_id": case.case_id,
                "repeat_index": str(repeat_index),
                "final_state": sm.current_state.value if sm is not None else "init_failed",
                "error_status": error_msg,
                "scoring_protocol_version": "1.0.0",
                "manifest_schema_version": case.schema_version,
                "confidence_is_calibrated": "False",
            })
            return EvaluationRunRecord(
                run_id=run_id,
                runner_id=self._runner_id,
                case_id=case.case_id,
                repeat_index=repeat_index,
                result=result,
                reproducibility_metadata=metadata,
                start_time_utc=start_time_utc,
                end_time_utc=end_time_utc,
            )

        end_time_utc = datetime.now(timezone.utc).isoformat()
        trajectory_str = " -> ".join(
            f"{src.value}->{dst.value}" for src, dst, _ in sm.transition_history
        )
        reason_codes_str = ";".join(
            f"{dst.value}:{reason}" for _, dst, reason in sm.transition_history if reason
        )

        metadata = dict(self._metadata)
        metadata.update({
            "runner_id": self._runner_id,
            "adapter_type": "OrchestrationReplayAdapter",
            "case_id": case.case_id,
            "repeat_index": str(repeat_index),
            "final_state": sm.current_state.value,
            "trajectory": trajectory_str,
            "reason_codes": reason_codes_str,
            "scoring_protocol_version": "1.0.0",
            "manifest_schema_version": case.schema_version,
            "confidence_is_calibrated": "False",
        })

        if sm.uncertainty_aggregation_result is not None:
            agg = sm.uncertainty_aggregation_result
            metadata["uncertainty_recommendation"] = agg.recommendation.value
            metadata["uncertainty_primary_reason"] = agg.primary_reason_code.value
            metadata["uncertainty_contributing_reasons"] = ",".join(rc.value for rc in agg.contributing_reason_codes)
            metadata["uncertainty_heuristic_score"] = f"{agg.overall_heuristic_score:.4f}"
            metadata["epistemic_uncertainty"] = str(len(agg.signals.epistemic_keywords_found) > 0)

        findings: tuple[AssessmentFindingRecord, ...] = ()
        primary_severity: FindingSeverity | None = None
        citations: tuple[str, ...] = ()

        if sm.current_state == OrchestrationState.COMPLETED:
            decision = FindingDecision.VERIFIED
            if sm.specialist_finding is not None:
                c_ids = tuple(c.citation.chunk_id for c in sm.specialist_finding.claim_citations)
                findings = (
                    AssessmentFindingRecord(
                        finding_id=sm.specialist_finding.finding_id,
                        specialist_role=sm.specialist_finding.specialist_role,
                        vulnerability_identified=sm.specialist_finding.vulnerability_identified,
                        cwe_id=sm.specialist_finding.cwe_id or case.locus.cwe_id,
                        severity=sm.specialist_finding.severity,
                        decision=FindingDecision.VERIFIED,
                        evidence_citations=c_ids,
                        rationale=sm.specialist_finding.reasoning_notes or sm.specialist_finding.summary,
                    ),
                )
                primary_severity = sm.specialist_finding.severity
                citations = c_ids
        elif sm.current_state == OrchestrationState.REJECTED:
            decision = FindingDecision.REJECTED
        elif sm.current_state in (OrchestrationState.ABSTAINED, OrchestrationState.FLAGGED_FOR_REVIEW):
            decision = FindingDecision.ABSTAINED
        else:
            decision = FindingDecision.ABSTAINED

        is_incomplete = (sm.current_state == OrchestrationState.FAILED)
        error_status = "orchestration_state_failed" if is_incomplete else None

        result = AssessmentResultRecord(
            case_id=case.case_id,
            run_id=run_id,
            decision=decision,
            findings=findings,
            primary_severity=primary_severity,
            evidence_citations=citations,
            error_status=error_status,
            is_incomplete=is_incomplete,
        )

        return EvaluationRunRecord(
            run_id=run_id,
            runner_id=self._runner_id,
            case_id=case.case_id,
            repeat_index=repeat_index,
            result=result,
            reproducibility_metadata=metadata,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
        )


def create_orchestration_case_fixture(
    case: EvaluationCaseManifestRecord,
    *,
    evidence_text: str = "Search query parameter directly concatenated into SQL query without sanitation.",
    vulnerability_identified: bool = True,
    specialist_role: str = "vulnerability_specialist:sqli",
    severity: FindingSeverity = FindingSeverity.HIGH,
    review_notes: str = "Adversarial evidence review: source provenance confirmed and excerpt is grounded.",
    source_id: str = "SRC-TEST-001",
    chunk_id: str = "CHK-TEST-001",
    target_url: str | None = None,
    authorized_scope: tuple[str, ...] | None = None,
    secondary_findings: Sequence[SpecialistFinding] | None = None,
    force_sufficient: bool | None = None,
    force_conflict: bool | None = None,
    forced_conflict_markers: Sequence[str] | None = None,
    custom_validation_result: GatedGenerationResult | None = None,
    specialist_adapter: Any = None,
) -> OrchestrationCaseFixture:
    """Helper to construct an OrchestrationCaseFixture from a case manifest record."""
    if target_url is None:
        target_uri = case.locus.target_uri
        if target_uri.startswith("http://") or target_uri.startswith("https://"):
            target_url = target_uri
        else:
            path = target_uri if target_uri.startswith("/") else f"/{target_uri}"
            target_url = f"http://127.0.0.1:3000{path}"

    if authorized_scope is None:
        authorized_scope = ("/",)

    if not evidence_text or not evidence_text.strip():
        # Empty evidence bundle (approved_source_count=0) triggers fail-closed abstention
        evidence_bundle = EvidenceBundle(
            bundle_id=f"bnd-{case.case_id}",
            request_id=f"req-{case.case_id}",
            retrieval_query=f"vulnerability query for {case.vulnerability_class}",
            chunks=(),
            citations=(),
            manifest_fingerprint="0" * 64,
            approved_source_count=0,
            evidence_status="no_approved_evidence",
        )
        specialist_finding = None
    else:
        digest = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
        src_meta = SourceMetadata(
            source_id=source_id,
            content_sha256=digest,
            review_state=SourceReviewState.APPROVED,
        )
        chunk = SourceChunk(
            chunk_id=chunk_id,
            provenance=src_meta,
            ordinal=0,
            start_offset=0,
            end_offset=len(evidence_text),
            content=evidence_text,
            content_sha256=digest,
        )
        cit_ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
        evidence_bundle = EvidenceBundle(
            bundle_id=f"bnd-{case.case_id}",
            request_id=f"req-{case.case_id}",
            retrieval_query=f"vulnerability query for {case.vulnerability_class}",
            chunks=(chunk,),
            citations=(cit_ref,),
            manifest_fingerprint=digest,
            approved_source_count=1,
            evidence_status="evidence_found",
        )

        claim = GeneratedClaim(
            text=f"Vulnerability observed at {case.locus.parameter}: {evidence_text}",
            citations=(cit_ref,),
        )
        claim_cit = ClaimCitationRecord(
            claim_id=f"clm-{case.case_id}-01",
            citation=cit_ref,
            cited_excerpt=evidence_text,
        )
        specialist_finding = SpecialistFinding(
            finding_id=f"fnd-{case.case_id}-01",
            request_id=f"req-{case.case_id}",
            specialist_role=specialist_role,
            vulnerability_identified=vulnerability_identified,
            severity=severity,
            summary=f"Analysis of {case.locus.parameter}",
            proposed_claims=(claim,),
            cwe_id=case.locus.cwe_id,
            claim_citations=(claim_cit,),
            reasoning_notes="Analytical finding grounded in retrieved source evidence.",
        )

    return OrchestrationCaseFixture(
        case_id=case.case_id,
        target_url=target_url,
        authorized_scope=authorized_scope,
        vulnerability_category=case.vulnerability_class,
        evidence_bundle=evidence_bundle,
        specialist_finding=specialist_finding,
        review_notes=review_notes,
        secondary_findings=tuple(secondary_findings or ()),
        validation_result=custom_validation_result,
        force_sufficient=force_sufficient,
        force_conflict=force_conflict,
        forced_conflict_markers=tuple(forced_conflict_markers) if forced_conflict_markers else None,
        specialist_adapter=specialist_adapter,
    )


def create_orchestration_replay_adapter(
    runner_id: str,
    case_manifests: Sequence[EvaluationCaseManifestRecord],
    *,
    case_fixtures: Mapping[str, OrchestrationCaseFixture] | None = None,
    specialist_adapter: Any = None,
    reproducibility_metadata: Mapping[str, str] | None = None,
    propagate_exceptions: bool = False,
) -> OrchestrationReplayAdapter:
    """Helper to generate an OrchestrationReplayAdapter for a suite of manifest cases."""
    fixtures: dict[str, OrchestrationCaseFixture] = dict(case_fixtures or {})
    for case in case_manifests:
        if case.case_id not in fixtures:
            fixtures[case.case_id] = create_orchestration_case_fixture(case, specialist_adapter=specialist_adapter)

    return OrchestrationReplayAdapter(
        runner_id=runner_id,
        case_fixtures=fixtures,
        specialist_adapter=specialist_adapter,
        reproducibility_metadata=reproducibility_metadata,
        propagate_exceptions=propagate_exceptions,
    )

