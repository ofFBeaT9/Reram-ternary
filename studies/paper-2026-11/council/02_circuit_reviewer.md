# Council review 02: the 3T3R one-of-three cell as a circuit contribution

Reviewer role: senior ReRAM compute-in-memory circuit designer, reviewing as for IEEE JSSC / TCAD / JETCAS.
Date: 8 November 2026. Every number below is read from a file in this repository (path given). Where I combine numbers,
the arithmetic is mine and labelled so. All results are evidence about the model, not about silicon.

## Verdict

The cell is a sound, simple idea, and one piece of its framing holds up well: with two-state devices, a constant-weight
code for three values needs at least n = 3 devices, because C(2,1) = 2 < 3. So 3T3R with one LRS is the *minimum*
constant-LRS-count ternary cell, and 4T4R or sign/magnitude dual-rail (4 devices, always 2 LRS) cost more for the same
property (STATUS 15.6 finds no gain from 4T4R). The paper should state this bound. It is short and a reviewer cannot argue
with it.

The paper plan's main claim, "removes that leak by construction ... shown on transistor-level read currents", is **not
supported by the result file now in the repository**. `results/security/tvla_circuit.json` (transistor-level waveforms,
150,000 traces per group) gives |t| = 12.14 for 2T2R weights, **22.16 for 1of3 weights** and 21.54 for 4T4R weights: all
three fail, and one-of-three is worse than 2T2R. The file's `assumptions` block has no `fixed_group_reprogrammed` or
`lrs_sigma_ln` field, which the current `tools/tvla_circuit.py` writes. So the file comes from the earlier version, in
which the fixed group keeps one frozen set of conductances. That test sees the device instance as well as the weights. It
has to be rerun with `--redraw` (or as a fixed-versus-fixed test with both groups reprogrammed) before the claim is
written. Even then, part of the 22.16 is likely real weight leakage, for the reason given in section 2. The sparsity
attack (`results/security/attack_sparsity.json`) does support the narrower claim: correlation 0.90 at 4,096 reads per row
on 2T2R, −0.014 on 1of3.

## 1. Cost

| Item | 2T2R | 3T3R | Ratio | Source |
|---|---|---|---|---|
| Cell | 3.6 × 3.0 µm | 5.6 × 3.0 µm (16.8 µm²) | 1.556 | `results/next_chip/array3.json`, `cell3.tcl` |
| Devices / bit lines / SL per weight | 2 / 2 / 1 | 3 / 3 / 1 (SL shared by P, Z, N) | 1.5 | `cell3.tcl` |
| Sense amplifiers, 24 columns | 48 | 72 | 1.5 | STATUS 15.6 |
| Analog macro | 1436.7 × 1391.7 µm (2.00 mm²) | 1566.3 × 1950.5 µm (3.06 mm²) | 1.53 (my arithmetic) | `macro3_layout.json` |
| Pulse steps per row (test bench) | mean 15.1, max 18 | mean 15.4, max 17 | about 1 | `results/sky130_chip/rtl_chip_110.log`, `rtl_chip_1of3_110.log` |
| Program command (constant time) | 1352 cycles | 1352 cycles | 1 | same logs |

Two cautions on area. First, the array (134.4 × 216 µm) is about 1 % of the 3T3R macro (my arithmetic). The 1.53× at the
macro level comes from the floorplan: bit-line slices sit in two stacks, which grow from 24 to 36 slices each
(`macro3.py`), and that sets the macro height. It is not the cell. A circuits reviewer will ask for cost with pitch-matched
periphery. There the honest numbers are +50 % sense amplifiers and bit-line drivers, +56 % cell, and a sense-amplifier
pitch of 1.87 µm per device (5.6 µm / 3). Second, quote area per weight at macro level, not the cell ratio, in the title
claim.

**Read energy** is the cost the plan leaves out. The read path clamps the LRS current: `sa_power.json` gives 2.384–2.386 µA
from 16 to 150 µS. HRS is not clamped (0.536 µA at 2 µS, 1.07 µA at 4.5 µS, 1.715 µA at 8 µS). From the transient means
in `sa_transient.json` (LRS 60 µS: 2.25 µA; HRS 4.5 µS: 1.00 µA), my arithmetic gives the sense-amplifier current per
weight:

- 2T2R: 3.25 µA for a non-zero weight, 2.00 µA for a zero;
- 3T3R: 4.25 µA for every weight.

The 3T3R / 2T2R ratio is 4.25 / (3.25 − 1.25 s) for zero fraction s: 1.31 at s = 0, 1.50 at s = 1/3, 1.62 at s = 0.5 and
1.79 at s = 0.7. Constant current is worst-case current, and the cost grows with exactly the sparsity that ternary networks
are trained for. At 1.8 V over the 250 ns read this is 1.9 pJ per weight per row read for the sense amplifiers alone (my
arithmetic). STATUS section 6 (IHP) puts sense amplifiers at 0.19 nJ of about 1.05 nJ per product, so the system-level
increase is smaller. That energy table exists only for IHP and 2T2R. Make it for SKY130 and both cells.

Programming: the constant-time sequence makes duration identical. But every weight now needs one set and two resets, so
each row step selects more devices (11,442 against 11,282 device pulses over the test bench, same logs). The
quasi-static `macro_sim3.json` reaches the set target in 7–8 pulses and the reset target in 1–7 pulses (cells up to three
decades slower), with 0.0 µS disturb on the 11 other devices. Quasi-static is not transient: rerun it with transient
pulses before calling it "no disturb".

## 2. Reliability and the constant-current residual

This is the strongest circuit argument, and the plan under-sells it. One-of-three is a distance-2 code. Of the nine
single-device flips from valid codes, all nine give an invalid code (no LRS, or two LRS), and the RTL flags it as WERR
(STATUS 15.7; tested by 168 directed checks, 7/7 Z-logic faults and 6/6 controller faults caught,
`mutation_chip_1of3.json`). In 2T2R only 2 of 6 single flips are detectable (into LRS/LRS); the other 4 silently become a
different valid weight. The important case is retention: an LRS that decays below the trip point (between 12 and 16 µS in
`sa_power.json`) becomes a silent zero in 2T2R but a detected 000 in 3T3R. The LRS clamp is flat down to about 16 µS, so
the constant-current property and error detection fail at the same point: drift is harmless until it is flagged. Note
the limits. Detection is not correction (an invalid weight still counts as 0). Double flips (P→HRS with Z→LRS) map to a
valid code. With three devices per weight, the chance that a weight holds a stuck or unformable device is about 1.5×
higher for small defect rates.

The residual is **not** mainly LRS spread, as the brief assumes. In digital mode the clamp removes LRS spread from the
mean (2.25–2.28 µA over 30–120 µS) but not from the first window: the peak is 4.02 µA at 30 µS against 3.31 µA at 90 µS,
and `lrs_spread_over_G_uA` is 0.50 µA. HRS is unclamped, and each 3T3R row carries 48 HRS devices, against an average of
32 for uniform 2T2R. There is also a *position* term. Each P, Z and N sense amplifier has its own frozen mismatch (sd
0.126 µA at LRS 60 µS), so which of the three carries the LRS changes the sum. The code keeps the LRS count constant; the
current still varies. NEXT_CHIP_SPEC says this ("a small first-order difference remains"), and LITERATURE D5 (Maghrebi)
and A6 make the same point. This probably explains part of the 22.16. Show a template attack on that position term, not
only a sparsity-count attack. Also, the downstream sense flip-flops still switch with the weight pattern (`--k-sense` is
0 by default in `tvla_circuit.py`).

## 3. Analog (current-summing) mode

The property survives only in part. With all three bit lines biased equally and fed from one supply, the total row current
stays one LRS per weight. But: (a) without the clamp the LRS conductance enters directly (30–120 µS, a factor of 4; σ_ln
0.35 in `tvla_circuit.py`), so the residual is much larger than in digital mode; (b) P − N column currents still depend on
the weights, so an ADC with data-dependent time or energy (ramp, integrating) leaks them; (c) the Z current is pure waste
unless it is reused as a reference; (d) row activation still reveals input sparsity. One clear analog benefit is worth a
paragraph. The source-line current per column becomes independent of the weights, so IR drop becomes a calibratable
constant, at its worst-case value. None of this has been simulated. The analog tile model in `array/` handles only 2T2R
(two bit lines per column, STATUS section 6).

## 4. Alternatives a reviewer will raise

- **Dummy column / row compensation with binary devices**: covering a row of all zeros needs 24 dummy devices per row,
  the same count as Z. Z is that dummy, placed in the cell, so it tracks layout, sense amplifier and drift. It must win on
  tracking, not on count.
- **Current-DAC flattening** (inject 2.39 µA × zeros per row): far cheaper in area. But it keeps the zero count in a logic
  register, which can leak, and it must track the corners (2.353 µA ss, 2.42 µA ff, `sa_power.json`) and mismatch. This is
  the baseline that threatens the paper. Simulate it.
- **2T2R with zero = LRS/LRS, or two half-LRS devices**: LRS/LRS reverses the leak. A half level (about 15 µS) lands on the
  sense amplifier's trip point and needs a middle level that SkyWater does not publish (NEXT_CHIP_SPEC).
- **Masking**: sign masking leaves zero positions unchanged, so it cannot hide sparsity. Row shuffling is already used.
- **Precharge sense amplifier** (Laborieux C1, C3): the leak mechanism there is decision time, not static current. The paper
  must say that its result is specific to a static current-mode sense amplifier.

## 5. What is missing for a circuit venue

Can be simulated now: (1) rerun `tvla_circuit.py --redraw` and add a position-template attack; (2) the SKY130 energy
table for 2T2R and 3T3R against sparsity; (3) the current-DAC baseline; (4) transient programming and read disturb of the
Z device, which is LRS for every zero and so the most-read LRS; (5) WERR rate against LRS decay; (6) network accuracy with
3T3R. The digital read is exact, so accuracy equals 2T2R (94.7 %, STATUS section 6) unless invalid codes occur, and (5)
supplies the number. (7) An analog-mode 3T3R tile model.

Cannot be simulated: silicon, and measured LRS/HRS spread, retention and per-position read currents. Without them this is
a TCAD/JETCAS simulation paper, not a JSSC paper. A further gap: the 3T3R chip has not been assembled or prechecked (48
more macro pins, ROADMAP).
