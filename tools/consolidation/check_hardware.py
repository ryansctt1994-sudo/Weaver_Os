"""Run simulation checks in a temporary directory; never program a board."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    for name in ("iverilog", "vvp"):
        if shutil.which(name) is None:
            raise SystemExit(f"required simulator missing: {name}")
    hw = ROOT / "hardware" / "lucifer_latch"
    with tempfile.TemporaryDirectory(prefix="weaver-board-simulation-") as directory:
        work = Path(directory)
        for name, sources in (
            (
                "tb_startup_reset",
                [
                    "lucifer_latch.v",
                    "arty_a7/sync_debounce.v",
                    "arty_a7/lucifer_arty_a7.v",
                    "arty_a7/tb_startup_reset.v",
                ],
            ),
            (
                "tb_arty_a7",
                [
                    "lucifer_latch.v",
                    "arty_a7/sync_debounce.v",
                    "arty_a7/lucifer_arty_a7.v",
                    "arty_a7/tb_arty_a7.v",
                ],
            ),
            ("tb_debounce_default", ["arty_a7/sync_debounce.v", "arty_a7/tb_debounce_default.v"]),
        ):
            binary = work / (name + ".vvp")
            subprocess.run(
                [
                    "iverilog",
                    "-g2012",
                    "-s",
                    name,
                    "-o",
                    str(binary),
                    *(str(hw / source) for source in sources),
                ],
                check=True,
                cwd=work,
                timeout=60,
            )
            subprocess.run(["vvp", "-n", str(binary)], check=True, cwd=work, timeout=120)


if __name__ == "__main__":
    main()
