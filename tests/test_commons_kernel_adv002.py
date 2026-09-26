from datetime import datetime, timedelta, timezone

import pytest

from commons_kernel import CommonsKernel, Grant, MintBasis, Proposal


NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def root(*, expires=timedelta(hours=1), subject="founder", actions=None, targets=None):
    return Grant(
        "ROOT", "genesis", subject,
        frozenset(actions or {"mint", "set"}),
        frozenset(targets or {"local_policy"}),
        NOW - timedelta(minutes=1), NOW + expires,
        mint_basis=MintBasis.ROOT_BOOTSTRAP,
    )


def child(
    grant_id="CHILD", grantor="founder", subject="steward",
    actions=None, targets=None, expires=timedelta(minutes=30),
    basis=MintBasis.ATTENUATED_DELEGATION, parent="ROOT",
):
    return Grant(
        grant_id, grantor, subject,
        frozenset(actions or {"set"}),
        frozenset(targets or {"local_policy"}),
        NOW, NOW + expires, parent_grant_id=parent, mint_basis=basis,
    )


def assert_reject_immutable(k, decision, reason):
    assert decision.verdict == "REJECT"
    assert decision.reason == reason
    assert decision.before_hash == decision.after_hash
    assert decision.before_grant_hash == decision.after_grant_hash


def test_h01_old_add_grant_is_fail_closed():
    k = CommonsKernel({"local_policy": "v1"})
    d = k.add_grant(child())
    assert_reject_immutable(k, d, "NO_GRANT_PROVENANCE")
    assert k.decide(Proposal("steward", "set", "local_policy", {"value": "pwn"}), NOW).verdict == "REJECT"


def test_h02_actor_without_mint_cannot_self_mint():
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    d = k.propose_mint("coordinator", child(grantor="coordinator", subject="coordinator"), NOW)
    assert_reject_immutable(k, d, "ACTOR_CANNOT_MINT")


def test_h03_expired_bootstrap_cannot_mint_or_act():
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root(expires=timedelta(seconds=-1)))
    d = k.propose_mint("founder", child(), NOW)
    assert_reject_immutable(k, d, "BOOTSTRAP_EXPIRED")
    assert k.decide(Proposal("founder", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


@pytest.mark.parametrize("actor", ["coordinator", "infra-admin", "backup-holder", "replacement-engineer"])
def test_h04_h06_structural_roles_cannot_mint(actor):
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    d = k.propose_mint(actor, child(grantor=actor, subject=actor), NOW)
    assert_reject_immutable(k, d, "ACTOR_CANNOT_MINT")


@pytest.mark.parametrize(
    "bad",
    [
        child(actions={"set", "delete"}),
        child(targets={"local_policy", "routing"}),
        child(expires=timedelta(hours=2)),
    ],
)
def test_h07_delegation_must_attenuate(bad):
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    d = k.propose_mint("founder", bad, NOW)
    assert_reject_immutable(k, d, "DELEGATION_EXPANDS_AUTHORITY")


def test_h08_federation_is_born_without_inherited_grants():
    k = CommonsKernel({"local_policy": "v1"})
    assert k.decide(Proposal("federation", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


def test_h09_expired_emergency_grant_cannot_act():
    emergency = root(expires=timedelta(seconds=-1), subject="emergency-operator", actions={"set", "emergency"})
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=emergency)
    assert k.decide(Proposal("emergency-operator", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


def test_h10_emergency_cannot_mint_standing_grant():
    emergency = root(subject="emergency-operator", actions={"mint", "set", "emergency"})
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=emergency)
    standing = child(
        grantor="emergency-operator", subject="emergency-operator",
        basis=MintBasis.EXPLICIT_GRANT,
    )
    d = k.propose_mint("emergency-operator", standing, NOW)
    assert_reject_immutable(k, d, "EMERGENCY_CANNOT_MINT_STANDING")


def test_h11_fork_does_not_load_predecessor_grants():
    original = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    fork = CommonsKernel(original.protected_state)
    assert fork.decide(Proposal("founder", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


def test_h12_router_failover_does_not_gain_policy_authority():
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    assert k.decide(Proposal("router-failover", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


def test_h13_restore_does_not_revive_expired_founder():
    restored = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root(expires=timedelta(seconds=-1)))
    assert restored.decide(Proposal("founder", "set", "local_policy", {"value": "v2"}), NOW).verdict == "REJECT"


def test_h14_valid_attenuated_mint_accepts_then_exercises():
    k = CommonsKernel({"local_policy": "v1"}, bootstrap_grant=root())
    d = k.propose_mint("founder", child(), NOW)
    assert d.verdict == "ACCEPT"
    assert d.before_grant_hash != d.after_grant_hash
    use = k.decide(Proposal("steward", "set", "local_policy", {"value": "v2"}), NOW)
    assert use.verdict == "ACCEPT"
    assert k.protected_state["local_policy"] == "v2"


def test_h15_recovery_does_not_coronate_operator():
    live = child(grant_id="LIVE", grantor="founder", subject="steward")
    restored = CommonsKernel({"local_policy": "v1"})
    restored.unsafe_test_inject(live)  # simulates verified persisted live grant only
    assert restored.decide(Proposal("steward", "set", "local_policy", {"value": "v2"}), NOW).verdict == "ACCEPT"
    d = restored.propose_mint("restore-operator", child(grantor="restore-operator"), NOW)
    assert_reject_immutable(restored, d, "NO_GRANT_PROVENANCE")
