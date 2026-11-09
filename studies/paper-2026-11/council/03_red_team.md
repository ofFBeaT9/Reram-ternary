# Council review 03: independent red team (8 November 2026)

Role: hostile TCHES / TCAD reviewer who did not write the draft. Read: `DRAFT.md` (draft 0.1, written 11:17), `make_draft.py`,
council files 00–02, `docs/TCIM0_explainer.html` sections `cells` and `leak3`, `docs/page/leak3_section.py`, `docs/page/full.py`
(the `done3` part), `tools/tvla_circuit.py`, `tools/tvla_tcim0.py`, `tools/attack_sparsity.py`, `rtl/tcim_core.sv` (LOCK, PCMD,
decode), and the result files named below. Every number is from the model, not from silicon.

Two checks of my own (short, not written to `results/`):

- **R1, the row-aligned run.** `tools/tvla_circuit.py --redraw --aligned --only 1of3 --secrets W --traces 20000`, output in the
  scratchpad (`aligned_1of3_20k.json`): one-of-three, weights, fixed group reprogrammed, row-aligned: **max |t| = 10.67 at 20,000
  traces per group: leaks.**
- **R2, noise-free prediction.** For each sense amplifier (SA), I averaged the SA's expected waveform over the conductance
  distributions using the tool's own `draw_g` / `interp` / seeds. That gives the noise-free mean difference between groups. I took the
  within-group variance from the tool's `traces()` with SIGMA = 0, added 25 µA² of noise, and projected |t| to 150,000 traces per
  group. Predicted signal |t| (no max-over-noise term):

  | Cell | shuffled (as in `tvla_circuit_redraw.json`) | row-aligned |
  |---|---|---|
  | 2T2R (fixed W: 565 zeros) | 9.4 (measured 11.94) | 392 |
  | 2T2R, same W changed to exactly 576 zeros | **0.36** | – |
  | one-of-three | 0.4 (measured 3.18) | **27.6** (20k: predicted 10.1, measured 10.67) |
  | 4T4R (as modelled) | 0.3 | 25.3 |

  The prediction matches the measured runs (9.4 vs 11.94, 10.1 vs 10.67), so the mechanism is understood.

## Findings

### 1. BLOCKER: one-of-three leaks the weights at first order in the draft's own default threat model

*Attacked:* abstract "making the number of conducting devices per row independent of the weights by construction"; §7 "A
second-order residual remains: the product of sense-amplifier mismatch and the position of the LRS device; we bound it only
through the tests above"; §9 "removes it by construction"; and §2 "row alignment is the default, not a worst case".

*Evidence:* R1 gives 10.67 at 20k traces per group, row-aligned and reprogrammed (it is **not** an instance fingerprint). R2 predicts
about 28 at 150k (4T4R about 25). The term is **first order** (a difference of means). Each SA has its own frozen mismatch, so the
current depends on *which* of P/Z/N holds the LRS. The shuffled test cannot see it: with a uniform start row, every time slot sees
the matrix average, and the term averages out by about 72× (finding 2). "Bounded through the tests above" is false: no test above
can see it.

*Fix:* run `--aligned` for all cells at 150k and put it in the table. Rewrite the claim: "One-of-three makes the number of LRS
devices per row independent of the weights. The remaining first-order leak is device-specific: the per-SA mismatch times the
position of the LRS device (row-aligned |t| ≈ 10.7 at 20,000 traces). A profiled attacker using another device cannot turn it into
sparsity (Section 6). An attacker who can calibrate the victim's SAs can (finding 3)." Remove "second-order" and "by construction"
for the current. Keep "by construction" only for the LRS count.

### 2. BLOCKER: the shuffled TVLA tests the matrix-wide zero count, not per-row sparsity, so neither verdict means what the text says

*Attacked:* abstract "so each row's read current reveals its number of zero weights (|t| 14.24 at 150,000 traces per group)". §4
table row "Cell (2T2R) … |t| 14.24". The abstract's planned "fixed-versus-random weight tests drop from 11.94 (2T2R) to 3.18 (3T3R)"
(`tvla_circuit_redraw.json`).

*Evidence:* the fixed matrices are not balanced. The circuit tool's matrix (seed 7) has 565 zeros, against 576 expected. The
behavioural tool's (seed 1) has 561. With a random start row, the fixed-group mean at every slot is the matrix average, so 2T2R
fails only because the global zero count is off by 11 (or 15). R2: the same 2T2R matrix changed to exactly 576 zeros gives a
predicted signal |t| of 0.36 and would **pass**. The 2T2R redraw (11.94) and frozen (12.14) results are almost equal, which fits a
global-count effect. So the 2T2R "leak" is luck of the draw (it passes for about 1 matrix in 12, |dev| < 2 zeros). The 1of3 "pass"
says nothing about per-row structure. The per-row 2T2R claim is supported only by the attack (corr 0.90/0.97), not by any TVLA.

*Fix:* (a) a fixed matrix with exactly the expected zero count and a fixed-vs-fixed test between two matrices with equal per-row zero
counts (council R1's E1c); (b) row-aligned tests for every claim about rows; (c) report results over at least 10 fixed matrices.
Rewrite the abstract as "… so the read current reveals the zero count (profiled attack: correlation 0.90 per row)" and quote |t| only
from a test that targets that quantity.

### 3. BLOCKER: the threat model contradicts the RTL. The attacker it describes can get the weights without a side channel, or can calibrate the victim

*Attacked:* §2 "chosen or known inputs … the margin check … still runs under LOCK, so an attacker can obtain repeated, row-aligned
reads"; §6 "the attacker cannot reprogram the victim without erasing the secret".

*Evidence (`rtl/tcim_core.sv`):*
- (a) `prog_cmd` (line 146) is not gated by `r_lock`: programming runs under LOCK. SA mismatch belongs to a column's device and is
  shared by all 72 rows. Reprogramming **one** row with known patterns erases 24 of 1,728 weights and calibrates every SA, which
  opens the position attack (finding 1) on the other 71 rows.
- (b) `r_lock <= 1'b0` on reset (line 280), and the weights are non-volatile. An attacker with bus access who can reset the chip
  gets read-back (PCMD −) before any firmware sets LOCK. The page already lists "LOCK-after-reset" as unfixed. The draft does not
  mention it.
- (c) Chosen inputs plus readable Y[0..23] (RO, not refused under LOCK) recover W exactly from 72 linearly independent input vectors.
  No power analysis is needed.

*Fix:* state exactly what the attacker controls. One option: inputs go only through the host, Y is not visible, reset is followed by
LOCK in boot ROM, and margin checks come from host maintenance software the attacker can trigger. Or change the RTL: refuse PCMD +
under LOCK, or make programming under LOCK erase the whole array first. Then drop or qualify "cannot reprogram the victim".
Without this, a TCHES reviewer stops reading at §2.

### 4. MAJOR: the title claims constant conductance

*Attacked:* title "a constant-conductance ternary ReRAM cell"; abstract "number of conducting devices".

*Evidence:* the conductances are lognormal (LRS σ_ln 0.35, 30–120 µS; HRS σ_ln 0.3), and HRS devices conduct (4.5 µS). What is
constant is the *count of LRS devices*. Finding 1 shows that the current is not constant either.

*Fix:* "a constant-weight (one-hot) ternary ReRAM cell", and "number of LRS devices".

### 5. MAJOR: "rest of the design unchanged and verified" (§9), and the cost stated as cell area only

*Evidence:* the macro grows from 1436.7 × 1391.7 µm (2.00 mm²) to 1566.3 × 1950.5 µm (3.06 mm²), **1.53×**
(`macro3_layout.json`, my arithmetic). Sense amplifiers go from 48 to 72. The digital block needs 48 more macro pins. The 3T3R chip
is not assembled or prechecked (page: "3T3R: still to do"). The progress and miter proofs do not cover `TCIM_CELL_1OF3` (CLAUDE.md).
The full mutation campaign on the option has run 28 of 122 faults (`rtl_mutation_1of3full_0_121.json`: 28 caught).

*Fix:* "… at 1.56× cell area and 1.53× analog-macro area. The controller option passes the test benches, the safety proof and the
fault campaigns run so far; the 3T3R chip is not yet assembled."

### 6. MAJOR: the precheck sentence names the wrong body and the wrong chip

*Attacked:* abstract "whose open SKY130 test-chip layout passes the foundry's precheck"; §3 "in the foundry's own pinned tool
versions".

*Evidence:* `results/sky130_chip/precheck.json` is ChipFoundry's cf-precheck 1.3.7 (14/14) on the **2T2R** revision 4.7 GDS.
ChipFoundry is the shuttle provider, not the foundry (SkyWater). Whether the shuttle accepts the ReRAM layer is still open (page:
"after ChipFoundry answers on ReRAM"). The evaluated 3T3R design has no precheck.

*Fix:* "The current 2T2R test chip passes ChipFoundry's shuttle precheck (14 of 14 checks, ChipFoundry's pinned tool versions); the
one-of-three variant is drawn and verified at block level but not assembled."

### 7. MAJOR: frozen versus reprogrammed. "Says nothing about its weights" is asserted, and §4 contradicts §6

*Attacked:* §6 "This is a fingerprint of one programmed array and says nothing about its weights". §4 uses the behavioural
`tvla.json` numbers (14.24 for 2T2R, 3.13 for one-of-three) as weight evidence. In `tvla_tcim0.py` those runs keep the fixed group's
HRS conductances frozen (`G_fixed`): they are frozen-instance tests.

*Evidence:* behavioural frozen one-of-three **passes** (3.13). Transistor-level frozen one-of-three **fails** (22.16). The draft
never reconciles the two. The likely reason: the behavioural model gives every LRS device the same clamped current (2.3961 µA), so
LRS spread cannot enter. Whether a deployed instance's fingerprint carries W is the nested test E1, which has not been run.

*Fix:* label §4 as frozen-instance and shuffled. Explain the behavioural/circuit difference in one sentence. Replace "says nothing
about its weights" with "is not shown to depend on the weights (nested test pending)".

### 8. MAJOR: "4T4R (two-of-four)" is not the cell that was simulated

*Evidence:* `lrs_mask` in `tools/tvla_tcim0.py` (used by both tools) builds 4T4R as `[p, n, z, zeros]`: one LRS out of four, with a
fourth device that is always HRS. §5 discusses two-of-four. The page's `cells` section says "one low-resistance device … among four".
Its `leak3` table (from `leak3_section.py` line 78) says "4T4R two-of-four".

*Fix:* call it "one-of-four (4T4R as proposed: one device always HRS)", or simulate a real two-of-four.

### 9. MAJOR: the tile's device distributions contradict the design's own programming simulation

*Evidence:* `macro_sim3.json` has a set-verify target of 27.36 µS, and set stops at 28.4–29.9 µS. The tile model uses an LRS median
of **60 µS** (σ_ln 0.35, clipped at 30 µS), but programmed devices sit near 30 µS. That is where the SA waveform changes most (peak
4.02 µA at 30 µS against 3.42 µA at 60 µS, `sa_transient.json`), and the LRS clamp gives way near 16 µS. Reset in the same file ends at
**0.31 µS**, while the tile's HRS median is 4.5 µS (SkyWater's figure). The 1.25 µA zero/non-zero difference, the cost table and
the HRS residual all depend on the HRS current. Rough check: with HRS ≈ 0.3 µS the ratio tends to 1/(1 − s), about 1.0× at 0 %
zeros and about 3.3× at 70 % zeros, against 1.31× and 1.79× now.

*Fix:* draw LRS from the verify-truncated distribution the program-and-verify run produces (or justify 60 µS through relaxation
data). Settle on one HRS model and recompute the read-current table for it, or show both.

### 10. MAJOR: the trace budget is tiny, and the runs leave out a leak the draft itself names

*Evidence:* 150,000 products × 72 reads × 250 ns = **2.7 s** of acquisition. A pass at that budget is not a pass at an attacker's
budget (margin checks can be repeated without limit). R2's shuffled one-of-three signal (|t| ≈ 0.4 at 150k) is small but not zero.
From noise-free means it would cross 4.5 somewhere near 10⁷ traces; that figure is uncertain and needs a run. All reported runs have
`k_sense_uA = 0.0` (`tvla_circuit_redraw.json`), so the sense-register switching leak named in §7 is off in every "pass". `--aligned`
models a product with NOSHUF (rows 0…71 in order, line 65), not a margin check (one row, three references, no accumulation).

*Fix:* report t against N up to 10⁷ (or traces to disclosure), include a `--k-sense` run, and model the margin-check read, or rename
the flag "aligned product" and say so.

### 11. MAJOR: the attack statistics are presented without baselines or uncertainty

*Attacked:* §6 table "one-of-three rows exact 0.01 … 0.03"; "On one-of-three the estimate carries no information"; "the remaining
error is the frozen device spread of the victim, which profiling on another device cannot remove".

*Evidence (`attack_sparsity.json`):* the linear attacker on one-of-three gets 0.8–2.6 % of rows exact, **far below** the 17.1 %
best-guess rate (my computation: Binomial(24, 1/3) at 8 gives 0.1707). That is an estimator artifact: the profiled slope is near 0
(−0.67 to 0.73 µA per zero), and dividing by it throws estimates to the clip limits 0 and 24. With 20 devices per point the standard
error of the mean correlation is about 0.026 (my arithmetic, 1/√72/√20), so −0.046 is 1.8 SE: no confidence intervals are given.
The second attacker reaches 0.97 and 70 % on 2T2R, which contradicts "cannot remove": the saturation at 0.90 comes from the
sum-of-windows estimator. Only the zero count is targeted: there is no position, P−N or collision target.

*Fix:* report bits per row or guessing entropy with the best-guess baseline, and 95 % intervals. Drop the linear one-of-three
"rows exact" column, or replace it with a maximum-likelihood estimator. Rewrite the saturation sentence. Add a position attack (with
victim calibration, finding 3) and a collision attack (finding 12).

### 12. MAJOR: threats a TCHES reviewer will name that the draft does not mention

- **Collision / horizontal attacks between rows (no profiling needed).** In one-of-three, a row's mean current is the sum over
  columns of a fixed per-column offset for each position. Rows with equal weights therefore give equal currents, and the distance
  between two rows' currents reflects how many columns they differ in. Margin checks give clean row-aligned reads. LITERATURE A8
  (Sapui and Tahoori) is exactly a ReRAM collision attack, and the draft cites it only for its countermeasure.
- **Localized EM.** The P, Z and N bit-line slices are separate physical structures (`macro3.py`: 72 slices). The total current is
  constant, but where it flows is the weight.
- **WERR as a fault oracle.** WERR is readable under LOCK and is set on any invalid code, including by the margin check.
- **The LFSR's state after reset** (seed 0xACE1) makes the start row of the first products predictable.
- **Programming events** observed when the model is loaded.
- **Trained ternary weight distributions** instead of uniform ones (the 17 % baseline and the cost both change).
- **Higher-order and multivariate TVLA**, and a deep-learning attack.

*Fix:* add a paragraph listing each threat as evaluated or out of scope, with a reason.

### 13. MAJOR: related work understates the closest prior art

*Evidence:* LITERATURE A6 (Sapui and Tahoori, ASP-DAC 2024) found that the leak in memristive crossbars comes from **device
mismatch**, which is exactly the residual in finding 1. The draft cites A6 only as an attack paper. A26 (Chen et al.,
complementary memristor groups whose power does not depend on the data, TVLA passes) and A3 (Mir, JETCAS 2026, balanced paths) are
in LITERATURE.md but not in the draft. D4 (Moore et al. 2003) is the published 1-of-n code, so "the ternary analogue of dual-rail" is
the 1-of-3 instance of a known code family. A4 already proposes current flattening as the countermeasure for ternary ReRAM.

*Fix:* one paragraph: "1-of-n hiding [D4] and dual-rail ReRAM storage [A8, A26] are known; mismatch defeats count-balancing [A6]; our
contribution is the ternary ReRAM cell, its minimality, its cost and a measured residual."

### 14. MAJOR: generator bugs, and the draft is out of date with results/

- `make_draft.py` prints `beh['assumptions']['k_dig_uA']` = **0.3** as "µA per flipped accumulator bit". 0.3 is K_DIG of the unused
  'count' model. The quoted cases use K_BIT = **0.15** per flipped bit (`k_uA` 0.15 in `tvla.json`).
- §7's "Cost" bullet sits in a non-f-string. The draft prints the literal text `{a3['cell']['area_vs_2t2r']:.3f}` and
  `{w3 / avg2:.2f}`.
- The chip-level "0 failures" is hard-coded (`{'' if not mc3 else ''}0 failures`) and not read from `rtl_chip_1of3_110.log` (which
  does report 92,076 checks, 0 failures). So are "2,718 points", "97,631 checks", "1.56×", "1.5×" and the tile-model parameters. The
  header "every number below is read from results/" is therefore untrue.
- The draft was written at 11:17. After that, `tvla_circuit.json` gained 4T4R inputs (3.79, at 11:20; the draft shows [pending]) and
  `tvla_circuit_redraw.json` gained results (11:35). The mutation file now holds 28 of 28 caught (the draft says 14 of 14).
- The page's "Full mutation test on the option: N of N faults caught" (`full.py`) has no "of 122 planned / in progress" qualifier.
  The `leak3` section still shows "running" for files that exist.

*Fix:* repair the three code paths, read every quoted number from a file, regenerate the draft and the page, and add the paper's
numbers to `tests/test_claims.py`.

### 15. MAJOR: the argument against a compensation baseline is wrong

*Attacked:* §7 "A dummy compensation column needs one more device per weight as well".

*Evidence:* per-row compensation for 0–24 zeros with binary-weighted compensation devices needs ⌈log2 25⌉ = 5 devices per row, not
24. Per-weight minimality (§5) is a per-cell bound and says nothing about per-row schemes. Such a scheme stores the zero count in
devices and has to be programmed, which has its own leak and tracking problems. That is the honest argument.

*Fix:* "Per-row compensation can use as few as 5 binary-weighted devices per row, but it stores the zero count, which then leaks
when it is programmed and must track every LRS; one-of-three needs no such state." Simulate it next to the current-DAC baseline.

### 16. MINOR: "it programs with the same pulse counts"

*Evidence:* quasi-static, 12 devices. Identical per-device pulses are expected, because the slice and the device model are the same.
Per test bench, the device pulses differ (11,442 for one-of-three against 11,282 for 2T2R, council 02). From an erased array,
one-of-three sets every weight (24 sets per row), while 2T2R sets only the non-zero weights.

*Fix:* "each device reaches its targets in the same number of pulses as in the 2T2R macro (quasi-static, 12 devices); transient
programming and disturb are not simulated."

### 17. MINOR: "detects every invalid code"

*Evidence:* `sa_inv` (line 214) covers all five invalid patterns. It sets a sticky WERR without the column, only when the weight is
read, and the weight counts as 0.

*Fix:* "flags (WERR) every invalid code when it is read; the invalid weight counts as 0."

### 18. MINOR: the minimality argument

*Evidence:* correct for identical two-state devices and per-cell constancy: C(2, k) ≤ 2 and C(3, 1) = C(3, 2) = 3. The draft omits
k = 2 (two-of-three, which draws more current), and says nothing about per-row schemes (finding 15).

*Fix:* add "(k = 2 also gives three codes at twice the LRS current)" and "per cell".

### 19. MINOR: error detection (9 of 9, 2 of 6)

*Evidence:* verified by enumeration. One-of-three: 3 codes × 3 devices, and every flip gives 0 or 2 LRS. 2T2R: +1 and −1 each have
one silent and one detected flip, and 0 has two silent flips, so 2 of 6 are detected.

*Fix:* none to the numbers. Add that three devices per weight raise the defect exposure by 1.5×.

### 20. MINOR: "the spread of the LRS current over 30–120 µS is 0.50 µA"

*Evidence:* `lrs_spread_over_G_uA` = 0.4959 µA is a window/peak spread. The mean currents over 30–120 µS differ by only 0.029 µA
(2.2472 to 2.2761).

*Fix:* say "largest difference in a 10 ns window".

### 21. MINOR: "|t| from 580.75 to 0 on the duration"

*Evidence:* a constant duration has zero variance (the tool adds 1e-9 jitter), so t = 0 is degenerate.

*Fix:* "the duration is the same for every input".

### 22. MINOR: the accumulator fix 19.55 → 3.59 is attributed to the offset alone

*Evidence:* revision 4.6 → 4.7 also changed the start-row distribution.

*Fix:* run the offset alone, or say "revision 4.7 (offset and start row mod 72)".

### 23. MINOR: "1.50× the array read current"

*Evidence:* this is the SA supply current only (no row or bit-line drivers, no logic). Numbers check: 2.2517 + 1.0013 = 3.25 µA;
2 × 1.0013 = 2.00 µA; 4.25 µA; 4.2543 / 2.836 = 1.500; ratios 1.31, 1.62 and 1.79 also check.

*Fix:* "sense-amplifier read current".

### 24. MINOR: "transistor-level" overstates the tile model

*Evidence:* the tile's 72 SAs are drawn from 40 Monte Carlo samples of one SA, so samples repeat. Waveforms are interpolated in
log G between 5 LRS and 5 HRS points. There is no shared supply network and no bit-line parasitics.

*Fix:* "SPICE-derived waveform templates of the drawn SA, summed".

### 25. MINOR: different HRS mismatch between the models

*Evidence:* the behavioural model uses 0.018 µA (DC); the transient model uses 0.044 µA. Not discussed.

### 26. MINOR: a growing residual at low noise that the draft omits

*Evidence:* `tvla_1of3_noise1uA.json`: one-of-three weights rise from 2.70 (20k) to 4.08 (150k) at 1 µA. That is close to the
threshold and rising with N. The page reports it; the draft does not.

## Verdict

The central claim **does not survive as written**. In the draft's own default threat model (row-aligned reads through the margin
check), one-of-three fails a first-order, reprogrammed fixed-versus-random test (|t| 10.67 at 20,000 traces per group, about 28
predicted at 150,000). The cause is that the per-SA mismatch makes the current depend on the position of the LRS device. The shuffled
tests that the abstract and tables rely on can see neither this term nor per-row sparsity at all (finding 2). Under the current RTL,
the attacker can also calibrate the victim's SAs by reprogramming one row under LOCK, or bypass LOCK with a reset (finding 3).

What survives, and is still worth a paper: one-of-three removes the *dependence of row current on the zero count*. A profiled
attacker using another device cannot estimate per-row sparsity (correlation within ±0.05 against 0.90–0.97 for 2T2R), and the cell
is the minimum per-cell way to do this, at 1.56× cell and 1.53× macro area. The remaining first-order leak is device-specific: it
needs calibration of the victim, which the RTL must then forbid (refuse programming under LOCK, or erase-all; LOCK held across
reset). The paper needs: aligned and matched-zero-count tests; position and collision attacks with and without calibration; the
LOCK/programming fix and a precise threat model; device distributions consistent with program-and-verify; and the
generator repaired. Until then this is a TCAD/JETCAS simulation paper with a stated residual, not a TCHES "closes the leak" paper.
