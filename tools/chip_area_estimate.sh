#!/bin/bash
# Cell area of the chip's digital block before place and route (revision 4.5 vs the present one; 4.6 on 4 November, 4.7 on 7 November 2026): yosys synth +
# abc on the sky130_fd_sc_hd typical library (no buffering, no clock tree). Inputs: the place-and-route sources
# (revision 4.5: the copy archived in results/rev45/sky130_chip/tcim_chip_digital.v). Writes results/sky130_chip/area_estimate.json.
set -e
cd "$(dirname "$0")/.."
L=${SKY130_STDCELL_LIB:?set SKY130_STDCELL_LIB to sky130_fd_sc_hd__tt_025C_1v80.lib}
T=$(mktemp -d)
R=${REV:-rev47}   # label of the present revision
for v in rev45:results/rev45/sky130_chip/tcim_chip_digital.v $R:flow/orfs/src/tcim_chip_digital.v; do
  n=${v%%:*}; f=${v#*:}
  yosys -q -p "read_verilog $f; synth -top tcim_chip_digital -flatten; dfflibmap -liberty $L; abc -liberty $L; tee -o $T/$n.txt stat -liberty $L" > /dev/null
done
python3 - $T $R <<'PY'
import json, re, sys
T, R = sys.argv[1], sys.argv[2]
r = json.load(open("results/sky130_chip/area_estimate.json")) if __import__("os").path.exists("results/sky130_chip/area_estimate.json") else {}
for n in ("rev45", R):
    t = open(f"{T}/{n}.txt").read()
    r[n] = dict(cell_area_um2=float(re.search(r"Chip area for module .*: ([\d.]+)", t).group(1)),
                cells=int(re.search(r"^\s+(\d+)\s+[\d.E+]+\s+cells$", t, re.M).group(1)))
r["note"] = "yosys synth + abc on sky130_fd_sc_hd__tt_025C_1v80 (before buffering and clock tree); core area of the block 160,609 um^2"
json.dump(r, open("results/sky130_chip/area_estimate.json", "w"), indent=1); print(r)
PY
