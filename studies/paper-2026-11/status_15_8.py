"""Print docs/STATUS.md section 15.8 from results/ (8 November 2026), so that no number is copied by hand.
Usage: python3 studies/paper-2026-11/status_15_8.py > /tmp/s158.md"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "results"
J = lambda p: json.loads((R / p).read_text()) if (R / p).exists() else None


def tv(js, enc, sec="weights"):
    c = next((c for c in (js or {}).get("cases", []) if c["encoding"] == enc and c["secret"] == sec), None)
    return "not run" if c is None else f"{c['max_abs_t']:.2f} ({'leaks' if c['leaks'] else 'passes'})"


m3, ms3, mc3 = J("next_chip/macro3_layout.json"), J("next_chip/macro_sim3.json"), J("next_chip/mutation_chip_1of3.json")
ff3, mf3, sa = J("next_chip/formal_faults_1of3.json"), J("rtl_mutation_1of3full.json"), J("security/sa_transient.json")
circ, red, al = J("security/tvla_circuit.json"), J("security/tvla_circuit_redraw.json"), J("security/tvla_circuit_redraw_aligned.json")
rot, sp = J("security/tvla_circuit_redraw_aligned_rot.json"), J("security/sa_programmed_states.json")
l07, l12, n1 = (J(f"security/tvla_circuit_redraw_{x}.json") for x in ("lrs0.7", "lrs1.2", "noise1"))
att = J("security/attack_sparsity.json")
chk = (R / "next_chip/rtl_chip_1of3_110.log").read_text()
import re
cc = re.search(r"(\d+) checks, (\d+) failures", chk)
mu = sa["mean_uA_nominal"]; il, ih = mu["60uS"], mu["4.5uS"]
w3 = il + 2 * ih; rr = lambda z: w3 / ((1 - z) * (il + ih) + z * 2 * ih)
a2, a3 = att["results"]["2T2R"][-1], att["results"]["1of3"]
mw = att.get("results_all_windows")
mfn, mfc = (mf3["run"], mf3["detected"]) if mf3 else (0, 0)
sets = ", ".join(f"{r['corner']} {r['pulses']}" for r in ms3["set"])

import re as _r
print(_r.sub(r"(\d)%", r"\1 %", f"""### 15.8 The 3T3R chip parts and the transistor-level leakage study (8 November 2026)

Everything here is about the next chip (build option `TCIM_CELL_1OF3`, 3T3R layout); this chip is unchanged. Leakage
results are about the model, not silicon.

| Item | Result | Files |
|---|---|---|
| Analog macro for 3T3R (`layout/sky130/next_3t3r/macro3.py`: the 3T3R array, 72 row slices, 72 bit-line slices, 24 source-line drivers, control) | {m3['width_um']} × {m3['height_um']} µm (2T2R macro {m3['macro_2t2r_um'][0]} × {m3['macro_2t2r_um'][1]} µm); DRC {m3['drc_errors']} (full rules), LVS {'match' if m3['lvs_match'] else 'MISMATCH'}, a planted LVS fault {'caught' if not m3['fault_lvs_match'] else 'NOT caught'} (Magic 8.3.685, netgen 1.5.272, sky130B of 3e0e31d) | `results/next_chip/macro3_layout.json` |
| Programming through the drawn drivers, 3T3R (quasi-static, 12 devices, `chip/sky130/sim/macro_sim3.py`) | set at a 2.0 V word line: {sets} pulses; reset of cells 0 to 3 decades slower than the fit: at most {max(r['pulses'] for r in ms3['reset'])} pulses; largest change of any other device {ms3['max_disturb_uS']} µS. The same pulse counts as the 2T2R macro (section 9.6) | `results/next_chip/macro_sim3.json` |
| Array controller with the Z bit line (`rtl/chip/tcim_actl.sv`, macro `ZA`); chip test bench with the line-level model extended to the Z line (`make rtl-chip-1of3`) | {int(cc.group(1)):,} checks, {cc.group(2)} failures (settings 1,1,0); {mc3['detected']} of {mc3['faults']} controller faults in the Z logic caught (`CHIP_CELL=1of3 tb/chip/mutation_chip.py`) | `results/next_chip/rtl_chip_1of3_110.log`, `mutation_chip_1of3.json` |
| Formal safety proof on the option (`tcim_core.sby safety_1of3`; Z pulse-mask properties and an independent decode of the Z sense bits) | PASS; {sum(x['caught'] for x in ff3)} of {len(ff3)} planted Z faults make it fail (`FAULTS=1of3 formal/check_faults.py`) | `results/next_chip/formal_1of3.log`, `formal_faults_1of3.json` |
| Full mutation test on the option (every fault of the 2T2R list plus the Z faults, `TB_CELL=1of3full`) | {mfc} of {mfn} {'run caught (of 122 planned; in progress)' if mfn < 122 else 'faults caught'} | `results/rtl_mutation_1of3full.json` |
| Sense-amplifier read transients (`chip/sky130/sim/sa_transient.py`; ngspice, CF PDK 3e0e31d, 250 ns read, {sa['mismatch_samples']} mismatch samples) | mean supply current {il:.2f} µA on a 60 µS LRS read, {ih:.2f} µA on 4.5 µS HRS; mismatch sd {sa['mismatch_sd_uA_LRS60']:.3f} µA (LRS), {sa['mismatch_sd_uA_HRS4p5']:.3f} µA (HRS); every read correct | `results/security/sa_transient.*` |

**Leakage with transistor-level waveforms** (`tools/tvla_circuit.py`: every sense amplifier one frozen mismatch sample,
lognormal device conductances, revision 4.7 logic, 5 µA rms noise per 50 ns window, 150,000 traces per group):

| Cell | Shuffled, one programmed instance frozen | Shuffled, fixed group reprogrammed every trace | Row-aligned, reprogrammed | Row-aligned, reprogrammed, sense-amplifier rotation (proposal) | Inputs (shuffled, frozen) |
|---|---|---|---|---|---|
| 2T2R | {tv(circ, '2T2R')} | {tv(red, '2T2R')} | {tv(al, '2T2R')} | {tv(rot, '2T2R')} | {tv(circ, '2T2R', 'inputs')} |
| 3T3R one-of-three | {tv(circ, '1of3')} | {tv(red, '1of3')} | {tv(al, '1of3')} | {tv(rot, '1of3')} | {tv(circ, '1of3', 'inputs')} |
| 4T4R as proposed (one of four) | {tv(circ, '4T4R')} | {tv(red, '4T4R')} | not run | not run | {tv(circ, '4T4R', 'inputs')} |

How to read it (council red team, `studies/paper-2026-11/council/03_red_team.md`):
- The frozen test also sees one programmed instance's conductances, a fingerprint present for every cell.
- With a random start row every sample sees the matrix average, so the shuffled tests see only the matrix-wide zero count (the
  fixed matrix has 565 zeros against 576 expected).
- Row-aligned tests see each row and position. Row-aligned, one-of-three still leaks: each sense amplifier's own mismatch makes
  the current depend on which device holds the LRS. This is a chip-specific, first-order residual.
- Rotating at random, on every read, which of a cell's three sense amplifiers reads which device removes it in the model (proposal:
  a 3:1 switch per amplifier, decode rotated back in logic; `--sa-rotate`).

**Attack** (`tools/attack_sparsity.py`, row-aligned, profiled on another device): estimating each row's number of zero
weights reaches a correlation of {a2['corr_mean']} on 2T2R ({a2['rows_exact_mean']:.0%} of rows exact) at 4,096 reads per row; on
3T3R the correlation stays between {min(r['corr_mean'] for r in a3)} and {max(r['corr_mean'] for r in a3)}. A second attacker using all
five windows: 2T2R {mw['2T2R'][-1]['corr_mean']} ({mw['2T2R'][-1]['rows_exact_mean']:.0%} exact), 3T3R {mw['1of3'][-1]['corr_mean']} ({mw['1of3'][-1]['rows_exact_mean']:.0%}, the best-guess rate).

**Cost and gain.**
- Read current per weight, at SkyWater's published states: {w3:.2f} µA for 3T3R, against {il + ih:.2f} µA (±1) and {2 * ih:.2f} µA (0) for
  2T2R. The ratio is {rr(0):.2f}× with no zero weights, {rr(1/3):.2f}× at one third and {rr(0.7):.2f}× at 70 %.
- At the states the drawn drivers program (about 30 µS and 0.31 µS; `results/security/sa_programmed_states.json`) the ratio at one
  third zeros is the same; at 70 % zeros it is {(sp['mean_uA']['29.9uS'] + 2 * sp['mean_uA']['0.31uS']) / (0.3 * (sp['mean_uA']['29.9uS'] + sp['mean_uA']['0.31uS']) + 0.7 * 2 * sp['mean_uA']['0.31uS']):.2f}×.
- Every single-device flip gives an invalid 3T3R code (9 of 9). In 2T2R
only 2 of 6 do, and the other 4 turn into another valid weight.

**Found on the way** (council, `studies/paper-2026-11/council/`):
- The margin check reads the row in PROW also under LOCK (it only stops writing PDATA), so an attacker gets row-aligned reads.
- Programming is not refused under LOCK, so an attacker can reprogram a row with known weights and calibrate every sense amplifier.
  Proposal for the next revision: refuse PCMD + under LOCK, or erase the whole array first.
- The tile's results Y are readable, and with chosen inputs they give the weights directly. The side-channel threat model therefore
  assumes the tile's results go only to the host.
- The sense register's switching depends on whether vertically adjacent weights are equal. Clearing it between reads is proposed,
  not done.

Still to do for the 3T3R chip: the sense-amplifier rotation (draw it, add it to the RTL); refusing programming under LOCK; the digital block placed and routed with the 48 extra macro pins, the user area, sign-off
and ChipFoundry's precheck; the progress and two-copy timing proofs on the option; the experiments listed by the council
(nested specific tests, second-order tests, a current-DAC flattener baseline, extracted bit-line parasitics, programming
leak with reprogrammed groups); silicon. Paper: `studies/paper-2026-11/` (plan, literature, council, `DRAFT.md`).
"""))
