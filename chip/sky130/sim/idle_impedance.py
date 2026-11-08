"""Idle supply impedance against the stored states (4 November 2026, security study; the DExiM attack of the input PDF
reads stored ReRAM data from the package impedance of an idle chip).

One column of the array as drawn in periph.spice, in the idle state the controller holds between operations (rtl/chip/
tcim_actl.sv: IDLE, every line grounded): both bit-line slices (level shifter, ground NOR, driver, sense amplifier) with
prg = bl_sen = flt = 0, the source-line driver with its ground switch on, 72 row slices with sel = 0 (word lines low), and
72 cells, each a ReRAM device (a resistor of the device's conductance) in series with its select transistor (W 1.0 /
L 0.5 um, gate on its word line) from the bit line to the source line. The reference bias sits at the read setting.
Small-signal AC impedance seen at each supply pin (vdda 3.3 V, vccd 1.8 V, VPRG 2.4 V, VWLP / VWLR word-line rails)
from 1 kHz to 1 GHz, with every device low-resistance (120 uS) and every device high-resistance (0.3 uS, below SkyWater's
reset state), tt 27 C. Positive control: the same deck with row 0 being read (its word line on, the bit lines on the sense
amplifiers), at vccd, where the read current comes from. Writes results/security/idle_impedance.json."""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "security" / "idle_impedance.json"
CELLS = (HERE / "periph.spice").read_text()


def deck(g, pin, read=False):
    ac = {p: ("ac 1" if p == pin else "") for p in ("vdda", "vccd", "vprg", "vwl")}
    rows = "\n".join(f"Xr{r} {'vccd' if (read and r == 0) else 0} wl{r} vwl vccd vdda 0 rowslice\n"
                     f"Rp{r} blp dp{r} {1 / g:.6g}\nXtp{r} dp{r} wl{r} sl 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5\n"
                     f"Rn{r} bln dn{r} {1 / g:.6g}\nXtn{r} dn{r} wl{r} sl 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5"
                     for r in range(72))
    sen = "vdda" if read else "0"
    return f"""* idle column
{S.lib("tt")}.temp 27
{CELLS}
Vda vdda 0 dc 3.3 {ac['vdda']}
Vcc vccd 0 dc 1.8 {ac['vccd']}
Vpg vprg 0 dc 2.4 {ac['vprg']}
Vwl vwl 0 dc 2.0 {ac['vwl']}
Vref vref 0 0.2
Iib vccd ib 0.8e-6
Xrb ib 0 vccd 0 vref vbp vcl vccd 0 refbias
* bit-line slices: prg_lv = 0, sen = 0, flt = 0 (idle: ground switch on)
Xbp 0 blp op vprg {sen} 0 vbp vcl vccd vdda 0 blslice
Xbn 0 bln on vprg {sen} 0 vbp vcl vccd vdda 0 blslice
* source-line driver: prg = 0, prgb = 1, dn = 1 (ground NOR output high in idle)
Xsl vprg sl 0 vdda vdda vdda 0 sld
{rows}
.control
ac dec 10 1e3 1e9
wrdata out.txt i(V{dict(vdda='da', vccd='cc', vprg='pg', vwl='wl')[pin]})
.endc
.end
"""


def main():
    res = dict(note="AC impedance |Z| = 1 / |I| for a 1 V AC source on the pin; one column (2 x 72 devices) in the idle state",
               pins={})
    for pin in ("vdda", "vccd", "vprg", "vwl"):
        z = {}
        for name, g in (("all_LRS_120uS", 120e-6), ("all_HRS_0.3uS", 0.3e-6)):
            a, _ = S.run(deck(g, pin))
            f = a[:, 0]; i = np.hypot(a[:, 1], a[:, 2])
            z[name] = (f, 1 / np.maximum(i, 1e-30))
        f, za = z["all_LRS_120uS"]; _, zb = z["all_HRS_0.3uS"]
        rel = np.abs(za - zb) / zb
        pick = [1e3, 1e5, 1e6, 1e7, 1e8, 1e9]
        res["pins"][pin] = dict(
            max_relative_difference=float(rel.max()), at_Hz=float(f[int(np.argmax(rel))]),
            table=[dict(f_Hz=float(f[int(np.argmin(abs(f - p)))]), Z_LRS_ohm=float(za[int(np.argmin(abs(f - p)))]),
                        Z_HRS_ohm=float(zb[int(np.argmin(abs(f - p)))])) for p in pick])
        print(pin, "max relative |Z| difference LRS vs HRS:", f"{rel.max():.3g}", "at", f"{f[int(np.argmax(rel))]:.3g} Hz", flush=True)
    # positive control: the same deck and method with row 0 being read (word line on, bit lines to the sense amplifiers);
    # the read current comes from vccd, so the method must see the stored state there
    z = {}
    for name, g in (("all_LRS_120uS", 120e-6), ("all_HRS_0.3uS", 0.3e-6)):
        a, _ = S.run(deck(g, "vccd", read=True))
        z[name] = 1 / np.maximum(np.hypot(a[:, 1], a[:, 2]), 1e-30)
    f = a[:, 0]; rel = np.abs(z["all_LRS_120uS"] - z["all_HRS_0.3uS"]) / z["all_HRS_0.3uS"]
    res["control_read_row0_vccd"] = dict(max_relative_difference=float(rel.max()), at_Hz=float(f[int(np.argmax(rel))]),
                                         Z_LRS_ohm_1kHz=float(z["all_LRS_120uS"][0]), Z_HRS_ohm_1kHz=float(z["all_HRS_0.3uS"][0]))
    print("control (row 0 read, vccd): max relative |Z| difference", f"{rel.max():.3g}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
