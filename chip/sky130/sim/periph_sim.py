"""Schematic-level simulation of the SKY130 periphery cells of chip/sky130/sim/periph.spice (11 October 2026).

A. Level shifter 1.8 -> 3.3 V: delays of both edges, static current; 5 corners x -40/27/125 C x supplies -10/+10 %.
B. Word-line driver into one word line of the drawn array (poly 0.5 um wide, 86.4 um long = 172.8 squares at
   48.2 ohm/sq; the 48 select gates W 1.0 / L 0.5 um as real transistors, in 12 RC sections): far end to 90 % of the
   rail, rail 1.4 / 1.7 / 2.5 / 3.0 / 3.3 V.
C. Program path of one device: rail VPRG -> bit-line (set) or source-line (reset) driver -> the cell as a conductance
   -> select transistor (W 1.0 / L 0.5 um) -> the other driver to ground. Voltage that reaches the cell, at the
   conductance extremes 4.5 and 120 uS and SkyWater's levels (set: WL 1.7 V, VPRG 2.4 V; reset: WL 2.5-3.0 V,
   VPRG 2.6-3.0 V; form: WL 2.5 V, VPRG 3.3 V); and the inhibited device of a reset (bit line at VPRG).
D. Sense amplifier with the reference bias and the column switch: trip conductance for the three reference ratios
   (reset target, read, set target) over corners, temperatures and supplies; local mismatch Monte Carlo (200 runs,
   typical corner); read time for 30 / 4.5 uS cells.
E. Revision 2 controls: one bit-line slice (level shifter, ground NOR, driver, sense amplifier) and one source-line
   driver with the shared controls (ctrlglob), driven by the controller's sequence at 16 MHz (BRK, MAKE, SETL ...,
   REL, BRK2, GND) for a set pulse on the bit line, a reset (bit line grounded, source line at VPRG) and a read; the
   cell is a conductance to the source line through an on select transistor. Reports the bit-line and source-line
   levels in each phase, the current and the charge drawn from VPRG in the 20 ns after each control edge (line charging
   plus any shoot-through); for the charge, also without the cell (no steady current) with and without flt
   (break-before-make removed) for comparison.
Writes results/sky130_chip/periph_sim.json."""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "sky130_chip" / "periph_sim.json"
CELLS = (HERE / "periph.spice").read_text()
IUNIT = 0.8e-6                       # reference unit (A); ratios 2 / 3 / 6
RATIO = dict(reset=2, read=3, set=6)
VREF = 0.2


def hdr(corner, temp, mm=False):
    return f"* deck\n{S.lib(corner, mm)}.temp {temp}\n{CELLS}\n"


# ---------------------------------------------------------------- A
def part_a(corner, temp, vccd, vdda):
    deck = hdr(corner, temp) + f"""Vcc vccd 0 {vccd}
Vda vdda 0 {vdda}
Vin in 0 pwl(0 0 20n 0 20.2n {vccd} 70n {vccd} 70.2n 0 120n 0)
X1 in out outb vccd vdda 0 ls_lv2hv
Cl out 0 20f
Cb outb 0 20f
.control
tran 0.02n 120n
wrdata out.txt v(in) v(out) i(Vda)
.endc
.end
"""
    a, _ = S.run(deck)
    t, vin, vo, ida = a[:, 0], a[:, 1], a[:, 3], a[:, 5]
    r = S.cross(t, vo, vdda / 2, True, 20e-9)
    f = S.cross(t, vo, vdda / 2, False, 70e-9)
    stat = max(abs(np.mean(ida[(t > 50e-9) & (t < 69e-9)])), abs(np.mean(ida[(t > 100e-9)])))
    return dict(rise_ns=None if r is None else round((r - 20.1e-9) * 1e9, 3), fall_ns=None if f is None else round((f - 70.1e-9) * 1e9, 3),
                static_nA=round(stat * 1e9, 3))


# ---------------------------------------------------------------- B
def part_b(corner, temp, vwl, vdda=3.3):
    n = 12
    rseg = 172.8 * 48.2 / n
    lines = []
    for k in range(n):
        lines.append(f"R{k} w{k} w{k + 1} {rseg:.4g}")
        for j in range(4):   # 48 gates over 12 sections
            lines.append(f"Xg{k}_{j} 0 w{k + 1} 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5")
    deck = hdr(corner, temp) + f"""Vda vdda 0 {vdda}
Vwl vwl 0 {vwl}
Vs sel 0 pwl(0 0 10n 0 10.2n {vdda} 60n {vdda} 60.2n 0 120n 0)
Vsb selb 0 pwl(0 {vdda} 10n {vdda} 10.2n 0 60n 0 60.2n {vdda} 120n {vdda})
X1 vwl w0 sel selb vdda 0 wld
{chr(10).join(lines)}
.control
tran 0.02n 120n
wrdata out.txt v(w0) v(w{n})
.endc
.end
"""
    a, _ = S.run(deck)
    t, far = a[:, 0], a[:, 3]
    r = S.cross(t, far, 0.9 * vwl, True, 10e-9)
    f = S.cross(t, far, 0.1 * vwl, False, 60e-9)
    return dict(far_rise_90_ns=None if r is None else round((r - 10.1e-9) * 1e9, 3),
                far_fall_10_ns=None if f is None else round((f - 60.1e-9) * 1e9, 3),
                far_final_V=round(float(far[np.argmin(abs(t - 59e-9))]), 4))


# ---------------------------------------------------------------- C
def part_c(corner, temp, mode, vwl, vprg, g):
    vdda = 3.3
    # cell = conductance g between the select transistor's drain (node d) and the bit line (node bl)
    if mode in ("set", "form"):
        drv = f"""Xb vprg bl nc_sa vdda 0 0 0 vdda 0 bld
Xs vprg sl 0 vdda vdda vdda 0 sld"""          # bit line to the rail, source line to ground
    elif mode == "reset":
        drv = f"""Xb vprg bl nc_sa 0 vdda vdda 0 vdda 0 bld
Xs vprg sl vdda 0 0 vdda 0 sld"""             # bit line to ground, source line to the rail
    else:                                      # inhibited device in a reset: bit line and source line at the rail
        drv = f"""Xb vprg bl nc_sa vdda 0 0 0 vdda 0 bld
Xs vprg sl vdda 0 0 vdda 0 sld"""
    deck = hdr(corner, temp) + f"""Vda vdda 0 {vdda}
Vp vprg 0 {vprg}
Vw wl 0 {vwl}
{drv}
Rbl bl blc 75
Rc blc d {1 / g:.6g}
Xt d wl slc 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
Rsl slc sl 40
Rsa nc_sa 0 1e9
.control
op
wrdata out.txt v(blc) v(d) v(bl) v(sl) i(Vp)
.endc
.end
"""
    a, _ = S.run(deck)
    vblc, vd, vbl, vsl, ip = a[0, 1], a[0, 3], a[0, 5], a[0, 7], a[0, 9]
    return dict(cell_V=round(float(vblc - vd), 4), cell_uA=round(float(abs(g * (vblc - vd))) * 1e6, 2),
                bl_V=round(float(vbl), 4), sl_V=round(float(vsl), 4), rail_mA=round(float(abs(ip)) * 1e3, 4))


# ---------------------------------------------------------------- D
def sa_deck(corner, temp, vccd, op, mm=False, analysis="dc"):
    r = dict(r0=0, r1=0, r2=0)
    r[{"reset": "r0", "read": "r1", "set": "r2"}[op]] = vccd
    deck = hdr(corner, temp, mm) + f"""Vcc vccd 0 {vccd}
Vda vdda 0 3.3
Vref vref 0 {VREF}
Iib vccd ib {IUNIT}
Vr0 r0 0 {r['r0']}
Vr1 r1 0 {r['r1']}
Vr2 r2 0 {r['r2']}
Xrb ib r0 r1 r2 vref vbp vcl vccd 0 refbias
Xsa sa out vbp vcl vccd 0 sa
Xcs bl vdda sa 0 sky130_fd_pr__nfet_g5v0d10v5 w=2 l=0.5
* the selected cell: conductance in series with its select transistor (word line at the read level 3.3 V);
* the 71 unselected cells of the column lumped as one 71 um transistor (word line 0) on 71 x 120 uS
Bc bl d i=v(gc)*v(bl,d)
Xt d wlr 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
Vwr wlr 0 3.3
Ru bl du {1 / (120e-6 * 71):.4g}
Xu du 0 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=71 l=0.5
"""
    return deck


def part_d_trip(corner, temp, vccd, op, mm=False, seed=None):
    deck = sa_deck(corner, temp, vccd, op, mm) + """Vgc gc 0 10e-6
.control
dc Vgc 1e-6 60e-6 0.05e-6
wrdata out.txt v(out) v(bl)
.endc
.end
"""
    a, _ = S.run(deck, seed=seed)
    g, out = a[:, 0], a[:, 1]
    k = np.nonzero(out > vccd / 2)[0]
    if len(k) == 0 or k[0] == 0:
        return None
    j = k[0]
    gt = g[j - 1] + (vccd / 2 - out[j - 1]) / (out[j] - out[j - 1]) * (g[j] - g[j - 1])
    return round(float(gt) * 1e6, 3)


def part_d_tran(corner, temp, op, gcell):
    vccd = 1.8
    deck = sa_deck(corner, temp, vccd, op).replace("Xcs bl vdda sa 0", "Xcs bl csg sa 0") + f"""Vgc gc 0 {gcell}
Vcs csg 0 pwl(0 0 20n 0 20.2n 3.3 400n 3.3)
Cbl bl 0 60f
.ic v(bl)=0
.control
tran 0.05n 400n
wrdata out.txt v(out)
.endc
.end
"""
    a, _ = S.run(deck)
    t, out = a[:, 0], a[:, 1]
    final = out[-1] > vccd / 2
    wrong = np.nonzero((out > vccd / 2) != final)[0]
    ts = (t[wrong[-1] + 1] if len(wrong) else t[0]) - 20.1e-9
    return dict(G_uS=gcell * 1e6, reads=int(final), settle_ns=round(max(ts, 0) * 1e9, 2))


def part_e(corner, temp, op, use_flt=True, vccd=1.8, vprg=2.4, g=30e-6):
    T = 62.5e-9                                    # 16 MHz controller clock
    # controller outputs per cycle (revision 2): (flt, prg, sen, slprg); cycles: IDLE, BRK, MAKE, SETL x4, WLON x8,
    # WLOFF, REL, BRK2, GND, IDLE x2
    mode = dict(set=(1, 0, 0), reset=(0, 0, 1), read=(0, 1, 0))[op]
    seq = [(0, 0, 0, 0), (1, 0, 0, 0)] + [(1, *mode)] + [(0, *mode)] * 13 + [(1, *mode), (1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]
    if not use_flt:
        seq = [(0, *x[1:]) for x in seq]
    def pwl(idx):
        pts = []
        for k, v in enumerate(seq):
            t0 = k * T + 2e-9
            pts += [f"{t0:.4g} {vccd * (seq[k - 1][idx] if k else 0)}", f"{t0 + 0.2e-9:.4g} {vccd * v[idx]}"]
        return "pwl(0 0 " + " ".join(pts) + ")"
    tend = len(seq) * T
    deck = hdr(corner, temp) + f"""Vcc vccd 0 {vccd}
Vda vdda 0 3.3
Vp vprg 0 {vprg}
Vref vref 0 {VREF}
Iib vccd ib {IUNIT}
Vflt flt_lv 0 {pwl(0)}
Vprg prg_lv 0 {pwl(1)}
Vsen sen_lv 0 {pwl(2)}
Vslp slprg_lv 0 {pwl(3)}
Vr1 r1 0 {vccd if op == 'read' else 0}
Xg sen_lv flt_lv slprg_lv 0 0 r1 0 ib vref 0 0 sen flt slprg slprgb sldn vwl vbp vcl vccd vdda 0 ctrlglob
Xb prg_lv bl out vprg sen flt vbp vcl vccd vdda 0 blslice
Xs vprg sl slprg slprgb sldn vdda 0 sld
Cbl bl 0 100f
Csl sl 0 100f
Rc bl d {1 / g:.6g}
Xt d vdda sl 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
.control
tran 0.1n {tend:.4g} 0 0.2n
wrdata out.txt v(bl) v(sl) i(Vp) v(out)
.endc
.end
"""
    a, _ = S.run(deck)
    t, bl, sl, ip, out = a[:, 0], a[:, 1], a[:, 3], -a[:, 5], a[:, 7]
    def at(cyc):                                   # value near the end of cycle cyc
        return int(np.argmin(abs(t - (cyc + 0.9) * T)))
    k_on = at(11)                                  # middle of WLON
    sw = np.zeros_like(t, bool)                    # windows of 20 ns after every control edge
    for k in range(1, len(seq)):
        if seq[k] != seq[k - 1]:
            sw |= (t > k * T + 2e-9) & (t < k * T + 22e-9)
    steady = float(abs(ip[k_on]))
    return dict(op=op, flt=use_flt, bl_on_V=round(float(bl[k_on]), 4), sl_on_V=round(float(sl[k_on]), 4),
                bl_end_V=round(float(bl[-1]), 4), sl_end_V=round(float(sl[-1]), 4), out_on=int(out[k_on] > vccd / 2),
                steady_uA=round(steady * 1e6, 2), peak_switch_uA=round(float(np.max(abs(ip[sw]))) * 1e6, 2),
                switch_charge_fC=round(float(np.trapezoid(np.where(sw, ip, 0.0), t)) * 1e15, 1))


FUNCS = {"A": part_a, "B": part_b, "C": part_c, "Dt": part_d_trip, "Dx": part_d_tran, "E": part_e}


def _job(args):
    kind, a = args
    return FUNCS[kind](*a)


def _full(args):
    """The same job with the full corner section of sky130.lib.spice (about two minutes per run)."""
    S.FULL = True
    try:
        return _job(args)
    finally:
        S.FULL = False


def only_e():
    """python3 periph_sim.py E : run part E alone and merge it into the existing periph_sim.json."""
    jobs = []
    for c, T in (("tt", 27), ("ss", -40), ("ff", 125), ("sf", -40), ("fs", 125)):
        for op in ("set", "reset", "read"):
            jobs.append((("E", (c, T, op)), f"{op} {c} {T}C"))
    for op in ("set", "reset"):
        jobs.append((("E", ("tt", 27, op, True, 1.8, 2.4, 1e-12)), f"{op} tt 27C no cell"))
        jobs.append((("E", ("tt", 27, op, False, 1.8, 2.4, 1e-12)), f"{op} tt 27C no cell, without flt"))
    with Pool(int(os.environ.get("JOBS", os.cpu_count() or 1))) as pool:
        out = pool.map(_job, [j for j, _ in jobs])
    res = json.loads(OUT.read_text())
    res["E"] = {k: r for (_, k), r in zip(jobs, out)}
    OUT.write_text(json.dumps(res, indent=1))
    for k, r in res["E"].items():
        print("E", k, r, flush=True)


if __name__ == "__main__" and sys.argv[1:] == ["E"]:
    only_e()
elif __name__ == "__main__":
    res = dict(cells="chip/sky130/sim/periph.spice", iunit_uA=IUNIT * 1e6, ratios=RATIO, vref_V=VREF, A={}, B={}, C={}, D={}, E={})
    jobs = []
    for c in S.CORNERS:
        for T in S.TEMPS:
            for vccd, vdda in ((1.62, 3.0), (1.8, 3.3), (1.98, 3.6)):
                jobs.append(("A", (c, T, vccd, vdda), ("A", f"{c} {T}C {vccd}/{vdda}V")))
            for vwl in (1.4, 1.7, 2.5, 3.0, 3.3):
                jobs.append(("B", (c, T, vwl), ("B", f"{c} {T}C vwl {vwl}V")))
            for vccd in (1.62, 1.8, 1.98):
                for op in RATIO:
                    jobs.append(("Dt", (c, T, vccd, op), ("D", f"trip {op} {c} {T}C {vccd}V")))
    for c in S.CORNERS:
        for T in S.TEMPS:
            for mode, vwl, vprg in (("set", 1.7, 2.4), ("reset", 2.5, 2.6), ("reset", 3.0, 3.0), ("form", 2.5, 3.3), ("inhibit", 3.0, 3.0)):
                for g in (4.5e-6, 120e-6):
                    jobs.append(("C", (c, T, mode, vwl, vprg, g), ("C", f"{mode} wl {vwl} prg {vprg} G {g * 1e6:g}uS {c} {T}C")))
    for c, T in (("tt", 27), ("ss", 125), ("ff", -40), ("ss", -40), ("ff", 125)):
        for op, gs in (("read", (30e-6, 4.5e-6)), ("set", (30e-6, 20e-6)), ("reset", (4.5e-6, 10e-6))):
            for g in gs:
                jobs.append(("Dx", (c, T, op, g), ("D", f"tran {op} G {g * 1e6:g}uS {c} {T}C")))
    res["E"] = {}
    for c, T in (("tt", 27), ("ss", -40), ("ff", 125), ("sf", -40), ("fs", 125)):
        for op in ("set", "reset", "read"):
            jobs.append(("E", (c, T, op), ("E", f"{op} {c} {T}C")))
    for op in ("set", "reset"):                     # switching charge with no cell current: with and without flt
        jobs.append(("E", ("tt", 27, op, True, 1.8, 2.4, 1e-12), ("E", f"{op} tt 27C no cell")))
        jobs.append(("E", ("tt", 27, op, False, 1.8, 2.4, 1e-12), ("E", f"{op} tt 27C no cell, without flt")))
    pool = Pool(int(os.environ.get("JOBS", os.cpu_count() or 1)))
    for (kind, a, (sec, key)), r in zip(jobs, pool.imap(_job, [(j[0], j[1]) for j in jobs])):
        res[sec][key] = r
        print(sec, key, r, flush=True)
    # mismatch Monte Carlo of the trip, typical corner 27 C 1.8 V, all three ratios
    for op in RATIO:
        mc = [x for x in pool.starmap(part_d_trip, [("tt", 27, 1.8, op, True, s) for s in range(1, 201)]) if x is not None]
        res["D"][f"mc {op}"] = dict(runs=200, valid=len(mc), mean_uS=round(float(np.mean(mc)), 3), sigma_uS=round(float(np.std(mc)), 3),
                                    min_uS=round(float(np.min(mc)), 3), max_uS=round(float(np.max(mc)), 3))
        print("D mc", op, res["D"][f"mc {op}"], flush=True)
    # the reduced library (spice.py) against the full one: one job of each kind, other corners, and a mismatch run
    chk = [("A", ("ss", 125, 1.62, 3.0)), ("B", ("ff", -40, 3.3)), ("C", ("sf", 27, "reset", 3.0, 3.0, 120e-6)),
           ("Dt", ("fs", 125, 1.98, "set")), ("Dx", ("ss", 125, "read", 4.5e-6)), ("Dt", ("tt", 27, 1.8, "read", True, 7))]
    full = pool.map(_full, chk)
    red = pool.map(_job, chk)
    res["libcheck"] = dict(jobs=[f"{k} {a}" for k, a in chk], full=full, reduced=red, identical=full == red)
    print("libcheck identical:", full == red, flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
