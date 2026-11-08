# TCIM0 on SkyWater SKY130 (sky130B): chip architecture

Started 11 October 2026. Target: ChipFoundry's analog harness (Caravan, `caravel_user_project_analog`): user area about
2.92 × 3.52 mm, 27 general-purpose pads (`io_in/out/oeb`), 11 direct analog pads without ESD (`io_analog[10:0]`),
18 GPIO with an analog path (`gpio_analog`), supplies vccd1/vccd2 1.8 V, vdda1/vdda2 3.3 V. Everything below is a
**proposal** until it is designed, simulated, drawn and checked; the status of each block is in `STATUS_CHIP.md`.
Revised the same day: controller written and verified (revision 2: shared controls and NOR ground switches),
pads assigned, periphery and macro drawn (section 2).

## 1. Operating conditions of the SkyWater ReRAM (sky130_fd_pr_reram v2.0.3, technology specifications)

| Operation | Word line | Bit line | Source line | Pulse | Published yield |
|---|---|---|---|---|---|
| Form | 1.4–2.5 V (0.1 V steps) | 2.4–3.3 V (0.1 V steps) | 0 | 1 µs | 92.73 % (1T1R), 99.80 % (1T4R #9) |
| Set | 1.7 V | 2.4 V | 0 | 1 µs | 97.45 % |
| Reset | 2.5–3.0 V | 0 | 2.4–3.0 V | 1 µs | 90.83 % at 2.5 / 2.6 V; 99.41 % stepped |
| States | pristine < 0.1 µS; after form or set 30–120 µS; after reset about 4.5 µS | | | | |

Every level is at most 3.3 V, so all array-side circuits use the 5 V transistors (`nfet_g5v0d10v5`,
`pfet_g5v0d10v5`, L ≥ 0.5 µm) and the 3.3 V supply vdda1. No forming path beyond 3.3 V is needed on SKY130.

## 2. Blocks

```
 GPIO (1.8 V) ── tcim_top (serial port + TCIM0 core, verified) ── arr_* ── tcim_actl (array controller) ──┐
                                                    rtl/chip/tcim_chip_core.sv = both, arr_adc tied to 0   │
                                                                                                          ▼
 analog macro (vdda1 3.3 V / vccd1 1.8 V):        wl_on[71:0], blp_prg[23:0], bln_prg[23:0]   (one per line)
   ctrlglob: 4 level shifters, ground NOR of the   bl_sen, flt, sl_prg, wl_prog, ref_sel[2:0]   (shared)
   source lines, word-line rail switch, reference  sa_p[23:0], sa_n[23:0]  ← sense outputs
   72 row slices (level shifter + word-line driver) ── array 72 × 24 2T2R ── 48 bit-line slices (level shifter,
   ground NOR, driver, sense amplifier) + 24 source-line drivers
   one 2T2R test cell with its four lines on pads
```

Netlists: `chip/sky130/sim/periph.spice` (cells `ls_lv2hv`, `tg`, `wld`, `bld`, `sld`, `sa`, `refbias`, `nor3hv`,
`nor2hv`, and the assemblies `rowslice`, `blslice`, `ctrlglob`). The test multiplexer of the IHP design is not on the
first SKY130 chip; the test cell gives direct access to two devices.

### 2.1 Array controller `tcim_actl` (rtl/chip/tcim_actl.sv, revision 2)

Turns one request of the TCIM0 core into timed line control; every macro-side output comes from a flip-flop.
In the macro each bit line goes to VPRG when its `prg` is high, to its sense amplifier when `bl_sen` is high, and to
ground when NOR(prg, bl_sen, flt); all source lines go to VPRG when `sl_prg` is high and to ground when NOR(sl_prg, flt).
`flt` is raised one cycle before any prg / bl_sen / sl_prg change and dropped one cycle after, so no line switches
directly between ground and a rail (break before make), whatever the skew between the level shifters.

Sequence: IDLE (all lines grounded) → BRK (flt = 1) → MAKE (modes, rail and reference set) → SETL (flt = 0;
T_SETTLE) → WLON (word line on for T_SENSE or T_PULSE; reads sample in the last cycle) → WLOFF (second sampling
flip-flop) → REL (flt = 1) → BRK2 (modes released) → GND (flt = 0, acknowledge) → IDLE.

| Operation | Bit lines of masked devices | Other bit lines | Source lines | Word-line rail | Reference |
|---|---|---|---|---|---|
| READ / VFY_SET / VFY_RESET | sense amplifier | sense amplifier | ground | VWLR | mid / set target / reset target |
| PULSE_SET | VPRG | ground | ground | VWLP | none |
| PULSE_RST | ground | VPRG | VPRG | VWLP | none |
| SUM (analog mode) | not supported on this chip: answered after one cycle with zero counts | | | | |

Times: T_SETTLE = 2^(ts+1), T_PULSE = 2^(tp+2), T_SENSE = 2^(tr+2) clock cycles, from static pins. With a 16 MHz board
clock T_PULSE = 16 cycles = 1 µs at tp = 2. The board reads `pk` (0 set, 1 reset) and `pamp` (amplitude code 0–20) from the start
of each pulse request and sets VPRG / VWLP during T_SETTLE; `pstb` is high while a program word line is on.

Verification: the full TCIM0 test bench runs on `tcim_chip_core` (`make rtl-chip`, three timing configurations)
against a line-level model of the macro that derives each line's state from prg / bl_sen / flt exactly as the macro does
and checks every cycle: no rail shorted to ground, at most one word line, no floating line while a word line is on, a
line floats for at most two cycles, no direct switch between two driven modes, prg / bl_sen / sl_prg change only with
flt high in that cycle and the one before, lines and rail stable while a word line is on, read and program set-ups,
exact T_SENSE / T_PULSE, lines settled for T_SETTLE, the strobe and the pulse-kind output. Sense outputs are random
for the first two cycles of a read. `tb/chip/mutation_chip.py` injects 26 faults into the controller; each must be
caught.

### 2.2 Pads

Digital (`io_in/out/oeb`, 1.8 V; mprj_io 0–4 stay with the management core):

| io | mprj_io | Signal | Dir |
|---|---|---|---|
| 5, 6 | 5, 6 | clk, rst_n | in |
| 7, 8, 9 | 7, 8, 9 | sck, cs_n, mosi | in |
| 10, 11 | 10, 11 | miso, irq | out |
| 12, 13 | 12, 13 | pstb, pk | out |
| 14–18 | 25–29 | pamp[4:0] | out |
| 19–21 | 30–32 | cfg_ts[2:0] | in |
| 22–24 | 33–35 | cfg_tp[2:0] | in |
| 25, 26 | 36, 37 | cfg_tr[1:0] | in |

Analog (`io_analog`, direct, no ESD in the harness). The harness offers clamps (io_clamp_high/low) for io_analog[4–6];
this design does not connect them, and draws no ESD diodes of its own (revision 4.5 as built, 12 October 2026). The pads
used are protected only by the junctions of the transistors they reach: antistatic handling and protection on the test
board are required.

| io_analog | mprj_io | Signal | Level | Protection on chip |
|---|---|---|---|---|
| 4 | 18 | VPRG | 0–3.3 V, a few mA | none (harness clamp [0] not connected) |
| 5 | 19 | VWLP | 0–3.3 V | none (harness clamp [1] not connected) |
| 6 | 20 | VWLR | 0–3.3 V | none (harness clamp [2] not connected) |
| 0 | 14 | VREF | 0.2 V | none |
| 1 | 15 | IBIAS | sink, about 0.8 µA | none |
| 2, 3, 7, 8 | 16, 17, 21, 22 | TC_WL, TC_BLP, TC_BLN, TC_SL (test cell) | 0–3.3 V | none |
| 9, 10 | 23, 24 | spare | | |

Antenna diodes (n+ / p-substrate, `sky130_fd_pr__diode_pw2nd_05v5`, 3 × 3 µm, to vssa1) are drawn on the 48 sense
outputs and 13 pad inputs of the digital block at the top level, and on the three reference-select nets (r0–r2) in the macro; they
protect gates during fabrication, not against ESD.

### 2.3 Programming levels (test board; checked by `chip/sky130/sim/macro_sim.py`)

The chip only switches the rails; the board maps (pk, pamp) to voltages, so the scheme can be changed after the first
measurement. Proposed map, from the simulations through the drawn drivers with the device model at SkyWater's
parameters (results/sky130_chip/macro_sim.json):

| Pulse | VWLP | VPRG by amplitude code | Simulated (5 corners/temperatures checked: tt 27, ss −40, ff 125 °C) |
|---|---|---|---|
| set | 2.0 V | 1.4 V + 0.1 V × code (code 0–19) | reaches the highest set-verify trip (27.4 µS) in 7–8 pulses; with SkyWater's 1.7 V word line it fails at ss −40 °C (21.8 µS after 20 pulses) because the 1 µm select transistor limits the current |
| reset | 2.5 V + 0.1 V × code (codes 0–5), then 3.0 V | 2.4 V (codes 0–5), then 2.5 V + 0.1 V × (code − 6) | a cell with the fitted reset rate resets in 1–2 pulses; cells 1, 2, 3 decades slower in 1–4, 3–5, 5–7 pulses; 4 decades slower fails at ss −40 °C |

With the worst routed wiring of the drawn macro (bit line 595 Ω, source line 442 Ω, `layout/sky130/periph/macro_rc.py`) and
the highest set-verify trip seen under mismatch (29.84 µS), the same map still works: set in 9–11 pulses at 2.0 V (fails
at tt 27 °C and ss −40 °C with a 1.7 V word line), reset in at most 8 pulses up to three decades slower, and 4 decades
slower fails at ss −40 °C as before (`results/sky130_chip/macro_sim_worst.json`).

Forming is done by the board firmware as ordinary program commands with a forming map (higher word-line rail),
first all +1, then all −1, then the target weights. The model cannot represent a pristine cell (below 0.3 µS), so forming
itself is not simulated.

## 3. Verification plan

1. Each analog cell: ngspice with the open_pdks sky130B models, 5 corners, −40 / 27 / 125 °C, supply ± 10 %, mismatch
   Monte Carlo where matching matters (sense amplifier, reference mirror).
2. Each drawn cell: Magic DRC, extraction, netgen LVS against its schematic, with a planted error that must be caught;
   re-simulation with extracted parasitics.
3. The macro: read, set, reset and form of a row with the ReRAM model (SkyWater parameters, fitted reset rate), with
   extracted wiring.
4. The controller: RTL test bench; the full TCIM0 test bench with the controller and a behavioural macro; mutation
   test of the controller; gate-level run after layout.
5. The chip: top level assembled by script (`layout/sky130/periph/top.py`) in `user_analog_project_wrapper`; full-chip
   Magic DRC (full rules) and netgen LVS with a planted error; Magic antenna check; timing after layout at every corner;
   ChipFoundry's precheck in ChipFoundry's own pinned versions (`flow/eda/pc_batch22.sh`). Results: `docs/STATUS.md`, section 9.
