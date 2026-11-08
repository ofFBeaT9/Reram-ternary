"""Static timing analysis of TCIM0 before layout: timing-driven synthesis (synth/run_synth_timing.sh), then OpenSTA
(synth/sta.tcl) on each library corner. Writes results/sta.json and results/sta_<tag>_<corner>.rpt.

Needs: yosys with slang, OpenSTA ('sta'), IHP_STDCELL_LIB (typical corner; the slow and fast corners are taken from
the same folder). SKY130_STDCELL_LIB is optional: sky130_fd_sc_hd__tt_025C_1v80.lib, for the second foundry route.

What the numbers are: cell delays from the foundry Liberty tables with the loads of the netlist. No wire
capacitance or resistance, an ideal clock, and the reset net is not buffered. Place and route will lower every slack."""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = [str(ROOT / "rtl" / f) for f in ("tcim_pkg.sv", "tcim_core.sv", "tcim_spi.sv", "tcim_top.sv")]
PERIOD_NS = 10.0                                   # the 100 MHz clock assumed in the roadmap (digital-mode timings)
B = ROOT / "synth" / "build_sta"


REV4 = [str(ROOT / "tests" / "equiv" / "rtl_rev4" / Path(f).name) for f in RTL]   # the logic of roadmap revision 4


def synth(tag, lib, driver, load_ff, tiehi, tielo, defs="", rtl=RTL):
    env = dict(os.environ, ABC_DRIVER=driver, ABC_LOAD=str(load_ff), TIEHI=tiehi, TIELO=tielo, SYNTH_DEFS=defs)
    subprocess.run([str(ROOT / "synth" / "run_synth_timing.sh"), tag, lib, str(int(PERIOD_NS * 1000)), "tcim_top", *rtl],
                   check=True, env=env, cwd=ROOT, stdout=subprocess.DEVNULL)
    log = (B / f"tcim_top.{tag}.log").read_text()
    m = re.findall(r"^\s+(\d+)\s+([\d.E+]+)\s+cells$", log, re.M)[-1]
    ff = sum(int(n) for n, name in re.findall(r"^\s+(\d+)\s+[\d.E+]+\s+(\S*(?:df[a-z]+|sdf[a-z]+)\S*)$", log, re.M))
    area = float(re.findall(r"Chip area for module '\\tcim_top': ([\d.]+)", log)[-1])
    return dict(cells=int(m[0]), area_um2=round(area, 1), flip_flops=ff)


def q_net(netlist, inst):
    """name of the net on the Q output of a flip-flop instance"""
    m = re.search(r"\b" + re.escape(inst) + r" \((.*?)\);", netlist, re.S)
    q = re.search(r"\.Q(?:_N)?\((.*?)\)", m.group(1)) if m else None
    return re.sub(r"_(\d+)_\s*$", r"[\1]", q.group(1).strip().lstrip("\\").strip()) if q else inst


def sta(tag, corner, lib, driver, load_pf):
    net = B / f"tcim_top.{tag}.v"
    env = dict(os.environ, STA_LIB=lib, STA_NETLIST=str(net), STA_TOP="tcim_top", STA_PERIOD=str(PERIOD_NS),
               STA_DRIVER=driver, STA_LOAD=str(load_pf))
    r = subprocess.run(["sta", "-no_init", "-exit", str(ROOT / "synth" / "sta.tcl")], capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    (ROOT / "results" / f"sta_{tag}_{corner}.rpt").write_text(out)
    if "Error" in out:
        raise SystemExit(f"OpenSTA reported an error for {tag} {corner}; see results/sta_{tag}_{corner}.rpt")
    val = {k: float(v) for k, v in re.findall(r"^@@ (\w+) (-?[\d.]+(?:e[-+]?\d+)?)$", out, re.M)}
    blk = lambda name: re.search(rf"@@ BEGIN {name}\n(.*?)@@ END", out, re.S).group(1)
    text = net.read_text()

    def path(b):
        sp = re.search(r"Startpoint: (\S+)", b).group(1); ep = re.search(r"Endpoint: (\S+)", b).group(1)
        arr = float(re.search(r"([\d.]+)\s+data arrival time", b).group(1))
        slack = float(re.search(r"(-?[\d.]+)\s+slack", b).group(1))
        stages = len(re.findall(r"^\s+[\d.]+\s+[\d.]+ [v^] \S+/\S+ \(", b, re.M))
        name = lambda p: q_net(text, p) if p.startswith("_") else p
        return dict(start=name(sp), end=name(ep), arrival_ns=arr, slack_ns=slack, cell_stages=stages)

    # limit checks: the reset pin drives every flip-flop directly here (place and route builds a buffer tree for it),
    # so its pins are counted apart from the data nets
    lim, kind, limits = blk("limits"), None, dict(reset_net=0, data_slew=0, data_capacitance=0, data_fanout=0)
    for line in lim.splitlines():
        if line.strip() in ("max slew", "max capacitance", "max fanout"):
            kind = line.strip().split()[1]
        elif "(VIOLATED)" in line:
            pin = line.split()[0]
            limits["reset_net" if pin == "rst_n" or pin.endswith(("/RESET_B", "/SET_B")) else "data_" + kind] += 1
    # worst slack per register (endpoints grouped by the name of the register they belong to)
    groups = {}
    for line in blk("endpoints").splitlines():
        m = re.match(r"\s*(\S+?)(?:/D)? \(\S+\)\s+[-\d.]+\s+[-\d.]+\s+(-?[\d.]+)", line)
        if not m:
            continue
        name = q_net(text, m.group(1)) if m.group(1).startswith("_") else m.group(1)
        name = re.sub(r"\[\d+\]$", "", name)
        groups[name] = min(groups.get(name, 1e9), float(m.group(2)))
    by_reg = dict(sorted(groups.items(), key=lambda kv: kv[1])[:8])
    return dict(worst_slack_by_register_ns=by_reg, setup_wns_ns=round(val["setup_wns"] * 1e9, 3), setup_tns_ns=round(val["setup_tns"] * 1e9, 3),
                hold_wns_ns=round(val["hold_wns"] * 1e9, 3), worst_path=path(blk("max path")),
                worst_register_to_register=path(blk("reg2reg")),
                limit_violations=limits)


if __name__ == "__main__":
    ihp = Path(os.environ["IHP_STDCELL_LIB"])
    corners = dict(typ_1p20V_25C=ihp, slow_1p08V_125C=ihp.with_name("sg13g2_stdcell_slow_1p08V_125C.lib"),
                   fast_1p32V_m40C=ihp.with_name("sg13g2_stdcell_fast_1p32V_m40C.lib"))
    res = dict(clock_period_ns=PERIOD_NS, tool=subprocess.run(["sta", "-version"], capture_output=True, text=True).stdout.strip(),
               scope="before layout: no wire parasitics, ideal clock, serial pins and reset excluded as asynchronous; "
                     "30 % of the period reserved on each side of the array interface", runs={})
    ihp_args = ("sg13g2_buf_4", 6, "sg13g2_tiehi L_HI", "sg13g2_tielo L_LO")
    for tag, defs in (("ihp", ""), ("ihp_pnx", "-D TCIM_ENC_PNX")):
        r = dict(library="IHP SG13G2 sg13g2_stdcell", trit_code="BSD-PNX" if defs else "two's complement",
                 netlist=synth(tag, str(ihp), *ihp_args, defs), corners={})
        for c, lib in corners.items():
            r["corners"][c] = sta(tag, c, str(lib), "sg13g2_buf_4", 0.006)
            print(tag, c, r["corners"][c]["setup_wns_ns"], r["corners"][c]["worst_path"]["end"], flush=True)
        res["runs"][tag] = r
    # the logic as it was in revision 4, to show what the analysis found before the result conversion became a table
    r = dict(library="IHP SG13G2 sg13g2_stdcell", trit_code="two's complement", rtl="tests/equiv/rtl_rev4",
             netlist=synth("ihp_rev4", str(ihp), *ihp_args, "", REV4), corners={})
    r["corners"]["typ_1p20V_25C"] = sta("ihp_rev4", "typ_1p20V_25C", str(ihp), "sg13g2_buf_4", 0.006)
    print("ihp_rev4 typ", r["corners"]["typ_1p20V_25C"]["setup_wns_ns"], r["corners"]["typ_1p20V_25C"]["worst_path"]["end"], flush=True)
    res["runs"]["ihp_rev4"] = r
    sky = os.environ.get("SKY130_STDCELL_LIB")
    if sky:
        r = dict(library="SkyWater SKY130 sky130_fd_sc_hd", trit_code="two's complement",
                 netlist=synth("sky130", sky, "sky130_fd_sc_hd__buf_4", 5, "sky130_fd_sc_hd__conb_1 HI", "sky130_fd_sc_hd__conb_1 LO"),
                 corners={})
        r["corners"]["tt_1p80V_25C"] = sta("sky130", "tt_1p80V_25C", sky, "sky130_fd_sc_hd__buf_4", 0.005)
        print("sky130 tt", r["corners"]["tt_1p80V_25C"]["setup_wns_ns"], flush=True)
        res["runs"]["sky130"] = r
    (ROOT / "results" / "sta.json").write_text(json.dumps(res, indent=1))
    print("wrote results/sta.json")
