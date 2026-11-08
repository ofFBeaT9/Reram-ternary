"""Device-model drift of a ReRAM device under a simulated voltage waveform (8 November 2026; used by empty_pulse.py, H6).

The gap of the device is advanced over the waveform with the SkyWater-fitted model (model/sky130_port.P; the reset
direction F times faster, F from results/fit_skywater.json, as macro_sim.py does), at most 2 pm per step. The change of
the gap is accumulated in its own variable (a gap of ~1 nm cannot absorb increments of ~1e-23 m in float64), so a small
drift is resolved instead of lost. Three conditions: nominal (27 C, F of the fit at k = 1), hot (85 C device
temperature, same F) and a fast-reset cell (27 C, F at k = 4, the largest of the fit). Returned: the relative change of the
0.2 V read conductance after one waveform, signed."""
import json, math, sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "model"))
from sky130_port import P, GMIN, GMAX     # noqa: E402
from reram_stanford import current, gap_rate  # noqa: E402

LOGF = {r["k"]: r["log10F"] for r in json.loads((ROOT / "results" / "fit_skywater.json").read_text())["cases"]["W 1.0 um, criteria 6/20"]["rows"]}
CONDITIONS = {"nominal_27C": (P, 10 ** LOGF[1.0]), "hot_85C": (replace(P, T0=358.15), 10 ** LOGF[1.0]),
              "fast_reset_cell": (P, 10 ** max(LOGF.values()))}
VREAD = 0.2


def gap_for(G):
    """Gap at which the device conducts G at the read; None if G is outside the model's range (GMIN ... GMAX)."""
    g = P.g0 * math.log(P.I0 * math.sinh(VREAD / P.V0) / (VREAD * G))
    return g if GMIN <= g <= GMAX else None


def g_at(g, p=P):
    return float(current(p, VREAD, g)) / VREAD


def drift(t, v, g0, cond):
    """Relative change of the read conductance after the waveform v(t), under one condition of CONDITIONS."""
    p, F = CONDITIONS[cond]
    pr = replace(p, v0=p.v0 * F)
    dg = 0.0
    for k in range(1, len(t)):
        dt, vv = t[k] - t[k - 1], 0.5 * (v[k] + v[k - 1])
        pp = p if vv >= 0 else pr
        h = 0.0
        while h < dt:
            r = float(gap_rate(pp, vv, g0 + dg))
            if r == 0.0:
                break
            s = min(dt - h, 2e-12 / abs(r))
            dg += r * s; h += s
            if not GMIN <= g0 + dg <= GMAX:
                dg = min(max(g0 + dg, GMIN), GMAX) - g0; break
    # G is proportional to exp(-g/g0) at the read: relative change without cancellation
    return math.expm1(-dg / P.g0)
