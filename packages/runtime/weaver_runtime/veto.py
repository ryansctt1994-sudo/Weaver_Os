"""Software twin of the Lucifer Latch RTL (``hardware/lucifer_latch/lucifer_latch.v``).

The twin is cycle-accurate at the register level. Each ``step`` is one rising clock
edge, and next-state values are computed from the *current* registers, as Verilog
nonblocking assignments are. Asynchronous reset is modelled as resetting the
registers on any step where ``rst_n`` is low. Outputs are only compared after edges,
where the two are equivalent.

Behaviour copied from the RTL, including the parts that are easy to misread:

- **ARMED.** ``trigger_in`` or ``threat_level >= 191`` on an edge moves to EVALUATING
  and clears the timing counter.
- **EVALUATING.** The counter runs to 68,000. On the next edge the latch locks. So
  ``latch_state`` and ``veto_signal`` rise on the 68,001st edge after the triggering
  edge. **The veto is not asserted during EVALUATING,** and dropping the trigger does
  not cancel it: only reset leaves this state.
- **TRIGGERED.** Permanent until reset. Unknown state encodings also go to TRIGGERED.
- ``status_led`` is 0 when ARMED, bit 23 of a free-running 24-bit counter when
  EVALUATING, and 1 when TRIGGERED.

This is a simulation model, not hardware enforcement. Agreement with the RTL is shown
by replaying shared vectors through both (``hardware/lucifer_latch/vectors``). Nothing
here says anything about silicon.
"""

from __future__ import annotations

from dataclasses import dataclass

TIMING_FLOOR_CYCLES = 68000
THREAT_THRESHOLD = 191
BLINK_MASK = (1 << 24) - 1

STATE_ARMED = 0
STATE_EVALUATING = 1
STATE_TRIGGERED = 2


@dataclass(frozen=True)
class LatchOutputs:
    state: int
    latch_state: int
    veto_signal: int
    status_led: int


class LuciferLatchTwin:
    """Register-level model of ``lucifer_latch``."""

    def __init__(self) -> None:
        self._reset_registers()

    def _reset_registers(self) -> None:
        self.current_state = STATE_ARMED
        self.latch_state = 0
        self.veto_signal = 0
        self.status_led = 0
        self.timing_counter = 0
        self.trigger_latched = 0
        self.blink_counter = 0

    def outputs(self) -> LatchOutputs:
        return LatchOutputs(self.current_state, self.latch_state, self.veto_signal, self.status_led)

    @staticmethod
    def _check_inputs(rst_n: int, trigger_in: int, threat_level: int) -> None:
        if rst_n not in (0, 1) or trigger_in not in (0, 1):
            raise ValueError("rst_n and trigger_in must be 0 or 1")
        if not isinstance(threat_level, int) or not 0 <= threat_level <= 255:
            raise ValueError("threat_level must be an integer in 0..255")

    def step(self, *, rst_n: int, trigger_in: int, threat_level: int) -> LatchOutputs:
        """Advance one rising clock edge."""
        self._check_inputs(rst_n, trigger_in, threat_level)
        if not rst_n:
            self._reset_registers()
            return self.outputs()

        old_blink = self.blink_counter
        self.blink_counter = (old_blink + 1) & BLINK_MASK
        state = self.current_state
        if state == STATE_ARMED:
            self.status_led = 0
            if trigger_in or threat_level >= THREAT_THRESHOLD:
                self.trigger_latched = 1
                self.timing_counter = 0
                self.current_state = STATE_EVALUATING
        elif state == STATE_EVALUATING:
            self.status_led = (old_blink >> 23) & 1
            if self.timing_counter < TIMING_FLOOR_CYCLES:
                self.timing_counter += 1
            else:
                self.current_state = STATE_TRIGGERED
                self.latch_state = 1
                self.veto_signal = 1
        elif state == STATE_TRIGGERED:
            self.status_led = 1
            self.latch_state = 1
            self.veto_signal = 1
        else:  # unknown encoding: fail safe
            self.current_state = STATE_TRIGGERED
            self.latch_state = 1
            self.veto_signal = 1
        return self.outputs()

    def run(
        self, cycles: int, *, rst_n: int, trigger_in: int, threat_level: int
    ) -> LatchOutputs:
        """Advance ``cycles`` edges with constant inputs.

        Two cases are skipped ahead exactly, because each edge in them changes only the
        blink counter: TRIGGERED with reset high, and ARMED with neither arming
        condition. Everything else is stepped edge by edge. ``tests/hardware`` checks
        that the skip-ahead matches plain stepping.
        """
        if not isinstance(cycles, int) or cycles < 1:
            raise ValueError("cycles must be a positive integer")
        self._check_inputs(rst_n, trigger_in, threat_level)
        remaining = cycles
        while remaining:
            idle_armed = (
                self.current_state == STATE_ARMED
                and not trigger_in
                and threat_level < THREAT_THRESHOLD
            )
            if rst_n and (self.current_state == STATE_TRIGGERED or idle_armed) and remaining > 1:
                self.step(rst_n=rst_n, trigger_in=trigger_in, threat_level=threat_level)
                remaining -= 1
                self.blink_counter = (self.blink_counter + remaining) & BLINK_MASK
                return self.outputs()
            self.step(rst_n=rst_n, trigger_in=trigger_in, threat_level=threat_level)
            remaining -= 1
        return self.outputs()

    def run_stepwise(
        self, cycles: int, *, rst_n: int, trigger_in: int, threat_level: int
    ) -> LatchOutputs:
        """Reference path with no skip-ahead, for equivalence tests."""
        for _ in range(cycles):
            self.step(rst_n=rst_n, trigger_in=trigger_in, threat_level=threat_level)
        return self.outputs()
