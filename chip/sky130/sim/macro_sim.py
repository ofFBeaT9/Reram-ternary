"""Transistor-level simulation of programming through the SKY130 periphery, with the ReRAM model at SkyWater's
parameters (11 October 2026).

Circuit (ngspice, open_pdks sky130B transistor models through spice.py): two rows x two ternary columns of the
2T2R array (8 devices, each with its own select transistor nfet_g5v0d10v5 W 1.0 / L 0.5 um as drawn), driven by the
cells of periph.spice exactly as the array controller drives them (rtl/chip/tcim_actl.sv):
  word-line rail: pad -> rail transmission gate (W 8/16 um) -> word-line driver of each row (row 0 selected);
  bit lines and source lines: bld / sld drivers in the mode of the operation; line resistance 75 / 40 ohm,
  word line 4.2 kohm + 100 fF lumped.
ReRAM: the Stanford-PKU equations (as model/reram_stanford_ihp.lib; V0 and v0 renamed Vs and vr0, since with
ngspice's HSPICE mode, needed by the PDK, parameter names are case-insensitive and v0 replaced V0) at SkyWater's parameters (model/sky130_port.P),
with the reset-direction rate multiplied by F (model/fit_skywater.py: F from SkyWater's 90.83 % single-pulse reset
yield). Top electrode on the bit line.
Runs:
  0. Check of the subcircuit with the rate factor against the Python reference (bare cell, constant voltage, 1 us).
  1. Set ladder on device P of column 0, row 0 from the reset state (4.5 uS): 1 us pulses, program rail VPRG stepped
     0.1 V from 1.4 V, word-line rail 1.7 / 2.0 / 2.5 V; pulses until the read conductance reaches the set target.
  2. Reset ladder on the same device from 60 uS: word-line rail 2.5-3.0 V, then VPRG 2.4-3.0 V in 0.1 V steps
     (SkyWater's stepped scheme), for a cell with the fitted F (k = 1, W 1 um, criteria 6/20) and cells 1-4 decades
     slower to reset.
  Method: quasi-static (pulse() below); cross-checked against full ngspice transients where those converge.
  3. Disturb: largest change of read conductance of the seven other devices during runs 1 and 2 (the N device of
     the same column, both devices of the other column (inhibited), all four devices of the unselected row).
Read conductance: I(0.2 V) / 0.2 V of the bare device. Writes results/sky130_chip/macro_sim.json."""
import json, math, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "model"))
import spice as S                                          # noqa: E402
from reram_stanford import step_gap, current, gap_rate     # noqa: E402
from dataclasses import replace                            # noqa: E402

TOX = 5.0e-9
# model/sky130_port.P (SkyWater's sky130_fd_pr_reram v2.0.3 parameters), written out to avoid importing its PDK paths
from reram_stanford import ReRAMParams                     # noqa: E402
P = ReRAMParams(I0=6.140e-5, g0=TOX - 4.7249e-9, V0=0.430, v0=2 * 150.0, Ea=1.5, a0=0.25e-9, tox=TOX, gamma0=16.5, beta=1.25,
                alpha=3.0, Rth=0.23e-9 / 3.1825e-16, T0=300.0, gap_max=TOX - 3.3e-9, Kth=0.0, C=TOX - 4.9e-9, WL=1.0)
GMIN, GMAX = TOX - 4.9e-9, TOX - 3.3e-9
FIT = json.loads((ROOT / "results" / "fit_skywater.json").read_text())["cases"]["W 1.0 um, criteria 6/20"]["rows"]
LOGF = {r["k"]: r["log10F"] for r in FIT}
CELLS = (HERE / "periph.spice").read_text()
OUT = ROOT / "results" / "sky130_chip" / os.environ.get("MACRO_SIM_OUT", "macro_sim.json")
# series resistance of a bit line and of a source line from the cell to its driver (ohm): the array's own wiring by
# default; macro_rc.py adds the routed wiring of the drawn macro (RBL / RSL in the environment)
RBL = float(os.environ.get("RBL", "75")); RSL = float(os.environ.get("RSL", "40"))
# verify targets: the sense-amplifier trips of periph_sim.json, taken at their worst corner (a set must pass the
# highest set trip, a reset the lowest reset trip)
_D = json.loads((ROOT / "results" / "sky130_chip" / "periph_sim.json").read_text())["D"]
SET_TARGET = max(v for k, v in _D.items() if k.startswith("trip set")) * 1e-6
RESET_TARGET = min(v for k, v in _D.items() if k.startswith("trip reset")) * 1e-6
# worst-case runs (macro_rc.py) raise the set target to the highest set-verify trip seen with transistor mismatch
if os.environ.get("SET_TARGET_US"):
    SET_TARGET = float(os.environ["SET_TARGET_US"]) * 1e-6

RRAM = f""".subckt rr te be gap I0={P.I0} g0={P.g0 * 1e9:.6g} Vs={P.V0} vr0={P.v0 * 1e9:.6g} Ea={P.Ea} a0={P.a0 * 1e9:.6g}
+ tox={P.tox * 1e9:.6g} gamma0={P.gamma0} beta={P.beta} alpha={P.alpha} Rth={P.Rth:.6g} T0={P.T0} gap_min={GMIN * 1e9:.6g}
+ gap_max={GMAX * 1e9:.6g} wsoft=0.01 cstate=1e-9 gap_ini=1.0 Fr=1
.param kb=8.617333262e-5
Cg gap 0 {{cstate}} ic={{gap_ini}}
Rg gap 0 1e15
Cpar te be 1f
Bcell te be I = I0*exp(-V(gap)/g0)*sinh(min(max(V(te,be)/Vs, -50), 50))
Bkt  kt  0 V = kb*(T0 + min(abs(V(te,be)*I0*exp(-V(gap)/g0)*sinh(min(max(V(te,be)/Vs, -50), 50)))*Rth, 3000))
Bx   x   0 V = min(max((gamma0 - beta*pwr(max(V(gap),0),alpha))*a0*V(te,be)/(tox*max(V(kt),1e-3)), -200), 200)
Brt  rt  0 V = -vr0*exp(-Ea/max(V(kt),1e-3))*sinh(min(max(V(x),-200),200))*(V(x) < 0 ? Fr : 1)
Bw   w   0 V = V(rt) < 0 ? min(1, max(0, (V(gap)-gap_min)/wsoft)) : min(1, max(0, (gap_max-V(gap))/wsoft))
Bg   0 gap I = cstate*V(rt)*V(w)
.ends rr
"""


def g_read(gap_nm):
    return float(current(P, 0.2, gap_nm * 1e-9)) / 0.2


def gap_for(gs):
    """gap (nm) with read conductance gs (S)."""
    return P.g0 * 1e9 * math.log(P.I0 * math.sinh(0.2 / P.V0) / (0.2 * gs))


# ---------------------------------------------------------------- 0. subcircuit check
def check(v, gap0, F):
    deck = (f"* check\n{RRAM}\nV1 t 0 pwl(0 0 1n {v})\nX1 t 0 g rr gap_ini={gap0} Fr={F}\n.ic v(g)={gap0}\n"
            f".control\ntran 0.1n 1.001u 0 0.5n\nwrdata out.txt v(g)\n.endc\n.end\n")
    a, _ = S.run(deck)
    ref = step_gap(replace(P, v0=P.v0 * F), v, gap0 * 1e-9, 1e-6, GMIN, GMAX) * 1e9
    return dict(V=v, gap0_nm=gap0, F=F, ngspice_nm=round(float(a[-1, 1]), 4), python_nm=round(ref, 4))


# ---------------------------------------------------------------- the 2 x 2 macro
GRID = np.round(np.arange(0.10, 1.7001, 0.01), 4)          # gap of the target device, nm
KEYS = [f"r{r}c{c}{d}" for r in (0, 1) for c in (0, 1) for d in ("p", "n")]


def vcell_table(op, vwl, vprg, gaps, corner="tt", temp=27):
    """DC solution of the 2 x 2 macro with the word line of row 0 on, for every gap of the target device r0c0p on GRID
    (the other devices at their gaps in `gaps`). Returns {device: array of V(top) - V(bottom) over GRID}."""
    vdda = 3.3
    on, off = "vdda", "0"          # control nodes
    # bld: vprg bl sa prg prgb dn sen vdda vss ; sld: vprg sl prg prgb dn vdda vss
    def bld(name, mode):          # mode: 'prg' or 'dn'
        p = mode == "prg"
        return f"X{name} vprg {name} nc_{name} {on if p else off} {off if p else on} {off if p else on} 0 vdda 0 bld\nR{name}_nc nc_{name} 0 1e9"
    def sld(name, mode):
        p = mode == "prg"
        return f"X{name} vprg {name} {on if p else off} {off if p else on} {off if p else on} vdda 0 sld"
    if op == "set":                # tcim_actl PULSE_SET with only P of column 0 masked
        mb = {"blp0": "prg", "bln0": "dn", "blp1": "dn", "bln1": "dn"}; ms = {"sl0": "dn", "sl1": "dn"}
    else:                          # PULSE_RST with only P of column 0 masked
        mb = {"blp0": "dn", "bln0": "prg", "blp1": "prg", "bln1": "prg"}; ms = {"sl0": "prg", "sl1": "prg"}
    lines = [bld(n, m) for n, m in mb.items()] + [sld(n, m) for n, m in ms.items()]
    cells = []
    for r in (0, 1):
        for c in (0, 1):
            for d in ("p", "n"):
                k = f"r{r}c{c}{d}"
                gnode = "gt" if k == "r0c0p" else f"{gaps[k]:.6f}"
                cells.append(f"Rb{k} bl{d}{c} te{k} {RBL}\n"
                             f"B{k} te{k} be{k} I = {P.I0}*exp(-{'V(gt)' if k == 'r0c0p' else gnode}/{P.g0 * 1e9:.6g})*sinh(V(te{k},be{k})/{P.V0})\n"
                             f"Xt{k} be{k} wl{r} s{k} 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5\nRs{k} s{k} sl{c} {RSL}")
    deck = f"""* macro DC
{S.lib(corner)}.temp {temp}
{CELLS}
Vda vdda 0 {vdda}
Vp vprg 0 {vprg}
Vwp wlpad 0 {vwl}
Vgt gt 0 1.0
Xrm wlpad vwl vdda 0 vdda 0 tg wn=8 wp=16
Xw0 vwl wl0 vdda 0 vdda 0 wld
Xw1 vwl wl1 0 vdda vdda 0 wld
{chr(10).join(lines)}
{chr(10).join(cells)}
.control
dc Vgt {GRID[0]} {GRID[-1]} 0.01
wrdata out.txt {' '.join(f'v(te{k},be{k})' for k in KEYS)}
.endc
.end
"""
    a, log = S.run(deck)
    if len(a) != len(GRID) or abs(a[-1, 0] - GRID[-1]) > 1e-6:
        raise RuntimeError("DC sweep incomplete:\n" + log[-1500:])
    return {k: a[:, 2 * i + 1] for i, k in enumerate(KEYS)}


def rate(v, g_m, F):
    """dg/dt (m/s) of the reference equations; the reset direction (v < 0) is F times faster."""
    return float(gap_rate(P if v >= 0 else replace(P, v0=P.v0 * F), v, g_m))


def pulse(op, vwl, vprg, gaps, F, corner="tt", temp=27, t_pulse=1e-6, table=None):
    """One pulse of `op` on device P of column 0, row 0, quasi-static: the circuit settles in nanoseconds (word line
    ~1 ns, periph_sim part B), the gap moves over the microsecond, so the cell voltages are taken from the DC solution
    at the present gap of the target device and every gap is advanced with the reference equations
    (model/reram_stanford.gap_rate, self-heating included), at most 2 pm per step. Returns (gaps after, mean target V)."""
    tab = table or vcell_table(op, vwl, vprg, gaps, corner, temp)
    g = {k: gaps[k] * 1e-9 for k in KEYS}
    t, vsum = 0.0, 0.0
    while t < t_pulse:
        gt = min(max(g["r0c0p"] * 1e9, GRID[0]), GRID[-1])
        v = {k: float(np.interp(gt, GRID, tab[k])) for k in KEYS}
        r = {k: rate(v[k], g[k], F) for k in KEYS}
        rmax = max(abs(x) for x in r.values())
        h = t_pulse - t if rmax == 0 else min(t_pulse - t, 2e-12 / rmax)
        for k in KEYS:
            g[k] = min(max(g[k] + r[k] * h, GMIN), GMAX)
        vsum += v["r0c0p"] * h; t += h
    return {k: g[k] * 1e9 for k in KEYS}, vsum / t_pulse


def pulse_tran(op, vwl, vprg, gaps, F, corner="tt", temp=27):
    """The same pulse as a full ngspice transient (word line switched at 20 ns for 1 us, the gaps as circuit states
    of the subcircuit RRAM). Used only to cross-check the quasi-static method; ngspice does not always converge on the
    abrupt set (returns None then)."""
    vdda = 3.3
    on, off = "vdda", "0"
    def bld(name, mode):
        p_ = mode == "prg"
        return f"X{name} vprg {name} nc_{name} {on if p_ else off} {off if p_ else on} {off if p_ else on} 0 vdda 0 bld\nR{name}_nc nc_{name} 0 1e9"
    def sld(name, mode):
        p_ = mode == "prg"
        return f"X{name} vprg {name} {on if p_ else off} {off if p_ else on} {off if p_ else on} vdda 0 sld"
    if op == "set":
        mb = {"blp0": "prg", "bln0": "dn", "blp1": "dn", "bln1": "dn"}; ms = {"sl0": "dn", "sl1": "dn"}
    else:
        mb = {"blp0": "dn", "bln0": "prg", "blp1": "prg", "bln1": "prg"}; ms = {"sl0": "prg", "sl1": "prg"}
    lines = [bld(n, m) for n, m in mb.items()] + [sld(n, m) for n, m in ms.items()]
    cells = []
    for k in KEYS:
        r, c, d = int(k[1]), int(k[3]), k[4]
        cells.append(f"Rb{k} bl{d}{c} te{k} {RBL}\nX{k} te{k} be{k} g{k} rr gap_ini={gaps[k]:.6f} Fr={F}\n"
                     f"Xt{k} be{k} wl{r}f s{k} 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5\nRs{k} s{k} sl{c} {RSL}")
    deck = f"""* macro pulse, transient
{S.lib(corner)}.temp {temp}
{CELLS}
{RRAM}
Vda vdda 0 {vdda}
Vp vprg 0 {vprg}
Vwp wlpad 0 {vwl}
Xrm wlpad vwl vdda 0 vdda 0 tg wn=8 wp=16
Vs0 sel0 0 pwl(0 0 20n 0 20.2n {vdda} 1020n {vdda} 1020.2n 0)
Vb0 selb0 0 pwl(0 {vdda} 20n {vdda} 20.2n 0 1020n 0 1020.2n {vdda})
Xw0 vwl wl0 sel0 selb0 vdda 0 wld
Xw1 vwl wl1 0 vdda vdda 0 wld
Rw0 wl0 wl0f 4200
Cw0 wl0f 0 100f
Rw1 wl1 wl1f 4200
Cw1 wl1f 0 100f
{chr(10).join(lines)}
{chr(10).join(cells)}
.ic {' '.join(f'v(g{k})={gaps[k]:.6f}' for k in KEYS)}
.options method=gear reltol=1e-3 itl4=200
.control
tran 2n 1200n
wrdata out.txt {' '.join(f'v(g{k})' for k in KEYS)}
.endc
.end
"""
    try:
        a, log = S.run(deck)
    except RuntimeError:
        return None
    if a[-1, 0] < 1.19e-6:
        return None
    return {k: float(a[-1, 2 * i + 1]) for i, k in enumerate(KEYS)}


def method_check(op, vwl, vprg, F):
    gaps = {k: gap_for(4.5e-6) for k in KEYS}
    if op == "reset":
        gaps["r0c0p"] = gap_for(60e-6)
    q, _ = pulse(op, vwl, vprg, gaps, F)
    t = pulse_tran(op, vwl, vprg, gaps, F)
    return dict(op=op, VWLP=vwl, VPRG=vprg, quasi_static_uS=round(g_read(q["r0c0p"]) * 1e6, 3),
                transient_uS=None if t is None else round(g_read(t["r0c0p"]) * 1e6, 3))


def ladder_set(vwl, F, corner="tt", temp=27):
    gaps = {f"r{r}c{c}{d}": gap_for(4.5e-6) for r in (0, 1) for c in (0, 1) for d in ("p", "n")}
    g0 = dict(gaps)
    steps = []
    for k in range(20):
        vprg = round(1.4 + 0.1 * k, 2)
        gaps, vcell = pulse("set", vwl, vprg, gaps, F, corner, temp)
        g = g_read(gaps["r0c0p"])
        steps.append(dict(VPRG=vprg, cell_V=round(vcell, 3), G_uS=round(g * 1e6, 2)))
        if g >= SET_TARGET:
            break
    dist = max(abs(g_read(gaps[k]) - g_read(g0[k])) for k in gaps if k != "r0c0p") * 1e6
    return dict(op="set", VWLP=vwl, corner=corner, temp=temp, pulses=len(steps), reached=g_read(gaps["r0c0p"]) >= SET_TARGET,
                final_uS=round(g_read(gaps["r0c0p"]) * 1e6, 2), max_disturb_uS=round(dist, 4), steps=steps)


def ladder_reset(slow, corner="tt", temp=27, g_start=60e-6):
    """A cell `slow` decades slower to reset than the fitted F (spread k = 1: F resets 90.83 % of the cells in one
    SkyWater pulse; the 10-90 % spread of the cells' critical F is about 2.2 decades, fit_skywater.json)."""
    F = 10 ** (LOGF[1.0] - slow)
    gaps = {f"r{r}c{c}{d}": gap_for(4.5e-6) for r in (0, 1) for c in (0, 1) for d in ("p", "n")}
    gaps["r0c0p"] = gap_for(g_start)
    for k in ("r1c0p", "r1c1n", "r0c1p"):          # a few of the other devices in the set state as well
        gaps[k] = gap_for(g_start)
    g0 = dict(gaps)
    seq = [(round(2.5 + 0.1 * i, 2), 2.4) for i in range(6)] + [(3.0, round(2.5 + 0.1 * i, 2)) for i in range(6)]
    steps = []
    for vwl, vprg in seq:
        gaps, vcell = pulse("reset", vwl, vprg, gaps, F, corner, temp)
        g = g_read(gaps["r0c0p"])
        steps.append(dict(VWLP=vwl, VPRG=vprg, cell_V=round(vcell, 3), G_uS=round(g * 1e6, 2)))
        if g <= RESET_TARGET:
            break
    dist = max(abs(g_read(gaps[k]) - g_read(g0[k])) for k in gaps if k != "r0c0p") * 1e6
    return dict(op="reset", slower_decades=slow, log10F=round(math.log10(F), 3), corner=corner, temp=temp, pulses=len(steps),
                reached=g_read(gaps["r0c0p"]) <= RESET_TARGET, final_uS=round(g_read(gaps["r0c0p"]) * 1e6, 2),
                max_disturb_uS=round(dist, 4), steps=steps)


def _job(a):
    kind, args = a
    return {"check": check, "set": ladder_set, "reset": ladder_reset, "method": method_check}[kind](*args)


if __name__ == "__main__":
    jobs = [("check", (v, g, F)) for v, g, F in ((1.0, 1.7, 1.0), (1.5, 1.7, 1.0), (-1.0, 0.3, 1e7), (-0.8, 0.3, 10 ** 7.375))]
    jobs += [("method", (op, w, v, 10 ** LOGF[1.0])) for op, w, v in (("set", 1.7, 2.4), ("set", 1.7, 3.3), ("set", 2.5, 2.4),
                                                                       ("set", 2.5, 3.3), ("reset", 2.5, 2.6), ("reset", 3.0, 3.0))]
    if os.environ.get("LADDERS_ONLY"):                # worst-case reruns: the ladders only
        jobs = []
    jobs += [("set", (vwl, 10 ** LOGF[1.0], c, T)) for vwl in (1.7, 2.0, 2.5) for c, T in (("tt", 27), ("ss", -40), ("ff", 125))]
    jobs += [("reset", (sl, c, T)) for sl in (0, 1, 2, 3, 4) for c, T in (("tt", 27), ("ss", -40), ("ff", 125))]
    with Pool(int(os.environ.get("JOBS", "2"))) as pool:
        res = pool.map(_job, jobs)
    out = dict(model="Stanford-PKU at SkyWater sky130_fd_pr_reram v2.0.3 parameters, reset rate x F (fit_skywater.json, W 1 um, 6/20)",
               set_target_uS=SET_TARGET * 1e6, reset_target_uS=RESET_TARGET * 1e6, R_bitline_ohm=RBL, R_sourceline_ohm=RSL,
               check=[r for (k, _), r in zip(jobs, res) if k == "check"],
               method_check=[r for (k, _), r in zip(jobs, res) if k == "method"],
               set=[r for (k, _), r in zip(jobs, res) if k == "set"],
               reset=[r for (k, _), r in zip(jobs, res) if k == "reset"])
    for r in out["check"] + out["method_check"]:
        print("check", r)
    for r in out["set"] + out["reset"]:
        print({k: v for k, v in r.items() if k != "steps"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
