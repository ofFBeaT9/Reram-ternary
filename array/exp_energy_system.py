"""Energy of one 72 x 24 product in digital mode, with every contribution that has been simulated so far.
Inputs: results/gnucap_sense.json (supply currents of the first-cut sense amplifier, real PDK transistors),
results/array_energy.json (rows read, word-line energy), results/synth_baseline.json (digital logic estimates).
Random ternary data with one third zeros: 1/3 of the devices are LRS, 2/3 HRS."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
sense = json.loads((R / "gnucap_sense.json").read_text())
arr = json.loads((R / "array_energy.json").read_text())
syn = json.loads((R / "synth_baseline.json").read_text())

VDD = 1.2
t = sense["tran"]
shared = 2 * (25.0 + sense["ib_uA"])                               # mirror diode + clamp replica, could serve all columns
i_lrs = t["tt | LRS3 mean 43.6 uA | others LRS3"]["i_vdd_end_uA"] - shared
i_hrs = t["tt | HRS mean 2.85 uA | others LRS3"]["i_vdd_end_uA"] - shared
rows = arr["LRS3"]["reads_digital"]
p_row_uW = VDD * (16 * i_lrs + 32 * i_hrs + shared)                # 48 bit lines, 1/3 LRS
t_worst = max(v["t_out_ns"] for v in t.values() if v["t_out_ns"] is not None)
out = dict(rows_read_per_product=rows, sense_branch_uA=dict(LRS=round(i_lrs, 2), HRS_mean=round(i_hrs, 2), shared_references=shared),
           sense_power_per_row_read_mW=round(p_row_uW * 1e-3, 4), slowest_valid_output_ns=t_worst,
           keep_alive_power_mW=round(VDD * (48 * sense["ib_uA"] + shared) * 1e-3, 4))
for win in (4.0, 10.0):
    e_sa = p_row_uW * 1e-6 * win * 1e-9 * rows * 1e9               # nJ
    out[f"window_{win:g}ns"] = dict(sense_amplifiers_nJ=round(e_sa, 4),
                                    array_at_0p2V_nJ=round(arr["LRS3"]["sum_power_digital_mW"] * 1e-3 * win * 1e-9 * 1e9, 4))
out["word_lines_nJ"] = round(arr["wordline"]["energy_per_row_read_pJ"] * rows * 1e-3, 4)
core = syn["tcim_core_digital_product"]
out["digital_logic_as_synthesized"] = dict(nJ_per_product=round(core["e_product_pJ"] * 1e-3, 3), cycles=round(core["cycles_per_product"], 1),
                                           pJ_per_cycle=round(core["e_total_pJ_per_cycle"], 2), of_which_clock_pJ=round(core["e_clock_pJ"], 2),
                                           note="no clock gating, no clock tree, zero-delay toggles; see synth/power_estimate.py")
if "tcim_core_digital_product_cg" in syn:
    cg = syn["tcim_core_digital_product_cg"]
    out["digital_logic_clock_gated"] = dict(nJ_per_product=round(cg["e_product_pJ"] * 1e-3, 3), cycles=round(cg["cycles_per_product"], 1),
                                            pJ_per_cycle=round(cg["e_total_pJ_per_cycle"], 2), of_which_clock_pJ=round(cg["e_clock_pJ"], 2),
                                            of_which_icg_pJ=round(cg["e_icg_pJ"], 2), icgs=cg["icgs"], gated_flops=cg["gated_flops"],
                                            note="integrated clock-gating cells inserted by Yosys clockgate; no clock tree, zero-delay toggles")
    if "tcim_top_cg" in syn:
        out["digital_logic_clock_gated"]["tcim_top_area_mm2"] = round(syn["tcim_top_cg"]["area_um2"] * 1e-6, 4)
out["digital_yardsticks"] = dict(
    tmac24_pJ_per_step=round(syn["tmac24"]["e_total_pJ_per_cycle"], 2),
    tmac24_72_steps_nJ=round(syn["tmac24"]["e_total_pJ_per_cycle"] * 72e-3, 3),
    flipflop_tile_nJ_per_product=round(syn["dtile72x24"]["e_product_pJ"] * 1e-3, 2),
    flipflop_tile_area_mm2=round(syn["dtile72x24"]["area_um2"] * 1e-6, 3),
    **({} if "dtile72x24_cg" not in syn else dict(
        flipflop_tile_clock_gated_nJ_per_product=round(syn["dtile72x24_cg"]["e_product_pJ"] * 1e-3, 2),
        flipflop_tile_clock_gated_area_mm2=round(syn["dtile72x24_cg"]["area_um2"] * 1e-6, 3))),
    tcim_top_area_mm2=round(syn["tcim_top"]["area_um2"] * 1e-6, 3), tmac24_area_mm2=round(syn["tmac24"]["area_um2"] * 1e-6, 4))
print(json.dumps(out, indent=1))
(R / "energy_system.json").write_text(json.dumps(out, indent=1))
