# Security items for the next chip (proposal, 4 November 2026)

These items of the input document need new drawn circuits or a new array, so they cannot go on the SKY130 chip of
revision 4.5 / 4.6 without a new layout. They are proposals: nothing here is drawn or simulated as a circuit unless
the line says so.

## 1. One-of-three cell (PDK item 2, constant-sum cells)

The document proposes weight 0 as two mid-conductance devices. SkyWater's ReRAM has two published states (reset about
4.5 µS, set 30–120 µS); a reliable middle level is not published. The same goal, a read current that does not depend on
the weights, is reached with two-state devices:

- Three devices per weight, P, N and Z, each with its own select transistor and bit line (3T3R).
- Exactly one device is low-resistance: +1 = P, −1 = N, 0 = Z. Every row then has exactly 24 low-resistance devices.
- Read: three sense amplifiers per weight (72 instead of 48). A read with other than one low-resistance device in a
  cell is a detected error (WERR), which the 2T2R cell can only partly detect (both devices low-resistance).
- Programming: reset the two devices that must be high-resistance, set the one that must be low-resistance; the
  constant-time sequence of revision 4.6 applies unchanged (21 + 21 steps).
- It needs revision 4.7's logic: a start row that is uniform over the 72 rows (revision 4.7) and the random accumulator
  offset.
- Cost: +50 % array area, 24 more bit-line slices, 24 more bit-line pads or a wider column multiplexer.
- Model result (`tools/tvla_tcim0.py`, model 2 of 6 November, `results/security/tvla.json`; 150,000 traces per group,
  5 µA noise, 0.15 µA per flipped accumulator bit): with revision 4.7's logic the largest |t| is
  3.13 (weights) and 2.61 (inputs), below 4.5; with revision 4.6's start rows
  7.34 (weights, no digital term), which leaks. At 1 µA noise (`results/security/tvla_1of3_noise1uA.json`)
  4.08 (weights): close to the limit. A small first-order difference remains (frozen sense-amplifier mismatch and
  high-resistance spread), which more traces or less noise would show. The 2T2R array with revision 4.7's logic:
  14.24 (weights).
- Programming still leaks through the number of devices each pulse selects (|t| 66.38 at 20,000
  traces), which depends on which devices must change and on how fast each one switches. Program the weights in a trusted place.

## 2. Separate array supply and decoupling (document item 6)

- The macro's 1.8 V (sense amplifiers, level-shifter inputs) moves from vccd1 to vccd2 with its own ground vssd2, so the
  logic's switching current and the array's read current are drawn from different pads and can be filtered separately on
  the board. Both domains stay at 1.8 V, so the signals between them need no level shifting.
- Decoupling capacitance (MIM or MOS) under the macro's supply buses; size to be set from the read current
  (2.386 µA per sense amplifier when it reads a low-resistance device, `results/security/sa_power.json`).
- Simulation for this chip: `chip/sky130/sim/idle_impedance.py` shows that in the powered idle state, in the schematic
  without layout parasitics and with the device as a resistor, the stored states change the impedance seen at any supply
  pin by at most 1e-6 (relative), while a read changes it by 0.49 at vccd. The idle isolation is met in that model (grounded
  lines, off select transistors); an unpowered chip and the package are not modelled. The separate supply is for reads.

## 3. Sensors (document item 5)

- Supply droop: a comparator of vccd against a reference (the chip has no bandgap; one would be needed) that, when it
  trips, aborts the running command, sets WERR and clears X0–X2 and PDATA.
- Clock glitch: a delay-line detector on the serial clock and the core clock with the same response.
- EM / laser: no detector specified; the document gives no circuit.
- The response is logic (tcim_core): an input `alarm` that forces the sequencer to S_FINISH with WERR. Specified here,
  not written into the RTL, because nothing drives it on this chip.

## 4. Random source

The LFSR that picks the start row and the accumulator offset of a product is deterministic after reset (seed 16'hace1,
advanced every clock): the same firmware gets the same values on every boot, and whoever controls the timing of GO controls
them. A true random source (ring-oscillator jitter) is needed.

## 5. Also for the next revision (from the review of 6 November)

- LOCK that survives reset (a fuse or a non-volatile bit), so that reset plus bus access cannot read the weights.
- A redundant count of row answers in a fixed-latency product (WERR when it is not 72), so that one fault cannot end a
  product early.
- Break-before-make on asynchronous reset in the array controller, and a transient simulation of empty pulses and of a
  reset during a pulse.
