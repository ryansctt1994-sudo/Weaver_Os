"""Bounded tests of offline synthetic benchmark. No live runtime tested."""
import copy

import pytest

from benchmarks.agent_reliability.portable import (
    FAMILIES, MUTANTS, Trace, authorize, evaluate, mac, make_cases, run_case,
)


def test_frozen_case_count_and_family_coverage():
    cases = make_cases()
    assert len(cases) == 44
    assert len({c["id"] for c in cases}) == 44
    assert all(sum(c["family"] == family for c in cases) == 4 for family in FAMILIES)
    assert sum(len(c["expected"]) for c in cases) == 48


def test_reference_and_mutation_controls():
    report = evaluate()
    assert report["reference"]["oracle_matches"] == 44
    assert report["reference"]["forbidden_commits"] == 0
    assert report["baseline"]["forbidden_commits"] == 40
    assert set(report["mutants_detected"]) == set(MUTANTS)
    assert all(report["mutants_detected"].values())
    assert report["reference"]["unreceipted"] == 4


def test_report_deterministic():
    assert evaluate() == evaluate()


def test_replay_and_evidence_outage():
    replay = next(c for c in make_cases() if c["family"] == "replay")
    outage = next(c for c in make_cases() if c["family"] == "evidence_loss")
    assert run_case(replay, "governed")["observed"] == ["allow", "deny"]
    assert run_case(outage, "governed")["observed"] == ["halt"]
    assert run_case(outage, "governed")["unreceipted"] == 1


@pytest.mark.parametrize("family", [f for f in FAMILIES if f not in ("authorized", "replay", "evidence_loss")])
def test_each_unauthorized_family(family):
    case = next(c for c in make_cases() if c["family"] == family)
    assert run_case(case, "governed")["observed"] == ["deny"]


def test_grant_binding_and_malformed_fail_closed():
    case = make_cases()[0]
    grant = copy.deepcopy(case["grant"])
    grant["action"] = "delete"
    assert authorize(case["request"], grant, 100, 2, False, True)[0] == "deny"
    assert mac(grant) != grant["mac"]
    grant.pop("mac")
    assert authorize(case["request"], grant, 100, 2, False, True)[0] == "deny"


def test_trace_and_local_head_limitation():
    chain = Trace()
    chain.append({"action": "write"})
    chain.append({"action": "deny"})
    assert chain.verify()
    altered = copy.deepcopy(chain)
    altered.entries[0]["event"]["action"] = "delete"
    assert not altered.verify()
    truncated = copy.deepcopy(chain)
    truncated.entries.pop()
    assert not truncated.verify()
    truncated.head = truncated.entries[-1]["hash"]
    assert truncated.verify()  # No independent custody of the head.
