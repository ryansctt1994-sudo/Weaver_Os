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
  --trusted-key-sha256 <64-lowercase-hex-key-fingerprint> \
  --expected-file-sha256 <64-lowercase-hex-file-digest>
```

The expected head and signer fingerprint must come from an independent trusted channel for authenticity. If the attacker controls those inputs too, a complete rewrite can pass. The test uses generated keys and constructed data. It proves the implementation's behavior for those cases, not independent reproduction or real-world authority.

Verification reads the file once and verifies, parses, and hashes that same byte snapshot. Duplicate JSON keys and nonstandard numeric constants are rejected. A regression replaces the file after the read and confirms that verification still evaluates the captured bytes.

The optional file digest pins the exact bytes, including formatting. Without it, signatures and the head bind canonical event contents; an innocuous whitespace change can pass. With the digest supplied, that change fails. Obtain the file digest through the same independently trusted process as the other anchors.

The tests exercise all 32 Boolean combinations of three block-tamper flags, trusted key, and pinned head using real signed JSONL. Acceptance matches the `WitnessBoundary.Verify` predicate for these constructed cases. This is a bounded correspondence test, not a formal refinement proof or a check of every TLA+ transition.

The existing `audit-package/formal/ccs/CCS_FORMAL_VERIFICATION_SCHEMA_v0.1.tla` declares invariants but explicitly uses uninterpreted predicates and says its proof obligations are not discharged. That status remains unchanged. The separate `audit-package/formal/tla+/WitnessBoundary.tla` now has a recorded bounded TLC run and a pinned CI workflow; its scope is described in that directory's README.
