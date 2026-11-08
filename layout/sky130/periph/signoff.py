"""Full-chip checks of the Caravan user area with Magic (12 October 2026): writes results/sky130_chip/top_signoff.json.

1. DRC with the full rule set, the same commands as ChipFoundry's precheck (cf-precheck 1.3.7,
   drc_scripts/magic_drc_check.tcl): gds read, load the top cell, `drc euclidean on`, `drc style drc(full)`, `drc check`,
   `drc listall why`. Run on the GDS of 11 October (before the met2 stub fix) it reproduces the precheck's three met2.2
   markers at (859.18, 1444.30); see STATUS.md section 9.7.
2. Antenna check with Magic's sky130B rules (partial model; metal sidewall ratio 400, plus 2200 per um2 of diode).
   The OpenROAD check of the digital block (reports/.../drt_antennas.log) uses the LEF rules and reports 0.
usage: python3 signoff.py [gds [output.json]]   (PDK_ROOT must point to the open_pdks installation with sky130B)"""
import hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GDS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "chip" / "sky130" / "caravan" / "gds" / "user_analog_project_wrapper.gds"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "results" / "sky130_chip" / "top_signoff.json"
TOP = "user_analog_project_wrapper"
RC = Path(os.environ["PDK_ROOT"]) / "sky130B" / "libs.tech" / "magic" / "sky130B.magicrc"

DRC_TCL = """gds read {gds}
load {top}
select top cell
expand
drc euclidean on
drc style drc(full)
drc check
set oscale [cif scale out]
set f [open {rep} w]
foreach {{why boxes}} [drc listall why] {{
  foreach b $boxes {{
    puts $f [format "%s|%.3f %.3f %.3f %.3f" $why [expr {{$oscale*[lindex $b 0]}}] [expr {{$oscale*[lindex $b 1]}}] \\
      [expr {{$oscale*[lindex $b 2]}}] [expr {{$oscale*[lindex $b 3]}}]]
  }}
}}
close $f
quit -noprompt
"""

ANT_TCL = """gds readonly true
gds read {gds}
load {top}
select top cell
extract no capacitance
extract no coupling
extract no resistance
extract no length
extract do local
extract all
antennacheck debug
antennacheck
puts "ANTENNA_ERRORS [feedback count]"
quit -noprompt
"""


def magic(tcl, wd):
    (wd / "run.tcl").write_text(tcl)
    env = dict(os.environ, MAGTYPE="mag")
    p = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(RC), "run.tcl"], cwd=wd, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True)
    return p.stdout + p.stderr


if __name__ == "__main__":
    res = dict(gds=str(GDS.relative_to(ROOT)) if GDS.is_relative_to(ROOT) else str(GDS),
               gds_md5=hashlib.md5(GDS.read_bytes()).hexdigest())
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        log = magic(DRC_TCL.format(gds=GDS, top=TOP, rep=wd / "drc.txt"), wd)
        rows = [l.split("|") for l in (wd / "drc.txt").read_text().splitlines() if l.strip()]
        res["drc_rules"] = "Magic drc(full), sky130B, commands of cf-precheck magic_drc_check.tcl"
        res["drc_markers"] = len(rows)
        res["drc_by_rule"] = {w: sum(1 for r in rows if r[0] == w) for w in sorted({r[0] for r in rows})}
        res["drc_boxes"] = [dict(rule=r[0], box_um=[float(x) for x in r[1].split()]) for r in rows[:50]]
        wd2 = wd / "ant"; wd2.mkdir()
        log = magic(ANT_TCL.format(gds=GDS, top=TOP), wd2)
        hits = re.findall(r"Cell: (\S+)\nAntenna violation detected at plane (.+)\nEffective antenna ratio ([\d.]+) > limit ([\d.]+)"
                          r"\nGate rect \((-?\d+) (-?\d+)\) to \((-?\d+) (-?\d+)\)", log)
        res["antenna_rules"] = "Magic antennacheck, sky130B tech (partial model)"
        # gate rectangle in Magic's internal units (0.005 um), top-cell coordinates
        res["antenna_violations"] = [dict(cell=c, plane=p, ratio=float(r), limit=float(lim),
                                          gate_rect_um=[round(int(v) * 0.005, 3) for v in (x0, y0, x1, y1)])
                                     for c, p, r, lim, x0, y0, x1, y1 in hits]
        res["antenna_violation_count"] = len(hits)
        res["antenna_feedback_count"] = int(re.search(r"ANTENNA_ERRORS (\d+)", log).group(1))
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "drc_boxes"}, indent=1))
