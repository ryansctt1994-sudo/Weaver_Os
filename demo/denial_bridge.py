"""Bounded executable projection of WN-E2E state into a Lean-style state.

The projection is a candidate abstraction, not a Lean/Python refinement proof.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from demo.e2e_transaction import transition


@dataclass(frozen=True)
class ModelState:
    """Core.lean State shape; fixture receipts/audit are deliberately excluded."""

    grants: tuple = ()
    receipts: tuple = ()
    executed: tuple = ()


def project(protected: dict) -> ModelState:
    """Encode the complete three-field protected state as an opaque observation.

    The executed slot carries a state snapshot, not a claim that Python artifact
    commits are Lean execution events. Its purpose is to detect any mutation.
    """
    if set(protected) != {"authority", "artifact", "revision"}:
        raise ValueError("projection requires exact protected-state schema")
    if type(protected["authority"]) is not int or type(protected["revision"]) is not int:
        raise ValueError("invalid protected-state counters")
    if protected["authority"] < 0 or protected["revision"] < 0:
        raise ValueError("negative protected-state counter")
    if protected["artifact"] is not None and type(protected["artifact"]) is not str:
        raise ValueError("invalid artifact")
    # A tuple preserves field boundaries and distinguishes None from a string.
    return ModelState(
        executed=((protected["authority"], protected["artifact"], protected["revision"]),)
    )


def model_denied_step(state: ModelState, *, check: bool) -> ModelState:
    """Core.lean step's denied execute branch for check=false."""
    if check:
        raise ValueError("this bridge only models denied execution")
    return state


def check_denied_projection(
    state: dict, tx: dict, *, runtime: Callable = transition
) -> tuple[dict, dict]:
    """Check a single actual rejection against the modeled identity branch."""
    before = copy.deepcopy(state)
    model_before = project(before)
    after, receipt = runtime(copy.deepcopy(before), copy.deepcopy(tx))
    if receipt["verdict"] != "REJECT":
        raise ValueError("outside denied-execution bridge")
    if state != before:
        raise AssertionError("runtime mutated its input")
    if after != before or project(after) != model_denied_step(model_before, check=False):
        raise AssertionError("denied execution changed protected state")
    return after, receipt


def replay(state: dict, transactions: Iterable[dict]) -> dict:
    """Pure left fold over the real fixture transition; not a Lean theorem."""
    current = copy.deepcopy(state)
    for tx in transactions:
        current, _ = transition(current, copy.deepcopy(tx))
    return current
