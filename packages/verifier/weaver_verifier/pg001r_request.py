"""Strict reader and command-line entry point for PG-001R promotion requests.

``weaver_verifier.pg001r`` is held byte-identical to its Lumen-Nexus source (see
``tests/verifier/test_pg001r_identity.py``), including its own ``main()``, which reads a
request with plain ``json.loads``. That reader keeps the last of a duplicated key, so a
request file can show a reviewer one value -- an open contradiction, say -- and be
evaluated on another. It also lets a deeply nested body escape as a traceback, which
shares exit code 1 with "blocked".

This module is the supported entry point. It reads the request with WX-CJSON-1's strict
reader (``parse_strict``: duplicate keys, floats, ``NaN``, a byte-order mark and over-deep
nesting are refused), then applies the unchanged contract and evaluator. The decision is
printed as WX-CJSON-1 canonical JSON.

Exit codes: 0 eligible, 1 blocked, 2 input rejected. An eligibility result is not an
operational grant; see ``weaver_verifier.pg001r``.

    python -m weaver_verifier.pg001r_request REQUEST.json
"""

from __future__ import annotations

import sys
from pathlib import Path

from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict
from weaver_contracts.pg001r import ContractError, PromotionRequest

from .pg001r import evaluate

MAX_REQUEST_BYTES = 1 << 20


def load_request(data: bytes) -> PromotionRequest:
    """Parse request bytes strictly; raise ``ContractError`` on anything ambiguous."""
    if len(data) > MAX_REQUEST_BYTES:
        raise ContractError(f"request is larger than {MAX_REQUEST_BYTES} bytes")
    try:
        payload = parse_strict(data)
    except CanonicalizationError as exc:
        raise ContractError(f"request is not strict JSON: {exc}") from exc
    return PromotionRequest.from_mapping(payload)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m weaver_verifier.pg001r_request REQUEST.json", file=sys.stderr)
        return 2
    try:
        with Path(args[0]).open("rb") as handle:
            data = handle.read(MAX_REQUEST_BYTES + 1)
        request = load_request(data)
    except (OSError, ContractError) as exc:
        print(f"PG-001R input rejected: {exc}", file=sys.stderr)
        return 2
    decision = evaluate(request)
    sys.stdout.write(canonicalize(decision.to_primitive()).decode("utf-8") + "\n")
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
