"""Old import paths kept after outline step 4 must resolve to the moved objects themselves."""

import importlib

import pytest

OLD_CRYPTO = "triadic_controls.crypto.verifier"
NEW_CRYPTO = "weaver_verifier.crypto"

SHIMS = [
    (OLD_CRYPTO, NEW_CRYPTO, "CryptoVerifier"),
    (OLD_CRYPTO, NEW_CRYPTO, "canonicalize_json"),
    (OLD_CRYPTO, NEW_CRYPTO, "verify_registry_root_signature"),
    ("triadic_controls.crypto.replay", "weaver_contracts.replay", "ReplayCacheProtocol"),
    ("triadic_controls.crypto.replay", "weaver_contracts.replay", "generate_replay_key"),
    ("triadic_controls.crypto.replay", "weaver_runtime.replay_cache", "InMemoryReplayCache"),
    ("triadic_controls.crypto.sqlite_replay", "weaver_runtime.replay_cache", "SQLiteReplayCache"),
    ("triadic_controls.crypto", "weaver_verifier.crypto", "CryptoVerifier"),
    ("triadic_controls.crypto", "weaver_runtime.replay_cache", "SQLiteReplayCache"),
    ("policy.claim_transition", "weaver_verifier.claim_transition", "validate_transition"),
    ("policy.claim_transition", "weaver_verifier.claim_transition", "claim_state_hash"),
]


@pytest.mark.parametrize("old, new, name", SHIMS)
def test_shim_reexports_the_same_object(old, new, name):
    old_obj = getattr(importlib.import_module(old), name)
    assert old_obj is getattr(importlib.import_module(new), name)


def test_every_public_name_survives_the_move():
    shim = importlib.import_module(OLD_CRYPTO)
    moved = importlib.import_module(NEW_CRYPTO)
    public = {
        name
        for name, value in vars(moved).items()
        if not name.startswith("_") and getattr(value, "__module__", None) == moved.__name__
    }
    assert public <= set(shim.__all__)
