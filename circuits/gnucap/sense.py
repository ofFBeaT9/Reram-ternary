"""First-cut read path for the digital mode (one bit line): current-mode sense amplifier with real PDK transistors.

  VDD 1.2 V -- PMOS mirror (reference current Iref) --> node sn --> clamp NMOS --> blsa --> 3.3 V column switch --> BL
  The clamp gate comes from a replica (diode NMOS standing on a 0.2 V reference, carrying Iref), so the bit line
  sits near 0.2 V in every process corner. Cell current > Iref pulls sn low (out = 1), cell current < Iref lets
  sn rise to VDD (out = 0).
All sizes are first guesses to be refined; references (0.2 V, Iref) are ideal sources here.
"""
import gnucap_run as g

SIZES = dict(wp=4.0, lp=1.0, wn=4.0, ln=0.5, wmux=10.0, wpi=1.0, wni=0.5)


def amp(mm=0, iref=25e-6, vref=0.2, ib=0.0, s=SIZES, vdd=1.2):
    """iref: trip current. ib: optional keep-alive current drawn from the bit line node so that the clamp
    transistor never runs dry (keeps the bit-line voltage closer to vref for small cell currents)."""
    return f"""
spice
Vdd vdd 0 dc {vdd}
Vref vr 0 dc {vref}
Vmux vmux 0 dc 3.3
Iref1 mirr 0 dc {iref + ib}
Iref2 vdd vclamp dc {iref + ib}
Ibleed blsa 0 dc {ib}
.verilog
sg13_lv_pmos #(.w({s['wp']}u), .l({s['lp']}u), .ng(1), .mm_ok({mm}), .rfmode(0)) mp1(mirr, mirr, vdd, vdd);
sg13_lv_pmos #(.w({s['wp']}u), .l({s['lp']}u), .ng(1), .mm_ok({mm}), .rfmode(0)) mp2(sn, mirr, vdd, vdd);
sg13_lv_nmos #(.w({s['wn']}u), .l({s['ln']}u), .ng(1), .mm_ok({mm}), .rfmode(0)) mnr(vclamp, vclamp, vr, \\0 );
sg13_lv_nmos #(.w({s['wn']}u), .l({s['ln']}u), .ng(1), .mm_ok({mm}), .rfmode(0)) mn1(sn, vclamp, blsa, \\0 );
sg13_hv_nmos #(.w({s['wmux']}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) mx(blsa, vmux, bl, \\0 );
sg13_lv_pmos #(.w({s['wpi']}u), .l(0.13u), .ng(1), .mm_ok({mm}), .rfmode(0)) pi(out, sn, vdd, vdd);
sg13_lv_nmos #(.w({s['wni']}u), .l(0.13u), .ng(1), .mm_ok({mm}), .rfmode(0)) ni(out, sn, \\0 , \\0 );
"""


def dc_trip(corner="tt", temp=None, **kw):
    """Sweep an ideal cell current; return table (Icell, v(bl), v(sn), v(out)). temp in degrees C (None: default 27)."""
    t = "" if temp is None else f".options temp={temp}\n"
    deck = g.header(corner, lv=True) + amp(**kw) + f"""
spice
{t}Icell bl 0 dc 0
.verilog
print dc v(bl) v(sn) v(out) v(vclamp)
dc Icell 1u 60u 0.25u
"""
    return g.run(deck)[0]


def read_tran(gap_sel, gap_unsel, corner="tt", w_um=4.5, n_unsel=71, t_wl=1e-9, t_end=12e-9, c_wire=30e-15, temp=None, **kw):
    """Transient row read: the bit line is already biased, the word line of the selected cell rises at t_wl.
    The other n_unsel cells of the column are lumped into one scaled cell with its word line at 0 V.
    Returns the table (Time, v(wl), v(bl), v(sn), v(out), i(Vdd))."""
    i0, rth = 854e-6 * n_unsel, 1500.0 / n_unsel
    t = "" if temp is None else f".options temp={temp}\n"
    deck = g.header(corner, lv=True) + amp(**kw) + f"""
spice
{t}Vwl wl 0 pwl(0 0 {t_wl:.3e} 0 {t_wl + 0.2e-9:.3e} 1.7 {t_end:.3e} 1.7)
Cw bl 0 {c_wire:.3e}
.verilog
reram_stanford_ihp #(.gap_ini({gap_sel:.5f})) rs(bl, xs, gs);
sg13_hv_nmos #(.w({w_um}u), .l(0.45u), .ng(1), .mm_ok(0), .rfmode(0)) ms(xs, wl, \\0 , \\0 );
reram_stanford_ihp #(.gap_ini({gap_unsel:.5f}), .I0({i0:.6e}), .Rth({rth:.6f})) ru(bl, xu, gu);
sg13_hv_nmos #(.w({w_um}u), .l(0.45u), .ng(1), .m({n_unsel}), .mm_ok(0), .rfmode(0)) mu(xu, \\0 , \\0 , \\0 );
print tran v(wl) v(bl) v(sn) v(out) i(Vdd) v(gs)
tran 0 {t_end:.3e} 0.05n 0.01n
"""
    return g.run(deck, timeout=1800)[0]
