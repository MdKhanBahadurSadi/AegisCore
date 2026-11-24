#!/usr/bin/env python3
"""Provision, verify, and run AEGISCORE in a no-veth Linux namespace."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

if sys.platform == "linux":
    import grp
    import pwd
else:
    grp = None
    pwd = None

from policy import PolicyError, build_ruleset, parse_port, parse_ports, verify_ruleset_text


_CONFIG_KEYS = {
    "AEGISCORE_NAMESPACE",
    "AEGISCORE_API_PORT",
    "AEGISCORE_TARGETS_FILE",
    "AEGISCORE_LOCAL_CLIENT_PORTS",
    "AEGISCORE_RUN_USER",
    "AEGISCORE_RUN_GROUP",
    "AEGISCORE_APP_ROOT",
    "AEGISCORE_PYTHON",
    "AEGISCORE_STORE_PATH",
    "AEGISCORE_AUTH_CONFIG_FILE",
}
_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_FIXED_PROBE_PORTS = tuple(range(49152, 49200))


class DeploymentError(RuntimeError):
    """The required isolated deployment could not be established safely."""


def _read_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise DeploymentError(f"deployment configuration is missing: {path}")
    config: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DeploymentError(f"invalid deployment configuration line {line_number}")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in _CONFIG_KEYS or key in config:
            raise DeploymentError(f"unknown or duplicate deployment configuration key: {key}")
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        if any(ord(char) < 0x20 for char in value):
            raise DeploymentError(f"invalid control character in configuration value: {key}")
        config[key] = value
    return config


def _require_linux_baseline() -> None:
    if sys.platform != "linux":
        raise DeploymentError("Linux network isolation requires Linux; deployment was not started")
    os_release = Path("/etc/os-release")
    if not os_release.is_file():
        raise DeploymentError("cannot establish Debian release identity")
    values: dict[str, str] = {}
    for line in os_release.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    if values.get("ID") != "debian" or values.get("VERSION_ID") != "13":
        raise DeploymentError("deployment baseline requires Debian 13")
    if platform.machine() not in {"x86_64", "amd64"}:
        raise DeploymentError("deployment baseline requires Debian amd64")
    if os.geteuid() != 0:
        raise DeploymentError("namespace and nftables provisioning requires root")
    for command in ("ip", "nft", "ss", "setpriv", "sysctl", "python3"):
        if shutil.which(command) is None:
            raise DeploymentError(f"required deployment command is missing: {command}")


def _run(argv: list[str], *, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, text=True, capture_output=True, input=input_text, check=False)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DeploymentError(f"deployment command failed ({argv[0]}): {detail[:400]}")
    return result


def _inside(namespace: str, argv: list[str], *, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return _run(["ip", "netns", "exec", namespace, *argv], check=check, input_text=input_text)


def _target_ports(app_root: Path, path_value: str) -> tuple[int, ...]:
    if not path_value:
        return ()
    target_file = Path(path_value).expanduser().resolve(strict=True)
    sys.path.insert(0, str(app_root))
    try:
        from aegiscore.target_authorization import load_target_registry

        registry = load_target_registry(target_file)
    except Exception:
        raise DeploymentError("configured authorized target registry could not be validated") from None
    if registry is None:
        return ()
    ports = tuple(sorted({registration.port for registration in registry.registrations if registration.enabled}))
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise DeploymentError("target registry contains an invalid TCP port")
    return ports


def _nft_snapshot(namespace: str) -> str:
    return _inside(namespace, ["nft", "-a", "list", "ruleset"]).stdout


def _verify_rules(
    namespace: str,
    *,
    api_port: int,
    targets: tuple[int, ...],
    clients: tuple[int, ...],
) -> None:
    try:
        verify_ruleset_text(
            _nft_snapshot(namespace),
            api_port=api_port,
            target_ports=targets,
            local_client_ports=clients,
        )
    except PolicyError as exc:
        raise DeploymentError(f"active namespace firewall did not match its generated policy: {exc}") from None


def _verify_namespace_shape(namespace: str) -> None:
    links = json.loads(_inside(namespace, ["ip", "-j", "link", "show"]).stdout)
    if {item.get("ifname") for item in links} != {"lo"}:
        raise DeploymentError("network namespace gained a non-loopback interface")
    if "UP" not in links[0].get("flags", []):
        raise DeploymentError("network namespace loopback interface is down")
    address_records = json.loads(_inside(namespace, ["ip", "-j", "address", "show", "dev", "lo"]).stdout)
    addresses = {
        (item.get("family"), item.get("local"), item.get("prefixlen"))
        for item in address_records[0].get("addr_info", [])
    }
    if addresses != {("inet", "127.0.0.1", 8), ("inet6", "::1", 128)}:
        raise DeploymentError("network namespace loopback addresses changed")
    for family, flag, loopback in (
        (4, "-4", ipaddress.ip_network("127.0.0.0/8")),
        (6, "-6", ipaddress.ip_network("::1/128")),
    ):
        routes = json.loads(_inside(namespace, ["ip", flag, "-j", "route", "show", "table", "main"]).stdout)
        for route in routes:
            destination = route.get("dst")
            if destination in {None, "default"} or route.get("dev") != "lo":
                raise DeploymentError("network namespace gained a default or non-loopback route")
            try:
                network = ipaddress.ip_network(destination, strict=False)
            except ValueError:
                raise DeploymentError("network namespace contains an invalid route") from None
            if network.version != family or not network.subnet_of(loopback):
                raise DeploymentError("network namespace gained a route outside loopback")
    ipv4_forward = _inside(namespace, ["sysctl", "-n", "net.ipv4.ip_forward"]).stdout.strip()
    ipv6_forward = _inside(namespace, ["sysctl", "-n", "net.ipv6.conf.all.forwarding"]).stdout.strip()
    if ipv4_forward != "0" or ipv6_forward != "0":
        raise DeploymentError("IP forwarding must remain disabled in the network namespace")


def _install_rules(namespace: str, ruleset: str, *, replace_existing: bool) -> None:
    payload = ("delete table inet aegiscore\n" if replace_existing else "") + ruleset
    _inside(namespace, ["nft", "-c", "-f", "-"], input_text=payload)
    _inside(namespace, ["nft", "-f", "-"], input_text=payload)


def _probe_port(
    namespace: str,
    api_port: int,
    targets: tuple[int, ...],
    clients: tuple[int, ...],
    *,
    reserved: tuple[int, ...] = (),
) -> int:
    used = {api_port, *targets, *clients, *reserved}
    for port in _FIXED_PROBE_PORTS:
        if port not in used:
            return port
    raise DeploymentError("no unused deterministic self-test port is available")


def _wait_for_ready(process: subprocess.Popen[str], ready_file: Path) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if ready_file.exists():
            return
        if process.poll() is not None:
            raise DeploymentError("controlled loopback HEAD fixture exited before becoming ready")
        time.sleep(0.05)
    raise DeploymentError("controlled loopback HEAD fixture did not become ready")


def _network_self_test(
    namespace: str,
    *,
    app_python: Path,
    probe_script: Path,
    api_port: int,
    targets: tuple[int, ...],
    clients: tuple[int, ...],
) -> None:
    test_port = _probe_port(namespace, api_port, targets, clients)
    input_deny_port = _probe_port(namespace, api_port, targets, clients, reserved=(test_port,))
    temporary_rules = build_ruleset(
        api_port=api_port,
        target_ports=targets,
        local_client_ports=clients,
        temporary_test_ports=(test_port,),
        temporary_egress_only_ports=(input_deny_port,),
        allow_api_client_test=True,
    )
    _install_rules(namespace, temporary_rules, replace_existing=False)
    with tempfile.TemporaryDirectory(prefix="aegiscore-egress-probe-") as scratch:
        ready_file = Path(scratch) / "ready"
        fixture = subprocess.Popen(
            ["ip", "netns", "exec", namespace, str(app_python), str(probe_script), "serve",
             "--port", str(test_port), "--input-deny-port", str(input_deny_port),
             "--ready-file", str(ready_file)],
            cwd=probe_script.parents[2],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            _wait_for_ready(fixture, ready_file)
            check_args = [
                "ip", "netns", "exec", namespace, str(app_python), str(probe_script), "check",
                "--api-port", str(api_port), "--probe-port", str(test_port),
                "--input-deny-port", str(input_deny_port),
                "--target-ports", ",".join(map(str, sorted({*targets, test_port}))),
                "--egress-only-test-ports", str(input_deny_port),
                "--local-client-ports", ",".join(map(str, clients)),
                "--allow-api-client",
            ]
            check_result = _run(check_args)
            print(check_result.stdout, end="")
        finally:
            fixture.terminate()
            try:
                fixture.wait(timeout=3)
            except subprocess.TimeoutExpired:
                fixture.kill()
                fixture.wait(timeout=3)


def _listener_present(namespace: str, api_port: int, *, process_pid: int | None = None) -> bool:
    result = _inside(namespace, ["ss", "-H", "-ltnp"], check=False)
    if result.returncode != 0:
        return False
    lines = result.stdout.splitlines()
    if len(lines) != 1:
        return False
    fields = lines[0].split()
    if len(fields) < 4 or fields[3] != f"127.0.0.1:{api_port}":
        return False
    return process_pid is None or re.search(rf"\bpid={process_pid}(?:,|\))", lines[0]) is not None


def _ensure_state_directory(store_path: Path, uid: int, gid: int) -> None:
    state_dir = store_path.parent
    if store_path != Path("/var/lib/aegiscore/records.sqlite3"):
        raise DeploymentError("SQLite state path must be /var/lib/aegiscore/records.sqlite3")
    if state_dir.is_symlink() or store_path.is_symlink():
        raise DeploymentError("SQLite state path must not contain a symlink")
    created = not state_dir.exists()
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    state = state_dir.stat()
    if created:
        os.chown(state_dir, uid, gid)
        os.chmod(state_dir, 0o750)
    elif state.st_uid != uid or state.st_mode & 0o022:
        raise DeploymentError("existing SQLite state directory must be owned by the service user and not group/world-writable")
    if store_path.exists():
        database = store_path.stat()
        if not store_path.is_file() or database.st_uid != uid or database.st_mode & 0o077:
            raise DeploymentError("existing SQLite database must be mode 0600 or stricter and owned by the service user")


def _namespace_exists(namespace: str) -> bool:
    result = _run(["ip", "netns", "list"], check=False)
    return any(line.split()[0] == namespace for line in result.stdout.splitlines() if line.split())


def _cleanup(namespace: str, created: bool) -> None:
    if not created or not _namespace_exists(namespace):
        return
    pids_result = _run(["ip", "netns", "pids", namespace], check=False)
    pids = [pid for pid in pids_result.stdout.split() if pid.isdigit()]
    if pids:
        raise DeploymentError("namespace still has processes; leaving it and its drop policy intact")
    _run(["ip", "netns", "del", namespace])


def _start_app(
    namespace: str,
    *,
    app_root: Path,
    python: Path,
    run_user: str,
    run_group: str,
    store_path: Path,
    api_port: int,
    target_file: str,
    auth_config: str,
) -> subprocess.Popen[str]:
    account = pwd.getpwnam(run_user)
    group = grp.getgrnam(run_group)
    if account.pw_uid == 0 or group.gr_gid == 0:
        raise DeploymentError("AEGISCORE must run as a non-root service identity")
    _ensure_state_directory(store_path, account.pw_uid, group.gr_gid)
    environment = {
        "PATH": os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin"),
        "HOME": account.pw_dir or "/var/empty",
        "LANG": "C.UTF-8",
        "PYTHONPATH": str(app_root),
        "AEGISCORE_API_HOST": "127.0.0.1",
        "AEGISCORE_API_PORT": str(api_port),
        "AEGISCORE_LOCAL_STORE_PATH": str(store_path),
    }
    if target_file:
        if not Path(target_file).is_absolute():
            raise DeploymentError("authorized target registry path must be absolute")
        environment["AEGISCORE_AUTHORIZED_TARGETS_FILE"] = target_file
    if auth_config:
        if not Path(auth_config).is_absolute():
            raise DeploymentError("authentication configuration path must be absolute")
        auth_path = Path(auth_config).expanduser().resolve(strict=True)
        auth_stat = auth_path.stat()
        if auth_stat.st_uid != account.pw_uid or auth_stat.st_mode & 0o077:
            raise DeploymentError("authentication configuration must be owned by the service user with mode 0600 or stricter")
        environment["AEGISCORE_AUTH_CONFIG_FILE"] = str(auth_path)

    env_args: list[str] = []
    for key, value in environment.items():
        env_args.append(f"{key}={value}")
    command = [
        "ip", "netns", "exec", namespace, "setpriv",
        "--reuid", str(account.pw_uid), "--regid", str(group.gr_gid), "--init-groups",
        "--inh-caps=-all", "--bounding-set=-all", "--no-new-privs",
        "/usr/bin/env", *env_args, str(python), "-m", "aegiscore.api",
    ]
    original_umask = os.umask(0o077)
    try:
        process = subprocess.Popen(command, cwd=app_root, text=True)
    finally:
        os.umask(original_umask)
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise DeploymentError(f"AEGISCORE exited during isolated startup with code {process.returncode}")
            if _listener_present(namespace, api_port, process_pid=process.pid):
                pid_list = _run(["ip", "netns", "pids", namespace]).stdout.split()
                if str(process.pid) not in pid_list:
                    raise DeploymentError("API listener is not owned by the process in the isolated namespace")
                return process
            time.sleep(0.1)
        raise DeploymentError("AEGISCORE did not bind its configured loopback API port")
    except Exception:
        _stop_process(process)
        raise


def _stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def run(config_path: Path) -> int:
    _require_linux_baseline()
    config = _read_config(config_path)
    namespace = config.get("AEGISCORE_NAMESPACE", "aegiscore")
    if _NAMESPACE_RE.fullmatch(namespace) is None:
        raise DeploymentError("network namespace name is invalid")
    if _namespace_exists(namespace):
        raise DeploymentError(f"network namespace {namespace} already exists; refusing to reuse unknown state")

    app_root = Path(config.get("AEGISCORE_APP_ROOT", "")).expanduser().resolve(strict=True)
    python = Path(config.get("AEGISCORE_PYTHON", "")).expanduser().resolve(strict=True)
    if not app_root.is_dir() or not python.is_file():
        raise DeploymentError("configured application root or Python executable is invalid")
    api_port = parse_port(config.get("AEGISCORE_API_PORT", "8000"), name="AEGISCORE_API_PORT")
    clients = parse_ports(config.get("AEGISCORE_LOCAL_CLIENT_PORTS", ""), name="AEGISCORE_LOCAL_CLIENT_PORTS")
    target_file = config.get("AEGISCORE_TARGETS_FILE", "")
    targets = _target_ports(app_root, target_file)
    if set(targets) & set(clients):
        raise DeploymentError("local client ports and registered target ports must not overlap")

    store_path = Path(config.get("AEGISCORE_STORE_PATH", "/var/lib/aegiscore/records.sqlite3")).expanduser()
    if not store_path.is_absolute():
        raise DeploymentError("AEGISCORE_STORE_PATH must be absolute")
    run_user = config.get("AEGISCORE_RUN_USER", "aegiscore")
    run_group = config.get("AEGISCORE_RUN_GROUP", run_user)
    auth_config = config.get("AEGISCORE_AUTH_CONFIG_FILE", "")
    probe_script = Path(__file__).with_name("isolation_probe.py").resolve(strict=True)

    created = False
    api_process: subprocess.Popen[str] | None = None
    stopping = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        stopping.set()

    old_term = signal.signal(signal.SIGTERM, request_stop)
    old_int = signal.signal(signal.SIGINT, request_stop)
    try:
        _run(["ip", "netns", "add", namespace])
        created = True
        _inside(namespace, ["ip", "link", "set", "lo", "up"])
        _inside(namespace, ["sysctl", "-w", "net.ipv4.ip_forward=0", "net.ipv6.conf.all.forwarding=0"])
        _verify_namespace_shape(namespace)

        _network_self_test(
            namespace,
            app_python=python,
            probe_script=probe_script,
            api_port=api_port,
            targets=targets,
            clients=clients,
        )

        # The API itself is checked by a TCP listener inspection, never by a GET.
        api_process = _start_app(
            namespace,
            app_root=app_root,
            python=python,
            run_user=run_user,
            run_group=run_group,
            store_path=store_path,
            api_port=api_port,
            target_file=target_file,
            auth_config=auth_config,
        )
        _run(["ip", "netns", "exec", namespace, str(python), str(probe_script), "tcp-check",
              "--host", "127.0.0.1", "--port", str(api_port)])
        print("PASS: API accepted a loopback TCP handshake during isolated startup verification")

        # Remove the temporary probe and API-client egress grants before the service
        # is considered deployed. Production egress is target ports plus configured
        # local-client ports only; inbound API access remains a separate rule.
        final_rules = build_ruleset(
            api_port=api_port,
            target_ports=targets,
            local_client_ports=clients,
        )
        _install_rules(namespace, final_rules, replace_existing=True)
        _verify_rules(namespace, api_port=api_port, targets=targets, clients=clients)
        if not _listener_present(namespace, api_port, process_pid=api_process.pid) or api_process.poll() is not None:
            raise DeploymentError("API listener or process did not survive final policy installation")
        print("PASS: production nftables policy is active and the API remains bound to loopback")
        print(f"INFO: inbound ports: API {api_port}, targets {','.join(map(str, targets)) or 'none'}")
        print(f"INFO: outbound ports: targets {','.join(map(str, targets)) or 'none'}, local clients {','.join(map(str, clients)) or 'none'}")
        print("PASS: no veth, external route, DNS route, or host-network interface is present")
        print("ACTIVE NFTABLES RULESET:")
        print(_nft_snapshot(namespace), end="")
        if target_file and targets:
            print("PASS: outbound execution ports exactly match enabled target-registry ports")
        else:
            print("INFO: no target registry is configured; new outbound execution is fully denied")
        print("INFO: authorization verification remains unavailable unless a real verifier is integrated")

        next_policy_audit = 0.0
        while not stopping.is_set():
            return_code = api_process.poll()
            if return_code is not None:
                raise DeploymentError(f"AEGISCORE stopped with exit code {return_code}")
            if time.monotonic() >= next_policy_audit:
                _verify_namespace_shape(namespace)
                _verify_rules(namespace, api_port=api_port, targets=targets, clients=clients)
                if not _listener_present(namespace, api_port, process_pid=api_process.pid):
                    raise DeploymentError("API loopback listener disappeared during deployment")
                next_policy_audit = time.monotonic() + 1.0
            stopping.wait(0.2)
        return 0
    finally:
        _stop_process(api_process)
        if created:
            _cleanup(namespace, created)
        signal.signal(signal.SIGTERM, old_term)
        signal.signal(signal.SIGINT, old_int)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/etc/aegiscore/linux-egress.conf"))
    args = parser.parse_args()
    try:
        return run(args.config)
    except (DeploymentError, PolicyError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"isolated deployment failed closed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
