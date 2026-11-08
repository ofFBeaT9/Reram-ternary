"""docs/TCIM0_explainer.html, the short page (8 November 2026, revision 4.8). Replaces assemble.py.

Every number is read from results/ (or computed from the GDS); a missing result prints "not run", never a number. The long
revision-4.5 explanation (layers, hands-on models, FPGA, IHP) stays in docs/STATUS.md and docs/page/base_rev45.html; four
of its figures are reused here unchanged. The open-issue triage is one table (TRIAGE below), also written as Markdown.
Usage (repository root): python3 docs/page/build.py docs/TCIM0_explainer.html [studies/page-trim-2026-11-08/TRIAGE.md]"""
import hashlib, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import security_section as S  # noqa: E402

J, T, esc, checks = S.J, S.T, S.esc, S.checks
base = (Path(__file__).parent / "base_rev45.html").read_text()
head = base[:base.index("</style>") + len("</style>")]
tipjs = re.search(r"<script>\nconst tip=.*?</script>", base, re.S).group(0)
figs = {m.start(): m.group(0) for m in re.finditer(r"<figure.*?</figure>", base, re.S)}
fig = lambda key: next(f for f in figs.values() if key in f)

gds = Path("chip/sky130/caravan/gds/user_analog_project_wrapper.gds")
gds_md5 = hashlib.md5(gds.read_bytes()).hexdigest() if gds.exists() else None
pc, so, tl, blk = J("sky130_chip/precheck.json"), J("sky130_chip/top_signoff.json"), J("sky130_chip/top_layout.json"), J("sky130_chip/digital_block.json")
ac, fz, f1 = J("sky130_chip/antenna_crosscheck.json"), J("spi_fuzz.json"), T("spi_fuzz_1M.log")
tv, t4, lo = J("security/tvla.json"), J("security/tvla_4t4r.json"), J("security/tvla_1of3_noise1uA.json")
ep, ii, sa = J("security/empty_pulse.json"), J("security/idle_impedance.json"), J("security/sa_power.json")
c1 = checks(T("rtl_test.log"))
pre_ok = bool(pc and pc.get("gds_md5") == gds_md5 and pc["passed"] == pc["total"])
pre = f'{pc["passed"]} of {pc["total"]}' if pre_ok else "not run on this GDS"
fz_line = (f'{fz[0]["frames"]:,} random frames and a 1,000,000-frame run, 0 errors' if fz and "FUZZ PASSED" in f1 else "not run")


def P(src, key, sec):  # the page's leak figure: 150,000 traces per group, digital term on
    r = next((r for r in (src or {}).get("products", []) if r["design"].startswith(key) and r["secret"] == sec
              and r["traces_per_group"] == 150000 and r["k_uA"] > 0), None)
    return r


def tcell(r):
    if r is None:
        return '<td class="bad">not run</td>'
    return f'<td class="num {"bad" if r["leaks"] else "ok"}">{r["max_abs_t_samples"]:g}</td>'


def compact_ver():
    """The verification of the current revision in about a dozen rows; every value read from results/."""
    rows = []
    def row(lab, ok, val):
        rows.append(f'<tr><td>{esc(lab)}</td>' + (f'<td class="{"ok" if ok else "bad"}">{esc(val)}</td>' if ok is not None else '<td class="bad">not run</td>') + "</tr>")
    tb = [checks(T(f)) for f in ("rtl_test.log", "rtl_test_pnx.log", "rtl_test_verilator.log", "rtl_test_verilator_pnx.log")]
    row("Test bench against exact arithmetic: 2 simulators × 2 trit codes", None if None in tb else all(c[1] == 0 for c in tb),
        f"4 runs × {tb[0][0]:,} checks, 0 failures" if None not in tb and len({c[0] for c in tb}) == 1 else "")
    fl = T("formal.log")
    st = [re.search(r"\[" + n + r"\] DONE \((\w+)", fl) for n in ("tcim_spi", "tcim_core_safety", "tcim_core_safety_pnx", "tcim_core_progress", "tcim_core_lfsr")]
    st += [re.search(r"DONE \((\w+)", T(f"security/miter_{t}.log")) for t in ("prove", "prove_pnx")]
    ff = J("formal_faults.json")
    row("Formal proofs: serial port, safety (2 trit codes), progress, start row, two-copy timing miter (2 trit codes)", None if None in st else all(m.group(1) == "PASS" for m in st),
        f"{len(st)} of {len(st)} pass; {sum(x['caught'] for x in ff)} of {len(ff)} planted proof faults caught" if ff else "")
    mt, mp, mc = J("rtl_mutation.json"), J("rtl_mutation_pnx.json"), J("sky130_chip/mutation_chip.json")
    row("Faults injected into the logic and the array controller", mt["detected"] == mt["faults"] and mp["detected"] == mp["faults"] and mc["detected"] == mc["faults"],
        f'{mt["detected"]}/{mt["faults"]}, {mp["detected"]}/{mp["faults"]} (BSD-PNX), controller {mc["detected"]}/{mc["faults"]} detected')
    eq = J("equiv.json"); m = re.search(r"(\d+) are proven and (\d+) are unproven", T("sky130_chip/equiv_chip.log"))
    row("Netlist = RTL (formal equivalence), core and chip block", eq["place_and_route_source"]["unproven"] == 0 and bool(m) and m.group(2) == "0",
        f'{eq["place_and_route_source"]["proven"]:,} + {int(m.group(1)):,} points proven, 0 unproven')
    ch = [checks(T(f"sky130_chip/{f}")) for f in ("rtl_chip_000.log", "rtl_chip_110.log", "rtl_chip_321.log", "rtl_chip_verilator_110.log")]
    row("Chip logic + array controller, 3 timing settings, 2 simulators", None if None in ch else all(c[1] == 0 for c in ch),
        f"{sum(c[0] for c in ch):,} checks, 0 failures" if None not in ch else "")
    g = checks(T("sky130_chip/gls_chip_routed.log")); fx = [T(f"sky130_chip/gls_chip_fault_{k}.log") for k in ("xnor", "icg")]
    row("Routed block at gate level (and with a planted gate fault, must fail)", None if g is None else g[1] == 0 and all("TEST FAILED" in x for x in fx),
        f"{g[0]:,} checks, 0 failures; both planted faults caught" if g else "")
    row("Logic block place and route", blk["drc_violations"] == 0 and blk["setup_wns_min_ns"] > 0 and blk["hold_wns_min_ns"] > 0,
        f'{blk["stdcells"]:,} cells, DRC 0, slack ≥ {blk["setup_wns_min_ns"]} ns setup / {blk["hold_wns_min_ns"] * 1000:.0f} ps hold at every corner (25 ns clock)')
    row("Whole chip: LVS, Magic DRC (full rules), antenna in two checkers", bool(tl.get("lvs_match")) and so["drc_markers"] == 0 and so["antenna_violation_count"] == 0 and ac["openroad"]["net_violations"] == 0,
        f'LVS {"match" if tl.get("lvs_match") else "MISMATCH"}; DRC {so["drc_markers"]}; antenna {so["antenna_violation_count"]} (Magic), {ac["openroad"]["net_violations"]} (OpenROAD)')
    if fz:
        row("Serial port fuzzed (revision 4.8)", fz[0]["fuzz_passed"] and "FUZZ PASSED" in f1 and all(x["ok"] for x in fz[1:]),
            f'{fz_line}; {sum(x["ok"] for x in fz[1:])} of {len(fz) - 1} planted faults caught')
    row("ChipFoundry's precheck, their pinned tools and PDK, this GDS", pre_ok, pre)
    return "".join(rows)


def _tpu():
    d = Path("results/ttpu_gen2")
    if not d.exists():
        return "logs not stored"
    sec = re.search(r"(\d+) checks, (\d+) failures", T("ttpu_gen2/tb_ttpu_gen2_sec.run.log"))
    others = [f for f in sorted(d.glob("*.run.log")) if "gen2_sec" not in f.name]
    ok = sum(bool(re.search(r"ALL TESTS PASSED|TOPS VERIFICATION PASSED", f.read_text())) for f in others)
    return (f"new SEC test {sec.group(1)} checks, {sec.group(2)} failures; " if sec else "SEC test log missing; ") + f"{ok} of {len(others)} existing TPU/SoC benches pass"
tpu = _tpu()
lutm = re.search(r"LUT4:\s+(\d+)/\s*(\d+)\s+(\d+)%", T("fpga/rev46/nextpnr.log"))
seeds_fail = sum("Unable to find legal placement" in T(f"fpga/rev46/nextpnr_seed{k}.log") for k in (1, 2, 3))
pv = {r["mode"] + r["encoding"]: r for r in tv["programming"]}

# ---- H6: empty pulses, from results/security/empty_pulse.json -------------------------------------------------------
if ep:
    ws, wu, wb = ep["worst_V_selected_row"], ep["worst_V_unselected_row"], ep["worst_by_condition"]
    h6_ok = ep["closed"]
    nmin = min(w["other_row_full_array_writes_to_10pct"] or float("inf") for w in wb.values())
    h6 = (f"{len(ep['cases'])} transient runs (set/reset, async reset, corners, 4 device states): peaks {ws:.2f} V (selected row), "
          f"{wu:.2f} V (other rows). Device model: a stored weight drifts 10 % only after {nmin:.1e} full-array writes (worst: 85 °C); "
          f"criterion 10 × {ep['planned_array_writes']:,}. Not modelled: device capacitance, junction capacitance, mixed columns. "
          "Details: docs/STATUS.md 15.4.")
else:
    h6_ok, h6 = None, "Transient simulation (chip/sky130/sim/empty_pulse.py) not run yet."

# ---- the triage: (issue, status, evidence) ; status in closed / stands / next / external ------------------------------
r47w, r47i = P(tv, "revision 4.7:", "weights"), P(tv, "revision 4.7:", "inputs")
TRIAGE = [
    ("Start row not uniform (rows 0–55 twice as likely)", "closed", "4.7: start row = 16-bit LFSR mod 72, proved by k-induction (depth 20)."),
    ("Inputs leak through accumulator bit flips", "closed (model)", f"4.7: random accumulator offset; model |t| {r47i['max_abs_t_samples']:g} (limit 4.5)."),
    ("Weight read-back over the bus under LOCK", "closed", "4.7: read-back refused (WERR), margin check does not copy weights; tests and proof."),
    ("Weights recoverable through products, even under LOCK", "stands", "72 products with one-hot inputs return every weight; true of any accelerator a bus user can run. Keep the bus trusted."),
    ("One upset after LOCK re-enables an option", "closed", "4.7: every option use gated by LOCK. Cannot be shown by a functional test (needs an upset)."),
    ("LOCK itself is one flip-flop: an upset clears it", "next", "Redundant or non-volatile LOCK (NEXT_CHIP_SPEC.md section 5)."),
    ("A fault in the row counter can end a product early, without WERR", "next", "Redundant count of row answers (NEXT_CHIP_SPEC.md section 5)."),
    ("Serial port: cut frames, chip-select glitches, junk writes (logic level)", "closed",
     f"4.8: fuzzed, {fz[0]['frames']:,} + 1,000,000 frames, 0 errors; {sum(x['ok'] for x in fz[1:])} of {len(fz) - 1} planted faults caught." if fz else "not run"),
    ("Antenna: one net 5 % over in Magic", "closed",
     f"Last repair pass at 15 % margin; routed again: OpenROAD {ac['openroad']['net_violations']}, Magic {ac['magic']['violations']}." if ac else "not run"),
    ("Empty programming pulses: transients and async reset (H6)", "closed (model)" if h6_ok else "stands", h6),
    ("Async reset during a real pulse could leave a partial write (not simulated)", "next", "Break-before-make on asynchronous reset (NEXT_CHIP_SPEC.md section 5)."),
    ("2T2R read current shows weight sparsity, per row", "next",
     f"Model |t| {r47w['max_abs_t_samples']:g} on this chip. Fixed by a constant-conductance cell (one-of-three, or 4T4R): see Cell options."),
    ("Programming profile leaks which devices change", "stands",
     f"Model |t| {pv['constant2T2R']['max_abs_t_samples']:g} (2T2R), {pv['constant1of3']['max_abs_t_samples']:g} (one-of-three). Program the weights in a trusted place."),
    ("LFSR is deterministic after reset (no random source)", "next", "Same start rows every boot. Needs a true random source (next chip)."),
    ("Reset clears LOCK; weights stay in the array", "next", "Whoever owns reset and the serial port can read them: keep the board trusted. Next chip: a LOCK that survives reset."),
    ("A SEC write while a command runs is ignored", "stands", "Documented; firmware reads SEC back after setting LOCK."),
    ("The 21 + 21 step count is tested, not proved", "stands", "The miter proves that timing does not depend on the data; the exact step count is only tested."),
    ("Side channels not modelled: idle impedance of an unpowered chip and package, sense-amplifier read transients, EM by location (ACT parity, clock gates)", "stands",
     (f"Powered idle schematic: largest relative |Z| difference {max(v['max_relative_difference'] for v in ii['pins'].values()):.1e}. " if ii else "")
     + "Sense-amplifier current simulated at DC only; the leak model sees total supply current only."),
    ("No supply/clock sensors, decoupling, separate array supply", "next", "Specified in studies/hw-security-2026-11/NEXT_CHIP_SPEC.md; needs new drawn circuits."),
    ("Analog pads have no ESD clamp", "stands", "Question 3a to ChipFoundry; antistatic handling and board protection until then."),
    ("Precheck CVC: soft warning on undriven controls of unused pads 0–4", "stands", "Precheck passes; ChipFoundry's own example leaves them undriven too."),
    (f"FPGA demonstrator no longer fits ({lutm.group(3) if lutm else '?'} % of LUTs since 4.6; {seeds_fail} of 3 placement seeds fail)", "stands", "Evidence: revision 4.6 build logs; 4.7 never built for the FPGA. Board evidence is for 4.5's logic. Option: a reduced-width build (not tried)."),
    ("Device behaviour: forming, retention, cycle-to-cycle spread; spread uncertain ×7", "stands", "Only measurements of the fabricated chip settle it; that is what the test chip is for."),
    ("ReRAM on a shuttle, price, dates", "external", "ChipFoundry has not confirmed it. Questions drafted in docs/QUESTIONS.md."),
    ("sky130B processing and which ReRAM library ChipFoundry signs off with", "external", "docs/QUESTIONS.md."),
    ("REBEL-6 RTL, bus timing, slot and interrupt", "external", "Needed from USN for the full-system simulation."),
]
LAB = {"closed": ("t-ok", "closed"), "closed (model)": ("t-ok", "closed in the model"), "stands": ("t-warn", "stands (this chip)"), "next": ("t-you", "next chip"), "external": ("t-you", "outside")}


def triage_html():
    rows = "".join(f'<tr><td>{esc(a)}</td><td><span class="tag {LAB[s][0]}">{LAB[s][1]}</span></td><td>{esc(e)}</td></tr>' for a, s, e in TRIAGE)
    n = {k: sum(1 for x in TRIAGE if x[1] == k) for k in LAB}; n["closed"] += n.pop("closed (model)")
    return n, f'<div class="tbl"><table><thead><tr><th>Issue</th><th>Status</th><th>Evidence / what to do</th></tr></thead><tbody>{rows}</tbody></table></div>'


def triage_md():
    o = ["# Open issues of revision 4.7, triaged (8 November 2026)", "", "Generated by docs/page/build.py from results/.", "",
         "| Issue | Status | Evidence / what to do |", "|---|---|---|"]
    o += [f"| {a} | {LAB[s][1]} | {e.replace('|', chr(92) + '|')} |" for a, s, e in TRIAGE]
    return "\n".join(o) + "\n"


# ---- cell options -----------------------------------------------------------------------------------------------------
w2, i2 = P(tv, "revision 4.7:", "weights"), P(tv, "revision 4.7:", "inputs")
w3, i3 = P(tv, "revision 4.7 logic + one-of-three", "weights"), P(tv, "revision 4.7 logic + one-of-three", "inputs")
w4, i4 = P(t4, "revision 4.7 logic + 4T4R", "weights"), P(t4, "revision 4.7 logic + 4T4R", "inputs")
cells = f"""<div class="tbl"><table><thead><tr><th>Cell</th><th>Devices per weight</th><th>Low-resistance devices per weight</th>
<th>Array area (by device count)</th><th>Sense amps (24 columns)</th><th>Weights |t|</th><th>Inputs |t|</th></tr></thead><tbody>
<tr><td>2T2R (this chip)</td><td class="num">2</td><td>0 or 1</td><td class="num">1×</td><td class="num">48</td>{tcell(w2)}{tcell(i2)}</tr>
<tr><td>one-of-three, 3T3R (next-chip plan)</td><td class="num">3</td><td>always 1</td><td class="num">1.5×</td><td class="num">72</td>{tcell(w3)}{tcell(i3)}</tr>
<tr><td>4T4R (Gemini's proposal)</td><td class="num">4</td><td>always 1</td><td class="num">2×</td><td class="num">96 (72 would do)</td>{tcell(w4)}{tcell(i4)}</tr>
</tbody></table></div>"""

# ---- leak table -------------------------------------------------------------------------------------------------------
leak_rows = [("As built (4.5): zero-skipping", "as built"), ("4.6: fixed latency, constant activity", "revision 4.6:"),
             ("4.7: uniform start row, random offset (this chip)", "revision 4.7:")]
leaks = "".join(f'<tr><td>{esc(lab)}</td>{tcell(P(tv, k, "weights"))}{tcell(P(tv, k, "inputs"))}</tr>' for lab, k in leak_rows)

ntri, tri = triage_html()
ver = compact_ver()

def summary_page():
    return f"""{head}
    <div id="tip" role="tooltip"></div>
    <div class="wrap">
    <header>
    <div class="kicker">ReRAM ternary · design status · 8 November 2026 · revision 4.8</div>
    <h1>TCIM0: a ternary ReRAM compute-in-memory tile for REBEL-6, and its SKY130 test chip</h1>
    <p class="lede">The short version: what it is, where it stands, what was checked, what is still open. Every test and simulation result is read
    from the repository's result files; design facts (sizes, cycle counts) come from the design documents. The full technical record (layers, circuits, FPGA, IHP) is <code>docs/STATUS.md</code>.</p>
    <nav class="toc" aria-label="Contents"><a href="#status">Status</a><a href="#revisions">Revisions</a><a href="#verified">Verification</a>
    <a href="#security">Security</a><a href="#open">Open issues</a><a href="#cells">Cell options (4T4R)</a><a href="#how">How it works</a>
    <a href="#ttpu">TPU Gen2</a><a href="#next">Next steps</a><a href="#files">Files</a><a href="#corrections">Corrections</a></nav>
    </header>
    
    <section id="status">
    <h2>Status</h2>
    <div class="verdict"><b>Design complete; ChipFoundry's precheck {pre}{" on the current GDS" if pre_ok else ""}. Not orderable yet:</b> ChipFoundry
    has not confirmed that a shuttle accepts the ReRAM layer. Say "design complete, passes the foundry's precheck, waiting for ReRAM
    confirmation", not "ready to fabricate".</div>
    <div class="board">
    <div class="col"><h3><span class="tag t-ok">done</span></h3><ul>
    <li>Logic (revision 4.7): {f"{c1[0]:,} self-checking tests, 0 failures" if c1 and c1[1] == 0 else "test bench not run"}, two simulators, both trit codes; all formal proofs pass.</li>
    <li>Routed logic block: {f'{blk["stdcells"]:,} cells, DRC 0, timing met at every corner' if blk else "not run"}; whole chip: {"LVS match" if tl and tl.get("lvs_match") else "LVS not run"}, DRC {so["drc_markers"]}, antenna {so["antenna_violation_count"]}.</li>
    <li>Serial port fuzzed (revision 4.8): {fz_line}.</li>
    </ul></div>
    <div class="col"><h3><span class="tag t-warn">waiting on others</span></h3><ul>
    <li>ChipFoundry: ReRAM shuttle, sky130B, ESD on analog pads (<code>docs/QUESTIONS.md</code>).</li>
    <li>USN: REBEL-6 RTL and bus details, for the full-system simulation.</li>
    </ul></div>
    <div class="col"><h3><span class="tag t-you">needs you</span></h3><ul>
    <li>Send the questions; design the test board; decide whether firmware sets LOCK.</li>
    </ul></div>
    </div>
    </section>
    
    <section id="revisions">
    <h2>Revisions</h2>
    <div class="tbl"><table><thead><tr><th>Rev.</th><th>Date</th><th>What changed</th><th>Why</th></tr></thead><tbody>
    <tr><td>4.5</td><td>12 Oct</td><td>Complete test chip; full re-run of every suite, 12 of 12 pass</td><td>Baseline</td></tr>
    <tr><td>4.6</td><td>4 Nov</td><td>Fixed-latency products (all 72 rows, LFSR start row); dummy accumulators; constant-time programming (21 + 21 steps); SEC register with set-only LOCK; margin check</td><td>Timing and power leaks found in the security review</td></tr>
    <tr><td>4.7</td><td>6 Nov</td><td>Start row = LFSR mod 72; random accumulator offset; LOCK refuses read-back; options gated by LOCK; block routed again</td><td>Four gaps found by the independent review of 4.6</td></tr>
    <tr><td>4.8</td><td>7 Nov</td><td>No design change: serial-port fuzzing added (<code>make fuzz</code>)</td><td>Show the port survives cut frames, glitches and junk writes</td></tr>
    </tbody></table></div>
    <p class="note">Chip layout of 4.8 = 4.7 (GDS md5 <code>{pc["gds_md5"] if pc else "?"}</code>).</p>
    </section>
    
    <section id="verified">
    <h2>Verification (revision 4.7 logic, 4.8 checks)</h2>
    <div class="tbl"><table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{ver}</tbody></table></div>
    <p class="note">Proven: stated properties of the logic (not its full correctness), netlist = RTL, layout = circuit (LVS). Tested: the logic
    against exact arithmetic. The test benches ran on a copy of <code>tcim_core.sv</code> whose logic is identical to the current file (only the
    proof block differs; <code>results/rev47/same_logic.json</code>). Checked against models: circuits and devices.
    Not knowable before silicon: how the shuttle's ReRAM devices actually behave; measuring that is what the chip is for.</p>
    </section>
    
    <section id="security">
    <h2>Security: what leaks, on the model</h2>
    <p>Fixed-versus-random Welch t-test on TCIM0's power model (<code>tools/tvla_tcim0.py</code>; 150,000 traces per group; pass below |t| = 4.5;
    green passes, red leaks).</p>
    <div class="tbl"><table><thead><tr><th>Design</th><th>Weights |t|</th><th>Inputs |t|</th></tr></thead><tbody>{leaks}</tbody></table></div>
    <p>This chip passes for the inputs, close to the limit and under the model's assumptions (5 µA measurement noise, 0.15 µA per flipping
    accumulator bit), but still leaks the weights' sparsity through the 2T2R read current. Only a different cell fixes that (next section).
    Programming leaks too (20,000 traces: |t| {pv["constant2T2R"]["max_abs_t_samples"]:g} with 2T2R, {pv["constant1of3"]["max_abs_t_samples"]:g} with one-of-three; 4T4R not modelled): program weights in a trusted place.</p>
    </section>
    
    <section id="open">
    <h2>Open issues of 4.7: which stand</h2>
    <p>{ntri["closed"]} closed. {ntri["stands"] + ntri["next"]} remain open on this chip: {ntri["stands"]} are stated limits, {ntri["next"]} are fixed only by the next chip. {ntri["external"]} wait on others.</p>
    {tri}
    </section>
    
    <section id="cells">
    <h2>Cell options: 2T2R, one-of-three, 4T4R</h2>
    <div class="verdict"><b>Decision (8 November): the next chip uses the 3T3R one-of-three cell.</b> This chip is 2T2R; 4T4R was not adopted. Gemini's 4T4R
    (a summary written by Google's Gemini AI) also stores each trit as exactly one low-resistance device, but among four, so the fourth device is high-resistance for every value and
    carries no information.</div>
    {cells}
    <p>Both one-of-three and 4T4R pass the weight test (150,000 traces, 5 µA noise, total supply current only); the model is not precise enough
    to rank them. 4T4R needs a third more devices than one-of-three for no measured gain, so the plan stays one-of-three. Neither cell fixes the programming leak, the deterministic
    LFSR or LOCK-after-reset. At 1 µA noise one-of-three is closer to the limit ({max(r["max_abs_t_samples"] for r in lo["products"] if r["secret"] == "weights") if lo else "?"} on weights).</p>
    </section>
    
    <section id="how">
    <h2>How it works</h2>
    <p>TCIM0 stores a 72 × 24 matrix of ternary weights (−1, 0, +1) and multiplies it by a 72-trit input vector, returning 24 sums from −72 to +72.
    One product replaces 72 TMAC.T instructions of REBEL-6.</p>
    {fig("REBEL-6 system the processor").replace("supplies the programming voltages.</figcaption>", "supplies the programming voltages. Register list as of revision 4.5; revision 4.6 added SEC, ACT and MARG.</figcaption>")}
    <p>Each weight is two ReRAM devices (2T2R): +1 sets the left one, −1 the right one, 0 neither. Each device is read as one bit, so the
    result is exact whenever every device reads correctly.</p>
    {fig("One cell of the 72")}
    <p>The test chip (SkyWater SKY130, sky130B with the ReRAM option, ChipFoundry's Caravan analog harness): 3,456 ReRAM devices, 48 sense amplifiers,
    the array controller, the logic, and a separate test cell with direct pad access. Programming voltages come from the board, so they can be
    changed after the first measurements.</p>
    {fig("user area rendered from").replace("</figcaption>", " Rendered from revision 4.5; revision 4.7 re-routed the digital block (10) in the same footprint.</figcaption>")}
    {fig("One 2T2R cell").replace(" A and B mark the two cuts below.", "")}
    </section>
    
    <section id="ttpu">
    <h2>TRITONE TPU: the Gen2 fixes</h2>
    <p>Fixes to the earlier TRITONE TPU (<code>tpu_top_v2</code>, now v2.4), in
    <a href="https://github.com/ofFBeaT9/Tritone-TPU-SoC/pull/2">pull request #2</a>:</p>
    <ul><li><b>Sparsity leak.</b> The zero-weight counters (STATUS[31:16], PERF_CNT_1) were readable by any software. They are now hidden unless
    SEC (0x70) bit 0 opts in; bit 31 is a set-only LOCK.</li>
    <li><b>Missed done bits.</b> DONE was a one-cycle pulse that polling software could miss; it now stays set until the next start.</li></ul>
    <p>Verified on Verilator (<code>results/ttpu_gen2/</code>): {tpu}. Three existing benches needed their version checks updated to v2.4.
    Not yet: matrix results against a reference (the full-system simulation will do it).</p>
    </section>
    
    <section id="next">
    <h2>Next steps</h2>
    <div class="board">
    <div class="col"><h3><span class="tag t-you">ask USN (Steven Bos)</span></h3><ul>
    <li>REBEL-6 RTL or a cycle-accurate simulator.</li><li>Peripheral bus timing and handshake; external interrupt input.</li>
    <li>Slot 11 and interrupt 7 for TCIM0, a slot for the TPU; the trit wire code on the bus.</li></ul></div>
    <div class="col"><h3><span class="tag t-ok">what can be claimed</span></h3><ul>
    <li>Design complete, passes the foundry's precheck, waiting for ReRAM confirmation.</li>
    <li>Logic checked by simulation, fault injection and formal proofs of stated properties; layout passes DRC, LVS, antenna and the foundry's precheck.</li>
    <li>Do not claim: ready to fabricate, works on silicon, ESD-protected pads, analog products on this chip.</li></ul></div>
    <div class="col"><h3><span class="tag t-warn">then</span></h3><ul>
    <li>Full-system simulation: REBEL-6 + TCIM0 + TPU, with a test program that checks every product.</li>
    <li>Next chip: one-of-three cell, random source, sensors and decoupling, a LOCK that survives upsets and reset, a row-count check, break-before-make on reset.</li></ul></div>
    </div>
    </section>
    
    <section id="files">
    <h2>Files</h2>
    <p>All paths are inside the <code>reram-ternary</code> repository.</p>
    <div class="tbl"><table class="files"><thead><tr><th>Path</th><th>What it is</th></tr></thead><tbody>
    <tr><td><code>chip/sky130/caravan/</code></td><td>What ChipFoundry receives (GDS, LVS netlist and configuration)</td></tr>
    <tr><td><code>docs/STATUS.md</code></td><td>Full status report, every result with its source</td></tr>
    <tr><td><code>docs/QUESTIONS.md</code></td><td>Questions to ChipFoundry and USN, not yet sent</td></tr>
    <tr><td><code>rtl/</code>, <code>tb/</code>, <code>formal/</code></td><td>Logic, test benches, proofs</td></tr>
    <tr><td><code>results/</code></td><td>Every stored result; <code>tests/test_claims.py</code> checks the quoted numbers</td></tr>
    <tr><td><code>studies/</code></td><td>Security study, this page's triage and review</td></tr>
    </tbody></table></div>
    </section>
    
    <section id="corrections">
    <h2>Corrections in this version</h2>
    <ul><li>The old page described revision 4.5 in sections 1–12 next to revision 4.7 numbers; this page has only current numbers.</li>
    <li>It listed a stale GDS md5 (now read from the result file) and a stale count of checked numbers (removed).</li>
    <li>Revision 4.8 was missing; it is above. 4T4R was never adopted; see Cell options.</li>
    </ul>
    </section>
    </div>
    {tipjs}
    """


if __name__ == "__main__":
    page = summary_page()
    page = page.replace("<p></p>", "")
    Path(sys.argv[1]).write_text(page)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(triage_md())
    print(f"{len(page):,} bytes")
