"""WEAVER-VERTICAL-001 acceptance cases, including explicit HOLDs.

The tests prove bounded application/SQLite atomicity, NOT OS confinement,
independent signing authority, physical veto, or qualified external witnessing.
V008/V012 remain explicit expected failures instead of false-green tests.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import Proposal
from weaver_runtime.gate import ABORTED, COMMITTED, REJECTED
from weaver_runtime.protected_write import GRANT_DOMAIN, ProtectedWriteOwner
from weaver_verifier.protected_write import verify_protected_write


class Veto:
    active = False

    def vetoed(self):
        return self.active


@pytest.fixture
def env(tmp_path):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    db = tmp_path / "bounded.db"
    veto = Veto()

    def open_owner():
        return ProtectedWriteOwner(
            db,
            trusted_public_key=public,
            issuer_id="issuer-a",
            allowed_keys=frozenset({"alpha", "beta"}),
            veto=veto,
            clock=lambda: 1000,
        )

    owner = open_owner()
    yield owner, key, db, veto, open_owner
    owner.close()


def proposal(pid="p1", key="alpha", value="one", action="WRITE_KEY"):
    return Proposal(pid, "agent-a", action, "policy-v1", {"key": key, "value": value})


def grant(key, p, *, issuer="issuer-a", audience="weaver-vertical-001",
          valid_from=900, valid_until=1100, grant_id="grant-a"):
    fields = {
        "issuer_id": issuer,
        "audience": audience,
        "grant_id": grant_id,
        "proposal_sha256": hashlib.sha256(canonicalize(p.to_dict())).hexdigest(),
        "valid_from": valid_from,
        "valid_until": valid_until,
    }
    signature = key.sign(GRANT_DOMAIN + canonicalize(fields))
    return {
        "grant": fields,
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
    }


def counts(owner):
    roots = owner.snapshot()["roots"]
    return len(roots["AUTHORITY"]), len(roots["REJECTION"])


def test_v001_valid_signed_bound_write_and_receipt(env):
    owner, key, *_ = env
    outcome = owner.submit(proposal(), grant(key, proposal()))
    assert outcome.status == COMMITTED
    assert owner.rows() == {"alpha": "one"}
    assert outcome.receipt.event_type == "EXECUTION_COMMITTED"
    assert counts(owner) == (1, 0)


def test_v002_missing_grant_refused_with_receipt(env):
    owner, *_ = env
    outcome = owner.submit(proposal(), None)
    assert outcome.status == REJECTED
    assert owner.rows() == {}
    assert counts(owner) == (0, 1)


def test_v003_untrusted_issuer_key_is_refused(env):
    owner, _key, *_ = env
    wrong_key = Ed25519PrivateKey.generate()
    p = proposal()
    outcome = owner.submit(p, grant(wrong_key, p))
    assert outcome.status == REJECTED
    assert owner.rows() == {}


def test_v004_wrong_scope_action_and_key_refused(env):
    owner, key, *_ = env
    p = proposal()
    signed = grant(key, p, audience="not-this-owner")
    assert owner.submit(p, signed).status == REJECTED
    wrong_key = proposal("p2", key="beta")
    assert owner.submit(wrong_key, grant(key, p)).status == REJECTED
    bad_action = proposal("p3", action="DELETE_KEY")
    assert owner.submit(bad_action, grant(key, bad_action)).status == ABORTED
    assert owner.rows() == {}


def test_v005_expired_and_not_yet_valid_grants_refused(env):
    owner, key, *_ = env
    p = proposal()
    assert owner.submit(p, grant(key, p, valid_until=999)).status == REJECTED
    assert owner.submit(p, grant(key, p, valid_from=1001)).status == REJECTED
    assert owner.rows() == {}


def test_v006_revocation_before_transaction_commit_aborts(env):
    owner, key, *_ = env
    p = proposal()
    original_stage = owner._stage

    def revoke_during_stage(ctx):
        result = original_stage(ctx)
        owner._ledger.set_control(
            "revoked:p1", "revoked", actor_id="operator", policy_version="policy-v1"
        )
        return result

    owner._stage = revoke_during_stage
    outcome = owner.submit(p, grant(key, p))
    assert (outcome.status, outcome.reason_code) == (
        ABORTED, "REVOKED_RECORDED_BEFORE_COMMIT"
    )
    assert owner.rows() == {}
    assert counts(owner) == (0, 1)


def test_v007_proposal_replacement_detected_before_effect(env):
    owner, key, *_ = env
    p = proposal()
    original_stage = owner._stage

    def tamper(ctx):
        result = original_stage(ctx)
        object.__setattr__(ctx.proposal, "actor_id", "different-agent")
        return result

    owner._stage = tamper
    outcome = owner.submit(p, grant(key, p))
    assert (outcome.status, outcome.reason_code) == (ABORTED, "PROPOSAL_MUTATED")
    assert owner.rows() == {}


@pytest.mark.xfail(
    strict=True,
    reason="HOLD: same-UID subprocess can directly edit SQLite; "
    "OS owner isolation absent",
)
def test_v008_direct_sqlite_bypass_must_be_denied_by_os(env):
    owner, *_rest = env
    db = _rest[1]
    proc = subprocess.run(
        [
            sys.executable, "-c",
            "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
            "c.execute(\"INSERT INTO protected_kv VALUES('alpha','bypass','untrusted')\"); "
            "c.commit()",
            str(db),
        ],
        capture_output=True, text=True, check=False,
    )
    # EXPECTED TO FAIL until a separate OS principal/service actually owns this file.
    assert proc.returncode != 0
    assert owner.rows() == {}


def test_v009_duplicate_proposal_id_commits_once(env):
    owner, key, *_ = env
    p = proposal()
    signed = grant(key, p)
    assert owner.submit(p, signed).status == COMMITTED
    assert owner.submit(p, signed).status != COMMITTED
    assert owner.rows() == {"alpha": "one"}
    assert counts(owner) == (1, 1)


def test_v010_concurrent_identical_submissions_commit_once(env):
    owner, key, _db, _veto, reopen = env
    other = reopen()
    try:
        p = proposal()
        signed = grant(key, p)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(owner.submit, p, signed),
                pool.submit(other.submit, p, signed),
            ]
            outcomes = [f.result() for f in futures]
        assert sum(x.status == COMMITTED for x in outcomes) == 1
        assert owner.rows() == {"alpha": "one"}
        assert counts(owner) == (1, 1)
    finally:
        other.close()


def test_v011_precommit_exception_leaves_no_resource_change(env):
    owner, key, *_ = env
    p = proposal()

    def crash(_conn, _proposal, _result):
        raise RuntimeError("injected before sqlite commit")

    owner._effect = crash
    result = owner.submit(p, grant(key, p))
    assert (result.status, result.reason_code) == (ABORTED, "EFFECT_WRITE_FAILED")
    assert owner.rows() == {}
    assert counts(owner) == (0, 1)


@pytest.mark.xfail(
    strict=True,
    reason="HOLD: process-kill-after-commit and acknowledgment-loss "
    "injection not yet exercised",
)
def test_v012_real_process_kill_after_commit_recovery_required():
    # A normal close/reopen is covered elsewhere; it is not a kill at the commit boundary.
    raise AssertionError("separate-process crash injector required")


def test_v013_fresh_python_process_replays_history(env):
    owner, key, _db, *_ = env
    p = proposal()
    assert owner.submit(p, grant(key, p)).status == COMMITTED
    payload = json.dumps({
        "snapshot": owner.snapshot(), "rows": owner.rows(), "anchor": owner.anchor()
    })
    code = (
        "import json,sys; from weaver_verifier.protected_write import verify_protected_write;"
        "d=json.loads(sys.argv[1]); x=verify_protected_write("
        "d['snapshot'],d['rows'],anchor=d['anchor']);"
        "print('PASS' if x.ok and x.anchored else x.reason);sys.exit(0 if x.ok else 1)"
    )
    root = Path(__file__).resolve().parents[2]
    env_vars = dict(os.environ)
    env_vars["PYTHONPATH"] = os.pathsep.join(
        [str(root / "packages" / "contracts"), str(root / "packages" / "verifier")]
    )
    run = subprocess.run(
        [sys.executable, "-c", code, payload],
        env=env_vars, capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "PASS"


def test_v014_tampered_history_and_anchor_are_rejected(env):
    owner, key, *_ = env
    p = proposal()
    assert owner.submit(p, grant(key, p)).status == COMMITTED
    snapshot, anchor, rows = owner.snapshot(), owner.anchor(), owner.rows()
    snapshot["roots"]["AUTHORITY"][0]["event"] = '{"fake":true}'
    assert not verify_protected_write(snapshot, rows, anchor=anchor).ok
    assert not verify_protected_write(
        {"schema": snapshot["schema"], "ledger_id": snapshot["ledger_id"],
         "roots": {"AUTHORITY": [], "REJECTION": []}},
        rows, anchor=anchor,
    ).ok


def test_v015_veto_recorded_before_commit_blocks_effect(env):
    owner, key, *_ = env
    owner._ledger.set_control(
        "veto", "active", actor_id="operator", policy_version="policy-v1"
    )
    p = proposal()
    result = owner.submit(p, grant(key, p))
    assert (result.status, result.reason_code) == (
        ABORTED, "VETO_RECORDED_BEFORE_COMMIT"
    )
    assert owner.rows() == {}


def test_v016_ledger_write_failure_rolls_back_effect(env):
    owner, key, *_ = env
    p = proposal()

    def disk_full(*_a, **_k):
        raise sqlite3.OperationalError("injected ledger write failure")

    owner._ledger._insert_entry = disk_full
    with pytest.raises(sqlite3.OperationalError, match="ledger write failure"):
        owner.submit(p, grant(key, p))
    assert owner.rows() == {}
    assert counts(owner) == (0, 0)


def test_effect_state_mismatch_is_detected_even_with_valid_chain(env):
    owner, key, db, *_ = env
    p = proposal()
    assert owner.submit(p, grant(key, p)).status == COMMITTED
    anchor, snapshot = owner.anchor(), owner.snapshot()
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE protected_kv SET value='tampered' WHERE key='alpha'")
    verdict = verify_protected_write(snapshot, owner.rows(), anchor=anchor)
    assert (verdict.ok, verdict.reason) == (False, "STATE_MISMATCH")


def test_commit_without_grant_is_not_possible_through_owner(env):
    owner, key, *_ = env
    p = proposal()
    bad = grant(key, p)
    bad["grant"]["proposal_sha256"] = "0" * 64
    assert owner.submit(p, bad).status == REJECTED
    assert owner.rows() == {}
