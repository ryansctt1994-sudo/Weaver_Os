"""Lucifer Latch software twin: spec properties, shared vectors, and RTL provenance.

The RTL side of the shared vectors runs in CI (``.github/workflows/hardware-sim.yml``)
with Icarus Verilog. These tests run the twin side, assert spec properties directly,
and pin the RTL sources to cathedral-verified.
"""

import hashlib
import random
import re
from pathlib import Path

import pytest
from weaver_runtime.veto import (
    STATE_ARMED,
    STATE_EVALUATING,
    STATE_TRIGGERED,
    THREAT_THRESHOLD,
    TIMING_FLOOR_CYCLES,
    LuciferLatchTwin,
)

from tools import gen_latch_vectors

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / "hardware" / "lucifer_latch"
VECTORS = HW / "vectors" / "lucifer_latch_vectors.txt"

# cathedral-verified @ 1c4181714b48dd9d9616a0bebbb4fef8532deff8 (RTL last changed in 76a7f7b)
CATHEDRAL_SHA256 = {
    "lucifer_latch.v": "e699f02a156195fea19f28d71aecc21b480783c981f221913660735415037867",
    "tb_lucifer_latch.v": "4fa7bdf6f3203396293c0b5d74eb4f4ea98fd0ca5ec4cbd7947f90e4121dcc87",
}


def armed_twin() -> LuciferLatchTwin:
    twin = LuciferLatchTwin()
    twin.run(4, rst_n=0, trigger_in=0, threat_level=0)
    twin.run(10, rst_n=1, trigger_in=0, threat_level=0)
    return twin


def edges_until_latch(twin: LuciferLatchTwin, limit: int = 70000) -> int:
    for edge in range(1, limit + 1):
        if twin.step(rst_n=1, trigger_in=0, threat_level=0).latch_state:
            return edge
    raise AssertionError("latch never fired")


# --- RTL provenance and constants ------------------------------------------


@pytest.mark.parametrize("name", sorted(CATHEDRAL_SHA256))
def test_rtl_is_byte_identical_to_cathedral(name):
    assert hashlib.sha256((HW / name).read_bytes()).hexdigest() == CATHEDRAL_SHA256[name]


def test_twin_constants_match_rtl_localparams():
    rtl = (HW / "lucifer_latch.v").read_text()
    floor = re.search(r"TIMING_FLOOR_CYCLES\s*=\s*17'd(\d+)", rtl)
    threshold = re.search(r"THREAT_THRESHOLD\s*=\s*8'd(\d+)", rtl)
    assert floor and int(floor.group(1)) == TIMING_FLOOR_CYCLES
    assert threshold and int(threshold.group(1)) == THREAT_THRESHOLD


# --- shared vectors -----------------------------------------------------------


def test_vector_file_matches_generator():
    assert gen_latch_vectors.main(["--check"]) == 0


def test_twin_replays_shared_vectors():
    twin = LuciferLatchTwin()
    lines = VECTORS.read_text(encoding="ascii").splitlines()
    assert len(lines) > 1500
    for number, line in enumerate(lines):
        cycles, rst_n, trig, threat, state, latch, veto, led = map(int, line.split())
        out = twin.run(cycles, rst_n=rst_n, trigger_in=trig, threat_level=threat)
        assert (out.state, out.latch_state, out.veto_signal, out.status_led) == (
            state,
            latch,
            veto,
            led,
        ), f"segment {number}"


def test_vectors_cover_every_state_and_the_blink_bit():
    rows = [tuple(map(int, line.split())) for line in VECTORS.read_text().splitlines()]
    assert {row[4] for row in rows} == {STATE_ARMED, STATE_EVALUATING, STATE_TRIGGERED}
    assert any(row[4] == STATE_EVALUATING and row[7] == 1 for row in rows)
    assert any(row[1] == 0 for row in rows)


# --- spec properties (asserted on the twin, independent of the RTL) -----------


def test_latch_fires_exactly_68001_edges_after_a_trigger_pulse():
    twin = armed_twin()
    assert twin.step(rst_n=1, trigger_in=1, threat_level=0).state == STATE_EVALUATING
    assert edges_until_latch(twin) == TIMING_FLOOR_CYCLES + 1


def test_veto_is_not_asserted_while_evaluating():
    twin = armed_twin()
    twin.step(rst_n=1, trigger_in=1, threat_level=0)
    for _ in range(TIMING_FLOOR_CYCLES):
        out = twin.step(rst_n=1, trigger_in=0, threat_level=0)
        assert out.state == STATE_EVALUATING and out.veto_signal == 0 and out.latch_state == 0


def test_threshold_is_191():
    below = armed_twin()
    assert below.run(10000, rst_n=1, trigger_in=0, threat_level=190).state == STATE_ARMED
    at = armed_twin()
    assert at.step(rst_n=1, trigger_in=0, threat_level=191).state == STATE_EVALUATING


def test_dropping_the_trigger_does_not_cancel_evaluation():
    twin = armed_twin()
    twin.step(rst_n=1, trigger_in=0, threat_level=255)
    assert edges_until_latch(twin) == TIMING_FLOOR_CYCLES + 1


def test_triggered_is_irreversible_without_reset():
    twin = armed_twin()
    twin.step(rst_n=1, trigger_in=1, threat_level=0)
    edges_until_latch(twin)
    rng = random.Random(7)
    for _ in range(20000):
        out = twin.step(rst_n=1, trigger_in=rng.randint(0, 1), threat_level=rng.randint(0, 255))
        assert (out.state, out.latch_state, out.veto_signal, out.status_led) == (2, 1, 1, 1)


def test_only_reset_clears_and_reset_aborts_evaluation():
    twin = armed_twin()
    twin.step(rst_n=1, trigger_in=1, threat_level=0)
    twin.run(1000, rst_n=1, trigger_in=0, threat_level=0)
    out = twin.step(rst_n=0, trigger_in=1, threat_level=255)
    assert (out.state, out.latch_state, out.veto_signal, out.status_led) == (0, 0, 0, 0)
    assert twin.timing_counter == 0 and twin.blink_counter == 0


def test_unknown_state_encoding_fails_safe():
    twin = armed_twin()
    twin.current_state = 3
    out = twin.step(rst_n=1, trigger_in=0, threat_level=0)
    assert (out.state, out.latch_state, out.veto_signal) == (STATE_TRIGGERED, 1, 1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rst_n": 2, "trigger_in": 0, "threat_level": 0},
        {"rst_n": 1, "trigger_in": -1, "threat_level": 0},
        {"rst_n": 1, "trigger_in": 0, "threat_level": 256},
        {"rst_n": 1, "trigger_in": 0, "threat_level": 1.5},
    ],
)
def test_inputs_are_validated(kwargs):
    with pytest.raises(ValueError):
        LuciferLatchTwin().step(**kwargs)


# --- fast path equivalence ------------------------------------------------------


def test_skip_ahead_matches_plain_stepping():
    rng = random.Random(20261107)
    fast, slow = LuciferLatchTwin(), LuciferLatchTwin()
    for _ in range(400):
        cycles = rng.choice([1, 2, rng.randint(3, 400), rng.randint(400, 70000)])
        inputs = {
            "rst_n": 0 if rng.random() < 0.05 else 1,
            "trigger_in": 1 if rng.random() < 0.05 else 0,
            "threat_level": rng.randint(0, 255),
        }
        fast.run(cycles, **inputs)
        slow.run_stepwise(cycles, **inputs)
        assert vars(fast) == vars(slow)
