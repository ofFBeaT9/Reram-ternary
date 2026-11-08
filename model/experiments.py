"""Quasi-static sweeps and pulse programming of a 1T1R cell with the reference model."""
import math, json, sys
from dataclasses import replace
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reram_stanford import *

DG = 2e-12   # largest gap change per integration sub-step (m)


def evolve(p, mos, v_app, vgate, g, dt, gmin, polarity=+1, gmax=None):
    """Hold the applied voltage for dt; re-solve the 1T1R operating point as the gap moves."""
    gmax = p.gap_max if gmax is None else gmax
    t = 0.0
    solve = solve_1t1r if polarity > 0 else solve_1t1r_reset
    n = 0
    while t < dt and n < 200000:
        v, i = solve(p, mos, v_app, vgate, g)
        r = float(gap_rate(p, v, g, i))
        if abs(r) < 1e-30:
            break
        h = min(dt - t, DG / abs(r))
        g += r * h
        t += h; n += 1
        if g <= gmin:
            g = gmin; break
        if g >= gmax:
            g = gmax; break
    return g


def read(p, mos, g, vread=0.2, vgate=1.7):
    return solve_1t1r(p, mos, vread, vgate, g)[1]


def dc_sweep_set(p, mos, vgate, g_start, vmax=1.5, step=0.05, rate=0.6, clamp=True):
    """0 -> vmax -> 0 on the bit line. Returns list of (V, I, gap) and the set voltage (largest dI/dV jump)."""
    dwell = step / rate
    gmin = p.gmin(vgate) if clamp else 0.05e-9
    vs = list(np.arange(step, vmax + 1e-9, step)); vs = vs + vs[-2::-1]
    g = g_start; out = []
    for v in vs:
        g = evolve(p, mos, v, vgate, g, dwell, gmin)
        vc, i = solve_1t1r(p, mos, v, vgate, g)
        out.append((v, i, g))
    up = out[:len(out) // 2 + 1]
    gaps = [o[2] for o in up]
    drops = [gaps[k - 1] - gaps[k] for k in range(1, len(gaps))]
    vset = up[1 + int(np.argmax(drops))][0] if max(drops) > 0 else None
    return out, vset


def dc_sweep_reset(p, mos, vgate, g_start, vmax=1.5, step=0.05, rate=0.6, gmax=None):
    dwell = step / rate
    vs = list(np.arange(step, vmax + 1e-9, step)); vs = vs + vs[-2::-1]
    g = g_start; out = []
    for v in vs:
        g = evolve(p, mos, v, vgate, g, dwell, 0.05e-9, polarity=-1, gmax=gmax)
        vc, i = solve_1t1r_reset(p, mos, v, vgate, g)
        out.append((v, i, g))
    up = out[:len(out) // 2 + 1]
    cur = [abs(o[1]) for o in up]
    vreset = up[int(np.argmax(cur))][0]      # voltage of the current maximum
    return out, vreset


if __name__ == "__main__":
    mos = NMOS()
    for name, p in (("published (Ea = 0.6 eV)", IHP_PUBLISHED),):
        print(name)
        for vg in (1.0, 1.2, 1.6):
            tr, vset = dc_sweep_set(p, mos, vg, p.gap_max)
            g_end = tr[-1][2]
            print(f"  Vg {vg}: Vset = {vset:.2f} V, final gap {g_end*1e9:.3f} nm, read {read(p, mos, g_end)*1e6:.1f} uA, 1T1R R = {0.2/read(p, mos, g_end)/1e3:.1f} kOhm")
        print("  gap after holding HRS (1.8 nm) at 0.2 V read bias for 1 s:", round(evolve(p, mos, 0.2, 1.7, p.gap_max, 1.0, 0.05e-9) * 1e9, 3), "nm")
