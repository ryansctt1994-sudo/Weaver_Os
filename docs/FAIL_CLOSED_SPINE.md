# Local fail-closed spine

Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`  
Authority: `O0`

`tools/fail_closed_spine.py` is the current file-level portfolio spine. It does not claim E3.5, independent witness, or operational authority.

The older `verify_attestations.py` path compares pinned constants to manifest values for the head/state checks. That can pass without deriving those values from the actual chain/runtime and must not be cited as reproduction.

## Run

From the repository root:

```bash
python3 tools/fail_closed_spine.py
python3 tools/fail_closed_spine.py --tamper
```

Clean mode prints the canonical ledger hash and the ordered hash-chain head. Tamper mode mutates the final payload and requires the ledger hash and chain head to diverge.

For the source state at `ee725f7cf923d86d915900fc93ef2e3f6e5eef1c`, the manifest v1.1 candidate binds:

```text
authority_ledger_hash = 82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9
expected_head_hash    = e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85
```

The state digest remains explicitly unqualified.

## What this earns

- A cloneable local program derives a ledger digest and ordered chain head from actual ledger contents.
- The specified payload tamper cannot retain both the original ledger digest and chain head.
- A stale manifest can be detected rather than silently treated as truth.

## What this does not earn

- Independent reproduction
- Runtime-derived state digest
- Chronicle-raft consensus
- Signed witness quorum
- Production readiness
- Authority to execute

## Next gates

1. Land the manifest/schema correction without changing the verifier.
2. Capture the expected-red `make verify-e35` result against the corrected manifest.
3. Repair the verifier in a separate change so it derives the chain head from ledger bytes.
4. Keep E3.5 red until every required runtime-derived field, including state digest, is actually qualified.
5. Reproduce on another host; do not call same-operator cross-host execution independent witness.
