# WEAVER-V008, crash-recovery slice: outcomes across the process boundary

Status: research prototype, stacked on the V008 first slice. V008 HOLD and the W0 / E2 / O0
classifications are unchanged. This slice adds local crash-recovery evidence for one host. It
is not independent validation and authorises nothing.

Weaver_Os is a Linux execution substrate with a protected-effect broker. It is not an
operating system, and this slice does not integrate it with zorel-kernel or Delta-717.

## The gap this closes

PR #125 made the effect and its receipt commit in one SQLite transaction inside one process,
and showed three things in-process:
- **V009:** a duplicate proposal id commits once.
- **V010:** concurrent identical submissions commit once.
- **V012:** after a hard exit between commit and acknowledgement, the effect stays and a
  retry is refused.

The first V008 slice moved the owner into its own process. That opened a new question: *the
requester lost its connection after sending a write. Did it commit?* A missing reply is not
evidence either way.

## What was added

No module from PR #125 changed. The protocol is built from what the gate already records:
- every attempt writes exactly one receipt;
- commit and refusal events embed the canonical proposal;
- a commit claims `EXECUTION_COMMITTED:<proposal_id>` as a unique key inside the commit
  transaction.

| File | Change |
|---|---|
| `owner_outcome.py` (new) | `lookup_outcome(snapshot, proposal_id)`: read-only answer from durable history |
| `owner_service.py` | `outcome` op; every `submit` reply also carries the proposal's `outcome`; `CONFLICT` check |
| `owner_ipc.py` | client errors `OwnerUnavailable` and `OutcomeUnknown`; `outcome()` with a client-side `CONFLICT` check |
| `owner_main.py` | launcher-armed failpoints that kill the owner with SIGKILL |

### Outcome statuses

| Status | Meaning | Final? |
|---|---|---|
| `COMMITTED` | A commit is durably recorded. `receipt` is that commit's receipt, the same on every retry and after every restart. | Yes |
| `REFUSED` | Every recorded attempt was refused and nothing committed. `receipt` is the latest refusal. | **No**: refusals claim no unique key, so a later attempt (for example with a fresh grant) may still commit. |
| `UNKNOWN` | No durable record. The owner never received it, or died before the commit transaction completed. | No |
| `CONFLICT` | The id can never commit for this caller. Either the caller's own actor committed it with different content, or one of the caller's own attempts was refused with `ALREADY_COMMITTED` (the gate gives that reason only after authorization passed). No receipt is returned. | Yes |

A `submit` reply has two layers. `status`, `reason_code` and `receipt` describe that one
attempt. `outcome` describes the proposal as durable history records it after the attempt.
A retry of a committed proposal is still a refused *attempt* (V009 chronicles it), and its
`outcome` is `COMMITTED` with the original receipt.

**Visibility.** Every lookup is scoped to actors. The `outcome` op sees only records whose
proposal actor the asking peer may speak for. A `submit` reply sees only the submitting actor's
records. Other actors' commits, refusals, receipts and counts are never disclosed. Another
actor's activity under the same id can neither show up in your answer nor hide your own records.
The only cross-actor signal is `CONFLICT` after an *authorised* attempt finds the id taken, which
the gate in #125 already reveals through its `ALREADY_COMMITTED` reason. A probe without a valid
grant learns nothing. The one-commit-per-id integrity check still counts every actor.

### Proposal-id invariant (unchanged from #125)

> A proposal ID identifies one proposed execution globally, regardless of actor. Once
> committed, that ID cannot commit again under another actor.

This PR keeps that contract deliberately. Moving to actor-scoped ids would change replay
protection, how grants are interpreted, and existing commit semantics. That is too large a
semantic change for a crash-recovery slice.

Two situations are kept apart:

- **An unauthorised query or probe learns nothing.** This covers an `outcome` query, or a
  `submit` without a valid grant, for an id another actor used or committed. The caller sees only
  its own records: `UNKNOWN`, or `REFUSED` for its own refused attempts.
- **An authorised attempt that meets a committed id learns of the conflict.** This is a submit
  carrying a valid grant for that id. Under the existing contract this disclosure is legitimate:
  the gate refuses with `ALREADY_COMMITTED` only after authorization has passed, and the outcome
  is `CONFLICT`, final, with no receipt and no detail about the other actor.

### Requester protocol

```
submit(p, grant)
  reply received      -> read reply.outcome (COMMITTED / REFUSED / CONFLICT)
  OwnerUnavailable    -> nothing was delivered; retry when an owner is serving
  OutcomeUnknown      -> outcome(p):
                           COMMITTED          -> done; the receipt is the original one
                           CONFLICT           -> the id belongs to other content; stop
                           REFUSED / UNKNOWN  -> resubmitting p (same id, same content) is safe
```

Resubmitting the *same* proposal is always safe: the unique key allows at most one commit.
Never reuse an id for different content: that is reported as `CONFLICT` and never commits.
The client does not retry on its own; callers follow the protocol above.

## Fault injection: real process termination

| Fault | How | What the tests check afterwards |
|---|---|---|
| Owner dies inside the commit transaction | `WEAVER_OWNER_FAILPOINT=inside-commit-transaction`: SIGKILL after the effect row is written, before SQLite commits | Requester gets `OutcomeUnknown`. While down, a submit is `OwnerUnavailable`. After restart the outcome is `UNKNOWN` and the ledger shows 0 rows, 0 commit keys and 0 receipts. A retry commits once, the next retry returns that receipt, and history replays. |
| Owner dies after commit, before reply | `WEAVER_OWNER_FAILPOINT=after-commit-before-reply` | Requester gets `OutcomeUnknown`. After restart the outcome is `COMMITTED`. A retry is refused as an attempt but returns the same receipt, also after a second, clean restart. Exactly 1 commit key and 1 row, and history replays. |
| Requester dies after sending | requester SIGKILLs itself without reading the reply | Outcome is `COMMITTED`; a retry returns the same receipt; exactly 1 commit; the owner keeps serving. |
| Requester dies mid-frame | sends half a frame, then SIGKILL | Outcome is `UNKNOWN`; no rows or receipts; the owner keeps serving and the next submit commits. |
| Two requesters race | two processes submit the same proposal at once | Exactly one attempt commits; both replies carry the same receipt; exactly 1 commit. |
| True race between two owners | two owner processes on one store. A process holds the SQLite write lock until both owners are authorised and parked at `BEGIN IMMEDIATE`, then releases it. | One commits. The other is `ABORTED` with `ALREADY_COMMITTED`, stopped by the ledger's unique key inside the transaction after its effect was written and rolled back, not by any in-memory check. Both replies carry the same receipt; exactly 1 commit. |
| `UNKNOWN` while the original is still queued | owner A is frozen with SIGSTOP holding the original request; owner B on the same store answers | The requester's original gets `OutcomeUnknown`. B reports `UNKNOWN`, which is true of durable history at that moment. A retry through B commits. After SIGCONT, A executes the queued original: refused, no second effect, and A then reports B's receipt. 1 commit, 1 refusal, 1 row. |
| Clean restart | SIGTERM, then restart | The outcome receipt is identical and history replays against the earlier anchor. |

Unknown failpoint names refuse to start. A failpoint also cannot be armed unless the
owner-private config contains `"test_failpoints": true`; without it, the environment variable
makes the owner refuse to start. All of these run under the V008 harness: owner uid 61001,
listed requesters 61002 and 61004, unlisted 61003. The uid isolation and socket authentication
tests run unchanged alongside them.

The mutation runner (`tools/check_v008_mutations.py`) now removes 26 controls, 11 of them from
this slice, and all 26 are detected. Examples of the new ones:
- the outcome lookup ignoring commits;
- a lost reply reported as a refusal;
- an unreachable owner reported as unknown;
- the actor scoping removed;
- the authorised-conflict signal ignored;
- the failpoint opt-in skipped;
- the ledger's unique-key claim removed. Here both racers commit, and the outcome integrity check
  then refuses to answer (`ledger-inconsistent`).

## Review findings addressed after the first revision (`0675f87`)

1. **Outcome-query authorization: a defect, now fixed.** The first revision matched records
   by proposal id across all actors, and checked only the actor of the latest refusal. Three
   effects, none present in #125's gate:
   - A peer with no grant could learn that another actor had committed an id: its submit reply
     said `CONFLICT`.
   - A `REFUSED` outcome counted other actors' refused attempts.
   - Another actor's newer refusal under the same id made the rightful owner's own query fail
     with `actor-not-permitted`.

   Lookups are now scoped to actors (see *Visibility*). Four acceptance tests written for the
   correct behaviour failed against `0675f87` and pass now.
2. **Retry safety under concurrency.** Shown directly by the true-race and queued-original tests
   above. When both attempts execute, the ledger's unique key is what allows only one commit,
   including when every in-memory check has already passed.
3. **Failpoint containment.** Arming now also requires a config opt-in (see the last limitation).

## Remaining limitations

- **Crash model.** Single host, `SIGKILL` of a process only. Not tested: power loss, kernel or
  VM crash, disks that acknowledge writes they have not made durable, full disks, or a
  corrupted WAL. Durability across power loss rests on SQLite's `synchronous=FULL`, untested.
- **Fault points.** Two owner points and two requester points. Crashes elsewhere (during a WAL
  checkpoint, during startup recovery, between accept and read) are not covered.
- **`UNKNOWN` is not proof of absence.** It means no durable record when the answer was
  computed. A request still queued in the socket backlog could commit afterwards. That is why
  the protocol says retry the same proposal rather than conclude failure.
- **`REFUSED` is not final**, by design (see above).
- **One owner, one request at a time.** Two owner processes on one store were exercised only in
  the two tests above (a true race and a queued original). A multi-owner deployment is not
  otherwise tested or claimed.
- **Head-of-line blocking (availability, not integrity): now bounded.** The owner serves one
  connection at a time. An absolute request deadline and a reply deadline now limit how long one
  connection can hold it, however its bytes are paced; see `docs/V008_REQUEST_DEADLINES.md`. A
  listed peer can still delay others by queueing several connections. No effect or receipt is
  affected either way.
- **Outcome lookup scans the whole ledger** on each call. Fine for a research prototype, not
  for scale.
- **Edge refusals still leave no receipt.** A request refused for its peer uid, actor id or a
  bad frame never reaches the gate. Its outcome stays `UNKNOWN`, and a retry is refused again
  the same way. Recording these is the planned follow-on.
- **Proposal ids are one global namespace, by decision** (see *Proposal-id invariant*). Once one
  actor commits an id, no other actor can. Taking an id needs a valid issuer grant, so the issuer
  must not grant the same id to different actors for different executions. That is an issuer
  responsibility, not something the owner enforces.
- **Grant windows still apply.** A retry after the grant expires is refused as an attempt.
  `outcome` still reports a commit if one exists.
- **Failpoint code ships in the launcher.** Arming it needs both the launcher's environment
  variable and `"test_failpoints": true` in the owner-private config. A deployment config that
  leaves the field out cannot arm it: the variable alone makes the owner refuse to start. Enabled
  test failpoints are announced on stderr. The code is still present in the build; removing it
  from production builds entirely is not done.
- **Evidence.** The same operator wrote and ran these tests on one container (and the repo's own
  CI runs them). That is not an independent witness.
