"""Negative controls for the Lucifer Latch differential testbench.

A differential testbench is only evidence if it can fail. This script runs it once on
the real RTL and vectors (it must pass), then on deliberately broken copies (each must
fail with at least one mismatch):

- ``flip-final-latch``: one expected final value flipped in the vector file;
- ``corrupt-long-checksum``: the expected checksum of the 8,388,600-cycle segment changed;
- ``rtl-threshold-192``: RTL threat threshold 191 -> 192;
- ``rtl-floor-67999``: RTL timing floor 68000 -> 67999;
- ``rtl-veto-glitch``: RTL pulses ``veto_signal`` for one cycle, 100 cycles into
  EVALUATING, and is back to normal before any segment ends. A comparison made only at
  segment boundaries misses this one. The per-cycle checksum is what catches it.

Needs ``iverilog`` and ``vvp`` on PATH. Exit 0 only if every expectation holds.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware" / "lucifer_latch"
RTL = HW / "lucifer_latch.v"
TB = HW / "tb_lucifer_latch_vectors.v"
VECTORS = HW / "vectors" / "lucifer_latch_vectors.txt"
LONG_SEGMENT = "8388600"

RTL_MUTATIONS = {
    "rtl-threshold-192": ("THREAT_THRESHOLD    = 8'd191", "THREAT_THRESHOLD    = 8'd192"),
    "rtl-floor-67999": ("TIMING_FLOOR_CYCLES = 17'd68000", "TIMING_FLOOR_CYCLES = 17'd67999"),
    "rtl-veto-glitch": (
        "                    timing_counter <= timing_counter + 1'b1;\n",
        "                    timing_counter <= timing_counter + 1'b1;\n"
        "                    veto_signal    <= (timing_counter == 17'd100);\n",
    ),
}


def _mutate_text(text: str, old: str, new: str, name: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{name}: mutation anchor not found exactly once")
    return text.replace(old, new, 1)


def _flip_final_latch(lines: list[str]) -> list[str]:
    fields = lines[5].split()
    fields[5] = str(1 - int(fields[5]))
    return lines[:5] + [" ".join(fields)] + lines[6:]


def _corrupt_long_checksum(lines: list[str]) -> list[str]:
    out = list(lines)
    for index, line in enumerate(out):
        fields = line.split()
        if fields[0] == LONG_SEGMENT:
            fields[8] = str((int(fields[8]) + 1) % (1 << 32))
            out[index] = " ".join(fields)
            return out
    raise SystemExit("corrupt-long-checksum: long segment not found")


def run(rtl: Path, vectors: Path, work: Path) -> tuple[int, int | None]:
    binary = work / "tb.vvp"
    subprocess.run(
        ["iverilog", "-g2012", "-o", str(binary), str(TB), str(rtl)], check=True
    )
    proc = subprocess.run(
        ["vvp", "-n", str(binary), f"+VECTORS={vectors}"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    found = re.search(r"MISMATCHES: (\d+)", proc.stdout)
    return proc.returncode, int(found.group(1)) if found else None


def main() -> int:
    results = []
    with tempfile.TemporaryDirectory(prefix="latch-negative-") as directory:
        work = Path(directory)
        cases: list[tuple[str, Path, Path, bool]] = [("baseline", RTL, VECTORS, True)]
        lines = VECTORS.read_text(encoding="ascii").splitlines()
        for name, transform in (
            ("flip-final-latch", _flip_final_latch),
            ("corrupt-long-checksum", _corrupt_long_checksum),
        ):
            path = work / f"{name}.txt"
            path.write_text("\n".join(transform(lines)) + "\n", encoding="ascii")
            cases.append((name, RTL, path, False))
        source = RTL.read_text(encoding="utf-8")
        for name, (old, new) in RTL_MUTATIONS.items():
            path = work / f"{name}.v"
            path.write_text(_mutate_text(source, old, new, name), encoding="utf-8")
            cases.append((name, path, VECTORS, False))

        for name, rtl, vectors, should_pass in cases:
            returncode, mismatches = run(rtl, vectors, work)
            if should_pass:
                ok = returncode == 0 and mismatches == 0
            else:
                ok = returncode != 0 and (mismatches or 0) > 0
            results.append(
                {
                    "case": name,
                    "expected": "pass" if should_pass else "fail",
                    "returncode": returncode,
                    "mismatches": mismatches,
                    "ok": ok,
                }
            )
            print(f"{'OK  ' if ok else 'BAD '} {name}: exit={returncode} mismatches={mismatches}")
    print(json.dumps({"schema": "latch-negative-controls-1", "results": results}, indent=2))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
