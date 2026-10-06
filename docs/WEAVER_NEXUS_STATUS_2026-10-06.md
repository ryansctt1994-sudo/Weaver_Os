# Weaver Nexus — consolidated status

**Date:** 2026-10-06  
**Status:** FROZEN · APPEND-ONLY  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Throne:** UNSEATED

## One-line state

The public spine now has corrected manifest semantics, derived local verification,
an executable one-coordinate A1 transition invariant, a deterministic local
authority-state reducer, and runtime-state observation mechanics. E3.5 remains
withheld because the actual E3.5 runtime replay and independent reproduction
have not been established.

## Canonical mainline milestones

- PR #69 — manifest binding semantics repaired.
- PR #70 — pinned-head verifier theater replaced by derived local verification.
- PR #71 — exact-predecessor and scope/support transition invariants added.
- PR #72 — runtime-state digest observation contract added.
- PR #73 — bounded local authority-state reducer added; manifest advanced to v1.2.
- PR #74 — witness RC1 runtime-state adapter is candidate state until merged.

## Current file-level spine

- Shared chain mechanics: `tools/spine_hash.py`.
- Local authority reducer: `tools/authority_state.py`.
- Runtime-state observer: `tools/runtime_state_digest.py`.
- Evidence ceiling for the local spine: `LOCAL_DETERMINISTIC_CHECK`.
- Canonical ledger digest: `82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9`.
- Ordered chain head: `e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85`.
- Local reducer digest: `39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e`.

## Preserved historical defects

### WN-DEFECT-MANIFEST-001

Historical manifest placeholder bindings were repaired; the defect remains
preserved as history.

### WN-DEFECT-VERIFY-001

Historical pinned-constant self-comparison was repaired for the local spine.

### WN-SPEC-IMPL-001

The historical E3.5 specification exceeded the implementation. The gap is now
explicit rather than silently treated as a result.

## Current propositions

```text
RepositoryPresence                 = ESTABLISHED
SpineImplementation                = ESTABLISHED
LocalDeterministicMechanics        = ESTABLISHED_WITHIN_SCOPE
ManifestV1_2Semantics              = MERGED
DerivedHeadVerification            = MERGED
LocalAuthorityReducer              = MERGED
LocalReducerStateDigest            = ESTABLISHED_WITHIN_SCOPE
RuntimeStateObservationContract    = MERGED
WitnessRC1RuntimeAdapter           = CANDIDATE_PR74
E35RuntimeReplay                   = NOT_ESTABLISHED
ReleasedArtifactReplay             = NOT_ESTABLISHED_FOR_E35
CrossHostReplay                    = NOT_ESTABLISHED
IndependentReproduction            = NOT_ESTABLISHED
Witness                            = W0
OperationalAuthority               = O0_WITHHELD
Production                         = PROHIBITED
```

## Governing separations

```text
Specification != LocalRun != IndependentReproduction != Authority
ManifestConsistency != KnownReleaseIdentity
LocalReducerDigest != RuntimeStateDigest
Mechanics != ScientificResult
Reproduction != Scope
ScopeCoverage != EvidentialSupport
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Qualify or reject PR #74 as a bounded real-runtime adapter.
2. Identify the actual E3.5 runtime/SUT that can replay `authority_ledger.json`.
3. Build a separate adapter for that exact runtime and exact replay input.
4. Preserve the local reducer digest as a distinct property; do not overwrite it.
5. Freeze and replay a released artifact.
6. Perform same-operator cross-host replay.
7. Obtain independent operator reproduction separately.
8. Enforce Gate Zero server-side.

No item above changes W0, O0, or production status.
