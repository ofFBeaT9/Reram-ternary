"""Cross-check of the three implementations of the ReRAM model on the cell alone (no transistor):
Python reference, ngspice behavioural subcircuit, Verilog-A compiled for Gnucap.

A: quasi-static ramp 0 -> 0.9 V at 0.6 V/s from the 1.8 nm gap: voltage at which the gap passes 1.25 nm.
B: gap after one 1 us pulse of +1.0 V from 1.8 nm.
C: step to +1.1 V (10 ns edge) from 1.8 nm: time at which the gap passes 1.0 nm.
D: step to -1.0 V (10 ns edge) from 0.6 nm: time at which the gap passes 1.2 nm.
Exit status 1 unless all three solvers agree within 1 mV (A), 2 pm (B) and 2 % (C, D)."""
import json, re, subprocess, sys
from dataclasses import replace
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model")); sys.path.insert(0, str(ROOT / "circuits" / "gnucap"))
from reram_stanford import IHP_PUBLISHED, step_gap
CAL = replace(IHP_PUBLISHED, Ea=1.0, v0=2.79)


def _tcross(g0, amp, level, rising, tmax=3e-6, dt=0.02e-9, edge=10e-9):
    g, t = g0, 0.0
    while t < tmax:
        v = amp * min(1.0, (t + dt / 2) / edge)
        gn = step_gap(CAL, v, g, dt, 0.05e-9)
        if (not rising and gn < level <= g) or (rising and gn > level >= g):
            return t + dt * (g - level) / (g - gn)
        g, t = gn, t + dt
    return float("nan")


def python_model():
    g, dt, rate = 1.8e-9, 1e-4, 0.6
    v_cross, v_prev, g_prev = None, 0.0, g
    for k in range(1, int(0.9 / rate / dt) + 1):
        v = rate * dt * k
        g = step_gap(CAL, v, g, dt, 0.725e-9)
        if v_cross is None and g < 1.25e-9:
            v_cross = v_prev + (v - v_prev) * (g_prev - 1.25e-9) / (g_prev - g)
        v_prev, g_prev = v, g
    g1 = step_gap(CAL, 1.0, 1.8e-9, 1e-6, 0.05e-9) * 1e9
    return v_cross, g1, _tcross(1.8e-9, 1.1, 1.0e-9, False) * 1e9, _tcross(0.6e-9, -1.0, 1.2e-9, True) * 1e9


def ngspice():
    d = ROOT / "circuits" / "ngspice"
    out = {}
    for deck in ("tb_cell_ramp.cir", "tb_cell_pulse.cir", "tb_cell_step.cir"):
        r = subprocess.run(["ngspice", "-b", deck], cwd=d, capture_output=True, text=True, timeout=900)
        for m in re.finditer(r"^(\w+)\s*=\s*([-+0-9.eE]+)", r.stdout + r.stderr, re.M):
            out[m.group(1)] = float(m.group(2))
    return out["v_half"], out["g1"], out["t_set"] * 1e9, out["t_reset"] * 1e9


def gnucap():
    import gnucap_run as g
    pre = f"load mgsim\nload {g.RERAM_SO}\nspice\n"
    t = g.run(pre + "Vte te 0 pwl(0 0 1.5 0.9 3.0 0)\n.verilog\n"
              "reram_stanford_ihp #(.gap_ini(1.8), .gap_min(0.725)) x1(te, \\0 , gap);\n"
              "print tran v(te) v(gap)\ntran 0 1.5 1m 0.1m\n")[0]["data"]
    k = int(np.where(t[:, 2] < 1.25)[0][0])
    v_cross = t[k - 1, 1] + (t[k, 1] - t[k - 1, 1]) * (t[k - 1, 2] - 1.25) / (t[k - 1, 2] - t[k, 2])
    p = g.run(pre + "Vte te 0 pwl(0 0 10n 1.0 1.01u 1.0 1.02u 0 1.5u 0)\n.verilog\n"
              "reram_stanford_ihp #(.gap_ini(1.8), .gap_min(0.05)) x1(te, \\0 , gap);\n"
              "print tran v(gap)\ntran 0 1.5u 10n 0.5n\n")[0]["data"]
    q = g.run(pre + "Va a 0 pwl(0 0 10n 1.1)\nVb b 0 pwl(0 0 10n -1.0)\n.verilog\n"
              "reram_stanford_ihp #(.gap_ini(1.8), .gap_min(0.05)) x1(a, \\0 , ga);\n"
              "reram_stanford_ihp #(.gap_ini(0.6), .gap_min(0.05)) x2(b, \\0 , gb);\n"
              "print tran v(ga) v(gb)\ntran 0 700n 0.2n 0.1n\n")[0]["data"]
    def cross(col, level, rising):
        y = q[:, col]
        k = int(np.where(y > level)[0][0]) if rising else int(np.where(y < level)[0][0])
        return (q[k - 1, 0] + (q[k, 0] - q[k - 1, 0]) * (level - y[k - 1]) / (y[k] - y[k - 1])) * 1e9
    return float(v_cross), float(p[-1, 1]), float(cross(1, 1.0, False)), float(cross(2, 1.2, True))


if __name__ == "__main__":
    res = {}
    for name, fn in (("python", python_model), ("ngspice", ngspice), ("gnucap", gnucap)):
        try:
            v, g1, ts, tr = fn()
            res[name] = dict(A_v_cross_V=round(float(v), 5), B_gap_nm=round(float(g1), 4), C_t_set_ns=round(float(ts), 2), D_t_reset_ns=round(float(tr), 2))
        except Exception as e:                                  # a missing tool is reported, not hidden
            res[name] = dict(error=str(e)[:300])
        print(name, res[name])
    ok = [r for r in res.values() if "error" not in r]
    sp = lambda k: max(r[k] for r in ok) - min(r[k] for r in ok)
    res["spread"] = dict(solvers=len(ok), A_mV=round(sp("A_v_cross_V") * 1e3, 3), B_pm=round(sp("B_gap_nm") * 1e3, 2),
                         C_percent=round(100 * sp("C_t_set_ns") / ok[0]["C_t_set_ns"], 2), D_percent=round(100 * sp("D_t_reset_ns") / ok[0]["D_t_reset_ns"], 2))
    print(res["spread"])
    (ROOT / "results" / "model_three_solvers.json").write_text(json.dumps(res, indent=1))
    s_ = res["spread"]
    sys.exit(0 if len(ok) == 3 and s_["A_mV"] < 1 and s_["B_pm"] < 2 and s_["C_percent"] < 2 and s_["D_percent"] < 2 else 1)
