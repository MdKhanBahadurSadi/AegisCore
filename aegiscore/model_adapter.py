"""Provider-neutral model adapter and evidence-grounded specialist.

This module provides:
  - Provider-neutral model request/response contracts with structured output validation,
    request tracking, token usage accounting, and typed error categories.
  - Explicit provider configuration (deterministic fake vs. unauthorized live provider).
  - DeterministicModelAdapter for reproducible offline test fixtures and replay.
  - UnauthorizedLiveModelAdapter enforcing default-deny egress when DEC-07 is PENDING.
  - GroundedSpecialistAdapter: an evidence-grounded specialist implementing the
    vulnerability analyst contract, strictly citing supplied evidence, distinguishing
    observed facts from inferences, and validating all schema and citations before
    findings enter orchestration.

Strict invariants:
  - Zero unapproved network calls.
  - Zero silent fallback from real/live providers to mock/fake models.
  - confidence_is_calibrated = False always.
  - factual_support = 'not_evaluated' always.
  - No secret or credential leakage in logs, exceptions, or string representations.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, Sequence

from aegiscore.claim_validation import validate_citation_excerpt
from aegiscore.generation import (
    CitationGroundingError,
    GeneratedClaim,
    GenerationContractError,
)
from aegiscore.orchestration import (
    ClaimCitationRecord,
    EvidenceBundle,
    FindingSeverity,
    OrchestrationContractError,
    SpecialistFinding,
)
from aegiscore.rag import (
    CitationReference,
    RagContractError,
    SourceChunk,
    _nonempty_text,
)
from aegiscore.specialist_roles import get_role_spec


# ---------------------------------------------------------------------------
# Enums and Error Hierarchy
# ---------------------------------------------------------------------------


class ProviderMode(str, Enum):
    """Explicit model provider execution mode."""

    DETERMINISTIC_FAKE = "deterministic_fake"
    LIVE_UNAUTHORIZED = "live_unauthorized"


class ModelErrorCategory(str, Enum):
    """Granular error categories for model adapter operations."""

    TIMEOUT = "timeout"
    AUTHENTICATION_UNAVAILABLE = "authentication_unavailable"
    PROVIDER_UNAUTHORIZED = "provider_unauthorized"
    CONNECTION_FAILURE = "connection_failure"
    SCHEMA_VALIDATION_FAILURE = "schema_validation_failure"
    CONTRADICTORY_OUTPUT = "contradictory_output"
    INTERNAL_PROVIDER_ERROR = "internal_provider_error"


class ModelAdapterError(Exception):
    """Base exception for all model adapter operations."""


class ModelConfigurationError(ModelAdapterError):
    """Model adapter configuration is invalid or inconsistent."""


class ModelProviderError(ModelAdapterError):
    """Error encountered during model provider execution."""

    def __init__(self, message: str, category: ModelErrorCategory = ModelErrorCategory.INTERNAL_PROVIDER_ERROR) -> None:
        super().__init__(message)
        self.category = category


class ModelTimeoutError(ModelProviderError):
    """Model provider execution exceeded configured timeout deadline."""

    def __init__(self, message: str = "Model execution exceeded timeout deadline") -> None:
        super().__init__(message, category=ModelErrorCategory.TIMEOUT)


class LiveProviderExecutionUnavailableError(ModelProviderError):
    """Attempted live model execution when provider is unauthorized or unavailable."""

    def __init__(
        self,
        message: str = (
            "Live model provider execution is unauthorized and unavailable. "
            "Decision DEC-07 in docs/SUPERVISOR_DECISION_REGISTER.md remains PENDING and "
            "ADR 0002 mandates default-deny network egress."
        ),
    ) -> None:
        super().__init__(message, category=ModelErrorCategory.PROVIDER_UNAUTHORIZED)


class ModelResponseValidationError(ModelAdapterError):
    """Model output violates schema, enum, citation, or grounding contracts."""

    def __init__(
        self,
        message: str,
        category: ModelErrorCategory = ModelErrorCategory.SCHEMA_VALIDATION_FAILURE,
    ) -> None:
        super().__init__(message)
        self.category = category


class ContradictoryOutputError(ModelResponseValidationError):
    """Model output contains self-contradictory claims or unsupported conclusions."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ModelErrorCategory.CONTRADICTORY_OUTPUT)


# ---------------------------------------------------------------------------
# Sensitive Content & Secret Redaction
# ---------------------------------------------------------------------------

_MAX_RAW_RESPONSE_CHARS = 65536

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)([^'\s\"\n\r]{4,})"),
    re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{8,})"),
    re.compile(r"(?i)(password\s*[:=]\s*['\"]?)([^'\s\"\n\r]{3,})"),
    re.compile(r"(?i)(secret\s*[:=]\s*['\"]?)([^'\s\"\n\r]{4,})"),
)


def redact_sensitive_text(text: str) -> str:
    """Redact identifiable credentials or secrets from text before recording."""
    if not isinstance(text, str):
        return ""
    result = text
    for pat in _SECRET_PATTERNS:
        result = pat.sub(r"\1***REDACTED***", result)
    return result


# ---------------------------------------------------------------------------
# Data Contracts: Configuration, Request, Response, Usage
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Accounted token consumption for a model request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        for name, val in (
            ("prompt_tokens", self.prompt_tokens),
            ("completion_tokens", self.completion_tokens),
            ("total_tokens", self.total_tokens),
        ):
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ModelConfigurationError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ModelProviderConfig:
    """Explicit configuration for a model provider."""

    provider_mode: ProviderMode = ProviderMode.DETERMINISTIC_FAKE
    model_id: str = "deterministic-fake-specialist-v1"
    timeout_seconds: float = 30.0
    temperature: float = 0.0
    max_tokens: int | None = None
    api_endpoint: str | None = None
    api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.provider_mode, ProviderMode):
            try:
                object.__setattr__(self, "provider_mode", ProviderMode(self.provider_mode))
            except (ValueError, TypeError) as exc:
                raise ModelConfigurationError(f"Invalid provider_mode '{self.provider_mode}'") from exc

        try:
            _nonempty_text(self.model_id, "model_id")
        except RagContractError as exc:
            raise ModelConfigurationError(str(exc)) from exc

        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ModelConfigurationError("timeout_seconds must be a positive number")

        if isinstance(self.temperature, bool) or not isinstance(self.temperature, (int, float)) or not (0.0 <= self.temperature <= 2.0):
            raise ModelConfigurationError("temperature must be bounded in [0.0, 2.0]")

        if self.max_tokens is not None:
            if isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
                raise ModelConfigurationError("max_tokens must be a positive integer if specified")

    def __repr__(self) -> str:
        key_repr = "'***REDACTED***'" if self.api_key else "None"
        return (
            f"ModelProviderConfig(provider_mode={self.provider_mode}, model_id='{self.model_id}', "
            f"timeout_seconds={self.timeout_seconds}, temperature={self.temperature}, "
            f"api_key={key_repr})"
        )


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Input request for model completion."""

    request_id: str
    model_id: str
    provider_mode: ProviderMode
    system_prompt: str = ""
    user_prompt: str = ""
    expected_schema: dict[str, Any] | None = None
    timeout_seconds: float = 30.0
    temperature: float = 0.0

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.model_id, "model_id")
        except RagContractError as exc:
            raise ModelConfigurationError(str(exc)) from exc

        if not isinstance(self.provider_mode, ProviderMode):
            raise ModelConfigurationError("provider_mode must be a ProviderMode enum")


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Outcome of model completion."""

    request_id: str
    model_id: str
    provider_mode: ProviderMode
    raw_content: str
    structured_output: dict[str, Any] | None = None
    usage: TokenUsage | None = None
    execution_duration_ms: float = 0.0

    def __post_init__(self) -> None:
        try:
            _nonempty_text(self.request_id, "request_id")
            _nonempty_text(self.model_id, "model_id")
        except RagContractError as exc:
            raise ModelConfigurationError(str(exc)) from exc

        if not isinstance(self.provider_mode, ProviderMode):
            raise ModelConfigurationError("provider_mode must be a ProviderMode enum")

        if len(self.raw_content) > _MAX_RAW_RESPONSE_CHARS:
            raise ModelResponseValidationError(
                f"raw_content length {len(self.raw_content)} exceeds maximum {_MAX_RAW_RESPONSE_CHARS}"
            )


# ---------------------------------------------------------------------------
# Model Adapter Protocol & Implementations
# ---------------------------------------------------------------------------


class ModelAdapterInterface(Protocol):
    """Provider-neutral model adapter interface."""

    @property
    def config(self) -> ModelProviderConfig:
        """The configuration under which this adapter operates."""
        ...

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Execute model completion for the supplied request."""
        ...


class DeterministicModelAdapter:
    """Deterministic offline model adapter for unit testing and offline replay.

    Produces repeatable, deterministic responses with zero network calls and no API keys.
    """

    def __init__(
        self,
        config: ModelProviderConfig | None = None,
        *,
        canned_responses: Mapping[str, ModelResponse | dict[str, Any] | str] | None = None,
        default_handler: Callable[[ModelRequest], ModelResponse] | None = None,
    ) -> None:
        if config is None:
            config = ModelProviderConfig(
                provider_mode=ProviderMode.DETERMINISTIC_FAKE,
                model_id="deterministic-fake-specialist-v1",
            )
        elif config.provider_mode != ProviderMode.DETERMINISTIC_FAKE:
            raise ModelConfigurationError(
                f"DeterministicModelAdapter requires provider_mode 'deterministic_fake', got '{config.provider_mode}'"
            )
        self._config = config
        self._canned_responses = dict(canned_responses) if canned_responses is not None else {}
        self._default_handler = default_handler

    @property
    def config(self) -> ModelProviderConfig:
        return self._config

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Execute deterministic completion without network access."""
        if not isinstance(request, ModelRequest):
            raise ModelConfigurationError("request must be a ModelRequest instance")

        # Check canned responses by request_id
        if request.request_id in self._canned_responses:
            canned = self._canned_responses[request.request_id]
            if isinstance(canned, ModelResponse):
                return canned
            if isinstance(canned, dict):
                return ModelResponse(
                    request_id=request.request_id,
                    model_id=self._config.model_id,
                    provider_mode=self._config.provider_mode,
                    raw_content=json.dumps(canned),
                    structured_output=canned,
                    usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                    execution_duration_ms=1.0,
                )
            if isinstance(canned, str):
                parsed = None
                try:
                    parsed = json.loads(canned)
                except Exception:
                    pass
                return ModelResponse(
                    request_id=request.request_id,
                    model_id=self._config.model_id,
                    provider_mode=self._config.provider_mode,
                    raw_content=canned,
                    structured_output=parsed if isinstance(parsed, dict) else None,
                    usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                    execution_duration_ms=1.0,
                )

        if self._default_handler is not None:
            return self._default_handler(request)

        # Default fallback response: deterministic abstention
        default_output = {
            "vulnerability_identified": False,
            "severity": "INFO",
            "cwe_id": None,
            "summary": "Deterministic fake analysis: no vulnerability confirmed from supplied evidence.",
            "reasoning_notes": "Deterministic fake model output. No active live analysis.",
            "is_abstained": True,
            "claims": [],
        }
        return ModelResponse(
            request_id=request.request_id,
            model_id=self._config.model_id,
            provider_mode=self._config.provider_mode,
            raw_content=json.dumps(default_output),
            structured_output=default_output,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            execution_duration_ms=1.0,
        )


class UnauthorizedLiveModelAdapter:
    """Fails closed whenever a live provider call is attempted without supervisor approval.

    Ensures that unapproved live provider execution NEVER silently falls back to a fake model.
    """

    def __init__(self, config: ModelProviderConfig) -> None:
        if config.provider_mode == ProviderMode.DETERMINISTIC_FAKE:
            raise ModelConfigurationError(
                "UnauthorizedLiveModelAdapter cannot be configured with DETERMINISTIC_FAKE mode"
            )
        self._config = config

    @property
    def config(self) -> ModelProviderConfig:
        return self._config

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Fail closed immediately with explicit boundary violation error."""
        raise LiveProviderExecutionUnavailableError(
            f"Live model provider '{self._config.provider_mode.value}' is unauthorized and unavailable. "
            "Decision DEC-07 in docs/SUPERVISOR_DECISION_REGISTER.md remains PENDING. "
            "ADR 0002 mandates default-deny network egress."
        )


def is_live_provider_authorized() -> bool:
    """Return whether live external LLM provider execution has been supervisor-approved.

    Currently returns False: DEC-07 is PENDING in docs/SUPERVISOR_DECISION_REGISTER.md.
    """
    return False


def get_model_adapter(config: ModelProviderConfig) -> ModelAdapterInterface:
    """Factory creating the appropriate adapter based on explicit configuration."""
    if not isinstance(config, ModelProviderConfig):
        raise ModelConfigurationError("config must be a ModelProviderConfig instance")
    if config.provider_mode == ProviderMode.DETERMINISTIC_FAKE:
        return DeterministicModelAdapter(config)
    return UnauthorizedLiveModelAdapter(config)


# ---------------------------------------------------------------------------
# Specialist Output Schema & Strict Validation
# ---------------------------------------------------------------------------

_VALID_SEVERITIES: frozenset[str] = frozenset({
    "INFO",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
})


def _strip_markdown_fences(content: str) -> str:
    """Strip optional ```json ... ``` code fence markers."""
    trimmed = content.strip()
    if trimmed.startswith("```"):
        first_newline = trimmed.find("\n")
        if first_newline != -1:
            trimmed = trimmed[first_newline + 1 :]
        if trimmed.endswith("```"):
            trimmed = trimmed[:-3]
    return trimmed.strip()


def validate_and_parse_specialist_output(
    raw_output: dict[str, Any] | str,
    bundle: EvidenceBundle,
    request_id: str,
    role_id: str,
) -> SpecialistFinding:
    """Strictly validate and parse raw model output into a typed SpecialistFinding.

    Enforces:
    1. Bounded size and valid JSON syntax.
    2. Strict schema typing and enum values.
    3. Mandatory citation matching against bundle chunks.
    4. Exact verbatim excerpt matching when cited_excerpt is supplied.
    5. No contradictory claims (e.g. vulnerable=True with is_abstained=True, or vulnerable=True with 0 claims).
    6. Preservation of invariants: is_confirmed=False, factual_support='not_evaluated'.
    """
    if isinstance(raw_output, str):
        if len(raw_output) > _MAX_RAW_RESPONSE_CHARS:
            raise ModelResponseValidationError(
                f"Model response size ({len(raw_output)} chars) exceeds maximum allowed ({_MAX_RAW_RESPONSE_CHARS})"
            )
        cleaned = _strip_markdown_fences(raw_output)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ModelResponseValidationError(f"Model output is not valid JSON: {exc}") from exc
    elif isinstance(raw_output, dict):
        parsed = raw_output
    else:
        raise ModelResponseValidationError(
            f"Model output must be a dict or JSON string, got {type(raw_output).__name__}"
        )

    if not isinstance(parsed, dict):
        raise ModelResponseValidationError("Model output JSON root must be an object/dict")

    # Required top-level keys
    required_keys = {"vulnerability_identified", "severity", "summary", "is_abstained", "claims"}
    missing = required_keys - set(parsed.keys())
    if missing:
        raise ModelResponseValidationError(f"Model output missing required fields: {sorted(missing)}")

    # Field type validation
    vuln_identified = parsed["vulnerability_identified"]
    if not isinstance(vuln_identified, bool):
        raise ModelResponseValidationError("vulnerability_identified must be a boolean")

    is_abstained = parsed["is_abstained"]
    if not isinstance(is_abstained, bool):
        raise ModelResponseValidationError("is_abstained must be a boolean")

    severity_raw = parsed["severity"]
    if not isinstance(severity_raw, str) or severity_raw.upper() not in _VALID_SEVERITIES:
        raise ModelResponseValidationError(
            f"severity '{severity_raw}' is invalid; must be one of {sorted(_VALID_SEVERITIES)}"
        )
    severity = FindingSeverity[severity_raw.upper()]

    summary = parsed["summary"]
    if not isinstance(summary, str) or not summary.strip():
        raise ModelResponseValidationError("summary must be non-empty text")

    reasoning_notes = parsed.get("reasoning_notes", "")
    if not isinstance(reasoning_notes, str):
        raise ModelResponseValidationError("reasoning_notes must be a string")

    cwe_id = parsed.get("cwe_id")
    if cwe_id is not None and not isinstance(cwe_id, str):
        raise ModelResponseValidationError("cwe_id must be a string or None")

    raw_claims = parsed["claims"]
    if not isinstance(raw_claims, list):
        raise ModelResponseValidationError("claims must be a list")

    # Contradiction checks
    if vuln_identified and is_abstained:
        raise ContradictoryOutputError(
            "Model output is self-contradictory: vulnerability_identified=True cannot coexist with is_abstained=True"
        )

    if vuln_identified and len(raw_claims) == 0:
        raise ContradictoryOutputError(
            "Model output is self-contradictory: vulnerability_identified=True requires at least one claim"
        )

    if not vuln_identified and severity in (FindingSeverity.HIGH, FindingSeverity.CRITICAL):
        raise ContradictoryOutputError(
            f"Model output is self-contradictory: severity={severity.value} is not permitted when vulnerability_identified=False"
        )

    # Validate citations against bundle
    chunk_map: dict[str, SourceChunk] = {chunk.chunk_id: chunk for chunk in bundle.chunks}
    generated_claims: list[GeneratedClaim] = []
    claim_citations: list[ClaimCitationRecord] = []

    for idx, c_dict in enumerate(raw_claims):
        if not isinstance(c_dict, dict):
            raise ModelResponseValidationError(f"Claim at index {idx} must be a dict")

        claim_text = c_dict.get("text")
        if not isinstance(claim_text, str) or not claim_text.strip():
            raise ModelResponseValidationError(f"Claim at index {idx} missing non-empty 'text'")

        citations_list = c_dict.get("citations")
        if not isinstance(citations_list, list) or len(citations_list) == 0:
            raise ModelResponseValidationError(f"Claim at index {idx} must contain a non-empty 'citations' list")

        claim_id = f"claim-{request_id}-{idx + 1}"
        claim_refs: list[CitationReference] = []

        for cit_idx, cit_dict in enumerate(citations_list):
            if not isinstance(cit_dict, dict):
                raise ModelResponseValidationError(
                    f"Citation at index {cit_idx} in claim {idx} must be a dict"
                )

            source_id = cit_dict.get("source_id")
            chunk_id = cit_dict.get("chunk_id")
            cited_excerpt = cit_dict.get("cited_excerpt")

            if not isinstance(source_id, str) or not source_id.strip():
                raise ModelResponseValidationError(
                    f"Citation {cit_idx} in claim {idx} has invalid source_id"
                )
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ModelResponseValidationError(
                    f"Citation {cit_idx} in claim {idx} has invalid chunk_id"
                )

            # Check chunk existence in bundle
            chunk = chunk_map.get(chunk_id)
            if chunk is None:
                raise CitationGroundingError(
                    f"Claim {idx} references chunk '{chunk_id}' not found in evidence bundle hits"
                )

            # Check source ID match
            chunk_source_id = getattr(chunk.provenance, "source_id", getattr(chunk, "source_id", ""))
            if chunk_source_id != source_id:
                raise CitationGroundingError(
                    f"Citation source_id '{source_id}' does not match chunk's source_id '{chunk_source_id}'"
                )

            ref = CitationReference(source_id=source_id, chunk_id=chunk_id)

            # Check excerpt validity if present
            if cited_excerpt is not None:
                if not isinstance(cited_excerpt, str) or not cited_excerpt.strip():
                    raise ModelResponseValidationError(
                        f"Citation {cit_idx} in claim {idx} has empty or non-string cited_excerpt"
                    )
                # Verify verbatim presence
                validate_citation_excerpt(ref, chunk, cited_excerpt=cited_excerpt)

            claim_refs.append(ref)
            claim_citations.append(
                ClaimCitationRecord(
                    claim_id=claim_id,
                    citation=ref,
                    cited_excerpt=cited_excerpt,
                    factual_support="not_evaluated",
                )
            )

        generated_claims.append(
            GeneratedClaim(
                text=claim_text,
                citations=tuple(claim_refs),
                factual_support="not_evaluated",
            )
        )

    finding_id = hashlib.sha256(
        f"finding-{request_id}-{role_id}-{summary}".encode("utf-8")
    ).hexdigest()[:16]

    return SpecialistFinding(
        finding_id=finding_id,
        request_id=request_id,
        specialist_role=role_id,
        vulnerability_identified=vuln_identified,
        severity=severity,
        summary=summary,
        proposed_claims=tuple(generated_claims),
        cwe_id=cwe_id,
        claim_citations=tuple(claim_citations),
        reasoning_notes=reasoning_notes,
        is_confirmed=False,
        factual_support="not_evaluated",
    )


# ---------------------------------------------------------------------------
# Grounded Specialist Adapter
# ---------------------------------------------------------------------------


class GroundedSpecialistAdapter:
    """Evidence-grounded vulnerability specialist backed by a provider-neutral model adapter.

    Complies with the VulnerabilityAnalystFakeProtocol contract:
        analyse(request_id: str, bundle: EvidenceBundle) -> SpecialistFinding

    Guarantees:
      - Supplies only explicitly retrieved evidence chunks to the model adapter.
      - Enforces strict output validation against evidence bundle before returning.
      - Automatically abstains when evidence bundle is empty or approved_source_count == 0.
      - Preserves is_confirmed=False and factual_support='not_evaluated'.
      - Does NOT silently catch real provider errors and fall back to mock models.
      - Zero autonomous scanning, zero exploit execution, zero target HTTP requests.
    """

    def __init__(
        self,
        role_id: str,
        model_adapter: ModelAdapterInterface,
        *,
        system_prompt_override: str | None = None,
    ) -> None:
        self._role_spec = get_role_spec(role_id)
        if not hasattr(model_adapter, "complete") or not hasattr(model_adapter, "config"):
            raise ModelConfigurationError("model_adapter must implement ModelAdapterInterface")
        self._role_id = role_id
        self._model_adapter = model_adapter
        self._system_prompt_override = system_prompt_override

    @property
    def role_id(self) -> str:
        return self._role_id

    @property
    def model_adapter(self) -> ModelAdapterInterface:
        return self._model_adapter

    def analyse(self, request_id: str, bundle: EvidenceBundle) -> SpecialistFinding:
        """Execute evidence-grounded specialist analysis.

        Fails closed on missing evidence, provider errors, or schema validation failures.
        """
        try:
            _nonempty_text(request_id, "request_id")
        except RagContractError as exc:
            raise OrchestrationContractError(str(exc)) from exc

        if not isinstance(bundle, EvidenceBundle):
            raise OrchestrationContractError("bundle must be an EvidenceBundle instance")

        # 1. Immediate fail-closed check for empty evidence
        if bundle.approved_source_count == 0 or len(bundle.chunks) == 0:
            finding_id = hashlib.sha256(
                f"finding-{request_id}-{self._role_id}-no-evidence".encode("utf-8")
            ).hexdigest()[:16]
            return SpecialistFinding(
                finding_id=finding_id,
                request_id=request_id,
                specialist_role=self._role_id,
                vulnerability_identified=False,
                severity=FindingSeverity.INFO,
                summary="No approved evidence available; abstaining from analysis.",
                proposed_claims=(),
                reasoning_notes="Empty evidence bundle or zero approved sources; abstention enforced.",
                is_confirmed=False,
                factual_support="not_evaluated",
            )

        # 2. Build prompt with strictly bounded evidence and role context
        system_prompt = self._system_prompt_override or self._build_system_prompt()
        user_prompt = self._build_user_prompt(request_id, bundle)

        request = ModelRequest(
            request_id=request_id,
            model_id=self._model_adapter.config.model_id,
            provider_mode=self._model_adapter.config.provider_mode,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=self._model_adapter.config.timeout_seconds,
            temperature=self._model_adapter.config.temperature,
        )

        # 3. Complete model request (do NOT catch provider errors for silent fallback!)
        response = self._model_adapter.complete(request)

        # 4. Strict validation and parsing
        raw = response.structured_output if response.structured_output is not None else response.raw_content
        return validate_and_parse_specialist_output(raw, bundle, request_id, self._role_id)

    def _build_system_prompt(self) -> str:
        return (
            f"You are the {self._role_spec.display_name} for AEGISCORE AI.\n"
            f"Responsibility: {self._role_spec.responsibility}\n"
            f"Permitted categories: {', '.join(self._role_spec.permitted_categories)}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. You MUST cite ONLY the provided Chunk IDs and Source IDs. Never invent citations.\n"
            "2. Distinguish observed evidence from inference and unknowns.\n"
            "3. If evidence is ambiguous, incomplete, sanitized, or contains epistemic keywords "
            "('unclear', 'possible', 'may be'), set 'is_abstained': true and 'vulnerability_identified': false.\n"
            "4. Never claim a vulnerability is confirmed. All findings are hypotheses.\n"
            "5. Return your response strictly as JSON matching this schema:\n"
            "{\n"
            '  "vulnerability_identified": bool,\n'
            '  "severity": "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
            '  "cwe_id": string | null,\n'
            '  "summary": string,\n'
            '  "reasoning_notes": string,\n'
            '  "is_abstained": bool,\n'
            '  "claims": [\n'
            "    {\n"
            '      "text": string,\n'
            '      "citations": [{"source_id": string, "chunk_id": string, "cited_excerpt": string | null}],\n'
            '      "observed_evidence": string,\n'
            '      "inference": string\n'
            "    }\n"
            "  ]\n"
            "}"
        )

    def _build_user_prompt(self, request_id: str, bundle: EvidenceBundle) -> str:
        chunks_text = []
        for idx, chunk in enumerate(bundle.chunks):
            source_id = getattr(chunk.provenance, "source_id", getattr(chunk, "source_id", ""))
            chunks_text.append(
                f"--- EVIDENCE CHUNK {idx + 1} ---\n"
                f"Chunk ID: {chunk.chunk_id}\n"
                f"Source ID: {source_id}\n"
                f"Section: {chunk.section or 'N/A'}\n"
                f"Content:\n{chunk.content}\n"
            )

        return (
            f"Assessment Request ID: {request_id}\n"
            f"Retrieval Query: {bundle.retrieval_query}\n"
            f"Evidence Chunks ({len(bundle.chunks)} available):\n\n"
            + "\n".join(chunks_text)
        )


__all__ = [
    "ContradictoryOutputError",
    "DeterministicModelAdapter",
    "GroundedSpecialistAdapter",
    "LiveProviderExecutionUnavailableError",
    "ModelAdapterError",
    "ModelAdapterInterface",
    "ModelConfigurationError",
    "ModelErrorCategory",
    "ModelProviderConfig",
    "ModelProviderError",
    "ModelRequest",
    "ModelResponse",
    "ModelResponseValidationError",
    "ModelTimeoutError",
    "ProviderMode",
    "TokenUsage",
    "UnauthorizedLiveModelAdapter",
    "get_model_adapter",
    "is_live_provider_authorized",
    "redact_sensitive_text",
    "validate_and_parse_specialist_output",
]
