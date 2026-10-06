# Local fail-closed spine

Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`  
Authority: `O0`

`tools/fail_closed_spine.py` and `verify_attestations.py --scope local-spine`
share the same pure canonical chain mechanics in `tools/spine_hash.py`.

This is intentionally separate from E3.5.

```text
LocalSpineVerified != E3.5
E3.5 != IndependentReproduction
Evidence != Authority
```

## Local mechanics

Run:

```bash
python3 tools/fail_closed_spine.py
python3 tools/fail_closed_spine.py --tamper
make verify-spine
```

For the source state at `ee725f7cf923d86d915900fc93ef2e3f6e5eef1c`:

```text
authority_ledger_hash = 82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9
ordered_chain_head    = e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85
```

The local verifier derives these values from `authority_ledger.json`; it no
longer substitutes the historical `beefcafe...` head constant.

## Strict E3.5 behavior

`make verify-e35` remains fail-closed and is expected to return non-zero.

Current blockers are explicit:

- release commit identity is unbound;
- the declared environment has not been replay-qualified;
- no runtime-derived state digest is qualified;
- independent reproduction is not implemented by the local verifier.

This is the desired state until those properties are actually demonstrated.

## What this earns

- shared deterministic chain mechanics;
- derived ledger/head verification against manifest v1.1;
- specified tamper changes both ledger digest and chain head;
- a distinct green local-spine gate;
- an explicit red E3.5 gate.

## What this does not earn

- released-artifact replay;
- runtime state reconstruction;
- Chronicle-raft consensus;
- independent reproduction;
- signed witness quorum;
- production readiness;
- authority to execute.

## Next gates

1. Run and archive `make verify-spine`.
2. Run and archive the expected-red `make verify-e35`.
3. Bind a concrete release artifact/commit externally.
4. Implement an actual runtime state-digest derivation path.
5. Reproduce on a second host.
6. Obtain an independent operator reproduction before any independent promotion.
