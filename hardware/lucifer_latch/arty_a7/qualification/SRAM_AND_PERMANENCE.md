# SRAM volatility and the permanence boundary

The Arty A7's Artix-7 FPGA has SRAM configuration and volatile flip-flop state.
Removing power, reconfiguring, or asserting the design's reset can discard the
trip. The supplied JTAG program script only loads volatile configuration. Writing
a bitstream into SPI boot flash would restore the *design* on power-up; it would
not restore the previous run's latched trip. The initialized design eventually
rearms after its startup qualification unless another persistent mechanism blocks
it. No eFUSE, OTP element, permanent physical latch or protected nonvolatile trip
authority is implemented or tested in this candidate.

The only candidate irreversibility claim is: **within a powered, correctly clocked,
configured interval, with reset/power/configuration and alternate effect paths
outside the attacker's control, the exposed software-trigger input cannot clear
an observed trip.** Physical tests must substantiate that claim and the custody
assumptions. It does not include indefinite hardware lifetime, metastability-free
operation, fault injection, power cycling or reprogramming resistance.

## Additional mechanisms and what they would establish

| Mechanism | Potential claim | Necessary conditions and unresolved work |
| --- | --- | --- |
| External mechanically latching interlock in the actual effect path | Trip survives loss of FPGA power; reset can require a physical operator | Verify fail-off driver, contact/current ratings and welded-contact detection; isolate reset coil/circuit from software; test power loss and brownouts. Operator-resettable is not permanent. |
| Protected monotonic nonvolatile trip authority outside attacker control | Durable software-nonclearable state across FPGA reconfiguration | Review atomic write/power-fail behavior, antirollback, boot default-OFF and key/reset custody; enforce at effect boundary. An ordinary file, flash bit or SQLite row under the same principal is insufficient. |
| Reviewed one-shot physical disconnect/OTP mechanism in the effect path | One-way state within a declared replacement/tampering threat model | Select and qualify a purpose-built component/circuit, trip energy, fault response and readback. Component replacement remains a boundary. This requires hardware design and separate acceptance; none is provided here. |

FPGA security eFUSE facilities are not automatically an application-level permanent
kill latch. Do not program device fuses or guess SPI parts from this packet. A
permanence requirement must be resolved by an explicit design review before any
irreversible programming or destructive test. This packet supplies no such steps.

Choose the required claim before testing. If E3.1 is required to mean permanent
physical irreversibility across power/reconfiguration, this candidate cannot earn
it even with flawless bounded-trip measurements and a witness quorum. If the
intended claim is bounded software non-clearability, publish those bounds on every
receipt and production review. Quorum signatures cannot strengthen the circuit.
