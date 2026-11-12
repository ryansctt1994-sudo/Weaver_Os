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
| `CONFLICT` | The id committed, but for different proposal content. No receipt is returned: it is not this proposal's. | Yes |

A `submit` reply has two layers. `status`, `reason_code` and `receipt` describe that one
attempt. `outcome` describes the proposal as durable history records it after the attempt.
A retry of a committed proposal is still a refused *attempt* (V009 chronicles it), and its
`outcome` is `COMMITTED` with the original receipt.

A peer can query outcomes only for proposals whose actor it may speak for. Otherwise the reply
is `actor-not-permitted`.

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
| Clean restart | SIGTERM, then restart | The outcome receipt is identical and history replays against the earlier anchor. |

Unknown failpoint names refuse to start. All of these run under the V008 harness: owner uid
61001, listed requesters 61002 and 61004, unlisted 61003. The uid isolation and socket
authentication tests run unchanged alongside them.

The mutation runner (`tools/check_v008_mutations.py`) now removes 23 controls, 8 of them from
this slice, and all 23 are detected. Examples of the new ones: the outcome lookup ignoring
commits, a lost reply reported as a refusal, an unreachable owner reported as unknown, and the
conflict and actor checks removed.

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
- **One owner, one request at a time.** Concurrency was exercised across requester processes
  only. Several owner processes on one store are not tested in this topology.
- **Outcome lookup scans the whole ledger** on each call. Fine for a research prototype, not
  for scale.
- **Edge refusals still leave no receipt.** A request refused for its peer uid, actor id or a
  bad frame never reaches the gate. Its outcome stays `UNKNOWN`, and a retry is refused again
  the same way. Recording these is the planned follow-on.
- **Small disclosure side channel.** `actor-not-permitted` versus `UNKNOWN` reveals whether some
  other actor has used a proposal id.
- **Grant windows still apply.** A retry after the grant expires is refused as an attempt.
  `outcome` still reports a commit if one exists.
- **Failpoint code ships in the launcher.** Only the trusted launcher's environment arms it, and
  an armed failpoint is printed on stderr. A deployment must not set it.
- **Evidence.** The same operator wrote and ran these tests on one container (and the repo's own
  CI runs them). That is not an independent witness.
