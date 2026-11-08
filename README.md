# reram-ternary

Design repository for a balanced-ternary ReRAM compute-in-memory tile (72 × 24, 2T2R, two states per device)
that a REBEL-6 processor sees as memory-mapped device TCIM0. Target process: IHP SG13G2 with the MEMRES module.

- **What is verified and what is open:** `docs/STATUS.md`
- **What the audit of revision 3 found and fixed:** `docs/AUDIT.md`
- **Why the design looks the way it does:** the roadmap, revision 4.3 (`docs/`); section 21 has what changed after the audit, section 22 what revision 4.2 added, section 23 what revision 4.3 added
- **Project memory for Claude Code:** `CLAUDE.md`

Everything here is simulation. No silicon, no measured device data, no foundry ReRAM kit.

## Quick start

```
tools/build_tools.sh          # builds Gnucap, the Verilog-A compiler, ngspice and the PDK model plugins
WITH_YOSYS=1 tools/build_tools.sh   # also Yosys (about two hours), or use the Yosys of your container
# export the four variables the script prints, then:
make pdk-check check-model    # minutes
make rtl rtl-pnx test         # about ten minutes: the test bench in both trit codes, then the claims check
make mutation mutation-pnx    # about an hour on two cores: does the test bench notice injected faults?
make equiv                    # minutes: conversion table = definition; logic = audited logic; place-and-route source = RTL
make sta                      # a minute: static timing before layout (needs OpenSTA; see tools/build_sta.sh)
make cell sense synth array   # about two hours in total on two cores
```

The Python parts (`model/`, `array/`) need only Python 3 with NumPy and SciPy, and run without any simulator:
the table of the real transistor's current is in `results/sg13_hv_nmos_table.npz`.

## Map

| Path | Content |
|---|---|
| `model/` | Stanford-PKU ReRAM model: Python reference, Verilog-A, ngspice subcircuit; calibration, programming, sizing |
| `array/` | Tile model: wiring, clamp, analog and digital read, network accuracy, energy |
| `circuits/gnucap/` | Circuit simulation with the IHP PSP103 transistors (cell, sense amplifier, Monte Carlo) |
| `circuits/ngspice/` | Device-model decks for ngspice |
| `rtl/`, `tb/` | TCIM0 in SystemVerilog, its self-checking test bench, and the mutation test |
| `tests/` | The audit: independent re-derivations, and quoted numbers checked against `results/`; `tests/equiv/`: equivalence proofs and the revision 4 logic they refer to |
| `synth/` | Synthesis on IHP standard cells, gate-level check, switching-energy estimate; timing-driven synthesis and OpenSTA script (`run_sta.py`, `sta.tcl`) |
| `flow/orfs/` | Place and route with OpenROAD-flow-scripts, IHP SG13G2 and SKY130 (run on the PC, revisions 4.2 and 4.3, clock-gated since 4.3); post-route timing at every corner and gate-level runs |
| `formal/` | Formal proofs (SymbiYosys) of serial-port and sequencer properties |
| `layout/` | The array transistors, the level shifter and the word-line driver drawn by script, checked with the PDK's KLayout DRC and LVS decks |
| `results/` | Outputs of all of the above; `results/rev4/`, `rev41/`, `rev42/` keep the files that earlier sections of the roadmap quote |
| `calc/` | The hand calculations of the roadmap as a script |

## Trit code

Two bits per trit. Default: two's complement (+1 = 01, 0 = 00, −1 = 11). With `TCIM_ENC_PNX` defined: BSD-PNX
(+1 = 10, 0 = 11, −1 = 01, 00 illegal), the code of the REBEL group's tools. Both builds pass the same test bench
and fault campaign. Which one REBEL-6 hardware uses is a question for the maintainers.

## Place and route on the PC

```
make orfs-src                              # writes flow/orfs/src/tcim_top.v (plain Verilog of the whole design)
flow\orfs\run_orfs_docker.bat ihp-sg13g2   # or sky130hd; needs Docker Desktop and the image openroad/orfs
```

Results go to `flow/orfs/out/`. This has not been run yet; expect to adjust `config.mk`.
