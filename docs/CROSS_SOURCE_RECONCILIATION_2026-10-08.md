# Cross-source reconciliation — 2026-10-08

**Purpose:** convert the connected-source sweep into explicit governance state without promoting evidence or authority.

Current state remains:

```text
E2 | W0 | O0 WITHHELD | PRODUCTION PROHIBITED | E4 NOT EARNED
```

## Source precedence

Machine-readable map: [`PORTFOLIO_SOURCE_MAP.json`](PORTFOLIO_SOURCE_MAP.json).

The portfolio now distinguishes canonical repository state, candidate PR state, exact artifact/receipt evidence, integration workspace material, archival sources, contact notifications, scheduled activity, and narrative reconstructions. No lower-precedence source silently overrides a higher-precedence admitted state.

## Workbench v0.9 local revalidation

The exact Library archive `Weaver_Workbench_v0.9_integrity_dev.zip` was re-executed on 2026-10-08 in an assistant-managed Linux x86_64 environment using Python 3.13.5.

Observed local result:

- outer ZIP SHA-256 matched the adjacent declared checksum: `d661f480531da762957acd2772233169560219641a980b076647b20ee516dc2c`;
- 53 ZIP members; no path-traversal members detected;
- `scripts/check_release.py`: `ok=true`, 52 shipped checksums verified;
- full unit suite: 176 tests PASS;
- demo PASS;
- reviewed local HTTP protocol-stub smoke PASS;
- bridge smoke PASS;
- local Git audit smoke PASS, with dirty and committed-blob tamper probes refused;
- live model inference: **false**.

Boundary: this is same-workspace/origin-class local evidence, not independent reproduction, not E4, and not production authority. The v0.9 line derives from archived v0.5.1 and does **not** inherit unavailable v0.5.2 crash-journal / `project-recover` / inode-bound export behavior.

## Receipt Core blocker correction

The older wording that `WN-RECEIPT-CORE-1.0` is simply missing the wrapper/`stable_result` construction is stale or partially superseded by later E4-001 material.

The honest current state is:

```text
WN-RECEIPT-CORE-1.0
BLOCKED / PRE-FREEZE ASSEMBLY
```

Known later progress includes the recovered target archive digest, locally qualified 8/8 targeted mutation suite, frozen `stable_result_sha256`, and required 5/5 wrapper negative controls.

The blocker is now to assemble the source + protocol + environment + output-invariance + mutation + nonclaims + instructions + negative findings under one `BundleDigest`, mechanically prove that the corrected behavior is inside that exact bundle, and pass the complete origin-side pre-arm audit.

Only then may it become `READY_FOR_EXTERNAL_ASSIGNMENT`, still at W0/O0 with no automatic evidence promotion.

## Gate A target drift

Machine-readable state: [`E4_GATE_A_STATUS.json`](E4_GATE_A_STATUS.json).

CALL-004 and WN-RECEIPT-CORE-1.0 have both been described historically as preferred first-witness candidates. Neither is admitted here as the ratified first target.

A valid Gate A decision must name exactly one artifact version and full digest and record why alternatives are deferred.

## Other cross-source corrections

- Google Drive contains Lucifer Latch RTL/testbench/checker/TLA+/configuration/constraint artifacts; this restores artifact provenance but does not establish physical FPGA validation.
- The Distributed Intelligence Compact has a send-ready expert review pack, but qualifying external review/outreach was not established in the connected Gmail sweep.
- Gmail retains earlier failed CI notifications; later GitHub runs may pass on later revisions. Preserve both histories and use GitHub as the current CI source.
- Dropbox is primarily historical/frozen lineage and provenance recovery, not the live control plane.
- ChatGPT Library is an integration/staging plane, not canonical authority.
- The primary Google Calendar search for October 2026 returned no witness/pilot/review events; absence of a scheduled event is not itself a blocker, but no calendar evidence of external execution was located.

## Result

The portfolio is stronger because provenance and execution state are now more explicit. No axis is promoted.

> Better bookkeeping is not stronger evidence. Better bookkeeping makes stronger evidence possible.
