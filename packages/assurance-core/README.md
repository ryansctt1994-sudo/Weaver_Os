# Weaver Assurance Core

The lower trust layer for the three-repository Weaver master stack.

This package provides bounded, testable primitives for:

- canonical hashing of authority data;
- Ed25519 authorization envelopes;
- atomic persistent replay protection;
- append-only, hash-chained Chronicle logs;
- evidence receipts and fail-closed promotion decisions;
- a physical-reset-only hardware veto reference design.

It does not decide whether a human or institution is legitimate, prove that a
model is safe, or turn a local test into independent reproduction.

```text
capability != authority
proposal != permission
receipt != truth
local replay != independent reproduction
```

## Quick start

```bash
python -m pip install -e ".[dev]"
pytest -q
weaver-assurance --help
```

The RTL suite is optional:

```bash
make test-rtl  # requires iverilog + vvp
```

## Evidence dialect

| Level | Meaning |
|---|---|
| E0 | assertion or idea |
| E1 | internally coherent specification |
| E2 | locally executed with recorded tests |
| E3 | reproducible package with pinned inputs and replay materials |
| E4 | independent reproduction by a distinct witness |
| E5 | qualified domain validation |
| E6 | bounded operational adoption |

No component may promote its own output beyond the evidence supplied to the
promotion gate.

## Provenance

This clean-room v2 slice consolidates the strongest bounded patterns from
`Weaver_Os`, `Lumen`, `Weaver--Cathedral-`, `cathedral-verified`, and the
ZOREL/Chronicle doctrine. Third-party systems remain adapters or references;
their code is not silently vendored.

