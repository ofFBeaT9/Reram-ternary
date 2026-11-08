"""Independent re-derivations of key results (audit of revision 3). Each check uses a second method that shares
no code with the model it checks. Run:  python3 tests/test_independent.py   (exit status 1 on any failure)"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "array")); sys.path.insert(0, str(ROOT / "model"))
FAIL = []
LOG = []


def check(name, ok, detail):
    print(("PASS  " if ok else "FAIL  ") + name + ": " + detail)
    LOG.append(dict(check=name, passed=bool(ok), detail=detail))
    if not ok:
        FAIL.append(name)


# ------------------------------------------------------------------ 1. tile solver against element-by-element stamping
def dense_column(gp, gn, gbl, gsl, gend, v_p, v_n, both_ends):
    """One column: nodes P_i, N_i, S_i. Every resistor is stamped individually into a dense matrix."""
    R = len(gp); n = 3 * R
    A = np.zeros((n, n)); b = np.zeros(n)
    P = lambda i: 3 * i; N = lambda i: 3 * i + 1; S = lambda i: 3 * i + 2

    def res(a, c, g):                      # resistor between nodes a and c
        A[a, a] += g; A[c, c] += g; A[a, c] -= g; A[c, a] -= g

    def to_source(a, g, v):                # resistor from node a to an ideal source v
        A[a, a] += g; b[a] += g * v

    for i in range(R):
        res(P(i), S(i), gp[i]); res(N(i), S(i), gn[i])
        if i + 1 < R:
            res(P(i), P(i + 1), gbl); res(N(i), N(i + 1), gbl); res(S(i), S(i + 1), gsl)
    ends = [0, R - 1] if both_ends else [0]
    for e in ends:
        to_source(P(e), gend, v_p); to_source(N(e), gend, v_n); to_source(S(e), gsl, 0.0)
    v = np.linalg.solve(A, b)
    ip = sum(gend * (v_p - v[P(e)]) for e in ends); i_n = sum(gend * (v_n - v[N(e)]) for e in ends)
    return ip, i_n


def test_tile():
    from tile import Tile, TileConfig
    rng = np.random.default_rng(2024)
    worst = 0.0
    for case in range(8):
        cfg = TileConfig(bl_metal=("TM1", "M2-5")[case % 2], bl_width_um=(1.64, 0.4)[case % 2], sl_metal="M2-5", sl_width_um=1.0,
                         both_ends=bool(case // 4), r_clamp=(1.0, 50.0)[(case // 2) % 2], sigma_vos=2e-3, spread_scale=1.5)
        t = Tile(cfg, rng); t.program(rng.choice((-1, 0, 1), size=(cfg.rows, cfg.cols)))
        act = rng.random(cfg.rows) < 0.6
        Ip, In = t.read_currents(act)
        for c in (0, 7, 23):
            ip, i_n = dense_column(t.Gp[:, c] * act, t.Gn[:, c] * act, t.g_bl, t.g_sl, t.g_end,
                                   cfg.v_read + t.vos[0, c], cfg.v_read + t.vos[1, c], cfg.both_ends)
            worst = max(worst, abs(ip - Ip[c]) / abs(ip), abs(i_n - In[c]) / abs(i_n))
    check("tile solver equals element-by-element nodal analysis", worst < 1e-9, f"largest relative difference {worst:.1e} over 8 configurations")


# ------------------------------------------------------------------ 2. analog error against the closed-form variance
def test_analog_rms():
    sl, sh, mu = 1.55, 1.85, 43.59 - 2.85
    # active rows: input non-zero (2/3 of 72). Per active row: weight +-1 (2/3): one LRS and one HRS device; weight 0 (1/3): two HRS devices
    var = 72 * (2 / 3) * ((2 / 3) * (sl ** 2 + sh ** 2) + (1 / 3) * 2 * sh ** 2)
    pred = math.sqrt(var) / mu
    sim = json.loads((ROOT / "results" / "array_analog_error.json").read_text())["LRS3 | E: ideal wires | rows/read 72 | spread x1"]["raw"]["rms"]
    check("analog RMS error equals the closed-form value", abs(sim - pred) / pred < 0.06, f"closed form {pred:.3f} steps, tile model {sim:.3f} steps")


# ------------------------------------------------------------------ 3. digital misread probability and Monte Carlo counts
def test_digital():
    d = json.loads((ROOT / "results" / "array_digital_mode.json").read_text())
    ok = True; msg = []
    for lrs, (ml, sl) in (("LRS3", (43.59, 1.55)), ("LRS1", (18.08, 1.96))):
        for k in (1.0, 2.0, 3.0):
            z = (ml - 2.85) / ((sl + 1.85) * k); p = 0.5 * math.erfc(z / math.sqrt(2))
            a = d[f"analytic_{lrs}_x{k:g}"]
            ok &= abs(a["p"] - p) <= 1e-6 * p
    # the Monte Carlo counts must be statistically compatible with the analytic probability (207,360 devices per case)
    for key, lrs, k in (("mc_LRS3_x3_vos2mV", "LRS3", 3.0), ("mc_LRS1_x1_vos0mV", "LRS1", 1.0), ("mc_LRS1_x2_vos2mV", "LRS1", 2.0)):
        lam = 2 * d[key]["weights"] * d[f"analytic_{lrs}_x{k:g}"]["p"]
        n = d[key]["weight_errors"]
        ok &= (lam - 5 * math.sqrt(lam) - 3) <= n <= (lam + 5 * math.sqrt(lam) + 3)
        msg.append(f"{key}: {n} observed, {lam:.1f} expected")
    check("digital-mode misread probabilities and Monte Carlo counts agree", ok, "; ".join(msg))


# ------------------------------------------------------------------ 4. device model with a general-purpose ODE solver
KB = 8.617333262e-5
P = dict(I0=854e-6, g0=0.28, V0=0.35, v0=2.79e9, Ea=1.0, a0=0.25, tox=6.0, gamma0=20.0, beta=0.4, alpha=3.0, Rth=1500.0, T0=300.0)


def rate(g, v, p=P):
    i = p["I0"] * math.exp(-g / p["g0"]) * math.sinh(v / p["V0"])
    kt = KB * (p["T0"] + abs(v * i) * p["Rth"])
    gam = p["gamma0"] - p["beta"] * g ** p["alpha"]
    return -p["v0"] * math.exp(-p["Ea"] / kt) * math.sinh(gam * p["a0"] * v / (p["tox"] * kt))       # nm/s


def test_device():
    ev = lambda t, y: y[0] - 1.25
    ev.terminal = True
    s = solve_ivp(lambda t, y: [rate(y[0], 0.6 * t)], (0, 1.5), [1.8], method="LSODA", rtol=1e-10, atol=1e-13, events=ev, max_step=1e-3)
    v_cross = 0.6 * s.t_events[0][0]
    ref = json.loads((ROOT / "results" / "model_three_solvers.json").read_text())
    worst = max(abs(v_cross - ref[k]["A_v_cross_V"]) for k in ("python", "ngspice", "gnucap"))
    check("set voltage in the ramp, general ODE solver against the three implementations", worst < 1e-3,
          f"LSODA {v_cross:.5f} V; largest difference {worst*1e3:.2f} mV")
    # the published kinetic values in the same equations
    pub = dict(P, Ea=0.6, v0=0.4e9)
    s2 = solve_ivp(lambda t, y: [rate(y[0], 0.6 * t, pub)], (0, 1.5), [1.8], method="LSODA", rtol=1e-10, atol=1e-13, events=ev, max_step=1e-3)
    v_pub = 0.6 * s2.t_events[0][0]
    check("published kinetic values give a set voltage far below the measured 0.65-0.75 V", v_pub < 0.4, f"{v_pub:.3f} V")
    # read disturb: time for the 0.2 V read current of a 2.85 uA cell to rise 10 % under 0.29 V (cell alone, no transistor)
    g_start = 1.4526; g_end = g_start - 0.28 * math.log(1.1)
    e2 = lambda t, y: y[0] - g_end
    e2.terminal = True
    s3 = solve_ivp(lambda t, y: [rate(y[0], 0.29)], (0, 1e5), [g_start], method="LSODA", rtol=1e-9, atol=1e-13, events=e2)
    t10 = s3.t_events[0][0]
    rd = json.loads((ROOT / "results" / "read_disturb.json").read_text())
    ref_t = rd["HRS at the published mean current (gap 1.4526 nm)"]["bias"]["0.29 V"]["seconds_to_plus_10_percent"]
    check("read-disturb time at 0.29 V, ODE solver against the reference model", abs(t10 - ref_t) / ref_t < 0.15,
          f"LSODA {t10:.0f} s (cell alone), reference model {ref_t:.0f} s (with transistor)")
    # static currents at the published gaps
    cur = {g: P["I0"] * math.exp(-g / 0.28) * math.sinh(0.2 / 0.35) * 1e6 for g in (0.95, 0.85, 0.73, 1.88)}
    ok = abs(cur[0.95] - 17.31) < 0.02 and abs(cur[0.85] - 24.74) < 0.02 and abs(cur[0.73] - 37.98) < 0.02 and abs(cur[1.88] - 0.625) < 0.002
    check("static cell currents at the published gap values", ok, ", ".join(f"{g} nm: {c:.2f} uA" for g, c in cur.items()))


# ------------------------------------------------------------------ 5. energy arithmetic from first principles
def test_energy():
    e = json.loads((ROOT / "results" / "energy_system.json").read_text())
    s = json.loads((ROOT / "results" / "gnucap_sense.json").read_text())["tran"]
    i_lrs = s["tt | LRS3 mean 43.6 uA | others LRS3"]["i_vdd_end_uA"] - 60.0
    i_hrs = s["tt | HRS mean 2.85 uA | others LRS3"]["i_vdd_end_uA"] - 60.0
    e_sa = 1.2 * (16 * i_lrs + 32 * i_hrs + 60.0) * 1e-6 * 4e-9 * e["rows_read_per_product"] * 1e9
    cox = 3.9 * 8.854e-12 / 7.4e-9
    e_wl = 48 * 4.5e-6 * 0.45e-6 * cox * 1.7 ** 2 * e["rows_read_per_product"] * 1e9
    syn = json.loads((ROOT / "results" / "synth_baseline.json").read_text())
    core = syn["tcim_core_digital_product"]
    e_logic = core["e_total_pJ_per_cycle"] * (core["cycles_per_product"] + 3) * 1e-3
    ok = abs(e_sa - e["window_4ns"]["sense_amplifiers_nJ"]) < 2e-4 and abs(e_wl - e["word_lines_nJ"]) < 2e-4 and \
        abs(e_logic - e["digital_logic_as_synthesized"]["nJ_per_product"]) < 2e-3
    check("energy table recomputed from the raw currents, capacitance and toggle counts", ok,
          f"sense amplifiers {e_sa:.4f} nJ, word lines {e_wl:.4f} nJ, logic {e_logic:.3f} nJ")
    # clock energy of the flip-flops from the library numbers
    ff = core["flops"]; per_ff = core["e_clock_pJ"] / ff * 1e3
    check("clock energy per flip-flop is in the range of the library data", 20 < per_ff < 40, f"{per_ff:.1f} fJ per flip-flop per cycle, {ff} flip-flops")


if __name__ == "__main__":
    test_tile(); test_analog_rms(); test_digital(); test_device(); test_energy()
    print(f"\n{len(FAIL)} failures" + (": " + ", ".join(FAIL) if FAIL else ""))
    (ROOT / "results" / "audit_independent.json").write_text(json.dumps(LOG, indent=1))
    sys.exit(1 if FAIL else 0)
