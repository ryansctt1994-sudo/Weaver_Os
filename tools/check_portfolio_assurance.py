"""Fail-closed validation of the *candidate snapshot*, not cross-repository security certification.

Only stdlib. No network calls, code execution from listed repositories, signing,
or promotion. A PASS here establishes metadata consistency of this input only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "governance/portfolio/control_snapshot_2026-11-09.json"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPO = re.compile(r"^ryansctt1994-sudo/[A-Za-z0-9_.-]+$")
_GATE_IDS = {"G0", "G1", "G2", "G3", "G4", "G5"}
_RISK_IDS = {"PORT-RISK-001", "PORT-RISK-002", "PORT-RISK-003", "PORT-RISK-004"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def read(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda constant: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON number: {constant}")
        ),
    )


def check(doc: dict) -> list[str]:
    errors = []
    if not isinstance(doc, dict):
        return ["root must be an object"]
    if doc.get("schema_version") != "weaver.portfolio-control.v0.1":
        errors.append("unexpected schema version")
    if doc.get("status") != "PROPOSED_UNRATIFIED":
        errors.append("snapshot may not ratify itself")
    review = doc.get("review") or {}
    if review.get("independent") is not False or not review.get("reviewer"):
        errors.append("reviewer must be named and non-independent")
    if not review.get("exclusions"):
        errors.append("review scope exclusions required")

    inventory = doc.get("inventory") or {}
    repos = inventory.get("repositories") or []
    if inventory.get("account") != "ryansctt1994-sudo":
        errors.append("account mismatch")
    if inventory.get("live_inventory_enforced") is not False:
        errors.append("cannot claim live inventory enforcement")
    if not isinstance(repos, list) or not repos:
        errors.append("repository inventory missing")
        repos = []
    if inventory.get("observed_count") != len(repos):
        errors.append("inventory observed_count differs from entries")
    seen = set()
    for item in repos:
        if not isinstance(item, dict):
            errors.append("inventory item is not an object")
            continue
        name = item.get("repository")
        if not isinstance(name, str) or not _REPO.fullmatch(name):
            errors.append(f"invalid repository identity: {name!r}")
            continue
        if name in seen:
            errors.append(f"duplicate repository: {name}")
        seen.add(name)
        if (item.get("inventory_classification") != "INVENTORIED_ONLY"
                or item.get("claim_coverage") != "NOT_AUDITED"
                or item.get("auto_promotion") is not False):
            errors.append(f"unearned repository verification/promotion: {name}")

    subjects = doc.get("subjects") or []
    if not subjects:
        errors.append("no pinned subjects")
    subject_repos = set()
    for s in subjects:
        if not isinstance(s, dict) or not _SHA.fullmatch(str(s.get("commit", ""))):
            errors.append("subject must have exact 40-character commit SHA")
            continue
        subject_repos.add(s.get("repository"))
        if s.get("repository") not in seen:
            errors.append("subject outside observed inventory")
    if "ryansctt1994-sudo/Weaver_Os" not in subject_repos:
        errors.append("canonical Weaver subject absent")

    ceiling = doc.get("portfolio_ceiling") or {}
    required_ceiling = {
        "evidence": "E2", "witness": "W0", "authority": "O0",
        "production": False, "promotion_gate": "HOLD", "signoff_ref": None,
    }
    for key, value in required_ceiling.items():
        if ceiling.get(key) != value:
            errors.append(f"forbidden ceiling/promotion change: {key}")
    if not ceiling.get("effective_basis"):
        errors.append("ceiling policy source unpinned")

    claims = doc.get("claim_register") or []
    identifiers = set()
    if not claims:
        errors.append("claim register empty")
    for c in claims:
        if not isinstance(c, dict):
            errors.append("malformed claim")
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or cid in identifiers:
            errors.append("missing or duplicate claim id")
        identifiers.add(cid)
        if not c.get("does_not_establish") or not c.get("evidence_refs"):
            errors.append(f"{cid}: evidence and explicit limitations required")
        if c.get("disposition") in {"PASS", "INDEPENDENT", "PRODUCTION", "RATIFIED"}:
            errors.append(f"{cid}: claim promotion not admissible in candidate snapshot")
        if (c.get("kind") == "RESEARCH_HYPOTHESIS"
                and c.get("disposition") != "UNTESTED_AS_PORTFOLIO_WIDE_CLAIM"):
            errors.append(f"{cid}: research hypothesis silently promoted")
        if c.get("kind") == "DOCUMENTED_POLICY":
            if not _SHA.fullmatch(str(c.get("subject_sha", ""))):
                errors.append(f"{cid}: policy source SHA missing")
        for number_field in (
            "reported_pass", "reported_killed", "network_states", "distinct_snapshots"
        ):
            if number_field in c and (
                not _SHA.fullmatch(str(c.get("subject_sha", "")))
                or not c.get("denominator_scope")
            ):
                errors.append(f"{cid}: unpinned numerical metric {number_field}")
    if identifiers != {"WNS-PORT-001", "WNS-PORT-002", "WNS-PORT-003"}:
        errors.append("frozen claim set changed; require new review snapshot")

    gates = doc.get("gates") or []
    if (
        {g.get("id") for g in gates if isinstance(g, dict)} != _GATE_IDS
        or len(gates) != len(_GATE_IDS)
    ):
        errors.append("incomplete/duplicate G0-G5 gate register")
    for g in gates:
        if not isinstance(g, dict):
            errors.append("invalid gate")
            continue
        if g.get("status") not in {"HOLD", "NOT_EVALUATED"}:
            errors.append(f"{g.get('id')}: gate cannot self-close in candidate snapshot")
        if not g.get("closure_authority") or not g.get("does_not_establish"):
            errors.append(f"{g.get('id')}: authority and limitations required")
        if g.get("closure_evidence"):
            errors.append(f"{g.get('id')}: unsigned evidence cannot auto-close gate")

    risks = doc.get("risk_register") or []
    if (
        len(risks) != len(_RISK_IDS)
        or {r.get("id") for r in risks if isinstance(r, dict)} != _RISK_IDS
    ):
        errors.append("critical portfolio risk entries missing")
    for risk in risks:
        if not isinstance(risk, dict):
            errors.append("invalid risk")
            continue
        if (
            risk.get("status") != "OPEN"
            or not risk.get("owner")
            or not risk.get("required_evidence")
        ):
            errors.append(f"{risk.get('id')}: risk silently closed or unowned")
    falsification = doc.get("falsification") or {}
    if (falsification.get("experiment") != "AIX-001"
            or falsification.get("outcome") != "HOLD"
            or len(falsification.get("kill_conditions") or []) < 5
            or not falsification.get("minimum_positive_control")
            or len(falsification.get("uninformative_conditions") or []) < 3):
        errors.append("AIX falsification/positive control is absent or silently promoted")
    inv = doc.get("invalidation") or {}
    if not inv.get("rule") or not inv.get("dependencies"):
        errors.append("gate invalidation rule absent")
    for dep in inv.get("dependencies") or []:
        if (
            not dep.get("artifact")
            or not dep.get("gates")
            or not set(dep.get("gates", [])).issubset(_GATE_IDS)
        ):
            errors.append("invalid gate dependency")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", nargs="?", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    try:
        errors = check(read(args.snapshot))
    except (ValueError, OSError, UnicodeError, TypeError) as exc:
        print(f"FAIL: unparseable control snapshot: {exc}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        return 1
    print(
        "PASS: candidate metadata internally consistent; "
        "NOT a witness, promotion or live-inventory check"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
