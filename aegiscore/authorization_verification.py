"""Fail-closed contract for authoritative target-approval verification.

This module defines the trust boundary only. A deployment must inject a verifier
backed by a real authority and pinned issuer keys. The repository intentionally
does not mint approvals or treat a local authorization-reference string as proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from aegiscore.safety import ApprovedTargetRegistration


class AuthorizationFailureReason(str, Enum):
    INVALID_SIGNATURE = "invalid_signature"
    UNKNOWN_ISSUER = "unknown_issuer"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"
    REVOKED = "revoked"
    INVALID_EVIDENCE = "invalid_evidence"
    UNAVAILABLE = "unavailable"


class AuthorizationVerificationError(RuntimeError):
    """A fail-closed authorization verification result."""

    def __init__(self, reason: AuthorizationFailureReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class VerifiedAuthorizationEvidence:
    """Evidence returned only after verifying an issuer signature and revocation state.

    The verifier must validate a signature over the approval reference, target ID,
    canonical endpoint, registration version, issuer/key IDs, and validity window.
    It must check revocation against an authoritative, still-valid source on every
    call. `signature_sha256` identifies the verified signature without persisting
    the signature or any secret key material.
    """

    authorization_ref: str
    issuer_id: str
    key_id: str
    target_id: str
    canonical_endpoint: str
    registration_version: str
    issued_at: str
    expires_at: str
    verified_at: str
    revocation_checked_at: str
    revocation_snapshot_expires_at: str
    signature_sha256: str
    signature_valid: bool
    revoked: bool

    def to_record(self) -> dict[str, str | bool]:
        return {
            "authorization_ref": self.authorization_ref,
            "issuer_id": self.issuer_id,
            "key_id": self.key_id,
            "target_id": self.target_id,
            "canonical_endpoint": self.canonical_endpoint,
            "registration_version": self.registration_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "verified_at": self.verified_at,
            "revocation_checked_at": self.revocation_checked_at,
            "revocation_snapshot_expires_at": self.revocation_snapshot_expires_at,
            "signature_sha256": self.signature_sha256,
            "signature_valid": self.signature_valid,
            "revoked": self.revoked,
        }


class AuthorizationVerifier(Protocol):
    """Trusted adapter for an authoritative approval and revocation source.

    Implementations must verify signatures with pinned keys, reject unknown or
    disabled issuers, validate the signed target/endpoint/version and time window,
    and perform a fresh revocation check. They must raise `UNAVAILABLE` when the
    approval or revocation source cannot be reached or its signed snapshot is stale.
    """

    @property
    def trusted_issuers(self) -> frozenset[str]:
        """Issuer IDs whose public keys were provisioned through trusted deployment config."""

    def verify(
        self,
        registration: ApprovedTargetRegistration,
        canonical_endpoint: str,
        *,
        now: datetime,
    ) -> VerifiedAuthorizationEvidence:
        """Verify the referenced approval for this exact target and return its proof metadata."""


_SIGNATURE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_TIMESTAMP_FIELDS = (
    "issued_at",
    "expires_at",
    "verified_at",
    "revocation_checked_at",
    "revocation_snapshot_expires_at",
)


def _aware_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def verify_authorization(
    verifier: AuthorizationVerifier | None,
    registration: ApprovedTargetRegistration,
    canonical_endpoint: str,
    *,
    now: datetime | None = None,
) -> VerifiedAuthorizationEvidence:
    """Verify an approval and independently validate the verifier's returned claims."""
    if verifier is None:
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)
    try:
        verify_method = getattr(verifier, "verify", None)
        trusted_issuers = getattr(verifier, "trusted_issuers", None)
    except Exception:
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE) from None
    if not callable(verify_method):
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)
    if not isinstance(trusted_issuers, (set, frozenset)) or not trusted_issuers:
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
    current_time = current_time.astimezone(timezone.utc)

    try:
        evidence = verify_method(registration, canonical_endpoint, now=current_time)
    except AuthorizationVerificationError:
        raise
    except Exception:
        # A verifier outage or implementation fault never becomes an allow decision.
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE) from None

    if not isinstance(evidence, VerifiedAuthorizationEvidence):
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
    if evidence.signature_valid is not True:
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_SIGNATURE)
    if not isinstance(evidence.issuer_id, str) or evidence.issuer_id not in trusted_issuers:
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNKNOWN_ISSUER)
    if evidence.revoked is True:
        raise AuthorizationVerificationError(AuthorizationFailureReason.REVOKED)
    if evidence.revoked is not False:
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)

    required_text = (
        evidence.authorization_ref,
        evidence.issuer_id,
        evidence.key_id,
        evidence.target_id,
        evidence.canonical_endpoint,
        evidence.registration_version,
        evidence.signature_sha256,
    )
    if any(not isinstance(value, str) or not value for value in required_text):
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
    if (
        evidence.authorization_ref != registration.authorization_ref
        or evidence.target_id != registration.target_id
        or evidence.canonical_endpoint != canonical_endpoint
        or evidence.registration_version != registration.registration_version
        or not evidence.key_id
        or _SIGNATURE_DIGEST.fullmatch(evidence.signature_sha256) is None
    ):
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)

    try:
        timestamps = {name: _aware_timestamp(getattr(evidence, name)) for name in _TIMESTAMP_FIELDS}
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE) from None

    if timestamps["issued_at"] > current_time or timestamps["verified_at"] > current_time:
        raise AuthorizationVerificationError(AuthorizationFailureReason.NOT_YET_VALID)
    if timestamps["expires_at"] <= current_time:
        raise AuthorizationVerificationError(AuthorizationFailureReason.EXPIRED)
    if timestamps["revocation_checked_at"] > current_time:
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
    if timestamps["revocation_snapshot_expires_at"] <= current_time:
        raise AuthorizationVerificationError(AuthorizationFailureReason.UNAVAILABLE)
    if timestamps["revocation_checked_at"] > timestamps["revocation_snapshot_expires_at"]:
        raise AuthorizationVerificationError(AuthorizationFailureReason.INVALID_EVIDENCE)
    return evidence
