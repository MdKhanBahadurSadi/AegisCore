# Linux default-deny deployment

This deployment uses a dedicated named network namespace with only `lo`, no veth, no bridge, and no default route. nftables policy is installed inside that namespace before the API starts. The API worker drops to a dedicated non-root UID. There is no package installation or network call in the runner.

## Baseline and packages

Required baseline: patched Debian 13 (Trixie), amd64, kernel network namespaces enabled, systemd, Python 3.13 with the application environment already provisioned, `iproute2`, `nftables`, `procps` (`sysctl`), and `util-linux` (`setpriv`). Do not use Docker host networking, an external bridge, a veth, or a public DNS resolver. Prepare Python dependencies before deployment using the organization's approved artifact process; the isolated runner never installs or downloads dependencies.

Install system packages from an approved Debian mirror or offline package set, then confirm the required commands exist:

```sh
command -v ip nft ss setpriv python3
grep -E '^(ID|VERSION_ID)=' /etc/os-release
uname -m
```

The runner independently requires Debian 13 amd64, root, and the required commands. Namespace creation, firewall validation, or any verification failure aborts startup. nftables base chains use explicit `policy drop`; packet counters are attached to each allow and final drop rule. [nftables documents drop policies and verdict behavior](https://www.netfilter.org/projects/nftables/manpage.html), and [ip-netns documents per-namespace network devices, routes, and firewall rules](https://man7.org/linux/man-pages/man8/ip-netns.8.html).

## Install

1. Install this repository at `/opt/aegiscore` with its prepared `.venv`.
2. Create the dedicated identity and state directory:

   ```sh
   sudo useradd --system --home-dir /var/lib/aegiscore --create-home --shell /usr/sbin/nologin aegiscore
   sudo chmod 0750 /var/lib/aegiscore
   ```

3. Install `aegiscore-linux-egress.conf.example` as `/etc/aegiscore/linux-egress.conf`. Set `AEGISCORE_APP_ROOT`, `AEGISCORE_PYTHON`, and the service identity to the installed values. Keep `AEGISCORE_TARGETS_FILE` empty until a reviewed loopback registry exists. If configured, the runner validates the registry and derives enabled target ports from it; operators cannot add free-form firewall ports. `AEGISCORE_LOCAL_CLIENT_PORTS` is empty by default. Set it only for explicit same-namespace client connections, such as a local UI that must connect to the API port.
4. If API authentication is needed, install the existing `AuthSettings` TOML as `AEGISCORE_AUTH_CONFIG_FILE`, owned by `aegiscore`, mode `0600`. This supplies API authentication only; it does not provide a target authorization verifier.
5. Install the systemd unit as `/etc/systemd/system/aegiscore-isolated.service`, then start it:

   ```sh
   sudo systemctl daemon-reload
   sudo systemctl enable --now aegiscore-isolated.service
   sudo systemctl status aegiscore-isolated.service
   ```

`run_isolated.py` first rejects an already existing namespace. It creates `aegiscore`, brings up only `lo`, sets IPv4 and IPv6 forwarding off, verifies loopback-only routing, installs a temporary self-test policy, and runs a local HEAD-only fixture plus denied-egress checks. It removes the temporary API-client and fixture allowances, installs and verifies the production policy, then starts `python -m aegiscore.api` inside the namespace using `setpriv` with all capabilities dropped and no-new-privileges. The API host is fixed to `127.0.0.1`. The runner remains the systemd main process, supervises the API, and rechecks firewall rules, loopback addresses, routes, forwarding flags, and API listener every second. Any drift terminates the API and fails the unit. It removes the namespace only after its processes exit. If a process remains, cleanup fails and leaves the namespace firewall in place.

The systemd unit permits only IPv4, IPv6, and netlink socket families; it omits `AF_UNIX` so the runner and API cannot connect to host Unix-domain service sockets. The application state uses a local SQLite file, not a Unix socket.

## Exact policy

Inbound and outbound are different chains and use different port sets:

| Chain | Allowed new flows | Denied by default |
|---|---|---|
| `input` | TCP arriving through `lo` to API listener port plus ports in enabled target registrations; IPv4 `127.0.0.0/8`, IPv6 `::1` | Every other inbound packet and interface. |
| `output` | TCP leaving through `lo` to enabled target-registration ports. Optionally, explicitly configured local-client destination ports. IPv4 `127.0.0.0/8`, IPv6 `::1` | Every other outbound packet, including UDP/DNS, every non-loopback destination, and all unlisted TCP ports. |

Established/related packets are allowed only when their ingress or egress interface is `lo`, so replies to explicitly allowed loopback flows work. The API listener port is **not** automatically allowed for outbound execution. The application still binds target authorization to an exact scheme, numeric address, port, and path; nftables cannot filter HTTP paths. If no target registry is configured, production output allows no new outbound flow. If an enabled registration changes, restart the service: the runner derives and applies the exact new port set. The app's real authorization verifier remains unconfigured and assessment creation/execution remain fail-closed.

The self-test temporarily allows the API listener and one deterministic fixture port for local TCP handshake and `HEAD` verification. A second controlled fixture port is permitted by the temporary output chain only; the matching input rule remains default-drop. The probe confirms the output allow counter increments and the input drop counter increments for IPv4 and IPv6, testing the input hook independently from the output drop test. It also tests unlisted loopback ports by observing output-drop counters. The runner then replaces the temporary rules and verifies the final production allowlist before deployment is accepted. The fixture's only successful HTTP method is `HEAD`; the test runner does not issue `GET`.

## Verify a live deployment

The runner performs these tests at every service start and logs each result to journald:

- only `lo` exists, and IPv4/IPv6 main routing tables contain no non-loopback route or default route;
- IPv4 and IPv6 controlled loopback `HEAD` requests to the authorized test fixture succeed;
- a controlled TCP connection to a second listening loopback fixture passes the temporary output allow rule but is dropped at input, verified by both counters for IPv4 and IPv6;
- one unlisted IPv4 and one unlisted IPv6 loopback TCP port fail and increment the output drop counter;
- IPv4/IPv6 TEST-NET documentation routes are unreachable; no connection packet is sent when route checks fail;
- UDP to the TEST-NET documentation DNS addresses is unroutable; no DNS query or public DNS request is sent;
- the complete active nftables ruleset contains only the expected table, input/output base chains, exact allow rules, counters, and final drops;
- the API starts inside the namespace, binds only to `127.0.0.1:<AEGISCORE_API_PORT>`, and remains alive after the production rules replace temporary test allowances.

The host network is checked structurally: only `lo` is attached, no veth or other interface exists, and the namespace has no route to the host. The verification deliberately does not probe a host or public target. The production process has no internet route and the output chain drops all destinations except exact loopback target/client TCP ports.

Inspect policy and process placement while the service is running:

```sh
sudo ip netns exec aegiscore ip -brief address
sudo ip netns exec aegiscore ip -4 route show table main
sudo ip netns exec aegiscore ip -6 route show table main
sudo ip netns exec aegiscore nft -a list ruleset
sudo ip netns exec aegiscore ss -lntp
sudo ip netns pids aegiscore
sudo journalctl -u aegiscore-isolated.service --since today
```

Expected: `lo` only, no default/non-loopback route, exact drop-policy chains, API listener on numeric loopback only, and one API process in the namespace. The named namespace and nftables policy persist while the systemd service is running; normal service stop terminates the API before removing the namespace. A failed startup must not be bypassed by running the API outside this unit.

## Trust limitation

The target registry's `authorization_ref` remains an identifier, not proof. This deployment adds no issuer, approval, public key, signature format, or verifier. The existing app factory has no production verifier loader, so the API logs that assessment creation/execution is unavailable. Before enabling those operations, integrate a real trusted verifier that validates issuer/key, signed target/endpoint/version and validity claims, and fresh revocation status. The current systemd unit permits loopback network sockets but disallows `AF_UNIX`; a verifier service therefore needs an explicitly reviewed loopback port added to the local-client allowlist. A future Unix-socket design would require a narrowly scoped unit and filesystem change followed by renewed isolation verification, and must not expose host service sockets. The authority must define issuance, renewal (new signed grant and registration version as needed), expiry, and revocation. Unknown issuer, invalid signature, stale revocation data, expired or revoked approval, and verifier outage must continue to deny execution.
