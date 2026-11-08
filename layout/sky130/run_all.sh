#!/bin/bash
# SKY130 (sky130B) 72 x 24 TCIM0 tile: draw (magic), DRC (hierarchical and flat), the DRC fault check on the cell,
# extraction, LVS (netgen) and the LVS fault check. Needs magic, netgen and PDK_ROOT with sky130B
# (the sandbox uses copies exported from the reram-eda image: flow/eda/pc_batch1.sh). Writes results/sky130_array.json.
set -e
cd "$(dirname "$0")"
RC=$PDK_ROOT/sky130B/libs.tech/magic/sky130B.magicrc
magic -dnull -noconsole -rcfile $RC ext_cell.tcl < /dev/null > cell.log 2>&1
magic -dnull -noconsole -rcfile $RC array.tcl < /dev/null > array.log 2>&1
python3 schematic.py
./lvs.sh > lvs_summary.txt
python3 - <<'PY'
import json, re, subprocess
a = open("array.log").read(); c = open("cell.log").read(); l = open("lvs_summary.txt").read()
lvs = open("lvs.out").read()
res = dict(
    pdk=open(__import__("os").environ["PDK_ROOT"] + "/sky130B/SOURCES").read().strip() if __import__("os").path.exists(__import__("os").environ["PDK_ROOT"] + "/sky130B/SOURCES") else "sky130B",
    magic=re.search(r"Magic (\S+ revision \S+)", a).group(1),
    cell=dict(name="rr2t2r", width_um=3.6, height_um=3.0, area_um2=10.8, select_transistor="sky130_fd_pr__nfet_g5v0d10v5 W 1.0 L 0.5 um",
              reram="sky130_fd_pr_reram__reram_cell 0.26 x 0.26 um (area_ox 0.0676 um2), between metal1 and metal2",
              lines="WL poly along the row; BL+/BL- metal2 and SL metal1 along the column; substrate tie strip along every row"),
    array=dict(rows=72, cols=24, width_um=24 * 3.6, height_um=72 * 3.0, devices=int(re.search(r"Number of devices: (\d+)", lvs).group(1)),
               nets=int(re.search(r"Number of nets: (\d+)", lvs).group(1))),
    drc_hierarchical_clean="ARRAY DRC: 0 rule groups" in a,
    drc_flat_errors=int(re.search(r"Total DRC errors found: (\d+)\s*\nFLAT DRC", a).group(1)),
    drc_fault_detected="ReRAM width" in c and "DRC total fault" in c,
    lvs_match="Circuits match uniquely" in l,
    lvs_fault_detected="do not match" in l,
)
json.dump(res, open("../../results/sky130_array.json", "w"), indent=1)
print(json.dumps(res, indent=1))
PY
