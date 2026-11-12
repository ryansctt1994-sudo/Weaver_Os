# WEAVER-V008: JSON nesting bound at the owner's edge

Status: research prototype, stacked on the telemetry-validation follow-up (#133). DO NOT
MERGE. V008 HOLD and E2 / W0 / O0 are unchanged. This is an **availability** fix: it changes
no decision, ledger fact, receipt, or outcome.

## The defect

The owner parses every request, every telemetry snapshot it loads at start-up, and its own
config with one strict JSON loader, `load_strict_json`. `json.loads` recurses once per nested
array or object, so a deeply nested payload makes it raise `RecursionError`. That is not a
`ValueError`, so the loader did not convert it, and the single-request owner's accept loop
did not catch it either: the owner process exited.

- **Reachable by any admitted requester, with one request.** A *listed* peer — one already
  past the uid allowlist — could send a single frame whose body is thousands of open brackets
  (well under the 64 KiB frame cap) and end the owner. A depth around 16,000 crashes every
  supported Python; on 3.10 a few thousand is enough.
- **Not what admission control addresses.** A listed peer is admitted by design, and this is
  one request, not a flood. Per-peer rate limiting would not prevent it.
- **The telemetry-file and config vectors share the loader.** A deeply nested
  `edge-telemetry.json` crashed start-up (only root or the owner uid can write that file); a
  deeply nested config did the same before the owner finished starting.
- **Scope.** Fail-closed: nothing commits, the ledger is untouched, no outcome is produced.
  The cost is availability. The defect was present in every V008 slice from #127 to #133.

## The fix

Two independent guards in the shared loader, in `owner_ipc.py`:

1. **A depth bound checked before parsing.** `MAX_JSON_DEPTH = 32`. `_reject_deep_nesting`
   scans the raw text iteratively — so the scan itself never recurses — counting `[` and `{`
   that open outside string literals, with backslash-escape handling so a structural
   character inside a string never counts. It raises the ordinary malformed-input error
   (`FrameError`) the moment a container opens past the bound. Real requests, configs and
   snapshots are only a few levels deep; 32 is far above anything legitimate and far below
   the parser's recursion limit.
2. **A `RecursionError` backstop.** If any payload still reached the parser and recursed,
   `load_strict_json` now converts `RecursionError` to the same `FrameError`, so it can never
   escape as an unexpected internal error.

The malformed-input error flows exactly where it already did: on the socket it becomes a
`bad-frame` reply and a `FRAME_REJECTED` edge-telemetry event; for the telemetry file it is
caught by the loader's corruption path and the file is set aside; for the config the owner
refuses to start with its ordinary message. No blanket exception handler was added, so a
genuinely unexpected internal error still stops the owner rather than being masked.

### Why the boundary is exact

`MAX_JSON_DEPTH = 32` means depth 32 is the deepest accepted; the 33rd open container is
refused as it opens. Depth is the count of simultaneously open arrays and objects, measured
on structure only — brackets and escaped quotes inside strings do not count.

## Tests

Cross-uid tests run as root with real peer processes
(`tests/isolation/test_v008_json_depth.py`); unit tests run as any user
(`tests/test_owner_ipc.py`, `tests/test_owner_telemetry.py`).

| Test | Required result | Where |
|---|---|---|
| Exact boundary | Depth 32 accepted when otherwise valid; depth 33 refused. Strings carrying brackets and an escaped quote sit inside the nesting and do not move the boundary. | unit |
| Escape handling | One object whose string value holds an escaped quote followed by 40 `[{` pairs loads as depth 1; handling that mistook `\"` for the string's end would read 80 open containers and refuse a valid, shallow request. | unit |
| Recursion backstop | An injected `RecursionError` on a shallow payload (which clears the depth scan) comes back as `FrameError`, never escapes. | unit |
| Deeply nested request | A listed peer's single ~16,000-deep frame gets a `bad-frame` reply, the owner keeps serving (a real grant then commits), and the refusal is counted once as `FRAME_REJECTED` under the peer's kernel uid. | cross-uid |
| Deeply nested config | The owner refuses to start with its ordinary message and exit code, not a traceback. | cross-uid |
| Deeply nested telemetry file | The file is set aside like any other unreadable file and counting restarts; start-up does not crash. | unit |

### Control removals (mutations)

Two mutations in `tools/check_v008_mutations.py`, kept **separate on purpose**. A single very
deep payload cannot tell the two guards apart, because either guard alone would refuse it:

- `v008n-depth-scan-removed` is caught by the depth-33 boundary test. Depth 33 is shallow
  enough that the parser never recurses, so only the scan can refuse it.
- `v008n-recursion-backstop-removed` is caught by the injected-`RecursionError` test on a
  shallow payload, which the depth scan admits regardless.

Each removal fails only its own test; neither masks the other.

## What this does not do

- **No change to what nests legitimately.** Nothing in V008's own messages approaches depth
  32; if a future message type needed more, the bound — not the message — would move.
- **Not independent validation.** Same operator, one host, plus the repository's own CI.
- **Availability only.** It prevents one denial-of-service path. It makes no authority,
  durability, or production-readiness claim, and V008 stays on HOLD.
