"""Re-simulation of the word-line driver as drawn in the pitch-matched column (layout/wld_pitch.py), 10 October 2026.

Devices: as extracted by the PDK's KLayout LVS from layout/tcim_wld72.gds (layout/ihp_checks/lvs_tcim_wld72/
tcim_wld72_extracted.cir): NMOS 6/0.45 um and PMOS 12/0.45 um, one finger each, drain diffusion 0.34 um long
(the Gnucap wrapper's z1, so its drain junction equals the drawn one; the PMOS enters as two 6 um copies because the
wrapper accepts at most 10 um per device).
Wiring, computed from the drawn geometry with the SG13G2 process specification (maximum values: salicided GatPoly
7.8 ohm/sq, Metal1 0.135 ohm/sq, Metal1 area capacitance 69 aF/um2 over Activ and 43 aF/um2 over field; no fringe
data are published, so the line capacitances are also run x3):
  input: GatPoly from the contact to the NMOS gate (0.25 um), along the NMOS gate (6 um), across to the PMOS (1.3 um),
         along the PMOS gate (12 um), 0.45 um wide;
  output: Metal1 0.26 um wide from the NMOS drain to the array edge, 21.3 um, 18 um of it over the two drains.
Load: the row of the drawn array exactly as in circuits/gnucap/periphery.py (48 select gates, 454 fF, GatPoly word line
of 509 squares at 7.8 ohm/sq with +3100 ppm/K, 24 RC sections).
Compared with the schematic run of revision 4.3 (results/gnucap_periphery.json). Writes results/wld_resim.json."""
import json
from pathlib import Path
import numpy as np
import gnucap_run as g
import periphery as P

OUT = Path(__file__).resolve().parents[2] / "results" / "wld_resim.json"
RS_POLY, RS_M1 = 7.8, 0.135
C_M1_ACT, C_M1_FIELD = 69e-18, 43e-18
W_POLY, W_M1 = 0.45, 0.26
R_IN_PAD = (0.25 + 0.0) / W_POLY * RS_POLY            # contact to the NMOS gate edge
R_IN_N = 6.0 / W_POLY * RS_POLY                         # along the NMOS gate
R_IN_GAP = 1.3 / W_POLY * RS_POLY                       # to the PMOS
R_IN_P = 12.0 / W_POLY * RS_POLY                        # along the PMOS gate
R_OUT = 21.3 / W_M1 * RS_M1
C_OUT = (18.0 * W_M1 * C_M1_ACT + 3.3 * W_M1 * C_M1_FIELD)


def run(corner, temp, vrail, kc=1.0):
    r_tot = P.WL_SQUARES * P.RS_POLY * (1 + P.TC_POLY * (temp - 25))
    ladder = "\n".join(f"R{k} n{k} n{k + 1} {r_tot / P.N_SEG:.4g}\nC{k} n{k + 1} 0 {P.C_ROW / P.N_SEG:.4e}" for k in range(P.N_SEG))
    deck = g.header(corner) + f"""
spice
{P.opt(temp)}Vr vr 0 dc {vrail}
Vin in 0 pwl(0 3.3 2n 3.3 2.05n 0 22n 0 22.05n 3.3 40n 3.3)
Rp0 in gn0 {R_IN_PAD:.4g}
Rp1 gn0 gn1 {R_IN_N / 2:.4g}
Rp2 gn1 gp0 {R_IN_N / 2 + R_IN_GAP + R_IN_P / 2:.4g}
Rp3 gp0 gp1 {R_IN_P / 2:.4g}
Ro out n0 {R_OUT:.4g}
Co out 0 {kc * C_OUT:.4e}
{ladder}
.verilog
sg13_hv_nmos #(.w(6u), .l(0.45u), .ng(1), .m(1), .mm_ok(0), .rfmode(0)) mn(out, gn1, \\0 , \\0 );
sg13_hv_pmos #(.w(6u), .l(0.45u), .ng(1), .m(2), .mm_ok(0), .rfmode(0)) mp(out, gp0, vr, vr);
print tran v(out) v(n{P.N_SEG})
tran 0 40n 0.01n
"""
    d = g.run(deck, timeout=900)[0]["data"]
    t = d[:, 0]
    res = dict(r_line_ohm=round(r_tot, 1))
    for tag, v in (("near", d[:, 1]), ("far", d[:, 2])):
        t10, t90 = P.cross(t, v, 0.1 * vrail, True, 2e-9), P.cross(t, v, 0.9 * vrail, True, 2e-9)
        f90, f10 = P.cross(t, v, 0.9 * vrail, False, 22e-9), P.cross(t, v, 0.1 * vrail, False, 22e-9)
        res[f"{tag}_rise_10_90_ns"] = None if None in (t10, t90) else round((t90 - t10) * 1e9, 3)
        res[f"{tag}_fall_90_10_ns"] = None if None in (f90, f10) else round((f10 - f90) * 1e9, 3)
        res[f"{tag}_settle_90_ns"] = None if t90 is None else round((t90 - 2.025e-9) * 1e9, 3)
    return res


if __name__ == "__main__":
    old = json.loads((OUT.parent / "gnucap_periphery.json").read_text())["wl_driver"]
    res = dict(wiring=dict(r_in_total_ohm=round(R_IN_PAD + R_IN_N + R_IN_GAP + R_IN_P, 1), r_out_ohm=round(R_OUT, 2),
                           c_out_fF=round(C_OUT * 1e15, 3)), runs={})
    for c, T in (("tt", 27), ("ss", 125), ("ff", -40), ("ss", 27), ("ff", 27)):
        for vr in (1.7, 3.3):
            for kc in (1.0, 3.0):
                r = run(c, T, vr, kc)
                ref = old.get(f"{c} {T} C {vr} V")
                r["rev43_far_settle_90_ns"] = ref["far_settle_90_ns"] if ref else None
                r["rev43_far_fall_90_10_ns"] = ref["far_fall_90_10_ns"] if ref else None
                res["runs"][f"{c} {T} C {vr} V cx{kc:g}"] = r
                print(c, T, vr, kc, r, flush=True)
    R = list(res["runs"].values())
    res["summary"] = dict(far_settle_90_max_ns=max(x["far_settle_90_ns"] for x in R),
                          far_fall_max_ns=max(x["far_fall_90_10_ns"] for x in R),
                          max_change_vs_rev43_ns=max(abs(x["far_settle_90_ns"] - x["rev43_far_settle_90_ns"]) for x in R if x["rev43_far_settle_90_ns"]))
    OUT.write_text(json.dumps(res, indent=1))
    print(res["summary"])
