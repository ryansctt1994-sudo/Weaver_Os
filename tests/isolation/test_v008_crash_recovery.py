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
import subprocess
import sys

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
from weaver_runtime.gate import COMMITTED as ATTEMPT_COMMITTED

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


def submit(dep, proposal, signed_grant, uid=REQUESTER_UID) -> dict:
    return dep.submit(uid, proposal, signed_grant)


def outcome(dep, proposal, uid=REQUESTER_UID) -> dict:
    target = proposal if isinstance(proposal, str) else proposal.to_dict()
    return dep.call(uid, "outcome", target)


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


def test_outcome_of_another_actors_proposal_is_not_disclosed(live):
    theirs = make_proposal(pid="pb", key="beta", actor="agent-b")
    reply = submit(live, theirs, make_grant(live.key, theirs), uid=SECOND_PEER_UID)["reply"]
    assert reply["status"] == ATTEMPT_COMMITTED
    assert outcome(live, "pb")["reply"] == {"ok": False, "error": "actor-not-permitted"}
    assert outcome(live, "pb", uid=SECOND_PEER_UID)["reply"]["outcome"]["status"] == "COMMITTED"


def test_owner_killed_inside_the_commit_transaction_leaves_no_effect(dep):
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
    done = dep.refused_start(failpoint="crash-somewhere-else")
    assert done.returncode == 2 and "unknown failpoint" in done.stderr
