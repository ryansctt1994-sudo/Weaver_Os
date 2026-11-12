"""V008 service-edge security telemetry: hostile clients cannot use it against the owner.

Telemetry is private, bounded, best-effort operational evidence about refusals at the
service edge. It is not a receipt, it is never read on the way to a decision, and no
requester can read it. These tests check, with real processes under real uids, that a
hostile client cannot use it to change an authorization decision (E01), alter another
actor's recorded history (E02), exhaust the owner beyond declared limits (E03, E05), forge
attribution (E04), or extract information (E06), and how an interrupted owner and a damaged
file are handled (E07). E08 (caps) is covered by tests/test_owner_telemetry.py, E09 by
tools/check_v008_mutations.py and E10 by the full suite.

Same root requirement and skip/fail rule as test_v008_isolated_owner.py.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from test_v008_crash_recovery import (
    enable_test_failpoints,
    facts,
    outcome,
    submit,
)
from test_v008_isolated_owner import (
    OTHER_UID,
    OWNER_UID,
    REQUESTER_UID,
    SECOND_PEER_UID,
    Deployment,
    make_grant,
    make_proposal,
)
from weaver_runtime.gate import COMMITTED as ATTEMPT_COMMITTED

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED and /proc"
)

TELEMETRY = "edge-telemetry.json"

HOSTILE = """
import json, os, socket, struct, sys
req = json.loads(sys.argv[1])
def frame(obj):
    body = json.dumps(obj).encode()
    return struct.pack('>I', len(body)) + body
done = 0
replies = []
for _ in range(req['n']):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(req.get('timeout', 30))
    sock.connect(req['socket'])
    kind = req['kind']
    if kind == 'bad-frame':
        sock.sendall(struct.pack('>I', 0))
    elif kind == 'oversized':
        sock.sendall(struct.pack('>I', 16 * 1024 * 1024))
    elif kind == 'request':
        sock.sendall(frame(req['payload']))
    data = b''
    try:
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    sock.close()
    if req.get('keep') and len(data) > 4:
        replies.append(json.loads(data[4:]))
    done += 1
print(json.dumps({'done': done, 'pid': os.getpid(), 'replies': replies}), flush=True)
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
    dep.pid = dep.start_owner()
    return dep


def hostile(dep, uid: int, kind: str, n: int, **extra) -> dict:
    payload = json.dumps({"socket": str(dep.sock), "kind": kind, "n": n, **extra})
    done = dep.run_as(uid, HOSTILE, payload, timeout=300)
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert report["done"] == n
    return report


def telemetry_path(dep) -> Path:
    return dep.data / TELEMETRY


def read_telemetry(dep) -> dict:
    return json.loads(telemetry_path(dep).read_text())


def stop_owner(dep, timeout: float = 30) -> tuple[float, dict]:
    """SIGTERM the owner; return how long it took and its telemetry shutdown summary."""
    proc = dep.proc
    assert proc is not None and proc.stderr is not None
    started = time.monotonic()
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=timeout)
    took = time.monotonic() - started
    err = proc.stderr.read()
    line = next((x for x in err.splitlines() if x.startswith("edge telemetry:")), "")
    assert line, err
    return took, dict(re.findall(r"(\w+)=(\S+)", line))


def _commit_as_agent_b(dep, pid: str):
    theirs = make_proposal(pid=pid, key="beta", actor="agent-b")
    reply = submit(dep, theirs, make_grant(dep.key, theirs), uid=SECOND_PEER_UID)["reply"]
    assert reply["status"] == ATTEMPT_COMMITTED
    return theirs


def test_e01_a_failing_telemetry_write_never_changes_a_decision(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="telemetry-persist-fails")
    hostile(dep, OTHER_UID, "connect", 20)
    forged = make_proposal(pid="px", key="beta", actor="agent-b")
    reply = submit(dep, forged, make_grant(dep.key, forged))["reply"]
    assert reply == {"ok": False, "error": "actor-not-permitted"}
    p = make_proposal()
    assert submit(dep, p, make_grant(dep.key, p))["reply"]["status"] == ATTEMPT_COMMITTED
    assert facts(dep, "px")["rows"] == {"alpha": "one"}
    _took, summary = stop_owner(dep)
    assert summary["events_observed"] == "21"
    assert int(summary["persist_failures"]) >= 1 and summary["last_persist"] == "failed"
    assert not telemetry_path(dep).exists()


def test_e01_a_hung_telemetry_write_cannot_hold_the_owner(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="telemetry-persist-hangs")
    # Short per-connection timeouts: if the owner were stuck, this fails in seconds
    # instead of waiting out a long client timeout.
    hostile(dep, OTHER_UID, "connect", 5, timeout=2)
    time.sleep(0.5)  # the writer is now stuck inside its write
    started = time.monotonic()
    p = make_proposal()
    reply = submit(dep, p, make_grant(dep.key, p), timeout=5)
    assert reply.get("reply", {}).get("status") == ATTEMPT_COMMITTED, reply
    assert time.monotonic() - started < 3.0
    hostile(dep, OTHER_UID, "connect", 5, timeout=2)
    took, summary = stop_owner(dep)
    assert took < 10.0, f"shutdown took {took:.1f}s"
    assert summary["shutdown_flush"] == "timed-out"
    assert "shutdown-flush-timed-out" in summary["degraded"]


def test_e01_a_failed_snapshot_is_never_evidence_and_degradation_rides_the_next(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="telemetry-persist-fails-once")
    hostile(dep, OTHER_UID, "connect", 3)
    time.sleep(1.2)  # the first write (which fails) happens after the flush interval
    assert not telemetry_path(dep).exists()  # no durable record says a failure occurred
    hostile(dep, OTHER_UID, "connect", 2)
    _took, summary = stop_owner(dep)
    assert summary["persist_failures"] == "1" and summary["last_persist"] == "ok"
    assert "persist-failed" in summary["degraded"]
    tel = read_telemetry(dep)
    assert tel["degraded"] == ["persist-failed"] and tel["events_observed"] == 5


def test_e01_a_failed_directory_sync_is_degraded_not_durable_success(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="telemetry-dir-fsync-fails")
    hostile(dep, OTHER_UID, "connect", 4)
    _took, summary = stop_owner(dep)
    assert summary["last_persist"] == "unsynced"
    assert summary["degraded"] == "dir-fsync-failed"
    assert read_telemetry(dep)["events_observed"] == 4  # present, but not claimed durable


FLOOD_UIDS = """
import os, socket, sys
base, count, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
for uid in range(base, base + count):
    pid = os.fork()
    if pid == 0:
        try:
            os.setgroups([])
            os.setgid(uid)
            os.setuid(uid)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect(path)
            s.recv(1)
        finally:
            os._exit(0)
    os.waitpid(pid, 0)
print("flooded", count)
"""


def test_e08_listed_principals_keep_dedicated_counters_under_70_unlisted_uids(live):
    # The helper runs as root only to switch to 70 distinct real uids, one connection each.
    flood = subprocess.run(
        [sys.executable, "-c", FLOOD_UIDS, "62000", "70", str(live.sock)],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert flood.returncode == 0 and "flooded 70" in flood.stdout, flood.stderr
    hostile(live, REQUESTER_UID, "request", 5, payload={"op": "nope"})
    hostile(live, SECOND_PEER_UID, "bad-frame", 4)
    stop_owner(live)
    tel = read_telemetry(live)
    # The cap is exhausted by unlisted uids, yet listed principals keep exact counters.
    assert tel["counters"][str(REQUESTER_UID)] == {"REQUEST_REJECTED": 5}
    assert tel["counters"][str(SECOND_PEER_UID)] == {"FRAME_REJECTED": 4}
    assert tel["reserved_uids"] == sorted([REQUESTER_UID, SECOND_PEER_UID])
    assert len(tel["retained_uids"]) == tel["limits"]["max_uids"] == 64
    assert all(62000 <= uid < 62070 for uid in tel["retained_uids"])
    assert tel["counters"]["other"] == {"PEER_DENIED": 6}
    assert sum(row.get("PEER_DENIED", 0) for row in tel["counters"].values()) == 70
    assert tel["events_observed"] == 79


def test_e01_a_recorder_that_raises_never_stops_the_owner(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="telemetry-record-fails")
    hostile(dep, OTHER_UID, "connect", 10)
    bad = hostile(dep, REQUESTER_UID, "request", 10, payload={"op": "nope"}, keep=True)
    assert bad["replies"] == [{"ok": False, "error": "bad-request"}] * 10
    p = make_proposal()
    assert submit(dep, p, make_grant(dep.key, p))["reply"]["status"] == ATTEMPT_COMMITTED
    assert dep.proc is not None and dep.proc.poll() is None
    _took, summary = stop_owner(dep)
    assert summary["record_errors"] == "20" and summary["events_observed"] == "0"


def test_e02_impersonation_leaves_the_victims_history_unchanged(live):
    _commit_as_agent_b(live, "victim-proposal-7q")
    before = outcome(live, "victim-proposal-7q", uid=SECOND_PEER_UID)["reply"]["outcome"]
    facts_before = facts(live, "victim-proposal-7q")
    forged = make_proposal(pid="victim-proposal-7q", key="beta", actor="agent-b",
                           value="evil-payload-7q")
    for _ in range(5):  # even holding a valid grant, uid 61002 cannot speak for agent-b
        reply = submit(live, forged, make_grant(live.key, forged))["reply"]
        assert reply == {"ok": False, "error": "actor-not-permitted"}
    after = outcome(live, "victim-proposal-7q", uid=SECOND_PEER_UID)["reply"]["outcome"]
    assert after == before
    assert facts(live, "victim-proposal-7q") == facts_before
    stop_owner(live)
    raw = telemetry_path(live).read_text()
    assert json.loads(raw)["counters"][str(REQUESTER_UID)] == {"ACTOR_DENIED": 5}
    assert "victim-proposal-7q" not in raw and "evil-payload-7q" not in raw


def test_e03_ten_thousand_hostile_events_stay_bounded_and_exactly_counted(live):
    hostile(live, OTHER_UID, "connect", 4000)
    hostile(live, REQUESTER_UID, "bad-frame", 3000)
    hostile(live, REQUESTER_UID, "request", 3000, payload={"op": "nope"})
    _took, summary = stop_owner(live)
    assert summary["events_observed"] == "10000" and summary["persist_failures"] == "0"
    tel = read_telemetry(live)
    assert tel["counters"][str(OTHER_UID)] == {"PEER_DENIED": 4000}
    assert tel["counters"][str(REQUESTER_UID)] == {"FRAME_REJECTED": 3000,
                                                   "REQUEST_REJECTED": 3000}
    assert tel["events_observed"] == 10000 and tel["saturated"] == []
    assert len(tel["recent"]) == tel["limits"]["max_recent"] == 256
    assert telemetry_path(live).stat().st_size < 64 * 1024


def test_e04_records_carry_the_kernel_uid_and_pid(live):
    unlisted = hostile(live, OTHER_UID, "connect", 3)
    listed = hostile(live, REQUESTER_UID, "request", 2,
                     payload={"op": "submit", "uid": 0, "pid": 1, "actor_id": "root"})
    stop_owner(live)
    recent = read_telemetry(live)["recent"]
    denied = [e for e in recent if e["class"] == "PEER_DENIED"]
    rejected = [e for e in recent if e["class"] == "REQUEST_REJECTED"]
    assert {(e["uid"], e["pid"]) for e in denied} == {(OTHER_UID, unlisted["pid"])}
    assert len(denied) == 3
    assert {(e["uid"], e["pid"]) for e in rejected} == {(REQUESTER_UID, listed["pid"])}
    assert len(rejected) == 2


def test_e05_hostile_metadata_never_reaches_the_record_or_the_filesystem(live):
    marker = "INJECT-7q"
    payloads = [
        {"op": "submit", "signed_grant": None, "proposal": {
            "proposal_id": marker + '\n{"class":"FORGED"}', "actor_id": "../../" + marker,
            "action": "WRITE_KEY", "policy_version": "p", "payload": {}}},
        {"op": marker + " " + "x" * 60_000},
        {"op": "outcome", "proposal_id": "../../../tmp/" + marker},
    ]
    for payload in payloads:
        hostile(live, REQUESTER_UID, "request", 1, payload=payload)
    hostile(live, REQUESTER_UID, "oversized", 3)
    stop_owner(live)
    raw = telemetry_path(live).read_text()
    tel = json.loads(raw)
    assert marker not in raw and "FORGED" not in raw
    assert tel["counters"][str(REQUESTER_UID)] == {"FRAME_REJECTED": 3, "REQUEST_REJECTED": 2}
    assert telemetry_path(live).stat().st_size < 64 * 1024
    expected = {"owner.db", "owner.db-wal", "owner.db-shm", TELEMETRY}
    assert set(os.listdir(live.data)) <= expected, os.listdir(live.data)
    assert not (Path("/tmp") / marker).exists()


def test_e06_no_requester_can_read_telemetry_or_learn_from_it(live):
    p = make_proposal()
    submit(live, p, make_grant(live.key, p))
    before = outcome(live, p)["reply"]
    asked = hostile(live, REQUESTER_UID, "request", 1, payload={"op": "telemetry"}, keep=True)
    stats = hostile(live, SECOND_PEER_UID, "request", 1, payload={"op": "stats"}, keep=True)
    assert asked["replies"] == stats["replies"] == [{"ok": False, "error": "bad-request"}]
    hostile(live, OTHER_UID, "connect", 300)
    hostile(live, REQUESTER_UID, "bad-frame", 200)
    assert outcome(live, p)["reply"] == before
    time.sleep(1.5)  # let the private file be written
    assert telemetry_path(live).exists()
    probe = (
        "import sys\ntry:\n    open(sys.argv[1]).read()\n    print('READ')\n"
        "except PermissionError:\n    print('DENIED')\n"
    )
    for uid in (REQUESTER_UID, SECOND_PEER_UID, OTHER_UID):
        done = live.run_as(uid, probe, str(telemetry_path(live)))
        assert done.stdout.strip() == "DENIED", (uid, done.stdout, done.stderr)


def test_e07_a_killed_owner_loses_at_most_the_unflushed_tail(dep):
    dep.start_owner()
    hostile(dep, OTHER_UID, "connect", 30)
    time.sleep(1.5)  # past the flush interval
    assert read_telemetry(dep)["events_observed"] == 30
    hostile(dep, OTHER_UID, "connect", 15)
    assert dep.proc is not None
    os.kill(dep.proc.pid, signal.SIGKILL)
    assert dep.wait_for_owner_exit() == -9
    survived = read_telemetry(dep)["events_observed"]  # the file is never torn
    assert 30 <= survived <= 45
    dep.start_owner()
    hostile(dep, OTHER_UID, "connect", 5)
    stop_owner(dep)
    tel = read_telemetry(dep)
    assert tel["carried_over"] is True and tel["events_observed"] == survived + 5


def test_e07_a_corrupt_telemetry_file_is_set_aside_and_counting_restarts(dep):
    dep.start_owner()
    hostile(dep, OTHER_UID, "connect", 3)
    stop_owner(dep)
    path = telemetry_path(dep)
    path.write_text("{garbage")
    os.chown(path, OWNER_UID, OWNER_UID)
    os.chmod(path, 0o600)
    dep.start_owner()
    hostile(dep, OTHER_UID, "connect", 2)
    stop_owner(dep)
    tel = read_telemetry(dep)
    assert tel["corrupt_recovered"] is True and tel["events_observed"] == 2
    assert (dep.data / f"{TELEMETRY}.corrupt").exists()


@pytest.mark.parametrize("problem", ["symlink", "foreign-owner"])
def test_e07_an_unsafe_telemetry_file_refuses_to_start(dep, problem):
    path = telemetry_path(dep)
    if problem == "symlink":
        os.symlink(dep.base / "elsewhere.json", path)
    else:
        path.write_text("{}")
        os.chown(path, REQUESTER_UID, REQUESTER_UID)
        os.chmod(path, 0o600)
    done = dep.refused_start()
    assert done.returncode == 2 and "telemetry" in done.stderr
