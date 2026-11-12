# WEAVER-V008, request deadlines: bounding head-of-line blocking

Status: research prototype, stacked on the crash-recovery slice (#128). V008 HOLD and the W0 / E2 /
O0 classifications are unchanged. This is an availability fix. Authorization, commit and receipt
semantics do not change.

## The problem

The owner serves one request at a time, and that stays deliberately. Before this change each
connection had a *per-read* timeout of 5 s:
- A listed peer that sent nothing held the owner for 5 s.
- A listed peer that sent one byte every 0.2 s never tripped a per-read timeout, so it held the owner
  indefinitely. It needed no write authority to do so.

Measured with the same script on both sides of the change (a trickling listed peer is connected,
then a legitimate request is sent with a 10 s client timeout):

| Code | Legitimate request |
|---|---|
| unchanged (`87c54f9`) | waited its whole 10.1 s timeout and got `OutcomeUnknown` |
| with deadlines | `COMMITTED` after 5.0 s, the default request deadline |

## What changed

| Control | Where | Default |
|---|---|---|
| **Absolute request deadline.** One complete request must arrive within `request_deadline_s` of the owner starting to read it, however its bytes are paced. It is a `time.monotonic()` deadline, so progress never extends it. | `recv_frame(deadline=...)`, `OwnerService.handle` | 5 s |
| **Size cap from the header.** A declared length above 64 KiB is refused on reading the 4-byte header, and none of the body is read. The cap already existed; the service level is now tested. | `recv_frame` | 64 KiB |
| **Reply deadline.** A reply the peer has not taken within `reply_deadline_s` is abandoned. The bound is on the whole send, not each chunk. | `send_frame(deadline=...)`, `OwnerService._reply` | 5 s |
| **Configuration.** `request_deadline_s` and `reply_deadline_s` are optional fields in the owner-private config: a number of seconds in (0, 300]. Anything else (0, negative, a boolean, a string) refuses to start. | `owner_main` | |

A peer cut off at the request deadline gets `{"ok": false, "error": "request-deadline-exceeded"}`
(best effort), then the connection closes. An oversized or malformed request gets `bad-frame`.

Unchanged on purpose: one request at a time, no worker pool, no asynchronous concurrency.

## The boundary: deadlines bound input, never execution

- The request deadline applies only while a request is being received. Once a request is complete,
  it executes to the end. The tests hold the SQLite write lock so that the commit happens *after* the
  request deadline has passed. The result is `COMMITTED`, with exactly one commit.
- A timeout is never evidence that a submitted operation did not commit:
  - In that same test, the requester's own 0.5 s timeout expires first. It gets `OutcomeUnknown`,
    then finds `COMMITTED` through `outcome`.
  - An abandoned reply looks to the requester like any lost reply (`OutcomeUnknown`), never like a
    refusal.
- A request cut off while still arriving was never complete, so it was never executed. It leaves no
  effect and no receipt; its outcome is `UNKNOWN`, and resubmitting it is safe.

## Tests

**Cross-uid** (`tests/isolation/test_v008_request_deadlines.py`, root): each peer is a real process
under the listed uid 61002, and the config sets a 1 s deadline.

| Case | Expected |
|---|---|
| Idle peer | Cut at about 1 s with `request-deadline-exceeded`. A legitimate request commits within the deadline plus start-up allowance. |
| Trickling peer (1 byte every 0.2 s) | Cut at about 1 s. A legitimate request commits. |
| Oversized header (16 MiB announced, none sent) | `bad-frame` in under half the deadline. Service continues. |
| Peer hangs up halfway through the header | Service continues. |
| Execution past the deadline (held write lock) | `COMMITTED`. The requester's own timeout gives `OutcomeUnknown`. Exactly one commit. |
| Deadline of 0, `true` or 301 in the config | The owner refuses to start. |

**Unprivileged** (`tests/test_owner_deadlines.py`, any user, every CI job):
- An idle sender and a trickling sender both hit the deadline.
- A complete frame inside the deadline is returned.
- An oversized header is refused without the body being read.
- Without a deadline, the old per-read timeout still applies.
- `send_frame`, and the service itself, give up on a peer that never reads at the reply deadline.
- Nonsensical deadline values are refused.

**Control removals** (`tools/check_v008_mutations.py`): five new `v008d-*` mutations:
- the receive deadline not applied;
- the send deadline not applied;
- the service ignoring the request deadline;
- the service ignoring the reply deadline;
- the header size cap removed.

All 31 V008 mutations are detected. (Detection counts are recorded on the pull request against the
exact commit.)

## Remaining limitations

- **Bounded per connection, not per peer.** A listed peer can still delay others by up to (its
  connections queued ahead of them) × the request deadline. It can also fill the listen backlog of
  8, so new connections are refused (`OwnerUnavailable`). Per-peer connection limits and rate
  limiting are not implemented.
- **Fairness is accept order only (FIFO).**
- **Time waiting in the accept queue is not charged to the peer.** The request deadline starts when
  the owner begins reading a connection, not when the peer connected.
- **The deadline counts all elapsed time,** including time the owner process is stopped
  (SIGSTOP), because it is measured on the monotonic clock.
- **Evidence:** single host, same operator, local evidence plus the repository's own CI.
  W0 / E2 / O0 are unchanged.
