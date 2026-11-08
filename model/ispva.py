"""Incremental-step pulse-and-verify programming (the published IHP M-ISPVA scheme) on the reference model."""
import sys, json
from dataclasses import replace
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reram_stanford import *
from experiments import evolve, read

CAL = replace(IHP_PUBLISHED, Ea=1.0, v0=2.79)      # re-fitted kinetics, see calibrate.py
MOS = NMOS(W=1.5e-6, L=0.45e-6)


def ispva_set(p, mos, vgate, target, g, pw=1e-6, v0=0.5, v1=2.5, dv=0.1, clamp=True):
    gmin = p.gmin(vgate) if clamp else 0.05e-9
    n = 0
    for amp in np.arange(v0, v1 + 1e-9, dv):
        g = evolve(p, mos, float(amp), vgate, g, pw, gmin); n += 1
        i = read(p, mos, g)
        if i >= target:
            return dict(ok=True, amp=float(amp), pulses=n, gap_nm=g * 1e9, iread_uA=i * 1e6)
    return dict(ok=False, amp=float(amp), pulses=n, gap_nm=g * 1e9, iread_uA=read(p, mos, g) * 1e6)


def ispva_reset(p, mos, target, g, vgate=2.7, pw=1e-6, v0=0.5, v1=2.5, dv=0.1):
    n = 0
    for amp in np.arange(v0, v1 + 1e-9, dv):
        g = evolve(p, mos, float(amp), vgate, g, pw, 0.05e-9, polarity=-1); n += 1
        i = read(p, mos, g)
        if i <= target:
            return dict(ok=True, amp=float(amp), pulses=n, gap_nm=g * 1e9, iread_uA=i * 1e6)
    return dict(ok=False, amp=float(amp), pulses=n, gap_nm=g * 1e9, iread_uA=read(p, mos, g) * 1e6)


if __name__ == "__main__":
    out = {}
    print("1 us pulses, amplitude 0.5 -> 2.5 V in 0.1 V steps, verify read at 0.2 V (gate 1.7 V)")
    for pw in (1e-6, 100e-9, 25e-9):
        print(f" pulse width {pw*1e9:.0f} ns")
        for vg in (1.0, 1.2, 1.5, 1.6):
            # target: 95 % of the read current the gate-voltage floor allows (model-specific)
            g_floor = max(CAL.gmin(vg), 0.05e-9)
            tgt = 0.95 * read(CAL, MOS, g_floor)
            r = ispva_set(CAL, MOS, vg, tgt, 1.8e-9, pw=pw)
            out[f"set_pw{pw:g}_vg{vg}"] = r
            print(f"   SET  Vg {vg}: target {tgt*1e6:5.1f} uA -> ok={r['ok']} at {r['amp']:.1f} V after {r['pulses']} pulses, gap {r['gap_nm']:.3f} nm, read {r['iread_uA']:.1f} uA")
        for name, g in (("LRS1", 0.95e-9), ("LRS3", 0.725e-9)):
            r = ispva_reset(CAL, MOS, 3e-6, g, pw=pw)
            out[f"reset_pw{pw:g}_{name}"] = r
            print(f"   RESET {name}: ok={r['ok']} at {r['amp']:.1f} V after {r['pulses']} pulses, gap {r['gap_nm']:.3f} nm, read {r['iread_uA']:.2f} uA")
    json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/device_ispva.json", "w"), indent=1)
