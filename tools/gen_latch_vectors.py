"""Generate the shared Lucifer Latch vectors replayed by the RTL testbench and the twin.

Each output line is one segment, as eight integers:

    cycles rst_n trigger_in threat_level  exp_state exp_latch exp_veto exp_led

The inputs are held for ``cycles`` rising edges, and then the four expected values are
checked. Expected values come from ``weaver_runtime.veto.LuciferLatchTwin``. The RTL
testbench (``tb_lucifer_latch_vectors.v``) checks the same file against the Verilog, so
the twin and the RTL must agree at every segment boundary. Spec properties such as the
exact 68,001-edge delay are asserted separately, in ``tests/hardware``.

The output is deterministic: a fixed seed and no wall-clock input.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from weaver_runtime.veto import LuciferLatchTwin

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "hardware" / "lucifer_latch" / "vectors" / "lucifer_latch_vectors.txt"
SEED = 20261107
RANDOM_SEGMENTS = 1500
FLOOR = 68000

Segment = tuple[int, int, int, int]  # cycles, rst_n, trigger_in, threat_level


def directed() -> list[Segment]:
    s: list[Segment] = []
    s += [(4, 0, 0, 0), (100, 1, 0, 0)]  # reset, then idle ARMED
    s += [(100, 1, 0, 190)]  # just below threshold: stays ARMED
    s += [(1, 1, 1, 0)]  # trigger pulse: -> EVALUATING
    s += [(FLOOR, 1, 0, 0), (1, 1, 0, 0)]  # still EVALUATING after 68000, TRIGGERED on 68001
    s += [(500, 1, 0, 0), (50, 1, 1, 255), (1, 1, 0, 0), (25, 1, 1, 0)]  # irreversible
    s += [(4, 0, 1, 255)]  # reset wins over trigger and max threat
    s += [(1, 1, 0, 191), (FLOOR, 1, 0, 0), (1, 1, 0, 0)]  # threshold path, trigger dropped
    s += [(4, 0, 0, 0), (1, 1, 1, 0), (1000, 1, 0, 0), (2, 0, 0, 0)]  # reset aborts EVALUATING
    s += [(10, 1, 0, 0)]  # back to ARMED, idle
    # Push the free-running blink counter past bit 23, then evaluate: LED shows bit 23.
    s += [(4, 0, 0, 0), (8_388_600, 1, 0, 0), (1, 1, 1, 0), (16, 1, 0, 0), (FLOOR, 1, 0, 0)]
    s += [(1, 1, 0, 0), (100, 1, 0, 0)]
    return s


def randomized(rng: random.Random) -> list[Segment]:
    s: list[Segment] = []
    for _ in range(RANDOM_SEGMENTS):
        roll = rng.random()
        if roll < 0.04:
            cycles = rng.choice([FLOOR - 1, FLOOR, FLOOR + 1, FLOOR + 2])
        elif roll < 0.15:
            cycles = rng.randint(51, 3000)
        else:
            cycles = rng.randint(1, 50)
        rst_n = 0 if rng.random() < 0.05 else 1
        trigger = 1 if rng.random() < 0.03 else 0
        threat = rng.randint(191, 255) if rng.random() < 0.03 else rng.randint(0, 190)
        s.append((cycles, rst_n, trigger, threat))
    return s


def build() -> list[tuple[int, ...]]:
    twin = LuciferLatchTwin()
    rows: list[tuple[int, ...]] = []
    for cycles, rst_n, trigger, threat in directed() + randomized(random.Random(SEED)):
        out = twin.run(cycles, rst_n=rst_n, trigger_in=trigger, threat_level=threat)
        expected = (out.state, out.latch_state, out.veto_signal, out.status_led)
        rows.append((cycles, rst_n, trigger, threat, *expected))
    return rows


def render(rows: list[tuple[int, ...]]) -> str:
    return "".join(" ".join(str(v) for v in row) + "\n" for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="fail if --out is not up to date")
    args = parser.parse_args(argv)
    text = render(build())
    if args.check:
        current = args.out.read_text(encoding="ascii") if args.out.exists() else ""
        if current != text:
            print(f"FAIL: {args.out} is stale; rerun tools/gen_latch_vectors.py")
            return 1
        print(f"OK: {args.out} matches the generator")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="ascii")
    rows = text.count("\n")
    total = sum(int(line.split()[0]) for line in text.splitlines())
    print(f"wrote {rows} segments, {total} cycles to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
