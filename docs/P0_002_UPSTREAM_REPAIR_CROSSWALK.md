# P0-002 — maintained-source security repair crosswalk

**Date:** 2026-10-08  
**Disposition:** review candidate only; no upstream merge or production authority.  
**Portfolio posture:** E2 ceiling / W0 / O0 WITHHELD / PRODUCTION PROHIBITED / E4 NOT EARNED.

## Provenance boundary

The P0-001 historical-source transfer suite is reported in the engineering handoff
as 4/4 red-to-green repair families, 235 local component regressions, 9 additional
supervisor checks, and 19 transfer-gate integrity checks. **This repository change
does not import, reproduce, or independently verify that historical bundle.**
Its recovered private archives are not published here. Historical test counts must
not be attributed to the maintained source trees or to this pull request.

All examined upstream pins below identify source under review, **not an assertion
that the historical patch can be applied to that source**.

## Source-pinned mapping and decisions

| P0-001 family | Maintained source examined | Source identity | P0-002 determination |
| --- | --- | --- | --- |
| Weaver action allowlist | `Weaver_Os/releases/weaver-witness-signed-rc1/src/weaver_core.py`; `tools/witness_rc1_state_adapter.py` | `Weaver_Os/main` commit `50ffc20917e4ca2748f3f647acaec23b3f724855` | The frozen RC1 runtime *already* accepts only exact `action == "increment"` for its fixed target. Add a maintained-source regression guard through the manifest-checking adapter. **No transplant, no frozen-source modification.** |
| Lumen receipt/replay | `Lumen/src/lumen/authority/verifier.py`, `src/lumen/receipt.py`, `src/lumen/replay.py` | `Lumen/main` commit `4efe4145059520f8ffa68c2374860f841879ce6e`; candidate [Lumen PR #4](https://github.com/ryansctt1994-sudo/Lumen/pull/4), head `6f62977a3eb583095e672967e918f94554d6c33c` | An existing review candidate binds claim, receipt hash, and nonempty replay tip and hardens cache ID retries. Do not duplicate; review its precise code and CI. **Hash integrity is not signer authentication.** |
| Lumen-Nexus related promotion controls | `Lumen-Nexus/packages/verifier/lumen_verifier/pg001r.py` | `Lumen-Nexus/main` commit `93689d76431e796a63379a7019e4528d384a87be` | PG-001R is a separate, read-only promotion-gate implementation, **not** a direct substitute for the legacy receipt/replay module. No automatic patch. |
| Cathedral supervisor identity | `cathedral-verified` main tree and [candidate PR #1](https://github.com/ryansctt1994-sudo/cathedral-verified/pull/1) | `cathedral-verified/main` commit `1c4181714b48dd9d9616a0bebbb4fef8532deff8` | Neither the main tree nor inspected candidate P0 module exposes the historical three-source supervisor quorum interface. **No matching migration target identified.** Must locate the maintained supervisor before proposing code. |
| Shock Kernel account schema | Targeted Weaver, Lumen, and Cathedral source trees | As pinned above | The historical Shock account-state validator was not identified in these targeted source trees. **Target unresolved**; do not invent a schema migration or claim global absence. |

## This PR's narrow executable gate

`tests/test_p0_002_rc1_action_boundary.py` uses the maintained RC1 state
adapter. The adapter checks its underlying core against the frozen release manifest
before importing the runtime. Tests cover:

- Exact allowlisted action accepted in the bounded simulated run.
- Alternate action spellings and production-like names rejected.
- Protected counter unchanged after rejection.
- Rejected command ID not entered in the used-ID set.
- Receipt and Chronicle records showing identical before/after state on rejection.
- Correctly named but unauthorized or wrong-target commands rejected.

These tests are **green-baseline regression guards**, not a historical RED → GREEN
demonstration. They do not exercise a generalized production dispatcher or
assert that the RC1 release implements all Weaver deployment actions.
No frozen release byte, signature, or manifest is modified.

## Review / promotion gates

1. Check that the PR is based on the stated `main` commit and changes only its
   new test and this mapping document.
2. Require repository-native GitHub Actions testing on the PR head. Record run
   ID, head SHA, job name, result, and any failing steps; do not infer CI from
   prior branches.
3. Review existing [Lumen PR #4](https://github.com/ryansctt1994-sudo/Lumen/pull/4)
   against its own base and head. Run and inspect its tests, and document remaining
   threats: untrusted self-asserted replay reports and absent trusted issuer identity.
4. Locate the genuine maintained supervisor implementation before transferring the
   historical one-worker/three-sources identity fix; demand a failing spoofed-quorum
   counterexample against that **actual** source.
5. Locate the maintained Shock Kernel schema before transferring validator changes;
   demand invalid-account rejection against that **actual** source.
6. Only when source identity, pre-fix failure, targeted repair, regression, hosted CI,
   and separately controlled reproduction exist should those gates be reconsidered.

Passing this PR's checks will support a **maintained-source regression candidate**,
not merged status, independent E4 reproduction, witness admission, or authority.
