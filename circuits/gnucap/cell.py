"""1T1R cell in Gnucap: calibrated ReRAM Verilog-A model + the real IHP sg13_hv_nmos (PSP103).

Cell:  BL -- TE [ReRAM] BE -- x -- drain [NMOS] source -- SL,  gate = WL, bulk = ground.
SET  : positive pulse on BL, SL at 0.   RESET: positive pulse on SL, BL at 0.
"""
from __future__ import annotations

import numpy as np

import gnucap_run as g

L_UM = 0.45


def _cell(gap, w_um, gap_min=0.10, dev=None):
    """dev: optional device parameters of the Verilog-A model for this one device, e.g. dict(v0=1.2e9, Ea=1.05, I0=8e-4)
    (v0 in nm/s as in the model file); used for devices that differ from the nominal one."""
    extra = "".join(f", .{k}({v:.6g})" for k, v in (dev or {}).items())
    return (
        f"reram_stanford_ihp #(.gap_ini({gap:.6f}), .gap_min({gap_min}){extra}) r1(bl, x, gap);\n"
        f"sg13_hv_nmos #(.w({w_um}u), .l({L_UM}u), .ng(1), .mm_ok(0), .rfmode(0)) m1(x, wl, sl, \\0 );\n"
    )


def read_dc(gap, w_um, corner="tt", vg=1.7, v=0.2):
    """Read current (A) with the gap frozen (DC operating point)."""
    deck = g.header(corner) + f"""
spice
Vbl bl 0 dc {v}
Vsl sl 0 dc 0
Vwl wl 0 dc {vg}
.verilog
{_cell(gap, w_um)}
print dc i(Vbl) v(x)
dc Vbl {v} {v} 1
"""
    t = g.run(deck)[0]
    return float(-g.col(t, "i(Vbl)")[0])


def pulse(gap, w_um, vg, amp, polarity=+1, corner="tt", pw=1e-6, edge=10e-9, v_read=0.2, vg_read=1.7, trace=False, dtmax=0.2e-9, dev=None):
    """One programming pulse followed by a verify read in the same transient.
    Returns (gap_after_nm, verify_current_A[, table])."""
    n = 1e9
    t0 = 20e-9
    t1 = t0 + edge              # top of pulse starts
    t2 = t1 + pw                # top of pulse ends
    t3 = t2 + edge
    t4 = t3 + 20e-9             # word line moves to the read level
    t5 = t4 + edge
    t6 = t5 + 10e-9             # bit line moves to the read voltage
    t7 = t6 + edge
    t8 = t7 + 100e-9            # end of verify
    pul = f"pwl(0 0 {t0:.4e} 0 {t1:.4e} {amp} {t2:.4e} {amp} {t3:.4e} 0 {t8:.4e} 0)"
    if polarity > 0:
        vbl = f"pwl(0 0 {t0:.4e} 0 {t1:.4e} {amp} {t2:.4e} {amp} {t3:.4e} 0 {t6:.4e} 0 {t7:.4e} {v_read} {t8:.4e} {v_read})"
        vsl = "dc 0"
    else:
        vbl = f"pwl(0 0 {t6:.4e} 0 {t7:.4e} {v_read} {t8:.4e} {v_read})"
        vsl = pul
    vwl = f"pwl(0 0 10n {vg} {t4:.4e} {vg} {t5:.4e} {vg_read} {t8:.4e} {vg_read})"
    deck = g.header(corner) + f"""
spice
Vbl bl 0 {vbl}
Vsl sl 0 {vsl}
Vwl wl 0 {vwl}
.verilog
{_cell(gap, w_um, dev=dev)}
print tran v(gap) v(x) i(Vbl) v(bl) v(sl) v(wl)
tran 0 {t8:.4e} 5n {dtmax:.3e}
"""
    t = g.run(deck)[0]
    d = t["data"]
    if d.shape[0] < 10 or abs(d[-1, 0] - t8) > 6e-9:
        raise RuntimeError("transient did not finish: " + "; ".join(t["problems"][:3]) + t["raw"][-800:])
    # The model limits the gap to [gap_min, gap_max] with a window; with 1 ns steps Gnucap can step past the
    # upper limit during a fast reset (seen: up to 0.11 nm). The state is put back on the model's limit here.
    gap_after = min(max(float(d[-1, 1]), 0.10), 1.80)
    i_ver = float(-d[-2, 3])
    return (gap_after, i_ver, t) if trace else (gap_after, i_ver)


def ispva(gap, w_um, vg, target, polarity=+1, corner="tt", v0=0.5, v1=2.5, dv=0.1, pw=1e-6, dev=None):
    """Incremental-step pulse and verify (published IHP scheme: amplitude ramp, read after every pulse)."""
    n = 0
    i = None
    for amp in np.arange(v0, v1 + 1e-9, dv):
        gap, i = pulse(gap, w_um, vg, round(float(amp), 3), polarity, corner, pw, dev=dev)
        n += 1
        done = i >= target if polarity > 0 else i <= target
        if done:
            return dict(ok=True, amp=round(float(amp), 2), pulses=n, gap_nm=round(gap, 4), iread_uA=round(i * 1e6, 2))
    return dict(ok=False, amp=round(float(amp), 2), pulses=n, gap_nm=round(gap, 4), iread_uA=round(i * 1e6, 2))


def gap_for_current(i_target, w_um, corner="tt"):
    """Gap (nm) that gives the wanted read current through the 1T1R cell."""
    lo, hi = 0.2, 1.9
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if read_dc(mid, w_um, corner) > i_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
