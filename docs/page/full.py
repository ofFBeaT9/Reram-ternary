"""docs/TCIM0_explainer.html, the full page (8 November 2026, revision 4.8).

The full explainer of revision 4.5 (every figure, 3D view and hands-on model; assemble.py) brought up to date: a new opening
(status, what is done, what remains, what can be done now, revisions, verification), a short "now" box in each section
whose design changed after 4.5, the logic section's registers, checks and timing chart redrawn for 4.7, the security
section with the 4T4R case, the triage of open issues and the cell options, a full TTPU-Gen2 section and the next steps.
Every result is read from results/ (through build.py, security_section.py and assemble.py).
Usage (repository root): python3 docs/page/full.py docs/TCIM0_explainer.html"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build as B  # noqa: E402   (summary page: data, triage, cells, compact verification)

J, T, esc = B.J, B.T, B.esc
tmp = Path(tempfile.mkdtemp()) / "asm.html"
subprocess.run([sys.executable, "docs/page/assemble.py", str(tmp)], check=True, capture_output=True)
s = tmp.read_text()


def cut(a_id, b_id):
    """Text from <section id=a_id> up to (not including) <section id=b_id>."""
    return s.index(f'<section id="{a_id}"'), s.index(f'<section id="{b_id}"')


def sub(old, new, count=1):
    global s
    assert old in s, "missing: " + old[:80]
    s = s.replace(old, new, count)


def now(html):
    return f'<div class="note"><b>Now (revision 4.7/4.8).</b> {html}</div>\n'


def after_h2(sec_id, html):
    global s
    a = s.index(f'<section id="{sec_id}"'); h = s.index("</h2>", a) + len("</h2>")
    s = s[:h] + "\n" + html + s[h:]


blk, pc, so, tl, ac, fz, ep = B.blk, B.pc, B.so, B.tl, B.ac, B.fz, B.ep
chk = lambda f: B.checks(T(f))
c_rtl = chk("rtl_test.log")
mt, mp, mc = J("rtl_mutation.json"), J("rtl_mutation_pnx.json"), J("sky130_chip/mutation_chip.json")
ff = J("formal_faults.json")
gls = chk("sky130_chip/gls_chip_routed.log")
chips = [chk(f"sky130_chip/rtl_chip_{k}.log") for k in ("000", "110", "321")]
mp_ = {r["spef_scale"]: r["min_period_ns"] for r in blk["min_period"]}
ntri = B.triage_html()[0]

# ---------------------------------------------------------------- header
sub('<div class="kicker">ReRAM ternary · design status · 12 October 2026</div>',
    '<div class="kicker">ReRAM ternary · design status · 8 November 2026 · revision 4.8</div>')
a = s.index('<p class="lede">'); b = s.index("</nav>", a) + len("</nav>")
s = s[:a] + """<p class="lede">What the design is, how every part works, what has been checked and how, what is done, what is still open, and what
can be done next. Test and simulation results are read from the repository's result files (<code>make test</code> checks
every number <code>docs/STATUS.md</code> quotes); design facts come from the design files.</p>
<nav class="toc" aria-label="Contents"><a href="#status">Status: done, remaining, next</a><a href="#revisions">Revisions</a><a href="#verified">Is everything verified?</a><a href="#tell">What can be claimed</a><a href="#files">Files</a>
<a href="#idea">1 The idea</a><a href="#weight">2 One weight</a><a href="#structure">3 Layers and materials</a><a href="#handson">Hands-on models</a><a href="#read">4 Reading</a><a href="#program">5 Programming</a><a href="#chip">6 The chip</a>
<a href="#controller">7 Controller</a><a href="#logic">8 Logic design</a><a href="#fpga">9 FPGA proof</a><a href="#layout">10 Layout and sign-off</a><a href="#cf">11 ChipFoundry's tools</a>
<a href="#limits">12 Limits</a><a href="#security">13 Security</a><a href="#open">13b Open issues</a><a href="#cells">13c Cells: 2T2R, one-of-three, 4T4R</a><a href="#ttpu">14 TPU Gen2</a><a href="#next">15 Next: system, USN</a><a href="#nov8">Corrections</a><a href="#glossary">Glossary</a></nav>""" + s[b:]

# ---------------------------------------------------------------- new opening (replaces ready / verified / tell / files)
a, b = cut("ready", "idea")
old_verified = s[s.index('<section id="verified"'):s.index('<section id="tell"')]
files_tbl = re.search(r'<div class="tbl"><table class="files">.*?</table></div>', s[s.index('<section id="files"'):b], re.S).group(0)
files_tbl = re.sub(r"[0-9a-f]{32}", pc["gds_md5"], files_tbl)
files_tbl = files_tbl.replace("today's fresh re-run in <code>results/regress_20261012/</code>", "the 12 October re-run in <code>results/regress_20261012/</code>")
opening = f"""<section id="status">
<h2>Status: what is done, what remains, what we can do now</h2>
<div class="verdict"><b>The design is complete and passes ChipFoundry's own precheck in their pinned tool and PDK versions ({B.pre}).
It cannot be ordered yet:</b> ChipFoundry has not confirmed that any shuttle accepts the ReRAM layer. Say "design complete, passes the
foundry's precheck, waiting for the foundry's confirmation of ReRAM", not "ready to fabricate".</div>
<div class="board">
<div class="col"><h3><span class="tag t-ok">done</span></h3><ul>
<li>Test chip for SkyWater SKY130 (sky130B, ReRAM) in ChipFoundry's Caravan analog harness: 3,456 ReRAM devices, drivers, 48 sense amplifiers, array controller, logic, pads, test cell.</li>
<li>Logic revision 4.7 (hardware security, section 13): {c_rtl[0]:,} self-checking tests per run, 0 failures, 2 simulators × 2 trit codes; {mt["detected"]}/{mt["faults"]} and {mp["detected"]}/{mp["faults"]} injected faults caught; all formal proofs pass, {sum(x["caught"] for x in ff)}/{len(ff)} planted proof faults caught.</li>
<li>Routed logic block {blk["stdcells"]:,} cells, DRC 0, timing met at every corner; whole chip LVS match, DRC {so["drc_markers"]}, antenna 0 in two checkers.</li>
<li>Serial port fuzzed (revision 4.8): {B.fz_line}.</li>
<li>Leakage measured on the chip's model; empty programming pulses simulated (32 runs, closed in the model).</li>
<li>TRITONE TPU fixed (TTPU-Gen2, section 14) and pushed as a pull request.</li>
</ul></div>
<div class="col"><h3><span class="tag t-warn">remaining before a chip can be ordered</span></h3><ul>
<li>ChipFoundry: is ReRAM accepted on a shuttle, which, when, at what price; sky130B processing; their ReRAM sign-off library; ESD clamps on analog pads (<code>docs/QUESTIONS.md</code>, not yet sent).</li>
<li>Test board: programming rails (VPRG, VWLP, VWLR), VREF, IBIAS, a controller on the serial port, a source-measure unit on the test cell, protection diodes on the analog pads.</li>
<li>Decide whether deployed firmware sets LOCK, and keep reset and the serial port trusted.</li>
<li>Submission to the shuttle once ChipFoundry answers.</li>
</ul></div>
<div class="col"><h3><span class="tag t-you">we can do now, without waiting</span></h3><ul>
<li><b>Full-system simulation</b> REBEL-6 + TCIM0 + TPU: with USN's RTL, or with an instruction-set model of REBEL-6 written from the published specification.</li>
<li><b>Test-board design</b>: schematic and parts list from the chip's pad list.</li>
<li><b>FPGA evidence for 4.7</b>: a reduced-width build that fits the Tang Nano 9K, then a recorded board run.</li>
<li><b>TPU</b>: a test bench that checks matrix results against a reference.</li>
<li><b>Simulations still open</b>: sense-amplifier read transients, empty pulses with device capacitance and mixed columns, 4T4R at 1 µA noise.</li>
<li><b>Next chip</b>: start the one-of-three cell and its periphery, a true random source, LOCK that survives reset, a row-count check.</li>
<li><b>Send the questions</b> to ChipFoundry and USN; write the report for your professor.</li>
</ul></div>
</div>
</section>

<section id="revisions">
<h2>Revisions</h2>
<div class="tbl"><table><thead><tr><th>Rev.</th><th>Date</th><th>What changed</th><th>Why</th></tr></thead><tbody>
<tr><td>4.5</td><td>12 Oct</td><td>Complete test chip; every automatic suite re-run from scratch, 12 of 12 pass</td><td>Baseline; sections 1–12 describe it</td></tr>
<tr><td>4.6</td><td>4 Nov</td><td>Fixed-latency products (all 72 rows, LFSR start row); dummy accumulators; constant-time programming (21 + 21 steps); SEC register with set-only LOCK; margin check</td><td>Timing and power leaks found in the security review</td></tr>
<tr><td>4.7</td><td>6 Nov</td><td>Start row = LFSR mod 72; random accumulator offset; LOCK refuses read-back; options gated by LOCK; block placed and routed again</td><td>Four gaps found by the independent review of 4.6</td></tr>
<tr><td>4.8</td><td>7 Nov</td><td>No design change: serial-port fuzzing (<code>make fuzz</code>)</td><td>Show the port survives cut frames, glitches and junk writes</td></tr>
</tbody></table></div>
<p class="note">The chip layout of 4.8 is that of 4.7 (GDS md5 <code>{pc["gds_md5"]}</code>). Sections 1–12 explain the design as built in 4.5;
a "Now" box in each section says what changed since.</p>
</section>

<section id="verified">
<h2>Is everything verified?</h2>
<div class="tbl"><table><thead><tr><th>Check (revision 4.7 logic, 4.8 checks)</th><th>Result</th></tr></thead><tbody>{B.compact_ver()}</tbody></table></div>
<p class="note">Every check, with its command, is in section 13. The full re-run of every suite was last done for revision 4.5 on 12 October
(<code>results/regress_20261012/</code>, 12 of 12 pass); the test benches of 4.7 ran on a copy of <code>tcim_core.sv</code> whose logic is identical to
the current file (only the proof block differs, <code>results/rev47/same_logic.json</code>).</p>
<h3>What "verified" means here, and what it cannot mean</h3>
<div class="board">
<div class="col"><h3><span class="tag t-ok">proven or checked exactly</span></h3><ul>
<li>Stated properties of the logic are proven (serial port, safety, progress, start row, timing independent of data); the logic as a whole is tested against exact arithmetic, on two simulators, in both trit codes, through the chip controller.</li>
<li>The tests can fail: every planted bug was caught ({mt["detected"]}/{mt["faults"]}, {mp["detected"]}/{mp["faults"]}, controller {mc["detected"]}/{mc["faults"]}, proofs {sum(x["caught"] for x in ff)}/{len(ff)}).</li>
<li>What is drawn is what is simulated (LVS); the netlist given to place and route equals the RTL (formal equivalence).</li>
<li>The layout obeys the foundry's rules: DRC 0, antenna 0 in two checkers, ChipFoundry's precheck {B.pre}.</li></ul></div>
<div class="col"><h3><span class="tag t-warn">verified against models</span></h3><ul>
<li>The circuits work in simulation with SkyWater's transistor models over corners, −40 to 125 °C, supply ±10 %, mismatch and the drawn wiring.</li>
<li>Reading and programming work for devices that behave like the device model (fitted to SkyWater's published ReRAM data), also at twice the published spread.</li>
<li>Leakage and empty-pulse results are about the model.</li></ul></div>
<div class="col"><h3><span class="tag t-you">cannot be known before silicon</span></h3><ul>
<li>How the shuttle's ReRAM devices behave: spread, forming, endurance, retention.</li>
<li>So what fraction of the 1,728 weights program correctly, and how accurate the analog read is. That is what the test chip is for (section 12).</li></ul></div>
</div>
</section>

<section id="tell">
<h2>What can be claimed</h2>
<div class="board">
<div class="col"><h3><span class="tag t-ok">accurate</span></h3><ul>
<li>TCIM0 stores a 72 × 24 matrix of ternary weights (−1, 0, +1) in ReRAM and multiplies it by a 72-trit vector, returning 24 integers from −72 to +72; one product replaces 72 TMAC.T instructions of REBEL-6.</li>
<li>Each weight is two ReRAM devices read as one bit each (2T2R), so the digital result is exact when every device reads correctly.</li>
<li>A complete SKY130 test chip has been designed and drawn; it passes DRC, LVS, the antenna rule and ChipFoundry's own precheck ({B.pre}).</li>
<li>The logic is checked by simulation, fault injection and formal proofs of stated properties, also after layout; revision 4.7 adds protections against timing and power side channels, measured on the chip's model.</li>
<li>The device spread is uncertain by a factor of about seven; measuring it is the chip's purpose.</li></ul></div>
<div class="col"><h3><span class="tag t-warn">do not claim</span></h3><ul>
<li>"Ready to fabricate" or "taped out": ReRAM availability is unconfirmed and nothing has been submitted.</li>
<li>"It works on silicon": the devices are modelled, not measured.</li>
<li>That the pads are ESD-protected, or that the chip does analog multi-row products (digital mode only on SKY130).</li>
<li>That the chip is secure: it leaks the weights' sparsity (2T2R), and anyone on the bus can recover the weights through products.</li>
<li>Energy or speed advantages: estimates only.</li></ul></div>
</div>
</section>

<section id="files">
<h2>Where the files are</h2>
<p>Everything is in the <code>reram-ternary</code> repository (your PC copy, and GitHub <code>ofFBeaT9/Reram-ternary</code>).</p>
{files_tbl}
</section>

"""
s = s[:a] + opening + s[b:]

# ---------------------------------------------------------------- "now" boxes in sections whose design changed after 4.5
after_h2("handson", now("Model C shows revision 4.5's product, which skipped rows whose input is 0. Since revision 4.6 every product reads all 72 rows, "
                        "starting from a row the LFSR picks, so its duration no longer tells the inputs (section 13)."))
after_h2("program", now("Pulse-and-verify no longer stops when every device has verified: every program command runs 21 reset and 21 set steps, "
                        "and a step whose devices have all verified issues a pulse with no device selected (an empty pulse). Those empty pulses were "
                        f"simulated on 8 November: peaks {ep['worst_V_selected_row']:.2f} V, drift negligible in the device model (section 13b). "
                        "PITER counts real pulses only and reads 0 under LOCK. A margin check (PCMD 0,+) flags devices drifting toward the read reference."))
after_h2("controller", now(f"The controller is unchanged since 4.5. With the 4.7 logic the chip test bench passes {chips[0][0]:,} / {chips[1][0]:,} / {chips[2][0]:,} checks "
                           f"in the three timing settings, and {mc['detected']} of {mc['faults']} planted controller faults are caught. An asynchronous reset in "
                           "the middle of a pulse is not break-before-make; empty pulses with a reset mid-pulse were simulated (section 13b), a real pulse cut by reset was not."))
after_h2("fpga", now(f"The board evidence below is for revision 4.5's logic. Revision 4.6 and later do not fit the board's FPGA "
                     f"({B.lutm.group(3) if B.lutm else '?'} % of the LUTs; {B.seeds_fail} of 3 placement seeds fail), and 4.7 was never built for it. "
                     "A reduced-width build would restore board evidence for the current logic (not tried)."))
after_h2("layout", now(f"Revision 4.7's logic block was placed and routed again in the same die: {blk['stdcells']:,} cells including antenna diodes, "
                       f"{blk['sequential']:,} flip-flops, {blk['clock_gates']} clock gates, utilization {blk['utilization']:.1%}, DRC 0, timing met at every corner "
                       f"(setup ≥ {blk['setup_wns_min_ns']} ns, hold ≥ {blk['hold_wns_min_ns'] * 1000:.0f} ps). The first routing left one net 5 % over the antenna limit "
                       "in Magic; a final repair pass at a 15 % margin removed it, and every check after routing was run again: "
                       f"antenna {ac['magic']['violations']} in Magic, {ac['openroad']['net_violations']} in OpenROAD; LVS match; DRC {so['drc_markers']}."))
after_h2("cf", now(f"On the revision 4.7 GDS (md5 <code>{pc['gds_md5']}</code>) the precheck in ChipFoundry's pinned versions passes {B.pre} "
                   "(PC batch 28c, 7 November). The description below is the October work that set up these versions."))
after_h2("chip", now("The chip is unchanged outside the logic block. Its digital block now holds revision 4.7's logic (section 10)."))

# ---------------------------------------------------------------- logic section: registers, steps, checks, timing for 4.7
s = re.sub(r'(<tr><td class="num">\+4, \+8, \+12</td>)',
           r'<tr><td class="num">+3</td><td>SEC</td><td>read/write</td><td>(4.6) t0 ZSKIP, t1 VARPROG, t2 NOSHUF: opt-ins to the old behaviour; t3 LOCK: set-only, cleared by reset; under LOCK the opt-ins are off, read-back is refused and PITER, ACT read 0</td></tr>\1', s, count=1)
sub("<td>+ : program the row from PDATA with verify; − : read the row into PDATA</td>",
    "<td>+ : program the row from PDATA (21 + 21 steps); − : read the row into PDATA (refused under LOCK); 0,+ : margin check (4.6)</td>")
s = re.sub(r"(<td>pulses the last program command used</td></tr>)",
           r"\1<tr><td class=\"num\">+50</td><td>ACT</td><td>read</td><td>(4.6) parity of the dummy accumulators; 0 under LOCK</td></tr>"
           r"<tr><td class=\"num\">+52</td><td>MARG</td><td>read (word)</td><td>(4.6) + for each column with a device in the margin band at the last margin check</td></tr>", s, count=1)
sub("then runs pulse-and-verify (section 5)\nin two phases, reset first and set second, pulsing only the devices that still fail their verify, at amplitude steps 0 to 20. If a device\nhas not passed after the last step, WERR is set. PITER reports how many pulses the row took.",
    "then runs pulse-and-verify (section 5)\nin two phases, reset first and set second, pulsing only the devices that still fail their verify, at amplitude steps 0 to 20; since 4.6 every\nstep is run, with an empty pulse once all devices have verified, so every command takes the same time. If a device has not passed after the last\nstep, WERR is set. PITER reports how many real pulses the row took.")
m = re.search(r'(<h3>How the logic was checked</h3>)(.*?)(<p><b>Why fault injection)', s, re.S)
s = s[:m.start(2)] + f"""
<div class="kv"><div class="num">{c_rtl[0]:,}</div><div>self-checking tests per run, 0 failures, CXXRTL and Verilator, both trit codes (revision 4.7)</div>
<div class="num">{mt["detected"]} / {mt["faults"]}</div><div>injected faults detected ({mp["detected"]} / {mp["faults"]} in the BSD-PNX build)</div>
<div class="num">7 / 7</div><div>formal proofs, including the start-row proof and the two-copy timing miter; {sum(x["caught"] for x in ff)} of {len(ff)} planted faults make a proof fail</div>
<div class="num">{gls[0]:,}</div><div>checks on the routed netlist (gate level), 0 failures</div></div>
""" + s[m.start(3):]
s = re.sub(r"<b>The logic block on the chip</b> is placed and routed with OpenROAD-flow-scripts on sky130B: .*?utilization\.",
           f"<b>The logic block on the chip</b> is placed and routed with OpenROAD-flow-scripts on sky130B: {blk['stdcells']:,} cells including antenna diodes "
           f"({blk['sequential']:,} flip-flops, {blk['clock_gates']} clock gates), {blk['utilization']:.1%} utilization (revision 4.7; 4.5 had 9,638 logic cells).", s, count=1, flags=re.S)


s = s.replace("input 0: row not read, costs no cycle", "input 0: read anyway (since 4.6), adds 0")
s = s.replace("only rows with input ≠ 0 are read: about 49.7 core clock cycles per product on random inputs, if the array answered at once;",
              "revision 4.5 read only rows with input ≠ 0; since 4.6 all 72 rows are read, from a start row the LFSR picks;")
s = s.replace("product sequencer: rows with input ≠ 0", "product sequencer: all 72 rows (4.6+)")
after_h2("logic", now("Every product reads all 72 rows from a random start row (LFSR mod 72) and starts its accumulators at a random offset, so "
                      "its duration and switching do not follow the inputs; programming takes a constant 21 + 21 steps; the SEC register adds a "
                      "set-only LOCK. The tables, checks and timing below are revision 4.7's; the worked example keeps 4.5's rule for clarity of the sums."))


def timing_chart():
    cs = sorted(blk["corners"].items(), key=lambda kv: kv[1]["setup_wns_ns"])
    W, x0, x1 = 760, 210, 720
    H = 40 + 26 * len(cs) + 30
    sx = lambda v: x0 + v / 25.0 * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Setup slack of the revision 4.7 logic block at a 25 ns clock in nine cases, all positive; '
         f'worst {cs[0][1]["setup_wns_ns"]} ns.">']
    for v in (0, 5, 10, 15, 20, 25):
        o.append(f'<line x1="{sx(v):.1f}" y1="24" x2="{sx(v):.1f}" y2="{H - 30}" stroke="var(--grid)"/><text x="{sx(v):.1f}" y="{H - 14}" text-anchor="middle" class="tick">{v}</text>')
    for k, (name, v) in enumerate(cs):
        y = 32 + 26 * k
        o.append(f'<text x="{x0 - 8}" y="{y + 13}" text-anchor="end" class="sm">{esc(name.replace("_", " "))}</text>'
                 f'<rect x="{x0}" y="{y}" width="{sx(v["setup_wns_ns"]) - x0:.1f}" height="18" rx="3" fill="var(--s1)" '
                 f'data-tip="{esc(name)}: setup {v["setup_wns_ns"]} ns, hold {v["hold_wns_ns"]} ns"/>'
                 f'<text x="{sx(v["setup_wns_ns"]) + 6:.1f}" y="{y + 13}" class="sm">{v["setup_wns_ns"]} ns</text>')
    o.append(f'<text x="{(x0 + x1) / 2}" y="{H - 1}" text-anchor="middle" class="axl">setup slack, ns (25 ns clock); k = wire parasitics scale</text></svg>')
    hold = min(v["hold_wns_ns"] for _, v in cs)
    return (f'<figure>{"".join(o)}<figcaption>Time to spare at a 25 ns clock (40 MHz), revision 4.7 block, nine cases: three corners × wire '
            f'parasitics 0.8 / 1.0 / 1.2. All positive; hold slack ≥ +{hold * 1000:.0f} ps. The shortest working period at the slow corner is '
            f'{mp_[1.0]} ns ({mp_[1.2]} ns with parasitics × 1.2).</figcaption></figure>')


m = re.search(r"<figure>(?:(?!<figure>).)*?Time to spare at a 25 ns clock.*?</figure>", s, re.S)
s = s[:m.start()] + timing_chart() + s[m.end():]

# ---------------------------------------------------------------- security: replace "What this does not fix" with triage + cells
a = s.index('<section id="security"'); h = s.index("<h3>What this does not fix</h3>", a); e = s.index("</section>", h)
cells_sec = B.summary_page()
cells_html = cells_sec[cells_sec.index('<section id="cells">'):cells_sec.index("</section>", cells_sec.index('<section id="cells">'))]
cells_html = cells_html.replace("<h2>Cell options: 2T2R, one-of-three, 4T4R</h2>", "<h2>13c · Cell options: 2T2R, one-of-three, 4T4R</h2>")
s = s[:h] + f"""</section>

<section id="open">
<h2>13b · Open issues of revision 4.7: which stand</h2>
<p>Each issue raised by the security study and its two reviews, checked against the files. {ntri["closed"]} closed; {ntri["stands"] + ntri["next"]} remain open on this chip
({ntri["stands"]} stated limits, {ntri["next"]} fixed only by the next chip); {ntri["external"]} wait on others. Also in <code>studies/page-trim-2026-11-08/TRIAGE.md</code>.</p>
{B.triage_html()[1]}
</section>

{cells_html}
""" + s[e:]

# ---------------------------------------------------------------- 14 TTPU-Gen2, 15 next, corrections
a, b = cut("ttpu", "nov")
ttpu = f"""<section id="ttpu">
<h2>14 · TRITONE TPU: the TTPU-Gen2 fixes (7 November 2026)</h2>
<p>TRITONE is the digital ternary TPU SoC of the earlier project (<code>ofFBeaT9/Tritone-TPU-SoC</code>, top level <code>tpu_top_v2</code>): a systolic
array of ternary multiply-accumulate cells behind a 32-bit register interface. It was checked against the same attacks as TCIM0. Its matrix
multiply takes the same time whatever the weights (a zero weight adds zero), so it has no timing leak like TCIM0's old zero-skipping. It had two
other problems. Both are fixed as TPU v2.4 ("TTPU-Gen2") in <a href="https://github.com/ofFBeaT9/Tritone-TPU-SoC/pull/2">pull request #2</a>.</p>
<figure><svg viewBox="0 0 760 170" role="img" aria-label="TTPU-Gen2: the zero-weight counters feed STATUS bits 31 to 16 and PERF_CNT_1 only when SEC bit 0 is set and LOCK, SEC bit 31, is clear.">
<rect x="20" y="50" width="170" height="60" rx="6" fill="var(--surface)" stroke="currentColor"/><text x="105" y="76" text-anchor="middle" class="sm">systolic array</text><text x="105" y="94" text-anchor="middle" class="sm">zero-weight count</text>
<rect x="270" y="40" width="190" height="80" rx="6" fill="var(--wash)" stroke="var(--s1)"/><text x="365" y="66" text-anchor="middle" class="sm">gate: SEC[0] and not LOCK</text><text x="365" y="86" text-anchor="middle" class="sm">SEC at 0x70</text><text x="365" y="104" text-anchor="middle" class="sm">LOCK = SEC[31], set-only</text>
<rect x="540" y="30" width="200" height="40" rx="6" fill="var(--surface)" stroke="currentColor"/><text x="640" y="55" text-anchor="middle" class="sm">STATUS[31:16]</text>
<rect x="540" y="90" width="200" height="40" rx="6" fill="var(--surface)" stroke="currentColor"/><text x="640" y="115" text-anchor="middle" class="sm">PERF_CNT_1</text>
<line x1="190" y1="80" x2="266" y2="80" stroke="currentColor" marker-end="url(#ttarr)"/><line x1="460" y1="70" x2="536" y2="50" stroke="currentColor" marker-end="url(#ttarr)"/><line x1="460" y1="90" x2="536" y2="110" stroke="currentColor" marker-end="url(#ttarr)"/>
<text x="228" y="72" text-anchor="middle" class="sm">per cycle</text><text x="500" y="150" text-anchor="middle" class="sm">read 0 unless opted in</text>
<defs><marker id="ttarr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L8,4L0,8z" fill="currentColor"/></marker></defs>
</svg><figcaption>The sparsity counters after the fix: they count, and can be read, only after software opts in through SEC; LOCK switches them off until reset.</figcaption></figure>
<div class="tbl"><table><thead><tr><th>Problem</th><th>Why it matters</th><th>Fix in v2.4</th></tr></thead><tbody>
<tr><td>STATUS[31:16] and PERF_CNT_1 counted the zero weights, readable by any software</td><td>The count of zeros is the weights' sparsity: the same leak as TCIM0's 2T2R read current, but through a register</td><td>New SEC register (0x70): counts kept at 0 and not accumulated unless SEC[0] opts in; SEC[31] LOCK is set-only, clears the opt-in, and only reset clears it</td></tr>
<tr><td>STATUS.DONE and DMA_STATUS.DONE were one-cycle pulses</td><td>Polling software could miss DONE and wait forever; two of the repository's own test benches timed out for this reason</td><td>Both DONE bits stay set until the next start</td></tr>
<tr><td>Version register</td><td>Software can tell which TPU it runs on</td><td>v2.4 (0x40 / 0x41); three benches' version checks updated</td></tr>
</tbody></table></div>
<p><b>Verified on Verilator</b> (<code>scripts/run_gen2_tests.sh</code>; logs in <code>results/ttpu_gen2/</code>): {B.tpu}.
<b>Not yet:</b> no TPU test compares matrix results with a reference (the full-system simulation, or a new bench, will); the power of a MAC still
depends on the data (adding zero toggles less), which these fixes do not change; the pull request is open, not merged.</p>
</section>

<section id="next">
<h2>15 · Next: REBEL-6 + TCIM0 + TPU in one simulation, and what to ask USN</h2>
<p>The three parts exist separately: REBEL-6 (USN's ternary CPU), TCIM0 (this chip) and the TRITONE TPU. Nothing connects them yet: no shared-bus design,
no simulation of the three together, no software on REBEL-6 that drives TCIM0. That simulation is the next step. The public ternary-workbench
repository has REBEL-6's specification, assembler and a debugger that talks to an external target, but no RTL and no emulator.</p>
<figure><svg viewBox="0 0 760 190" role="img" aria-label="Planned system: REBEL-6 on a ternary memory bus, TCIM0 in slot 11 with interrupt 7, and the TPU behind a bridge from 24-trit words to its 32-bit AXI bus.">
<rect x="20" y="70" width="150" height="60" rx="6" fill="var(--surface)" stroke="currentColor"/><text x="95" y="96" text-anchor="middle" class="sm">REBEL-6 CPU</text><text x="95" y="114" text-anchor="middle" class="sm">24-trit words</text>
<line x1="170" y1="100" x2="300" y2="100" stroke="currentColor" stroke-width="3"/><text x="235" y="90" text-anchor="middle" class="sm">MMIO bus</text>
<rect x="300" y="20" width="190" height="60" rx="6" fill="var(--wash)" stroke="var(--s1)"/><text x="395" y="46" text-anchor="middle" class="sm">TCIM0 (this chip)</text><text x="395" y="64" text-anchor="middle" class="sm">slot 11, IRQ 7 (proposed)</text>
<rect x="300" y="120" width="190" height="60" rx="6" fill="var(--surface)" stroke="currentColor" stroke-dasharray="5 3"/><text x="395" y="146" text-anchor="middle" class="sm">bridge (to design)</text><text x="395" y="164" text-anchor="middle" class="sm">24 trits ↔ 32-bit AXI</text>
<rect x="570" y="120" width="170" height="60" rx="6" fill="var(--surface)" stroke="currentColor"/><text x="655" y="146" text-anchor="middle" class="sm">TRITONE TPU v2.4</text><text x="655" y="164" text-anchor="middle" class="sm">systolic array</text>
<line x1="300" y1="100" x2="300" y2="50" stroke="currentColor"/><line x1="300" y1="100" x2="300" y2="150" stroke="currentColor"/><line x1="490" y1="150" x2="570" y2="150" stroke="currentColor"/>
</svg><figcaption>The planned system. Dashed: not designed yet. On the test chip TCIM0 is reached through its serial port instead of the bus.</figcaption></figure>
<div class="board">
<div class="col"><h3><span class="tag t-you">ask Steven Bos (USN)</span></h3><ul>
<li>REBEL-6 RTL or netlist (or a cycle-accurate simulator).</li><li>How a peripheral attaches: bus timing and handshake of the MMIO region, the external interrupt input.</li>
<li>Slot 11 and interrupt 7 for TCIM0, a slot for the TPU; the trit wire code on that bus (TCIM0 builds with BSD-PNX or two's complement).</li>
<li>Access to the board with TMAC.T and to USN's test bench.</li></ul></div>
<div class="col"><h3><span class="tag t-ok">what you can share</span></h3><ul>
<li>This page (share it from claude.ai) and <code>docs/STATUS.md</code>.</li><li>TCIM0's register map and serial protocol (section 8).</li>
<li>The verification and sign-off numbers above, with "What can be claimed".</li><li>Not the Gemini summaries: they mark unbuilt things as verified.</li></ul></div>
<div class="col"><h3><span class="tag t-warn">needed for the system simulation</span></h3><ul>
<li>REBEL-6 RTL, or an instruction-set model written from the published specification (can start now).</li>
<li>The bridge between 24-trit words and the TPU's 32-bit AXI bus.</li>
<li>A REBEL-6 program that programs TCIM0's weights, runs products and checks them, and a TPU job checked against a reference.</li></ul></div>
</div>
</section>

<section id="nov8">
<h2>Corrections made on 8 November</h2>
<ul>
<li>The opening sections described revision 4.5 next to 4.7 numbers; they now give the current state, and each section that changed after 4.5 has a "Now" box.</li>
<li>The logic section listed 4.5's registers, checks and timing; it now has SEC, ACT, MARG, constant-time programming and the 4.7 numbers.</li>
<li>The GDS md5 of the files table was the 4.5 one; it is now read from the precheck result.</li>
<li>Revision 4.8 was missing. 4T4R was never adopted; section 13c compares it.</li>
<li>"LOCK protects the weights from the bus" was too strong: read-back is refused, but products still run, so 72 products with one-hot inputs recover every weight (section 13b).</li>
</ul>
</section>

"""
s = s[:a] + ttpu + s[b:]
s = s.replace('class=\\"num\\"', 'class="num"')
out = Path(sys.argv[1]); out.write_text(s)
print(f"{len(s):,} bytes")
