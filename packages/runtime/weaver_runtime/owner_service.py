"""WEAVER-V008 (first slice): a separately privileged resource-owner service.

Research-only. ``OwnerService`` wraps the existing ``ProtectedWriteOwner`` and serves it
over a Unix-domain socket. Its security rests on the deployment, not on this class alone:
the process must run as its own unprivileged uid, own the SQLite files in a 0700
directory, and own the socket directory. ``owner_main`` enforces that at startup.

Per connection the service:
  1. reads the kernel-reported peer uid (SO_PEERCRED) and closes WITHOUT READING if that
     uid is not in the configured peer table;
  2. reads one strict, size-limited JSON frame;
  3. for ``submit``, additionally requires the proposal's ``actor_id`` to be one the peer
     uid is allowed to speak for, then hands the proposal and signed grant to the owner.

Requests refused at steps 1 and 3 never reach the gate, so they produce no receipt; only
the in-process refusal counter changes. That is a known gap, not a feature.
"""
from __future__ import annotations

import contextlib
import dataclasses
import os
import socket
import stat
import threading
from collections.abc import Mapping
from typing import Any

from weaver_contracts.gate import GateContractError, Proposal

from .owner_ipc import (
    FrameError,
    UntrustedPathError,
    assert_trusted_path,
    peer_credentials,
    recv_frame,
    send_frame,
)
from .protected_write import ProtectedWriteOwner

_PROPOSAL_FIELDS = frozenset({"proposal_id", "actor_id", "action", "policy_version", "payload"})


class FileVeto:
    """A veto that is active while a flag file exists inside the owner's private directory."""

    def __init__(self, flag_path: str | os.PathLike[str]) -> None:
        self._path = os.fspath(flag_path)

    def vetoed(self) -> bool:
        return os.path.lexists(self._path)


class OwnerService:
    def __init__(
        self,
        socket_path: str | os.PathLike[str],
        owner: ProtectedWriteOwner,
        *,
        peers: Mapping[int, frozenset[str]],
        io_timeout: float = 5.0,
    ) -> None:
        if not peers:
            raise ValueError("peers must name at least one uid; the default is deny")
        self._path = os.fspath(socket_path)
        self._owner = owner
        self._peers = {int(uid): frozenset(actors) for uid, actors in peers.items()}
        self._io_timeout = io_timeout
        self._sock: socket.socket | None = None
        self.refused_peers = 0
        self.refused_actors = 0

    def start(self) -> None:
        parent = os.path.dirname(os.path.abspath(self._path))
        assert_trusted_path(parent, os.geteuid(), leaf="public_dir")
        try:
            st = os.lstat(self._path)
        except FileNotFoundError:
            pass
        else:
            # Only a stale socket that this uid owns may be replaced.
            if not stat.S_ISSOCK(st.st_mode) or st.st_uid != os.geteuid():
                raise UntrustedPathError(f"{self._path} exists and is not our stale socket")
            os.unlink(self._path)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            old = os.umask(0o111)  # socket file mode 0666: access control is the peer uid
            try:
                sock.bind(self._path)
            finally:
                os.umask(old)
            sock.listen(8)
        except BaseException:
            sock.close()
            raise
        self._sock = sock

    def serve_forever(self, stop: threading.Event) -> None:
        if self._sock is None:
            raise RuntimeError("start() has not been called")
        self._sock.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                if stop.is_set():
                    break
                raise
            with conn:
                self.handle(conn)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
            with contextlib.suppress(FileNotFoundError):
                os.unlink(self._path)

    def handle(self, conn: socket.socket) -> None:
        creds = peer_credentials(conn)
        actors = self._peers.get(creds.uid)
        if actors is None:
            self.refused_peers += 1
            return  # close without reading a byte
        conn.settimeout(self._io_timeout)
        try:
            reply = self._dispatch(recv_frame(conn), actors)
        except FrameError:
            reply = {"ok": False, "error": "bad-frame"}
        except OSError:
            return
        with contextlib.suppress(OSError, FrameError):
            send_frame(conn, reply)

    def _dispatch(self, request: Any, actors: frozenset[str]) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("op"), str):
            return {"ok": False, "error": "bad-request"}
        op = request["op"]
        if op == "rows" and set(request) == {"op"}:
            return {"ok": True, "rows": self._owner.rows()}
        if op == "anchor" and set(request) == {"op"}:
            return {"ok": True, "anchor": self._owner.anchor()}
        if op == "submit" and set(request) == {"op", "proposal", "signed_grant"}:
            return self._submit(request["proposal"], request["signed_grant"], actors)
        return {"ok": False, "error": "bad-request"}

    def _submit(
        self, raw: Any, signed_grant: Any, actors: frozenset[str]
    ) -> dict[str, Any]:
        if not isinstance(raw, dict) or set(raw) != _PROPOSAL_FIELDS:
            return {"ok": False, "error": "bad-request"}
        if signed_grant is not None and not isinstance(signed_grant, dict):
            return {"ok": False, "error": "bad-request"}
        try:
            proposal = Proposal(**raw)
        except (GateContractError, TypeError, ValueError):
            return {"ok": False, "error": "bad-request"}
        if proposal.actor_id not in actors:
            self.refused_actors += 1
            return {"ok": False, "error": "actor-not-permitted"}
        outcome = self._owner.submit(proposal, signed_grant)
        return {
            "ok": True,
            "status": outcome.status,
            "reason_code": outcome.reason_code,
            "receipt": dataclasses.asdict(outcome.receipt),
            "result": None if outcome.result is None else dict(outcome.result),
        }
