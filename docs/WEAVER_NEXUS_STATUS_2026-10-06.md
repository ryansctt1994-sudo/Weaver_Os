# Weaver Nexus — consolidated status

**Date:** 2026-10-06  
**Status:** FROZEN · APPEND-ONLY  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Throne:** UNSEATED

## One-line state

The public spine now has corrected manifest semantics, derived ledger/head
verification, an executable A1 transition invariant, a bounded runtime-state
observation contract, and a deterministic local authority-state reducer.
E3.5 remains withheld because actual qualified runtime replay and independent
operator reproduction have not been established.

## Canonical mainline milestones

- PR #69 — manifest binding repair.
- PR #70 — derived ledger/head verifier and explicit E3.5 hold.
- PR #71 — exact-predecessor and scope/support transition invariant.
- PR #72 — bounded runtime-state digest contract mechanics.
- PR #73 — bounded local authority-state replay and manifest v1.2.

## Current file-level spine

- Executable spine: `tools/fail_closed_spine.py`.
- Shared chain mechanics: `tools/spine_hash.py`.
- Local state reducer: `tools/authority_state.py`.
- Runtime observation contract: `tools/runtime_state_digest.py`.
- Evidence ceiling for local spine: `LOCAL_DETERMINISTIC_CHECK`.
- Canonical ledger digest:
  `82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9`.
- Ordered chain head:
  `e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85`.
- Local projected state digest:
  `39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e`.
- State digest class: `LOCAL_REDUCER_COMPUTED`.

## Preserved historical defects

### WN-DEFECT-MANIFEST-001

Historical placeholder source/image/head bindings.

**Disposition:** repaired; history preserved.

### WN-DEFECT-VERIFY-001

Historical pinned constants labeled as computed values.

**Disposition:** repaired for bounded local verification.

### WN-SPEC-IMPL-001

Historical E3.5 specification exceeded the implemented replay path.

**Disposition:** narrowed; E3.5 remains fail-closed.

## Current propositions

```text
RepositoryPresence                 = ESTABLISHED
SpineImplementation                = ESTABLISHED
LocalDeterministicMechanics        = ESTABLISHED_WITHIN_SCOPE
DerivedHeadVerification            = ESTABLISHED_WITHIN_SCOPE
LocalAuthorityStateReduction       = ESTABLISHED_WITHIN_SCOPE
RuntimeStateContractMechanics      = ESTABLISHED_WITH_FIXTURE_SCOPE
QualifiedRuntimeReplay             = NOT_ESTABLISHED
E35Qualification                   = WITHHELD
A1PredecessorBindingReference      = ESTABLISHED_WITHIN_SCOPE
A1ScopeSupportSeparationReference  = ESTABLISHED_WITHIN_SCOPE
RemoteCIReceipt                    = CANDIDATE_PENDING_EXECUTION
IndependentReproduction            = NOT_ESTABLISHED
Witness                            = W0
OperationalAuthority               = O0_WITHHELD
Production                         = PROHIBITED
```

## Governing separations

```text
Specification != LocalRun != RuntimeReplay != IndependentReproduction != Authority
LocalReducerDigest != RuntimeStateDigest
ManifestConsistency != KnownReleaseIdentity
Mechanics != ScientificResult
Reproduction != Scope
ScopeCoverage != EvidentialSupport
RemoteCIReplay != IndependentOperatorReproduction
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Emit an artifact-bound remote CI spine receipt.
2. Preserve same-origin remote CI as non-independent evidence only.
3. Implement a real named-runtime adapter to the runtime-state contract.
4. Bind replay input and runtime source independently.
5. Compare runtime-derived state against the correct projection contract.
6. Obtain independent operator reproduction separately.
7. Enforce Gate Zero server-side.

No item above changes W0, O0, or production status.
