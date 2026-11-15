"""Experiment list of paper v1 (14 November 2026). Every result goes to results/security/v1/<name>.json.

  python3 studies/paper-v1-2026-11-14/run_v1.py tvla [part k of n] | zeros | bound | extras
All results are statements about the model (tools/leak_v1.py), not about silicon."""
import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import leak_v1 as L   # noqa: E402

V1 = L.V1
NS = (1, 16, 256, 4096, 65536, 1048576, 16777216)
DC = 5.5     # fF: assumed sd of a line's routing capacitance about its column's mean (the 2T2R macro's extraction gives 5.5 fF)

DESIGNS = {   # name: (cell, layout, dc, rot, rot_at_array)
    "2t2r":                 ("2T2R", "drawn", "extracted", False, False),
    "1of3_drawn":           ("1of3", "drawn", 0.0, False, False),
    "1of3_drawn_rot":       ("1of3", "drawn", 0.0, True, False),
    "1of3_bal":             ("1of3", "balanced", 0.0, False, False),
    "1of3_bal_rot":         ("1of3", "balanced", 0.0, True, False),
    "1of3_bal_dc_rot":      ("1of3", "balanced", DC, True, False),
    "1of3_bal_dc_rotarr":   ("1of3", "balanced", DC, True, True),
    "1of3_drawn_dc":        ("1of3", "drawn", DC, False, False),
    "1of3_drawn_dc_rot":    ("1of3", "drawn", DC, True, False),
}


def design(T, name):
    return L.Design(T, *DESIGNS[name])


def save(name, r):
    r["assumptions"] = dict(noise_uA_rms_per_window=L.SIGMA, k_dig_uA=L.K_DIG, windows=L.NW, window_ns=62.5)
    (V1 / f"{name}.json").write_text(json.dumps(r, indent=1))


def run_tvla(part=0, parts=1, ntr=150000):
    T = L.Templates("shared", "published")
    jobs = [("2t2r", "fvr"), ("2t2r", "fvf"), ("1of3_drawn", "fvr"), ("1of3_drawn", "fvf"), ("1of3_drawn_rot", "fvr"),
            ("1of3_drawn_rot", "fvf"), ("1of3_bal_rot", "fvr"), ("1of3_bal_rot", "fvf"), ("1of3_bal", "fvf")]
    cps = (10000, 20000, 50000, 100000, 150000, 300000, 600000, 1000000)
    for k, (d, kind) in enumerate(jobs):
        if k % parts != part or (V1 / f"tvla_{d}_{kind}.json").exists():
            continue
        t0 = time.time(); r = L.tvla(T, design(T, d), kind, ntr, checkpoints=cps); r["seconds"] = round(time.time() - t0)
        save(f"tvla_{d}_{kind}", r); print(d, kind, r["max_abs_t_first"], r["max_abs_t_second"], r["seconds"], "s", flush=True)


def run_tvla_matrices(part=0, parts=1, ntr=50000):
    """The headline cases over five fixed matrices (and chips)."""
    T = L.Templates("shared", "published"); out = {}
    jobs = [("1of3_drawn", "fvf"), ("1of3_drawn_rot", "fvf"), ("1of3_bal_rot", "fvf"), ("1of3_bal_rot", "fvr")]
    for k, (d, kind) in enumerate(jobs):
        if k % parts != part:
            continue
        rs = [L.tvla(T, design(T, d), kind, ntr, mseed=100 + m) for m in range(3)]
        r = dict(design=rs[0]["design"], test=rs[0]["test"], traces_per_group=ntr, matrices=3,
                 max_abs_t_first=[x["max_abs_t_first"] for x in rs], max_abs_t_second=[x["max_abs_t_second"] for x in rs])
        save(f"tvlam_{d}_{kind}", r); print(d, kind, r["max_abs_t_first"], r["max_abs_t_second"], flush=True)


def run_zeros():
    for states in ("published", "programmed"):
        T = L.Templates("shared", states)
        names = list(DESIGNS) if states == "published" else ["2t2r", "1of3_drawn", "1of3_drawn_rot", "1of3_bal_rot"]
        for d in names:
            r = L.attack_zeros(T, design(T, d), NS); r["states"] = states
            save(f"zeros_{d}" + ("" if states == "published" else "_prog"), r)
            print(states, d, [(x["reads_per_row"], x["corr_mean"], x["rows_exact_mean"]) for x in r["results"]], flush=True)
    # trained weights: the three 72 x 24 tiles of the digits network's first layer
    T = L.Templates("shared", "published")
    T1 = np.load(ROOT / "results" / "ternary_digits_weights.npz")["T1"]
    tiles = np.stack([T1[:, 24 * k:24 * (k + 1)] for k in range(3)])
    for d in ("2t2r", "1of3_drawn", "1of3_drawn_rot", "1of3_bal_rot"):
        r = L.attack_zeros(T, design(T, d), NS, wsrc=tiles); r["weights"] = "digits network, layer 1 (16.7 % zeros)"
        r["zero_count_sd"] = round(float((tiles == 0).sum(2).std()), 2)
        save(f"zeros_{d}_trained", r); print("trained", d, [(x["reads_per_row"], x["corr_mean"]) for x in r["results"]], flush=True)


def run_bound():
    T = L.Templates("shared", "published"); ns = (1, 1e2, 1e4, 1e6, 1e8)
    for d in DESIGNS:
        des = design(T, d)
        r = dict(calibrated=L.bound(T, des, ns, True), profiled=L.bound(T, des, ns, False))
        save(f"bound_{d}", r); print(d, "calibrated", r["calibrated"]["bits_per_row"], "profiled", r["profiled"]["bits_per_row"], flush=True)


def run_extras():
    """Mismatch spreads of both Monte Carlo sets, cost table, error-detection table, per-layer signal sizes."""
    out = {}
    for v in ("shared", "full"):
        f = V1 / f"seq_mm_{v}.json"
        if f.exists():
            s = json.loads(f.read_text()); out[f"mismatch_{v}"] = dict(sd_read_mean_uA=s["mismatch_sd_uA_read_mean"], reads_correct=s["reads_correct"],
                                                                         samples=s["mismatch_samples"])
    T = L.Templates("shared", "published")
    # per-read supply charge (fC) of one amplifier at the published and the programmed states
    z = np.load(V1 / "seq_mm_shared.npz"); G = list(z["G_uS"]); nom = z["nominal_uA"]
    qf = lambda g: float(nom[G.index(g)].sum() * 62.5e-9 * 1e-6 * 1e15)
    out["charge_fC_per_read"] = {f"{g:g}uS": round(qf(g), 2) for g in (0.31, 4.5, 30.0, 60.0)}
    pre = float(nom[G.index(4.5)][:4].sum() * 62.5e-9 * 1e-6 * 1e15)
    out["precharge_fC"] = round(pre, 2)
    cost = {}
    for name, gl, gh in (("published", 60.0, 4.5), ("programmed", 30.0, 0.31)):
        qL, qH = qf(gl), qf(gh)
        row = dict(one_of_three_fC=round(qL + 2 * qH, 2), t2t2r_nonzero_fC=round(qL + qH, 2), t2t2r_zero_fC=round(2 * qH, 2))
        for s in (0.0, 1 / 3, 0.5, 0.7):
            row[f"ratio_at_{round(s * 100)}pct_zeros"] = round((qL + 2 * qH) / ((1 - s) * (qL + qH) + s * 2 * qH), 3)
        cost[name] = row
    out["read_charge_cost"] = cost
    # layout term: zero weight minus non-zero weight, nominal, neighbors averaged (LRS with probability 1/3)
    d3 = L.Design(T, "1of3", "drawn"); rng = np.random.default_rng(5)
    W = rng.integers(-1, 2, (20000, L.COLS)); lm, kidx = L.states(W, "1of3")
    lay = d3.K[np.arange(3), kidx]                       # (n, COLS, 3, NW)
    percell = lay.sum(2)                                 # (n, COLS, NW)
    inner = (slice(None), slice(1, L.COLS - 1))
    z0 = percell[inner][W[inner] == 0].mean(0); nz = percell[inner][W[inner] != 0].mean(0)
    p1 = percell[inner][W[inner] == 1].mean(0); m1 = percell[inner][W[inner] == -1].mean(0)
    out["layout_term_nA"] = dict(zero_minus_nonzero=[round(float(x) * 1e3, 2) for x in z0 - nz], plus_minus_minus=[round(float(x) * 1e3, 2) for x in p1 - m1])
    out["routing_sensitivity_nA_per_fF"] = dict(LRS=[round(float(x) * 1e3, 3) for x in T.SC[1]], HRS=[round(float(x) * 1e3, 3) for x in T.SC[0]],
                                                lrs_minus_hrs=[round(float(x) * 1e3, 3) for x in T.SC[1] - T.SC[0]])
    # 2T2R: zero minus non-zero, nominal single-line templates
    out["t2t2r_zero_minus_nonzero_uA"] = [round(float(x), 3) for x in T.nom[0] - T.nom[1]]
    # amplifier mismatch: sd over amplifiers of (LRS - HRS) per window, conductance-averaged
    TTm = T.TT.mean(2); out["mismatch_sd_lrs_minus_hrs_uA"] = [round(float(x), 4) for x in (TTm[:, 1] - TTm[:, 0]).std(0)]
    out["conductance_fixed_pattern_sd_uA"] = dict(HRS=[round(float(x), 4) for x in T.TT[:, 0].std(1).mean(0)], LRS=[round(float(x), 4) for x in T.TT[:, 1].std(1).mean(0)])
    # error detection: a device changes state with probability p (LRS -> HRS: pl; HRS -> LRS: ph), independently
    det = {}
    for pl, ph in ((1e-4, 1e-4), (1e-3, 1e-4), (1e-4, 1e-6)):
        # 2T2R, weights uniform: +-1 (one LRS, one HRS), 0 (two HRS)
        s_nz = pl * (1 - ph)            # LRS lost, HRS stays: silent zero
        s_nz += pl * ph                 # both flip: the opposite sign, silent
        s_z = 2 * ph * (1 - ph)         # one HRS sets: a silent +-1
        silent2 = (2 / 3) * s_nz + (1 / 3) * s_z
        det2 = (2 / 3) * (1 - pl) * ph + (1 / 3) * ph * ph
        # one-of-three: silent only if the LRS is lost and exactly one of the two HRS sets
        silent3 = pl * 2 * ph * (1 - ph)
        det3 = 1 - (1 - pl) * (1 - ph) ** 2 - silent3
        det[f"pl={pl:g},ph={ph:g}"] = dict(t2t2r_silent=float(f"{silent2:.3g}"), t2t2r_detected=float(f"{det2:.3g}"),
                                           one_of_three_silent=float(f"{silent3:.3g}"), one_of_three_detected=float(f"{det3:.3g}"))
    out["error_detection_per_weight"] = det
    save("extras", out); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    a = [int(x) for x in sys.argv[2:]]
    if cmd == "tvla":
        run_tvla(*a)
    elif cmd == "tvlam":
        run_tvla_matrices(*a)
    elif cmd == "zeros":
        run_zeros()
    elif cmd == "bound":
        run_bound()
    elif cmd == "extras":
        run_extras()
