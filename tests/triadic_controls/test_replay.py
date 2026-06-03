import time

from triadic_controls.crypto.replay import InMemoryReplayCache, generate_replay_key


def test_generate_replay_key_determinism():
    key1 = generate_replay_key("iss1", "key1", "nonceA", "TOKEN", "sys1", "hash1")
    key2 = generate_replay_key("iss1", "key1", "nonceA", "TOKEN", "sys1", "hash1")
    assert key1 == key2

    key3 = generate_replay_key("iss1", "key1", "nonceB", "TOKEN", "sys1", "hash1")
    assert key1 != key3


def test_in_memory_cache_check_and_record():
    cache = InMemoryReplayCache()
    replay_key = "test_hash_string"
    expiry = time.time() + 3600

    assert cache.check_and_record(replay_key, expiry) is True
    assert cache.check_and_record(replay_key, expiry) is False


def test_in_memory_cache_opportunistic_pruning():
    cache = InMemoryReplayCache()
    replay_key = "test_hash_string"

    now = time.time()
    past_expiry = now - 100
    future_expiry = now + 100

    cache.record(replay_key, past_expiry)
    assert cache.seen(replay_key, now=now) is False

    cache.record("future_key", future_expiry)
    assert cache.seen("future_key", now=now) is True
