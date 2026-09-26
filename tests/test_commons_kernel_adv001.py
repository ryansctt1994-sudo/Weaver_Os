from datetime import datetime, timedelta, timezone

import pytest

from commons_kernel import CommonsKernel, Grant, Proposal


NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def kernel_with_grant() -> CommonsKernel:
    k = CommonsKernel({"local_policy": "v1", "routing": "local"})
    k.add_grant(
        Grant(
            grant_id="G-LOCAL-001",
            subject="local-steward",
            actions=frozenset({"set"}),
            targets=frozenset({"local_policy"}),
            expires_at=NOW + timedelta(hours=1),
        )
    )
    return k


def assert_rejected_without_mutation(k: CommonsKernel, p: Proposal) -> None:
    state_before = k.protected_state
    hash_before = k.state_hash()
    d = k.decide(p, NOW)
    assert d.verdict == "REJECT"
    assert d.reason == "NO_ACTIVE_GRANT"
    assert d.before_hash == d.after_hash == hash_before
    assert k.protected_state == state_before


def test_authorized_narrow_grant_accepts() -> None:
    k = kernel_with_grant()
    d = k.decide(
        Proposal("local-steward", "set", "local_policy", {"value": "v2"}),
        NOW,
    )
    assert d.verdict == "ACCEPT"
    assert d.grant_id == "G-LOCAL-001"
    assert k.protected_state["local_policy"] == "v2"


@pytest.mark.parametrize(
    ("actor", "basis"),
    [
        ("federation", "larger_group"),
        ("router", "routing_control"),
        ("coordinator", "coordination_role"),
        ("delegate", "delegated_beyond_scope"),
        ("fork", "copy_inheritance"),
        ("infra-admin", "infrastructure_control"),
        ("popular-steward", "reputation"),
    ],
)
def test_structural_power_never_implies_authority(actor: str, basis: str) -> None:
    k = kernel_with_grant()
    assert_rejected_without_mutation(
        k,
        Proposal(actor, "set", "local_policy", {"value": "captured"}, basis),
    )


def test_grant_cannot_expand_target_scope() -> None:
    k = kernel_with_grant()
    assert_rejected_without_mutation(
        k,
        Proposal("local-steward", "set", "routing", {"value": "centralized"}),
    )


def test_expired_grant_rejects_without_mutation() -> None:
    k = CommonsKernel({"local_policy": "v1"})
    k.add_grant(
        Grant(
            "G-EXPIRED",
            "steward",
            frozenset({"set"}),
            frozenset({"local_policy"}),
            expires_at=NOW - timedelta(seconds=1),
        )
    )
    assert_rejected_without_mutation(
        k, Proposal("steward", "set", "local_policy", {"value": "v2"})
    )


def test_revoked_grant_rejects_without_mutation() -> None:
    k = CommonsKernel({"local_policy": "v1"})
    k.add_grant(
        Grant(
            "G-REVOKED",
            "steward",
            frozenset({"set"}),
            frozenset({"local_policy"}),
            revoked=True,
        )
    )
    assert_rejected_without_mutation(
        k, Proposal("steward", "set", "local_policy", {"value": "v2"})
    )


def test_dissolved_cell_has_no_inherited_authority() -> None:
    k = CommonsKernel({"local_policy": "v1"})
    assert_rejected_without_mutation(
        k,
        Proposal("successor-cell", "set", "local_policy", {"value": "v2"}, "predecessor_history"),
    )
