# 3T3R completion and paper (8 November 2026), m1frame mode C

**Recall.** Decided today: next chip = 3T3R one-of-three. Done today: RTL option `TCIM_CELL_1OF3` with test bench (97,631
checks) and 7/7 Z faults; drawn 3T3R cell and array (DRC 0, LVS). Open (STATUS 15.7): periphery and macro, array
controller and chip test bench with Z, formal proofs and full mutation test on the option, transistor-level simulation of
the cell, leak model with circuit data. Owner wants a publishable contribution; novelty not yet established.

**Analyst.** The candidate contribution is a side-channel-hardened ternary ReRAM CIM tile on an open PDK: three logic
countermeasures (fixed latency + LFSR start row, random accumulator offset, constant-time programming) and a
constant-conductance 3T3R cell against the sparsity leak that logic cannot remove. The weakest point for a reviewer:
leakage evidence comes from a behavioural model with DC sense-amplifier currents. Hypothesis: transient, transistor-level
read currents of the drawn periphery (with mismatch) still show the 2T2R sparsity leak and its removal by 3T3R.

**PM.** Goal: finish the 3T3R items that can be finished in this workspace, strengthen the evidence to paper level, and
produce a paper plan and draft. Requirements: every number from a script in the repository; the 2T2R chip unchanged and
re-proven; literature search by a dedicated agent. Success: (1) circuit-level TVLA for 2T2R vs 3T3R; (2) 3T3R
programming through the drawn drivers; (3) controller + chip test bench with Z, controller mutation; (4) formal safety
proof and full mutation test on the option; (5) 3T3R analog macro drawn with DRC and LVS; (6) page, STATUS, git updated;
(7) paper outline + draft. Out of scope: chip-level re-assembly and precheck of a 3T3R chip (needs the digital block
re-placed and routed on the PC with 48 more macro pins, and ChipFoundry's ReRAM answer first), silicon.

**Architect.**
- E3 `chip/sky130/sim/sa_transient.py`: transient read of one bit-line slice + sense amplifier from `periph.spice`,
  device at LRS / HRS spread, Monte Carlo mismatch; supply-current templates; `tools/tvla_circuit.py` builds row traces
  (48 or 72 slices, mismatch frozen per slice, devices drawn from SkyWater's spread) and runs the same Welch test.
- E9 `chip/sky130/sim/macro_sim3.py`: the quasi-static programming of `macro_sim.py` with a third device; checks that
  programming P leaves Z and N (unselected, same row) unchanged.
- E4 `rtl/chip/tcim_actl.sv` + `tcim_chip_core.sv`: Z bit line (`prg_z`, `sa_z`) under the same option; `make rtl-chip`
  with the option; `mutation_chip.py` on it.
- E5 `formal/tcim_core.sby`: a task with `TCIM_CELL_1OF3`; Z versions of the pulse-mask properties.
- E6 full `tb/mutation_test.py` with `TB_CELL=1of3` and the MZ list appended (on the PC if the sandbox is too slow).
- E7 `layout/sky130/next_3t3r/macro3.py`: `macro.py` with a Z bit-line slice per column on the 3T3R array; DRC, LVS.
- E10 paper: `studies/paper-2026-11/PAPER_PLAN.md` and `paper/` draft.

**Scrum.** Stories in order E3, E9, E4, E7, E5, E6, E10, page/git; each closes only with its result file in `results/`.
