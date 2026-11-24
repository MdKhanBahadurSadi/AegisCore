"""Generate and verify AEGISCORE's narrow nftables network-namespace policy."""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable


class PolicyError(ValueError):
    """A deployment port or observed ruleset violates the strict policy."""


_PORT_RE = re.compile(r"^[0-9]{1,5}$")
_COUNTER_RE = re.compile(r"\bcounter packets [0-9]+ bytes [0-9]+\b")
_HANDLE_RE = re.compile(r"\s+# handle [0-9]+\s*$")


def parse_port(value: str, *, name: str) -> int:
    if not isinstance(value, str) or _PORT_RE.fullmatch(value) is None:
        raise PolicyError(f"{name} must be a decimal TCP port from 1 through 65535")
    port = int(value)
    if not 1 <= port <= 65535:
        raise PolicyError(f"{name} must be a decimal TCP port from 1 through 65535")
    return port


def parse_ports(value: str | None, *, name: str, allow_empty: bool = True) -> tuple[int, ...]:
    if value is None or not value.strip():
        if allow_empty:
            return ()
        raise PolicyError(f"{name} must list at least one TCP port")
    items = [part.strip() for part in value.split(",")]
    if any(not item for item in items):
        raise PolicyError(f"{name} contains an empty TCP port")
    ports = tuple(sorted(parse_port(item, name=name) for item in items))
    if len(set(ports)) != len(ports):
        raise PolicyError(f"{name} contains duplicate TCP ports")
    return ports


def _port_set(ports: Iterable[int]) -> str:
    ordered = tuple(sorted(set(ports)))
    if not ordered:
        raise PolicyError("an nftables port set cannot be empty")
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ordered):
        raise PolicyError("nftables port set contains an invalid port")
    if len(ordered) == 1:
        return str(ordered[0])
    return "{ " + ", ".join(str(port) for port in ordered) + " }"


def _verdict_rules(*, direction: str, ports: tuple[int, ...]) -> list[str]:
    interface = "iifname" if direction == "input" else "oifname"
    rules = [f'    {interface} "lo" ct state established,related counter accept']
    if ports:
        port_set = _port_set(ports)
        rules.extend(
            (
                f'    {interface} "lo" ip daddr 127.0.0.0/8 tcp dport {port_set} '
                "ct state new counter accept",
                f'    {interface} "lo" ip6 daddr ::1 tcp dport {port_set} '
                "ct state new counter accept",
            )
        )
    rules.append("    counter drop")
    return rules


def build_ruleset(
    *,
    api_port: int,
    target_ports: Iterable[int],
    local_client_ports: Iterable[int] = (),
    temporary_test_ports: Iterable[int] = (),
    temporary_egress_only_ports: Iterable[int] = (),
    allow_api_client_test: bool = False,
) -> str:
    """Build separate default-drop ingress and egress chains.

    API ingress is always permitted on the loopback listener. Outbound execution
    is limited to explicitly registered target ports. Optional local-client ports
    are a separately configured need. Temporary self-test permissions are only
    for the pre-start network verification phase and must be removed afterwards.
    `temporary_egress_only_ports` proves the input drop hook independently after
    a test packet passes the output allow rule; it is removed before service use.
    """
    if type(api_port) is not int or not 1 <= api_port <= 65535:
        raise PolicyError("api_port must be a TCP port from 1 through 65535")
    targets = tuple(sorted(set(target_ports)))
    clients = tuple(sorted(set(local_client_ports)))
    temporary = tuple(sorted(set(temporary_test_ports)))
    egress_only_test = tuple(sorted(set(temporary_egress_only_ports)))
    all_ports = (*targets, *clients, *temporary, *egress_only_test)
    if any(type(port) is not int or not 1 <= port <= 65535 for port in all_ports):
        raise PolicyError("port list contains an invalid TCP port")
    if api_port in targets:
        raise PolicyError("API listener port cannot also be an execution target port")
    if (
        set(targets) & set(clients)
        or set(temporary) & (set(targets) | set(clients) | set(egress_only_test) | {api_port})
        or set(egress_only_test) & (set(targets) | set(clients) | {api_port})
    ):
        raise PolicyError("target, client, and temporary test ports must be distinct")

    inbound_ports = tuple(sorted({api_port, *targets, *temporary}))
    outbound_ports = tuple(sorted({*targets, *clients, *temporary, *egress_only_test}))
    if allow_api_client_test:
        outbound_ports = tuple(sorted({*outbound_ports, api_port}))

    input_rules = "\n".join(_verdict_rules(direction="input", ports=inbound_ports))
    output_rules = "\n".join(_verdict_rules(direction="output", ports=outbound_ports))
    return (
        "table inet aegiscore {\n"
        "  chain input {\n"
        "    type filter hook input priority filter; policy drop;\n"
        f"{input_rules}\n"
        "  }\n"
        "  chain output {\n"
        "    type filter hook output priority filter; policy drop;\n"
        f"{output_rules}\n"
        "  }\n"
        "}\n"
    )


def _chain_body(snapshot: str, chain: str) -> list[str]:
    match = re.search(
        rf"^[ \t]*chain {re.escape(chain)} \{{(?:[ \t]+# handle [0-9]+)?[ \t]*$",
        snapshot,
        flags=re.MULTILINE,
    )
    if match is None:
        raise PolicyError(f"active nftables chain {chain} is missing")
    lines: list[str] = []
    for line in snapshot[match.end() :].splitlines():
        if line.strip() == "}":
            return lines
        normalized = _HANDLE_RE.sub("", line.strip())
        normalized = _COUNTER_RE.sub("counter", normalized)
        if normalized:
            lines.append(normalized)
    raise PolicyError(f"active nftables chain {chain} is incomplete")


def verify_ruleset_text(
    snapshot: str,
    *,
    api_port: int,
    target_ports: Iterable[int],
    local_client_ports: Iterable[int] = (),
    temporary_egress_only_ports: Iterable[int] = (),
    allow_api_client: bool = False,
) -> None:
    """Fail unless the active nft output is exactly the requested policy."""
    table_lines = [
        _HANDLE_RE.sub("", line.strip())
        for line in snapshot.splitlines()
        if re.match(r"^\s*table\s+\S+\s+\S+\s*\{", line)
    ]
    if table_lines != ["table inet aegiscore {"]:
        raise PolicyError("namespace nftables ruleset contains an unexpected table")
    chain_names = re.findall(r"^[ \t]*chain ([A-Za-z0-9_-]+) \{", snapshot, flags=re.MULTILINE)
    if chain_names != ["input", "output"]:
        raise PolicyError("namespace nftables table contains an unexpected chain")

    expected = build_ruleset(
        api_port=api_port,
        target_ports=target_ports,
        local_client_ports=local_client_ports,
        temporary_egress_only_ports=temporary_egress_only_ports,
        allow_api_client_test=allow_api_client,
    )
    for chain in ("input", "output"):
        body = _chain_body(snapshot, chain)
        expected_body = _chain_body(expected, chain)
        if body != expected_body:
            raise PolicyError(f"active nftables {chain} chain differs from the required policy")

    # Reject sets, maps, flowtables, and other declarations inside the table too.
    # The generated deployment table consists only of the two checked chains.
    table_start = re.search(r"^\s*table\s+inet\s+aegiscore\s*\{", snapshot, flags=re.MULTILINE)
    if table_start is None:
        raise PolicyError("active nftables table is missing")
    table_lines = snapshot[table_start.end() :].splitlines()
    declarations = [
        _HANDLE_RE.sub("", line.strip())
        for line in table_lines
        if re.match(r"^\s*(?:set|map|flowtable|chain)\s+", line)
    ]
    if declarations != ["chain input {", "chain output {"]:
        raise PolicyError("active nftables table contains unexpected declarations")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", required=True)
    parser.add_argument("--target-ports", default="")
    parser.add_argument("--local-client-ports", default="")
    args = parser.parse_args()
    api_port = parse_port(args.api_port, name="api_port")
    targets = parse_ports(args.target_ports, name="target_ports")
    clients = parse_ports(args.local_client_ports, name="local_client_ports")
    print(build_ruleset(api_port=api_port, target_ports=targets, local_client_ports=clients), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
