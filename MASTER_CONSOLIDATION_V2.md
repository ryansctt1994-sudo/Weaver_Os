# Weaver Assurance Core — master consolidation v2

The new implementation lives in `packages/assurance-core/` so the existing
Weaver_OS history and experiments remain intact while the hardened core is
reviewed.

This package is the shared trust boundary for the three master repositories:

- canonical hashing that rejects ambiguous numeric encodings;
- Ed25519 authority envelopes with action, lifetime, level, and separated-quorum checks;
- atomic SQLite replay protection;
- fail-closed append-only Chronicle records with checkpoints;
- verifiable evidence receipts and cumulative E0–E6 promotion gates;
- a reference asynchronous hardware veto latch and simulation testbench.

The Python suite exercises tamper, replay, concurrency, expiry, truncation,
receipt, and promotion failure paths. RTL simulation remains a model, not
evidence of physical silicon behavior.
