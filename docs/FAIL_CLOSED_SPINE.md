# Local fail-closed spine

Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`  
Authority: `O0`

`tools/fail_closed_spine.py` is the portfolio advance artifact. It does not claim E3.5, independent witness, or operational authority.

The older `verify_attestations.py` path compares pinned constants, including `expected_head_hash = beefcafe...`, to themselves. That check can pass without reading a real chain. Do not cite it as reproduction.

## Run

From the repository root:

```bash
python3 tools/fail_closed_spine.py
python3 tools/fail_closed_spine.py --tamper
```

Clean mode prints the canonical ledger hash and the hash-chain head. Tamper mode mutates the last payload and requires the head to diverge. A silent match is a failure.

## What this earns

- A stranger can clone the repo and run one command.
- A mutated ledger cannot keep the same chain head.
- The published manifest is reported as match or stale. It is not silently treated as truth.

## What this does not earn

- Independent reproduction
- Chronicle-raft consensus
- Signed witness quorum
- Production readiness
- Authority to execute

Next real gate: replace the pinned head in `published_manifest.json` with the chain head this tool prints, then have a second machine run the same command and archive the stdout.
