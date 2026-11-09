"""A sparsity-recovery attack on the array read current (8 November 2026; paper study).

Strongest attacker for this leak: it knows which row each read belongs to (worst case: the start row is known, e.g. with
NOSHUF or a cracked LFSR), averages N reads of every row, and estimates each row's number of zero weights from its mean
supply current with a linear model calibrated on a second chip of the same design (profiling). The array read current is
the transistor-level template model of tools/tvla_circuit.py (sense-amplifier waveforms with frozen mismatch, device
spreads, SIGMA uA noise per window). Success: every one of the 72 rows' zero count recovered exactly.
Reported for 2T2R and the one-of-three 3T3R cell: the correlation between true and estimated zero counts and the
fraction of rows recovered exactly, against the reads per row N. Writes results/security/attack_sparsity.json."""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tvla_circuit as C   # noqa: E402

ROWS, COLS = C.ROWS, C.COLS


def chip_reads(rng, enc, W, n, windows=False):
    """mean read current (sum over windows, or every window: (ROWS, NW)) of every row of matrix W over n reads: (ROWS,)"""
    nsa = COLS * C.M.NDEV[enc]
    seed = rng.integers(0, C.MM.shape[0], nsa)
    lm = C.M.lrs_mask(W, enc)                                # (ROWS, nsa)
    g = C.draw_g(rng, lm)                                    # programmed once: frozen conductances
    cur = C.read_current(seed, lm, g)                        # (ROWS, NW) noiseless
    if windows:
        return cur + rng.normal(0, C.SIGMA, (n, ROWS, C.NW)).mean(0)
    noise = rng.normal(0, C.SIGMA * np.sqrt(C.NW), (n, ROWS)).mean(0)   # n reads, SIGMA per window
    return cur.sum(-1) + noise


def run_multi(enc, ns=(1, 16, 256, 4096), chips=20, prof=8, seed0=13):
    """second attacker: least squares of the zero count on all five windows of the read (not only their sum),
    profiled on `prof` devices of known weights"""
    rng = np.random.default_rng(seed0)
    out = []
    for n in ns:
        corr, exact = [], []
        for _ in range(chips):
            Xp, yp = [], []
            for _ in range(prof):
                Wp = rng.integers(-1, 2, (ROWS, COLS)); Xp.append(chip_reads(rng, enc, Wp, 4096, True)); yp.append((Wp == 0).sum(1))
            Xp = np.concatenate(Xp); yp = np.concatenate(yp)
            A = np.c_[np.ones(len(Xp)), Xp]; beta = np.linalg.lstsq(A, yp, rcond=None)[0]
            W = rng.integers(-1, 2, (ROWS, COLS)); z = (W == 0).sum(1)
            est = np.clip(np.rint(np.c_[np.ones(ROWS), chip_reads(rng, enc, W, n, True)] @ beta), 0, COLS)
            corr.append(float(np.corrcoef(z, est)[0, 1]) if np.std(est) > 0 else 0.0)
            exact.append(float((est == z).mean()))
        out.append(dict(reads_per_row=n, corr_mean=round(float(np.mean(corr)), 3), rows_exact_mean=round(float(np.mean(exact)), 3)))
        print(enc, "all windows", out[-1], flush=True)
    return out


def run(enc, ns=(1, 4, 16, 64, 256, 1024, 4096), chips=20, seed0=11):
    rng = np.random.default_rng(seed0)
    out = []
    for n in ns:
        corr, exact = [], []
        for _ in range(chips):
            # profiling chip: known weights, fit current = a + b * zeros
            Wp = rng.integers(-1, 2, (ROWS, COLS)); zp = (Wp == 0).sum(1)
            ip = chip_reads(rng, enc, Wp, 4096)
            b, a = np.polyfit(zp, ip, 1) if np.ptp(zp) > 0 else (0.0, ip.mean())
            # victim chip
            W = rng.integers(-1, 2, (ROWS, COLS)); z = (W == 0).sum(1)
            iv = chip_reads(rng, enc, W, n)
            est = np.clip(np.rint((iv - a) / b), 0, COLS) if abs(b) > 1e-9 else np.full(ROWS, np.rint(zp.mean()))
            corr.append(float(np.corrcoef(z, est)[0, 1]) if np.std(est) > 0 else 0.0)
            exact.append(float((est == z).mean()))
        out.append(dict(reads_per_row=n, corr_mean=round(float(np.mean(corr)), 3), rows_exact_mean=round(float(np.mean(exact)), 3),
                        profile_slope_uA_per_zero=round(float(b), 3)))
        print(enc, out[-1], flush=True)
    return out


if __name__ == "__main__":
    res = dict(note=__doc__.split("\n\n")[0], sigma_uA_per_window=C.SIGMA, windows_per_read=C.NW, chips_per_point=20,
               note_chance="a guess of the most likely count (8 zeros of 24) is right for about 17 % of rows (Binomial(24, 1/3))",
               results={enc: run(enc) for enc in ("2T2R", "1of3")},
               note_all_windows="second attacker: least squares on all five 50 ns windows, profiled on 8 devices",
               results_all_windows={enc: run_multi(enc) for enc in ("2T2R", "1of3")})
    (ROOT / "results" / "security" / "attack_sparsity.json").write_text(json.dumps(res, indent=1))
