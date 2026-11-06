import multiprocessing
import sqlite3
import time

import pytest

from triadic_controls.crypto.sqlite_replay import SQLiteReplayCache


def _contend(path, barrier, queue):
    cache = SQLiteReplayCache(path, create=False)
    barrier.wait(timeout=15)
    queue.put(cache.check_and_record("one-nonce", time.time() + 3600))


def test_fresh_processes_admit_exactly_once(tmp_path):
    path = tmp_path / "replay.db"
    SQLiteReplayCache(path)
    ctx = multiprocessing.get_context("spawn")
    barrier, queue = ctx.Barrier(8), ctx.Queue()
    children = [ctx.Process(target=_contend, args=(path, barrier, queue)) for _ in range(8)]
    try:
        for child in children:
            child.start()
        results = [queue.get(timeout=20) for _ in children]
        for child in children:
            child.join(timeout=5)
            assert child.exitcode == 0
        assert results.count(True) == 1 and results.count(False) == 7
        assert SQLiteReplayCache(path, create=False).seen("one-nonce")
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
            child.join()
        queue.close()


def test_missing_runtime_state_is_not_recreated(tmp_path):
    path = tmp_path / "replay.db"
    cache = SQLiteReplayCache(path)
    path.unlink()
    with pytest.raises(sqlite3.DatabaseError):
        cache.check_and_record("nonce", time.time() + 100)
    assert not path.exists()


def test_strict_startup_refuses_missing_and_zero_byte_state(tmp_path):
    path = tmp_path / "replay.db"
    with pytest.raises(sqlite3.DatabaseError):
        SQLiteReplayCache(path, create=False)
    assert not path.exists()
    path.write_bytes(b"")
    with pytest.raises(sqlite3.DatabaseError):
        SQLiteReplayCache(path, create=False)
    assert path.stat().st_size == 0


def test_retention_cannot_be_shortened_and_bad_clock_is_rejected(tmp_path):
    cache = SQLiteReplayCache(tmp_path / "replay.db")
    cache.record("nonce", 100)
    cache.record("nonce", 1)
    assert cache.seen("nonce", now=50)
    assert not cache.check_and_record("expired", expires_at=9, now=10)
    for invalid in (float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            cache.check_and_record("bad", expires_at=100, now=invalid)
