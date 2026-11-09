# Final report: 3T3R follow-through and paper study (8 November 2026)

## Verdict

The 3T3R one-of-three cell is a real but narrower contribution than first claimed. It removes the weight-sparsity (zero-count)
leak of the 2T2R ternary cell. That leak is the one a profiled attacker exploits across chips: correlation 0.90 to 0.97 on 2T2R,
about 0 on 3T3R. The red team found a chip-specific residual in row-aligned reads: each sense amplifier's own mismatch, combined
with which device holds the LRS, gives |t| 26.32 at 150,000 traces per group. A new proposal removes that residual in the model:
rotate at random, on every read, which of a cell's three sense amplifiers reads which device (|t| 2.70).

Two logic gaps must close before the security claim holds for the system:
- programming runs under LOCK;
- reset clears LOCK.

All results are about the model, not silicon.

Paper: draft 0.2 (`DRAFT.md`), generated from `results/`. As the evidence stands the realistic venue is IEEE TCAD or JETCAS.
TCHES 2027/3 (deadline 15 January 2027) needs the open items below.

## What was done (the "not done" list)

| Item | Result | File |
|---|---|---|
| Periphery and analog macro, 3T3R | 1566.3 × 1950.5 µm (1.53× the 2T2R macro area); DRC 0; LVS match; planted fault caught | `results/next_chip/macro3_layout.json` |
| Programming through the drawn drivers | set 7 / 8 / 7 pulses (tt / ss / ff), reset ≤ 7; same as 2T2R per device; disturb 0.0 µS (quasi-static) | `results/next_chip/macro_sim3.json` |
| Array controller with Z, chip test bench | 92,076 checks, 0 failures; 6 of 6 Z faults caught | `results/next_chip/rtl_chip_1of3_110.log`, `mutation_chip_1of3.json` |
| Formal safety proof on the option | PASS; 3 of 3 planted Z faults make it fail | `results/next_chip/formal_1of3.log`, `formal_faults_1of3.json` |
| Full mutation test on the option | 122 of 122 faults caught (`TB_CELL=1of3full`) | `results/rtl_mutation_1of3full.json` |
| Transistor-level read simulation | SA transients with 40 mismatch samples; programmed-state run | `results/security/sa_transient.*`, `sa_programmed_states.json` |
| Leak model with circuit data | frozen, shuffled, row-aligned and rotation tests for 2T2R, 3T3R and 4T4R | `results/security/tvla_circuit*.json` |
| Attack | two profiled attackers | `results/security/attack_sparsity.json` |
| Literature search (dedicated agent) | 70 entries; no one-of-three ReRAM cell for side-channel resistance found (web only) | `LITERATURE.md` |
| Council: 2 specialists + independent red team | 3 papers + synthesis; 3 blockers accepted and resolved or stated | `council/` |
| 3D visual for 3T3R | Fig A′ on the page (P/Z/N paths, Z lit for weight 0) | `docs/page/fig3d_3t3r.py` |
| Page, STATUS, claims | section 13d, 3T3R board, STATUS 15.8; 645 claims, 0 stale | `docs/TCIM0_explainer.html`, `docs/STATUS.md` |

## Open, in order of value for the paper

1. Draw the sense-amplifier rotation (a 3:1 switch per amplifier) and put it in the RTL with its decode; then test, prove and mutate
   it.
2. Refuse programming under LOCK, or erase the whole array first. This changes revision 4.7's signed-off logic, so it is the owner's
   decision.
3. Tests the red team asked for:
   - matched-zero-count and multi-matrix tests;
   - more than 150,000 traces;
   - k_sense on;
   - a margin-check read model;
   - collision and template attacks on the position term.
4. Baselines: a current-DAC flattener and per-row compensation.
5. Run the leakage again at the programmed device states; transient programming.
6. IEEE Xplore and patent search; read the closest papers (A4, A6, A8) in full.
7. Assemble the 3T3R chip and run the precheck.
8. Silicon.
