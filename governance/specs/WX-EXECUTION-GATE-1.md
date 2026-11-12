# Execution gate (`weaver_runtime.gate`)

**Status:** IMPLEMENTED
**Evidence:** R2[self]
**Authority:** O0. The gate records decisions made by an injected authorizer and grants nothing itself.
**Outline step:** 5, part 2

## Order

| Stage | Check | Refusal (Rejection Root) |
|---|---|---|
| 0. Pin | the proposal canonicalizes and every field passes the contract; its canonical bytes are pinned before anyone else sees it | raises `GateContractError`, like a non-`Proposal` argument |
| 1. Observe | veto source clear | `VETO_ACTIVE`; the authorizer is **not called** |
| 2. Authorize | injected authorizer allows; a decision that is malformed or raises counts as a refusal; the proposal still matches the pin after the authorizer returns | the authorizer's `reason_code`, `AUTHORIZATION_ERROR`, or `PROPOSAL_MUTATED` |
| | window = min(`valid_until`, now + `max_window`) is still open | `WINDOW_EXPIRED` |
| 3. Reserve | proposal not already committed (early check against the ledger at startup) and not already running in this gate | `ALREADY_COMMITTED`, `ALREADY_RESERVED` |
| 4. Execute | the action stages a result; `context.checkpoint()` rechecks the proposal against the pin, the veto, the window, and **authority** (authorizer asked again) | aborted: `EXECUTION_FAILED`, `PROPOSAL_MUTATED`, `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
| 5. Revalidate | proposal matches the pin (before and after the authorizer is asked again), veto clear, window open, **authorizer asked again** still allows, with a decision that has not expired | aborted: `PROPOSAL_MUTATED`, `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
| 6. Commit | result recorded on the Authority Root (`EXECUTION_COMMITTED`) with ledger `unique_key` `EXECUTION_COMMITTED:<proposal_id>`, enforced inside the append's transaction | aborted: `ALREADY_COMMITTED` (another gate won), `RESULT_NOT_RECORDABLE` |

**Every call produces exactly one receipt, while the ledger can record.** A commit goes on the
Authority Root, and every refusal and abort goes on the Rejection Root, with its stage and detail. If
the ledger itself fails (for example `LedgerBusy`), `execute` raises, nothing is committed, the
reservation is released, and **no receipt exists for that call**. Durable recovery from ledger
failure is not implemented.

## Decisions built into the design

- **The commit is the ledger append.** Actions stage results and must not apply irreversible effects.
  Callers apply external effects only after a `COMMITTED` outcome. The gate cannot enforce this
  for code it does not control.
- **A latch in EVALUATING counts as a veto.** The RTL only asserts `veto_signal` 68,001 cycles after
  a trigger, but it is irreversibly committed to TRIGGERED from the first cycle. `TwinVeto` therefore
  refuses as soon as the state leaves ARMED (`test_observe_comes_before_authorize`).
- **Authority is asked for again before the commit and at every checkpoint.** A revocation between
  the first authorization and the commit aborts it, even though the first verification passed
  (`test_revocation_between_authorize_and_commit_aborts`). A revocation during a long action stops
  it at the next checkpoint (`test_revocation_mid_action_is_caught_at_the_next_checkpoint`).
- **The authorizer must be a side-effect-free query.** It is called at least twice per execution,
  plus once per checkpoint, and must answer "is this proposal authorized right now?". A one-shot
  verifier that consumes a token or records a replay key on each call (`CryptoVerifier` does) cannot
  be passed in directly: its second answer is a replay refusal, so every execution aborts
  (`test_one_shot_authorizer_cannot_commit`). That fails closed, but such a verifier needs an
  adapter that verifies once and then answers revocation and expiry queries.
- **Fail closed.** An authorizer exception, a non-decision return value, an unrecordable result, or an
  action exception all end in a Rejection Root receipt, never in a commit.
- **What is recorded is what was submitted.** `Proposal.payload` is a deep read-only view of the
  payload's canonical bytes, so in-place edits raise. Because `object.__setattr__` bypasses any frozen
  dataclass, the gate also pins the proposal's canonical bytes on entry, takes every id from the pin,
  and writes only the pinned copy into receipts. A proposal that no longer matches the pin aborts with
  `PROPOSAL_MUTATED`, and a proposal poisoned with a non-canonical value still gets exactly one receipt
  (`tests/gate/test_proposal_integrity.py`). Before this, an action could rewrite the payload and
  commit it under the decision issued for the original, or leave no receipt at all.

## Tests and mutations

`tests/gate/test_execution_gate.py` has 38 tests covering every row above, replay across a ledger
reopen, concurrent execution of one proposal in one gate and across two gates sharing a ledger,
reservation release after an abort, the one-receipt-per-call invariant, ledger failure, and the
two commit-boundary characterization tests. `tools/check_verifier_mutations.py` disables the pre-commit live
check, pre-commit re-authorization, checkpoint re-authorization, the EVALUATING-is-veto rule, and
the replay guard. Each is caught by a named test.

## Ledger-authoritative commit guard (candidate for C-GATE-001)

**Status:** candidate, implemented on this branch. **C-GATE-001 is not closed.** This is the
ledger-recorded form of the same-transaction direction chosen in GD-0003 (D8).

- `ReceiptLedger.set_control` writes the `veto` control and `revoked:<proposal_id>` controls under the
  commit's own serialization lock, logged in `control_log`.
- `ReceiptLedger.admit(..., guard=...)` runs the guard after `BEGIN IMMEDIATE` and before any write.
  A `CommitRefused` rolls the transaction back and nothing is written.
- The gate's guard refuses with `VETO_RECORDED_BEFORE_COMMIT` when `veto` is `active`, and with
  `REVOKED_RECORDED_BEFORE_COMMIT` when `revoked:<proposal_id>` is `revoked`.
- **Defined ordering.** A control committed before the commit's transaction is seen and refuses the
  commit. A control written after the commit is ordered after it and does not undo it.
- **Closure criterion status.** `test_veto_recorded_in_the_ledger_before_commit_aborts` commits on the
  gate without this guard, and aborts with it. The mutation `commit-boundary-gate-guard-unwired` shows
  the test depends on the guard. The pre-candidate gate had no `set_control`, so the test cannot run
  against it unmodified. The behaviour, not the API, is what it tests.

**Still open (why this is not closure):**

- The physical latch does not write into the ledger. Until a bridge does, the hardware veto is not
  covered by this path.
- The in-memory twin veto stays advisory. Its characterization tests still commit.
- Controls are outside the verified chains and the state digest. A verifier cannot check control history
  independently, so control history is not evidence until it is anchored.
- Scope is one SQLite store on a local file system. A second store is not covered.

## Limits

- **The commit boundary is not atomic with the veto or the authorizer (C-GATE-001).** Revalidation
  happens immediately before the ledger append, but a veto or revocation in between is not seen, and
  the commit goes through. Two characterization tests pin this:
  `test_known_limit_veto_in_the_commit_interval_still_commits` and
  `test_known_limit_revocation_in_the_commit_interval_still_commits`. More checks would only shrink the
  window. Closing it needs the veto and revocations to share a serialization point with the commit (for
  example, both recorded through the same ledger transaction), or the hardware veto to gate the
  actuator directly. **Effect confinement is therefore not claimed.**
- Multiple gates on one ledger: at most one commit per proposal, enforced by the ledger's `unique_key`
  (`test_two_gates_sharing_a_ledger_cannot_both_commit`). Live reservations are per gate, so two gates
  may both *run* the action for the same proposal. Only one commits, and the other aborts with
  `ALREADY_COMMITTED`.
- **A decision is not bound to the proposal it was issued for.** `AuthorizationDecision` carries no
  proposal id or digest, so the gate cannot tell a decision issued for this proposal from one issued
  for another. That binding is the authorizer's responsibility. Closing it needs a proposal digest
  in the decision contract, checked by the gate.
- The veto source is the software twin. Wiring it to a real latch is outside this repository.
- Windows use an injected integer clock. Clock trust is the deployer's problem.
