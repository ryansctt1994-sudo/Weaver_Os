# Weaver Witness RC1 Runtime-State Adapter

**Status:** BOUNDED REAL-RUNTIME ADAPTER · NOT E3.5  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The runtime-state digest contract needs at least one real, named runtime adapter
before it is useful beyond fixtures.

The repository already contains a frozen bounded runtime in:

```text
releases/weaver-witness-signed-rc1/src/weaver_core.py
```

`tools/witness_rc1_state_adapter.py` replays one command through that exact
runtime and emits the `weaver-runtime-state-1` envelope.

## Source binding

The adapter computes SHA-256 over the actual `weaver_core.py` bytes and requires
that value to match the frozen release manifest entry before execution.

Current release-manifest value:

```text
e6b713a7c138d369c59652493448e96ff93dfc4d37bce2cb49e912960608992c
```

The observer still supplies that expected value independently.

Therefore:

```text
AdapterComputesSourceHash
+
ReleaseManifestBindsSourceHash
+
ObserverExpectsSourceHash
```

must all agree.

## State scope

The adapter's state object includes:

- protected state;
- replay-cache command IDs;
- Chronicle entries;
- last verdict;
- last receipt.

This is intentionally broader than the historical RC1 `Runtime.state_hash()`,
which hashes only `protected`.

Therefore:

```text
RC1 state_hash != Adapter full-state digest
```

They answer different questions.

## Replay input

The adapter accepts a single command document and binds the canonical digest of
that document into `replay_input_digest`.

The test vector is:

```text
tests/fixtures/witness_rc1_authorized_command.json
```

## What this establishes

If the tests pass, they establish only that:

- a real frozen RC1 runtime can be adapted to the new state-envelope contract;
- source bytes are checked against the release manifest;
- replay-input identity is bound;
- the observer, not the runtime, derives the final full-state digest;
- changed commands produce changed full-state digests in the named tests.

## What this does not establish

This adapter does not replay `authority_ledger.json`.

It is not the missing E3.5 governance runtime.

Therefore:

```text
WitnessRC1AdapterPass != E3.5RuntimeReplay
WitnessRC1StateDigest != PublishedManifestExpectedStateDigest
SameRepoExecution != IndependentReproduction
```

The E3.5 manifest must remain:

```text
expected_state_digest = null
state_digest_status = NOT_COMPUTED_FROM_RUNTIME
```

until a named runtime actually replays the E3.5 ledger under the frozen
qualification protocol.
