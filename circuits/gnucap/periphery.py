"""First-cut periphery circuits with IHP's PSP 103 transistors (8 October 2026). NOT a finished design.

1. Level shifter 1.2 V -> 3.3 V: low-voltage inverter for the complement, two thick-oxide NMOS pull-downs,
   cross-coupled thick-oxide PMOS, thick-oxide output inverter. Checked: it switches both ways, delays (input 50 %
   to output 50 %), and the static 3.3 V supply current (sum of the off-transistor currents) with the input low and high,
   at five corners and -40 / 27 / 125 C.
2. Word-line driver: thick-oxide inverter on a selectable rail (1.7 V read and set gate, 2.7 V reset gate,
   3.3 V), driving one row: 48 select gates of 4.5/0.45 um (454 fF, roadmap section 18.8) on the GatPoly word
   line of the drawn array (layout/cell_2t2r.py: 229 um long, 0.45 um wide, 509 squares of salicided n+ poly,
   7.8 ohm/sq, the maximum of the process specification, with its +3100 ppm/K), as a 24-section RC line.
   Checked: 10-90 % rise and fall at the driver end and at the far end, and the settled level.
3. Column switch for programming: thick-oxide transmission gate between the programming rail and one bit or
   source line, carrying one device's programming current (0.6 mA, the worst case of results/gnucap_cell).
   Checked: voltage lost across the switch from 0.5 V to 3.0 V (the pulse range and the SkyWater forming range).
Sizes are first guesses. References, the programming-voltage source itself and layout parasitics are not here.
Writes results/gnucap_periphery.json."""
import json
from pathlib import Path
import numpy as np
import gnucap_run as g

OUT = Path(__file__).resolve().parents[2] / "results" / "gnucap_periphery.json"
CORNERS = ("tt", "ss", "ff", "sf", "fs")
TEMPS = (-40, 27, 125)
LS = dict(wn=1.0, wp=0.3, wpo=2.0, wno=1.0)              # level shifter
WLD = dict(wp=12.0, wn=6.0)                              # word-line driver
TG = dict(wn=20.0, wp=40.0)                              # column switch
C_ROW = 454e-15
WL_SQUARES = 229.0 / 0.45          # drawn word line: length / width
RS_POLY, TC_POLY = 7.8, 3100e-6    # salicided n+ GatPoly, ohm/sq (max of SG13G2 process spec 2.7) and ppm/K
N_SEG = 24


def hv(kind, w, d, gt, s, b, l=0.45):
    # the PDK's wrapper accepts w up to 10 um per device; wider devices are m parallel copies
    m = int(np.ceil(w / 10.0 - 1e-9))
    return f"sg13_hv_{kind}mos #(.w({w / m:g}u), .l({l}u), .ng(1), .m({m}), .mm_ok(0), .rfmode(0)) m{kind}{d}{gt}({d}, {gt}, {s}, {b});"


def lv(kind, w, d, gt, s, b, l=0.13):
    return f"sg13_lv_{kind}mos #(.w({w}u), .l({l}u), .ng(1), .mm_ok(0), .rfmode(0)) l{kind}{d}{gt}({d}, {gt}, {s}, {b});"


def opt(temp):
    return f".options temp={temp}\n"


def cross(t, v, level, rising, after=0.0):
    k = np.where(t >= after)[0]
    t, v = t[k], v[k]
    idx = np.where((v[:-1] < level) & (v[1:] >= level))[0] if rising else np.where((v[:-1] > level) & (v[1:] <= level))[0]
    if not idx.size:
        return None
    i = idx[0]
    return float(t[i] + (level - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i]))


# ---------------------------------------------------------------- 1. level shifter
def level_shifter(corner, temp):
    deck = g.header(corner, lv=True) + f"""
spice
{opt(temp)}Vdd vdd 0 dc 1.2
Vddh vddh 0 dc 3.3
Vin in 0 pwl(0 0 5n 0 5.1n 1.2 25n 1.2 25.1n 0 50n 0)
Cl out 0 20f
.verilog
{lv('p', 0.6, 'inb', 'in', 'vdd', 'vdd')}
{lv('n', 0.3, 'inb', 'in', '\\0 ', '\\0 ')}
{hv('n', LS['wn'], 'x', 'in', '\\0 ', '\\0 ')}
{hv('n', LS['wn'], 'xb', 'inb', '\\0 ', '\\0 ')}
{hv('p', LS['wp'], 'x', 'xb', 'vddh', 'vddh')}
{hv('p', LS['wp'], 'xb', 'x', 'vddh', 'vddh')}
{hv('p', LS['wpo'], 'out', 'x', 'vddh', 'vddh')}
{hv('n', LS['wno'], 'out', 'x', '\\0 ', '\\0 ')}
print tran v(in) v(out) i(Vddh)
tran 0 50n 0.02n
"""
    d = g.run(deck, timeout=900)[0]["data"]
    t, vin, vout, ih = d[:, 0], d[:, 1], d[:, 2], -d[:, 3]
    r = dict(t_rise_ns=cross(t, vout, 1.65, True, 5e-9), t_fall_ns=cross(t, vout, 1.65, False, 25e-9))
    r = {k: (None if v is None else round((v - (5e-9 if k == "t_rise_ns" else 25e-9)) * 1e9, 3)) for k, v in r.items()}
    r.update(out_high_V=round(float(vout[np.argmin(abs(t - 24e-9))]), 3), out_low_V=round(float(vout[-1]), 4))
    for name, vin_dc in (("i_static_in_low_nA", 0.0), ("i_static_in_high_nA", 1.2)):
        r[name] = round(ls_static(corner, temp, vin_dc) * 1e9, 4)
    r["ok"] = r["t_rise_ns"] is not None and r["t_fall_ns"] is not None and r["out_high_V"] > 3.2 and r["out_low_V"] < 0.1
    return r


def off_current(kind, w, corner, temp):
    """Current of one thick-oxide transistor held off (gate at its source) with 3.3 V across drain and source,
    read through a 1 Mohm sense resistor (1 nA drops 1 mV). Gnucap reports a voltage source's own current with
    a resolution coarser than 1 nA, so the sense resistor is used."""
    if kind == "n":
        src = "Vh vh0 0 dc 3.3\nRs vh0 d 1e6\nVg gg 0 dc 0\nVs ss 0 dc 0"
    else:
        src = "Vs ss 0 dc 3.3\nVg gg 0 dc 3.3\nRs d 0 1e6"
    deck = g.header(corner) + f"""
spice
{opt(temp)}{src}
.verilog
{hv(kind, w, 'd', 'gg', 'ss', 'ss')}
print op i(Rs)
op
"""
    return abs(float(g.run(deck, timeout=900)[0]["data"][0, 1]))


def ls_static(corner, temp, vin):
    """Static current from the 3.3 V supply. In either state every node of the shifter sits at a rail, so the
    supply current is the sum of the currents of the three transistors that are off with 3.3 V across them:
    input low: the pull-down on x, the cross-coupled PMOS on xb, the output PMOS; input high: the pull-down on xb,
    the cross-coupled PMOS on x, the output NMOS. (A DC operating point of the whole shifter did not converge
    reliably to pA resolution in Gnucap; single transistors converge in 5 to 7 iterations.)"""
    if vin < 0.6:
        return off_current("n", LS["wn"], corner, temp) + off_current("p", LS["wp"], corner, temp) + off_current("p", LS["wpo"], corner, temp)
    return off_current("n", LS["wn"], corner, temp) + off_current("p", LS["wp"], corner, temp) + off_current("n", LS["wno"], corner, temp)


# ---------------------------------------------------------------- 2. word-line driver
def wl_driver(corner, temp, vrail):
    r_tot = WL_SQUARES * RS_POLY * (1 + TC_POLY * (temp - 25))
    ladder = "\n".join(f"R{k} n{k} n{k + 1} {r_tot / N_SEG:.4g}\nC{k} n{k + 1} 0 {C_ROW / N_SEG:.4e}" for k in range(N_SEG))
    deck = g.header(corner) + f"""
spice
{opt(temp)}Vr vr 0 dc {vrail}
Vin in 0 pwl(0 3.3 2n 3.3 2.05n 0 22n 0 22.05n 3.3 40n 3.3)
{ladder}
.verilog
{hv('p', WLD['wp'], 'n0', 'in', 'vr', 'vr')}
{hv('n', WLD['wn'], 'n0', 'in', '\\0 ', '\\0 ')}
print tran v(n0) v(n{N_SEG})
tran 0 40n 0.01n
"""
    d = g.run(deck, timeout=900)[0]["data"]
    t = d[:, 0]
    out = dict(r_line_ohm=round(r_tot, 1))
    for tag, v in (("near", d[:, 1]), ("far", d[:, 2])):
        t10, t90 = cross(t, v, 0.1 * vrail, True, 2e-9), cross(t, v, 0.9 * vrail, True, 2e-9)
        f90, f10 = cross(t, v, 0.9 * vrail, False, 22e-9), cross(t, v, 0.1 * vrail, False, 22e-9)
        out[f"{tag}_rise_10_90_ns"] = None if None in (t10, t90) else round((t90 - t10) * 1e9, 3)
        out[f"{tag}_fall_90_10_ns"] = None if None in (f90, f10) else round((f10 - f90) * 1e9, 3)
        out[f"{tag}_settle_90_ns"] = None if t90 is None else round((t90 - 2.025e-9) * 1e9, 3)
        out[f"{tag}_settled_V"] = round(float(v[np.argmin(abs(t - 21e-9))]), 4)
    return out


# ---------------------------------------------------------------- 3. column switch
def column_switch(corner, temp, i_load=0.6e-3):
    deck = g.header(corner) + f"""
spice
{opt(temp)}Vp vp 0 dc 0.5
Vgn gn 0 dc 3.3
Vgp gp 0 dc 0
Vbn bn 0 dc 0
Vbp bp 0 dc 3.3
Il bl 0 dc {i_load}
.verilog
{hv('n', TG['wn'], 'bl', 'gn', 'vp', 'bn')}
{hv('p', TG['wp'], 'bl', 'gp', 'vp', 'bp')}
print dc v(vp) v(bl)
dc Vp 0.5 3.0 0.05
"""
    d = g.run(deck, timeout=900)[0]["data"]
    vp, vbl = d[:, 1], d[:, 2]
    drop = vp - vbl
    return dict(drop_max_mV=round(float(drop.max()) * 1e3, 2), at_V=round(float(vp[int(np.argmax(drop))]), 2),
                drop_at_0p5V_mV=round(float(drop[0]) * 1e3, 2), drop_at_2p5V_mV=round(float(drop[np.argmin(abs(vp - 2.5))]) * 1e3, 2),
                drop_at_3p0V_mV=round(float(drop[-1]) * 1e3, 2))


if __name__ == "__main__":
    res = dict(sizes=dict(level_shifter=LS, wl_driver=WLD, column_switch=TG), c_row_fF=C_ROW * 1e15, wl_squares=round(WL_SQUARES, 1), rs_poly_ohm_sq=RS_POLY, level_shifter={}, wl_driver={}, column_switch={})
    import sys
    if "--resume" in sys.argv and OUT.exists():          # continue an interrupted run with the same sizes
        old = json.loads(OUT.read_text())
        if old.get("sizes") == res["sizes"] and old.get("rs_poly_ohm_sq") == RS_POLY:
            for k in ("level_shifter", "wl_driver", "column_switch"):
                res[k] = old[k]
    for c in CORNERS:
        for T in TEMPS:
            if f"{c} {T} C" in res["level_shifter"] and f"{c} {T} C 3.3 V" in res["wl_driver"]:
                continue
            res["level_shifter"][f"{c} {T} C"] = level_shifter(c, T)
            res["column_switch"][f"{c} {T} C"] = column_switch(c, T)
            for vr in (1.7, 2.7, 3.3):
                res["wl_driver"][f"{c} {T} C {vr} V"] = wl_driver(c, T, vr)
            print(c, T, res["level_shifter"][f"{c} {T} C"], res["column_switch"][f"{c} {T} C"], flush=True)
            OUT.write_text(json.dumps(res, indent=1))
    ls = list(res["level_shifter"].values()); wl = list(res["wl_driver"].values()); cs = list(res["column_switch"].values())
    res["summary"] = dict(
        level_shifter_all_ok=all(x["ok"] for x in ls), level_shifter_delay_max_ns=max(max(x["t_rise_ns"] or 99, x["t_fall_ns"] or 99) for x in ls),
        level_shifter_static_max_nA=max(max(x["i_static_in_low_nA"], x["i_static_in_high_nA"]) for x in ls),
        wl_far_rise_max_ns=max(x["far_rise_10_90_ns"] or 99 for x in wl), wl_far_fall_max_ns=max(x["far_fall_90_10_ns"] or 99 for x in wl),
        wl_far_settle_90_max_ns=max(x["far_settle_90_ns"] or 99 for x in wl), wl_near_rise_max_ns=max(x["near_rise_10_90_ns"] or 99 for x in wl),
        wl_settled_min_fraction=min(x["far_settled_V"] / float(k.split()[-2]) for k, x in res["wl_driver"].items()),
        column_switch_drop_max_mV=max(x["drop_max_mV"] for x in cs), cases=len(ls))
    print(res["summary"])
    OUT.write_text(json.dumps(res, indent=1))
