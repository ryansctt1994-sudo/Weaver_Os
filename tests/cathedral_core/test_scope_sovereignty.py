from datetime import datetime, timedelta, timezone

from cathedral_core.lumen.scope_sovereignty import within_scope


def future_expiry():
    return datetime.now(timezone.utc) + timedelta(minutes=5)


def past_expiry():
    return datetime.now(timezone.utc) - timedelta(minutes=5)


def test_scope_requires_actor():
    decision = within_scope("", "execute", "target", future_expiry())

    assert decision.allowed is False
    assert decision.reason == "missing_actor"


def test_scope_requires_action():
    decision = within_scope("actor", "", "target", future_expiry())

    assert decision.allowed is False
    assert decision.reason == "missing_action"


def test_scope_requires_target():
    decision = within_scope("actor", "execute", "", future_expiry())

    assert decision.allowed is False
    assert decision.reason == "missing_target"


def test_scope_requires_expiry():
    decision = within_scope("actor", "execute", "target", None)

    assert decision.allowed is False
    assert decision.reason == "missing_expiry"


def test_scope_rejects_expired_authority():
    decision = within_scope("actor", "execute", "target", past_expiry())

    assert decision.allowed is False
    assert decision.reason == "expired_scope"


def test_scope_accepts_bounded_future_authority():
    decision = within_scope("actor", "execute", "target", future_expiry())

    assert decision.allowed is True
    assert decision.reason == "within_scope"
