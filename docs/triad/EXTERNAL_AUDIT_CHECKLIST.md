# Independent review checklist — bounded Triad kernel

Status: **UNVERIFIED CHECKLIST**. These are instructions to produce evidence, **not** a statement that an audit took place.

## Freeze the subject first

- [ ] Record repository URL, exact commit SHA, Git tree SHA, branch or PR, clean/dirty worktree, and hashes of any uncommitted overlays. Do not combine evidence from different heads.
- [ ] Record runtime, OS, dependency lock, interpreter version, command, exit code, actor/custody, and independent execution host.
- [ ] Use an isolated checkout with no production secrets or privileged mutation permissions.

## Testable audit work

| Check | Reproduction entry point or bounded gap | Pass requirement |
| --- | --- | --- |
| Install and baseline tests | `python -m pip install -e ".[dev]"`; `pytest -q` from the root README | Exact command and exit 0, test counts recorded |
| Build/package | `python -m build` | Built artifacts hashed and checked against source identity |
| Schema verification | `schemas/`, `triadic_controls/`, `packages/contracts/` | Locate and execute schema tests; reject invalid required fields and malformed types |
| Ledger integrity | `packages/runtime/`, `packages/verifier/`, `tests/` | Inject payload and prior-hash tampering and observe explicit refusal |
| Signatures and actor identity | `packages/verifier/`, `witness_py/`, `weaver_auth/` | Positive valid-signature test and negative unknown-key, bad-signature, revoked-key tests; mark untested cases UNVERIFIED |
| Replay reconstruction | `packages/runtime/`, `packages/verifier/`, `tests/` | Reconstruct deterministically from frozen records; reject reordered, missing, and duplicate records |
| P12 self-falsification | [P12_SELF_FALSIFICATION.md](P12_SELF_FALSIFICATION.md) | Invalid input intentionally constructed, refusal observed, receipt saved, replay reproduces rejection |
| Evidence labels | [EVIDENCE_LABELS.md](EVIDENCE_LABELS.md) | Each conclusion limited to inspected receipts and an executable reproduction path |
| Non-claims | [NON_CLAIMS.md](NON_CLAIMS.md) | Explicitly preserve production, external-witness and distributed non-claims |

Paths identify likely review surfaces, not a guarantee that a suitable test exists. If a step cannot run, record `UNVERIFIED`, the missing prerequisite, and the precise command/error; do not silently check the box.

## Required negative controls

Demonstrate that the checker itself fails (nonzero exit or explicit denial) when: a receipt byte changes; a signature is missing/invalid; a prior hash is wrong; a policy version is stale; a purported witness tries to authorize an action; or a test is intentionally made to fail. Separate controls actually run from proposed cases. Retain raw stdout/stderr, exact source hashes, and control outcomes.

## Evidence disposition

Capture a row for each claim: `claim_id | source_commit | source_tree | execution_identity | command | receipt_path+sha256 | control | result | evidence_label | reviewer | limitations`. Verify that the receipt is self-contained for the claimed reproduction, or downgrade the assertion to a reference-only record. An independent reviewer must use their own infrastructure and keys where independence is claimed.

No checklist completion, origin CI pass, or document change grants merge authority, E4, witness status, or production approval. Require separate human review and effective branch protection checks described in [issue #29](https://github.com/ryansctt1994-sudo/Weaver_Os/issues/29).
