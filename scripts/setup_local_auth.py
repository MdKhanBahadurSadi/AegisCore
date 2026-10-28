"""Interactively provision the single local AEGISCORE API account."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argon2 import PasswordHasher

from aegiscore.api.auth import default_auth_config_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        help="write to a custom config path instead of the per-user default",
    )
    args = parser.parse_args()
    target = (args.config.expanduser() if args.config else default_auth_config_path()).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit("Refusing to write authentication configuration inside the repository.")
    if target.exists():
        raise SystemExit(f"Authentication config already exists at {target}; it was not changed.")

    username = input("Local API username: ").strip()
    if not username or len(username) > 128:
        raise SystemExit("Username must contain 1 to 128 characters.")
    password = getpass.getpass("Local API password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")

    password_hash = PasswordHasher().hash(password)
    payload = (
        "[auth]\n"
        f"username = {json.dumps(username)}\n"
        f"password_hash = {json.dumps(password_hash)}\n"
        "session_ttl_seconds = 1800\n"
        'permissions = ["records:read", "evidence:read"]\n'
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit(f"Authentication config already exists at {target}; it was not changed.") from None
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as config_file:
        config_file.write(payload)
        config_file.flush()
        os.fsync(config_file.fileno())
    if os.name != "nt":
        os.chmod(target, 0o600)
    print(f"Local authentication config created at: {target}")
    if args.config:
        print("Set AEGISCORE_AUTH_CONFIG_FILE to this path before launching the API.")
    else:
        print("The API will discover this per-user config automatically.")
    print("No password or password hash was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
