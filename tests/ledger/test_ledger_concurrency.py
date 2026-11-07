"""Concurrency and interrupted-transaction behaviour (ADR-0006 required evidence)."""

import sqlite3
import subprocess
import threading

import pytest
from weaver_runtime.ledger import LedgerBusy
from weaver_verifier.ledger import verify_snapshot

from tests.ledger.helpers import PYTHON, admit_n, child_env, open_ledger

THREADS = 8
PER_THREAD = 25


def test_threads_with_separate_instances_get_one_total_order(tmp_path):
    path = tmp_path / "ledger.db"
    open_ledger(path).close()
    results: list = []
    errors: list = []
    barrier = threading.Barrier(THREADS)

    def worker(worker_id):
        try:
            with open_ledger(path, busy_timeout_ms=30000) as ledger:
                barrier.wait()
                results.extend(admit_n(ledger, PER_THREAD, start=worker_id * 1000))
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    total = THREADS * PER_THREAD
    assert sorted(r.sequence for r in results) == list(range(total))
    with open_ledger(path) as ledger:
        snapshot = ledger.snapshot()
        assert verify_snapshot(snapshot, anchor=ledger.anchor().to_dict()).ok
    stored = {e["receipt"]["receipt_digest"] for e in snapshot["roots"]["AUTHORITY"]}
    assert stored == {r.receipt_digest for r in results}


def test_shared_instance_is_safe_across_threads(tmp_path):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        threads = [
            threading.Thread(target=admit_n, args=(ledger, 20), kwargs={"start": i * 100})
            for i in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert ledger.heads()["AUTHORITY"].length == 80
        assert verify_snapshot(ledger.snapshot()).ok


CHILD_APPEND = """
import sys
sys.path.insert(0, {tests!r})
from tests.ledger.helpers import admit_n, open_ledger
with open_ledger({path!r}, busy_timeout_ms=30000) as ledger:
    admit_n(ledger, {n}, start={start})
"""


def test_processes_get_one_total_order(tmp_path):
    path = str(tmp_path / "ledger.db")
    open_ledger(path).close()
    from tests.ledger.helpers import REPO

    procs = [
        subprocess.Popen(
            [PYTHON, "-c", CHILD_APPEND.format(tests=str(REPO), path=path, n=25, start=i * 1000)],
            env=child_env(),
        )
        for i in range(4)
    ]
    assert [p.wait(timeout=120) for p in procs] == [0, 0, 0, 0]
    with open_ledger(path) as ledger:
        snapshot = ledger.snapshot()
        entries = snapshot["roots"]["AUTHORITY"]
        assert [e["receipt"]["sequence"] for e in entries] == list(range(100))
        assert verify_snapshot(snapshot).ok


def test_busy_store_fails_explicitly_and_changes_nothing(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path, busy_timeout_ms=50) as ledger:
        admit_n(ledger, 2)
        before = ledger.anchor()
        holder = sqlite3.connect(path, isolation_level=None)
        holder.execute("BEGIN IMMEDIATE")
        try:
            with pytest.raises(LedgerBusy):
                admit_n(ledger, 1, start=2)
        finally:
            holder.execute("ROLLBACK")
            holder.close()
        assert ledger.anchor() == before
        assert admit_n(ledger, 1, start=2)[0].sequence == 2


CHILD_CRASH = """
import os, sys
sys.path.insert(0, {tests!r})
from tests.ledger.helpers import admit_n, open_ledger
ledger = open_ledger({path!r})
def crash(receipt):
    os._exit(3)  # process dies after the entry insert, before head update and COMMIT
ledger._advance_head = crash
admit_n(ledger, 1, start=99)
"""


def test_process_killed_mid_transaction_leaves_store_consistent(tmp_path):
    path = str(tmp_path / "ledger.db")
    with open_ledger(path) as ledger:
        admit_n(ledger, 3)
        before = ledger.snapshot()
    from tests.ledger.helpers import REPO

    proc = subprocess.run(
        [PYTHON, "-c", CHILD_CRASH.format(tests=str(REPO), path=path)],
        env=child_env(),
        timeout=60,
    )
    assert proc.returncode == 3
    with open_ledger(path) as ledger:
        assert ledger.snapshot() == before
        assert verify_snapshot(ledger.snapshot()).ok
        assert admit_n(ledger, 1, start=3)[0].sequence == 3
