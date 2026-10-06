# Weaver Nexus — consolidated status

**Date:** 2026-10-06  
**Status:** FROZEN · APPEND-ONLY  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Throne:** UNSEATED

## One-line state

The public spine now has corrected manifest semantics, a derived local verifier,
and a bounded executable A1 transition invariant. E3.5 remains deliberately
withheld because no qualified runtime-state replay or independent reproduction
has been established.

## Canonical mainline milestones

- Manifest binding repair merged through PR #69.
- Derived ledger/head verifier merged through PR #70.
- Exact-predecessor / scope-separation transition invariant merged through PR #71.
- Mainline verification workflows were green after the merged sequence.

## Current file-level spine

- Executable spine: `tools/fail_closed_spine.py`.
- Shared chain mechanics: `tools/spine_hash.py`.
- Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`.
- Canonical ledger digest: `82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9`.
- Ordered chain head: `e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85`.

## Preserved historical defects

### WN-DEFECT-MANIFEST-001

The historical manifest carried placeholder source/image/head fields.

**Disposition:** repaired in manifest v1.1; history preserved.

### WN-DEFECT-VERIFY-001

The historical verifier assigned pinned constants to values labeled computed.

**Disposition:** repaired for the local spine; the verifier now derives the
ledger digest and ordered chain head from actual ledger content.

### WN-SPEC-IMPL-001

The historical E3.5 specification described a stronger replay procedure than
the implementation provided.

**Disposition:** preserved and narrowed. E3.5 remains withheld until the
missing runtime/reproduction predicates exist.

## Current propositions

```text
RepositoryPresence                = ESTABLISHED
SpineImplementation               = ESTABLISHED
LocalDeterministicMechanics       = ESTABLISHED_WITHIN_SCOPE
ManifestV1HistoricalCorrectness   = FAILED_STALE_PRESERVED
ManifestV1_1Semantics             = MERGED
DerivedHeadVerification           = MERGED
E35Qualification                  = WITHHELD
A1PredecessorBindingReference     = MERGED
A1ScopeSupportSeparationReference = MERGED
RuntimeStateDigestQualification   = NOT_ESTABLISHED
CrossHostReplay                   = NOT_ESTABLISHED
IndependentReproduction           = NOT_ESTABLISHED
Witness                           = W0
OperationalAuthority              = O0_WITHHELD
Production                        = PROHIBITED
```

## Governing separations

```text
Specification != LocalRun != IndependentReproduction != Authority
ManifestConsistency != KnownReleaseIdentity
Mechanics != ScientificResult
Reproduction != Scope
ScopeCoverage != EvidentialSupport
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Define the runtime-state digest boundary without inventing a runtime result.
2. Implement a real adapter from a named runtime to that boundary.
3. Bind replay input identity to the frozen E3.5 ledger.
4. Populate `expected_state_digest` only after the runtime actually derives it.
5. Perform same-operator cross-host replay.
6. Obtain independent operator reproduction separately.
7. Enforce Gate Zero server-side.

No item above changes W0, O0, or production status.
