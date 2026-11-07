# ReceiptLedger (store `wx-receipt-ledger-store-1`)

**Status:** IMPLEMENTED (`weaver_runtime.ledger`, `weaver_verifier.ledger`, `weaver_contracts.ledger`)
**Evidence:** R2[self] (implementation plus origin-controlled tests in this repository)
**Authority:** O0
**Outline step:** 3 (§5.2)
**Implements:** Lumen-Nexus ADR-0006 "Single-Owner ReceiptLedger", **accepted for this
repository by [GD-0002](../decisions/GD-0002.md)** (single steward). It is still PROPOSED in
Lumen-Nexus itself.

## Why

Two of the three Chronicle implementations being merged let linkage state live outside a
single owner. That is the defect class behind `C-RCPT-001`. Both behaviours were reproduced
in this session:

| Source | Behaviour observed | Consequence |
|---|---|---|
| Lumen `src/lumen/chronicle.py` | `last_hash` is held per instance. Two `Chronicle` objects on one file each append from their own head | The chain forks; `Chronicle.verify` returns `False` |
| Lumen `src/lumen/chronicle.py` | Appends are not atomic and not fsynced; reopening after a torn last line raises `JSONDecodeError` | The ledger cannot be reopened after a crash |
| cathedral-verified `chronicle/chronicle.py` | `merkle_root` pads odd layers by duplicating the last leaf, so `[a,b,c]` and `[a,b,c,c]` share a root | Harmless there (chain links plus anchor count catch it), but the root alone is ambiguous, so it is **not** carried over |

Cathedral's chain verification and head anchoring were sound. Its adversarial suite is ported
as the core of the new tests.

## Design

- **One owner.** `ReceiptLedger` alone assigns `sequence`, chooses `predecessor_digest`,
  and advances each root's head. `admit()` and `reject()` take event content and a gate
  decision. They have no parameter through which a caller could pass linkage state.
- **Dual Ledger.** `AUTHORITY` and `REJECTION` are separate hash chains, each with its own
  sequence from 0. The **Chronicle Root** (`weaver_contracts.ledger.chronicle_root`) binds
  both heads and lengths. Rejected and quarantined attempts are receipted on the Rejection Root
  and are never state.
- **Receipts are the chain.** Each entry stores the WX-CJSON-1 canonical event bytes and its
  wx-receipt-1 receipt. A receipt's `predecessor_digest` is the previous receipt's
  `receipt_digest` in the same root.
- **Atomic.** One SQLite transaction (`BEGIN IMMEDIATE`, WAL, `synchronous=FULL`) inserts the
  entry and advances the head. Any failure rolls back both. The receipt is returned only after
  `COMMIT`.
- **One total order.** Concurrent writers (threads or processes) are serialized by SQLite.
  Each append either commits with the next sequence or raises `LedgerBusy`.
- **Fail closed on a corrupted store.** Before extending a root, the ledger checks that the head
  row matches the root's entry count and last receipt digest, and raises `LedgerCorrupted`
  otherwise. This is a local guard only. Full re-verification is the verifier's job.
- **Read-only verification.** `weaver_verifier.ledger.verify_snapshot` imports only contracts,
  so under UADR-0001 (enforced by `tools/check_trust_domains.py`) it cannot reach the ledger to
  append, latch, or repair. It never modifies its input.
- **Anchors.** `ReceiptLedger.anchor()` returns lengths, heads, and the Chronicle Root. Without
  an anchor held somewhere the operator cannot rewrite, truncation and full forward-recompute
  rewrites are undetectable, and the verifier's verdict says so explicitly.

## ADR-0006 required evidence → tests

| ADR-0006 requirement | Tests (`tests/ledger/`) |
|---|---|
| Positive append and replay | `test_append_assigns_sequence_and_links`, `test_roots_have_independent_chains`, `test_replay_reconstructs_identical_chain`, `test_persistence_round_trip` |
| Predecessor, sequence, and canonicalization mismatch rejection | `test_T3_…`, `test_T4_…`, `test_T5_…`, `test_X2_non_canonical_event_bytes_rejected_even_with_matching_digest`, `test_refuses_to_extend_when_*` |
| Mutation isolation: ingress, storage, return | `test_ingress_mutation_after_append_changes_nothing`, `test_stored_bytes_are_the_hashed_bytes`, `test_returned_objects_do_not_alias_store`, `test_X9_verifier_does_not_modify_its_input` |
| Concurrency | `test_threads_with_separate_instances_get_one_total_order` (8×25), `test_shared_instance_is_safe_across_threads`, `test_processes_get_one_total_order` (4 processes×25), `test_busy_store_fails_explicitly_and_changes_nothing` |
| Interrupted transactions | `test_failure_inside_transaction_rolls_back`, `test_process_killed_mid_transaction_leaves_store_consistent` (child calls `os._exit` after the insert, before `COMMIT`) |
| Failed appends do not advance | `test_failed_admission_does_not_advance` (6 cases) |
| Callers cannot own linkage | `test_callers_cannot_supply_linkage` (5 cases) |
| Cross-runtime canonicalization vectors | WX-CJSON-1 vectors (step 2) |
| Clean-clone repair receipt | **Not done.** See below |

## cathedral-verified suite → ported tests

| Cathedral | Port (`test_ledger_adversarial.py` unless noted) |
|---|---|
| T1 honest chain verifies | `test_T1_honest_chain_verifies` |
| T2 payload edit | `test_T2_payload_edit_detected` |
| T3 tamper + re-hash one entry | `test_T3_local_reseal_breaks_downstream_link` |
| T4 reorder | `test_T4_reorder_detected` |
| T5 delete | `test_T5_deletion_detected` |
| T6 truncation internally valid | `test_T6_truncation_is_internally_valid_without_anchor` |
| T7 forged insert | `test_T7_forged_insert_detected` |
| T8 persistence round-trip | `test_receipt_ledger.py::test_persistence_round_trip` |
| T9 on-disk tamper | `test_T9_on_disk_tamper_detected` (SQLite row edit) |
| T10 determinism | `test_T10_chronicle_root_is_deterministic_and_content_sensitive` |
| T11 anchor catches truncation | `test_T11_anchor_detects_truncation` |
| T12 full rewrite caught by anchor | `test_T12_full_forward_rewrite_fails_anchor` |

Cathedral's 15 checks are spread across these 12 scenarios (T6, T10 and T11 each make two),
and all of them are covered.

Lumen's Chronicle tests (two appends then `verify`; the FreeLattice import writing an
`event_type`/`data`/`metadata` entry) are covered by `test_append_assigns_sequence_and_links` and
`test_lumen_shape_event_type_data_metadata`. Those tests were written fresh. No Lumen
(Apache-2.0) code was copied, so the GD-0001 D4 rule for moved Lumen files is not triggered.

New cases with no Cathedral equivalent: X1 (re-sealing the *last* entry is caught only by an
anchor), X2 (non-canonical bytes with a matching digest), X3/X4 (moving a rejection onto the
Authority Root), X5–X7 (wrong ledger, foreign or tampered anchor), X8 (strict shapes), X9
(verifier purity), and X10 (a snapshot is itself WX-CJSON-1 exportable).

## Mutation checks

`tools/check_verifier_mutations.py` (run in CI) now includes 8 ledger mutations. Each disables
one guard in a copy of the repository and requires a named test to fail: head guard, rollback,
sequence ownership, link check, canonical-bytes check, event-digest check, anchor length, and
root check. All 14 mutations in the tool, the 6 existing ones and the 8 new ones, are detected.

## What is still open

- **ADR-0006 acceptance.** Done for this repository by GD-0002. It is still PROPOSED in Lumen-Nexus.
- **Repair receipt.** `C-RCPT-001` requires a reproducible repair receipt from a clean clone,
  bound to full source and environment hashes, under an approved receipt profile. The signed
  profile is blocked on Lumen-Nexus #13. Until both exist, `C-RCPT-001` stays OPEN, and nothing
  here is above R2[self].
- **Signatures.** Receipts carry integrity digests, not signatures.
- **External anchoring.** The ledger produces anchors, but no external append-only store or
  witness set holds them yet.
- **Retiring the old Chronicles.** `chronicle/` in this repository still defers to the RC1 witness
  archive (`C-STUB-001`). Switching it to this ledger is an admission decision, and Lumen's and
  Cathedral's copies are unchanged in their own repositories.
