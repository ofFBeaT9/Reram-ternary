# QA gates, paper v1

## Gate 1 (roadmap, 14 November 2026)

- The hypothesis predicts a result that weakens the earlier headline (rotation exposes a design-wide leak). The run must report
  it either way.
- New templates change every leakage number of draft 0.2. The paper must say so and must not mix old and new numbers in one table.
- Routing capacitance of the 3T3R macro is not extracted. Any routing-imbalance result is a sensitivity (per fF) or an assumed
  spread, labelled as such; the array part is from the drawn cell.
- The bound is a Gaussian-channel bound under stated noise; it is not a security proof. Say so.
- Per-amplifier mismatch with a shared nominal bias leaves out the reference generator's own mismatch, which is common to a chip.
  Run the per-sample-bias set as a check and report both spreads.
- Rotation in the RTL and both layout changes are not done in this run: the paper says "simulated at circuit level, not drawn,
  not in the RTL".
- Prior art found before the experiments (US 9,704,576: one LOW-R element of three for a TCAM state; TSMC's "symmetric read
  current profile" patents: random swap of two sense amplifiers; dual-rail routing balance in secure logic) narrows the novelty
  claim. The paper claims the analysis, the numbers and the open design, not the code or the swap.

Gate: PASS with concerns (compute: two cores; the layout items stay open).

## Gate 2 (executed work, 14 November 2026)

Council: not run. The owner asked to finish without a full council after the session hit its limit; this gate is a
single-reviewer audit by the author of the run, which is weaker than an independent red team. An independent review is the
first item of the next steps.

Checks made:

- **Falsification points of the roadmap.** (a) The 2T2R leak reappears with the new templates (correlation 0.80 from one read;
  row-aligned |t| 529.55). (b) A balanced layout gives no nominal weight term: SPICE of the balanced and of the transposed
  column returns identical currents for the three weights. (c) The 8 November numbers changed for three stated reasons: the
  read sequence, 400 independent amplifier samples with a shared bias, and the layout terms.
- **The hypothesis.** Confirmed in the model: as drawn, the one-of-three cell gives the zero count back (0.56 at 65,536 reads,
  0.90 at 1,048,576); rotation does not change that; balanced lines do; position-only tests leak as drawn with and without
  rotation and pass for the balanced, rotated cell. The prediction that rotation would make the layout term more visible by
  removing the amplifier pattern is only weakly seen (0.93 against 0.90 at 1,048,576 reads, 0.98 against 0.95 at 16,777,216), because the amplifier term is
  smaller than the 8 November draft assumed. The paper does not claim that effect.
- **Numbers.** `PAPER.md` is generated; every leakage number is read from `results/security/v1/`. The brief's numbers were
  checked by hand against the same files.
- **Seeds.** A leak appeared in the precharge cycle of the one-of-three tests, where the model has no weight-dependent term.
  Cause: the mismatch seed was not applied (see FINAL_REPORT, "A fault in its mismatch data"), so an amplifier's LRS and HRS
  templates came from different samples. Fixed, asserted in the script, and every result produced again. The same fault is in
  the 8 November dataset; its position numbers are withdrawn.
- **Estimator.** The first version of the attack fitted noise-free profiles by plain least squares and failed on 2T2R
  (correlation 0.05 from one read). Replaced by the linear minimum-mean-square-error estimate for the given number of reads, with
  a stated ridge of 1e-5 µA². The ridge matters only above 1e7 reads.
- **Prior art.** Three patents and two papers found on 14 November narrow the claim: the code [P1], the amplifier swap [P2]
  and the bit-line imbalance of dual-rail memory [P3] are not new. The paper says so in the introduction. The patent front
  pages could not be opened as text here: inventors, assignees and dates of P1 and P3 are from Google Patents and Justia
  pages; P2's assignee and inventors are from search-result text for the family (US 10,706,918, US 11,621,037) and must be
  checked on the front page of US 10,269,420 itself.

Findings that stay open (in the paper's limitations):

- One corner, no supply network, no bit-line resistance, lumped line capacitances.
- The transposed column's term between neighboring columns is not simulated.
- Routing of the 3T3R macro is not extracted; the routing results are a sensitivity and an assumed spread.
- The bound is zero for the balanced, rotated cell by construction of the model (identical nominal lines). On silicon, residual
  asymmetry will remain; the claim is "none in this model up to 1.7e7 reads", not "secure".
- Trained weights: one small network.
- References A–F carry over from the 8 November list and are not re-opened here.

Gate: PASS with concerns. No claim in the paper stands above its evidence as far as this audit sees; the evidence is a model.
