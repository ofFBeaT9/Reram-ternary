"""Statistical check of the reduced SKY130 library for mismatch Monte Carlo (11 October 2026).

The reduced library (spice.py) gives results identical to the full corner section for every deterministic run
(periph_sim.py, libcheck). With mismatch on, the same seed gives a different sample: the full library evaluates many more
random-parameter expressions (of devices this design does not use) before reaching ours, so the random stream is shifted.
This script checks that the *distributions* agree: N sense-amplifier trip points at tt 27 C with the full library,
compared with the 200 reduced-library runs stored in results/sky130_chip/periph_sim.json (mean: Welch t test; spread:
ratio of standard deviations with its 95 % interval from the F distribution).
Usage: JOBS=<n> python3 mc_libcheck.py run [N] [op ...]   simulate (needs ngspice, SKY130_NGSPICE_LIB; numpy only)
       python3 mc_libcheck.py stats                       statistics (needs scipy)
Writes results/sky130_chip/mc_libcheck.json"""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results" / "sky130_chip" / "mc_libcheck.json"


def one(args):
    import spice as S
    import periph_sim as P
    S.FULL = True
    return P.part_d_trip("tt", 27, 1.8, args[0], True, args[1])


def run(n, ops):
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    for op in ops:
        seeds = list(range(1001, 1001 + n))           # seeds not used by the reduced runs (1 ... 200)
        with Pool(int(os.environ.get("JOBS", "2"))) as pool:
            vals = pool.map(one, [(op, s) for s in seeds])
        print(op, vals, flush=True)
        res[op] = dict(seeds=[seeds[0], seeds[-1]], full_values_uS=vals)
        OUT.write_text(json.dumps(res, indent=1))


def stats_():
    import numpy as np
    from scipy import stats
    red = json.loads((ROOT / "results" / "sky130_chip" / "periph_sim.json").read_text())["D"]
    res = json.loads(OUT.read_text())
    for op, d in res.items():
        x = np.array([v for v in d["full_values_uS"] if v is not None])
        r = red[f"mc {op}"]
        m2, s2, n2 = r["mean_uS"], r["sigma_uS"], r["valid"]
        m1, s1, n1 = float(x.mean()), float(x.std(ddof=1)), len(x)
        se = np.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
        t = (m1 - m2) / se
        dof = se ** 4 / ((s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1))
        p_mean = float(2 * stats.t.sf(abs(t), dof))
        ratio = s1 / s2
        lo = ratio / np.sqrt(stats.f.ppf(0.975, n1 - 1, n2 - 1))
        hi = ratio / np.sqrt(stats.f.ppf(0.025, n1 - 1, n2 - 1))
        d.update(full_runs=n1, full_mean_uS=round(m1, 3), full_sigma_uS=round(s1, 3), full_min_uS=round(float(x.min()), 3),
                 full_max_uS=round(float(x.max()), 3), reduced_runs=n2, reduced_mean_uS=m2, reduced_sigma_uS=s2,
                 welch_t=round(float(t), 3), p_mean=round(p_mean, 4), sigma_ratio=round(float(ratio), 3),
                 sigma_ratio_95=[round(float(lo), 3), round(float(hi), 3)], agree=bool(p_mean > 0.05 and lo <= 1.0 <= hi))
        print(op, {k: v for k, v in d.items() if k != "full_values_uS"})
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 48, sys.argv[3:] or ["reset", "read", "set"])
    else:
        stats_()
