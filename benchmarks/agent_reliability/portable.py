"""Offline synthetic reliability benchmark. No system adapters or external effects."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

PUBLIC_FIXTURE_KEY = b"PUBLIC-TEST-KEY-NOT-FOR-AUTHENTICATION"
FAMILIES = (
    "authorized", "wrong_principal", "wrong_action", "wrong_resource",
    "payload_swap", "nonce_swap", "expired", "revoked", "replay",
    "invalid_mac", "evidence_loss",
)
MUTANTS = (
    "signature", "principal", "action", "resource", "payload",
    "nonce", "expiry", "epoch", "replay", "evidence", "deny_all",
)
GENESIS = "0" * 64


def encode(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def mac(grant: dict) -> str:
    payload = encode({k: v for k, v in grant.items() if k != "mac"})
    return hmac.new(PUBLIC_FIXTURE_KEY, payload, hashlib.sha256).hexdigest()


def make_cases() -> list[dict]:
    """Generate exactly 44 deterministic cases; labels never enter authorize."""
    cases = []
    for family in FAMILIES:
        for i in range(1, 5):
            name = f"{family}-{i:02d}"
            req = {
                "principal": f"agent-{i}", "action": "write",
                "resource": f"sandbox/{i}/file.txt", "payload": f"payload-{i}",
                "nonce": f"nonce:{name}",
            }
            grant = {
                "principal": req["principal"], "action": req["action"],
                "resource": req["resource"], "payload_sha256": sha(req["payload"].encode()),
                "nonce": req["nonce"], "expires_at": 110, "epoch": 2,
            }
            if family == "wrong_principal":
                grant["principal"] = "unauthorized-agent"
            elif family == "wrong_action":
                grant["action"] = "delete"
            elif family == "wrong_resource":
                grant["resource"] = "sandbox/private/file.txt"
            elif family == "payload_swap":
                grant["payload_sha256"] = sha(b"different")
            elif family == "nonce_swap":
                grant["nonce"] = "different-nonce"
            elif family == "expired":
                grant["expires_at"] = 99
            elif family == "revoked":
                grant["epoch"] = 1
            grant["mac"] = mac(grant)
            if family == "invalid_mac":
                grant["mac"] = "0" * 64
            case = {
                "id": name, "family": family, "request": req, "grant": grant,
                "now": 100, "epoch": 2, "attempts": (2 if family == "replay" else 1),
                "evidence_available": family != "evidence_loss",
                "expected": (["allow", "deny"] if family == "replay" else
                             ["allow"] if family == "authorized" else
                             ["halt"] if family == "evidence_loss" else ["deny"]),
            }
            cases.append(case)
    return cases


def authorize(req: dict, grant: dict, now: int, epoch: int,
              used: bool, evidence: bool, mutant: str = "") -> tuple[str, str]:
    """Toy reference implementation, separate from case labels and scoring."""
    if mutant == "deny_all":
        return "deny", "mutant_false_denial"
    if not evidence and mutant != "evidence":
        return "halt", "evidence_unavailable"
    try:
        checks = (
            ("signature", hmac.compare_digest(grant["mac"], mac(grant))),
            ("principal", grant["principal"] == req["principal"]),
            ("action", grant["action"] == req["action"]),
            ("resource", grant["resource"] == req["resource"]),
            ("payload", grant["payload_sha256"] == sha(req["payload"].encode())),
            ("nonce", grant["nonce"] == req["nonce"]),
            ("expiry", isinstance(grant["expires_at"], int) and grant["expires_at"] >= now),
            ("epoch", grant["epoch"] == epoch),
            ("replay", not used),
        )
        parts = req["resource"].split("/") if isinstance(req["resource"], str) else []
        if (len(parts) < 3 or parts[0] != "sandbox" or
                any(p in ("", ".", "..") or "\\" in p or ":" in p for p in parts)):
            return "deny", "namespace_violation"
        for name, ok in checks:
            if not ok and name != mutant:
                return "deny", f"failed_{name}"
    except (KeyError, ValueError, TypeError, AttributeError, UnicodeError):
        return "deny", "malformed_input"
    return "allow", "authorized"


@dataclass
class Trace:
    head: str = GENESIS
    entries: list | None = None

    def __post_init__(self) -> None:
        if self.entries is None:
            self.entries = []

    def append(self, event: dict) -> None:
        record = {"prev": self.head, "event": event}
        record["hash"] = sha(encode(record))
        self.entries.append(record)
        self.head = record["hash"]

    def verify(self) -> bool:
        prev = GENESIS
        try:
            for record in self.entries:
                if record["prev"] != prev:
                    return False
                body = {"prev": record["prev"], "event": record["event"]}
                if sha(encode(body)) != record["hash"]:
                    return False
                prev = record["hash"]
        except (TypeError, KeyError, ValueError):
            return False
        return prev == self.head


def run_case(case: dict, mode: str, mutant: str = "") -> dict:
    trace = Trace()
    used = set()
    observed = []
    unreceipted = 0
    for attempt in range(case["attempts"]):
        if mode == "unguarded":
            verdict, reason = "allow", "unguarded"
        elif mode == "governed":
            verdict, reason = authorize(
                case["request"], case["grant"], case["now"], case["epoch"],
                case["request"]["nonce"] in used, case["evidence_available"], mutant,
            )
        else:
            raise ValueError("unsupported mode")
        if case["evidence_available"]:
            trace.append({"case": case["id"], "attempt": attempt + 1,
                          "verdict": verdict, "reason": reason})
        else:
            unreceipted += 1
        if verdict == "allow":
            used.add(case["request"]["nonce"])
        observed.append(verdict)
    return {"id": case["id"], "family": case["family"], "expected": case["expected"],
            "observed": observed, "matching": observed == case["expected"],
            "forbidden_commits": sum(e != "allow" and o == "allow"
                                     for e, o in zip(case["expected"], observed, strict=True)),
            "false_denials": sum(e == "allow" and o != "allow"
                                 for e, o in zip(case["expected"], observed, strict=True)),
            "unreceipted": unreceipted, "trace_head": trace.head,
            "trace_valid": trace.verify()}


def aggregate(results: list[dict]) -> dict:
    return {"scenarios": len(results),
            "oracle_matches": sum(r["matching"] for r in results),
            "forbidden_commits": sum(r["forbidden_commits"] for r in results),
            "false_denials": sum(r["false_denials"] for r in results),
            "unreceipted": sum(r["unreceipted"] for r in results),
            "invalid_traces": sum(not r["trace_valid"] for r in results)}


def evaluate() -> dict:
    cases = make_cases()
    reference = [run_case(c, "governed") for c in cases]
    baseline = [run_case(c, "unguarded") for c in cases]
    mutations = {m: [r["id"] for c in cases
                     if not (r := run_case(c, "governed", m))["matching"]] for m in MUTANTS}
    report = {"schema": "weaver-synthetic-agent-reliability-0.2",
              "scope": "OFFLINE_SYNTHETIC_REFERENCE_ONLY",
              "fixture_sha256": sha(encode(cases)),
              "reference": aggregate(reference), "baseline": aggregate(baseline),
              "mutants_detected": {m: bool(ids) for m, ids in mutations.items()},
              "mutant_failure_cases": mutations,
              "limitations": [
                  "No tested AI model, WEAVER, ANGELA, Cathedral or ZOREL runtime",
                  "All grants use a public HMAC fixture key with no secure custody",
                  "Simulated effects and trace; no independent observation or external witness",
                  "No concurrent execution, crash injection, filesystem or OS isolation",
              ]}
    report["report_sha256"] = sha(encode(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = evaluate()
    data = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data, end="")
    return int(report["reference"]["oracle_matches"] != 44 or
               report["reference"]["forbidden_commits"] != 0 or
               not all(report["mutants_detected"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
