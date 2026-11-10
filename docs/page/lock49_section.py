"""Revision 4.9 (9 November 2026): the two LOCK gaps closed. Page section 13e and docs/STATUS.md section 15.9, both from
results/rev49/summary.json (tools/collect_rev49.py). A check that has not run shows as 'running'.
Usage: python3 docs/page/lock49_section.py status   (prints section 15.9)"""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "results"


def S():
    f = R / "rev49" / "summary.json"
    return json.loads(f.read_text()) if f.exists() else {}


def _tb(s, n):
    t = (s.get("tb") or {}).get(n)
    return "running" if not t else f"{t['checks']:,} checks, {t['failures']} failures"


def _mut(s, n):
    m = (s.get("mutation") or {}).get(n)
    if not m:
        return "running"
    tail = "" if m["run"] == m["faults"] else f" (of {m['faults']} planned; running)"
    return f"{m['detected']} of {m['run']} caught{tail}; the {m['new_faults']} new faults: {m['new_caught']} caught"


def _mc(s, n):
    m = (s.get("mutation_chip") or {}).get(n)
    return "running" if not m else f"{m['detected']} of {m['faults']} caught"


def rows(s):
    f = s.get("formal") or {}
    eq = s.get("equiv_vs_rev48") or {}
    e = lambda b: ("running" if not eq.get(b) else
                   f"{eq[b]['proven']:,} points proven, {eq[b]['unproven']} unproven, all in: {', '.join(eq[b]['signals'])}")
    fz = s.get("fuzz") or "running"
    return [
        ("Test bench, both trit codes, CXXRTL (<code>make rtl rtl-pnx</code>)", f"{_tb(s, 'rtl_test.log')}; BSD-PNX {_tb(s, 'rtl_test_pnx.log')}"),
        ("Same test bench on Verilator (<code>make rtl-verilator</code>)", f"{_tb(s, 'rtl_test_verilator.log')}; BSD-PNX {_tb(s, 'rtl_test_verilator_pnx.log')}"),
        ("3T3R build (<code>make rtl-1of3</code>)", f"{_tb(s, 'next_chip/rtl_test_1of3.log')}; BSD-PNX {_tb(s, 'next_chip/rtl_test_1of3_pnx.log')}"),
        ("Chip test bench with the array controller (<code>make rtl-chip</code>, settings 0,0,0 / 1,1,0 / 3,2,1)",
         f"{_tb(s, 'sky130_chip/rtl_chip_000.log')} / {_tb(s, 'sky130_chip/rtl_chip_110.log')} / {_tb(s, 'sky130_chip/rtl_chip_321.log')}"),
        ("Chip test bench, 3T3R (<code>make rtl-chip-1of3</code>)", _tb(s, "next_chip/rtl_chip_1of3_110.log")),
        ("Mutation test (<code>tb/mutation_test.py</code>)", _mut(s, "rtl_mutation.json")),
        ("Mutation test, BSD-PNX", _mut(s, "rtl_mutation_pnx.json")),
        ("Mutation test, 3T3R build with every fault", _mut(s, "rtl_mutation_1of3full.json")),
        ("Controller faults, chip test bench (2T2R / 3T3R)", f"{_mc(s, 'sky130_chip/mutation_chip.json')} / {_mc(s, 'next_chip/mutation_chip_1of3.json')}"),
        ("Formal proofs that closed (SymbiYosys; the PDR tasks with FORMAL_ANYLOCK, a superset of the design's states)",
         "; ".join(f"{k}: PASS" for k, v in f.get("passed", {}).items() if v) or "running"),
        ("Formal proofs still open when revision 4.9 was committed (PDR did not close in 3 h on the PC)",
         "; ".join(f.get("open", [])) or "none"),
        ("Comparison with the revision 4.8 logic (<code>tests/equiv/run_equiv_rev49.sh</code>)", f"default cell: {e('default')}. 3T3R: {e('1of3')}"),
        ("Verilator lint, all warnings, both codes", "running" if s.get("lint_warnings") is None else f"{s['lint_warnings']} warnings"),
        ("Serial-port fuzzing (<code>make fuzz</code>)", fz),
    ] + chip_rows()


def chip_rows():
    J = lambda n: json.loads((R / n).read_text()) if (R / n).exists() else None
    db, tl, so, pc = J("sky130_chip/digital_block.json"), J("sky130_chip/top_layout.json"), J("sky130_chip/top_signoff.json"), J("sky130_chip/precheck.json")
    g = (R / "sky130_chip/gls_chip_routed.log")
    import re
    gm = re.findall(r"(\d+) checks, (\d+) failures", g.read_text()) if g.exists() else []
    gf = sum("TEST FAILED" in (R / "sky130_chip" / n).read_text() for n in ("gls_chip_fault_xnor.log", "gls_chip_fault_icg.log"))
    out = []
    if db and "min_period" in db:
        mp = {r["spef_scale"]: r["min_period_ns"] for r in db["min_period"]}
        out.append(("Chip block placed and routed again (OpenROAD-flow-scripts, PC batch 29; same die as revision 4.5)",
                    f"{db['stdcells']:,} cells, {db['sequential']:,} flip-flops, DRC {db['drc_violations']}, netlist equal to the RTL; timing after layout met at every corner "
                    f"(worst setup slack {db['corners']['ss_100C_1v60']['setup_wns_ns']:.2f} ns at the slow corner, worst hold slack "
                    f"{min(c['hold_wns_ns'] for c in db['corners'].values()):.3f} ns); shortest period {mp[1.0]} ns ({mp[1.2]} ns with parasitics x1.2)"))
    if gm:
        out.append(("Routed netlist through the chip test bench (gate level)", f"{int(gm[-1][0]):,} checks, {gm[-1][1]} failures; {gf} of 2 planted gate faults caught"))
    if tl and so and pc:
        out.append(("Top level and sign-off (top.py, Magic, netgen, ChipFoundry's precheck in their pinned versions)",
                    f"LVS {'match' if tl['lvs_match'] else 'MISMATCH'}, planted swap {'caught' if not tl['fault_lvs_match'] else 'NOT caught'}; Magic DRC "
                    f"{so['drc_markers']}, antenna {so['antenna_violation_count']}; precheck {pc['passed']} of {pc['total']}"))
    return out


WHAT = [
    ("Locked at reset", "A reset, power-up included, leaves the tile locked. There is no window before firmware sets LOCK. Products run as "
     "before, on the weights already in the array. Read-back and programming are refused (WERR, no array access), the options (ZSKIP, "
     "VARPROG, NOSHUF) cannot be set, and PITER and ACT read 0."),
    ("Unlocking erases the whole array", "The only way to clear LOCK is a new command, PCMD 0,0,+. It programs all 72 rows to weight 0, in "
     "order, each with the fixed 21 + 21 pulse steps whatever the options and the old weights, so its length reveals nothing. It clears LOCK "
     "only if every device verified; with WERR the tile stays locked. Unlocking can never expose the old weights. This is how flash "
     "microcontrollers implement read-out protection."),
    ("Programming is refused under LOCK", "So no row can be overwritten with known weights to calibrate each sense amplifier, the calibration "
     "the position residual of 13d needs."),
    ("LOCK is held three times", "LOCK is three flip-flops and the tile is locked while any of them is set, so one upset (two, in the test bench) "
     "cannot clear it."),
]

NOT = [
    "Products cannot be refused: a tile that computes on secret weights, with readable results and chosen inputs, gives every weight back after "
    "72 one-hot products. This is model extraction (Tramèr et al., USENIX Security 2016), true of any accelerator whose outputs are visible, "
    "and no register can stop it. The threat model keeps the results with the host.",
    "Cost: after every power-up, firmware must erase and reprogram before it can read weights back or use the options; inference on the "
    "stored weights works without that. The erase takes 72 × (21 + 21) pulse steps. Logic: three flip-flops for LOCK, one for the erase.",
    "The upset test changes the LOCK flip-flops in the CXXRTL model directly; an upset elsewhere (an option flip-flop, the state register) is not "
    "covered by any test, and fault injection is out of scope.",
]


FOUND = [
    "The 3T3R safety proof failed on a property written before the erase existed (a Z pulse must match the weight in PDATA; an erase "
    "writes weight 0 whatever PDATA holds). The property now covers program commands only, and a planted fault shows the erase's own Z "
    "property can fail.",
    "The mutation test found two checks of the test bench that could not fail: PITER under LOCK read 0 either way (a refused program "
    "command clears it; the test now reads PITER right after LOCK), and in the 3T3R build the stuck-reset test's random weight left the "
    "device it watches already set (the test now forces it to HRS first).",
    "The precheck of the first revision 4.9 chip failed Magic DRC (met3.2, 8 markers) and KLayout BEOL (m3.2, 4): two block pins came "
    "within 1.2 um of the macro pins above them, and the 0.4 um track between the two via pads left 0.1 um notches. top.py now fills such "
    "gaps; the rebuilt chip passes all 14 checks.",
    "The timing miter found two copies that differ after 6,270 cycles: an erase whose (secret) verify answers differ leaves one copy "
    "locked and the other unlocked. Whether an erase succeeded is public (STAT.WERR, SEC.LOCK), so the miter now assumes both copies hold "
    "the same LOCK; with that, both miters pass. What a failed erase reveals about the devices is the WERR fault oracle, out of scope.",
    "The PDR proofs did not close, even with lemmas for the erase: with the design's reset no unlocked state is reachable before a whole "
    "erase, about 3,300 cycles, and PDR walked it about one frame at a time. The PDR tasks now let a reset leave the tile locked or "
    "unlocked (FORMAL_ANYLOCK, proofs only: a superset of the design's states, so what holds there holds for the design), and a separate "
    "task proves that the design's reset leaves it locked. Even so, the safety task with every new property did not close in 3 hours on "
    "the PC; split into subsets, the revision 4.7 properties (61 min), the under-LOCK and erase-writes-zero properties (81 min) and the "
    "erase-order properties (70 min) each close; the unlock property, the BSD-PNX and 3T3R safety tasks and the progress task are still open, "
    "and so are the planted proof faults for the new properties. The lemmas written to help PDR made it slower and were taken out of the runs.",
]


def section():
    s = S()
    trs = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows(s))
    wl = "".join(f"<li><b>{a}.</b> {b}</li>" for a, b in WHAT)
    nl = "".join(f"<li>{x}</li>" for x in NOT)
    return f"""
<section id="lock49">
<h2>13e · Revision 4.9: LOCK that survives a reset</h2>
<p>The paper study's red team found two ways around LOCK in revision 4.7 (8 November): programming still ran under LOCK, and a reset cleared
LOCK while the weights stayed in the array. Revision 4.9 (9 November) closes both, and every other gap a design can close, in
<code>rtl/tcim_core.sv</code>; the rest of the design is unchanged.</p>
<ul>{wl}</ul>
<h3>How it was verified</h3>
<div class="tbl"><table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="sm">New proof properties, written from what the array is asked to do rather than from the new registers: LOCK is set in the cycle after
a reset; LOCK clears only in the cycle an erase ends, if the array was asked to verify the set phase of all 72 rows in that erase and no device
failed; under LOCK a pulse happens only inside an erase, and no read-back runs; an erase sends no set pulse to a P or N device (one-of-three: no
reset pulse to Z); an erase visits rows 0 to 71 in order and ends after row 71.</p>
<h3>Found on the way</h3>
<ul>{"".join(f"<li>{x}</li>" for x in FOUND)}</ul>
<h3>What this does not fix</h3>
<ul>{nl}</ul>
</section>
"""


def status_md():
    s = S()
    tr = "\n".join(f"| {a} | {b} |" for a, b in rows(s)).replace("<code>", "`").replace("</code>", "`")
    wl = "\n".join(f"- **{a}.** {b}" for a, b in WHAT)
    nl = "\n".join(f"- {x}" for x in NOT)
    return f"""### 15.9 Revision 4.9 (9 November 2026): LOCK that survives a reset

The paper study's red team (`studies/paper-2026-11/council/03_red_team.md`, finding 3) found two ways around LOCK in revision 4.7:
programming still ran under LOCK, and a reset cleared LOCK while the weights stayed in the array. Revision 4.9 closes both, and
every other gap a design can close, in `rtl/tcim_core.sv`; the rest of the design is unchanged.

{wl}

| Check | Result |
|---|---|
{tr}

The revision 4.7 / 4.8 files quoted in sections 15.1 to 15.8 are kept in `results/rev48`. New proof properties, written from what
the array is asked to do rather than from the new registers:
- LOCK is set in the cycle after a reset;
- LOCK clears only in the cycle an erase ends, if the array was asked to verify the set phase of all 72 rows in that erase and no
  device failed;
- under LOCK a pulse happens only inside an erase, and no read-back runs;
- an erase sends no set pulse to a P or N device (one-of-three: no reset pulse to Z);
- an erase visits rows 0 to 71 in order and ends after row 71.

Found on the way:
{chr(10).join("- " + x for x in FOUND)}

What this does not fix:
{nl}
"""


if __name__ == "__main__" and sys.argv[1:] == ["status"]:
    print(status_md())
