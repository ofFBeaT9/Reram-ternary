"""Select-transistor sizing study on the reference model (stand-in MOSFET, to be repeated with PSP).
For each width: lowest gate voltage at which 1 us pulse-and-verify SET reaches each read-current target,
and whether RESET from the deepest level succeeds."""
import sys, json
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reram_stanford import *
from experiments import evolve, read
from ispva import CAL, ispva_set, ispva_reset

TARGETS = {"LRS1": 18.08e-6, "LRS2": 31.01e-6, "LRS3": 43.59e-6}    # IHP array means at 0.2 V
res = {}
for W in (1.5e-6, 3.0e-6, 4.5e-6, 6.0e-6):
    mos = NMOS(W=W, L=0.45e-6)
    row = {"ron_read_kohm": 0.2 / mos.ids(1.7, 0.2) / 1e3 if mos.ids(1.7, 0.2) > 0 else None}
    for name, tgt in TARGETS.items():
        found = None
        for vg in np.arange(1.0, 3.31, 0.1):
            r = ispva_set(CAL, mos, float(vg), tgt, 1.8e-9, clamp=False)
            if r["ok"]:
                found = dict(vg=round(float(vg), 1), amp=r["amp"], pulses=r["pulses"], iread_uA=r["iread_uA"], gap_nm=r["gap_nm"]); break
        row[name] = found
    g3 = 0.692e-9   # gap that gives 43.6 uA across the cell at 0.2 V
    for vg in (2.7, 3.3):
        r = ispva_reset(CAL, mos, 6e-6, g3, vgate=vg)
        row[f"reset_LRS3_vg{vg}"] = dict(ok=r["ok"], amp=r["amp"], pulses=r["pulses"], iread_uA=r["iread_uA"])
    res[f"W{W*1e6:.1f}um"] = row
    print(f"W = {W*1e6:.1f} um (L 0.45 um): on-resistance at read {row['ron_read_kohm']:.2f} kOhm")
    for name in TARGETS:
        f = row[name]
        print("   SET  %s: %s" % (name, "not reached up to Vg 3.3 V" if f is None else f"Vg {f['vg']} V, amplitude {f['amp']:.1f} V, {f['pulses']} pulses, read {f['iread_uA']:.1f} uA"))
    for vg in (2.7, 3.3):
        r = row[f"reset_LRS3_vg{vg}"]
        print(f"   RESET LRS3 at Vg {vg}: ok={r['ok']}, amplitude {r['amp']:.1f} V, {r['pulses']} pulses, read {r['iread_uA']:.2f} uA")
json.dump(res, open(__file__.rsplit('/', 2)[0] + "/results/device_sizing.json", "w"), indent=1)
