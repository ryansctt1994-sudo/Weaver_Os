# Hardware-first receipted replay candidate

2026-11-06 status: **NOT_READY; E3.1 not earned; production authority not earned.**
The actual gate receipt reports verified public-log inclusion, anchored Chronicle
and artifact hashes, and existing persistent replay state. It exits 2 because the
external authority policy and physical/clean-room receipts are absent. No board
or Vivado host was accessible in the author workspace.

## What is wired

`triadic_controls.crypto.interlock_gate` provides an opt-in evidence gate and
`build_evidence_gated_verifier`. The factory requires a pinned authority policy,
external Chronicle inclusion proof, exact artifact bindings, a vendor bitstream
included in that anchor, and two role receipts before constructing the existing
`CryptoVerifier` with `SQLiteReplayCache(create=False)`. There is no memory-cache
fallback. Existing direct constructors remain pilot APIs; the factory is not a
claim that every application entrypoint or physical executor now uses it.

This is a deployment evidence gate. It cannot replace the physical circuit: the
external effect must pass through the FPGA's active-high default-OFF load enable.
Software validation of a receipt cannot stop an alternative physical effect path.
See the cathedral-verified board procedure and custody requirements before use.

The cache now closes connections deterministically, uses WAL/FULL synchronization,
and prunes/adopts a nonce inside one `BEGIN IMMEDIATE` transaction. Eight separately
spawned processes contended for one nonce; exactly one admitted. Retention cannot
be shortened by `record`, expired admissions and nonfinite clock inputs reject,
and runtime missing/zeroed state cannot silently become a new empty cache.
`create=True` remains an explicit initialization convenience for pilot code;
deployed paths must use the strict factory.

This proves atomic nonce consumption against the current SQLite database, not
exactly-once external effects, immunity to authentic snapshot rollback, protection
from caller-controlled clocks, or durable storage beyond the filesystem's guarantees.
SQLite and an external actuator do not share a transaction. A crash after nonce
consumption may burn an action without executing it; do not automatically replay it.

## Reproduce the current result

From a clean checkout with Python 3.10+:

```sh
python3 -m venv ../weaver-venv
../weaver-venv/bin/python -m pip install -e '.[dev]'
../weaver-venv/bin/python -m pytest -q
```

Verify `evidence/silicon/2026-11-06/candidate-bundle.sha256` with `sha256sum -c`
from that directory, then extract the ZIP into a new writable directory `BUNDLE`.
The archive contains an ordinary MIT source license and no signing private keys.
The recorded candidate digest is externally logged at
[Rekor index 3719860200](https://rekor.sigstore.dev/api/v1/log/entries/108e9186e8c5677a94273e14be960ad44a21d0a146c2013b824b6e4209bcd8a87d1f7c08e56c03d3).
The source verifier checks signatures/inclusion offline. It pins the log key in
code and rejects manifest, body, SET, Merkle-path and checkpoint mutations.

Create **local test state only**, then run the evidence gate:

```sh
../weaver-venv/bin/python -c "from triadic_controls.crypto.sqlite_replay import SQLiteReplayCache; SQLiteReplayCache('../candidate-replay.db')"
../weaver-venv/bin/python -m triadic_controls.crypto.interlock_gate --bundle BUNDLE --replay-db ../candidate-replay.db
```

Expected current result: `NOT_READY`, exit **2**, with external authority policy
unconfigured. Do not replace that exit with zero or fabricate missing receipts.
The complete public anchor and source binding can verify while qualification stays red.

## External authority and receipts

The actual authority policy must be supplied by the operator and pinned by SHA-256
outside the incoming request. No trusted witness is configured by this release.
It contains `author_principal`, `checkpoint_sha256`, `bitstream_sha256`, and
`authorities` entries for `hardware_operator` and `clean_room_reviewer`. Each entry
provides a separately controlled `principal`, 32-byte Ed25519 `public_key_hex`, and
`custody_receipt_sha256`. Policy changes require a separately visible review.
Do not name two agents under one principal as independent operators.

Each `independent-receipts/ROLE.json` is `{payload,signature}`. Signature is base64
Ed25519 over `WEAVER-SILICON-EVIDENCE-v1` + LF + canonical payload (sorted ASCII keys,
compact JSON). Payload binds role/principal, custody receipt hash, checkpoint and
bitstream digests, `status=OBSERVED_PASS`, `direct_execution=true`, model
`Arty A7-35T`, board serial and every control named in `REQUIRED_CONTROLS`.
Those controls include vendor timing/CDC review, measured debounce, observed
software/reset-bounce refusal to clear, physical effect-path wiring, readback
binding, and disclosure of reset/power/JTAG custody.

Signatures authenticate observations as statements by the pinned key owner.
Distinct principal strings and custody hashes do not prove independent ownership
or the statements' truth. External governance must establish that custody and
review the raw traces, run provenance, board identity and limitations. No participant
is asked to pretend to sign or compute a hash they cannot control or verify.

## Evidence ladder and remaining blockers

1. Local primitive checks and xc7 mapping: observed author evidence, below silicon.
2. Candidate Chronicle external log inclusion: observed, with signed proof.
3. Routed vendor bitstream, timing/CDC review and actual board programming: missing.
4. Physical pulse/debounce/irreversibility/effect-boundary traces: missing.
5. External key custody and separately controlled clean-room receipts: missing.
6. A complete immutable receipted replay package: eligible for **E3.1 review** only
   after those prerequisites, source hashes and reproducible instructions agree.

The gate's `READY_FOR_E3_1_REVIEW` is a review state, not automatic E3.1 promotion.
It always leaves `production_authority_earned=false`. The earlier audit package
and its pending receipts are not silently rewritten or promoted by this change.
The same author/machine ran these tests. Independent clean-room verification has
not occurred. The public log is external publication, not a witness quorum or
independent observation of hardware.


## 2026-11-06 physical packet and stronger evidence requirements

The published [physical reproduction packet at `0f3b0973`](https://github.com/ryansctt1994-sudo/cathedral-verified/tree/0f3b0973b95ecbadb49ca4f7d989ed1da8a2f6b9/hardware/lucifer_latch/arty_a7/qualification)
adds continuous video, independently controlled raw timing capture, observer
noninterference and unguarded-reference controls, nine physical coverage cases,
and unsigned collection templates. Its checksum-list SHA-256 is
`d668739d2db6c219a7bb6373807254f800434195f8a835ba38e67aba53bea8bd`.
The packet also documents SRAM volatility and separately assessed mechanisms
needed for persistent or permanent trip state. No such mechanism is implemented.

A new startup simulation exposed the earlier board wrapper permitting before its
initial reset input was qualified. The revised RTL requires initial stable-level
qualification, and the original failing trace plus passing revised tests/mapping
are public in that commit. **The earlier Rekor checkpoint still binds the earlier
candidate.** It is not an anchor for the changed RTL or future bitstreams. Any
hardware qualification must bind a new actual-build checkpoint and retain that
prior history; this repository's original bundle has not been replaced.

The packet proposes a public **2-of-3 outside-witness** policy. The three actual
principals, their own keys/custody disclosures and adjudicator must be enrolled and
published before qualifying runs. Both counted affirmative witnesses must directly
rebuild and reproduce on independently controlled benches; independent timing
receipts must accompany their raw evidence. No witnesses are enrolled and no
physical reproduction has occurred. A text-only reviewer or another agent under
the author's principal cannot substitute. The quorum is an attestation threshold,
not a claim of Byzantine fork immunity or guaranteed availability.

**Implementation boundary:** the existing `interlock_gate` checks two role receipts;
it does not verify the new public quorum, independent timing formats or all raw
physical evidence. Its `READY_FOR_E3_1_REVIEW` remains insufficient to satisfy this
stronger review policy. It cannot authorize promotion to E3.1 or production.
The new packet formats have no implemented quorum verifier in this change.
Also, the current two-role policy binds one bitstream digest, while independent
builds may legitimately differ: preserve and review each build's exact digest and
provenance rather than pretending they are identical. A future machine-enforced
cross-build/quorum policy needs a separately reviewed implementation.

E3.1 remains **NOT_READY** until outsiders reproduce the silicon evidence and the
public receipt set, custody, coverage, failure history and actual effect path are
verified. The software factory and receipt signatures alone cannot establish that.
No board access, flashing, video, physical measurements, outside receipt, witness
enrollment or production transition is recorded by this documentation update.
