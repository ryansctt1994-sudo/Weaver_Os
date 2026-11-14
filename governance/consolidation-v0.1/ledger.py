#!/usr/bin/env python3
"""Validate an append-only experimental test ledger; never infer authority.

Usage: python governance/consolidation-v0.1/ledger.py [--self-test]
Events are an ordered JSONL file. Historical donor statistics are catalog
references, NOT fresh execution results.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTCOMES = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "SKIP"}
EVIDENCE = {"OWNER_LOCAL", "OWNER_CI", "EXTERNAL_REPORTED"}


def verify(catalog, events):
    if catalog.get("status") != "PROPOSAL_ONLY":
        raise ValueError("catalog cannot silently promote itself")
    owners = set(catalog["owners"].values())
    ids = [x["id"] for x in catalog["candidates"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate ID")
    if any(x["owner"] not in owners for x in catalog["candidates"]):
        raise ValueError("candidate owner outside four-repo map")
    known = set(ids)
    seen = {}
    for index, event in enumerate(events):
        required = ("event_id", "candidate_id", "source_sha", "environment",
                    "outcome", "evidence_class", "receipt_url")
        if any(not isinstance(event.get(k), str) or not event[k].strip()
               for k in required):
            raise ValueError(f"event {index}: missing field")
        eid = event["event_id"]
        if eid in seen:
            raise ValueError(f"duplicate event_id: {eid}")
        if event["candidate_id"] not in known:
            raise ValueError(f"unknown candidate: {event['candidate_id']}")
        if event["outcome"] not in OUTCOMES:
            raise ValueError(f"invalid outcome: {event['outcome']}")
        if event["evidence_class"] not in EVIDENCE:
            raise ValueError("invalid evidence_class")
        if not event["source_sha"] or len(event["source_sha"]) != 40 or any(
                c not in "0123456789abcdef" for c in event["source_sha"].lower()):
            raise ValueError("source_sha must be a full 40-character SHA-1")
        repaired = event.get("repair_of")
        if repaired is not None:
            previous = seen.get(repaired)
            if (previous is None or previous["outcome"] != "FAIL" or
                    previous["candidate_id"] != event["candidate_id"]):
                raise ValueError("repair_of must reference a preceding failure of same case")
        seen[eid] = event
    return summarize(catalog, events)


def summarize(catalog, events):
    counts = Counter(e["outcome"] for e in events)
    by_case = {}
    for e in events:
        by_case[e["candidate_id"]] = e
    repaired = sum(1 for e in events if e["outcome"] == "PASS" and "repair_of" in e)
    owner_by_case = {x["id"]: x["owner"] for x in catalog["candidates"]}
    by_owner = {}
    for owner in catalog["owners"].values():
        own = [e for e in events if owner_by_case[e["candidate_id"]] == owner]
        c = Counter(e["outcome"] for e in own)
        by_owner[owner] = {"attempts": len(own), **{k.lower(): c[k] for k in sorted(OUTCOMES)}}
    return {
        "candidate_count": len(catalog["candidates"]),
        "fresh_attempts": len(events),
        "fresh_pass": counts["PASS"],
        "fresh_fail": counts["FAIL"],
        "fresh_blocked": counts["BLOCKED"],
        "fresh_inconclusive": counts["INCONCLUSIVE"],
        "fresh_skip": counts["SKIP"],
        "validated_repair_passes": repaired,
        "latest_pass_cases": sum(e["outcome"] == "PASS" for e in by_case.values()),
        "latest_fail_cases": sum(e["outcome"] == "FAIL" for e in by_case.values()),
        "not_yet_run_cases": len(catalog["candidates"]) - len(by_case),
        "by_owner": by_owner,
        "authority": "O0_WITHHELD",
        "production": "PROHIBITED",
    }


def self_test():
    catalog = {"status": "PROPOSAL_ONLY",
               "owners": {"a": "repo/a", "b": "repo/b", "c": "repo/c", "d": "repo/d"},
               "candidates": [{"id": "ONE", "owner": "repo/a"}]}
    assert verify(catalog, [])["fresh_pass"] == 0
    base = {"candidate_id": "ONE", "source_sha": "a" * 40,
            "environment": "test", "evidence_class": "OWNER_LOCAL",
            "receipt_url": "https://example.org/receipt"}
    fail = {**base, "event_id": "one-fail", "outcome": "FAIL"}
    repaired = {**base, "event_id": "one-fix", "outcome": "PASS", "repair_of": "one-fail"}
    summary = verify(catalog, [fail, repaired])
    assert (summary["fresh_fail"], summary["fresh_pass"],
            summary["validated_repair_passes"], summary["latest_pass_cases"]) == (1, 1, 1, 1)
    for bad in ([fail, fail], [{**repaired}], [{**fail, "outcome": "INVALID"}]):
        try:
            verify(catalog, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("negative control passed")
    print("PASS: four-repo ledger self-tests and negative controls")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    events = []
    lines = (ROOT / "events.jsonl").read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise SystemExit(f"invalid JSON at events line {line_number}: {error}") from error
    print(json.dumps(verify(catalog, events), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
