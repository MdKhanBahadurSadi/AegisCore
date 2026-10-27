"""Fake-transport-compatible execution boundary for deterministic policy permits.

This module provides no HTTP client, socket, DNS, shell, or other I/O. Any
transport is injected; production transports are intentionally absent.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from aegiscore.safety import (
    CanonicalOperation,
    ConfigurationError,
    OperationAuthorization,
    OperationIntent,
    OperationPermit,
    PolicyDecision,
    PolicyReason,
    PolicyEngine,
)


class OperationTransport(Protocol):
    """Injected dispatch interface. Implementations receive only canonical data."""

    def dispatch(self, operation: CanonicalOperation, permit: OperationPermit) -> object:
        """Record or perform one already-authorized operation."""


class CancellationToken:
    """Thread-safe, one-way cancellation signal for one guarded execution context."""

    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()


@dataclass(frozen=True, slots=True)
class DispatchResult:
    decision: PolicyDecision
    transport_invoked: bool
    result: object | None = None

    @property
    def allowed(self) -> bool:
        return self.decision.allowed and self.transport_invoked


class GuardedExecutionBoundary:
    """Latch denials and consume engine permits before calling an injected transport."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        transport: OperationTransport,
        *,
        cancellation: CancellationToken | None = None,
    ) -> None:
        if not isinstance(policy_engine, PolicyEngine):
            raise ConfigurationError("policy engine is missing or invalid")
        if transport is None or not callable(getattr(transport, "dispatch", None)):
            raise ConfigurationError("operation transport is missing or invalid")
        if cancellation is not None and not isinstance(cancellation, CancellationToken):
            raise ConfigurationError("cancellation token is invalid")
        self._policy_engine = policy_engine
        self._transport = transport
        self._cancellation = cancellation or CancellationToken()
        self._lock = threading.RLock()
        self._terminal_denial: PolicyDecision | None = None

    @property
    def terminal_denial(self) -> PolicyDecision | None:
        with self._lock:
            return self._terminal_denial

    def authorize(self, intent: OperationIntent) -> OperationAuthorization:
        return self._authorize(intent, is_redirect=False)

    def authorize_redirect(self, intent: OperationIntent) -> OperationAuthorization:
        """Authorize one redirect hop; automatic redirect following is not provided."""
        return self._authorize(intent, is_redirect=True)

    def dispatch(self, authorization: object, intent: object) -> DispatchResult:
        """Consume the exact permit and invoke the injected transport at most once."""
        with self._lock:
            if self._terminal_denial is not None:
                return DispatchResult(self._workflow_denied(), False)
            if self._cancellation.cancelled:
                return DispatchResult(self._latch(PolicyReason.RUN_CANCELLED, self._target_id(intent)), False)
            if not isinstance(authorization, OperationAuthorization) or authorization.permit is None:
                return DispatchResult(self._latch(PolicyReason.PERMIT_INVALID, self._target_id(intent)), False)

            decision = self._policy_engine.consume_operation_permit(authorization, intent)
            if not decision.allowed:
                self._terminal_denial = decision
                return DispatchResult(decision, False)
            # Recheck cancellation immediately before handing off to the injected transport.
            if self._cancellation.cancelled:
                return DispatchResult(self._latch(PolicyReason.RUN_CANCELLED, authorization.permit.operation.target_id), False)
            try:
                result = self._transport.dispatch(authorization.permit.operation, authorization.permit)
            except Exception:
                failure = self._latch(PolicyReason.TRANSPORT_FAILURE, authorization.permit.operation.target_id)
                return DispatchResult(failure, True)
            return DispatchResult(decision, True, result)

    def _authorize(self, intent: OperationIntent, *, is_redirect: bool) -> OperationAuthorization:
        with self._lock:
            if self._terminal_denial is not None:
                return OperationAuthorization(self._workflow_denied(), None)
            if self._cancellation.cancelled:
                decision = self._latch(PolicyReason.RUN_CANCELLED, self._target_id(intent))
                return OperationAuthorization(decision, None)
            authorization = self._policy_engine.authorize_operation(intent, is_redirect=is_redirect)
            if not authorization.allowed:
                self._terminal_denial = authorization.decision
            return authorization

    def _latch(self, reason: PolicyReason, target_id: str | None) -> PolicyDecision:
        if self._terminal_denial is not None:
            return self._workflow_denied()
        decision = self._policy_engine.latch_operation_denial(reason, target_id)
        self._terminal_denial = decision
        return decision

    def _workflow_denied(self) -> PolicyDecision:
        target_id = self._terminal_denial.target_id if self._terminal_denial is not None else None
        return self._policy_engine.workflow_denial(target_id)

    @staticmethod
    def _target_id(intent: object) -> str | None:
        value = getattr(intent, "target_id", None)
        return value if isinstance(value, str) else None
