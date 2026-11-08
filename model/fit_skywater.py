"""Fit of the device model's reset kinetics and cell-to-cell spread to SkyWater's measured yields (9 October 2026).

Why. With SkyWater's own model parameters (model/sky130_port.py) the 1T1R does not reset at SkyWater's published
reset condition (word line 2.5 V, source line 2.6 V, 1 us) at any transistor width; on silicon 90.83 % of the cells
reset there. The model's reset is too slow. SkyWater's yield table is the one public silicon statistic of a HfO2
1T1R that can calibrate (a) how much faster reset is on silicon than in the model and (b) how much the cells differ
from each other. (b) is what the IHP reset-gate study (model/program_mc.py) had to assume.

Data (sky130_fd_pr_reram v2.0.3, docs/technology_specifications.rst, checked against original_tables.png):
  1T1R #5: reset WL 2.5 V, BL 0, SL 2.6 V, 1000 ns: 90.83 %; set WL 1.7 V, BL 2.4 V, 1000 ns: 97.45 %
  1T4R #4: same reset and set: 91.25 %, 99.78 %
  1T4R #9: reset WL 2.5-3.0 V (0.1 V steps), SL 2.4-3.0 V (0.1 V steps; WL stepped first, then SL): 99.41 %
  After forming the cells are at 30-120 uS; the HRS is about 4.5 uS (same document).
Not published, so ASSUMED and varied: the pass criteria (reset: read conductance <= 6 / 10 / 15 uS; set: >= 20 /
30 / 40 uS, read at 0.2 V with the gate at 3.3 V), the transistor width (1, 2, 4 um; L 0.5 um), the starting state
after forming (log-uniform 30-100 uS for the cell alone: the model's smallest gap, 0.1 nm, conducts 103 uS, so
the top of the published 30-120 uS range cannot be represented), and the read voltage.

Model. Reference equations (model/reram_stanford.py) at SkyWater's parameters (sky130_port.P), SkyWater's nhv
transistor as an ngspice table (sky130_port.mos_table, corner tt). Two fitted numbers:
  F  - multiplier on the switching rate in the reset direction only (the set direction is left as published),
  k  - spread scale, in units of the "1x" spread of model/program_mc.py: each cell gets
       v0 * exp(0.5 k z1), Ea + 0.03 k z2 (eV), I0 * exp(0.10 k z3), z ~ N(0, 1), the same draws for set and reset.
For each k, F is found so that the single-pulse reset yield is 90.83 %; k is then the value at which the set
yield (of the cells that reset) is 97.45 %. The 1T4R #9 stepped reset (99.41 %) is predicted, not fitted; it is a
different structure (one transistor for four cells), so it is a consistency check only.
Every failure is attributed to the spread. Cells that are defective (stuck) are counted as slow cells, so the
fitted k is an upper bound on the kinetic spread.

Output: results/fit_skywater.json. Then:  python3 model/fit_skywater.py transfer
  re-runs the IHP reset-gate study (program_mc.reset_gate_study) with the fitted spread, gates 2.5-3.3 V.
"""
import json, os, sys, math
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import sky130_port as S                                   # noqa: E402
from experiments import evolve, read                      # noqa: E402

P = S.P
N_DEV = int(os.environ.get("FIT_N", "400"))
CACHE = Path(os.environ.get("FIT_CACHE", "/tmp/fit_skywater_cache"))
VREAD, VG_READ = 0.2, 3.3
RESET_Y, SET_Y, LADDER_Y = 0.9083, 0.9745, 0.9941
KS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
WIDTHS = (1.0, 2.0, 4.0)
CRIT = {"6/20": (6e-6, 20e-6), "10/30": (10e-6, 30e-6), "15/40": (15e-6, 40e-6)}   # reset <=, set >= (S)
LOGF_LO, LOGF_HI = 0.0, 16.0


def mos(w, corner="tt"):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"nhv_{corner}_{w}.npy"
    if not f.exists():
        np.save(f, S.mos_table(corner, w))
    return S.SkyNHV(np.load(f))


def g_read(m, g):
    return read(P, m, g, VREAD, VG_READ) / VREAD


def gap_for(G):
    """Gap at which the cell alone (no transistor) conducts G at 0.2 V."""
    g = P.g0 * math.log(P.I0 * math.sinh(VREAD / P.V0) / (VREAD * G))
    return min(max(g, S.GMIN), S.GMAX)


def draws(n=N_DEV, seed=7):
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n, 3))
    u = rng.random(n)                           # starting state after forming, log-uniform 30-100 uS (cell alone)
    return z, 30e-6 * (100 / 30) ** u


def cell(k, z):
    return replace(P, v0=P.v0 * math.exp(0.5 * k * z[0]), Ea=P.Ea + 0.03 * k * z[1], I0=P.I0 * math.exp(0.10 * k * z[2]))


def reset_pulse(p, m, F, g, wl=2.5, sl=2.6):
    return evolve(replace(p, v0=p.v0 * F), m, sl, wl, g, 1e-6, S.GMIN, polarity=-1, gmax=S.GMAX)


def set_pulse(p, m, g, wl=1.7, bl=2.4):
    return evolve(p, m, bl, wl, g, 1e-6, S.GMIN)


def crit_logF(args):
    """Smallest log10 F at which this cell resets (read <= Gth) with one pulse; LOGF_HI+1 if none up to 1e16."""
    w, k, z, g0, gth = args
    m = mos(w); p = cell(k, z)
    ok = lambda lf: g_read(m, reset_pulse(p, m, 10 ** lf, g0)) <= gth
    if not ok(LOGF_HI):
        return LOGF_HI + 1
    lo, hi = LOGF_LO, LOGF_HI
    if ok(lo):
        return lo
    while hi - lo > 0.02:
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def set_after(args):
    """Reset with F, then set; returns (reset ok, set ok, read after set)."""
    w, k, z, g0, F, gr, gs = args
    m = mos(w); p = cell(k, z)
    g = reset_pulse(p, m, F, g0)
    r_ok = g_read(m, g) <= gr
    g2 = set_pulse(p, m, g)
    return bool(r_ok), bool(g_read(m, g2) >= gs), g_read(m, g2)


def ladder(args):
    """1T4R #9 procedure on a 1T1R: SL from 2.4 to 3.0 V; for each SL, WL from 2.5 to 3.0 V; stop when reset."""
    w, k, z, g0, F, gr = args
    m = mos(w); p = cell(k, z); g = g0; n = 0
    for sl in np.arange(2.4, 3.0001, 0.1):
        for wl in np.arange(2.5, 3.0001, 0.1):
            g = reset_pulse(p, m, F, g, wl=float(wl), sl=float(sl)); n += 1
            if g_read(m, g) <= gr:
                return True, n
    return False, n


def fit(pool):
    z, G0 = draws()
    out = dict(n_cells=N_DEV, ks=KS, widths=WIDTHS, criteria=CRIT, cases={})
    for w in WIDTHS:
        m = mos(w)
        g0 = [gap_for(G) for G in G0]
        nominal_set = g_read(m, set_pulse(P, m, S.GMAX)) * 1e6
        for cname, (gr, gs) in CRIT.items():
            rows = []
            for k in KS:
                lfs = np.array(pool.map(crit_logF, [(w, k, z[i], g0[i], gr) for i in range(N_DEV)]))
                logF = float(np.quantile(lfs, RESET_Y))           # 90.83 % of the cells reset at this F
                F = 10 ** logF
                res = pool.map(set_after, [(w, k, z[i], g0[i], F, gr, gs) for i in range(N_DEV)])
                r_ok = [r for r in res if r[0]]
                set_y = sum(r[1] for r in r_ok) / len(r_ok)
                lad = pool.map(ladder, [(w, k, z[i], g0[i], F, gr) for i in range(N_DEV)])
                lad_y = sum(x[0] for x in lad) / N_DEV
                row = dict(k=k, log10F=round(logF, 3), reset_yield=round(sum(r[0] for r in res) / N_DEV, 4),
                           set_yield=round(set_y, 4), ladder_yield=round(lad_y, 4),
                           ladder_pulses_max=int(max(x[1] for x in lad)),
                           crit_logF_spread_decades_10_90=round(float(np.quantile(lfs, 0.9) - np.quantile(lfs, 0.1)), 2))
                rows.append(row)
                print(w, cname, json.dumps(row), flush=True)
            # interpolate k where set yield = 97.45 % (set yield falls as k grows)
            ks = [r["k"] for r in rows]; sy = [r["set_yield"] for r in rows]
            k_fit = None
            for a in range(len(rows) - 1):
                if sy[a] >= SET_Y >= sy[a + 1] and sy[a] != sy[a + 1]:
                    k_fit = ks[a] + (sy[a] - SET_Y) / (sy[a] - sy[a + 1]) * (ks[a + 1] - ks[a]); break
            out["cases"][f"W {w} um, criteria {cname}"] = dict(nominal_set_read_uS=round(nominal_set, 2), rows=rows,
                                                                k_fit=None if k_fit is None else round(k_fit, 2))
            (ROOT / "results" / "fit_skywater.json").write_text(json.dumps(out, indent=1))
    return out


def _reset_one(args):
    """One IHP device, reset phase only (program_mc.reset_gate_study, split per device for many cores)."""
    corner, p, vg, g0 = args
    import program_mc as PM
    r = PM.ispva_reset(p, PM.TableNMOS(4.5, corner), PM.RESET_TARGET, g0, vgate=vg)
    return r["ok"], r["pulses"]


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "transfer":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    sys.argv = [sys.argv[0], str(n)]            # program_mc reads its device count from argv at import
    import program_mc as PM
    path = ROOT / "results" / "fit_skywater.json"
    res = json.loads(path.read_text())
    kf = [c["k_fit"] for c in res["cases"].values() if c["k_fit"] is not None]
    res["k_fit_range"] = [min(kf), max(kf)]
    vgates = (2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.3)
    tr = {}
    with Pool(int(os.environ.get("FIT_JOBS", os.cpu_count() or 1))) as pool:
        for kk in sorted({round(x, 2) for x in kf}):
            s_v, s_e, s_i = 0.5 * kk, 0.03 * kk, 0.10 * kk
            for c in ("tt", "ss"):
                # the same devices as program_mc.reset_gate_study: same seed and draw order
                mos = PM.TableNMOS(4.5, c)
                rng = np.random.default_rng(1)
                g0 = PM.ispva_set(PM.CAL, mos, PM.VG_SET, PM.SET_TARGET, PM.CAL.gap_max, clamp=False)["gap_nm"] * 1e-9
                devs = [replace(PM.CAL, v0=PM.CAL.v0 * float(np.exp(rng.normal(0, s_v))), Ea=PM.CAL.Ea + float(rng.normal(0, s_e)),
                                I0=PM.CAL.I0 * float(np.exp(rng.normal(0, s_i)))) for _ in range(n)]
                out = {}
                for vg in vgates:
                    rs = pool.map(_reset_one, [(c, p, vg, g0) for p in devs])
                    out[f"vg {vg}"] = dict(failed=sum(not ok for ok, _ in rs), pulses_max=max(k for _, k in rs),
                                           pulses_mean=round(float(np.mean([k for _, k in rs])), 2))
                tr[f"{c} k={kk}"] = out
                print(c, kk, json.dumps(out), flush=True)
    res["transfer_ihp_reset_gate"] = dict(n_cells=n, note="IHP model (ispva.CAL, sg13_hv_nmos W 4.5 um), 21-step reset ladder 0.5-2.5 V, "
                                          "target 6 uA; spread = fitted k in program_mc '1x' units; no reset-rate correction "
                                          "applied to IHP (its reset voltage already matches IHP's published 0.6-0.9 V)", runs=tr)
    path.write_text(json.dumps(res, indent=1))
    sys.exit(0)

if __name__ == "__main__":
    for w in WIDTHS:
        mos(w)                                   # build the tables once, before the workers start
    with Pool(int(os.environ.get("FIT_JOBS", os.cpu_count() or 1))) as pool:
        fit(pool)
