# Step 7 design: independent evidence custody (DRAFT)

**Status:** DRAFT. Not implemented. Proposed under GD-0003 (D10), not yet ratified.
**Closes (when implemented and witnessed):** C-CUSTODY-001
**Evidence now:** none. This document is a design, not an result.
**Authority:** NONE. Witness: W0.

## Goal

An operator who holds the ledger must be unable to rewrite history **and** the trusted
reference together without an independently controlled witness detecting the substitution.

This is measurable. The acceptance tests in section 6 define it.

## The problem, stated concretely

Step 6 control C8 shows the gap. A party that holds the ledger can rewrite every entry, recompute
every digest, and publish a matching anchor and state digest. `state_report` returns
`ANCHOR_MATCHED`, and that status is correct about the arithmetic. It says nothing about who
wrote the history. Any design in this document must address that directly.

## Design

### 1. Witness keys the operator does not hold

A witness is a party that signs **checkpoints**. Checkpoints are signed with Ed25519, and the
keys are held by someone other than the ledger operator. The verifier accepts only signatures
from a pinned set of witness public keys, supplied out of band. A key taken from the snapshot
under test is never trusted.

This follows the pinned-root pattern already used by `triadic_controls`.

### 2. Checkpoint content

A checkpoint signs a canonical (WX-CJSON-1) statement with these fields:

- `schema`: `wx-checkpoint-1`
- `ledger_id`
- `checkpoint_seq`: the witness's own counter, strictly increasing
- `chronicle_root`, which already binds both roots' lengths and heads
- `roots`: `{AUTHORITY, REJECTION}` → `{length, head}`
- `witness_id`

### 3. Witness behaviour: append-only and fork-refusing

A witness signs a new checkpoint only if the new state **extends** its last signed state. To
check that, it requires the entries from its last checkpoint onward. For each root, the entry at
the old length must have the old head as its `receipt_digest`. Since receipts already link through
`predecessor_digest`, that check is a prefix check.

If the new state does not extend the last signed one, the witness refuses to sign. Refusal is
a logged event, not an error to be hidden.

### 4. Verifier behaviour

`verify_snapshot` gains an optional witness requirement. A snapshot is accepted as witnessed only
if:

- a checkpoint carries a valid signature from a pinned witness key;
- the snapshot extends that checkpoint (the same prefix check as the witness);
- the checkpoint's Chronicle Root matches the snapshot.

A report based on this path can say `WITNESSED` only when the witnesses named in the report are
independent of the operator. The report must state which keys were pinned and where they came
from.

### 5. Publication cadence

A rewrite is detectable only against a checkpoint that already exists. So the detection window is
the time between checkpoints. Publication must be frequent and must happen automatically.

Silence is not proof. A witness that stops receiving checkpoints can only report absence. The
verifier must report "no checkpoint since N" and never report the history as current.

## What this detects

- Truncation or rewriting **after** a signed checkpoint, provided the witness saw the honest
  history before the rewrite.
- A complete recomputation that disagrees with any signed head at or before the checkpoint.
- A witness that is shown two different histories at the same checkpoint (a fork), if the
  witnesses compare notes or the pinned set has more than one member.

## What this does not detect (stated limitations)

- **A rewrite before the first checkpoint.** If no witness ever saw the honest history, a
  self-consistent alternative is indistinguishable from it. That case must be reported as
  UNWITNESSED, not authentic.
- **A rewrite after the last checkpoint.** It is undetectable until the next checkpoint is
  published. Detection latency equals the checkpoint interval.
- **Witness key compromise or collusion.** One compromised witness is caught only if another
  witness saw the honest history. With a single witness, nothing is caught.
- **Withheld publication.** Detected only as absence (section 5).
- **The operator's own clock, and what the witness was told.** Checkpoints bind content, not
  wall-clock truth.

## The blocker that code cannot remove

An "independently controlled" witness is a second party: another person or organization that
holds a key and runs a witness. The repository cannot supply one. This is the same organizational
blocker as C-DUAL-001.

Until a second party exists, the implementation can still be built and tested. In that case
every report must say the witness is **simulated by a key holder inside the test harness**, and the
status must remain W0.

## 6. Acceptance tests (required before any closure claim)

| # | Test | Required result |
|---|---|---|
| A1 | Honest checkpoint signed, snapshot extends it | accepted as WITNESSED |
| A2 | Operator recomputes the whole chain and re-issues the anchor after a signed checkpoint | refused: fork against the signed head |
| A3 | Operator rewrites before the first checkpoint | accepted, reported UNWITNESSED, never authentic |
| A4 | Witness is asked to sign a regressing or forked state | refuses, and logs the refusal |
| A5 | Checkpoint signed by a key not in the pinned set | rejected |
| A6 | Pinned keys supplied by the snapshot under test | rejected: keys are never taken from the input |
| A7 | Truncation after a signed checkpoint | refused: shorter than the checkpoint |
| A8 | Absence: no checkpoint for N intervals | reported as "no checkpoint since N", never as current |

Each test must also be added to the mutation checker, so that removing the prefix check, the
pinned-key check, or the refusal path is detected.

## Interaction with the existing digest

`wx-state-digest-1` is unchanged. Checkpoints bind the same `chronicle_root`. If the digest
preimage ever changes, that is a new schema version (`wx-state-digest-2`), and the old version is
refused rather than reinterpreted.

## Out of scope

Physical interlock validation (proposed step 8). Learning through PG-001R (proposed step 9).
C-GATE-001 (its own track under GD-0003).
