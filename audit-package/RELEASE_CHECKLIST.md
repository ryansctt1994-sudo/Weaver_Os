# Release Checklist

## Before release

- All root documents are present.
- Evidence artifacts are present or marked pending.
- Documentation directories are populated or marked pending.
- Formal-methods artifacts are included or marked pending.
- Tests are present or marked pending.
- Scripts are present or marked pending.
- Environment assumptions are documented.
- Hashes are generated when the package is frozen.
- Claims and evidence are synchronized.
- Nonclaims are explicit.
- Limits and gaps are explicit.

## Integrity checks

- SHA256SUMS.txt matches included files after final hash generation.
- EVIDENCE_MANIFEST.md matches actual evidence items.
- CLAIM_TRACEABILITY_MATRIX.md covers every major claim.
- WITNESS_ATTESTATIONS.md matches witness records.
- FAILURE_AND_COUNTEREXAMPLE_LOG.md preserves failed paths.
- LIMITATIONS_AND_NONCLAIMS.md blocks overclaiming.
- VERIFY.md is sufficient for reviewer execution.

## Reviewer readiness

- Reviewer can identify the package boundary immediately.
- Reviewer can find the claims register immediately.
- Reviewer can find the replay package immediately.
- Reviewer can verify hashes immediately.
- Reviewer can record a conclusion using the template.

## Release status

Current status: package scaffold pushed; final artifact hashes pending.
