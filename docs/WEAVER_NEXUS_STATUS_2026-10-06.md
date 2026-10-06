# Weaver Nexus — consolidated status

**Date:** 2026-10-06  
**Status:** FROZEN · APPEND-ONLY  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Throne:** UNSEATED

## One-line state

The public spine now has corrected manifest semantics, derived ledger/head
verification, an executable A1 transition invariant, a deterministic local
authority-state reducer, generic runtime-state observation mechanics, one
bounded real-runtime adapter for Witness RC1, an artifact-bound successful
same-origin remote CI replay of the bounded spine on canonical main, and a
fail-closed E3.5 runtime-admission gate whose checked-in SUT remains UNBOUND.

The remaining E3.5 gap is specific: the actual E3.5 runtime/SUT has not replayed
the frozen authority ledger under the qualification protocol, no released E3.5
artifact has been qualified, and no independent operator has reproduced that
result.

## Canonical mainline milestones

- PR #69 — manifest binding repair.
- PR #70 — derived ledger/head verifier and explicit E3.5 hold.
- PR #71 — exact-predecessor and scope/support transition invariant.
- PR #72 — bounded runtime-state observation/digest contract.
- PR #73 — bounded local authority-state replay and manifest v1.2.
- PR #74 — bounded Witness RC1 real-runtime state adapter.
- PR #75 — conflicting remote-receipt candidate; closed and superseded.
- PR #76 — reconciled remote CI spine receipt; merged to main.
- PR #77 — artifact-bound mainline remote CI receipt preserved on main.
- Candidate branch — E3.5 runtime-admission gate; governance SUT remains UNBOUND.

## Canonical mainline receipt

Carry-forward main commit:

```text
6926dc263a39da152c2808a6c10cb98509b4938d
```

The successful same-origin receipt remains anchored to source commit:

```text
b8719c35f2970b5169d42d4ac6fa2c60e3f4952d
```

That source commit's push triggered six workflows and all six completed
successfully:

```text
CI                       run 37511431229  PASS
tests                    run 37511431214  PASS
triadic-controls CI      run 37511431186  PASS
Witness TLA model        run 37511431217  PASS
Verification evidence    run 37511431213  PASS
Cross-host spine receipt run 37511431224  PASS
```

The cross-host workflow emitted:

```text
execution_class       = REMOTE_CI_SAME_ORIGIN
source_head_sha       = b8719c35f2970b5169d42d4ac6fa2c60e3f4952d
verified_commit       = b8719c35f2970b5169d42d4ac6fa2c60e3f4952d
operator_independence = NOT_ESTABLISHED
witness_state         = W0
authority             = O0_WITHHELD
production            = PROHIBITED
overall_result        = PASS
```

Workflow artifact:

```text
artifact_id =
11434757818

artifact_zip_sha256 =
5df1d9eb889fdb2e45f010d6c96addc5862674cd5e62dea4216492796eb83bd4

receipt_sha256 =
c96feceeb89bb13f62e18b02cbcead4b8ae7fba65e99d0a820a4f6ad1f1ac0ad
```

The receipt payload digest was independently recomputed during review and
matched the recorded `receipt_sha256`.

The raw receipt and artifact binding are preserved under
`evidence/spine-receipts/`.

This establishes a bounded same-origin remote CI replay only.

```text
RemoteCIReplay != IndependentOperatorReproduction
RemoteCIReplay != E3.5
RemoteCIReplay != WitnessPromotion
```

## Current file-level spine

- Executable spine: `tools/fail_closed_spine.py`.
- Shared chain mechanics: `tools/spine_hash.py`.
- Local authority reducer: `tools/authority_state.py`.
- Runtime-state observer: `tools/runtime_state_digest.py`.
- Witness RC1 adapter: `tools/witness_rc1_state_adapter.py`.
- Remote receipt emitter: `tools/emit_spine_receipt.py`.
- E3.5 runtime admission gate: `tools/e35_runtime_gate.py`.
- E3.5 runtime SUT record: `evidence/e35-runtime-sut.json` (currently UNBOUND).

Bound local values:

```text
authority_ledger_hash =
82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9

ordered_chain_head =
e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85

local_authority_state_digest =
39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e

state_digest_status =
LOCAL_REDUCER_COMPUTED
```

## Preserved historical defects

### WN-DEFECT-MANIFEST-001

Historical placeholder source/image/head bindings.

**Disposition:** repaired; history preserved.

### WN-DEFECT-VERIFY-001

Historical pinned constants labeled as computed values.

**Disposition:** repaired for bounded local verification.

### WN-SPEC-IMPL-001

Historical E3.5 specification exceeded the implemented replay path.

**Disposition:** narrowed. The remaining gap is explicit.

### WN-TEST-MUTATION-001

A signature-negative-control test attempted to mutate a signature by replacing
its first character with `A`. When the original signature already began with
`A`, the mutation was a no-op and the test incorrectly expected rejection.

**Disposition:** repaired by forcing the replacement character to differ from
the original first character.

```text
MutationIntent != MutationOccurred
```

## Current propositions

```text
RepositoryPresence                  = ESTABLISHED
SpineImplementation                 = ESTABLISHED
LocalDeterministicMechanics         = ESTABLISHED_WITHIN_SCOPE
DerivedHeadVerification             = ESTABLISHED_WITHIN_SCOPE
LocalAuthorityStateReduction        = ESTABLISHED_WITHIN_SCOPE
LocalReducerStateDigest             = ESTABLISHED_WITHIN_SCOPE
RuntimeStateObservationContract     = ESTABLISHED_WITH_FIXTURE_SCOPE
WitnessRC1RuntimeAdapter            = ESTABLISHED_WITHIN_BOUNDED_RC1_SCOPE
WitnessRC1E35Equivalence            = NOT_CLAIMED
RemoteCISpineReceipt                = ESTABLISHED_WITHIN_SAME_ORIGIN_CI_SCOPE
CrossHostMechanicsReplay            = ESTABLISHED_WITHIN_SAME_ORIGIN_CI_SCOPE
E35RuntimeAdmissionGate             = HARDENED_CANDIDATE_THIS_BRANCH
E35RuntimeSUT                       = UNBOUND
E35RuntimeReplay                    = NOT_ESTABLISHED
ReleasedArtifactReplayForE35        = NOT_ESTABLISHED
IndependentOperatorReproduction     = NOT_ESTABLISHED
Witness                             = W0
OperationalAuthority               = O0_WITHHELD
Production                          = PROHIBITED
```

## Governing separations

```text
Specification != LocalRun != RuntimeReplay != IndependentReproduction != Authority
LocalReducerDigest != RuntimeStateDigest
WitnessRC1AdapterPass != E3.5RuntimeReplay
DifferentProjectionContract != ComparableDigestMeaning
ManifestConsistency != KnownReleaseIdentity
Mechanics != ScientificResult
Reproduction != Scope
ScopeCoverage != EvidentialSupport
RemoteCIReplay != IndependentOperatorReproduction
MutationIntent != MutationOccurred
InjectionClient != GovernanceRuntime
AttestationSnippet != RunnableSUT
DirectPathExecPrePostHash != AtomicByteToProcessIdentity
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Admit the actual E3.5 governance runtime artifact; do not substitute the
   injection client, attestation snippet, local reducer, or Witness RC1 runtime.
2. Pin that artifact's exact SHA-256 in `evidence/e35-runtime-sut.json`.
3. Run `tools.e35_runtime_gate` against frozen `authority_ledger.json`.
4. Preserve the local reducer and RC1 projections as separate coordinates.
5. Harden path-based pre/post hashing toward atomic byte-to-process identity.
6. Freeze and replay a released E3.5 artifact.
7. Obtain independent operator reproduction separately.
8. Enforce Gate Zero server-side.

No item above changes W0, O0, or production status.
