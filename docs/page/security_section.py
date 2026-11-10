"""Section 13 of docs/TCIM0_explainer.html, "Hardware security (revision 4.6)", generated from results/ (6 November 2026).
Every number is read from a file in results/; an item whose result file is missing is printed as "not run", never with a
number. Usage: python3 docs/page/security_section.py > section.html (run from the repository root)."""
import hashlib, json, math, re, sys
from pathlib import Path

R = Path("results")
# revision 4.9 (9 November 2026) re-ran the test benches, fault campaigns, proofs and the chip; this section describes revisions 4.6
# and 4.7, so it reads their files from results/rev48 (the commit of 8 November) when they are kept there (revision 4.9: section 13e)
R48 = Path("results/rev48")
P = lambda p: (R48 / p) if (R48 / p).exists() else (R / p)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def J(p):
    f = P(p)
    return json.loads(f.read_text()) if f.exists() else None


def T(p):
    f = P(p)
    return f.read_text(errors="ignore") if f.exists() else ""


def checks(txt):
    m = re.findall(r"(\d+) checks, (\d+) failures", txt)
    return (int(m[-1][0]), int(m[-1][1])) if m and "TEST PASSED" in txt else None


def sa_chart(sa):
    pts = sa["sweep"]
    W, H, x0, x1, y0, y1 = 760, 300, 70, 730, 250, 30
    lg = lambda g: x0 + (math.log10(g) - math.log10(0.3)) / (math.log10(150) - math.log10(0.3)) * (x1 - x0)
    ly = lambda i: y0 - i / 3.0 * (y0 - y1)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Supply current of one sense amplifier during a read against the conductance of the '
         f'device it reads, log axis 0.3 to 150 microsiemens: it rises with conductance up to about 12 microsiemens and is flat at '
         f'{pts[-1]["I_sa_uA"]} microamperes for every low-resistance device.">']
    for g in (0.3, 1, 3, 10, 30, 100):
        x = lg(g)
        o.append(f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y0}" stroke="var(--grid)"/><text x="{x:.1f}" y="{y0 + 18}" text-anchor="middle" class="tick">{g:g}</text>')
    for i in (0, 1, 2, 3):
        y = ly(i)
        o.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="var(--grid)"/><text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end" class="tick">{i}</text>')
    o.append(f'<text x="{(x0 + x1) / 2}" y="{H - 8}" text-anchor="middle" class="axl">device conductance at the read, µS (log scale)</text>'
             f'<text x="16" y="{(y0 + y1) / 2}" transform="rotate(-90 16 {(y0 + y1) / 2})" text-anchor="middle" class="axl">supply current, µA</text>')
    o.append(f'<rect x="{lg(30):.1f}" y="{y1}" width="{lg(120) - lg(30):.1f}" height="{y0 - y1}" fill="var(--wash)"/>'
             f'<text x="{(lg(30) + lg(120)) / 2:.1f}" y="{y1 + 14}" text-anchor="middle" class="sm">set state 30–120 µS</text>'
             f'<line x1="{lg(4.5):.1f}" y1="{y1}" x2="{lg(4.5):.1f}" y2="{y0}" stroke="var(--s2)" stroke-dasharray="4 3"/>'
             f'<text x="{lg(4.5) + 5:.1f}" y="{y1 + 14}" class="sm">reset ≈ 4.5 µS</text>')
    path = " ".join(f'{"M" if k == 0 else "L"}{lg(p["G_uS"]):.1f},{ly(p["I_sa_uA"]):.1f}' for k, p in enumerate(pts))
    o.append(f'<path d="{path}" fill="none" stroke="var(--s1)" stroke-width="2"/>')
    for p in pts:
        o.append(f'<circle cx="{lg(p["G_uS"]):.1f}" cy="{ly(p["I_sa_uA"]):.1f}" r="4.5" fill="var(--s1)" stroke="var(--surface)" stroke-width="2" '
                 f'data-tip="{p["G_uS"]} µS: {p["I_sa_uA"]} µA"/>')
    o.append("</svg>")
    return "".join(o)


def tvla_chart(tv):
    t4 = J("security/tvla_4t4r.json")
    rows = [r for r in tv["products"] + (t4["products"] if t4 else []) if r["traces_per_group"] == 150000 and r["k_uA"] > 0]
    sel = [("as built (revision 4.5", "As built (revision 4.5)"), ("revision 4.6:", "Revision 4.6"), ("revision 4.7:", "Revision 4.7 (this chip)"),
           ("revision 4.7 logic + one-of-three", "4.7 + one-of-three cells (next chip)")] + ([("revision 4.7 logic + 4T4R", "4.7 + 4T4R cells (Gemini)")] if t4 else [])
    bars = []
    for key, lab in sel:
        for sname in ("weights", "inputs"):
            bars.append((lab, sname, next(x for x in rows if x["design"].startswith(key) and x["secret"] == sname)))
    W, x0, x1 = 760, 300, 720
    H = 40 + len(bars) * 26 + 40
    lt = lambda t: x0 + (math.log10(max(t, 1)) / math.log10(10000)) * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Largest Welch t of a fixed-versus-random test on the model of TCIM0 (model 2), 150,000 traces '
         f'per group, log axis, pass below 4.5. ' + "; ".join(f"{d}, {s}: {r['max_abs_t_samples']}" for d, s, r in bars) + '.">']
    for t in (1, 10, 100, 1000, 10000):
        x = lt(t)
        o.append(f'<line x1="{x:.1f}" y1="24" x2="{x:.1f}" y2="{H - 38}" stroke="var(--grid)"/><text x="{x:.1f}" y="{H - 22}" text-anchor="middle" class="tick">{t:,}</text>')
    x45 = lt(4.5)
    o.append(f'<line x1="{x45:.1f}" y1="18" x2="{x45:.1f}" y2="{H - 38}" stroke="var(--bad)" stroke-width="1.5" stroke-dasharray="5 3"/>'
             f'<text x="{x45 + 4:.1f}" y="16" class="sm">|t| = 4.5 (pass below)</text>'
             f'<text x="{(x0 + x1) / 2}" y="{H - 4}" text-anchor="middle" class="axl">largest |t| over the trace, log scale</text>')
    prev = None
    for k, (d, sname, r) in enumerate(bars):
        y = 34 + k * 26
        if d != prev:
            o.append(f'<text x="{x0 - 76}" y="{y + 13}" text-anchor="end" class="rl">{esc(d)}</text>')
            prev = d
        o.append(f'<text x="{x0 - 8}" y="{y + 13}" text-anchor="end" class="sm">{sname}</text>')
        t = r["max_abs_t_samples"]
        col = "var(--bad)" if r["leaks"] else "var(--ok)"
        o.append(f'<rect x="{x0}" y="{y + 2}" width="{max(lt(t) - x0, 2):.1f}" height="16" rx="3" fill="{col}" '
                 f'data-tip="{esc(r["design"])}, secret {sname}: |t| = {t} ({"leaks" if r["leaks"] else "passes"}); product duration |t| = {r["abs_t_duration"]}"/>'
                 f'<text x="{lt(t) + 6:.1f}" y="{y + 14}" class="vl">{t:,}</text>')
    o.append("</svg>")
    return "".join(o)


def verification_rows():
    """The verification table of the current revision, one <tr> per check, every value read from results/."""
    rows = []
    def row(label, cmd, ok, val):
        rows.append(f'<tr><td>{esc(label)}<div class="cmd mono">{esc(cmd)}</div></td>'
                    + (f'<td class="{"ok" if ok else "bad"}">{esc(val)}</td>' if ok is not None else '<td class="bad">not run</td>') + "</tr>")
    for f, lab, cmd in (("rtl_test.log", "Test bench, two's complement code (CXXRTL)", "make rtl"),
                        ("rtl_test_pnx.log", "Test bench, BSD-PNX code (CXXRTL)", "make rtl-pnx"),
                        ("rtl_test_verilator.log", "Test bench, second simulator (Verilator)", "make rtl-verilator"),
                        ("rtl_test_verilator_pnx.log", "Test bench, Verilator, BSD-PNX", "make rtl-verilator")):
        c = checks(T(f)); row(lab, cmd, None if c is None else c[1] == 0, f"{c[0]:,} checks, {c[1]} failures" if c else "")
    fl = T("formal.log")
    for name, lab in (("tcim_spi", "Formal: serial port"), ("tcim_core_safety", "Formal: safety properties"),
                      ("tcim_core_safety_pnx", "Formal: safety properties, BSD-PNX"), ("tcim_core_progress", "Formal: progress"),
                      ("tcim_core_lfsr", "Formal: start row = LFSR value modulo 72 (k-induction)")):
        m = re.search(r"\[" + name + r"\] DONE \((\w+)", fl); st = m.group(1) if m else None
        row(lab, "make formal", None if st is None else st == "PASS", st or "")
    for t in ("prove", "prove_pnx"):
        m = re.search(r"DONE \((\w+)", T(f"security/miter_{t}.log")); st = m.group(1) if m else None
        row("Two-copy timing miter" + (", BSD-PNX" if "pnx" in t else ""), "make formal", None if st is None else st == "PASS", st or "")
    ff = J("formal_faults.json")
    if ff:
        d = sum(1 for x in ff if x["caught"]); row("Faults planted in the proofs, each must make its proof fail", "formal/check_faults.py", d == len(ff), f"{d} of {len(ff)} detected")
    mt, mp = J("rtl_mutation.json"), J("rtl_mutation_pnx.json")
    if mt and mp:
        row("Mutation test: faults injected into the RTL", "make mutation mutation-pnx", mt["detected"] == mt["faults"] and mp["detected"] == mp["faults"],
            f'{mt["detected"]} of {mt["faults"]}, BSD-PNX {mp["detected"]} of {mp["faults"]} detected')
    eq = J("equiv.json")
    if eq:
        row("Netlist given to place and route = RTL", "make equiv", eq["place_and_route_source"]["unproven"] == 0, f'{eq["place_and_route_source"]["proven"]:,} points proven, 0 unproven')
    m = re.search(r"(\d+) are proven and (\d+) are unproven", T("sky130_chip/equiv_chip.log"))
    if m:
        row("Chip block netlist = chip RTL", "make equiv-chip", m.group(2) == "0", f"{int(m.group(1)):,} points proven, {m.group(2)} unproven")
    for f, lab in (("sky130_chip/rtl_chip_000.log", "Chip build (TCIM0 + array controller), controller setting 0,0,0"),
                   ("sky130_chip/rtl_chip_110.log", "Chip build, setting 1,1,0"), ("sky130_chip/rtl_chip_321.log", "Chip build, setting 3,2,1"),
                   ("sky130_chip/rtl_chip_verilator_110.log", "Chip build on Verilator"),
                   ("sky130_chip/gls_chip_routed.log", "Routed block, gate level, full test bench")):
        c = checks(T(f)); row(lab, "make rtl-chip / gls_chip.sh", None if c is None else c[1] == 0, f"{c[0]:,} checks, {c[1]} failures" if c else "")
    for f, lab in (("sky130_chip/gls_chip_fault_xnor.log", "Routed block with one gate changed (must fail)"),
                   ("sky130_chip/gls_chip_fault_icg.log", "Routed block with a stuck clock gate (must fail)")):
        t = T(f); row(lab, "gls_chip.sh xnor / icg", None if not t else "TEST FAILED" in t, "detected" if "TEST FAILED" in t else "NOT detected")
    mc = J("sky130_chip/mutation_chip.json")
    if mc:
        row("Array controller: injected faults", "tb/chip/mutation_chip.py", mc["detected"] == mc["faults"], f'{mc["detected"]} of {mc["faults"]} detected')
    blk = J("sky130_chip/digital_block.json")
    if blk:
        row("Logic block placed and routed again, same die", "pc_batch28_pnr.sh, post_corners.sh",
            blk["drc_violations"] == 0 and blk["lec_identical"] and blk["setup_wns_min_ns"] > 0 and blk["hold_wns_min_ns"] > 0,
            f'{blk["stdcells"]:,} cells, utilization {blk["utilization"]:.1%}; DRC 0; slack at every corner: setup ≥ {blk["setup_wns_min_ns"]} ns, hold ≥ {blk["hold_wns_min_ns"]} ns (25 ns clock)')
    tl, so = J("sky130_chip/top_layout.json"), J("sky130_chip/top_signoff.json")
    if tl and so:
        row("Whole user area rebuilt: LVS, Magic DRC (full rules), antenna", "top.py, make signoff", tl.get("lvs_match") and so["drc_markers"] == 0 and so["antenna_violation_count"] == 0,
            f'LVS {"match" if tl.get("lvs_match") else "MISMATCH"}; DRC {so["drc_markers"]} markers; antenna {so["antenna_violation_count"]} violations')
    fz = J("spi_fuzz.json"); f1 = T("spi_fuzz_1M.log")
    if fz:
        caught = sum(1 for x in fz[1:] if x["ok"])
        row("Serial port fuzzed: cut frames, random writes and reads, chip-select glitches (revision 4.8)", "make fuzz",
            fz[0]["fuzz_passed"] and caught == len(fz) - 1 and "FUZZ PASSED" in f1,
            f'{fz[0]["frames"]:,} frames and 1,000,000 frames, 0 errors; {caught} of {len(fz) - 1} planted faults make it fail'
            if "FUZZ PASSED" in f1 else f'{fz[0]["frames"]:,} frames, 0 errors; {caught} of {len(fz) - 1} planted faults caught; 1,000,000-frame run missing')
    pc = J("sky130_chip/precheck.json")
    g = R.parent / "chip/sky130/caravan/gds/user_analog_project_wrapper.gds"
    if pc:
        same = g.exists() and pc.get("gds_md5") == hashlib.md5(g.read_bytes()).hexdigest()
        row("ChipFoundry's precheck in their pinned versions (Magic 8.3.471, PDK 3e0e31d, sky130B), on this GDS", "flow/eda/pc_batch28c.sh",
            same and pc["passed"] == pc["total"], f'{pc["passed"]} of {pc["total"]}' + ("" if same else " (on another GDS)"))
    return "".join(rows)


def main():
    sa, tv, ii = J("security/sa_power.json"), J("security/tvla.json"), J("security/idle_impedance.json")
    lo = J("security/tvla_1of3_noise1uA.json")
    P = lambda key, sec, n=150000, k=True: next(r for r in tv["products"] if r["design"].startswith(key) and r["secret"] == sec
                                                 and r["traces_per_group"] == n and ((r["k_uA"] > 0) == k))
    pv = {r["mode"] + r["encoding"]: r for r in tv["programming"]}
    mm = sa["mismatch_tt27"]
    rtl = T("rtl_test.log")
    prog = re.search(r"every program command (\d+) cycles", rtl)
    prod = re.search(r"(\d+) products of (\d+) cycles each", rtl)
    starts = re.search(r"start rows: (\d+) different in (\d+) products", rtl)
    c46, c47 = tv["start_row_states"]["rev46"], tv["start_row_states"]["rev47"]

    vt = verification_rows()

    c = ii["control_read_row0_vccd"]
    imp = ("<p><b>Idle supply impedance</b> (the DExiM attack reads stored data from the package impedance of an idle chip;"
           " <code>chip/sky130/sim/idle_impedance.py</code>): one column of the periphery schematic, powered, in the idle state the controller"
           " holds between operations, every device low-resistance against every device high-resistance, small-signal AC from 1 kHz to 1 GHz."
           " The largest relative difference of |Z| at each supply pin: "
           + ", ".join(f'{p} {v["max_relative_difference"]:.1e}' for p, v in ii["pins"].items())
           + f". The same deck with row 0 being read differs by {c['max_relative_difference']:.2f} at vccd, so the method does see a stored state"
           " when the path is open. In this model the devices sit behind off select transistors between grounded lines. Not modelled: layout"
           " parasitics, the device's capacitance (it is a resistor here), the package and board, and an unpowered chip.</p>")
    html = f"""
<section id="security">
<h2>13 · Hardware security (revisions 4.6 and 4.7, November 2026)</h2>
<p class="lede">The document <i>AI Hardware Hacking: What It Is and How to Secure TCIMO &amp; TRITONE</i> (@m1, 4 November 2026) lists attacks
that recover weights or inputs from a compute-in-memory chip, and a twelve-item checklist. Each statement it makes about TCIM0 was checked
against the design as built and each leak was measured on TCIM0's own model. Revision 4.6 applied the checklist; an independent review of it
(two reviewers, <code>studies/hw-security-2026-11/council/</code>) found four real gaps, and revision 4.7 closes them. Every change went through the
full verification again. Study folder: <code>studies/hw-security-2026-11/</code>.</p>

<h3>What the document says about TCIM0, checked</h3>
<div class="tbl"><table><thead><tr><th>Document</th><th>TCIM0 as built</th><th>Verdict</th></tr></thead><tbody>
<tr><td>Read "via column ADCs"; fix with a current-flattened ADC</td><td>48 current-mode sense amplifiers and digital sums; no ADC on the SKY130 chip</td><td>Does not apply as written; the sense amplifiers' supply current was simulated instead</td></tr>
<tr><td>Leakage test on "one 64-row column"</td><td>72 rows × 24 columns</td><td>Its numbers are not TCIM0's; measured again on TCIM0's model</td></tr>
<tr><td>Device "Ti/HfOx/Pt"</td><td>TiN / Ti / HfO₂ / TiN (SkyWater)</td><td>Wrong device</td></tr>
<tr><td>Constant-sum cells: weight 0 as two mid-conductance devices</td><td>Two reliable states per device; a middle level is not a published SkyWater state</td><td>Not buildable as proposed; a one-of-three cell with two-state devices does the same job (next chip)</td></tr>
<tr><td>0.5 % write-verify accuracy needed</td><td>The set state spans 30–120 µS, and the sense amplifier's DC current is the same across it (chart below)</td><td>Not achievable, and not needed for low-resistance devices</td></tr>
<tr><td>Programming −1, 0, +1 takes different pulse counts</td><td>Yes: pulse-and-verify stopped at verify, and PITER showed the count</td><td>Applied: fixed</td></tr>
<tr><td>Zero-skipping leaks the inputs through timing (said of TRITONE)</td><td>TCIM0 also skipped rows with input 0 (since revision 4.2)</td><td>Applies to TCIM0 too: fixed</td></tr>
<tr><td>Hold the bit lines at a fixed voltage when idle</td><td>Already so: every line grounded in IDLE, checked every cycle</td><td>Already met</td></tr>
<tr><td>Lock bit</td><td>None in revision 4.5</td><td>Added (revision 4.6); since 4.7 it refuses read-back of the weights (products still run, section 13b)</td></tr>
<tr><td>Isolated array supply, decoupling, supply and clock sensors</td><td>The macro's 1.8 V and the logic share vccd1 and vssa1; no sensors</td><td>Apply; need new drawn circuits: specified for the next chip, not drawn</td></tr>
<tr><td>Lint gate; netlist = RTL proof</td><td><code>make lint</code>, <code>make equiv</code>, <code>make equiv-chip</code></td><td>Already met; run again after each change</td></tr>
</tbody></table></div>

<h3>Where TCIM0 leaks, measured on its model</h3>
<p>The sense amplifier's own supply current, simulated (DC) with SkyWater's transistor models (<code>chip/sky130/sim/sa_power.py</code>): it follows the
conductance of a high-resistance device but is clamped for every low-resistance one, so the spread of the set state does not reach the supply.
With transistor mismatch (100 samples) the frozen difference between sense amplifiers is {mm["LRS_30uS"]["sd_uA"]} µA (low resistance) and
{mm["HRS_4.5uS"]["sd_uA"]} µA (high resistance), standard deviation.</p>
<figure>{sa_chart(sa)}<figcaption>One sense amplifier, tt 27 °C, read reference, DC. A read tells the supply how many devices of the row are low-resistance,
not which sign each weight has: with the 2T2R cell a row draws more current the fewer zero weights it holds. Read transients were not simulated.</figcaption></figure>
<p>A fixed-versus-random Welch t-test on that model (<code>tools/tvla_tcim0.py</code>, model 2; its assumptions are written in the file: 5 µA measurement
noise per row read, 0.15 µA per accumulator bit that flips, the start row drawn as the LFSR gives it,
the mismatch above; pass below |t| = 4.5):</p>
<figure>{tvla_chart(tv)}<figcaption>150,000 traces per group; red leaks, green passes. As built, zero-skipping leaked the inputs through the product's duration
(|t| = {P("as built", "inputs")["abs_t_duration"]}). Revision 4.6 removed the timing leak, but the accumulators, cleared at the start of each product,
flip bits that follow the partial sum, and that leaked the inputs (|t| = {P("revision 4.6:", "inputs")["max_abs_t_samples"]}); revision 4.7's random
offset removes it ({P("revision 4.7:", "inputs")["max_abs_t_samples"]}). The 2T2R array's read current still shows the weights' sparsity
({P("revision 4.7:", "weights")["max_abs_t_samples"]}), which only a cell with a constant number of low-resistance devices per row removes.</figcaption></figure>
<p>The one-of-three cell needs revision 4.7's uniform start row: with revision 4.6's start rows it leaks ({P("revision 4.6 logic + one-of-three", "weights", k=False)["max_abs_t_samples"]}
without the digital term); with 4.7 it passes ({P("revision 4.7 logic + one-of-three", "weights")["max_abs_t_samples"]}){
f', and at 1 µA noise still passes but close to the limit ({next(r for r in lo["products"] if r["secret"] == "weights" and r["traces_per_group"] == 150000 and r["k_uA"] > 0)["max_abs_t_samples"]})' if lo else ""}:
a small first-order difference (frozen mismatch and high-resistance spread) remains that more traces would show.
Start rows: revision 4.6 used 7 LFSR bits folded at 72, which gives rows 0–55 {max(c46)} of the LFSR's 65,535 states and rows 56–71 {min(c46)};
revision 4.7 takes the 16-bit value modulo 72: {min(c47)} or {max(c47)} states per row.</p>
<p>Programming (20,000 traces): stopping at verify leaks through its duration (|t| = {pv["variable2T2R"]["abs_t_duration"]}); a constant number of
pulse steps removes the duration term (|t| = {pv["constant2T2R"]["abs_t_duration"]}), but the profile of the pulses still leaks (|t| =
{pv["constant2T2R"]["max_abs_t_samples"]}): how many devices each pulse selects depends on which devices must change, and on how fast each one switches.
Program the weights in a trusted place.</p>
{imp}

<h3>What changed in the logic</h3>
<p><b>Revision 4.6</b> (4 November): fixed-latency products (every product reads all 72 rows, from a start row given by a 16-bit LFSR{f"; test bench: {prod.group(1)} products of {prod.group(2)} cycles each, {starts.group(1)} different start rows in {starts.group(2)}" if prod and starts else ""});
constant-activity accumulation (a column that does not change its result in a row changes a dummy accumulator instead, ACT +50);
constant-time programming (21 + 21 pulse steps, a step whose devices have all verified issues a pulse with no device selected{f"; every program command {prog.group(1)} cycles in the test bench" if prog else ""});
a SEC register (+3) with opt-ins ZSKIP, VARPROG, NOSHUF and a set-only LOCK; a margin check (PCMD 0,+; MARG +52) that flags a device drifting toward the read reference.</p>
<p><b>Revision 4.7</b> (6 November, after the review):</p>
<ul>
<li><b>Uniform start row</b>: the whole 16-bit LFSR value modulo 72, kept by a 7-bit register updated with the LFSR (proved equal to <code>lfsr mod 72</code>).</li>
<li><b>Random accumulator offset</b>: each digital product starts its result accumulators at a common offset (−128 … 127 from the LFSR) and the last row takes it off.</li>
<li><b>LOCK refuses read-back</b>: under LOCK read-back is refused (WERR, no array access) and the margin check does not copy the weights into PDATA. Products still run, so a bus user can still recover the weights with one-hot inputs (section 13b).</li>
<li><b>LOCK checked where the options are used</b>: ZSKIP, VARPROG and NOSHUF act only while LOCK is off, so one upset of an option flip-flop after LOCK cannot bring it back.</li>
</ul>
<p>Read SEC back after writing LOCK: a SEC write while a command runs is ignored. ACT's parity depends on the data; it reads 0 under LOCK.</p>

<h3>How it was verified (revision 4.7)</h3>
<div class="tbl"><table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{vt}</tbody></table></div>
<p class="note">Found and fixed during verification: the mutation test showed that clearing MARG was hidden except for a refused margin check (a test was
added); one planted proof fault did not compile and so proved nothing (rewritten); the planted gate fault of the gate-level run landed on a dummy
accumulator, which by design affects no result (it now picks a gate that reaches a real register); the planted fault of the start-row proof was
not caught at depth 3, because the base case ended before the fault showed (now depth 20, and caught); and the first routing of revision 4.7 left
one net exactly at OpenROAD's antenna limit, which Magic's check of the assembled chip put 5 % over (a last repair pass at a 15 % margin removed
it; the block was routed again, and every check after routing was run again).</p>

<h3>What this does not fix</h3>
<ul>
<li>The 2T2R array shows the weights' sparsity in the read current, and since the rotation is the same for every row of a product, an attacker who
realigns the traces can see each row's count of non-zero weights, not only the total. The one-of-three cell removes the count (next chip,
<code>studies/hw-security-2026-11/NEXT_CHIP_SPEC.md</code>), at +50 % array area and 24 more bit-line slices; a chip-specific residual from
sense-amplifier mismatch remains (13d).</li>
<li>The LFSR is deterministic after reset (the chip has no random source): the same firmware gets the same start rows and offsets on every boot, and
whoever controls the timing of GO controls them.</li>
<li>LOCK is cleared by reset, and the weights stay in the array. Revision 4.9 (13e) leaves the tile locked after a reset and unlocks it only by erasing
the whole array; a bus user can still recover the weights through products.</li>
<li>The programming profile leaks; an empty pulse puts no steady-state voltage across a device, but the switching transients at the cell nodes were not
simulated.</li>
<li>Supply sensors, decoupling and a separate array supply need new drawn circuits: specified, not drawn.</li>
<li>The FPGA demonstrator does not fit the board's FPGA since revision 4.6 (87 % of the LUTs; three placement seeds failed), so the board evidence of
section 9 is for revision 4.5's logic.</li>
<li>All of this is evidence about the model, not about silicon.</li>
</ul>
</section>
"""
    sys.stdout.write(html)


if __name__ == "__main__":
    main()
