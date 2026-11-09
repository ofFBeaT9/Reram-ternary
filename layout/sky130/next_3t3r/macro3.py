"""The analog macro for the next-chip 3T3R one-of-three array (8 November 2026), made from macro.py of the SKY130 test chip
(11 October 2026) by scripted edits (layout/sky130/next_3t3r/macro3.py): the 72 x 24 3T3R array, 72 row slices, 72 bit-line
slices (P, Z, N of every column), 24 source-line drivers and the shared control block. Not assembled into a chip.

Original description:

Contents: the drawn 72 x 24 2T2R array (layout/sky130/tcim_sky130_array), 72 row slices, 48 bit-line slices, 24
source-line drivers and the shared control block (cells from gen.py, each DRC- and LVS-checked on its own).

Floorplan (x to the right, y up; the array's lower-left corner is the origin):
  - word lines leave the array on its right edge (poly -> li -> metal1 -> metal2 -> metal3), run right on metal3 at
    their own height to a vertical track (metal2) in the channel of their stack, down to their slice, and right on
    metal3 into the slice's word-line track;
  - bit lines (metal2) and source lines (metal1 -> metal2) leave the array at its bottom edge, run down on metal2 to
    their own horizontal track (metal3) in the channel below the array, right to a vertical track (metal2) in the
    channel of their stack, down, and into the slice;
  - stacks, left to right: rows 0-35, rows 36-71, bit lines of columns 0-11, of columns 12-23, source lines; each with
    its line channel on its left and its 1.8 V channel on its right;
  - shared nets: one vertical metal4 strap per net in the left margin of each stack, crossing every slice's track of
    that net (via3), up to a horizontal metal5 bus above the stacks (via4); the control block (top right) feeds the
    buses through metal4 jumpers;
  - 1.8 V signals (row selects, bit-line programs, sense outputs, shared controls): from each slice's right edge on
    metal3 to a vertical metal4 track in the stack's 1.8 V channel, down to a pin on the macro's bottom edge;
  - pads (VPRG, VWLP, VWLR, VREF, IBIAS) and supplies (vdda, vccd, vss) are pins on the macro's right edge.
Every horizontal wire is metal3 (or metal5 for buses) and every vertical one metal2 or metal4, each at a coordinate of
its own, so no two nets share a track on one layer. Checked by magic DRC and by netgen LVS of the whole macro against
the reference netlist built from periph.spice and the array's schematic (one swapped connection must fail).

Usage: python3 macro.py   (after gen.py; needs magic, netgen, PDK_ROOT). Writes results/sky130_chip/macro_layout.json.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "periph"))
import gen  # noqa: E402

ROOT = gen.ROOT
WORK = gen.WORK
ARR = HERE.parent / "next_3t3r"       # the 3T3R array
ROWS, COLS = 72, 24
OUT = ROOT / "results" / "next_chip" / "macro3_layout.json"


def R(layer, x0, y0, x1, y1):
    return gen.R(layer, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def via(layer, x, y, s):
    return R(layer, x - s / 2, y - s / 2, x + s / 2, y + s / 2)


class Wires:
    """Collects shapes; contacts are painted last (painting a metal over a contact can erase it)."""
    def __init__(self):
        self.m, self.v = [], []

    def add(self, layer, x0, y0, x1, y1):
        self.m.append(R(layer, x0, y0, x1, y1))

    def v12(self, x, y):
        self.add("metal1", x - 0.25, y - 0.25, x + 0.25, y + 0.25); self.add("metal2", x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        self.v.append(via("via1", x, y, 0.32))

    def v23(self, x, y):
        self.add("metal2", x - 0.3, y - 0.3, x + 0.3, y + 0.3); self.add("metal3", x - 0.3, y - 0.3, x + 0.3, y + 0.3)
        self.v.append(via("via2", x, y, 0.4))

    def v34(self, x, y):
        self.add("metal3", x - 0.3, y - 0.3, x + 0.3, y + 0.3); self.add("metal4", x - 0.3, y - 0.3, x + 0.3, y + 0.3)
        self.v.append(via("via3", x, y, 0.4))

    def v45(self, x, y):
        self.add("metal4", x - 0.8, y - 0.8, x + 0.8, y + 0.8); self.add("metal5", x - 0.9, y - 0.9, x + 0.9, y + 0.9)
        self.v.append(via("via4", x, y, 1.2))

    def diode(self, x, y, s=3.0):
        """Antenna diode: an s x s n+ diffusion in the p-substrate (sky130_fd_pr__diode_pw2nd_05v5, area s*s um2), joined
        through li, metal1 and metal2 to the metal3 track that passes over (x, y)."""
        self.add("ndiode", x - s / 2, y - s / 2, x + s / 2, y + s / 2)
        self.add("locali", x - 0.3, y - 0.3, x + 0.3, y + 0.3)
        self.v.append(via("ndiodec", x, y, 0.17))
        self.v.append(via("viali", x, y, 0.17))
        self.add("metal1", x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        self.v12(x, y)
        self.v23(x, y)

    def h(self, layer, x0, x1, y, w):
        self.add(layer, min(x0, x1), y - w / 2, max(x0, x1), y + w / 2)

    def vt(self, layer, x, y0, y1, w):
        self.add(layer, x - w / 2, min(y0, y1), x + w / 2, max(y0, y1))

    def tcl(self):
        return "\n".join(self.m + self.v)


def geo(name):
    _, g = gen.build_cell(name, gen.cell_spec(name), margin=gen.MARGIN.get(name, 0.0))
    return g


def build(fault=False):
    G = {n: geo(n) for n in ("rowslice", "blslice", "sld", "ctrlglob")}
    W = Wires()
    place = []                                  # (cell, x, y) origins
    labels = []                                 # (name, layer, x0, y0, x1, y1, side)
    STR = gen.STRAP
    # ---------------------------------------------------------------- array and its line exits
    place.append(("tcim_sky130_array3", 0.0, 0.0))
    for r in range(ROWS):                       # word lines: right edge
        yc = 3.0 * r + 1.2
        W.add("poly", 134.30, yc - 0.25, 135.30, yc + 0.25)
        W.add("locali", 134.60, yc - 0.2, 135.45, yc + 0.2)
        W.v.append(via("polycont", 134.85, yc, 0.17))
        W.v.append(via("viali", 135.20, yc, 0.17))
        W.add("metal1", 135.00, yc - 0.2, 136.00, yc + 0.2)
        W.v12(135.75, yc)
        W.h("metal2", 135.75, 136.60, yc, 0.4)
        W.v23(136.60, yc)
    col_lines = []                              # (name, x in array)
    for c in range(COLS):
        col_lines += [(f"BLP{c}", 5.6 * c + 0.80), (f"SL{c}", 5.6 * c + 1.80), (f"BLZ{c}", 5.6 * c + 2.80), (f"BLN{c}", 5.6 * c + 4.80)]
    YH = {name: -3.0 - i * 1.0 for i, (name, _) in enumerate(col_lines)}
    XA = dict(col_lines)
    for name, x in col_lines:
        if name.startswith("SL"):
            W.add("metal1", x - 0.15, -0.8, x + 0.15, 0.05)
            W.v12(x, -0.6)
            W.vt("metal2", x, -0.6, YH[name], 0.3)
        else:
            W.vt("metal2", x, 0.05, YH[name], 0.36)
        W.v23(x, YH[name])
    YCH_BOT = -3.0 - len(col_lines) * 1.0      # bottom of the column channel
    # array vss rail (metal1, x -1.0..-0.6) -> metal4 strap to the vss bus
    W.add("metal1", -1.0, -2.2, -0.6, 0.0)
    W.v12(-0.8, -1.9); W.v23(-0.8, -1.9); W.v34(-0.8, -1.9)
    # ---------------------------------------------------------------- stacks
    ystack_top = YCH_BOT - 8.0
    stacks = [("R1", "rowslice", [f"r{r}" for r in range(35, -1, -1)]),
              ("R2", "rowslice", [f"r{r}" for r in range(71, 35, -1)]),
              ("B1", "blslice", [f"{pn}{c}" for c in range(0, 12) for pn in ("p", "z", "n")]),
              ("B2", "blslice", [f"{pn}{c}" for c in range(12, 24) for pn in ("p", "z", "n")]),
              ("S", "sld", [f"s{c}" for c in range(COLS)])]
    straps = {"rowslice": ["vwl", "vccd", "vdda", "vss"],
              "blslice": ["vprg", "sen", "flt", "vbp", "vcl", "vccd", "vdda", "vss"],
              "sld": ["vprg", "prg", "prgb", "dn", "vdda", "vss"]}
    bus_of = {"prg": "slprg", "prgb": "slprgb", "dn": "sldn"}
    lv_ports = {"rowslice": ["sel_lv"], "blslice": ["prg_lv", "out"], "sld": []}
    line_port = {"rowslice": "wl", "blslice": "bl", "sld": "sl"}
    x = 140.0
    strap_list = []                             # (bus net, x, y_bottom)
    lv_pins = []                                # (pin name, x)
    slices = []                                 # (stack, cell, key, origin x, origin y)
    for sname, cell, keys in stacks:
        g = G[cell]
        n = len(keys)
        ch_x0 = x
        xv = {k: ch_x0 + 1.0 + i * 1.0 for i, k in enumerate(keys)}      # vertical line tracks of this stack
        xs = ch_x0 + n * 1.0 + 3.0                                       # stack's left edge
        ox = xs - g["bbox"][0]
        hgt = g["bbox"][3] - g["bbox"][1]
        for j, k in enumerate(keys):
            top = ystack_top - j * (hgt + 1.0)
            oy = top - g["bbox"][3]
            slices.append((sname, cell, k, ox, oy))
            place.append((cell, ox, oy))
            # line: vertical track in the channel, horizontal into the slice's line track
            ly = oy + g["port_y"][line_port[cell]]
            if cell == "rowslice":
                r = int(k[1:]); y0 = 3.0 * r + 1.2
                W.h("metal3", 136.6, xv[k], y0, 0.6)                    # from the array's right edge
                W.v23(xv[k], y0)
            else:
                lname = {"p": "BLP", "z": "BLZ", "n": "BLN", "s": "SL"}[k[0]] + k[1:]
                y0 = YH[lname]
                W.h("metal3", XA[lname], xv[k], y0, 0.6)                # along the column channel
                W.v23(xv[k], y0)
            W.vt("metal2", xv[k], y0, ly, 0.3)
            W.v23(xv[k], ly)
            W.h("metal3", xv[k], xs + 0.5, ly, 0.6)
        ybot = ystack_top - n * (hgt + 1.0)
        # straps
        for i, net in enumerate(straps[cell]):
            sx = xs + 1.2 + i * STR
            strap_list.append((bus_of.get(net, net), sx, ybot + 1.0))
            for (_, c2, k, ox2, oy2) in [s for s in slices if s[0] == sname]:
                W.v34(sx, oy2 + g["port_y"][net])
        # 1.8 V channel on the right
        xr = ox + g["bbox"][2]
        lvx = xr + 2.0
        for (_, c2, k, ox2, oy2) in [s for s in slices if s[0] == sname]:
            for pname in lv_ports[cell]:
                py = oy2 + g["port_y"][pname]
                W.h("metal3", xr - 0.5, lvx, py, 0.6)
                W.v34(lvx, py)
                pin = {"sel_lv": f"sel_lv{k[1:]}", "prg_lv": f"prg_{k}", "out": f"out_{k}"}[pname]
                lv_pins.append((pin, lvx, py))
                lvx += 1.2
        x = lvx + 3.0
    YBOT = min(s[4] for s in slices) + min(G[c]["bbox"][1] for c in G) - 6.0
    # ---------------------------------------------------------------- shared-net buses (metal5) above the stacks
    bus_nets = ["vss", "vdda", "vccd", "vprg", "vwl", "sen", "flt", "vbp", "vcl", "slprg", "slprgb", "sldn"]
    BUSW = {"vss": 4.0, "vdda": 4.0, "vccd": 3.0}
    ybus, yb = {}, YCH_BOT + 2.0
    for net in bus_nets:
        w = BUSW.get(net, 2.0)
        ybus[net] = yb + w / 2
        yb += w + 2.0
    # control block, top right
    gc = G["ctrlglob"]
    cg_x = x + 60.0
    cg_ox = cg_x - gc["bbox"][0]
    cg_oy = max(yb + 6.0, 0.0) - gc["bbox"][1]
    place.append(("ctrlglob", cg_ox, cg_oy))
    jx = x + 4.0                                  # metal4 jumpers between the stacks and the control block
    cg_conn = {}
    for net in ["vss", "vdda", "vccd", "vwl", "sen", "flt", "vbp", "vcl", "slprg", "slprgb", "sldn"]:
        py = cg_oy + gc["port_y"][net]
        W.h("metal3", jx, cg_x + 0.5, py, 0.6)
        W.v34(jx, py)
        strap_list.append((net, jx, py))
        jx += STR
    for net in ["sen_lv", "flt_lv", "slprg_lv", "wlprog_lv", "r0", "r1", "r2"]:
        py = cg_oy + gc["port_y"][net]
        W.h("metal3", jx, cg_x + 0.5, py, 0.6)
        W.v34(jx, py)
        lv_pins.append((net, jx, py))
        jx += STR
    # antenna diodes on the reference selects: their gates (1 x 0.15 um) see the control block's full-width port track
    # (metal3) and the metal4 jumper to the macro's bottom edge (layout/sky130/periph/top.py: antenna check)
    for k, net in enumerate(["r0", "r1", "r2"]):
        W.diode(cg_x - 4.0 - 4.0 * k, cg_oy + gc["port_y"][net])
    assert jx < cg_x - 2.0, "control-block jumpers overlap the block"
    XRIGHT = cg_ox + gc["bbox"][2] + 10.0
    for net in ["vwlr", "vwlp", "ib", "vref"]:                     # pads: control block tracks to the right edge
        py = cg_oy + gc["port_y"][net]
        W.h("metal3", cg_ox + gc["bbox"][2] - 0.5, XRIGHT, py, 0.6)
        labels.append((net, "metal3", XRIGHT - 1.0, py - 0.3, XRIGHT, py + 0.3))
    # straps up to their buses
    strap_list.append(("vss", -0.8, -1.9))
    for net, sx, y0 in strap_list:
        yb_ = ybus[net]
        W.vt("metal4", sx, y0, yb_, 0.6)
        W.v45(sx, yb_)
    for net in bus_nets:
        xs_ = [sx for n2, sx, _ in strap_list if n2 == net]
        x0, x1 = min(xs_) - 1.0, max(xs_) + 1.0
        if net in ("vss", "vdda", "vccd", "vprg"):
            x1 = XRIGHT                                             # supplies and VPRG: pins on the right edge
            labels.append((net, "metal5", XRIGHT - 2.0, ybus[net] - BUSW.get(net, 2.0) / 2, XRIGHT, ybus[net] + BUSW.get(net, 2.0) / 2))
        W.h("metal5", x0, x1, ybus[net], BUSW.get(net, 2.0))
    # 1.8 V pins: metal4 down to the bottom edge
    for pin, px, py in lv_pins:
        W.vt("metal4", px, py, YBOT, 0.4)
        labels.append((pin, "metal4", px - 0.2, YBOT, px + 0.2, YBOT + 0.6))
    if fault:                                   # LVS check of the check: two row selects exchanged at their pins
        a = [i for i, p in enumerate(labels) if p[0] == "sel_lv0"][0]; b = [i for i, p in enumerate(labels) if p[0] == "sel_lv1"][0]
        labels[a] = ("sel_lv1",) + labels[a][1:]; labels[b] = ("sel_lv0",) + labels[b][1:]
    return place, W, labels, dict(ybot=YBOT, xright=XRIGHT, ytop=max(216.0, cg_oy + gc["bbox"][3]), slices=len(slices),
                                  lv_pins=len(lv_pins))


def tcl_for(name, place, W, labels):
    out = [f"load {name} -force", "snap internal"]
    for cell, ox, oy in place:
        out.append(f"box values {ox:.3f}um {oy:.3f}um {ox:.3f}um {oy:.3f}um\ngetcell {cell} child 0 0 parent {ox:.3f}um {oy:.3f}um")
    out.append(W.tcl())
    for i, (net, layer, x0, y0, x1, y1) in enumerate(labels):
        out.append(f"box values {x0:.3f}um {y0:.3f}um {x1:.3f}um {y1:.3f}um\nlabel {net} c {layer}\nport make {i + 1}")
    out.append(f"save {name}")
    return "\n".join(out)


def reference(pins):
    """Reference netlist: array schematic + slices + control block, flattened subcircuits from periph.spice."""
    arr = (ARR / "schematic3.spice").read_text()
    subs = "\n".join(gen.subckt_text(n) for n in ("rowslice", "blslice", "sld", "ctrlglob"))
    inst = [f"Xarr {' '.join([f'WL{r}' for r in range(ROWS)] + [f'BL{s}{c}' for s in 'PZN' for c in range(COLS)] + [f'SL{c}' for c in range(COLS)])} vss tcim_sky130_array3"]
    for r in range(ROWS):
        inst.append(f"Xr{r} sel_lv{r} WL{r} vwl vccd vdda vss rowslice")
    for c in range(COLS):
        for pn, L in (("p", "BLP"), ("z", "BLZ"), ("n", "BLN")):
            inst.append(f"Xb{pn}{c} prg_{pn}{c} {L}{c} out_{pn}{c} vprg sen flt vbp vcl vccd vdda vss blslice")
        inst.append(f"Xs{c} vprg SL{c} slprg slprgb sldn vdda vss sld")
    inst.append("Xg sen_lv flt_lv slprg_lv wlprog_lv r0 r1 r2 ib vref vwlr vwlp sen flt slprg slprgb sldn vwl vbp vcl vccd vdda vss ctrlglob")
    for net in ("r0", "r1", "r2"):                                    # antenna diodes (build())
        inst.append(f"Xd{net} vss {net} sky130_fd_pr__diode_pw2nd_05v5 perim=1.2e+07 area=9e+12")
    return f"* reference of the analog macro\n{arr}\n{subs}\n.subckt tcim_macro {' '.join(pins)}\n" + "\n".join(inst) + "\n.ends\n"


if __name__ == "__main__":
    for f in ("tcim_sky130_array3.mag", "rr3t3r.mag"):
        shutil.copy(ARR / f, WORK / f)
    place, W, labels, info = build()
    placef, Wf, labelsf, _ = build(fault=True)
    for c in ("tcim_macro3", "tcim_macro3_fault"):
        (WORK / f"{c}.mag").unlink(missing_ok=True)
    script = tcl_for("tcim_macro3", place, W, labels) + "\n" + tcl_for("tcim_macro3_fault", placef, Wf, labelsf) + """
foreach c {tcim_macro3 tcim_macro3_fault} {
  load $c
  select top cell
  puts "BBOX $c [box values]"
  extract all
  ext2spice lvs
  ext2spice -o $c.spice
}
load tcim_macro3
select top cell
drc style drc(full)
drc check
drc catchup
puts "DRCCOUNT [drc list count total]"
puts "DRCWHY [drc listall why]"
gds write tcim_macro3.gds
"""
    log = gen.magic(script, "macro.log")
    pins = [l[0] for l in labels]
    (WORK / "tcim_macro3_ref.spice").write_text(reference(pins))
    res = dict(info)
    m = re.search(r"DRCCOUNT (\d+)", log)
    res["drc_errors"] = int(m.group(1)) if m else None
    w = re.search(r"DRCWHY (.*)", log)
    res["drc_why"] = w.group(1)[:1500] if w and res["drc_errors"] else ""
    b = re.search(r"BBOX tcim_macro3 (-?\d+) (-?\d+) (-?\d+) (-?\d+)", log)
    if b:
        x0, y0, x1, y1 = (int(v) * 0.005 for v in b.groups())
        res["width_um"], res["height_um"] = round(x1 - x0, 1), round(y1 - y0, 1)
    for c in ("tcim_macro3", "tcim_macro3_fault"):
        r = subprocess.run(["netgen", "-batch", "lvs", f"{c}.spice {c}", "tcim_macro3_ref.spice tcim_macro", str(gen.NETGEN_SETUP),
                            f"{c}_lvs.out"], cwd=WORK, capture_output=True, text=True, timeout=7200)
        txt = (WORK / f"{c}_lvs.out").read_text() if (WORK / f"{c}_lvs.out").exists() else ""
        res["lvs_match" if c == "tcim_macro3" else "fault_lvs_match"] = ("Circuits match uniquely" in txt and "Final result: Circuits match" in (r.stdout + txt)
                                                                     and "property errors" not in (r.stdout + txt))
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
