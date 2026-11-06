# Gate discrimination and direct log check — 2026-11-06

**E3.1 remains NOT_READY; production authority remains unearned.**

## What the anchor establishes

Rekor commits to a digest and a signed log-integration time. An inclusion proof
plus matching file hashes supports existence of the committed content by that
log-reported time and detects changes relative to the commitment. The log does
not store or execute the RTL. Inclusion does not prove compilation, successful
tests, refusal behavior, physical execution, a running system, or the truth of
any statement inside the bundle. Changes to local files remain possible; the
pinned digest makes a mismatch detectable. The log clock, signing-key trust and
consistency assumptions remain part of the claim.

The unchanged prior checkpoint is
`b0439f7d0878dd8d888bd7fde2dc37baca645829d10e999609c79b38a3018332`,
Rekor index 3721019269. This addendum supplies verification records without editing
that checkpoint, its original ZIP, or the frozen reproduction packet. Runtime
changes in this follow-up are reviewable in Git; the earlier RTL anchor does not
silently cover new verifier code.

## Fetch the log's own signed checkpoint

`live-log/` contains raw responses fetched **directly from Rekor's HTTPS API** at
2026-11-06T23:12:50–51Z, independently of the bundled checkpoint copy. The service
public key matched the pinned DER key ID. The signed checkpoint was verified and
an RFC6962 consistency proof connected the bundled tree of size **3599115121** to
the independently fetched tree of size **3604353200**. The log had grown, so equality
of those roots would be the wrong requirement. Both reconstructed roots matched
their respective signed checkpoints. This checks this pair of observations;
it cannot exclude all split views or guarantee future availability.

The consistency endpoint also returned an unsigned `rootHash` convenience field
that differed from the requested signed checkpoint's root. That field is recorded
but never used for acceptance: the verifier reconstructs both roots from the
proof and compares the signed roots at the explicitly requested sizes.

From Weaver repository root, another operator can perform a fresh read-only check:

```sh
python -m triadic_controls.crypto.live_log \
  --manifest evidence/silicon/2026-11-06/revised-anchor/checkpoint.json \
  --entry evidence/silicon/2026-11-06/revised-anchor/rekor-entry.json \
  --checkpoint-sha256 b0439f7d0878dd8d888bd7fde2dc37baca645829d10e999609c79b38a3018332 \
  --output /absolute/path/to/NEW_AUDIT_DIRECTORY
```

The equivalent cathedral module is `chronicle.live_log`. Each invocation preserves
new raw responses and observation times. A healthy connection returns
`VERIFIED_LIVE_CHECKPOINT_CONNECTION`, exit 0. API, signature, proof or malformed
record failures return `INCONCLUSIVE`, `LIVE_LOG_CHECK_FAILED`, exit 2. An existing
output directory is refused to protect prior records. The executed check was by
the same principal as the author: an external data route is not an independent
human observer. Full TUF-chain verification remains unperformed.

## A gate that can admit and refuse

The gate now prints additive machine fields `decision`, `exit_code`, `reason_codes`
and `refusals` (code/stage/detail). The legacy `status` and human-readable
`missing_or_invalid` remain. `decision=READY` means that this role-receipt gate's
implemented predicates pass; its status remains `READY_FOR_E3_1_REVIEW`, exit 0.
It does not award E3.1. The output explicitly retains `silicon_E3_1=NOT_READY`,
`public_quorum_verified=false` and `production_authority_earned=false`.

`controls.json` records a **SYNTHETIC_GATE_CONTROL**, with a complete test trust
domain: real ECDSA author/log signatures, signed checkpoint, inclusion proof,
Chronicle, bitstream-shaped test bytes bound by digest, strict SQLite state, pinned
policy, and Ed25519 role receipts. The test substitutes only its isolated log-key
pin; no verification function is stubbed and no production pin override, fixture
CLI flag or production acceptance path is added. The control returns READY/exit 0.
The same synthetic root is rejected under the production pin. No synthetic key,
principal or asserted control is counted as an actual outside observer or board.

Paired negative controls remove one prerequisite or corrupt one authenticated
record. Missing policy, missing replay state, changed bitstream, invalid signature,
a re-signed false physical control and invalid anchor each produce NOT_READY/exit 2
with a specific code. This rejects both a constant-refusal implementation and a
constant-admission implementation. Reproduce all checks with:

```sh
python -m pytest -q tests/triadic_controls/test_interlock_discrimination.py tests/triadic_controls/test_live_log.py
```

The positive control demonstrates discrimination across **implemented admission
predicates**. A genuinely qualifying physical READY case is still unavailable:
no board, vendor build, independent measurements, real role receipts, outsider
reproduction or enrolled quorum exists. The existing gate still does not implement
the proposed public 2-of-3 quorum. No synthetic result fills those gaps.

`real-bundle-refusal.json` records the new code for the actual public source bundle:
`AUTHORITY_POLICY_MISSING`, NOT_READY, exit 2. Inclusion, Chronicle/artifacts and
existing local test replay state pass. This is a specific unmet prerequisite,
not a claim that the physical experiment ran and refused an attack.

## Refusal vocabulary v1

- `ANCHOR_INVALID`, `CHRONICLE_INVALID`, `REPLAY_STATE_UNAVAILABLE`
- `AUTHORITY_POLICY_MISSING`, `AUTHORITY_POLICY_UNREADABLE`,
  `AUTHORITY_POLICY_HASH_MISMATCH`, `AUTHORITY_POLICY_INVALID`, `POLICY_CANDIDATE_MISMATCH`
- `BITSTREAM_UNAVAILABLE`, `BITSTREAM_HASH_MISMATCH`, `BITSTREAM_NOT_ANCHORED`
- `PHYSICAL_RECEIPT_MISSING`, `PHYSICAL_RECEIPTS_INVALID`, `RECEIPT_SIGNATURE_INVALID`
- `RECEIPT_PRINCIPAL_CONFLICT`, `RECEIPT_CUSTODY_INVALID`, `RECEIPT_IDENTITY_MISMATCH`,
  `RECEIPT_CANDIDATE_MISMATCH`, `RECEIPT_CUSTODY_MISMATCH`, `RECEIPT_EXECUTION_UNOBSERVED`,
  `RECEIPT_BOARD_UNIDENTIFIED`, `RECEIPT_CONTROLS_INCOMPLETE`

The gate records the first failure within each verification stage; it does not
claim that later predicates in that stage ran. Stages can report additional
failures after an upstream failure, and those are not independent observations.
Human exception text is diagnostic detail, never the stable machine interface.
