"""Read path, first cut: trip current across corners, transient row reads, supply energy.
Writes results/gnucap_sense.json. Slow (PSP models in transient): about half a minute per transient."""
import json, sys, time
from pathlib import Path
import numpy as np
import sense

OUT = Path(__file__).resolve().parents[2] / "results"
IB = 5e-6
# gaps (nm) that give these 1T1R read currents at 0.2 V with the 4.5/0.45 um select transistor, typical corner
# (computed with model/sizing_real_mos.gap_for)
GAP = {"LRS3 mean 43.6 uA": 0.6508, "LRS3 mean-6sigma 34.3 uA": 0.7270, "HRS mean+6sigma 14 uA": 0.9969,
       "reset target 6 uA": 1.2413, "HRS mean 2.85 uA": 1.4526}


def trip(d):
    i, out = d[:, 0], d[:, 3]
    k = np.where(out > 0.6)[0][0]
    return i[k - 1] + (i[k] - i[k - 1]) * (0.6 - out[k - 1]) / (out[k] - out[k - 1])


def analyse(t, t_wl=1e-9):
    d = t["data"]
    tm, wl, bl, sn, out, ivdd = d[:, 0], d[:, 1], d[:, 2], d[:, 3], d[:, 4], -d[:, 5]
    hi = np.where(out > 0.6)[0]
    t_out = float(tm[hi[0]] - t_wl) if hi.size else None
    sel = tm >= t_wl
    e10 = float(np.trapezoid(ivdd[sel] * 1.2, tm[sel]))            # supply energy from WL rise to the end, J
    return dict(bl_idle_V=round(float(bl[0]), 4), bl_end_V=round(float(bl[-1]), 4), bl_max_V=round(float(bl.max()), 4),
                out_end_V=round(float(out[-1]), 3), t_out_ns=None if t_out is None else round(t_out * 1e9, 2),
                i_vdd_idle_uA=round(float(ivdd[0]) * 1e6, 2), i_vdd_end_uA=round(float(ivdd[-1]) * 1e6, 2),
                e_supply_pJ=round(e10 * 1e12, 4), window_ns=round(float(tm[-1] - t_wl) * 1e9, 2))


if __name__ == "__main__":
    res = {"ib_uA": IB * 1e6, "sizes": sense.SIZES, "dc": {}, "tran": {}}
    for c in ("tt", "ss", "ff", "sf", "fs"):
        d = sense.dc_trip(c, ib=IB)["data"]
        bl = lambda x: float(np.interp(x, d[:, 0] * 1e6, d[:, 1]))
        res["dc"][c] = dict(trip_uA=round(trip(d) * 1e6, 2), bl_V_at_1uA=round(bl(1), 3), bl_V_at_3uA=round(bl(3), 3),
                            bl_V_at_14uA=round(bl(14), 3), bl_V_at_24uA=round(bl(24), 3))
        print(c, res["dc"][c], flush=True)
    for corner in ("tt", "ss", "ff"):
        for name, gap in GAP.items():
            for uname, ugap in (("others LRS3", 0.6508), ("others HRS", 1.4526)):
                if corner != "tt" and (uname != "others LRS3" or "6sigma" not in name):
                    continue                                   # corners: worst-case cells only
                t0 = time.time()
                r = analyse(sense.read_tran(gap, ugap, corner, ib=IB, t_end=11e-9))
                res["tran"][f"{corner} | {name} | {uname}"] = r
                print(corner, name, uname, r, f"{time.time()-t0:.0f} s", flush=True)
                (OUT / "gnucap_sense.json").write_text(json.dumps(res, indent=1))
