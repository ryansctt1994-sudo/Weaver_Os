# Consolidated review candidate

This candidate combines the JSON nesting repair (#134), the Zorel/Delta
proposal bridge and adversarial tests (#130–#131), and selected Cathedral/Forge
capabilities under Weaver's existing owner, contracts and ReceiptLedger.

V008 HOLD. E2 ceiling / W0 / O0. No production authorization or independent
validation is claimed. A successful donor test does not promote a combined tree.

## Available under Weaver

- `python -m tools.claim_audit ROOT --json REPORT`: advisory claim analysis.
  The CLI and legacy JCS report profile are retained; existing Zorel/Delta pins
  remain valid in the donor repository. This tool does not grant execution rights.
- `tools.consolidation.findings`: repeated-observation comparison and duplicate
  suppression. Results remain EVIDENCE_ONLY / O0. Observations are supplied by the
  caller and do not establish reviewer independence or authenticated ground truth.
- `weaver_verifier.public_log.verify_publication`: offline retained Rekor inclusion
  verification with a pinned log key. File loading is in
  `python -m tools.consolidation.verify_publication MANIFEST ENTRY LOG_KEY`.
  Historical signed bytes retain their original profile; authority data continues
  to use WX-CJSON-1. Publication does not establish correctness of published claims.
- `make test-hw-consolidation`: core/twin vectors, failure controls, Arty startup
  reset and debounce simulations. Physical reproduction and vendor timing closure
  are still open gates. Board programming scripts are manual-only artifacts.
- `forge/`: contributor/reviewer reference documents and expanded receipt fields.

`source-manifest.json` pins original commits, source bytes, transformed target
bytes and disposition. `python -m tools.consolidation.validate` refuses drift,
escaped paths, symlinked assets or activation through the manifest.
Five independent control-removal checks cover the log SET signature, signed
checkpoint, finding type distinctions, asset digests and advisory import boundary:
`python -m tools.consolidation.check_mutations`. A failed baseline refuses scoring.

## Preserved research, not enabled authority

`research/consolidation/snapshots/` contains eight original source snapshots,
including their licenses, tests and limitations. They preserve Chronicle,
the Cathedral P0 recognizer, the staging authority spine, the Ed25519 role gate,
Agent OS, finding confirmation and Forge. No runtime module imports these sources.

The P0 recognizer still has a post-parse recursion failure. Agent OS still captures
subprocess output before truncation and uses a legacy assurance-core dependency.
The original HMAC gate has custody limitations; the separate Ed25519 role gate
still requires live non-root deployment and independent adversarial acceptance.
Keeping source here does not enable, fix or accept those boundaries.

Do not replace Weaver's ledger, canonical authority profile or owner with donor
implementations. The archived source and historical receipt hashes remain intact.

## Validation and remaining acceptance

`make validate-consolidation` checks asset integrity, the new tests, trust domains
and this documentation's claim language. `make verify` runs the complete software
verification gate. Root-required owner tests and V008 mutations remain separate;
the hardware target runs simulation only. The consolidation workflow records the
Python matrix and hardware checks on every PR, including stacked branches.

An exact source head, clean-tree result and raw reports must accompany each gate.
Issue #1 authorization/commit acceptance, peer admission control, independent
reproduction, physical hardware and production acceptance remain open.
