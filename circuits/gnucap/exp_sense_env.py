"""Read path over temperature and supply: trip current and bit-line voltage of the first-cut sense amplifier
at five process corners, -40 / 27 / 85 / 125 C and VDD 1.08 / 1.20 / 1.32 V; then transient reads of the
worst-case cells at the hot slow and cold fast extremes. Writes results/gnucap_sense_env.json.

What varies: the transistors (PSP 103 with temperature). What does not: the 25 uA reference current and the
0.2 V reference are ideal sources, and the ReRAM model has no temperature term in its conduction, so the cell
currents at a given gap do not change with temperature here. The margins are therefore those of the sense
amplifier alone, against the published 6-sigma device tails (HRS 14 uA, LRS3 34.3 uA)."""
import json, time
from pathlib import Path
import numpy as np
import sense, exp_sense

OUT = Path(__file__).resolve().parents[2] / "results" / "gnucap_sense_env.json"
IB = exp_sense.IB
HRS6, LRS6 = 14.0, 34.3                    # published 6-sigma tails, uA (results/gnucap_sense.json, GAP table)

if __name__ == "__main__":
    res = dict(ib_uA=IB * 1e6, tails_uA=dict(hrs_6sigma=HRS6, lrs3_6sigma=LRS6), dc={}, tran={})
    for c in ("tt", "ss", "ff", "sf", "fs"):
        for T in (-40, 27, 85, 125):
            for v in (1.08, 1.2, 1.32):
                d = sense.dc_trip(c, temp=T, ib=IB, vdd=v)["data"]
                tr = exp_sense.trip(d) * 1e6
                bl = lambda x: float(np.interp(x, d[:, 0] * 1e6, d[:, 1]))
                res["dc"][f"{c} {T} C {v} V"] = dict(trip_uA=round(tr, 3), margin_uA=round(min(tr - HRS6, LRS6 - tr), 2),
                                                     bl_V_at_3uA=round(bl(3), 4), bl_V_at_14uA=round(bl(14), 4), bl_V_at_24uA=round(bl(24), 4))
        print(c, flush=True)
    trips = [x["trip_uA"] for x in res["dc"].values()]
    bls = [x["bl_V_at_3uA"] for x in res["dc"].values()]
    res["summary"] = dict(trip_min_uA=min(trips), trip_max_uA=max(trips), margin_min_uA=min(x["margin_uA"] for x in res["dc"].values()),
                          bl_at_3uA_min_V=min(bls), bl_at_3uA_max_V=max(bls), cases=len(trips))
    print(res["summary"], flush=True)
    for corner, T in (("ss", 125), ("ff", -40), ("ss", -40), ("ff", 125)):
        for name in ("LRS3 mean-6sigma 34.3 uA", "HRS mean+6sigma 14 uA"):
            t0 = time.time()
            r = exp_sense.analyse(sense.read_tran(exp_sense.GAP[name], 0.6508, corner, ib=IB, t_end=11e-9, temp=T))
            res["tran"][f"{corner} {T} C | {name} | others LRS3"] = r
            print(corner, T, name, r, f"{time.time() - t0:.0f} s", flush=True)
            OUT.write_text(json.dumps(res, indent=1))
    OUT.write_text(json.dumps(res, indent=1))
