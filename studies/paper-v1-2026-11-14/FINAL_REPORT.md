# Paper v1: final report (14 November 2026)

m1frame, native pipeline (mode C). Files: `PAPER.md` / `PAPER.pdf` (draft 1.0), `BOS_BRIEF.md` / `BOS_BRIEF.pdf`,
`ROADMAP.md`, `QA_GATE.md`, `run_v1.py`, `figures.py`, `make_paper.py`; code `chip/sky130/sim/seq_read.py`, `tools/leak_v1.py`;
results `results/security/v1/`.

## Verdict

The one-of-three cell does what it was drawn for, and that is less than the 8 November draft said. It removes the zero count
from the read current. As drawn, its bit lines give the count back to an attacker who profiled another chip, at about 10⁵ to 10⁶
reads per row instead of one to a few hundred. Sense-amplifier rotation does not change this. Equal bit-line capacitances do.
The paper is rewritten around this result under the title "One of Three Is Not Enough".

## Evidence (all from the model; nothing measured)

- Read-current templates in the controller's order, SPICE of the drawn circuits, ChipFoundry PDK models, 400 mismatch samples in
  two conventions (shared reference bias: 27 nA sd per amplifier on an LRS read; per-sample bias, 100 samples: 120 nA).
- Bit-line capacitances of the drawn 3T3R cell from Magic's extraction: 15.5 / 10.7 / 14.7 fF (P / Z / N) over 72 rows,
  coupling 5.57 fF in a column and 7.01 fF between columns. A zero weight draws +29 nA in the first read cycle and −27 nA in the
  recharge cycle against a non-zero weight. Balanced and transposed columns: no difference.
- Profiled zero-count attack (correlation at 1 / 4,096 / 65,536 / 1,048,576 reads per row): 2T2R 0.80 / 1.00 / 1.00 / 1.00;
  one-of-three as drawn 0.00 / 0.20 / 0.56 / 0.90; with rotation 0.00 / 0.22 / 0.58 / 0.93; balanced with rotation 0.00 / −0.02 /
  −0.02 / −0.01 (and −0.02 at 16,777,216).
- Row-aligned tests, 150,000 traces per group: see Table 3 of the paper.
- Bound on the information per row (38.0 bits) at 10⁶ reads: 2T2R 6.8 bits, one-of-three as drawn 3.8 bits, balanced with
  rotation 0 bits.
- Rotation switch matrix in SPICE: every weight decodes for every shift; 0.7 % more read charge.
- Cost: 1.56× cell area, 1.53× macro area, 1.50× read charge at one third zeros. Silent single-weight errors at a flip
  probability of 10⁻⁴: 1.3e-4 (2T2R) against 2e-8.

## What changed against the 8 November draft

- Its waveforms started with the word line on; the controller precharges with the word line off. All leakage numbers are new.
- Its amplifier term (|t| 26.32, 0.126 µA sd) included the reference generator's mismatch, which is common to a chip. The
  amplifier term proper is about four times smaller.
- **A fault in its mismatch data.** `set rndseed` in `.spiceinit` (`chip/sky130/sim/spice.py`) has no effect with ngspice 42: two
  runs with one seed give different samples. In `results/security/sa_transient.npz` the "same" amplifier at 60 and at 120 µS
  differs with an sd of 0.129 µA, which is √2 times the spread over seeds (0.091 µA): the samples are independent. The tile model
  of 8 November therefore interpolated between unrelated amplifiers, and its position numbers (26.32 without rotation, 2.70 with)
  are withdrawn. The same fault was in the first Monte Carlo sets of this run; it showed as a leak in the precharge cycle, where
  none can exist. `seq_read.py` now sets `.option seed=` in the deck and asserts that one seed gives one amplifier (precharge
  currents within 0.01 µA; measured 0.004 µA). Every result of this run was produced again after the fix. Scripts that use seeds
  only for distributions (`periph_sim.py`, `mc_libcheck.py`) are not affected in their statistics.
- Its claim "rotation removes the residual" holds only for the amplifier term. The bit-line term was not in that model.
- Prior art found on 14 November: the one-of-three code (Rambus, TCAM), the amplifier swap (TSMC), bit-line imbalance of
  dual-rail memory (Infineon). The paper now claims the analysis and the numbers, not the code or the swap.

## Caveats

- No council and no independent red team in this run (owner's instruction after the session limit). Gate 2 is a self-audit.
- The first run of the row-aligned tests was stopped when the session's environment shut down; the list was trimmed (no
  routing-imbalance rows, three extra matrices instead of five) and run again, and once more after the seed fix.
- One corner, no supply network, no bit-line resistance; routing of the 3T3R macro not extracted; noise level assumed.
- Rotation and balanced bit lines are not drawn and not in the RTL. The owner's PC was not used: its shell is limited to
  180 s per call and cannot start Docker, and the sandbox ran everything needed (ngspice 42 and ChipFoundry's models).
- P2's bibliographic details need a check on the patent's front page.

## Next steps

1. Independent red-team review of `PAPER.md` and `tools/leak_v1.py`.
2. Draw the balanced cell or the transposed column on the PC (Magic), extract, re-run `run_v1.py` on extracted values; extract
   the 3T3R macro's routing.
3. Rotation in the RTL (controller option) with tests, injected faults and proofs; draw the switch.
4. Current-flattener baseline; corners; a supply-network model; template attack on the position terms.
5. Send the questions to ChipFoundry, IHP and the REBEL-6 group; meeting with Bos (brief attached).
6. Preprint after steps 1 to 3.
