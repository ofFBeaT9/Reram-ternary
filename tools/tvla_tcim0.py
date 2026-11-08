"""Pre-silicon leakage test (TVLA, fixed-vs-random Welch t) of TCIM0's own model (4 November 2026, security study).

  python3 tools/tvla_tcim0.py [--traces N] [--seed S]      writes results/security/tvla.json

What is modelled, and from where:
- Array: 72 rows x 24 columns. Cell encodings: '2T2R' as built (+1 = P low-resistance, -1 = N, 0 = both high) and
  '1of3' (next-chip proposal: devices P, N, Z, exactly one low-resistance), and '4T4R' (8 November: the complementary
  4T4R cell of the Gemini summaries, one low-resistance device of four; read as 1of3 plus a fourth device that is
  high-resistance for every weight, which is what "exactly one LRS of four" leaves for three values).
- Read power: every bit line of the selected row goes to its sense amplifier (chip/sky130/sim/sa_power.py, SPICE,
  results/security/sa_power.json): a low-resistance device draws the clamped reference current (2.39 uA, independent
  of its conductance from 16 to 150 uS); a high-resistance device draws I_H(G) from the SPICE sweep. Frozen sense-
  amplifier mismatch from the SPICE Monte Carlo (sd 0.111 uA when low-resistance, 0.018 uA when high).
- High-resistance conductance after reset-verify: lognormal, median 4.5 uS (SkyWater's typical value after reset),
  sigma_ln 0.3, cut at the reset-verify level 7.93 uS. ASSUMPTION (SkyWater publishes no distribution).
- Digital accumulation, two models (both ASSUMPTIONS, not from a netlist; reported with and without the term):
  'count': K_DIG uA per accumulator update in a row read (model 1, 4 November);
  'toggle': K_BIT uA per accumulator bit that flips in a row read (model 2, 6 November, after the council review): the
  24 result accumulators (10-bit two's complement, cleared at GO, or from revision 4.7 started at a random offset
  -128 ... 127 that the last row takes off again) and the 24 dummy accumulators (a +/-1 random walk that is never cleared,
  uniform over 0 ... 1023 at the start of a product) are simulated bit by bit, following rtl/tcim_core.sv.
- Start row of a fixed-latency product: drawn from the distribution the RTL produces over the LFSR's 65,535 states,
  assuming GO falls at a uniformly random LFSR state ('rev46': lfsr[6:0] folded once at 72, rows 0-55 twice as likely
  as 56-71; 'rev47': the 16-bit value mod 72, 911 or 910 states per row). Model 1 drew it uniformly.
- Measurement noise: SIGMA uA rms per sample (one sample per row read). ASSUMPTION; the trace count needed scales with
  SIGMA squared.
- Sequencer behaviour as in rtl/tcim_core.sv: zero-skipping (revision 4.2) reads only rows with a non-zero input, in
  increasing order; the fixed-latency mode reads all 72 rows from a start row rotated per product.
- Programming: each device needs a number of pulses = round(n0 * speed_dev * c2c), speed_dev frozen per device
  (lognormal sigma 0.25), c2c per pulse train (lognormal 0.15); n0 = 7.5 set, 1.5 reset (from macro_sim.json: set in
  7-8 pulses, reset in 1-2 at nominal). Variable mode stops when every device verifies; constant mode always runs
  21 + 21 steps with empty pulses as padding. Sample per step = devices pulsed x I_PULSE + noise.
A test fails (leaks) when max |t| > 4.5 over the samples of the trace."""
import argparse, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SA = json.loads((ROOT / "results/security/sa_power.json").read_text())
ROWS, COLS = 72, 24
SIGMA = 5.0          # uA rms measurement noise per sample (assumption)
K_DIG = 0.3          # uA per accumulator update (assumption, model 'count')
K_BIT = 0.15         # uA per flipped accumulator bit (assumption, model 'toggle'; about 2 bits flip per +/-1 update)
I_PULSE = 50.0       # uA per device during a programming pulse (order of VPRG x G; assumption)
G_ = np.array([r["G_uS"] for r in SA["sweep"]]); I_ = np.array([r["I_sa_uA"] for r in SA["sweep"]])
I_LRS = SA["mismatch_tt27"]["LRS_30uS"]["mean_uA"]; SD_LRS = SA["mismatch_tt27"]["LRS_30uS"]["sd_uA"]
SD_HRS = SA["mismatch_tt27"]["HRS_4.5uS"]["sd_uA"]


def lfsr_starts():
    """Start-row histograms over the 65,535 states of the RTL's LFSR (x^16 + x^14 + x^13 + x^11 + 1, seed 0xace1)."""
    v, seen = 0xACE1, []
    for _ in range(65535):
        seen.append(v)
        fb = ((v >> 15) ^ (v >> 13) ^ (v >> 12) ^ (v >> 10)) & 1
        v = ((v << 1) | fb) & 0xFFFF
    a = np.array(seen)
    assert len(set(seen)) == 65535
    lo = a & 127
    h46 = np.bincount(np.where(lo >= ROWS, lo - ROWS, lo), minlength=ROWS)
    h47 = np.bincount(a % ROWS, minlength=ROWS)
    return dict(rev46=h46 / h46.sum(), rev47=h47 / h47.sum(), counts46=h46, counts47=h47)


START = lfsr_starts()


def i_hrs(g):
    return np.interp(g, G_[G_ <= 12], I_[G_ <= 12])


class Welch:
    """Streaming Welch t per sample point."""
    def __init__(self, n):
        self.s = np.zeros((2, n)); self.q = np.zeros((2, n)); self.c = np.zeros((2, n))

    def add(self, grp, x, valid=None):
        v = np.ones_like(x, bool) if valid is None else valid
        self.s[grp] += np.where(v, x, 0).sum(0); self.q[grp] += np.where(v, x * x, 0).sum(0); self.c[grp] += v.sum(0)

    def t(self):
        c = np.maximum(self.c, 2)
        m = self.s / c; var = (self.q - c * m * m) / (c - 1)
        den = np.sqrt(np.maximum(var[0] / c[0] + var[1] / c[1], 0.0))   # a constant trace: rounding may give -0
        with np.errstate(invalid="ignore", divide="ignore"):
            t = np.where(den > 0, (m[0] - m[1]) / den, 0.0)
        return np.nan_to_num(t)


def hrs_g(rng, shape):
    g = np.exp(rng.normal(np.log(4.5), 0.3, shape))
    return np.minimum(g, 7.93)


NDEV = {"2T2R": 2, "1of3": 3, "4T4R": 4}


def chip(rng, enc):
    nsa = COLS * NDEV[enc]
    return dict(mmL=rng.normal(0, SD_LRS, nsa), mmH=rng.normal(0, SD_HRS, nsa), nsa=nsa)


def lrs_mask(w, enc):
    """w: (..., COLS) in {-1,0,1} -> bool (..., nsa) of low-resistance devices, sense amplifiers ordered P, N(, Z)."""
    p, n = w == 1, w == -1
    if enc == "2T2R": return np.concatenate([p, n], axis=-1)
    if enc == "1of3": return np.concatenate([p, n, w == 0], axis=-1)
    return np.concatenate([p, n, w == 0, np.zeros_like(p)], axis=-1)


def row_current(rng, ch, w_rows, g_frozen=None):
    """w_rows: (B, R, COLS) weights of the rows read; returns (B, R) supply current of the sense amplifiers."""
    lm = lrs_mask(w_rows, ch["enc"])
    g = hrs_g(rng, lm.shape) if g_frozen is None else g_frozen
    cur = np.where(lm, I_LRS + ch["mmL"], i_hrs(g) + ch["mmH"])
    return cur.sum(-1)


def toggles(v, d):
    """bits that flip when the 10-bit two's-complement register v becomes v + d"""
    return np.bitwise_count(((v ^ (v + d)) & 1023).astype(np.uint16)).astype(float)


def product_traces(rng, ch, W_fixed, n, group, secret, mode, k_dig, X_fixed=None, G_fixed=None, rot="uniform",
                   digital="count", offset=False):
    """Traces of digital products. secret 'W': group 0 = fixed weights (frozen conductances), 1 = random weights per
    trace (reprogrammed, new conductances); inputs random in both. secret 'X': weights fixed, inputs fixed vs random.
    mode 'zskip' (as built) or 'fixed' (all rows, rotated start). Returns samples (n, 72), valid mask, durations."""
    if secret == "W" and group == 1:
        W = rng.integers(-1, 2, (n, ROWS, COLS)); G = None
    else:
        W = np.broadcast_to(W_fixed, (n, ROWS, COLS)); G = G_fixed
    if secret == "X" and group == 0:
        X = np.broadcast_to(X_fixed, (n, ROWS))
    else:
        X = rng.integers(-1, 2, (n, ROWS))
    nz = X != 0
    if mode.startswith("zskip"):
        order = np.argsort(~nz, axis=1, kind="stable")           # non-zero rows first, increasing
        valid = np.take_along_axis(nz, order, 1)
    else:
        start = (rng.integers(0, ROWS, (n, 1)) if rot == "uniform" else rng.choice(ROWS, (n, 1), p=START[rot]))
        order = (start + np.arange(ROWS)) % ROWS
        valid = np.ones((n, ROWS), bool)
    Wr = np.take_along_axis(W, order[:, :, None], 1)
    Xr = np.take_along_axis(X, order, 1)
    if G is not None:
        G = np.broadcast_to(G, (n, ROWS, ch["nsa"]))
        G = np.take_along_axis(G, order[:, :, None], 1)
    cur = row_current(rng, ch, Wr, G)
    if digital == "toggle":
        # result accumulators: start at 0 (to revision 4.6) or at a common random offset (revision 4.7)
        A = (rng.integers(-128, 128, (n, 1)) if offset else np.zeros((n, 1), int)) + np.zeros((n, COLS), int)
        D = rng.integers(0, 1024, (n, COLS))                       # dummy accumulators: a long random walk
        dig = np.zeros(cur.shape)
        for k in range(ROWS):
            act = valid[:, k:k + 1]                                # zero-skipping: rows not read do nothing
            upd = (Wr[:, k] != 0) & (Xr[:, k:k + 1] != 0) & act
            dlt = Wr[:, k] * Xr[:, k:k + 1]
            tr = np.where(upd, toggles(A, dlt), 0.0)
            A = np.where(upd, A + dlt, A)
            if mode.endswith("+ca"):                               # the dummy of every column that did not update
                dd = rng.choice([-1, 1], (n, COLS))
                dm = act & ~upd
                tr += np.where(dm, toggles(D, dd), 0.0)
                D = np.where(dm, D + dd, D)
            dig[:, k] = k_dig * tr.sum(1)
    elif mode.endswith("+ca"):                     # constant-activity accumulation: every column updates in every row read
        dig = np.full(cur.shape, k_dig * COLS)
    else:
        dig = k_dig * ((Wr != 0) & (Xr[:, :, None] != 0)).sum(-1)
    y = cur + dig + rng.normal(0, SIGMA, cur.shape)
    return y, valid, valid.sum(1)


def tvla_products(rng, enc, mode, secret, ntr, k_dig, chunk=5000, rot="uniform", digital="count", offset=False):
    ch = chip(rng, enc); ch["enc"] = enc
    W_fixed = rng.integers(-1, 2, (ROWS, COLS)); X_fixed = rng.integers(-1, 2, ROWS)
    G_fixed = hrs_g(rng, (ROWS, ch["nsa"]))
    wt = Welch(ROWS); dur = Welch(1)
    for grp in (0, 1):
        left = ntr
        while left:
            b = min(chunk, left); left -= b
            y, v, d = product_traces(rng, ch, W_fixed, b, grp, secret, mode, k_dig, X_fixed, G_fixed, rot, digital, offset)
            wt.add(grp, y, v); dur.add(grp, d[:, None].astype(float) + rng.normal(0, 1e-9, (b, 1)))
    t = wt.t(); td = dur.t()
    return dict(max_abs_t_samples=round(float(np.abs(t).max()), 2), abs_t_duration=round(float(abs(td[0])), 2))


def prog_traces(rng, enc, mode, ntr, speed, W_fixed, group):
    """One row programmed from a random previous content to the target (fixed or random). Samples: one per step of
    the reset phase then the set phase (22 + 22 steps max, padded with NaN after the end in variable mode)."""
    ns = COLS * NDEV[enc]
    prev = rng.integers(-1, 2, (ntr, COLS))
    new = np.broadcast_to(W_fixed, (ntr, COLS)) if group == 0 else rng.integers(-1, 2, (ntr, COLS))
    lp, ln = lrs_mask(prev, enc), lrs_mask(new, enc)
    need_reset = lp & ~ln; need_set = ln & ~lp
    c2c = np.exp(rng.normal(0, 0.15, (ntr, ns)))
    k_r = np.clip(np.rint(1.5 * speed * c2c), 1, 21).astype(int)
    k_s = np.clip(np.rint(7.5 * speed * c2c), 1, 21).astype(int)
    steps = 21
    out = np.full((ntr, 2 * steps), np.nan)
    rr = np.arange(steps)[None, :, None]
    pr = (need_reset[:, None, :] & (rr < k_r[:, None, :])).sum(-1)       # devices pulsed in reset step i
    ps = (need_set[:, None, :] & (rr < k_s[:, None, :])).sum(-1)
    y = np.concatenate([pr, ps], 1) * I_PULSE + rng.normal(0, SIGMA, (ntr, 2 * steps))
    if mode == "constant":
        out = y; dur = np.full(ntr, 2 * steps)
    else:
        nr = np.where(need_reset.any(1), np.where(need_reset, k_r, 0).max(1), 0)
        nsx = np.where(need_set.any(1), np.where(need_set, k_s, 0).max(1), 0)
        for i in range(ntr):                                      # pack: reset steps then set steps, no gaps
            out[i, :nr[i]] = y[i, :nr[i]]; out[i, nr[i]:nr[i] + nsx[i]] = y[i, steps:steps + nsx[i]]
        dur = nr + nsx
    return out, dur


def tvla_prog(rng, enc, mode, ntr):
    ns = COLS * NDEV[enc]
    speed = np.exp(rng.normal(0, 0.25, ns))
    W_fixed = rng.integers(-1, 2, COLS)
    wt = Welch(42); dur = Welch(1)
    for grp in (0, 1):
        y, d = prog_traces(rng, enc, mode, ntr, speed, W_fixed, grp)
        v = ~np.isnan(y)
        wt.add(grp, np.nan_to_num(y), v); dur.add(grp, d[:, None].astype(float) + rng.normal(0, 1e-9, (ntr, 1)))
    return dict(max_abs_t_samples=round(float(np.abs(wt.t()).max()), 2), abs_t_duration=round(float(abs(dur.t()[0])), 2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--traces", type=int, default=20000); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--big", type=int, default=150000)
    ap.add_argument("--sigma", type=float, default=SIGMA, help="measurement noise, uA rms (default 5)")
    ap.add_argument("--only", default=None, help="run only this case label prefix, products only (supplementary runs)")
    ap.add_argument("--out", default="results/security/tvla.json")
    a = ap.parse_args()
    globals()["SIGMA"] = a.sigma
    res = dict(assumptions=dict(noise_uA_rms=SIGMA, k_dig_uA=K_DIG, i_pulse_uA=I_PULSE, hrs_median_uS=4.5, hrs_sigma_ln=0.3,
                                sa_lrs_uA=I_LRS, sa_lrs_mismatch_sd_uA=SD_LRS, sa_hrs_mismatch_sd_uA=SD_HRS),
               threshold=4.5, products=[], programming=[])
    res["start_row_states"] = dict(rev46=START["counts46"].tolist(), rev47=START["counts47"].tolist())
    # model 2 (6 November 2026): start rows as the RTL draws them, accumulator bit flips as the digital term
    cases = [("2T2R", "zskip", "uniform", False, "as built (revision 4.5, zero-skipping since 4.2)"),
             ("2T2R", "fixed+ca", "rev46", False, "revision 4.6: fixed latency, LFSR start row (7 bits folded), constant activity"),
             ("2T2R", "fixed+ca", "rev47", True, "revision 4.7: + start row = LFSR mod 72, random accumulator offset"),
             ("1of3", "fixed+ca", "rev46", False, "revision 4.6 logic + one-of-three cells"),
             ("1of3", "fixed+ca", "rev47", True, "revision 4.7 logic + one-of-three cells (next chip)"),
             ("4T4R", "fixed+ca", "rev47", True, "revision 4.7 logic + 4T4R cells (Gemini's proposal)")]
    for n in (a.traces, a.big):
        for enc, mode, rot, off, label in [c for c in cases if a.only is None or c[4].startswith(a.only)]:
            for secret in ("W", "X"):
                for kd in (0.0, K_BIT):
                    rng = np.random.default_rng(a.seed)
                    r = tvla_products(rng, enc, mode, secret, n, kd, rot=rot, digital="toggle", offset=off)
                    r.update(design=label, encoding=enc, mode=mode, rot=rot, offset=off, digital="toggle", secret={"W": "weights", "X": "inputs"}[secret],
                             k_uA=kd, traces_per_group=n)
                    r["leaks"] = bool(r["max_abs_t_samples"] > 4.5 or r["abs_t_duration"] > 4.5)
                    m = max(r["max_abs_t_samples"], r["abs_t_duration"])
                    # a real leak grows as sqrt(traces): traces per group at which it would reach |t| = 4.5
                    r["traces_to_4.5_est"] = int(n * (4.5 / m) ** 2) if m > 6 else None
                    res["products"].append(r); print(r, flush=True)
    for n in ((a.traces,) if a.only is None else ()):
        for enc, mode, label in [("2T2R", "variable", "as built: stop at verify"), ("2T2R", "constant", "constant pulse count (RTL fix)"),
                                 ("1of3", "constant", "constant pulse count + one-of-three cells (next chip)")]:
            rng = np.random.default_rng(a.seed)
            r = tvla_prog(rng, enc, mode, n)
            r.update(design=label, encoding=enc, mode=mode, traces_per_group=n)
            r["leaks"] = bool(r["max_abs_t_samples"] > 4.5 or r["abs_t_duration"] > 4.5)
            res["programming"].append(r); print(r, flush=True)
    res["assumptions"]["noise_uA_rms"] = SIGMA
    out = ROOT / a.out
    out.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
