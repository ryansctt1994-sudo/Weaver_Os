# Silicon reproduction packet v1 — 2026-11-06

**E3.1: NOT_READY. No physical measurements, video, timing receipts, or outside
reproductions exist in this packet.** The JSON/CSV files are unfilled collection
forms, not observed receipts. The witness roster is unconfigured. This is a dated
addition to the original eight-step acceptance procedure, not a replacement of
its history or of the separate S5 protocol.

## What a new operator needs

- An Arty A7-35T, recorded board revision/serial, and Vivado supporting exact part
  `xc7a35ticsg324-1L`; record installer/version/license and executable provenance.
- An isolated harmless load-enable indicator, external default-OFF pull-down and
  suitable driver, common ground, a 3.3 V-compatible stimulus generator, and the
  [exact pinout](../README.md#exact-candidate-pinout). No production actuator.
- A calibrated oscilloscope/logic analyzer with raw export, sufficient bandwidth
  and sample rate for the declared minimum pulse, a continuous video camera, and
  a timing witness who controls their own capture equipment, clock and key.
- A separately controlled clean-room operator, plus the public roster and custody
  disclosures described in [PUBLIC_WITNESS_POLICY.md](PUBLIC_WITNESS_POLICY.md).
  Distinct local keys, accounts, agents or cloud VMs are not independent ownership.

The adapter/stimulus implementation and physical wiring depend on the actual
instruments. Their model, scripts, connections, voltage levels and failure modes
must be documented and hashed before the run. This generic packet is not a claim
that a board-specific fixture has already been commissioned without questions.
Missing equipment/adapter details remain NOT_READY, never invented defaults.

## Obtain and check the exact packet

```sh
git clone --single-branch --branch hardware/arty-a7-e31-candidate-20261106 https://github.com/ryansctt1994-sudo/cathedral-verified.git
cd cathedral-verified
git rev-parse HEAD
git status --porcelain
sha256sum -c hardware/lucifer_latch/arty_a7/qualification/packet.sha256
```

Compare the commit and checksum-list digest with the immutable published packet
link and independent witness's copy before proceeding. A mutable branch name is
not a source pin. The checksum list pins procedure, forms and relevant RTL/build
inputs; it does not prove that their contents are correct. Work from a clean,
detached checkout of that recorded commit. Do not copy the author's build outputs
and describe that as an independent build.

Install Python 3.10+, Icarus Verilog 12.0, Yosys/ABC and run `make test test-board`.
The startup regression must pass in addition to original core, board and full
500000-cycle debounce tests. Build and review the Vivado reports using
[the existing build/program commands](../README.md#vivado-and-board-work-still-required).
Freeze tool versions, seeds/options, constraints and all reports. Every operator
must identify their own generated bitstream: tool metadata can change binary
hashes, and an independent build need not be byte-identical. A difference requires
review and binding of both digests, not pretending the digests match. The current
Weaver role format accepts only one bitstream digest and cannot by itself express
this broader reproduction record.

`program.tcl` loads **volatile configuration**. It does not write SPI flash. A
persistent boot image requires the confirmed board revision, actual flash part,
reviewed flash procedure and power-cycle verification. No supplied command
programs OTP/eFUSE. Boot-image persistence does not preserve the tripped state.

## Run, return, and adjudicate

1. Read [PHYSICAL_RUN_PROTOCOL.md](PHYSICAL_RUN_PROTOCOL.md) and
   [SRAM_AND_PERMANENCE.md](SRAM_AND_PERMANENCE.md). Agree the bounded claim.
2. Fill and publish the preflight manifest and external roster; freeze their hashes
   before observations. Create a new build Chronicle checkpoint containing the
   actual vendor bitstream, source, protocol, roster and fixture hashes.
3. Have the external timing witness issue a fresh signed challenge; execute the
   positive control and all declared cases. Keep failures and missing coverage.
4. Publish original traces/video, measurement CSV, machine-readable run manifest,
   signed timing and reproduction receipts, hashes and public inclusion proofs.
   A summary or edited video alone is insufficient.
5. Outside operators independently rebuild, program, instrument and reproduce;
   the public witnesses apply the fixed policy. Until then E3.1 stays NOT_READY.

The template files deliberately contain nulls, `UNATTEMPTED` and `NOT_READY`.
Never replace missing measurements with zero. Signers generate and hold their own
keys; this packet neither supplies private keys nor signs for them. No outsider
has been recruited or claimed to have accepted this procedure.

## Retained preflight finding and anchor scope

At source `49fc0fdd61b2c8f5487b0aeebe38b219bdf512f3`, a new simulation found
`run_permit` high at startup before the initial reset level was qualified, including
when the physical reset input was held high. The same regression fails on that
source. This revision adds explicit initial stable-level qualification; its
simulation/mapping evidence is stored under
`evidence/silicon/2026-11-06/startup-amendment/`. This is a digital finding/fix,
not a physical observation. The changed startup behavior must be measured.

The earlier Rekor checkpoint at index 3719860200 remains an accurate immutable
record of the **earlier candidate**. It does not authenticate this revised RTL,
a future bitstream, these new documents, or physical results. Obtain a new public
anchor for the actual build before physical qualification. Do not overwrite the
old checkpoint or transplant its successful inclusion result onto new bytes.
