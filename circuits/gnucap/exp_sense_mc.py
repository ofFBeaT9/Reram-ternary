"""Mismatch Monte Carlo of the sense amplifier's trip current (PDK mismatch model, typical corner).
For every seed the cell current is swept and the trip point is read off. Writes results/gnucap_sense_mc.json."""
import json, sys
from pathlib import Path
import numpy as np
import gnucap_run as g
import sense

OUT = Path(__file__).resolve().parents[2] / "results"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
I0, I1, DI = 20e-6, 29e-6, 0.25e-6

if __name__ == "__main__":
    trips = []
    npts = int(round((I1 - I0) / DI)) + 1
    for first in range(1, N + 1, 25):                       # 25 seeds per Gnucap run
        last = min(first + 24, N)
        deck = g.header("tt", lv=True, mc=True) + sense.amp(mm=1, ib=5e-6) + f"""
spice
Icell bl 0 dc 0
.verilog
print dc v(out)
dc Icell {I0} {I1} {DI} $seed {first} {last} 1
"""
        d = g.run(deck, timeout=3000)[0]["data"]
        d = d.reshape(-1, npts, 2)
        for blk in d:
            i, out = blk[:, 0], blk[:, 1]
            hi = np.where(out > 0.6)[0]
            if hi.size == 0 or hi[0] == 0:
                trips.append(float("nan")); continue
            k = hi[0]
            trips.append(float(i[k - 1] + (i[k] - i[k - 1]) * (0.6 - out[k - 1]) / (out[k] - out[k - 1])))
        t = np.array(trips)
        print(f"seeds 1..{last}: mean {np.nanmean(t)*1e6:.3f} uA, sigma {np.nanstd(t, ddof=1)*1e6:.3f} uA, min {np.nanmin(t)*1e6:.2f}, max {np.nanmax(t)*1e6:.2f}, outside sweep {int(np.isnan(t).sum())}", flush=True)
        (OUT / "gnucap_sense_mc.json").write_text(json.dumps(dict(n=len(trips), mean_uA=float(np.nanmean(t) * 1e6), sigma_uA=float(np.nanstd(t, ddof=1) * 1e6),
                                                                 min_uA=float(np.nanmin(t) * 1e6), max_uA=float(np.nanmax(t) * 1e6), trips_uA=[round(x * 1e6, 3) for x in trips]), indent=1))
