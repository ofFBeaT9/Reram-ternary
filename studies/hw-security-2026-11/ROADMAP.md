# TCIM0 hardware security: roadmap (m1frame, native mode)

4 November 2026. Input: `input_AI_Hardware_Hacking_m1.pdf` ("AI Hardware Hacking: What It Is and How to Secure TCIMO &
TRITONE", @m1, 4 Nov 2026, 18 pages). Owner's decision: apply everything the PDF lists for TCIM0.
Rule of the repository: a number is stated only when a script here reproduces it.

## 0. Recall (what is already known about TCIM0, from docs/STATUS.md and chip/sky130/ARCHITECTURE.md)

- SKY130 test chip: 72 x 24 array of 2T2R cells, two states per device (+1 = LRS/HRS, 0 = HRS/HRS, -1 = HRS/LRS).
- Read path: 48 current-mode sense amplifiers (one per bit line, `sa` in chip/sky130/sim/periph.spice), all rows
  summed digitally in tcim_core. There is no ADC on this chip (the analog SUM operation answers with zero counts).
- tcim_core (revision 4.2): a digital product reads only rows with a non-zero input (zero-skipping on inputs);
  programming is pulse-and-verify and stops as soon as every device verifies; PITER shows the pulse count.
- In IDLE every bit, source and word line is grounded (checked every cycle by the chip test bench).
- Supplies at the top level: macro 3.3 V on vdda1, macro 1.8 V (sense amplifiers, level-shifter inputs) and the digital
  block both on vccd1, one ground vssa1 for both.
- The first chip holds test patterns, not secret weights.

## 1. Analyst: project brief

Problem: the PDF lists attack families that recover weights or inputs from power, timing, faults and Trojans, and a
12-item defence checklist (items 1-6 TCIM0, 7-9 TRITONE, 10-12 all/prototype).
Grounded anchors: TCIM0's own RTL, netlists and device model; SkyWater's ReRAM data.
Core hypothesis: some PDF fixes do not map onto TCIM0 as built (no ADC; two-state devices; 72 rows); the leaks that
TCIM0 really has must be measured on TCIM0's own model before and after each fix.

## 2. PM: requirements

Functional
- F1 Products take a number of clock cycles independent of inputs and weights (default); zero-skipping opt-in.
- F2 Rows are read in a randomized order (default).
- F3 Every program command issues the same number of pulse steps whatever the weights and device behaviour (default);
  padding pulses must not bias any device. Variable (stop-at-verify) programming opt-in.
- F4 A set-only LOCK bit, cleared only by reset, that forces F1-F3 on and hides the pulse count.
- F5 A margin check command that flags a device drifting toward the read reference before it misreads (the PDF's
  "CRC/MAC on stored weights ... fires before accuracy drops").
- F6 Read power independent of the stored weights: a cell encoding with a constant number of low-resistance devices
  per row, buildable with two-state devices (PDF item 2; its own proposal, w = 0 as two mid-conductance devices,
  needs a third reliable level).
- F7 Sense-amplifier ("ADC") supply current independent of the decision, or made irrelevant by F6 (PDF item 1).
- F8 Idle PDN impedance independent of stored states (PDF item 6, DExiM); bit lines fixed when idle.
- F9 Supply-droop / clock-glitch / EM sensors with automatic reset (PDF item 5).
- F10 Decoupling and isolated array supply (PDF item 6).
- F11 Lint gate, netlist = RTL proof, pinned tools and hashes (items 10, 12); host-link fuzzing of the FPGA prototype
  (item 11).
Non-functional: every existing check keeps passing; every new behaviour has a test that fails on a planted fault.
Out of scope: TRITONE items 7-9 except where they apply to TCIM0 (lock bit, reset values); the PDF's CEO quotes.
Success metrics: TVLA |t| < 4.5 on TCIM0's model at the trace counts stated; two-copy formal miter proves timing
independence; all suites pass; ChipFoundry precheck 14 of 14 on the rebuilt chip.

## 3. Architect: design

- RTL (tcim_core): new register SEC (+3, tryte): t0 ZSKIP, t1 VARPROG, t2 NOSHUF (all opt-in, reset 0), t3 LOCK
  (set-only). Products read all 72 rows starting at a pseudo-random row (16-bit LFSR, rotation mod 72) unless ZSKIP.
  Programming: each phase runs exactly 21 verify-pulse steps and a final verify; a step whose devices all verify
  issues a pulse with empty masks. With the macro's line rules an empty set pulse grounds every bit and source line,
  an empty reset pulse puts VPRG on every bit and source line: no voltage across any device.
  PCMD t0 = 0, t1 = + : margin check (READ, VFY_SET, VFY_RESET of the row); PDATA <- weights read, MARG (+52, word,
  RO) <- + for each column with a device inside the margin band; WERR if any.
- Cell encoding for the next chip (F6): one-of-three per weight (3T3R): devices P, N, Z; exactly one is LRS
  (+1: P, -1: N, 0: Z). Every row then has exactly 24 LRS devices; a read with other than one LRS per cell is a
  detected error. +50 % array area, 24 more bit-line slices.
- Analog checks: sense amplifier supply current by decision (SPICE, mismatch); idle supply impedance with all-LRS vs
  all-HRS rows (SPICE AC).
- Physical: rebuild the digital block (place and route on the PC), top level, sign-off, precheck.

## 4. Scrum master: stories (acceptance criteria)

S1 tools/tvla_tcim0.py: fixed-vs-random Welch t on TCIM0's model for read power, product time and programming,
   baseline and each fix (AC: results/security/tvla.json, reproducible with a seed).
S2 RTL F1-F5 (AC: lint 0 warnings; make rtl / rtl-pnx / rtl-verilator pass with new directed tests; mutation with new
   faults all detected; formal safety + new properties + check_faults; two-copy miter proves equal timing).
S3 equiv: the netlist given to place and route equals the new RTL (AC: 0 unproven); the comparison with the
   revision 4.1 reference moved deliberately.
S4 chip: make rtl-chip (3 timing settings), Verilator, mutation_chip 26/26 (+ new), FPGA sim checks.
S5 SPICE: sense amplifier current by decision; idle impedance; one-of-three read currents (AC: numbers in results/security).
S6 PC: place and route, gate-level run, top level, DRC/LVS/antenna, ChipFoundry precheck in their versions.
S7 Page and documents with every number from S1-S6; council and red team; final report.
