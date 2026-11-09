# Council review 01: side-channel methodology (TCHES reviewer's view)

Reviewer role: senior TCHES reviewer, side-channel analysis of hardware. Date: 8 November 2026.
Files read: `studies/paper-2026-11/PAPER_PLAN.md`, `LITERATURE.md` (sections 1, 6-8), `tools/tvla_circuit.py`,
`tools/attack_sparsity.py`, `tools/tvla_tcim0.py`, `chip/sky130/sim/sa_transient.py`, `results/security/{tvla_circuit,
attack_sparsity, sa_transient, tvla}.json`, `rtl/tcim_core.sv` (margin check, invalid codes), `layout/sky130/next_3t3r/macro3.py`
(header). No `results/security/tvla_circuit_redraw*.json` existed when I read the folder, so I could not check the redraw numbers
(2T2R 6.41, 1of3 2.92 at 20,000 traces per group) against a file. Every number below is about the model, not silicon.

**Verdict.** The encoding argument is sound and simple: a constant-weight (one-hot) code makes the *number* of LRS devices per
row independent of the weights, the ternary counterpart of dual-rail storage. As the evidence stands, TCHES would return
reject or major revision. The cell is not the problem. The evaluation is: first-order, shuffled, non-specific TVLA plus one
univariate linear attack, a noise level that is assumed, and the known residual channels left unmeasured. All of this can be
fixed in simulation before 15 January 2027.

## 1. Frozen vs redrawn conductances, and the 22.16

A fixed-vs-random test with one frozen programmed instance compares one sample of the conductance distribution with the
population. For any analog storage, the mean of that one instance differs from the population mean, and |t| grows as
sqrt(N). The frozen result (`tvla_circuit.json`, 150,000 traces: 1of3 22.16, 2T2R 12.14) is what that predicts. 1of3 is
larger because a 1of3 row has 72 sense amplifiers instead of 48 and always 24 LRS devices, so its instance deviation is
larger. A TCHES reviewer will read 22.16 as "the test is not specific to the secret". If the paper prints it next to a claim
of "no leak", the reviewer will read it as "the countermeasure fails". Report it, but frame it as a calibration of the test.

The redraw test (fixed weights, new conductances per trace, sense-amplifier mismatch frozen in both groups, `tvla()` line 91)
is the right test of the *encoding*. It is not the deployed threat: a deployed chip holds one instance. The question the
paper must answer is whether that instance's fingerprint carries information about W. Use a nested design for this:
(a) same W, two programmings (the null: how big the fingerprint is); (b) W_A against W_B, each programmed once; (c) W_A
against W_B with the same per-row zero counts. If (b) and (c) are no larger than (a) for 1of3, the fingerprint is
instance-only. Better still, estimate perceived or mutual information directly instead of pass/fail (Goodwill, ICMC 2017,
cited in LITERATURE F14: a pass needs a set-up that has been shown able to fail).

The bigger methodological problem is **shuffling**. With a uniformly random cyclic start row, each time slot sees a random
row, so first-order fixed-vs-random only tests the *matrix-average* current, that is, the global sparsity. The per-row
structure the paper claims to protect lives in the aligned or second-order statistics. `tvla.json` shows that the 1of3 pass
depends on this: with the revision 4.6 start-row distribution (non-uniform), 1of3 weights give 7.34 at 150,000 traces
(leaks); with revision 4.7 they give 2.88. That residual is probably the same fingerprint, but a reviewer cannot tell
without the specific test. Rotation hides about log2(72) ≈ 6.2 bits and can be undone by circular cross-correlation
whenever rows differ. Most important: as I read `rtl/tcim_core.sv` (lines 23-25, 413, 578), the margin check reads a
*chosen* row and still runs under LOCK (only the PDATA write is suppressed). That gives the attacker an unshuffled,
repeatable, row-addressed read. **The row-aligned case is then the default attack path, not a worst case.** Every TVLA
must therefore also be run row-aligned (start row known), on the margin-check read as well as the product read.

## 2. Attacker model and attack strength

Profiling on a second device is reasonable and transfers systematic effects but not random mismatch. State whether the
attacker can program the victim (that matters for learning its mismatch) and what LOCK forbids.

`attack_sparsity.py` is weak. It takes the sum over the five windows, fits a linear model of current against zero count,
and reports exact recovery. For 2T2R, correlation reaches 0.90 and exact recovery about 0.35 at 4,096 reads, then stops
improving: the victim's frozen conductance spread is noise that averaging cannot remove. For 1of3 the estimator is
linear in zero count, which is exactly what the cell cancels by construction, so a result near 0 says little. A stronger
attack would:
- use multivariate Gaussian templates or LDA on all windows (`sa_transient.json`: the nominal peak is 3.42 µA at 60 µS
  against 1.48 µA at 4.5 µS, so the waveform shape differs and not only the mean), at 10 ns windows as well as 50 ns;
- add a deep-learning baseline, as is standard at TCHES;
- target functions other than the zero count: the P-vs-N count, which systematic asymmetry could expose, and equality
  of vertically adjacent weights (section 3);
- report information in bits per row and guessing entropy, not exact counts. As a scale: the zero count of a uniform row
  carries at most 3.25 bits of its 38.0 bits (my computation, Binomial(24, 1/3)). The end goal, a model-extraction
  fidelity on a trained ternary network, should be shown.

Uniform random weights are also unrealistic. Use weights from a trained ternary network mapped onto tiles.

## 3. Second-order residuals

- **Mismatch × LRS position.** The frozen per-amplifier mismatch (sd 0.126 µA at LRS 60 µS, 0.044 µA at HRS 4.5 µS,
  `sa_transient.json`) makes each column's current depend on *which* of P, Z, N is LRS. The term is per column, so it is
  the same in every row and an attacker who can calibrate the victim can exploit it. The model has only random local
  mismatch. Systematic P/Z/N differences from layout are absent: the deck uses `Cbl 60f` for every bit line, while
  `macro3.py` routes each bit line on its own track and therefore with its own length. These differences transfer
  through profiling. Extract them.
- **Sense registers (`K_SENSE`).** The default is 0, so the preliminary runs presumably exclude it. In 1of3 the Hamming
  distance between consecutive sense words is 2 × (the number of columns where w_k ≠ w_{k+1}). That is a
  weight-dependent leak that has nothing to do with sparsity. Clearing both register stages (q1, arr_sa) between reads
  turns the distance into a Hamming weight, which is a constant 24 for a one-hot code. The fix is cheap and only the
  encoding makes it possible, so put it in the paper. The decode logic (`sa_p_d = arr_sa_p & ~arr_sa_z`, ...) has
  data-dependent glitches. The one-hot and dual-rail literature (WDDL, MDPL; LITERATURE D2-D4) shows that early
  evaluation and unbalanced routing leak. Address it.
- **Dummy vs real accumulators.** The model gives both K_DIG per flipped bit. In silicon their loads differ. With chosen
  inputs, "real or dummy" per column *is* the zero mask (`upd = W≠0 & X≠0`), so the leak becomes per column instead of
  per-row count. Measure this on the routed netlist with extracted parasitics.
- **Programming.** `tvla.json`: 2T2R variable 87.35, constant 65.67, 1of3 constant 66.38. That test freezes per-device
  speed and fixes W, so it has the same fingerprint confound. With random previous content, the number of SETs per 1of3
  row is Binomial(24, 2/3) for any target. From an erased state it is always 24, while for 2T2R it equals the number of
  non-zeros. So "programming leak unchanged" may be wrong in either direction. Re-run with fresh speeds and with known
  previous content.
- **HRS history and invalid codes.** The model draws every HRS from one lognormal. A device reset from LRS and one never
  set may differ, and history correlates with weight updates. Invalid codes count as 0 and set WERR, which is constant
  time. But drift (LRS to HRS, code 000) changes the row current by one LRS, and WERR is a fault oracle, which is outside
  the stated model but should be named.

## 4. Missing experiments (all in simulation, using existing scripts)

| # | Experiment | Effort |
|---|---|---|
| E1 | Nested specific tests (same-W/two-programmings, W_A vs W_B, matched zero counts) in `tvla_circuit.py` | 0.5 day + CPU hours (the 150k cases took 370-845 s each) |
| E2 | Row-aligned TVLA (known start row; margin-check read), first and second order (centered squares), multivariate across windows; t against N up to 10^6 | 1 day |
| E3 | Noise sweep (1-10 µA rms) with results given as a function of SNR; justify 5 µA against a real shunt set-up including the Caravan management core | 0.5 day |
| E4 | Template/LDA and one-layer neural network attacks, perceived information, trained ternary weights, extraction fidelity | 2-3 days |
| E5 | Per-bit-line R/C extracted from `tcim_sky130_array3.ext` / macro3 and fed into `sa_transient.py`; systematic SA offset gradient | 1-2 days |
| E6 | K_SENSE sweep with and without return-to-zero; decode-logic glitch power at gate level | 1 day |
| E7 | Real vs dummy accumulator power from the routed 2T2R chip block (VCD + SPEF); the 1of3 block is not routed yet | 2 days |
| E8 | Programming TVLA with fresh speeds, erased vs random previous content; transistor-level pulse profile | 1 day |
| E9 | LRS-spread sweep to the clip limits (`--lrs-sigma`), HRS history model, temperature corners of the SA waveforms | 1 day |
| E10 | One combined run with every residual switched on | 0.5 day |

Silicon remains decisive. TCHES accepts pre-silicon work only when the method is beyond reproach, and the open artifact
helps here.

## 5. Strongest honest claim

"In a transistor-level model of a signed-off SKY130 ternary ReRAM compute-in-memory tile, a one-of-three 3T3R cell
removes the first-order dependence of the array read current on per-row weight sparsity that the 2T2R cell shows (a
linear sparsity attack reaches correlation 0.90 on 2T2R and about 0 on 3T3R), at 1.56× cell area, while residual leakage
from device instances, sense-amplifier mismatch and the digital periphery remains to be bounded."
