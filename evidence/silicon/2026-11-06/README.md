# Silicon and external-anchor candidate evidence — 2026-11-06

**Hardware E3.1 NOT_READY; production authority not earned.**

Observed: Chronicle 15/15, original latch RTL 8/8, board wrapper 12 checks, full
500000-cycle press/release debounce simulation, and Yosys xc7 technology mapping
with structural checks passing. Weaver's final local suite passed 178 tests,
including eight fresh processes admitting one nonce exactly once. The actual
evidence gate exits 2 because physical/independent authority is unconfigured.

- `STATUS.json`: observed/missing evidence and source baselines.
- `candidate-bundle.zip` / `.sha256`: original source, mapped netlists and raw logs,
  candidate Chronicle, checkpoint, public keys, signed transparency proof, and
  author execution receipt. Extract into a NEW directory.
- `checkpoint.json`, `rekor-entry.json`, `rekor-public-key.pem`: offline proof inputs.
- `anchor-verification.json`: observed signature/Merkle/checkpoint verification.
- `rekor-readback*.json`: later public API readback and verification.
- `interlock-gate.json` / `.exit`: actual NOT_READY result, never replaced with PASS.
- `weaver-final-role-tests.log`: final 178-test run; earlier logs retained separately.

Checkpoint SHA-256:
`cfbc72137d476a7c89817ba5e12f0104aa3e3b5be35079f8be295743a83fbd78`.
Public log index **3719860200**:
https://rekor.sigstore.dev/api/v1/log/entries/108e9186e8c5677a94273e14be960ad44a21d0a146c2013b824b6e4209bcd8a87d1f7c08e56c03d3

The anchor freezes the candidate's artifact hashes; it does not attest hardware
truth. Signatures, inclusion proof and signed checkpoint verified against the
pinned Rekor key, cross-checked with official Sigstore trusted-root metadata over
HTTPS. Full TUF-chain validation, log gossip/consistency monitoring and witness
quorum were not performed.

No board was accessible, no Vivado implementation/bitstream/flash occurred, no
physical debounce/metastability/irreversibility result was measured, and no outside
operator has reproduced this package. The author/machine/principal are the same
for all local checks. An Arty SRAM configuration can clear on power loss or JTAG
reconfiguration; only a bounded software-input irreversibility claim is exercised.

The later [physical packet status](physical-packet-status.json) records the revised
startup-reset RTL and outside reproduction requirements. The old bundle and Rekor
entry remain unchanged historical evidence for the prior source. Neither the
revised hardware nor a physical run is qualified by that old entry. See the
[updated integration limits](../../../docs/SILICON_E3_1_GATE.md#2026-11-06-physical-packet-and-stronger-evidence-requirements).
