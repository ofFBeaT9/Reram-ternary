"""Supply current of the sense amplifiers over one read, following the array controller's sequence (14 November 2026; paper study v1).

sa_transient.py (8 November) starts the read with the word line already on and the bit line discharged, so its waveform mixes
the bit-line precharge with the cell current. rtl/chip/tcim_actl.sv does it in this order (cycles of 62.5 ns at 16 MHz, shortest
settings cfg_ts = cfg_tr = 0):

    t = 0        BRK    lines leave ground (float at 0 V)
    62.5 ns      MAKE   bl_sen = 1: every bit line to its sense amplifier, word lines off  -> the lines precharge
    125 ns       SETL   2 cycles
    250 ns       WLON   4 cycles: the selected word line on; sampled in the last cycle
    500 ns       WLOFF, REL  word line off, bit lines still on the amplifiers -> a line that held an LRS device recharges
    625 ns       BRK2   bl_sen = 0
    687.5 ns     GND    lines grounded
    750 ns       end (ACK)

Here every bit line is a node with its capacitance to ground (array part + routing), coupling capacitors to its neighbor
lines, the selected cell (a conductance in series with its select transistor), the 71 unselected cells lumped, the bit-line
driver's off transmission gate, pull-down and column switch, and its own sense amplifier on its own 1.8 V source.
The supply current of each amplifier is averaged in 12 windows of one clock cycle (62.5 ns).

Capacitances of the drawn layouts (Magic extraction, layout/sky130/next_3t3r/rr3t3r.ext and tcim_sky130_array3.ext, per cell
row x 72 rows; layout/sky130/rr2t2r.ext): see CAP below. Routing capacitance outside the array is not extracted for the 3T3R
macro; the 2T2R macro's extraction (results/sky130_chip/macro_rc.json) gives 84-172 fF per line.

  python3 chip/sky130/sim/seq_read.py smoke | mm <full|shared> [NMM] | cell | rot | sens
Writes results/security/v1/seq_*.npz / .json."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S          # noqa: E402
import periph_sim as PS    # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "security" / "v1"
TC = 62.5e-9
T_END = 12 * TC
NWIN = 12
G_HRS = [0.31e-6, 1e-6, 2e-6, 3e-6, 4.5e-6, 6e-6, 7.93e-6]
G_LRS = [24e-6, 30e-6, 45e-6, 60e-6, 90e-6, 120e-6]
G_ALL = G_HRS + G_LRS
GL, GH = 60e-6, 4.5e-6
C_ROUTE = 130e-15                      # routing outside the array, per line (2T2R macro: 84-172 fF); reference value
# drawn 3T3R cell, per line over 72 rows (aF per cell row x 72): capacitance to substrate, source line, word lines and the
# devices' inner nodes counted as ground; coupling between neighboring bit lines kept as capacitors.
CAP3 = dict(cg=dict(P=215.3e-18 * 72, Z=148.2e-18 * 72, N=204.1e-18 * 72), c_pz=77.3e-18 * 72, c_zn=77.3e-18 * 72,
            c_np=97.4e-18 * 72)       # c_np: N of column c to P of column c+1
CAP2 = dict(cg=dict(P=222.0e-18 * 72, N=222.0e-18 * 72), c_pn=38.66e-18 * 72, c_np=97.4e-18 * 72)
NJ = int(os.environ.get("JOBS", "2"))


def deck(lines, coup=(), mm=False, bias=None, rot=None, c_sa=None):
    """lines: [(G in S, C to ground in F)]; coup: [(i, j, C)]; bias: (vbp, vcl) replaces the reference generator;
    rot: None, or r in 0..2 for three lines behind a 3 x 3 switch matrix (amplifier k reads line (k + r) mod 3);
    c_sa: capacitance on each amplifier's input node (routing between a rotation switch at the array edge and the amplifier)."""
    d = PS.hdr("tt", 27, mm) + f"""Vcc vccd 0 1.8
Vda vdda 0 3.3
Vprg vprg 0 0
"""
    if bias is None:
        d += f"""Vref vref 0 {PS.VREF}
Iib vccd ib {PS.IUNIT}
Vr0 r0 0 0
Vr1 r1 0 1.8
Vr2 r2 0 0
Xrb ib r0 r1 r2 vref vbp vcl vccd 0 refbias
"""
    else:
        d += f"Vbp vbp 0 {bias[0]}\nVcl vcl 0 {bias[1]}\n"
    d += """Vcs csg 0 pwl(0 0 62.5n 0 62.8n 3.3 625n 3.3 625.3n 0)
Vwl wlr 0 pwl(0 0 250n 0 252n 3.3 500n 3.3 502n 0)
Vdn dng 0 pwl(0 3.3 0.3n 0 687.5n 0 687.8n 3.3)
"""
    n = len(lines)
    for k, (g, cg) in enumerate(lines):
        d += f"""Vsa{k} vsa{k} 0 1.8
Xsa{k} sa{k} out{k} vbp vcl vsa{k} 0 sa
Xtg{k} vprg bl{k} 0 vdda vdda 0 tg wn=4 wp=8
Xpd{k} bl{k} dng 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=2 l=0.5
Vg{k} gc{k} 0 {g}
Bc{k} bl{k} dv{k} i=v(gc{k})*v(bl{k},dv{k})
Xt{k} dv{k} wlr 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
Ru{k} bl{k} du{k} {1 / (120e-6 * 71):.4g}
Xu{k} du{k} 0 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=71 l=0.5
Cg{k} bl{k} 0 {cg}
"""
        if c_sa:
            d += f"Csa{k} sa{k} 0 {c_sa}\n"
    if rot is None:
        for k in range(n):
            d += f"Xcs{k} bl{k} csg sa{k} 0 sky130_fd_pr__nfet_g5v0d10v5 w=2 l=0.5\n"
    else:
        assert n == 3
        d += "Vz zg 0 0\n"
        for k in range(3):
            for j in range(3):
                gate = "csg" if j == (k + rot) % 3 else "zg"
                d += f"Xcs{k}{j} bl{j} {gate} sa{k} 0 sky130_fd_pr__nfet_g5v0d10v5 w=2 l=0.5\n"
    for q, (i, j, c) in enumerate(coup):
        d += f"Cc{q} bl{i} bl{j} {c}\n"
    vec = " ".join(f"i(Vsa{k})" for k in range(n)) + " " + " ".join(f"v(out{k})" for k in range(n)) + " " + \
          " ".join(f"v(bl{k})" for k in range(n))
    return d + f""".control
tran 0.25n {T_END * 1e9:.1f}n
wrdata out.txt {vec}
.endc
.end
"""


def windows(t, i):
    e = np.arange(NWIN + 1) * TC
    tt = np.linspace(0, T_END, 12 * 250 + 1)
    ii = np.interp(tt, t, i)
    return np.array([np.trapezoid(ii[(tt >= a) & (tt <= b)], tt[(tt >= a) & (tt <= b)]) / TC for a, b in zip(e[:-1], e[1:])])


def run(lines, coup=(), seed=None, bias=None, rot=None, c_sa=None, full=False):
    d = deck(lines, coup, seed is not None, bias, rot, c_sa)
    if seed is not None:        # `set rndseed` in .spiceinit (spice.run) has no effect with ngspice 42 from apt: found on 14 November,
        d = d.replace(".control", f".option seed={seed}\n.control", 1)   # two runs with one seed differed. The option does work.
    a, _ = S.run(d)
    n = len(lines); t = a[:, 0]
    cur = np.array([windows(t, -a[:, 2 * k + 1] * 1e6) for k in range(n)])           # (n, NWIN) uA
    ks = np.searchsorted(t, 495e-9)
    out = np.array([a[ks, 2 * (n + k) + 1] for k in range(n)])
    vbl = np.array([[a[np.searchsorted(t, x), 2 * (2 * n + k) + 1] for x in (245e-9, 495e-9, 620e-9)] for k in range(n)])
    if full:
        return cur, out, vbl, a
    return cur, out, vbl


def nominal_bias():
    d = PS.hdr("tt", 27, False) + f"""Vcc vccd 0 1.8
Vref vref 0 {PS.VREF}
Iib vccd ib {PS.IUNIT}
Vr0 r0 0 0
Vr1 r1 0 1.8
Vr2 r2 0 0
Xrb ib r0 r1 r2 vref vbp vcl vccd 0 refbias
.control
op
print v(vbp) v(vcl)
.endc
.end
"""
    import subprocess, tempfile, re
    with tempfile.TemporaryDirectory() as td:
        Path(td, ".spiceinit").write_text("set ngbehavior=hsa\n"); Path(td, "t.cir").write_text(d)
        r = subprocess.run(["ngspice", "-b", "t.cir"], cwd=td, capture_output=True, text=True)
    v = dict(re.findall(r"v\((vbp|vcl)\) = (\S+)", r.stdout))
    return float(v["vbp"]), float(v["vcl"])


def _mm_job(job):
    g, seed, bias = job
    cur, out, _ = run([(g, CAP3["cg"]["P"] + C_ROUTE)], seed=seed, bias=bias)
    return g, seed, cur[0], float(out[0])


def do_mm(variant, nmm):
    bias = nominal_bias() if variant == "shared" else None
    jobs = [(g, None, bias) for g in G_ALL] + [(g, 2000 + s, bias) for s in range(nmm) for g in G_ALL]
    with ProcessPoolExecutor(NJ) as ex:
        res = list(ex.map(_mm_job, jobs, chunksize=8))
    nom = np.zeros((len(G_ALL), NWIN)); mm = np.zeros((nmm, len(G_ALL), NWIN)); ok = True
    for g, seed, w, vout in res:
        k = G_ALL.index(g)
        if seed is None:
            nom[k] = w
        else:
            mm[seed - 2000, k] = w
        ok &= (vout > 0.9) == (g >= 24e-6)        # the amplifier's output is high when the cell draws more than the reference
    # one seed must be one amplifier: its precharge current (window 1, word line off) cannot depend on the cell
    same = float(np.abs(mm[:, :, 1] - mm[:, :1, 1]).max())
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / f"seq_mm_{variant}.npz", G_uS=np.array(G_ALL) * 1e6, nominal_uA=nom, mm_uA=mm)
    kL, kH = G_ALL.index(GL), G_ALL.index(GH)
    summ = dict(note="sense-amplifier supply current over one read in the controller's sequence, 12 windows of 62.5 ns; "
                     "tt 27 C; local mismatch Monte Carlo, one seed = one physical amplifier",
                variant=variant, bias_V=bias, mismatch_samples=nmm, line_capacitance_fF=round((CAP3["cg"]["P"] + C_ROUTE) * 1e15, 2),
                mean_uA_nominal={f"{G_ALL[k] * 1e6:g}uS": round(float(nom[k].mean()), 4) for k in range(len(G_ALL))},
                windows_uA_nominal={f"{G_ALL[k] * 1e6:g}uS": [round(float(x), 4) for x in nom[k]] for k in (kH, kL)},
                mismatch_sd_uA_per_window=dict(LRS60=[round(float(x), 4) for x in mm[:, kL].std(0)],
                                               HRS4p5=[round(float(x), 4) for x in mm[:, kH].std(0)]),
                mismatch_sd_uA_read_mean=dict(LRS60=round(float(mm[:, kL].mean(1).std()), 4), HRS4p5=round(float(mm[:, kH].mean(1).std()), 4)),
                reads_correct=bool(ok), seed_check_max_precharge_difference_uA=round(same, 5))
    assert same < 0.01, "a seed did not reproduce the same amplifier"
    (OUT / f"seq_mm_{variant}.json").write_text(json.dumps(summ, indent=1)); print(json.dumps(summ, indent=1))


def _cell_job(job):
    tag, lines, coup, kw = job
    cur, out, vbl = run(lines, coup, **kw)
    return tag, cur, out, vbl


def cell3_lines(w, left_l, right_l, cap=CAP3, croute=None):
    """five lines: N of column c-1, P, Z, N of column c, P of column c+1. w in +1/0/-1; left_l / right_l: the neighbor line
    holds an LRS device. croute: routing capacitance of the three lines of column c (P, Z, N)."""
    cr = croute or dict(P=C_ROUTE, Z=C_ROUTE, N=C_ROUTE)
    st = dict(P=w == 1, Z=w == 0, N=w == -1)
    g = lambda lrs: GL if lrs else GH
    lines = [(g(left_l), cap["cg"]["N"] + C_ROUTE)] + [(g(st[x]), cap["cg"][x] + cr[x]) for x in "PZN"] + \
            [(g(right_l), cap["cg"]["P"] + C_ROUTE)]
    coup = [(0, 1, cap["c_np"]), (1, 2, cap["c_pz"]), (2, 3, cap["c_zn"]), (3, 4, cap["c_np"])]
    return lines, coup


def cell2_lines(w, left_l, right_l, cap=CAP2):
    """four lines: N of column c-1, P, N of column c, P of column c+1"""
    g = lambda lrs: GL if lrs else GH
    lines = [(g(left_l), cap["cg"]["N"] + C_ROUTE), (g(w == 1), cap["cg"]["P"] + C_ROUTE), (g(w == -1), cap["cg"]["N"] + C_ROUTE),
             (g(right_l), cap["cg"]["P"] + C_ROUTE)]
    return lines, [(0, 1, cap["c_np"]), (1, 2, cap["c_pn"]), (2, 3, cap["c_np"])]


def do_cell():
    """Nominal currents of one column's amplifiers with the drawn capacitances, for every weight and neighbor state."""
    jobs = []
    for w in (1, 0, -1):
        for ll in (0, 1):
            for rl in (0, 1):
                lines, coup = cell3_lines(w, ll, rl)
                jobs.append((("3T3R", "drawn", w, ll, rl), lines, coup, {}))
                l2, c2 = cell2_lines(w, ll, rl)
                jobs.append((("2T2R", "drawn", w, ll, rl), l2, c2, {}))
    # balanced reference: the three lines of a column with the same capacitance to ground and no coupling
    cgm = float(np.mean(list(CAP3["cg"].values()))); capb = dict(cg=dict(P=cgm, Z=cgm, N=cgm), c_pz=0.0, c_zn=0.0, c_np=0.0)
    for w in (1, 0, -1):
        lines, coup = cell3_lines(w, 0, 0, capb)
        jobs.append((("3T3R", "balanced", w, 0, 0), lines, [], {}))
    # transposed bit lines (every line spends a third of the column in each track): equal ground capacitance, in-column
    # coupling 2/3 of a neighbor pair between every two lines, 1/3 of the column-to-column coupling to the next line type
    cpair = (CAP3["c_pz"] + CAP3["c_zn"]) / 3
    for w in (1, 0, -1):
        st = dict(P=w == 1, Z=w == 0, N=w == -1)
        lines = [((GL if st[x] else GH), cgm + C_ROUTE) for x in "PZN"]
        jobs.append((("3T3R", "transposed", w, 0, 0), lines, [(0, 1, cpair), (1, 2, cpair), (0, 2, cpair)], {}))
    # routing imbalance: +10 fF on one line of the column at a time (sensitivity)
    for x in "PZN":
        for w in (1, 0, -1):
            cr = dict(P=C_ROUTE, Z=C_ROUTE, N=C_ROUTE); cr[x] += 10e-15
            lines, coup = cell3_lines(w, 0, 0, capb, cr)
            jobs.append((("3T3R", f"balanced+10fF_{x}", w, 0, 0), lines, [], {}))
    with ProcessPoolExecutor(NJ) as ex:
        res = list(ex.map(_cell_job, jobs))
    out = dict(note="nominal (tt 27 C) supply current of the sense amplifiers of one column over one read, controller sequence, "
                    "12 windows of 62.5 ns, with the drawn bit-line capacitances; lines: (N of column c-1,) P, (Z,) N (, P of column c+1)",
               cap3_fF={k: ({a: round(b * 1e15, 3) for a, b in v.items()} if isinstance(v, dict) else round(v * 1e15, 3)) for k, v in CAP3.items()},
               cap2_fF={k: ({a: round(b * 1e15, 3) for a, b in v.items()} if isinstance(v, dict) else round(v * 1e15, 3)) for k, v in CAP2.items()},
               c_route_fF=C_ROUTE * 1e15, G_LRS_uS=GL * 1e6, G_HRS_uS=GH * 1e6, cases=[])
    for tag, cur, o, vbl in res:
        out["cases"].append(dict(cell=tag[0], layout=tag[1], weight=tag[2], left_lrs=tag[3], right_lrs=tag[4],
                                 line_uA=[[round(float(x), 5) for x in r] for r in cur], out_V=[round(float(x), 3) for x in o],
                                 vbl_V_at_245_495_620ns=[[round(float(x), 4) for x in r] for r in vbl]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "seq_cell.json").write_text(json.dumps(out)); print("cases", len(out["cases"]))


def do_rot():
    """Three lines behind a 3 x 3 switch matrix: every weight and rotation, nominal; and the decode."""
    cgm = float(np.mean(list(CAP3["cg"].values())))
    jobs = []
    for where in ("amplifier", "array_edge"):
        for w in (1, 0, -1):
            st = dict(P=w == 1, Z=w == 0, N=w == -1)
            for r in (None, 0, 1, 2):
                if where == "amplifier":
                    lines = [((GL if st[x] else GH), cgm + C_ROUTE) for x in "PZN"]; kw = dict(rot=r)
                else:
                    lines = [((GL if st[x] else GH), cgm) for x in "PZN"]; kw = dict(rot=r, c_sa=C_ROUTE)
                    if r is None:
                        continue
                jobs.append(((where, w, r), lines, [], kw))
    with ProcessPoolExecutor(NJ) as ex:
        res = list(ex.map(_cell_job, jobs))
    out = dict(note="3 x 3 column-switch matrix (amplifier k reads line (k + r) mod 3); nominal tt 27 C; 'amplifier': switches at the "
                    "amplifier, routing capacitance on the line; 'array_edge': switches at the array, routing capacitance on the amplifier input",
               cases=[])
    ok = True
    for (where, w, r), cur, o, vbl in res:
        lrs_line = {1: 0, 0: 1, -1: 2}[w]
        if r is not None:
            sa_hi = int(np.argmax(o)); ok &= (sa_hi + r) % 3 == lrs_line and sorted(o)[1] < 0.9 and max(o) > 0.9
        out["cases"].append(dict(where=where, weight=w, rot=r, sa_uA=[[round(float(x), 5) for x in rr] for rr in cur],
                                 out_V=[round(float(x), 3) for x in o]))
    out["decode_correct"] = bool(ok)
    (OUT / "seq_rot.json").write_text(json.dumps(out)); print("decode_correct", ok)


def do_sens():
    """Nominal single line against its capacitance (for the routing-imbalance term)."""
    res = {}
    for c in (100e-15, 150e-15, 200e-15):
        for name, g in (("LRS", GL), ("HRS", GH)):
            cur, o, vbl = run([(g, c)])
            res[f"{name}_{c * 1e15:.0f}fF"] = dict(uA=[round(float(x), 5) for x in cur[0]], vbl_V=[round(float(x), 4) for x in vbl[0]])
    (OUT / "seq_sens.json").write_text(json.dumps(dict(note="single line, nominal, against its capacitance to ground", cases=res), indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if cmd == "smoke":
        import time
        t0 = time.time()
        for g in (GL, GH):
            cur, o, vbl = run([(g, 150e-15)])
            print(f"G {g * 1e6:g} uS  windows uA {cur[0].round(3)}  out@495ns {o[0]:.3f}  v(bl) {vbl[0].round(3)}")
        print(round(time.time() - t0, 1), "s; bias", nominal_bias())
    elif cmd == "mm":
        do_mm(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 400)
    elif cmd == "cell":
        do_cell()
    elif cmd == "rot":
        do_rot()
    elif cmd == "sens":
        do_sens()
