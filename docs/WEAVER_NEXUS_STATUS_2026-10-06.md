# Weaver Nexus — consolidated status

**Date:** 2026-10-06  
**Status:** FROZEN · APPEND-ONLY  
**Authority:** O0 · WITHHELD  
**Witness:** W0  
**Production:** PROHIBITED  
**Throne:** UNSEATED

## One-line state

The portfolio now has a public executable spine with a specific manifest defect and a specific verifier defect. The next unit of progress is a bound patch/replay sequence, not additional architecture.

## Current file-level spine

- Repository baseline: `Weaver_Os@ee725f7cf923d86d915900fc93ef2e3f6e5eef1c`.
- Executable spine: `tools/fail_closed_spine.py`.
- Evidence ceiling: `LOCAL_DETERMINISTIC_CHECK`.
- Canonical ledger digest: `82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9`.
- Ordered chain head: `e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85`.

## Named defects

### WN-DEFECT-MANIFEST-001

The historical manifest carried placeholder source/image/head fields. Manifest v1.1 corrects the known ledger/head binding, removes the unbuilt image claim, and marks runtime state digest unqualified.

### WN-DEFECT-VERIFY-001

The historical verifier assigns pinned constants to `computed_head_hash` and `computed_state_digest`. That is not independent computation.

```text
ExpectedConstantComparedToPinnedConstant != Reproduction
```

### WN-SPEC-IMPL-001

The E3.5 specification describes a stronger replay procedure than the current Makefile/verifier implement.

```text
SpecifiedProcedure != ImplementedProcedure
```

## Current propositions

```text
RepositoryPresence                = ESTABLISHED
SpineImplementation               = ESTABLISHED
LocalDeterministicMechanics       = ESTABLISHED_WITHIN_SCOPE
ManifestV1HistoricalCorrectness   = FAILED_STALE
ManifestV1_1Candidate             = CORRECTIVE_CANDIDATE
E35VerifierCorrectness            = FAILED_PINNED_CONSTANTS
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
CandidatePRState != CanonicalMainState
DeclaredGovernance != ServerEnforcedGovernance
```

## Immediate sequence

1. Correct manifest/schema semantics only.
2. Capture expected-red verifier output.
3. Repair verifier separately.
4. Keep E3.5 withheld until runtime-derived state digest and all required predicates are real.
5. Run second-host replay.
6. Enforce Gate Zero server-side.
7. Bind one formal lemma to the live spine or stop adding formal surface.

No item above changes W0, O0, or production status.
