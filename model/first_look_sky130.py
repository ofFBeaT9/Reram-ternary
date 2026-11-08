"""First look at a second foundry (7 October 2026). NOT a verified result.

SkyWater publishes a ReRAM library for SKY130 (github.com/google/skywater-pdk-libs-sky130_fd_pr_reram, v2.0.3)
with a Verilog-A model that has the same equations as model/reram_stanford.py. This script puts SkyWater's
parameters (file cells/reram_cell/sky130_fd_pr_reram__reram_cell.va of that library) into our reference model:
    gap g = Tox - Tfilament;  g0 = Tox - Tfilament_ref;  v0 = 2 * velocity_k1 (their two exponentials = 2 sinh);
    Rth = tau_thermal / C_thermal (steady state of their thermal equation).
Cell alone, no transistor, no check against their Xyce example yet. Writes results/first_look_sky130.json."""
import sys, math, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reram_stanford import ReRAMParams, current, gap_rate, step_gap
tox = 5.0e-9
p = ReRAMParams(I0=6.140e-5, g0=tox - 4.7249e-9, V0=0.430, v0=2 * 150.0, Ea=1.5, a0=0.25e-9, tox=tox, gamma0=16.5, beta=1.25, alpha=3.0,
                Rth=0.23e-9 / 3.1825e-16, T0=300.0, gap_max=tox - 3.3e-9, Kth=0.0, C=tox - 4.9e-9, WL=1.0)
gmin, gmax = tox - 4.9e-9, tox - 3.3e-9
out = dict(g0_nm=p.g0 * 1e9, gap_min_nm=gmin * 1e9, gap_max_nm=gmax * 1e9, Rth_K_per_W=p.Rth)
for name, g in (("LRS_full", gmin), ("HRS_full", gmax)):
    i = float(current(p, 0.2, g)); out[name] = dict(uA_at_0p2V=i * 1e6, uS=i / 0.2 * 1e6, kohm=0.2 / i / 1e3)
# smallest pulse amplitude (cell alone) that moves the gap half way within 1 us
def switches(v, g_start, target, dt=1e-6):
    g = step_gap(p, v, g_start, dt, gmin, gmax)
    return (g <= target) if v > 0 else (g >= target)
mid = 0.5 * (gmin + gmax)
for name, sign, g_start in (("set_1us_V", +1, gmax), ("reset_1us_V", -1, gmin)):
    v = 0.05
    while v < 4.0 and not switches(sign * v, g_start, mid): v += 0.05
    out[name] = round(v, 2)
# read disturb: HRS gap change after 1 s at 0.2 V
g = step_gap(p, 0.2, gmax, 1.0, gmin, gmax); out["hrs_gap_shift_pm_after_1s_at_0p2V"] = (gmax - g) * 1e12
(Path(__file__).resolve().parents[1] / "results" / "first_look_sky130.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
