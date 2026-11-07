import os
import sys
from pathlib import Path

from weaver_runtime.ledger import ReceiptLedger

REPO = Path(__file__).resolve().parents[2]
CLOCK = "2026-11-07T10:00:00Z"
LEDGER_ID = "wx-test"


def fixed_clock() -> str:
    return CLOCK


def open_ledger(path, **kwargs) -> ReceiptLedger:
    kwargs.setdefault("ledger_id", LEDGER_ID)
    kwargs.setdefault("clock", fixed_clock)
    return ReceiptLedger(path, **kwargs)


def admit_n(ledger, n, start=0, actor="op-1"):
    return [
        ledger.admit(
            "STATE_TRANSITION",
            {"event": f"action_{i}", "actor": "L0:Steward", "value": i},
            actor_id=actor,
            policy_version="policy-v1",
        )
        for i in range(start, start + n)
    ]


def child_env() -> dict:
    env = dict(os.environ)
    paths = [
        REPO / "packages" / "contracts",
        REPO / "packages" / "runtime",
        REPO / "packages" / "verifier",
        REPO,
    ]
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in paths)
    return env


PYTHON = sys.executable
