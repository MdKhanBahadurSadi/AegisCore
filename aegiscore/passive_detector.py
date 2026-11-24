"""Deterministic rule-based passive security header detector for AEGISCORE AI."""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

_EVIDENCE_ID_PATTERN = re.compile(r"^evi_[0-9a-f]{32}$")
_ASSESSMENT_ID_PATTERN = re.compile(r"^asm_[0-9a-f]{32}$")


class PassiveHeaderDetector:
    """Consumes normalized evidence records and emits deterministic configuration observations."""

    @staticmethod
    def analyze(assessment_id: str, target_url: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        """Run rule-based detection on normalized evidence.

        Returns a list of structured finding dictionaries.
        """
        findings: list[dict[str, Any]] = []

        # Validate mandatory assessment_id format
        if not isinstance(assessment_id, str) or _ASSESSMENT_ID_PATTERN.match(assessment_id) is None:
            return findings

        # Validate mandatory evidence fields and evidence ID format
        evidence_id = evidence.get("evidence_id")
        if not isinstance(evidence_id, str) or _EVIDENCE_ID_PATTERN.match(evidence_id) is None:
            return findings

        # Verify evidence belongs strictly to the requested assessment_id
        ev_asm_id = evidence.get("assessment_id")
        if not isinstance(ev_asm_id, str) or ev_asm_id != assessment_id:
            return findings

        # Only analyze if evidence collection succeeded and returned a 2xx response
        collection_status = evidence.get("collection_status")
        http_status = evidence.get("http_status")
        if collection_status != "observed" or http_status is None or not (200 <= http_status < 300):
            return findings

        headers = evidence.get("normalized_headers", {})
        header_flags = evidence.get("header_flags", {})
        evidence_ids = (evidence_id,)

        parsed_url = urllib.parse.urlsplit(target_url)
        is_https = parsed_url.scheme.lower() == "https"

        now_iso = datetime.now(timezone.utc).isoformat()

        def _make_finding_id(rule_id: str) -> str:
            raw = f"{assessment_id}\0{rule_id}".encode("utf-8")
            return f"fnd_{hashlib.sha256(raw).hexdigest()[:32]}"

        # Rule 1: Content Security Policy (WEB-HEADER-001)
        if "content-security-policy" not in headers:
            findings.append({
                "finding_id": _make_finding_id("WEB-HEADER-001"),
                "assessment_id": assessment_id,
                "rule_id": "WEB-HEADER-001",
                "title": "Content Security Policy header not observed",
                "description": (
                    "The HTTP Content-Security-Policy header was not observed in the 2xx response. "
                    "Configuring CSP helps restrict resource loading and mitigate cross-site scripting."
                ),
                "classification": "configuration_observation",
                "severity": "info",
                "confidence": "low",
                "status": "detected",
                "evidence_ids": evidence_ids,
                "remediation": "Configure a strict Content-Security-Policy header restricting script, style, and object sources.",
                "created_at": now_iso,
            })

        # Rule 2: MIME Sniffing Protection (WEB-HEADER-002)
        if "x-content-type-options" not in headers:
            findings.append({
                "finding_id": _make_finding_id("WEB-HEADER-002"),
                "assessment_id": assessment_id,
                "rule_id": "WEB-HEADER-002",
                "title": "MIME sniffing protection header not observed",
                "description": (
                    "The X-Content-Type-Options header was not observed in the 2xx response. "
                    "Setting 'X-Content-Type-Options: nosniff' prevents browsers from MIME-sniffing response content."
                ),
                "classification": "configuration_observation",
                "severity": "low",
                "confidence": "medium",
                "status": "detected",
                "evidence_ids": evidence_ids,
                "remediation": "Add 'X-Content-Type-Options: nosniff' to HTTP responses.",
                "created_at": now_iso,
            })

        # Rule 3: Framing Protection (WEB-HEADER-003)
        csp_val = headers.get("content-security-policy", "").lower()
        has_frame_ancestors = "frame-ancestors" in csp_val
        has_x_frame_options = "x-frame-options" in headers
        csp_is_oversized = header_flags.get("content-security-policy") == "oversized"
        xfo_is_oversized = header_flags.get("x-frame-options") == "oversized"

        # Do not generate framing finding if X-Frame-Options is present, OR frame-ancestors is present,
        # OR CSP/XFO headers are oversized (since framing policy cannot be fully analyzed).
        if not has_x_frame_options and not has_frame_ancestors and not csp_is_oversized and not xfo_is_oversized:
            findings.append({
                "finding_id": _make_finding_id("WEB-HEADER-003"),
                "assessment_id": assessment_id,
                "rule_id": "WEB-HEADER-003",
                "title": "Framing protection not observed",
                "description": (
                    "Neither X-Frame-Options nor a CSP 'frame-ancestors' directive was observed in the 2xx response. "
                    "Configuring framing protection helps prevent clickjacking."
                ),
                "classification": "configuration_observation",
                "severity": "low",
                "confidence": "medium",
                "status": "detected",
                "evidence_ids": evidence_ids,
                "remediation": "Configure 'X-Frame-Options: DENY' (or 'SAMEORIGIN') or set CSP 'frame-ancestors' directive.",
                "created_at": now_iso,
            })

        # Rule 4: Referrer Policy (WEB-HEADER-004)
        if "referrer-policy" not in headers:
            findings.append({
                "finding_id": _make_finding_id("WEB-HEADER-004"),
                "assessment_id": assessment_id,
                "rule_id": "WEB-HEADER-004",
                "title": "Explicit Referrer Policy not observed",
                "description": (
                    "An explicit Referrer-Policy header was not observed in the 2xx response. "
                    "Setting a Referrer-Policy controls how much referrer information is included with requests."
                ),
                "classification": "configuration_observation",
                "severity": "info",
                "confidence": "low",
                "status": "detected",
                "evidence_ids": evidence_ids,
                "remediation": "Configure 'Referrer-Policy: strict-origin-when-cross-origin' or another restrictive policy.",
                "created_at": now_iso,
            })

        # Rule 5: HTTPS Strict Transport Security (WEB-HEADER-005) - HTTPS targets only
        if is_https and "strict-transport-security" not in headers:
            findings.append({
                "finding_id": _make_finding_id("WEB-HEADER-005"),
                "assessment_id": assessment_id,
                "rule_id": "WEB-HEADER-005",
                "title": "HTTP Strict Transport Security header not observed",
                "description": (
                    "The Strict-Transport-Security header was not observed on this HTTPS endpoint. "
                    "HSTS enforces encrypted HTTPS connections and prevents SSL stripping."
                ),
                "classification": "configuration_observation",
                "severity": "low",
                "confidence": "medium",
                "status": "detected",
                "evidence_ids": evidence_ids,
                "remediation": "Configure 'Strict-Transport-Security: max-age=31536000; includeSubDomains' on all HTTPS endpoints.",
                "created_at": now_iso,
            })

        return findings
