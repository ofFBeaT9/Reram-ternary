"""Port of the cell simulations to SkyWater SKY130 with its ReRAM option (8 October 2026).

A. Mapping check. SkyWater's Verilog-A model (sky130_fd_pr_reram__reram_cell.va, library v2.0.3) is transcribed
   here line by line, with its own explicit 1 ns time update, and compared with our reference model
   (model/reram_stanford.py) at the parameters of model/first_look_sky130.py: read current at 0.2 V over the
   whole gap range, and the gap after constant-voltage pulses of 1 us on the bare cell. SkyWater's update is run
   with a 10 ps step (converged) and with the 1 ns step its $bound_step allows; near a switching threshold the
   1 ns step overshoots, which is a property of their discretization, not of the equations.
B. 1T1R in ngspice with SkyWater's transistor models (sky130_fd_pr__nfet_g5v0d10v5, the "nhv" device of
   SkyWater's 1T1R cells) and our ngspice ReRAM subcircuit at SkyWater's parameters. SkyWater's published
   programming conditions for its 1T1R test structure (#5: set WL 1.7 V, BL 2.4 V, 1 us; reset WL 2.5 V,
   SL 2.6 V, 1 us) are applied, and the read current at 0.2 V is computed before and after.
   The transistor width of SkyWater's test structure is not published; several widths are tried. The word-line
   voltage the model needs to reset the set state in 1 us is found by a scan (source line 0.1 V above it).

Environment: SKY130_FD_PR = a checkout of google/skywater-pdk-libs-sky130_fd_pr (models/ and cells/*.spice).
Writes results/sky130_port.json."""
import json, math, os, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from reram_stanford import ReRAMParams, current, step_gap  # noqa: E402

TOX = 5.0e-9
P = ReRAMParams(I0=6.140e-5, g0=TOX - 4.7249e-9, V0=0.430, v0=2 * 150.0, Ea=1.5, a0=0.25e-9, tox=TOX, gamma0=16.5, beta=1.25,
                alpha=3.0, Rth=0.23e-9 / 3.1825e-16, T0=300.0, gap_max=TOX - 3.3e-9, Kth=0.0, C=TOX - 4.9e-9, WL=1.0)
GMIN, GMAX = TOX - 4.9e-9, TOX - 3.3e-9


# ---------------------------------------------------------------- A. SkyWater's model, transcribed
def sky_va_pulse(v, tf0, t_pulse=1e-6, dt=1e-9):
    """Constant voltage v across the bare cell for t_pulse, SkyWater's update order and constants.
    Returns the final filament thickness (m)."""
    k, q = 1.380649e-23, 1.602176634e-19
    Tox, Tmin, Tmax = 5.0e-9, 3.3e-9, 4.9e-9
    Eg, Er, Ik1, Tref, Vref, vk1, gk0, gk1 = 1.501, 1.500, 6.140e-5, 4.7249e-9, 0.430, 150.0, 16.5, -1.25
    T0, Cth, tau, a0 = 300.0, 3.1825e-16, 0.23e-9, 0.25e-9
    T, tf = T0, tf0
    for _ in range(int(round(t_pulse / dt))):
        gamma = gk0 + gk1 * ((Tox - tf) / 1e-9) ** 3
        kTq = k * T / q
        dtf = vk1 * (math.exp(-Eg / kTq) * math.exp(gamma * a0 / Tox * v / kTq) - math.exp(-Er / kTq) * math.exp(-gamma * a0 / Tox * v / kTq))
        tf = min(max(tf + dtf * dt, Tmin), Tmax)
        i = Ik1 * math.exp(-(Tox - tf) / (Tox - Tref)) * math.sinh(v / Vref)
        T = (T + dt * (abs(v * i) / Cth + T0 / tau)) / (1 + dt / tau)
    return tf


def part_a():
    out = dict(read_current=[], pulses=[])
    for g_nm in np.linspace(0.1, 1.7, 9):
        g = g_nm * 1e-9
        i_ref = float(current(P, 0.2, g))
        i_sky = 6.140e-5 * math.exp(-g / (TOX - 4.7249e-9)) * math.sinh(0.2 / 0.430)
        out["read_current"].append(dict(gap_nm=round(g_nm, 3), ours_uA=i_ref * 1e6, skywater_uA=i_sky * 1e6, rel_diff=abs(i_ref / i_sky - 1)))
    for v, g0 in ((1.6, GMAX), (1.8, GMAX), (2.0, GMAX), (2.2, GMAX), (-1.0, GMIN), (-1.2, GMIN), (-1.4, GMIN), (-1.6, GMIN)):
        g_ref = float(step_gap(P, v, g0, 1e-6, GMIN, GMAX))
        g_sky = TOX - sky_va_pulse(v, TOX - g0, dt=1e-11)       # SkyWater's update with a small step: converged
        g_sky1 = TOX - sky_va_pulse(v, TOX - g0, dt=1e-9)       # with the 1 ns step its $bound_step allows
        out["pulses"].append(dict(V=v, start_gap_nm=round(g0 * 1e9, 3), ours_gap_nm=g_ref * 1e9, skywater_gap_nm=g_sky * 1e9,
                                  diff_pm=abs(g_ref - g_sky) * 1e12, skywater_1ns_step_gap_nm=g_sky1 * 1e9))
    out["max_read_rel_diff"] = max(r["rel_diff"] for r in out["read_current"])
    out["max_gap_diff_pm"] = max(r["diff_pm"] for r in out["pulses"])
    return out


# ---------------------------------------------------------------- B. 1T1R with SkyWater's transistor
# The transistor enters as a table Id(Vsb, Vgs, Vds) computed by ngspice with SkyWater's own BSIM models; the cell
# is our reference model at SkyWater's parameters, solved in series exactly as for IHP (model/experiments.py).
# (Driving our ngspice ReRAM subcircuit directly at SkyWater's fast kinetics did not converge.)
from experiments import evolve, read  # noqa: E402

VSB = np.arange(0.0, 3.01, 0.25)
VGS = np.arange(0.0, 3.31, 0.1)
VDS = np.arange(0.0, 3.31, 0.05)


def lib_text(corner):
    f = os.environ["SKY130_FD_PR"]
    inc = [f"{f}/models/parameters/invariant.spice", f"{f}/models/corners/{corner}/nonfet.spice",
           f"{f}/cells/nfet_g5v0d10v5/sky130_fd_pr__nfet_g5v0d10v5__mismatch.corner.spice",
           f"{f}/cells/nfet_g5v0d10v5/sky130_fd_pr__nfet_g5v0d10v5__{corner}.corner.spice"]
    return ".param mc_mm_switch=0 mc_pr_switch=0\n" + "".join(f'.include "{p}"\n' for p in inc)


def mos_table(corner, w, l=0.5):
    tab = np.zeros((len(VSB), len(VGS), len(VDS)))
    with tempfile.TemporaryDirectory() as d:
        Path(d, ".spiceinit").write_text("set ngbehavior=hsa\n")
        for a, vsb in enumerate(VSB):
            deck = f"""* nhv table
.option scale=1e-6
{lib_text(corner)}
Vd d 0 0
Vg g 0 0
Vb b 0 {-vsb}
Xm d g 0 b sky130_fd_pr__nfet_g5v0d10v5 w={w} l={l}
.control
dc Vd 0 {VDS[-1]:.3f} 0.05 Vg 0 {VGS[-1]:.3f} 0.1
wrdata out.txt -i(Vd)
.endc
.end
"""
            Path(d, "t.cir").write_text(deck)
            subprocess.run(["ngspice", "-b", "t.cir"], cwd=d, capture_output=True, text=True, timeout=600)
            data = np.loadtxt(Path(d, "out.txt"))
            ids = data[:, 1].reshape(len(VGS), len(VDS))
            tab[a] = np.clip(ids, 0, None)
    return tab


class SkyNHV:
    """Same interface as model/table_mos.TableNMOS."""
    def __init__(self, tab):
        self.vsb, self.vgs, self.vds, self.tab = VSB, VGS, VDS, tab

    @staticmethod
    def _idx(axis, x):
        x = min(max(x, axis[0]), axis[-1])
        k = min(int((x - axis[0]) / (axis[1] - axis[0])), len(axis) - 2)
        return k, (x - axis[k]) / (axis[k + 1] - axis[k])

    def ids(self, vgs, vds, vsb=0.0):
        if vds <= 0.0 or vgs <= 0.0:
            return 0.0
        a, fa = self._idx(self.vsb, vsb); b, fb = self._idx(self.vgs, vgs); c, fc = self._idx(self.vds, vds)
        t = self.tab[a:a + 2, b:b + 2, c:c + 2]
        t = t[0] * (1 - fa) + t[1] * fa
        t = t[0] * (1 - fb) + t[1] * fb
        return float(t[0] * (1 - fc) + t[1] * fc)


def part_b():
    out = {}
    for corner in ("tt", "ss", "ff"):
        for w in (0.42, 1.0, 2.0, 4.0):
            mos = SkyNHV(mos_table(corner, w))
            r = dict(on_current_uA_vgs3p3_vds0p2=mos.ids(3.3, 0.2) * 1e6)
            g_set = evolve(P, mos, 2.4, 1.7, GMAX, 1e-6, GMIN)                             # SkyWater 1T1R #5 set
            r["set"] = dict(gap_nm=g_set * 1e9, read_uA_wl3p3=read(P, mos, g_set, 0.2, 3.3) * 1e6, read_uA_wl1p7=read(P, mos, g_set, 0.2, 1.7) * 1e6)
            g_rst = evolve(P, mos, 2.6, 2.5, GMIN, 1e-6, GMIN, polarity=-1, gmax=GMAX)   # SkyWater 1T1R #5 reset
            r["reset"] = dict(gap_nm=g_rst * 1e9, read_uA_wl3p3=read(P, mos, g_rst, 0.2, 3.3) * 1e6, read_uA_wl1p7=read(P, mos, g_rst, 0.2, 1.7) * 1e6)
            # the same reset from the state the set pulse left, and set from the state the reset left (one cycle)
            r["cycle"] = dict(set_after_reset_gap_nm=evolve(P, mos, 2.4, 1.7, g_rst, 1e-6, GMIN) * 1e9,
                              reset_after_set_gap_nm=evolve(P, mos, 2.6, 2.5, g_set, 1e-6, GMIN, polarity=-1, gmax=GMAX) * 1e9)
            # which word-line voltage the model needs to reset the set state in 1 us (source line = WL + 0.1 V)
            r["reset_scan"] = []
            for wl in np.arange(2.5, 5.01, 0.25):
                g = evolve(P, mos, wl + 0.1, wl, g_set, 1e-6, GMIN, polarity=-1, gmax=GMAX)
                r["reset_scan"].append(dict(WL=round(float(wl), 2), SL=round(float(wl) + 0.1, 2), gap_nm=g * 1e9, read_uA_wl3p3=read(P, mos, g, 0.2, 3.3) * 1e6))
            ok = [x["WL"] for x in r["reset_scan"] if x["gap_nm"] >= 1.0]
            r["reset_wl_needed_V"] = ok[0] if ok else None
            out[f"{corner} W {w} um"] = r
            print(corner, w, json.dumps(r), flush=True)
    return out


if __name__ == "__main__":
    a = part_a()
    print("A: read current max relative difference", a["max_read_rel_diff"], "; gap after 1 us pulses max difference (pm)", a["max_gap_diff_pm"])
    for p in a["pulses"]:
        print(p)
    res = dict(part_a=a)
    if os.environ.get("SKY130_FD_PR"):
        res["part_b"] = part_b()
    (ROOT / "results" / "sky130_port.json").write_text(json.dumps(res, indent=1))
