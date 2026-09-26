import copy
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from demo.xproc_authority import Authority, Scope, semantic_result

SCOPE = Scope("fixture-actor", "promote", "artifact-A", "policy-v1", 1)


def fixture():
    issuer = Authority()
    return issuer, issuer.issue(SCOPE, not_before=10, expires=20)


def deny_unchanged(issuer, grant, scope=SCOPE, now=15):
    outcome = issuer.consume(grant, scope, now=now)
    assert not outcome["accepted"]
    assert outcome["before"] == outcome["after"]
    return outcome["reason"]


def test_once_then_replay():
    issuer, grant = fixture()
    result = issuer.consume(grant, SCOPE, now=15)
    assert result["accepted"] and result["before"] != result["after"]
    assert result["state"] == {"artifact": "artifact-A", "revision": 1}
    assert deny_unchanged(issuer, grant) == "reused"


def test_foreign_process_identity():
    first, grant = fixture()
    second = Authority()
    assert deny_unchanged(second, grant) == "foreign_issuer"
    assert semantic_result(SCOPE) == semantic_result(SCOPE)
    assert first.instance != second.instance


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor", "other"),
        ("action", "read"),
        ("artifact", "artifact-B"),
        ("policy", "policy-v2"),
        ("epoch", 2),
    ],
)
def test_scope_mismatch(field, value):
    issuer, grant = fixture()
    assert (
        deny_unchanged(issuer, grant, SCOPE.__class__(**{**SCOPE.__dict__, field: value}))
        == "scope_mismatch"
    )


def test_stale_epoch():
    issuer = Authority(epoch=2)
    grant = issuer.issue(SCOPE, not_before=10, expires=20)
    assert deny_unchanged(issuer, grant) == "stale_epoch"


@pytest.mark.parametrize("now", [9, 20])
def test_time_bounds(now):
    issuer, grant = fixture()
    assert deny_unchanged(issuer, grant, now=now) == "outside_validity"


def test_revoked():
    issuer, grant = fixture()
    issuer.revoked.add(grant["body"]["nonce"])
    assert deny_unchanged(issuer, grant) == "revoked"


def test_tampered_or_malformed():
    issuer, grant = fixture()
    changed = copy.deepcopy(grant)
    changed["body"]["artifact"] = "artifact-B"
    assert deny_unchanged(issuer, changed) == "bad_signature"
    changed = copy.deepcopy(grant)
    changed["signature"] = "invalid"
    assert deny_unchanged(issuer, changed) == "bad_signature"
    changed = copy.deepcopy(grant)
    changed["body"]["epoch"] = True
    assert deny_unchanged(issuer, changed) == "malformed"


def test_duplicate_concurrent_consume():
    issuer, grant = fixture()
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: issuer.consume(grant, SCOPE, now=15), range(8)))
    assert sum(o["accepted"] for o in outcomes) == 1
    assert issuer.state["revision"] == 1
    assert all(o["before"] == o["after"] for o in outcomes if not o["accepted"])


def test_fresh_process_semantics_and_foreign_denial():
    parent, foreign = fixture()
    script = """import json,sys
from demo.xproc_authority import Authority,Scope,semantic_result
scope=Scope("fixture-actor","promote","artifact-A","policy-v1",1)
a=Authority()
g=a.issue(scope,not_before=10,expires=20)
accepted=a.consume(g,scope,now=15)
foreign=a.consume(json.loads(sys.stdin.read()),scope,now=15)
print(json.dumps({"semantic":semantic_result(scope),"instance":a.instance,"nonce":g["body"]["nonce"],"accepted":accepted["accepted"],"foreign":foreign},sort_keys=True))"""
    outputs = []
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, "-c", script],
            input=json.dumps(foreign),
            text=True,
            capture_output=True,
            check=True,
        )
        outputs.append(json.loads(proc.stdout))
    assert outputs[0]["semantic"] == outputs[1]["semantic"] == semantic_result(SCOPE)
    assert len({parent.instance, *(out["instance"] for out in outputs)}) == 3
    assert outputs[0]["nonce"] != outputs[1]["nonce"]
    assert all(out["accepted"] for out in outputs)
    assert all(
        out["foreign"]["reason"] == "foreign_issuer"
        and out["foreign"]["before"] == out["foreign"]["after"]
        for out in outputs
    )
