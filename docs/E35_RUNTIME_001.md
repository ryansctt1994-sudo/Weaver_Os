# E3.5-RUNTIME-001 — governance runtime admission gate

**Status:** MECHANICS IMPLEMENTED · SUT UNBOUND · E3.5 WITHHELD  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED

## Purpose

The Weaver spine already derives the authority-ledger chain head, computes a
bounded local reference state, observes external runtime state, and adapts the
frozen Witness RC1 runtime. The remaining E3.5 runtime gap is narrower:

> no executable governance runtime has been admitted that replays the frozen
> `authority_ledger.json` under the E3.5 qualification contract.

`tools/e35_runtime_gate.py` makes that missing predicate executable instead of
leaving it implicit.

## Repository finding

At the time this gate was added:

- `chronicle/chronicle.py` explicitly defers executable Chronicle behavior to
  the bound RC1 witness artifact and raises if source-tree implementation
  symbols are requested;
- `chronicle-raft/` contains an HTTP attestation integration snippet, not a
  runnable Chronicle/Raft server;
- `inject_ledger.py` is a client that posts events to an assumed `/events`
  endpoint, not the runtime itself.

Therefore none of those may be silently renamed the E3.5 runtime/SUT.

The checked-in admission record is intentionally:

```text
status = UNBOUND
reason = NO_ADMITTED_GOVERNANCE_RUNTIME
```

and the gate exits withheld.

## Admission record

`evidence/e35-runtime-sut.json` is the single machine-readable admission point.

A candidate must bind:

- a non-empty runtime ID;
- a repository-relative executable artifact path;
- the exact SHA-256 of that artifact;
- `authority-transition-reducer-v1` as the comparable projection method;
- an argv vector containing exactly one `{artifact}` and one `{ledger}`
  placeholder.

The gate does not invoke a shell.

## Runtime replay

For an admitted candidate the gate:

1. parses the frozen authority ledger;
2. derives the local reference projection using
   `authority-transition-reducer-v1`;
3. independently derives the canonical replay-input digest;
4. hashes the runtime artifact before execution;
5. invokes the candidate through the existing runtime-state observer;
6. requires the runtime envelope to bind the same runtime ID, artifact digest,
   and replay-input digest;
7. observer-derives the runtime state digest;
8. hashes the runtime artifact and replay input again after execution;
9. refuses if either changed;
10. requires the runtime state digest to equal the semantically equivalent
    local reference digest.

A local pass therefore establishes only:

```text
AdmittedArtifact
+ BoundReplayInput
+ ObserverDerivedState
+ EquivalentReferenceProjection
= LOCAL_RUNTIME_REPLAY
```

It does not establish E3.5 independent reproduction.

## Execution binding limit

The current gate classifies execution binding as:

```text
PRE_POST_HASHED_PATH_EXEC
```

The artifact is hashed before and after execution and the runtime envelope must
report the same binding. This narrows ordinary mutation/race failures but does
not prove atomic identity between the bytes hashed and the bytes the operating
system mapped into the running process.

Therefore:

```text
PrePostHashPathExec != AtomicByteToProcessIdentity
```

A later hardened launcher may use a platform mechanism that executes from an
already-open immutable object or equivalent measured-launch primitive.

## Fail-closed result today

With the checked-in `UNBOUND` admission record:

```bash
python -m tools.e35_runtime_gate
```

must return non-zero and report:

```text
E3.5_RUNTIME_WITHHELD:E35_RUNTIME_SUT_UNBOUND:NO_ADMITTED_GOVERNANCE_RUNTIME
WITNESS: W0
AUTHORITY: O0_WITHHELD
PRODUCTION: PROHIBITED
```

That refusal is the correct result.

## Non-equivalences

```text
InjectionClient != GovernanceRuntime
AttestationSnippet != RunnableSUT
LocalReducer != RuntimeReplay
WitnessRC1AdapterPass != E3.5RuntimeReplay
LocalRuntimeReplay != IndependentOperatorReproduction
PrePostHashPathExec != AtomicByteToProcessIdentity
ReceiptAccepted != AuthorityGranted
```

## Next real promotion opportunity

Do not add another reference runtime merely to make this gate green.

The next legitimate change is to admit the actual governance runtime artifact
that is intended to own E3.5 replay, pin its exact bytes in
`evidence/e35-runtime-sut.json`, and run this gate against the frozen
`authority_ledger.json`.

Until then:

```text
E35RuntimeSUT = UNBOUND
E35RuntimeReplay = NOT_ESTABLISHED
Witness = W0
Authority = O0_WITHHELD
Production = PROHIBITED
```
