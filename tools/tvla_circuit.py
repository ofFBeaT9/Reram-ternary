"""Leakage of the array read current with transistor-level waveforms (8 November 2026; paper study).

tools/tvla_tcim0.py models each sense amplifier's supply current as one DC value per read. Here every sense amplifier
of the chip is one of the transient Monte Carlo samples of chip/sky130/sim/sa_transient.py (its waveform depends on the
device it reads and on its own frozen mismatch), sampled in WIN-ns windows over the 250 ns read. Everything else is
revision 4.7 as in tvla_tcim0.py: every product reads all 72 rows from a uniformly random start row, the result
accumulators start at a random offset, every column that does not update its result updates a dummy accumulator,
and each flipped accumulator bit adds K_DIG uA in the last window of its read.

Fixed-versus-random Welch t (pass |t| < 4.5). secret 'W': fixed weights (frozen device conductances) against random
weights reprogrammed for every trace (new conductances); secret 'X': fixed inputs against random inputs, fixed weights.
Device conductances: HRS lognormal, median 4.5 uS, sigma_ln 0.3, at most 7.93 uS (the reset-verify level); LRS lognormal,
median 60 uS, sigma_ln 0.35, clipped to 30-120 uS (SkyWater's set range). ASSUMPTIONS, stated so they can be changed:
measurement noise SIGMA uA rms per window, K_DIG uA per flipped bit.
Usage: python3 tools/tvla_circuit.py [--traces N] [--sigma S] [--only 2T2R,1of3] -> results/security/tvla_circuit.json"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tvla_tcim0 as M   # noqa: E402  (Welch, toggles, lrs_mask, NDEV, ROWS, COLS)

ROWS, COLS = M.ROWS, M.COLS
Z = np.load(ROOT / "results" / "security" / "sa_transient.npz")
GG = Z["G_uS"]; MM = Z["mm_uA"]                    # (seeds, G, windows of 10 ns)
NW = 5                                              # windows per read: 50 ns each (10-ns windows averaged by 5)
MM = MM.reshape(MM.shape[0], MM.shape[1], NW, -1).mean(-1)
HI, LI = GG < 12, GG >= 30
LGH, LGL = np.log(GG[HI]), np.log(GG[LI])
TH, TL = MM[:, HI], MM[:, LI]                       # (seeds, 5 points, NW)
K_DIG, SIGMA = 0.15, 5.0
LRS_SIG = 0.35                                      # sigma_ln of the LRS conductance (--lrs-sigma)
REDRAW = False    # --redraw: the fixed-weights group is reprogrammed every trace too (fresh conductances), so the test
                  # sees the weights only, not the frozen conductances of one programmed device instance
ALIGNED = False   # --aligned: every read starts at row 0 (what a margin check gives: it reads the row in PROW, also under LOCK)
SA_ROT = False    # --sa-rotate (proposal, 8 Nov): every read connects the devices of each cell to its sense amplifiers in a random
                  # cyclic order (a 3:1 switch per amplifier); the decode undoes it. Spreads each amplifier's mismatch over P/Z/N
K_SENSE = 0.0     # uA per flipped sense-output flip-flop bit between consecutive reads (--k-sense; two flip-flops per bit)


def draw_g(rng, lm):
    gh = np.minimum(np.exp(rng.normal(np.log(4.5), 0.3, lm.shape)), 7.93)
    gl = np.clip(np.exp(rng.normal(np.log(60.0), LRS_SIG, lm.shape)), 30.0, 120.0)
    return np.where(lm, gl, gh)


def interp(tab, lg, seed, x):
    """tab (seeds, P, NW); lg (P,); seed (..., nsa) ints; x (..., nsa) log G -> (..., nsa, NW)"""
    i = np.clip(np.searchsorted(lg, x) - 1, 0, len(lg) - 2)
    f = np.clip((x - lg[i]) / (lg[i + 1] - lg[i]), 0.0, 1.0)[..., None]
    return tab[seed, i] * (1 - f) + tab[seed, i + 1] * f


def read_current(seed, lm, g):
    x = np.log(g)
    cur = np.where(lm[..., None], interp(TL, LGL, seed, x), interp(TH, LGH, seed, x))
    return cur.sum(-2)                                                      # (..., NW)


def traces(rng, enc, seed, W_fixed, G_fixed, X_fixed, n, group, secret):
    if secret == "W" and group == 1:
        W = rng.integers(-1, 2, (n, ROWS, COLS)); G = None
    else:
        W = np.broadcast_to(W_fixed, (n, ROWS, COLS)); G = None if REDRAW else G_fixed
    X = np.broadcast_to(X_fixed, (n, ROWS)) if (secret == "X" and group == 0) else rng.integers(-1, 2, (n, ROWS))
    order = ((np.zeros((n, 1), int) if ALIGNED else rng.integers(0, ROWS, (n, 1))) + np.arange(ROWS)) % ROWS
    Wr = np.take_along_axis(W, order[:, :, None], 1); Xr = np.take_along_axis(X, order, 1)
    lm = M.lrs_mask(Wr, enc)
    if G is None:
        g = draw_g(rng, lm)
    else:
        g = np.take_along_axis(np.broadcast_to(G, (n, ROWS, lm.shape[-1])), order[:, :, None], 1)
    if SA_ROT:   # sense amplifier of device d of column c: ((d + r) mod ndev) * COLS + c, r random per read and column
        nd = lm.shape[-1] // COLS
        r = rng.integers(0, nd, (n, ROWS, 1, COLS))
        d = np.arange(nd)[None, None, :, None]; c = np.arange(COLS)[None, None, None, :]
        sd = seed[(((d + r) % nd) * COLS + c).reshape(n, ROWS, nd * COLS)]
    else:
        sd = seed
    cur = read_current(sd, lm, g)                                           # (n, ROWS, NW)
    if K_SENSE:   # the sense bits are held in two flip-flop stages (q1, arr_sa) from one read to the next
        flips = (lm[:, 1:] != lm[:, :-1]).sum(-1)
        cur[:, 1:, -1] += 2 * K_SENSE * flips
    A = rng.integers(-128, 128, (n, 1)) + np.zeros((n, COLS), int)          # revision 4.7 random offset
    D = rng.integers(0, 1024, (n, COLS))
    for k in range(ROWS):
        upd = (Wr[:, k] != 0) & (Xr[:, k:k + 1] != 0)
        dlt = Wr[:, k] * Xr[:, k:k + 1]
        tr = np.where(upd, M.toggles(A, dlt), 0.0)
        A = np.where(upd, A + dlt, A)
        dd = rng.choice([-1, 1], (n, COLS)); tr += np.where(~upd, M.toggles(D, dd), 0.0); D = np.where(~upd, D + dd, D)
        cur[:, k, -1] += K_DIG * tr.sum(1)
    y = cur + rng.normal(0, SIGMA, cur.shape)
    return y.reshape(n, ROWS * NW)


def tvla(enc, secret, ntr, seed0=7, chunk=500):
    rng = np.random.default_rng(seed0)
    nsa = COLS * M.NDEV[enc]
    seed = rng.integers(0, MM.shape[0], nsa)                                # each sense amplifier: one MC sample, frozen
    W_fixed = rng.integers(-1, 2, (ROWS, COLS)); G_fixed = draw_g(rng, M.lrs_mask(W_fixed, enc)); X_fixed = rng.integers(-1, 2, ROWS)
    w = M.Welch(ROWS * NW)
    done = 0
    while done < ntr:
        n = min(chunk, ntr - done)
        for grp in (0, 1):
            w.add(grp, traces(rng, enc, seed, W_fixed, G_fixed, X_fixed, n, grp, secret))
        done += n
    t = w.t()
    return dict(encoding=enc, secret={"W": "weights", "X": "inputs"}[secret], traces_per_group=ntr,
                max_abs_t=round(float(np.abs(t).max()), 2), leaks=bool(np.abs(t).max() > 4.5))


def main():
    global SIGMA, LRS_SIG, K_SENSE, REDRAW, ALIGNED, SA_ROT
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=int, default=100000)
    ap.add_argument("--sigma", type=float, default=SIGMA)
    ap.add_argument("--only", default="2T2R,1of3")
    ap.add_argument("--lrs-sigma", type=float, default=LRS_SIG)
    ap.add_argument("--k-sense", type=float, default=K_SENSE)
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--aligned", action="store_true")
    ap.add_argument("--sa-rotate", action="store_true")
    ap.add_argument("--secrets", default="W,X")
    ap.add_argument("--out", default=str(ROOT / "results" / "security" / "tvla_circuit.json"))
    a = ap.parse_args(); SIGMA = a.sigma; LRS_SIG = a.lrs_sigma; K_SENSE = a.k_sense; REDRAW = a.redraw; ALIGNED = a.aligned; SA_ROT = a.sa_rotate
    res = dict(note=__doc__.split("\n\n")[0], assumptions=dict(noise_uA_rms_per_window=SIGMA, k_dig_uA=K_DIG, windows_per_read=NW,
               window_ns=250 / NW, lrs_sigma_ln=LRS_SIG, k_sense_uA=K_SENSE, fixed_group_reprogrammed=REDRAW, row_aligned=ALIGNED, sa_rotation=SA_ROT, mismatch_samples=int(MM.shape[0]), source="results/security/sa_transient.npz"), threshold=4.5, cases=[])
    for enc in a.only.split(","):
        for sec in a.secrets.split(","):
            t0 = time.time(); r = tvla(enc, sec, a.traces); r["seconds"] = round(time.time() - t0)
            res["cases"].append(r); print(r, flush=True)
            Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
