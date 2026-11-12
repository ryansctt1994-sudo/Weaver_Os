"""V008 request deadlines: a listed peer cannot hold the single-request owner.

The owner still serves one request at a time. What changes is how long one connection may
keep it: a complete request must arrive within an absolute deadline, however its bytes are
paced; an oversized request is refused from its header; a reply that is never read is
abandoned at a deadline. Every peer here is a real process under a listed requester uid.

The boundary these tests also hold: the deadline bounds input only. Once a request is
complete it executes to the end, and a timeout is never treated as evidence that a
submitted operation did not commit.

Same root requirement and skip/fail rule as test_v008_isolated_owner.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest
from test_v008_crash_recovery import (
    HOLD_WRITE_LOCK,
    assert_single_commit,
    outcome,
    popen_as,
    submit,
)
from test_v008_isolated_owner import (
    OWNER_UID,
    REQUESTER_UID,
    Deployment,
    make_grant,
    make_proposal,
)
from weaver_runtime.gate import COMMITTED as ATTEMPT_COMMITTED

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED and /proc"
)

DEADLINE = 1.0  # request_deadline_s set in the owner-private config for these tests
SLACK = 2.5  # process start-up and scheduling allowance on top of the deadline

_CONNECT = """
import json, socket, sys, time
from weaver_runtime.owner_ipc import peer_credentials, recv_frame
req = json.loads(sys.argv[1])
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(req["socket"])
assert peer_credentials(sock).uid == req["owner_uid"]
start = time.monotonic()
print("CONNECTED", flush=True)
"""

IDLE_PEER = _CONNECT + """
sock.settimeout(60)
try:
    result = {"reply": recv_frame(sock)}  # say nothing; wait for the owner's verdict
except Exception as exc:
    result = {"exception": type(exc).__name__}
result["held"] = time.monotonic() - start
print(json.dumps(result), flush=True)
"""

TRICKLE_PEER = _CONNECT + """
import select, struct
result = {"cut": False}
try:
    sock.sendall(struct.pack(">I", 200))  # promise 200 bytes, then deliver one at a time
    for _ in range(200):
        readable, _, _ = select.select([sock], [], [], req["interval"])
        if readable:
            sock.settimeout(5)
            result = {"cut": True, "reply": recv_frame(sock)}
            break
        sock.sendall(b" ")
except OSError as exc:
    result = {"cut": True, "exception": type(exc).__name__}
result["held"] = time.monotonic() - start
print(json.dumps(result), flush=True)
"""

OVERSIZED_PEER = _CONNECT + """
import struct
sock.sendall(struct.pack(">I", 16 * 1024 * 1024))  # announce 16 MiB; send none of it
sock.settimeout(30)
try:
    result = {"reply": recv_frame(sock)}
except Exception as exc:
    result = {"exception": type(exc).__name__}
result["held"] = time.monotonic() - start
print(json.dumps(result), flush=True)
"""

HANG_UP_PEER = _CONNECT + """
sock.sendall(b"\\x00\\x00")  # half of a header, then an orderly close
sock.close()
print(json.dumps({"held": time.monotonic() - start}), flush=True)
"""


@pytest.fixture
def dep():
    deployment = Deployment()
    try:
        yield deployment
    finally:
        deployment.cleanup()


@pytest.fixture
def live(dep):
    dep.config["request_deadline_s"] = DEADLINE
    dep.config["reply_deadline_s"] = DEADLINE
    dep.write_config()
    dep.pid = dep.start_owner()
    return dep


def start_peer(dep, code: str, **extra):
    payload = json.dumps({"socket": str(dep.sock), "owner_uid": OWNER_UID, **extra})
    peer = popen_as(dep, REQUESTER_UID, code, payload)
    assert peer.stdout is not None
    assert peer.stdout.readline().strip() == "CONNECTED"
    return peer


def timed_commit(dep, pid="p1") -> float:
    """Submit a fresh proposal and return how long the requester waited for COMMITTED."""
    p = make_proposal(pid=pid)
    started = time.monotonic()
    reply = submit(dep, p, make_grant(dep.key, p), timeout=30)
    waited = time.monotonic() - started
    assert reply.get("reply", {}).get("status") == ATTEMPT_COMMITTED, reply
    return waited


def report_of(peer) -> dict:
    # Read through the same buffered reader that consumed "CONNECTED": a report printed
    # right after it may already sit in that buffer, where communicate() would miss it.
    assert peer.stdout is not None
    peer.wait(timeout=90)
    return json.loads(peer.stdout.read())


def test_an_idle_listed_peer_is_cut_off_at_the_deadline(live):
    idle = start_peer(live, IDLE_PEER)
    waited = timed_commit(live)
    report = report_of(idle)
    assert report["reply"] == {"ok": False, "error": "request-deadline-exceeded"}, report
    assert DEADLINE * 0.9 <= report["held"] < DEADLINE + SLACK, report
    assert waited < DEADLINE + SLACK, f"a legitimate request waited {waited:.1f}s"


def test_a_trickling_listed_peer_cannot_hold_the_owner_beyond_the_deadline(live):
    # One byte every 0.2 s: each read makes progress, so a per-read timeout never fires.
    trickle = start_peer(live, TRICKLE_PEER, interval=0.2)
    waited = timed_commit(live)
    report = report_of(trickle)
    assert report["cut"], report
    assert report.get("reply", {"error": "request-deadline-exceeded"}) == {
        "ok": False, "error": "request-deadline-exceeded"
    } or report.get("exception") in {"BrokenPipeError", "ConnectionResetError"}, report
    assert report["held"] < DEADLINE + SLACK, report
    assert waited < DEADLINE + SLACK, f"a legitimate request waited {waited:.1f}s"


def test_an_oversized_request_is_refused_from_its_header_and_service_continues(live):
    report = report_of(start_peer(live, OVERSIZED_PEER))
    assert report["reply"] == {"ok": False, "error": "bad-frame"}, report
    # Refused on reading the 4-byte header, not by waiting out the deadline.
    assert report["held"] < DEADLINE * 0.5, report
    assert timed_commit(live) < SLACK


def test_service_recovers_after_a_peer_hangs_up_mid_request(live):
    report_of(start_peer(live, HANG_UP_PEER))
    assert timed_commit(live) < SLACK


def test_the_deadline_bounds_input_never_execution_and_a_timeout_is_not_a_failure(live):
    holder = popen_as(
        live, OWNER_UID, HOLD_WRITE_LOCK, str(live.data / "owner.db"), stdin=subprocess.PIPE
    )
    assert holder.stdout is not None and holder.stdin is not None
    assert holder.stdout.readline().strip() == "LOCKED"
    p = make_proposal()
    signed = make_grant(live.key, p)
    # The request arrives complete, then its commit waits on the lock past the deadline.
    first = submit(live, p, signed, timeout=0.5)
    assert first["error"] == "OutcomeUnknown"  # the client's timeout proves nothing
    time.sleep(DEADLINE + 0.5)  # execution is now running past the request deadline
    holder.stdin.write("release\n")
    holder.stdin.flush()
    holder.communicate(timeout=10)
    found = outcome(live, p, timeout=30)["reply"]["outcome"]
    assert found["status"] == "COMMITTED", found  # it was not cut off by the deadline
    assert_single_commit(live, "p1", {"alpha": "one"})


@pytest.mark.parametrize(
    ("field", "value"),
    [("request_deadline_s", 0), ("request_deadline_s", True), ("reply_deadline_s", 301)],
)
def test_owner_refuses_a_nonsensical_deadline(dep, field, value):
    dep.config[field] = value
    dep.write_config()
    done = dep.refused_start()
    assert done.returncode == 2 and "deadline" in done.stderr
