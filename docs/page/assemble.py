"""Builds docs/TCIM0_explainer.html for revision 4.7 (6 November 2026) from the revision 4.5 page of 14 October
(docs/page/base_rev45.html, the page as published then) and results/: a new opening section, section 13 (security,
docs/page/security_section.py), a corrections section, and two corrected sentences. Every number comes from results/.
Usage (repository root): python3 docs/page/assemble.py <out.html>"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

R = Path("results")
base = Path("docs/page/base_rev45.html").read_text()


def J(p):
    f = R / p
    return json.loads(f.read_text()) if f.exists() else None


def T(p):
    f = R / p
    return f.read_text(errors="ignore") if f.exists() else ""


def checks(txt):
    m = re.findall(r"(\d+) checks, (\d+) failures", txt)
    return (int(m[-1][0]), int(m[-1][1])) if m and "TEST PASSED" in txt else None


def sub1(s, old, new):
    assert s.count(old) == 1, old[:80]
    return s.replace(old, new)


gds = Path("chip/sky130/caravan/gds/user_analog_project_wrapper.gds")
gds_md5 = hashlib.md5(gds.read_bytes()).hexdigest() if gds.exists() else None
pc, so, tl, blk = J("sky130_chip/precheck.json"), J("sky130_chip/top_signoff.json"), J("sky130_chip/top_layout.json"), J("sky130_chip/digital_block.json")
mt, mp, ff = J("rtl_mutation.json"), J("rtl_mutation_pnx.json"), J("formal_faults.json")
fl = T("formal.log")
proofs_ok = all(f"[{t}] DONE (PASS" in fl for t in ("tcim_spi", "tcim_core_safety", "tcim_core_safety_pnx", "tcim_core_progress")) and \
    all("DONE (PASS" in T(f"security/miter_{t}.log") for t in ("prove", "prove_pnx"))
c1, c2 = checks(T("rtl_test.log")), checks(T("rtl_test_pnx.log"))
pre_ok = bool(pc and pc.get("gds_md5") == gds_md5 and pc["passed"] == pc["total"])
pre_txt = (f'ChipFoundry\'s precheck in their pinned versions on the revision 4.7 GDS: <b>{pc["passed"]} of {pc["total"]}</b>' if pc and pc.get("gds_md5") == gds_md5
           else "ChipFoundry's precheck has <b>not yet been run</b> on the revision 4.7 GDS")

ready = f"""<section id="ready">
<h2>Is it ready for fabrication?</h2>
<div class="verdict"><b>Revision 4.7 (6–7 November 2026).</b> The logic block was changed for hardware security (section 13), placed and routed again in the
same footprint, and the whole user area rebuilt. {pre_txt}. {"The design is complete on its side;" if pre_ok else "Until that passes, the design is not complete;"}
it still cannot be ordered: ChipFoundry has not confirmed that any shuttle accepts the ReRAM layer. Say "design complete, passes the foundry's
precheck, waiting for the foundry's confirmation of ReRAM", not "ready to fabricate".</div>
<p class="note">Sections 1–12 below describe revision 4.5 (12 October) and keep its numbers; the logic block of revision 4.7 differs only in what section 13
lists, and section 13 gives its verification and sign-off numbers.</p>
<div class="board">
<div class="col"><h3><span class="tag t-ok">done on the design side</span></h3><ul>
<li>Logic of revision 4.7: {f"{c1[0]:,} self-checking tests in each trit code, 0 failures" if c1 and c2 and c1[1] == c2[1] == 0 else "test bench not run"}, two simulators;
{f'{mt["detected"]} of {mt["faults"]} and {mp["detected"]} of {mp["faults"]} injected faults detected' if mt and mp else "mutation test not run"};
{"every formal proof passes, including the two-copy timing miter" if proofs_ok else "formal proofs not all passed"}{f', {sum(x["caught"] for x in ff)} of {len(ff)} planted proof faults caught' if ff else ""}.</li>
<li>Logic block placed and routed again: {f'{blk["stdcells"]:,} cells, utilization {blk["utilization"]:.1%}, DRC 0, timing met at every corner (setup ≥ {blk["setup_wns_min_ns"]} ns at a 25 ns clock)' if blk else "not run"}.</li>
<li>Whole user area: {"LVS match" if tl and tl.get("lvs_match") else "LVS not run"}; Magic DRC full rules {so["drc_markers"] if so else "?"} markers; antenna {so["antenna_violation_count"] if so else "?"} violations.</li>
<li>{pre_txt}.</li>
<li>Leakage measured on TCIM0's model before and after each change (section 13).</li>
</ul></div>
<div class="col"><h3><span class="tag t-warn">ask ChipFoundry</span></h3><ul>
<li><b>Is ReRAM accepted on a shuttle, which one, at what price and dates?</b> Not published.</li>
<li><b>Is the chip processed as sky130B?</b> Only sky130B has the ReRAM layer; with sky130A their LVS does not recognise the 3,456 ReRAM devices.</li>
<li><b>Which ReRAM library do they sign off with?</b> Their pinned PDK (3e0e31d), enabled for sky130B with ciel's default libraries, includes
<code>sky130_fd_pr_reram</code> (commit d6d2a3c); this chip was drawn with open_pdks 1e35547.</li>
<li>The test structure behind SkyWater's published yields, which would narrow the device-spread uncertainty (section 12).</li>
</ul></div>
<div class="col"><h3><span class="tag t-you">needs you</span></h3><ul>
<li>Send the questions (drafted in <code>docs/QUESTIONS.md</code>).</li>
<li>Design the test board (programming rails, VREF, IBIAS, a controller on the serial port, a source-measure unit on the test-cell pads).</li>
<li>Decide whether deployed firmware sets LOCK, and keep the board's reset and serial port trusted (section 13).</li>
<li>Antistatic handling: the analog pads used have no ESD protection (section 6).</li>
</ul></div>
</div>
</section>"""

page = base
a = page.index('<section id="ready">'); b = page.index("</section>", a) + len("</section>")
page = page[:a] + ready + page[b:]
page = sub1(page, "<h2>Is everything verified? A fresh re-run of every automatic check, today</h2>",
            "<h2>Is everything verified? The re-run of 12 October (revision 4.5)</h2>\n<p class=\"note\">This table is the full regression of revision 4.5. "
            "The verification of revision 4.7 is in section 13.</p>")
sec = subprocess.run([sys.executable, "docs/page/security_section.py"], capture_output=True, text=True, check=True).stdout
corr = """<section id="nov">
<h2>Corrections made on 6 November</h2>
<ul>
<li><b>ChipFoundry's PDK and the ReRAM library.</b> This page said their pinned PDK (3e0e31d) has no <code>sky130_fd_pr_reram</code> folder. It has one when
sky130B is enabled with ciel's default libraries (commit d6d2a3c; <code>results/sky130_chip/cfpdk_3e0e31d_contents.txt</code>); batch 22 had enabled
the PDK with an option that left it out.</li>
<li><b>Leakage model.</b> The first model (4 November) drew the start row uniformly and counted accumulator updates. The review showed that the RTL's start
rows were not uniform and that bit flips, not update counts, carry the inputs. The second model fixes both; its results replace the first
(the first is kept in <code>results/security/tvla_model1_rev46.json</code>).</li>
<li><b>"One-of-three passes"</b> (4 November) held only with a uniform start row; it holds with revision 4.7's logic, not with 4.6's.</li>
</ul>
</section>
"""
ttpu = """<section id="ttpu">
<h2>14 · TRITONE TPU: the TTPU-Gen2 fixes (7 November 2026)</h2>
<p>The digital ternary TPU of the earlier TRITONE SoC (<code>ofFBeaT9/Tritone-TPU-SoC</code>, <code>tpu_top_v2</code>) was checked against the same
attacks. Its matrix multiply takes the same time whatever the weights (a zero weight adds zero), so it has no timing leak like TCIM0's old
zero-skipping. It had two other problems, fixed as TPU v2.4 ("TTPU-Gen2") in
<a href="https://github.com/ofFBeaT9/Tritone-TPU-SoC/pull/2">pull request #2</a>:</p>
<ul>
<li><b>Sparsity leak.</b> STATUS[31:16] and PERF_CNT_1 counted the zero weights, readable by any software. A new SEC register (0x70) hides them
unless bit 0 opts in; bit 31 is a set-only LOCK that clears the opt-in (only reset clears LOCK).</li>
<li><b>Done bits a CPU could miss.</b> STATUS.DONE and DMA_STATUS.DONE were one-cycle pulses, so polling software could wait forever. Two of the
repository's own test benches timed out for this reason. They now stay set until the next start.</li>
</ul>
<p>Verified on Verilator: a new test of the SEC register (11 checks; 7 of them fail on the old design) and the five TPU and SoC test benches,
all passing (2 of 5 passed before). <b>Not yet verified:</b> no TPU test compares matrix-multiply results with a reference; the
full-system simulation will. The power of a MAC still depends on the data (adding zero toggles less), which the fix does not change.</p>
</section>
<section id="next">
<h2>15 · Next: REBEL-6 + TCIM0 + TPU in one simulation, and what to ask USN</h2>
<p>The three parts exist separately: REBEL-6 (USN's ISA; your silicon), TCIM0 (this chip) and the TRITONE TPU. Nothing connects them yet:
no shared-bus design, no simulation of the three together, no software on REBEL-6 that drives TCIM0. That simulation is the next step, and
it needs REBEL-6 itself. The public <code>ternary-workbench</code> repository has the specification, the assembler and a debugger that
talks to an external target, but no RTL and no emulator.</p>
<div class="board">
<div class="col"><h3><span class="tag t-you">ask Steven Bos (USN)</span></h3><ul>
<li><b>REBEL-6 RTL or netlist</b> (or a cycle-accurate simulator), to simulate the real CPU with TCIM0 and the TPU.</li>
<li><b>How a peripheral attaches</b>: the MMIO bus timing and handshake of the <code>−</code> region, and the external interrupt input.</li>
<li><b>Slot 11 and interrupt source 7</b> for TCIM0 (and a slot for the TPU).</li>
<li><b>The trit wire code</b> on that bus (BSD-PNX or other); TCIM0 builds with either.</li>
<li>Access to the executor or board with TMAC.T, and to USN's test bench.</li>
</ul></div>
<div class="col"><h3><span class="tag t-ok">what you can share</span></h3><ul>
<li>This page (share it from claude.ai) and <code>docs/STATUS.md</code>.</li>
<li>TCIM0's register map (section 1.4 of STATUS) and its serial protocol.</li>
<li>The verification and sign-off numbers above; say "design complete, passes the foundry's precheck", not "ready to fabricate".</li>
<li>Not the Gemini summaries: they mark unbuilt things as verified.</li>
</ul></div>
<div class="col"><h3><span class="tag t-warn">needed for the system simulation</span></h3><ul>
<li>REBEL-6 RTL from USN or your project (otherwise an instruction-set model written from the published specification).</li>
<li>A bridge: the TPU's bus is 32-bit binary with AXI, REBEL-6's data words are 24 trits; TCIM0 talks through its serial port.</li>
<li>A test program on REBEL-6 that programs TCIM0's weights, runs products and checks them, and a TPU job checked against a reference.</li>
</ul></div>
</div>
</section>
"""
page = sub1(page, '<section id="today">', sec + ttpu + corr + '<section id="today">')
page = sub1(page, '<a href="#limits">12 Limits</a><a href="#today">Corrections today</a>',
            '<a href="#limits">12 Limits</a><a href="#security">13 Hardware security</a><a href="#ttpu">14 TPU Gen2</a><a href="#next">15 Next</a><a href="#nov">Corrections 6 Nov</a><a href="#today">Corrections 12 Oct</a>')
page = sub1(page, "<h2>Corrections made today (12 October)</h2>", "<h2>Corrections made on 12 October</h2>")
if not page.lstrip().lower().startswith("<!doctype"):
    page = '<!DOCTYPE html>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' + page
Path(sys.argv[1]).write_text(page)
print("written", sys.argv[1], len(page), "bytes; precheck on this GDS:", pre_ok, "; proofs:", proofs_ok)
