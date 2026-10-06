# E3.5-RUNTIME-001 — governance runtime admission gate

**Status:** GATE HARDENED · SUT UNBOUND · E3.5 WITHHELD  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Portfolio ceiling:** E2

## Purpose

This gate makes one missing predicate executable:

> an explicitly admitted governance runtime must replay one exactly pinned
> `authority_ledger.json` and expose a state projection equivalent to the
> frozen local reducer.

The gate does **not** supply that runtime and does not promote a test fixture
into one.

## Checked-in state

`evidence/e35-runtime-sut.json` remains:

```text
E35RuntimeSUT = UNBOUND
E35RuntimeReplay = NOT_ESTABLISHED
```

The checked-in refusal is the correct result.

## Admission schema v2

An `ADMITTED_CANDIDATE` record must bind all of the following:

- non-empty runtime ID;
- repository-relative executable artifact path;
- exact SHA-256 of the artifact bytes;
- repository-relative ledger path;
- exact SHA-256 of the ledger file bytes;
- canonical replay-input digest of the parsed ledger;
- `authority-transition-reducer-v1` projection;
- launch mode `DIRECT_ARTIFACT_EXEC`.

The descriptor no longer accepts an arbitrary command vector.

That closes the earlier substitution class:

```text
ArtifactPinned != ArtifactExecuted
```

Under v2, the admitted artifact itself is `argv[0]` and the admitted ledger is
its first argument. A wrapper/interpreter command that merely mentions the
artifact is rejected by schema.

## Replay binding

For an admitted candidate the gate now requires two independent ledger
bindings:

1. **raw-file identity** — SHA-256 of the exact ledger bytes;
2. **semantic replay identity** — SHA-256 of canonical parsed JSON.

This makes both of the following observable:

```text
LedgerBytesChanged
ReplaySemanticsChanged
```

A whitespace-only rewrite is therefore still a different frozen replay
artifact even if its canonical semantics are unchanged.

## Execution sequence

The gate:

1. loads the exact SUT record and hashes the record bytes;
2. verifies artifact location, exact artifact hash, and executable permission;
3. verifies the exact admitted ledger path;
4. verifies raw ledger-file SHA-256;
5. verifies canonical replay-input digest;
6. derives the local reference projection;
7. executes the admitted artifact directly, without a shell;
8. requires the runtime envelope to bind runtime ID, artifact digest, and
   replay-input digest;
9. hashes artifact and ledger again after execution;
10. rejects artifact or ledger mutation during the run;
11. requires observer-derived runtime state to equal the local reference
    projection.

A successful candidate receipt is deliberately named:

```text
LOCAL_CANDIDATE_REPLAY_PASS
```

not `E3.5_RUNTIME_PASS`.

The receipt also states:

```text
E35_ADMISSION = WITHHELD
INDEPENDENT_REPRODUCTION = NOT_ESTABLISHED
WITNESS = W0
AUTHORITY = O0_WITHHELD
PRODUCTION = PROHIBITED
```

## Hostile/non-vacuity suite

The test suite contains a positive control plus fail-closed cases for:

- state-projection mismatch;
- artifact hash mismatch;
- non-executable artifact;
- descriptor command injection;
- non-equivalent projection method;
- byte-changed ledger with unchanged semantics;
- wrong pinned semantic digest;
- alternate/unadmitted ledger path;
- runtime-ID substitution;
- source-binding substitution;
- runtime replay-digest substitution;
- artifact mutation during execution;
- ledger mutation during execution.

The positive control uses only a temporary executable fixture. It proves gate
mechanics are not vacuous. It is **not** an admitted portfolio runtime.

## Remaining execution-binding limit

The v2 gate improves:

```text
ARBITRARY_COMMAND_WITH_ARTIFACT_PLACEHOLDER
    ->
DIRECT_ARTIFACT_PATH_EXEC
```

but path execution still does not prove atomic identity between the bytes hashed
before launch and the exact bytes mapped by the operating system.

The receipt therefore records:

```text
execution_binding_class = DIRECT_PATH_EXEC_PRE_POST_HASHED
atomic_process_identity = NOT_ESTABLISHED
```

So:

```text
DirectPathExecPrePostHash != AtomicByteToProcessIdentity
```

A later launcher may use an immutable already-open executable object, measured
launch, or an equivalent platform primitive.

## Current portfolio disposition

This branch advances **the gate only**.

It does not:

- nominate `chronicle/chronicle.py`;
- nominate the Chronicle/Raft HTTP snippet;
- nominate `inject_ledger.py`;
- nominate Witness RC1;
- merge Activation Runtime #65;
- ratify the obsolete #67 freeze;
- establish an independent operator run;
- change E2/W0/O0/production state.

## Next legitimate admission step

The next candidate must identify the actual runtime intended to own E3.5 replay,
pin its exact executable bytes and exact frozen ledger bytes in the v2 record,
then run this gate.

After a local candidate pass, a stronger execution binding and non-origin
operator reproduction remain separate gates.

Until then:

```text
E35RuntimeSUT = UNBOUND
E35RuntimeReplay = NOT_ESTABLISHED
E35Admission = WITHHELD
Witness = W0
Authority = O0_WITHHELD
Production = PROHIBITED
PortfolioE4 = NOT_EARNED
```
