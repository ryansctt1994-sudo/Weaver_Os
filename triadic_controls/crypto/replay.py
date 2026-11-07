"""Compatibility shim (outline step 4).

The protocol and key derivation moved to ``weaver_contracts.replay``; the in-memory
cache moved to ``weaver_runtime.replay_cache``.
"""

from weaver_contracts.replay import ReplayCacheProtocol, generate_replay_key
from weaver_runtime.replay_cache import InMemoryReplayCache

__all__ = ["InMemoryReplayCache", "ReplayCacheProtocol", "generate_replay_key"]
