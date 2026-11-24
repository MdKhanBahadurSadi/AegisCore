"""Deterministic in-namespace checks using one controlled HEAD-only fixture."""

from __future__ import annotations

import argparse
import errno
import http.server
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from policy import PolicyError, verify_ruleset_text


_DOC_IPV4 = ("198.51.100.1", 443)
_DOC_IPV6 = ("2001:db8::1", 443, 0, 0)
_DNS_TEST_IPV4 = ("192.0.2.53", 53)
_DNS_TEST_IPV6 = ("2001:db8::53", 53, 0, 0)


class _HeadOnlyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib HTTP handler API
        if self.path != "/isolation-check":
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


class _IPv6HeadServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


def _run(*argv: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, check=check)


def _assert_only_loopback_and_no_routes() -> None:
    links = json.loads(_run("ip", "-j", "link", "show").stdout)
    names = {item.get("ifname") for item in links}
    if names != {"lo"}:
        raise PolicyError(f"network namespace has unexpected interfaces: {sorted(names)}")
    if "UP" not in links[0].get("flags", []):
        raise PolicyError("network namespace loopback interface is down")
    addresses = json.loads(_run("ip", "-j", "address", "show", "dev", "lo").stdout)
    address_pairs = {
        (item.get("family"), item.get("local"), item.get("prefixlen"))
        for item in addresses[0].get("addr_info", [])
    }
    if address_pairs != {("inet", "127.0.0.1", 8), ("inet6", "::1", 128)}:
        raise PolicyError("loopback interface has missing or unexpected IPv4/IPv6 addresses")
    print("NAMESPACE INTERFACES: " + json.dumps(links, sort_keys=True))
    print("NAMESPACE LOOPBACK ADDRESSES: " + json.dumps(addresses, sort_keys=True))
    for family, argv in (
        (4, ("ip", "-4", "-j", "route", "show", "table", "main")),
        (6, ("ip", "-6", "-j", "route", "show", "table", "main")),
    ):
        routes = json.loads(_run(*argv).stdout)
        print(f"NAMESPACE IPv{family} MAIN ROUTES: " + json.dumps(routes, sort_keys=True))
        for route in routes:
            destination = route.get("dst")
            device = route.get("dev")
            if destination in {None, "default"} or device != "lo":
                raise PolicyError("network namespace contains a default or non-loopback route")
            try:
                network = ipaddress.ip_network(destination, strict=False)
            except ValueError:
                raise PolicyError("network namespace route has an invalid destination") from None
            if network.version != family or not network.subnet_of(ipaddress.ip_network("127.0.0.0/8" if family == 4 else "::1/128")):
                raise PolicyError("network namespace contains a route outside loopback")
    for address in ("198.51.100.1", "2001:db8::1", "192.0.2.53", "2001:db8::53"):
        argv = ("ip", "-6", "route", "get", address) if ":" in address else ("ip", "-4", "route", "get", address)
        result = _run(*argv, check=False)
        if result.returncode == 0:
            raise PolicyError(f"non-loopback route exists for reserved test address {address}")
        print(f"NO ROUTE: {address} (route lookup exit {result.returncode})")


def _active_output_drop_count() -> int:
    output = _run("nft", "-a", "list", "chain", "inet", "aegiscore", "output").stdout
    counts = re.findall(r"counter packets ([0-9]+) bytes [0-9]+ drop\b", output)
    if len(counts) != 1:
        raise PolicyError("the output chain must have exactly one counted final drop rule")
    return int(counts[0])


def _active_input_drop_count() -> int:
    output = _run("nft", "-a", "list", "chain", "inet", "aegiscore", "input").stdout
    counts = re.findall(r"counter packets ([0-9]+) bytes [0-9]+ drop\b", output)
    if len(counts) != 1:
        raise PolicyError("the input chain must have exactly one counted final drop rule")
    return int(counts[0])


def _active_output_allow_count(port: int) -> int:
    output = _run("nft", "-a", "list", "chain", "inet", "aegiscore", "output").stdout
    counts: list[int] = []
    for line in output.splitlines():
        match = re.search(r"\btcp dport (\{[^}]+\}|[0-9]+)", line)
        if match is None or not re.search(r"\baccept\b", line):
            continue
        expression = match.group(1)
        listed_ports = {int(item) for item in re.findall(r"[0-9]+", expression)}
        if port not in listed_ports:
            continue
        counter = re.search(r"counter packets ([0-9]+) bytes [0-9]+", line)
        if counter is None:
            raise PolicyError("the output allow rule has no packet counter")
        counts.append(int(counter.group(1)))
    if len(counts) != 1:
        raise PolicyError(f"the output chain must have exactly one counted allow rule for port {port}")
    return counts[0]


def _assert_firewall(
    *, api_port: int, target_ports: tuple[int, ...], local_client_ports: tuple[int, ...],
    temporary_egress_only_ports: tuple[int, ...], allow_api_client: bool
) -> None:
    snapshot = _run("nft", "-a", "list", "ruleset").stdout
    verify_ruleset_text(
        snapshot,
        api_port=api_port,
        target_ports=target_ports,
        local_client_ports=local_client_ports,
        temporary_egress_only_ports=temporary_egress_only_ports,
        allow_api_client=allow_api_client,
    )
    print("ACTIVE SELF-TEST NFTABLES RULESET:")
    print(snapshot, end="")


def _head(host: str, port: int) -> int:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    endpoint = (host, port, 0, 0) if family == socket.AF_INET6 else (host, port)
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(1.0)
        client.connect(endpoint)
        client.sendall(
            f"HEAD /isolation-check HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode("ascii")
        )
        response = bytearray()
        while b"\r\n\r\n" not in response and len(response) < 4096:
            chunk = client.recv(512)
            if not chunk:
                break
            response.extend(chunk)
    status_line = bytes(response).split(b"\r\n", 1)[0].decode("ascii", errors="strict")
    match = re.match(r"^HTTP/1\.[01] ([0-9]{3})\b", status_line)
    if match is None:
        raise PolicyError("loopback fixture returned an invalid HTTP response")
    return int(match.group(1))


def _assert_denied_loopback(host: str, port: int) -> None:
    before = _active_output_drop_count()
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    endpoint = (host, port, 0, 0) if family == socket.AF_INET6 else (host, port)
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(0.4)
        result = client.connect_ex(endpoint)
    after = _active_output_drop_count()
    if result == 0 or after <= before:
        raise PolicyError(f"unauthorized loopback connection to {host}:{port} was not firewall-dropped")
    print(f"OUTPUT COUNTER: denied {host}:{port}; final-drop packets {before}->{after}; connect_ex={result}")


def _assert_inbound_dropped(host: str, port: int) -> None:
    before_input_drop = _active_input_drop_count()
    before_output_allow = _active_output_allow_count(port)
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    endpoint = (host, port, 0, 0) if family == socket.AF_INET6 else (host, port)
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(0.4)
        result = client.connect_ex(endpoint)
    after_input_drop = _active_input_drop_count()
    after_output_allow = _active_output_allow_count(port)
    if result == 0:
        raise PolicyError(f"unauthorized inbound loopback connection to {host}:{port} succeeded")
    if after_output_allow <= before_output_allow:
        raise PolicyError("inbound policy check did not pass through the permitted output rule")
    if after_input_drop <= before_input_drop:
        raise PolicyError(f"unauthorized inbound loopback connection to {host}:{port} did not increment input-drop counter")
    print(
        f"INPUT COUNTERS: {host}:{port}; output-allow packets {before_output_allow}->{after_output_allow}; "
        f"input-final-drop packets {before_input_drop}->{after_input_drop}; connect_ex={result}"
    )


def _assert_no_route_connect(family: int, endpoint: tuple[object, ...], label: str) -> None:
    # The route-table preflight runs first. These addresses are IANA documentation
    # prefixes; with no route/device, connect must fail before a packet can leave.
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(0.5)
        result = client.connect_ex(endpoint)
    if result == 0:
        raise PolicyError(f"reserved non-routable {label} connection unexpectedly succeeded")
    if result not in {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL, errno.ENETDOWN}:
        raise PolicyError(f"reserved {label} connection did not fail for lack of a route (errno {result})")
    print(f"NO EXTERNAL IPv{4 if family == socket.AF_INET else 6} TCP ROUTE: errno={result}")


def _assert_dns_unroutable(family: int, endpoint: tuple[object, ...], label: str) -> None:
    with socket.socket(family, socket.SOCK_DGRAM) as client:
        try:
            client.sendto(b"", endpoint)
        except OSError as exc:
            if exc.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL, errno.ENETDOWN}:
                print(f"NO EXTERNAL IPv{4 if family == socket.AF_INET else 6} UDP/DNS ROUTE: errno={exc.errno}")
                return
            raise PolicyError(f"reserved {label} DNS test failed unexpectedly (errno {exc.errno})") from None
    raise PolicyError(f"reserved {label} DNS endpoint had a route; no query was sent by this probe")


def _serve(port: int, input_deny_port: int, ready_file: Path) -> None:
    servers: list[http.server.ThreadingHTTPServer] = []
    try:
        for service_port in (port, input_deny_port):
            for server_type, host in ((http.server.ThreadingHTTPServer, "127.0.0.1"), (_IPv6HeadServer, "::1")):
                server = server_type((host, service_port), _HeadOnlyHandler)
                server.daemon_threads = True
                servers.append(server)
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        ready_file.write_text("ready\n", encoding="ascii")
        while True:
            time.sleep(3600)
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


def _check(args: argparse.Namespace) -> None:
    api_port = int(args.api_port)
    input_deny_port = int(args.input_deny_port)
    target_ports = tuple(int(port) for port in args.target_ports.split(",") if port)
    local_client_ports = tuple(int(port) for port in args.local_client_ports.split(",") if port)
    egress_only_test_ports = tuple(int(port) for port in args.egress_only_test_ports.split(",") if port)
    _assert_only_loopback_and_no_routes()
    _assert_firewall(
        api_port=api_port,
        target_ports=target_ports,
        local_client_ports=local_client_ports,
        temporary_egress_only_ports=egress_only_test_ports,
        allow_api_client=args.allow_api_client,
    )
    if _head("127.0.0.1", args.probe_port) != 204:
        raise PolicyError("authorized IPv4 loopback HEAD fixture did not return 204")
    if _head("::1", args.probe_port) != 204:
        raise PolicyError("authorized IPv6 loopback HEAD fixture did not return 204")

    _assert_inbound_dropped("127.0.0.1", input_deny_port)
    _assert_inbound_dropped("::1", input_deny_port)

    denied_port = next(port for port in range(49152, 65536) if port not in {api_port, args.probe_port, input_deny_port, *target_ports, *local_client_ports})
    _assert_denied_loopback("127.0.0.1", denied_port)
    _assert_denied_loopback("::1", denied_port)
    _assert_no_route_connect(socket.AF_INET, _DOC_IPV4, "IPv4")
    _assert_no_route_connect(socket.AF_INET6, _DOC_IPV6, "IPv6")
    _assert_dns_unroutable(socket.AF_INET, _DNS_TEST_IPV4, "IPv4")
    _assert_dns_unroutable(socket.AF_INET6, _DNS_TEST_IPV6, "IPv6")
    print("PASS: only lo is present; IPv4/IPv6 main routing tables are empty")
    print("PASS: authorized IPv4 and IPv6 loopback HEAD service access")
    print("PASS: unauthorized IPv4 and IPv6 loopback input packets incremented input-drop counters after passing output")
    print("PASS: unauthorized IPv4 and IPv6 loopback ports incremented output-drop counters")
    print("PASS: reserved IPv4/IPv6 routes and DNS endpoints are unreachable without sending external traffic")
    print("PASS: nftables ruleset exactly matches the temporary verification allowlist")


def _tcp_check(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    endpoint = (host, port, 0, 0) if family == socket.AF_INET6 else (host, port)
    with socket.socket(family, socket.SOCK_STREAM) as client:
        client.settimeout(1.0)
        client.connect(endpoint)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, required=True)
    serve.add_argument("--input-deny-port", type=int, required=True)
    serve.add_argument("--ready-file", type=Path, required=True)
    check = commands.add_parser("check")
    check.add_argument("--api-port", type=int, required=True)
    check.add_argument("--probe-port", type=int, required=True)
    check.add_argument("--input-deny-port", type=int, required=True)
    check.add_argument("--target-ports", default="")
    check.add_argument("--local-client-ports", default="")
    check.add_argument("--egress-only-test-ports", default="")
    check.add_argument("--allow-api-client", action="store_true")
    tcp_check = commands.add_parser("tcp-check")
    tcp_check.add_argument("--host", required=True)
    tcp_check.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if args.command == "serve":
        _serve(args.port, args.input_deny_port, args.ready_file)
    elif args.command == "check":
        _check(args)
    else:
        _tcp_check(args.host, args.port)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except (PolicyError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"isolation verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
