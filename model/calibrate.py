"""Re-fit of the switching kinetics.

Finding: with the parameters printed in Table 3 of the 2021 IHP paper (Ea = 0.6 eV, v0 = 0.4 m/s)
this implementation sets at 0.25 V and a 0.2 V read erases the HRS within a second, which contradicts
the measured set voltages (0.65-0.75 V) in the same paper. The static parameters (I0, g0, V0, gaps) are
kept. The kinetics are re-fitted with two constraints:
  - Ea = 1.0 eV, inside the 0.97-1.16 eV range IHP measured from retention (Perez et al., JEDS 2019);
  - v0 chosen so that the quasi-static set voltage is 0.70 V under the published sweep (0.6 V/s).
"""
import sys, json, math
from dataclasses import replace
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reram_stanford import *
from experiments import *

MOS = NMOS(W=1.5e-6, L=0.45e-6)


def vset_fine(p, vgate=1.2, clamp=True):
    tr, v = dc_sweep_set(p, MOS, vgate, p.gap_max, step=0.01, rate=0.6, clamp=clamp)
    return v, tr


def fit_v0(ea=1.0, target=0.70):
    lo, hi = -3.0, 6.0     # log10(v0)
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        p = replace(IHP_PUBLISHED, Ea=ea, v0=10 ** mid)
        v, _ = vset_fine(p)
        if v is None or v > target:
            lo = mid
        else:
            hi = mid
    return 10 ** (0.5 * (lo + hi))


if __name__ == "__main__":
    res = {}
    v0 = fit_v0()
    p = replace(IHP_PUBLISHED, Ea=1.0, v0=v0)
    res["calibrated"] = {"Ea_eV": 1.0, "v0_m_per_s": v0}
    print(f"fitted v0 = {v0:.3g} m/s at Ea = 1.0 eV")
    res["dc_set"] = {}
    for vg in (1.0, 1.2, 1.6):
        tr, vs = dc_sweep_set(p, MOS, vg, p.gap_max)           # published sweep: 0.05 V steps
        g = tr[-1][2]; ir = read(p, MOS, g)
        res["dc_set"][vg] = {"vset": vs, "gap_nm": g * 1e9, "iread_uA": ir * 1e6, "R_1T1R_kohm": 0.2 / ir / 1e3,
                             "R_cell_kohm": 0.2 / float(current(p, 0.2, g)) / 1e3}
        print(f"  SET  Vg {vg}: Vset {vs:.2f} V, gap {g*1e9:.3f} nm, 1T1R read {ir*1e6:.1f} uA ({0.2/ir/1e3:.1f} kOhm), cell alone {0.2/float(current(p,0.2,g))/1e3:.1f} kOhm")
    res["dc_reset"] = {}
    for name, g0_ in (("LRS1", 0.95e-9), ("LRS2", 0.85e-9), ("LRS3", 0.725e-9)):
        tr, vr = dc_sweep_reset(p, MOS, 2.7, g0_)
        g = tr[-1][2]; ir = read(p, MOS, g)
        res["dc_reset"][name] = {"vreset": vr, "gap_nm": g * 1e9, "iread_uA": ir * 1e6}
        print(f"  RESET from {name}: Vreset {vr:.2f} V, final gap {g*1e9:.3f} nm, read {ir*1e6:.2f} uA ({0.2/ir/1e3:.0f} kOhm)")
    # read disturb
    for hold in (1.0, 1e3, 1e6):
        g = evolve(p, MOS, 0.2, 1.7, 1.8e-9, hold, 0.05e-9)
        print(f"  read disturb: HRS gap after {hold:g} s at 0.2 V: {g*1e9:.4f} nm")
        res.setdefault("read_disturb_gap_nm", {})[hold] = g * 1e9
    # self-limited set without the gmin clamp (physical compliance by the transistor)
    res["self_limited"] = {}
    for vg in (1.0, 1.2, 1.5):
        tr, vs = dc_sweep_set(p, MOS, vg, p.gap_max, clamp=False)
        g = tr[-1][2]; ir = read(p, MOS, g)
        icomp = MOS.ids(vg, 1.0)
        res["self_limited"][vg] = {"vset": vs, "gap_nm": g * 1e9, "iread_uA": ir * 1e6, "icomp_uA": icomp * 1e6}
        print(f"  no clamp Vg {vg}: Vset {vs:.2f}, gap {g*1e9:.3f} nm, read {ir*1e6:.1f} uA; transistor saturation current {icomp*1e6:.0f} uA")
    json.dump(res, open(__file__.rsplit('/', 2)[0] + "/results/device_calibration.json", "w"), indent=1)
