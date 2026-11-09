# TCIM0: a balanced-ternary ReRAM compute-in-memory tile and its SKY130 test chip

TCIM0 stores a 72 × 24 matrix of ternary weights (−1, 0, +1) in ReRAM and multiplies it by a 72-trit vector, returning
24 integers from −72 to +72. Each weight is two ReRAM devices read as one bit each (2T2R). A REBEL-6 processor sees the
tile as a memory-mapped device; on the test chip a host reaches the same registers through a four-wire serial port.

**Status (revision 4.8, 8 November 2026).** The test chip for SkyWater SKY130 (sky130B, ReRAM option) in ChipFoundry's
Caravan analog harness is complete: 3,456 ReRAM devices, drivers, 48 sense amplifiers, array controller, logic, pads and
a test cell. It passes DRC, LVS, the antenna rule and ChipFoundry's precheck in their pinned versions (14 of 14). It cannot
be ordered until ChipFoundry confirms ReRAM on a shuttle. Everything is simulation: no silicon, no measured device data.

| Read | For |
|---|---|
| `docs/TCIM0_explainer.html` | The illustrated explainer (open in a browser): how every part works, status, open issues |
| `docs/STATUS.md` | The status report: every result with the file it comes from |
| `docs/QUESTIONS.md` | Open questions to ChipFoundry and to the REBEL-6 group at USN |
| `studies/` | Hardware-security study (revisions 4.6, 4.7) and the triage of open issues |
| `chip/sky130/ARCHITECTURE.md` | Chip architecture, pad list, programming map |

## Revisions

| Rev. | Date | Change |
|---|---|---|
| 4.5 | 12 Oct 2026 | Complete SKY130 test chip; every suite re-run, 12 of 12 pass |
| 4.6 | 4 Nov 2026 | Fixed-latency products, dummy accumulators, constant-time programming, SEC/LOCK register, margin check |
| 4.7 | 6 Nov 2026 | Uniform start row (LFSR mod 72), random accumulator offset, LOCK refuses read-back; block routed again |
| 4.8 | 7 Nov 2026 | Serial-port fuzzing; no design change |
| next chip | 8 Nov 2026 | 3T3R one-of-three cell: build option `TCIM_CELL_1OF3` (core and array controller), test benches, formal safety proof, fault campaigns; drawn cell, array and analog macro (DRC, LVS) in `layout/sky130/next_3t3r/`; transistor-level leakage study and paper draft in `studies/paper-2026-11/` |

## Map

| Path | Content |
|---|---|
| `rtl/`, `rtl/chip/` | TCIM0 core, serial port and top (SystemVerilog); array controller and chip digital block |
| `tb/` | Self-checking test benches (CXXRTL, Verilator), mutation tests, serial-port fuzzer |
| `formal/` | SymbiYosys proofs: serial port, safety, progress, start row, two-copy timing miter; planted-fault check |
| `chip/sky130/` | Caravan project (`caravan/`: GDS, LVS netlist), circuit netlists and simulations (`sim/`) |
| `layout/` | Array, periphery and chip layout scripts; sign-off and antenna cross-check |
| `flow/orfs/`, `flow/eda/` | Place and route (OpenROAD-flow-scripts), PC batch scripts, precheck reports |
| `model/`, `array/` | ReRAM device model and its fit to SkyWater's data; tile model (wiring, read, accuracy, energy) |
| `circuits/`, `synth/` | IHP SG13G2 circuits and synthesis (earlier target) |
| `tools/` | Tool builds, leak model (`tvla_tcim0.py`), FPGA host and checker |
| `results/` | Every stored result; `tests/test_claims.py` checks each number the status report quotes against these files |

## Run

```
make rtl rtl-pnx            # test bench, both trit codes
make rtl-verilator          # second simulator
make formal                 # proofs (SymbiYosys)
make mutation mutation-pnx  # do the tests notice injected faults?
make equiv equiv-chip       # netlist = RTL
make fuzz                   # serial-port fuzzing
make rtl-1of3               # the test bench on the next-chip 3T3R cell option
make rtl-chip-1of3          # the chip test bench with the Z bit line (line-level macro model)
python3 tools/tvla_circuit.py --redraw   # leakage with transistor-level sense-amplifier waveforms
python3 studies/paper-2026-11/make_draft.py   # the paper draft, numbers read from results/
make test                   # every quoted number against results/
```

Place and route, sign-off and the precheck run in Docker on a PC (`flow/eda/pc_batch*.sh`). Not in the repository:
SkyWater PDK copies, build folders and large regenerable files (see `.gitignore`).

## Trit code

Two bits per trit. Default two's complement (+1 = 01, 0 = 00, −1 = 11); with `TCIM_ENC_PNX`, BSD-PNX (+1 = 10, 0 = 11,
−1 = 01). Both builds pass the same tests.
