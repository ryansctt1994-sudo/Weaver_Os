"""Compatibility shim. SQLiteReplayCache moved to ``weaver_runtime.replay_cache`` (step 4)."""

from weaver_contracts.replay import ReplayCacheProtocol
from weaver_runtime.replay_cache import SQLiteReplayCache

__all__ = ["ReplayCacheProtocol", "SQLiteReplayCache"]
