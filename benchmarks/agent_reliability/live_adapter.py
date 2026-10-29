"""Thin offline adapter: real WEAVER CryptoVerifier -> observer-only dry-run log.

No executor, production authority, protected writes, model calls, network or OS sandbox.
The actual cryptographic gate is triadic_controls.crypto.verifier.CryptoVerifier.
The experimental grant-to-attempt policy lives HERE, NOT in CryptoVerifier.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import (
    CryptoVerifier,
    build_signing_object,
    compute_payload_hash,
)

from .portable import evaluate, make_cases, sha

ISSUER_ID = "11111111-1111-4111-8111-111111111111"
KEY_ID = "22222222-2222-4222-8222-222222222222"
SYSTEM_ID = "weaver-observer-fixture"
# Published, fixed TEST FIXTURE seed. NEVER a trusted key.
TEST_PRIVATE_KEY = bytes.fromhex("37" * 32)
PROTOCOL = "weaver-dry-observer-v0.3"
FROZEN_V02 = {
    "commit": "d72737d7fa51704e2af3d222ecc321e4839770c6",
    "branch": "freeze/agent-reliability-v0.2-20261029",
    "fixture_sha256": "68a0eb8bc8a41ccda9d799a743a9a29c13091f1ca888b80424ffe05e6700c75f",
    "report_sha256": "59841f8206222e65011550406be0cc6319a0b294a12976c4af28e08c3bdf6872",
}


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass
class IssueResult:
    valid: bool
    codes: list[str]


@dataclass
class LiveSession:
    """In-memory fixture authorization state; uses real CryptoVerifier for signatures.

    Revocation is a grant-ID deny-list maintained by this adapter following a
    verified REFUSAL_SIGNAL; the WEAVER verifier alone does NOT apply revocation.
    """
    verifier: CryptoVerifier = field(init=False)
    signer: ed25519.Ed25519PrivateKey = field(init=False)
    issued: dict[str, dict] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)
    used: set[tuple[str, str]] = field(default_factory=set)
    events: list[dict] = field(default_factory=list)
    sequence: int = 0

    def __post_init__(self) -> None:
        self.signer = ed25519.Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY)
        public = self.signer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        now = datetime.now(timezone.utc)
        registry = {
            "valid_from": iso(now - timedelta(hours=1)),
            "valid_until": iso(now + timedelta(hours=1)),
            "issuers": [{"issuer_id": ISSUER_ID, "key_id": KEY_ID, "public_key": b64(public),
                         "public_key_encoding": "base64url", "key_type": "ed25519",
                         "status": "ACTIVE",
                         "issued_at": iso(now - timedelta(hours=1)),
                         "expires_at": iso(now + timedelta(hours=1)),
                         "assigned_roles": ["fixture-issuer"]}],
            "roles": [{"role_id": "fixture-issuer", "separation_group": "fixture-group",
                       "may_grant_authority": True, "may_revoke_or_refuse": True,
                       "max_grant_level": 3, "can_participate_in_quorum": True,
                       "allowed_scopes": {"systems": [SYSTEM_ID], "regions": ["offline"],
                                          "tasks": ["dry-run"],
                                          "max_authority_duration_sec": 1800}}],
        }
        # No production schema or trusted registry-root signature is supplied.
        self.verifier = CryptoVerifier(registry, InMemoryReplayCache())

    def _envelope(self, payload: dict, kind: str, nonce: str, corrupt: bool = False) -> dict:
        now = datetime.now(timezone.utc)
        domain = {"system_id": SYSTEM_ID, "scope_hash": sha(canonical(payload["scope"])),
                  "valid_from": iso(now - timedelta(seconds=30)),
                  "valid_until": iso(now + timedelta(minutes=10))}
        payload_hash = compute_payload_hash(payload)
        signing_domain = f"triadic-controls:v0.4.0:{kind.lower()}"
        message = build_signing_object(signing_domain, kind, "0.4.0", payload_hash, domain, nonce)
        signature = b64(self.signer.sign(message))
        if corrupt:
            signature = b64(bytes(64))
        return {"payload_type": kind, "payload_schema_version": "0.4.0",
                "payload_hash_alg": "sha256", "payload_hash": payload_hash,
                "signing_domain": signing_domain, "replay_domain": domain,
                "signatures": [{"issuer_id": ISSUER_ID, "key_id": KEY_ID, "algorithm": "ed25519",
                                "signature_encoding": "base64url", "signature": signature,
                                "nonce_or_sequence": nonce, "signed_at": iso(now)}]}

    def issue(self, grant_id: str, claim: dict, *, corrupt_signature: bool = False) -> IssueResult:
        payload = {"grant_id": grant_id, "system_id": SYSTEM_ID, "authority_level": 3,
                   "scope": {"task": "dry-run", "region": "offline"}, **copy.deepcopy(claim)}
        envelope = self._envelope(
            payload, "AUTHORITY_TOKEN", f"issue:{grant_id}", corrupt_signature
        )
        result = self.verifier.verify_authority_token(
            envelope, requested_level=3, inner_payload=payload
        )
        if result.is_valid and grant_id not in self.issued and grant_id not in self.revoked:
            self.issued[grant_id] = copy.deepcopy(payload)
            return IssueResult(True, [])
        codes = result.failure_codes if not result.is_valid else ["DUPLICATE_GRANT"]
        return IssueResult(False, codes)

    def revoke(self, grant_id: str, *, corrupt_signature: bool = False) -> IssueResult:
        payload = {"grant_id": grant_id, "system_id": SYSTEM_ID,
                   "scope": {"task": "dry-run", "region": "offline"}}
        envelope = self._envelope(
            payload, "REFUSAL_SIGNAL", f"revoke:{grant_id}", corrupt_signature
        )
        result = self.verifier.verify_refusal_signal(
            envelope, requested_cap_level=3, inner_payload=payload
        )
        if result.is_valid and grant_id in self.issued:
            self.revoked.add(grant_id)
            return IssueResult(True, [])
        codes = result.failure_codes if not result.is_valid else ["UNKNOWN_GRANT"]
        return IssueResult(False, codes)

    def attempt(self, case_id: str, grant_id: str, request: dict, *,
                now: int = 100, epoch: int = 2, evidence_available: bool = True) -> dict:
        allowed_keys = {"principal", "action", "resource", "payload", "nonce"}
        reason = "grant_absent"
        verdict = "DENY"
        claim = self.issued.get(grant_id)
        if not evidence_available:
            reason, verdict = "observation_unavailable", "HALT"
        elif not isinstance(request, dict) or set(request) != allowed_keys or not all(
            isinstance(v, str) for v in request.values()
        ):
            reason = "invalid_request"
        elif claim is None:
            reason = "grant_absent"
        elif grant_id in self.revoked:
            reason = "grant_revoked"
        elif (
            claim.get("expires_at") is None
            or type(claim["expires_at"]) is not int
            or now > claim["expires_at"]
        ):
            reason = "expired"
        elif claim.get("epoch") != epoch:
            reason = "epoch_mismatch"
        elif (grant_id, request["nonce"]) in self.used:
            reason = "attempt_replay"
        elif request["principal"] != claim["principal"]:
            reason = "principal_mismatch"
        elif request["action"] != claim["action"]:
            reason = "action_mismatch"
        elif request["resource"] != claim["resource"]:
            reason = "resource_mismatch"
        elif sha(request["payload"].encode("utf-8")) != claim["payload_sha256"]:
            reason = "payload_mismatch"
        elif request["nonce"] != claim["nonce"]:
            reason = "nonce_mismatch"
        elif (request["action"] != "write" or not request["resource"].startswith("sandbox/")
              or any(part in ("", ".", "..") for part in request["resource"].split("/"))):
            reason = "non_demo_effect"
        else:
            verdict, reason = "ALLOW", "verified_grant_and_adapter_scope"
            self.used.add((grant_id, request["nonce"]))
        self.sequence += 1
        event = {"case": case_id, "attempt": self.sequence, "decision": verdict,
                 "reason": reason, "request": copy.deepcopy(request)}
        self.events.append(event)
        return event


def check_observer_response(inputs: list[dict], output: dict) -> bool:
    """Confirm observer did not omit, reorder or change any requested record."""
    if (not isinstance(output, dict) or output.get("protocol") != PROTOCOL
            or output.get("real_commits") != 0 or not isinstance(output.get("records"), list)
            or len(output["records"]) != len(inputs)):
        return False
    previous = "0" * 64
    for i, (sent, record) in enumerate(zip(inputs, output["records"], strict=True)):
        if (record.get("sequence") != i or record.get("prev") != previous
                or record.get("event") != sent or record.get("actual_effect") != "NONE"):
            return False
        expectation = None
        if sent["decision"] == "ALLOW":
            req = sent["request"]
            expectation = {"kind": "WOULD_WRITE", "target_label": req["resource"],
                           "payload_sha256": hashlib.sha256(req["payload"].encode()).hexdigest()}
        if record.get("would_effect") != expectation:
            return False
        content = {"sequence": i, "prev": previous, "event": sent,
                   "would_effect": expectation, "actual_effect": "NONE"}
        previous = sha(canonical(content))
        if record.get("hash") != previous:
            return False
    return output.get("head") == previous


def observe_in_subprocess(events: list[dict], *, script: Path | None = None) -> dict:
    """Run a fixed stdio-only observer in a separate *same-host* Python process.

    -I isolates Python import startup; it does NOT create an OS security sandbox.
    If the process is unavailable or malformed, return an UNKNOWN result, never
    a forged successful receipt or implied absence of effects.
    """
    worker = script if script is not None else Path(__file__).with_name("observer_worker.py")
    wire = json.dumps({"protocol": PROTOCOL, "events": events}, separators=(",", ":"))
    try:
        run = subprocess.run(
            [sys.executable, "-I", str(worker)], input=wire, text=True,
            capture_output=True, check=False, timeout=10,
        )
        if run.returncode != 0 or len(run.stdout) > 3_000_000:
            raise ValueError("observer_failed")
        output = json.loads(run.stdout)
        if not check_observer_response(events, output):
            raise ValueError("observer_receipt_mismatch")
        return output
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, json.JSONDecodeError):
        return {"protocol": PROTOCOL, "records": [], "head": None,
                "real_commits": None, "observer_classification": "UNKNOWN_OBSERVATION"}


def evaluate_live() -> dict:
    frozen = evaluate()
    if (frozen["fixture_sha256"] != FROZEN_V02["fixture_sha256"]
            or frozen["report_sha256"] != FROZEN_V02["report_sha256"]):
        raise RuntimeError("FROZEN_V02_DRIFT: stop; v0.2 content differs")
    decisions: list[dict] = []
    issues: list[dict] = []
    events: list[dict] = []
    for case in make_cases():
        session = LiveSession()
        grant_id = f"fixture-{case['id']}"
        claim = {key: copy.deepcopy(case["grant"][key]) for key in
                 ("principal", "action", "resource", "payload_sha256",
                  "nonce", "expires_at", "epoch")}
        result = session.issue(grant_id, claim, corrupt_signature=case["family"] == "invalid_mac")
        issues.append({"case": case["id"], "grant_issued": result.valid,
                       "gate_failure_codes": result.codes})
        for _ in range(case["attempts"]):
            event = session.attempt(case["id"], grant_id, case["request"],
                                    now=case["now"], epoch=case["epoch"],
                                    evidence_available=case["evidence_available"])
            decisions.append(event)
            if case["evidence_available"]:
                events.append(event)
    # Four additions exercise the ACTUAL WEAVER refusal verifier rather than
    # interpreting v0.2's stale epoch as signed grant revocation.
    for i, case in enumerate((c for c in make_cases() if c["family"] == "authorized"), start=1):
        session = LiveSession()
        grant_id = f"revocation-{i:02d}"
        claim = {key: case["grant"][key] for key in
                 ("principal", "action", "resource", "payload_sha256",
                  "nonce", "expires_at", "epoch")}
        issued = session.issue(grant_id, claim)
        revoked = session.revoke(grant_id)
        issues.append({"case": grant_id, "grant_issued": issued.valid,
                       "refusal_verified": revoked.valid,
                       "gate_failure_codes": issued.codes + revoked.codes})
        event = session.attempt(grant_id, grant_id, case["request"])
        decisions.append(event)
        events.append(event)
    observer = observe_in_subprocess(events)
    observed = len(observer["records"])
    expected = {"allow": "ALLOW", "deny": "DENY", "halt": "HALT"}
    expected_pairs = [(case["id"], value) for case in make_cases() for value in case["expected"]]
    seen_pairs = [(e["case"], e["decision"]) for e in decisions[:48]]
    matches = seen_pairs == [(name, expected[v]) for name, v in expected_pairs]
    report = {"schema": "weaver-observer-adapter-v0.3",
              "scope": "REAL_CRYPTO_VERIFIER_DRY_RUN_OBSERVER_ONLY",
              "frozen_v02": FROZEN_V02,
              "actual_weaver_path": "triadic_controls.crypto.verifier.CryptoVerifier",
              "reference_case_match": matches, "grant_events": issues,
              "attempts": len(decisions), "allow": sum(e["decision"] == "ALLOW" for e in decisions),
              "deny": sum(e["decision"] == "DENY" for e in decisions),
              "halt": sum(e["decision"] == "HALT" for e in decisions),
              "observer_records": observed, "observer_head": observer["head"],
              "unobserved": len(decisions) - observed,
              "observer_integrity": (observed == len(events) and
                                     observer["observer_classification"] != "UNKNOWN_OBSERVATION"),
              "actual_commits": 0 if observer["real_commits"] == 0 else None,
              "observation": [{"case": record["event"]["case"],
                               "decision": record["event"]["decision"],
                               "would_effect": record["would_effect"], "hash": record["hash"]}
                              for record in observer["records"]],
              "unobserved_case_ids": [e["case"] for e in decisions if e not in events],
              "limitations": [
                  "Same-host worker is not an OS sandbox or independent witness",
                  "Grant lifecycle and resource binding are adapter logic",
                  "Public test-signing key and unsigned local registry",
                  "No actual operation, write, persistent replay or hardware effect",
                              "Frozen v0.2 corpus was reused; shared oracle assumptions remain",
                              "No production authority; E2 ceiling / W0 / O0 HOLD"]}
    report["report_sha256"] = sha(canonical(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="WEAVER non-destructive observer adapter")
    parser.add_argument("--out", type=Path, help="Optional JSON report path; no effect target")
    args = parser.parse_args()
    report = evaluate_live()
    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content, encoding="utf-8")
    print(content, end="")
    return int(not report["reference_case_match"] or not report["observer_integrity"]
               or report["actual_commits"] != 0 or report["unobserved"] != 4)


if __name__ == "__main__":
    raise SystemExit(main())
