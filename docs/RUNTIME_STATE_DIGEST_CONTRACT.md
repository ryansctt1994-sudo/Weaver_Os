# Runtime State Digest Contract

**Status:** CANDIDATE MECHANICS · NOT E3.5 QUALIFICATION  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The E3.5 path requires a runtime-derived state digest. The repository now has
two lower-level mechanics that must remain distinct:

1. a bounded local authority-state reducer;
2. a runtime-state observation contract.

Neither is, by itself, a qualified Weaver runtime replay.

```text
LocalReducerDigest != RuntimeStateDigest
RuntimeStateContractMechanics != ActualRuntimeReplay
ActualRuntimeReplay != IndependentReproduction
```

## Local reference projection

`tools/authority_state.py` deterministically reduces the admitted
`STATE_TRANSITION` events in `authority_ledger.json` to:

```json
{"receipt_id":"AL-ADOC-2026-001","state":"EXECUTED"}
```

Its current local digest is:

```text
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e
```

and its method is:

```text
authority-transition-reducer-v1
```

The manifest may bind this value only as:

```text
state_digest_status = LOCAL_REDUCER_COMPUTED
```

This is not equivalent to `COMPUTED_FROM_RUNTIME`.

## Runtime output envelope

A future qualified runtime command must emit exactly one JSON object:

```json
{
  "schema": "weaver-runtime-state-1",
  "runtime_id": "runtime-name",
  "source_binding": {
    "kind": "git_commit",
    "value": "<exact source revision>"
  },
  "replay_input_digest": "<digest of the replay input under the agreed contract>",
  "state": {
    "...": "canonical runtime state"
  }
}
```

The observer derives:

```text
STATE_DIGEST = SHA256(canonical_json(state))
```

The runtime does not get to supply its own trusted digest.

## Independent bindings

The caller supplies independently:

- expected runtime identity;
- expected source-binding kind;
- expected source-binding value;
- expected replay-input digest.

All must match the runtime envelope.

Therefore:

```text
RuntimeClaimsSource != SourceBindingEstablished
RuntimeClaimsReplayInput != ReplayInputBindingEstablished
RuntimeEmitsState != RuntimeStateQualified
```

## Reference-to-runtime comparison

If a runtime adapter claims to implement the same state projection as
`authority-transition-reducer-v1`, its projected state digest must equal the
local reference digest for the same bound replay input.

If it exposes a different state projection, the digests are not directly
comparable and the method must be separately named and specified.

```text
SameDigestMeaningRequiresSameProjectionContract
```

## Execution behavior

`tools/runtime_state_digest.py`:

- executes the runtime command without a shell;
- requires exit code zero;
- applies a timeout;
- rejects oversized stdout/stderr after capture;
- rejects malformed or ambiguous output;
- rejects source/runtime/input substitution;
- derives the state digest itself.

The stdout/stderr limits are post-execution admission limits, not a hard
subprocess memory sandbox.

## Test fixture boundary

`tests/fixtures/runtime_state_emitter.py` exists only to test the contract.

A passing fixture establishes contract mechanics, not an actual Weaver runtime.

## Current manifest state

The current manifest is allowed to contain the local reference digest:

```text
expected_state_digest =
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e

state_digest_status = LOCAL_REDUCER_COMPUTED
state_digest_method = authority-transition-reducer-v1
```

E3.5 still requires a separately qualified runtime-derived state result.

## Next gate

Provide a real adapter from a named Weaver runtime to the runtime envelope,
bind it to the frozen replay input and exact runtime source, then compare the
runtime projection against the appropriate frozen projection contract.

Until that exists:

```text
E3.5 = WITHHELD
Witness = W0
Authority = O0_WITHHELD
Production = PROHIBITED
```
