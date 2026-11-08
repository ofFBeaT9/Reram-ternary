"""E1: accuracy of the analog (current-summing) mode for one 72 x 24 tile, with line resistance and device spread."""
import sys, json, itertools, time
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tile import *

WIRING = {
    "A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end": dict(bl_metal="M2-5", bl_width_um=0.4, sl_metal="M2-5", sl_width_um=1.0, both_ends=False),
    "B: BL TopMetal1, SL Metal2-5 1um, one end":      dict(bl_metal="TM1", bl_width_um=1.64, sl_metal="M2-5", sl_width_um=1.0, both_ends=False),
    "C: BL TopMetal1, SL TopMetal1, one end":         dict(bl_metal="TM1", bl_width_um=1.64, sl_metal="TM1", sl_width_um=1.64, both_ends=False),
    "D: BL TopMetal1, SL TopMetal1, both ends":       dict(bl_metal="TM1", bl_width_um=1.64, sl_metal="TM1", sl_width_um=1.64, both_ends=True),
    "E: ideal wires":                                 dict(bl_metal="TM1", bl_width_um=1e6, sl_metal="TM1", sl_width_um=1e6, both_ends=False, r_clamp=1e-3),
}

def run(lrs, wiring, rpr, spread, n_tiles=6, n_vec=100, n_cal=48, seed=0, vos=0.0, gain=0.0, r_clamp=1.0):
    rng = np.random.default_rng(seed)
    err_raw = []; err_cal = []
    for t in range(n_tiles):
        kw = dict(WIRING[wiring]); kw.setdefault('r_clamp', r_clamp)
        cfg = TileConfig(lrs=lrs, spread_scale=spread, sigma_vos=vos, sigma_gain=gain, **kw)
        tile = Tile(cfg, rng)
        tile.program(rng.choice((-1, 0, 1), size=(cfg.rows, cfg.cols), p=(1/3, 1/3, 1/3)))
        g, o = tile.calibrate(n_cal, rows_per_read=rpr)
        for _ in range(n_vec):
            x = rng.choice((-1, 0, 1), size=cfg.rows, p=(1/3, 1/3, 1/3))
            ex = tile.exact(x)
            raw, _, _ = tile.analog_raw(x, rpr)
            y0 = raw / tile.ideal_step()
            y1 = (y0 - o) / g
            err_raw.append(y0 - ex); err_cal.append(y1 - ex)
    def stats(e):
        e = np.concatenate(e); r = np.rint(e)
        return dict(rms=float(np.sqrt(np.mean(e**2))), p_exact=float(np.mean(r == 0)), p_within1=float(np.mean(np.abs(r) <= 1)), max_abs=float(np.max(np.abs(e))))
    return dict(raw=stats(err_raw), cal=stats(err_cal))

if __name__ == "__main__":
    out = {}; t0 = time.time()
    for lrs in ("LRS3", "LRS1"):
        for wiring in WIRING:
            for rpr in (None, 24):
                for spread in (1.0, 2.0):
                    key = f"{lrs} | {wiring} | rows/read {rpr or 72} | spread x{spread:g}"
                    out[key] = run(lrs, wiring, rpr, spread)
                    r = out[key]
                    print(f"{key}: raw rms {r['raw']['rms']:.2f} exact {100*r['raw']['p_exact']:.0f}% | calibrated rms {r['cal']['rms']:.2f} exact {100*r['cal']['p_exact']:.0f}% within1 {100*r['cal']['p_within1']:.0f}% max {r['cal']['max_abs']:.1f}", flush=True)
    # clamp input resistance on the best wiring
    for rc in (0.2, 1.0, 5.0, 20.0, 50.0):
        key = f"LRS3 | D | rows/read 72 | spread x1 | clamp input resistance {rc:g} ohm"
        out[key] = run("LRS3", "D: BL TopMetal1, SL TopMetal1, both ends", None, 1.0, r_clamp=rc)
        r = out[key]; print(f"{key}: raw rms {r['raw']['rms']:.2f} exact {100*r['raw']['p_exact']:.0f}% | calibrated rms {r['cal']['rms']:.2f} exact {100*r['cal']['p_exact']:.0f}% within1 {100*r['cal']['p_within1']:.0f}%", flush=True)
    # periphery mismatch on the best wiring
    for vos, gain in ((0.5e-3, 0.0), (2e-3, 0.0), (0.0, 0.01), (2e-3, 0.01)):
        key = f"LRS3 | D | rows/read 72 | spread x1 | clamp offset {vos*1e3:g} mV, mirror gain error {gain*100:g}%"
        out[key] = run("LRS3", "D: BL TopMetal1, SL TopMetal1, both ends", None, 1.0, vos=vos, gain=gain)
        r = out[key]; print(f"{key}: raw rms {r['raw']['rms']:.2f} | calibrated rms {r['cal']['rms']:.2f} exact {100*r['cal']['p_exact']:.0f}% within1 {100*r['cal']['p_within1']:.0f}%", flush=True)
    json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/array_analog_error.json", "w"), indent=1)
    print("done in %.0f s" % (time.time() - t0))
