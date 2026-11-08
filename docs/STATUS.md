# TCIM0: a balanced-ternary ReRAM compute-in-memory tile for REBEL-6, and its SKY130 test chip

**Design status report, revision 4.8, 8 November 2026** (sections 1–14 as of revision 4.5, 12 October, except where marked; section 15 gives the security changes of revisions 4.6 and 4.7, their verification, revision 4.8 and the cell options).
Repository `reram-ternary`. Every number in this report is produced by a script in the repository and stored in
`results/`; the file is named where the number is quoted, or in the validation table (section 12). `make test` re-derives
key results by a second method and compares every number the roadmap quotes with the stored files. The roadmap
(`docs/ROADMAP_v4.4.md`) holds the history of each result; this report gives the state of the design as a whole and
explains how each part works.

---

## Summary

**What it is.** TCIM0 is one tile of a compute-in-memory accelerator. It stores a 72 × 24 matrix of ternary weights
(−1, 0, +1) in resistive memory (ReRAM) and multiplies it with a 72-trit input vector, returning 24 integers between −72
and +72. It is a memory-mapped device for REBEL-6, the balanced-ternary processor of the research group at the University
of South-Eastern Norway (USN); one product replaces 72 executions of REBEL-6's ternary multiply-accumulate instruction.
Each weight is held by two ReRAM devices that are each either on or off (2T2R), so every device is read as one bit and
the digital result is exact whenever every device is read correctly.

**What has been built.** A complete test chip for SkyWater's SKY130 process with its ReRAM option, drawn for
ChipFoundry's analog harness (Caravan): the drawn 72 × 24 array with 3,456 ReRAM devices, all periphery (word-line and
bit-line drivers, level shifters, 48 sense amplifiers with a switchable reference), an array controller, the verified
TCIM0 logic with its serial port, pads, supplies, and one separate 2T2R cell wired to pads for direct device measurement.

**What is established, by simulation and by checks of the drawn layout.**
- *Logic* (revision 4.7). Two simulators run 97,463 self-checking tests without a failure in both supported trit codes;
  every one of 115 injected faults is detected (121 in the second code); formal proofs cover the sequencers, and each of
  28 faults planted in them makes its proof fail.
  The chip's array controller is tested cycle by cycle against an electrical model of the analog macro; all
  26 faults injected into it are detected.
- *Circuits.* The read path, drivers and level shifters work over 5 process corners, −40 to 125 °C and ±10 % supply,
  and with transistor mismatch. Programming through the drawn drivers reaches the set and reset targets at all corners,
  with SkyWater's device model and the reset rate fitted to SkyWater's published yields.
- *Layout.* Every periphery cell, the analog macro and the full chip pass the design-rule check (DRC) and match their
  schematics (layout versus schematic, LVS); a deliberately planted error was caught by each check. The logic block
  is placed and routed, meets timing at every corner, and its routed netlist passes the full test bench. ChipFoundry's
  own precheck passes all 14 of its checks on the final layout, run in ChipFoundry's own pinned tool and PDK versions
  (section 9.10; for revision 4.7, PC batch 28c, section 15.3).
- *Security* (revisions 4.6 and 4.7, section 15). Products take the same time whatever the inputs, programming takes
  the same time whatever the devices do, LOCK blocks the debug paths, and the leak model shows no input leak. The
  weights still leak through the 2T2R cell in the model; a one-of-three cell for the next chip closes that in the model.

**What is not established.** Everything about the memory devices themselves rests on models: the device model is fitted
to published data, and SkyWater's public yield statistics cannot pin the device-to-device spread down to better than a
factor of about seven (section 3.3). Simulation can make the logic certain and the circuit margins robust against a
stated range of device behaviour; it cannot say whether the cells on a wafer fall inside that range. The test chip is
designed to measure exactly that, with programming levels supplied from the test board so that they can be changed
after the first measurement.

**What remains before fabrication** (section 11): no design work. ChipFoundry must confirm that a shuttle accepts the
ReRAM layer (their ReRAM page still names a November 2025 shuttle; their FAQ says their standard shuttle "does not
initially support ReRam"), that the chip is processed as sky130B, and which PDK and ReRAM library they sign off with.
Then the project folder must be submitted through their flow, and the test board must be built. Until ChipFoundry
confirms ReRAM, the accurate description is "design complete, passes the foundry's precheck", not "ready to fabricate".

---

## Contents

1. What TCIM0 computes and how
2. How the evidence is produced
3. The memory device and its model
4. Programming: pulse-and-verify
5. Reading: sense amplifier and reference
6. The tile: digital mode, analog mode, a network
7. The logic: function, verification, timing
8. The IHP SG13G2 design (periphery, layout)
9. The SKY130 test chip
10. FPGA demonstration
11. Fabrication readiness
12. Validation summary
13. Limits: what cannot be made certain before silicon
14. Open questions to people outside the project
15. Hardware security (revisions 4.6 and 4.7)

Appendices: A. Tools and versions. B. How to reproduce. C. History of revisions. D. Glossary.

---

## 1. What TCIM0 computes and how

### 1.1 The function

For column j the device returns

  Y[j] = Σ W[r][j] · X[r], summed over the rows r = 0 … 71,

with weights W and inputs X in {−1, 0, +1}. In REBEL-6 software the same number takes three TMAC.T instructions per
column, 72 per tile. In its digital mode the device must return exactly what those instructions return, and the test
bench checks equality.

The tile size follows REBEL-6's word: a data word is 24 trits. Seventy-two rows are exactly three input words, one row of
weights is exactly one word, and the 24 results fit in 6-trit trytes (range ±364).

### 1.2 One weight is two resistors (2T2R)

A ReRAM device is a resistor with two stable states, low resistance (LRS) and high resistance (HRS), switched by voltage
pulses: a *set* pulse (bit line positive) forms a conducting filament and gives the LRS, a *reset* pulse of opposite
polarity ruptures it and gives the HRS. A ternary weight uses two devices, each in series with its own select transistor,
on two bit lines BL+ and BL−:

| Weight | Device on BL+ | Device on BL− | Read current at 0.2 V, IHP published means | Read conductance, SkyWater published |
|---|---|---|---|---|
| +1 | LRS | HRS | 43.59 µA / 2.85 µA | 30–120 µS / about 4.5 µS |
| 0 | HRS | HRS | 2.85 µA / 2.85 µA | 4.5 µS / 4.5 µS |
| −1 | HRS | LRS | 2.85 µA / 43.59 µA | 4.5 µS / 30–120 µS |

Two states per device are far easier to program and to read than the four levels per device the original draft
proposed. The encoding is prior art (Laborieux et al., 2020, on a 2T2R array from CEA-Leti); TCIM0 differs in how it
reads (section 5). Both devices in LRS is an invalid cell; the logic reports it (WERR) and counts it as 0.

### 1.3 Two read modes

- **Digital mode, the product.** One row is selected at a time. Each of the 48 bit-line currents is compared with a
  reference between the HRS and LRS currents, so each device is read as one bit and the weight is recovered exactly. A
  counter per column adds or subtracts the weight according to the input trit. Rows whose input is 0 are skipped. The
  result is exact whenever every device is read correctly.
- **Analog mode, an experiment.** Several rows are selected together, their currents add on the bit lines, and the
  difference BL+ − BL− is converted to a number. Positive and negative inputs are evaluated in two phases (a word line
  cannot apply a negative input). It is faster but approximate, because every device's deviation from its nominal
  current enters the sum. The SKY130 test chip has no converter and supports the digital mode only.

### 1.4 The device seen by the processor

TCIM0 is a memory-mapped device with the register map below (proposal: slot 11, the first reserved slot of REBEL-6's
I/O space, and interrupt source 7, the first platform source; both to be agreed with the REBEL-6 maintainers).

| Offset (trytes) | Register | Function |
|---|---|---|
| +0 | CTRL | enable, interrupt enable, mode (digital/analog), GO |
| +1 | STAT | BUSY, DONE, WERR (programming failed, invalid cell or invalid row), SAT (analog result clipped) |
| +4, +8, +12 | X0..X2 | the 72-trit input vector |
| +16 … +39 | Y[0..23] | column results |
| +40 | PROW | row to program or read back |
| +44 | PDATA | the 24 weights of that row |
| +3 | SEC | (revision 4.6) t0 ZSKIP, t1 VARPROG, t2 NOSHUF: opt-ins to the earlier behaviour; t3 LOCK: set-only, cleared by reset; setting LOCK clears the opt-ins, and (revision 4.7) every use of an opt-in is gated by LOCK |
| +48 | PCMD | + programs the row with verify, − reads it back (revision 4.7: refused under LOCK, WERR, no array access), (0,+) margin check (revision 4.6; under LOCK it does not write PDATA) |
| +49 | PITER | pulses used by the last program command (real pulses only; reads 0 under LOCK) |
| +50 | ACT | (revision 4.6) parity of the dummy accumulators; reads 0 under LOCK |
| +52 | MARG | (revision 4.6, word) + for each column whose devices drifted into the margin band at the last margin check |

Behind the registers are three sequencers. The **product sequencer** reads every row (revision 4.6: all 72 rows from a
start row given by a 16-bit LFSR (revision 4.7: the LFSR value modulo 72, so every row is equally likely), so that the time does not depend on the inputs; with ZSKIP only the rows with a
non-zero input, as up to revision 4.5), one array request per row, back to back. The **programming sequencer** applies
pulse-and-verify to a whole row (section 4; revision 4.6: always 21 + 21 pulse steps, unless VARPROG). The
**read-back** fills PDATA from the array. Section 15 explains the revision 4.6 and 4.7 changes (4.7 also starts the result
accumulators at a random offset that the last row takes off again). A four-wire serial port (SPI mode 0, 64-bit frames) gives a test chip access to
the registers; on a REBEL-6 system an FPGA hosting the processor bridges memory-mapped accesses to that port.

Trits travel on two wires each. REBEL-6's specification defines no wire code for a trit; the USN group's tools use
BSD-PNX (10 = +1, 11 = 0, 01 = −1). TCIM0 builds with BSD-PNX or with a two's-complement code (01 = +1, 00 = 0,
11 = −1), and both builds are fully verified. The SKY130 chip uses the two's-complement build.

---

## 2. How the evidence is produced

- **Scripts, not hand calculation.** Each result has a script; its output is written to `results/`. A test
  (`tests/test_claims.py`) compares every number the roadmap quotes with those files and fails if one is stale.
- **Second methods.** Key results are derived a second way (`tests/test_independent.py`). The device model is
  implemented three times (Python, ngspice, Verilog-A in Gnucap) and solved a fourth time with a general-purpose stiff
  integrator; the tile solver is checked against a brute-force solver of the full resistor network; the analog-mode
  error is checked against a closed-form value; the SKY130 programming method (quasi-static) is checked against full
  transient simulation where both converge (section 9.6).
- **Tests that are shown able to fail.** A passing test proves little by itself. The test bench is measured by
  *mutation testing*: copies of the logic, each with one deliberate fault, must all be caught. The formal proofs, the
  gate-level runs, every LVS and every DRC were also run once with a planted error and had to report it. On 11 October
  this method found a gap in the chip test bench (section 9.4): a fault survived, a test was added, and the fault is now
  detected.
- **Model versus silicon.** A simulation result is a statement about the models. This report says which one is meant.
  Proposals are labelled as proposals.
- **Frozen revisions.** When a revision closes, the files its roadmap section quotes are copied to `results/rev<NN>`
  (4, 4.1, 4.2, 4.3 and 4.4 so far); the claims of older sections are checked against those copies.

---

## 3. The memory device and its model

### 3.1 The model

The device model is the Stanford-PKU compact model, the same equations SkyWater's open ReRAM model uses. It has one state
variable, the gap g between the tip of a conducting filament and the opposite electrode:

- current: I = I0 · exp(−g/g0) · sinh(V/V0);
- gap dynamics: dg/dt = −v0 · exp(−Ea/kT) · sinh(γ a0 V / (tox · kT/q)), with γ falling as the gap grows;
- filament temperature from its own dissipation: T = T0 + |V·I| · Rth.

The current falls exponentially with the gap; the tip moves exponentially faster with voltage and temperature. That is
why switching has a sharp threshold, and why a small change in a parameter moves the switching voltage noticeably.

For IHP the static parameters are IHP's published values (I0 854 µA, g0 0.28 nm, V0 0.35 V, tox 6 nm, maximum gap
1.8 nm). **The kinetic values printed in the same IHP paper (Ea 0.6 eV, v0 0.4 m/s) do not reproduce the paper's own
switching**: with them the model sets at 0.21 V instead of the measured 0.65 to 0.75 V, and a 0.2 V read erases the HRS
within a second. The kinetics were re-fitted to Ea = 1.0 eV (inside the 0.97 to 1.16 eV IHP measured from retention) and
v0 = 2.79 m/s, which puts the set voltage at the measured 0.70 V. This fit rests on one measured number. For SKY130 the
model runs with SkyWater's own parameters (`sky130_fd_pr_reram` v2.0.3) and the reset rate fitted in section 3.3.

The model contains no forming, no retention loss without bias, no temperature dependence of the read current, no
cycle-to-cycle randomness, and an abrupt reset. Device-to-device spread is added as scenarios, not as data. **It is a
stand-in** for the foundries' own models.

### 3.2 The three implementations agree

Python reference, ngspice behavioural subcircuit, and Verilog-A in Gnucap with the gap as a circuit node: the set
voltage of a ramp agrees within 0.26 mV, the gap after a 1 µs pulse within 0.5 pm, the time to set after a 1.1 V step
within 0.11 %, the time to reset after a −1.0 V step within 1.0 %. The SKY130 macro simulations use a fourth
implementation (an ngspice subcircuit in `chip/sky130/sim/macro_sim.py`), which agrees with the Python reference within
about 1 pm of gap. Agreement shows the equations are implemented consistently; it does not show that they describe the
device.

### 3.3 Device-to-device spread, and a fit to SkyWater's silicon yields

Cells differ from each other. The programming studies give each device its own v0, Ea and I0, drawn from a normal
distribution scaled by a factor k (k = 1: σ 0.5 in ln v0, 0.03 eV in Ea, 0.10 in ln I0). These are **assumptions**.

SkyWater publishes the only public silicon yield statistic of a HfO2 1T1R cell: with one 1 µs pulse, 90.83 % of cells
reset (word line 2.5 V, source line 2.6 V) and 97.45 % set. The model was fitted to these two numbers with two free
parameters: a factor F on the reset switching rate, and the spread k. SkyWater does not publish its test structure's
transistor width or its pass criteria, so 1, 2 and 4 µm and three pairs of criteria were tried (`model/fit_skywater.py`,
400 cells per point).

- Three of the nine combinations reproduce both yields. They give **k between 0.53 and 3.48**: the public data cannot
  pin the spread down to better than a factor of about seven.
- In every combination the model's reset must be made faster by **2.3 to 8.9 orders of magnitude** (log10 F). With
  SkyWater's own published parameters the model resets far too slowly; those parameters do not describe SkyWater's cells.

The SKY130 chip simulations use the fit for a 1 µm select transistor (log10 F = 7.375) and test cells whose reset is up
to four decades slower than that (section 9.6).

---

## 4. Programming: pulse-and-verify

### 4.1 The scheme

Programming follows the scheme IHP published for these devices. Each pulse is 1 µs. The pulse amplitude rises one step
per pulse (21 amplitude codes, 0 to 20), and after every pulse the device is read against a *verify* reference; a device
stops receiving pulses as soon as its read passes. The select transistor's gate voltage limits the current through the
device and so sets where a set pulse lands. A row is programmed in two phases: devices that must become HRS are reset
first, then devices that must become LRS are set. Three references therefore exist: the reset target (a device must read
below it after reset), the read reference (between the states), and the set target (a device must read above it after
set). The gaps between them are the guard bands that keep a programmed device from being misread later.

| | IHP design (0.2 V read) | SKY130 chip (0.2 V read) |
|---|---|---|
| Reset target | ≤ 6 µA (30 µS) | ≤ 8 µS (simulated trip 7.9–8.4 µS) |
| Read reference | 25 µA (125 µS) | 12 µS (simulated trip 12.0–12.8 µS) |
| Set target | ≥ 42 µA (210 µS) | ≥ 24 µS (simulated trip 23.7–27.4 µS) |
| Amplitude ladder | 0.5 V + 0.1 V per code, on chip | set by the test board from the code (section 9.6) |

### 4.2 IHP: select transistor and the reset gate voltage

- **Select transistor**: IHP 3.3 V NMOS, W = 4.5 µm, L = 0.45 µm. At 1.5 µm a fully set device cannot be reset even
  with a 3.3 V gate; 4.5 µm resets with margin.
- **Set** uses one generous gate voltage, 1.7 V, and stops on the verify read; the LRS lands between 44 and 50 µA.
- **Current**: about 0.5 mA per device during set, 0.52 to 0.60 mA during reset; a row programmed in parallel draws
  up to 12 mA (set) or 29 mA (reset).

Reset is the weak phase. How high must the select transistor's gate be during reset so that every device resets within
the 21 pulses?

| Study | Result |
|---|---|
| Assumed spread k = 2, 100 devices per corner | at the published 2.7 V, 7 (typical) to 12 (slow corner) of 100 devices do not reset; at 3.0 and 3.3 V none fail |
| Full circuit (PSP103 transistors + Verilog-A cell), the three slowest failing devices | not reset at 2.7 V; all reset at 3.0 and 3.3 V; peak reset current bounded at 0.76 mA |
| Spread fitted to SkyWater (k = 0.53 / 2.01 / 3.48), 200 cells, typical and slow corner | k = 0.53: 2.7 V is enough. k = 2.01: 3.3 V needed, 1 of 200 still fails at the slow corner. k = 3.48: 4 (typical) and 10 (slow) of 200 do not reset even at 3.3 V |

**Conclusion for IHP.** A reset gate of 3.0 to 3.3 V suffices unless the real spread lies at the high end of what
SkyWater's data allow; part of that high end is defective cells, which no voltage repairs. Open question to IHP: the
process specification states the 3.3 V gate limit for thick-oxide NMOS of L ≥ 0.6 µm; the select transistor is 0.45 µm.

### 4.3 Forming

A fresh device must be *formed* once: a higher voltage creates the conducting filament. IHP's published arrays form with
sweeps up to about 5 V; SkyWater forms at 2.2 to 3.1 V (bit line 2.4–3.3 V, word line 1.4–2.5 V). On SKY130 every level
is within 3.3 V, so forming uses the ordinary programming path with a forming map on the test board (section 9.6). For
IHP a forming path up to 5 V was built from stacked 3.3 V transistors (section 8.3). The model has no pristine state, so
forming itself is not simulated on either process.

---

## 5. Reading: sense amplifier and reference

### 5.1 The circuit

Each bit line is held near the read voltage (0.2 V) by a clamp transistor whose gate comes from a replica: a
diode-connected copy of the clamp that carries the reference current and stands on the 0.2 V reference, so the bit line
sits at 0.2 V exactly at the trip point in every corner. A PMOS current mirror supplies the reference current into the
sense node; if the cell draws more than the reference, the sense node falls and an inverter flips. The comparison is
thus between the cell's *conductance* and the reference conductance (reference current ÷ 0.2 V), not between two
voltages, and it needs no clock.

### 5.2 IHP SG13G2 (1.2 V devices, 3.3 V column switch)

| Check | Result |
|---|---|
| Trip current, 5 process corners | 24.61 to 24.66 µA for a 25 µA reference |
| Transistor mismatch, 200 Monte Carlo runs | mean 24.64 µA, σ 0.24 µA, range 24.03 to 25.37 µA |
| 5 corners × −40 / 27 / 85 / 125 °C × 1.08 / 1.20 / 1.32 V (60 cases) | trip 24.24 to 24.86 µA; smallest margin 9.4 µA to the six-sigma tails of the device distributions |
| Decision time after the word line rises | about 2 to 3 ns; LRS output within 3.75 ns in the worst case |
| On-chip reference (replica column ending in a 7.7 kΩ poly resistor) | trip 103 to 147 µS over 27 extreme cases; ±10 % read voltage moves it by less than 2 %; margins 33 µS to the HRS tail and 25 µS to the LRS tail |

**Read disturb.** The plain clamp reads HRS cells at about 0.29 V instead of 0.20 V. In the model this shortens the life
of an HRS state under reading; the numbers rest on the one-point kinetic fit and may be wrong by orders of magnitude.
Remedies, if measurements require them: a regulated clamp, a lower read voltage, or periodic refresh.

### 5.3 SkyWater SKY130

SkyWater's cells sit at 30 to 120 µS after set and about 4.5 µS after reset, so the read reference moves to 12 µS, near
the geometric mean of the two states. The read path of the chip is described with the other chip circuits in section
9.5; the first study (revision 4.4, `results/rev44/sky130_read.json`) gave trip points of 12.46 to 13.29 µS over 45
corner, temperature and supply cases, σ 0.43 µS under mismatch, and a settled output 6.0 to 7.7 ns after the word line.

### 5.4 The hybrid read: evaluated, not adopted

A variant reads the sign of a weight by comparing the pair's two devices with each other, and only zero against the
reference. In the tile model it removes up to half of the "non-zero read as zero" errors but raises sign flips by a
factor of 1.7 to 2.9; the mean weight error falls by 0 to 36 %. At the published spread neither read makes an error.
Not adopted.

---

## 6. The tile: digital mode, analog mode, a network

The tile model solves the resistor network of a 72 × 24 tile: two bit lines and one source line per ternary column,
device currents drawn from IHP's published distributions, a clamp with input resistance and offset at each bit line, a
current mirror with gain error. It agrees with a brute-force network solver to one part in 10¹⁰.

**Digital mode** (60 tiles of 1,728 weights per case, 10 products per tile, least favourable wiring):

| Device level and spread | Wrong weights of 103,680 | Products with an error, of 600 |
|---|---|---|
| LRS3, published spread | 0 | 0 |
| LRS3, twice the spread, 2 mV clamp offset | 0 | 0 |
| LRS3, three times the spread | 4 | 24 |
| LRS1 (the weaker set level), published | 2 | 14 |
| LRS1, twice the spread | 4,616 | 600 |

With the LRS3 level the two states are 12 standard deviations from the reference, which is why the design programs to
the strongest level. "Exact" holds for bell-shaped distributions with the published means and spreads, which come from
4-kbit arrays read directly after programming. On silicon, exactness will rest on the verify step, read-back and
re-programming of cells that moved.

**Analog mode**: RMS error of a 72-row sum 0.41 result steps at the published spread (77 % of results exact, largest
error 1.7), 0.75 at twice the spread. Device spread alone gives the 0.41: ideal wires give the same number, so no circuit
can go below it. Analog mode stays an experiment.

**A network.** A small all-ternary network (72 inputs, 72 hidden, 10 outputs) for the 8 × 8 digits set reaches 94.7 % in
software. Digital mode gives the identical 94.7 % through the tile model and through the RTL. The data set is small; this
shows the approach is not broken, not that it scales.

**Energy and area (estimates).** Per product in digital mode: sense amplifiers 0.19 nJ, word lines 0.06 nJ, clock-gated
logic 0.80 nJ (zero-delay toggle count without clock tree or wires; real logic 1.5 to 3 times higher). A plain-CMOS tile
with its weights in flip-flops needs 2.27 nJ with clock gating. At this size the case for ReRAM is not energy; it is
1,728 weights stored without power in about 0.02 mm² of array (IHP), a seventh to a tenth of the flip-flops that would
hold them.

---

## 7. The logic: function, verification, timing

### 7.1 Verification

| Check | Result |
|---|---|
| Self-checking test bench, CXXRTL simulator (`make rtl`, `make rtl-pnx`) | 82,554 checks, 0 failures, both trit codes |
| The same test bench on Verilator, a second simulator (`make rtl-verilator`) | identical, both codes |
| Mutation test: copies with one injected fault each (`make mutation`, `make mutation-pnx`) | 75 of 75 faults detected; 81 of 81 in the BSD-PNX build |
| Lint (Verilator, all warnings) | 0 warnings, both codes, and the chip's logic (`make equiv-chip`) |
| Formal proofs (SymbiYosys): serial port, sequencer safety and progress, both codes | all four proven again on 12 October (safety in the BSD-PNX code: 3 h of solver time); 9 of 9 injected faults make a proof fail |
| Equivalence proofs | the conversion table equals its definition for all inputs in both codes; the plain-Verilog netlists given to place and route equal the RTL (TCIM0: 1,697 points; the chip block: 1,954 points, all proven) |

What the test bench covers: register access through the serial port; programming all 72 rows with verify and reading
them back, with a monitor on every pulse (amplitude starts at 0 and rises one step per pulse, reset before set, no
pulse reaches a device that has passed its verify, no pulse to a device that must not change); digital products against
the exact dot product; analog products against the expected converter counts, including clipping; error paths (devices
that never set or reset, invalid cells, all 657 invalid row indices, a device left between the reset target and the read
reference); every result value from −364 to +364 through the conversion to balanced ternary; the interrupt; the digits
network through the RTL. The array in the test bench is behavioural, with per-device currents drawn from the published
distributions; in the chip build it is replaced by a line-level model of the analog macro (section 9.4).

History that shaped the method: the revision 3 test bench had 60,401 passing checks and missed 30 of 66 injected faults
and two real bugs (an interrupt that could not be acknowledged after a failed command, and a serial frame decoded twice).
Both bugs were fixed and the test bench was extended until it detected every fault. The fault campaigns of revision 4.2
found three further gaps in the checks themselves, and that of 11 October one more (section 9.4). A review on 11 October
found that no test read the CTRL mode bit back: a design that never stored it would have passed. A test was added
(write EN and MODE, read both back; clear MODE, read again), with a matching injected fault ("CTRL mode bit never
stored"), which is detected. All gaps found are closed.

### 7.2 Synthesis, energy, clock gating

The product sequencer reads only rows with a non-zero input, back to back: 49.7 clock cycles per product on random data.
Clock gating, inserted by synthesis with the libraries' integrated clock-gating cells, halves the estimated logic energy
from 1.54 to 0.80 nJ per product. The gated netlists were simulated with and without a gating cell stuck off; the fault
is detected each time.

### 7.3 Place and route and timing after layout

| | IHP SG13G2 | SKY130 sky130A | SKY130 sky130B | **SKY130 chip block** (sky130B) |
|---|---|---|---|---|
| Design | TCIM0 | TCIM0 | TCIM0 | TCIM0 core + array controller, no converter |
| Flow library | typical | typical | slow (ss, 100 °C, 1.60 V) | slow (ss, 100 °C, 1.60 V) |
| Standard cells | 10,630 | 11,157 | 11,302 | 9,638 logic cells (1,074 flip-flops, 56 clock gates) + 610 antenna diodes |
| Routed block | 0.393 mm² | 0.174 mm² | 0.175 mm² | 0.189 mm² (550 × 343 µm, 48 % utilization) |
| Design-rule check | 5 chip-level density markers | 0 | 0 | 0 |
| Clock | 10 ns | 10 ns | 16 ns | 25 ns (board clock up to 40 MHz) |
| Setup slack, worst corner and parasitic case | +1.40 ns | −5.40 ns | +0.762 ns | +9.72 ns (ss, parasitics × 1.2) |
| Shortest period, slow corner (parasitics × 1 / × 1.2) | 8.61 / 9.27 ns | 15.43 / 16.17 ns | 15.24 / 15.75 ns | 14.73 / 15.31 ns |
| Hold slack, worst | ≥ 109 ps | positive | positive | +145 ps (ff, −40 °C, parasitics × 1.2) |
| Gate-level run of the routed netlist | 82,512 checks, 0 failures | 82,512 / 0 | 82,512 / 0 | 76,975 checks, 0 failures (Verilator) |

Timing after layout uses the parasitics extracted from the routed design, with ±20 % as a stand-in for best- and
worst-case extraction (on sky130B the platform's extraction rules are still those of sky130A). The sequencers count clock
cycles, so a slower clock lengthens every operation in proportion; the array's own read and pulse times are set by the
configuration pins (section 9.4). The flow's own equivalence check of the chip block's final netlist reports identical circuits
(`6_final_lec_check.log`). The chip block was routed twice: the second routing adds 602 antenna diodes (section 9.7) and
leaves the logic netlist unchanged line for line; the numbers in the table are those of the final routing.

The gate-level runs of the IHP and earlier SKY130 blocks used CXXRTL. For the chip block the run uses Verilator
(`flow/orfs/post/gls_chip.sh`: the routed netlist flattened by Yosys with the cell models, then the same test bench):
CXXRTL's model of this flattened netlist did not run correctly (the serial output stayed stuck), and the cause was not
found. The Verilator run passes, and fails as it must with one gate changed (an XNOR replaced) and with the clock gate of
the largest fan-out stuck; CXXRTL on the RTL and Verilator on the RTL agree check for check.

---

## 8. The IHP SG13G2 design (periphery, layout)

IHP SG13G2 with its MEMRES ReRAM module was the original target. Everything that the open PDK allows has been designed,
simulated with the PDK's PSP103 transistor models in Gnucap over 5 process corners and −40, 27 and 125 °C, and drawn.
The ReRAM element itself, its layers and rules are in IHP's MEMRES kit, which has not been available, so an IHP chip
cannot be completed (section 11.2).

### 8.1 Word-line driver, level shifter, column switch, test multiplexer

- Level shifter 1.2 V → 3.3 V: delay ≤ 2.74 ns, static current ≤ 0.61 nA.
- Word-line driver (NMOS 6/0.45 µm, PMOS 12/0.45 µm) into the drawn polysilicon word line (up to 5.2 kΩ, 48 gates,
  454 fF): far end at 90 % within 4.1 ns. Drawn at the array's pitch (72 drivers in a column 26.42 µm wide, two rows per
  2.17 µm slice); DRC clean and LVS match with the PDK's KLayout decks; re-simulated as extracted: far end settled within
  4.125 ns, at most 23 ps from the schematic run.
- Column switch (thick-oxide transmission gate, NMOS 40 µm, PMOS 80 µm): drops at most 95 mV at 0.6 mA and 127 mV at
  0.80 mA from 0.5 to 3.0 V, so the ladder's 0.1 V steps are not swallowed.
- Test multiplexer, 16 bit-line or source-line nodes to a pad with separate force and sense: on-resistance ≤ 630 Ω,
  off-channel leakage ≤ 38 nA at 125 °C.

### 8.2 Programming voltages for a first IHP chip (proposal)

Only 1.2 V (logic) and 3.3 V (thick oxide) are generated on chip. The pulse amplitude (0.5 to 3.0 V), the 1.7 V word-line
level, the 0.2 V clamp reference and the forming voltage come in through pads, so they can be changed after the first
measurements. Up to 48 devices of a row can be pulsed at once, so an on-chip amplitude source would need about 36 mA; it
belongs on a second chip. The SKY130 chip follows the same principle (section 9.6).

### 8.3 Forming path up to 5 V from 3.3 V transistors

Every gate and channel voltage of every transistor must stay within 3.3 V. The design uses only the gate lengths for
which the process specification states the 3.3 V limit (NMOS 0.6 µm, PMOS 0.5 µm), and keeps 0.3 V of margin: its
protection biases are at 3.0 V. The switch from a VFORM pad to one bit line is two stacked PMOS: the upper one is switched
by a level shifter that floats between VMID = VFORM − 3.0 V and VFORM, the lower one has its gate at VMID; each PMOS sits
in its own n-well tied to its own source. Bit-line pull-down and column switch are two stacked NMOS each.

| Quantity, 45 cases (VFORM 3.6 / 4.4 / 5.0 V × 5 corners × 3 temperatures) | Result |
|---|---|
| Largest gate or channel voltage, settled | 3.001 V |
| Largest at any time while switching | 3.60 V, for at most 0.8 ns (at VFORM 5.0 V); never above 3.3 V at 3.6 and 4.4 V |
| Bit line: drop at 0.25 mA, rise to 90 % | ≤ 244 mV, ≤ 3.25 ns |
| Layout (`tcim_form`, 15 transistors, 55.2 × 26.9 µm) | DRC clean, LVS match, planted error caught |

**The array limits forming.** With one source line per column, that line must sit at VMID to keep the unselected select
transistors off, and the selected cell receives only 3.00 V at VFORM 5.0 V; with one source line per row it receives the
full 5.00 V. Forming above about 3 V on IHP therefore needs the source lines along the rows, or forming from pads or on
the wafer. Questions to IHP.

### 8.4 What is drawn for IHP

| Block | State |
|---|---|
| Array transistors, 72 × 24 2T2R | drawn by script; clean with the PDK's full KLayout deck; 1.085 µm row pitch, 4.75 µm device pitch, tile about 0.0206 mm². The ReRAM element is a placeholder |
| Level shifter, word-line driver, driver column at the array pitch, forming switch | drawn; DRC clean, LVS match; the driver column extracted and re-simulated |
| Logic block | placed and routed; timing closed at 10 ns at every corner |

---

## 9. The SKY130 test chip

### 9.1 Why SKY130, and what the chip is for

SkyWater's ReRAM layer, design rules and device model are public (`sky130_fd_pr_reram`), so a complete chip with real
ReRAM can be drawn and checked with open tools; on IHP the ReRAM layers are in a kit that has not been available. The chip
targets ChipFoundry's analog harness, Caravan (`user_analog_project_wrapper`): a user area of 2.92 × 3.52 mm, 27
general-purpose pads with digital input and output buffers, 11 direct analog pads, a 1.8 V supply (vccd1) and a 3.3 V
supply (vdda1). Process variant: sky130B, the one with the ReRAM layer.

The chip has two purposes: to measure the devices (how they form, set, reset and spread, and how they hold their state),
and to run the complete TCIM0 tile on them, programming and products, from a host through the serial port.

### 9.2 SkyWater's ReRAM and its operating conditions

The cell is a TiN / HfO2 / Ti / TiN stack between metal1 and metal2, drawn as a 0.26 × 0.26 µm square. SkyWater's
technology notes give:

| Operation | Word line | Bit line | Source line | Pulse | Published yield |
|---|---|---|---|---|---|
| Form | 1.4–2.5 V (0.1 V steps) | 2.4–3.3 V (0.1 V steps) | 0 | 1 µs | 92.73 % (1T1R) |
| Set | 1.7 V | 2.4 V | 0 | 1 µs | 97.45 % |
| Reset | 2.5–3.0 V | 0 | 2.4–3.0 V | 1 µs | 90.83 % at 2.5 / 2.6 V; 99.41 % stepped |
| States | pristine < 0.1 µS; after form or set 30–120 µS; after reset about 4.5 µS | | | | |

Every level is at most 3.3 V. All array-side circuits therefore use SKY130's 5 V transistors (`nfet_g5v0d10v5`,
`pfet_g5v0d10v5`, L ≥ 0.5 µm) on the 3.3 V supply; logic and sensing use the 1.8 V core transistors.

### 9.3 Architecture

```
 13 GPIO inputs, 9 outputs (1.8 V)                            analog pads (no harness ESD on the ones used)
       │                                                      VPRG  VWLP  VWLR  VREF  IBIAS    TC_WL TC_BLP TC_BLN TC_SL
       ▼                                                        │     │     │     │     │         │     │      │     │
 ┌──────────────────────────────┐  wl_on[71:0]   ┌──────────────────────────────────────────┐   ┌──────────────────┐
 │ digital block (550 × 343 µm) │  blp/bln_prg   │ analog macro (1437 × 1392 µm)            │   │ test cell: one   │
 │  serial port + TCIM0 core    │  [23:0] each   │  72 row slices: level shifter + WL driver│   │ 2T2R cell, its   │
 │  (registers, sequencers)     │ ─────────────▶ │  48 bit-line slices: level shifter,      │   │ four lines on    │
 │  array controller tcim_actl  │  bl_sen, flt,  │    ground NOR, driver, sense amplifier   │   │ pads             │
 │  tie cells for pad controls  │  sl_prg,       │  24 source-line drivers                  │   └──────────────────┘
 │                              │  wl_prog,      │  shared controls + reference (ctrlglob)  │
 │                              │  ref_sel[2:0]  │  array 72 × 24 2T2R, 3,456 ReRAM devices │
 │                              │ ◀───────────── │                                          │
 └──────────────────────────────┘  sa_p/sa_n[23:0]└──────────────────────────────────────────┘
```

The logic is the verified TCIM0 core unchanged. Between the core's request interface (one row, one operation, masks)
and the macro sits a new block, the array controller, which turns each request into timed line controls. The macro has
175 1.8 V control and sense pins; it level-shifts every control to 3.3 V itself. The *programming levels* (pulse rail
VPRG, word-line program rail VWLP, word-line read rail VWLR) and the read reference (VREF 0.2 V, bias current IBIAS) come
from the test board through analog pads, so the scheme can be changed after the first measurements. The chip tells the
board which pulse comes next through three outputs: pulse kind `pk` (0 set, 1 reset), amplitude code `pamp` (0–20), and a
strobe `pstb` that is high while a programming word line is on.

### 9.4 The array controller (`rtl/chip/tcim_actl.sv`)

**Line drive.** In the macro each bit line is connected to the pulse rail VPRG when its `prg` control is high, to its
sense amplifier when the shared `bl_sen` is high, and to ground when NOR(prg, bl_sen, flt) is high; all 24 source lines
go to VPRG when `sl_prg` is high and to ground when NOR(sl_prg, flt). The NOR gates sit in the 3.3 V domain next to each
driver. This is what makes the drive safe: a line is grounded by default, every line is always either driven or briefly
floating, and the controller needs only one wire per bit line plus four shared ones.

**Break before make.** Level shifters have different delays for rising and falling inputs (section 9.5). If a bit line
were switched directly from ground to VPRG, the ground switch might still be on when the rail switch closes, and the
rail would be shorted to ground through the two switches. The controller therefore raises `flt` one cycle before any
`prg`, `bl_sen` or `sl_prg` changes and drops it one cycle after; while `flt` is high every ground switch is off, so
the line passes through a floating interval in each direction, whatever the skew between the level shifters.

**Sequence of one request.** IDLE (all lines grounded) → BRK (flt = 1) → MAKE (modes, word-line rail and reference
selected) → SETL (flt = 0; lines settle for T_SETTLE) → WLON (one word line on for T_SENSE or T_PULSE; reads sample in
the last cycle) → WLOFF (second sampling flip-flop) → REL (flt = 1) → BRK2 (modes released) → GND (flt = 0, lines
grounded, acknowledge) → IDLE. Every macro-side output comes directly from a flip-flop, so no logic glitch reaches the
level shifters.

| Operation | Bit lines of masked devices | Other bit lines | Source lines | Word-line rail | Reference |
|---|---|---|---|---|---|
| READ / VFY_SET / VFY_RESET | sense amplifier | sense amplifier | ground | VWLR | read / set target / reset target |
| PULSE_SET | VPRG | ground | ground | VWLP | none |
| PULSE_RST | ground | VPRG | VPRG | VWLP | none |
| SUM (analog mode) | not on this chip: answered after one cycle with zero counts | | | | |

In a reset pulse the source line of a column is at VPRG; a device of that column that must *not* change keeps its bit
line at VPRG too, so it sees no voltage (inhibit). Times are set by static configuration pins: T_SETTLE = 2^(ts+1),
T_PULSE = 2^(tp+2), T_SENSE = 2^(tr+2) clock cycles. With a 16 MHz board clock T_PULSE = 16 cycles = 1 µs at tp = 2.

**Verification.** The full TCIM0 test bench runs on the chip's logic (`make rtl-chip`) in three timing configurations
(ts, tp, tr) = (0, 0, 0), (1, 1, 0) and (3, 2, 1): 76,823, 76,973 and 79,228 checks, 0 failures. The same test bench on
Verilator gives the identical 76,973 checks for the middle configuration (`make rtl-chip-verilator`). In this build the array is replaced by a *line-level model of the macro* that derives each line's state from
prg / bl_sen / flt exactly as the macro does and checks every clock cycle: no rail shorted to ground; no sense input
driven by a driver; at most one word line; no floating line under a word line; no line floating for more than two
cycles; no direct switch between two driven modes; prg / bl_sen / sl_prg change only while flt has been high for two
cycles; lines and rails stable while a word line is on; read and program set-ups; exact T_SENSE and T_PULSE; lines
settled for T_SETTLE; strobe and pulse kind correct. Sense outputs are random for the first two cycles of a read. Each
word-line pulse is turned back into an array operation on the behavioural array, so the core's programming and products
are checked end to end through the controller.

The controller's mutation test (`tb/chip/mutation_chip.py`) injects 26 faults. On 11 October one fault survived: a reset
verify against the *read* reference instead of the reset target. The behavioural array only ever placed reset devices
far below both references, so the two were indistinguishable. A directed test was added (a device left at 15 µS-equivalent,
between the reset target and the read reference, must fail the reset verify and be pulsed); the fault is now detected,
and all 26 faults are detected.

### 9.5 Analog cells

All cells are written once as a SPICE netlist (`chip/sky130/sim/periph.spice`), simulated with the open_pdks sky130B
models in ngspice (`chip/sky130/sim/periph_sim.py`), and drawn from the same netlist (section 9.7).

| Cell | Circuit | Purpose |
|---|---|---|
| `ls_lv2hv` level shifter | 1.8 V inverter; two 5 V NMOS (W 4 µm) pull down cross-coupled 5 V PMOS loads (W 0.42 / L 1 µm); 3.3 V output buffers | 1.8 V control → 3.3 V. The 5 V NMOS see only 1.8 V on their gates, so they are made wide and the PMOS weak and long |
| `wld` word-line driver | transmission gate (NMOS 2 / PMOS 4 µm) from the shared rail to the word line, NMOS pull-down | connects the selected row to VWLR (read) or VWLP (program); unselected rows are grounded |
| `bld` bit-line driver | transmission gate to VPRG (4 / 8 µm), NMOS to ground (2 µm), NMOS column switch to the sense amplifier (2 µm) | the three modes of a bit line |
| `sld` source-line driver | transmission gate to VPRG (8 / 16 µm), NMOS to ground (4 µm) | carries both devices of a column in a reset |
| `nor3hv`, `nor2hv` | 5 V NOR gates | ground switch of each bit line, of the source lines |
| `sa` sense amplifier | PMOS mirror (W 4 / L 4 µm) from vbp into the sense node, clamp NMOS (2 / 1 µm) gated by vcl, inverter | compares the cell conductance with the reference |
| `refbias` reference | NMOS diode from the board's bias current (about 0.8 µA); switched legs of 2, 3 and 6 units (reset target, read, set target) into a PMOS diode whose gate vbp feeds every sense amplifier; a replica clamp on VREF sets vcl | one reference generator for 48 sense amplifiers, three selectable levels |
| `rowslice`, `blslice`, `ctrlglob` | assemblies: level shifter + word-line driver; level shifter + NOR + driver + sense amplifier; four level shifters, source-line NOR, word-line rail switch, reference | the repeated units of the macro |

The three reference levels are 2, 3 and 6 units of about 0.8 µA at 0.2 V, i.e. 8, 12 and 24 µS nominal: the reset
target sits above SkyWater's 4.5 µS reset state, the read reference near the geometric mean of the states, and the set
target below the lowest set state (30 µS).

| Check (5 corners × −40 / 27 / 125 °C × 1.62 / 1.80 / 1.98 V unless stated) | Result |
|---|---|
| A. Level shifter (45 cases, 3.0 / 3.3 / 3.6 V high side) | rise ≤ 0.335 ns, fall ≤ 1.626 ns, static current ≤ 21.7 nA |
| B. Word-line driver into the drawn poly word line (8.3 kΩ, 48 gates), rails 1.4–3.3 V (75 cases) | far end at 90 % ≤ 1.53 ns, back to 10 % ≤ 1.71 ns |
| C. Line voltages through the drivers with a 4.5 or 120 µS cell, set / reset / form / inhibit (150 cases) | set (word line 1.7 V, VPRG 2.4 V): bit line ≥ 2.21 V, source line ≤ 0.06 V; reset (2.5 / 2.6 V and 3.0 / 3.0 V): source line ≥ 2.52 and ≥ 2.92 V, bit line ≤ 0.15 V; form (2.5 / 3.3 V): bit line ≥ 3.06 V, at most 0.24 mA from the rail; inhibited device 0.0 V |
| D. Trip points, 45 cases each | reset target 7.93–8.37 µS, read 11.95–12.81 µS, set target 23.71–27.36 µS; no overlap |
| D. Mismatch Monte Carlo, 200 runs each, tt 27 °C | reset target 8.20 ± 0.46 µS, read 12.31 ± 0.71 µS, set target 25.62 ± 1.22 µS (mean ± σ) |
| D. Sense transient (bit line 60 fF, 5 corner/temperature pairs) | read: a 30 µS cell gives 1 within 5.57 ns, a 4.5 µS cell gives 0; verify (a 10 µS cell against the reset target, a 30 µS cell against the set target): decided within 36.4 ns (the shortest T_SENSE is 4 clock cycles) |
| E. One full controller sequence through the drawn slice, set / reset / read, with and without break-before-make (16 MHz) | set: bit line 2.31 V at VPRG 2.4 V; reset: source line 2.37 V; read: bit line 0.085 V, output correct; with break-before-make the switching charge drawn from the rail falls from 280 to 262 fC (set) and 356 to 280 fC (reset), the peak from 799 to 744 µA and 1,004 to 685 µA |

The read margins: the read reference at its lowest Monte Carlo value (10.4 µS) is 5.9 µS above SkyWater's reset state;
at its highest (14.5 µS) it is 15.5 µS below the lowest set state. The verify references lie inside those bounds with
their own spreads (reset 7.0–9.5 µS, set 22.2–29.8 µS; with the full library, below, the set target reaches down to
21.5 µS), so a device that passes verify is read correctly by every sense amplifier of the population simulated.

**Fast simulation, checked against the full library.** The SKY130 transistor library loads every device type of the
process, about two minutes per ngspice run. The simulations load a reduced copy with only the four transistor types used,
from the same files in the same order (`chip/sky130/sim/spice.py`). For every deterministic case checked the two give
identical results. With mismatch on, the same seed gives a different sample, because the full library evaluates many
more random expressions before reaching ours. The distributions were therefore compared (`chip/sky130/sim/mc_libcheck.py`,
48 runs per reference with the full library against the 200 with the reduced one):

| Reference | Full library, mean ± σ (range) | Reduced library, mean ± σ | Means (Welch test) | σ ratio full / reduced |
|---|---|---|---|---|
| reset target | 8.17 ± 0.44 µS (7.27–8.98) | 8.20 ± 0.46 µS | agree, p = 0.67 | 0.95 |
| read | 12.45 ± 0.64 µS (11.10–14.09) | 12.31 ± 0.71 µS | agree, p = 0.20 | 0.90 |
| set target | 25.26 ± 1.51 µS (21.55–28.78) | 25.62 ± 1.22 µS | agree, p = 0.13 | **1.24** |

The means agree in all three, and the spreads of the reset target and the read reference agree. The set target's spread
is 1.24 times larger with the full library; with 48 samples that ratio is only known to lie between about 1.0 and 1.6,
so the true spread of the set target may be up to about 1.6 times the reduced library's. Both consequences were checked. The
highest set-target trip seen with the full library (28.78 µS) is below the 29.84 µS used as the target of the worst-case
programming run (section 9.6), so programming covers it. The lowest (21.55 µS) is still 7.1 µS above the highest read
reference seen with either library (14.46 µS), so a device that passes the set verify is still read as set.

### 9.6 Programming through the drawn drivers (`chip/sky130/sim/macro_sim.py`)

Programming is simulated cell by cell through the drawn drivers (bit-line driver, select transistor W 1 µm, source-line
driver) with the device model at SkyWater's parameters and the fitted reset rate. A 1 µs pulse with the model's
exponential kinetics is stiff: the transient solver does not converge for most pulses. The simulation is therefore
*quasi-static*: for each gap the circuit's DC solution gives the cell voltage, and the gap is integrated over the pulse
with the model's rate equation (`reram_stanford.gap_rate`). Where the transient does converge the two agree: 23.56 vs
23.49 µS, 62.08 vs 61.86 µS, 73.68 vs 73.42 µS (quasi-static vs transient). The targets are the highest set-verify trip
(27.36 µS) and the lowest reset-verify trip (7.93 µS) of section 9.5, so a cell that reaches them passes verify with every
corner of the sense amplifier.

| Pulse | Board map (proposal) | Result (tt 27 °C, ss −40 °C, ff 125 °C) |
|---|---|---|
| Set, SkyWater's word line 1.7 V | VPRG 1.4 V + 0.1 V × code | tt: target in 19 pulses; ff: 13; **ss −40 °C: fails** (21.75 µS after 20 pulses): the 1 µm select transistor limits the current |
| **Set, word line 2.0 V** | VPRG 1.4 V + 0.1 V × code | target in 7–8 pulses at all three; final 28.3–29.8 µS |
| Set, word line 2.5 V | VPRG 1.4 V + 0.1 V × code | target in 5 pulses; final 29.6–33.4 µS |
| **Reset** | VWLP 2.5 V + 0.1 V × code (codes 0–5), then 3.0 V; VPRG 2.4 V (codes 0–5), then 2.5 V + 0.1 V × (code − 6) | cell with the fitted rate: 1–2 pulses; 1, 2, 3 decades slower: 1–4, 3–5, 5–7 pulses; 4 decades slower: 7–9 pulses at tt and ff, **fails at ss −40 °C** |
| Disturb | unselected devices of the row during each pulse | no change (0.0 µS) in any case |

The proposed map is therefore set at 2.0 V on the word line and the stepped reset above. Forming is done by the board
firmware as ordinary program commands with a forming map (higher word-line rail), first all +1, then all −1, then the
target weights; the model has no pristine state, so forming is not simulated.

**Wiring of the drawn macro** (`layout/sky130/periph/macro_rc.py`). The circuit simulations above assumed a short bit
line (75 Ω, 60 fF) and the bare poly word line. In the drawn macro every line also runs up to 1.4 mm through metal2,
metal3 and metal4 to its slice. The script rebuilds the drawn shapes, joins them into nets (shapes of one layer that
touch, and shapes joined by a via), and sums the squares of every rectangle of a line times its layer's sheet resistance
(poly 48.2, metal1/2 0.125, metal3/4 0.047, metal5 0.029 Ω/□) plus its vias. Counting every rectangle in series over-states
the resistance, so the values are upper bounds. The capacitance comes from Magic's extraction of the whole macro
(capacitance to substrate and between nets), split into the array's share and the routing's.

| Line | Routing resistance (min–max) | Worst capacitance |
|---|---|---|
| bit lines BL+ / BL− (48) | 86–520 Ω (+ 75 Ω in the array: worst 595 Ω) | 172 fF routing + 22.8 fF array (BLP23), against 60 fF assumed |
| source lines (24) | 125–402 Ω (+ 40 Ω in the array: worst 442 Ω) | |
| word lines (72), driver to array | 384–815 Ω (+ 8.3 kΩ poly in the array) | 103 fF routing + 11.1 fF array (WL42) |

With the worst line of each kind (`chip/sky130/sim/rc_sim.py`, 5 corner / temperature pairs):
- **Read and verify**: every decision is still correct (a 30 µS cell reads 1, a 4.5 µS cell 0; verify of 30 / 20 µS
  against the set target and 4.5 / 10 µS against the reset target). The output settles within 13.68 ns for a read
  (5.57 ns before) and 25.42 ns for a verify, both far inside the shortest sense window (4 clock cycles, 100 ns at
  40 MHz).
- **Word line**: the far end reaches 90 % within 2.79 ns and falls to 10 % within 3.52 ns (1.53 / 1.71 ns before).
- **Programming** (`macro_sim.py` with the worst bit-line and source-line resistance in series, and the set target
  raised to 29.84 µS, the highest set-verify trip seen under mismatch, instead of the 27.36 µS corner value): set at a
  2.0 V word line still reaches the target at all three corners, in 9–11 pulses instead of 7–8; with SkyWater's 1.7 V it
  now fails at tt 27 °C as well as at ss −40 °C. Reset: up to three decades slower than the fit, at most 8 pulses; four
  decades slower fails at ss −40 °C, as before. No unselected device changes (`results/sky130_chip/macro_sim_worst.json`).

The proposed board map (set at 2.0 V on the word line, stepped reset) therefore holds with the drawn wiring and the
widest reference spread.

### 9.7 Physical design

All layout is generated by script with Magic and the open_pdks sky130B technology, and checked with Magic's full design
rules (`drc style drc(full)`) and netgen LVS.

**Cells** (`layout/sky130/periph/gen.py`). Each transistor is drawn by the PDK's own device generator
(`sky130::<device>_draw`), then placed in a row and wired by the script: drain and source jog from metal1 through via1
to metal2 stubs and up to metal3 port tracks; gates come out on poly pads; every cell has a guard ring with its body
contact. Same-kind devices are spaced by 0.6 µm (5 V PMOS 2.1 µm, 1.8 V PMOS 1.5 µm, for n-well rules), different kinds
by 2.6 µm. Port tracks run the full cell width on metal3; slices keep a margin on the left for metal4 straps of the shared
nets at 2.4 µm pitch.

| Cell | Size (µm) | | Cell | Size (µm) |
|---|---|---|---|---|
| level shifter | 58.1 × 23.2 | | sense amplifier | 26.9 × 17.8 |
| word-line driver | 17.9 × 15.6 | | reference | 115.8 × 24.8 |
| bit-line driver | 21.3 × 22.6 | | row slice | 85.2 × 27.6 |
| source-line driver | 33.3 × 28.6 | | bit-line slice | 152.0 × 43.6 |
| NOR3 / NOR2 | 30.6 × 16.6 / 22.1 × 20.6 | | shared-control block | 379.6 × 84.6 |

Every cell: DRC 0 with the full rules, LVS match against its netlist (assemblies against the flattened netlist), and a
planted wiring error caught by LVS (`results/sky130_chip/periph_layout.json`).

**Array** (`layout/sky130/`, revision 4.4). One 2T2R cell is 3.6 × 3.0 µm: the ReRAM element between metal1 and metal2,
the select transistor `nfet_g5v0d10v5` W 1.0 / L 0.5 µm, word line in poly along the row, BL+ / BL− on metal2 and the
source line on metal1 along the column, a substrate tie strip along every row. The 72 × 24 array is 86.4 × 216.0 µm with
6,912 devices; DRC clean hierarchical and flat; LVS match with netgen including the ReRAM devices; a planted DRC error and
a planted wiring error are both caught.

**Analog macro** (`layout/sky130/periph/macro.py`), 1,436.7 × 1,391.7 µm: the array, 72 row slices, 48 bit-line slices,
24 source-line drivers and the shared-control block. Word lines leave the array on its right edge, bit and source lines
at its bottom; each runs on its own metal3 track to a vertical metal2 track in the channel beside its stack of slices.
Every horizontal wire is metal3 (metal5 for buses) and every vertical one metal2 or metal4, each at its own coordinate,
so no two nets share a track on one layer. Shared nets (rails, reference, controls) run as metal4 straps through the
stacks up to metal5 buses. The 175 1.8 V signals leave on metal4 at the macro's bottom edge. DRC 0 (full rules), LVS
match of the whole macro against the netlist built from `periph.spice` and the array schematic, and one swapped
connection detected (`results/sky130_chip/macro_layout.json`).

**Digital block**: placed and routed with OpenROAD-flow-scripts on sky130B (section 7.3): macro-side pins on its top edge,
pad-side pins on its bottom edge, power rings on metal4 / metal5. DRC 0, timing met at every corner, 610 antenna diodes
(section 9.7 explains why so many).

**Top level** (`layout/sky130/periph/top.py`): the macro near the top of the user area facing the analog pads, the
digital block below it, the test cell near the top right. A channel joins the macro's 175 1.8 V pins to the block's top
pins (metal4 down from the macro, one metal3 track per signal, metal2 into the block); the block's 57 pad-side pins run
to the GPIO pins on the left and right edges through edge channels. Supplies: vertical metal4 trunks for ground (vssa1),
vccd1 and vdda1, joined to the harness supply pins and to the macro's buses and the block's rings. One ground, vssa1,
serves both the macro and the logic, whose substrate ties meet in the p-substrate anyway; vssd1 is not used.

*How the top level is checked.* Magic writes only the top cell; every other cell (the PDK's devices, the standard cells,
the routed block) goes into the GDS exactly as it was read (`gds readonly`). The standard cells are taken from
`layout/sky130/periph/stdcells_cf` (section 9.10), read before the routed block's GDS (`gds noduplicates`), so the copies
inside the place-and-route output are not used. For LVS the user area is extracted for connectivity only, with pins of the same name joined, as ChipFoundry's
precheck does for analog projects (`extract unique notopports`: the harness joins those pins). The reference netlist is
assembled from the macro's netlist, the routed block's Verilog netlist converted to SPICE (with the antenna diodes the
router inserted, which are physical-only cells and absent from the Verilog), the test cell and the top-level antenna
diodes. netgen compares the two with the PDK's setup; a mismatch in a device property (a transistor's length, a
resistor's size) counts as a failure.

| Check of the user area | Result |
|---|---|
| LVS (netgen) | circuits match uniquely; no cell with property errors |
| LVS with two pad inputs swapped (io_in[5] and io_in[6]) | mismatch reported |
| DRC, Magic full rules, the precheck's commands (`signoff.py`) | 0 markers (open_pdks 1e35547 tech); 0 with ChipFoundry's Magic 8.3.471 and 3e0e31d tech |
| Antenna check, Magic | 0 violations (both tech versions) |
| Antenna check of the routed block, OpenROAD | 0 violations |

*What the checks of the assembled chip found.* Each of these passed every check of its own block and appeared only when
the chip was assembled; each was fixed and the check repeated:
1. Writing every cell back out (`writeall`) re-wrote the PDK's transistor cells and changed a gate length from 0.15 to
   0.14 µm in the GDS. Now only the top cell is written.
2. The tie cell `conb_1` exists in two versions: its two polysilicon resistors are marked 0.045 µm long in older
   libraries (the place-and-route platform's copy, and open_pdks 3e0e31d, which ChipFoundry pins) and 0.5 µm in
   open_pdks 1e35547. LVS against a netlist of the other version reports a property error. The chip now carries the
   3e0e31d cell, matching ChipFoundry's netlist (section 9.10).
3. A 0.2 µm wide metal2 stub into a 0.14 µm pin of the block left a 0.04 µm notch against the block's own wire on the same
   net (rule met2.2, found by the precheck's Magic DRC). Stubs are now 0.14 µm wide inside the block.
4. Antenna rule: a gate may only see a limited metal area before the wire reaches a diffusion, or charge collected
   during plasma etching can damage its oxide. At the top level, the inputs of the block's 48 sense-output buffers and 13
   pad-input buffers, and the macro's three reference-select inputs, hung on metal3 tracks up to 1 mm long whose drivers
   join them only at metal4 or above (the sense amplifiers, the control block) or only inside the harness (the pads). Each now has a 3 × 3 µm n+ diode to ground on its track (61 + 3), and the sense
   outputs take the lowest channel tracks so that their metal2 stubs stay short.
5. Earlier precheck runs also found an enclosure error of a via4 at a ground link, and pin stubs ending short of their
   pins (KLayout BEOL and pin-label checks); both were fixed in the script.
6. With every standard cell from 3e0e31d, ChipFoundry's KLayout FEOL check found one npc.2 violation (nitride-poly-cut
   spacing 0.16 µm, rule 0.27 µm) where an `and2_0` abuts an `a21boi_0`: the 3e0e31d `and2_0` has a notch in its NPC
   shape that 1e35547 fills. The other cells therefore stay at 1e35547 (section 9.10).

*The antenna rule, two checkers.* Two tools check it with the same SkyWater limits (metal side area up to 400 times the
gate area, more when a diode is attached; via cut area up to 6 times). OpenROAD checks the routed block from its
database with the technology LEF; Magic checks the whole user area from the GDS (`layout/sky130/periph/signoff.py`). With
the block as first routed (8 antenna diodes, all from the router), OpenROAD reported 0 violations and Magic, after the
61 + 3 top-level diodes, flagged 4 gates, all inside the block. The four were located in the block and their numbers set
beside OpenROAD's for the same gate (`antenna_crosscheck.py`):

| Gate flagged by Magic (first routing) | Magic | OpenROAD, same gate |
|---|---|---|
| nand2 `_09982_`, input B | metal3: 403.6 (limit 400) | metal3 side area: 383 (limit 400) |
| o21ai `_10531_`, input A2 | "metal4 contact": 1,073 (limit 400) | via4 cut area: 4.03 (limit 6) |
| clock gate dlclkp `_12789_`, enable input | "metal4 contact": 1,073 (limit 400) | via4 cut area: 4.03 (limit 6) |
| one more gate (Magic names an o22ai, but none lies within 19 µm of its coordinates) | "metal4 contact": 419.8 (limit 400) | not located |

On the first gate the two tools agree within 5 % and put it at the limit. On the two others that could be located, Magic's
figure for the via between metal4 and metal5 is 266 times OpenROAD's via ratio, against a limit 67 times larger: about four
times stricter than the LEF rule; why was not found. (Files of this first routing: `results/sky130_chip/first_routing/`.) Rather than choose between the checkers, the block was routed again with
a second antenna repair after detailed routing (`flow/orfs/sky130hd_chip/post_drt.tcl`): a diode on every net that
OpenROAD puts above 24 % of any of its limits (a 76 % margin, enough for Magic's stricter via figure), and then a repair
at the normal limit of any net that the re-routing around the new diodes pushed over (two such nets; one of them was also
the only gate Magic still flagged, at 674 against 400 on metal2, where OpenROAD agreed with 661). A first attempt with a
40 % margin had cleared three of the four. The logic netlist is unchanged by this (diodes are physical-only cells: the
Verilog netlist is identical line for line to the first routing's), and every check of the block was repeated on the new
routing. Final state: 610 antenna diodes in the block, **0 violations with OpenROAD and 0 with Magic**.

### 9.8 Pads, supplies and protection

| Pads | Signals |
|---|---|
| GPIO inputs (1.8 V) | clk, rst_n, sck, cs_n, mosi (mprj_io 5–9); cfg_ts[2:0], cfg_tp[2:0], cfg_tr[1:0] (30–37) |
| GPIO outputs (1.8 V) | miso, irq, pstb, pk (10–13); pamp[4:0] (25–29) |
| Analog (direct) | io_analog[4] VPRG, [5] VWLP, [6] VWLR (0–3.3 V); [0] VREF 0.2 V; [1] IBIAS about 0.8 µA; [2] TC_WL, [3] TC_BLP, [7] TC_BLN, [8] TC_SL (test cell); [9], [10] unused |
| Supplies | vccd1 1.8 V, vdda1 3.3 V, vssa1 ground |

The output-enable and output controls of the GPIO pads come from tie cells inside the digital block, so no pad control is
wired straight to a supply (`tcim_chip_digital.sv`); the power-on modes are in `chip/sky130/caravan/verilog/rtl/user_defines.v`.
Pads 0 to 4 are not used: they stay in the management modes the harness gives them at power-on, and this design does not
drive their user-side controls (io_out[4:0], io_oeb[4:0]). The circuit-validity checker run by the precheck (CVC) notes
three of them as "unknown voltage" (io_out[0], io_out[1], io_oeb[0]); the precheck counts this as a soft warning and
passes, and ChipFoundry's own example project leaves them undriven in the same way. In management mode the harness takes
those pads' signals from the management core, not from the user area.

**Protection.** Caravan's direct analog pads have no ESD diodes of their own; the harness offers clamps on io_analog[4–6]
which this design does not connect. The pads used are therefore unprotected apart from the junctions of the transistors
they reach. This is a handling risk (antistatic handling, board-level protection on the test board), not a functional
one; diodes to vdda1 / vssa1 can be added in a later revision. Revision 4.8 (7 November) did not connect the harness
clamps: tying io_clamp_high[i] to its own pad puts two wrapper ports on one net, which ChipFoundry's LVS may reject, so
the question went to ChipFoundry (`docs/QUESTIONS.md`, 3a); until they answer, the test board carries the protection
(a low-leakage TVS or diode pair on every analog pad). The undriven controls of pads 0 to 4 also stay as they are (soft
CVC warning; driving them needs new pins on the routed block, and ChipFoundry's example leaves them undriven too).

### 9.9 How the chip was checked

| Level | Check | Result |
|---|---|---|
| Controller | full test bench through the controller, line-level macro model, 3 timing configurations | 76,823 / 76,973 / 79,228 checks, 0 failures; Verilator identical |
| Controller | mutation test | 26 of 26 faults detected |
| Digital block | timing after layout, 3 corners × parasitics 0.8 / 1.0 / 1.2 | setup ≥ +9.72 ns at 25 ns, hold ≥ +145 ps; shortest period 14.73 ns (slow corner) |
| Digital block | gate-level run of the routed netlist with the chip test bench (Verilator) | 76,975 checks, 0 failures; a changed gate and a stuck clock gate both detected |
| Cells | simulation over corners, temperature, supply, mismatch | section 9.5 |
| Cells | DRC (full rules), LVS, planted error | all 12 clean, matched, error caught |
| Macro | programming through the drawn drivers | section 9.6 |
| Macro | DRC (full rules), LVS of the whole macro, planted error | clean, matched, caught |
| Chip | DRC (Magic full rules), LVS of the whole user area, planted error | 0 markers; match, no property errors; swap detected |
| Chip | antenna rule: OpenROAD on the block, Magic on the user area | 0 and 0 (after the second routing, section 9.7) |
| Chip | ChipFoundry precheck (cf-precheck 1.3.7, all 14 checks, optional Magic DRC included) on the final GDS, in ChipFoundry's pinned tool and PDK versions | 14 of 14 pass (`results/sky130_chip/precheck.json`, section 9.10) |

### 9.10 ChipFoundry's precheck in ChipFoundry's own tool versions

ChipFoundry's precheck (cf-precheck, commit 6c401ed of 15 September 2026, still the latest on 12 October) pins its tools
and, like ChipFoundry's analog project template, its PDK: Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12 and open_pdks
3e0e31d (September 2025), installed through ciel from ChipFoundry's release site. The precheck of batch 16 ran with the
PC image's newer versions (Magic 8.3.685, open_pdks 1e35547 of October 2026). On 12 October the precheck was run again
in ChipFoundry's exact versions (`flow/eda/pc_batch19.sh`, `pc_batch21.sh`, `pc_batch22.sh`):

| Run | Standard cells in the GDS | Result in ChipFoundry's versions (sky130B) |
|---|---|---|
| batch 19 | all from 1e35547 | 13 of 14: LVS property error on `conb_1` (0.5 µm resistor in the layout, 0.045 µm in their netlist) |
| batch 21 | all from 3e0e31d | 13 of 14: LVS passes; KLayout FEOL reports one npc.2 at `and2_0` `_09919_` (section 9.7, item 6) |
| **batch 22** | **1e35547, except `conb_1` from 3e0e31d** | **14 of 14 pass**; Magic DRC 0 and Magic antenna check 0 with their Magic and tech files |

Compared shape by shape (after normalising polygon start points), only four cells differ in geometry between the two
libraries: `and2_0` (NPC), `and4b_2` (one poly shape), `conb_1` (the 66/15 resistor marker and NPC) and `o211a_2` (not
used); the SPICE netlists differ only in `conb_1`. The final GDS therefore takes every cell from 1e35547 and `conb_1` from
3e0e31d (`layout/sky130/periph/stdcells_cf/README.md`), and uses 3e0e31d's netlist for LVS. The final GDS
(md5 37a6fb425f7dbea11b9ea7c1be3c6352) passes DRC and the antenna checks with both versions' tools, and LVS against
3e0e31d's netlist; against 1e35547's netlist LVS reports `conb_1` the other way round (seen in batch 21 with the same
cell), as expected, and that environment is not ChipFoundry's.
CVC notes the same six soft "unexpected voltage" entries as before (section 9.8).

**sky130A.** Run with sky130A (the default of ChipFoundry's analog template), the precheck fails LVS: sky130A has no
ReRAM layer, so the 3,456 ReRAM devices are not extracted (batch 19). The chip must be processed as sky130B. ChipFoundry's
pinned PDK also has no `sky130_fd_pr_reram` library folder (its Magic and netgen setups do handle the ReRAM device); the
ReRAM cell, model and rules used here are those of `sky130_fd_pr_reram` v2.0.3 in open_pdks 1e35547. Both points are
questions for ChipFoundry (section 14).

---

## 10. FPGA demonstration

TCIM0's logic runs on a Sipeed Tang Nano 9K (Gowin GW1NR-9) with an **emulated** array: a block in the FPGA answers the
array requests the way the analog macro would, with device-to-device and pulse-to-pulse variability taken from the
programming Monte Carlo and IHP's published distributions. It is not a model of silicon; it shows the logic, the serial
protocol and the programming loop working end to end at speed against a misbehaving array. A host program on the PC
programs a random 72 × 24 matrix, reads it back, and runs 100 random products in each mode against exact arithmetic.

| Run | Weights wrong after programming | Digital products exact | Largest analog error |
|---|---|---|---|
| Board, published spread | 0 of 1,728 | 100 of 100 | 1 |
| Board, twice the spread | 378 | 0 of 100 | 11 |
| Board, three times the spread | 624 | 0 of 100 | 14 |
| Simulation, published spread | 0 | 100 of 100 | 2 |

With too much spread the sequencer raises its error flag for the rows it cannot program instead of computing silently
with wrong weights, as designed. The gate-level simulation of the FPGA netlist gives numbers identical to the RTL
simulation.

**What the board found.** The first bitstream computed every negative analog sum wrongly (errors up to 364, full scale),
although every simulation passed. The emulator used the FPGA's hard multiplier with signed operands; the gate-level model
of that cell, written from the documentation, agreed with the RTL, and the board did not. The emulator now uses unsigned
products only, and the build fails if a signed multiplier appears. TCIM0 itself was not affected. The lesson applies to
the whole project: a gate-level run is only as good as its cell models.

**Evidence.** The board runs are stored as summaries (`results/fpga/board_bank0/1/2.json`), directed cases with the full
weight matrix (`board_debug.json`), the first bitstream's failure (`board_v1_signed_mult_*.json`) and the bitstream itself
(`rtl/fpga/build/tcim_fpga.fs`, SHA-256 daecc0b3…a7ea, re-hashed on 12 October: identical). This is engineering evidence,
not publication-grade proof: the random runs kept counts rather than the individual products, there is no byte-level
record of the serial line, no record identifying the board or the load, and no photo or video. Since 12 October the host
records every byte with times and hashes (`tools/fpga_host.py --transcript`), and `tools/fpga_verify.py` rebuilds every
result from those bytes alone; both were checked on the simulation model, including a planted altered byte that the
checker caught (`results/fpga/transcript_sim_check.json`). The protocol for a recorded re-run on the board is in
`docs/FPGA_EVIDENCE.md`.

---

## 11. Fabrication readiness

### 11.1 SkyWater SKY130 through ChipFoundry (the first chip)

**Done on the design side.** The project folder `chip/sky130/caravan` holds what ChipFoundry's submission reads: the
GDS of the user area (md5 37a6fb425f7dbea11b9ea7c1be3c6352), the LVS reference netlist, the LVS configuration and the
power-on modes of the GPIO pads. ChipFoundry's own precheck (cf-precheck 1.3.7, commit 6c401ed, the latest on 12 October
2026) passes all 14 of its checks on exactly that GDS, run in ChipFoundry's pinned tool and PDK versions (section 9.10).
Every simulation and check that can be run before silicon has been run on the final design (section 12); no further PC
runs are needed unless ChipFoundry asks for a change.

**What ChipFoundry must answer** (none of it can be settled from the design files; read on their pages on 12 October 2026):

1. **Whether ReRAM is accepted on a shuttle, which one, price and dates.** Their ReRAM page ("ReRam with ChipCreate",
   chipfoundry.io/reram) offers ReRAM on "ChipCreate MPW shuttles" and still names a "November 2025 ChipCreate Shuttle";
   it gives no price. Their FAQ says: "chipIgnite does not initially support ReRam. Future support consideration will
   depend on customer demand." For scale only: the standard chipIgnite run costs $14,950 per tapeout (100 QFN-packaged
   parts or bare die); the next listed one, CI2612, has commitment 4 November 2026, tape-out 7 December 2026 and delivery
   25 May 2027. None of this is stated for ReRAM.
2. **That the chip is processed as sky130B** (the only variant with the ReRAM layer; with sky130A their LVS fails).
3. **Which PDK and ReRAM library they sign off with**: their pinned open_pdks 3e0e31d has no `sky130_fd_pr_reram` library
   folder; this design uses `sky130_fd_pr_reram` v2.0.3 from open_pdks 1e35547.
4. The transistor width and pass criteria of the test structure behind SkyWater's yield table (section 3.3).

**Then:**

5. **Submit the project folder** (`chip/sky130/caravan`) through ChipFoundry's platform: they run the precheck again at
   submission and place the user area into the Caravan harness.
6. In parallel, design the **test board**: the five analog levels (VPRG, VWLP, VWLR from a DAC through buffers able to
   source a few mA; VREF 0.2 V; IBIAS about 0.8 µA), a microcontroller or FPGA for the serial port that maps (pk, pamp) to
   the levels during each pulse (section 9.6), a source-measure unit on the four test-cell pads, and antistatic handling
   (section 9.8).

### 11.2 IHP SG13G2 with MEMRES

Cannot be completed from here. The ReRAM element's layers, design rules, Verilog-A model and sign-off flow are in IHP's
MEMRES kit, which has not been available. Before an IHP tape-out: the kit; re-running the device-dependent studies with
IHP's model; the answers on the 0.45 µm gate limit and on forming; full-chip assembly with fill.

---

## 12. Validation summary (re-run on 11 and 12 October 2026)

Every row was produced again from the scripts on 11 or 12 October 2026, after the last change to the design file it
checks. "Planted error" means the check was also run with a deliberate fault and reported it; "—" means the check has no
such run. The device-level studies of sections 3 to 6 and 8 (IHP) did not change in revision 4.5; their files are kept in
`results/rev44` and earlier and are checked by `make test` against the numbers quoted.

| Area | Check | How (command or script) | Result | Planted error |
|---|---|---|---|---|
| Device model | three implementations agree; PDK reference tests | `make check-model pdk-check` | within 0.26 mV, 0.5 pm, 0.11 %, 1.0 %; 26 of 26 PDK tests identical | — |
| TCIM0 logic | self-checking test bench, CXXRTL, both trit codes | `make rtl rtl-pnx` | 82,554 checks, 0 failures, each code | — |
| TCIM0 logic | the same on Verilator | `make rtl-verilator` | 82,554 checks, 0 failures, each code | — |
| TCIM0 logic | mutation test | `make mutation mutation-pnx` (PC, `pc_batch12.sh`) | 75 of 75 and 81 of 81 faults detected | the method itself |
| TCIM0 logic | formal proofs: serial port, safety (both codes), progress | `make formal` (PC, `pc_batch14.sh`, `pc_batch18.sh`) | serial port, safety (both codes), progress: all proven | 9 of 9 injected faults make a proof fail |
| TCIM0 logic | lint; equivalence proofs | `make lint equiv` | 0 warnings; table = definition (both codes); place-and-route source = RTL (1,697 points) | — |
| TCIM0 logic | synthesis and timing before layout | `make synth sta` | re-run; every quoted number unchanged | — |
| Chip logic | test bench through the controller, 3 timing configurations | `make rtl-chip` | 76,823 / 76,973 / 79,228 checks, 0 failures | — |
| Chip logic | the same on Verilator | `make rtl-chip-verilator` | 76,973 checks, 0 failures | — |
| Chip logic | mutation test of the controller | `tb/chip/mutation_chip.py` | 26 of 26 detected | the method itself |
| Chip logic | lint; place-and-route source = RTL | `make equiv-chip` | 0 warnings; 1,954 of 1,954 points proven | — |
| Digital block | place and route, DRC, the flow's equivalence check | PC, `pc_batch17.sh` | 9,638 logic cells + 610 antenna diodes; DRC 0; netlist equivalent to synthesis | — |
| Digital block | timing after layout, 3 corners × parasitics 0.8 / 1.0 / 1.2 at 25 ns | `post_corners.sh`, `min_period.py` | setup ≥ +9.72 ns, hold ≥ +145 ps; shortest period 14.73 / 15.31 ns at the slow corner | — |
| Digital block | gate-level run of the routed netlist (Verilator) | `gls_chip.sh` | 76,975 checks, 0 failures | a changed gate and a stuck clock gate both detected |
| Digital block | antenna rule, OpenROAD | PC, `pc_batch17.sh` | 0 violations | — |
| Analog cells | 12 cells: corners, temperature, supply, mismatch | `periph_sim.py` | section 9.5 | — |
| Analog cells | full vs reduced transistor library under mismatch | `mc_libcheck.py` | means agree; set-target σ 1.24× (section 9.5) | — |
| Analog cells | DRC (full rules), LVS | `gen.py` | 12 of 12 clean and matched | wiring error caught in each |
| Analog macro | DRC (full rules), LVS of the whole macro | `macro.py` | clean, matched | swapped connection caught |
| Analog macro | programming through the drawn drivers, nominal and worst wiring | `macro_sim.py`, `macro_rc.py`, `rc_sim.py` | section 9.6 | — |
| Chip | LVS of the whole user area | `top.py` | match, no property errors | pad swap caught |
| Chip | DRC, Magic full rules (the precheck's commands); antenna, Magic | `make signoff`; with ChipFoundry's Magic and tech in `pc_batch22.sh` | DRC 0 markers; antenna 0 violations; the same with ChipFoundry's versions | the GDS of 11 October reproduces the precheck's 3 met2.2 markers |
| Chip | ChipFoundry precheck, all 14 checks, on the final GDS, in ChipFoundry's pinned tool and PDK versions | PC, `flow/eda/pc_batch22.sh` | 14 of 14 pass on GDS md5 37a6fb42…; CVC notes 3 undriven controls of unused pads (soft) | batches 19 and 21 each failed one check (section 9.10) |
| Claims | every number quoted in the roadmap and in this report's chip section against `results/`; second-method re-derivations | `make test` | 508 numbers checked, 0 stale; 9 of 9 re-derivations agree | — |
| FPGA | simulation, gate level, board netlist | `tb/fpga/run_fpga_checks.sh` | published spread: 0 wrong weights, 100 of 100 products exact; gate level identical to RTL; no signed multiplier | signed multiplier check |

**Fresh re-run on a clean copy (12 October 2026, afternoon).** To check that the stored results are reproducible, a copy of
the repository was taken and twelve suites were run again from scratch, one after the other: `make test`, `make lint`,
`make equiv`, `make equiv-chip`, `make rtl`, `make rtl-pnx`, `make rtl-verilator`, `make rtl-chip`, `make rtl-chip-verilator`,
`tb/chip/mutation_chip.py`, `tb/fpga/run_fpga_checks.sh` and `make check-model` (about two hours). All twelve passed with the
numbers in the table above (508 numbers, 0 stale; 82,554 checks per code and simulator; 76,823 / 76,973 / 79,228 chip checks;
26 of 26 controller faults, each caught by the same first failure as before; 0 / 214 / 677 wrong weights in the FPGA
simulation; the three model solvers within 0.26 mV, 0.5 pm, 0.11 % and 1.02 %). Of the result files the suites rewrote, 21 are
byte for byte identical to the stored ones and 6 differ only in run times. The controller's fault run was done in two
parts (faults 0 to 22, then 23 to 25) because the background job reached its time limit. Not part of this re-run: the
formal proofs, the core's fault campaign, the gate-level runs, the circuit simulations and place and route (rows above).
Logs, exit codes and the file comparison: `results/regress_20261012/`.

---

## 13. Limits: what cannot be made certain before silicon

| Kind | Can it be made certain before silicon? | State |
|---|---|---|
| Logic | Yes: exact reference, two simulators, fault injection, formal proofs, checks after layout | done, for TCIM0 and the chip's controller |
| Circuit margins | Yes, against a stated range of device behaviour: corners, mismatch, temperature, extracted layout | done for every SKY130 chip circuit; for IHP done for the read path, drivers, switches and the forming path |
| Physical correctness | Yes: DRC with the foundry's rules, LVS of every level, the foundry's precheck | done for SKY130 (section 9.9) |
| Device behaviour | No. Whether the cells on the wafer fall inside the assumed range is not knowable from simulation | assumed from published data; the spread fitted to SkyWater's yields is uncertain by a factor of seven |

The design answers the last kind with margin and with structure: a two-state read that tolerates twice the published
spread, a digital mode whose correctness does not depend on analog accuracy, programming that stops on a verify read,
programming levels that come from the test board and can be changed after the first measurement, and a test cell with
direct pad access to two devices.

Known simplifications of the simulations, stated so that they are not mistaken for results:
- The device model has no forming, no retention loss, no read-current temperature dependence and no cycle-to-cycle
  randomness; forming is not simulated.
- Programming is simulated quasi-statically (checked against transient where both converge, section 9.6).
- Timing after layout on sky130B uses the platform's sky130A extraction rules, with ±20 % as a stand-in for corners.
- Analog cells were simulated from their schematics; their layouts match those schematics (LVS) and the long wires of the
  macro were assessed separately (section 9.6); the cells' own short internal wiring was not back-annotated.
- Transistor mismatch was simulated with a reduced copy of the SKY130 library. Its means agree with the full library's,
  but the set-verify reference's spread may be up to about 1.6 times the simulated one; the consequences were checked
  (section 9.5).
- The gate-level run of the chip's routed logic uses Verilator; CXXRTL, used for the other gate-level runs, did not run
  this flattened netlist correctly, and the cause was not found (section 7.3).
- The antenna rule was checked by two tools that disagree on one via figure by a factor of about four; the logic block
  was routed again until both pass, rather than deciding which is right (section 9.7).
- The user-side controls of the five unused pads (0 to 4) are not driven; the precheck's CVC notes this as a soft
  warning (section 9.8).

---

## 14. Open questions to people outside the project

Drafted in `docs/QUESTIONS.md`, not yet sent.

- **ChipFoundry**: ReRAM on the next shuttle (price, dates, user area, parts); whether the open `sky130_fd_pr_reram`
  cells, rules and model (v2.0.3) are the sign-off set, and with which PDK version (their pinned PDK 3e0e31d, enabled for
  sky130B with ciel's default libraries, includes `sky130_fd_pr_reram` at commit d6d2a3c; corrected on 6 November); that the chip is processed as sky130B; the test structure's transistor width and
  pass criteria behind SkyWater's yield table (they decide the spread to within the factor of seven of section 3.3).
- **IHP**: the MEMRES kit (how to obtain it, layers, rules, model); recommended forming, set and reset voltages; whether
  a 0.45 µm thick-oxide NMOS may carry 3.3 V on its gate; whether short excursions above 3.3 V are allowed while forming;
  measured statistics; access and 2027 dates.
- **REBEL-6 maintainers at USN**: slot 11 and interrupt 7; the wire code of a trit; access to the current executor with
  TMAC.T and memory-mapped devices; encoding space for an extension later.

---

## 15. Hardware security (revisions 4.6 and 4.7, 4–7 November 2026)

**Why.** The document *AI Hardware Hacking: What It Is and How to Secure TCIMO & TRITONE* (@m1, 4 November 2026;
`studies/hw-security-2026-11/input_AI_Hardware_Hacking_m1.pdf`) lists attacks that recover weights or inputs from a
compute-in-memory chip (timing, power and electromagnetic side channels, fault injection, the debug port, idle-supply
impedance) and a twelve-item checklist. Each statement it makes about TCIM0 was checked against the design as built, and
each leak was measured on TCIM0's own model (`tools/tvla_tcim0.py`, `chip/sky130/sim/sa_power.py`,
`chip/sky130/sim/idle_impedance.py`). These are results about the model, not about silicon.

### 15.1 What changed

Revision 4.6 (4 November) applied the checklist:
- **Fixed-latency products.** Every product reads all 72 rows, from a start row given by a 16-bit LFSR, so its time no
  longer depends on how many inputs are zero. Zero-skipping stays available as the ZSKIP opt-in.
- **Constant activity.** Each column has a dummy accumulator. In every row read, each column updates exactly one of its
  result accumulator and its dummy accumulator. Their parity can be read in ACT (+50), which reads 0 under LOCK.
- **Constant-time programming.** Every program command runs 21 reset steps and 21 set steps (152 cycles). A step in
  which every device has already verified issues a pulse with empty masks. Stopping at verify stays available as VARPROG.
- **SEC register (+3).** It holds the ZSKIP, VARPROG and NOSHUF opt-ins and a set-only LOCK. Setting LOCK clears the
  opt-ins; LOCK hides PITER and ACT.
- **Margin check.** PCMD (0,+) checks whether any device of a row has drifted into the band near the read reference.
  MARG (+52) reports the columns that have.

An independent review of revision 4.6 (two reviewers; `studies/hw-security-2026-11/council/`) found four real gaps.
Revision 4.7 (6 November) closes them (`council/03_resolution.md`):
- **H1. The start row was not uniform.** Folding 7 LFSR bits into 0…71 made rows 0–55 twice as likely as rows 56–71
  (1,024 against 512 LFSR states per row). Revision 4.7 uses the LFSR value modulo 72, kept in its own register `lfsr_m72`.
  That gives 910 or 911 states per row, and the identity `lfsr_m72 == lfsr % 72` is proved.
- **H2. The input result passed by construction.** The first leak model counted accumulator updates. Bit flips around zero
  carry the inputs: a partial sum that crosses zero flips many bits. Revision 4.7 starts the result accumulators at a random
  offset from the LFSR (−128…127) and takes it off again with the last row.
- **H4. LOCK left the weights readable.** Under LOCK, read-back is now refused (WERR, no array access), and a margin check
  does not write PDATA.
- **H5. One upset after LOCK brought an option back.** Every use of ZSKIP, VARPROG and NOSHUF is now gated by LOCK.

### 15.2 Leakage measured on the model (Welch t, threshold 4.5; `results/security/tvla.json`)

Each case uses 150,000 traces per group, with the digital term on (0.15 µA per flipped accumulator bit). The table gives
the largest |t|; a value above 4.5 means the model leaks.

| Design | Weights | Inputs |
|---|---|---|
| As built (revision 4.5, zero-skipping) | 79.69 | 4,605.29 |
| Revision 4.6 | 19.04 | 19.55 |
| Revision 4.7 | 14.24 | 3.59 |
| Revision 4.6 logic with one-of-three cells | 6.56 | 23.41 |
| Revision 4.7 logic with one-of-three cells (next chip) | 3.13 | 2.61 |

Programming, with 20,000 traces per group: stopping at verify gives |t| 87.35 and leaks in duration too. The constant
pulse count gives 65.67. That is still a leak, because the number of devices each pulse selects depends on which devices
must change.

What the table says: revision 4.7 closes the input leak in this model. The weights still leak through the 2T2R cell,
because the sense current differs between the two stored states. Only a one-of-three cell (next chip;
`studies/hw-security-2026-11/NEXT_CHIP_SPEC.md`) brings the weights below the threshold, and only with revision 4.7's
logic. With the 4.6 logic it does not.

### 15.3 Verification of revision 4.7

| Check | Result | File |
|---|---|---|
| Test bench, both trit codes, two simulators | 97,463 checks each, 0 failures | `results/rtl_test*.log` |
| Mutation test | 115 of 115 faults detected; BSD-PNX 121 of 121 | `results/rtl_mutation*.json` |
| Formal: serial port, safety, safety (BSD-PNX), progress | all pass (PDR) | `results/formal.log` |
| Formal: `lfsr_m72 == lfsr % 72` | passes (k-induction, depth 20) | `results/formal.log` |
| Two-copy timing miter, both codes | pass | `results/security/miter_*.log` |
| Faults planted in the proofs | 28 of 28 make their proof fail | `results/formal_faults.json` |
| Netlist for place and route = RTL; chip block = chip RTL | 2,764 and 3,021 points proven, 0 unproven | `results/equiv.json`, `results/sky130_chip/equiv_chip.log` |
| Chip build with the array controller | 90,196 / 91,844 / 93,928 checks (settings 0,0,0 / 1,1,0 / 3,2,1); Verilator 91,844; 0 failures | `results/sky130_chip/rtl_chip_*.log` |
| Array controller: injected faults | 26 of 26 detected | `results/sky130_chip/mutation_chip.json` |
| Logic block placed and routed again, same die | 15,140 cells (1,123 antenna diodes), 1,377 flip-flops, 85 clock gates; utilization 73.9 %; DRC 0; final netlist equivalent | `results/sky130_chip/digital_block.json` |
| Timing after layout, 3 corners × parasitics ×0.8/×1/×1.2 | setup slack ≥ 7.59 ns, hold ≥ 68 ps at 25 ns; shortest period at the slow corner 16.62 ns (×1.2: 17.44 ns) | same |
| Routed block, gate level | 91,846 checks, 0 failures; one gate changed (xnor) and a stuck clock gate both detected | `results/sky130_chip/gls_chip_*.log` |
| Whole user area | LVS match (a planted swap is caught); Magic DRC, full rules, 0 markers; antenna 0 violations in Magic and in OpenROAD | `results/sky130_chip/top_layout.json`, `top_signoff.json` |
| ChipFoundry's precheck (cf-precheck 1.3.7, their pinned Magic 8.3.471 and PDK 3e0e31d, sky130B) | 14 of 14 on the final GDS (md5 08e7dea2…); Magic DRC 0 and antenna 0 with their Magic and tech | `results/sky130_chip/precheck.json` |

**How the runs relate to the files.** The simulations, mutation tests, equivalence proofs and place and route ran on
`rtl/tcim_core.sv` md5 d41aed6c (PC batch 27, kept as `results/rev47/tcim_core_batch27.sv`). The formal properties were
restructured after that, so PDR could close them. The present file differs only in its `ifdef FORMAL` block and in
comments (`tools/same_logic.py`, `results/rev47/same_logic.json`). The proofs ran on the present file (PC batches 28 and 28b).

Two flow fixes came out of these runs:
- **Antenna margin.** Batch 27 left one net exactly at OpenROAD's antenna limit; Magic's check of the assembled chip put it
  5 % over (ratio 420.6 against 400). `post_drt.tcl` now ends with a repair pass at a 15 % margin, and batch 28 is the
  result.
- **Depth of the lfsr proof.** At depth 3, the base case of the k-induction ended before the planted fault showed (the
  fault appears at step 3), so the fault was not caught. The depth is now 20.

Area before place and route (`results/sky130_chip/area_estimate.json`, yosys + abc on the typical library): 60,385 µm²
(revision 4.5), 82,369 µm² (4.6), 95,135 µm² (4.7), in a core of 160,609 µm².

### 15.4 Limits (stated, not solved)

- Everything above is evidence about the model. No measurement on silicon exists.
- **The LFSR is not a random source.** It is deterministic after reset, so an attacker who controls reset and the timing
  of GO can control the start row and the offset. The chip has no true random-number source.
- **Reset clears LOCK.** The board's reset line and the serial port must be trusted. Read SEC back after setting LOCK:
  a SEC write while BUSY is ignored.
- **The weights still leak through the 2T2R cell** (15.2). After the start row is realigned, the cell also leaks
  per-row sparsity (H3). The fix is the one-of-three cell on the next chip.
- **Empty pulses (H6), simulated 8 November** (`chip/sky130/sim/empty_pulse.py`, `results/security/empty_pulse.json`):
  32 transient runs of one column (empty set and reset pulses, with and without an asynchronous reset mid-pulse, tt/ss/ff,
  devices at 100 / 28 µS and 4.5 / 7.93 µS, CF PDK 3e0e31d models, ngspice 42). Transients reach 1.32 V across a
  selected-row device and 1.05 V in an unselected row (empty reset pulse, high-resistance devices, in the direction that
  moves them away from the read reference). The device model integrated over every waveform (`empty_pulse_gap.py`)
  gives, as drift toward the reference: selected row at most 1.5e-12 per program command at 27 °C, 8.2e-9 at 85 °C;
  a row written once reaches 10 % after 1.1e9 full-array writes at 27 °C, 3.3e7 for the fastest-reset cell of the fit,
  2.2e5 at 85 °C. Against a stated 10,000 writes (criterion: 10×), closed in the model, with the smallest margin at 85 °C.
  Not modelled: the device's own capacitance and non-linear I-V, junction capacitances, mixed (non-uniform) columns.
  A reset during a real pulse can leave a partial write (not simulated); break-before-make on reset is for the next chip.
- **Idle impedance.** The model is the powered, idle schematic with the device as a resistor. The package, the board and an
  unpowered chip are not modelled (H7).
- **Sense-amplifier power** is a DC model; read transients were not simulated (H8).
- **Parts of the verification are tests, not proofs.** The 21 + 21 steps are tested (every program command takes 152
  cycles), and the miter proves that the timing does not depend on the data; the step count itself is not proved. The
  LOCK gating of the options cannot be tested functionally, because without an upset it behaves exactly like the
  ungated design. Sensors, decoupling and an early-end-of-product fault primitive are specified for the next revision
  (`NEXT_CHIP_SPEC.md`), not drawn.

### 15.5 Revision 4.8 (7 November 2026): serial-port fuzzing; no change to the design

`make fuzz` (`tb/extra/spi_fuzz.cc`) sends random traffic to the serial port. The traffic mixes three kinds of frame:
frames cut short at 0 to 55 clocks with random bits, complete writes and reads to every address, and chip-select glitches.
The serial clock runs between clk/6 and clk/10. A model of X0 to X2, PDATA and PROW is read back every 64 frames, and the
status byte of every frame is checked against the register map.

| Run | Result |
|---|---|
| 200,000 frames | 0 mismatches, 0 wrong status bytes (`results/spi_fuzz.json`) |
| 1,000,000 frames | 0 mismatches, 0 wrong status bytes (`results/spi_fuzz_1M.log`) |
| Four planted faults in `tcim_spi.sv`: a cut frame writes, bit counter not cleared, error flag not latched, read launched a bit late | each makes the fuzz fail |

Revision 4.8 changes no RTL or layout, so the GDS, the precheck result and every other section 15 number stand. The ESD
clamps and the pad tie-offs were not added; section 9.8 says why.

### 15.6 Cell options: 2T2R, one-of-three, 4T4R (8 November 2026)

A Gemini summary proposes a "complementary 4T4R dual-rail cell": every trit sets exactly one low-resistance device among
four. This chip was never changed to 4T4R; it is 2T2R, and the next-chip plan is the one-of-three cell (3T3R,
`studies/hw-security-2026-11/NEXT_CHIP_SPEC.md`). With exactly one low-resistance device per trit, the fourth device is
high-resistance for every value, so the leak model treats 4T4R as one-of-three plus a device that never changes
(`tools/tvla_tcim0.py`, encoding `4T4R`; `results/security/tvla_4t4r.json`).

| Cell | Devices per weight | Array area | Sense amplifiers (24 columns) | Weights \|t\| | Inputs \|t\| |
|---|---|---|---|---|---|
| 2T2R (this chip) | 2 | 1× | 48 | 14.24 (leaks) | 3.59 |
| one-of-three (next chip) | 3 | 1.5× | 72 | 3.13 | 2.61 |
| 4T4R | 4 | 2× | 96 (72 would do: the fourth device carries no information) | 3.14 | 1.78 |

(Revision 4.7 logic, 150,000 traces per group, digital term on, pass below 4.5.) Both constant-conductance cells pass the weight test that 2T2R fails (150,000 traces, 5 µA noise, total supply
current only; a small first-order difference remains, `NEXT_CHIP_SPEC.md`); 4T4R needs a third more devices than one-of-three for no measured gain, so the
plan stays one-of-three. Neither cell changes the programming-profile leak, the deterministic LFSR or LOCK after reset.

---

## Appendix A. Tools and versions

| Tool | Version | Used for |
|---|---|---|
| Gnucap with gnucap-modelgen-verilog | tag 20260729-dev | IHP circuits with PSP103 transistors and the Verilog-A ReRAM model |
| IHP-Open-PDK | main 5e6d592 (1 Sep 2026) | IHP models, standard cells, KLayout DRC and LVS decks |
| ngspice | 46 (sandbox), 42 (PC image) | device model; all SKY130 circuits |
| open_pdks | 1e35547 | sky130A and sky130B, including sky130_fd_pr_reram |
| Magic, netgen | 8.3 revision 685 | SKY130 layout, DRC, extraction, LVS |
| Yosys with slang | 0.69+ | elaboration, CXXRTL, synthesis, equivalence proofs, FPGA synthesis |
| Verilator | 5.040 | lint, second simulator, gate-level runs |
| SymbiYosys | b1a1e98 (sandbox); the build in the PC image's OSS CAD Suite ran the proofs of 12 October | formal proofs |
| OpenSTA | 3.1.0 | timing before and after layout |
| OpenROAD-flow-scripts | image openroad/orfs:26Q4-71-g9b26ff8ff (PC) | place and route |
| cf-precheck, CVC, KLayout | 1.3.7 (commit 6c401ed); CVC from github.com/d-m-bailey/cvc (built 12 Oct 2026); KLayout 0.29.12 | ChipFoundry's precheck (batch 16) |
| ChipFoundry's pinned versions | Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, open_pdks 3e0e31d (via ciel from chipfoundry.github.io/ciel-releases) | ChipFoundry's precheck as they run it (batches 19, 21, 22); `conb_1` and the LVS netlist of the standard cells |
| nextpnr-himbaechel, gowin_pack, openFPGALoader | nextpnr 0.11.1-54; openFPGALoader 1.1.1 | FPGA demonstration |

The sandbox has two CPU cores; place and route, large Monte Carlo runs, the KLayout checks and the mutation campaigns of
earlier revisions ran on the owner's PC in Docker (32 cores).

## Appendix B. How to reproduce

```
make check-model pdk-check         # device model three ways; PDK reference tests
make rtl rtl-pnx rtl-verilator lint formal equiv   # logic
make rtl-chip rtl-chip-verilator   # the chip's logic through the line-level macro model (3 timing configurations)
make equiv-chip                    # lint of the chip RTL; place-and-route source = RTL
make mutation mutation-pnx         # fault injection, TCIM0
python3 tb/chip/mutation_chip.py   # fault injection, array controller
make synth sta                     # synthesis, timing before layout
make test                          # second-method re-derivations; every quoted number against results/
python3 chip/sky130/sim/periph_sim.py; python3 chip/sky130/sim/macro_sim.py   # SKY130 chip circuits
python3 chip/sky130/sim/mc_libcheck.py run 48 && python3 chip/sky130/sim/mc_libcheck.py stats   # full vs reduced library
cd layout/sky130/periph && python3 gen.py && python3 macro.py && python3 top.py   # chip layout, DRC, LVS
python3 macro_rc.py; python3 ../../../chip/sky130/sim/rc_sim.py               # wiring of the macro, re-simulation
make signoff; python3 layout/sky130/periph/antenna_crosscheck.py               # Magic DRC and antenna; two checkers
bash tb/fpga/run_fpga_checks.sh    # FPGA design: simulation, gate level, board netlist
```

On the PC (Docker): place and route of the chip's logic with the second antenna repair, `flow/eda/pc_batch17.bat`
(batch 7 plus `flow/orfs/sky130hd_chip/post_drt.tcl`); ChipFoundry's precheck on the project folder,
`flow/eda/pc_batch16.bat`, and in ChipFoundry's own versions `flow/eda/pc_batch22.bat`; the mutation test of TCIM0 from a pack made by `tb/mutation_remote.py gen`,
`flow/eda/pc_batch12.bat`; the formal proofs, `flow/eda/pc_batch14.bat`. Then, here: `DESIGN=tcim_chip_digital
flow/orfs/post/post_corners.sh`, `min_period.py`, `collect_chip_digital.py`, `gls_chip.sh` (with and without the `xnor`
and `icg` faults), `top.py`, `make signoff`.

## Appendix C. History of revisions

| Revision | Date | Main content |
|---|---|---|
| 3 | 6 Oct 2026 | device model, cell, tile, read path, logic in simulation |
| 4 | 6 Oct | audit of revision 3: two bugs fixed, test bench measured by fault injection |
| 4.1 | 7 Oct | timing analysis (one slow path removed), BSD-PNX code, equivalence proofs |
| 4.2 | 8–9 Oct | place and route on both processes, gate-level runs, lint, Verilator, formal proofs, faster product sequencer, array transistors drawn, first periphery |
| 4.3 | 9 Oct | clock gating, timing at every corner, reset gate in the full circuit, on-chip reference, drawn periphery |
| 4.4 | 10 Oct | model fitted to SkyWater's yields, SKY130 array with ReRAM drawn, sky130B place and route, SKY130 read path, forming path, pitch-matched driver, FPGA board |
| 4.5 | 11–12 Oct | the SKY130 test chip: array controller, periphery circuits and layout, analog macro, digital block, full chip in the Caravan harness; sign-off (precheck, antenna rule under two checkers, wiring of the macro); the precheck in ChipFoundry's own versions and the standard-cell versions it requires |
| 4.6 | 4 Nov | hardware security: fixed-latency products, dummy accumulators, constant-time programming, SEC register with LOCK, margin check (section 15) |
| 4.7 | 6–7 Nov | after an independent review: uniform start row (LFSR mod 72), random accumulator offset, LOCK gates the options and blocks read-back; logic block placed and routed again, chip rebuilt and signed off (section 15) |

## Appendix D. Glossary

- **2T2R**: two transistors and two resistive devices per stored weight.
- **LRS / HRS**: low- and high-resistance state of a ReRAM device. LRS1 to LRS3 are IHP's three published set levels.
- **Set / reset / forming**: switching to LRS, switching to HRS, and the one-time creation of the filament.
- **Pulse-and-verify**: apply a pulse, read against a verify reference, stop when the read passes, otherwise raise the
  amplitude.
- **Select transistor, word line, bit line, source line**: the transistor in series with each device; the line that turns
  a row's transistors on; the lines along a column that carry each device's current to the sense amplifier; the return
  line on the other side of the device.
- **Sense amplifier, clamp, reference, trip point**: the circuit that compares a bit-line current with a reference
  current; the transistor that holds the bit line at the read voltage; the current or conductance that separates the two
  states; the cell conductance at which the output flips.
- **Level shifter**: converts a 1.8 V logic signal into a 3.3 V one.
- **Break before make**: switching a line through a brief floating state, so that two drivers are never on together.
- **Process corner**: a model of transistors fabricated faster or slower than typical (tt, ss, ff, sf, fs).
- **Mismatch Monte Carlo**: many simulations with random differences between nominally equal transistors.
- **σ (sigma)**: standard deviation.
- **Setup / hold slack**: how much earlier than needed a signal arrives before the clock edge (setup), and how long it
  stays stable after it (hold). Positive is good.
- **Parasitics**: the resistance and capacitance of the drawn wires, extracted from the layout.
- **Place and route**: placing the standard cells of the logic and drawing their wires.
- **DRC / LVS**: design-rule check (every shape obeys the foundry's geometric rules) and layout versus schematic (the
  drawn circuit is the intended one).
- **Antenna rule**: a limit on the metal area connected to a transistor gate before the wire reaches a diffusion, to
  avoid charge damage during fabrication.
- **Gate-level run**: simulating the netlist of library cells after synthesis or layout, instead of the RTL.
- **Mutation testing**: injecting one fault at a time into the design to measure whether the tests notice.
- **Formal proof / equivalence proof**: a mathematical proof that a property holds in every reachable state, or that two
  designs compute the same function.
- **Clock gating**: switching off the clock of flip-flops that do not change, to save energy.
- **Trit, tryte, word**: a balanced-ternary digit (−1, 0, +1); 6 trits; 24 trits.
- **BSD-PNX**: the two-wire trit code used by the REBEL-6 group's tools.
- **MPW shuttle, harness, Caravan**: a fabrication run shared by many designs; the standard frame (pads, supplies,
  management processor) into which each design is placed; ChipFoundry's harness for analog designs.
- **Precheck**: the foundry service's automatic checks of a submitted design.
