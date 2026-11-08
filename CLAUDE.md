# ReRAM ternary accelerator for REBEL-6 — design repository

Project memory for Claude Code. Read this first, then `docs/STATUS.md` and `docs/AUDIT.md`.
Roadmap revision 4.4 (10 October 2026); section 21 lists what changed after the audit, section 22 what revision 4.2 added
(place and route, gate-level runs, lint, Verilator, formal proofs, the product-sequencer change, layout, periphery,
programming with spread, the SKY130 port), section 23 what revision 4.3 added (clock gating, timing at all corners,
reset gate in the full circuit, read reference, test multiplexer, drawn periphery cells, programming-voltage plan),
section 24 what revision 4.4 added (model fitted to SkyWater's yields, SKY130 array drawn with the ReRAM layer, sky130B
place and route, SKY130 read path, hybrid read declined, 5 V forming path, pitch-matched word-line driver, FPGA demo).
Sections 1 to 21 quote the files kept in `results/rev41`, section 22 `results/rev42`, section 23 `results/rev43`,
section 24 `results/`.

## What this is

A balanced-ternary compute-in-memory accelerator: one tile of 72 rows × 24 ternary columns, 2T2R cells
(+1 = LRS/HRS, 0 = HRS/HRS, −1 = HRS/LRS, two states per device), target process IHP SG13G2 with the MEMRES
ReRAM module, presented to a REBEL-6 CPU as memory-mapped device TCIM0 (proposed slot 11, interrupt source 7).

**The CPU target is REBEL-6 as published by the USN group** (specification in `aiunderstand/ternary-workbench`).
The owner's earlier processors (the "Tritone" projects in `E:\ternary cmos compile` and `C:\Tritone SoC`) are
context and a source of tools. Do not adapt TCIM0 to them, and do not use their status files as evidence.

The owner's rule: **being correct is the only option.** Tape-out is parked until the design is verified.
Nothing is "done" until a script in this repository reproduces the number and the number is written to `results/`.

## Ground rules

- Never state a number without a source: a script here, or a cited publication (see the roadmap, section 17).
- A simulation result is evidence about the *model*, not about silicon. Say which one you mean.
- Published IHP device data are from 0.25 µm arrays read directly after programming. The SG13G2 MEMRES kit has
  not been seen. Every device parameter is a placeholder until the kit or measured data arrives.
- Keep the three implementations of the device model in step: `model/reram_stanford.py` (reference),
  `model/reram_stanford_ihp.va` (Verilog-A), `model/reram_stanford_ihp.lib` (ngspice behavioural).
  After any change run `make check-model`.
- Proposals are labelled as proposals. Do not turn a proposal into a fact by repeating it.
- A passing test bench proves little by itself. After any RTL change run `make rtl` and `make mutation`;
  every injected fault must be detected. For every bug found, add a fault to `tb/mutation_test.py` and a test
  that detects it. (The revision 3 test bench had 60,401 passing checks and missed two real bugs.)
- After any re-run, `make test`: it re-derives key results by a second method and checks every number quoted
  in the roadmap against `results/`. Update `tests/test_claims.py` when a quoted number changes.
- Numbers from a web page or a paper are read from the page text itself, never from an automatic summary.
  A summarizer invented table values for two IHP papers during the audit.
- The device model in `model/` is a stand-in. IHP states that the MEMRES kit contains a Verilog-A model.
  When it is available it replaces the stand-in and sections 18.2 to 18.6 of the roadmap are re-run.
- Two trit codes are supported (`rtl/tcim_pkg.sv`): two's complement by default, BSD-PNX with `TCIM_ENC_PNX`.
  After any RTL change run both (`make rtl rtl-pnx`, `make mutation mutation-pnx`). Never write `'0` into a
  register that holds trits; use `ZERO_TRYTE` / `ZERO_WORD`.
- After any RTL change run `make equiv` and `make sta`. The comparison with the reference logic
  (`tests/equiv/rtl_rev41` since revision 4.2) must prove every point unless the logic is meant to change; if it is,
  check that `results/equiv_unproven.txt` lists only the intended signals, say so in the roadmap, and move the
  reference deliberately. (The proof caught a signed table index on 7 October before any simulation ran.)
- Timing numbers from `make sta` are before layout: no wires, ideal clock, unbuffered reset. Say so every time.
  Timing after layout comes from `flow/orfs/post/sta_post.tcl` on the routed netlist with extracted parasitics.
- The formal proofs (`make formal`) and the gate-level run of routed netlists (`make gls`) have each been shown
  able to fail (`formal/check_faults.py`, the `xnor` fault of `gls.sh`). Keep it that way when changing them.
  Write properties from an independent decoding of the registers, not from the logic's own derived signals: a
  property stated in terms of `x_nz` could not catch a fault in `x_nz` (found by `check_faults.py` on 8 October).
  State what must happen, not only what happens when something ends: "every command that ends sets DONE" could
  not see a command that never started (found by `check_faults.py` on 9 October; now also "every accepted
  command runs or has ended with DONE").
- Clock gating (revision 4.3) is inserted by synthesis (`CLKGATE=` in `synth/run_synth.sh`, `INFER_CLKGATES` in the flow
  configs), not written in the RTL, so the RTL proofs do not cover it. After a change, run the gated netlist through
  `flow/orfs/post/gls.sh` with and without the `icg` fault. The test bench lets inputs settle with the clock low before
  the edge (`tick()` in `tb/tb_tcim.cc`); a latch-based clock gate in a zero-delay simulation needs that. Keep it.
- Timing after layout at every corner: `make post-corners` (parasitics x0.8 and x1.2 as a stand-in for RC corners);
  SKY130 slow/fast Liberty files come from `tools/make_sky130_corner_libs.sh`. SKY130 does not meet 10 ns at its slow corner; on sky130B, optimized against the slow library, it meets 16 ns (revision 4.4).
- When a revision is closed, copy the files its section quotes to `results/rev<NN>` and point that section's claims in
  `tests/test_claims.py` there (done for 4.1, 4.2 and 4.3).
- Gnucap: a node held only by off transistors (inside a transistor stack, a level-shifter output) gets an arbitrary DC
  solution, up to hundreds of volts (found on 10 October in `circuits/gnucap/forming.py`). Tie every such node to a
  defined voltage through 1 GOhm. (Gnucap still reports one "open circuit: internal node" per forming run after that;
  the voltages are physical, so check the voltages, not only the warning.)
- FPGA demo: the board's MULT18X18 with signed operands converted negative sums wrongly (10 October), while the
  gate-level model (written from the documentation) agreed with the RTL. Use unsigned products only;
  `tb/fpga/run_fpga_checks.sh` fails if the board netlist has a signed multiplier. The design is near the GW1NR-9's
  placement limit (about 84-85 % of LUTs places, 86 % does not); check nextpnr before adding logic.
- SKY130 array (`layout/sky130/`, Magic + netgen, sky130B) and the FPGA demo (`rtl/fpga/`, `tools/fpga_host.py`) run in the
  `reram-eda` image on the PC (`flow/eda/`). The FPGA board needs the WinUSB driver on its JTAG interface (interface 0,
  "USB Serial Converter A"); the serial port (interface 1) keeps its driver. The owner sets drivers, not Claude.
- SKY130 test chip (revision 4.5, `chip/sky130/`, `rtl/chip/`, `layout/sky130/periph/`, project folder
  `chip/sky130/caravan`): after a change to `rtl/chip/tcim_actl.sv` run `make rtl-chip` and `tb/chip/mutation_chip.py`
  (every fault must be detected), then place and route the block again (`flow/eda/pc_batch7.bat`), `gls_chip.sh` and
  `top.py`. After a change to `periph.spice` run `periph_sim.py`, `macro_sim.py`, then `gen.py`, `macro.py`, `top.py`.
- ngspice with the SKY130 models runs in HSPICE mode, where parameter names are case-insensitive (`V0` and `v0` collide:
  renamed `Vs` / `vr0`) and a subcircuit port named `gnd` becomes the global ground (renamed `dn`). The reduced library
  (`chip/sky130/sim/spice.py`) is identical to the full one for deterministic runs; with mismatch on it draws a different
  sample (checked statistically by `mc_libcheck.py`).
- Magic by script: painting a metal over a contact can erase the contact, so contacts are painted last; `load -force`
  reads a stale file, so delete the .mag first; use `drc style drc(full)` for sign-off counts.
- Chip sign-off (12 October 2026): `make equiv-chip` (lint of the chip RTL and proof that `flow/orfs/src/tcim_chip_digital.v`
  equals it), `make signoff` (Magic DRC with the precheck's commands, Magic antenna check; results/sky130_chip/top_signoff.json),
  `layout/sky130/periph/antenna_crosscheck.py` (Magic's antenna hits against OpenROAD's ratios for the same gates), ChipFoundry's
  precheck on the PC (`flow/eda/pc_batch13.sh`: all 14 checks, CVC built from source, needs libreadline-dev; in
  ChipFoundry's own pinned versions, Magic 8.3.471 / netgen 1.5.272 / CVC v1.1.7 / open_pdks 3e0e31d: `pc_batch22.sh`,
  which is the run that counts). Standard cells written into the chip: `layout/sky130/periph/stdcells_cf` (README there). The harness
  template files `top.py` reads are in `layout/sky130/periph/harness/`. Do not leave `.cf/` or `precheck_results/` inside
  `chip/sky130/caravan`.
- SymbiYosys: never run two tasks of the same .sby file in parallel; they share the task's status database and the
  later ones stop before proving anything ("No such file or directory: .../status.sqlite", batch 12). Run them in sequence.
- Background shells: `pgrep -f "<pattern>"` in a wait loop matches the loop's own command line; wait on a PID or a file.
- The mutation test can run on a machine with many cores: `tb/mutation_remote.py gen` here, `run` there (only python3 and
  a C++ compiler needed), then `tb/mutation_merge.py`.
- Security (revision 4.6, 4 November 2026; `studies/hw-security-2026-11/`): products read all 72 rows from an LFSR start row,
  programming runs a fixed 21 + 21 pulse steps (empty-mask pulses), SEC register (+3) with ZSKIP / VARPROG / NOSHUF opt-ins and a
  set-only LOCK, margin check (PCMD 0,+; MARG +52), dummy accumulators seen through ACT (+50). After an RTL change also run the
  two-copy timing miter (`cd formal && $SBY -f tcim_miter.sby prove` and `prove_pnx`; its faults are in `check_faults.py`).
  The leak models are `tools/tvla_tcim0.py` and `chip/sky130/sim/sa_power.py` (evidence about the model only).
- The FPGA demo builds tcim_core with `TCIM_NO_DUMMY` (no dummy accumulators): with them synthesis gives 8,076 LUTs + ALUs
  against 6,773 for revision 4.5, which placed at 83 % (`results/fpga/rev46/yosys_stat_with_dummy.txt`).
  `tb/fpga/run_fpga_checks.sh` takes FPGA_BUILD / FPGA_RESULTS / FPGA_TBBUILD; revision 4.6 uses `rtl/fpga/build_rev46`,
  `results/fpga/rev46`; never overwrite `rtl/fpga/build` (the board-run bitstream).
- The chip block's die and core are fixed in `flow/orfs/sky130hd_chip/config.mk` (those of revision 4.5) because `top.py`
  connects to fixed ring coordinates of the block; a different die needs `top.py` changed.
- Revision 4.7 (6-7 November 2026, after the council review in `studies/hw-security-2026-11/council/`): the start row is the
  LFSR value modulo 72 (register `lfsr_m72`), the result accumulators start at a random offset (`r_off`, -128 ... 127) taken off
  with the last row, every use of ZSKIP / VARPROG / NOSHUF is gated by ~LOCK, read-back is refused under LOCK (WERR, no array
  access) and a margin check under LOCK does not write PDATA. Formal: `p_lfsr_m72` (lfsr_m72 == lfsr % 72) is proved by
  k-induction in its own task (`tcim_core.sby lfsr`, depth 20: at depth 3 the base case could not see the planted fault) and dropped from the PDR tasks, where it does not converge; the offset is
  proved through the shadow sum `f_sum0` (column 0 equals offset + f_sum0 while a product runs, f_sum0 after it), not
  through inequality lemmas (PDR did not close those). `make formal` runs the miter and `check_faults.py`, which refuses to
  count faults unless every base proof has passed; `JOBS=<n>` runs the faults side by side (each in its own folder).
- PC batches from 27 on: ChipFoundry's PDK comes from the local mirror `flow/eda/cfpdk_mirror` (`tools/cf_pdk_mirror.sh`,
  sha256-checked assets served on 127.0.0.1:8765; set NO_PROXY), because the release download failed twice in the container.
  The ORFS image has no standalone OpenSTA: run the timing after layout (`post_corners.sh`, `min_period.py`,
  `collect_chip_digital.py`) where `sta` is on the path (the sandbox, `tools/build_sta.sh`; needs flex).
- `gls_chip.sh`'s `xnor` fault changes the first xnor2_1 whose output reaches a flip-flop other than a dummy accumulator
  (batch 25 put it on a dummy accumulator, where no test can see it).
- Antenna: `flow/orfs/sky130hd_chip/post_drt.tcl` ends with a pass at a 15 % margin (batch 27 left a net at exactly OpenROAD's
  limit that Magic's check of the assembled chip put 5 % over it).
- The cloud sandbox: `env_oss.sh` puts YosysHQ's OSS CAD Suite (2026-10-09, with the slang front end) on the path.
- Serial-port fuzzing (revision 4.8): `make fuzz` (`tb/extra/spi_fuzz.cc`, faults in `tb/extra/spi_fuzz_faults.py`).
  Rerun it after any change to `rtl/tcim_spi.sv` or the register map.
- US spelling in documents. Units with every number.

## Layout

| Path | Content |
|---|---|
| `model/` | Stanford-PKU ReRAM model (Python reference, Verilog-A, ngspice), calibration, pulse-and-verify, transistor sizing |
| `array/` | 72 × 24 tile model: wiring, clamp, both read modes, network accuracy, energy and time |
| `circuits/gnucap/` | Gnucap decks driven from Python: real IHP PSP103 transistors + the Verilog-A ReRAM model |
| `circuits/ngspice/` | ngspice decks for the device model alone |
| `rtl/` | TCIM0: `tcim_pkg`, `tcim_core` (registers, sequencers), `tcim_spi`, `tcim_top`; `baseline/` digital yardsticks |
| `tb/` | CXXRTL self-checking test bench and its vectors; `mutation_test.py` injects faults into the RTL |
| `tests/` | Audit: independent re-derivations (`test_independent.py`), quoted numbers against results (`test_claims.py`); `equiv/`: proofs and the revision 4 RTL they compare with |
| `synth/` | Yosys scripts, Liberty reader, switching-energy estimate; timing-driven synthesis and OpenSTA (`run_sta.py`); `conv_study/` |
| `flow/orfs/` | Place and route with OpenROAD-flow-scripts (IHP SG13G2, SKY130): configuration, Docker launchers (`run_full.bat` on the PC), `post/` timing after layout, gate-level run, result collection |
| `formal/` | SymbiYosys proofs of the properties written under `ifdef FORMAL` in the RTL, and the faults that must make them fail |
| `layout/` | The transistor part of the 2T2R array and the level shifter / word-line driver drawn by script (GDS); the PDK's KLayout DRC and LVS runs for the PC |
| `results/` | Every number quoted in the roadmap, as JSON or log; `rev4/` holds the files section 20 quotes, `rev41/` those of sections 18, 19 and 21, `rev42/` those of section 22, `rev43/` those of section 23; `fpga/` the FPGA demo; `pnr/` place-and-route reports; `periph_layout/` DRC/LVS of the drawn periphery |
| `docs/` | `STATUS.md` (what is verified, what is open), `AUDIT.md` (what the audit of revision 3 found), the roadmap |

## Tools

Set four things (copy `env_example.sh`; `env_sandbox.sh` shows the values used in the cloud sandbox): `PATH` with `gnucap`, `gnucap-mg-vams`, `ngspice`, `yosys`;
`LD_LIBRARY_PATH` with Gnucap's library; `IHP_GNUCAP=<IHP-Open-PDK>/ihp-sg13g2/libs.tech/gnucap`; `IHP_STDCELL_LIB` = the typical 1.2 V Liberty file.

`make sta` also needs OpenSTA (`sta`) on the path; `tools/build_sta.sh` builds it with its dependencies from source.
`SKY130_STDCELL_LIB` (optional) = `sky130_fd_sc_hd__tt_025C_1v80.lib`, e.g. from the `sky130hd` platform of
OpenROAD-flow-scripts.

**Already on the owner's PC** (seen on 7 October 2026 in the earlier project folders; not run from here):
OpenROAD-flow-scripts in `C:\Tritone SoC\OpenROAD-flow-scripts-master` with the platforms `ihp-sg13g2` and
`sky130hd`, run through Docker (`openroad/orfs:latest`); an OpenLane v1 Docker flow for SKY130 that completed a
small run with clean DRC and LVS; QuestaSim, Icarus Verilog and Vivado according to their log and project files.
Treat those two folders as read-only. Put new flow files in this repository (`flow/orfs/`).

For the analog work the simplest route is the IIC-OSIC-TOOLS container (Docker + WSL2), which ships ngspice, OpenVAF-Reloaded,
Xschem, KLayout, Yosys, Verilator, OpenROAD and the IHP PDK. Gnucap with `gnucap-modelgen-verilog` must be built
from source if it is not in the container (`docs/STATUS.md` lists the exact commits that worked).

## Commands

```
make check-model     # device model: Python vs ngspice vs Gnucap
make pdk-check       # the PDK's own transistor reference tests in Gnucap
make cell            # 1T1R with the real transistor: reads, set, reset, corners
make sense           # read path: corners, transients, mismatch Monte Carlo, read disturb
make array           # tile experiments (slow: tens of minutes)
make rtl             # build and run the RTL test bench (about five minutes)
make rtl-pnx         # the same test bench on the build with the BSD-PNX trit code
make mutation        # inject one fault at a time; all must be detected (about half an hour on two cores)
make mutation-pnx    # the same on the BSD-PNX build, plus the faults that only matter there
make equiv           # proofs: table = definition, place-and-route source = RTL; comparison with the revision 4.1 logic
make test            # independent re-derivations; every quoted number against results/
make synth           # synthesize TCIM0 and the digital baselines on IHP standard cells
make sta             # timing-driven synthesis and OpenSTA: three IHP corners, both codes, SKY130 if its library is set
make orfs-src        # plain Verilog of the design for flow/orfs
make lint            # Verilator lint, all warnings, both codes
make rtl-verilator   # the test bench on Verilator (second simulator), both codes
make formal          # SymbiYosys proofs, then the injected faults that must make them fail
make gls POST_DIR=... POST_LIB=...   # routed netlist through the full test bench (and with one gate changed)
make layout          # GDS of the array transistors; DRC: layout/run_drc.bat in Docker on the PC
make sense-env periphery program-mc sky130-port   # read path over T and V; periphery (incl. reset gate, read reference); programming with spread; SKY130
make post-corners PLATFORM=... WORK=... LIBDIR=... SLOWLIB=...   # timing after layout, all corners, parasitics x0.8/x1.2, shortest period
python3 tb/mutation_remote.py gen <pack> | run <pack> <jobs>      # mutation test split for a many-core machine
```

After any RTL change also run `make lint rtl-verilator formal`, regenerate `make orfs-src`, place and route again
(`flow/orfs/run_full.bat <folder>` on the PC), then post-route timing and `make gls` on the new netlists.
