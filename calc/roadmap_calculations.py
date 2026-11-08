"""Reproduces the calculated figures of the verified roadmap (revision 2, Appendix A).

Inputs
  - Read-current statistics of IHP 4-kbit 1T1R arrays, optimized M-ISPVA scheme:
    Perez et al., Electronics 10, 1084 (2021), Table 2 (mean and sigma in uA at 0.2 V).
  - IHP SG13G2 Process Specification Rev. 1.2 (sheet resistance, current limits, thickness).
  - IHP / Europractice 2026 list prices for SG13G2 and the MEMRES module.
Assumptions are marked ASSUMPTION. Run:  python3 roadmap_calculations.py
"""
import math
import numpy as np

MU = {"HRS": 2.85, "LRS1": 18.08, "LRS2": 31.01, "LRS3": 43.59}   # uA at 0.2 V
SG = {"HRS": 1.85, "LRS1": 1.96, "LRS2": 1.60, "LRS3": 1.55}      # uA
VREAD = 0.2
RSH = {"M1": 0.110, "M2-5": 0.088, "TM1": 0.018}                   # ohm/sq, target values


def separation(lo, hi):
    return (MU[hi] - MU[lo]) / (SG[hi] + SG[lo])


def tail(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def sum_error(lrs, rows):
    """Standard deviation of a differential column sum, in result steps, and P(rounded result wrong)."""
    step = MU[lrs] - MU["HRS"]
    pair = math.sqrt(SG[lrs] ** 2 + SG["HRS"] ** 2)
    steps = math.sqrt(rows) * pair / step
    return steps, math.erfc(0.5 / (steps * math.sqrt(2)))


def bitline_error(rows, lrs, metal, width_um, pitch_um, both_ends=False):
    """Far-end bitline voltage as a fraction of VREAD; all rows selected and in LRS."""
    g_cell = MU[lrs] * 1e-6 / VREAD
    g_seg = 1.0 / (RSH[metal] * pitch_um / width_um)
    a = np.zeros((rows, rows)); b = np.zeros(rows)
    for i in range(rows):
        a[i, i] += g_cell; b[i] += g_cell * VREAD
        a[i, i] += g_seg
        if i > 0: a[i, i - 1] -= g_seg
        if i < rows - 1:
            a[i, i] += g_seg; a[i, i + 1] -= g_seg
        elif both_ends:
            a[i, i] += g_seg
    return np.linalg.solve(a, b).max() / VREAD


def pads(area_mm2):
    """Pads on a square die with sg13g2_io cells: 80 um pads, 180 um corners."""
    return 4 * math.floor((math.sqrt(area_mm2) * 1000 - 360) / 80)


def price(area_mm2, member=False):
    return (6205 + 510) * area_mm2 + 2000 if member else (7300 + 600) * area_mm2 + 2500


if __name__ == "__main__":
    print("Level separation (combined sigmas) and misread probability")
    for lo, hi in (("HRS", "LRS1"), ("LRS1", "LRS2"), ("LRS2", "LRS3"), ("LRS1", "LRS3"), ("HRS", "LRS3")):
        z = separation(lo, hi); print(f"  {lo}-{hi}: z = {z:.2f}, tail = {tail(z):.1e}")
    print("Analog-mode error from device spread (Table 6.1)")
    for lrs in ("LRS1", "LRS3"):
        for rows in (24, 64, 72):
            s, p = sum_error(lrs, rows); print(f"  {lrs}, {rows} rows: {s:.2f} steps, P(wrong) = {100 * p:.1f} %")
    print("Far-end bitline error, 72 rows (Table 6.2); pitch is an ASSUMPTION")
    for metal, w, both in (("M2-5", 0.4, False), ("M2-5", 1.0, False), ("M2-5", 0.4, True), ("TM1", 1.64, False)):
        vals = [100 * bitline_error(72, l, metal, w, p, both) for l in ("LRS1", "LRS3") for p in (2.0, 3.0)]
        print(f"  {metal} {w} um {'both ends' if both else 'one end'}: " + ", ".join(f"{v:.1f} %" for v in vals))
    print("Time-to-threshold converter of the draft: distinct codes for results 1..64 in the best case:",
          len({64 // k for k in range(1, 65)}))
    print("Pads:", {a: pads(a) for a in (0.8, 1.0, 1.5)}, " 64 pads need", round(((16 * 80 + 360) / 1000) ** 2, 2), "mm2")
    print("Price with MEMRES (EUR):", {a: round(price(a)) for a in (0.8, 1.0, 1.5, 2.69)}, " member 0.8 mm2:", round(price(0.8, True)))
    print("Metal1 limit: %.2e A/cm2" % (1e-3 / (1e-4 * 0.42e-4)))
    print("Per mole O (kJ/mol):", {k: round(h / n, 1) for k, (h, n) in {"Al2O3": (-1675.7, 3), "HfO2": (-1144.7, 2), "TiO2": (-944.0, 2)}.items()})
