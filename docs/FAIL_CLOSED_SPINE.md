# Local fail-closed spine

Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`  
Authority: `O0`

The local spine now has three separately derived values:

1. canonical authority-ledger digest;
2. ordered chain head;
3. a bounded local authority-state projection digest.

The state projection is produced by `tools/authority_state.py` and is **not**
Chronicle/Raft runtime state.

```text
LocalReducerDigest != RuntimeStateDigest
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

For the manifest v1.2 candidate derived from
`75f58094d0842f56054bb987e50deb175df8486a`:

```text
authority_ledger_hash =
82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9

ordered_chain_head =
e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85

local_state_digest =
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e

state_digest_method =
authority-transition-reducer-v1
```

The canonical local projected state is:

```json
{"receipt_id":"AL-ADOC-2026-001","state":"EXECUTED"}
```

The chain head commits to transition history. The local state digest commits only
to the final bounded state projection. They are distinct properties.

## Reducer admission rules

The local reducer fails closed on:

- malformed payload JSON;
- duplicate JSON keys;
- missing transition fields;
- unrecognized payload fields;
- receipt identity changes;
- state discontinuity;
- no-op transitions;
- unsupported event types;
- malformed ledger sequence.

## Strict E3.5 behavior

`make verify-e35` remains intentionally non-zero.

The local state digest does not satisfy the E3.5 runtime-state requirement.
Open gates remain:

- externally bound release identity;
- replay-qualified environment;
- Chronicle/runtime-derived state digest;
- independent reproduction.

## What this earns

- deterministic local replay of the admitted transition sequence;
- a bounded final-state projection;
- a locally derived state digest;
- explicit separation between local reduction and runtime replay;
- continued fail-closed E3.5 behavior.

## What this does not earn

- Chronicle/Raft runtime equivalence;
- released-artifact replay;
- cross-host reproduction;
- independent reproduction;
- witness promotion;
- production readiness;
- operational authority.
