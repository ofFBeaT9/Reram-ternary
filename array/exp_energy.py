"""E3: first-order time and array energy of one matrix-vector product on a 72 x 24 tile.
Array energy = read voltage x bit-line current x time the cells are biased. Periphery is estimated separately."""
import sys, json
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tile import *

rng = np.random.default_rng(3)
out = {}
for lrs in ("LRS3", "LRS2", "LRS1"):
    pd = []; pa = []; nd = []; na = []; macs = []
    for t in range(6):
        cfg = TileConfig(lrs=lrs, bl_metal="TM1", bl_width_um=1.64, sl_metal="TM1", sl_width_um=1.64, both_ends=True)
        tile = Tile(cfg, rng); tile.program(rng.choice((-1, 0, 1), size=(72, 24)))
        iref = reference_current(lrs)
        for _ in range(20):
            x = rng.choice((-1, 0, 1), size=72)
            _, p, n = tile.digital(x, iref); pd.append(p); nd.append(n)
            _, p2, n2 = tile.analog_raw(x); pa.append(p2); na.append(n2)
            macs.append(72 * 24)
    Pd, Pa = np.mean(pd), np.mean(pa)
    row = dict(sum_power_digital_mW=Pd * 1e3, reads_digital=float(np.mean(nd)), sum_power_analog_mW=Pa * 1e3, reads_analog=float(np.mean(na)))
    print(f"{lrs}: digital {np.mean(nd):.0f} row reads, sum of read powers {Pd*1e3:.2f} mW; analog {np.mean(na):.0f} reads, sum {Pa*1e3:.2f} mW")
    for ts in (10e-9, 20e-9, 50e-9):
        e = Pd * ts; row[f"digital_E_nJ_tsense_{ts*1e9:.0f}ns"] = e * 1e9
        print(f"   digital, sense {ts*1e9:.0f} ns: array energy {e*1e9:.3f} nJ per product = {e/1728*1e15:.0f} fJ per weight; time {np.mean(nd)*(ts+10e-9)*1e6:.2f} us with 10 ns overhead per read")
    for tc in (50e-9, 200e-9, 1.6e-6):
        e = Pa * tc; row[f"analog_E_nJ_tconv_{tc*1e9:.0f}ns"] = e * 1e9
        print(f"   analog, conversion {tc*1e9:.0f} ns: array energy {e*1e9:.3f} nJ per product = {e/1728*1e15:.0f} fJ per weight; time {np.mean(na)*tc*1e6:.2f} us")
    out[lrs] = row
# word-line switching estimate for the digital mode: 48 thick-oxide gates of W/L = 4.5/0.45 um per row
cox = 3.9 * 8.854e-12 / 7.4e-9            # F/m2, thick oxide ~7.4 nm (IHP spec 7.3-7.5 nm)
cg = 48 * 4.5e-6 * 0.45e-6 * cox
e_wl = cg * 1.7 ** 2
out["wordline"] = dict(gate_cap_fF=cg * 1e15, energy_per_row_read_pJ=e_wl * 1e12)
print(f"word line: gate capacitance of one row about {cg*1e15:.0f} fF (wire not included); {e_wl*1e12:.2f} pJ per row read at 1.7 V")
json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/array_energy.json", "w"), indent=1)
