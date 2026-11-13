#!/usr/bin/env python3
"""WC-4R-001 v0.2 research ledger: execution is not evidence or authority.

JSONL commitments detect accidental modification and internal reordering. They
cannot detect tail deletion or wholesale re-hashing without external custody.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = "weaver-test-event/v0.2"
DEFECT_SCHEMA = "weaver-defect-event/v0.2"
OUTCOMES = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "SKIP"}
EVIDENCE = {"COMPLETE", "INCOMPLETE", "UNVERIFIED"}
INDEPENDENCE = {"OWNER_LOCAL", "OWNER_CI", "EXTERNAL_REPORTED", "INDEPENDENT_WITNESS"}
LIFECYCLE = ("OPEN", "REPRODUCED", "PATCHED", "REGRESSION_PASS", "REVIEWED", "CLOSED")
ZERO = "0" * 64


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True)


def commit_hash(event):
    return hashlib.sha256(canonical({k: v for k, v in event.items() if k != "event_hash"}).encode()).hexdigest()


def require(cond, message):
    if not cond:
        raise ValueError(message)


def sha(value, n):
    return isinstance(value, str) and len(value) == n and bool(re.fullmatch("[0-9a-f]+", value))


def valstr(event, key):
    require(isinstance(event.get(key), str) and bool(event[key].strip()), f"missing/empty {key}")


def records(path):
    def no_duplicates(pairs):
        obj = {}
        for k, v in pairs:
            require(k not in obj, f"duplicate JSON key {k}")
            obj[k] = v
        return obj

    out = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line, object_pairs_hook=no_duplicates,
                                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))))
            except (ValueError, json.JSONDecodeError) as e:
                raise ValueError(f"{path.name}:{line_no}: {e}") from e
    return out


def chain(events, schema, identifier):
    prev = ZERO
    ids = set()
    for i, e in enumerate(events):
        require(isinstance(e, dict), f"{identifier} {i} is not an object")
        require(e.get("schema") == schema, f"{identifier} {i}: unsupported schema")
        valstr(e, identifier)
        require(e[identifier] not in ids, f"duplicate {identifier} {e[identifier]}")
        ids.add(e[identifier])
        require(e.get("prev_hash") == prev, f"{identifier} {i}: broken prev_hash")
        require(e.get("event_hash") == commit_hash(e), f"{identifier} {i}: body hash mismatch")
        prev = e["event_hash"]


def validate_tests(catalog, events):
    ids = {x["id"] for x in catalog["candidates"]}
    chain(events, SCHEMA, "event_id")
    by_id = {}
    fingerprints = {}
    for e in events:
        for key in ("candidate_id", "source_sha", "target_sha", "environment",
                    "test_selector", "outcome", "evidence_status", "independence_class", "receipt_url"):
            valstr(e, key)
        require(e["candidate_id"] in ids, "unknown test candidate")
        require(sha(e["source_sha"], 40) and sha(e["target_sha"], 40), "invalid source/target SHA")
        require(e["outcome"] in OUTCOMES, "invalid outcome")
        require(e["evidence_status"] in EVIDENCE, "invalid evidence_status")
        require(e["independence_class"] in INDEPENDENCE, "invalid independence_class")
        require(e["receipt_url"].startswith("https://"), "receipt_url must be HTTPS")
        artifact = e.get("artifact_sha256")
        require(artifact is None or sha(artifact, 64), "invalid artifact_sha256")
        if e["evidence_status"] == "COMPLETE":
            require(sha(artifact, 64), "COMPLETE requires artifact_sha256")
        if e["independence_class"] == "INDEPENDENT_WITNESS":
            require(bool(e.get("witness_receipt_url")), "missing claimed witness receipt")
        # A re-execution is legitimate, but must have a distinct run identity
        # and receipt. Do not count the same run/result twice.
        fingerprint = (e["candidate_id"], e["source_sha"], e["target_sha"],
                       e["environment"], e["test_selector"], e["outcome"], e["receipt_url"])
        require(fingerprint not in fingerprints, "duplicate report for same run/result")
        fingerprints[fingerprint] = e["event_id"]
        prior_id = e.get("repair_of")
        if prior_id is not None:
            prior = by_id.get(prior_id)
            require(prior is not None and prior["outcome"] == "FAIL", "repair_of needs prior FAIL")
            require(prior["candidate_id"] == e["candidate_id"] and
                    prior["source_sha"] == e["source_sha"] and
                    prior["test_selector"] == e["test_selector"], "repair/baseline mismatch")
            require(e["outcome"] == "PASS", "repair_of only valid on PASS")
            require(prior["target_sha"] != e["target_sha"], "repair must target changed code SHA")
        by_id[e["event_id"]] = e
    return by_id


def validate_defects(catalog, defects, tests):
    known = {x["id"] for x in catalog["candidates"]}
    chain(defects, DEFECT_SCHEMA, "step_id")
    state = {}
    for e in defects:
        for k in ("defect_id", "candidate_id", "state", "source_sha", "target_sha", "receipt_url"):
            valstr(e, k)
        require(e["candidate_id"] in known, "unknown defect candidate")
        require(e["state"] in LIFECYCLE, "unknown defect lifecycle state")
        require(sha(e["source_sha"], 40) and sha(e["target_sha"], 40), "invalid defect SHA")
        require(e["receipt_url"].startswith("https://"), "defect receipt must be HTTPS")
        history = state.setdefault(e["defect_id"], [])
        require(len(history) < len(LIFECYCLE) and e["state"] == LIFECYCLE[len(history)],
                f"invalid transition for {e['defect_id']}")
        require(not history or (history[0]["source_sha"] == e["source_sha"] and
                                 history[0]["candidate_id"] == e["candidate_id"]),
                "defect source/candidate changed")
        if e["state"] == "OPEN":
            require(e["target_sha"] == e["source_sha"], "open defect must pin its origin")
        if e["state"] == "REPRODUCED":
            t = tests.get(e.get("test_event_id"))
            require(t is not None and t["outcome"] == "FAIL" and
                    t["candidate_id"] == e["candidate_id"] and t["target_sha"] == e["source_sha"],
                    "REPRODUCED needs actual baseline FAIL")
        if e["state"] == "PATCHED":
            require(e["target_sha"] != e["source_sha"], "PATCHED must change code")
            require(e["repair_sha"] == e["target_sha"], "PATCHED repair_sha mismatch")
        if e["state"] in ("REGRESSION_PASS", "REVIEWED", "CLOSED"):
            patched = history[2]
            require(e["target_sha"] == patched["target_sha"], "defect fix pin changed")
        if e["state"] == "REGRESSION_PASS":
            baseline = tests.get(e.get("baseline_event_id"))
            fixed = tests.get(e.get("repair_event_id"))
            require(baseline is not None and fixed is not None, "missing regression pair")
            require(baseline["outcome"] == "FAIL" and fixed["outcome"] == "PASS" and
                    fixed.get("repair_of") == baseline["event_id"], "regression fail/pass link invalid")
            require(baseline["candidate_id"] == e["candidate_id"] and
                    fixed["candidate_id"] == e["candidate_id"] and
                    baseline["source_sha"] == e["source_sha"] and
                    fixed["target_sha"] == e["target_sha"], "regression SHA/owner mismatch")
            require(baseline["test_selector"] == fixed["test_selector"], "different regressions")
        if e["state"] == "REVIEWED":
            for k in ("reviewer_id", "review_receipt_url"):
                valstr(e, k)
            require(e["review_receipt_url"].startswith("https://"), "invalid review URL")
            # Recording review metadata is NOT cryptographic independent-witness verification.
        if e["state"] == "CLOSED":
            require(history[-1]["state"] == "REVIEWED", "closure needs recorded review")
        history.append(e)
    return {key: seq[-1]["state"] for key, seq in state.items()}


def summarize(catalog, tests, defects):
    counts = Counter(x["outcome"] for x in tests)
    latest = {}
    for e in tests:
        latest[e["candidate_id"]] = e["outcome"]
    repair_passes = sum(1 for e in tests if e["outcome"] == "PASS" and e.get("repair_of"))
    return {
        "catalog_family_count": len(catalog["candidates"]),
        "fresh_attempts": len(tests),
        "raw_outcomes": {x: counts[x] for x in sorted(OUTCOMES)},
        "evidence_status": dict(sorted(Counter(e["evidence_status"] for e in tests).items())),
        "independence_class": dict(sorted(Counter(e["independence_class"] for e in tests).items())),
        "linked_repair_passes_not_closures": repair_passes,
        "latest_pass_families": sum(o == "PASS" for o in latest.values()),
        "latest_fail_families": sum(o == "FAIL" for o in latest.values()),
        "not_run_families": len(catalog["candidates"]) - len(latest),
        "defect_states": dict(sorted(Counter(defects.values()).items())),
        "authority": "O0_WITHHELD",
        "production": "PROHIBITED",
        "independent_witnesses_admitted": 0,  # never inferred from self-reported metadata
    }


def attach(stream, payload):
    event = {**payload, "prev_hash": stream[-1]["event_hash"] if stream else ZERO}
    event["event_hash"] = commit_hash(event)
    return event


def self_test(catalog):
    case = "AL-SNAPSHOT"
    base = "a" * 40
    fix = "b" * 40
    data = {"schema": SCHEMA, "candidate_id": case, "source_sha": base,
            "environment": "ubuntu311", "test_selector": "tests/test_snapshot.py",
            "evidence_status": "INCOMPLETE", "independence_class": "OWNER_CI",
            "receipt_url": "https://example.org/run/1"}
    first = attach([], {**data, "event_id": "run-base", "target_sha": base, "outcome": "FAIL"})
    second = attach([first], {**data, "event_id": "run-fix", "target_sha": fix,
                               "outcome": "PASS", "repair_of": "run-base"})
    tests = validate_tests(catalog, [first, second])
    assert summarize(catalog, [first, second], {})["linked_repair_passes_not_closures"] == 1
    stages = []
    def step(state, **extra):
        event = attach(stages, {"schema": DEFECT_SCHEMA, "step_id": f"step-{len(stages)}",
                                "defect_id": "AL-SNAPSHOT-001", "candidate_id": case,
                                "state": state, "source_sha": base,
                                "target_sha": fix if len(stages) >= 2 else base,
                                "receipt_url": "https://example.org/defect", **extra})
        stages.append(event)
    step("OPEN")
    step("REPRODUCED", test_event_id="run-base")
    step("PATCHED", repair_sha=fix)
    step("REGRESSION_PASS", baseline_event_id="run-base", repair_event_id="run-fix")
    assert validate_defects(catalog, stages, tests)["AL-SNAPSHOT-001"] == "REGRESSION_PASS"
    step("REVIEWED", reviewer_id="third-party", review_receipt_url="https://example.org/review")
    step("CLOSED")
    assert validate_defects(catalog, stages, tests)["AL-SNAPSHOT-001"] == "CLOSED"

    def rejected(fn):
        try:
            fn()
        except ValueError:
            return
        raise AssertionError("negative control was accepted")
    rejected(lambda: validate_tests(catalog, [first, first]))
    rejected(lambda: validate_tests(catalog, [{**first, "outcome": "PASS"}]))
    rejected(lambda: validate_tests(catalog, [first, {**second, "repair_of": "missing"}]))
    rejected(lambda: validate_tests(catalog, [first, {**second, "source_sha": "c" * 40}]))
    rejected(lambda: validate_tests(catalog, [first, {**second, "target_sha": base}]))
    rejected(lambda: validate_tests(catalog, [first, {**second, "evidence_status": "COMPLETE"}]))
    rejected(lambda: validate_tests(catalog, [first, {**second, "independence_class": "INDEPENDENT_WITNESS"}]))
    rejected(lambda: validate_defects(catalog, stages[:-2] + [stages[-1]], tests))
    rejected(lambda: validate_defects(catalog, [stages[1]], tests))
    rejected(lambda: validate_defects(catalog, stages[:3] + [{**stages[3], "repair_event_id": "run-base"}], tests))
    print("PASS: WC-4R-001 v0.2 chains, evidence axes, repair and lifecycle negative controls")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    require(catalog.get("status") == "PROPOSAL_ONLY", "catalog must remain proposed")
    require(len(set(catalog["owners"].values())) == 4, "owner registry must have four distinct repos")
    require(len({x["id"] for x in catalog["candidates"]}) == len(catalog["candidates"]),
            "duplicate candidate IDs")
    if args.self_test:
        self_test(catalog)
        return
    tests = records(ROOT / "events-v02.jsonl")
    defects = records(ROOT / "defect-events-v02.jsonl")
    by_id = validate_tests(catalog, tests)
    state = validate_defects(catalog, defects, by_id)
    print(json.dumps(summarize(catalog, tests, state), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
