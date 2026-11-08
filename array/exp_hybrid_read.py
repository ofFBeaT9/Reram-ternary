"""E8: hybrid digital read (9 October 2026): sign from the pair, zero from the reference.

Reference read (TCIM0 as designed): each device is compared with i_ref; w = [Ip > i_ref] - [In > i_ref].
Hybrid read (proposal): w = 0 if max(Ip, In) <= i_ref, else sign(Ip - In).
The hybrid read adds one comparison per column (Ip against In) to the two reference comparisons.

Why: Bocquet et al. (IEDM 2018) measured that comparing the two devices of a 2T2R pair with each other cuts the
bit error rate from 1.2 % (one device against a reference) to 0.2 %; Laborieux et al. (2020) use the same weight
encoding as TCIM0 and detect zero by timing, with 6.5-18.5 % of zeros misread. The hybrid read keeps the pair
comparison for the sign and uses the reference only to tell zero from non-zero.

Part A, per weight (device level, no wiring): error rate by type, both reads, for the published IHP statistics
(array/tile.py IHP_STATS, LRS3 and LRS1), spread x1 / x2 / x3, and two ASSUMED relaxation scenarios (no
relaxation data exist for this device): "mild" = LRS mean -10 %, HRS mean +30 %, sigmas x1.5; "strong" = LRS mean
-20 %, HRS mean +60 %, sigmas x2 (applied on top of the spread scale). Sampling: 4 million weights of each kind.
The reference is the equal-z reference of the un-relaxed distributions (25.0 uA for LRS3), as programmed into
TCIM0; for each case the reference that minimizes the total error is also found (scan), for both reads.
Part B, full tiles with wiring (as array/exp_digital_mode.py: poor wiring, clamp 50 ohm, offset sigma 2 mV):
wrong weights and inexact matrix-vector products, both reads, same tiles.
Writes results/array_hybrid_read.json.
"""
import sys, json
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tile import Tile, TileConfig, IHP_STATS, reference_current   # noqa: E402

N = 4_000_000
RELAX = {"none": (1.0, 1.0, 1.0), "mild": (0.90, 1.30, 1.5), "strong": (0.80, 1.60, 2.0)}


def sample(rng, state, scale, relax, n):
    mu, sg = IHP_STATS[state]
    lrs_f, hrs_f, s_f = RELAX[relax]
    mu = mu * (hrs_f if state == "HRS" else lrs_f)
    return np.maximum(rng.normal(mu, sg * scale * s_f, n), 0.05)


def reads(ip, i_n, iref):
    ref = (ip > iref).astype(np.int8) - (i_n > iref).astype(np.int8)
    hyb = np.where(np.maximum(ip, i_n) > iref, np.where(ip > i_n, 1, -1), 0).astype(np.int8)
    return ref, hyb


def part_a():
    rng = np.random.default_rng(2026)
    out = {}
    for lrs in ("LRS3", "LRS1"):
        iref0 = reference_current(lrs) * 1e6
        for scale in (1.0, 2.0, 3.0):
            for relax in RELAX:
                # +1 weights (by symmetry -1 behaves the same) and 0 weights
                lp, hn = sample(rng, lrs, scale, relax, N), sample(rng, "HRS", scale, relax, N)
                h1, h2 = sample(rng, "HRS", scale, relax, N), sample(rng, "HRS", scale, relax, N)

                def errs(iref):
                    rp, hp = reads(lp, hn, iref); r0, h0 = reads(h1, h2, iref)
                    d = {}
                    for name, a, b in (("reference", rp, r0), ("hybrid", hp, h0)):
                        d[name] = dict(nonzero_read_as_zero=float((a == 0).mean()), sign_flipped=float((a == -1).mean()),
                                       zero_read_as_nonzero=float((b != 0).mean()))
                        # weights equally likely +1, 0, -1
                        d[name]["total"] = (2 * (d[name]["nonzero_read_as_zero"] + d[name]["sign_flipped"]) + d[name]["zero_read_as_nonzero"]) / 3
                    return d
                e = errs(iref0)
                scan = [(float(r), errs(r)) for r in np.arange(6.0, IHP_STATS[lrs][0] + 0.01, 0.5)]
                best = {}
                for name in ("reference", "hybrid"):
                    r_best, d_best = min(scan, key=lambda x: x[1][name]["total"])
                    best[name] = dict(iref_uA=r_best, **d_best[name])
                key = f"{lrs} spread x{scale:g} relaxation {relax}"
                out[key] = dict(iref_uA=round(iref0, 2), at_design_reference=e, best_reference=best)
                print(key, json.dumps(e), json.dumps(best), flush=True)
    return out


def part_b():
    rng = np.random.default_rng(11)
    out = {}
    for lrs, scale, vos, n_tiles in (("LRS3", 2.0, 2e-3, 60), ("LRS3", 3.0, 2e-3, 60), ("LRS1", 1.0, 2e-3, 60), ("LRS1", 2.0, 2e-3, 60)):
        tot = dict(reference=[0, 0], hybrid=[0, 0]); nw = 0; npd = 0
        for _ in range(n_tiles):
            cfg = TileConfig(lrs=lrs, spread_scale=scale, sigma_vos=vos, bl_metal="M2-5", bl_width_um=0.4, sl_metal="M2-5", sl_width_um=1.0, r_clamp=50.0)
            t = Tile(cfg, rng)
            W = rng.choice((-1, 0, 1), size=(cfg.rows, cfg.cols)); t.program(W)
            iref = reference_current(lrs)
            Wr = np.array([t.digital_read_row(r, iref)[0] for r in range(cfg.rows)])
            Wh = np.array([t.hybrid_read_row(r, iref)[0] for r in range(cfg.rows)])
            xs = rng.choice((-1, 0, 1), size=(10, cfg.rows))
            for name, M in (("reference", Wr), ("hybrid", Wh)):
                tot[name][0] += int((M != W).sum())
                tot[name][1] += int(((xs @ M) != (xs @ W)).any(axis=1).sum())
            nw += W.size; npd += len(xs)
        key = f"{lrs} spread x{scale:g} offset {vos*1e3:g} mV"
        out[key] = dict(weights=nw, products=npd, **{f"{k}_wrong_weights": v[0] for k, v in tot.items()},
                        **{f"{k}_inexact_products": v[1] for k, v in tot.items()})
        print(key, json.dumps(out[key]), flush=True)
    return out


if __name__ == "__main__":
    res = dict(note="relaxation scenarios are assumptions, not data; statistics: Perez et al. 2021 (IHP 4-kbit, read right after programming)",
               relaxation_scenarios={k: dict(lrs_mean_factor=v[0], hrs_mean_factor=v[1], sigma_factor=v[2]) for k, v in RELAX.items()},
               part_a=part_a(), part_b=part_b())
    json.dump(res, open(__file__.rsplit('/', 2)[0] + "/results/array_hybrid_read.json", "w"), indent=1)
