"""Cross-platform tests for the generated Linux isolation policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_POLICY_PATH = Path(__file__).parents[1] / "deploy" / "linux-egress" / "policy.py"
_SPEC = importlib.util.spec_from_file_location("aegiscore_linux_egress_policy", _POLICY_PATH)
assert _SPEC is not None and _SPEC.loader is not None
policy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(policy)


def _nft_listing(rules: str) -> str:
    return (
        rules.replace(" counter accept", " counter packets 12 bytes 440 accept")
        .replace(" counter drop", " counter packets 0 bytes 0 drop")
        .replace("priority filter;", "priority filter;", 1)
    )


def test_policy_separates_api_ingress_from_execution_egress() -> None:
    rules = policy.build_ruleset(api_port=8000, target_ports=(3000, 18080))
    input_chain = policy._chain_body(rules, "input")
    output_chain = policy._chain_body(rules, "output")

    assert any("tcp dport { 3000, 8000, 18080 }" in line for line in input_chain)
    assert any("tcp dport { 3000, 18080 }" in line for line in output_chain)
    assert not any("tcp dport { 3000, 8000, 18080 }" in line for line in output_chain)
    assert "type filter hook input priority filter; policy drop;" in input_chain
    assert "type filter hook output priority filter; policy drop;" in output_chain
    assert any("ip6 daddr ::1" in line for line in output_chain)
    assert all("udp" not in line and "dport 53" not in line for line in output_chain)


def test_default_empty_registry_allows_no_new_outbound_connections() -> None:
    rules = policy.build_ruleset(api_port=8000, target_ports=())
    output_chain = policy._chain_body(rules, "output")
    assert output_chain == [
        "type filter hook output priority filter; policy drop;",
        'oifname "lo" ct state established,related counter accept',
        "counter drop",
    ]


def test_temporary_api_client_rule_is_not_in_production_rules() -> None:
    rules = policy.build_ruleset(
        api_port=8000,
        target_ports=(3000,),
        temporary_test_ports=(49152,),
        allow_api_client_test=True,
    )
    output_chain = policy._chain_body(rules, "output")
    assert any("dport { 3000, 8000, 49152 }" in line for line in output_chain)

    production = policy.build_ruleset(api_port=8000, target_ports=(3000,))
    assert "dport { 3000, 8000, 49152 }" not in production


def test_temporary_egress_permission_can_isolate_input_drop_verification() -> None:
    rules = policy.build_ruleset(
        api_port=8000,
        target_ports=(),
        temporary_test_ports=(49152,),
        temporary_egress_only_ports=(49153,),
    )
    input_chain = policy._chain_body(rules, "input")
    output_chain = policy._chain_body(rules, "output")

    assert "49152" in "\n".join(input_chain)
    assert "49153" not in "\n".join(input_chain)
    assert any("tcp dport { 49152, 49153 }" in line for line in output_chain)

    policy.verify_ruleset_text(
        _nft_listing(rules),
        api_port=8000,
        target_ports=(49152,),
        temporary_egress_only_ports=(49153,),
    )


def test_active_ruleset_verification_accepts_only_exact_generated_rules() -> None:
    rules = policy.build_ruleset(api_port=8000, target_ports=(3000,))
    listing = _nft_listing(rules)
    policy.verify_ruleset_text(listing, api_port=8000, target_ports=(3000,))
    handled_listing = listing.replace("table inet aegiscore {", "table inet aegiscore { # handle 1")
    handled_listing = handled_listing.replace("chain input {", "chain input { # handle 2")
    handled_listing = handled_listing.replace("chain output {", "chain output { # handle 3")
    policy.verify_ruleset_text(handled_listing, api_port=8000, target_ports=(3000,))

    with pytest.raises(policy.PolicyError):
        policy.verify_ruleset_text(
            listing.replace("127.0.0.0/8", "0.0.0.0/0"),
            api_port=8000,
            target_ports=(3000,),
        )
    with pytest.raises(policy.PolicyError):
        policy.verify_ruleset_text(
            listing.replace("table inet aegiscore {", "table inet aegiscore {\n}\ntable inet extra {"),
            api_port=8000,
            target_ports=(3000,),
        )
    with pytest.raises(policy.PolicyError):
        policy.verify_ruleset_text(
            listing.replace('oifname "lo" ip daddr 127.0.0.0/8', 'meta mark set 1\n    oifname "lo" ip daddr 127.0.0.0/8'),
            api_port=8000,
            target_ports=(3000,),
        )
    with pytest.raises(policy.PolicyError):
        policy.verify_ruleset_text(
            listing.replace("  chain input {", "  set unexpected { type inet_service; }\n  chain input {"),
            api_port=8000,
            target_ports=(3000,),
        )


@pytest.mark.parametrize("value", ["0", "65536", "80/443", "80,,443", "80,80", "80 x"])
def test_port_configuration_rejects_ambiguous_or_invalid_values(value: str) -> None:
    with pytest.raises(policy.PolicyError):
        policy.parse_ports(value, name="target ports")
