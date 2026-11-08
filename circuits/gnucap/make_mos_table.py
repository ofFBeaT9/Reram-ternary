"""Tabulate Id(Vsb, Vgs, Vds) of the real IHP sg13_hv_nmos (PSP103, L = 0.45 um) with Gnucap.
The tables let the fast Python reference model use the real transistor instead of the stand-in."""
import sys, time
from pathlib import Path
import numpy as np
import gnucap_run as g

OUT = Path(__file__).resolve().parents[2] / "results"
VSB = np.round(np.arange(0.0, 2.0001, 0.1), 3)
VGS = np.round(np.arange(0.0, 3.3001, 0.05), 3)
VDS = np.round(np.arange(0.0, 3.3001, 0.05), 3)


def table(w_um, corner):
    deck = g.header(corner) + f"""
spice
Vs s 0 dc 0
Vg g s dc 0
Vd d s dc 0
.verilog
sg13_hv_nmos #(.w({w_um}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) m1(d, g, s, \\0 );
print dc i(Vd)
dc Vd 0 3.3 0.05 Vg 0 3.3 0.05 Vs 0 2.0 0.1
"""
    t = g.run(deck, timeout=3000)[0]
    i = -g.col(t, "i(Vd)")
    n = len(VSB) * len(VGS) * len(VDS)
    if i.size != n:
        raise RuntimeError(f"expected {n} points, got {i.size}; {t['problems'][:3]}")
    # the first sweep named is the innermost loop
    return i.reshape(len(VSB), len(VGS), len(VDS))


if __name__ == "__main__":
    jobs = [(w, "tt") for w in (1.5, 3.0, 4.5, 6.0)] + [(4.5, "ss"), (4.5, "ff")]
    data = {"vsb": VSB, "vgs": VGS, "vds": VDS}
    for w, c in jobs:
        t0 = time.time()
        tab = table(w, c)
        data[f"id_{c}_W{w}"] = tab
        print(f"W {w} um {c}: Id(0,3.3,3.3) = {tab[0,-1,-1]*1e6:.1f} uA, Id(1.0,1.7,2.3)= {tab[10,34,46]*1e6:.1f} uA, {time.time()-t0:.0f} s", flush=True)
    np.savez_compressed(OUT / "sg13_hv_nmos_table.npz", **data)
