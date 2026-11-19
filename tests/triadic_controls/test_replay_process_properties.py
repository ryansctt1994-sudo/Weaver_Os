"""Replay uniqueness across independent processes and generated operation traces."""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

from hypothesis import given, settings
from hypothesis import strategies as st
from weaver_runtime.replay_cache import SQLiteReplayCache


def _claim(path, barrier):
    cache = SQLiteReplayCache(path)
    barrier.wait(timeout=20)
    return cache.check_and_record("contested", expires_at=2000, now=1000)


def test_processes_admit_exactly_one_claim(tmp_path):
    path = str(tmp_path / "replay.sqlite")
    # Include concurrent initializers, not just concurrent inserts.
    ctx = mp.get_context("spawn")
    with ctx.Manager() as manager:
        barrier = manager.Barrier(8)
        with ProcessPoolExecutor(8, mp_context=ctx) as pool:
            jobs = [pool.submit(_claim, path, barrier) for _ in range(8)]
            results = [job.result(timeout=60) for job in jobs]
    assert results.count(True) == 1
    assert results.count(False) == 7
    assert not SQLiteReplayCache(path).check_and_record("contested", 2000, now=1000)


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 8), st.integers(0, 10)), max_size=80))
def test_generated_replay_expiry_and_restart_trace(operations):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "replay.sqlite"
        model = {}
        now = 1000
        for key, advance in operations:
            now += advance
            model = {k: expiry for k, expiry in model.items() if expiry > now}
            expected = key not in model
            # A fresh instance for each operation exercises restart persistence.
            cache = SQLiteReplayCache(path)
            assert cache.check_and_record(str(key), now + 10, now=now) is expected
            if expected:
                model[key] = now + 10
            for candidate in range(9):
                assert cache.seen(str(candidate), now=now) is (candidate in model)
