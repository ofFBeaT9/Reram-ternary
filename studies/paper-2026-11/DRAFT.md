# One of Three: a one-hot ternary ReRAM cell against weight-sparsity leakage in compute-in-memory

*Draft 0.2, 8 November 2026, after an independent red-team review (`council/03_red_team.md`). Every number in this draft is read
from `results/` by `studies/paper-2026-11/make_draft.py`. All leakage results are from models of the design, built from SPICE
waveforms of the drawn sense amplifier, not from silicon. Device parameters are placeholders fitted to SkyWater's published data.*

## Abstract

Compute-in-memory (CIM) accelerators keep a neural network's weights in the memory array, so the array's supply current is a side
channel on the model. With the common 2T2R ternary encoding, a zero weight has no low-resistance (LRS) device, so a row's read current
counts its zero weights. On TCIM0, a 72 × 24 ternary ReRAM CIM tile with an open SKY130 layout, a profiled attacker recovers each
row's zero count with a correlation of 0.90 (0.97 using every window of the read). We propose a
one-of-three (3T3R) cell that holds each weight in exactly one LRS device out of three, so the number of LRS devices per row does not
depend on the weights; the same attacks then find no correlation. Row-aligned tests show what remains: each sense amplifier's own
mismatch makes the current depend on *which* device holds the LRS (|t| 26.32, threshold 4.5, 150,000 traces per group). This
residual is specific to one chip. Rotating at random, on every read, which sense amplifier reads which of the cell's three devices
brings the row-aligned test to |t| 2.70 in the model. The cell costs 1.56× the 2T2R cell area, 1.53× the
analog-macro area and 1.50× the sense-amplifier read current at one third zero weights. Every single-device flip becomes a
detectable invalid code (9 of 9, against 2 of 6 for 2T2R).

## 1. Introduction

Ternary weights (−1, 0, +1) make a multiply a sign selection, and ternary networks carry many zeros. A digital accelerator that skips
zeros leaks their positions through timing [F4, F5]. A CIM array that stores a zero as "no conducting device" leaks their number
through its read current, even when the logic does nothing data-dependent [A4, A13].

Contributions:
1. A layered leakage study of a ternary ReRAM CIM tile (array, sense amplifiers, controller, accumulators), separating what logic
   fixes (timing, accumulator switching) from what it cannot (the cell).
2. The one-of-three cell, the smallest two-state-device ternary cell with a weight-independent LRS count. It is drawn in SKY130 with its
   periphery and analog macro, and supported by the controller, test benches, a formal safety proof and fault campaigns.
3. An evaluation that separates three effects which a single fixed-versus-random test mixes: the fingerprint of one programmed
   instance, the matrix-wide zero count, and the per-row, per-position signal. A sense-amplifier rotation (proposal) removes the
   position residual in the model.

## 2. Threat model

The attacker:
- has physical access to a programmed device and measures its supply current;
- knows or chooses the inputs;
- owns a second device of the same design for profiling;
- can trigger margin checks. A margin check reads one chosen row at three references and, in revision 4.7, still runs under
  LOCK, so row-aligned reads are available.

The attacker does **not** read the tile's results. In a deployment the tile sits inside a larger network, and its results go only to
the host. With readable results, 72 chosen input vectors would give the weights directly, and no side channel would be needed. This is
model extraction through the prediction interface [Tramèr et al., USENIX Security 2016]; it holds for any accelerator whose outputs are
visible, and no on-chip mechanism prevents it.

Revision 4.7's logic had two gaps that contradicted this model. Revision 4.9 closes both in the RTL (§3; verification in
`results/rev49/summary.json`), following the read-out protection of flash microcontrollers:
- Programming ran under LOCK, so an attacker could reprogram one row with known patterns (erasing 24 weights) and calibrate
  every sense amplifier. Revision 4.9 refuses programming under LOCK (WERR, no array access).
- A reset cleared LOCK while the weights persisted. Revision 4.9 sets LOCK at reset. The only way to clear it is an erase of the whole
  array, which programs every row to weight 0 in a fixed number of pulse steps and clears LOCK only if every device verified.
- LOCK is held in three flip-flops, so a single upset cannot clear it.

## 3. The TCIM0 tile

TCIM0 is a 72 × 24 ternary tile presented to a host as a memory-mapped device. The current test chip uses 2T2R cells on SKY130
(sky130B, Caravan harness). Its layout passes ChipFoundry's shuttle precheck (14 of 14 checks),
run with ChipFoundry's pinned tool versions. The one-of-three variant is drawn and verified at block level; it is not yet assembled
into a chip.

Security features (revision 4.7, with the two additions of revision 4.9):
- fixed-latency products that read all 72 rows from an LFSR-chosen start row;
- a random result-accumulator offset, removed with the last row;
- dummy accumulators;
- fixed-length programming (21 + 21 pulse steps);
- a set-only LOCK;
- refusal of read-back under LOCK;
- (revision 4.9) LOCK set by reset and cleared only by a constant-time erase of the whole array; refusal of programming under LOCK;
  LOCK held in three flip-flops.

## 4. Leakage, layer by layer (behavioural model)

Fixed-versus-random Welch t-tests (threshold 4.5), 5.0 µA rms noise, 0.15 µA per flipped accumulator bit,
150,000 traces per group, one programmed instance (`results/security/tvla.json`).

| Layer | Before | Fix | After |
|---|---|---|---|
| Timing | zero-skipping: the duration depends on the inputs (\|t\| 580.75) | fixed latency, all 72 rows, LFSR start row | the duration is the same for every input |
| Accumulators | bit flips around zero carry the inputs: \|t\| 19.55 | revision 4.7: random offset, start row = LFSR mod 72 | 3.59 |
| Cell, 2T2R | the read current counts LRS devices: \|t\| 14.24 for the weights | none in logic | — |

The behavioural model gives each sense amplifier a constant LRS current, so it cannot see the position residual of Section 6. Its
weight test also shares the limits that Section 6 explains: one programmed instance and a random start row.

## 5. The one-of-three cell

**Code.**
- +1 = (P LRS, Z HRS, N HRS)
- 0 = (HRS, LRS, HRS)
- −1 = (HRS, HRS, LRS)

**Why three.** Take one cell of identical two-state devices with a fixed number k of LRS devices. n devices give C(n, k) codes.
n = 2 gives at most 2. n = 3 gives 3 for k = 1, or for k = 2 at twice the LRS current. One-of-three is therefore the smallest such
cell. Per-row schemes are not bound by this (Section 7).

**Error detection.**
- One-of-three: every single-device flip gives 0 or 2 LRS devices, so 9 of 9 flips are invalid codes.
- 2T2R: only 2 of 6 flips are invalid. The other 4 turn a weight silently into another valid weight, and an LRS device that decays
  below the trip point becomes a silent zero.
- The logic flags (WERR) an invalid code when it is read and counts the weight as 0.
- Detection is not correction, and three devices per weight raise the exposure to device defects by 1.5×.

**Layout.**
- Devices: SkyWater ReRAM devices (0.26 × 0.26 µm), each on a 5 V select transistor (W 1.0 µm, L 0.5 µm).
- Cell: 5.6 × 3.0 µm, 1.556× the 2T2R cell.
- 72 × 24 array: 134.4 × 216.0 µm, 10,368 devices.
- Checks: DRC clean, LVS match; planted DRC and LVS faults both caught.

**Periphery and macro.** Each device column has its own bit-line slice and sense amplifier, so the tile has 72 instead of 48. The
analog macro grows from 1436.7 × 1391.7 µm to 1566.3 × 1950.5 µm (1.53× in area),
mostly from the stacked floorplan of the slices, not from the array. DRC 0, LVS match;
a planted LVS fault was caught.

**Programming.** A quasi-static simulation of 12 devices through the drawn drivers:
- Set at a 2.0 V word line takes 7 / 8 / 7 pulses (tt / ss / ff).
- Reset of devices up to three decades slower than nominal takes at most 7 pulses.
- Each device takes the same number of pulses as in the 2T2R macro.
- No other device changed by more than 0.0 µS.

Transient programming and disturb are not simulated. From an erased array, one-of-three sets one device for every weight, where
2T2R sets one per non-zero weight.

**Logic.** Build option `TCIM_CELL_1OF3`. Without the option, the core is proven equivalent to the verified revision 4.7 core
(2,718 points, 0 unproven). With it:
- RTL test bench: 107,302 and 107,302 checks in the two trit codes, 0 failures.
- Chip test bench through a line-level macro model: 101,737 checks, 0 failures.
- Planted controller faults in the Z logic: 6 of 6 caught.
- Formal safety proof: passes; 3 of 3 planted Z faults make it fail.
- Full mutation campaign: 133 of 133 faults caught.

The progress and two-copy timing proofs do not yet cover the option.

**Read current (cost).** Mean sense-amplifier supply current over the 250 ns read, from SPICE transients of the drawn amplifier:

| Device states | one-of-three weight (µA) | 2T2R ±1 / 0 (µA) | ratio, 0 % zeros | 33 % | 50 % | 70 % |
|---|---|---|---|---|---|---|
| SkyWater's published states (LRS 60 µS, HRS 4.5 µS) | 4.25 | 3.25 / 2.00 | 1.31× | 1.50× | 1.62× | 1.79× |
| states the drawn drivers program (LRS 29.9 µS, HRS 0.31 µS) | 2.60 | 2.44 / 0.32 | 1.07× | 1.50× | 1.88× | 2.72× |

A constant LRS count means the worst-case current every time. The penalty grows with sparsity, and more so if programmed HRS devices
sit far below SkyWater's 4.5 µS.

## 6. Evaluation with sense-amplifier waveforms

**Waveforms.** ngspice transients of the drawn SKY130 sense amplifier over the 250 ns read, for conductances from 2 to 120 µS,
nominal and with 40 Monte Carlo mismatch samples:
- Mismatch: 0.126 µA sd on an LRS read, 0.044 µA on HRS.
- Over 30 to 120 µS the mean LRS current varies by 0.028 µA; the largest difference in one 10 ns window is
  0.50 µA.
- Every read is correct.

**Tile model.**
- The 72 sense amplifiers are drawn from the 40 mismatch samples (so samples repeat) and frozen.
- Waveforms are interpolated in log G. There is no shared supply network and no bit-line parasitics.
- Conductances are lognormal at SkyWater's published states: HRS median 4.5 µS, σ_ln 0.3, at most 7.93 µS; LRS median 60 µS,
  σ_ln 0.35, 30–120 µS.
- Five 50 ns windows per read; revision 4.7 logic; 5.0 µA rms noise per window; sense-register switching
  off (k_sense 0).
- 150,000 traces per group are about 2.7 s of acquisition, small against an attacker's budget.

**Three effects, three tests.**
- (a) With one programmed instance in the fixed group, a test also sees that instance's conductances, a fingerprint. The weight test
  reprograms the fixed group for every trace.
- (b) With a random start row, every sample sees the matrix average, so a shuffled test only sees the matrix-wide zero count. The
  fixed matrix has 565 zeros against 576 expected, and that is what the 2T2R result detects.
- (c) Row-aligned tests see each row and each position.

| Cell | shuffled, frozen instance | shuffled, reprogrammed | row-aligned, reprogrammed | row-aligned, reprogrammed, sense-amplifier rotation |
|---|---|---|---|---|
| 2T2R | 12.14 (leaks) | 11.94 (leaks) | 394.41 (leaks) | 387.06 (leaks) |
| one-of-three | 22.16 (leaks) | 3.18 (passes) | 26.32 (leaks) | 2.70 (passes) |
| one-of-four (4T4R as proposed: a fourth device always HRS) | 21.54 (leaks) | 3.09 (passes) | [not run] | [not run] |

Inputs (shuffled, frozen): 2T2R 3.42 (passes), one-of-three 3.17 (passes), one-of-four
3.79 (passes). Max |t| over 360 samples, 150,000 traces per group. The row-aligned runs model a product whose rows are
read in order (as with NOSHUF); a margin check reads one row at three references.

**The position residual.** In the row-aligned test one-of-three still leaks. Each sense amplifier has its own mismatch, and which
sense amplifier reads the LRS device depends on the weight. This is a first-order, chip-specific signal:
- Profiling on another chip does not calibrate it.
- Reprogramming the victim does (Section 2).
- Collisions between rows do: every row of a column uses the same three sense amplifiers, so two rows with equal weights in a column
  draw equal currents there.

**Proposal: sense-amplifier rotation.** On every read, connect the cell's three bit lines to its three sense amplifiers in a random
cyclic order: a 3:1 switch per amplifier, two random bits per column, and the decode rotated back in logic. Each amplifier's mismatch
is then spread over P, Z and N. In the model this takes the row-aligned test from 26.32 to 2.70; for 2T2R it changes
nothing (394.41 to 387.06), because the zero count is still there. The rotation is not drawn and not in the RTL,
and its random bits would come from the same deterministic LFSR as the start row.

**Attack.** A profiled sparsity-recovery attack (`attack_sparsity.py`). Row alignment is granted; the attacker averages N reads of
every row and fits current against zero count on a profiling device. 20 victim devices per point; means shown.

| Reads per row | 2T2R correlation | 2T2R rows exact | one-of-three correlation | one-of-three rows exact |
|---|---|---|---|---|
| 1 | 0.71 | 0.18 | -0.05 | 0.01 |
| 4 | 0.86 | 0.25 | -0.04 | 0.02 |
| 16 | 0.88 | 0.32 | -0.01 | 0.02 |
| 64 | 0.89 | 0.32 | 0.04 | 0.01 |
| 256 | 0.89 | 0.35 | -0.01 | 0.02 |
| 1,024 | 0.90 | 0.34 | 0.02 | 0.03 |
| 4,096 | 0.90 | 0.35 | -0.01 | 0.01 |

Guessing the most likely count is right for about 17 % of rows.
- The linear attacker stops near 0.90 on 2T2R.
- On one-of-three its exact-row rate falls below the guessing rate. The fitted slope is near zero, so the clipped estimates land at the
  ends of the range. This is an estimator artifact, not information.
- A second attacker regresses on all five windows, profiled on 8 devices. 2T2R: correlation 0.97, 70 % of
  rows exact at 4,096 reads per row. One-of-three: -0.02 and 17 %, the guessing rate.
- Neither attack targets the position residual.

## 7. Discussion and limitations

- **What is claimed.** The one-of-three cell removes the dependence of row current on the zero count, which a profiling attacker can
  exploit across chips. It does not make the current constant. The position residual needs the rotation above, or an attacker model
  without access to the victim's own calibration.
- **Alternatives.**
  - Per-row compensation can use as few as 5 binary-weighted devices per row (0 to 24 zeros). It stores the zero count, which leaks
    when it is programmed, and it must track every LRS device.
  - A current-DAC flattener costs less area, but it holds the zero count in logic and must track corners and mismatch.
  - Neither is simulated here; they are the baselines to compare next.
  - Sign masking cannot hide which weights are zero.
- **Threats not covered.**
  - Localized electromagnetic probing of the separate P, Z and N bit lines.
  - WERR as a fault oracle (fault injection is out of scope).
  - The deterministic LFSR after reset.
  - Higher-order and template attacks on the position term.
  - Sense-register switching, which depends on whether vertically adjacent weights are equal. Clearing the register between reads is
    proposed.
  - Trained weight distributions instead of uniform random weights.
- **Device states.** The tile model uses SkyWater's published states (60 µS, 4.5 µS). The drawn drivers program to about 30 µS and,
  with one reset pulse, about 0.3 µS. The cost table shows both.
- **Programming.** The per-pulse profile of the fixed-length program command still leaks in the behavioural model. That test has the
  frozen-instance confound and must be repeated with reprogrammed groups for both cells.
- **Precharge sense amplifiers and analog read.** The result holds for this static current-mode amplifier and the digital read. In
  current-summing CIM with separate P and N lines, the Z current is a constant offset and does not hide the weights.
- **Evidence.** These are models only; silicon is the decisive test.

## 8. Related work

- Power and timing attacks on CIM and NN accelerators [A1, A4, A13, F4, F5].
- Device mismatch as the leakage source in memristive crossbars [A6]; our position residual is that effect.
- CIM countermeasures [A2, A3, B1].
- Power-balanced memristive implementations [A26] and dual-rail ReRAM storage against collision attacks [A8].
- Ternary and binary differential ReRAM storage [C1, C3].
- Dual-rail and 1-of-n codes in secure logic [D2, D3, D4, D5]; one-of-three is the 1-of-n code [D4] applied to the memory cell.
- Fixed-weight codewords for ternary memory reliability [D1].
- Open ternary CIM on SKY130 [E1].

We found no one-of-three ReRAM cell for side-channel resistance (web search, 8 November 2026; IEEE Xplore and patent search still
pending).

## 9. Conclusion

The 2T2R ternary encoding leaks weight sparsity through the read current, and logic cannot repair it. Storing each weight as one LRS
device out of three removes the zero-count signal, at 1.56× cell area and 1.53× macro area. What remains is a
position signal from sense-amplifier mismatch. It is chip-specific and, in the model, removed by rotating the sense amplifiers. The
controller option passes the test benches, the safety proof and the fault campaigns run so far. The 3T3R chip is not yet assembled.

## Artifact

- Layout: `layout/sky130/next_3t3r/`.
- RTL option: `rtl/tcim_core.sv`, `rtl/chip/tcim_actl.sv`; formal task `safety_1of3`.
- Leakage tools: `tools/tvla_circuit.py` (`--redraw`, `--aligned`, `--sa-rotate`), `tools/attack_sparsity.py`,
  `chip/sky130/sim/sa_transient.py`.
- Results: `results/security/`, `results/next_chip/`.

## References (to be checked against the papers before submission; IDs as in LITERATURE.md)

- [A1] F. J. Mir et al., "Extracting Weights of CIM-Based Neural Networks Through Power Analysis of Adder-Trees," ETS 2024.
- [A2] F. J. Mir et al., "Make it Darker: A Gray Code Popcounter to Protect BNN CIM Against Power Attacks," DATE 2026.
- [A3] F. J. Mir, A. Aljuffri, S. Hamdioui, M. Taouil, "Securing Weights of CIM-Based Neural Networks Against Power Analysis Attacks," IEEE JETCAS, 2026.
- [A4] J. J. C. Goudzwaard, "Analog CiM Security Analysis: Reverse-Engineering Ternary Neural Network Parameters," MSc thesis, TU Delft, 2025.
- [A6] B. Sapui, M. B. Tahoori, "Power Side-Channel Analysis and Mitigation for Neural Network Accelerators based on Memristive Crossbars," ASP-DAC 2024.
- [A8] B. Sapui, M. B. Tahoori, "Side-channel Collision Attacks on Hyper-Dimensional Computing Based on Emerging Resistive Memories," ASP-DAC 2025.
- [A13] C. Merkel, "Enhancing Adversarial Attacks on Single-Layer NVM Crossbar-Based Neural Networks with Power Consumption Information," arXiv 2207.02764, 2022.
- [A26] Z. Chen et al., "Power-balanced Memristive Cryptographic Implementation Against Side Channel Attacks," arXiv 2312.01170.
- [B1] M. Ashok et al., "A Secure Digital In-Memory Compute Macro with Protections Against Side-Channel and Bus Probing Attacks," CICC 2024.
- [C1] A. Laborieux et al., "Implementation of Ternary Weights With Resistive RAM Using a Single Sense Operation per Synapse," arXiv 2007.14234.
- [C3] M. Bocquet et al., "In-Memory and Error-Immune Differential RRAM Implementation of Binarized Deep Neural Networks," IEDM 2018.
- [D1] C. V. A. Laurent, R. Muzzetto, "Fixed weight codewords for ternary memory cells," US 11,811,424 B2, 2023.
- [D2] K. Tiri, I. Verbauwhede, "A Logic Level Design Methodology for a Secure DPA Resistant ASIC or FPGA Implementation," DATE 2004.
- [D3] T. Popp, S. Mangard, "Masked Dual-Rail Pre-Charge Logic," CHES 2005.
- [D4] S. Moore et al., "Balanced Self-Checking Asynchronous Logic for Smart Card Applications," Microprocessors and Microsystems, 2003.
- [D5] H. Maghrebi, V. Servant, J. Bringer, "There is Wisdom in Harnessing the Strengths of your Enemy," FSE 2016.
- [E1] M. Pai, "Ankhdjet: An Open-Source Compiler for Mask-Programmed Ternary Compute-in-ROM on an Open PDK," arXiv 2608.26206, 2026.
- [F4] W. Hua, Z. Zhang, G. E. Suh, "Reverse Engineering Convolutional Neural Networks Through Side-channel Information Leaks," DAC 2018.
- [F5] S. Maji, U. Banerjee, A. P. Chandrakasan, "Leaky Nets," IEEE IoT Journal, 2021.
