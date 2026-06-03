import concurrent.futures
import time

from triadic_controls.crypto.sqlite_replay import SQLiteReplayCache


def test_sqlite_cache_check_and_record_first_insert(tmp_path):
    cache = SQLiteReplayCache(tmp_path / "replay.db")
    replay_key = "key-first-insert"
    expires_at = time.time() + 3600

    assert cache.check_and_record(replay_key, expires_at) is True
    assert cache.seen(replay_key) is True


def test_sqlite_cache_duplicate_insert_detects_replay(tmp_path):
    cache = SQLiteReplayCache(tmp_path / "replay.db")
    replay_key = "key-duplicate"
    expires_at = time.time() + 3600

    assert cache.check_and_record(replay_key, expires_at) is True
    assert cache.check_and_record(replay_key, expires_at) is False


def test_sqlite_cache_prunes_expired_records(tmp_path):
    cache = SQLiteReplayCache(tmp_path / "replay.db")
    now = time.time()
    expired_key = "key-expired"
    future_key = "key-future"

    cache.record(expired_key, now - 100)
    cache.record(future_key, now + 100)

    assert cache.seen(expired_key, now=now) is False
    assert cache.seen(future_key, now=now) is True


def test_sqlite_cache_survives_object_restart(tmp_path):
    db_path = tmp_path / "replay.db"
    replay_key = "key-persistent"
    expires_at = time.time() + 3600

    cache_1 = SQLiteReplayCache(db_path)
    assert cache_1.check_and_record(replay_key, expires_at) is True

    cache_2 = SQLiteReplayCache(db_path)
    assert cache_2.check_and_record(replay_key, expires_at) is False
    assert cache_2.seen(replay_key) is True


def test_sqlite_cache_concurrent_check_and_record_is_atomic(tmp_path):
    db_path = tmp_path / "concurrent_replay.db"
    cache = SQLiteReplayCache(db_path)
    replay_key = "highly-contested-concurrent-nonce-001"
    expires_at = time.time() + 3600
    max_workers = 32

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(cache.check_and_record, replay_key, expires_at)
            for _ in range(max_workers)
        ]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    assert results.count(True) == 1
    assert results.count(False) == max_workers - 1
