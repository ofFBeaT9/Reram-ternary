"""SKY130 read path for the digital (reference-compare) mode, in ngspice with SkyWater's transistor models (9 October 2026).

Same topology as the IHP read path (circuits/gnucap/sense.py), re-sized for SkyWater's ReRAM:
  VDD 1.8 V -- PMOS mirror (Iref) --> node sn --> clamp NMOS --> blsa --> column switch (nfet_g5v0d10v5, gate 3.3 V) --> BL
  The clamp gate comes from a replica diode NMOS standing on Vref = 0.2 V and carrying Iref, so BL sits near 0.2 V.
  Cell conductance > Iref / 0.2 V pulls sn low (out = 1).
Why a new threshold: SkyWater's cells are at 30-120 uS after set and about 4.5 uS after reset (sky130_fd_pr_reram
technology specifications), against about 25 uA / 0.2 V = 125 uS for TCIM0 on IHP (sections 18.5, 23.6). The threshold is placed
near the geometric mean of 4.5 and 30 uS: Iref = 2.4 uA, 12 uS at 0.2 V.
Cell: a conductance G in series with its select transistor (nfet_g5v0d10v5, W 1.0 um, L 0.5 um, word line 1.8 V).
The 71 unselected cells of the column are one select transistor of W 71 um with its word line at 0 V, standing on
the largest conductance (120 uS x 71) to the grounded source line: worst-case leakage.
Ideal sources for Vref and Iref (as in the IHP first cut); transistor sizes are first choices.
Runs:
  A. DC trip conductance: corners tt ss ff sf fs, -40 / 27 / 125 C, VDD 1.62 / 1.80 / 1.98 V
  B. Local mismatch Monte Carlo (SkyWater mismatch models, mc_mm_switch=1), tt 27 C, 200 runs
  C. Transient: word line rises at 1 ns, BL capacitance 30 fF; time until the output settles, for G = 30 uS and
     4.5 uS, at tt/ss/ff 27 C and ss 125 C
Environment: SKY130_NGSPICE_LIB = open_pdks sky130B libs.tech/ngspice/sky130.lib.spice (used for every run when set; needed for B),
or SKY130_FD_PR = a checkout of google/skywater-pdk-libs-sky130_fd_pr (A and C only). Writes results/sky130_read.json.
"""
import json, os, subprocess, sys, tempfile
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FDPR = Path(os.environ["SKY130_FD_PR"])
DEVICES = ("nfet_01v8", "pfet_01v8", "nfet_g5v0d10v5")


OPDK = os.environ.get("SKY130_NGSPICE_LIB")     # open_pdks sky130B libs.tech/ngspice/sky130.lib.spice (with mismatch)


def lib(corner, mm=0):
    if OPDK:                                     # open_pdks: W/L in um, mismatch through the <corner>_mm sections
        return f'.lib "{OPDK}" {corner}{"_mm" if mm else ""}\n'
    return _lib_raw(corner)


def _lib_raw(corner):
    inc = [FDPR / "models/parameters/invariant.spice", FDPR / f"models/corners/{corner}/nonfet.spice"]
    for d in DEVICES:
        inc += [FDPR / f"cells/{d}/sky130_fd_pr__{d}__mismatch.corner.spice", FDPR / f"cells/{d}/sky130_fd_pr__{d}__{corner}.corner.spice"]
    return "".join(f'.include "{p}"\n' for p in inc)
IREF, VREF = 2.4e-6, 0.2
G_LRS_MIN, G_HRS_TYP = 30e-6, 4.5e-6
S = dict(wp=1.0, lp=4.0, wn=2.0, ln=1.0, wmux=2.0, lmux=0.5, wsel=1.0, lsel=0.5)


def circuit(vdd=1.8, temp=27, s=S, mm=0, seed=1):
    return f"""* SKY130 ReRAM read path
{'' if OPDK else '.option scale=1e-6' + chr(10) + f'.param mc_mm_switch={mm} mc_pr_switch=0'}
CORNER
.temp {temp}
Vdd vdd 0 {vdd}
Vref vr 0 {VREF}
Vmux vmux 0 3.3
Vwlu wlu 0 0
Iref1 mirr 0 {IREF}
Iref2 vdd vclamp {IREF}
Xp1 mirr mirr vdd vdd sky130_fd_pr__pfet_01v8 w={s['wp']} l={s['lp']}
Xp2 sn mirr vdd vdd sky130_fd_pr__pfet_01v8 w={s['wp']} l={s['lp']}
Xnr vclamp vclamp vr 0 sky130_fd_pr__nfet_01v8 w={s['wn']} l={s['ln']}
Xn1 sn vclamp blsa 0 sky130_fd_pr__nfet_01v8 w={s['wn']} l={s['ln']}
Xmx blsa vmux bl 0 sky130_fd_pr__nfet_g5v0d10v5 w={s['wmux']} l={s['lmux']}
Xpi out sn vdd vdd sky130_fd_pr__pfet_01v8 w=1 l=0.15
Xni out sn 0 0 sky130_fd_pr__nfet_01v8 w=0.5 l=0.15
* selected cell: conductance G (node gc carries G in siemens as a voltage) in series with the select transistor
Bcell bl x I=V(gc)*V(bl,x)
Xsel x wl 0 0 sky130_fd_pr__nfet_g5v0d10v5 w={s['wsel']} l={s['lsel']}
* unselected cells, lumped
Rleak bl xu {1 / (120e-6 * 71):.4g}
Xun xu wlu 0 0 sky130_fd_pr__nfet_g5v0d10v5 w={71 * s['wsel']} l={s['lsel']}
"""


def run(deck, seed=None):
    with tempfile.TemporaryDirectory() as d:
        Path(d, ".spiceinit").write_text("set ngbehavior=hsa\nset num_threads=1\n" + (f"set rndseed={seed}\n" if seed else ""))
        Path(d, "t.cir").write_text(deck)
        r = subprocess.run(["ngspice", "-b", "t.cir"], cwd=d, capture_output=True, text=True, timeout=900)
        f = Path(d, "out.txt")
        if not f.exists():
            raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
        return np.loadtxt(f)


def dc_trip(corner="tt", vdd=1.8, temp=27, mm=0, seed=1):
    deck = circuit(vdd, temp, mm=mm).replace("CORNER", lib(corner, mm)) + f"""Vgc gc 0 10e-6
Vwl wl 0 1.8
.control
dc Vgc 2e-6 40e-6 0.1e-6
wrdata out.txt v(out) v(bl) v(sn)
.endc
.end
"""
    a = run(deck, seed if mm else None)
    g, out, bl = a[:, 0], a[:, 1], a[:, 3]
    k = np.nonzero(out > vdd / 2)[0]
    if len(k) == 0 or k[0] == 0:
        return dict(trip_uS=None)
    j = k[0]
    gt = g[j - 1] + (vdd / 2 - out[j - 1]) / (out[j] - out[j - 1]) * (g[j] - g[j - 1])
    vbl = lambda gx: float(np.interp(gx, g, bl))
    return dict(trip_uS=round(gt * 1e6, 3), vbl_at_30uS_mV=round(vbl(30e-6) * 1e3, 1), vbl_at_4p5uS_mV=round(vbl(4.5e-6) * 1e3, 1))


def tran(corner="tt", temp=27, G=30e-6, vdd=1.8):
    deck = circuit(vdd, temp).replace("CORNER", lib(corner)) + f"""Vgc gc 0 {G}
Vwl wl 0 pwl(0 0 1n 0 1.2n 1.8 400n 1.8)
Cbl bl 0 30f
.control
tran 0.05n 400n
wrdata out.txt v(out) v(bl) v(wl)
.endc
.end
"""
    a = run(deck)
    t, out = a[:, 0], a[:, 1]
    final = out[-1]
    hi = final > vdd / 2
    # settle time: last time the output was on the wrong side of VDD/2, measured from the word-line edge at 1 ns
    wrong = np.nonzero((out > vdd / 2) != hi)[0]
    t_settle = (t[wrong[-1] + 1] if len(wrong) else t[0]) - 1e-9
    return dict(G_uS=G * 1e6, out_final_V=round(float(final), 3), reads_as=int(hi), settle_ns=round(max(t_settle, 0) * 1e9, 2))


if __name__ == "__main__":
    res = dict(iref_uA=IREF * 1e6, vref_V=VREF, threshold_design_uS=IREF / VREF * 1e6, sizes_um=S,
               lrs_min_uS=G_LRS_MIN * 1e6, hrs_typ_uS=G_HRS_TYP * 1e6, A={}, B={}, C={})
    jobs = [(c, vdd, temp) for c in ("tt", "ss", "ff", "sf", "fs") for temp in (-40, 27, 125) for vdd in (1.62, 1.80, 1.98)]
    pool = Pool(int(os.environ.get("JOBS", os.cpu_count() or 1)))
    for (c, vdd, temp), r in zip(jobs, pool.starmap(dc_trip, jobs)):
        res["A"][f"{c} {temp}C {vdd}V"] = r
        print("A", c, temp, vdd, r, flush=True)
    trips = [v["trip_uS"] for v in res["A"].values() if v["trip_uS"] is not None]
    res["A_summary"] = dict(trip_min_uS=min(trips), trip_max_uS=max(trips), failed=sum(v["trip_uS"] is None for v in res["A"].values()),
                            margin_to_lrs_min_uS=round(G_LRS_MIN * 1e6 - max(trips), 2), margin_to_hrs_typ_uS=round(min(trips) - G_HRS_TYP * 1e6, 2))
    print(res["A_summary"], flush=True)
    res["models"] = f"open_pdks {OPDK}" if OPDK else f"google/skywater-pdk-libs-sky130_fd_pr {FDPR}"
    if OPDK:
        mc = [r["trip_uS"] for r in pool.starmap(dc_trip, [("tt", 1.8, 27, 1, s) for s in range(1, 201)])]
        mc = np.array([x for x in mc if x is not None])
        res["B"] = dict(runs=200, valid=int(len(mc)), mean_uS=round(float(mc.mean()), 3), sigma_uS=round(float(mc.std()), 3),
                        min_uS=round(float(mc.min()), 3), max_uS=round(float(mc.max()), 3))
        print("B", res["B"], flush=True)
    else:
        res["B"] = "not run: the raw sky130_fd_pr models carry no ngspice mismatch hook; set SKY130_NGSPICE_LIB to the open_pdks library"
    for c, temp in (("tt", 27), ("ss", 27), ("ff", 27), ("ss", 125), ("ff", -40)):
        for G in (G_LRS_MIN, G_HRS_TYP):
            r = tran(c, temp, G)
            res["C"][f"{c} {temp}C G {G*1e6:g} uS"] = r
            print("C", c, temp, r, flush=True)
    (ROOT / "results" / "sky130_read.json").write_text(json.dumps(res, indent=1))
