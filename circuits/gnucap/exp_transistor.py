"""Characterise the real IHP sg13_hv_nmos (PSP103) select transistor in Gnucap, all five corners."""
import json
from pathlib import Path
import numpy as np
import gnucap_run as g

OUT = Path(__file__).resolve().parents[2] / "results"


def idvg(w_um, corner, vd, vgs):
    deck = g.header(corner) + f"""
spice
Vd d 0 dc {vd}
Vg g 0 dc 0
.verilog
sg13_hv_nmos #(.w({w_um}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) m1(d, g, \\0 , \\0 );
print dc i(Vd)
dc Vg {vgs[0]} {vgs[-1]} {vgs[1]-vgs[0]:.4f}
"""
    t = g.run(deck)[0]
    return -g.col(t, "i(Vd)")


if __name__ == "__main__":
    res = {}
    vgs = np.round(np.arange(0.0, 3.3001, 0.05), 3)
    for corner in ("tt", "ss", "ff", "sf", "fs"):
        for w in (1.5, 3.0, 4.5):
            sat = idvg(w, corner, 3.3, vgs)
            lin = idvg(w, corner, 0.05, vgs)
            gm = np.gradient(lin, vgs)
            k = int(np.argmax(gm))
            vth = vgs[k] - lin[k] / gm[k] - 0.025      # linear extrapolation at maximum gm
            res[f"{corner}_W{w}"] = {
                "idsat_3v3_uA": round(float(sat[-1]) * 1e6, 1),
                "idsat_per_um_uA": round(float(sat[-1]) * 1e6 / w, 1),
                "id_vg1v7_vd0v05_uA": round(float(lin[34]) * 1e6, 2),
                "ron_vg1v7_ohm": round(0.05 / float(lin[34]), 0),
                "ron_vg3v3_ohm": round(0.05 / float(lin[-1]), 0),
                "vth_lin_extrap_V": round(float(vth), 3),
            }
            print(corner, w, res[f"{corner}_W{w}"])
    (OUT / "gnucap_transistor.json").write_text(json.dumps(res, indent=1))
