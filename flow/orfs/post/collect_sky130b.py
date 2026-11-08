"""Collect the sky130B place-and-route run (flow/orfs/sky130hd_b, run on the PC with flow/eda/pc_batch3.bat, exported to
flow/orfs/out44b) into results/pnr_sky130b.json: flow metrics, post-route timing at the three corners
(flow/orfs/post/post_corners.sh), shortest period (min_period.py, parasitics x1 and x1.2)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
O = ROOT / "flow/orfs/out44b"
m = json.loads((O / "logs/sky130hd/tcim_top/base/6_report.json").read_text())
g = lambda k: m[f"finish__{k}"]
cls = lambda c: m[f"finish__design__instance__count__class:{c}"]
res = dict(
    tool="OpenROAD-flow-scripts, image openroad/orfs:26Q4-71-g9b26ff8ff, on the owner's PC (Docker Desktop)",
    platform="sky130hd standard cells with the sky130B technology LEF (ReRAM variant: via1 / metal2 heights); slow-corner "
             "library ss_100C_1v60 for every step; RC table of the platform unchanged (sky130A)",
    clock_period_ns=16.0,
    stdcells=g("design__instance__count__stdcell"), stdcell_area_um2=round(g("design__instance__area__stdcell"), 1),
    die_area_um2=round(g("design__die__area")), core_area_um2=round(g("design__core__area")),
    flip_flops=cls("sequential_cell"), clock_gate_cells=cls("clock_gate_cell"), clock_buffers=cls("clock_buffer"),
    timing_repair_buffers=cls("timing_repair_buffer"), antenna_cells=cls("antenna_cell"),
    flow_setup_ws_ns=round(g("timing__setup__ws"), 3), flow_hold_ws_ns=round(g("timing__hold__ws"), 3),
    flow_setup_tns=g("timing__setup__tns"), flow_hold_tns=g("timing__hold__tns"),
    clock_skew_ns=round(g("clock__skew__setup"), 3), power_W_default_activity=round(g("power__total"), 6),
    drc_violations=int((O / "reports/sky130hd/tcim_top/base/6_drc_count.rpt").read_text().split()[0]),
    post_route_sta={}, min_period=[])
for f in sorted(O.glob("post_*.rpt")):
    t = f.read_text()
    v = lambda k: round(float(re.search(rf"@@ {k} (\S+)", t).group(1)) * 1e9, 3)
    res["post_route_sta"][f.stem[5:]] = dict(setup_wns_ns=v("setup_wns"), setup_tns_ns=v("setup_tns"), hold_wns_ns=v("hold_wns"))
for k in ("1", "1.2"):
    res["min_period"].append(json.loads((O / f"min_period_k{k}.json").read_text()))
(ROOT / "results/pnr_sky130b.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
