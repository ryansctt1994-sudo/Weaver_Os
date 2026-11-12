"""WEAVER-V008 (first slice): launcher for the resource-owner process.

    python -m weaver_runtime.owner_main --config /path/to/owner.json

Research-only. The launcher refuses to run unless the environment it was given looks
like the intended deployment. Each refusal exits non-zero with one line on stderr:

* it must not be root (the owner is meant to be its own unprivileged principal);
* it must have inherited no file descriptors beyond stdin/stdout/stderr;
* the config must be a regular file owned by this uid with mode 0600/0400, reached
  through a path that no unprivileged user could redirect;
* the data directory must be owned by this uid, mode 0700, and not a symlink;
* an existing database or SQLite sidecar must be a regular file owned by this uid.

It then marks itself non-dumpable (so same-uid ptrace and /proc/<pid>/mem are closed to
other users), sets umask 077 and serves until SIGTERM/SIGINT. It prints ``READY`` once
the socket is listening.

The trusted configuration (issuer key, allowed keys, peer-uid table) comes only from the
config file. A requester can supply a proposal and a signed grant, never configuration.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import ctypes
import os
import signal
import stat
import sys
import threading
from pathlib import Path
from typing import Any

from .owner_ipc import IpcError, UntrustedPathError, assert_trusted_path, load_strict_json
from .owner_service import FileVeto, OwnerService
from .protected_write import ProtectedWriteOwner

_PR_SET_DUMPABLE = 4
_REQUIRED = frozenset(
    {"data_dir", "socket_path", "issuer_id", "allowed_keys", "trusted_public_key_b64", "peers"}
)
_OPTIONAL = frozenset({"audience", "ledger_id"})
_SIDECARS = ("", "-wal", "-shm", "-journal")


class StartupRefused(Exception):
    pass


def _open_descriptors() -> list[int]:
    found: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        try:
            target = os.readlink(f"/proc/self/fd/{name}")
        except OSError:
            continue  # the descriptor used for this listing is already gone
        if target.startswith("/proc/") and target.endswith("/fd"):
            continue
        found.append(int(name))
    return sorted(found)


def _refuse_inherited_descriptors() -> None:
    extra = [fd for fd in _open_descriptors() if fd > 2]
    if extra:
        raise StartupRefused(f"inherited file descriptors {extra}; launch with close_fds")


def _set_non_dumpable() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(_PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
        raise StartupRefused("could not clear the dumpable flag")


def _load_config(path: str) -> dict[str, Any]:
    assert_trusted_path(path, os.geteuid(), leaf="private_file")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags)
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        config = load_strict_json(handle.read(65536))
    if not isinstance(config, dict):
        raise StartupRefused("config must be a JSON object")
    keys = set(config)
    if not _REQUIRED <= keys or keys - _REQUIRED - _OPTIONAL:
        raise StartupRefused("config has missing or unknown fields")
    return config


def _check_existing_db(db_path: Path) -> None:
    for suffix in _SIDECARS:
        candidate = Path(f"{db_path}{suffix}")
        try:
            st = os.lstat(candidate)
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISREG(st.st_mode)
            or st.st_uid != os.geteuid()
            or st.st_mode & 0o077
            or st.st_nlink != 1
        ):
            raise StartupRefused(f"{candidate} is not a private regular file owned by us")


def _parse_peers(raw: Any) -> dict[int, frozenset[str]]:
    if not isinstance(raw, dict) or not raw:
        raise StartupRefused("peers must be a nonempty object")
    peers: dict[int, frozenset[str]] = {}
    for uid_text, actors in raw.items():
        if not uid_text.isdecimal() or not isinstance(actors, list) or not actors:
            raise StartupRefused("each peer needs a numeric uid and a nonempty actor list")
        if not all(isinstance(actor, str) and actor for actor in actors):
            raise StartupRefused("actor ids must be nonempty strings")
        peers[int(uid_text)] = frozenset(actors)
    return peers


def run(config_path: str) -> int:
    _refuse_inherited_descriptors()
    if os.geteuid() == 0:
        raise StartupRefused("refusing to run as root; the owner needs its own uid")
    os.umask(0o077)
    _set_non_dumpable()
    config = _load_config(config_path)

    data_dir = Path(config["data_dir"])
    assert_trusted_path(data_dir, os.geteuid(), leaf="private_dir")
    db_path = data_dir / "owner.db"
    _check_existing_db(db_path)
    try:
        key = base64.b64decode(config["trusted_public_key_b64"], validate=True)
    except (binascii.Error, TypeError) as exc:
        raise StartupRefused("trusted_public_key_b64 is not base64") from exc
    allowed = config["allowed_keys"]
    if not isinstance(allowed, list):
        raise StartupRefused("allowed_keys must be a list")

    owner = ProtectedWriteOwner(
        db_path,
        trusted_public_key=key,
        issuer_id=config["issuer_id"],
        allowed_keys=frozenset(allowed),
        veto=FileVeto(data_dir / "veto.flag"),
        audience=config.get("audience", "weaver-vertical-001"),
        ledger_id=config.get("ledger_id", "weaver-vertical-001"),
    )
    service = OwnerService(config["socket_path"], owner, peers=_parse_peers(config["peers"]))
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    try:
        service.start()
        print("READY", flush=True)
        service.serve_forever(stop)
    finally:
        service.close()
        owner.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="weaver_runtime.owner_main")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        return run(args.config)
    except (StartupRefused, UntrustedPathError, IpcError, OSError, ValueError) as exc:
        print(f"owner refused to start: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
