"""WVR-009: an older, validly signed key registry must not undo a newer one.

Each test builds root-signed registries inside their validity window. Without a sequence
store, CryptoVerifier keeps no memory between instances, so a registry in which a key was
still ACTIVE verifies tokens signed by that key even after a newer registry revoked it
(``test_known_limit_without_a_sequence_store_rollback_still_verifies``).
"""

import copy
import threading

import pytest
from weaver_contracts.registry_sequence import (
    MAX_REGISTRY_SEQUENCE,
    REGISTRY_ROLLBACK,
    REGISTRY_SEQUENCE_CONFLICT,
)
from weaver_runtime.registry_sequence import (
    InMemoryRegistrySequenceStore,
    SQLiteRegistrySequenceStore,
)
from weaver_runtime.replay_cache import InMemoryReplayCache
from weaver_verifier.crypto import CryptoVerifier

from tests.triadic_controls.test_crypto_verifier import authority_payload, signed_envelope
from tests.triadic_controls.test_registry_root_signature import (
    generate_keypair,
    sign_registry,
    unsigned_registry,
)


@pytest.fixture()
def keys():
    root_sk, root_pk = generate_keypair()
    issuer_sk, issuer_pk = generate_keypair()
    return root_sk, root_pk, issuer_sk, issuer_pk


def registry_at(keys, sequence: int, *, status: str = "ACTIVE", note: str | None = None) -> dict:
    root_sk, _, _, issuer_pk = keys
    reg = unsigned_registry(issuer_pk)
    reg["registry_sequence"] = sequence
    reg["issuers"][0]["status"] = status
    reg["roles"][0]["allowed_scopes"].update(
        systems=["rover-7"], regions=["sector-7"], tasks=["navigate"],
        max_authority_duration_sec=7200,
    )
    if note is not None:
        reg["roles"][0]["description"] = note
    return sign_registry(reg, root_sk)


def verifier(keys, registry, store=None) -> CryptoVerifier:
    return CryptoVerifier(
        key_registry=registry,
        replay_cache=InMemoryReplayCache(),
        root_public_key_b64url=keys[1],
        registry_sequence_store=store,
    )


def token_verifies(keys, v: CryptoVerifier, nonce: str) -> bool:
    payload = authority_payload(level=3)
    envelope = signed_envelope(keys[2], nonce=nonce, inner_payload=payload)
    return v.verify_authority_token(envelope, requested_level=3, inner_payload=payload).is_valid


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryRegistrySequenceStore()
    return SQLiteRegistrySequenceStore(tmp_path / "registry-sequence.db")


# --- the attack ------------------------------------------------------------------


def test_known_limit_without_a_sequence_store_rollback_still_verifies(keys):
    """Characterization: callers that pass no store keep the old behaviour."""
    current = registry_at(keys, 2, status="REVOKED")
    old = registry_at(keys, 1, status="ACTIVE")
    assert not token_verifies(keys, verifier(keys, current), "n-1")
    assert token_verifies(keys, verifier(keys, old), "n-2")


def test_rollback_cannot_reactivate_a_revoked_key(keys, store):
    current = registry_at(keys, 2, status="REVOKED")
    old = registry_at(keys, 1, status="ACTIVE")
    assert not token_verifies(keys, verifier(keys, current, store), "n-1")
    with pytest.raises(ValueError, match=REGISTRY_ROLLBACK):
        verifier(keys, old, store)


# --- the mark -------------------------------------------------------------------


def test_forward_transition_is_accepted(keys, store):
    verifier(keys, registry_at(keys, 1), store)
    verifier(keys, registry_at(keys, 2), store)
    verifier(keys, registry_at(keys, 7), store)


def test_same_registry_reloaded_is_accepted(keys, store):
    reg = registry_at(keys, 3)
    verifier(keys, reg, store)
    verifier(keys, copy.deepcopy(reg), store)


def test_equal_sequence_with_different_content_is_refused(keys, store):
    verifier(keys, registry_at(keys, 3, note="first"), store)
    with pytest.raises(ValueError, match=REGISTRY_SEQUENCE_CONFLICT):
        verifier(keys, registry_at(keys, 3, note="second"), store)


def test_a_refusal_does_not_move_the_mark(keys, store):
    current = registry_at(keys, 5)
    verifier(keys, current, store)
    with pytest.raises(ValueError):
        verifier(keys, registry_at(keys, 4), store)
    verifier(keys, current, store)
    verifier(keys, registry_at(keys, 6), store)


def test_registries_with_different_ids_have_independent_marks(keys, store):
    verifier(keys, registry_at(keys, 9), store)
    other = unsigned_registry(keys[3])
    other["registry_id"] = "99999999-9999-4999-8999-999999999999"
    other["registry_sequence"] = 1
    verifier(keys, sign_registry(other, keys[0]), store)


# --- only authenticated registries move the mark ----------------------------------


def test_store_requires_a_root_key(keys, store):
    with pytest.raises(ValueError, match="requires a root-signed registry"):
        CryptoVerifier(
            key_registry=registry_at(keys, 1),
            replay_cache=InMemoryReplayCache(),
            registry_sequence_store=store,
        )


def test_tampered_high_sequence_registry_cannot_lock_out_the_real_one(keys, store):
    forged = registry_at(keys, 2)
    forged["registry_sequence"] = MAX_REGISTRY_SEQUENCE  # signature no longer matches
    with pytest.raises(ValueError, match="root signature"):
        verifier(keys, forged, store)
    verifier(keys, registry_at(keys, 2), store)


@pytest.mark.parametrize(
    "field, value",
    [
        ("registry_sequence", True),
        ("registry_sequence", "3"),
        ("registry_sequence", -1),
        ("registry_sequence", 3.0),
        ("registry_sequence", MAX_REGISTRY_SEQUENCE + 1),
        ("registry_sequence", None),
        ("registry_id", ""),
        ("registry_id", 7),
    ],
)
def test_malformed_identity_is_refused(keys, store, field, value):
    reg = unsigned_registry(keys[3])
    reg[field] = value
    with pytest.raises(ValueError, match="rollback protection"):
        verifier(keys, sign_registry(reg, keys[0]), store)


def test_caller_edits_after_construction_do_not_reach_the_verifier(keys, store):
    reg = registry_at(keys, 2, status="REVOKED")
    v = verifier(keys, reg, store)
    reg["issuers"][0]["status"] = "ACTIVE"  # caller's dict, after the checks ran
    assert not token_verifies(keys, v, "n-1")


# --- persistence and concurrency (SQLite) ------------------------------------------


def test_sqlite_mark_survives_restart(keys, tmp_path):
    path = tmp_path / "registry-sequence.db"
    verifier(keys, registry_at(keys, 4), SQLiteRegistrySequenceStore(path))
    with pytest.raises(ValueError, match=REGISTRY_ROLLBACK):
        verifier(keys, registry_at(keys, 3), SQLiteRegistrySequenceStore(path))


def test_conflicting_registries_racing_at_one_sequence_exactly_one_wins(keys, tmp_path):
    """Separate store instances, so separate SQLite connections, released together."""
    path = tmp_path / "registry-sequence.db"
    SQLiteRegistrySequenceStore(path)
    candidates = [registry_at(keys, 10, note=f"candidate-{i}") for i in range(8)]
    barrier = threading.Barrier(len(candidates))
    accepted: list[int] = []
    refused: list[str] = []
    lock = threading.Lock()

    def race(i: int) -> None:
        own_store = SQLiteRegistrySequenceStore(path)
        barrier.wait()
        try:
            verifier(keys, candidates[i], own_store)
            with lock:
                accepted.append(i)
        except ValueError as exc:
            with lock:
                refused.append(str(exc))

    threads = [threading.Thread(target=race, args=(i,)) for i in range(len(candidates))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(accepted) == 1
    assert len(refused) == len(candidates) - 1
    assert all(REGISTRY_SEQUENCE_CONFLICT in r for r in refused)
