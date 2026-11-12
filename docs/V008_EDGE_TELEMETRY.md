# WEAVER-V008: service-edge security telemetry

Status: research prototype, stacked on the request-deadline slice (#129). DO NOT MERGE. V008
HOLD and W0 / E2 / O0 are unchanged. This is **operational security telemetry, not a receipt**.
It has none of the durability or integrity properties a receipt implies, and writing a refusal
to a file does not strengthen any evidentiary claim.

## What it is, and what it is not

The owner turns some requests away at its edge, before they reach the gate: an unlisted peer,
a bad frame, a malformed request, a peer claiming an actor it may not speak for, or a request
that missed its deadline. Until now those left no trace at all. This slice keeps a private,
bounded record of them for the operator.

It is deliberately separate from everything authoritative:
- **The ledger:** not part of the hash-chained ledger, and not covered by the anchor.
- **Decisions:** never read on the way to a decision. Requests are refused exactly as before.
- **Requesters:** no socket operation reads it, and the file is mode 0600 in the owner's 0700
  directory.
- **Outcomes:** not part of the outcome protocol. The gate's own refusal receipts and
  `COMMITTED` / `REFUSED` / `UNKNOWN` / `CONFLICT` are unchanged.

The first rule is the most important. Edge events are filed by **who connected** (the
kernel-reported uid and pid), never by what they claimed. If a peer's request claiming another
actor's proposal id were filed under that id, the victim's outcome would show an impostor's
refusal. So nothing the client sent is recorded: no proposal ids, actor ids or field values.

## Event classes

A namespace of its own, separate from the gate's `REFUSED` outcome:

| Event class | Meaning |
|---|---|
| `PEER_DENIED` | The kernel-authenticated peer uid has no service permission. The connection is closed without reading a byte. |
| `FRAME_REJECTED` | Transport or framing violation: oversized, malformed, or cut short |
| `REQUEST_REJECTED` | A parsed request that breaks the service contract (`bad-request`) |
| `ACTOR_DENIED` | The claimed actor is not one the authenticated peer may speak for |
| `DEADLINE_EXCEEDED` | The request did not arrive before the request deadline |

Each recent record holds exactly: class, kernel uid, kernel pid, the owner's sequence number,
and the owner's wall-clock second.

## Ordering: decide, respond or close, then record

Every edge path runs `DECIDE REFUSAL -> RESPOND OR CLOSE -> BEST-EFFORT TELEMETRY`.

- **Recording is in memory**: a constant-time update under a lock. A background writer thread
  persists a snapshot, coalescing a burst into at most one write per 0.5 s, and once more on
  shutdown. Disk I/O is never on the request path, so a slow or hung file system cannot hold
  the single-request owner.
- **Shutdown is bounded:** the final flush waits at most 2 s. If a write is hung, shutdown
  reports `shutdown_flush=timed-out` and the owner exits anyway.
- **Failures change nothing:** if the recorder raises, the error is counted (`record_errors`)
  and the owner carries on.
- **Possible loss:** a crash between responding and recording, or between recording and the
  next write, loses those events. That is acceptable for non-authoritative telemetry.

## Counter contract

- **Normal operation:** counts are exact for every event recorded, up to `max_count`
  (2^53 − 1, the largest integer every JSON reader keeps exactly). A counter that reaches it
  stays there and is listed in `saturated`. The sequence number saturates the same way.
- **Reserved uids:** the owner's configured service principals (the listed peers) always have
  dedicated counters. They never compete for a slot, so no number of unlisted uids can displace
  their attribution.
- **Unlisted uids:** the first 64 distinct unlisted uids get their own counters. Every later
  one counts in the `other` bucket, permanently. Nothing is evicted while running, so no count
  moves, and `other` is never presented as a per-uid history.
- **Restart (carry-over):** counters carry over only from the last completed write
  (`carried_over`). Any uid that is no longer reserved and no longer inside the retained slots
  (the config changed, or the cap was lowered) is **folded into `other` exactly once**. The sums
  per event class and `events_observed` do not change; a sum above `max_count` saturates and is
  marked `other|<class>`. `folded_uids` reports how many were folded. The folded state is what
  the next write persists, so a second restart has nothing left to fold. A uid that was retained
  and is now reserved simply keeps its counters.
- **Degradation is visible, and never claimed as durable evidence.** The in-memory `degraded`
  list names every kind of persistence failure this process has seen:

  | Reason | Meaning |
  |---|---|
  | `persist-failed` | A snapshot could not be written. Nothing was replaced. |
  | `dir-fsync-failed` | A snapshot was renamed into place, but syncing the directory failed. Its contents are visible, but whether the rename survives a crash is unknown, so this is never reported as durable success (`last_persist=unsynced`). |
  | `shutdown-flush-timed-out` | The final write did not finish in time. |

  A failed write leaves nothing on disk, so it cannot record that it failed. The flag is kept in
  memory, shown on the operator's shutdown line, and written by the **next successful**
  snapshot. A file that lacks the flag is therefore not evidence that no failure occurred.
- **Crash:** the ring of recent records starts empty after a restart, and events after the last
  completed write may be lost.
- **Fixed ceilings:** at most 1,025 counter rows of 5 counters and 256 recent records. A snapshot
  is a few tens of KiB and never more than 1 MiB.

Operator line at shutdown:
`edge telemetry: events_observed=… persist_failures=… last_persist=ok|failed|unsynced|none shutdown_flush=ok|timed-out degraded=<reasons>|none record_errors=…`

## Filesystem safety

- **One trusted acquisition, then descriptor-relative.** The recorder walks the directory path
  once with the trusted-path check (no symlink, no ancestor that anyone but root or the owner can
  write), opens it with `O_DIRECTORY | O_NOFOLLOW`, then checks the **descriptor** with `fstat`:
  a directory, owned by the owner, mode 0700, with the same device and inode the walk saw. After
  that, every open, rename, unlink and sync is relative to that descriptor. Replacing the path
  afterwards, even renaming the directory away and putting another in its place, cannot redirect a
  write. A parent that is not private, or is reached through a symlink, refuses to start.
- **The file.** `edge-telemetry.json`, mode 0600. An existing file is opened `O_NOFOLLOW` and
  `O_NONBLOCK` and judged on the opened descriptor: it must be a regular file owned by the owner,
  with no group or other access and one link. A symlink, FIFO, foreign-owned or loosely-moded file
  refuses to start (only root or the owner uid could have put it there). A FIFO is refused without
  blocking.
- **Writes.** Each write goes to `edge-telemetry.json.tmp`, opened `O_CREAT | O_EXCL | O_NOFOLLOW`,
  fsynced, then atomically renamed, and then the directory is fsynced. A planted link at the temp
  name is never followed. A leftover temp file that is a private regular file is removed at start;
  anything else refuses to start.
- **Corruption.** A safe file that is unreadable, malformed or not this schema is moved to
  `edge-telemetry.json.corrupt` and counting restarts (`corrupt_recovered`). Only one `.corrupt`
  file is kept.
- **A stuck writer.** If shutdown times out on a hung write, the directory descriptor is not
  closed, so a resumed write can never land on a reused descriptor number. The process is exiting.

## Acceptance tests

Cross-uid tests are in `tests/isolation/test_v008_edge_telemetry.py` and run as root with
real processes. Unit tests are in `tests/test_owner_telemetry.py` and run as any user.

| Test | Required result | Where |
|---|---|---|
| E01 telemetry write fails | Every write fails: refusals stay enforced, a legitimate request commits, no protected effect, failures reported, no file written. A write that hangs: the owner keeps serving (checked with short client timeouts, so a stuck owner fails in seconds), and shutdown is bounded and reported as degraded. A recorder that raises: the owner keeps serving. The first write fails once: no file exists afterwards, and the next successful snapshot carries `degraded: [persist-failed]`. A directory sync that fails: `last_persist=unsynced`, `degraded=dir-fsync-failed`, contents present, durability not claimed. | cross-uid, unit |
| E02 actor impersonation | A peer with a valid grant claiming another actor's committed id gets `actor-not-permitted` five times. The victim's outcome and ledger facts are unchanged, and neither the id nor the payload appears in telemetry. | cross-uid |
| E03 10,000 hostile events | 4,000 `PEER_DENIED`, 3,000 `FRAME_REJECTED` and 3,000 `REQUEST_REJECTED`, counted exactly. 256 recent records; the file stays under 64 KiB. | cross-uid |
| E04 peer attribution | Each record carries the attacking process's real uid and pid, whatever the request claims. | cross-uid |
| E05 malicious metadata | Newlines, quotes, path traversal, Unicode separators, a 60 KB field and 16 MiB headers: none of it is recorded. The file stays valid and bounded, no new files appear, and nothing appears at the traversal target. | cross-uid |
| E06 unauthorized lookup | `telemetry` and `stats` ops are `bad-request`. An outcome is identical before and after 500 hostile events. Requester uids cannot read the file. | cross-uid |
| E07 interruption and damage | After SIGKILL: no torn file, only the unflushed tail is lost. Exact again after a clean stop. A corrupt file is set aside. A symlink or foreign-owned file refuses to start. | cross-uid |
| E08 counter limits | 70 real, distinct unlisted uids (62000–62069) each connect once. Listed principals still have exact dedicated counters (5 and 4). 64 unlisted uids are retained, the other 6 are counted in `other`, and the 70 sum exactly. Unit: reserved uids under overflow; fold on restart preserves totals and does not fold twice; a retained uid that becomes reserved keeps its counts; a fold that overflows saturates and says so; the 1,000-uid bound. | cross-uid, unit |
| E09 control removals | 17 `v008t-*` mutations, each caught by its named test. | `tools/check_v008_mutations.py` |
| E10 full regression | Every existing suite stays green. | all |
| Filesystem | A loose or symlinked parent refuses to start. A parent directory swapped after start cannot redirect writes. A planted FIFO, symlink or hard-linked file is refused. A planted temp symlink is never followed. | unit |

Unit tests also make the ordering observable: a recorder that takes a full second does not delay
the reply, or the close of an unlisted peer's connection.

## What this does not do

- **No tamper evidence.** Records are not hash-chained or anchored. Root or the owner uid can
  edit or delete the file, and nothing would show it.
- **No rate limiting or per-peer admission control.** Telemetry observes hostile traffic; it
  does not slow it.
- **Unlisted uids can still crowd each other.** An attacker who can act from many uids can fill
  the 64 unlisted slots first-come, so later unlisted uids count only in `other`. Listed
  principals are not affected.
- **Ancestors rely on the trusted-path walk.** Descriptor-relative operations protect everything
  after the directory is acquired. Acquiring it relies on no ancestor being writable by anyone but
  root or the owner. The device-and-inode comparison between the walk and the open is defence in
  depth, and no test can drive that window deterministically.
- **Durability is not proven.** `fsync` of the file and of the directory is requested and its
  failure is reported, but power loss, a disk that acknowledges writes it has not made durable,
  and a full disk are untested.
- **Not recorded:** the internal `ledger-inconsistent` reply, which is an integrity alarm, not an
  edge refusal.
- **Pids can be reused** by the kernel, and the timestamp is the owner's wall clock to the second.
- **Evidence:** same operator, one host, plus the repository's own CI. Not independently
  reproduced.
