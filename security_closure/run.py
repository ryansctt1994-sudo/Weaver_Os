"""Frozen corpus runner. Exit fails on wrong verdict or unexpected protected effect."""

import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

from security_closure.boundary import Boundary, Request

CORPUS = Path(__file__).with_name("corpus.json")


def run_case(case, boundary_type=Boundary):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "boundary.db"
        boundary = boundary_type(path)
        boundary.bootstrap()
        request = Request("agent", "increment", "counter", 1, "fixed-nonce")
        token = boundary.approve(request)
        principal, now, grant = "agent", 2, "leaf"
        attack = case["id"]
        if attack == "forged_grant":
            grant = "self-issued-unregistered"
        elif attack == "revoked_parent":
            with boundary.connect() as db:
                db.execute("UPDATE grants SET revoked=1 WHERE id='root'")
        elif attack == "poisoned_memory":
            # Retrieved text has no dispatch path to grant creation or approval.
            request = replace(request, actor="admin")
            principal = "admin"
        elif attack == "request_substitution":
            request = replace(request, amount=2)
        elif attack == "stolen_token":
            principal = "intruder"
        elif attack == "expired_approval":
            now = 81
        elif attack == "scope_escalation":
            request = replace(request, action="delete_database")
            token = boundary.approve(request)
        elif attack == "restart_replay":
            assert boundary.execute(request, token, principal) == "ACCEPT"
            boundary = boundary_type(path)
        elif attack.startswith("crash_"):
            mode = "before_commit" if attack == "crash_before_commit" else "after_commit"
            try:
                boundary.execute(request, token, principal, crash=mode)
            except RuntimeError:
                pass
            else:
                raise AssertionError("crash injection did not fire")
            boundary = boundary_type(path)
            expected_value = 0 if mode == "before_commit" else 1
            assert boundary.snapshot() == [("counter", expected_value)]
        before = boundary.snapshot()
        verdict = boundary.execute(request, token, principal, now, grant)
        after = boundary.snapshot()
        assert verdict == case["expected"], (attack, verdict)
        if verdict == "REJECT":
            assert before == after, (attack, "protected effect on rejection")
        else:
            assert after == [("counter", before[0][1] + 1)], (attack, "wrong effect")
        with boundary.connect() as db:
            receipt = db.execute(
                "SELECT verdict,reason,before_value,after_value "
                "FROM receipts ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        assert receipt and receipt[0] == verdict
        return dict(
            attack=attack,
            expected=case["expected"],
            observed=verdict,
            before=before,
            after=after,
            receipt=receipt,
        )


def run_all():
    cases = json.loads(CORPUS.read_text())
    return dict(
        corpus_sha256=hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        outcomes=[run_case(case) for case in cases],
        independent_witness=False,
    )


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2))
