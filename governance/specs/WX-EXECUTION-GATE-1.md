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
| 3. Reserve | proposal not already committed (checked against the ledger at startup) and not already running | `ALREADY_COMMITTED`, `ALREADY_RESERVED` |
| 4. Execute | the action stages a result; `context.checkpoint()` rechecks the veto, the window, and **authority** (authorizer asked again) | aborted: `EXECUTION_FAILED`, `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
| 5. Revalidate | veto clear, window open, **authorizer asked again** still allows, with a decision that has not expired | aborted: `VETO_DURING_EXECUTION`, `WINDOW_EXPIRED`, `REVALIDATION_DENIED` |
| 6. Commit | result recorded on the Authority Root (`EXECUTION_COMMITTED`) | aborted: `RESULT_NOT_RECORDABLE` |

**Every call produces exactly one receipt.** A commit goes on the Authority Root. Every refusal
and abort goes on the Rejection Root, with its stage and detail.

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

`tests/gate/test_execution_gate.py` has 33 tests covering every row above, replay across a ledger
reopen, concurrent execution of one proposal, reservation release after an abort, and the
one-receipt-per-call invariant. `tools/check_verifier_mutations.py` disables the pre-commit live
check, pre-commit re-authorization, checkpoint re-authorization, the EVALUATING-is-veto rule, and
the replay guard. Each is caught by a named test.

## Limits

- One gate per ledger. Reservations and the committed-proposal set are in-process, and a second gate
  process on the same ledger would not see the first one's live reservations. Committed proposals are
  reloaded from the ledger at startup.
- The veto source is the software twin. Wiring it to a real latch is outside this repository.
- Windows use an injected integer clock. Clock trust is the deployer's problem.
