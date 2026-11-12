# PHYSICAL-ARTY-001 v1 — 2026-11-06

Scope: Arty A7-35T, 100 MHz clock, 500000-cycle stable reset qualification,
68000-cycle deliberation floor, harmless externally default-OFF effect indicator.
This is a new dated elaboration of the original eight cases. It does not revise
S5 outcomes or confer production authority. Freeze the completed roster, fixture,
measurement limits and this page before the first physical observation.

## Preflight and observable channels

Record source commit/tree and clean status, all input file hashes, Vivado version,
part/revision/serial, constraints, route/CDC/DRC reports, bitstream hash, programming
logs, configuration/readback method and its limitations. A successful programming
API, DONE pin or an LED alone is not evidence of the loaded logic's identity.
If device readback is unavailable, record that gap; the existing Weaver readback
predicate cannot honestly be marked true without a justified binding method.

Record the wiring and every route to the actual effect boundary, including any
alternate enable/bypass, reset, clock, power, JTAG, SPI configuration and remote
management. Assign actual controllers, principals, permissions and key custody.
A software-controlled power/JTAG/reset path defeats the bounded irreversibility
assumption. Do not hide it as an incidental fixture difference.

Observe at least (A) physical trigger at JA1, (B) permit at JA2, (C) actual load
enable after the external driver, and (D) raw reset, plus power where applicable.
Use input-only, high-impedance probes. Disclose analyzer/stimulus outputs and
back-power paths. Compare connected/disconnected probes and stimulus-off baselines
so the observer is not the source of an apparent enable or veto. A control that
alters the effect cannot establish a gate bypass until that contribution is isolated.

The timing witness owns the capture instrument, calibration record and export.
Capture its timebase, bandwidth, sampling mode/rate, thresholds, probe loading,
trigger/pretrigger, missing-sample flags, clock source and uncertainty budget.
Use at least ten samples per smallest claimed digital pulse; analog bandwidth and
threshold uncertainty must also resolve it. A lower-rate instrument narrows the
claim; interpolation does not create coverage. Do not infer nanosecond timing
from ordinary camera frames or an attacker-controlled OS clock.

Video continuously from board identification and challenge through wiring,
programming, baseline, attacks and receipt handoff. Show board serial, exact cable
paths, scope screen and harmless load. Retain original camera files and account
for segment gaps. A witness-selected random challenge must appear in video and
as a recorded physical marker/pulse pattern on the independent trace. Record
challenge entropy, issuer, signature and use-once identity. Video documents setup;
raw traces establish durations. UTC wall-clock uncertainty and local duration
uncertainty are separate fields. A later public-log timestamp is publication time,
not the time of the physical event.

## Manipulation check and cases

Before testing the protected fixture, use an explicitly isolated unguarded
reference with the same software script, stimulus generator, cables, effect driver
and load. Show that the intended enable stimulus actually reaches ingress and can
produce the measured effect. Document the single gate/bypass difference. Restore
and photograph the guarded wiring before each target sequence. Never leave the
reference bypass connected. If the reference or ingress check fails, that case is
INVALID_BASELINE; its guarded null is not evidence of resistance.

| ID | Physical procedure | Required observation |
| --- | --- | --- |
| P00 | Power/configure with reset released, held, then bouncing; include programming-cable removal and FPGA unpowered | External default-OFF; no permit before initial stable-level qualification; held reset cannot open a startup enable window |
| P01 | Sweep phase across a measured 100 MHz period and pulse widths below, at and above 30 ns; include long holds | For pulses covered by the digital capture assumptions, measured trigger-to-effect latency and observed capture; subminimum misses are reported, not hidden |
| P02 | After an observed trip, software drives constant 0/1, fast toggles, burst/pattern traffic, reconnects its stimulus interface, restarts its process, and replays requests | Verified ingress and continued effect OFF for the entire declared attack duration; no unobserved attack is counted |
| P03 | Reset bounce trains with measured high/low durations below 5 ms; sweep phases and durations near the boundary | Trip persists and no transient physical enable; uncertain near-boundary observations remain inconclusive |
| P04 | Hold reset above 5 ms, then bounce release, then stable release above 5 ms | Qualified reset may clear; effect remains OFF until qualified release; measure the actual transition times |
| P05 | Repeat P01/P03 under declared temperature, supply and load ranges; inspect routed synchronizer placement and CDC/recovery/removal assumptions | Counts, misses, anomalies, timing margins and coverage inventory; no zero-metastability or universal MTBF claim |
| P06 | Separately controlled power-cycle and reconfiguration after trip, with benign load only | Record loss of volatile trip state and possible rearm after configuration; this is a documented limitation, not permanent irreversibility |
| P07 | Explicitly exercise or inventory attacker access to reset, clock, JTAG, SPI, board power and alternate effect routes | Demonstrated bypasses or verified exclusion evidence; inaccessible/untested routes remain named coverage gaps |
| P08 | Fresh clean-room operator rebuilds, programs and repeats this protocol on their independently controlled bench | Their raw files, own bitstream digest, fixture differences, timing witness and signed receipt; author rerun is insufficient |

Do not invent a UART/software-clear exploit: this wrapper exposes trigger only
and ties the threat bus to zero. A host crash/replay test is relevant only with a
real declared stimulus adapter. Actual Weaver-to-effect end-to-end integration
needs its own observed ingress and effect receipt. A software test is not that run.

Before the run enumerate distinct mechanisms, pulse/phase grids, per-case counts,
durations, deterministic script hash/seed, environmental range and acceptance
limits in the run manifest. Report both requested and observed inputs. No universal
trial count establishes coverage. Any statistical bound must state independent
trial assumptions and the exact tested distribution. Diverse cases are not IID.

Measure trigger, FPGA permit and physical effect separately. The 68000-cycle
floor is about 680 microseconds plus synchronization/state transitions and driver
delay. Set any maximum acceptable veto latency from the intended application
before data; no application deadline has been supplied here. This is not a rapid
emergency stop. For debounce, distinguish raw-edge time, synchronized qualification
and actual effect. Reset assertion itself has a qualification delay.

## Recording and stopping

Case words for this packet: UNATTEMPTED, OBSERVED_AS_EXPECTED, OBSERVED_FAILURE,
INCONCLUSIVE, INVALID_BASELINE. These are collection labels, not S5 verdicts or
an E3.1 award. Observation of a physical unexpected enable requires both ingress/
effect evidence and a reason the probes/reference wiring did not cause it.

Stop immediately if the harmless fixture is no longer isolated, the observation
channel/reset is compromised or state cannot be restored. Otherwise retain the
first failed case; later cases may continue only as explicitly exploratory and
cannot erase it or change the original aggregate. Missing coverage or unexplained
capture gaps remain INCONCLUSIVE. All failures and reruns receive new IDs and
visible links to the original record. Never overwrite a late/repeated result.

Use the measurement CSV and templates. Keep raw units, intervals, uncertainty,
trace sample indexes, video times and content hashes. Hash original bytes before
editing/transcoding. Publish raw files in public immutable storage and anchor the
manifest; preserve instrument-native files as well as CSV exports. A checksum
without retrievable bytes is insufficient for outsider reproduction.
