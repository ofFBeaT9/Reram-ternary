# Paper v1: roadmap (14 November 2026)

m1frame, native pipeline (mode C). Follows `studies/paper-2026-11/` (draft 0.2, 8 November) and revision 4.9 (9 November).
Goal set by the owner: write the paper and improve it into impactful research; be ready for the meeting with Steven Bos (USN)
in the week of 16 November.

## 0. Recall (what is already known; not re-derived)

- Draft 0.2 claims: the 2T2R ternary code leaks each row's zero count through the read current (profiled attack, correlation
  0.90-0.97); a one-of-three cell removes that; a chip-specific position residual remains (row-aligned |t| 26.32) and a random
  sense-amplifier rotation removes it in the model (|t| 2.70). Costs: 1.56x cell area, 1.53x macro area, 1.50x read current.
- Open after draft 0.2 (its FINAL_REPORT): rotation not drawn and not in the RTL; tests with matched zero counts, more traces,
  k_sense, a margin-check read model, collision and template attacks; baselines; leakage at the programmed states; IEEE Xplore and
  patent search; 3T3R chip assembly; silicon.
- Revision 4.9 closed the two LOCK gaps of the red team.
- Contradiction on record: the 13 November dossier audit lists results that have no file (rotation RTL, closed proofs,
  co-simulation). They are not used here.

## 1. Analyst: brief

**Problem.** The one-of-three paper rests on waveform templates that do not follow the controller's read sequence, on 40
mismatch samples reused for 72 amplifiers, on equal bit-line capacitances, and on a prior-art search limited to the open web.
Each of these is a point a reviewer will press, and the meeting with Bos needs a defensible statement of what is new.

**Anchors.** `rtl/chip/tcim_actl.sv` (the sequence: precharge with the word line off, read, recharge);
`layout/sky130/next_3t3r/*.ext` and `results/sky130_chip/macro_rc.json` (extracted capacitances); `chip/sky130/sim/periph.spice`
(the drawn amplifier); ChipFoundry's PDK 3e0e31d models; the literature list of 8 November.

**Hypothesis (falsifiable).** A constant LRS count is necessary but not sufficient. Three further layers decide what the read
current tells: (L2) amplifier mismatch times LRS position, specific to a chip; (L3) bit-line capacitance asymmetry times LRS
position, the same on every chip, hence open to profiling; (L4) the devices' own conductances, a fixed pattern that carries no
weight information by itself. Prediction: rotation removes L2 and, by removing the chip-specific pattern, makes L3 visible to a
profiling attacker; only a balanced layout removes L3.

## 2. PM: requirements

- R1. Read-current templates that follow the controller's sequence, from SPICE of the drawn cells with ChipFoundry's models.
- R2. Every amplifier of a chip an independent mismatch sample (400 samples).
- R3. Bit-line capacitances from the drawn layouts in the model; sensitivity to routing imbalance.
- R4. Row-aligned tests of first and second order; a test with matched zero counts (position only); several fixed matrices.
- R5. Attacks: profiled zero count against the reads per row, up to 1.7e7; a bound on the information per row.
- R6. Rotation: switch matrix in SPICE (decode correct, cost), at the amplifier and at the array edge.
- R7. Trained weights and programmed device states as sensitivity cases.
- R8. Prior art: patents and papers on one-hot resistive cells, amplifier swapping, balanced bit lines, balanced NVM cells.
- R9. Paper draft 1.0 generated from result files; every number traceable; claims match evidence.
- R10. Meeting brief for Bos: what is new, what is asked of him, questions.
- Success: gate 2 passes with no claim above its evidence; an independent red team finds no blocker left unanswered.
- Out of scope in this run: layout of the rotation switch and of transposed bit lines (needs Magic on the PC); RTL of the rotation
  (planned next, with the mutation and formal flow); silicon.

## 3. Architect: design

- `chip/sky130/sim/seq_read.py`: decks for one line (mismatch Monte Carlo, shared nominal bias or per-sample bias), for the coupled
  lines of one column with its neighbors (drawn capacitances, balanced, transposed, +10 fF on one line), for the 3 x 3 switch matrix.
- `tools/leak_v1.py`: tile model (templates per amplifier sample and conductance quantile, layout correction per line and
  neighbor state, routing-imbalance term, rotation), tests (`tvla`), attack (`zeros`), bound (`bound`).
- `studies/paper-v1-2026-11-14/run_v1.py`: the experiment list; `make_paper.py`: the paper from `results/security/v1/`.
- Falsification points: (a) the 2T2R leak must reappear with the new templates; (b) a balanced layout must give exactly no
  nominal weight term; (c) the old headline numbers must be explained where they change.

## 4. Scrum master: stories

1. SPICE datasets (R1-R3, R6). Done when the files exist and the reads decode correctly.
2. Tile model and tests (R4). Done when 2T2R leaks, and the one-of-three results are stable over matrices.
3. Attacks and bound (R5, R7). Done when each result has its standard error or is a stated bound.
4. Prior art (R8). Done when each close item is read from its own page and placed in the related-work table.
5. Paper 1.0 and figures (R9). 6. Council and red team; gate 2. 7. Brief for Bos (R10); record and deliver.
