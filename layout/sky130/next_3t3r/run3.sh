#!/bin/bash
# 3T3R one-of-three tile (next-chip proposal): draw, DRC (cell, hierarchical array, flat array), extract, LVS against
# the schematic and against a copy with one ReRAM element on the wrong bit line (must fail). Needs magic, netgen and
# PDK_ROOT with sky130B. Writes ../../../results/next_chip/array3.json.
set -e
cd "$(dirname "$0")"
RC=$PDK_ROOT/sky130B/libs.tech/magic/sky130B.magicrc
S=$PDK_ROOT/sky130B/libs.tech/netgen/sky130B_setup.tcl
MAGIC=${MAGIC:-magic}; NETGEN=${NETGEN:-netgen}
$MAGIC -dnull -noconsole -rcfile $RC drc_ext3.tcl < /dev/null > cell3.log 2>&1
$MAGIC -dnull -noconsole -rcfile $RC array3.tcl < /dev/null > array3.log 2>&1
python3 schematic3.py
$NETGEN -batch lvs "tcim_sky130_array3.spice tcim_sky130_array3" "schematic3.spice tcim_sky130_array3" $S lvs3.out > lvs3.log 2>&1 || true
$NETGEN -batch lvs "tcim_sky130_array3.spice tcim_sky130_array3" "schematic3_fault.spice tcim_sky130_array3" $S lvs3_fault.out > lvs3_fault.log 2>&1 || true
python3 - <<'PY'
import json, re
a = open("array3.log").read(); c = open("cell3.log").read(); l = open("lvs3.out").read(); lf = open("lvs3_fault.out").read()
res = dict(
    magic=re.search(r"Magic (\S+ revision \S+)", a).group(1),
    netgen=re.search(r"Netgen (\S+)", open("lvs3.log").read()).group(1) if re.search(r"Netgen (\S+)", open("lvs3.log").read()) else None,
    pdk=__import__("os").environ.get("PDK_TAG", "sky130B (PDK_ROOT)"),
    cell=dict(name="rr3t3r", width_um=5.6, height_um=3.0, area_um2=16.8, area_vs_2t2r=round(16.8 / 10.8, 3),
              devices="3 x (sky130_fd_pr__nfet_g5v0d10v5 W 1.0 L 0.5 um + sky130_fd_pr_reram__reram_cell 0.26 x 0.26 um)",
              lines="WL poly along the row; BLP / BLZ / BLN metal2 and SL metal1 along the column"),
    cell_drc_clean=bool(re.search(r"CELL DRC total: (0)?\s*\n(No errors found|CELLWHY)", c)) and "CELLWHY" not in c,
    cell_drc_fault_detected="ReRAM width" in c or bool(re.search(r"DRC total fault: [1-9]", c)),
    array=dict(rows=72, cols=24, width_um=round(24 * 5.6, 2), height_um=72 * 3.0,
               devices=int(re.search(r"Number of devices: (\d+)", l).group(1)) if "Number of devices" in l else None),
    array_drc_hierarchical_clean="ARRAY DRC: 0 rule groups" in a,
    array_drc_flat_errors=int(re.search(r"Total DRC errors found: (\d+)\s*\nFLAT DRC", a).group(1)),
    lvs_match="Circuits match uniquely" in l,
    lvs_fault_detected=("do not match" in lf) or ("Netlists do not match" in lf),
)
json.dump(res, open("../../../results/next_chip/array3.json", "w"), indent=1); print(res)
PY
