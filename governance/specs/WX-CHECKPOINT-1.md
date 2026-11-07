# wx-checkpoint-1: witness checkpoints

**Status:** IMPLEMENTED ([GD-0005](../decisions/GD-0005.md) D14)
**Evidence:** R2[self]. Witness: W0. Every witness exercised so far is simulated.
**Authority:** NONE. A checkpoint attests what a witness saw. It grants nothing.
**Outline step:** 7 (independent evidence custody), design in [STEP7-EVIDENCE-CUSTODY](STEP7-EVIDENCE-CUSTODY.md)

## The statement

```json
{
  "schema": "wx-checkpoint-1",
  "ledger_id": "wx-test",
  "witness_id": "witness-a",
  "checkpoint_seq": 1,
  "roots": {
    "AUTHORITY": {"length": 3, "head": "<receipt_digest of entry 2>"},
    "REJECTION": {"length": 1, "head": "<receipt_digest of entry 0>"}
  },
  "chronicle_root": "<wx-chronicle-anchor-1 digest of ledger_id and both heads>"
}
```

- `checkpoint_seq` is the witness's own counter for this ledger, starting at 1 and increasing by
  one per signed checkpoint.
- `chronicle_root` is recomputed on parse. A statement whose root does not match its heads is
  MALFORMED.
- Exact field sets everywhere. A checkpoint cannot carry a public key or anything else a
  verifier might be tempted to trust.

## Signing

The witness signs, with Ed25519:

```text
b"wx-checkpoint-1\x00" + WX-CJSON-1(statement)
```

The domain prefix keeps these bytes distinct from every other signed format. A signature over
the bare canonical statement does not verify (`test_signatures_are_domain_separated`).

A signed checkpoint is `{"statement": {...}, "signature": {"algorithm": "ed25519", "value": "<128 hex>"}}`.

## Verifier: `weaver_verifier.checkpoint.custody_report(snapshot, checkpoints, *, pinned_keys)`

`pinned_keys` maps `witness_id` to a 32-byte public key in hex. It is required and must come
from somewhere other than the data under test. The checks run in this order, and the first
failure refuses:

| Check | Refusal reason |
|---|---|
| The snapshot verifies (`verify_snapshot`) | `SNAPSHOT_INVALID` |
| Each checkpoint parses strictly | `MALFORMED` |
| Its witness is pinned | `UNPINNED_KEY` |
| Its signature verifies under that pinned key | `BAD_SIGNATURE` |
| It is for this ledger | `MALFORMED` |
| No two checkpoints give different heads for the same root and length; no witness signs two different checkpoints with one sequence number, or shortens a root between its own checkpoints | `SPLIT_VIEW` |
| The snapshot extends every checkpoint: at least as long per root, and the entry at the checkpoint's length has its head as `receipt_digest` | `REGRESSED`, `FORKED` |

Results:

| Status | Meaning |
|---|---|
| `REFUSED` | a check above failed. Nothing is repaired. The reason says to freeze and escalate |
| `UNWITNESSED` | no checkpoints. History before the first checkpoint cannot be told apart from a rewrite |
| `CHECKPOINT_CONSISTENT` | every check passed |

Every report also carries `witnesses` (distinct pinned witness ids), `corroboration`
(`UNCORROBORATED` for one, `CORROBORATED` for two or more), `covered` and
`unwitnessed_entries` per root, `freshness` (`COVERED_TO_HEAD` or
`NO_CHECKPOINT_FOR_LAST_<n>_ENTRIES`), `independence: NOT_ESTABLISHED` and `witness_level: W0`.
There is no `WITNESSED` status.

## Witness: `weaver_witness.witness.Witness`

- Signs only a snapshot that verifies and extends its last checkpoint for that ledger. A state
  it has already signed returns `UNCHANGED` with the same checkpoint.
- Refuses anything else (`INVALID_SNAPSHOT`, `REGRESSED`, `FORKED`, `MALFORMED`), and appends
  the refusal to its log.
- Its log is JSON Lines of WX-CJSON-1 records, fsynced per append. On start it re-verifies
  every checkpoint in the log against its own key and checks the sequence numbers. A log it
  cannot account for raises `WitnessLogError`.

## Limits

- **Independence is not checkable.** A witness counts only if someone the operator does not
  control holds its key and log. In this repository every witness is simulated.
- **Before the first checkpoint, nothing is detected.** If a witness first sees an already
  rewritten history, the verifier reports it consistent
  (`test_known_limit_a_rewrite_no_witness_ever_saw_is_indistinguishable`).
- **After the newest checkpoint, nothing is covered.** Those entries are counted, not checked.
- **No time.** Checkpoints bind content. Staleness is counted in entries.
- **Corroboration counts witness ids, not channels.** Fetching checkpoints from at least two
  channels the operator does not control is the caller's job.
- **No key rotation, no publication.** Both are open (STEP7 "Custody rules").
- **Single process per witness log**, on a local file system.
