"""QGS evidence ladder.

The ladder is deliberately represented as an IntEnum so admissibility gates can
compare evidence levels mechanically.  Names, labels, and narrative claims do
not matter at this boundary; only the receipt class does.
"""

from __future__ import annotations

from enum import IntEnum


class QGSLevel(IntEnum):
    """Quantized governance support / evidence level."""

    E0_CLAIM = 0
    E1_SPEC = 1
    E2_IMPLEMENTED = 2
    E3_RECEIPTED = 3
    E4_REPLICATED = 4
    E5_PRODUCTION_BOUND = 5


def evidence_sufficient(actual: QGSLevel, required: QGSLevel) -> bool:
    """Return whether ``actual`` meets or exceeds ``required`` evidence."""

    return actual >= required
