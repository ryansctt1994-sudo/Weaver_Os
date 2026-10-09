# P0-004 — Read-only Weaver evidence-bundle verification

**Status:** maintained-source review candidate. **Authority:** O0 WITHHELD. **Witness:** W0.
**Portfolio evidence ceiling:** E2. **Production:** PROHIBITED.

## Purpose and source relationships

The maintained verifier runner (`tools/verify_all.py`) generates the
`verification-output/` reports and hashes. The new
`tools/verify_evidence_bundle.py` is a **separate implementation** with no
imports from the generating runner. It reads finalized bytes, compares their
hashes, cross-checks redundant transcripts, and rejects unsafe paths or
ambiguous source labels. It does not rerun the generating tests or authenticate
the source, operator, reviewer, or GitHub Actions environment.

Existing PR #83 repairs two related producer bugs: stale report hashes on
output-directory reuse and evidence label shadowing. P0-004 checks the consumer
side without depending on the implementation of either PR #83 repair. **Neither
PR implies the other is merged.**

The parsing/policy separation was informed by:

- [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md),
  which binds named subjects to their digests.
- [SLSA v1.2 Verification Summary Attestation](https://slsa.dev/spec/v1.2/verification_summary),
  which distinguishes verification policy/results from trusted signer/verifier
  identity and requires authenticated envelopes for delegated trust.

**This package neither emits an in-toto attestation nor claims SLSA conformity.**

## Run

After the existing `make verify` has produced a complete local bundle:

```bash
python -m tools.verify_evidence_bundle --root . --output verification-output
```

For separately supplied repo and evidence directories:

```bash
python -m tools.verify_evidence_bundle --root /path/to/pinned/checkout \
  --output /path/to/unpacked/verification-output
```

A success emits `BUNDLE_BYTES_CONSISTENT` and
`LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION` with the claimed commit,
checked-file count and manifest digest. A refused or failed producer report
returns nonzero. This result is **not** an independently controlled witness
receipt or a trusted assertion of execution.

## Bounded verification rules

1. Parse report and manifest JSON with duplicate-member and nonfinite-value
   rejection; require supported schema and explicit local assurance scope.
2. Require the canonical `verification-report.json` and `report.json` bytes
   to be identical.
3. Validate report against the repository's verification-report schema.
4. Hash the manifest bytes and compare to the report's exact manifest SHA-256;
   require report and manifest artifact inventories to agree.
5. Check **every** manifested file against its SHA-256; reject unknown,
   missing, traversal, ambiguous, duplicate-alias, and symlinked file paths.
6. Require output files other than the three generated reports to be manifested.
7. Require lockfile binding, exactly one recorded wheel digest when PASS,
   per-step log contents, and the exact flattened verifier-command transcript.
8. Require all seven expected verifier identities, all six adversarial case
   IDs, the adversarial JSON document and fixture hashes, and an actual
   positive producer verdict.
9. Return a bounded byte-integrity conclusion, never operational authority.

## Attack fixtures

`tests/test_evidence_bundle_independent.py` supplies synthetic complete
bundles (inside and outside the checkout) and mutations for changed/missing
logs, forged commands, wheel digest mismatch, changed adversarial results,
manifest hash drift, duplicate JSON keys, shadowed output basenames,
symlinks, path traversal, inconsistent report copies and untracked files.
Synthetic fixtures are **not** signed or representative of a production
reproduction run.

## Limits and next gate

- This checks **current bytes only**. It does not establish immutable
  snapshot semantics if an attacker can modify the files during verification.
  An independently owned archive, trusted digest/checkpoint and filesystem
  isolation are needed for a stronger claim.
- The schema and source root are supplied by the caller. This tool does not
  independently pin trusted Git commit identity or policy.
- An attacker able to rewrite the entire bundle and recompute all unkeyed
  hashes can still construct a mutually consistent forged bundle. A trusted
  signer and separately controlled trust root are required.
- A log saying PASS is not proof the command executed. Independently replay
  the commands and compare results in a controlled external environment.
- No external reviewer, authenticated attestation, WORM store, branch
  enforcement, production deployment, or E4 witness is established.
- Do not automatically reuse private historical archives when content cannot
  be retrieved and byte-verified.

**Canonical boundary:** E2 | W0 | O0 WITHHELD | PRODUCTION PROHIBITED.
