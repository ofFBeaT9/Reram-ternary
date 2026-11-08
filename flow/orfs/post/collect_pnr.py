r"""Collect the place-and-route results of both platforms into results/pnr.json.

usage: collect_pnr.py <ihp work dir> <sky130 work dir> <export dir> [<folder with checks_<platform>.log or <platform>.log>]
  (run_full.bat: work dir = the unpacked export\<work folder>_<platform>.tgz, logs in <work folder>\)
  work dir = the ORFS WORK_HOME of a platform (logs/, reports/, results/), as written by flow/orfs/run_all.bat,
             plus the post-route timing reports post_<corner>.rpt written by sta_post.tcl
  export dir = flow/orfs/export as written by flow/orfs/collect.bat (DRC counts, LVS database)
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ihp, sky, exp = (Path(a) for a in sys.argv[1:4])
chk = Path(sys.argv[4]) if len(sys.argv) > 4 else None


def flow_metrics(work, plat):
    d = json.loads((work / f"logs/{plat}/tcim_top/base/6_report.json").read_text())
    g = lambda k: d.get(k)
    return dict(
        stdcells=g("finish__design__instance__count__stdcell"), stdcell_area_um2=g("finish__design__instance__area__stdcell"),
        die_area_um2=g("finish__design__die__area"), core_area_um2=g("finish__design__core__area"),
        utilization=g("finish__design__instance__utilization"),
        flip_flops=g("finish__design__instance__count__class:sequential_cell"),
        clock_buffers=g("finish__design__instance__count__class:clock_buffer"),
        timing_repair_buffers=g("finish__design__instance__count__class:timing_repair_buffer"),
        antenna_cells=g("finish__design__instance__count__class:antenna_cell"),
        flow_setup_tns=g("finish__timing__setup__tns"), flow_hold_tns=g("finish__timing__hold__tns"),
        clock_skew_ns=g("finish__clock__skew__setup"),
        ir_drop_worst_VDD_V=g("finish__design_powergrid__drop__worst__net:VDD__corner:default"),
        flow_errors=g("finish__flow__errors__count"),
        clock_gate_cells=g("finish__design__instance__count__class:clock_gate_cell") or 0,
        power_W_default_activity=g("finish__power__total"))


def post_sta(rpt):
    t = rpt.read_text()
    v = lambda k: float(re.search(rf"@@ {k} (\S+)", t).group(1)) * 1e9
    lim = t.split("@@ BEGIN limits")[1].split("@@ END")[0]
    return dict(setup_wns_ns=round(v("setup_wns"), 3), setup_tns_ns=round(v("setup_tns"), 3), hold_wns_ns=round(v("hold_wns"), 3),
                limit_violations_listed=len([l for l in lim.splitlines() if "VIOLATED" in l]))


out = dict(tool="OpenROAD-flow-scripts, image openroad/orfs:26Q4-71-g9b26ff8ff, on the owner's PC (Docker Desktop)",
           clock_period_ns=10.0, platforms={})
for plat, work, corners in (("ihp-sg13g2", ihp, ("typ_1p20V_25C", "slow_1p08V_125C", "fast_1p32V_m40C")),
                            ("sky130hd", sky, ("tt_1p80V_25C", "tt_025C_1v80", "ss_100C_1v60", "ff_n40C_1v95"))):
    p = flow_metrics(work, plat)
    p["post_route_sta"] = {c: post_sta(work / f"post_{c}.rpt") for c in corners if (work / f"post_{c}.rpt").exists()}
    # post_corners.sh: the same corners with every extracted R and C scaled by 0.8 and 1.2
    sens = {f"k{k} {c}": post_sta(work / f"post_k{k}_{c}.rpt") for k in ("0.8", "1.2") for c in corners
            if (work / f"post_k{k}_{c}.rpt").exists()}
    if sens:
        p["parasitic_sensitivity"] = sens
    cnt = exp / f"{plat}_6_drc_count.rpt"
    if not cnt.exists():                                  # run_full.bat keeps the count inside the work folder
        cnt = work / f"reports/{plat}/tcim_top/base/6_drc_count.rpt"
    p["drc_violations"] = int(cnt.read_text().strip()) if cnt.exists() else None
    lvs = exp / f"{plat}_6_lvs.lvsdb"
    p["lvs"] = None if not lvs.exists() else ("not supported by the ORFS platform" if "not supported" in lvs.read_text(errors="ignore")[:200] else "database written")
    logs = [chk / f"checks_{plat}.log", chk / f"{plat}.log"] if chk is not None else []
    for lf in [x for x in logs if x.exists()][:1]:
        t = lf.read_text(errors="ignore")
        if "Netlists match" in t:
            p["lvs"] = "netlists match (KLayout)"
        elif "LVS not supported" in t:
            p["lvs"] = "not supported by the ORFS platform"
    out["platforms"][plat] = p
ihp_drc = exp / "ihp-sg13g2_6_drc.lyrdb"
if not ihp_drc.exists():
    ihp_drc = ihp / "reports/ihp-sg13g2/tcim_top/base/6_drc.lyrdb"
if ihp_drc.exists():
    cats = re.findall(r"<item>.*?<category>'?([^<']+)'?</category>", ihp_drc.read_text(), re.S)
    out["platforms"]["ihp-sg13g2"]["drc_categories"] = {c: cats.count(c) for c in sorted(set(cats))}
ih = out["platforms"]["ihp-sg13g2"]
dens = all(re.match(r"M\d(Fil)?\.[a-z]/[a-z]", c) for c in ih.get("drc_categories", {}))
ih["notes"] = ("DRC: " + ("all markers are chip-level density rules (global Metal2-4 density, filler coverage), met at chip "
    "assembly with metal fill; the ORFS IHP deck is a reduced set." if dens else "see drc_categories.") +
    " Limits: see post_route_sta[...].limit_violations_listed (the reports list them).")
(ROOT / "results" / "pnr.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
