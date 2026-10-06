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
authority-state reducer, generic runtime-state observation mechanics, and one
bounded real-runtime adapter for Witness RC1. The remaining E3.5 gap is now
specific: the actual E3.5 runtime/SUT has not replayed the frozen authority
ledger under the qualification protocol, and no independent operator has
reproduced that result.

## Canonical mainline milestones

- PR #69 — manifest binding repair.
- PR #70 — derived ledger/head verifier and explicit E3.5 hold.
- PR #71 — exact-predecessor and scope/support transition invariant.
- PR #72 — bounded runtime-state observation/digest contract.
- PR #73 — bounded local authority-state replay and manifest v1.2.
- PR #74 — bounded Witness RC1 real-runtime state adapter.
- PR #75 — remote CI spine receipt: candidate until merged and replayed on main.

## Current file-level spine

- Executable spine: `tools/fail_closed_spine.py`.
- Shared chain mechanics: `tools/spine_hash.py`.
- Local authority reducer: `tools/authority_state.py`.
- Runtime-state observer: `tools/runtime_state_digest.py`.
- Witness RC1 adapter: `tools/witness_rc1_state_adapter.py`.
- Candidate remote receipt emitter: `tools/emit_spine_receipt.py`.

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
E35RuntimeReplay                    = NOT_ESTABLISHED
ReleasedArtifactReplayForE35        = NOT_ESTABLISHED
RemoteCISpineReceipt                = CANDIDATE_PR75
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
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Qualify or reject PR #75 and preserve its remote CI receipt.
2. Keep remote CI classified as same-origin/non-independent.
3. Identify the actual E3.5 runtime/SUT for `authority_ledger.json`.
4. Build an adapter for that exact runtime and exact replay input.
5. Compare only semantically equivalent state projections.
6. Freeze and replay a released E3.5 artifact.
7. Obtain independent operator reproduction separately.
8. Enforce Gate Zero server-side.

No item above changes W0, O0, or production status.
