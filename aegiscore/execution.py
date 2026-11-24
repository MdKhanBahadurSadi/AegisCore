"""MVP Assessment Execution Engine for AEGISCORE AI.

Provides controlled, passive local-lab connectivity observations via bounded
HTTP HEAD requests without response-body retrieval, redirect following, or
proxy forwarding.
"""

from __future__ import annotations

import ipaddress
import http.client
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from aegiscore.orchestration import ScopeViolationError, _validate_lab_target_url

ALLOWLISTED_SECURITY_HEADERS: frozenset[str] = frozenset({
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
})
MAX_HEADER_VALUE_LENGTH = 2048
# A single bounded HEAD request has a 5-second execution budget. The lease adds
# a 25-second safety margin for persistence and scheduling overhead.
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 5.0
EXECUTION_LEASE_SAFETY_MARGIN_SECONDS = 25.0
DEFAULT_EXECUTION_LEASE_SECONDS = (
    DEFAULT_EXECUTION_TIMEOUT_SECONDS + EXECUTION_LEASE_SAFETY_MARGIN_SECONDS
)


def _validate_execution_target_url(
    url: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Validate that target URL for execution is strictly a numeric loopback IP literal."""
    # Apply general lab scope rules (scheme http/https, no credentials, no fragments, etc.)
    _validate_lab_target_url(url)

    parsed = urllib.parse.urlsplit(url)
    hostname = parsed.hostname
    if not hostname or "%" in hostname or "#" in url or "@" in parsed.netloc:
        raise ScopeViolationError("Execution target URL must contain a valid hostname or IP address")

    # Hostnames (localhost, *.local, *.internal, etc.) are strictly prohibited for execution.
    # Only numeric IP literals corresponding to loopback (127.0.0.0/8 or ::1) are permitted.
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError as exc:
        raise ScopeViolationError(
            f"Execution target '{hostname}' is not a numeric IP literal; hostnames are prohibited for execution."
        ) from exc

    if not ip.is_loopback:
        raise ScopeViolationError(
            f"Execution target IP '{hostname}' is not an authorized numeric loopback address (127.0.0.0/8 or ::1)."
        )
    if ip.compressed != hostname:
        raise ScopeViolationError("Execution target IP address must use its canonical numeric representation")
    return ip


class ConnectedPeerMismatchError(OSError):
    """The connected socket peer did not match the numeric loopback target."""


def _verify_connected_peer(
    sock: socket.socket,
    expected_peer: ipaddress.IPv4Address | ipaddress.IPv6Address,
    expected_port: int,
) -> str:
    peer = sock.getpeername()
    if (
        not isinstance(peer, tuple)
        or len(peer) < 2
        or not isinstance(peer[0], str)
        or type(peer[1]) is not int
        or "%" in peer[0]
    ):
        raise ConnectedPeerMismatchError("connected peer address is unverifiable")
    try:
        actual_peer = ipaddress.ip_address(peer[0])
    except ValueError:
        raise ConnectedPeerMismatchError("connected peer address is unverifiable") from None
    if actual_peer != expected_peer or not actual_peer.is_loopback or peer[1] != expected_port:
        raise ConnectedPeerMismatchError("connected peer does not match authorized target endpoint")
    return actual_peer.compressed


class _PeerCheckedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, *, expected_peer: ipaddress.IPv4Address | ipaddress.IPv6Address,
                 peer_callback, **kwargs) -> None:
        self._expected_peer = expected_peer
        self._peer_callback = peer_callback
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        if self._tunnel_host:
            raise ConnectedPeerMismatchError("HTTP tunnels are not permitted")
        self.sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        try:
            connected_peer = _verify_connected_peer(self.sock, self._expected_peer, self.port)
        except Exception:
            self.close()
            raise
        self._peer_callback(connected_peer)


class _PeerCheckedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, expected_peer: ipaddress.IPv4Address | ipaddress.IPv6Address,
                 peer_callback, **kwargs) -> None:
        self._expected_peer = expected_peer
        self._peer_callback = peer_callback
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        if self._tunnel_host:
            raise ConnectedPeerMismatchError("HTTPS tunnels are not permitted")
        raw_socket = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        try:
            connected_peer = _verify_connected_peer(raw_socket, self._expected_peer, self.port)
        except Exception:
            raw_socket.close()
            raise
        self._peer_callback(connected_peer)
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except Exception:
            raw_socket.close()
            raise


class _PeerCheckedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, expected_peer: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        super().__init__()
        self.connected_peer: str | None = None
        self._expected_peer = expected_peer

    def http_open(self, req):
        def connection_factory(host: str, **kwargs):
            return _PeerCheckedHTTPConnection(
                host,
                expected_peer=self._expected_peer,
                peer_callback=self._set_peer,
                **kwargs,
            )

        return self.do_open(connection_factory, req)

    def _set_peer(self, peer: str) -> None:
        self.connected_peer = peer


class _PeerCheckedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, expected_peer: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        super().__init__(context=ssl.create_default_context())
        self.connected_peer: str | None = None
        self._expected_peer = expected_peer

    def https_open(self, req):
        def connection_factory(host: str, **kwargs):
            return _PeerCheckedHTTPSConnection(
                host,
                expected_peer=self._expected_peer,
                peer_callback=self._set_peer,
                **kwargs,
            )

        return self.do_open(connection_factory, req, context=self._context)

    def _set_peer(self, peer: str) -> None:
        self.connected_peer = peer


def _extract_allowlisted_headers(headers: Any) -> tuple[dict[str, str], dict[str, str]]:
    """Extract and case-normalize strictly allowlisted security headers with size bounds checking."""
    normalized: dict[str, str] = {}
    flags: dict[str, str] = {}

    if not headers:
        return normalized, flags

    items = headers.items() if hasattr(headers, "items") else []
    for key, val in items:
        norm_key = str(key).strip().lower()
        if norm_key in ALLOWLISTED_SECURITY_HEADERS:
            val_str = str(val).strip()
            if len(val_str) > MAX_HEADER_VALUE_LENGTH:
                flags[norm_key] = "oversized"
                val_str = val_str[:MAX_HEADER_VALUE_LENGTH]
            normalized[norm_key] = val_str

    return normalized, flags


class AssessmentExecutionEngine:
    """Bounded, fail-closed execution engine for target connectivity observations."""

    def __init__(self, timeout_seconds: float = DEFAULT_EXECUTION_TIMEOUT_SECONDS) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a positive numeric float")
        if not (0.0 < float(timeout_seconds) <= 30.0):
            raise ValueError("timeout_seconds must be bounded between 0.0 and 30.0 seconds")
        self._timeout_seconds = float(timeout_seconds)

    def execute_connectivity_observation(self, target_url: str) -> dict[str, Any]:
        """Perform exactly one passive HTTP HEAD observation against an authorized numeric loopback target."""
        expected_peer = _validate_execution_target_url(target_url)

        start_time = time.monotonic()
        executed_at = datetime.now(timezone.utc).isoformat()

        req = urllib.request.Request(
            target_url,
            method="HEAD",
            headers={"User-Agent": "AEGISCORE-AI-Lab-Observer/1.0"},
        )

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                # Do not follow redirects
                return None

        # Explicitly disable proxies (ProxyHandler({})) to ignore HTTP_PROXY, HTTPS_PROXY, etc.
        http_handler = _PeerCheckedHTTPHandler(expected_peer)
        https_handler = _PeerCheckedHTTPSHandler(expected_peer)
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirectHandler,
            http_handler,
            https_handler,
        )

        try:
            with opener.open(req, timeout=self._timeout_seconds) as response:
                connected_peer = http_handler.connected_peer or https_handler.connected_peer
                if connected_peer != expected_peer.compressed:
                    raise ConnectedPeerMismatchError("connected peer verification was not completed")
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                status_code = response.getcode()
                captured_headers, header_flags = _extract_allowlisted_headers(response.headers)
                return {
                    "reachable": True,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "executed_at": executed_at,
                    "method": "HEAD",
                    "redirect_detected": False,
                    "captured_headers": captured_headers,
                    "header_flags": header_flags,
                    "connected_peer": connected_peer,
                    "outcome": f"Target responded with HTTP {status_code}",
                }
        except urllib.error.HTTPError as exc:
            connected_peer = http_handler.connected_peer or https_handler.connected_peer
            if connected_peer != expected_peer.compressed:
                return {
                    "reachable": False,
                    "http_status": None,
                    "duration_ms": round((time.monotonic() - start_time) * 1000, 2),
                    "executed_at": executed_at,
                    "method": "HEAD",
                    "redirect_detected": False,
                    "captured_headers": {},
                    "header_flags": {},
                    "connected_peer": None,
                    "outcome": "Execution failed due to an unverifiable connected peer",
                }
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            status_code = exc.code
            captured_headers, header_flags = _extract_allowlisted_headers(exc.headers)
            is_redirect = 300 <= status_code < 400
            if is_redirect:
                return {
                    "reachable": True,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "executed_at": executed_at,
                    "method": "HEAD",
                    "redirect_detected": True,
                    "captured_headers": captured_headers,
                    "header_flags": header_flags,
                    "connected_peer": connected_peer,
                    "outcome": f"Target returned HTTP {status_code} redirect (redirect not followed)",
                }
            elif status_code == 405:
                return {
                    "reachable": True,
                    "http_status": 405,
                    "duration_ms": duration_ms,
                    "executed_at": executed_at,
                    "method": "HEAD",
                    "redirect_detected": False,
                    "captured_headers": captured_headers,
                    "header_flags": header_flags,
                    "connected_peer": connected_peer,
                    "outcome": "Target returned HTTP 405 Method Not Allowed for HEAD request",
                }
            else:
                return {
                    "reachable": True,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "executed_at": executed_at,
                    "method": "HEAD",
                    "redirect_detected": False,
                    "captured_headers": captured_headers,
                    "header_flags": header_flags,
                    "connected_peer": connected_peer,
                    "outcome": f"Target returned HTTP {status_code}",
                }
        except urllib.error.URLError as exc:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            reason_msg = str(exc.reason).lower()
            if "refused" in reason_msg:
                sanitized_reason = "Connection refused"
            elif "timeout" in reason_msg or "timed out" in reason_msg:
                sanitized_reason = "Connection timed out"
            elif "unreachable" in reason_msg or "network" in reason_msg:
                sanitized_reason = "Host unreachable"
            else:
                sanitized_reason = "Connection failed"

            return {
                "reachable": False,
                "http_status": None,
                "duration_ms": duration_ms,
                "executed_at": executed_at,
                "method": "HEAD",
                "redirect_detected": False,
                "captured_headers": {},
                "header_flags": {},
                "connected_peer": http_handler.connected_peer or https_handler.connected_peer,
                "outcome": f"Target unreachable: {sanitized_reason}",
            }
        except TimeoutError:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            return {
                "reachable": False,
                "http_status": None,
                "duration_ms": duration_ms,
                "executed_at": executed_at,
                "method": "HEAD",
                "redirect_detected": False,
                "captured_headers": {},
                "header_flags": {},
                "connected_peer": http_handler.connected_peer or https_handler.connected_peer,
                "outcome": "Target connection timed out",
            }
        except Exception:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            return {
                "reachable": False,
                "http_status": None,
                "duration_ms": duration_ms,
                "executed_at": executed_at,
                "method": "HEAD",
                "redirect_detected": False,
                "captured_headers": {},
                "header_flags": {},
                "connected_peer": http_handler.connected_peer or https_handler.connected_peer,
                "outcome": "Execution failed due to an internal transport error",
            }
