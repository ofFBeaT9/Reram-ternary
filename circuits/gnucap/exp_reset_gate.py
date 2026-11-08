"""Full-circuit check of the reset gate voltage (revision 4.3).

model/program_mc.py found, with the fast reference model and an ASSUMED device-to-device spread, that some slow
devices do not reset within the 21-step ladder at the published 2.7 V gate, and that 3.0 V and 3.3 V fix it.
Here the same devices are simulated as full transients in Gnucap: IHP sg13_hv_nmos (PSP103, W 4.5 um, L 0.45 um)
and the Verilog-A ReRAM model with each device's own v0, Ea and I0. Each device is first set with the nominal
parameters to the 42 uA target at a 1.7 V gate (as the Monte Carlo does), then reset with its own parameters, at
gates of 2.7, 3.0 and 3.3 V. Devices: the nominal device and the three slowest devices of the "ss 2x" case.
Also recorded, as an upper bound for the drivers and the lines: the peak current of one pulse at the final reset
amplitude applied to the fully set device.
Writes results/gnucap_reset_gate.json."""
import json, sys
from pathlib import Path
import numpy as np
import cell

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "gnucap_reset_gate.json"
W = 4.5


def devices():
    mc = json.loads((ROOT / "results" / "program_mc.json").read_text())
    rows = mc["runs"]["ss 2x"]["devices"]
    slow = sorted([r for r in rows if not r["reset_ok"]], key=lambda r: r["v0"] * np.exp(-r["Ea"] / 0.02585))[:3]
    out = [("nominal", None, None)]
    for k, r in enumerate(slow):
        out.append((f"slow {k + 1}", dict(v0=r["v0"] * 1e9, Ea=r["Ea"], I0=r["I0"]), r))
    return out


def peak_reset_current(gap, vg, amp, corner, dev):
    _, _, t = cell.pulse(gap, W, vg, amp, -1, corner, dev=dev, trace=True)
    return float(np.max(np.abs(cell.g.col(t, "i(Vbl)"))))


if __name__ == "__main__":
    corner = sys.argv[1] if len(sys.argv) > 1 else "ss"
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    s = cell.ispva(1.8, W, 1.7, 42e-6, +1, corner)
    res[f"{corner} set nominal"] = s
    print(corner, "set", s, flush=True)
    for name, dev, mcrow in devices():
        for vg in (2.7, 3.0, 3.3):
            r = cell.ispva(s["gap_nm"], W, vg, 6e-6, -1, corner, dev=dev)
            if r["ok"]:
                r["peak_current_bound_uA"] = round(peak_reset_current(s["gap_nm"], vg, r["amp"], corner, dev) * 1e6, 1)
            r["device"] = dev; r["mc_model_reset_ok_at_2p7"] = None if mcrow is None else mcrow["reset_ok"]
            res[f"{corner} {name} vg {vg}"] = r
            print(corner, name, vg, r, flush=True)
            OUT.write_text(json.dumps(res, indent=1))
