# Runtime State Digest Contract

**Status:** IMPLEMENTED CONTRACT MECHANICS · E3.5 RUNTIME REPLAY NOT QUALIFIED  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The E3.5 path requires a runtime-derived state digest. The repository now has
three distinct layers that must not impersonate one another:

1. a bounded local authority-state reducer;
2. a generic runtime-state observation contract;
3. a bounded adapter for the frozen Witness RC1 runtime.

None of those, by itself, is the missing E3.5 authority-ledger runtime replay.

```text
LocalReducerDigest != RuntimeStateDigest
RuntimeContractMechanics != ActualRuntimeReplay
WitnessRC1AdapterPass != E3.5RuntimeReplay
RuntimeReplay != IndependentReproduction
```

## Local reference projection

`tools/authority_state.py` deterministically reduces the admitted
`STATE_TRANSITION` events in `authority_ledger.json` to:

```json
{"receipt_id":"AL-ADOC-2026-001","state":"EXECUTED"}
```

Current local digest:

```text
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e
```

Method:

```text
authority-transition-reducer-v1
```

Manifest classification:

```text
state_digest_status = LOCAL_REDUCER_COMPUTED
```

That is not equivalent to `COMPUTED_FROM_RUNTIME`.

## Generic runtime output envelope

A runtime command may be observed through:

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

The caller independently supplies expected runtime identity, source binding, and
replay-input identity.

```text
RuntimeClaimsSource != SourceBindingEstablished
RuntimeClaimsReplayInput != ReplayInputBindingEstablished
RuntimeEmitsState != RuntimeStateQualified
```

## Witness RC1 adapter

`tools/witness_rc1_state_adapter.py` adapts the frozen runtime at:

```text
releases/weaver-witness-signed-rc1/src/weaver_core.py
```

to the generic runtime envelope.

This is a real bounded runtime adapter. It binds actual RC1 source bytes against
the frozen RC1 release manifest and binds its named command input.

Its state projection includes protected state, used command IDs, Chronicle
entries, last verdict, and last receipt.

That projection is intentionally different from the authority-ledger local
reference projection.

Therefore:

```text
WitnessRC1StateDigest != LocalAuthorityReducerDigest
DifferentProjectionContract != ComparableDigestMeaning
```

The RC1 adapter also does **not** replay `authority_ledger.json`.

Therefore:

```text
WitnessRC1AdapterPass != E3.5RuntimeReplay
```

## Projection-comparison rule

Two state digests are directly comparable only when all of the following match:

- replay input identity;
- projection contract;
- canonicalization contract;
- digest algorithm;
- relevant source/runtime binding.

```text
SameDigestMeaningRequiresSameProjectionContract
```

If a future E3.5 adapter implements the same bounded state projection as
`authority-transition-reducer-v1`, the runtime-derived digest may be compared
against the local reference digest.

If it exposes a different state projection, it must use a separately named
method and may not silently replace the local result.

## Current manifest state

```text
expected_state_digest =
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e

state_digest_status = LOCAL_REDUCER_COMPUTED
state_digest_method = authority-transition-reducer-v1
```

This remains correct even though the RC1 runtime adapter exists, because RC1 is
a different runtime/input/projection from the E3.5 authority-ledger path.

## Next E3.5 gate

The next adapter must target the actual E3.5 runtime/SUT and:

1. bind its exact runtime source or release;
2. bind the exact `authority_ledger.json` replay input;
3. replay that input;
4. emit a named canonical state projection;
5. allow the observer to derive the digest;
6. compare only against a semantically equivalent reference projection;
7. preserve the local reducer and RC1 results as separate historical properties.

Until that exists:

```text
E3.5 = WITHHELD
Witness = W0
Authority = O0_WITHHELD
Production = PROHIBITED
```
