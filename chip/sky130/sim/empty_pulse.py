"""Empty pulses and an asynchronous reset in mid-pulse (8 November 2026; council finding H6 of the security study).

Revision 4.6 pads programming to 21 + 21 steps with pulses whose masks are empty: the controller runs the whole
sequence of rtl/chip/tcim_actl.sv (BRK flt=1, MAKE modes, SETL flt=0, WLON for T_PULSE, REL, BRK2, GND) but no device is
selected for change. In steady state no device then sees a voltage; this deck checks the transients. One column as drawn
in periph.spice: the shared-control block (ctrlglob: level shifters of sen / flt / sl_prg / wl_prog, word-line rail switch,
reference), both bit-line slices, the source-line driver, 72 row slices (row 0 selected) and 72 cells (ReRAM device as a
resistor + select transistor W 1.0 / L 0.5 um), clock 16 MHz (62.5 ns), T_SETTLE 2 and T_PULSE 16 cycles.
Cases: an empty set pulse (all lines grounded, word line to VWLP 2.0 V), an empty reset pulse (all bit lines and the
source line at VPRG 3.0 V, word line to VWLP 3.0 V), and both again with an asynchronous reset in the middle of the pulse
(every control steps to its idle value in the same instant, without break-before-make). Every device low-resistance
(120 uS) or high-resistance (4.5 uS); corners tt, ss, ff at 27 C.
Reported: the largest |voltage| across any device of the selected row and of an unselected row, the largest current
drawn from VPRG, and (device model, empty_pulse_gap.py) how far one empty pulse moves each device's read conductance. Writes results/security/empty_pulse.json. Runs where ngspice and the SKY130 models are (the reram-eda
image on the PC)."""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "security" / "empty_pulse.json"
CACHE = ROOT / "results" / "security" / "empty_pulse_cases"       # one file per finished case, so a rerun skips it
CELLS = (HERE / "periph.spice").read_text()
T = 62.5e-9          # clock period, 16 MHz
E = 0.5e-9           # control edge


def pwl(name, node, v, edges):
    """edges: list of (cycle, level 0/1); starts at 0."""
    pts = ["0 0"]
    lvl = 0
    for c, l in edges:
        t = c * T
        pts.append(f"{t:.4g} {lvl * v}"); pts.append(f"{t + E:.4g} {l * v}"); lvl = l
    return f"V{name} {node} 0 pwl({' '.join(pts)})"


def deck(kind, g, corner, areset, gear=False):
    reset = kind == "reset"
    vprg, vwlp = (3.0, 3.0) if reset else (2.4, 2.0)
    stop = 13 if areset else None                     # asynchronous reset in the middle of the pulse (cycles 5 ... 21)
    def ed(seq):
        if stop is None: return seq
        return [(c, l) for c, l in seq if c < stop] + [(stop, 0)]
    flt = ed([(1, 1), (3, 0), (22, 1), (24, 0)])
    mode = ed([(2, 1), (23, 0)])                      # wl_prog (and for a reset: prg of both bit lines, sl_prg)
    sel = ed([(5, 1), (21, 0)])
    rows = "\n".join(f"Xr{r} {'sel0' if r == 0 else 0} wl{r} vwl vccd vdda 0 rowslice\n"
                     f"Rp{r} blp dp{r} {1 / g:.6g}\nXtp{r} dp{r} wl{r} sl 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5\n"
                     f"Rn{r} bln dn{r} {1 / g:.6g}\nXtn{r} dn{r} wl{r} sl 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5"
                     for r in range(72))
    prg = pwl("prg", "prgl", 1.8, mode) if reset else "Vprg prgl 0 0"
    slp = pwl("slp", "slprgl", 1.8, mode) if reset else "Vslp slprgl 0 0"
    return f"""* empty pulse, {kind}
{S.lib(corner)}.temp 27
{".options method=gear reltol=2e-3" if gear else ""}
{CELLS}
Vda vdda 0 3.3
Vcc vccd 0 1.8
Vpg vprg 0 {vprg}
Vwp vwlp 0 {vwlp}
Vwr vwlr 0 1.0
Vref vref 0 0.2
Iib vccd ib 0.8e-6
{pwl("flt", "fltl", 1.8, flt)}
{pwl("wlp", "wlpl", 1.8, mode)}
{pwl("sel", "sel0", 1.8, sel)}
{prg}
{slp}
Vsen senl 0 0
Xcg senl fltl slprgl wlpl 0 0 0 ib vref vwlr vwlp sen flt slprg slprgb sldn vwl vbp vcl vccd vdda 0 ctrlglob
Xbp prgl blp op vprg sen flt vbp vcl vccd vdda 0 blslice
Xbn prgl bln on vprg sen flt vbp vcl vccd vdda 0 blslice
Xsl vprg sl slprg slprgb sldn vdda 0 sld
{rows}
.control
tran 0.05n {26 * T:.4g}
let dp0 = v(blp) - v(dp0)
let dn0 = v(bln) - v(dn0)
let dp1 = v(blp) - v(dp1)
let dn1 = v(bln) - v(dn1)
let ipg = -i(Vpg)
wrdata out.txt dp0 dn0 dp1 dn1 ipg v(wl0)
.endc
.end
"""


W_PLANNED = 10_000          # full-array writes assumed over the chip's life; stated on the page with the result
EV_CMD = 42                 # pulse steps of one program command (21 reset + 21 set)
OTHER_ROWS = 71


def one(c):
    import empty_pulse_gap as G     # device-model drift (model/sky130_port.py), three conditions
    import subprocess
    kind, areset, corner, name, g = c
    cache = CACHE / f"{kind}_{int(areset)}_{corner}_{name}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    solver = "trapezoidal"
    try:
        a, _ = S.run(deck(kind, g, corner, areset), timeout=1500)
    except (subprocess.TimeoutExpired, RuntimeError):          # retried once with Gear integration
        solver = "gear, reltol 2e-3 (trapezoidal did not finish)"
        try:
            a, _ = S.run(deck(kind, g, corner, areset, gear=True), timeout=2400)
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            r = dict(pulse=kind, async_reset_mid_pulse=areset, corner=corner, devices=name, failed=f"ngspice: {type(e).__name__}")
            print(r, flush=True); return r
    t = a[:, 0]
    g0 = G.gap_for(g)
    hrs = name.startswith("HRS")
    dev = {}
    for nm, col in (("row0_p", 1), ("row0_n", 3), ("row1_p", 5), ("row1_n", 7)):
        d = dict(max_abs_V=float(np.abs(a[:, col]).max()))
        for cond in G.CONDITIONS:
            rel = G.drift(t, a[:, col], g0, cond)
            d[cond] = dict(rel_change_G=rel, toward_reference=max(rel, 0.0) if hrs else max(-rel, 0.0))
        dev[nm] = d
    r = dict(pulse=kind, async_reset_mid_pulse=areset, corner=corner, devices=name,
             max_V_selected_row=max(dev["row0_p"]["max_abs_V"], dev["row0_n"]["max_abs_V"]),
             max_V_unselected_row=max(dev["row1_p"]["max_abs_V"], dev["row1_n"]["max_abs_V"]),
             max_I_vprg_A=float(np.abs(a[:, 9]).max()), wl0_peak_V=float(a[:, 11].max()), sim_end_ns=float(t[-1] * 1e9), solver=solver,
             device_model=dev)
    CACHE.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(r))
    print({k: r[k] for k in ("pulse", "async_reset_mid_pulse", "corner", "devices", "max_V_selected_row", "max_V_unselected_row")},
          {k: {c: f'{v[c]["rel_change_G"]:.2e}' for c in G.CONDITIONS} for k, v in dev.items()}, flush=True)
    return r


def main():
    import os
    from concurrent.futures import ProcessPoolExecutor
    import empty_pulse_gap as G
    devs = (("LRS_100uS", 100e-6), ("LRS_28uS_set_verify_edge", 28e-6), ("HRS_4.5uS", 4.5e-6), ("HRS_7.93uS_reset_verify_edge", 7.93e-6))
    cases = [(k, ar, co, nm, g) for k in ("set", "reset") for ar in (False, True) for nm, g in devs
             for co in (("tt", "ss", "ff") if nm in ("HRS_4.5uS", "LRS_28uS_set_verify_edge") else ("tt",))]
    with ProcessPoolExecutor(int(os.environ.get("JOBS", "2"))) as ex:
        allc = list(ex.map(one, cases))
    out = [c for c in allc if "failed" not in c]
    failed = [c for c in allc if "failed" in c]
    worst = {}
    for cond in G.CONDITIONS:
        b0 = max(c["device_model"][f"row0_{s}"][cond]["toward_reference"] for c in out for s in "pn")
        b1 = max(c["device_model"][f"row1_{s}"][cond]["toward_reference"] for c in out for s in "pn")
        w1 = 0.1 / (b1 * EV_CMD * OTHER_ROWS) if b1 > 0 else None
        worst[cond] = dict(selected_row_per_pulse=b0, selected_row_per_command=b0 * EV_CMD,
                           other_row_per_pulse=b1, other_row_full_array_writes_to_10pct=w1,
                           ok=b0 * EV_CMD < 0.01 and (w1 is None or w1 >= 10 * W_PLANNED))
    res = dict(note="Empty programming pulses (H6): largest |V| across a device (row 0 selected, row 1 not), largest current from "
                    "VPRG, and the read-conductance drift toward the read reference (HRS up, LRS down) from the device model over each "
                    "waveform (empty_pulse_gap.py). A row is re-verified when it is programmed, so the selected row's drift counts per "
                    "command (42 steps); a row written once drifts while the 71 other rows are programmed (42 x 71 steps per full-array "
                    "write). The device is a linear resistor in the deck and the cell transistors have no junction areas, so coupling "
                    "may be underestimated; uniform columns only.",
               ngspice_lib=S.LIB, planned_array_writes=W_PLANNED,
               criterion="per condition: selected-row drift per command < 1 % and other-row full-array writes to 10 % >= 10 x planned",
               cases=out, worst_V_selected_row=max(c["max_V_selected_row"] for c in out),
               worst_V_unselected_row=max(c["max_V_unselected_row"] for c in out), worst_by_condition=worst,
               failed_cases=failed, closed=not failed and all(w["ok"] for w in worst.values()))
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
