# Triad multi-event verifier experiment

Run from a fresh clone:

```sh
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_triad_multiblock.py
```

The test builds a three-event Ed25519-signed JSONL chain, pins its final hash and signer fingerprint, and calls `tools/verify_triad_ledger.py`'s verification function. It changes a byte in the middle event, truncates the final event, substitutes a fully re-signed chain under a different key, removes a signature, and adds an empty line. Each case must fail. The verifier also exposes a CLI:

```sh
python tools/verify_triad_ledger.py path/to/ledger.jsonl \
  --expected-head <64-lowercase-hex-head> \
  --trusted-key-sha256 <64-lowercase-hex-key-fingerprint>
```

The expected head and signer fingerprint must come from an independent trusted channel for authenticity. If the attacker controls those inputs too, a complete rewrite can pass. The test uses generated keys and constructed data. It proves the implementation's behavior for those cases, not independent reproduction or real-world authority.

The existing `audit-package/formal/ccs/CCS_FORMAL_VERIFICATION_SCHEMA_v0.1.tla` declares invariants but explicitly uses uninterpreted predicates and says its proof obligations are not discharged. This experiment does not change that status. A bounded TLA+ model with recorded TLC execution is a separate task.
