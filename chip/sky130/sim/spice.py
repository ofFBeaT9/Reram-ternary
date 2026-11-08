"""Small ngspice runner for the SKY130 chip work (11 October 2026).

SKY130_NGSPICE_LIB = open_pdks sky130B libs.tech/ngspice/sky130.lib.spice (corner sections tt, ss, ff, sf, fs and the
*_mm mismatch sections). Decks are written to a temporary folder with a .spiceinit that selects HSPICE compatibility,
run in batch mode, and the vectors written with wrdata are returned as a numpy array (time or sweep variable first)."""
import os, subprocess, tempfile
from pathlib import Path
import numpy as np

LIB = os.environ.get("SKY130_NGSPICE_LIB")
FULL = False                     # True: load the full corner section of sky130.lib.spice (for the reduced-library check)
CORNERS = ("tt", "ss", "ff", "sf", "fs")
TEMPS = (-40, 27, 125)


DEVICES = ("nfet_01v8", "pfet_01v8", "nfet_g5v0d10v5", "pfet_g5v0d10v5")


def _reduced(corner, mm):
    """The corner section of sky130.lib.spice with only the four transistor types used here: the same files, in the same
    order, minus every other device (each FET type is tens of thousands of lines; loading all of them takes about two
    minutes per run). periph_sim.py checks that the reduced and the full library give the same results."""
    root = Path(LIB).parent
    cache = Path(os.environ.get("SKY130_LIBCACHE", tempfile.gettempdir())) / f"sky130_reduced_{corner}{'_mm' if mm else ''}.spice"
    if cache.exists():
        return cache
    keep = tuple(f"sky130_fd_pr__{d}_" for d in DEVICES) + tuple(f"sky130_fd_pr__{d}." for d in DEVICES)

    def wanted(line):
        return any(k in line for k in keep) and "esd_" not in line and "rf_" not in line and "special_" not in line

    out = ["* reduced SKY130 library: nfet/pfet_01v8 and nfet/pfet_g5v0d10v5 only",
           f".param mc_mm_switch={1 if mm else 0}", ".param mc_pr_switch=0"]
    allsp = (root / "all.spice").read_text().splitlines()
    k = 0                                           # header of all.spice: scale, layout-dependent parameters, .param block
    while k < len(allsp) and not allsp[k].startswith(".include \"parasitics"):
        line = allsp[k]
        out.append(line.replace('.include "', f'.include "{root}/') if line.startswith(".include") else line)
        k += 1
    for line in (root / "corners" / f"{corner}.spice").read_text().splitlines():
        if line.startswith(".include") and wanted(line):
            out.append(line.replace('.include "', f'.include "{root}/corners/'))
    out.append(f'.include "{root}/corners/{corner}/nonfet.spice"')
    for line in allsp[k:]:
        if line.startswith(".include") and wanted(line):
            out.append(line.replace('.include "', f'.include "{root}/'))
    cache.write_text("\n".join(out) + "\n")
    return cache


def lib(corner, mm=False):
    if not LIB:
        raise RuntimeError("set SKY130_NGSPICE_LIB")
    if FULL:
        return f'.lib "{LIB}" {corner}{"_mm" if mm else ""}\n'
    return f'.include "{_reduced(corner, mm)}"\n'


def run(deck, seed=None, timeout=1800):
    with tempfile.TemporaryDirectory() as d:
        Path(d, ".spiceinit").write_text("set ngbehavior=hsa\nset num_threads=1\n" + (f"set rndseed={seed}\n" if seed else ""))
        Path(d, "t.cir").write_text(deck)
        r = subprocess.run(["ngspice", "-b", "t.cir"], cwd=d, capture_output=True, text=True, timeout=timeout)
        f = Path(d, "out.txt")
        if not f.exists():
            raise RuntimeError("ngspice failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
        a = np.loadtxt(f, ndmin=2)
        return a, r.stdout


def cross(t, v, level, rising, after=0.0):
    """First time after `after` at which v crosses `level` in the given direction (linear interpolation), or None."""
    for k in range(1, len(t)):
        if t[k] <= after:
            continue
        a, b = v[k - 1], v[k]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return t[k - 1] + (level - a) / (b - a) * (t[k] - t[k - 1])
    return None
