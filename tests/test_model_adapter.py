"""Unit tests for Phase 8F.4: Provider-Neutral LLM Adapter & Evidence-Grounded Specialist.

Verifies:
- Valid structured responses parsed and grounded correctly.
- Invalid schema and malformed JSON fail closed.
- Unknown evidence IDs and mismatched sources rejected.
- Excerpt verbatim validation enforced.
- Missing or empty evidence triggers immediate fail-closed abstention.
- Explicit abstention modeled correctly.
- Contradictory output (e.g. vulnerable=True with is_abstained=True) rejected.
- Provider timeout and failure fail closed without silent fallback.
- Unauthorized live provider fails closed with DEC-07 boundary notice.
- Strict prohibition of silent fallback from real-provider errors to mock findings.
- Zero unapproved network calls.
- Deterministic repeatability for offline adapters.
- Bounded raw output and secret redaction.
- Compatibility with OrchestrationStateMachine and evaluation replay.
- Strict preservation of invariants (is_confirmed=False, factual_support='not_evaluated').
"""

from __future__ import annotations

import hashlib
import json
import socket
from typing import Any
from unittest.mock import patch

import pytest

from aegiscore.generation import CitationGroundingError
from aegiscore.model_adapter import (
    ContradictoryOutputError,
    DeterministicModelAdapter,
    GroundedSpecialistAdapter,
    LiveProviderExecutionUnavailableError,
    ModelConfigurationError,
    ModelErrorCategory,
    ModelProviderConfig,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ModelResponseValidationError,
    ModelTimeoutError,
    ProviderMode,
    TokenUsage,
    UnauthorizedLiveModelAdapter,
    get_model_adapter,
    is_live_provider_authorized,
    redact_sensitive_text,
    validate_and_parse_specialist_output,
)
from aegiscore.orchestration import (
    AssessmentRequest,
    ClaimCitationRecord,
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    OrchestrationStateMachine,
    OrchestrationState,
    SpecialistFinding,
)
from aegiscore.rag import CitationReference, SourceChunk, SourceMetadata
from aegiscore.specialist_roles import ROLE_XSS_ANALYST, ROLE_SQLI_ANALYST
from aegiscore.evaluation import (
    AdjudicationState,
    CanonicalLocus,
    EvaluationCaseManifestRecord,
    GroundTruthStatus,
    InclusionStatus,
)
from aegiscore.evaluation_harness import (
    ConditionStatus,
    OrchestrationCaseFixture,
    OrchestrationReplayAdapter,
    create_orchestration_replay_adapter,
)


# ---------------------------------------------------------------------------
# Helpers & Synthetic Fixtures
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str = "chk-1", source_id: str = "src-xss", content: str = "target parameter reflected without encoding") -> SourceChunk:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    meta = SourceMetadata(source_id=source_id, content_sha256=digest)
    return SourceChunk(
        chunk_id=chunk_id,
        provenance=meta,
        ordinal=0,
        start_offset=0,
        end_offset=len(content),
        content=content,
        content_sha256=digest,
    )


def _make_bundle(
    chunk_id: str = "chk-1",
    source_id: str = "src-xss",
    content: str = "target parameter reflected without encoding",
    request_id: str = "req-test-01",
) -> EvidenceBundle:
    c = _make_chunk(chunk_id, source_id, content)
    ref = CitationReference(source_id=source_id, chunk_id=chunk_id)
    return EvidenceBundle(
        bundle_id=f"bnd-{request_id}",
        request_id=request_id,
        retrieval_query="xss reflection in parameter",
        chunks=(c,),
        citations=(ref,),
        manifest_fingerprint="sha256-test-manifest",
        approved_source_count=1,
    )


def _make_empty_bundle(request_id: str = "req-test-empty") -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id=f"bnd-{request_id}",
        request_id=request_id,
        retrieval_query="empty search",
        chunks=(),
        citations=(),
        manifest_fingerprint="sha256-test-manifest",
        approved_source_count=0,
        evidence_status="no_approved_evidence",
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_valid_structured_response() -> None:
    """A well-formed structured model response is validated and parsed into a SpecialistFinding."""
    bundle = _make_bundle()
    valid_output = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-79",
        "summary": "Reflected XSS detected: user input is emitted into HTML response without encoding.",
        "reasoning_notes": "Retrieved chunk demonstrates unencoded reflection.",
        "is_abstained": False,
        "claims": [
            {
                "text": "User parameter is reflected without encoding into the HTML response.",
                "citations": [
                    {
                        "source_id": "src-xss",
                        "chunk_id": "chk-1",
                        "cited_excerpt": "reflected without encoding",
                    }
                ],
                "observed_evidence": "Chunk explicitly states: reflected without encoding.",
                "inference": "Vulnerability is plausible given lack of encoding.",
            }
        ],
    }

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": valid_output}
    )
    specialist = GroundedSpecialistAdapter(
        role_id=ROLE_XSS_ANALYST,
        model_adapter=adapter,
    )

    finding = specialist.analyse("req-test-01", bundle)

    assert isinstance(finding, SpecialistFinding)
    assert finding.request_id == "req-test-01"
    assert finding.specialist_role == ROLE_XSS_ANALYST
    assert finding.vulnerability_identified is True
    assert finding.severity == FindingSeverity.HIGH
    assert finding.cwe_id == "CWE-79"
    assert len(finding.proposed_claims) == 1
    assert len(finding.claim_citations) == 1
    assert finding.claim_citations[0].cited_excerpt == "reflected without encoding"
    assert finding.is_confirmed is False
    assert finding.factual_support == "not_evaluated"


def test_markdown_code_fence_handling() -> None:
    """Model output wrapped in markdown code fences is cleanly unwrapped and parsed."""
    bundle = _make_bundle()
    fenced_output = """```json
    {
        "vulnerability_identified": false,
        "severity": "INFO",
        "cwe_id": null,
        "summary": "Analysis inconclusive; abstaining.",
        "reasoning_notes": "Epistemic ambiguity detected.",
        "is_abstained": true,
        "claims": []
    }
    ```"""

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": fenced_output}
    )
    specialist = GroundedSpecialistAdapter(
        role_id=ROLE_XSS_ANALYST,
        model_adapter=adapter,
    )

    finding = specialist.analyse("req-test-01", bundle)
    assert finding.vulnerability_identified is False
    assert finding.severity == FindingSeverity.INFO


def test_invalid_schema_missing_fields_fails_closed() -> None:
    """Model output missing mandatory keys fails closed with ModelResponseValidationError."""
    bundle = _make_bundle()
    incomplete_output = {
        "vulnerability_identified": True,
        # missing severity, summary, is_abstained, claims
    }

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": incomplete_output}
    )
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ModelResponseValidationError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "missing required fields" in str(exc_info.value)


def test_invalid_schema_malformed_json_fails_closed() -> None:
    """Malformed non-JSON output fails closed with ModelResponseValidationError."""
    bundle = _make_bundle()
    malformed = "This is not JSON at all: {unclosed"

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": malformed}
    )
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ModelResponseValidationError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "not valid JSON" in str(exc_info.value)


def test_invalid_severity_enum_fails_closed() -> None:
    """An unknown severity enum string is rejected."""
    bundle = _make_bundle()
    bad_severity = {
        "vulnerability_identified": False,
        "severity": "ULTRA_CRITICAL",
        "summary": "Test summary",
        "reasoning_notes": "",
        "is_abstained": True,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": bad_severity}
    )
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ModelResponseValidationError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "severity 'ULTRA_CRITICAL' is invalid" in str(exc_info.value)


def test_unknown_evidence_chunk_id_rejected() -> None:
    """A claim referencing a chunk ID not present in the evidence bundle is rejected."""
    bundle = _make_bundle()
    bad_chunk_citation = {
        "vulnerability_identified": True,
        "severity": "MEDIUM",
        "cwe_id": "CWE-79",
        "summary": "Reflected XSS",
        "reasoning_notes": "",
        "is_abstained": False,
        "claims": [
            {
                "text": "Reflected input observed.",
                "citations": [
                    {
                        "source_id": "src-xss",
                        "chunk_id": "chk-UNKNOWN-GHOST",
                        "cited_excerpt": None,
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": bad_chunk_citation}
    )
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(CitationGroundingError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "chk-UNKNOWN-GHOST" in str(exc_info.value)


def test_source_id_mismatch_rejected() -> None:
    """A claim citing a source_id inconsistent with the chunk's true provenance is rejected."""
    bundle = _make_bundle(chunk_id="chk-1", source_id="src-xss")
    mismatched_source = {
        "vulnerability_identified": True,
        "severity": "MEDIUM",
        "cwe_id": "CWE-79",
        "summary": "Reflected XSS",
        "reasoning_notes": "",
        "is_abstained": False,
        "claims": [
            {
                "text": "Reflected input observed.",
                "citations": [
                    {
                        "source_id": "src-FABRICATED",
                        "chunk_id": "chk-1",
                        "cited_excerpt": None,
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(
        canned_responses={"req-test-01": mismatched_source}
    )
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(CitationGroundingError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "does not match chunk's source_id" in str(exc_info.value)


def test_cited_excerpt_verbatim_validation() -> None:
    """Verbatim excerpt matching is strictly enforced; mismatched excerpt fails closed."""
    bundle = _make_bundle(content="exact verified text inside chunk")

    # Mismatched excerpt
    mismatched = {
        "vulnerability_identified": True,
        "severity": "LOW",
        "summary": "XSS finding",
        "reasoning_notes": "",
        "is_abstained": False,
        "claims": [
            {
                "text": "Claim statement.",
                "citations": [
                    {
                        "source_id": "src-xss",
                        "chunk_id": "chk-1",
                        "cited_excerpt": "nonexistent text hallucination",
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": mismatched})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(CitationGroundingError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "Cited excerpt does not occur verbatim" in str(exc_info.value)


def test_empty_evidence_bundle_abstains_immediately() -> None:
    """When the evidence bundle is empty or has zero approved sources, abstention is immediate."""
    empty_bundle = _make_empty_bundle()

    # Create an adapter that would fail if called
    def _explode_if_called(req: ModelRequest) -> ModelResponse:
        raise AssertionError("Adapter should not be called on empty evidence bundle!")

    adapter = DeterministicModelAdapter(default_handler=_explode_if_called)
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    finding = specialist.analyse("req-test-empty", empty_bundle)

    assert finding.vulnerability_identified is False
    assert finding.severity == FindingSeverity.INFO
    assert len(finding.proposed_claims) == 0
    assert "No approved evidence available" in finding.summary
    assert finding.is_confirmed is False


def test_explicit_abstention_handling() -> None:
    """When model reports is_abstained=True and vulnerability_identified=False, finding is abstained."""
    bundle = _make_bundle()
    abstained_output = {
        "vulnerability_identified": False,
        "severity": "INFO",
        "cwe_id": None,
        "summary": "Evidence is ambiguous; abstention recommended.",
        "reasoning_notes": "Sanitization functions detected in surrounding code.",
        "is_abstained": True,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": abstained_output})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    finding = specialist.analyse("req-test-01", bundle)

    assert finding.vulnerability_identified is False
    assert finding.severity == FindingSeverity.INFO
    assert finding.is_confirmed is False


def test_contradictory_output_vulnerable_and_abstained_rejected() -> None:
    """vulnerability_identified=True coexisting with is_abstained=True is rejected as contradictory."""
    bundle = _make_bundle()
    contradictory = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "summary": "Contradictory output",
        "reasoning_notes": "",
        "is_abstained": True,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": contradictory})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ContradictoryOutputError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "vulnerability_identified=True cannot coexist with is_abstained=True" in str(exc_info.value)


def test_contradictory_output_vulnerable_with_zero_claims_rejected() -> None:
    """vulnerability_identified=True with 0 claims is rejected as contradictory."""
    bundle = _make_bundle()
    contradictory = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "summary": "Vulnerable without claims",
        "reasoning_notes": "",
        "is_abstained": False,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": contradictory})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ContradictoryOutputError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "requires at least one claim" in str(exc_info.value)


def test_contradictory_output_high_severity_without_vulnerability_rejected() -> None:
    """vulnerability_identified=False with HIGH/CRITICAL severity is rejected as contradictory."""
    bundle = _make_bundle()
    contradictory = {
        "vulnerability_identified": False,
        "severity": "CRITICAL",
        "summary": "High severity but not vulnerable",
        "reasoning_notes": "",
        "is_abstained": True,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": contradictory})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ContradictoryOutputError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "is not permitted when vulnerability_identified=False" in str(exc_info.value)


def test_provider_timeout_fails_closed_without_silent_fallback() -> None:
    """ModelTimeoutError propagates and is NEVER silently replaced by mock findings."""
    bundle = _make_bundle()

    def _timeout_handler(req: ModelRequest) -> ModelResponse:
        raise ModelTimeoutError("Simulated provider timeout deadline exceeded")

    adapter = DeterministicModelAdapter(default_handler=_timeout_handler)
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ModelTimeoutError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "Simulated provider timeout" in str(exc_info.value)


def test_unauthorized_live_provider_fails_closed() -> None:
    """Live provider execution without supervisor approval raises LiveProviderExecutionUnavailableError."""
    config = ModelProviderConfig(
        provider_mode=ProviderMode.LIVE_UNAUTHORIZED,
        model_id="gemini-1.5-pro",
    )
    adapter = UnauthorizedLiveModelAdapter(config)
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)
    bundle = _make_bundle()

    with pytest.raises(LiveProviderExecutionUnavailableError) as exc_info:
        specialist.analyse("req-test-01", bundle)

    assert "DEC-07 in docs/SUPERVISOR_DECISION_REGISTER.md remains PENDING" in str(exc_info.value)
    assert "ADR 0002 mandates default-deny network egress" in str(exc_info.value)


def test_no_silent_fallback_after_real_provider_error() -> None:
    """When a configured provider fails, the error propagates directly without fallback to fake."""
    bundle = _make_bundle()

    class FailingRealProviderAdapter:
        @property
        def config(self) -> ModelProviderConfig:
            return ModelProviderConfig(
                provider_mode=ProviderMode.LIVE_UNAUTHORIZED,
                model_id="live-gemini-pro",
            )

        def complete(self, request: ModelRequest) -> ModelResponse:
            raise ModelProviderError("503 Service Unavailable: Remote API failure", category=ModelErrorCategory.CONNECTION_FAILURE)

    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, FailingRealProviderAdapter())

    with pytest.raises(ModelProviderError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "503 Service Unavailable" in str(exc_info.value)
    assert exc_info.value.category == ModelErrorCategory.CONNECTION_FAILURE


def test_no_unapproved_network_calls() -> None:
    """Verify that adapter and specialist execution perform ZERO socket connections."""
    bundle = _make_bundle()
    valid_output = {
        "vulnerability_identified": False,
        "severity": "INFO",
        "cwe_id": None,
        "summary": "Safe offline execution.",
        "reasoning_notes": "Offline test.",
        "is_abstained": True,
        "claims": [],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": valid_output})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    def _prohibit_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Network connection attempted during offline execution!")

    with patch("socket.socket.connect", side_effect=_prohibit_network):
        finding = specialist.analyse("req-test-01", bundle)

    assert finding.vulnerability_identified is False


def test_deterministic_offline_adapter_repeatability() -> None:
    """Identical inputs produce identical outputs with deterministic hashes."""
    bundle = _make_bundle()
    output = {
        "vulnerability_identified": False,
        "severity": "INFO",
        "cwe_id": None,
        "summary": "Deterministic repeatable test.",
        "reasoning_notes": "Deterministic run.",
        "is_abstained": True,
        "claims": [],
    }

    adapter1 = DeterministicModelAdapter(canned_responses={"req-repeat": output})
    specialist1 = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter1)
    finding1 = specialist1.analyse("req-repeat", bundle)

    adapter2 = DeterministicModelAdapter(canned_responses={"req-repeat": output})
    specialist2 = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter2)
    finding2 = specialist2.analyse("req-repeat", bundle)

    assert finding1.finding_id == finding2.finding_id
    assert finding1.summary == finding2.summary
    assert finding1.severity == finding2.severity


def test_bounded_raw_output_size() -> None:
    """Model output exceeding 65,536 characters is rejected to prevent memory exhaustion."""
    bundle = _make_bundle()
    oversized = "A" * 70000

    adapter = DeterministicModelAdapter(canned_responses={"req-test-01": oversized})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)

    with pytest.raises(ModelResponseValidationError) as exc_info:
        specialist.analyse("req-test-01", bundle)
    assert "exceeds maximum" in str(exc_info.value)


def test_secret_redaction() -> None:
    """Sensitive patterns are redacted from strings and config representations."""
    leaked = "Found api_key = 'AIzaSySecretKey12345' and Bearer eyJhbGciOiJIUzI1NiIn..."
    redacted = redact_sensitive_text(leaked)

    assert "AIzaSySecretKey12345" not in redacted
    assert "***REDACTED***" in redacted

    config = ModelProviderConfig(
        provider_mode=ProviderMode.DETERMINISTIC_FAKE,
        api_key="super_secret_token_123",
    )
    repr_str = repr(config)
    assert "super_secret_token_123" not in repr_str
    assert "***REDACTED***" in repr_str


def test_factory_and_authority_check() -> None:
    """get_model_adapter produces the right adapter and authority check returns False."""
    assert is_live_provider_authorized() is False

    fake_config = ModelProviderConfig(provider_mode=ProviderMode.DETERMINISTIC_FAKE)
    fake_adapter = get_model_adapter(fake_config)
    assert isinstance(fake_adapter, DeterministicModelAdapter)

    live_config = ModelProviderConfig(provider_mode=ProviderMode.LIVE_UNAUTHORIZED)
    live_adapter = get_model_adapter(live_config)
    assert isinstance(live_adapter, UnauthorizedLiveModelAdapter)


def test_compatibility_with_orchestration_state_machine() -> None:
    """A SpecialistFinding produced by GroundedSpecialistAdapter integrates with OrchestrationStateMachine."""
    bundle = _make_bundle(request_id="req-orch-01")
    output = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-79",
        "summary": "Verified XSS via grounded adapter",
        "reasoning_notes": "Input reaches sink without encoding.",
        "is_abstained": False,
        "claims": [
            {
                "text": "User input reflected into HTML response.",
                "citations": [
                    {
                        "source_id": "src-xss",
                        "chunk_id": "chk-1",
                        "cited_excerpt": "reflected without encoding",
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-orch-01": output})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)
    finding = specialist.analyse("req-orch-01", bundle)

    request = AssessmentRequest(
        request_id="req-orch-01",
        target_url="http://127.0.0.1:3000/rest/search",
        vulnerability_category="XSS",
        authorized_scope=("/rest",),
    )
    sm = OrchestrationStateMachine(request)
    sm.validate_request()
    sm.record_retrieval(bundle)
    assert sm.current_state == OrchestrationState.RETRIEVAL_COMPLETED

    sm.record_specialist_analysis(finding)
    assert sm.current_state == OrchestrationState.SPECIALIST_ANALYSIS_COMPLETED
    assert sm.specialist_finding is finding
    assert sm.specialist_finding.is_confirmed is False


def test_compatibility_with_evaluation_replay() -> None:
    """A SpecialistFinding produced by GroundedSpecialistAdapter can be replayed in OrchestrationReplayAdapter."""
    bundle = _make_bundle(request_id="req-replay-01")
    output = {
        "vulnerability_identified": True,
        "severity": "HIGH",
        "cwe_id": "CWE-79",
        "summary": "Replay specialist finding",
        "reasoning_notes": "Grounding verified.",
        "is_abstained": False,
        "claims": [
            {
                "text": "Parameter reflected without encoding.",
                "citations": [
                    {
                        "source_id": "src-xss",
                        "chunk_id": "chk-1",
                        "cited_excerpt": "reflected without encoding",
                    }
                ],
            }
        ],
    }

    adapter = DeterministicModelAdapter(canned_responses={"req-replay-01": output})
    specialist = GroundedSpecialistAdapter(ROLE_XSS_ANALYST, adapter)
    finding = specialist.analyse("req-replay-01", bundle)

    case_record = EvaluationCaseManifestRecord(
        case_id="CASE-MODEL-001",
        locus=CanonicalLocus(target_uri="http://127.0.0.1:3000/api", parameter="q", cwe_id="CWE-79"),
        benchmark_target="juice-shop",
        benchmark_version="15.0.0",
        vulnerability_class="XSS",
        expected_label=GroundTruthStatus.VULNERABLE,
        inclusion_status=InclusionStatus.INCLUDED,
        review_status=AdjudicationState.ADJUDICATED,
        ground_truth_provenance="official-benchmark",
    )

    fixture = OrchestrationCaseFixture(
        case_id="CASE-MODEL-001",
        target_url="http://127.0.0.1:3000/api",
        authorized_scope=("/api",),
        vulnerability_category="XSS",
        evidence_bundle=bundle,
        specialist_finding=finding,
        review_notes="Evidence reviewed and consistent.",
    )

    replay_adapter = create_orchestration_replay_adapter(
        runner_id="model-replay-runner",
        case_manifests=[case_record],
        case_fixtures={"CASE-MODEL-001": fixture},
    )

    run_record = replay_adapter.run_case(case_record, repeat_index=0)

    assert run_record.case_id == "CASE-MODEL-001"
    assert run_record.result.is_incomplete is False
    meta = run_record.reproducibility_metadata
    assert meta["final_state"] == OrchestrationState.COMPLETED.value
    assert meta["confidence_is_calibrated"] == "False"
