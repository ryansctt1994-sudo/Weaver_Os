"""V008 request deadlines: unprivileged checks of the deadline primitives.

These run as any user, on every CI Python version. The cross-uid tests with real peer
processes live in tests/isolation/test_v008_request_deadlines.py and need root.
"""
from __future__ import annotations

import os
import socket
import struct
import sys
import threading
import time

import pytest
from weaver_runtime.owner_ipc import (
    MAX_FRAME_BYTES,
    DeadlineExceeded,
    FrameError,
    encode_frame,
    recv_frame,
    send_frame,
)
from weaver_runtime.owner_service import OwnerService

linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SO_PEERCRED")

DEADLINE = 0.5
SLACK = 0.5


def _pair():
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    return a, b


def _within(started: float) -> float:
    return time.monotonic() - started


def test_an_idle_sender_hits_the_deadline():
    reader, writer = _pair()
    with reader, writer:
        started = time.monotonic()
        with pytest.raises(DeadlineExceeded):
            recv_frame(reader, deadline=started + DEADLINE)
        assert DEADLINE * 0.9 <= _within(started) < DEADLINE + SLACK


def test_a_trickling_sender_hits_the_deadline_despite_steady_progress():
    reader, writer = _pair()
    stop = threading.Event()

    def trickle():
        writer.sendall(struct.pack(">I", 100))
        for _ in range(100):
            if stop.wait(0.05):
                return
            try:
                writer.sendall(b" ")
            except OSError:
                return

    thread = threading.Thread(target=trickle, daemon=True)
    with reader, writer:
        thread.start()
        started = time.monotonic()
        try:
            with pytest.raises(DeadlineExceeded):
                recv_frame(reader, deadline=started + DEADLINE)
            assert _within(started) < DEADLINE + SLACK
        finally:
            stop.set()
            thread.join(timeout=5)


def test_a_complete_frame_inside_the_deadline_is_returned():
    reader, writer = _pair()
    with reader, writer:
        writer.sendall(encode_frame({"op": "rows"}))
        assert recv_frame(reader, deadline=time.monotonic() + DEADLINE) == {"op": "rows"}


def test_an_oversized_header_is_refused_without_reading_the_body():
    reader, writer = _pair()
    with reader, writer:
        writer.sendall(struct.pack(">I", MAX_FRAME_BYTES + 1) + b"x" * 1024)
        started = time.monotonic()
        with pytest.raises(FrameError) as caught:
            recv_frame(reader, deadline=started + DEADLINE)
        assert not isinstance(caught.value, DeadlineExceeded)
        assert _within(started) < DEADLINE * 0.5
        reader.setblocking(False)
        assert len(reader.recv(4096)) == 1024  # the body was left unread


def test_without_a_deadline_the_socket_timeout_still_applies_per_read():
    reader, writer = _pair()
    with reader, writer:
        reader.settimeout(0.2)
        with pytest.raises(TimeoutError):
            recv_frame(reader)


def _small_send_buffer(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)


def test_a_peer_that_never_reads_cannot_hold_send_frame_past_its_deadline():
    sender, peer = _pair()
    _small_send_buffer(sender)
    big = {"rows": {f"k{i:05d}": "v" * 48 for i in range(500)}}  # ~30 KiB, under the cap
    assert len(encode_frame(big)) < MAX_FRAME_BYTES
    raised: list[BaseException] = []

    def send():
        try:
            send_frame(sender, big, deadline=time.monotonic() + DEADLINE)
        except BaseException as exc:  # recorded and asserted on below
            raised.append(exc)

    worker = threading.Thread(target=send, daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(timeout=DEADLINE + 3)
    took = _within(started)
    peer.close()  # unblocks a send that ignored its deadline, so the thread can end
    worker.join(timeout=5)
    sender.close()
    assert took < DEADLINE + SLACK, f"send_frame held on for {took:.1f}s"
    assert len(raised) == 1 and isinstance(raised[0], DeadlineExceeded), raised


class _BigRowsOwner:
    """Just enough of ProtectedWriteOwner for a `rows` request with a large reply."""

    def rows(self):
        return {f"k{i:05d}": "v" * 48 for i in range(500)}


@linux_only
def test_the_service_abandons_a_reply_its_peer_never_reads(tmp_path):
    server, client = _pair()
    # A long request deadline, so any timeout left over from reading the request is far
    # longer than the reply deadline: only the reply deadline can end this quickly.
    service = OwnerService(
        tmp_path / "unused.sock", _BigRowsOwner(),  # type: ignore[arg-type]
        peers={os.geteuid(): frozenset({"agent-a"})},
        request_deadline=8.0, reply_deadline=DEADLINE,
    )
    _small_send_buffer(server)
    client.sendall(encode_frame({"op": "rows"}))  # ask, then never read the answer
    worker = threading.Thread(target=service.handle, args=(server,), daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(timeout=DEADLINE + 10)
    took = _within(started)
    client.close()  # unblocks a send that ignored its deadline, so the thread can end
    worker.join(timeout=5)
    server.close()
    assert took < DEADLINE + SLACK + 0.5, f"handle() held the owner for {took:.1f}s"


@linux_only
def test_the_service_cuts_an_idle_peer_and_says_why(tmp_path):
    server, client = _pair()
    service = OwnerService(
        tmp_path / "unused.sock", _BigRowsOwner(),  # type: ignore[arg-type]
        peers={os.geteuid(): frozenset({"agent-a"})},
        request_deadline=DEADLINE, reply_deadline=DEADLINE,
    )
    with server, client:
        started = time.monotonic()
        service.handle(server)
        assert DEADLINE * 0.9 <= _within(started) < DEADLINE + SLACK
        client.settimeout(2)
        assert recv_frame(client) == {"ok": False, "error": "request-deadline-exceeded"}
    assert service.deadline_cutoffs == 1


@pytest.mark.parametrize("value", [0, -1, 301, True, "5", None])
def test_nonsensical_deadlines_are_refused(tmp_path, value):
    with pytest.raises(ValueError, match="deadline"):
        OwnerService(
            tmp_path / "unused.sock", _BigRowsOwner(),  # type: ignore[arg-type]
            peers={0: frozenset({"agent-a"})}, request_deadline=value,
        )
