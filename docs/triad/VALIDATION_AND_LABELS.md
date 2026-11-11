# Triad validation and evidence-label procedure

Status: **DOCUMENTATION / UNVERIFIED**. This procedure makes the claim rules explicit; automation of these gates has not been established by this document.

1. Freeze exact commit and tree; if the worktree is modified, record a complete reproducible patch/overlay and its digest.
2. Run `python -m pip install -e ".[dev]"` then `pytest -q` in an isolated environment; preserve versions, exit status, and logs. Run `python -m build` when evaluating distributable artifacts.
3. Run the relevant targeted tests, including deliberately malformed and authority-spoofing negative controls. Log specific test identifiers, exit codes and their limitations.
4. Verify every cited receipt exists, is readable from the stated source, matches its declared hash, and contains enough inputs to reconstruct its scoped claim. A pointer alone is not independent reproduction.
5. Assign the narrowest supported label from [EVIDENCE_LABELS.md](EVIDENCE_LABELS.md). Broken or missing commands, hashes, artifacts or controls require downgrade to `UNVERIFIED`, `REPORTED` or `FAILED` as appropriate.
6. Capture reviewer/custody, environment, negative-control results, scope, and exceptions using [EXTERNAL_AUDIT_CHECKLIST.md](EXTERNAL_AUDIT_CHECKLIST.md). Do not equate source-owner CI with independent witnessing.
7. Check [NON_CLAIMS.md](NON_CLAIMS.md) and [DISTRIBUTED_BOUNDARY.md](DISTRIBUTED_BOUNDARY.md) before publishing any release or deployment-language claim.

For the P0 integration chain, follow the live review routing in [issue #29](https://github.com/ryansctt1994-sudo/Weaver_Os/issues/29). A green test run is not permission to merge or promote.
