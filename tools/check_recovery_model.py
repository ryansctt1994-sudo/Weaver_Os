"""Bounded recovery model, targeted mutations, and crash-window reachability probes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "audit-package" / "formal" / "tla+"


def check(jar: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    source = (FORMAL / "WeaverRecovery.tla").read_text()
    config = (FORMAL / "WeaverRecovery.cfg").read_text()
    probes = [("baseline", source, config, None)]
    changes = [
        (
            "dispatch-before-fsync",
            'phase[r] = "Ready" /\\ durable[r] = "Intent"',
            'phase[r] = "IntentBuffered" /\\ durable[r] = "Absent"',
            "Inv_DurableBeforeDispatch",
        ),
        (
            "fresh-nonce-bypass",
            '/\\ reconciliation \\in {"Reconciled", "Waived"}',
            "/\\ TRUE",
            "Inv_ReplacementRequiresResolution",
        ),
        (
            "recovery-fabricates-reject",
            'durable\' = [durable EXCEPT ![r] = "Indeterminate"]',
            'durable\' = [durable EXCEPT ![r] = "Reject"]',
            "Inv_UnknownNeverRedispatched",
        ),
        (
            "unstable-normalization",
            'THEN "Indeterminate" ELSE d[r]',
            'THEN "Indeterminate" ELSE IF d[r] = "Indeterminate" THEN "Intent" ELSE d[r]',
            "Inv_RecoveryIdempotent",
        ),
    ]
    for name, old, new, invariant in changes:
        if source.count(old) != 1:
            raise ValueError(f"mutation target drift: {name}")
        probes.append((name, source.replace(old, new), config, invariant))
    for effect in ("None", "Partial", "Complete"):
        probe = (
            '\nCrashWindowAbsent == ~ (durable[R1] = "Indeterminate"'
            f' /\\ effects[R1] = "{effect}")\n'
        )
        probes.append(
            (
                f"reachable-{effect.lower()}",
                source.replace("====", probe + "===="),
                config + "  CrashWindowAbsent\n",
                "CrashWindowAbsent",
            )
        )
    results = []
    for name, model, cfg, expected in probes:
        with tempfile.TemporaryDirectory(prefix="weaver-recovery-") as directory:
            path = Path(directory)
            (path / "WeaverRecovery.tla").write_text(model)
            (path / "WeaverRecovery.cfg").write_text(cfg)
            run = subprocess.run(
                [
                    "java",
                    "-cp",
                    str(jar.resolve()),
                    "tlc2.TLC",
                    "-deadlock",
                    "-config",
                    "WeaverRecovery.cfg",
                    "WeaverRecovery.tla",
                ],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=60,
            )
        log = run.stdout + run.stderr
        passed = (
            run.returncode == 0 and "No error has been found" in log
            if expected is None
            else run.returncode == 12 and f"Invariant {expected} is violated" in log
        )
        for suffix, text in (("tla", model), ("cfg", cfg), ("log", log)):
            (output / f"{name}.{suffix}").write_text(text)
        results.append(
            {
                "name": name,
                "passed": passed,
                "returncode": run.returncode,
                "expected_invariant": expected,
            }
        )
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.iterdir())
        if p.suffix in {"tla", "cfg", "log"}
    }
    report = {
        "schema": "weaver-recovery-model-check-1",
        "results": results,
        "artifacts_sha256": hashes,
        "scope": "two ordered attempts, one semantic operation; atomic durable records",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if not all(r["passed"] for r in results):
        raise SystemExit("recovery check failed; inspect retained report and logs")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jar", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check(args.jar, args.output)
    print(json.dumps(report["results"], indent=2))


if __name__ == "__main__":
    main()
