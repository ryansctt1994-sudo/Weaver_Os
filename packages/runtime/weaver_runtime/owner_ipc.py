"""WEAVER-V008 (first slice): IPC primitives for a separately privileged resource owner.

Research-only. This module gives a requester process and an owner process a small,
strict wire format and two kernel-backed checks:

* ``peer_credentials`` reads SO_PEERCRED, the pid/uid/gid the kernel recorded when the
  peer connected. Neither side can forge it by sending bytes.
* ``assert_trusted_path`` refuses a path whose chain of directories could be rewritten by
  an unprivileged user (symlinks, wrong owner, group/other-writable without sticky root).

What this does NOT do: it does not protect against root, a kernel bug, a compromised owner
uid, or an attacker who already runs as the owner uid. It is Linux-only (SO_PEERCRED, /proc).
"""
from __future__ import annotations

import json
import os
import socket
import stat
import struct
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .owner_outcome import COMMITTED, conflict, proposal_digest

MAX_FRAME_BYTES = 64 * 1024
_HEADER = struct.Struct(">I")
_PEERCRED = struct.Struct("3i")

_LEAF_KINDS = frozenset({"socket", "public_dir", "private_dir", "private_file"})


class IpcError(Exception):
    """Base class for owner IPC failures."""


class FrameError(IpcError):
    """A frame was oversized, truncated, not UTF-8 JSON, or ambiguous."""


class DeadlineExceeded(FrameError):
    """A peer did not finish sending a request, or accepting a reply, before the deadline."""


class PeerIdentityError(IpcError):
    """The kernel-reported peer uid is not the expected one."""


class UntrustedPathError(IpcError):
    """A path component could be replaced or rewritten by an unprivileged user."""


class MissingPathError(UntrustedPathError):
    """The path does not exist (for a socket: the owner is not serving)."""


class OwnerUnavailable(IpcError):
    """The request was NOT delivered: there was no owner to connect to. Nothing happened."""


class OutcomeUnknown(IpcError):
    """The request may have reached the owner, but no reply came back.

    This is not a refusal and not a failure. Ask the owner for the proposal's ``outcome``;
    resubmitting the same proposal is safe because at most one commit per proposal id is
    possible.
    """


@dataclass(frozen=True)
class PeerCredentials:
    pid: int
    uid: int
    gid: int


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FrameError(f"duplicate key {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise FrameError(f"non-finite number {name}")


def load_strict_json(text: str) -> Any:
    """Parse JSON, refusing duplicate object keys and NaN/Infinity."""
    try:
        return json.loads(
            text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant
        )
    except ValueError as exc:  # includes JSONDecodeError and int-digit-limit errors
        raise FrameError(f"not valid JSON: {exc}") from exc


def encode_frame(obj: Any) -> bytes:
    try:
        body = json.dumps(
            obj, separators=(",", ":"), allow_nan=False, ensure_ascii=True
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise FrameError(f"not encodable: {exc}") from exc
    if len(body) > MAX_FRAME_BYTES:
        raise FrameError("frame too large")
    return _HEADER.pack(len(body)) + body


def _time_left(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise DeadlineExceeded("deadline exceeded")
    return left


def _recv_exact(sock: socket.socket, count: int, deadline: float | None = None) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        if deadline is not None:
            sock.settimeout(_time_left(deadline))  # absolute: progress never extends it
        try:
            chunk = sock.recv(remaining)
        except TimeoutError as exc:
            if deadline is None:
                raise
            raise DeadlineExceeded("deadline exceeded while receiving") from exc
        if not chunk:
            raise FrameError("connection closed mid-frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_frame(sock: socket.socket, *, deadline: float | None = None) -> Any:
    """Read one frame.

    With ``deadline`` (a ``time.monotonic()`` value) the whole frame must arrive before it,
    however its bytes are paced. The size cap is checked from the 4-byte header, before any
    of the body is read. Without ``deadline`` the socket's own timeout applies per read.
    """
    (length,) = _HEADER.unpack(_recv_exact(sock, _HEADER.size, deadline))
    if length == 0 or length > MAX_FRAME_BYTES:
        raise FrameError("frame length out of range")
    body = _recv_exact(sock, length, deadline)
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FrameError("frame is not UTF-8") from exc
    return load_strict_json(text)


def send_frame(sock: socket.socket, obj: Any, *, deadline: float | None = None) -> None:
    """Send one frame; with ``deadline`` the whole send must finish before it."""
    frame = encode_frame(obj)
    if deadline is not None:
        sock.settimeout(_time_left(deadline))  # sendall: total time, not per chunk
    try:
        sock.sendall(frame)
    except TimeoutError as exc:
        if deadline is None:
            raise
        raise DeadlineExceeded("deadline exceeded while sending") from exc


def peer_credentials(sock: socket.socket) -> PeerCredentials:
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, _PEERCRED.size)
    pid, uid, gid = _PEERCRED.unpack(raw)
    return PeerCredentials(pid, uid, gid)


def assert_trusted_path(path: str | os.PathLike[str], owner_uid: int, *, leaf: str) -> None:
    """Refuse ``path`` unless no unprivileged user could redirect or replace it.

    The path is walked lexically (it is never resolved through symlinks). Every ancestor
    must be a real directory owned by root or ``owner_uid``. An ancestor that group or
    other can write to is accepted only if it is root-owned and sticky (like ``/tmp``),
    where an unprivileged user cannot rename or delete entries they do not own.

    ``leaf`` is one of:
      socket        a socket owned by owner_uid (any mode; see the note at the check)
      public_dir    a directory owned by owner_uid, not group/other writable
      private_dir   a directory owned by owner_uid, no group/other access at all
      private_file  a regular file owned by owner_uid, no group/other access at all
    """
    if leaf not in _LEAF_KINDS:
        raise ValueError(f"unknown leaf kind {leaf!r}")
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    for depth in range(1, len(parts) + 1):
        current = Path(*parts[:depth])
        try:
            st = os.lstat(current)
        except FileNotFoundError as exc:
            raise MissingPathError(f"cannot stat {current}: {exc.strerror}") from exc
        except OSError as exc:
            raise UntrustedPathError(f"cannot stat {current}: {exc.strerror}") from exc
        if stat.S_ISLNK(st.st_mode):
            raise UntrustedPathError(f"{current} is a symlink")
        if depth < len(parts):
            if not stat.S_ISDIR(st.st_mode):
                raise UntrustedPathError(f"{current} is not a directory")
            if st.st_uid not in (0, owner_uid):
                raise UntrustedPathError(f"{current} is owned by uid {st.st_uid}")
            if st.st_mode & 0o022 and not (st.st_mode & stat.S_ISVTX and st.st_uid == 0):
                raise UntrustedPathError(f"{current} is group/other writable")
            continue
        if st.st_uid != owner_uid:
            raise UntrustedPathError(f"{current} is owned by uid {st.st_uid}")
        kind_ok = {
            "socket": stat.S_ISSOCK,
            "public_dir": stat.S_ISDIR,
            "private_dir": stat.S_ISDIR,
            "private_file": stat.S_ISREG,
        }[leaf](st.st_mode)
        if not kind_ok:
            raise UntrustedPathError(f"{current} is not the expected kind ({leaf})")
        # A socket's mode bits decide who may connect, not who may replace it: replacing
        # is governed by the (already checked) parent directory, and who may talk to the
        # owner is decided by the peer uid, so a socket leaf has no forbidden mode bits.
        forbidden = {"socket": 0, "public_dir": 0o022}.get(leaf, 0o077)
        if st.st_mode & forbidden:
            raise UntrustedPathError(
                f"{current} has mode {oct(st.st_mode & 0o777)}; "
                f"bits {oct(forbidden)} must be clear"
            )


class OwnerClient:
    """Requester-side client. It proves WHO it is talking to before it sends anything.

    The order is deliberate: validate the path chain, connect, read the kernel-reported
    uid of the server, and only then write the request. A process that is not running as
    ``expected_owner_uid`` never receives the signed grant.
    """

    def __init__(
        self,
        socket_path: str | os.PathLike[str],
        *,
        expected_owner_uid: int,
        timeout: float = 5.0,
        verify_path: bool = True,
    ) -> None:
        self._path = os.fspath(socket_path)
        self._owner_uid = expected_owner_uid
        self._timeout = timeout
        # verify_path=False exists only so tests can exercise the peer-uid check on its
        # own. A deployment must leave it on.
        self._verify_path = verify_path

    def _call(self, request: Mapping[str, Any], *, mutating: bool = False) -> dict[str, Any]:
        frame = encode_frame(request)
        if self._verify_path:
            try:
                assert_trusted_path(self._path, self._owner_uid, leaf="socket")
            except MissingPathError as exc:
                raise OwnerUnavailable(f"no owner socket at {self._path}") from exc
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self._timeout)
            try:
                sock.connect(self._path)
            except OSError as exc:
                raise OwnerUnavailable(f"cannot connect to the owner: {exc}") from exc
            creds = peer_credentials(sock)
            if creds.uid != self._owner_uid:
                raise PeerIdentityError(
                    f"server runs as uid {creds.uid}, expected {self._owner_uid}"
                )
            # From the first byte sent, the owner may act on the request. A missing,
            # truncated or late reply after this point is NOT evidence of failure.
            try:
                sock.sendall(frame)
                reply = recv_frame(sock)
            except (OSError, FrameError) as exc:
                if mutating:
                    raise OutcomeUnknown(f"no reply after sending: {exc}") from exc
                raise IpcError(f"no reply: {exc}") from exc
        if not isinstance(reply, dict):
            raise FrameError("reply is not an object")
        return reply

    def submit(self, proposal: Any, signed_grant: Mapping[str, Any] | None) -> dict[str, Any]:
        """Submit once. Raises OutcomeUnknown if the reply is lost; see ``outcome``."""
        body = proposal if isinstance(proposal, Mapping) else proposal.to_dict()
        request = {"op": "submit", "proposal": dict(body), "signed_grant": signed_grant}
        return self._call(request, mutating=True)

    def outcome(self, proposal: Any) -> dict[str, Any]:
        """What durable history says about a proposal: COMMITTED, REFUSED, UNKNOWN or CONFLICT.

        Pass the proposal itself (not just its id) whenever you have it: a commit recorded
        for the same id but different content is then reported as CONFLICT, never as yours.
        """
        if isinstance(proposal, str):
            return self._call({"op": "outcome", "proposal_id": proposal})
        body = dict(proposal if isinstance(proposal, Mapping) else proposal.to_dict())
        reply = self._call({"op": "outcome", "proposal_id": body["proposal_id"]})
        found = reply.get("outcome")
        if (
            reply.get("ok")
            and isinstance(found, dict)
            and found.get("status") == COMMITTED
            and found.get("proposal_sha256") != proposal_digest(body)
        ):
            reply = dict(reply, outcome=conflict(body["proposal_id"]))
        return reply

    def rows(self) -> dict[str, Any]:
        return self._call({"op": "rows"})

    def anchor(self) -> dict[str, Any]:
        return self._call({"op": "anchor"})
