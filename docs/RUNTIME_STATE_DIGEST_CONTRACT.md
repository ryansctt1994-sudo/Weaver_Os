# Runtime State Digest Contract

**Status:** IMPLEMENTED CONTRACT MECHANICS · RUNTIME E3.5 NOT QUALIFIED  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The E3.5 path requires a runtime-derived state digest.

The repository now also has a deterministic **local authority-state reducer**.
That is a different property from runtime replay.

Current manifest v1.2 records:

```text
state_digest_status = LOCAL_REDUCER_COMPUTED
state_digest_method = authority-transition-reducer-v1
expected_state_digest = 39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e
```

That digest is derived from the bounded local projection of
`authority_ledger.json`. It is **not** a Chronicle/Raft or other runtime-state
digest.

Therefore:

```text
LocalReducerDigest != RuntimeStateDigest
LocalReplay != RuntimeReplay
```

The correct response is not to reinterpret the local reducer digest as runtime
evidence.

## Runtime output envelope

A runtime command must emit exactly one JSON object:

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

The runtime does not get to supply its own trusted state digest.

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

A passing fixture test establishes:

```text
RuntimeStateContractMechanics
```

It does not establish:

```text
ActualWeaverRuntimeReplay
ReleasedArtifactReplay
IndependentReproduction
E3.5
Authority
```

## Named-runtime adapter

The next layer is a real adapter from an already frozen runtime to this
envelope. The witness RC1 adapter exercises that contract against a real bounded
runtime, but it does not replay the E3.5 authority ledger.

Therefore:

```text
WitnessRC1AdapterPass != E3.5RuntimeReplay
```

## Next E3.5 gate

A future E3.5 runtime adapter must:

1. identify the exact runtime implementation;
2. bind the exact runtime source/release;
3. replay the exact E3.5 ledger/input;
4. emit canonical runtime state;
5. allow the observer to derive the digest;
6. preserve the existing local-reducer digest as a separate historical property.

No runtime-derived state should silently overwrite or impersonate the existing
local-reducer result.
