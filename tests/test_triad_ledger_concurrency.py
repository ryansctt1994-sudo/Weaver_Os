"""Regression tests for the TriadLedger append race (C-RCPT-001).

Before the fix, ``append_event`` did an unlocked load, check, append. Two writers
that both loaded before either appended both passed the index/prev_hash check,
both appended event 0, and the ledger then failed to load.
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from triadic_controls.ledger import (
    GENESIS_PREV_HASH,
    LedgerChainError,
    TriadLedger,
    compute_event_hash,
)

REPO = Path(__file__).resolve().parents[1]
PUBLIC_KEY = "00" * 32  # unsigned events are allowed by the v1.0 schema


def make_event(index: int, prev_hash: str, actor: str) -> dict:
    event = {
        "index": index,
        "timestamp": "2026-11-07T10:00:00Z",
        "event_type": "proposal",
        "actor": actor,
        "public_key": PUBLIC_KEY,
        "payload": {"id": f"{actor}-{index}", "action": "update_config", "value": index},
        "prev_hash": prev_hash,
        "event_hash": "",
        "policy_version": "policy-v1",
    }
    event["event_hash"] = compute_event_hash(event)
    return event


def test_interleaved_writers_cannot_both_append(tmp_path, monkeypatch):
    """The exact interleaving that corrupted the ledger: both writers load before either writes."""
    path = tmp_path / "triad.jsonl"
    original_load = TriadLedger.load_events

    def slow_load(self):
        events = original_load(self)
        time.sleep(0.3)  # widen the load-to-write window
        return events

    monkeypatch.setattr(TriadLedger, "load_events", slow_load)
    start = threading.Barrier(2)
    outcomes: dict[str, str] = {}

    def writer(actor: str) -> None:
        start.wait()
        try:
            TriadLedger(path).append_event(make_event(0, GENESIS_PREV_HASH, actor))
            outcomes[actor] = "appended"
        except LedgerChainError as exc:
            outcomes[actor] = f"rejected: {exc}"

    threads = [threading.Thread(target=writer, args=(a,)) for a in ("writer-a", "writer-b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    monkeypatch.undo()

    assert sorted(o.split(":")[0] for o in outcomes.values()) == ["appended", "rejected"]
    assert any("index mismatch" in o for o in outcomes.values())
    events = TriadLedger(path).load_events()
    assert len(events) == 1


CHILD_WRITER = """
import sys
sys.path.insert(0, {repo!r})
from tests.test_triad_ledger_concurrency import make_event
from triadic_controls.ledger import GENESIS_PREV_HASH, LedgerChainError, TriadLedger
ledger = TriadLedger({path!r})
done = 0
while done < {n}:
    events = ledger.load_events()
    prev = events[-1]["event_hash"] if events else GENESIS_PREV_HASH
    try:
        ledger.append_event(make_event(len(events), prev, {actor!r}))
        done += 1
    except LedgerChainError:
        continue  # another writer won; re-read the head and retry
"""


def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO), str(REPO / "packages" / "contracts"), str(REPO / "packages" / "verifier")]
    )
    return env


def test_processes_serialize_and_the_ledger_stays_loadable(tmp_path):
    path = str(tmp_path / "triad.jsonl")
    procs = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                CHILD_WRITER.format(repo=str(REPO), path=path, n=10, actor=f"p{i}"),
            ],
            env=_env(),
        )
        for i in range(4)
    ]
    assert [p.wait(timeout=120) for p in procs] == [0, 0, 0, 0]
    events = TriadLedger(path).load_events()
    assert [e["index"] for e in events] == list(range(40))
    assert sorted({e["actor"] for e in events}) == ["p0", "p1", "p2", "p3"]


CHILD_CRASH = """
import os, sys
sys.path.insert(0, {repo!r})
from tests.test_triad_ledger_concurrency import make_event
from triadic_controls.ledger import GENESIS_PREV_HASH, TriadLedger
def die(self):
    os._exit(3)  # dies while holding the lock, before writing
TriadLedger.load_events = die
TriadLedger({path!r}).append_event(make_event(0, GENESIS_PREV_HASH, "crasher"))
"""


def test_writer_killed_while_holding_the_lock_does_not_block_others(tmp_path):
    path = str(tmp_path / "triad.jsonl")
    proc = subprocess.run(
        [sys.executable, "-c", CHILD_CRASH.format(repo=str(REPO), path=path)],
        env=_env(),
        timeout=60,
    )
    assert proc.returncode == 3
    finished = threading.Event()

    def append_after_crash() -> None:
        TriadLedger(path).append_event(make_event(0, GENESIS_PREV_HASH, "survivor"))
        finished.set()

    worker = threading.Thread(target=append_after_crash, daemon=True)
    worker.start()
    assert finished.wait(timeout=10), "append blocked after the lock holder died"
    assert [e["actor"] for e in TriadLedger(path).load_events()] == ["survivor"]
