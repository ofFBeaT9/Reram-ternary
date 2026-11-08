"""Monte Carlo of the two-state program-and-verify cycle with device-to-device spread (8 October 2026).

Question: does the programming scheme of TCIM0 (rtl/tcim_core.sv: reset phase then set phase, amplitude 0.5 V to
2.5 V in 0.1 V steps, at most 21 pulses per phase, PITER <= 42) still finish for devices that differ from each
other, and where do the verified devices end up relative to the 25 uA read reference?

Scheme as in the RTL and roadmap section 8 / 18.3: 1 us pulses; reset with gate 2.7 V until the read at 0.2 V
(gate 1.7 V) is at or below 6 uA; then set with gate 1.7 V until the read is at or above 42 uA.
Transistor: IHP sg13_hv_nmos, W 4.5 um, L 0.45 um, PSP103 table (model/table_mos.py), corners tt, ss, ff.
Device: the re-fitted reference model (model/ispva.py: CAL, Ea 1.0 eV, v0 2.79 m/s).

ASSUMED SPREAD. No device-to-device statistics of the switching kinetics are published for this device; the
published spreads are of read currents after verify (roadmap Table 4.1). Each device here gets its own
  v0  (log-normal, sigma of ln v0 = S_V),  Ea  (normal, sigma S_E),  I0 (log-normal, sigma of ln I0 = S_I),
with three levels: none, "1x" (S_V 0.5, S_E 0.03 eV, S_I 0.10) and "2x" (twice those). These are scenarios,
not data. 0.03 eV of activation energy changes the switching rate by a factor of about 3 at room temperature.
Each device starts from a set state (the nominal device programmed to 42 uA, then its own I0 applied).
Writes results/program_mc.json.
  python3 model/program_mc.py 100               the cycle at tt, ss, ff with no, 1x and 2x spread
  python3 model/program_mc.py 100 reset-gate    then: the same devices, reset phase alone, gate 2.7 / 3.0 / 3.3 V"""
import sys, json
from dataclasses import replace
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ispva import CAL, ispva_set, ispva_reset          # noqa: E402
from table_mos import TableNMOS                        # noqa: E402
from experiments import read                           # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SET_TARGET, RESET_TARGET, READ_REF = 42e-6, 6e-6, 25e-6
VG_SET, VG_RESET = 1.7, 2.7
LEVELS = {"none": (0.0, 0.0, 0.0), "1x": (0.5, 0.03, 0.10), "2x": (1.0, 0.06, 0.20)}
N_DEV = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def run(corner, level, n, seed=1):
    mos = TableNMOS(4.5, corner)
    s_v, s_e, s_i = LEVELS[level]
    rng = np.random.default_rng(seed)
    g_set_nominal = ispva_set(CAL, mos, VG_SET, SET_TARGET, CAL.gap_max, clamp=False)["gap_nm"] * 1e-9
    rows = []
    for k in range(n if level != "none" else 1):
        p = replace(CAL, v0=CAL.v0 * float(np.exp(rng.normal(0, s_v))), Ea=CAL.Ea + float(rng.normal(0, s_e)),
                    I0=CAL.I0 * float(np.exp(rng.normal(0, s_i))))
        r = ispva_reset(p, mos, RESET_TARGET, g_set_nominal, vgate=VG_RESET)
        s = ispva_set(p, mos, VG_SET, SET_TARGET, r["gap_nm"] * 1e-9, clamp=False)
        rows.append(dict(reset_ok=r["ok"], reset_pulses=r["pulses"], reset_amp=r["amp"], hrs_uA=r["iread_uA"],
                         set_ok=s["ok"], set_pulses=s["pulses"], set_amp=s["amp"], lrs_uA=s["iread_uA"],
                         v0=p.v0, Ea=p.Ea, I0=p.I0))
    ok = [x for x in rows if x["reset_ok"] and x["set_ok"]]
    a = lambda key, xs: np.array([x[key] for x in xs]) if xs else np.array([np.nan])
    summ = dict(devices=len(rows), both_verified=len(ok), reset_failed=sum(not x["reset_ok"] for x in rows),
                set_failed=sum(x["reset_ok"] and not x["set_ok"] for x in rows),
                pulses_total_max=int(max(x["reset_pulses"] + x["set_pulses"] for x in rows)),
                pulses_total_mean=round(float(np.mean([x["reset_pulses"] + x["set_pulses"] for x in rows])), 2),
                reset_amp_max_V=round(float(a("reset_amp", ok).max()), 2), set_amp_max_V=round(float(a("set_amp", ok).max()), 2),
                lrs_min_uA=round(float(a("lrs_uA", ok).min()), 2), lrs_max_uA=round(float(a("lrs_uA", ok).max()), 2),
                hrs_max_uA=round(float(a("hrs_uA", ok).max()), 3), hrs_min_uA=round(float(a("hrs_uA", ok).min()), 3))
    summ["lrs_margin_to_ref_uA"] = round(summ["lrs_min_uA"] - READ_REF * 1e6, 2)
    summ["hrs_margin_to_ref_uA"] = round(READ_REF * 1e6 - summ["hrs_max_uA"], 2)
    return summ, rows


def reset_gate_study(corner, level, n, vgates=(2.7, 3.0, 3.3), seed=1):
    """The same sampled devices as run() (same seed and draw order), reset phase only, at several gate voltages."""
    mos = TableNMOS(4.5, corner)
    s_v, s_e, s_i = LEVELS[level]
    rng = np.random.default_rng(seed)
    g_set_nominal = ispva_set(CAL, mos, VG_SET, SET_TARGET, CAL.gap_max, clamp=False)["gap_nm"] * 1e-9
    devs = [replace(CAL, v0=CAL.v0 * float(np.exp(rng.normal(0, s_v))), Ea=CAL.Ea + float(rng.normal(0, s_e)),
                    I0=CAL.I0 * float(np.exp(rng.normal(0, s_i)))) for _ in range(n)]
    out = {}
    for vg in vgates:
        rs = [ispva_reset(p, mos, RESET_TARGET, g_set_nominal, vgate=vg) for p in devs]
        out[f"vg {vg}"] = dict(failed=sum(not r["ok"] for r in rs), pulses_max=max(r["pulses"] for r in rs),
                               pulses_mean=round(float(np.mean([r["pulses"] for r in rs])), 2))
    return out


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "reset-gate":
    path = ROOT / "results" / "program_mc.json"
    res = json.loads(path.read_text())
    res["reset_gate_study"] = {f"{c} {lv}": reset_gate_study(c, lv, N_DEV) for c in ("tt", "ss") for lv in ("1x", "2x")}
    print(json.dumps(res["reset_gate_study"], indent=1))
    path.write_text(json.dumps(res, indent=1))
    sys.exit(0)

if __name__ == "__main__":
    res = dict(scheme=dict(set_target_uA=42, reset_target_uA=6, read_reference_uA=25, vg_set=VG_SET, vg_reset=VG_RESET,
                           amplitudes="0.5-2.5 V, 0.1 V steps, 21 per phase", pulse_us=1, transistor="sg13_hv_nmos W4.5 L0.45"),
               spread_levels={k: dict(sigma_ln_v0=v[0], sigma_Ea_eV=v[1], sigma_ln_I0=v[2]) for k, v in LEVELS.items()},
               note="assumed spreads (scenarios), not data; model reset is abrupt, so HRS currents are model artifacts",
               runs={})
    for corner in ("tt", "ss", "ff"):
        for level in LEVELS:
            summ, rows = run(corner, level, N_DEV)
            res["runs"][f"{corner} {level}"] = dict(summary=summ, devices=rows)
            print(corner, level, json.dumps(summ), flush=True)
            (ROOT / "results" / "program_mc.json").write_text(json.dumps(res, indent=1))
