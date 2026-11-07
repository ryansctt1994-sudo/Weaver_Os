# Execution gate (`weaver_runtime.gate`)

**Status:** IMPLEMENTED
**Evidence:** R2[self]
**Authority:** O0. The gate records decisions made by an injected authorizer and grants nothing itself.
**Outline step:** 5, part 2

## Order

| Stage | Check | Refusal (Rejection Root) |
|---|---|---|
| 1. Observe | veto source clear | `VETO_ACTIVE`; the authorizer is **not called** |
| 2. Authorize | injected authorizer allows; a decision that is malformed or raises counts as a refusal | the authorizer's `reason_code`, or `AUTHORIZATION_ERROR` |
| | window = min(`valid_until`, now + `max_window`) is still open | `WINDOW_EXPIRED` |
| 3. Reserve | proposal not already committed (early check against the ledger at startup) and not already running in this gate | `ALREADY_COMMITTED`, `ALREADY_RESERVED` |
| 4. Execute | the action stages a result; `context.checkpoint()` rechecks the veto, the window, and **authority** (authorizer asked again) | aborted: `EXECUTION_FAILED`, `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
| 5. Revalidate | veto clear, window open, **authorizer asked again** still allows, with a decision that has not expired | aborted: `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
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

## Tests and mutations

`tests/gate/test_execution_gate.py` has 38 tests covering every row above, replay across a ledger
reopen, concurrent execution of one proposal in one gate and across two gates sharing a ledger,
reservation release after an abort, the one-receipt-per-call invariant, ledger failure, and the
two commit-boundary characterization tests. `tools/check_verifier_mutations.py` disables the pre-commit live
check, pre-commit re-authorization, checkpoint re-authorization, the EVALUATING-is-veto rule, and
the replay guard. Each is caught by a named test.

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
- The veto source is the software twin. Wiring it to a real latch is outside this repository.
- Windows use an injected integer clock. Clock trust is the deployer's problem.
