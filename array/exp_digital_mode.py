"""E2: digital (row-by-row, reference-compare) read mode: weight error rate and product correctness."""
import sys, json, math
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tile import *

def tail(z): return 0.5 * math.erfc(z / math.sqrt(2))

out = {}
print("Analytic device misread probability at the equal-z reference (Gaussian fits):")
for lrs in ("LRS1", "LRS2", "LRS3"):
    for scale in (1.0, 1.5, 2.0, 3.0):
        (m0, s0), (m1, s1) = IHP_STATS["HRS"], IHP_STATS[lrs]
        z = (m1 - m0) / ((s0 + s1) * scale)
        out[f"analytic_{lrs}_x{scale:g}"] = dict(z=z, p=tail(z), iref_uA=m0 + (m1 - m0) * s0 / (s0 + s1))
        print(f"  {lrs}, spread x{scale:g}: z = {z:5.2f}, P(misread) = {tail(z):.1e}, reference {m0 + (m1-m0)*s0/(s0+s1):.1f} uA")

print("Monte Carlo over full tiles (wiring A, clamp 50 ohm = pessimistic periphery), 72 x 24 weights each:")
rng = np.random.default_rng(11)
for lrs, scale, vos, n_tiles in (("LRS3", 1.0, 0.0, 60), ("LRS3", 2.0, 2e-3, 60), ("LRS3", 3.0, 2e-3, 60), ("LRS1", 1.0, 0.0, 60), ("LRS1", 2.0, 2e-3, 60)):
    werr = 0; ntot = 0; prod_wrong = 0; nprod = 0
    for t in range(n_tiles):
        cfg = TileConfig(lrs=lrs, spread_scale=scale, sigma_vos=vos, bl_metal="M2-5", bl_width_um=0.4, sl_metal="M2-5", sl_width_um=1.0, r_clamp=50.0)
        tile = Tile(cfg, rng)
        W = rng.choice((-1, 0, 1), size=(cfg.rows, cfg.cols)); tile.program(W)
        iref = reference_current(lrs)
        Wr = np.array([tile.digital_read_row(r, iref)[0] for r in range(cfg.rows)])
        werr += int((Wr != W).sum()); ntot += W.size
        for _ in range(10):
            x = rng.choice((-1, 0, 1), size=cfg.rows)
            prod_wrong += int((x @ Wr != x @ W).any()); nprod += 1
    key = f"mc_{lrs}_x{scale:g}_vos{vos*1e3:g}mV"
    out[key] = dict(weights=ntot, weight_errors=werr, products=nprod, products_with_any_error=prod_wrong)
    print(f"  {lrs}, spread x{scale:g}, clamp offset sigma {vos*1e3:g} mV: {werr} wrong weights in {ntot}; {prod_wrong} of {nprod} matrix-vector products not exact")
json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/array_digital_mode.json", "w"), indent=1)
