# Runtime State Digest Contract

**Status:** CANDIDATE MECHANICS · NOT E3.5 QUALIFICATION  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The E3.5 path requires a runtime-derived state digest, but the repository does
not currently contain a qualified runtime adapter that replays
`authority_ledger.json` into a canonical runtime state.

The correct response is not to place another pinned digest in the manifest.

This contract defines the boundary a future runtime adapter must satisfy.

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

The runtime does not get to supply its own state digest.

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
RuntimeEmitsState != ManifestStateDigestQualified
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

## Next gate

The next implementation must provide a real adapter from a named Weaver runtime
to this envelope and bind its replay input to the same ledger identity used by
the E3.5 manifest.

Until that exists:

```text
expected_state_digest = null
state_digest_status = NOT_COMPUTED_FROM_RUNTIME
```

remains the correct manifest state.
