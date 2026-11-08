# Audit of roadmap revision 3 — 6 October 2026

Short form of section 20 of the roadmap. The audit asked six questions, each with a method that
could prove the work wrong. The numbers of the logic in this file are those of 6 October (kept in `results/rev4`).
Revision 4.1 changed the logic the day after (section 21 of the roadmap), and revision 4.2 on 8 October changed the
product sequencer and added lint, a second simulator, formal proofs and place and route (section 22, `docs/STATUS.md`).
Revision 4.3 on 9 October added clock gating by synthesis and repeated the fault campaigns, the gate-level runs (now
also with a stuck clock-gate enable) and place and route on the gated design (section 23).
The gaps listed under "What the audit did not cover" that those close are marked there.

| Question | Method | Outcome |
|---|---|---|
| Does every quoted number match a stored result? | `tests/test_claims.py` | 232 numbers, 0 stale |
| Are the results right, or only reproducible? | `tests/test_independent.py`: second methods that share no code with the first | 9 checks, all agree |
| Do the tools agree with an outside reference? | `circuits/gnucap/pdk_check.py`: Gnucap against the PDK's ngspice reference data | 4,264 points within 0.1 % |
| Would the test bench notice a broken design? | `tb/mutation_test.py`: 66 copies of the RTL with one fault each | revision 3 test bench missed 30; revision 4 test bench 0 |
| Is the code right? | reading the RTL, the device model and the scripts against the text | two RTL faults, a wrong speed limit, one wrong description, one wrong conclusion |
| Are the external facts still right? | each fact the plan depends on read again from the page text | four changes |

## What was wrong, and what was done

**External facts**

- IHP's open-source runs are not free any more. The free runs of 2023 to September 2025 were funded by the
  FMD-QNC project. Now: SG13G2 €2,800 per mm², SG13CMOS5L €1,500 falling to €900 per mm², packaging extra.
- IHP states that MEMRES comes with a design kit that includes layout and a Verilog-A simulation model.
  It replaces the stand-in model of `model/`. First question to IHP.
- IHP's 2021 announcement says HfO2 and Al2O3 switching layers are used in combination; the device papers
  describe a single Al-doped HfO2 layer.
- MEMRES runs are marked "lower priority" by IHP. Tiny Tapeout's listed analog prices are for SKY130, and
  its IHP templates list no 3.3 V supply.
- The compact-model paper has three slips besides the kinetic values (see `docs/STATUS.md`, section 2).
- An automatic page summarizer invented table values for two papers during the audit. All numbers were taken
  from page text read directly.

**RTL** (`rtl/`)

1. `irq = IE & (DONE | WERR)`: reading STAT clears DONE but not WERR, so the interrupt of a failed command
   could not be acknowledged. Now `irq = IE & DONE`; WERR never occurs without DONE.
2. The serial port's 7-bit bit counter wrapped after 128 clocks; clocks after the 16th byte of an over-long
   frame were decoded as a new frame. Now it stops at 64 until chip select rises.
3. Program and read-back commands cleared WERR but not SAT. Now every command clears both.
4. The header of `tcim_spi.sv` allowed a serial clock of clk/4. At that speed every transfer is wrong (MISO
   changes up to three clock cycles after the falling edge). The limit is clk/8; clk/6 still works in
   simulation (`tb/extra/spi_speed.cc`, `results/spi_speed.log`).

Left as it is, and now written down: the Y registers are valid only while BUSY is 0; a read of STAT clears DONE
as soon as the address byte has arrived, even if the frame is then cut short; clearing EN does not stop a running
command; `arr_ack`, the sense and converter inputs and the release of `rst_n` are assumed synchronous to `clk`.

Synthesis, the gate-level check and the energy estimate were run again: core 7,234 cells
(revision 3: 7,282), 27.3 pJ per cycle (27.6), 3.43 nJ per product (3.47).

**Test bench** (`tb/tb_tcim.cc`): from 60,401 to 71,598 checks. Added: a monitor on every programming
pulse (amplitude sequence, reset before set, no pulse on a device that passed verify or must not change,
right row, PITER equals pulses delivered); directed tests for each missed fault; exhaustive tests of all 729
result values, all 657 invalid row indices, and the unused trit code in every register that takes trits.

Faults the revision 3 test bench did not detect (30 of 66):

- a cell with both devices in LRS counted as +1
- invalid cell not flagged during read-back
- product read uses the set-verify reference
- no pulse limit in the reset phase
- no pulse limit in the set phase
- reset pulses not counted in PITER
- positive clip limit off by one
- negative clip limit off by one
- SAT flag never set
- interrupt ignores the enable trit
- negative row index accepted
- register writes accepted while busy
- program command works without EN
- GO works without EN
- WERR not cleared by GO
- code 10 treated as -1
- serial port: interrupt flag not reported
- interrupt held by WERR (revision 3 behaviour)
- serial port: bit counter wraps on a long frame (revision 3 behaviour)
- reset pulses repeated on devices that already passed verify
- set amplitude not restarted after the reset phase
- PITER not restarted by a new program command
- SAT not cleared by GO
- SAT not cleared by a read-back command
- DONE not cleared by GO
- MODE changed while busy
- read-back works without EN
- serial port: a write frame also launches a read
- pulse limit one step short
- read-back of an invalid cell returns +1

**Description and conclusions**

- The tile model has one source line per column pair, not per row. Each carries at most 1.2 mA while
  programming. The 12–29 mA of a row is a requirement on drivers and supply, not on the lines.
- The cell area used a pitch into which the 4.5 µm transistor does not fit. Lower bound from the layout
  rules: 0.018 mm² per tile (`model/cell_footprint.py`). With the shorter row pitch the uncalibrated
  analog error of the thin-metal wiring falls from 0.55 to 0.46 result steps (`array/exp_pitch.py`),
  so the assumed 2.0 µm stays as the cautious value.
- The PDK's "identical output" tests compare Gnucap with Gnucap. A comparison with ngspice data was added.
- The printed kinetic values set at 0.21 V (continuous ramp) to 0.25 V (0.05 V staircase), not "0.25 V".
- "Exact" for digital mode now carries its conditions; the network accuracy its missing validation set.
- After a reset pulse Gnucap can leave the gap up to 0.11 nm above the model's 1.8 nm limit (time-step
  overshoot), and `circuits/gnucap/cell.py` stored and passed on that value. It is now limited to the model's
  range. All three corners were run again: 139 of 142 stored values are reproduced exactly; the 3 that changed are the reset gaps that had overshot the 1.8 nm limit (1.80, 1.84 and 1.91 nm). No quoted number depended on them.

## Independent re-derivations

| Check | Result | Detail |
|---|---|---|
| tile solver equals element-by-element nodal analysis | agrees | largest relative difference 5.2e-11 over 8 configurations |
| analog RMS error equals the closed-form value | agrees | closed form 0.422 steps, tile model 0.407 steps |
| digital-mode misread probabilities and Monte Carlo counts agree | agrees | mc_LRS3_x3_vos2mV: 4 observed, 6.7 expected; mc_LRS1_x1_vos0mV: 2 observed, 6.6 expected; mc_LRS1_x2_vos2mV: 4616 observed, 4732.2 expected |
| set voltage in the ramp, general ODE solver against the three implementations | agrees | LSODA 0.66949 V; largest difference 0.26 mV |
| published kinetic values give a set voltage far below the measured 0.65-0.75 V | agrees | 0.213 V |
| read-disturb time at 0.29 V, ODE solver against the reference model | agrees | LSODA 183 s (cell alone), reference model 200 s (with transistor) |
| static cell currents at the published gap values | agrees | 0.95 nm: 17.31 uA, 0.85 nm: 24.74 uA, 0.73 nm: 37.98 uA, 1.88 nm: 0.62 uA |
| energy table recomputed from the raw currents, capacitance and toggle counts | agrees | sense amplifiers 0.1941 nJ, word lines 0.0628 nJ, logic 3.498 nJ |
| clock energy per flip-flop is in the range of the library data | agrees | 30.5 fJ per flip-flop per cycle, 668 flip-flops |

## What the audit did not cover

- It is not an independent review: same assistant, same tools. A person who has designed ReRAM circuits
  should read this.
- The device model is still unvalidated against any device.
- The logic is tested, not proven: no second simulator, no lint, no formal proof, no timing analysis at the
  time of the audit. (Revision 4.1 added timing analysis before layout and equivalence proofs; revision 4.2 added
  lint, Verilator as a second simulator, formal proofs of the sequencers, and place and route with timing after layout.)
- The analog blocks around the logic do not exist; the test bench talks to a behavioural array.
- The energy estimate was checked for arithmetic and plausibility only.
- Sources read only through a page reader: Leti/CMP announcement, KV260 brief, thermal-model review, synapse
  proposal abstract, Tiny Tapeout news item, RAELLA abstract. Not read: the REBEL-6 paper text.

## Re-running the audit

```
make test        # re-derivations and quoted numbers, seconds
make pdk-check   # transistor models against the PDK references, minutes
make rtl         # test bench, about five minutes
make mutation    # fault injection, about an hour on two cores
```

The comparison with the revision 3 test bench (kept in `tb/rev3/`, results in `results/rtl_mutation_rev3.json`):

```
TB_SRC=tb/rev3/tb_tcim_rev3.cc TB_TAG=_rev3 python3 tb/mutation_test.py && python3 tb/mutation_merge.py _rev3
```

`results/gnucap_cell_W4.5.rev3.json` holds the cell results as stored before the audit, for comparison.
