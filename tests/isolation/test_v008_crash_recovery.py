"""V008 crash-recovery slice: two-process fault injection with real process termination.

Every fault here is a real process death: the owner or the requester is killed with SIGKILL
at a chosen point, then a fresh process asks what happened. Nothing is simulated with an
exception. Facts about the ledger are read straight from SQLite by the owner uid.

Acceptance criteria exercised:
* exactly one committed effect for repeated submissions of the same proposal;
* the same receipt (same receipt_digest) across retries and owner restarts;
* a lost reply is reported as unknown (OutcomeUnknown / UNKNOWN), never as committed or
  refused, and a commit of different content under the same id is CONFLICT, never a commit;
* V008's uid isolation and socket authentication are unchanged (same harness, same owner).

Same root requirement and skip/fail rule as test_v008_isolated_owner.py. Same operator, one
host: this is local crash-recovery evidence, not independent validation.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from test_v008_isolated_owner import (
    OWNER_UID,
    REQUESTER_UID,
    SECOND_PEER_UID,
    SUBMIT,
    Deployment,
    make_grant,
    make_proposal,
)
from weaver_runtime.gate import ABORTED as ATTEMPT_ABORTED
from weaver_runtime.gate import COMMITTED as ATTEMPT_COMMITTED
from weaver_runtime.owner_outcome import proposal_digest

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED and /proc"
)

LEDGER_FACTS = """
import json, sqlite3, sys
db, pid = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
one = lambda sql, *args: conn.execute(sql, args).fetchone()[0]
print(json.dumps({
    "rows": dict(conn.execute("SELECT key, value FROM protected_kv")),
    "commit_keys": one("SELECT COUNT(*) FROM unique_keys WHERE key = ?",
                       "EXECUTION_COMMITTED:" + pid),
    "authority": one("SELECT COUNT(*) FROM entries WHERE root = 'AUTHORITY'"),
    "rejection": one("SELECT COUNT(*) FROM entries WHERE root = 'REJECTION'"),
}))
"""

REPLAY = """
import json, sqlite3, sys
from weaver_runtime.ledger import ReceiptLedger
from weaver_verifier.protected_write import verify_protected_write
data = json.loads(sys.argv[1])
with ReceiptLedger(data["path"], ledger_id="weaver-vertical-001") as ledger:
    snapshot = ledger.snapshot()
with sqlite3.connect(data["path"]) as conn:
    rows = dict(conn.execute("SELECT key, value FROM protected_kv"))
result = verify_protected_write(snapshot, rows, anchor=data["anchor"])
print("PASS" if result.ok and result.anchored else result.reason)
"""

SEND_THEN_DIE = """
import json, os, signal, socket, sys
from weaver_runtime.owner_ipc import encode_frame, peer_credentials
req = json.loads(sys.argv[1])
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(req["socket"])
assert peer_credentials(sock).uid == req["owner_uid"]
frame = encode_frame(req["request"])
sock.sendall(frame[: len(frame) // 2] if req["partial"] else frame)
os.kill(os.getpid(), signal.SIGKILL)  # die without reading any reply
"""


HOLD_WRITE_LOCK = """
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], isolation_level=None, timeout=10)
conn.execute("BEGIN IMMEDIATE")
print("LOCKED", flush=True)
sys.stdin.readline()  # hold the write lock until the test says release
conn.execute("ROLLBACK")
"""

SEND_AND_REPORT = """
import json, socket, sys
from weaver_runtime.owner_ipc import encode_frame, peer_credentials, recv_frame
req = json.loads(sys.argv[1])
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(30)
sock.connect(req["socket"])
assert peer_credentials(sock).uid == req["owner_uid"]
sock.sendall(encode_frame(req["request"]))
print("SENT", flush=True)
print(json.dumps(recv_frame(sock)), flush=True)
"""


def popen_as(dep, uid: int, code: str, *args: str, stdin=subprocess.DEVNULL):
    return subprocess.Popen(
        [sys.executable, "-c", code, *args], user=uid, group=uid, extra_groups=[],
        env=dep.env(), cwd="/", stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )


def second_owner(dep) -> Path:
    """Start owner B on the same store, serving its own socket; return that socket."""
    sock_b = dep.run / "owner-b.sock"
    config_b = dep.conf / "owner-b.json"
    Deployment.write_config_file(config_b, dict(dep.config, socket_path=str(sock_b)))
    dep.start_extra_owner(config_b)
    return sock_b


def enable_test_failpoints(dep) -> None:
    dep.config["test_failpoints"] = True
    dep.write_config()


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


def facts(dep, proposal_id: str) -> dict:
    done = dep.run_as(OWNER_UID, LEDGER_FACTS, str(dep.data / "owner.db"), proposal_id)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def submit(dep, proposal, signed_grant, uid=REQUESTER_UID, **kwargs) -> dict:
    return dep.submit(uid, proposal, signed_grant, **kwargs)


def outcome(dep, proposal, uid=REQUESTER_UID, **kwargs) -> dict:
    target = proposal if isinstance(proposal, str) else proposal.to_dict()
    return dep.call(uid, "outcome", target, **kwargs)


def replays(dep, anchor) -> bool:
    payload = json.dumps({"path": str(dep.data / "owner.db"), "anchor": anchor})
    done = dep.run_as(OWNER_UID, REPLAY, payload)
    return done.stdout.strip() == "PASS"


def send_then_die(dep, request, *, partial: bool) -> int:
    payload = json.dumps(
        {"socket": str(dep.sock), "owner_uid": OWNER_UID, "request": request, "partial": partial}
    )
    return dep.run_as(REQUESTER_UID, SEND_THEN_DIE, payload).returncode


def assert_single_commit(dep, proposal_id: str, rows: dict) -> None:
    found = facts(dep, proposal_id)
    assert found["commit_keys"] == 1 and found["authority"] == 1, found
    assert found["rows"] == rows


def test_outcome_of_a_proposal_never_sent_is_unknown_not_refused(live):
    reply = outcome(live, "never-sent")["reply"]
    assert reply["ok"]
    assert (reply["outcome"]["status"], reply["outcome"]["final"]) == ("UNKNOWN", False)
    assert reply["outcome"]["receipt"] is None


def test_retry_after_commit_returns_the_original_receipt_and_no_second_effect(live):
    p = make_proposal()
    signed = make_grant(live.key, p)
    first = submit(live, p, signed)["reply"]
    assert first["status"] == ATTEMPT_COMMITTED
    receipt = first["receipt"]["receipt_digest"]
    assert first["outcome"]["receipt"]["receipt_digest"] == receipt
    for _ in range(3):
        again = submit(live, p, signed)["reply"]
        assert again["status"] != ATTEMPT_COMMITTED  # V009: refused and chronicled
        assert again["outcome"]["status"] == "COMMITTED"
        assert again["outcome"]["receipt"]["receipt_digest"] == receipt
    assert outcome(live, p)["reply"]["outcome"]["receipt"]["receipt_digest"] == receipt
    assert_single_commit(live, "p1", {"alpha": "one"})
    assert facts(live, "p1")["rejection"] == 3


def test_refused_attempt_is_reported_as_not_final_and_a_later_commit_wins(live):
    p = make_proposal()
    refused = submit(live, p, None)["reply"]
    assert refused["status"] != ATTEMPT_COMMITTED
    assert (refused["outcome"]["status"], refused["outcome"]["final"]) == ("REFUSED", False)
    committed = submit(live, p, make_grant(live.key, p))["reply"]
    assert committed["status"] == ATTEMPT_COMMITTED
    assert committed["outcome"]["status"] == "COMMITTED"
    assert committed["outcome"]["refused_attempts"] == 1


def test_same_id_with_different_content_is_a_conflict_never_a_commit(live):
    original = make_proposal(value="one")
    submit(live, original, make_grant(live.key, original))
    replacement = make_proposal(value="two")
    reply = submit(live, replacement, make_grant(live.key, replacement))["reply"]
    assert reply["status"] != ATTEMPT_COMMITTED
    assert reply["outcome"]["status"] == "CONFLICT" and reply["outcome"]["receipt"] is None
    assert outcome(live, replacement)["reply"]["outcome"]["status"] == "CONFLICT"
    assert outcome(live, original)["reply"]["outcome"]["status"] == "COMMITTED"
    assert_single_commit(live, "p1", {"alpha": "one"})


def _commit_as_agent_b(dep, pid="pb"):
    theirs = make_proposal(pid=pid, key="beta", actor="agent-b")
    reply = submit(dep, theirs, make_grant(dep.key, theirs), uid=SECOND_PEER_UID)["reply"]
    assert reply["status"] == ATTEMPT_COMMITTED
    return theirs


def test_another_actors_records_are_invisible_to_outcome_queries(live):
    _commit_as_agent_b(live)
    reply = outcome(live, "pb")["reply"]  # asked by the agent-a peer, by id only
    assert reply["ok"], reply
    assert (reply["outcome"]["status"], reply["outcome"]["receipt"]) == ("UNKNOWN", None)
    assert outcome(live, "pb", uid=SECOND_PEER_UID)["reply"]["outcome"]["status"] == "COMMITTED"


def test_another_actors_later_refusal_neither_leaks_nor_hides_your_own_record(live):
    mine = make_proposal(pid="px", key="beta", actor="agent-b")
    submit(live, mine, None, uid=SECOND_PEER_UID)  # refused: no grant
    intruder = make_proposal(pid="px")  # agent-a reuses the id, also refused
    first = submit(live, intruder, None)["reply"]
    assert first["outcome"]["refused_attempts"] == 1, "counts only agent-a's own attempts"
    own = outcome(live, "px", uid=SECOND_PEER_UID)["reply"]
    assert own["ok"], own
    assert (own["outcome"]["status"], own["outcome"]["refused_attempts"]) == ("REFUSED", 1)
    assert own["outcome"]["proposal_sha256"] == proposal_digest(mine.to_dict())


def test_a_probe_without_a_grant_cannot_learn_that_another_actor_committed_an_id(live):
    _commit_as_agent_b(live)
    probe = make_proposal(pid="pb")  # agent-a, no grant
    reply = submit(live, probe, None)["reply"]
    assert reply["reason_code"] != "ALREADY_COMMITTED"  # the gate authorises first
    assert reply["outcome"]["status"] == "REFUSED", reply["outcome"]
    assert outcome(live, "pb")["reply"]["outcome"]["status"] == "REFUSED"


def test_an_authorised_attempt_on_an_id_another_actor_committed_is_a_final_conflict(live):
    _commit_as_agent_b(live)
    mine = make_proposal(pid="pb")  # agent-a holds a valid grant for its own content
    reply = submit(live, mine, make_grant(live.key, mine))["reply"]
    assert reply["reason_code"] == "ALREADY_COMMITTED"  # disclosed by the gate, as in #125
    assert (reply["outcome"]["status"], reply["outcome"]["final"]) == ("CONFLICT", True)
    assert reply["outcome"]["receipt"] is None
    assert outcome(live, mine)["reply"]["outcome"]["status"] == "CONFLICT"
    assert_single_commit(live, "pb", {"beta": "one"})


def test_owner_killed_inside_the_commit_transaction_leaves_no_effect(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="inside-commit-transaction")
    p = make_proposal()
    signed = make_grant(dep.key, p)
    assert submit(dep, p, signed)["error"] == "OutcomeUnknown"
    assert dep.wait_for_owner_exit() == -9
    # While no owner is serving, nothing is delivered and nothing is claimed.
    assert submit(dep, p, signed)["error"] == "OwnerUnavailable"
    dep.start_owner()
    found = outcome(dep, p)["reply"]["outcome"]
    assert (found["status"], found["receipt"]) == ("UNKNOWN", None)
    assert facts(dep, "p1") == {"rows": {}, "commit_keys": 0, "authority": 0, "rejection": 0}
    retried = submit(dep, p, signed)["reply"]
    assert retried["status"] == ATTEMPT_COMMITTED
    receipt = retried["receipt"]["receipt_digest"]
    again = submit(dep, p, signed)["reply"]
    assert again["outcome"]["receipt"]["receipt_digest"] == receipt
    assert_single_commit(dep, "p1", {"alpha": "one"})
    assert replays(dep, dep.call(REQUESTER_UID, "anchor")["reply"]["anchor"])


def test_owner_killed_after_commit_before_reply_keeps_one_effect_and_its_receipt(dep):
    enable_test_failpoints(dep)
    dep.start_owner(failpoint="after-commit-before-reply")
    p = make_proposal()
    signed = make_grant(dep.key, p)
    assert submit(dep, p, signed)["error"] == "OutcomeUnknown"
    assert dep.wait_for_owner_exit() == -9
    dep.start_owner()
    found = outcome(dep, p)["reply"]["outcome"]
    assert (found["status"], found["final"]) == ("COMMITTED", True)
    receipt = found["receipt"]["receipt_digest"]
    retried = submit(dep, p, signed)["reply"]
    assert retried["status"] != ATTEMPT_COMMITTED  # V012: a lost ack is no licence to replay
    assert retried["outcome"]["receipt"]["receipt_digest"] == receipt
    dep.stop()
    dep.start_owner()  # and once more across a clean restart
    assert outcome(dep, p)["reply"]["outcome"]["receipt"]["receipt_digest"] == receipt
    assert_single_commit(dep, "p1", {"alpha": "one"})
    assert replays(dep, dep.call(REQUESTER_UID, "anchor")["reply"]["anchor"])


def test_requester_killed_after_sending_loses_only_the_acknowledgement(live):
    p = make_proposal()
    signed = make_grant(live.key, p)
    request = {"op": "submit", "proposal": p.to_dict(), "signed_grant": signed}
    assert send_then_die(live, request, partial=False) == -9
    found = outcome(live, p)["reply"]["outcome"]
    assert found["status"] == "COMMITTED"
    receipt = found["receipt"]["receipt_digest"]
    retried = submit(live, p, signed)["reply"]
    assert retried["outcome"]["receipt"]["receipt_digest"] == receipt
    assert_single_commit(live, "p1", {"alpha": "one"})
    assert live.proc.poll() is None


def test_requester_killed_mid_frame_has_no_effect_and_the_owner_keeps_serving(live):
    p = make_proposal()
    request = {"op": "submit", "proposal": p.to_dict(), "signed_grant": make_grant(live.key, p)}
    assert send_then_die(live, request, partial=True) == -9
    assert outcome(live, p)["reply"]["outcome"]["status"] == "UNKNOWN"
    assert facts(live, "p1") == {"rows": {}, "commit_keys": 0, "authority": 0, "rejection": 0}
    assert submit(live, p, make_grant(live.key, p))["reply"]["status"] == ATTEMPT_COMMITTED
    assert live.proc.poll() is None


def test_concurrent_identical_submissions_from_two_processes_commit_once(live):
    p = make_proposal()
    signed = make_grant(live.key, p)
    request = json.dumps(
        {"socket": str(live.sock), "owner_uid": OWNER_UID, "op": "submit",
         "args": [p.to_dict(), signed], "verify_path": True}
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", SUBMIT, request], user=REQUESTER_UID, group=REQUESTER_UID,
            extra_groups=[], env=live.env(), cwd="/", stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for _ in range(2)
    ]
    replies = [json.loads(proc.communicate(timeout=30)[0])["reply"] for proc in procs]
    assert sorted(r["status"] == ATTEMPT_COMMITTED for r in replies) == [False, True]
    digests = {r["outcome"]["receipt"]["receipt_digest"] for r in replies}
    assert len(digests) == 1
    assert_single_commit(live, "p1", {"alpha": "one"})


def test_a_true_race_between_two_owners_is_settled_by_the_ledger_unique_key(live):
    """Both owners pass every in-memory check before either commits; the ledger decides."""
    sock_b = second_owner(live)
    p = make_proposal()
    request = {"op": "submit", "proposal": p.to_dict(), "signed_grant": make_grant(live.key, p)}
    holder = popen_as(
        live, OWNER_UID, HOLD_WRITE_LOCK, str(live.data / "owner.db"), stdin=subprocess.PIPE
    )
    assert holder.stdout is not None and holder.stdin is not None
    assert holder.stdout.readline().strip() == "LOCKED"
    racers = [
        popen_as(live, REQUESTER_UID, SEND_AND_REPORT, json.dumps(
            {"socket": str(sock), "owner_uid": OWNER_UID, "request": request}
        ))
        for sock in (live.sock, sock_b)
    ]
    for racer in racers:
        assert racer.stdout is not None
        assert racer.stdout.readline().strip() == "SENT"
    time.sleep(1.0)  # both owners are now authorised and parked at BEGIN IMMEDIATE
    holder.stdin.write("release\n")
    holder.stdin.flush()
    holder.communicate(timeout=10)
    replies = [json.loads(racer.communicate(timeout=30)[0]) for racer in racers]
    winners = [r for r in replies if r["status"] == ATTEMPT_COMMITTED]
    losers = [r for r in replies if r["status"] != ATTEMPT_COMMITTED]
    assert len(winners) == 1 and len(losers) == 1, replies
    # ABORTED at COMMIT (not REJECTED at RESERVE): the unique key stopped it, inside the
    # transaction, after its effect was written and then rolled back.
    assert (losers[0]["status"], losers[0]["reason_code"]) == (ATTEMPT_ABORTED, "ALREADY_COMMITTED")
    receipt = winners[0]["receipt"]["receipt_digest"]
    assert {r["outcome"]["receipt"]["receipt_digest"] for r in replies} == {receipt}
    assert_single_commit(live, "p1", {"alpha": "one"})


def test_unknown_while_the_original_is_still_queued_then_both_execute_once(live):
    """UNKNOWN is a statement about durable history now, not about requests in flight."""
    sock_b = second_owner(live)
    p = make_proposal()
    signed = make_grant(live.key, p)
    assert live.proc is not None
    os.kill(live.proc.pid, signal.SIGSTOP)  # owner A hangs; its queue keeps filling
    try:
        original = submit(live, p, signed, timeout=1)
        assert original["error"] == "OutcomeUnknown"  # delivered to A, no reply
        seen = outcome(live, p, socket_path=sock_b)["reply"]["outcome"]
        assert seen["status"] == "UNKNOWN"  # true of durable history at this moment
        retried = submit(live, p, signed, socket_path=sock_b)["reply"]
        assert retried["status"] == ATTEMPT_COMMITTED
    finally:
        os.kill(live.proc.pid, signal.SIGCONT)
    receipt = retried["receipt"]["receipt_digest"]
    # A resumes, executes the queued original (refused, no second effect), then answers.
    late = outcome(live, p, timeout=20)["reply"]["outcome"]
    assert (late["status"], late["receipt"]["receipt_digest"]) == ("COMMITTED", receipt)
    found = facts(live, "p1")
    assert (found["commit_keys"], found["authority"], found["rejection"]) == (1, 1, 1), found
    assert found["rows"] == {"alpha": "one"}


def test_clean_restart_keeps_receipt_identity_and_history_replays(live):
    p = make_proposal()
    first = submit(live, p, make_grant(live.key, p))["reply"]
    anchor = live.call(REQUESTER_UID, "anchor")["reply"]["anchor"]
    live.stop()
    live.start_owner()
    found = outcome(live, p)["reply"]["outcome"]
    assert found["receipt"] == first["outcome"]["receipt"]
    assert replays(live, anchor)


def test_unknown_failpoint_refuses_to_start(dep):
    enable_test_failpoints(dep)
    done = dep.refused_start(failpoint="crash-somewhere-else")
    assert done.returncode == 2 and "unknown failpoint" in done.stderr


def test_a_failpoint_cannot_be_armed_unless_the_owner_config_opts_in(dep):
    done = dep.refused_start(failpoint="after-commit-before-reply")
    assert done.returncode == 2 and "does not enable test_failpoints" in done.stderr
    dep.config["test_failpoints"] = "yes"
    dep.write_config()
    done = dep.refused_start(failpoint="after-commit-before-reply")
    assert done.returncode == 2 and "must be true or false" in done.stderr
