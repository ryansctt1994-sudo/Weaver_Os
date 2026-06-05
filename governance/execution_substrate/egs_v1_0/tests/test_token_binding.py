from datetime import datetime, timezone

from governance.execution_substrate.egs_v1_0.specs.exec_token import TokenContext, validate


CTX = TokenContext(
    subject_user="researcher-001",
    institution="example-institution",
    project="approved-project",
    facility="facility-alpha",
    device_id="device-123",
    design_digest="sha256:" + "a" * 64,
    reagent_lot="lot-001",
    tier="T1",
    execution_environment="local",
)


def token():
    return {
        "token_id": "tok-12345678",
        "issuer": "egs-test-ca",
        "subject_user": CTX.subject_user,
        "institution": CTX.institution,
        "project": CTX.project,
        "facility": CTX.facility,
        "device_id": CTX.device_id,
        "design_digest": CTX.design_digest,
        "reagent_lot": CTX.reagent_lot,
        "scope": {
            "tier": CTX.tier,
            "max_batch_size": 1,
            "execution_environment": CTX.execution_environment,
        },
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2027-01-01T00:00:00Z",
        "revoked": False,
    }


def test_valid_token_accepts_exact_context():
    ok, failures = validate(token(), CTX, datetime(2026, 6, 4, tzinfo=timezone.utc))
    assert ok
    assert failures == ()


def test_single_context_mismatch_rejects():
    t = token()
    t["device_id"] = "different-device"
    ok, failures = validate(t, CTX, datetime(2026, 6, 4, tzinfo=timezone.utc))
    assert not ok
    assert "mismatch:device_id" in failures


def test_revoked_token_rejects():
    t = token()
    t["revoked"] = True
    ok, failures = validate(t, CTX, datetime(2026, 6, 4, tzinfo=timezone.utc))
    assert not ok
    assert "revoked" in failures


def test_outside_time_window_rejects():
    ok, failures = validate(token(), CTX, datetime(2028, 1, 1, tzinfo=timezone.utc))
    assert not ok
    assert "outside_time_window" in failures
