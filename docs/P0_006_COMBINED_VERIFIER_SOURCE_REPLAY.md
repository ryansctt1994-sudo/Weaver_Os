# P0-006 Combined Verifier Review

Date: 2026-10-09 UTC. **Review-only**; no merge or production deployment.

## Exact sources

- Base main: `50ffc20917e4ca2748f3f647acaec23b3f724855`.
- [PR #83](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/83) head `6422531c14bb00f708c25b394a703b52b95285c1`: candidate branch origin. Excludes regenerated reports from the manifest and rejects evidence-label collisions.
- [PR #80](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/80) head `d0773c4c7d5172a69ca06acf18514421e2df99a7`: transferred verdict checking function, mypy flags, and regression tests.

PR #80's historical inventory documents were not copied. Neither original PR was modified. The new integrated tests check that both repair families remain active in the combined candidate.

## Review checks

```bash
python -m pytest -q
python -m ruff check .
python -m mypy .
```

Check hosted CI **at this exact combined head** before any merge consideration. Separate green PRs do not imply an integrated green result. This does not include the distinct consumer-side PR #84.

**Status E2; W0; O0 WITHHELD; production PROHIBITED.**

## Additional consumer-side integration: PR #84

The same review branch also transfers the **read-only** verifier from
[PR #84](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/84) at exact head
`2a7a77aaa2a078d3e95be24c7cee6361cf5e0af8`:

- `tools/verify_evidence_bundle.py`: standalone byte-level validation of final
  manifests, outputs, logs and related report fields.
- `tests/test_evidence_bundle_independent.py`: negative tests for tampering,
  missing artifacts, dangerous paths and forged report fields.
- `docs/P0_004_EVIDENCE_BUNDLE_VERIFIER.md`: bounded trust model.
- `.github/workflows/verification.yml`: run the independent verifier only
  after the complete existing verification producer.

The composite therefore tests producer-side verdict guards, producer-side
manifest integrity, and consumer-side bundle checking on **one commit**.
Neither PR #84 nor its release authority is promoted or merged. No authenticated
independent witness has been acquired.

The producer/consumer full workflow must pass on this combined head. The
consumer reports only locally consistent bytes; it is not a trusted
attestation, nor is the reviewed composite a production release.
