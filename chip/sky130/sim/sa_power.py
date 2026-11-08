"""Supply current of one sense amplifier during a read, by device conductance (4 November 2026, security study).

The power side channel of a read: every bit line of the selected row goes to its sense amplifier; the current each
sense amplifier draws from its 1.8 V supply depends on the device it reads. This deck is part D of periph_sim.py
(reference bias, sense amplifier, column switch, the selected cell with its select transistor, the 71 unselected
cells lumped) with the sense amplifier on its own supply source, so that its current is measured alone.

  nominal:  tt, 27 C, read reference; DC sweep of the device conductance 0.3 ... 150 uS
  corners:  ss -40 C, ff 125 C at 4.5 and 30 uS
  mismatch: 100 local-mismatch samples (tt_mm, 27 C) at 4.5 uS (HRS) and 30 uS (LRS): the frozen sense-amplifier-to-
            sense-amplifier spread an attacker averaging many traces would see
Writes results/security/sa_power.json."""
import json, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S  # noqa: E402
import periph_sim as PS  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "security" / "sa_power.json"


def deck(corner, temp, mm=False):
    d = PS.sa_deck(corner, temp, 1.8, "read", mm)
    # the sense amplifier alone on its own 1.8 V source
    return d.replace("Xsa sa out vbp vcl vccd 0 sa", "Vsa vsa 0 1.8\nXsa sa out vbp vcl vsa 0 sa")


def sweep(corner, temp):
    d = deck(corner, temp) + """Vgc gc 0 10e-6
.control
dc Vgc 0.3e-6 150e-6 0.1e-6
wrdata out.txt i(Vsa) v(out) v(bl)
.endc
.end
"""
    a, _ = S.run(d)
    return a[:, 0], -a[:, 1], a[:, 3], a[:, 5]


def point(args):
    corner, temp, g, mm, seed = args
    d = deck(corner, temp, mm) + f"""Vgc gc 0 {g}
.control
op
wrdata out.txt i(Vsa) v(out)
.endc
.end
"""
    a, _ = S.run(d, seed=seed)
    return float(-a[0, 1]), float(a[0, 3])


def main():
    g, isa, out, vbl = sweep("tt", 27)
    pick = [0.3e-6, 1e-6, 2e-6, 4.5e-6, 8e-6, 12e-6, 16e-6, 20e-6, 27.4e-6, 30e-6, 50e-6, 80e-6, 120e-6, 150e-6]
    tab = []
    for p in pick:
        k = int(np.argmin(abs(g - p)))
        tab.append(dict(G_uS=round(g[k] * 1e6, 2), I_sa_uA=round(isa[k] * 1e6, 3), out_V=round(out[k], 3), bl_V=round(vbl[k], 4)))
    res = dict(note="tt 27 C, read reference; I_sa = current from the sense amplifier's own 1.8 V source", sweep=tab)
    with Pool(2) as pool:
        cor = pool.map(point, [(c, t, gg, False, None) for c, t in (("tt", 27), ("ss", -40), ("ff", 125)) for gg in (4.5e-6, 30e-6)])
        res["corners"] = [dict(corner=c, temp=t, G_uS=gg * 1e6, I_sa_uA=round(v[0] * 1e6, 3), out_V=round(v[1], 3))
                          for (c, t, gg), v in zip([(c, t, gg) for c, t in (("tt", 27), ("ss", -40), ("ff", 125)) for gg in (4.5e-6, 30e-6)], cor)]
        mc = {}
        for name, gg in (("HRS_4.5uS", 4.5e-6), ("LRS_30uS", 30e-6), ("LRS_120uS", 120e-6)):
            v = pool.map(point, [("tt", 27, gg, True, 1000 + s) for s in range(100)])
            i = np.array([x[0] for x in v]) * 1e6
            mc[name] = dict(mean_uA=round(float(i.mean()), 4), sd_uA=round(float(i.std(ddof=1)), 4),
                            min_uA=round(float(i.min()), 4), max_uA=round(float(i.max()), 4), samples=[round(float(x), 4) for x in i])
        res["mismatch_tt27"] = mc
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "mismatch_tt27"}, indent=1))
    print({k: {kk: vv for kk, vv in v.items() if kk != "samples"} for k, v in res["mismatch_tt27"].items()})


if __name__ == "__main__":
    main()
