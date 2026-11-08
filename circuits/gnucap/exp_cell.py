"""Full-circuit confirmation of the 1T1R cell with the real IHP transistor (Gnucap transients, 1 ns steps).

  1. read currents at the published gap values
  2. pulse-and-verify SET to the three published targets, at the gate voltages found by model/sizing_real_mos.py
  3. pulse-and-verify RESET from the deepest level
  4. the same at the slow and fast transistor corners
Usage: python3 exp_cell.py [W_um]
"""
import json, sys, time
from pathlib import Path
import cell

OUT = Path(__file__).resolve().parents[2] / "results"
TARGETS = {"LRS1": 18.08e-6, "LRS2": 31.01e-6, "LRS3": 43.59e-6}

if __name__ == "__main__":
    W = float(sys.argv[1]) if len(sys.argv) > 1 else 4.5
    plan = json.loads((OUT / "device_sizing_psp.json").read_text())
    res = {"W_um": W}
    for corner in ("tt", "ss", "ff"):
        t0 = time.time()
        r = {"read_uA": {f"{g:.2f}nm": round(cell.read_dc(g, W, corner) * 1e6, 2) for g in (0.95, 0.85, 0.73, 1.88)}}
        key = f"W{W}_{corner}" if f"W{W}_{corner}" in plan else f"W{W}_tt"
        for name, tgt in TARGETS.items():
            vg = plan[f"W{W}_tt"][name]["vg"]              # one gate voltage per level, taken from the typical corner
            r[f"set_{name}"] = dict(vg=vg, model=plan[key][name], **cell.ispva(1.8, W, vg, tgt, +1, corner))
            print(corner, name, r[f"set_{name}"], flush=True)
        # two-state recipe for the digital mode: one generous gate voltage, stop when the read reaches the LRS3 mean
        r["set_LRS3_vg1.7"] = cell.ispva(1.8, W, 1.7, TARGETS["LRS3"], +1, corner)
        print(corner, "LRS3 at Vg 1.7", r["set_LRS3_vg1.7"], flush=True)
        g3 = r["set_LRS3_vg1.7"]["gap_nm"]
        r["reset_LRS3_vg2.7"] = cell.ispva(g3, W, 2.7, 6e-6, -1, corner)
        print(corner, "reset", r["reset_LRS3_vg2.7"], f"{time.time()-t0:.0f} s", flush=True)
        res[corner] = r
        (OUT / f"gnucap_cell_W{W}.json").write_text(json.dumps(res, indent=1))
