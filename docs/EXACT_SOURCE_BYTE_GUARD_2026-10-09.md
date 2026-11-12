# Exact-source byte guard — local reproduction candidate

Source base: PR #91, `e7a9a2a78d6376fbd0117733d21e09b933056962`.

## Defect

An exact HEAD plus a clean `git status` did not establish that the files used
by the operator rehearsal contained that commit's bytes. `assume-unchanged`
and `skip-worktree` hid modifications and missing files. Git's filemode setting
hid executable-bit changes. Clean filters could normalize a different worktree
back to the committed blob. Replacement refs could redirect the tree while
preserving the displayed HEAD identity.

The controlled regressions reproduced these false admissions. They also cover
symlink and FIFO substitutions: the latter must be refused without opening it.

## Repair

The existing preflight runs both before and after the complete verifier. It now
reads the pinned commit's NUL-delimited tree with replacement objects disabled,
checks every tracked entry is an ordinary file with ordinary directory parents,
compares executable mode, and computes each Git blob identity directly from raw
worktree bytes. It bypasses index flags and clean filters. The local result
adds `source.tracked_source_binding = GIT_BLOB_BYTES_AND_EXECUTABLE_MODE_PRE_POST`.

This exact-source profile refuses tracked symlinks and submodules. It also
refuses line-ending conversions; use an exact-byte checkout. Unchanged files
with index optimization flags remain valid. Filenames containing spaces, tabs,
or newlines are parsed using NUL boundaries rather than whitespace splitting.

## Local validation

Python 3.12, assistant-managed Linux environment, 2026-10-09:

- Exact base plus the new operator tests: 9 failures / 20 passes.
- Repaired operator tests: 29 passes.
- Full repository: 294 passes.
- Whole-repository Ruff and configured mypy: PASS.

Reproduce with `python -m pytest -q tests/test_reproduce_review_candidate.py`.
Copy that test file onto the exact base implementation to reproduce RED.
Hosted CI and the detached exact-commit rehearsal qualify their own published
head separately; local results do not predict or replace those runs.

## Limits

This compares tracked source snapshots, not atomic process identity. It does not
detect changes made and restored between checks, authenticate the Git binary or
host, isolate ignored/generated files or Python imports, or attest interpreter
and dependency provenance. The SHA-1 check implements the existing Git object
identity, not a new cryptographic trust anchor. No production authority or
independent witness is created. E2 / W0 / O0 WITHHELD / PRODUCTION PROHIBITED /
E4 NOT EARNED remain unchanged.
