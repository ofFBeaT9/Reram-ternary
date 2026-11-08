# QA gates

## Gate 1: the roadmap and the input PDF (4 November 2026)

### The PDF's statements about TCIM0, checked against the design as built

| # | PDF statement | TCIM0 as built (source) | Verdict |
|---|---|---|---|
| 1 | TCIM0 is read "via column ADCs"; fix: current-flattened ADC | SKY130 chip: 48 current-mode sense amplifiers, digital sums; analog SUM answers zero counts (ARCHITECTURE.md 2.1) | Does not apply as written; the sense amplifier's supply current is the analog read leak to check (S5) |
| 2 | Leakage test on "one 64-row ternary ReRAM column" | 72 rows x 24 columns | Its numbers are not TCIM0's; re-measured on TCIM0's model (S1) |
| 3 | Device "Ti/HfOx/Pt" | TiN / Ti / HfO2 / TiN (SkyWater ReRAM documentation) | Wrong device for TCIM0 |
| 4 | Constant-sum cells: w = 0 as two mid-conductance devices | Two states per device by design; a mid level is not a published SkyWater state | Not buildable as proposed; replaced by one-of-three encoding (two-state devices) |
| 5 | 0.5 % write-verify accuracy needed | SkyWater after set: 30-120 µS (factor 4 spread); verify here is a threshold, not a target | Not achievable; whether it is needed depends on how much of the device spread reaches the supply (S5) |
| 6 | Writing -1, 0, +1 takes different pulse counts and leaks | 0 needs two resets, +/-1 one set and one reset; counts depend on devices; PITER shows them | Applies (F3) |
| 7 | Zero-skipping timing trap is a TRITONE issue | tcim_core also skips rows with input 0 (revision 4.2) | Applies to TCIM0 too; the PDF missed it (F1) |
| 8 | Bit lines held at a fixed voltage when idle | Already so: every line grounded in IDLE, checked every cycle (make rtl-chip) | Already met; idle impedance to be measured (S5) |
| 9 | Isolated array supply | Macro 1.8 V and digital share vccd1 and vssa1 (top.py) | Applies (F10) |
| 10 | DExiM reads stored data from idle package impedance | Devices sit behind off select transistors between grounded lines when idle | To be measured, expected to be blocked (S5) |
| 11 | Lint gate, netlist = RTL proof | make lint (0 warnings), make equiv / equiv-chip (proved) exist | Already met; re-run after the change |
| 12 | "Masking is unproven for analog CIM" (PDF's own caveat) | — | Agreed; input masking is not applied to the analog path |

### Findings on the roadmap and how they are folded in

1. Constant-time programming raises the reads per program command to 44 verify reads; read disturb at 0.2 V was
   analysed in revision 4.4 for far more reads, so this is within it. State it on the page.
2. The empty reset pulse puts VPRG on every bit line and source line at once with the word line on: no voltage across
   any device, but the board's VPRG supply charges 48 bit lines and 24 source lines. State it; no device stress.
3. The shuffle seed is a free-running LFSR: deterministic after reset, so an attacker who controls the GO timing can
   control the start row. The chip has no random-number source. State it as a limit; do not call it random.
4. Products become slower for sparse inputs (always 72 row reads). Zero-skipping stays available as opt-in.
5. The margin check uses the existing verify references, so it needs no new analog circuit.
6. The one-of-three cell cannot go on this tape-out (new array, 24 more bit-line slices, new layout); it is modelled
   and simulated now and specified for the next chip. Sensors (F9) and decoupling (F10) likewise need new drawn
   circuits: specified, not drawn, unless time allows.

Gate 1: **PASS with concerns** (findings 3 and 6 are limits to state, not defects).

## Gate 2 (7 November 2026): the executed work and the council's findings

Audit of revision 4.7 against the council's findings (`council/03_resolution.md`) and the results files. `make test` passes:
584 numbers, 0 stale. Section 26 of `tests/test_claims.py` checks every number that STATUS section 15 and the explainer
quote for revisions 4.6 and 4.7.

| Item | Evidence | Verdict |
|---|---|---|
| H1 uniform start row | `lfsr_m72 == lfsr % 72` proved (k-induction, depth 20); 910 or 911 LFSR states per row | closed |
| H2 input leak through bit flips | random offset; model 2: inputs \|t\| 3.59 (4.6: 19.55) | closed in the model |
| H4 weights readable under LOCK | read-back refused, margin check keeps PDATA; tests in `tb/tb_tcim.cc`; proof properties with planted faults caught | closed |
| H5 upset re-enables an option | uses gated by ~LOCK; mutation faults; not testable without an upset (stated) | closed, with a stated limit |
| H3, H6, H7, H8 | stated as limits on the page and in STATUS 15.4 | stated |
| V1 page quoted old proofs | the page reads `results/formal.log`, rebuilt from batch 28/28b logs of the final RTL (md5 8cc900b8) | closed |
| V2 make formal and check_faults | pipefail, miter inside `make formal`, base proofs required; `JOBS` added | closed |
| V3 logs tied to inputs | `flow/eda/batch28/md5_formal_inputs*.txt`; `results/rev47/same_logic.json` for the simulation runs | closed |
| V4, V5, V9, V10, V12 | properties, faults and harness fixes in place; 28 of 28 planted proof faults caught | closed |
| Physical design | block routed again (batch 28), timing at all corners, GLS with both planted faults detected, LVS, DRC 0, antenna 0 in both checkers, ChipFoundry precheck 14 of 14 on the final GDS (batch 28c) | closed |

Found during gate 2 and fixed: the start-row proof at depth 3 did not catch its planted fault, so the depth is now 20.
Batch 27 left one net at OpenROAD's antenna limit that Magic put 5 % over, so an antenna pass was added and the block was
routed again. `results/rev45` was incomplete in the restored repository and was rebuilt from the PC's archives of
12 October (`results/rev45/README.md`).

Open: weights leak through the 2T2R cell (next chip); no true random source; reset clears LOCK; the FPGA demonstrator
no longer fits its FPGA.

Gate 2: **PASS with concerns** (the concerns are stated limits, not defects).
