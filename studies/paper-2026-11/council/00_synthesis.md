# Council synthesis (8 November 2026)

Two specialist reviews ran as separate agents, each given the repository and no draft text:
`01_side_channel_reviewer.md` (TCHES side-channel lens) and `02_circuit_reviewer.md` (ReRAM CIM circuit lens).
A third, independent red-team agent reviews the draft after this synthesis (`03_red_team.md`).

## Where the reviewers agree

1. The encoding argument is sound: one-of-three is the smallest two-state-device ternary cell with a weight-independent
   number of LRS devices (C(2,1) = 2 < 3 codes; C(3,1) = 3). Reviewer 2 supplied the minimality argument; it is now in the draft.
2. The frozen-instance TVLA (`tvla_circuit.json`: 2T2R 12.14, one-of-three 22.16, 4T4R 21.54) does not test the weights. It
   tests one programmed device against the population and fails for every cell. Both reviewers read it this way. Reviewer 2
   read it as a contradiction of the headline, and it would be one if it were presented as a weight test. Resolution: the
   paper's weight test is the reprogrammed one (`--redraw`, `tvla_circuit_redraw.json`). The frozen test stays in the paper
   as a calibration that shows the test works.
3. The sparsity attack as first written (linear in the zero count of the summed current) is the weakest piece of evidence.

## Contradictions and how they were resolved (not averaged)

| Issue | Reviewer position | Resolution (with what ran) |
|---|---|---|
| Does the shuffle carry the result? | R1: first-order TVLA with a random start row sees only the matrix average; the margin check reads PROW under LOCK, so row-aligned reads are the default | Checked in `rtl/tcim_core.sv` (lines 23–25, 578): confirmed. Added `--aligned` to `tools/tvla_circuit.py`; a row-aligned reprogrammed run is queued (`tvla_circuit_redraw_aligned.json`). The threat model in the draft now states that row alignment is the default. |
| Is the attack strong enough? | R1: needs multivariate / template attacks | Added a second attacker (least squares on all five windows, profiled on 8 devices): 2T2R correlation 0.97, 70 % of rows exact; one-of-three −0.02, 17 % (the best-guess rate) (`attack_sparsity.json`). A position template attack needs each victim sense amplifier's own mismatch, which profiling on another device does not give, and reprogramming the victim erases the secret. This argument is in the draft. A systematic P/Z/N difference (extracted bit-line parasitics) is still untested. |
| Residual: LRS spread (plan) or HRS spread and mismatch × position (R2)? | R2: the SA clamps the LRS current, so HRS spread and per-SA mismatch dominate | Accepted. The LRS-spread sweep stays as a stress test (`_lrs0.7`, `_lrs1.2`). The draft names HRS spread and the position term as the residuals. |
| Cost | R2: read current is the missing cost, and it grows with sparsity | Added a table to the draft (from the `sa_transient.json` means): 1.31× with no zeros, 1.50× at one third, 1.62× at half, 1.79× at 70 % zeros. |
| Reliability | R2: under-sold. 9 of 9 single flips are detected, against 2 of 6 for 2T2R | Added to the draft (combinatorial argument, checked by hand). |
| Programming leak "unchanged" | R1: the same frozen-instance confound applies; from an erased array, set counts differ by cell | The claim is withdrawn from the draft and stated as a limitation, to be re-run with reprogrammed groups. |
| Sense-register switching | R1: K_SENSE leaks whether vertically adjacent weights are equal; clearing both stages between reads fixes it | Recorded as a proposal (no RTL change in this run). |
| Baseline the paper must beat | R2: a current-DAC flattener is cheaper | Added to the draft's discussion as the next comparison. Not simulated. |

## Strongest honest claim (merged)

In a transistor-level model of a signed-off SKY130 ternary ReRAM CIM tile, replacing the 2T2R cell with the one-of-three
3T3R cell removes the dependence of row read current on per-row weight sparsity that 2T2R shows. Profiled attacks reach a
correlation of 0.90–0.97 on 2T2R and none on 3T3R. The cost is 1.56× cell area and 1.5× read current at one third zeros.
Residual leakage from device instances, sense-amplifier mismatch and the digital periphery remains to be bounded, and
silicon is the decisive test.

## Venue (merged)

Both reviewers put the evidence below TCHES or JSSC acceptance as it stands. R1 lists about 10–14 working days of
simulation work (E1–E10) that could make TCHES 2027/3 (15 January 2027) reachable. R2's view is that without silicon this
is a TCAD or JETCAS paper. Plan: write for TCHES 2027/3 and run E1–E10. If the nested specific tests or the row-aligned
second-order tests show a residual leak, move to TCAD with the residual stated.

## After the red team (`03_red_team.md`, 26 findings)

The red team found three blockers. All three were checked and accepted; none was averaged away.

| Blocker | Check | Resolution |
|---|---|---|
| Row-aligned one-of-three leaks at first order (each sense amplifier's own mismatch × which device holds the LRS) | Re-run at 150,000 traces: 26.32 (leaks); 2T2R 394.41 | Accepted. The paper claims removal of the zero-count leak only. Proposed and modelled a fix: rotate at random, on every read, which of the cell's three sense amplifiers reads which device (`--sa-rotate`). One-of-three then gives 2.70 (passes); 2T2R gives 387.06 (the zero count is untouched). Proposal; not drawn, not in the RTL. |
| The shuffled test sees only the matrix-wide zero count (565 against 576 zeros) | Zero count recomputed from the tool's seed: 565 | Accepted. Per-row claims now rest on the row-aligned tests and the attacks. The shuffled table is kept, with its meaning stated. |
| The threat model contradicts the RTL: programming under LOCK, LOCK cleared by reset, readable results | Confirmed in `rtl/tcim_core.sv` | Stated in the draft's threat model and in STATUS 15.8. Proposal for the next revision: refuse PCMD + under LOCK, or erase the whole array first. The side-channel model assumes the results go only to the host. Not changed in the RTL in this run, because it would reopen the signed-off revision 4.7; that is the owner's decision. |

Majors fixed in draft 0.2:
- Title changed to "one-hot".
- The precheck is now attributed to ChipFoundry's shuttle precheck, on the 2T2R chip.
- 1.53× macro area added.
- 4T4R relabelled one-of-four.
- Device states: a SPICE run at the programmed states (`sa_programmed_states.json`), with both cost rows shown.
- Attack wording and the estimator artifact explained.
- Missing threats listed.
- Related work: A3, A6 and A26 added; D4 named as the 1-of-n origin.
- Generator bugs fixed: 0.15 µA, no hard-coded counts, and the stale results.
- The compensation argument corrected (5 devices per row).

Majors left open, stated in the draft:
- No matched-zero-count or multi-matrix tests.
- Trace budget limited to 150,000.
- k_sense off.
- No margin-check-specific read model.
- No template or collision attack.
- No current-DAC baseline.

## Verdict

A narrower claim survives. One-of-three removes the zero-count signal that a profiling attacker can exploit across chips, at 1.56×
cell area and 1.53× macro area. A chip-specific position residual remains; a sense-amplifier rotation removes it in the model. Two
logic gaps (programming under LOCK, LOCK after reset) must close before the security claim holds for the system.

Venue: as it stands, IEEE TCAD or JETCAS. TCHES 2027/3 (15 January 2027) becomes realistic only with:
- the rotation drawn and in the RTL;
- the LOCK fix;
- the open tests (matched matrices, more traces, k_sense, collision and template attacks).
