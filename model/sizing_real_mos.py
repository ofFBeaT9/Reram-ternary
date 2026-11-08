"""Select-transistor study with the REAL IHP sg13_hv_nmos (PSP103 table from Gnucap) in the reference model.

For each width and corner:
  * 1T1R read current of the four published gap values and of the gap that gives each target current
  * quasi-static SET sweeps at gate 1.0 / 1.2 / 1.6 V -> LRS resistance (published: 16 / 11 / 8 kOhm)
  * 1 us pulse-and-verify SET: lowest gate voltage that reaches each read-current target, amplitude, pulses
  * 1 us pulse-and-verify RESET from the deepest level at gate 2.7 V and 3.3 V
Selected points are confirmed with full Gnucap transients in circuits/gnucap/exp_cell.py."""
import sys, json
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reram_stanford import *
from experiments import evolve, read, dc_sweep_set, dc_sweep_reset
from ispva import CAL, ispva_set, ispva_reset
from table_mos import TableNMOS

TARGETS = {"LRS1": 18.08e-6, "LRS2": 31.01e-6, "LRS3": 43.59e-6}    # IHP array means at 0.2 V
RESET_TARGET = 6e-6


def gap_for(mos, i_target):
    lo, hi = 0.2e-9, 1.9e-9
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if read(CAL, mos, mid) > i_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def study(W, corner):
    mos = TableNMOS(W, corner)
    row = {"read_uA_at_published_gaps": {f"{g:.2f}nm": round(read(CAL, mos, g * 1e-9) * 1e6, 2) for g in (0.95, 0.85, 0.73, 1.88)}}
    row["quasi_static"] = {}
    for vg in (1.0, 1.2, 1.6):
        tr, vset = dc_sweep_set(CAL, mos, vg, CAL.gap_max, clamp=False)
        g_end = tr[-1][2]
        i = read(CAL, mos, g_end)
        _, vreset = dc_sweep_reset(CAL, mos, 2.7, g_end)
        row["quasi_static"][f"vg{vg}"] = dict(vset=round(float(vset), 2), gap_nm=round(g_end * 1e9, 3), read_uA=round(i * 1e6, 2),
                                              r_kohm=round(0.2 / i / 1e3, 2), vreset=round(float(vreset), 2))
    for name, tgt in TARGETS.items():
        found = None
        for vg in np.arange(0.9, 3.31, 0.05):
            r = ispva_set(CAL, mos, float(vg), tgt, 1.8e-9, clamp=False)
            if r["ok"]:
                found = dict(vg=round(float(vg), 2), amp=round(r["amp"], 2), pulses=r["pulses"], iread_uA=round(r["iread_uA"], 2), gap_nm=round(r["gap_nm"], 4))
                break
        row[name] = found
    g3 = gap_for(mos, TARGETS["LRS3"])
    row["gap_for_LRS3_nm"] = round(g3 * 1e9, 4)
    for vg in (2.7, 3.3):
        r = ispva_reset(CAL, mos, RESET_TARGET, g3, vgate=vg)
        row[f"reset_LRS3_vg{vg}"] = dict(ok=r["ok"], amp=round(r["amp"], 2), pulses=r["pulses"], iread_uA=round(r["iread_uA"], 2), gap_nm=round(r["gap_nm"], 4))
    return row


if __name__ == "__main__":
    res = {}
    for W, corner in ((1.5, "tt"), (3.0, "tt"), (4.5, "tt"), (6.0, "tt"), (4.5, "ss"), (4.5, "ff")):
        row = study(W, corner)
        res[f"W{W}_{corner}"] = row
        print(f"W = {W} um, L 0.45 um, corner {corner}")
        print("   read at published gaps:", row["read_uA_at_published_gaps"])
        for k, q in row["quasi_static"].items():
            print(f"   quasi-static {k}: Vset {q['vset']} V, LRS {q['r_kohm']} kOhm ({q['read_uA']} uA, gap {q['gap_nm']} nm), Vreset {q['vreset']} V")
        for name in TARGETS:
            f = row[name]
            print("   SET  %s: %s" % (name, "not reached up to Vg 3.3 V" if f is None else f"Vg {f['vg']} V, amplitude {f['amp']} V, {f['pulses']} pulses, read {f['iread_uA']} uA, gap {f['gap_nm']} nm"))
        for vg in (2.7, 3.3):
            r = row[f"reset_LRS3_vg{vg}"]
            print(f"   RESET LRS3 (gap {row['gap_for_LRS3_nm']} nm) at Vg {vg}: ok={r['ok']}, amplitude {r['amp']} V, {r['pulses']} pulses, read {r['iread_uA']} uA")
        sys.stdout.flush()
    json.dump(res, open(__file__.rsplit('/', 2)[0] + "/results/device_sizing_psp.json", "w"), indent=1)
