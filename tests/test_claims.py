"""Every number quoted in sections 18, 20, 21, 22, 23 and 24 of the roadmap, checked against the stored results.
Section 20 describes the audit of 6 October and is checked against the files of that day in results/rev4;
the logic numbers of sections 18, 19 and 21 are those of revision 4.1 and are checked against results/rev41;
section 22 (revision 4.2) against results/rev42; section 23 (revision 4.3) against results/rev43; section 24 (revision 4.4)
against the present results.
Run after any re-run of the experiments:  python3 tests/test_claims.py   (exit status 1 if a quoted number is stale)."""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
J = lambda n: json.loads((R / n).read_text())
J41 = lambda n: json.loads((R / "rev41" / n).read_text())     # files of revision 4.1, which sections 18 to 21 quote
bad = []
N_CLAIMS = 0


def claim(text, quoted, actual, tol):
    global N_CLAIMS
    N_CLAIMS += 1
    ok = abs(quoted - actual) <= tol
    if not ok:
        bad.append(text)
    print(("ok    " if ok else "STALE ") + f"{text}: quoted {quoted}, results {actual:.6g}")


# ---- device model
s = J("model_three_solvers.json")
claim("three solvers, ramp spread (mV)", 0.26, s["spread"]["A_mV"], 0.01)
claim("three solvers, gap spread (pm)", 0.5, s["spread"]["B_pm"], 0.05)
claim("three solvers, set time spread (%)", 0.11, s["spread"]["C_percent"], 0.01)
claim("three solvers, reset time spread (%)", 1.0, s["spread"]["D_percent"], 0.05)
c = J("device_calibration.json")
claim("re-fitted v0 (m/s)", 2.79, c["calibrated"]["v0_m_per_s"], 0.005)
claim("HRS gap after 1 s at 0.2 V: shift (pm)", 0.006, (1.8 - c["read_disturb_gap_nm"]["1.0"]) * 1e3, 0.001)
claim("HRS gap after 1000 s at 0.2 V: shift (pm)", 6.0, (1.8 - c["read_disturb_gap_nm"]["1000.0"]) * 1e3, 0.3)

# ---- select transistor and programming
z = J("device_sizing_psp.json")
for w, vgs, rst in ((1.5, (1.60, 2.15, 2.95), None), (3.0, (1.20, 1.45, 1.70), (2.1, 17)), (4.5, (1.10, 1.30, 1.45), (1.4, 10)), (6.0, (1.05, 1.20, 1.30), (1.2, 8))):
    row = z[f"W{w}_tt"]
    for name, vg in zip(("LRS1", "LRS2", "LRS3"), vgs):
        claim(f"W {w} um, gate voltage for {name}", vg, row[name]["vg"], 0.001)
    r = row["reset_LRS3_vg2.7"]
    if rst is None:
        claim(f"W {w} um, reset fails at 2.7 V and 3.3 V (0 = fails)", 0, int(r["ok"]) + int(row["reset_LRS3_vg3.3"]["ok"]), 0)
    else:
        claim(f"W {w} um, reset amplitude", rst[0], r["amp"], 0.001); claim(f"W {w} um, reset pulses", rst[1], r["pulses"], 0)
for w, rk in ((1.5, (13.5, 10.0, 7.2, 323)),):
    cur = z[f"W{w}_tt"]["read_uA_at_published_gaps"]
    for g, q in zip(("0.95nm", "0.85nm", "0.73nm", "1.88nm"), rk):
        claim(f"1T1R resistance at {g}, W {w} um (kOhm)", q, 0.2 / cur[g] * 1e3, 0.6 if q > 100 else 0.06)
t = J("gnucap_transistor.json")
for corner, q in (("tt", 547), ("ss", 479), ("ff", 619)):
    claim(f"saturation current {corner} (uA/um)", q, t[f"{corner}_W4.5"]["idsat_per_um_uA"], 0.6)
for w, q in ((1.5, 1.76), (3.0, 0.85), (4.5, 0.57)):
    claim(f"on-resistance at read, W {w} um (kOhm)", q, t[f"tt_W{w}"]["ron_vg1v7_ohm"] / 1e3, 0.006)
g = J("gnucap_cell_W4.5.json")
quoted = {"tt": ((18.2, 31.1, 44.0), (44.2, 1.3, 9), (1.4, 10)), "ss": ((13.8, 27.5, 38.7), (45.6, 1.5, 11), (1.6, 12)), "ff": ((18.2, 32.5, 44.9), (50.3, 1.3, 9), (1.4, 10))}
for corner, (levels, two, rst) in quoted.items():
    for name, q in zip(("LRS1", "LRS2", "LRS3"), levels):
        claim(f"{corner} set {name} with typical gate voltage (uA)", q, g[corner][f"set_{name}"]["iread_uA"], 0.06)
    r = g[corner]["set_LRS3_vg1.7"]
    claim(f"{corner} two-state set current (uA)", two[0], r["iread_uA"], 0.06); claim(f"{corner} two-state amplitude", two[1], r["amp"], 0.001); claim(f"{corner} two-state pulses", two[2], r["pulses"], 0)
    r = g[corner]["reset_LRS3_vg2.7"]
    claim(f"{corner} reset amplitude", rst[0], r["amp"], 0.001); claim(f"{corner} reset pulses", rst[1], r["pulses"], 0)
claim("slow corner misses every level (number of levels reached)", 0, sum(g["ss"][f"set_{n}"]["ok"] for n in ("LRS1", "LRS2", "LRS3")), 0)
pc = J("gnucap_pulse_currents.json")
claim("set current per device (mA)", 0.50, pc["set, gate 1.7 V, 1.3 V pulse from 1.8 nm"]["peak_uA"] / 1e3, 0.005)
claim("reset peak current, 1.4 V (mA)", 0.52, pc["reset, gate 2.7 V, 1.4 V pulse from 0.6467 nm"]["peak_uA"] / 1e3, 0.005)
claim("reset peak current, worst case (mA)", 0.60, pc["reset, gate 2.7 V, 2.5 V pulse from 0.6467 nm (worst case)"]["peak_uA"] / 1e3, 0.005)

# ---- tile
a = J("array_analog_error.json")
rows = (("LRS3 | D: BL TopMetal1, SL TopMetal1, both ends | rows/read 72 | spread x1", "cal", 0.41, 77, 99.97, 1.7),
        ("LRS3 | D: BL TopMetal1, SL TopMetal1, both ends | rows/read 72 | spread x2", "cal", 0.75, 49, 95.4, 3.0),
        ("LRS3 | A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end | rows/read 72 | spread x1", "raw", 0.55, 63, 99.3, 2.2),
        ("LRS3 | A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end | rows/read 72 | spread x1", "cal", 0.45, 73, 99.9, 2.1),
        ("LRS1 | D: BL TopMetal1, SL TopMetal1, both ends | rows/read 72 | spread x1", "cal", 1.20, 33, 79, 5.1),
        ("LRS1 | D: BL TopMetal1, SL TopMetal1, both ends | rows/read 72 | spread x2", "cal", 2.26, 18, 50, 10.1))
for key, kind, rms, ex, w1, mx in rows:
    r = a[key][kind]
    claim(f"analog RMS [{key[:26]}.. {kind}]", rms, r["rms"], 0.006); claim("   exact (%)", ex, 100 * r["p_exact"], 0.6)
    claim("   within +-1 (%)", w1, 100 * r["p_within1"], 0.06 if w1 > 99 else 0.6); claim("   largest", mx, r["max_abs"], 0.06)
claim("clamp 20 ohm, uncalibrated RMS", 0.46, a["LRS3 | D | rows/read 72 | spread x1 | clamp input resistance 20 ohm"]["raw"]["rms"], 0.006)
claim("clamp 50 ohm, uncalibrated RMS", 0.67, a["LRS3 | D | rows/read 72 | spread x1 | clamp input resistance 50 ohm"]["raw"]["rms"], 0.006)
d = J("array_digital_mode.json")
for key, we, pe in (("mc_LRS3_x1_vos0mV", 0, 0), ("mc_LRS3_x2_vos2mV", 0, 0), ("mc_LRS3_x3_vos2mV", 4, 24), ("mc_LRS1_x1_vos0mV", 2, 14), ("mc_LRS1_x2_vos2mV", 4616, 600)):
    claim(f"digital mode {key}: wrong weights", we, d[key]["weight_errors"], 0); claim("   products with an error", pe, d[key]["products_with_any_error"], 0)
n = J("array_network.json")
claim("network software accuracy (%)", 94.7, 100 * n["test_acc_software"], 0.05)
hw = n["hardware"]
claim("network digital accuracy (%)", 94.7, 100 * hw["digital, LRS3, published spread, poor wiring"]["acc_mean"], 0.05)
accs = [100 * v["acc_mean"] for k, v in hw.items() if k.startswith("analog")]
claim("network analog accuracy, lowest (%)", 94.6, min(accs), 0.05); claim("network analog accuracy, highest (%)", 95.3, max(accs), 0.05)
mm = [100 * v["layer1_result_mismatch"] for k, v in hw.items() if k.startswith("analog")]
claim("first-layer sums differing, lowest (%)", 25, min(mm), 0.6); claim("first-layer sums differing, highest (%)", 83, max(mm), 0.6)

# ---- read path
se = J("gnucap_sense.json")
trips = [v["trip_uA"] for v in se["dc"].values()]
claim("trip current, lowest corner (uA)", 24.61, min(trips), 0.005); claim("trip current, highest corner (uA)", 24.66, max(trips), 0.005)
tr = se["tran"]
claim("LRS3 mean, output delay (ns)", 2.1, tr["tt | LRS3 mean 43.6 uA | others LRS3"]["t_out_ns"], 0.01)
claim("LRS3 -6 sigma, typical (ns)", 2.9, tr["tt | LRS3 mean-6sigma 34.3 uA | others LRS3"]["t_out_ns"], 0.01)
claim("LRS3 -6 sigma, slow (ns)", 3.1, tr["ss | LRS3 mean-6sigma 34.3 uA | others LRS3"]["t_out_ns"], 0.01)
claim("LRS3 -6 sigma, fast (ns)", 2.75, tr["ff | LRS3 mean-6sigma 34.3 uA | others LRS3"]["t_out_ns"], 0.01)
claim("HRS +6 sigma never trips (number of runs that tripped)", 0, sum(v["t_out_ns"] is not None for k, v in tr.items() if k.split(" | ")[1].startswith(("HRS", "reset target"))), 0)
claim("bit line, mean HRS cell (V)", 0.29, tr["tt | HRS mean 2.85 uA | others LRS3"]["bl_end_V"], 0.005)
claim("bit line, HRS +6 sigma (V)", 0.23, tr["tt | HRS mean+6sigma 14 uA | others LRS3"]["bl_end_V"], 0.005)
claim("bit line, idle (V)", 0.32, tr["tt | HRS mean 2.85 uA | others LRS3"]["bl_idle_V"], 0.005)
mc = J("gnucap_sense_mc.json")
claim("trip current mismatch, mean (uA)", 24.64, mc["mean_uA"], 0.006); claim("trip current mismatch, sigma (uA)", 0.24, mc["sigma_uA"], 0.005)
claim("trip current mismatch, min (uA)", 24.03, mc["min_uA"], 0.006); claim("trip current mismatch, max (uA)", 25.37, mc["max_uA"], 0.006)
claim("Monte Carlo runs", 200, mc["n"], 0)
rd = J("read_disturb.json")["HRS at the published mean current (gap 1.4526 nm)"]["bias"]
claim("reads to +10 % at 0.20 V (1e11)", 7, rd["0.20 V"]["reads_of_4ns"] / 1e11, 0.5); claim("reads to +10 % at 0.29 V (1e10)", 5, rd["0.29 V"]["reads_of_4ns"] / 1e10, 0.05)

# ---- digital and energy
sy = J41("synth_baseline.json")
claim("TCIM0 with serial port: cells", 7560, sy["tcim_top"]["cells"], 0); claim("   flip-flops", 844, sy["tcim_top"]["flops"], 0); claim("   area (mm2)", 0.111, sy["tcim_top"]["area_um2"] / 1e6, 0.0005)
core = sy["tcim_core_digital_product"]
claim("TCIM0 core: cells", 7146, core["cells"], 0); claim("   flip-flops", 668, core["flops"], 0); claim("   area (mm2)", 0.098, core["area_um2"] / 1e6, 0.0005)
claim("   pJ per cycle", 27.8, core["e_total_pJ_per_cycle"], 0.06); claim("   of which clock", 20.4, core["e_clock_pJ"], 0.06)
claim("dot-product block: cells", 680, sy["tmac24"]["cells"], 0); claim("   pJ per step", 6.65, sy["tmac24"]["e_total_pJ_per_cycle"], 0.006)
claim("flip-flop tile: cells", 12452, sy["dtile72x24"]["cells"], 0); claim("   flip-flops", 3848, sy["dtile72x24"]["flops"], 0)
claim("   area (mm2)", 0.322, sy["dtile72x24"]["area_um2"] / 1e6, 0.0005); claim("   nJ per product", 10.1, sy["dtile72x24"]["e_product_pJ"] / 1e3, 0.06)
e = J41("energy_system.json")
claim("cell currents at 0.2 V (nJ)", 0.03, e["window_4ns"]["array_at_0p2V_nJ"], 0.006); claim("sense amplifiers, 4 ns (nJ)", 0.19, e["window_4ns"]["sense_amplifiers_nJ"], 0.006)
claim("sense amplifiers, 10 ns (nJ)", 0.49, e["window_10ns"]["sense_amplifiers_nJ"], 0.006); claim("word lines (nJ)", 0.06, e["word_lines_nJ"], 0.006)
claim("digital logic (nJ)", 3.5, e["digital_logic_as_synthesized"]["nJ_per_product"], 0.06); claim("clock cycles per product", 123, e["digital_logic_as_synthesized"]["cycles"], 0.6)
claim("72 dot-product steps (nJ)", 0.48, e["digital_yardsticks"]["tmac24_72_steps_nJ"], 0.006)
ae = J("array_energy.json")["LRS3"]
claim("analog mode, supply energy at 200 ns per phase (nJ)", 9, ae["sum_power_analog_mW"] * 1e-3 * 6 * 200e-9 * 1e9, 0.3)
claim("rows read per product", 47.9, ae["reads_digital"], 0.06)
p = J("pdk_check.json")["summary"]
claim("PDK reference tests identical", 26, p["identical"], 0)
claim("sweeps compared with the PDK's ngspice reference", 16, p["ngspice_sweeps"], 0); claim("   points above 100 nA", 4264, p["ngspice_points"], 0)
claim("   largest relative difference below 0.1 % (1 = yes)", 1, int(p["ngspice_max_rel_diff"] < 1e-3), 0)

# ---- test bench and fault campaign of the present logic (sections 18.7 and 21)
import re
def tb_log(path):
    t = path.read_text(); m = re.search(r"(\d+) checks, (\d+) failures", t)
    return int(m.group(1)), int(m.group(2)), int(re.search(r"(\d+) clock cycles", t).group(1)), int("TEST PASSED" in t), t
n, fail, cyc, ok, _ = tb_log(R / "rev41" / "rtl_test.log")
claim("test bench: checks", 81966, n, 0); claim("   failures", 0, fail, 0)
claim("   clock cycles (million)", 44.8, cyc / 1e6, 0.05); claim("   test passed (1 = yes)", 1, ok, 0)
n, fail, cyc, ok, t = tb_log(R / "rev41" / "rtl_test_pnx.log")
claim("test bench, BSD-PNX build: checks", 81966, n, 0); claim("   failures", 0, fail, 0); claim("   test passed in that code (1 = yes)", 1, int(ok and "BSD-PNX" in t), 0)
sp = {int(a): int(b) for a, b in re.findall(r"sck = clk/(\d+)\): (\d+) of 200", (R / "spi_speed.log").read_text())}
claim("serial clock at clk/4: wrong transfers of 200", 200, sp[4], 0); claim("   at clk/6", 0, sp[6], 0); claim("   at clk/8", 0, sp[8], 0)
mu = J41("rtl_mutation.json")
claim("mutation test: faults", 69, mu["faults"], 0); claim("   detected", 69, mu["detected"], 0)
mp = J41("rtl_mutation_pnx.json")
claim("mutation test, BSD-PNX build: faults", 75, mp["faults"], 0); claim("   detected", 75, mp["detected"], 0)

# ---- section 20, the audit of 6 October: against the files kept from that day
A = R / "rev4"
n, fail, cyc, ok, _ = tb_log(A / "rtl_test.log")
claim("audit: test bench checks", 71598, n, 0); claim("   failures", 0, fail, 0); claim("   clock cycles (million)", 44.8, cyc / 1e6, 0.05)
am = json.loads((A / "rtl_mutation.json").read_text())
claim("audit: faults", 66, am["faults"], 0); claim("   detected by the revision 4 test bench", 66, am["detected"], 0)
m3 = J("rtl_mutation_rev3.json")
claim("   detected by the revision 3 test bench", 36, m3["detected"], 0)
asy = json.loads((A / "synth_baseline.json").read_text()); aen = json.loads((A / "energy_system.json").read_text())
claim("revision 4: cells with serial port", 7737, asy["tcim_top"]["cells"], 0); claim("   core cells", 7234, asy["tcim_core_digital_product"]["cells"], 0)
claim("   area (mm2)", 0.1116, asy["tcim_top"]["area_um2"] / 1e6, 0.00005)
claim("   pJ per cycle", 27.3, aen["digital_logic_as_synthesized"]["pJ_per_cycle"], 0.06); claim("   nJ per product", 3.43, aen["digital_logic_as_synthesized"]["nJ_per_product"], 0.006)

# ---- section 21: timing before layout, proofs, the conversion alone
claim("revision 4.1: area with serial port (mm2)", 0.1108, sy["tcim_top"]["area_um2"] / 1e6, 0.00005)
claim("   pJ per cycle", 27.8, e["digital_logic_as_synthesized"]["pJ_per_cycle"], 0.06); claim("   nJ per product", 3.50, e["digital_logic_as_synthesized"]["nJ_per_product"], 0.006)
st = J41("sta.json")["runs"]
C = lambda tag, corner: st[tag]["corners"][corner]
T, SL, FA = "typ_1p20V_25C", "slow_1p08V_125C", "fast_1p32V_m40C"
r4 = C("ihp_rev4", T)
claim("timing, revision 4 logic: setup slack (ns)", -4.02, r4["setup_wns_ns"], 0.006); claim("   worst path (ns)", 13.9, r4["worst_path"]["arrival_ns"], 0.06)
claim("   slack of the next-worst register (ns)", 4.5, sorted(r4["worst_slack_by_register_ns"].values())[1], 0.06)
claim("   cells on that path", 96, r4["worst_path"]["cell_stages"], 0); claim("   cells in the netlist", 8114, st["ihp_rev4"]["netlist"]["cells"], 0)
for tag, cells, rows in (("ihp", 7951, ((T, 4.67, 3.3, 0.18), (SL, 3.35, 5.2, 0.29), (FA, 5.47, 2.2, 0.12))),
                         ("ihp_pnx", 8238, ((T, 4.82, 3.5, 0.18), (SL, 3.59, 5.4, 0.29), (FA, 5.58, 2.3, 0.12))),
                         ("sky130", 8014, (("tt_1p80V_25C", 2.62, 5.1, 0.33),))):
    claim(f"timing, {tag}: cells", cells, st[tag]["netlist"]["cells"], 0)
    for corner, setup, r2r, hold in rows:
        x = C(tag, corner)
        claim(f"   {corner}: setup slack (ns)", setup, x["setup_wns_ns"], 0.006)
        claim(f"   {corner}: longest register-to-register path (ns)", r2r, x["worst_register_to_register"]["arrival_ns"], 0.06)
        claim(f"   {corner}: hold slack (ns)", hold, x["hold_wns_ns"], 0.006)
claim("timing: flip-flops", 844, st["ihp"]["netlist"]["flip_flops"], 0); claim("   nets above fan-out 8 (IHP)", 431, C("ihp", T)["limit_violations"]["data_fanout"], 0)
claim("   area of the timing-driven netlist, IHP (mm2)", 0.114, st["ihp"]["netlist"]["area_um2"] / 1e6, 0.0005)
claim("   area of the timing-driven netlist, SKY130 (mm2)", 0.063, st["sky130"]["netlist"]["area_um2"] / 1e6, 0.0005)
eq = J41("equiv.json")
claim("proof: comparison points", 2410, eq["equivalence_points"], 0); claim("   unproven", 0, eq["unproven"], 0)
claim("   table equals definition in both codes (2 = both)", 2, int(eq["table_equals_definition_default"]) + int(eq["table_equals_definition_pnx"]), 0)
claim("   place-and-route source: unproven points", 0, eq["place_and_route_source"]["unproven"], 0)
cv = J41("conv_study.json")
claim("conversion alone, chain of dividers (ns)", 12.3, cv["chain"]["path_ns"], 0.06); claim("   cells", 482, cv["chain"]["cells_with_22_flip_flops"] - 22, 0)
claim("conversion alone, table (ns)", 1.7, cv["table"]["path_ns"], 0.06); claim("   cells", 392, cv["table"]["cells_with_22_flip_flops"] - 22, 0)

# ---- cell footprint, row pitch (audit)
fp = J("cell_footprint.json")
claim("cell footprint: row pitch (um)", 1.085, fp["row_pitch_um"], 0.0005); claim("   device pitch (um)", 4.71, fp["device_pitch_um"], 0.005)
claim("   area per device (um2)", 5.1, fp["area_per_device_um2"], 0.06); claim("   array, rule count (mm2)", 0.018, fp["array_area_mm2"], 0.0005)
claim("   array, assumed pitch (mm2)", 0.023, fp["assumed_in_tile_model"]["array_area_mm2"], 0.0005)
claim("   block height (um)", 78, fp["array_height_um"], 0.6); claim("   block width (um)", 226, fp["array_width_um"], 0.6)
claim("   flip-flop storage (mm2)", 0.17, fp["flipflop"]["storage_mm2"], 0.005); claim("   contacts that fit per terminal", 13, fp["contacts"]["fit_in_width"], 0)
pt = J("array_pitch.json")
claim("row pitch 2.0 um, thin metal, uncalibrated RMS", 0.55, pt["A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end | row pitch 2 um"]["raw"]["rms"], 0.006)
claim("row pitch 1.085 um, thin metal, uncalibrated RMS", 0.46, pt["A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end | row pitch 1.085 um"]["raw"]["rms"], 0.006)
ind = J("audit_independent.json")
claim("independent re-derivations", 9, len(ind), 0); claim("   of which agree", 9, sum(x["passed"] for x in ind), 0)

# ---- section 22 (revision 4.2): the files of revision 4.2, kept in results/rev42
R42 = R / "rev42"
J42 = lambda n: json.loads((R42 / n).read_text())
import re as _re
Q2 = J42("pnr.json")["platforms"]; PI, PS = Q2["ihp-sg13g2"], Q2["sky130hd"]
def tb2(name):
    t = (R42 / name).read_text(); m = _re.search(r"(\d+) checks, (\d+) failures", t)
    return int(m.group(1)), int(m.group(2)), int("TEST PASSED" in t)
claim('4.2 rtl_test.log: checks', 82512, tb2('rtl_test.log')[0], 0)
claim('4.2 rtl_test.log: failures', 0, tb2('rtl_test.log')[1], 0)
claim('4.2 rtl_test_pnx.log: checks', 82512, tb2('rtl_test_pnx.log')[0], 0)
claim('4.2 rtl_test_pnx.log: failures', 0, tb2('rtl_test_pnx.log')[1], 0)
claim('4.2 rtl_test_verilator.log: checks', 82512, tb2('rtl_test_verilator.log')[0], 0)
claim('4.2 rtl_test_verilator.log: failures', 0, tb2('rtl_test_verilator.log')[1], 0)
claim('4.2 rtl_test_verilator_pnx.log: checks', 82512, tb2('rtl_test_verilator_pnx.log')[0], 0)
claim('4.2 rtl_test_verilator_pnx.log: failures', 0, tb2('rtl_test_verilator_pnx.log')[1], 0)
claim('4.2 gls_ihp_routed.log: checks', 82512, tb2('gls_ihp_routed.log')[0], 0)
claim('4.2 gls_ihp_routed.log: failures', 0, tb2('gls_ihp_routed.log')[1], 0)
claim('4.2 gls_sky130_routed.log: checks', 82512, tb2('gls_sky130_routed.log')[0], 0)
claim('4.2 gls_sky130_routed.log: failures', 0, tb2('gls_sky130_routed.log')[1], 0)
claim('4.2 gate-level fault: failures (must be > 0, quoted as detected = 1)', 1, int(tb2("gls_ihp_fault_xnor.log")[1] > 0), 0)
claim('4.2 mutation: faults', 74, J42("rtl_mutation.json")["faults"], 0)
claim('4.2 mutation: detected', 74, J42("rtl_mutation.json")["detected"], 0)
claim('4.2 mutation BSD-PNX: faults', 80, J42("rtl_mutation_pnx.json")["faults"], 0)
claim('4.2 mutation BSD-PNX: detected', 80, J42("rtl_mutation_pnx.json")["detected"], 0)
claim('4.2 formal faults caught', 9, sum(x["caught"] for x in J42("formal_faults.json")), 0)
claim('4.2 lint warnings', 0, len(_re.findall("%Warning", (R42 / "lint.log").read_text())), 0)
claim('4.2 P&R source unproven points', 0, J42("equiv.json")["place_and_route_source"]["unproven"], 0)
claim('4.2 energy per product (nJ)', 1.54, J42("energy_system.json")["digital_logic_as_synthesized"]["nJ_per_product"], 0.006)
claim('4.2 cycles per product', 49.7, J42("energy_system.json")["digital_logic_as_synthesized"]["cycles"], 0.06)
claim('4.2 IHP after layout typ_1p20V_25C: setup slack (ns)', 3.91, PI["post_route_sta"]["typ_1p20V_25C"]["setup_wns_ns"], 0.006)
claim('4.2 IHP after layout typ_1p20V_25C: hold slack (ns)', 0.147, PI["post_route_sta"]["typ_1p20V_25C"]["hold_wns_ns"], 0.0006)
claim('4.2 IHP after layout slow_1p08V_125C: setup slack (ns)', 1.9, PI["post_route_sta"]["slow_1p08V_125C"]["setup_wns_ns"], 0.006)
claim('4.2 IHP after layout slow_1p08V_125C: hold slack (ns)', 0.263, PI["post_route_sta"]["slow_1p08V_125C"]["hold_wns_ns"], 0.0006)
claim('4.2 IHP after layout fast_1p32V_m40C: setup slack (ns)', 5.01, PI["post_route_sta"]["fast_1p32V_m40C"]["setup_wns_ns"], 0.006)
claim('4.2 IHP after layout fast_1p32V_m40C: hold slack (ns)', 0.079, PI["post_route_sta"]["fast_1p32V_m40C"]["hold_wns_ns"], 0.0006)
claim('4.2 SKY130 after layout: setup slack (ns)', 1.85, PS["post_route_sta"]["tt_1p80V_25C"]["setup_wns_ns"], 0.006)
claim('4.2 IHP DRC markers', 5, PI["drc_violations"], 0)
claim('4.2 SKY130 DRC violations', 0, PS["drc_violations"], 0)
claim('4.2 SKY130 LVS match (1 = yes)', 1, int(PS["lvs"] == "netlists match (KLayout)"), 0)
claim('4.2 IHP standard cells', 12033, PI["stdcells"], 0)
claim('4.2 IHP block area (mm2)', 0.434, PI["die_area_um2"] * 1e-6, 0.0006)
claim('4.2 layout device pitch (um)', 4.75, J42("cell_layout.json")["device_pitch_um"], 0.0005)
claim('4.2 layout tile (mm2)', 0.0206, J42("cell_layout.json")["tile_estimate"]["area_mm2"], 6e-05)
claim('4.2 layout DRC clean (1 = yes)', 1, int("Passed" in (R42 / "cell_layout_drc.txt").read_text()), 0)
claim('4.2 sense trip min (uA)', 24.24, J42("gnucap_sense_env.json")["summary"]["trip_min_uA"], 0.006)
claim('4.2 sense trip max (uA)', 24.86, J42("gnucap_sense_env.json")["summary"]["trip_max_uA"], 0.006)
claim('4.2 sense margin min (uA)', 9.44, J42("gnucap_sense_env.json")["summary"]["margin_min_uA"], 0.006)
claim('4.2 word line far settle max (ns)', 4.1, J42("gnucap_periphery.json")["summary"]["wl_far_settle_90_max_ns"], 0.06)
claim('4.2 column switch drop max (mV)', 190, J42("gnucap_periphery.json")["summary"]["column_switch_drop_max_mV"], 0.6)
claim('4.2 level shifter delay max (ns)', 2.74, J42("gnucap_periphery.json")["summary"]["level_shifter_delay_max_ns"], 0.006)
claim('4.2 program MC ss 1x: reset failures', 1, J42("program_mc.json")["runs"]["ss 1x"]["summary"]["reset_failed"], 0)
claim('4.2 program MC tt 2x: reset failures', 7, J42("program_mc.json")["runs"]["tt 2x"]["summary"]["reset_failed"], 0)
claim('4.2 program MC ss 2x: reset failures', 12, J42("program_mc.json")["runs"]["ss 2x"]["summary"]["reset_failed"], 0)
claim('4.2 program MC ff 2x: reset failures', 7, J42("program_mc.json")["runs"]["ff 2x"]["summary"]["reset_failed"], 0)
claim('4.2 program MC: set failures, all cases', 0, sum(v["summary"]["set_failed"] for v in J42("program_mc.json")["runs"].values()), 0)
claim('4.2 reset at 3.0 V gate: failures, all cases', 0, sum(v["vg 3.0"]["failed"] for v in J42("program_mc.json")["reset_gate_study"].values()), 0)
claim('4.2 SKY130 port: read current identical (relative difference)', 0.0, J42("sky130_port.json")["part_a"]["max_read_rel_diff"], 1e-12)
claim('4.2 SKY130 port: reset at published conditions works anywhere (0 = nowhere)', 0, sum(v["reset"]["gap_nm"] >= 1.0 for v in J42("sky130_port.json")["part_b"].values()), 0)


# ---- section 23 (revision 4.3): the files of revision 4.3, kept in results/rev43
R43 = R / "rev43"
J43 = lambda n: json.loads((R43 / n).read_text())
P3 = J43("pnr.json")["platforms"]; PI3, PS3 = P3["ihp-sg13g2"], P3["sky130hd"]
for name in ("rtl_test.log", "rtl_test_pnx.log", "rtl_test_verilator.log", "rtl_test_verilator_pnx.log",
             "gls_ihp_synth_cg.log", "gls_ihp_routed.log", "gls_sky130_routed.log"):
    t = (R43 / name).read_text(); m = _re.search(r"(\d+) checks, (\d+) failures", t)
    claim(f'4.3 {name}: checks', 82512, int(m.group(1)), 0)
    claim(f'4.3 {name}: failures', 0, int(m.group(2)), 0)
claim('4.3 RTL clock cycles of the test bench', 43694575, int(_re.search(r"(\d+) clock cycles", (R43 / "rtl_test.log").read_text()).group(1)), 0)
for name in ("gls_ihp_synth_cg_fault_icg.log", "gls_ihp_fault_icg.log", "gls_ihp_fault_xnor.log", "gls_sky130_fault_icg.log"):
    claim(f'4.3 {name}: fault detected (1 = yes)', 1, int("TEST FAILED" in (R43 / name).read_text()), 0)
claim('4.3 mutation: detected of 74', 74, J43("rtl_mutation.json")["detected"], 0)
claim('4.3 mutation BSD-PNX: detected of 80', 80, J43("rtl_mutation_pnx.json")["detected"], 0)
claim('4.3 mutation: unchanged RTL passes in the PC environment (both codes)', 2, sum(v["passed"] for v in J43("rtl_mutation_baseline.json").values()), 0)
eg, e0, yd = J43("energy_system.json")["digital_logic_clock_gated"], J43("energy_system.json")["digital_logic_as_synthesized"], J43("energy_system.json")["digital_yardsticks"]
claim('4.3 energy per product, gated (nJ)', 0.80, eg["nJ_per_product"], 0.006)
claim('4.3 energy per product, ungated (nJ)', 1.54, e0["nJ_per_product"], 0.006)
claim('4.3 gated pJ per cycle', 15.27, eg["pJ_per_cycle"], 0.006)
claim('4.3 gated clock pJ per cycle', 7.86, eg["of_which_clock_pJ"], 0.006)
claim('4.3 gating cells pJ per cycle', 1.53, eg["of_which_icg_pJ"], 0.006)
claim('4.3 gating cells', 49, eg["icgs"], 0); claim('4.3 gated flip-flops', 612, eg["gated_flops"], 0)
claim('4.3 flip-flop tile gated (nJ)', 2.27, yd["flipflop_tile_clock_gated_nJ_per_product"], 0.006)
claim('4.3 tcim_top area gated (mm2)', 0.104, J43("synth_baseline.json")["tcim_top_cg"]["area_um2"] * 1e-6, 0.0006)
claim('4.3 IHP routed standard cells', 10630, PI3["stdcells"], 0)
claim('4.3 IHP routed block (mm2)', 0.393, PI3["die_area_um2"] * 1e-6, 0.0006)
claim('4.3 IHP clock-gate cells', 49, PI3["clock_gate_cells"], 0); claim('4.3 SKY130 clock-gate cells', 49, PS3["clock_gate_cells"], 0)
claim('4.3 IHP DRC markers', 5, PI3["drc_violations"], 0); claim('4.3 SKY130 DRC', 0, PS3["drc_violations"], 0)
claim('4.3 SKY130 LVS match (1 = yes)', 1, int(PS3["lvs"] == "netlists match (KLayout)"), 0)
claim('4.3 SKY130 routed standard cells', 11157, PS3["stdcells"], 0)
claim('4.3 SKY130 routed block (mm2)', 0.174, PS3["die_area_um2"] * 1e-6, 0.0006)
claim('4.3 IHP slow setup slack (ns)', 1.40, PI3["post_route_sta"]["slow_1p08V_125C"]["setup_wns_ns"], 0.006)
claim('4.3 IHP slow setup slack, parasitics x1.2 (ns)', 0.75, PI3["parasitic_sensitivity"]["k1.2 slow_1p08V_125C"]["setup_wns_ns"], 0.006)
claim('4.3 IHP fast hold slack, min over parasitic cases (ps)', 109, 1000 * min(PI3["post_route_sta"]["fast_1p32V_m40C"]["hold_wns_ns"], PI3["parasitic_sensitivity"]["k0.8 fast_1p32V_m40C"]["hold_wns_ns"], PI3["parasitic_sensitivity"]["k1.2 fast_1p32V_m40C"]["hold_wns_ns"]), 0.6)
claim('4.3 SKY130 slow setup slack (ns)', -5.40, PS3["post_route_sta"]["ss_100C_1v60"]["setup_wns_ns"], 0.006)
claim('4.3 SKY130 slow limit violations', 354, PS3["post_route_sta"]["ss_100C_1v60"]["limit_violations_listed"], 0)
claim('4.3 SKY130 typical setup slack (ns)', 2.28, PS3["post_route_sta"]["tt_025C_1v80"]["setup_wns_ns"], 0.006)
mp = {f"{r['platform']} {r['spef_scale']}": r for r in J43("pnr_min_period.json")["runs"]}
claim('4.3 IHP shortest period slow (ns)', 8.61, mp["ihp-sg13g2 1.0"]["min_period_ns"], 0.006)
claim('4.3 IHP shortest period slow, x1.2 (ns)', 9.27, mp["ihp-sg13g2 1.2"]["min_period_ns"], 0.006)
claim('4.3 SKY130 shortest period slow (ns)', 15.43, mp["sky130hd 1.0"]["min_period_ns"], 0.006)
claim('4.3 SKY130 shortest period slow, x1.2 (ns)', 16.17, mp["sky130hd 1.2"]["min_period_ns"], 0.006)
rg = J43("gnucap_reset_gate.json")
claim('4.3 reset: slow devices not reset at 2.7 V', 3, sum(not rg[f"ss slow {k} vg 2.7"]["ok"] for k in (1, 2, 3)), 0)
claim('4.3 reset: all devices reset at 3.0 and 3.3 V (1 = yes)', 1, int(all(rg[f"ss {d} vg {v}"]["ok"] for d in ("nominal", "slow 1", "slow 2", "slow 3") for v in ("3.0", "3.3"))), 0)
claim('4.3 reset peak current bound (mA)', 0.76, max(r.get("peak_current_bound_uA", 0) for r in rg.values()) / 1000, 0.006)
p2 = J43("gnucap_periphery2.json")["summary"]
claim('4.3 read reference cases', 27, p2["ratio_cases"], 0)
claim('4.3 trip conductance min (uS)', 103, p2["g_trip_min_uS"], 0.6); claim('4.3 trip conductance max (uS)', 147, p2["g_trip_max_uS"], 0.6)
claim('4.3 margin to HRS tail (uS)', 33, p2["margin_HRS_min_uS"], 0.6); claim('4.3 margin to LRS tail (uS)', 25, p2["margin_LRS3_min_uS"], 0.6)
claim('4.3 column switch drop 0.6 mA (mV)', 95, p2["column_switch_drop_max_mV"], 0.6)
claim('4.3 column switch test current = reset bound rounded up (mA)', 0.80, p2["column_switch_reset_bound_mA"], 0.001)
claim('4.3 column switch drop at that current (mV, rounded up)', 127, p2["column_switch_reset_bound_drop_max_mV"], 0.75)
claim('4.3 test mux R_on max (ohm)', 630, p2["test_mux_ron_max_ohm"], 0.6)
claim('4.3 test mux leakage max (nA)', 37.9, p2["test_mux_leak_max_nA"], 0.06)
pl = J43("periphery_layout.json")["cells"]
for c in ("tcim_ls", "tcim_wld"):
    claim(f'4.3 {c}: DRC clean, LVS match, LVS fault detected (3 = all)', 3, int(pl[c]["drc_clean"]) + int(pl[c]["lvs_match"]) + int(pl[c]["lvs_detects_injected_fault"]), 0)
    claim(f'4.3 {c}: self-check errors', 0, len(pl[c]["self_check_errors"]), 0)
claim('4.3 word-line driver height (um)', 11.5, pl["tcim_wld"]["height_um"], 0.06)

# ---- section 24 (revision 4.4): the files of revision 4.4, kept in results/rev44 (frozen 11 October 2026)
R44 = R / "rev44"
J44 = lambda n: json.loads((R44 / n).read_text())
fs = J44("fit_skywater.json")
claim('4.4 fit: spread k, low end', 0.53, fs["k_fit_range"][0], 0.006)
claim('4.4 fit: spread k, high end', 3.48, fs["k_fit_range"][1], 0.006)
claim('4.4 fit: combinations that fit', 3, sum(v.get("k_fit") is not None for v in fs["cases"].values()), 0)
lf = [r["log10F"] for v in fs["cases"].values() for r in v["rows"]]
claim('4.4 fit: reset-rate factor, log10 min', 2.3, min(lf), 0.06); claim('4.4 fit: reset-rate factor, log10 max', 8.9, max(lf), 0.06)
tr = fs["transfer_ihp_reset_gate"]["runs"]
claim('4.4 transfer: tt k=3.48 not reset at 3.3 V', 4, tr["tt k=3.48"]["vg 3.3"]["failed"], 0)
claim('4.4 transfer: ss k=3.48 not reset at 3.3 V', 10, tr["ss k=3.48"]["vg 3.3"]["failed"], 0)
claim('4.4 transfer: ss k=2.01 not reset at 3.3 V', 1, tr["ss k=2.01"]["vg 3.3"]["failed"], 0)
claim('4.4 transfer: k=0.53 not reset at 2.7 V, tt + ss', 0, tr["tt k=0.53"]["vg 2.7"]["failed"] + tr["ss k=0.53"]["vg 2.7"]["failed"], 0)
sa = J44("sky130_array.json")
claim('4.4 SKY130 array devices', 6912, sa["array"]["devices"], 0)
claim('4.4 SKY130 array DRC flat errors', 0, sa["drc_flat_errors"], 0)
claim('4.4 SKY130 array LVS match, faults detected (4 = all)', 4, int(sa["lvs_match"]) + int(sa["lvs_fault_detected"]) + int(sa["drc_fault_detected"]) + int(sa["drc_hierarchical_clean"]), 0)
claim('4.4 SKY130 cell area (um2)', 10.8, sa["cell"]["area_um2"], 0.06)
pb = J44("pnr_sky130b.json")
claim('4.4 sky130B stdcells', 11302, pb["stdcells"], 0)
claim('4.4 sky130B slow setup slack at 16 ns (ns)', 0.762, pb["post_route_sta"]["ss_100C_1v60"]["setup_wns_ns"], 0.0006)
claim('4.4 sky130B DRC', 0, pb["drc_violations"], 0)
mpb = {r["spef_scale"]: r for r in pb["min_period"]}
claim('4.4 sky130B shortest period (ns)', 15.24, mpb[1.0]["min_period_ns"], 0.006)
claim('4.4 sky130B shortest period x1.2 (ns)', 15.75, mpb[1.2]["min_period_ns"], 0.006)
t = (R44 / "gls_sky130b_routed.log").read_text(); m = _re.search(r"(\d+) checks, (\d+) failures", t)
claim('4.4 sky130B gate-level checks', 82512, int(m.group(1)), 0); claim('4.4 sky130B gate-level failures', 0, int(m.group(2)), 0)
claim('4.4 sky130B gating fault detected (1 = yes)', 1, int("TEST FAILED" in (R44 / "gls_sky130b_fault_icg.log").read_text()), 0)
rd = J44("sky130_read.json")
claim('4.4 SKY130 read trip min (uS)', 12.46, rd["A_summary"]["trip_min_uS"], 0.006)
claim('4.4 SKY130 read trip max (uS)', 13.29, rd["A_summary"]["trip_max_uS"], 0.006)
claim('4.4 SKY130 read mismatch sigma (uS)', 0.43, rd["B"]["sigma_uS"], 0.006)
claim('4.4 SKY130 read settle max (ns)', 7.7, max(v["settle_ns"] for v in rd["C"].values()), 0.06)
hy = J44("array_hybrid_read.json")["part_b"]
claim('4.4 hybrid tiles LRS3 x3: wrong weights reference', 9, hy["LRS3 spread x3 offset 2 mV"]["reference_wrong_weights"], 0)
claim('4.4 hybrid tiles LRS3 x3: wrong weights hybrid', 7, hy["LRS3 spread x3 offset 2 mV"]["hybrid_wrong_weights"], 0)
claim('4.4 hybrid tiles LRS1 x2: reference', 4601, hy["LRS1 spread x2 offset 2 mV"]["reference_wrong_weights"], 0)
claim('4.4 hybrid tiles LRS1 x2: hybrid', 3188, hy["LRS1 spread x2 offset 2 mV"]["hybrid_wrong_weights"], 0)
wr = J44("wld_resim.json")["summary"]
claim('4.4 drawn word-line driver: far settle max (ns)', 4.125, wr["far_settle_90_max_ns"], 0.0006)
claim('4.4 drawn word-line driver: change vs 4.3 (ps)', 23, wr["max_change_vs_rev43_ns"] * 1000, 0.6)
wp = J44("wld_pitch.json")
claim('4.4 driver column width (um)', 26.42, wp["width_um"], 0.006)
fl = J44("forming_layout.json")
claim('4.4 forming switch area (um2)', 1483, fl["area_um2"], 0.6)
chk = (R44 / "ihp_checks.log").read_text()
claim('4.4 IHP checks: DRC passed, LVS matched (4 = all)', 4, chk.count("Passed: No DRC violations") + chk.count("PASS (netlists match)"), 0)
claim('4.4 IHP checks: LVS faults detected', 2, chk.count("FAIL (netlists do not match)"), 0)
fp = lambda n: json.loads((R44 / "fpga" / n).read_text())
claim('4.4 FPGA sim bank 0: wrong weights', 0, fp("sim_bank0.json")["readback_wrong_weights"], 0)
claim('4.4 FPGA sim bank 0: inexact digital products', 0, fp("sim_bank0.json")["digital"]["inexact_products"], 0)
claim('4.4 FPGA sim bank 1: wrong weights', 214, fp("sim_bank1.json")["readback_wrong_weights"], 0)
claim('4.4 FPGA sim bank 2: wrong weights', 677, fp("sim_bank2.json")["readback_wrong_weights"], 0)
claim('4.4 FPGA gate level identical to RTL (1 = yes)', 1, int(fp("gls_vs_rtl.json")["identical"]), 0)
claim('4.4 FPGA fmax (MHz)', 26.0, fp("nextpnr_report.json")["fmax"]["clk"]["achieved"], 0.06)
claim('4.4 FPGA board netlist has no signed multiplier', 0, len(fp("mult_sign_check.json")["signed_multipliers"]), 0)
for b, ww in ((0, 0), (1, 378), (2, 624)):
    claim(f'4.4 FPGA board bank {b}: wrong weights', ww, fp(f"board_bank{b}.json")["readback_wrong_weights"], 0)
claim('4.4 FPGA board bank 0: inexact digital products', 0, fp("board_bank0.json")["digital"]["inexact_products"], 0)
claim('4.4 FPGA board bank 0: analog max error', 1, fp("board_bank0.json")["analog"]["max_abs_error"], 0)
claim('4.4 FPGA board, first bitstream: analog max error', 364, fp("board_v1_signed_mult_bank0.json")["analog"]["max_abs_error"], 0)
fo = J44("gnucap_forming.json"); fs_ = fo["part_a_summary"]
claim('4.4 forming cases', 45, fs_["cases"], 0)
claim('4.4 forming settled max (V)', 3.00, fs_["settled_max_V"], 0.006)
claim('4.4 forming transient max (V)', 3.60, fs_["transient_max_V"], 0.006)
claim('4.4 forming time above 3.3 V max (ns)', 0.8, fs_["ns_above_3p3_max"], 0.06)
claim('4.4 forming bit-line drop max (mV)', 244, fs_["drop_max_mV"], 0.6)
claim('4.4 forming: cell voltage with column source line, 5 V (V)', 3.00, fo["part_b"]["column 5.0 V tt 27 C"]["selected_cell_V"], 0.006)
claim('4.4 forming: cell voltage with row source line, 5 V (V)', 5.00, fo["part_b"]["row 5.0 V tt 27 C"]["selected_cell_V"], 0.006)

# ---- section 25 (revision 4.5): the SKY130 test chip as taped out on 12 October 2026 (docs/STATUS.md, section 9).
# Revision 4.5 was closed on 4 November 2026: its files are in results/rev45, its layout in chip/sky130/caravan_rev45 and
# flow/orfs/outdig_rev45 (revision 4.6, section 26, changed the logic).
R45 = R / "rev45"
RC5 = R45 / "sky130_chip"
J5 = lambda n: json.loads((RC5 / n).read_text())
def chk5(n):
    m = _re.search(r"(\d+) checks, (\d+) failures", (RC5 / n).read_text()); return int(m.group(1)), int(m.group(2))
for n, q in (("rtl_chip_000.log", 76823), ("rtl_chip_110.log", 76973), ("rtl_chip_321.log", 79228),
             ("rtl_chip_verilator_110.log", 76973), ("gls_chip_routed.log", 76975)):
    c, f = chk5(n); claim(f'4.5 chip {n}: checks', q, c, 0); claim(f'4.5 chip {n}: failures', 0, f, 0)
claim('4.5 chip gate-level faults detected (xnor, icg; 2 = both)', 2,
      sum(int("TEST FAILED" in (RC5 / n).read_text()) for n in ("gls_chip_fault_xnor.log", "gls_chip_fault_icg.log")), 0)
mc5 = J5("mutation_chip.json")
claim('4.5 controller faults injected', 26, mc5["faults"], 0); claim('4.5 controller faults detected', 26, mc5["detected"], 0)
db = J5("digital_block.json")
claim('4.5 chip block stdcells incl. 610 antenna diodes', 10248, db["stdcells"], 0); claim('4.5 chip block flip-flops', 1074, db["sequential"], 0)
claim('4.5 chip block clock gates', 56, db["clock_gates"], 0); claim('4.5 chip block area (um2)', 188757, db["die_area_um2"], 0)
claim('4.5 chip block utilization', 0.479, db["utilization"], 0.0006); claim('4.5 chip block DRC', 0, db["drc_violations"], 0)
claim('4.5 chip block equivalence (1 = identical)', 1, int(db["lec_identical"]), 0)
claim('4.5 chip block worst setup slack (ns)', 9.72, db["setup_wns_min_ns"], 0.006)
claim('4.5 chip block worst hold slack (ps)', 145, db["hold_wns_min_ns"] * 1000, 0.6)
mp5 = {r["spef_scale"]: r["min_period_ns"] for r in db["min_period"]}
claim('4.5 chip block shortest period (ns)', 14.73, mp5[1.0], 0.006); claim('4.5 chip block shortest period x1.2 (ns)', 15.31, mp5[1.2], 0.006)
claim('4.5 chip block antenna diodes (DEF)', 610, len(_re.findall(r"- \S+ sky130_fd_sc_hd__diode_2 ", (R.parent / "flow/orfs/outdig_rev45/results/sky130hd/tcim_chip_digital/base/6_final.def").read_text())), 0)
pc5 = J5("precheck.json")
claim('4.5 ChipFoundry precheck: checks passed of 14', 14, pc5["passed"] if pc5["total"] == 14 else -1, 0)
import hashlib as _hl
claim('4.5 precheck ran on the GDS in the project folder (1 = same md5)', 1,
      int(pc5["gds_md5"] == _hl.md5((R.parent / "chip/sky130/caravan_rev45/gds/user_analog_project_wrapper.gds").read_bytes()).hexdigest()), 0)
claim('4.5 precheck md5 = sign-off md5 (1 = same)', 1, int(pc5["gds_md5"] == J5("top_signoff.json")["gds_md5"]), 0)
claim('4.5 precheck in ChipFoundry\'s pinned versions: checks passed of 14', 14,
      pc5["chipfoundry_env"]["passed"] if pc5["chipfoundry_env"]["total"] == 14 else -1, 0)
claim('4.5 precheck in ChipFoundry\'s versions ran on the final GDS (1 = same md5)', 1,
      int(pc5["chipfoundry_env"]["gds_md5"] == pc5["gds_md5"]), 0)
socf = J5("top_signoff_cfenv.json")
claim('4.5 chip Magic DRC markers, ChipFoundry\'s Magic and tech', 0, socf["drc_markers"], 0)
claim('4.5 chip Magic antenna violations, ChipFoundry\'s Magic and tech', 0, socf["antenna_violation_count"], 0)
claim('4.5 ChipFoundry-version sign-off on the final GDS (1 = same md5)', 1, int(socf["gds_md5"] == pc5["gds_md5"]), 0)
claim('4.5 batch 21 (all cells from 3e0e31d): checks passed of 14', 13,
      sum(v == "PASS" for v in pc5["history"][2]["checks"].values()), 0)
claim('4.5 batch 21 FEOL markers (npc.2 at and2_0)', 1,
      len(_re.findall(r"<item>", (RC5 / "precheck_cfenv_allcf" / "klayout_feol_check.xml").read_text())), 0)
claim('4.5 standard-cell GDS of the chip (md5 as documented, 1 = same)', 1,
      int(_hl.md5((R.parent / "layout/sky130/periph/stdcells_cf/sky130_fd_sc_hd.gds").read_bytes()).hexdigest() == "2a5e1a68a1963e0177dae14cd1ce6cf6"), 0)
fl5 = (R45 / "formal.log").read_text()
claim('4.5 formal proofs passed (spi, safety, safety_pnx, progress)', 4,
      sum(f"[{t}] DONE (PASS, rc=0)" in fl5 for t in ("tcim_spi", "tcim_core_safety", "tcim_core_safety_pnx", "tcim_core_progress")), 0)
claim('4.5 formal faults caught', 9, sum(x["caught"] for x in json.loads((R45 / "formal_faults.json").read_text())), 0)
pl = J5("periph_layout.json")
claim('4.5 periphery cells drawn', 12, len(pl), 0)
claim('4.5 periphery cells clean, matched, fault caught (36 = all)', 36,
      sum(int(c["drc_errors"] == 0) + int(c["lvs_match"]) + int(not c["fault_lvs_match"]) for c in pl.values()), 0)
ml = J5("macro_layout.json")
claim('4.5 macro DRC', 0, ml["drc_errors"], 0); claim('4.5 macro LVS match and fault caught (2 = both)', 2, int(ml["lvs_match"]) + int(not ml["fault_lvs_match"]), 0)
claim('4.5 macro width (um)', 1436.7, ml["width_um"], 0.06); claim('4.5 macro height (um)', 1391.7, ml["height_um"], 0.06)
claim('4.5 macro 1.8 V pins', 175, ml["lv_pins"], 0)
tl = J5("top_layout.json")
claim('4.5 chip LVS match and planted swap caught (2 = both)', 2, int(tl["lvs_match"]) + int(not tl["fault_lvs_match"]), 0)
claim('4.5 chip LVS cells with property errors', 0, len(tl["property_errors_in"]), 0)
claim('4.5 chip antenna diodes at the top level', 61, tl["antenna_diodes"], 0); claim('4.5 chip pad signals', 57, tl["pad_signals"], 0)
so = J5("top_signoff.json")
claim('4.5 chip Magic DRC markers (full rules)', 0, so["drc_markers"], 0)
claim('4.5 chip Magic antenna violations', 0, so["antenna_violation_count"], 0)
fr = json.loads((RC5 / "first_routing" / "top_signoff.json").read_text())
claim('4.5 first routing: Magic antenna violations', 4, fr["antenna_violation_count"], 0)
claim('4.5 first routing: Magic antenna largest ratio', 1073.4, max(v["ratio"] for v in fr["antenna_violations"]), 0.06)
ac = json.loads((RC5 / "first_routing" / "antenna_crosscheck.json").read_text())
claim('4.5 final block OpenROAD antenna violations (nets + pins)', 0, J5("antenna_crosscheck.json")["openroad"]["net_violations"] + J5("antenna_crosscheck.json")["openroad"]["pin_violations"], 0)
claim('4.5 first routing: OpenROAD antenna violations (nets + pins)', 0, ac["openroad"]["net_violations"] + ac["openroad"]["pin_violations"], 0)
claim('4.5 Magic metal3 hit: OpenROAD side-area ratio of the same gate', 383, ac["hits"][0]["openroad_pins"]["B"]["openroad_worst"][0][3], 0.6)
claim('4.5 Magic metal4-contact hits: OpenROAD via4 ratio of the same gates', 4.03,
      max(h["openroad_pins"][p]["openroad_worst"][0][3] for h, p in ((ac["hits"][2], "A2"), (ac["hits"][3], "GATE"))), 0.006)
ps = J5("periph_sim.json"); D5 = ps["D"]
for op, lo, hi in (("reset", 7.93, 8.37), ("read", 11.95, 12.81), ("set", 23.71, 27.36)):
    v = [x for k, x in D5.items() if k.startswith(f"trip {op} ")]
    claim(f'4.5 trip {op} cases', 45, len(v), 0)
    claim(f'4.5 trip {op} min (uS)', lo, min(v), 0.006); claim(f'4.5 trip {op} max (uS)', hi, max(v), 0.006)
for op, mu, sg in (("reset", 8.20, 0.46), ("read", 12.31, 0.71), ("set", 25.62, 1.22)):
    claim(f'4.5 trip {op} mismatch mean (uS)', mu, D5[f"mc {op}"]["mean_uS"], 0.006)
    claim(f'4.5 trip {op} mismatch sigma (uS)', sg, D5[f"mc {op}"]["sigma_uS"], 0.006)
lc = J5("mc_libcheck.json")
claim('4.5 full-library mismatch runs per reference', 48, lc["set"]["full_runs"], 0)
claim('4.5 full vs reduced library: means agree (3 = all)', 3, sum(int(lc[o]["p_mean"] > 0.05) for o in ("reset", "read", "set")), 0)
claim('4.5 full-library set-target sigma (uS)', 1.51, lc["set"]["full_sigma_uS"], 0.006)
claim('4.5 full / reduced set-target sigma ratio', 1.24, lc["set"]["sigma_ratio"], 0.006)
claim('4.5 full-library set-target max (uS)', 28.78, lc["set"]["full_max_uS"], 0.006)
rc5 = J5("macro_rc.json"); w5 = rc5["worst_case"]; rs5 = rc5["resim"]
claim('4.5 worst bit line R incl. array (ohm)', 595, w5["R_bitline_ohm"], 0.6)
claim('4.5 worst source line R (ohm)', 442, w5["R_sourceline_ohm"], 0.6)
claim('4.5 worst word-line route R (ohm)', 815, w5["R_wordline_route_ohm"], 0.6)
claim('4.5 worst bit-line route C (fF)', 172, w5["C_bitline_route_F"] * 1e15, 0.6)
claim('4.5 resim: all read and verify decisions correct (1 = yes)', 1, int(rs5["all_decisions_correct"]), 0)
claim('4.5 resim: read settle max (ns)', 13.68, rs5["read_settle_max_ns"], 0.006)
claim('4.5 resim: verify settle max (ns)', 25.42, rs5["verify_settle_max_ns"], 0.006)
claim('4.5 resim: word line far end rise max (ns)', 2.79, rs5["wl_rise_max_ns"], 0.006)
claim('4.5 resim: word line far end fall max (ns)', 3.52, rs5["wl_fall_max_ns"], 0.006)
for tg, q in (("", 75), ("_pnx", 81)):
    mt5 = json.loads((R45 / f"rtl_mutation{tg}.json").read_text())
    claim(f'4.5 mutation{tg}: faults', q, mt5["faults"], 0); claim(f'4.5 mutation{tg}: detected', q, mt5["detected"], 0)
claim('4.5 mutation baseline checks (unchanged RTL, both codes)', 2 * 82554,
      sum(int(_re.search(r"(\d+) checks", v["in_test"]).group(1)) for v in json.loads((R45 / "rtl_mutation_baseline.json").read_text()).values()), 0)
def prog5(n):
    m = J5(n)
    s20 = [r for r in m["set"] if r["VWLP"] == 2.0]
    rs = [r for r in m["reset"] if r["slower_decades"] <= 3]
    return m, s20, rs
m5, s20, rs = prog5("macro_sim.json")
claim('4.5 set at 2.0 V: all reached (1 = yes)', 1, int(all(r["reached"] for r in s20)), 0)
claim('4.5 set at 2.0 V: most pulses', 8, max(r["pulses"] for r in s20), 0)
claim('4.5 set at 1.7 V, ss -40 C: final (uS)', 21.75, [r for r in m5["set"] if r["VWLP"] == 1.7 and r["corner"] == "ss"][0]["final_uS"], 0.006)
claim('4.5 reset up to 3 decades slower: most pulses', 7, max(r["pulses"] for r in rs), 0)
claim('4.5 programming disturb max (uS)', 0.0, max(r["max_disturb_uS"] for r in m5["set"] + m5["reset"]), 0)
mw, s20w, rsw = prog5("macro_sim_worst.json")
claim('4.5 worst wiring: set target used (uS)', 29.84, mw["set_target_uS"], 0.006)
claim('4.5 worst wiring: set at 2.0 V all reached (1 = yes)', 1, int(all(r["reached"] for r in s20w)), 0)
claim('4.5 worst wiring: set at 2.0 V fewest pulses', 9, min(r["pulses"] for r in s20w), 0)
claim('4.5 worst wiring: set at 2.0 V most pulses', 11, max(r["pulses"] for r in s20w), 0)
claim('4.5 worst wiring: reset up to 3 decades slower, most pulses', 8, max(r["pulses"] for r in rsw), 0)
claim('4.5 worst wiring: reset 4 decades slower fails only at ss -40 C (1 = yes)', 1,
      int([(r["corner"], r["reached"]) for r in mw["reset"] if r["slower_decades"] == 4] == [("tt", True), ("ss", False), ("ff", True)]), 0)

# ---- section 26 (revisions 4.6 and 4.7, 4-7 November 2026): hardware security (docs/STATUS.md, section 15; the explainer's
# section 13). Against the live results/ (revision 4.7 is the present one).
# revision 4.9 (9 November 2026) re-ran the test benches, fault campaigns and proofs: the revision 4.7 / 4.8 files these claims
# quote are kept in results/rev48 (from the commit of 8 November) and read from there when present
P48 = lambda n: (R / "rev48" / n) if (R / "rev48" / n).exists() else (R / n)
J7 = lambda n: json.loads(P48(n).read_text())
def chk7(n):
    t = P48(n).read_text(); m = _re.findall(r"(\d+) checks, (\d+) failures", t)
    return (int(m[-1][0]), int(m[-1][1])) if m and "TEST PASSED" in t else (-1, -1)
for n in ("rtl_test.log", "rtl_test_pnx.log", "rtl_test_verilator.log", "rtl_test_verilator_pnx.log"):
    c, f = chk7(n); claim(f'4.7 {n}: checks', 97463, c, 0); claim(f'4.7 {n}: failures', 0, f, 0)
rt7 = P48("rtl_test.log").read_text()
claim('4.7 every program command (cycles)', 152, int(_re.search(r"every program command (\d+) cycles", rt7).group(1)), 0)
claim('4.7 fixed-latency product (cycles)', 110, int(_re.search(r"products of (\d+) cycles each", rt7).group(1)), 0)
claim('4.7 same logic as the file the simulations ran on (1 = yes)', 1, int(J7("rev47/same_logic.json")["same_logic_outside_formal_block_and_comments"]), 0)
for tg, q in (("", 115), ("_pnx", 121)):
    mt7 = J7(f"rtl_mutation{tg}.json"); claim(f'4.7 mutation{tg}: faults', q, mt7["faults"], 0); claim(f'4.7 mutation{tg}: detected', q, mt7["detected"], 0)
claim('4.7 netlist for place and route = RTL: points proven', 2764, J7("equiv.json")["place_and_route_source"]["proven"], 0)
claim('4.7 netlist for place and route = RTL: unproven', 0, J7("equiv.json")["place_and_route_source"]["unproven"], 0)
m7 = _re.search(r"(\d+) are proven and (\d+) are unproven", P48("sky130_chip/equiv_chip.log").read_text())
claim('4.7 chip block netlist = chip RTL: proven', 3021, int(m7.group(1)), 0); claim('4.7 chip block netlist = chip RTL: unproven', 0, int(m7.group(2)), 0)
for n, q in (("rtl_chip_000.log", 90196), ("rtl_chip_110.log", 91844), ("rtl_chip_321.log", 93928), ("rtl_chip_verilator_110.log", 91844)):
    c, f = chk7("sky130_chip/" + n); claim(f'4.7 chip {n}: checks', q, c, 0); claim(f'4.7 chip {n}: failures', 0, f, 0)
mc7 = J7("sky130_chip/mutation_chip.json")
claim('4.7 controller faults detected (of 26)', 26, mc7["detected"] if mc7["faults"] == 26 else -1, 0)
fl7 = P48("formal.log").read_text()
claim('4.7 formal proofs passed (spi, safety, safety_pnx, progress, lfsr)', 5,
      sum(f"[{t}] DONE (PASS, rc=0)" in fl7 for t in ("tcim_spi", "tcim_core_safety", "tcim_core_safety_pnx", "tcim_core_progress", "tcim_core_lfsr")), 0)
claim('4.7 timing miters passed (prove, prove_pnx)', 2, sum("DONE (PASS" in P48(f"security/miter_{t}.log").read_text() for t in ("prove", "prove_pnx")), 0)
ff7 = J7("formal_faults.json")
claim('4.7 planted proof faults', 28, len(ff7), 0); claim('4.7 planted proof faults caught', 28, sum(x["caught"] for x in ff7), 0)
tv7 = J7("security/tvla.json")
def tv(key, sec, k):
    return next(r for r in tv7["products"] if r["design"].startswith(key) and r["secret"] == sec and r["traces_per_group"] == 150000 and ((r["k_uA"] > 0) == k))["max_abs_t_samples"]
for key, sec, q in (("as built", "inputs", 4605.29), ("revision 4.6:", "weights", 19.04), ("revision 4.6:", "inputs", 19.55),
                    ("revision 4.7:", "weights", 14.24), ("revision 4.7:", "inputs", 3.59), ("revision 4.6 logic + one", "weights", 6.56),
                    ("revision 4.7 logic + one", "weights", 3.13), ("revision 4.7 logic + one", "inputs", 2.61)):
    claim(f'4.7 leak model |t| max, {key} {sec}, digital term on', q, tv(key, sec, True), 0.006)
pg7 = {r["mode"] + r["encoding"]: r["max_abs_t_samples"] for r in tv7["programming"]}
claim('4.7 programming |t| max, stop at verify', 87.35, pg7["variable2T2R"], 0.006)
claim('4.7 programming |t| max, constant pulse count', 65.67, pg7["constant2T2R"], 0.006)
for rv, lo, hi in (("rev46", 512, 1024), ("rev47", 910, 911)):
    claim(f'4.7 LFSR states per start row, {rv}: fewest', lo, min(tv7["start_row_states"][rv]), 0)
    claim(f'4.7 LFSR states per start row, {rv}: most', hi, max(tv7["start_row_states"][rv]), 0)

for key, sec, q in (("as built", "weights", 79.69), ("revision 4.6 logic + one", "inputs", 23.41)):
    claim(f'4.7 leak model |t| max, {key} {sec}, digital term on', q, tv(key, sec, True), 0.006)
db7 = J7("sky130_chip/digital_block.json")
claim('4.7 chip block stdcells incl. antenna diodes', 15140, db7["stdcells"], 0); claim('4.7 chip block flip-flops', 1377, db7["sequential"], 0)
claim('4.7 chip block clock gates', 85, db7["clock_gates"], 0); claim('4.7 chip block area (um2), same die as 4.5', 188757, db7["die_area_um2"], 0)
claim('4.7 chip block utilization', 0.739, db7["utilization"], 0.0006); claim('4.7 chip block DRC', 0, db7["drc_violations"], 0)
claim('4.7 chip block equivalence (1 = identical)', 1, int(db7["lec_identical"]), 0)
claim('4.7 chip block worst setup slack (ns)', 7.59, db7["setup_wns_min_ns"], 0.006)
claim('4.7 chip block worst hold slack (ps)', 68, db7["hold_wns_min_ns"] * 1000, 0.6)
mp7 = {r["spef_scale"]: r["min_period_ns"] for r in db7["min_period"]}
claim('4.7 chip block shortest period (ns)', 16.62, mp7[1.0], 0.006); claim('4.7 chip block shortest period x1.2 (ns)', 17.44, mp7[1.2], 0.006)
claim('4.7 chip block antenna diodes (DEF)', 1123, len(_re.findall(r"- \S+ sky130_fd_sc_hd__diode_2 ", (R.parent / "flow/orfs/outdig_rev47/results/sky130hd/tcim_chip_digital/base/6_final.def").read_text())), 0)
c, f = chk7("sky130_chip/gls_chip_routed.log"); claim('4.7 routed block, gate level: checks', 91846, c, 0); claim('4.7 routed block, gate level: failures', 0, f, 0)
claim('4.7 gate-level faults detected (xnor, icg; 2 = both)', 2,
      sum(int("TEST FAILED" in P48("sky130_chip/" + n).read_text()) for n in ("gls_chip_fault_xnor.log", "gls_chip_fault_icg.log")), 0)
tl7, so7, ax7 = J7("sky130_chip/top_layout.json"), J7("sky130_chip/top_signoff.json"), J7("sky130_chip/antenna_crosscheck.json")
claim('4.7 chip LVS match and planted swap caught (2 = both)', 2, int(tl7["lvs_match"]) + int(not tl7["fault_lvs_match"]), 0)
claim('4.7 chip Magic DRC markers (full rules)', 0, so7["drc_markers"], 0)
claim('4.7 chip Magic antenna violations', 0, so7["antenna_violation_count"], 0)
claim('4.7 block OpenROAD antenna violations (nets + pins)', 0, ax7["openroad"]["net_violations"] + ax7["openroad"]["pin_violations"], 0)
import hashlib as _hl7
# (revision 4.9 rebuilt the GDS; the revision 4.7 sign-off and precheck are compared with each other through their recorded md5)
g7 = J7("sky130_chip/precheck.json")["gds_md5"]
claim('4.7 sign-off ran on the GDS in the project folder (1 = same md5)', 1, int(so7["gds_md5"] == g7), 0)
pc7 = J7("sky130_chip/precheck.json")
claim('4.7 ChipFoundry precheck on that GDS: checks passed of 14', 14, pc7["passed"] if pc7["total"] == 14 and pc7["gds_md5"] == g7 else -1, 0)
ae7 = J7("sky130_chip/area_estimate.json")
for rv, q in (("rev45", 60385), ("rev46", 82369), ("rev47", 95135)):
    claim(f'4.7 cell area before place and route, {rv} (um2)', q, ae7[rv]["cell_area_um2"], 0.6)

ax27 = J7("rev47/batch27/antenna_crosscheck.json")["hits"][0]
claim('4.7 batch 27 Magic antenna hit: ratio', 420.6, ax27["magic"]["ratio"], 0.06); claim('4.7 batch 27 Magic antenna hit: limit', 400, ax27["magic"]["limit"], 0)
claim('4.7 batch 27 same gate, OpenROAD ratio of its limit', 1.0, ax27["openroad_pins"]["B"]["openroad_worst"][0][0], 0.006)
claim('4.7 batch 27 Magic antenna violations', 1, J7("rev47/batch27/top_signoff.json")["antenna_violation_count"], 0)

# ---- revision 4.8 (7 November 2026): serial-port fuzzing (docs/STATUS.md, section 15.5)
fz8 = J7("spi_fuzz.json")
claim('4.8 fuzz: the design passes 200,000 frames (1 = yes)', 1, int(fz8[0]["fuzz_passed"] and fz8[0]["frames"] == 200000), 0)
claim('4.8 fuzz: planted faults that make it fail (of 4)', 4, sum(int(x["ok"]) for x in fz8[1:]) if len(fz8) == 5 else -1, 0)
f8 = P48("spi_fuzz_1M.log").read_text()
claim('4.8 fuzz: 1,000,000 frames pass (1 = yes)', 1, int("1000000 frames" in f8 and "FUZZ PASSED" in f8), 0)

# ---- 8 November 2026: 4T4R in the leak model (docs/STATUS.md, section 15.6)
t4 = J7("security/tvla_4t4r.json")
for sec, q in (("weights", 3.14), ("inputs", 1.78)):
    claim(f'4T4R leak model |t| max, {sec}, digital term on', q, next(r for r in t4["products"] if r["secret"] == sec and r["traces_per_group"] == 150000 and r["k_uA"] > 0)["max_abs_t_samples"], 0.006)
ep = J7("security/empty_pulse.json")
claim('H6 empty-pulse runs (all finished)', 32, len(ep["cases"]) if not ep["failed_cases"] else -1, 0)
claim('H6 worst |V| selected row (V)', 1.32, ep["worst_V_selected_row"], 0.006)
claim('H6 worst |V| unselected row (V)', 1.05, ep["worst_V_unselected_row"], 0.006)
wb = ep["worst_by_condition"]
claim('H6 full-array writes to 10 %, 27 C', 1.1e9, wb["nominal_27C"]["other_row_full_array_writes_to_10pct"], 0.06e9)
claim('H6 full-array writes to 10 %, 85 C', 2.2e5, wb["hot_85C"]["other_row_full_array_writes_to_10pct"], 0.06e5)
claim('H6 full-array writes to 10 %, fastest-reset cell', 3.3e7, wb["fast_reset_cell"]["other_row_full_array_writes_to_10pct"], 0.06e7)
claim('H6 selected-row drift per command, 85 C (x1e-9)', 8.2, wb["hot_85C"]["selected_row_per_command"] * 1e9, 0.06)

# ---- next chip (8 November 2026): 3T3R one-of-three design files (docs/STATUS.md, section 15.7)
a3 = J7("next_chip/array3.json")
claim('3T3R cell width (um)', 5.6, a3["cell"]["width_um"], 0); claim('3T3R cell area vs 2T2R', 1.556, a3["cell"]["area_vs_2t2r"], 0.0006)
claim('3T3R array width (um)', 134.4, a3["array"]["width_um"], 0.006); claim('3T3R array devices (LVS)', 10368, a3["array"]["devices"], 0)
claim('3T3R DRC clean, LVS match, both planted faults caught (4 = all)', 4,
      int(a3["cell_drc_clean"]) + int(a3["array_drc_flat_errors"] == 0 and a3["array_drc_hierarchical_clean"]) + int(a3["lvs_match"]) + int(a3["lvs_fault_detected"] and a3["cell_drc_fault_detected"]), 0)
for x in ("", "_pnx"):
    c, f = chk7(f"next_chip/rtl_test_1of3{x}.log"); claim(f'3T3R test bench{x}: checks', 97631, c, 0); claim(f'3T3R test bench{x}: failures', 0, f, 0)
import glob as _g
mz7 = sum((json.loads(open(f).read()) for f in sorted(_g.glob(str(R / "rev48" / "mutation_parts" / "rtl_mutation_1of3_*.json")))), [])
claim('3T3R Z-logic faults caught (of 7)', 7, sum(1 for r in mz7 if r["status"] == "caught") if len(mz7) == 7 else -1, 0)
mq = _re.search(r"Of those cells (\d+) are proven and (\d+) are unproven", (R / "next_chip/equiv_default_build_unchanged.log").read_text())
claim('default build = revision 4.7 core: points proven', 2718, int(mq.group(1)), 0); claim('default build = revision 4.7 core: unproven', 0, int(mq.group(2)), 0)

# ---- next chip (8 November 2026): 3T3R periphery, controller, proofs, transistor-level leakage (docs/STATUS.md, section 15.8)
m3 = J7("next_chip/macro3_layout.json")
claim('3T3R macro width (um)', 1566.3, m3["width_um"], 0.06); claim('3T3R macro height (um)', 1950.5, m3["height_um"], 0.06)
claim('3T3R macro DRC errors', 0, m3["drc_errors"], 0); claim('3T3R macro LVS match, planted fault caught (2 = both)', 2, int(m3["lvs_match"]) + int(not m3["fault_lvs_match"]), 0)
ms3 = J7("next_chip/macro_sim3.json")
for cr, q in (("tt", 7), ("ss", 8), ("ff", 7)):
    claim(f'3T3R set pulses at 2.0 V, {cr}', q, next(r["pulses"] for r in ms3["set"] if r["corner"] == cr), 0)
claim('3T3R reset pulses, worst (0-3 decades slower)', 7, max(r["pulses"] for r in ms3["reset"]), 0); claim('3T3R programming disturb (uS)', 0.0, ms3["max_disturb_uS"], 0)
c, f = chk7("next_chip/rtl_chip_1of3_110.log"); claim('3T3R chip test bench: checks', 92076, c, 0); claim('3T3R chip test bench: failures', 0, f, 0)
mc3 = J7("next_chip/mutation_chip_1of3.json"); claim('3T3R controller Z faults caught (of 6)', 6, mc3["detected"] if mc3["faults"] == 6 else -1, 0)
claim('3T3R formal safety proof passes (1 = yes)', 1, int("DONE (PASS" in P48("next_chip/formal_1of3.log").read_text()), 0)
ff3 = J7("next_chip/formal_faults_1of3.json"); claim('3T3R formal Z faults caught (of 3)', 3, sum(x["caught"] for x in ff3) if len(ff3) == 3 else -1, 0)
mf8 = J7("rtl_mutation_1of3full.json"); claim('3T3R full mutation test: faults caught (of 122 run)', 122, mf8["detected"] if mf8["run"] == 122 and not mf8["missing"] else -1, 0)
sa8 = J7("security/sa_transient.json")
claim('SA mean current, 60 uS LRS (uA)', 2.25, sa8["mean_uA_nominal"]["60uS"], 0.006); claim('SA mean current, 4.5 uS HRS (uA)', 1.00, sa8["mean_uA_nominal"]["4.5uS"], 0.006)
claim('SA mismatch sd on LRS (uA)', 0.126, sa8["mismatch_sd_uA_LRS60"], 0.0006)
at8 = J7("security/attack_sparsity.json")
claim('attack 2T2R correlation, 4096 reads per row', 0.90, at8["results"]["2T2R"][-1]["corr_mean"], 0.006)
claim('attack 3T3R |correlation| max over N', 0.05, max(abs(r["corr_mean"]) for r in at8["results"]["1of3"]), 0.0041)
claim('attack, all windows, 2T2R correlation at 4096', 0.97, at8["results_all_windows"]["2T2R"][-1]["corr_mean"], 0.006)
claim('attack, all windows, 3T3R correlation at 4096', -0.02, at8["results_all_windows"]["1of3"][-1]["corr_mean"], 0.006)
tc8 = J7("security/tvla_circuit.json")
for enc, q in (("2T2R", 12.14), ("1of3", 22.16), ("4T4R", 21.54)):
    claim(f'circuit TVLA, frozen instance, weights, {enc}', q, next(r["max_abs_t"] for r in tc8["cases"] if r["encoding"] == enc and r["secret"] == "weights"), 0.006)
for enc, q in (("2T2R", 3.42), ("1of3", 3.17), ("4T4R", 3.79)):
    claim(f'circuit TVLA, inputs, {enc}', q, next(r["max_abs_t"] for r in tc8["cases"] if r["encoding"] == enc and r["secret"] == "inputs"), 0.006)
for fn, enc, q in (("tvla_circuit_redraw", "2T2R", 11.94), ("tvla_circuit_redraw", "1of3", 3.18), ("tvla_circuit_redraw", "4T4R", 3.09),
                   ("tvla_circuit_redraw_aligned", "2T2R", 394.41), ("tvla_circuit_redraw_aligned", "1of3", 26.32),
                   ("tvla_circuit_redraw_aligned_rot", "1of3", 2.70), ("tvla_circuit_redraw_aligned_rot", "2T2R", 387.06)):
    claim(f'circuit TVLA {fn[13:]}, weights, {enc}', q, next(r["max_abs_t"] for r in J7(f"security/{fn}.json")["cases"] if r["encoding"] == enc), 0.006)
sp8 = J7("security/sa_programmed_states.json")
claim('SA mean current, 29.9 uS (uA)', 2.2764, sp8["mean_uA"]["29.9uS"], 0.00005); claim('SA mean current, 0.31 uS (uA)', 0.1614, sp8["mean_uA"]["0.31uS"], 0.00005)
claim('SA mean current, 60 uS, second run (uA)', 2.2517, sp8["mean_uA"]["60uS"], 0.00005)

Q9 = dict(tb=107134, tb_vl=107059, tb3=107302, c000=99792, c110=101504, c321=103659, c3=101737)   # PC batch 29d
# ---- section 15.9 (revision 4.9, 9 November 2026): locked at reset, erase of the whole array to unlock, programming refused under
# LOCK, LOCK in three flip-flops (docs/STATUS.md 15.9; page 13e). Against the live results/ (revision 4.9 is the present one).
S9 = J("rev49/summary.json")
claim('4.9 erase: clock cycles (72 rows x 42 pulse steps)', 18541, S9["erase_cycles"], 0)
for n, q in (("rtl_test.log", Q9["tb"]), ("rtl_test_pnx.log", Q9["tb"]), ("rtl_test_verilator.log", Q9["tb_vl"]), ("rtl_test_verilator_pnx.log", Q9["tb_vl"]),
             ("next_chip/rtl_test_1of3.log", Q9["tb3"]), ("next_chip/rtl_test_1of3_pnx.log", Q9["tb3"]),
             ("sky130_chip/rtl_chip_000.log", Q9["c000"]), ("sky130_chip/rtl_chip_110.log", Q9["c110"]), ("sky130_chip/rtl_chip_321.log", Q9["c321"]),
             ("next_chip/rtl_chip_1of3_110.log", Q9["c3"])):
    t9 = S9["tb"][n]; claim(f'4.9 {n}: checks', q, t9["checks"] if t9 and t9["passed"] else -1, 0); claim(f'4.9 {n}: failures', 0, t9["failures"] if t9 else -1, 0)
for n, q in (("rtl_mutation.json", 126), ("rtl_mutation_pnx.json", 132), ("rtl_mutation_1of3full.json", 133)):
    m9 = S9["mutation"][n]; claim(f'4.9 {n}: faults', q, m9["faults"], 0); claim(f'4.9 {n}: caught', q, m9["detected"] if m9["run"] == q else -1, 0)
    claim(f'4.9 {n}: new faults caught (of 12)', 12, m9["new_caught"] if m9["new_faults"] == 12 else -1, 0)
for n, q in (("sky130_chip/mutation_chip.json", 26), ("next_chip/mutation_chip_1of3.json", 6)):
    claim(f'4.9 {n}: caught', q, S9["mutation_chip"][n]["detected"] if S9["mutation_chip"][n]["faults"] == q else -1, 0)
f9 = S9["formal"]
claim('4.9 proofs passed (spi, lfsr, lock, two miters, safety variants A, B, C)', 8, f9["n_passed"], 0)
claim('4.9 proofs listed as open', 5, len(f9["open"]), 0)
claim('4.9 safety variant A (4.7 properties) proof time (s)', 3653, f9["variant_seconds"]["A"], 0)
claim('4.9 timing miter counterexample before the LOCK-public assumption (1 = yes)', 1, int(f9["miter_counterexample_before_fix"]), 0)
e9 = S9["equiv_vs_rev48"]
claim('4.9 vs 4.8 logic, default cell: points proven', 2615, e9["default"]["proven"], 0); claim('4.9 vs 4.8 logic, default cell: unproven', 175, e9["default"]["unproven"], 0)
claim('4.9 vs 4.8 logic, 3T3R: points proven', 2639, e9["1of3"]["proven"], 0); claim('4.9 vs 4.8 logic, 3T3R: unproven', 223, e9["1of3"]["unproven"], 0)
claim('4.9 lint warnings', 0, S9["lint_warnings"], 0)
claim('4.9 netlist for place and route = RTL: unproven', 0, J("equiv.json")["place_and_route_source"]["unproven"], 0)
m9c = _re.search(r"(\d+) are proven and (\d+) are unproven", (R / "sky130_chip/equiv_chip.log").read_text())
claim('4.9 chip block netlist = chip RTL: proven', 3050, int(m9c.group(1)), 0); claim('4.9 chip block netlist = chip RTL: unproven', 0, int(m9c.group(2)), 0)
fz9 = (R / "spi_fuzz_1M.log").read_text()
claim('4.9 serial-port fuzzing: frames, mismatches', 1000000, int(_re.search(r"(\d+) frames", fz9).group(1)) if "0 mismatches" in fz9 and "FUZZ PASSED" in fz9 else -1, 0)
db9 = J("sky130_chip/digital_block.json")
claim('4.9 chip block stdcells', 14736, db9["stdcells"], 0); claim('4.9 chip block flip-flops', 1380, db9["sequential"], 0)
claim('4.9 chip block clock gates', 85, db9["clock_gates"], 0); claim('4.9 chip block utilization', 0.716, db9["utilization"], 0.0006)
claim('4.9 chip block DRC', 0, db9["drc_violations"], 0); claim('4.9 chip block equivalence (1 = identical)', 1, int(db9["lec_identical"]), 0)
claim('4.9 chip block worst setup slack, slow corner (ns)', 8.905, db9["corners"]["ss_100C_1v60"]["setup_wns_ns"], 0.0006)
claim('4.9 chip block worst hold slack, all corners (ns)', 0.203, min(c["hold_wns_ns"] for c in db9["corners"].values()), 0.0006)
mp9 = {r["spef_scale"]: r["min_period_ns"] for r in db9["min_period"]}
claim('4.9 chip block shortest period (ns)', 16.12, mp9[1.0], 0.006); claim('4.9 chip block shortest period x1.2 (ns)', 16.94, mp9[1.2], 0.006)
c9 = (R / "sky130_chip/gls_chip_routed.log").read_text()
claim('4.9 routed block, gate level, final test bench (sandbox): checks', 101506, int(_re.findall(r"(\d+) checks", c9)[-1]), 0)
claim('4.9 routed block, gate level: failures', 0, int(_re.findall(r"(\d+) failures", c9)[-1]) if "TEST PASSED" in c9 else -1, 0)
claim('4.9 gate-level faults detected (xnor, icg)', 2, sum(int("TEST FAILED" in (R / "sky130_chip" / n).read_text()) for n in ("gls_chip_fault_xnor.log", "gls_chip_fault_icg.log")), 0)
tl9, so9, ax9, pc9 = J("sky130_chip/top_layout.json"), J("sky130_chip/top_signoff.json"), J("sky130_chip/antenna_crosscheck.json"), J("sky130_chip/precheck.json")
claim('4.9 chip LVS match and planted swap caught (2 = both)', 2, int(tl9["lvs_match"]) + int(not tl9["fault_lvs_match"]), 0)
claim('4.9 chip Magic DRC markers (full rules)', 0, so9["drc_markers"], 0); claim('4.9 chip Magic antenna violations', 0, so9["antenna_violation_count"], 0)
claim('4.9 block OpenROAD antenna violations', 0, ax9["openroad"]["net_violations"] + ax9["openroad"]["pin_violations"], 0)
g9 = _hl7.md5((R.parent / "chip/sky130/caravan/gds/user_analog_project_wrapper.gds").read_bytes()).hexdigest()
claim('4.9 sign-off and precheck on the GDS in the project folder (2 = both md5 match)', 2, int(so9["gds_md5"] == g9) + int(pc9["gds_md5"] == g9), 0)
claim('4.9 ChipFoundry precheck: checks passed of 14', 14, pc9["passed"] if pc9["total"] == 14 else -1, 0)
claim('4.9 batch 29 precheck before the top.py fix: checks passed of 14', 12, pc9["history"][0]["passed"], 0)

(R / "audit_claims.json").write_text(json.dumps(dict(numbers=N_CLAIMS, stale=bad), indent=1))
print(f"\n{N_CLAIMS} numbers checked, {len(bad)} stale" + (": " + "; ".join(bad) if bad else ""))
sys.exit(1 if bad else 0)
