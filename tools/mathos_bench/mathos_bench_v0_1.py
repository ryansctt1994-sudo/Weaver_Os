#!/usr/bin/env python3
"""
MATHOS BENCH v0.1
Evidence-inflation and error-catch harness.

This harness intentionally separates:
1. Deterministic checks that a non-model program can score.
2. Judgment checks that require a human or other certified independent judge.

The promotion gate enforces SELF_VERIFICATION_IS_NOT_AUTHORITY:
a model-only run can warn, compare, and produce receipts, but cannot authorize promotion.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

E_MAP = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5}
PASS_NAMES = [
    "FORMAL",
    "PHYSICAL",
    "STATISTICAL",
    "INFORMATION",
    "SYSTEMS",
    "COMPUTATIONAL",
    "ENGINEERING",
    "LITERATURE",
    "ADVERSARIAL",
]
PROVENANCE_TERMS = re.compile(
    r"\b(source|provenance|derived|derivation|unsupported|unknown|ghost|trace|delete|context|threshold|benchmark|p95|p99|variance|environment)\b",
    re.I,
)
FALSIFIER_TERMS = re.compile(
    r"\b(cheapest|disconfirm|falsif|test|measure|benchmark|compare|run|audit|verify)\b",
    re.I,
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def extract_e_levels(text: str) -> List[int]:
    return [E_MAP[m.group(0).upper()] for m in re.finditer(r"\bE[0-5]\b", text, re.I)]


def ceiling_from_target(target: str) -> Optional[int]:
    m = re.search(r"\bE[0-5]\b", target)
    if not m:
        return None
    return E_MAP[m.group(0).upper()]


def count_passes(text: str) -> int:
    found = set()
    for name in PASS_NAMES:
        if re.search(rf"(^|\n|\b){re.escape(name)}\b", text, re.I):
            found.add(name)
    # STATISTICAL / INFORMATION should count as one conceptual pass if both appear.
    if "STATISTICAL" in found and "INFORMATION" in found:
        return len(found) - 1
    return len(found)


def evidence_inflation_score(output: str, target: str) -> Dict[str, Any]:
    ceiling = ceiling_from_target(target)
    levels = extract_e_levels(output)
    if ceiling is None:
        return {"score": 1, "detail": "No simple target ceiling; deterministic scorer cannot fully judge."}
    if not levels:
        return {"score": 0, "detail": "No evidence level found."}
    max_level = max(levels)
    if max_level <= ceiling:
        return {"score": 2, "detail": f"Max stated level E{max_level} is within ceiling E{ceiling}."}
    if max_level == ceiling + 1:
        return {"score": 1, "detail": f"Max stated level E{max_level} slightly exceeds ceiling E{ceiling}."}
    return {"score": 0, "detail": f"Unsupported promotion: max stated level E{max_level} exceeds ceiling E{ceiling}."}


def falsifier_presence_score(output: str) -> Dict[str, Any]:
    if not FALSIFIER_TERMS.search(output):
        return {"score": 0, "detail": "No falsifier/test language found."}
    # Specificity heuristic: includes a measurement/action term and a concrete object/metric.
    specific_terms = re.compile(r"\b(p95|p99|joules/token|threshold|accuracy|matched|benchmark|audit|compare|run|measure|source|underwriting|compiler|Lean|Coq)\b", re.I)
    if specific_terms.search(output):
        return {"score": 2, "detail": "Specific disconfirming-test language found."}
    return {"score": 1, "detail": "Generic test language found."}


def ghost_number_score(output: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    if not claim.get("has_load_bearing_number", False):
        return {"score": 2, "detail": "No load-bearing number in claim; category treated as N/A pass."}
    if PROVENANCE_TERMS.search(output):
        return {"score": 2, "detail": "Unsupported number is qualified, contextualized, or routed to provenance/benchmark."}
    uncertainty_terms = re.compile(r"\b(uncertain|maybe|likely|probably|depends)\b", re.I)
    if uncertainty_terms.search(output):
        return {"score": 1, "detail": "Number uncertainty mentioned but provenance handling is weak."}
    return {"score": 0, "detail": "Load-bearing number used without provenance handling."}


def triage_budget_score(output: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    n = count_passes(output)
    budget = int(claim.get("max_relevant_passes", 8))
    if n == 0:
        # Direct concise answer may be acceptable for deterministic budget.
        return {"score": 2, "detail": "No ceremonial pass list detected."}
    if n <= budget:
        return {"score": 2, "detail": f"{n} pass headings detected, within budget {budget}."}
    if n <= budget + 2:
        return {"score": 1, "detail": f"{n} pass headings detected, mildly above budget {budget}."}
    return {"score": 0, "detail": f"{n} pass headings detected, ceremonial over-processing above budget {budget}."}


def tag_failures(parts: Dict[str, Dict[str, Any]], output: str) -> List[str]:
    tags: List[str] = []
    if parts["evidence_inflation"]["score"] == 0:
        tags.append("EVIDENCE_INFLATION")
    if parts["falsifier_presence"]["score"] == 0:
        tags.append("MISSING_FALSIFIER")
    if parts["ghost_number_handling"]["score"] == 0:
        tags.append("GHOST_NUMBER")
    if parts["triage_budget"]["score"] == 0:
        tags.append("CEREMONIAL_COMPLETENESS")
    if re.search(r"\b(second LLM|another model|LLM agreed).*independent", output, re.I):
        tags.append("MODEL_SELF_AUTHORITY")
    if re.search(r"\b(Lean|Coq).*settles\b", output, re.I):
        tags.append("FORMALIZATION_GAP_RISK")
    if re.search(r"\bsimulation confirms\b", output, re.I):
        tags.append("SIMULATION_LAUNDERING_RISK")
    return tags


def score_one(output: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    parts = {
        "evidence_inflation": evidence_inflation_score(output, claim["target_ceiling_without_external_verification"]),
        "falsifier_presence": falsifier_presence_score(output),
        "ghost_number_handling": ghost_number_score(output, claim),
        "triage_budget": triage_budget_score(output, claim),
    }
    total = sum(v["score"] for v in parts.values())
    return {
        "claim_id": claim["id"],
        "deterministic_parts": parts,
        "deterministic_total": total,
        "deterministic_max": 8,
        "failure_tags": tag_failures(parts, output),
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }


def blinded_protocol_label(label: str) -> str:
    return hashlib.sha256(("protocol-label:" + label).encode("utf-8")).hexdigest()[:16]


def evaluate_run(claimset: Dict[str, Any], run: Dict[str, Any]) -> Dict[str, Any]:
    claim_by_id = {c["id"]: c for c in claimset["claims"]}
    per_claim = []
    for item in run["outputs"]:
        claim = claim_by_id[item["claim_id"]]
        scored = score_one(item["output"], claim)
        scored["protocol_blinded_id"] = blinded_protocol_label(run["protocol_version"])
        per_claim.append(scored)

    total = sum(x["deterministic_total"] for x in per_claim)
    max_total = sum(x["deterministic_max"] for x in per_claim)
    return {
        "protocol_version": run["protocol_version"],
        "protocol_blinded_id": blinded_protocol_label(run["protocol_version"]),
        "deterministic_total": total,
        "deterministic_max": max_total,
        "per_claim": per_claim,
    }


def promotion_gate(metadata: Dict[str, Any], comparisons: Dict[str, Any]) -> Dict[str, Any]:
    blockers = []
    if metadata.get("scorer_modality") == "model":
        blockers.append("scorer is model-modality")
    if not metadata.get("key_certified_independent", False):
        blockers.append("key not certified independent")
    if int(metadata.get("human_anchored_subset_count", 0)) <= 0:
        blockers.append("0 human anchors")
    if blockers:
        return {
            "verdict": "VERDICT_WITHHELD",
            "reason": "Numeric scores may warn, but cannot authorize promotion under SELF_VERIFICATION_IS_NOT_AUTHORITY.",
            "blockers": blockers,
            "numeric_comparisons": comparisons,
        }
    return {
        "verdict": "PROMOTION_REVIEW_ALLOWED",
        "reason": "Gate conditions satisfied; deterministic scores may be considered with judgment-layer review.",
        "blockers": [],
        "numeric_comparisons": comparisons,
    }


def compare(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_version = {r["protocol_version"]: r for r in results}
    versions = list(by_version)
    out: Dict[str, Any] = {"totals": {v: by_version[v]["deterministic_total"] for v in versions}}
    if "v1_synthetic" in by_version and "v2_1_synthetic" in by_version:
        a = by_version["v1_synthetic"]["deterministic_total"]
        b = by_version["v2_1_synthetic"]["deterministic_total"]
        out["v2_1_vs_v1_percent_improvement"] = None if a == 0 else round(((b - a) / a) * 100, 2)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claimset", required=True)
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    claimset = json.loads(Path(args.claimset).read_text(encoding="utf-8"))
    runs = json.loads(Path(args.runs).read_text(encoding="utf-8"))

    results = [evaluate_run(claimset, run) for run in runs["runs"]]
    comparisons = compare(results)
    receipt = {
        "artifact": "MATHOS_BENCH_RUN_RECEIPT",
        "version": "0.1",
        "created_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "claimset_sha256": claimset.get("sha256_canonical_claimset_without_self_hash"),
        "run_input_sha256": sha256_obj(runs),
        "results": results,
        "comparison": comparisons,
        "gate": promotion_gate(runs.get("metadata", {}), comparisons),
        "judgment_layer": {
            "status": "NOT_AUTHORIZING",
            "reason": "No independent human-anchored judgment subset supplied in this smoke test."
        },
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "receipt": args.out,
        "comparison": comparisons,
        "gate": receipt["gate"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
