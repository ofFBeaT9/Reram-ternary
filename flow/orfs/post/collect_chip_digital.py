"""Collect the place-and-route results of the digital block of the SKY130 chip (tcim_chip_digital, 11 October 2026):
the flow's final report, timing after layout at three corners with the parasitics x0.8 / x1 / x1.2 (post_corners.sh with
DESIGN=tcim_chip_digital), the shortest period at the slow corner (min_period.py, lines saved in min_period.jsonl), the
flow's DRC count and its equivalence check of the final netlist. Writes results/sky130_chip/digital_block.json."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
W = ROOT / "flow" / "orfs" / "outdig"
B = "sky130hd/tcim_chip_digital/base"
rep = json.loads((W / "logs" / B / "6_report.json").read_text())
out = dict(
    flow_library="sky130_fd_sc_hd__ss_100C_1v60 (flow optimised at the slow corner)", clock_period_ns=25.0,
    stdcells=rep["finish__design__instance__count__stdcell"], sequential=rep["finish__design__instance__count__class:sequential_cell"],
    clock_gates=rep["finish__design__instance__count__class:clock_gate_cell"],
    die_area_um2=rep["finish__design__die__area"], utilization=round(rep["finish__design__instance__utilization"], 3),
    flow_setup_ws_ns=round(rep["finish__timing__setup__ws"], 3), flow_hold_ws_ns=round(rep["finish__timing__hold__ws"], 3),
    ir_drop_worst_mV=round(1000 * rep["finish__design_powergrid__drop__worst__net:VDD__corner:default"], 3),
    drc_violations=int((W / "reports" / B / "6_drc_count.rpt").read_text().split()[0]),
    lec_identical="Circuits are IDENTICAL" in (W / "logs" / B / "6_final_lec_check.log").read_text(),
    corners={}, min_period=[json.loads(l) for l in (W / "min_period.jsonl").read_text().splitlines() if l.strip()])
for f in sorted(W.glob("post_*.rpt")):
    t = f.read_text()
    g = lambda k: float(re.search(rf"@@ {k} (\S+)", t).group(1)) * 1e9
    out["corners"][f.stem[5:]] = dict(setup_wns_ns=round(g("setup_wns"), 3), hold_wns_ns=round(g("hold_wns"), 3))
out["setup_wns_min_ns"] = min(v["setup_wns_ns"] for v in out["corners"].values())
out["hold_wns_min_ns"] = min(v["hold_wns_ns"] for v in out["corners"].values())
p = ROOT / "results" / "sky130_chip" / "digital_block.json"
p.write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
