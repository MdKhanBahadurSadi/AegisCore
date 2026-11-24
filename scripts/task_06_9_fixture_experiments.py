"""Reproduce TASK 06.9 deterministic and fake-adapter timing measurements.

This is an offline research fixture only. It never opens a socket or invokes a
live model provider. Timing values are machine/run dependent; counts are fixed by
the synthetic input and the current detector/reviewer implementation.
"""

from __future__ import annotations

import json
import platform
import statistics
import time
from typing import Any

from aegiscore.assessment_ai import PassiveAssessmentAIReviewer
from aegiscore.model_adapter import (
    ModelProviderConfig,
    ModelRequest,
    ModelResponse,
    ProviderMode,
)
from aegiscore.passive_detector import PassiveHeaderDetector


ASSESSMENT_ID = "asm_00000000000000000000000000000001"
EVIDENCE_ID = "evi_00000000000000000000000000000001"
TARGET_URL = "https://127.0.0.1:8443/fixture"
EVIDENCE: dict[str, Any] = {
    "evidence_id": EVIDENCE_ID,
    "assessment_id": ASSESSMENT_ID,
    "collection_status": "observed",
    "http_method": "HEAD",
    "http_status": 200,
    "normalized_headers": {},
    "header_flags": {},
}


class FixtureAdapter:
    """Return schema-shaped deterministic commentary without external I/O."""

    config = ModelProviderConfig(
        provider_mode=ProviderMode.DETERMINISTIC_FAKE,
        model_id="task-06-9-local-fixture",
        timeout_seconds=2.0,
    )

    def complete(self, request: ModelRequest) -> ModelResponse:
        payload = json.loads(request.user_prompt)
        reviews = [
            {
                "finding_id": finding["finding_id"],
                "inferred_risk": "A missing policy may permit unintended resource loading.",
                "uncertainty": "This HEAD observation does not show page content or prove exploitability.",
                "recommendation": "Review the endpoint's application-specific resource policy before deployment.",
                "evidence_ids": finding["evidence_ids"],
            }
            for finding in payload["deterministic_findings"]
        ]
        output = {"status": "reviewed", "abstention_reason": None, "reviews": reviews}
        return ModelResponse(
            request_id=request.request_id,
            model_id=self.config.model_id,
            provider_mode=self.config.provider_mode,
            raw_content=json.dumps(output, separators=(",", ":")),
            structured_output=output,
            execution_duration_ms=0.0,
        )


def _normalize_findings(findings: list[dict[str, Any]]) -> str:
    normalized = []
    for finding in findings:
        item = dict(finding)
        item.pop("created_at", None)
        normalized.append(json.dumps(item, sort_keys=True, separators=(",", ":")))
    return json.dumps(sorted(normalized), separators=(",", ":"))


def _detector_repeatability(iterations: int = 100) -> dict[str, Any]:
    signatures: set[str] = set()
    finding_count = 0
    valid_links = 0
    started = time.perf_counter()
    for _ in range(iterations):
        findings = PassiveHeaderDetector.analyze(ASSESSMENT_ID, TARGET_URL, EVIDENCE)
        signatures.add(_normalize_findings(findings))
        finding_count += len(findings)
        valid_links += sum(
            item.get("assessment_id") == ASSESSMENT_ID
            and item.get("evidence_ids") == (EVIDENCE_ID,)
            for item in findings
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "iterations": iterations,
        "distinct_complete_finding_sets": len(signatures),
        "findings_per_iteration": finding_count // iterations,
        "evidence_links_valid": valid_links,
        "evidence_links_total": finding_count,
        "elapsed_ms_total": round(elapsed_ms, 3),
        "elapsed_ms_per_iteration": round(elapsed_ms / iterations, 3),
    }


def _summarize(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = int(0.95 * (len(ordered) - 1))
    return {
        "median_ms": round(statistics.median(ordered), 4),
        "mean_ms": round(statistics.mean(ordered), 4),
        "p95_ms": round(ordered[p95_index], 4),
    }


def _latency_comparison(
    warmups_per_path: int = 20,
    measured_pairs: int = 250,
) -> dict[str, Any]:
    reviewer = PassiveAssessmentAIReviewer(FixtureAdapter())

    def run(with_review: bool) -> None:
        findings = PassiveHeaderDetector.analyze(ASSESSMENT_ID, TARGET_URL, EVIDENCE)
        if with_review:
            result = reviewer.review_safely(EVIDENCE, findings)
            if result.get("status") != "reviewed":
                raise RuntimeError("The local advisory fixture did not validate.")

    for _ in range(warmups_per_path):
        run(False)
        run(True)

    detector_only: list[float] = []
    detector_plus_fake_reviewer: list[float] = []
    for _ in range(measured_pairs):
        started = time.perf_counter()
        run(False)
        detector_only.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        run(True)
        detector_plus_fake_reviewer.append((time.perf_counter() - started) * 1000)

    detector_summary = _summarize(detector_only)
    advisory_summary = _summarize(detector_plus_fake_reviewer)
    return {
        "warmups_per_path": warmups_per_path,
        "measured_pairs": measured_pairs,
        "findings_per_run": len(PassiveHeaderDetector.analyze(ASSESSMENT_ID, TARGET_URL, EVIDENCE)),
        "deterministic_only": detector_summary,
        "deterministic_plus_local_fake_reviewer": advisory_summary,
        "median_increment_ms": round(advisory_summary["median_ms"] - detector_summary["median_ms"], 4),
        "p95_definition": "sorted sample at index floor(0.95 * (n - 1))",
    }


def main() -> None:
    result = {
        "experiment": "TASK 06.9 offline fixtures; no network or live provider",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "deterministic_repeatability": _detector_repeatability(),
        "local_fake_adapter_latency": _latency_comparison(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
