"""Top level of the SKY130 test chip: ChipFoundry's Caravan user area (user_analog_project_wrapper), by script
(11 October 2026).

Placed in the 2920 x 3520 um user area:
  - the analog macro tcim_macro (macro.py) near the top: its pad pins face the analog pads on the top edge;
  - the digital block tcim_chip_digital (placed and routed with OpenROAD-flow-scripts, flow/orfs/sky130hd_chip),
    below the macro; its 175 macro-side pins (top edge) are joined to the macro's 1.8 V pins through a channel
    (metal4 down from the macro, a metal3 track per signal, metal2 down to the block), its 57 pad-side pins (bottom
    edge) to the GPIO pins on the left and right edges (metal2, a metal3 track per signal, a metal4 track in an edge
    channel, metal3 into the pin);
  - one 2T2R cell of the array (rr2t2r) as a test structure, its word line, both bit lines and its source line on
    analog pads;
  - supplies: vertical metal4 trunks for vssa1, vccd1 and vdda1 near the right edge, joined to the wrapper's supply
    pins (metal3) and to the macro's buses and the digital block's rings (metal5). One ground, vssa1, for both the
    macro and the digital block: their substrate ties meet in the p-substrate anyway; vssd1 is left unused.
Pad assignment: chip/sky130/ARCHITECTURE.md section 2.2.
Writes layout/sky130/periph/work/user_analog_project_wrapper.mag/.gds, the reference netlist
netgen/user_analog_project_wrapper.spice and gds/ (chip/sky130/caravan), runs the extraction (connectivity only; pins of the
same name joined, as ChipFoundry's precheck does for analog projects: the harness joins them) and netgen LVS, once more
with a planted error (must fail), and writes results/sky130_chip/top_layout.json. Magic DRC (full rules) and the Magic
antenna check of the whole user area: signoff.py; ChipFoundry's precheck (all checks): flow/eda/pc_batch12.sh."""
import json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen    # noqa: E402
import macro  # noqa: E402

ROOT = gen.ROOT
WORK = gen.WORK
HARNESS = HERE / "harness"   # files of ChipFoundry's caravel_user_project_analog (README there)
DIG = ROOT / "flow" / "orfs" / "outdig" / "results" / "sky130hd" / "tcim_chip_digital" / "base"
# standard cells: the netlist of ChipFoundry's pinned PDK (open_pdks 3e0e31d), which ChipFoundry's LVS compares against, and
# the layouts of open_pdks 1e35547 except the tie cell conb_1, taken from 3e0e31d (stdcells_cf/README.md)
STD_SPICE = HERE / "stdcells_cf" / "sky130_fd_sc_hd.spice"
STD_GDS = HERE / "stdcells_cf" / "sky130_fd_sc_hd.gds"
OUTDIR = ROOT / "chip" / "sky130" / "caravan"
Wires = macro.Wires

# ---------------------------------------------------------------- pads of the harness (from the empty wrapper)
def harness_pins():
    pins = {}
    for l in (HARNESS / "user_analog_project_wrapper_empty.mag").read_text().splitlines():
        m = re.match(r"flabel (\S+) \S+ (-?\d+) (-?\d+) (-?\d+) (-?\d+) .* (\S+)$", l.strip())
        if m:
            lay, x0, y0, x1, y1, n = m.groups()
            pins.setdefault(n, []).append((lay, int(x0) / 100, int(y0) / 100, int(x1) / 100, int(y1) / 100))
    return pins


# digital pins -> GPIO (io index); inputs get io_out = tie_lo, io_oeb = tie_hi; outputs io_oeb = tie_lo
GPIO = {"clk": 5, "rst_n": 6, "sck": 7, "cs_n": 8, "mosi": 9, "miso": 10, "irq": 11, "pstb": 12, "pk": 13,
        "pamp[4]": 14, "pamp[3]": 15, "pamp[2]": 16, "pamp[1]": 17, "pamp[0]": 18,
        "cfg_ts[2]": 19, "cfg_ts[1]": 20, "cfg_ts[0]": 21, "cfg_tp[2]": 22, "cfg_tp[1]": 23, "cfg_tp[0]": 24,
        "cfg_tr[1]": 25, "cfg_tr[0]": 26}
INPUTS = ["clk", "rst_n", "sck", "cs_n", "mosi", "cfg_ts[2]", "cfg_ts[1]", "cfg_ts[0]", "cfg_tp[2]", "cfg_tp[1]",
          "cfg_tp[0]", "cfg_tr[1]", "cfg_tr[0]"]
OUTPUTS = ["miso", "irq", "pstb", "pk", "pamp[4]", "pamp[3]", "pamp[2]", "pamp[1]", "pamp[0]"]


def pad_signals():
    """(digital pin, wrapper pin) for the 57 pad-side connections."""
    out = []
    for k, s in enumerate(INPUTS):
        io = GPIO[s]
        out += [(s, f"io_in[{io}]"), (f"tie_lo[{k}]", f"io_out[{io}]"), (f"tie_hi[{k}]", f"io_oeb[{io}]")]
    for k, s in enumerate(OUTPUTS):
        io = GPIO[s]
        out += [(s, f"io_out[{io}]"), (f"tie_lo[{13 + k}]", f"io_oeb[{io}]")]
    return out


# macro 1.8 V pin <-> digital pin
def lv_map():
    m = {}
    for r in range(72):
        m[f"sel_lv{r}"] = f"wl_on[{r}]"
    for c in range(24):
        m[f"prg_p{c}"] = f"blp_prg[{c}]"; m[f"prg_n{c}"] = f"bln_prg[{c}]"
        m[f"out_p{c}"] = f"sa_p[{c}]"; m[f"out_n{c}"] = f"sa_n[{c}]"
    m.update({"sen_lv": "bl_sen", "flt_lv": "flt", "slprg_lv": "sl_prg", "wlprog_lv": "wl_prog",
              "r0": "ref_sel[0]", "r1": "ref_sel[1]", "r2": "ref_sel[2]"})
    return m


def def_pins():
    d = (DIG / "6_final.def").read_text()
    i, j = d.index("\nPINS"), d.index("END PINS")
    pins = {}
    for m in re.finditer(r"- (\S+) \+ NET \S+ \+ DIRECTION (\S+).*?LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \).*?PLACED \( (-?\d+) (-?\d+) \)",
                         d[i:j], re.S):
        n, dr, lay, a, b, c, e, x, y = m.groups()
        pins[n.replace("\\", "")] = (dr, lay, int(x) / 1000, int(y) / 1000)
    die = re.search(r"DIEAREA \( 0 0 \) \( (\d+) (\d+) \)", d)
    return pins, int(die.group(1)) / 1000, int(die.group(2)) / 1000


# ---------------------------------------------------------------- geometry
MX, MY = 60.0, 3150.0                  # analog macro origin (its top at MY + 216)
DX, DY = 409.0, 1444.0                 # digital block origin; pad tracks 1385-1441 clear of the GPIO pins
TX, TY = 2100.0, 3300.0                # test cell origin
TRUNK = {"vss": 2720.0, "vccd": 2740.0, "vdda": 2760.0}
TRW = 6.0


def build():
    P = harness_pins()
    W = Wires()
    place = [("tcim_macro", MX, MY), ("tcim_chip_digital", DX, DY), ("rr2t2r", TX, TY)]
    labels = []
    info = {}
    _, _, mlabels, minfo = macro.build()
    ml = {l[0]: l for l in mlabels}
    dp, dw, dh = def_pins()
    info.update(digital_die_um=[dw, dh])
    # ------------------------------------------------ channel: macro 1.8 V pins -> digital top pins
    lvm = lv_map()
    ybot_m = MY + minfo["ybot"]                       # macro bottom edge
    ytop_d = DY + dh                                  # digital top edge
    # the 48 sense outputs take the lowest tracks: their metal2 stubs (up from the input buffers of the digital block) stay
    # short, which keeps the buffers' gates within the antenna ratio at metal2 (before the diodes join at metal3)
    sig = sorted(lvm, key=lambda p: (not p.startswith("out_"), ml[p][2]))
    assert ybot_m - ytop_d > len(sig) * 1.0 + 4.0, "channel too small"
    diodes = []                                       # (net in the reference, x, y): antenna diodes
    nsense = 0
    for i, p in enumerate(sig):
        yt = ytop_d + 2.5 + i * 1.0
        xm = MX + (ml[p][2] + ml[p][4]) / 2
        q = dp[lvm[p]]; xd = DX + q[2]
        W.vt("metal4", xm, ybot_m + 0.3, yt, 0.4)
        W.v34(xm, yt)
        W.h("metal3", xm, xd, yt, 0.4)
        W.v23(xd, yt)
        if abs(xm - xd) < 1.2:
            # the two 0.6 um via pads closer than 1.2 um: a 0.4 um track between them leaves 0.1 um notches narrower than
            # met3.2 (0.3 um). Fill the gap at the pads' height (batch 29: 8 Magic / 4 KLayout met3.2 markers, where the
            # revision 4.9 block put two pins within 0.85 and 0.71 um of the macro pins above them)
            W.h("metal3", xm, xd, yt, 0.6)
        if p.startswith("out_"):
            # sense output -> input buffer of the digital block: until metal4 joins it to the sense amplifier, the
            # buffer's gate sees only this metal3 track, up to 1 mm long. A diode at the end of the track, right of the
            # channel (x 1560-1602, staggered so that diodes of neighbouring tracks do not touch).
            xdio = 1560.0 + 6.0 * (nsense % 8); nsense += 1
            W.h("metal3", max(xm, xd), xdio, yt, 0.4)
            W.diode(xdio, yt)
            diodes.append((f"lv_{lvm[p]}", xdio, yt))
        # into the pin: inside the block 0.14 um wide, the pin's own width (0.2 um there came within 0.14 um of the
        # block's routing next to the pin: met2.2 in the precheck's Magic DRC), 0.2 um outside it
        W.vt("metal2", xd, ytop_d - 0.4, ytop_d, 0.14)
        W.vt("metal2", xd, ytop_d, yt, 0.2)
    # ------------------------------------------------ pads: digital bottom pins -> GPIO pins on the edges
    ps = pad_signals()
    rk = lk = 0
    nin_r = nin_l = 0
    yb0 = DY - 3.0
    right_x0, left_x0 = 2870.0, 12.0
    for i, (dpin, wpin) in enumerate(sorted(ps, key=lambda t: dp[t[0]][2])):
        q = dp[dpin]; xd = DX + q[2]; yb = yb0 - i * 1.0
        lay, x0, y0, x1, y1 = P[wpin][0]
        yp = (y0 + y1) / 2
        right = x0 > 1000
        xe = right_x0 + rk if right else left_x0 + lk
        if right:
            rk += 1.0
        else:
            lk += 1.0
        W.vt("metal2", xd, DY + 0.4, DY, 0.14)     # inside the block at the pin's width (see the channel stubs)
        W.vt("metal2", xd, DY, yb, 0.2)
        W.v23(xd, yb)
        W.h("metal3", xd, xe, yb, 0.4)
        W.v34(xe, yb)
        W.vt("metal4", xe, yb, yp, 0.4)
        W.v34(xe, yp)
        W.h("metal3", xe, x1 if right else x0, yp, 0.4)
        if dpin in INPUTS:
            # pad input -> input buffer of the digital block: the buffer's gate sees this metal3 track and the metal4
            # of the edge channel before the harness joins it to the pad. A diode on the track, clear of everything else.
            xdio = (1100.0 + 6.0 * nin_r) if right else (100.0 + 6.0 * nin_l)
            if right:
                nin_r += 1
            else:
                nin_l += 1
            W.diode(xdio, yb)
            diodes.append((wpin, xdio, yb))
    info["pad_signals"] = len(ps)
    info["antenna_diodes"] = len(diodes)
    (WORK / "top_diodes.json").write_text(json.dumps(diodes))
    # ------------------------------------------------ supplies
    # trunks
    pin_y = lambda name, k=0: ((P[name][k][2] + P[name][k][4]) / 2)
    tr_span = {"vss": (pin_y("vssa1", 2) - 5, TY + 4.0),
               "vccd": (DY + 190.0, pin_y("vccd1", 0) + 5), "vdda": (pin_y("vdda1", 0) - 5, MY - 61.0)}
    for n, (y0, y1) in tr_span.items():
        W.vt("metal4", TRUNK[n], y0, y1, TRW)
    def to_pin(net, pname, k):
        lay, x0, y0, x1, y1 = P[pname][k]
        yc = (y0 + y1) / 2
        W.h("metal3", TRUNK[net] - TRW / 2, x1, yc, 10.0)
        for dy in (-3.0, 0.0, 3.0):
            W.v34(TRUNK[net], yc + dy)
    to_pin("vss", "vssa1", 2); to_pin("vccd", "vccd1", 0); to_pin("vdda", "vdda1", 0)
    # macro buses (metal5 at the macro's right edge) to the trunks; VPRG to its pad
    xm_r = MX + minfo["xright"]
    for net, tn in (("vss", "vss"), ("vdda", "vdda"), ("vccd", "vccd")):
        l = ml[net]; yc = MY + (l[3] + l[5]) / 2; w = l[5] - l[3]
        W.h("metal5", xm_r - 1.0, TRUNK[tn] + TRW / 2, yc, w)
        W.v45(TRUNK[tn], yc)
    lv = ml["vprg"]; yv = MY + (lv[3] + lv[5]) / 2
    pad = P["io_analog[4]"][0]; xpad = (pad[1] + pad[3]) / 2
    W.h("metal5", xm_r - 1.0, xpad + 3.0, yv, 2.0)
    for dx in (-1.5, 1.5):
        W.v45(xpad + dx, yv)
    W.vt("metal4", xpad, yv - 1.0, pad[4], 6.0)                  # pad io_analog[4] has metal4
    # digital block rings (metal4 right segments) to the trunks on metal5
    # (at y 99.9, between the block's met5 stripes; at 85.9 the via landed on the block's own ring via: via4.1)
    W.h("metal5", DX + 537.61 - 1.0, TRUNK["vss"] + TRW / 2, DY + 99.9, 2.0)
    W.v45(DX + 537.61, DY + 99.9); W.v45(TRUNK["vss"], DY + 99.9)
    W.h("metal5", DX + 542.41 - 1.0, TRUNK["vccd"] + TRW / 2, DY + 197.9, 2.0)
    W.v45(DX + 542.41, DY + 197.9); W.v45(TRUNK["vccd"], DY + 197.9)
    # ------------------------------------------------ analog pads of the macro
    xs = {"vwlp": 1505.0, "vwlr": 1515.0, "vref": 1525.0, "ib": 1535.0}
    yjog = {"vwlp": 3420.0, "vwlr": 3440.0, "vref": 3402.0, "ib": 3500.0}
    for net in ("vwlp", "vwlr", "vref", "ib"):
        l = ml[net]; y = MY + (l[3] + l[5]) / 2
        W.h("metal3", xm_r - 0.5, xs[net], y, 0.6)
        W.v34(xs[net], y)
        W.vt("metal4", xs[net], y, yjog[net], 0.8)
    for net, padn in (("vwlp", "io_analog[5]"), ("vwlr", "io_analog[6]")):
        pd = P[padn][0]; xpc = (pd[1] + pd[3]) / 2
        W.v45(xs[net], yjog[net])
        W.h("metal5", xpc - 1.0, xs[net] + 1.0, yjog[net], 2.0)
        W.v45(xpc, yjog[net])
        W.vt("metal4", xpc, yjog[net], pd[4], 6.0)                # pads 5 and 6 have metal4
    pd = P["io_analog[0]"][0]                                     # VREF: right edge, metal3
    W.v34(xs["vref"], yjog["vref"])
    W.h("metal3", xs["vref"], pd[3], yjog["vref"], 0.6)
    W.vt("metal3", pd[1] + 3.0, yjog["vref"], (pd[2] + pd[4]) / 2, 0.6)
    W.h("metal3", pd[1] + 2.0, pd[3], (pd[2] + pd[4]) / 2, 1.0)
    pd = P["io_analog[1]"][0]; xpc = (pd[1] + pd[3]) / 2           # IBIAS: top, metal3; along the top on metal5
    W.v45(xs["ib"], yjog["ib"])
    W.h("metal5", xs["ib"] - 1.0, xpc + 1.0, yjog["ib"], 2.0)
    W.v45(xpc, yjog["ib"]); W.v34(xpc, yjog["ib"])
    W.vt("metal3", xpc, yjog["ib"], pd[4], 1.0)
    # ------------------------------------------------ test cell (rr2t2r at TX, TY): WL poly, BLP/BLN metal2, SL metal1
    tc = {"wl": "io_analog[2]", "blp": "io_analog[3]", "bln": "io_analog[7]", "sl": "io_analog[8]"}
    yc = TY + 1.2                                                  # word line: poly 0.95..1.45 across the cell
    W.add("poly", TX + 3.5, yc - 0.25, TX + 4.6, yc + 0.25)
    W.add("locali", TX + 3.95, yc - 0.2, TX + 4.75, yc + 0.2)
    W.v.append(macro.via("polycont", TX + 4.15, yc, 0.17))
    W.v.append(macro.via("viali", TX + 4.5, yc, 0.17))
    W.add("metal1", TX + 4.3, yc - 0.2, TX + 5.3, yc + 0.2)
    W.v12(TX + 5.05, yc); W.v23(TX + 5.05, yc); W.v34(TX + 5.05, yc)
    pd = P[tc["wl"]][0]; xpc = (pd[1] + pd[3]) / 2
    W.vt("metal4", TX + 5.05, yc, 3480.0, 0.8); W.v34(TX + 5.05, 3480.0)
    W.h("metal3", TX + 5.05, xpc, 3480.0, 0.8); W.vt("metal3", xpc, 3480.0, pd[4], 1.0)
    # bit lines (metal2 at x 0.62..0.98 and 2.62..2.98 of the cell, full height 0..3.0): up to metal4
    for name, xo, padn, ylev in (("blp", 0.80, tc["blp"], 3486.0), ("bln", 2.80, tc["bln"], 3492.0)):
        x = TX + xo
        W.vt("metal2", x, TY + 3.0, TY + 4.5 + (0 if name == "blp" else 2.0), 0.36)
        y2 = TY + 4.5 + (0 if name == "blp" else 2.0)
        W.v23(x, y2); W.v34(x, y2)
        W.vt("metal4", x, y2, ylev, 0.8)
        pd = P[padn][0]; xpc = (pd[1] + pd[3]) / 2
        if name == "blp":
            W.v34(x, ylev); W.h("metal3", xpc, x, ylev, 0.8); W.vt("metal3", xpc, ylev, pd[4], 1.0)
        else:
            W.v45(x, ylev); W.h("metal5", xpc, x, ylev, 2.0); W.v45(xpc, ylev)
            W.vt("metal4", xpc, ylev, 3505.0, 0.8); W.v34(xpc, 3505.0); W.vt("metal3", xpc, 3505.0, pd[4], 1.0)
    # source line (metal1 x 1.65..1.95): below the cell to metal4, metal5 west at y TY - 6 to its pad
    x = TX + 1.80
    W.add("metal1", x - 0.15, TY - 1.0, x + 0.15, TY + 0.05)
    W.v12(x, TY - 0.8); W.v23(x, TY - 0.8); W.v34(x, TY - 0.8)
    pd = P[tc["sl"]][0]; xpc = (pd[1] + pd[3]) / 2
    W.vt("metal4", x, TY - 0.8, TY - 6.0, 0.8)
    W.v45(x, TY - 6.0)
    W.h("metal5", xpc - 1.0, x + 1.0, TY - 6.0, 2.0)
    W.v45(xpc, TY - 6.0)
    W.vt("metal4", xpc, TY - 6.0, 3508.0, 0.8); W.v34(xpc, 3508.0); W.vt("metal3", xpc, 3508.0, pd[4], 1.0)
    # substrate tie of the cell (li strip at y 2.51..2.77 across the cell) -> vss trunk
    W.add("locali", TX + 3.6, TY + 2.51, TX + 4.4, TY + 2.77)
    W.v.append(macro.via("viali", TX + 4.2, TY + 2.64, 0.17))
    W.add("metal1", TX + 4.0, TY + 2.44, TX + 4.6, TY + 2.84)
    W.v12(TX + 4.35, TY + 2.64); W.v23(TX + 4.35, TY + 2.64)
    W.h("metal3", TX + 4.35, TRUNK["vss"] + TRW / 2, TY + 2.64, 0.6)
    for dx in (-1.5, 0.0, 1.5):
        W.v34(TRUNK["vss"] + dx, TY + 2.64)
    return place, W, labels, info


# ---------------------------------------------------------------- reference netlist
def verilog_to_spice():
    """6_final.v of the digital block as a SPICE subcircuit with explicit supplies (VDD, VSS)."""
    std = {}
    for m in re.finditer(r"^\.subckt (\S+) (.*)$", STD_SPICE.read_text(), re.M):
        std[m.group(1)] = m.group(2).split()
    v = (DIG / "6_final.v").read_text()
    head = re.search(r"module tcim_chip_digital\s*\((.*?)\);", v, re.S).group(1)
    ports = [p.strip().replace("\\", "") for p in head.split(",")]
    widths = {}
    for m in re.finditer(r"^\s*(input|output)\s*(\[(\d+):(\d+)\])?\s*([^;]+);", v, re.M):
        for n in m.group(5).split(","):
            n = n.strip()
            widths[n] = (int(m.group(3)), int(m.group(4))) if m.group(2) else None
    flat = []
    for p in ports:
        w = widths.get(p)
        flat += [p] if w is None else [f"{p}[{i}]" for i in range(w[1], w[0] + 1)]
    lines = [f".subckt tcim_chip_digital {' '.join(flat)} VDD VSS"]
    for m in re.finditer(r"^\s*(sky130_fd_sc_hd__\S+)\s+(\S+)\s*\((.*?)\);", v, re.M | re.S):
        cell, inst, body = m.groups()
        conn = {a: b.strip().replace("\\", "").replace(" ", "") for a, b in re.findall(r"\.(\w+)\(([^)]*)\)", body)}
        nets = []
        for pin in std[cell]:
            if pin in ("VPWR", "VPB"):
                nets.append("VDD")
            elif pin in ("VGND", "VNB"):
                nets.append("VSS")
            else:
                n = conn.get(pin, "")
                nets.append(n if n else f"nc_{inst}_{pin}")
        lines.append(f"X{inst.replace(chr(92), '')} {' '.join(nets)} {cell}")
    # antenna diodes inserted by the router: in the DEF and the GDS, not in 6_final.v (physical-only cells there)
    d = (DIG / "6_final.def").read_text()
    i, j = d.index("\nNETS"), d.index("END NETS")
    nets = {}
    for m in re.finditer(r"- (\S+)((?:\s*\( \S+ \S+ \))+)", d[i:j]):
        for inst, pin in re.findall(r"\( (\S+) (\S+) \)", m.group(2)):
            nets[(inst, pin)] = m.group(1).replace("\\", "")
    for inst in re.findall(r"- (\S+) sky130_fd_sc_hd__diode_2 ", d):
        conn = {"DIODE": nets[(inst, "DIODE")]}
        nets_ = [conn.get(p) or ("VDD" if p in ("VPWR", "VPB") else "VSS") for p in std["sky130_fd_sc_hd__diode_2"]]
        lines.append(f"X{inst} {' '.join(nets_)} sky130_fd_sc_hd__diode_2")
    assert not re.search(r"^\s*assign\s", v, re.M), "6_final.v has assign statements: not handled"
    lines.append(".ends")
    return "\n".join(lines), flat


def reference():
    ports = (HARNESS / "wrapper_ports.txt").read_text().split()
    dsub, dports = verilog_to_spice()
    msub = macro.reference([l[0] for l in macro.build()[2]])
    lvm = lv_map()
    mpins = [l[0] for l in macro.build()[2]]
    conn = {}
    # macro pins
    mnet = {p: f"lv_{lvm[p]}" if p in lvm else p for p in mpins}
    mnet.update({"vss": "vssa1", "vdda": "vdda1", "vccd": "vccd1", "vprg": "io_analog[4]", "vwlp": "io_analog[5]",
                 "vwlr": "io_analog[6]", "vref": "io_analog[0]", "ib": "io_analog[1]"})
    dnet = {}
    for p in dports:
        dnet[p] = None
    for mp, dpn in lvm.items():
        dnet[dpn] = f"lv_{dpn}"
    for dpin, wpin in pad_signals():
        dnet[dpin] = wpin
    dl = [dnet[p] if dnet.get(p) else f"dnc_{p}" for p in dports] + ["vccd1", "vssa1"]
    inst = [f"Xmacro {' '.join(mnet[p] for p in mpins)} tcim_macro",
            f"Xdig {' '.join(dl)} tcim_chip_digital",
            "Xtc io_analog[2] io_analog[3] io_analog[7] io_analog[8] vssa1 tc2t2r"]
    for net, _, _ in json.loads((WORK / "top_diodes.json").read_text()):     # antenna diodes (build())
        inst.append(f"Xd_{net} vssa1 {net} sky130_fd_pr__diode_pw2nd_05v5 perim=1.2e+07 area=9e+12")
    tcsub = """.subckt tc2t2r wl blp bln sl vss
XMp dp wl sl vss sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
XRp blp dp sky130_fd_pr_reram__reram_cell area_ox=0.0676
XMn dn wl sl vss sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
XRn bln dn sky130_fd_pr_reram__reram_cell area_ox=0.0676
.ends"""
    body = "\n".join(inst)
    return (f"* user_analog_project_wrapper: TCIM0 SKY130 test chip (reference for LVS)\n{msub}\n{dsub}\n{tcsub}\n"
            f".subckt user_analog_project_wrapper {' '.join(ports)}\n{body}\n.ends\n")


def tcl(place, W, labels):
    # gds readonly: the routed digital block is written back to the output GDS exactly as OpenROAD wrote it (a round trip
    # through Magic's own layer model regenerates implant layers and snaps 1 nm data, which broke implant and contact rules)
    # The standard cells come from STD_GDS, read first (gds noduplicates: the copies inside 6_final.gds are ignored). The
    # PDK versions differ in the tie cell conb_1 (resistor marker 0.045 um in 3e0e31d, 0.5 um in 1e35547; LVS against the
    # other version reports a property error) and in the NPC of and2_0 (3e0e31d's notch fails npc.2 next to a21boi_0):
    # STD_GDS takes conb_1 from 3e0e31d and every other cell from 1e35547 (stdcells_cf/README.md).
    out = ["gds readonly true", "gds noduplicates true", f'gds read "{STD_GDS}"', f'gds read "{DIG / "6_final.gds"}"',
           "load user_analog_project_wrapper", "snap internal"]
    for cell, ox, oy in place:
        out.append(f"box values {ox:.3f}um {oy:.3f}um {ox:.3f}um {oy:.3f}um\ngetcell {cell} child 0 0 parent {ox:.3f}um {oy:.3f}um")
    out.append(W.tcl())
    out.append("save user_analog_project_wrapper")          # the top cell only: the cells below stay as their own scripts wrote them
    return "\n".join(out)


def fault_lvs():
    """The same LVS with a planted error: clk and rst_n exchanged at the digital block in the reference. Must fail."""
    ref = (WORK / "top_ref.spice").read_text()
    i = ref.index("Xdig ")
    j = ref.index("\n", i)
    line = ref[i:j].replace("io_in[5] ", "@@ ").replace("io_in[6] ", "io_in[5] ").replace("@@ ", "io_in[6] ")
    assert line != ref[i:j]
    (WORK / "top_ref_fault.spice").write_text(ref[:i] + line + ref[j:])
    r = subprocess.run(["netgen", "-batch", "lvs", "user_analog_project_wrapper.spice user_analog_project_wrapper",
                        "top_ref_fault.spice user_analog_project_wrapper", str(gen.NETGEN_SETUP), "top_fault_lvs.out"],
                       cwd=WORK, capture_output=True, text=True, timeout=14400)
    txt = (WORK / "top_fault_lvs.out").read_text()
    return "Final result: Circuits match" in (r.stdout + txt) and "Circuits match uniquely" in txt


if __name__ == "__main__" and sys.argv[1:] == ["fault"]:
    out = ROOT / "results" / "sky130_chip" / "top_layout.json"
    info = json.loads(out.read_text())
    info["fault_lvs_match"] = fault_lvs()
    out.write_text(json.dumps(info, indent=1))
    print("fault LVS match:", info["fault_lvs_match"])
elif __name__ == "__main__":
    t = (HARNESS / "user_analog_project_wrapper_empty.mag").read_text().replace("tech $PDK", "tech sky130B")
    (WORK / "user_analog_project_wrapper.mag").write_text(t)
    for f in ("tcim_sky130_array.mag", "rr2t2r.mag"):
        shutil.copy(gen.ROOT / "layout" / "sky130" / f, WORK / f)
    place, W, labels, info = build()
    log = gen.magic(tcl(place, W, labels) + """
load user_analog_project_wrapper
select top cell
puts "BBOX [box values]"
gds write user_analog_project_wrapper.gds
extract no capacitance
extract no coupling
extract no resistance
extract no length
extract unique notopports
extract all
ext2spice lvs
ext2spice -o user_analog_project_wrapper.spice
""", "top.log")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "netgen").mkdir(exist_ok=True)
    ref = reference()
    std = STD_SPICE.read_text()
    (WORK / "top_ref.spice").write_text(ref + "\n" + std)
    (OUTDIR / "netgen" / "user_analog_project_wrapper.spice").write_text(ref)
    (OUTDIR / "gds").mkdir(exist_ok=True)
    shutil.copy(WORK / "user_analog_project_wrapper.gds", OUTDIR / "gds" / "user_analog_project_wrapper.gds")
    r = subprocess.run(["netgen", "-batch", "lvs", "user_analog_project_wrapper.spice user_analog_project_wrapper",
                        "top_ref.spice user_analog_project_wrapper", str(gen.NETGEN_SETUP), "top_lvs.out"],
                       cwd=WORK, capture_output=True, text=True, timeout=14400)
    txt = (WORK / "top_lvs.out").read_text() if (WORK / "top_lvs.out").exists() else ""
    # property errors (device sizes) count as failures (a conb_1 of the wrong PDK version shows up here: see tcl())
    m = re.search(r"The following cells had property errors:\n((?: \S+\n)*)", r.stdout + txt)
    prop = [c.strip() for c in m.group(1).splitlines()] if m else []
    info["property_errors_in"] = prop
    info["lvs_match"] = ("Final result: Circuits match" in (r.stdout + txt) and "Circuits match uniquely" in txt and not prop)
    info["lvs_tail"] = (r.stdout + txt)[-1500:]
    info["fault_lvs_match"] = fault_lvs()
    out = ROOT / "results" / "sky130_chip" / "top_layout.json"
    out.write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "lvs_tail"}, indent=1))
    print(info["lvs_tail"])
