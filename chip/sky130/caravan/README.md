# TCIM0 SKY130 test chip: ChipFoundry Caravan project folder

The files ChipFoundry's precheck and submission read, for the analog harness (`user_analog_project_wrapper`):

| Path | Content | Made by |
|---|---|---|
| `gds/user_analog_project_wrapper.gds` | layout of the user area (2920 × 3520 µm), sky130B | `layout/sky130/periph/top.py` |
| `netgen/user_analog_project_wrapper.spice` | reference netlist for LVS (analog macro from `chip/sky130/sim/periph.spice` and the array schematic, the routed digital block from its netlist, the test cell) | `top.py` |
| `lvs/user_analog_project_wrapper/lvs_config.json` | LVS configuration for the precheck (standard cells: sky130_fd_sc_hd) | by hand |
| `verilog/rtl/user_defines.v` | power-on modes of the GPIO pads | by hand, from `chip/sky130/ARCHITECTURE.md` section 2.2 |

Pad assignment and the chip's architecture: `chip/sky130/ARCHITECTURE.md`. Status and results: `docs/STATUS.md`, section 9.

State on 12 October 2026: ChipFoundry's precheck (cf-precheck 1.3.7, commit 6c401ed, all 14 checks, optional Magic DRC
included), run in ChipFoundry's pinned versions (Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, open_pdks
3e0e31d, sky130B), passes on `gds/user_analog_project_wrapper.gds` with md5 37a6fb425f7dbea11b9ea7c1be3c6352
(`results/sky130_chip/precheck.json`, run by `flow/eda/pc_batch22.sh`). The standard cells in the GDS are those of
`layout/sky130/periph/stdcells_cf` (open_pdks 1e35547, tie cell conb_1 from 3e0e31d; see its README). The chip must be
processed as sky130B (the ReRAM layer). ReRAM availability on a shuttle is not yet confirmed by ChipFoundry. Do not leave the precheck's `.cf/` or `precheck_results/` folders in this folder.
