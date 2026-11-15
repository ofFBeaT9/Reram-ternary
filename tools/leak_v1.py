"""Leakage of the array read current, model v1 (14 November 2026; paper study v1).

What changed against tools/tvla_circuit.py (8 November):
- Waveforms follow the array controller's sequence (chip/sky130/sim/seq_read.py): precharge with the word line off, the read,
  the recharge after the word line falls; 12 windows of one clock cycle (62.5 ns) per row read.
- Every sense amplifier of a chip is its own Monte Carlo sample (400 samples; 72 or 48 drawn without replacement per chip).
- The bit-line capacitances of the drawn layout enter: a nominal correction per line that depends on the line (P, Z or N), on
  its own device and on its two neighbor lines (SPICE of the coupled lines, results/security/v1/seq_cell.json), and a routing
  imbalance term (the line's deviation in fF times the SPICE sensitivity, seq_sens.json).
- Sense-amplifier rotation per column and read (option), at the amplifier or at the array edge.

Tests and attacks (all are statements about this model, not about silicon):
  tvla        row-aligned Welch t, first order and second order (centered squares): fixed weights against random weights, and
              fixed against fixed with every row's columns permuted (same zero count and sign counts per row: position only);
              both groups reprogrammed for every trace unless --frozen.
  zeros       profiled zero-count attack: least squares on the 12 windows, profiled on other chips of the same design.
  bound       Gaussian-channel bound on the information about one row's 24 weights in its averaged read current.
Assumptions, stated so that they can be changed: measurement noise SIGMA uA rms per window; K_DIG uA per flipped accumulator bit;
conductance distributions (published: HRS lognormal median 4.5 uS, sigma_ln 0.3, at most 7.93 uS; LRS lognormal median 60 uS,
sigma_ln 0.35, 30-120 uS; programmed: LRS uniform 28.4-29.9 uS, HRS lognormal median 0.6 uS, sigma_ln 0.3, 0.31-7.93 uS)."""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tvla_tcim0 as M   # noqa: E402  (toggles)

V1 = ROOT / "results" / "security" / "v1"
ROWS, COLS, NW, Q = 72, 24, 12, 32
SIGMA, K_DIG, W_DIG = 5.0, 0.15, 8
RIDGE = 1e-5          # uA^2: ridge of the attack's estimator (3 nA rms per window); without it the estimate degrades above 1e7 reads
ND = {"2T2R": 2, "1of3": 3}


def gq(states):
    u = (np.arange(Q) + 0.5) / Q
    if states == "published":
        h = np.minimum(4.5 * np.exp(0.3 * norm.ppf(u)), 7.93); lo = np.clip(60.0 * np.exp(0.35 * norm.ppf(u)), 30.0, 120.0)
    else:
        h = np.clip(0.6 * np.exp(0.3 * norm.ppf(u)), 0.31, 7.93); lo = 28.4 + 1.5 * u
    return h, lo


class Templates:
    def __init__(self, variant="shared", states="published"):
        z = np.load(V1 / f"seq_mm_{variant}.npz"); G = z["G_uS"]; mm = z["mm_uA"]; nom = z["nominal_uA"]
        self.S = mm.shape[0]; hi = G < 12; lo = G >= 24
        gh, gl = gq(states)

        def itp(tab, g, x):                      # tab (..., P, NW) on grid g -> (..., Q, NW) at conductances x, linear in log G
            lg, lx = np.log(g), np.log(x)
            i = np.clip(np.searchsorted(lg, lx) - 1, 0, len(lg) - 2); f = ((lx - lg[i]) / (lg[i + 1] - lg[i]))[:, None]
            return tab[..., i, :] * (1 - f) + tab[..., i + 1, :] * f
        self.TT = np.stack([itp(mm[:, hi], G[hi], gh), itp(mm[:, lo], G[lo], gl)], 1).astype(np.float32)   # (S, state, Q, NW)
        self.nom = np.stack([nom[list(G).index(4.5)], nom[list(G).index(60.0)]])                              # (state, NW) at 4.5 / 60 uS
        s = json.loads((V1 / "seq_sens.json").read_text())["cases"]
        self.SC = np.stack([(np.array(s["HRS_200fF"]["uA"]) - np.array(s["HRS_100fF"]["uA"])) / 100.0,
                            (np.array(s["LRS_200fF"]["uA"]) - np.array(s["LRS_100fF"]["uA"])) / 100.0]).astype(np.float32)  # uA per fF
        self.cell = json.loads((V1 / "seq_cell.json").read_text())["cases"]

    def ktab(self, cell, layout):
        nd = ND[cell]; K = np.zeros((nd, 8, NW)); n = np.zeros((nd, 8))
        if layout != "drawn":
            return K.astype(np.float32)
        for c in self.cell:
            if c["cell"] != ("3T3R" if cell == "1of3" else "2T2R") or c["layout"] != "drawn":
                continue
            w = c["weight"]; a = np.array(c["line_uA"])
            st = [c["left_lrs"], w == 1] + ([w == 0] if nd == 3 else []) + [w == -1, c["right_lrs"]]
            for d in range(nd):
                i = d + 1; key = int(st[i]) * 4 + int(st[i - 1]) * 2 + int(st[i + 1])
                K[d, key] += a[i] - self.nom[int(st[i])]; n[d, key] += 1
        return (K / np.maximum(n, 1)[..., None]).astype(np.float32)


class Design:
    """What is the same on every chip: cell, layout corrections, routing imbalance, rotation."""
    def __init__(self, T, cell, layout="drawn", dc_sd=0.0, rot=False, rot_at_array=False, seed=1):
        self.cell, self.nd, self.layout, self.rot, self.rot_at_array = cell, ND[cell], layout, rot, rot_at_array
        self.K = T.ktab(cell, layout)
        rng = np.random.default_rng(1000 + seed)
        if dc_sd == "extracted":                 # 2T2R macro: every line's routing capacitance minus its column's mean
            L = json.loads((ROOT / "results/sky130_chip/macro_rc.json").read_text())["routing_C"]["lines"]
            c = np.array([[L[f"BLP{k}"]["C_total_fF"] - L[f"BLP{k}"]["C_array_fF"], L[f"BLN{k}"]["C_total_fF"] - L[f"BLN{k}"]["C_array_fF"]]
                          for k in range(COLS)])
            self.dC = (c - c.mean(1, keepdims=True)).astype(np.float32)
        else:
            d = rng.normal(0, 1, (COLS, self.nd)); d -= d.mean(1, keepdims=True)
            self.dC = (d * dc_sd * np.sqrt(self.nd / (self.nd - 1))).astype(np.float32)
        self.label = f"{cell} {layout}" + (f" dC={dc_sd}" if dc_sd else "") + (" rot" + ("@array" if rot_at_array else "") if rot else "")


def new_chip(rng, T, des):
    return rng.choice(T.S, (COLS, des.nd), replace=False)


def states(W, cell):
    """W (..., COLS) -> lm (..., COLS, nd) LRS mask in the physical order of the lines (P, Z, N or P, N), and the index of the
    layout correction of every line: own * 4 + left neighbor * 2 + right neighbor."""
    p, n, z = W == 1, W == -1, W == 0
    F = np.zeros_like(p[..., :1])
    nL = np.concatenate([F, n[..., :-1]], -1); pR = np.concatenate([p[..., 1:], F], -1)
    if cell == "1of3":
        lm = np.stack([p, z, n], -1); left = np.stack([nL, p, z], -1); right = np.stack([z, n, pR], -1)
    else:
        lm = np.stack([p, n], -1); left = np.stack([nL, p], -1); right = np.stack([n, pR], -1)
    return lm, lm * 4 + left * 2 + right


CI = np.arange(COLS)[:, None]


def traces(rng, T, des, chip, W, n, Gq=None, digital=True, noise=True):
    """n row-aligned traces (n, ROWS, NW). W: (ROWS, COLS) or None (random weights for every trace). Gq: (ROWS, COLS, nd) frozen
    conductance quantiles, or None (reprogrammed for every trace)."""
    nd = des.nd
    Wn = rng.integers(-1, 2, (n, ROWS, COLS)) if W is None else np.broadcast_to(W, (n, ROWS, COLS))
    lm, kidx = states(Wn, des.cell)
    q = rng.integers(0, Q, lm.shape) if Gq is None else np.broadcast_to(Gq, lm.shape)
    d = np.arange(nd)
    if des.rot:
        r = rng.integers(0, nd, (n, ROWS, COLS, 1)); sidx = (d + r) % nd
        sa = chip[CI, sidx]
    else:
        sidx = np.broadcast_to(d, lm.shape); sa = np.broadcast_to(chip, lm.shape)
    y = T.TT[sa, lm.astype(np.int8), q].sum((2, 3), dtype=np.float64)                       # (n, ROWS, NW)
    y += des.K[d, kidx].sum((2, 3))
    if np.any(des.dC):
        dc = des.dC[CI, sidx] if (des.rot and des.rot_at_array) else np.broadcast_to(des.dC, lm.shape)
        y += (T.SC[lm.astype(np.int8)] * dc[..., None]).sum((2, 3))
    if digital:
        X = rng.integers(-1, 2, (n, ROWS))
        A = rng.integers(-128, 128, (n, 1)) + np.zeros((n, COLS), int); D = rng.integers(0, 1024, (n, COLS))
        for k in range(ROWS):
            upd = (Wn[:, k] != 0) & (X[:, k:k + 1] != 0); dlt = Wn[:, k] * X[:, k:k + 1]
            tr = np.where(upd, M.toggles(A, dlt), 0.0); A = np.where(upd, A + dlt, A)
            dd = rng.choice([-1, 1], (n, COLS)); tr += np.where(~upd, M.toggles(D, dd), 0.0); D = np.where(~upd, D + dd, D)
            y[:, k, W_DIG] += K_DIG * tr.sum(1)
    if noise:
        y += rng.normal(0, SIGMA, y.shape)
    return y


class Mom:
    """Streaming moments per sample point for first- and second-order Welch t."""
    def __init__(self, n):
        self.c = np.zeros(2); self.s = np.zeros((2, 4, n))

    def add(self, g, x):
        x = x.reshape(len(x), -1); self.c[g] += len(x)
        for k in range(4):
            self.s[g, k] += (x ** (k + 1)).sum(0)

    def t(self):
        m = self.s / self.c[:, None, None]
        m1 = m[:, 0]; v = m[:, 1] - m1 ** 2
        t1 = (m1[0] - m1[1]) / np.sqrt(v[0] / self.c[0] + v[1] / self.c[1])
        # second order: centered squares; mean = v, variance = mu4 - v^2
        mu4 = m[:, 3] - 4 * m[:, 2] * m1 + 6 * m[:, 1] * m1 ** 2 - 3 * m1 ** 4
        v2 = np.maximum(mu4 - v ** 2, 1e-30)
        t2 = (v[0] - v[1]) / np.sqrt(v2[0] / self.c[0] + v2[1] / self.c[1])
        return t1, t2


def permute_rows(rng, W):
    return np.stack([r[rng.permutation(COLS)] for r in W])


def tvla(T, des, kind, ntr, mseed=7, frozen=False, chunk=250, wsrc=None, checkpoints=()):
    rng = np.random.default_rng(mseed)
    chip = new_chip(rng, T, des)
    W0 = rng.integers(-1, 2, (ROWS, COLS)) if wsrc is None else wsrc
    W1 = permute_rows(rng, W0) if kind == "fvf" else None
    G0 = rng.integers(0, Q, (ROWS, COLS, des.nd)) if frozen else None
    mom = Mom(ROWS * NW); done = 0; curve = []
    while done < ntr:
        n = min(chunk, ntr - done)
        mom.add(0, traces(rng, T, des, chip, W0, n, G0)); mom.add(1, traces(rng, T, des, chip, W1, n))
        done += n
        if done in checkpoints:
            t1, t2 = mom.t(); curve.append(dict(traces=done, t1=round(float(np.abs(t1).max()), 2), t2=round(float(np.abs(t2).max()), 2)))
    t1, t2 = mom.t()
    k1 = int(np.abs(t1).argmax())
    return dict(design=des.label, test={"fvr": "fixed vs random weights", "fvf": "fixed vs fixed, columns of every row permuted"}[kind],
                traces_per_group=ntr, matrix_seed=mseed, fixed_group_frozen=frozen, zeros_in_fixed=int((W0 == 0).sum()),
                max_abs_t_first=round(float(np.abs(t1).max()), 2), max_abs_t_second=round(float(np.abs(t2).max()), 2),
                window_of_max_first=k1 % NW, leaks_first=bool(np.abs(t1).max() > 4.5), leaks_second=bool(np.abs(t2).max() > 4.5),
                curve=curve)


# ------------------------------------------------------------------------------------------------ expected currents of a chip
def chip_mean(T, des, chip, W, Gq):
    """Noise-free expected current of every row (R, NW) of a programmed chip (frozen conductance quantiles Gq (R, COLS, nd)),
    averaged over the rotation if the design rotates; and the variance per read that the rotation adds (R, NW)."""
    nd = des.nd; lm, kidx = states(W, des.cell); st = lm.astype(np.int8); d = np.arange(nd)
    R = W.shape[0]; ci = np.broadcast_to(CI, (R, COLS, nd))
    if des.rot:
        per = np.stack([T.TT[chip[ci, (d + r) % nd], st, Gq].sum(2) for r in range(nd)])   # (nd, R, COLS, NW)
        y = per.mean(0).sum(1); var = per.var(0).sum(1)
    else:
        y = T.TT[np.broadcast_to(chip, lm.shape), st, Gq].sum((1, 2)); var = np.zeros_like(y)
    y = y + des.K[d, kidx].sum((1, 2))
    if np.any(des.dC):
        if des.rot and des.rot_at_array:
            dc = np.broadcast_to(des.dC.mean(1, keepdims=True), lm.shape)
        else:
            dc = np.broadcast_to(des.dC, lm.shape)
        y = y + (T.SC[st] * dc[..., None]).sum((1, 2))
    return y, var


def attack_zeros(T, des, ns, chips=20, prof=8, seed=13, wsrc=None):
    """Profiled zero-count attack. Profiling: `prof` chips of the same design with known random weights, read without noise
    (an attacker can average its own chips as long as it likes): the mean and covariance of the row currents and their
    covariance with the zero count. Victim: N reads of every row averaged. Estimator: the linear minimum-mean-square-error
    estimate for that N (the profiled covariance plus the noise of N reads plus a ridge of RIDGE), rounded to an integer."""
    rng = np.random.default_rng(seed); out = []
    res = {n: ([], []) for n in ns}
    for _ in range(chips):
        Xp, yp = [], []
        for _ in range(prof):
            Wp = rng.integers(-1, 2, (ROWS, COLS)) if wsrc is None else permute_rows(rng, wsrc[rng.integers(len(wsrc))])
            m, _ = chip_mean(T, des, new_chip(rng, T, des), Wp, rng.integers(0, Q, (ROWS, COLS, des.nd)))
            Xp.append(m); yp.append((Wp == 0).sum(1))
        Xp = np.concatenate(Xp); yp = np.concatenate(yp).astype(float)
        mu = Xp.mean(0); zb = yp.mean(); Xc = Xp - mu
        Sxx = Xc.T @ Xc / len(Xc); Sxz = Xc.T @ (yp - zb) / len(Xc)
        W = rng.integers(-1, 2, (ROWS, COLS)) if wsrc is None else wsrc[rng.integers(len(wsrc))]
        z = (W == 0).sum(1)
        m, var = chip_mean(T, des, new_chip(rng, T, des), W, rng.integers(0, Q, (ROWS, COLS, des.nd)))
        for n in ns:
            nv = (SIGMA ** 2 + var.mean(0)) / n
            beta = np.linalg.solve(Sxx + np.diag(nv) + RIDGE * np.eye(NW), Sxz)
            y = m + rng.normal(0, 1, m.shape) * np.sqrt((SIGMA ** 2 + var) / n)
            est = np.clip(np.rint(zb + (y - mu) @ beta), 0, COLS)
            res[n][0].append(float(np.corrcoef(z, est)[0, 1]) if np.std(est) > 0 else 0.0); res[n][1].append(float((est == z).mean()))
    for n in ns:
        c = np.array(res[n][0]); e = np.array(res[n][1])
        out.append(dict(reads_per_row=n, corr_mean=round(float(c.mean()), 3), corr_se=round(float(c.std(ddof=1) / np.sqrt(len(c))), 3),
                        rows_exact_mean=round(float(e.mean()), 3)))
    return dict(design=des.label, chips=chips, profiling_chips=prof, results=out)


def bound(T, des, ns, knows_sa, chips=8, nrows=3000, seed=17):
    """Gaussian-channel bound on I(weights of one row; its averaged read current), bits. Signal: the expected current as a
    function of the row's weights (conductances averaged). Noise: measurement noise / N, the rotation's sampling noise / N, and
    the fixed pattern of the device conductances (not known to the attacker, does not average out). knows_sa: the attacker knows
    every sense amplifier of the victim (calibrated); otherwise the amplifiers' mismatch is one more unknown fixed pattern."""
    rng = np.random.default_rng(seed); nd = des.nd; d = np.arange(nd)
    TTm = T.TT.mean(2)                                    # (S, state, NW) conductance-averaged
    cq = np.einsum("ssqw,ssqv->ssqwv", np.zeros((1, 1, 1, 1)), np.zeros((1, 1, 1, 1))) if False else None
    dev = T.TT - TTm[:, :, None]                          # (S, state, Q, NW)
    covq = np.einsum("asqw,asqv->aswv", dev, dev) / Q     # (S, state, NW, NW) covariance over conductance
    pool_m = TTm.mean(0); pd_ = TTm - pool_m              # pool mean (state, NW)
    cov_s = np.einsum("asw,asv->swv", pd_, pd_) / T.S     # (state, NW, NW) covariance over amplifiers
    acc = {n: [] for n in ns}
    for _ in range(chips):
        chip = new_chip(rng, T, des)
        W = rng.integers(-1, 2, (nrows, COLS)); lm, kidx = states(W, des.cell); st = lm.astype(np.int8)
        ci = np.broadcast_to(CI, (nrows, COLS, nd))
        if des.rot:
            per = np.stack([TTm[chip[ci, (d + r) % nd], st].sum(2) for r in range(nd)]); sa_part = per.mean(0).sum(1); rv = per.var(0).sum(1).mean(0)
            fp = np.mean([covq[chip[ci, (d + r) % nd], st].sum((1, 2)) for r in range(nd)], 0).mean(0) / nd   # averaged over nd rotations
        else:
            sa_part = TTm[np.broadcast_to(chip, lm.shape), st].sum((1, 2)); rv = np.zeros(NW)
            fp = covq[np.broadcast_to(chip, lm.shape), st].sum((1, 2)).mean(0)
        lay = des.K[d, kidx].sum((1, 2))
        if np.any(des.dC):
            dc = np.broadcast_to(des.dC.mean(1, keepdims=True) if (des.rot and des.rot_at_array) else des.dC, lm.shape)
            lay = lay + (T.SC[st] * dc[..., None]).sum((1, 2))
        if knows_sa:
            mu = sa_part + lay
        else:
            mu = pool_m[st].sum((1, 2)) + lay
            k = (1.0 / nd) if des.rot else 1.0            # rotation averages each amplifier's deviation over nd devices
            fp = fp + k * cov_s[st].sum((1, 2)).mean(0)
        Ss = np.cov(mu.T)
        for n in ns:
            Sn = fp + np.diag((SIGMA ** 2 + rv) / n) + 1e-12 * np.eye(NW)
            acc[n].append(0.5 * np.linalg.slogdet(np.eye(NW) + np.linalg.solve(Sn, Ss))[1] / np.log(2))
    return dict(design=des.label, attacker="knows the victim's sense amplifiers" if knows_sa else "profiles other chips only",
                bits_per_row={str(n): round(float(np.mean(v)), 3) for n, v in acc.items()}, row_entropy_bits=round(COLS * np.log2(3), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tvla", "zeros", "bound", "smoke"])
    ap.add_argument("--variant", default="shared"); ap.add_argument("--states", default="published")
    ap.add_argument("--cell", default="1of3"); ap.add_argument("--layout", default="drawn"); ap.add_argument("--dc", default="0")
    ap.add_argument("--rot", action="store_true"); ap.add_argument("--rot-at-array", action="store_true")
    ap.add_argument("--kind", default="fvr"); ap.add_argument("--traces", type=int, default=150000); ap.add_argument("--mseed", type=int, default=7)
    ap.add_argument("--frozen", action="store_true"); ap.add_argument("--out", default="")
    a = ap.parse_args()
    T = Templates(a.variant, a.states)
    des = Design(T, a.cell, a.layout, a.dc if a.dc == "extracted" else float(a.dc), a.rot, a.rot_at_array)
    t0 = time.time()
    if a.cmd == "smoke":
        rng = np.random.default_rng(1); chip = new_chip(rng, T, des)
        y = traces(rng, T, des, chip, None, 200); print(y.shape, y.mean((0, 1)).round(2), round(time.time() - t0, 2), "s for 200 traces")
        return
    if a.cmd == "tvla":
        r = tvla(T, des, a.kind, a.traces, a.mseed, a.frozen)
    elif a.cmd == "zeros":
        r = attack_zeros(T, des, (1, 16, 256, 4096, 65536, 1048576, 16777216))
    else:
        r = dict(calibrated=bound(T, des, (1, 1e3, 1e6, 1e9), True), profiled=bound(T, des, (1, 1e3, 1e6, 1e9), False))
    r["seconds"] = round(time.time() - t0); r["assumptions"] = dict(noise_uA_rms_per_window=SIGMA, k_dig_uA=K_DIG, windows=NW, window_ns=62.5,
                                                                       states=a.states, mismatch_variant=a.variant)
    print(json.dumps(r, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
