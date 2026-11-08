"""Read disturb in the calibrated model: how long a continuous read bias takes to move an HRS device.
The kinetics were fitted to ONE measured quantity (set voltage 0.70 V at 0.6 V/s), so the extrapolation to
0.2-0.33 V is a model prediction with large uncertainty, not a measurement. It tells which way the risk goes."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ispva import CAL
from experiments import evolve, read
from table_mos import TableNMOS

mos = TableNMOS(4.5, "tt")
res = {}
for name, g0 in (("HRS at the published mean current (gap 1.4526 nm)", 1.4526e-9), ("HRS at the 14 uA tail (gap 0.9969 nm)", 0.9969e-9),
                 ("fully reset (gap 1.8 nm)", 1.8e-9)):
    i0 = read(CAL, mos, g0)
    row = {}
    for v in (0.20, 0.25, 0.29, 0.33):
        # time for the 0.2 V read current to rise by 10 %: bisection on log time
        lo, hi = -9.0, 12.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            g = evolve(CAL, mos, v, 1.7, g0, 10 ** mid, 0.05e-9)
            if read(CAL, mos, g) > 1.1 * i0:
                hi = mid
            else:
                lo = mid
        t = 10 ** (0.5 * (lo + hi))
        row[f"{v:.2f} V"] = dict(seconds_to_plus_10_percent=float(f"{t:.3g}"), reads_of_4ns=float(f"{t/4e-9:.3g}"))
    res[name] = dict(read_uA=round(i0 * 1e6, 2), bias=row)
    print(name, f"({i0*1e6:.2f} uA)")
    for k, q in row.items():
        print(f"   {k}: {q['seconds_to_plus_10_percent']:.3g} s of bias = {q['reads_of_4ns']:.3g} reads of 4 ns")
(Path(__file__).resolve().parents[1] / "results" / "read_disturb.json").write_text(json.dumps(res, indent=1))
