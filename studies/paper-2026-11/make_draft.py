"""Write DRAFT.md, the paper draft, with every number read from results/ (8 November 2026; draft 0.2 after the red-team review,
council/03_red_team.md).

Run: python3 studies/paper-2026-11/make_draft.py  ->  studies/paper-2026-11/DRAFT.md
A result file that is missing prints as [not run] and is listed at the end."""
import json, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results"
MISSING = []


def J(p):
    f = R / p
    if not f.exists():
        MISSING.append(p)
        return None
    return json.loads(f.read_text())


def T(p):
    f = R / p
    return f.read_text() if f.exists() else ""


def tv(js, enc, sec="weights"):
    return next((c for c in (js or {}).get("cases", []) if c["encoding"] == enc and c["secret"] == sec), None)


def ft(c):
    return "[not run]" if c is None else f"{c['max_abs_t']:.2f} ({'leaks' if c['leaks'] else 'passes'})"


def tval(c):
    return "[not run]" if c is None else f"{c['max_abs_t']:.2f}"


def checks(p):
    m = re.search(r"(\d+) checks, (\d+) failures", T(p))
    return (int(m.group(1)), int(m.group(2))) if m else (0, -1)


beh = J("security/tvla.json")
circ = J("security/tvla_circuit.json")
red = J("security/tvla_circuit_redraw.json")
al = J("security/tvla_circuit_redraw_aligned.json")
rot = J("security/tvla_circuit_redraw_aligned_rot.json")
att = J("security/attack_sparsity.json")
sa = J("security/sa_transient.json")
sp = J("security/sa_programmed_states.json")
a3 = J("next_chip/array3.json")
m3 = J("next_chip/macro3_layout.json")
ms3 = J("next_chip/macro_sim3.json")
ms2 = J("sky130_chip/macro_sim.json")
mc3 = J("next_chip/mutation_chip_1of3.json")
ff3 = J("next_chip/formal_faults_1of3.json")
mfj = J("rtl_mutation_1of3full.json")
pre = J("sky130_chip/precheck.json")
t3 = checks("next_chip/rtl_test_1of3.log"); t3p = checks("next_chip/rtl_test_1of3_pnx.log"); ch3 = checks("next_chip/rtl_chip_1of3_110.log")
eqd = re.search(r"Of those cells (\d+) are proven and (\d+) are unproven", T("next_chip/equiv_default_build_unchanged.log"))
formal_ok = "DONE (PASS" in T("next_chip/formal_1of3.log")


def bp(enc, rot_, sec, k, n):
    return next((c for c in beh["products"] if c["encoding"] == enc and c["rot"] == rot_ and c["secret"] == sec
                 and c["k_uA"] == k and c["traces_per_group"] == n), None)


K = 0.15
z_in = bp("2T2R", "uniform", "inputs", K, 150000)
r46_in, r47_in = bp("2T2R", "rev46", "inputs", K, 150000), bp("2T2R", "rev47", "inputs", K, 150000)
r47_w = bp("2T2R", "rev47", "weights", K, 150000)

mu = sa["mean_uA_nominal"]


def cost(il, ih):
    w3, nz, z = il + 2 * ih, il + ih, 2 * ih
    return w3, nz, z, (lambda f: w3 / ((1 - f) * nz + f * z))


cS = cost(mu["60uS"], mu["4.5uS"])
cP = cost(sp["mean_uA"]["29.9uS"], sp["mean_uA"]["0.31uS"]) if sp else None

att2, att3 = att["results"]["2T2R"], att["results"]["1of3"]
mw = att.get("results_all_windows") or {}
a2 = att2[-1]

set3 = {r["corner"]: r["pulses"] for r in ms3["set"]}
set2 = {r["corner"]: r["pulses"] for r in ms2["set"] if r["VWLP"] == 2.0}
rst3 = {(r["slower_decades"], r["corner"]): r["pulses"] for r in ms3["reset"]}
rst2 = {(r["slower_decades"], r["corner"]): r["pulses"] for r in ms2["reset"] if r["slower_decades"] <= 3}
same_prog = set3 == set2 and all(rst3.get(k) == v for k, v in rst2.items())
mf_n, mf_c, mf_tot = (mfj["run"], mfj["detected"], mfj["faults"]) if mfj else (0, 0, 122)
mac_ratio = (m3["width_um"] * m3["height_um"]) / (m3["macro_2t2r_um"][0] * m3["macro_2t2r_um"][1])

sys.path.insert(0, str(ROOT / "tools"))
import tvla_tcim0 as TM  # noqa: E402
_r = np.random.default_rng(7); _r.integers(0, 40, 24 * TM.NDEV["2T2R"]); zfix = int((_r.integers(-1, 2, (72, 24)) == 0).sum())

ntr = (red or circ)["cases"][0]["traces_per_group"]
rot1, al1, al2, red1, red2 = tv(rot, "1of3"), tv(al, "1of3"), tv(al, "2T2R"), tv(red, "1of3"), tv(red, "2T2R")


def crow(lab, c):
    return f"| {lab} | {c[0]:.2f} | {c[1]:.2f} / {c[2]:.2f} | " + " | ".join(f"{c[3](f):.2f}×" for f in (0, 1 / 3, 0.5, 0.7)) + " |"


cost_rows = crow("SkyWater's published states (LRS 60 µS, HRS 4.5 µS)", cS)
if cP:
    cost_rows += "\n" + crow("states the drawn drivers program (LRS 29.9 µS, HRS 0.31 µS)", cP)
mfall = f"{mf_c} of {mf_n} faults caught" + (f" (of {mf_tot} planned; in progress)" if mf_n < mf_tot else "")

D = f"""# One of Three: a one-hot ternary ReRAM cell against weight-sparsity leakage in compute-in-memory

*Draft 0.2, 8 November 2026, after an independent red-team review (`council/03_red_team.md`). Every number in this draft is read
from `results/` by `studies/paper-2026-11/make_draft.py`. All leakage results are from models of the design, built from SPICE
waveforms of the drawn sense amplifier, not from silicon. Device parameters are placeholders fitted to SkyWater's published data.*

## Abstract

Compute-in-memory (CIM) accelerators keep a neural network's weights in the memory array, so the array's supply current is a side
channel on the model. With the common 2T2R ternary encoding, a zero weight has no low-resistance (LRS) device, so a row's read current
counts its zero weights. On TCIM0, a 72 × 24 ternary ReRAM CIM tile with an open SKY130 layout, a profiled attacker recovers each
row's zero count with a correlation of {a2['corr_mean']:.2f} ({mw['2T2R'][-1]['corr_mean']:.2f} using every window of the read). We propose a
one-of-three (3T3R) cell that holds each weight in exactly one LRS device out of three, so the number of LRS devices per row does not
depend on the weights; the same attacks then find no correlation. Row-aligned tests show what remains: each sense amplifier's own
mismatch makes the current depend on *which* device holds the LRS (|t| {tval(al1)}, threshold 4.5, 150,000 traces per group). This
residual is specific to one chip. Rotating at random, on every read, which sense amplifier reads which of the cell's three devices
brings the row-aligned test to |t| {tval(rot1)} in the model. The cell costs {a3['cell']['area_vs_2t2r']:.2f}× the 2T2R cell area, {mac_ratio:.2f}× the
analog-macro area and {cS[3](1 / 3):.2f}× the sense-amplifier read current at one third zero weights. Every single-device flip becomes a
detectable invalid code (9 of 9, against 2 of 6 for 2T2R).

## 1. Introduction

Ternary weights (−1, 0, +1) make a multiply a sign selection, and ternary networks carry many zeros. A digital accelerator that skips
zeros leaks their positions through timing [F4, F5]. A CIM array that stores a zero as "no conducting device" leaks their number
through its read current, even when the logic does nothing data-dependent [A4, A13].

Contributions:
1. A layered leakage study of a ternary ReRAM CIM tile (array, sense amplifiers, controller, accumulators), separating what logic
   fixes (timing, accumulator switching) from what it cannot (the cell).
2. The one-of-three cell, the smallest two-state-device ternary cell with a weight-independent LRS count. It is drawn in SKY130 with its
   periphery and analog macro, and supported by the controller, test benches, a formal safety proof and fault campaigns.
3. An evaluation that separates three effects which a single fixed-versus-random test mixes: the fingerprint of one programmed
   instance, the matrix-wide zero count, and the per-row, per-position signal. A sense-amplifier rotation (proposal) removes the
   position residual in the model.

## 2. Threat model

The attacker:
- has physical access to a programmed device and measures its supply current;
- knows or chooses the inputs;
- owns a second device of the same design for profiling;
- can trigger margin checks. A margin check reads one chosen row at three references and, in revision 4.7, still runs under
  LOCK, so row-aligned reads are available.

The attacker does **not** read the tile's results. In a deployment the tile sits inside a larger network, and its results go only to
the host. With readable results, 72 chosen input vectors would give the weights directly, and no side channel would be needed.

Two gaps in revision 4.7's logic contradict this model. They are stated here, not solved:
- Programming is not refused under LOCK. An attacker can reprogram one row with known patterns (erasing 24 weights) and calibrate
  every sense amplifier.
- Reset clears LOCK while the weights persist, so the system must set LOCK before any external access after reset.

The fix proposed for the next revision refuses programming under LOCK, or erases the whole array first.

## 3. The TCIM0 tile

TCIM0 is a 72 × 24 ternary tile presented to a host as a memory-mapped device. The current test chip uses 2T2R cells on SKY130
(sky130B, Caravan harness). Its layout passes ChipFoundry's shuttle precheck{(' (' + str(pre['passed']) + ' of ' + str(pre['total']) + ' checks)') if pre else ''},
run with ChipFoundry's pinned tool versions. The one-of-three variant is drawn and verified at block level; it is not yet assembled
into a chip.

Revision 4.7's security features:
- fixed-latency products that read all 72 rows from an LFSR-chosen start row;
- a random result-accumulator offset, removed with the last row;
- dummy accumulators;
- fixed-length programming (21 + 21 pulse steps);
- a set-only LOCK;
- refusal of read-back under LOCK.

## 4. Leakage, layer by layer (behavioural model)

Fixed-versus-random Welch t-tests (threshold 4.5), {beh['assumptions']['noise_uA_rms']} µA rms noise, {K} µA per flipped accumulator bit,
150,000 traces per group, one programmed instance (`results/security/tvla.json`).

| Layer | Before | Fix | After |
|---|---|---|---|
| Timing | zero-skipping: the duration depends on the inputs (\\|t\\| {z_in['abs_t_duration']:.2f}) | fixed latency, all 72 rows, LFSR start row | the duration is the same for every input |
| Accumulators | bit flips around zero carry the inputs: \\|t\\| {r46_in['max_abs_t_samples']:.2f} | revision 4.7: random offset, start row = LFSR mod 72 | {r47_in['max_abs_t_samples']:.2f} |
| Cell, 2T2R | the read current counts LRS devices: \\|t\\| {r47_w['max_abs_t_samples']:.2f} for the weights | none in logic | — |

The behavioural model gives each sense amplifier a constant LRS current, so it cannot see the position residual of Section 6. Its
weight test also shares the limits that Section 6 explains: one programmed instance and a random start row.

## 5. The one-of-three cell

**Code.**
- +1 = (P LRS, Z HRS, N HRS)
- 0 = (HRS, LRS, HRS)
- −1 = (HRS, HRS, LRS)

**Why three.** Take one cell of identical two-state devices with a fixed number k of LRS devices. n devices give C(n, k) codes.
n = 2 gives at most 2. n = 3 gives 3 for k = 1, or for k = 2 at twice the LRS current. One-of-three is therefore the smallest such
cell. Per-row schemes are not bound by this (Section 7).

**Error detection.**
- One-of-three: every single-device flip gives 0 or 2 LRS devices, so 9 of 9 flips are invalid codes.
- 2T2R: only 2 of 6 flips are invalid. The other 4 turn a weight silently into another valid weight, and an LRS device that decays
  below the trip point becomes a silent zero.
- The logic flags (WERR) an invalid code when it is read and counts the weight as 0.
- Detection is not correction, and three devices per weight raise the exposure to device defects by 1.5×.

**Layout.**
- Devices: SkyWater ReRAM devices (0.26 × 0.26 µm), each on a 5 V select transistor (W 1.0 µm, L 0.5 µm).
- Cell: {a3['cell']['width_um']} × {a3['cell']['height_um']} µm, {a3['cell']['area_vs_2t2r']:.3f}× the 2T2R cell.
- 72 × 24 array: {a3['array']['width_um']} × {a3['array']['height_um']} µm, {a3['array']['devices']:,} devices.
- Checks: DRC clean, LVS match; planted DRC and LVS faults both caught.

**Periphery and macro.** Each device column has its own bit-line slice and sense amplifier, so the tile has 72 instead of 48. The
analog macro grows from {m3['macro_2t2r_um'][0]} × {m3['macro_2t2r_um'][1]} µm to {m3['width_um']} × {m3['height_um']} µm ({mac_ratio:.2f}× in area),
mostly from the stacked floorplan of the slices, not from the array. DRC {m3['drc_errors']}, LVS {'match' if m3['lvs_match'] else 'mismatch'};
a planted LVS fault was {'caught' if not m3['fault_lvs_match'] else 'not caught'}.

**Programming.** A quasi-static simulation of 12 devices through the drawn drivers:
- Set at a 2.0 V word line takes {set3.get('tt')} / {set3.get('ss')} / {set3.get('ff')} pulses (tt / ss / ff).
- Reset of devices up to three decades slower than nominal takes at most {max(r['pulses'] for r in ms3['reset'])} pulses.
- Each device takes {'the same number of pulses as in the 2T2R macro' if same_prog else 'a different number of pulses than in the 2T2R macro'}.
- No other device changed by more than {ms3['max_disturb_uS']} µS.

Transient programming and disturb are not simulated. From an erased array, one-of-three sets one device for every weight, where
2T2R sets one per non-zero weight.

**Logic.** Build option `TCIM_CELL_1OF3`. Without the option, the core is proven equivalent to the verified revision 4.7 core
({int(eqd.group(1)):,} points, {eqd.group(2)} unproven). With it:
- RTL test bench: {t3[0]:,} and {t3p[0]:,} checks in the two trit codes, {t3[1] + t3p[1]} failures.
- Chip test bench through a line-level macro model: {ch3[0]:,} checks, {ch3[1]} failures.
- Planted controller faults in the Z logic: {mc3['detected']} of {mc3['faults']} caught.
- Formal safety proof: {'passes' if formal_ok else 'NOT passed'}; {sum(x['caught'] for x in ff3)} of {len(ff3)} planted Z faults make it fail.
- Full mutation campaign: {mfall}.

The progress and two-copy timing proofs do not yet cover the option.

**Read current (cost).** Mean sense-amplifier supply current over the 250 ns read, from SPICE transients of the drawn amplifier:

| Device states | one-of-three weight (µA) | 2T2R ±1 / 0 (µA) | ratio, 0 % zeros | 33 % | 50 % | 70 % |
|---|---|---|---|---|---|---|
{cost_rows}

A constant LRS count means the worst-case current every time. The penalty grows with sparsity, and more so if programmed HRS devices
sit far below SkyWater's 4.5 µS.

## 6. Evaluation with sense-amplifier waveforms

**Waveforms.** ngspice transients of the drawn SKY130 sense amplifier over the 250 ns read, for conductances from 2 to 120 µS,
nominal and with {sa['mismatch_samples']} Monte Carlo mismatch samples:
- Mismatch: {sa['mismatch_sd_uA_LRS60']:.3f} µA sd on an LRS read, {sa['mismatch_sd_uA_HRS4p5']:.3f} µA on HRS.
- Over 30 to 120 µS the mean LRS current varies by {abs(mu['30uS'] - mu['120uS']):.3f} µA; the largest difference in one 10 ns window is
  {sa['lrs_spread_over_G_uA']:.2f} µA.
- Every read is correct.

**Tile model.**
- The 72 sense amplifiers are drawn from the {sa['mismatch_samples']} mismatch samples (so samples repeat) and frozen.
- Waveforms are interpolated in log G. There is no shared supply network and no bit-line parasitics.
- Conductances are lognormal at SkyWater's published states: HRS median 4.5 µS, σ_ln 0.3, at most 7.93 µS; LRS median 60 µS,
  σ_ln 0.35, 30–120 µS.
- Five 50 ns windows per read; revision 4.7 logic; {circ['assumptions']['noise_uA_rms_per_window']} µA rms noise per window; sense-register switching
  off (k_sense 0).
- 150,000 traces per group are about 2.7 s of acquisition, small against an attacker's budget.

**Three effects, three tests.**
- (a) With one programmed instance in the fixed group, a test also sees that instance's conductances, a fingerprint. The weight test
  reprograms the fixed group for every trace.
- (b) With a random start row, every sample sees the matrix average, so a shuffled test only sees the matrix-wide zero count. The
  fixed matrix has {zfix} zeros against 576 expected, and that is what the 2T2R result detects.
- (c) Row-aligned tests see each row and each position.

| Cell | shuffled, frozen instance | shuffled, reprogrammed | row-aligned, reprogrammed | row-aligned, reprogrammed, sense-amplifier rotation |
|---|---|---|---|---|
| 2T2R | {ft(tv(circ, '2T2R'))} | {ft(red2)} | {ft(al2)} | {ft(tv(rot, '2T2R'))} |
| one-of-three | {ft(tv(circ, '1of3'))} | {ft(red1)} | {ft(al1)} | {ft(rot1)} |
| one-of-four (4T4R as proposed: a fourth device always HRS) | {ft(tv(circ, '4T4R'))} | {ft(tv(red, '4T4R'))} | [not run] | [not run] |

Inputs (shuffled, frozen): 2T2R {ft(tv(circ, '2T2R', 'inputs'))}, one-of-three {ft(tv(circ, '1of3', 'inputs'))}, one-of-four
{ft(tv(circ, '4T4R', 'inputs'))}. Max |t| over 360 samples, {ntr:,} traces per group. The row-aligned runs model a product whose rows are
read in order (as with NOSHUF); a margin check reads one row at three references.

**The position residual.** In the row-aligned test one-of-three still leaks. Each sense amplifier has its own mismatch, and which
sense amplifier reads the LRS device depends on the weight. This is a first-order, chip-specific signal:
- Profiling on another chip does not calibrate it.
- Reprogramming the victim does (Section 2).
- Collisions between rows do: every row of a column uses the same three sense amplifiers, so two rows with equal weights in a column
  draw equal currents there.

**Proposal: sense-amplifier rotation.** On every read, connect the cell's three bit lines to its three sense amplifiers in a random
cyclic order: a 3:1 switch per amplifier, two random bits per column, and the decode rotated back in logic. Each amplifier's mismatch
is then spread over P, Z and N. In the model this takes the row-aligned test from {tval(al1)} to {tval(rot1)}; for 2T2R it changes
nothing ({tval(al2)} to {tval(tv(rot, '2T2R'))}), because the zero count is still there. The rotation is not drawn and not in the RTL,
and its random bits would come from the same deterministic LFSR as the start row.

**Attack.** A profiled sparsity-recovery attack (`attack_sparsity.py`). Row alignment is granted; the attacker averages N reads of
every row and fits current against zero count on a profiling device. 20 victim devices per point; means shown.

| Reads per row | 2T2R correlation | 2T2R rows exact | one-of-three correlation | one-of-three rows exact |
|---|---|---|---|---|
""" + "\n".join(f"| {a['reads_per_row']:,} | {a['corr_mean']:.2f} | {a['rows_exact_mean']:.2f} | {b['corr_mean']:.2f} | {b['rows_exact_mean']:.2f} |"
                 for a, b in zip(att2, att3)) + f"""

Guessing the most likely count is right for about 17 % of rows.
- The linear attacker stops near {a2['corr_mean']:.2f} on 2T2R.
- On one-of-three its exact-row rate falls below the guessing rate. The fitted slope is near zero, so the clipped estimates land at the
  ends of the range. This is an estimator artifact, not information.
- A second attacker regresses on all five windows, profiled on 8 devices. 2T2R: correlation {mw['2T2R'][-1]['corr_mean']:.2f}, {mw['2T2R'][-1]['rows_exact_mean']:.0%} of
  rows exact at {mw['2T2R'][-1]['reads_per_row']:,} reads per row. One-of-three: {mw['1of3'][-1]['corr_mean']:.2f} and {mw['1of3'][-1]['rows_exact_mean']:.0%}, the guessing rate.
- Neither attack targets the position residual.

## 7. Discussion and limitations

- **What is claimed.** The one-of-three cell removes the dependence of row current on the zero count, which a profiling attacker can
  exploit across chips. It does not make the current constant. The position residual needs the rotation above, or an attacker model
  without access to the victim's own calibration.
- **Alternatives.**
  - Per-row compensation can use as few as 5 binary-weighted devices per row (0 to 24 zeros). It stores the zero count, which leaks
    when it is programmed, and it must track every LRS device.
  - A current-DAC flattener costs less area, but it holds the zero count in logic and must track corners and mismatch.
  - Neither is simulated here; they are the baselines to compare next.
  - Sign masking cannot hide which weights are zero.
- **Threats not covered.**
  - Localized electromagnetic probing of the separate P, Z and N bit lines.
  - WERR as a fault oracle (fault injection is out of scope).
  - The deterministic LFSR after reset.
  - Higher-order and template attacks on the position term.
  - Sense-register switching, which depends on whether vertically adjacent weights are equal. Clearing the register between reads is
    proposed.
  - Trained weight distributions instead of uniform random weights.
- **Device states.** The tile model uses SkyWater's published states (60 µS, 4.5 µS). The drawn drivers program to about 30 µS and,
  with one reset pulse, about 0.3 µS. The cost table shows both.
- **Programming.** The per-pulse profile of the fixed-length program command still leaks in the behavioural model. That test has the
  frozen-instance confound and must be repeated with reprogrammed groups for both cells.
- **Precharge sense amplifiers and analog read.** The result holds for this static current-mode amplifier and the digital read. In
  current-summing CIM with separate P and N lines, the Z current is a constant offset and does not hide the weights.
- **Evidence.** These are models only; silicon is the decisive test.

## 8. Related work

- Power and timing attacks on CIM and NN accelerators [A1, A4, A13, F4, F5].
- Device mismatch as the leakage source in memristive crossbars [A6]; our position residual is that effect.
- CIM countermeasures [A2, A3, B1].
- Power-balanced memristive implementations [A26] and dual-rail ReRAM storage against collision attacks [A8].
- Ternary and binary differential ReRAM storage [C1, C3].
- Dual-rail and 1-of-n codes in secure logic [D2, D3, D4, D5]; one-of-three is the 1-of-n code [D4] applied to the memory cell.
- Fixed-weight codewords for ternary memory reliability [D1].
- Open ternary CIM on SKY130 [E1].

We found no one-of-three ReRAM cell for side-channel resistance (web search, 8 November 2026; IEEE Xplore and patent search still
pending).

## 9. Conclusion

The 2T2R ternary encoding leaks weight sparsity through the read current, and logic cannot repair it. Storing each weight as one LRS
device out of three removes the zero-count signal, at {a3['cell']['area_vs_2t2r']:.2f}× cell area and {mac_ratio:.2f}× macro area. What remains is a
position signal from sense-amplifier mismatch. It is chip-specific and, in the model, removed by rotating the sense amplifiers. The
controller option passes the test benches, the safety proof and the fault campaigns run so far. The 3T3R chip is not yet assembled.

## Artifact

- Layout: `layout/sky130/next_3t3r/`.
- RTL option: `rtl/tcim_core.sv`, `rtl/chip/tcim_actl.sv`; formal task `safety_1of3`.
- Leakage tools: `tools/tvla_circuit.py` (`--redraw`, `--aligned`, `--sa-rotate`), `tools/attack_sparsity.py`,
  `chip/sky130/sim/sa_transient.py`.
- Results: `results/security/`, `results/next_chip/`.

## References (to be checked against the papers before submission; IDs as in LITERATURE.md)

- [A1] F. J. Mir et al., "Extracting Weights of CIM-Based Neural Networks Through Power Analysis of Adder-Trees," ETS 2024.
- [A2] F. J. Mir et al., "Make it Darker: A Gray Code Popcounter to Protect BNN CIM Against Power Attacks," DATE 2026.
- [A3] F. J. Mir, A. Aljuffri, S. Hamdioui, M. Taouil, "Securing Weights of CIM-Based Neural Networks Against Power Analysis Attacks," IEEE JETCAS, 2026.
- [A4] J. J. C. Goudzwaard, "Analog CiM Security Analysis: Reverse-Engineering Ternary Neural Network Parameters," MSc thesis, TU Delft, 2025.
- [A6] B. Sapui, M. B. Tahoori, "Power Side-Channel Analysis and Mitigation for Neural Network Accelerators based on Memristive Crossbars," ASP-DAC 2024.
- [A8] B. Sapui, M. B. Tahoori, "Side-channel Collision Attacks on Hyper-Dimensional Computing Based on Emerging Resistive Memories," ASP-DAC 2025.
- [A13] C. Merkel, "Enhancing Adversarial Attacks on Single-Layer NVM Crossbar-Based Neural Networks with Power Consumption Information," arXiv 2207.02764, 2022.
- [A26] Z. Chen et al., "Power-balanced Memristive Cryptographic Implementation Against Side Channel Attacks," arXiv 2312.01170.
- [B1] M. Ashok et al., "A Secure Digital In-Memory Compute Macro with Protections Against Side-Channel and Bus Probing Attacks," CICC 2024.
- [C1] A. Laborieux et al., "Implementation of Ternary Weights With Resistive RAM Using a Single Sense Operation per Synapse," arXiv 2007.14234.
- [C3] M. Bocquet et al., "In-Memory and Error-Immune Differential RRAM Implementation of Binarized Deep Neural Networks," IEDM 2018.
- [D1] C. V. A. Laurent, R. Muzzetto, "Fixed weight codewords for ternary memory cells," US 11,811,424 B2, 2023.
- [D2] K. Tiri, I. Verbauwhede, "A Logic Level Design Methodology for a Secure DPA Resistant ASIC or FPGA Implementation," DATE 2004.
- [D3] T. Popp, S. Mangard, "Masked Dual-Rail Pre-Charge Logic," CHES 2005.
- [D4] S. Moore et al., "Balanced Self-Checking Asynchronous Logic for Smart Card Applications," Microprocessors and Microsystems, 2003.
- [D5] H. Maghrebi, V. Servant, J. Bringer, "There is Wisdom in Harnessing the Strengths of your Enemy," FSE 2016.
- [E1] M. Pai, "Ankhdjet: An Open-Source Compiler for Mask-Programmed Ternary Compute-in-ROM on an Open PDK," arXiv 2608.26206, 2026.
- [F4] W. Hua, Z. Zhang, G. E. Suh, "Reverse Engineering Convolutional Neural Networks Through Side-channel Information Leaks," DAC 2018.
- [F5] S. Maji, U. Banerjee, A. P. Chandrakasan, "Leaky Nets," IEEE IoT Journal, 2021.
"""
if MISSING:
    D += "\n*Result files missing when this draft was written: " + ", ".join(MISSING) + ".*\n"
D = re.sub(r"(\d)%", r"\1 %", D)
(Path(__file__).with_name("DRAFT.md")).write_text(D)
print("DRAFT.md written; missing:", MISSING)
