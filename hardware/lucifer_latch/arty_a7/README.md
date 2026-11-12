> Weaver import: simulation candidate only. Historical packet checksums and commands
> below apply to the original source tree preserved in
> `research/consolidation/snapshots/arty-hardware.zip`, not the combined Weaver tree.
> Use `make test-hw-consolidation` for the host simulation gate.

# Arty A7-35T bench interlock candidate

**2026-11-06 follow-up:** the [physical reproduction packet](qualification/README.md)
defines continuous video, raw timing traces, independently signed observations and
a proposed public 2-of-3 outside-witness policy. No outside witness is enrolled.
It also documents [SRAM and permanent-irreversibility limits](qualification/SRAM_AND_PERMANENCE.md).
E3.1 remains **NOT_READY**.

The earlier wrapper permitted before initial reset qualification, including reset
held at boot. A retained failing simulation and new regression exposed that gap.
The revised debounce block explicitly qualifies the initial pin level before
`run_permit` can assert. Both held/released/bouncing startup and normal reset
press/release use the full 500000-cycle qualification. Later reset assertion still
has its qualification delay. This revision needs new physical measurements and
a new actual-build anchor; the historical Rekor entry below binds the earlier RTL.

Status on 2026-11-06: local RTL simulation and Xilinx 7-series technology mapping
completed. **No Arty was connected, no Vivado implementation was run, no bitstream
was produced or programmed, and no physical irreversibility/debounce/metastability
claim is earned.** The evidence ceiling remains below the requested hardware E3.1.

## Hardware boundary first

The new top-level has one asynchronous trigger, a physical reset button, two LEDs,
and an active-high `run_permit` output. There is no software clear or UART command
path. The original 68000-cycle deliberation floor is preserved: this is a roughly
680 microsecond delayed veto, not a fast emergency stop.

`trigger_async` uses two flip-flops marked `ASYNC_REG` and `SHREG_EXTRACT=NO`.
Guaranteed digital capture requires a pulse held for at least three clock periods.
The reset button crosses a separate two-flop synchronizer and must remain stable
for 500000 clock samples in both directions (5 ms at 100 MHz). Short press/release
bounces cannot clear/rearm the latch. This digital mitigation does not eliminate
metastability or establish a measured MTBF; placement, recovery/removal, CDC review,
and device-specific metastability assumptions remain necessary.

During power-on initialization and qualified reset, `run_permit` stays low.
Initialization now includes initial stable reset-level qualification, not just
the 32-cycle power-on register.
An external load-enable circuit must default OFF when the FPGA is absent, unpowered,
or configuring, using an independent pull-down and suitable external driver.
Do not attach a real actuator for this bench. Use a harmless canary/load-enable
indicator and measure the actual effect boundary, not just an FPGA LED.

**Irreversibility is bounded to a powered, configured FPGA with its reset path held
outside software control.** Arty's SRAM FPGA loses state on power cycling and can
be reprogrammed through JTAG. If the effect software also controls JTAG, board
power, or reset, it can clear the configuration without touching a physical button.
Disclose/isolate those paths before claiming a hardware interlock. Persistence
across power/reconfiguration requires a separately assessed physical latching
mechanism or protected nonvolatile authority; it is absent here.

The threat-level bus is tied to zero at this board wrapper. Independent per-bit
synchronizers cannot make a multi-bit asynchronous bus coherent. A future UART
or bus adapter needs a validated protocol/handshake; no UART is claimed working.

## Exact candidate pinout

Only Arty A7-35T is supported by the supplied constraint set. Do not infer 100T
compatibility or flash-part identity. Confirm model and board revision first.

| Port | Board pin | Bench use |
| --- | --- | --- |
| clk | E3 | 100 MHz oscillator |
| reset_button | D9 | BTN0, active high |
| trigger_async | G13 | Pmod JA1, 3.3 V input |
| run_permit | B11 | Pmod JA2, 3.3 V load-enable indicator |
| tripped_led | H5 | LED0 |
| ready_led | J5 | LED1 |

Pins were checked against Digilent's
[Arty-A7-35-Master.xdc](https://github.com/Digilent/digilent-xdc/blob/master/Arty-A7-35-Master.xdc).
Part `xc7a35ticsg324-1L` was checked against Digilent's
[board file](https://github.com/Digilent/vivado-boards/blob/master/new/board_files/arty-a7-35/E.0/1.1/board.xml).
Common ground and external default-OFF bias are required; FPGA pins are not load drivers.

## Reproduce local evidence

From repository root, install Python 3.10+, Icarus Verilog 12.0, and Yosys/ABC
(author run: Yosys 0.23, Debian binaries). Ordinary system installations work:

```sh
make test
make test-board
mkdir xc7-build
yosys -l xc7-build/synthesis.log -p 'read_verilog hardware/lucifer_latch/lucifer_latch.v hardware/lucifer_latch/arty_a7/sync_debounce.v hardware/lucifer_latch/arty_a7/lucifer_arty_a7.v; synth_xilinx -family xc7 -top lucifer_arty_a7; check -assert; stat; write_json xc7-build/netlist.json'
```

Observed: Chronicle 15/15; original latch 8/8; wrapper 12 checks with an 8-cycle
scaled debounce; a separate test uses the actual 500000-cycle press/release.
The simulator now returns nonzero on assertion failure and timeout. Yosys mapping
and structural checks passed, but do not establish routing or 100 MHz timing closure.
The author's initial synthesis attempt failed because ABC was missing from PATH;
its log is retained, and the rerun used the same RTL after correcting the tool path.

## Vivado and board work still required

From this directory on the operator's Vivado host:

```sh
vivado -mode batch -source build.tcl -tclargs xc7a35ticsg324-1L NEW_BUILD_DIRECTORY
```

The script preserves synth/routed checkpoints, utilization, min/max timing, CDC
and DRC reports. It refuses negative setup/hold slack, absent timing paths, or
error DRCs. It does **not** replace review of CDC findings, ignored constraints,
unconstrained endpoints, pulse-width requirements, or the provisional 2 ns output
budget. `ASYNC_REG` must survive implementation with appropriate physical placement.

Only after reports are reviewed and a harmless bench is isolated, select the exact
hardware serial and bind the generated `.bit` SHA-256 into the test receipt:

```sh
vivado -mode batch -source program.tcl -tclargs EXACT_TARGET_SERIAL /absolute/path/lucifer_arty_a7.bit
```

This script programs volatile FPGA configuration only. Nonvolatile SPI flashing
requires confirmed board revision, flash part, and a separately reviewed procedure;
none was performed here. Do not call a successful programming API a physical test.

## Physical acceptance procedure (freeze before the run)

Record source commit, bitstream digest, board model/revision/serial, Vivado version,
probe model/sample rate, wiring diagram, power/reset/JTAG custody and UTC times.
An operator with their own pinned signing key must collect raw traces and the
actual load-enable observation for all cases:

1. Power/configuration/reset hold the external load-enable OFF; verify the external
   pull-down with the FPGA unpowered and the programming cable removed.
2. Apply phase-varied triggers of declared pulse widths; measure trigger-to-veto
   latency including synchronization and the 68000-cycle floor.
3. After trip, repeatedly toggle every software-controlled signal and confirm the
   external load cannot re-enable. Keep power/reset/programming ownership explicit.
4. Inject measured short reset bounces; verify no trip clearing or transient permit.
5. Hold physical reset for the configured qualification time: the latch may clear,
   but load enable remains OFF until a qualified stable release.
6. Review post-route CDC placement and timing; exercise phase/width sweeps. Report
   observation counts and limits. A finite bench run cannot prove zero metastability.
7. Demonstrate power/reconfiguration behavior as a limitation. Do not relabel
   clearing across those paths as irreversible physical storage.
8. Have a separately controlled reviewer reproduce from instructions and return
   a signed receipt binding this exact checkpoint, bitstream and raw evidence.

Failing fixture/coverage/identity/custody prerequisites remain missing evidence.
Do not create an independent identity by generating another local key or agent.

## External Chronicle anchor

The **earlier candidate's** Chronicle checkpoint digest is
`cfbc72137d476a7c89817ba5e12f0104aa3e3b5be35079f8be295743a83fbd78`.
It is publicly included in Rekor at index **3719860200**:
[entry and signed proof](https://rekor.sigstore.dev/api/v1/log/entries/108e9186e8c5677a94273e14be960ad44a21d0a146c2013b824b6e4209bcd8a87d1f7c08e56c03d3).

The [public evidence bundle](https://github.com/ryansctt1994-sudo/cathedral-verified/tree/e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c/evidence/silicon/2026-11-06/) contains the
exact checkpoint, chain, source files, mapped netlists, logs, and proof. Extract
`candidate-bundle.zip` into a new directory, then from repository root run:

```sh
python3 -m pip install cryptography==50.0.0
python3 -m chronicle.external_anchor BUNDLE/checkpoint.json BUNDLE/rekor-entry.json BUNDLE/rekor-public-key.pem
```

The verifier checks the local author signature, pinned Rekor key, signed entry
timestamp, RFC6962 inclusion path, shard UUID and signed checkpoint. The key was
matched against official Sigstore GitHub trusted-root metadata over HTTPS; this
run did not perform full TUF-chain verification. Single-log inclusion proves
publication of the digest, not event truth, hardware behavior, future consistency,
fork immunity, a witness quorum, or an independent reproduction.

The Chronicle is an actual one-entry candidate ledger, not a running production
Chronicle. Its anchored payload explicitly records hardware/production claims
as unearned. New bitstreams or observations require new append-only checkpoints;
never rewrite this published receipt to make it describe later work.
