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

Crash recovery: every ``submit`` reply also carries ``outcome``, what durable history says
about the proposal id after this attempt (see ``owner_outcome``). ``outcome`` answers the
same question for a proposal id alone, so a requester that lost a reply can find out whether
its proposal committed and get the original receipt, instead of guessing. Requests are
served one at a time, so an ``outcome`` answer is never racing an attempt this owner is
still executing.

Deadlines: one connection may hold the owner only so long. A complete request must arrive
within ``request_deadline`` seconds of the owner starting to read it, however its bytes are
paced; an oversized request is refused from its 4-byte header; a reply is abandoned if the
peer has not taken it within ``reply_deadline`` seconds. Neither deadline applies to
execution: a complete request runs to the end.
"""
from __future__ import annotations

import contextlib
import dataclasses
import os
import socket
import stat
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from weaver_contracts.gate import GateContractError, Proposal

from .gate import COMMITTED as ATTEMPT_COMMITTED
from .owner_ipc import (
    DeadlineExceeded,
    FrameError,
    UntrustedPathError,
    assert_trusted_path,
    peer_credentials,
    recv_frame,
    send_frame,
)
from .owner_outcome import OutcomeError, lookup_outcome, proposal_digest
from .protected_write import ProtectedWriteOwner

_PROPOSAL_FIELDS = frozenset({"proposal_id", "actor_id", "action", "policy_version", "payload"})
DEFAULT_DEADLINE_S = 5.0
MAX_DEADLINE_S = 300.0


def valid_deadline(value: Any) -> bool:
    """A deadline is a real number of seconds in (0, MAX_DEADLINE_S]; booleans are not."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 < value <= MAX_DEADLINE_S
    )


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
        request_deadline: float = DEFAULT_DEADLINE_S,
        reply_deadline: float = DEFAULT_DEADLINE_S,
        after_commit: Callable[[], None] | None = None,
    ) -> None:
        if not peers:
            raise ValueError("peers must name at least one uid; the default is deny")
        for name, value in (("request_deadline", request_deadline),
                            ("reply_deadline", reply_deadline)):
            if not valid_deadline(value):
                raise ValueError(f"{name} must be a number of seconds in (0, {MAX_DEADLINE_S}]")
        self._path = os.fspath(socket_path)
        self._owner = owner
        self._peers = {int(uid): frozenset(actors) for uid, actors in peers.items()}
        self._request_deadline = float(request_deadline)
        self._reply_deadline = float(reply_deadline)
        # Fault injection only: owner_main installs this from the trusted launcher's
        # environment to kill the process after a commit and before the reply.
        self._after_commit = after_commit
        self._sock: socket.socket | None = None
        self.refused_peers = 0
        self.refused_actors = 0
        self.deadline_cutoffs = 0

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
        # One complete request must arrive before an absolute deadline, however its bytes
        # are paced. The deadline bounds input only: once a request is complete it executes
        # to the end, and nothing here treats a timeout as evidence that nothing committed.
        deadline = time.monotonic() + self._request_deadline
        try:
            request = recv_frame(conn, deadline=deadline)
        except DeadlineExceeded:
            self.deadline_cutoffs += 1
            self._reply(conn, {"ok": False, "error": "request-deadline-exceeded"})
            return
        except FrameError:
            self._reply(conn, {"ok": False, "error": "bad-frame"})
            return
        except OSError:
            return
        self._reply(conn, self._dispatch(request, actors))

    def _reply(self, conn: socket.socket, reply: dict[str, Any]) -> None:
        # A peer that never reads its reply cannot hold the owner either. If this send is
        # abandoned, the requester sees a lost reply (OutcomeUnknown), not a refusal.
        with contextlib.suppress(OSError, FrameError):
            send_frame(conn, reply, deadline=time.monotonic() + self._reply_deadline)

    def _dispatch(self, request: Any, actors: frozenset[str]) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("op"), str):
            return {"ok": False, "error": "bad-request"}
        op = request["op"]
        if op == "rows" and set(request) == {"op"}:
            return {"ok": True, "rows": self._owner.rows()}
        if op == "anchor" and set(request) == {"op"}:
            return {"ok": True, "anchor": self._owner.anchor()}
        try:
            if op == "submit" and set(request) == {"op", "proposal", "signed_grant"}:
                return self._submit(request["proposal"], request["signed_grant"], actors)
            if op == "outcome" and set(request) == {"op", "proposal_id"}:
                return self._outcome(request["proposal_id"], actors)
        except OutcomeError:
            return {"ok": False, "error": "ledger-inconsistent"}
        return {"ok": False, "error": "bad-request"}

    def _outcome(self, proposal_id: Any, actors: frozenset[str]) -> dict[str, Any]:
        if not isinstance(proposal_id, str) or not proposal_id:
            return {"ok": False, "error": "bad-request"}
        # Only records of the actors this peer may speak for are visible.
        found = lookup_outcome(self._owner.snapshot(), proposal_id, actors=actors)
        return {"ok": True, "outcome": found}

    def _proposal_outcome(self, proposal: Proposal) -> dict[str, Any]:
        return lookup_outcome(
            self._owner.snapshot(),
            proposal.proposal_id,
            actors=frozenset({proposal.actor_id}),
            submitted_sha256=proposal_digest(proposal.to_dict()),
        )

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
        # The gate runs for every attempt, retries included, so each attempt leaves its own
        # receipt (V009) and the ledger's unique key still allows at most one commit (V010).
        attempt = self._owner.submit(proposal, signed_grant)
        if attempt.status == ATTEMPT_COMMITTED and self._after_commit is not None:
            self._after_commit()
        return {
            "ok": True,
            # status/reason_code/receipt describe THIS attempt; outcome describes the
            # proposal id as durable history now records it.
            "status": attempt.status,
            "reason_code": attempt.reason_code,
            "receipt": dataclasses.asdict(attempt.receipt),
            "result": None if attempt.result is None else dict(attempt.result),
            "outcome": self._proposal_outcome(proposal),
        }
