"""Remaining first-cut periphery (revision 4.3), with IHP's PSP 103 transistors and poly resistors in Gnucap.

1. Ratiometric read reference. The first-cut sense amplifier (sense.py) compares the cell current with an IDEAL
   25 uA source. Here the reference current is made on chip by a replica column: the same clamp transistor and
   column switch as a real bit line, ending in a poly resistor R_ref (rppd, 8 kohm) instead of a cell. Its current
   is mirrored into every sense amplifier, so a cell is read as LRS when its conductance exceeds about 1/R_ref,
   whatever the exact read voltage. The 0.2 V clamp reference stays an ideal source here (a buffered divider on
   chip, or a pad on the first chip); it is varied by +-10 % to show that the decision does not depend on it.
   Checked: trip current and trip conductance over transistor corners, resistor corners, temperature, supply and
   read voltage, against the published six-sigma device tails (70 uS and 171.5 uS at 0.2 V).
2. Column switch for programming, twice the size of revision 4.2 (NMOS 40 um, PMOS 80 um): voltage lost at 0.6 mA,
   and at the reset-current bound of exp_reset_gate.py (--add-cs-bound, run after exp_reset_gate.py).
3. Test multiplexer: thick-oxide transmission gates that connect one of 16 bit-line or source-line nodes to a pad
   (force and sense pads separate). Checked: on-resistance from 0 to 3.3 V, and the leakage of 15 channels that are
   off with 3.3 V across them at 125 C (it adds to what a parameter analyzer measures).
Writes results/gnucap_periphery2.json."""
import json, sys
from pathlib import Path
import numpy as np
import gnucap_run as g
import periphery as p1
import sense

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "gnucap_periphery2.json"
IHP = g.IHP
R_REF = dict(w=1.0, l=9.0, b=2)      # rppd, um, b = bends: three 9 um segments, about 8 kohm at 260 ohm/sq
TAILS_uS = dict(HRS=14.0 / 0.2, LRS3=34.3 / 0.2)


def res_header(rcorner):
    return (f"load {IHP}/plugins/models/resistor_paramset.so\n"
            f"include {IHP}/models/cornerRES.va\n"
            f"res_{rcorner} corner_res();\n")


# ---------------------------------------------------------------- 1. ratiometric read reference
def ratio_trip(corner="tt", temp=27, rcorner="typ", vref=0.2, vdd=1.2):
    s = sense.SIZES
    deck = g.header(corner, lv=True) + res_header(rcorner) + f"""
spice
.options temp={temp}
Vdd vdd 0 dc {vdd}
Vref vr 0 dc {vref}
Vmux vmux 0 dc 3.3
Vm rbl rbl2 dc 0
Icell bl 0 dc 0
.verilog
sg13_lv_pmos #(.w({s['wp']}u), .l({s['lp']}u), .ng(1), .mm_ok(0), .rfmode(0)) mp1(mirr, mirr, vdd, vdd);
sg13_lv_nmos #(.w({s['wn']}u), .l({s['ln']}u), .ng(1), .mm_ok(0), .rfmode(0)) mnrep(mirr, vclamp, rblsa, \\0 );
sg13_hv_nmos #(.w({s['wmux']}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) mxr(rblsa, vmux, rbl, \\0 );
rppd #(.w({R_REF['w']}u), .l({R_REF['l']}u), .b({R_REF['b']}), .mm_ok(0)) rref(rbl2, \\0 , \\0 );
sg13_lv_pmos #(.w({s['wp']}u), .l({s['lp']}u), .ng(1), .mm_ok(0), .rfmode(0)) mp3(vclamp, mirr, vdd, vdd);
sg13_lv_nmos #(.w({s['wn']}u), .l({s['ln']}u), .ng(1), .mm_ok(0), .rfmode(0)) mnr(vclamp, vclamp, vr, \\0 );
sg13_lv_pmos #(.w({s['wp']}u), .l({s['lp']}u), .ng(1), .mm_ok(0), .rfmode(0)) mp2(sn, mirr, vdd, vdd);
sg13_lv_nmos #(.w({s['wn']}u), .l({s['ln']}u), .ng(1), .mm_ok(0), .rfmode(0)) mn1(sn, vclamp, blsa, \\0 );
sg13_hv_nmos #(.w({s['wmux']}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) mx(blsa, vmux, bl, \\0 );
sg13_lv_pmos #(.w({s['wpi']}u), .l(0.13u), .ng(1), .mm_ok(0), .rfmode(0)) pi(out, sn, vdd, vdd);
sg13_lv_nmos #(.w({s['wni']}u), .l(0.13u), .ng(1), .mm_ok(0), .rfmode(0)) ni(out, sn, \\0 , \\0 );
print dc v(bl) v(out) i(Vm) v(rbl)
dc Icell 1u 60u 0.1u
"""
    t = g.run(deck, timeout=900)[0]
    d = t["data"]
    icell, vbl, vout, iref, vrbl = d[:, 0], d[:, 1], d[:, 2], np.abs(d[:, 3]), d[:, 4]
    k = np.where((vout[:-1] < vdd / 2) & (vout[1:] >= vdd / 2))[0]
    if not k.size:
        return dict(ok=False)
    k = k[0]
    f = (vdd / 2 - vout[k]) / (vout[k + 1] - vout[k])
    itrip = icell[k] + f * (icell[k + 1] - icell[k])
    vtrip = vbl[k] + f * (vbl[k + 1] - vbl[k])
    gtrip = itrip / vtrip
    r_ref = float(np.median(vrbl / np.maximum(iref, 1e-12)))
    return dict(ok=True, i_trip_uA=round(itrip * 1e6, 3), v_bl_at_trip_V=round(vtrip, 4), g_trip_uS=round(gtrip * 1e6, 2),
                i_ref_uA=round(float(np.median(iref)) * 1e6, 3), r_ref_ohm=round(r_ref, 1), g_ref_uS=round(1e6 / r_ref, 2),
                margin_to_HRS_tail_uS=round(gtrip * 1e6 - TAILS_uS["HRS"], 2), margin_to_LRS3_tail_uS=round(TAILS_uS["LRS3"] - gtrip * 1e6, 2))


# ---------------------------------------------------------------- 3. test multiplexer
TM = dict(wn=10.0, wp=20.0, channels=16)


def mux_ron(corner, temp):
    deck = g.header(corner) + f"""
spice
.options temp={temp}
Vgn gn 0 dc 3.3
Vgp gp 0 dc 0
Vbp bp 0 dc 3.3
Vin nin 0 dc 0
Itest pad 0 dc 10u
.verilog
{p1.hv('n', TM['wn'], 'pad', 'gn', 'nin', '\\0 ')}
{p1.hv('p', TM['wp'], 'pad', 'gp', 'nin', 'bp')}
print dc v(nin) v(pad)
dc Vin 0 3.3 0.1
"""
    d = g.run(deck, timeout=900)[0]["data"]
    vin, vpad = d[:, 1], d[:, 2]
    ron = np.abs(vin - vpad) / 10e-6
    return dict(ron_max_ohm=round(float(ron.max()), 1), ron_at_0V=round(float(ron[0]), 1), ron_at_3p3V=round(float(ron[-1]), 1),
                worst_at_V=round(float(vin[int(np.argmax(ron))]), 2))


def mux_leak(corner, temp):
    """15 channels off, 3.3 V on their inputs, pad held at 0 V: total leakage into the pad."""
    n = TM["channels"] - 1
    deck = g.header(corner) + f"""
spice
.options temp={temp}
Vgn gn 0 dc 0
Vgp gp 0 dc 3.3
Vbp bp 0 dc 3.3
Vin nin 0 dc 3.3
Vpad pad0 0 dc 0
Rs pad0 pad 1e6
.verilog
sg13_hv_nmos #(.w({TM['wn']}u), .l(0.45u), .ng(1), .m({n}), .mm_ok(0), .rfmode(0)) mn(pad, gn, nin, \\0 );
sg13_hv_pmos #(.w({TM['wp'] / 2}u), .l(0.45u), .ng(1), .m({2 * n}), .mm_ok(0), .rfmode(0)) mp(pad, gp, nin, bp);
print op v(pad)
op
"""
    d = g.run(deck, timeout=900)[0]["data"]
    return dict(leak_nA=round(abs(float(d[0, 1])) / 1e6 * 1e9, 4))


def add_column_switch_bound():
    """exp_reset_gate.py bounds the reset current (final amplitude on the fully set device). The same switch at that
    bound, rounded up to 0.05 mA, added to an existing results file (run after exp_reset_gate.py)."""
    import math
    res = json.loads(OUT.read_text())
    rg = json.loads((ROOT / "results" / "gnucap_reset_gate.json").read_text())
    peak_mA = max(r.get("peak_current_bound_uA", 0) for r in rg.values()) / 1000
    i_mA = math.ceil(peak_mA * 20 - 1e-9) / 20
    p1.TG.update(wn=40.0, wp=80.0)
    res.pop("column_switch_0p7mA", None); res["summary"].pop("column_switch_0p7mA_drop_max_mV", None)
    res["column_switch_reset_bound"] = dict(reset_peak_bound_mA=round(peak_mA, 4), i_load_mA=i_mA,
        cases={f"{c} {T} C": p1.column_switch(c, T, i_mA * 1e-3) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125)})
    res["summary"]["column_switch_reset_bound_mA"] = i_mA
    res["summary"]["column_switch_reset_bound_drop_max_mV"] = max(v["drop_max_mV"] for v in res["column_switch_reset_bound"]["cases"].values())
    OUT.write_text(json.dumps(res, indent=1))
    print(res["summary"])


if __name__ == "__main__" and "--add-cs-bound" in sys.argv:
    add_column_switch_bound()
elif __name__ == "__main__":
    res = dict(r_ref=R_REF, tails_uS=TAILS_uS, sizes=dict(sense=sense.SIZES, column_switch=dict(wn=40.0, wp=80.0), test_mux=TM),
               ratio={}, column_switch={}, test_mux={})
    cases = [(c, T, "typ", 0.2, 1.2) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125)]
    cases += [("tt", 27, rc, 0.2, 1.2) for rc in ("bcs", "wcs")]
    cases += [(c, T, "typ", v, 1.2) for (c, T) in (("tt", 27), ("ss", 125), ("ff", -40)) for v in (0.18, 0.22)]
    cases += [("tt", 27, "typ", 0.2, v) for v in (1.08, 1.32)]
    cases += [("ss", 125, "wcs", 0.18, 1.08), ("ff", -40, "bcs", 0.22, 1.32)]
    for c, T, rc, vr, vdd in cases:
        k = f"{c} {T} C res {rc} vref {vr} vdd {vdd}"
        res["ratio"][k] = ratio_trip(c, T, rc, vr, vdd)
        print(k, res["ratio"][k], flush=True)
        OUT.write_text(json.dumps(res, indent=1))
    p1.TG.update(wn=40.0, wp=80.0)
    for c in ("tt", "ss", "ff", "sf", "fs"):
        for T in (-40, 27, 125):
            res["column_switch"][f"{c} {T} C"] = p1.column_switch(c, T)
            res["test_mux"][f"{c} {T} C"] = dict(mux_ron(c, T), **mux_leak(c, T))
            print(c, T, res["column_switch"][f"{c} {T} C"], res["test_mux"][f"{c} {T} C"], flush=True)
            OUT.write_text(json.dumps(res, indent=1))
    ok = [v for v in res["ratio"].values() if v.get("ok")]
    res["summary"] = dict(
        ratio_cases=len(res["ratio"]), ratio_all_trip=len(ok) == len(res["ratio"]),
        i_trip_min_uA=min(v["i_trip_uA"] for v in ok), i_trip_max_uA=max(v["i_trip_uA"] for v in ok),
        g_trip_min_uS=min(v["g_trip_uS"] for v in ok), g_trip_max_uS=max(v["g_trip_uS"] for v in ok),
        margin_HRS_min_uS=min(v["margin_to_HRS_tail_uS"] for v in ok), margin_LRS3_min_uS=min(v["margin_to_LRS3_tail_uS"] for v in ok),
        column_switch_drop_max_mV=max(v["drop_max_mV"] for v in res["column_switch"].values()),
        test_mux_ron_max_ohm=max(v["ron_max_ohm"] for v in res["test_mux"].values()),
        test_mux_leak_max_nA=max(v["leak_nA"] for v in res["test_mux"].values()))
    print(json.dumps(res["summary"], indent=1))
    OUT.write_text(json.dumps(res, indent=1))
