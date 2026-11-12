"""V008 JSON nesting bound: one deeply nested request cannot take the owner down.

The owner parses each request, each snapshot it loads, and its own config with the same
strict JSON loader, and ``json.loads`` recurses once per nested container. Before this slice
a single deeply nested frame from a *listed* peer made the parser raise ``RecursionError``,
which the single-request owner did not catch, so the process exited -- an availability
failure reachable by any admitted requester with one request. Admission control does not
address it: a listed peer is admitted by design, and it takes one request, not a flood.

These tests use real peer processes under distinct uids. Same root requirement and
skip/fail rule as test_v008_isolated_owner.py. Nothing here commits or is withheld; the
boundary stays availability only -- no decision, ledger fact or receipt is affected.
"""
from __future__ import annotations

import json
import signal
import sys

import pytest
from test_v008_crash_recovery import submit
from test_v008_isolated_owner import (
    REQUESTER_UID,
    Deployment,
    make_grant,
    make_proposal,
)

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED and /proc"
)

TELEMETRY = "edge-telemetry.json"

# A listed peer sends one frame whose body is thousands of open brackets: a valid 4-byte
# header, a body under the 64 KiB cap, nested far past anything the parser could recurse
# through. It reads whatever the owner says back, then reports it.
DEEP_FRAME = """
import json, socket, struct, sys
req = json.loads(sys.argv[1])
body = (b"[" * req["depth"]) + (b"]" * req["depth"])
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(30)
sock.connect(req["socket"])
sock.sendall(struct.pack(">I", len(body)) + body)
data = b""
try:
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
except OSError:
    pass
sock.close()
reply = json.loads(data[4:]) if len(data) > 4 else None
print(json.dumps({"reply": reply}), flush=True)
"""


@pytest.fixture
def dep():
    deployment = Deployment()
    try:
        yield deployment
    finally:
        deployment.cleanup()


def _read_telemetry(dep) -> dict:
    return json.loads((dep.data / TELEMETRY).read_text())


def test_a_deeply_nested_request_is_refused_and_the_owner_keeps_serving(dep):
    dep.pid = dep.start_owner()
    payload = json.dumps({"socket": str(dep.sock), "depth": 16000})
    done = dep.run_as(REQUESTER_UID, DEEP_FRAME, payload, timeout=60)
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)

    # The owner answered with its ordinary malformed-frame refusal, and did not die.
    assert report["reply"] == {"ok": False, "error": "bad-frame"}
    assert dep.proc is not None and dep.proc.poll() is None, "owner exited on a deep frame"

    # It still serves: a real grant from the same peer commits exactly as before.
    proposal = make_proposal(pid="after-deep-frame")
    reply = submit(dep, proposal, make_grant(dep.key, proposal))["reply"]
    assert reply["status"] == "COMMITTED"

    # The refusal was recorded as edge telemetry under the peer's kernel uid, as a rejected
    # frame -- not as anything that implies the request was admitted or had an outcome.
    dep.proc.send_signal(signal.SIGTERM)
    dep.proc.wait(timeout=30)
    counters = _read_telemetry(dep)["counters"]
    assert counters[str(REQUESTER_UID)] == {"FRAME_REJECTED": 1}


def test_a_deeply_nested_config_is_refused_cleanly(dep):
    # The config travels through the same loader. A config nested past the bound must make
    # the owner refuse to start with its ordinary message, not fall over with a traceback.
    nested = json.loads("[" * 40 + "]" * 40)
    deep_config = dict(dep.config, audience=nested)
    config_path = dep.conf / "deep.json"
    Deployment.write_config_file(config_path, deep_config)
    done = dep.refused_start(config_path=config_path)
    assert done.returncode == 2, done.stderr
    assert "owner refused to start" in done.stderr
    assert "Traceback" not in done.stderr and "RecursionError" not in done.stderr
