"""Layout of two first-cut periphery circuits in IHP SG13G2, drawn by script (revision 4.3, 9 October 2026).

Cells (sizes from circuits/gnucap/periphery.py, which simulated them with the PDK's PSP 103 transistors):
- tcim_ls: level shifter 1.2 V -> 3.3 V. 1.2 V inverter for the complement (PMOS 0.6/0.13, NMOS 0.3/0.13 um),
  thick-oxide NMOS pull-downs 1.0/0.45, cross-coupled thick-oxide PMOS 0.3/0.45, thick-oxide output inverter
  (PMOS 2.0/0.45, NMOS 1.0/0.45). Ports in, out, vdd (1.2 V), vddh (3.3 V), vss.
- tcim_wld: word-line driver. Thick-oxide inverter, PMOS 12/0.45 um as two 6 um fingers, NMOS 6/0.45 um, on a
  selectable rail. Ports in, out, vr (rail), vss.

Style: every transistor in one row, gates up, sources and drains down. Each net has its own horizontal Metal2
track, above the row for gate nets and below it for source/drain nets; Metal1 stubs reach the tracks through Via1.
A net that has both a gate and a source/drain joins its two tracks with a Metal1 riser at the right end of the cell.
Thick-oxide devices sit in one ThickGateOx region, with their own NWell; the 1.2 V inverter sits outside it.
Every NWell has an n+ tie to its supply, every group of NMOS a p+ substrate tie to vss.

Checked on the PC with the PDK's KLayout DRC (layout/run_periph_checks.bat, density excluded: a cell this small
cannot meet fill density) and the PDK's KLayout LVS against layout/periphery_cells.cdl. A connectivity self-check
below runs here first: shapes of different nets must not touch, and every net must be one connected piece.
Writes layout/tcim_periphery.gds, layout/periphery_cells.cdl and results/periphery_layout.json.
All coordinates in nm on the 5 nm grid; rule names as in the PDK's DRC deck."""
import json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GDS = ROOT / "layout" / "tcim_periphery.gds"
CDL = ROOT / "layout" / "periphery_cells.cdl"

ACTIV, GATPOLY, CONT, METAL1, VIA1, METAL2, PSD, NWELL, TGO = (1, 0), (5, 0), (6, 0), (8, 0), (19, 0), (10, 0), (14, 0), (31, 0), (44, 0)
M2_TEXT = (10, 25)

CNT, CNT_SP, CNT_ACT, CNT_GATE = 160, 180, 70, 110       # Cnt.a, Cnt.b, Cnt.c, Cnt.f
SD = CNT_ACT + CNT + CNT_GATE                            # 340 >= Act.c 230: Activ beyond the gate
SD_IN = CNT_GATE + CNT + CNT_GATE                        # 380 between two gates of one device
POLY_END = 180                                           # Gat.c
POLY_ENC = 70                                            # Cnt.d
CNT_POLY_ACT = 250                                       # >= Cnt.e 140: poly contact to Activ
M1W = 260                                                # Metal1 stubs: Cont 160 + 2 x 50 (M1.c1)
V = 190                                                  # V1.a
M2W = 300                                                # Metal2 tracks (M2.a 200)
TRACK = 600                                              # track pitch (M2.b 210)
PSD_ENC = 400                                            # pSD.i1 (PFET gate in ThickGateOx) and pSD.c 180
NW_ENC_HV, NW_ENC_LV = 620, 310                          # NW.c1, NW.c; also NW.e1 for the ties
DEV_GAP = 600                                            # Activ to Activ between devices (Act.b 210, Gat.b1 250)
TIE_W, TIE_H = 300, 600                                  # tie Activ


class Cell:
    def __init__(self, name):
        self.name, self.shapes, self.texts = name, [], []
        self.net_shapes = []          # (layer, box, net) for the self-check

    def box(self, layer, x0, y0, x1, y1, net=None):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        assert x1 > x0 and y1 > y0, (layer, x0, y0, x1, y1)
        for v in (x0, y0, x1, y1):
            assert v % 5 == 0, ("off grid", self.name, layer, x0, y0, x1, y1)
        self.shapes.append((layer, x0, y0, x1, y1))
        if net is not None:
            self.net_shapes.append((layer, (x0, y0, x1, y1), net))

    def text(self, layer, x, y, s):
        self.texts.append((layer, int(x), int(y), s))


def snap(v):
    return int(5 * round(v / 5))


def contact_column(c, xc, y0, y1, net, layer=CONT):
    """Contacts centred at xc between y0 and y1 (Activ edges), Cnt.c from the edges; returns the contact extent."""
    n = max(1, (y1 - y0 - 2 * CNT_ACT + CNT_SP) // (CNT + CNT_SP))
    span = n * CNT + (n - 1) * CNT_SP
    s = snap(y0 + (y1 - y0 - span) / 2)
    for k in range(n):
        yy = s + k * (CNT + CNT_SP)
        c.box(layer, xc - CNT // 2, yy, xc + CNT // 2, yy + CNT, net)
    return s, s + span


def mos(c, x0, w, l, nf, kind, hv, d, g, s):
    """One transistor, bottom of Activ at y = 0. Terminals: source/drain columns alternate s, d, s, ...
    Returns dict(x1=right Activ edge, sd=[(x, net, y_bottom_of_metal)], gate=(x, y_top_of_pad), ...)."""
    act_w = 2 * SD + nf * l + (nf - 1) * SD_IN
    c.box(ACTIV, x0, 0, x0 + act_w, w)
    gx = [x0 + SD + i * (l + SD_IN) for i in range(nf)]
    cols = [x0 + CNT_ACT + CNT // 2] + [gx[i] + l + CNT_GATE + CNT // 2 for i in range(nf)]
    nets = [s if i % 2 == 0 else d for i in range(nf + 1)]
    sd = []
    for xc, net in zip(cols, nets):
        cy0, cy1 = contact_column(c, xc, 0, w, net)
        sd.append(dict(x=xc, net=net, top=cy1 + 50, bottom=cy0 - 50))
    # gates; a bar joins the fingers above Activ, the gate contact sits on the bar (or on the head of one finger)
    for x in gx:
        c.box(GATPOLY, x, -POLY_END, x + l, w + POLY_END, g)
    head_h = CNT + 2 * POLY_ENC + (CNT_POLY_ACT - POLY_END - POLY_ENC) * 2   # 300: contact 250 .. 410 above Activ
    ytop = w + POLY_END + head_h
    if nf == 1:
        xm = gx[0] + l / 2
        hw = max(l, CNT + 2 * POLY_ENC + 2 * 5 * ((300 - CNT - 2 * POLY_ENC) // 10))
        c.box(GATPOLY, snap(xm - hw / 2), w + POLY_END, snap(xm + hw / 2), ytop, g)
    else:
        xm = gx[0] + l / 2
        c.box(GATPOLY, gx[0], w + POLY_END, gx[-1] + l, ytop, g)
    xm = snap(xm)
    yc0 = w + CNT_POLY_ACT
    c.box(CONT, xm - CNT // 2, yc0, xm + CNT // 2, yc0 + CNT, g)
    return dict(x0=x0, x1=x0 + act_w, w=w, sd=sd, gate=dict(x=xm, net=g, bottom=yc0 - 50), kind=kind, hv=hv,
                l=l, nf=nf, d=d, g=g, s=s)


def tie(c, x0, kind, net):
    """kind 'n': n+ tie in an NWell (no pSD); 'p': p+ substrate tie with pSD. Bottom at y = 0."""
    c.box(ACTIV, x0, 0, x0 + TIE_W, TIE_H, net)
    if kind == "p":
        c.box(PSD, x0 - 180, -180, x0 + TIE_W + 180, TIE_H + 180)
    xc = x0 + TIE_W // 2
    cy0, cy1 = contact_column(c, xc, 0, TIE_H, net)
    return dict(x0=x0, x1=x0 + TIE_W, sd=[dict(x=xc, net=net, top=cy1 + 50, bottom=cy0 - 50)])


def route(c, devices, ties, ports, x_right):
    """Metal2 tracks per net (gate nets above, source/drain nets below), Metal1 stubs and Via1, risers."""
    sd_nets, g_nets = [], []
    for dv in devices + ties:
        for t in dv["sd"]:
            if t["net"] not in sd_nets:
                sd_nets.append(t["net"])
    for dv in devices:
        if dv["gate"]["net"] not in g_nets:
            g_nets.append(dv["gate"]["net"])
    top_dev = max(dv["w"] for dv in devices) + POLY_END + 300
    y_low = {n: -1000 - k * TRACK for k, n in enumerate(sd_nets)}
    y_high = {n: top_dev + 800 + k * TRACK for k, n in enumerate(g_nets)}
    span = {}

    def via(x, y, net):
        c.box(VIA1, x - V // 2, y - V // 2, x + V // 2, y + V // 2, net)
        lo, hi = span.get((net, y), (x, x))
        span[(net, y)] = (min(lo, x), max(hi, x))

    for dv in devices + ties:
        for t in dv["sd"]:
            y = y_low[t["net"]]
            c.box(METAL1, t["x"] - M1W // 2, y - V // 2 - 50, t["x"] + M1W // 2, t["top"], t["net"])
            via(t["x"], y, t["net"])
    for dv in devices:
        gt = dv["gate"]
        y = y_high[gt["net"]]
        c.box(METAL1, gt["x"] - M1W // 2, gt["bottom"], gt["x"] + M1W // 2, y + V // 2 + 50, gt["net"])
        via(gt["x"], y, gt["net"])
    # risers for nets that are both gate and source/drain
    xr = x_right + 800
    for n in g_nets:
        if n in sd_nets:
            c.box(METAL1, xr - M1W // 2, y_low[n] - V // 2 - 50, xr + M1W // 2, y_high[n] + V // 2 + 50, n)
            via(xr, y_low[n], n)
            via(xr, y_high[n], n)
            xr += TRACK
    for (net, y), (lo, hi) in span.items():
        x0, x1 = lo - V // 2 - 100, hi + V // 2 + 100
        if x1 - x0 < 500:                     # Mn.d: Metal2 area >= 0.144 um2 (a track with a single via)
            x1 = x0 + 500
        c.box(METAL2, x0, y - M2W // 2, x1, y + M2W // 2, net)
    for p in ports:
        y = y_low.get(p, y_high.get(p))
        lo, _ = span[(p, y)]
        c.text(M2_TEXT, lo, y, p)
    return dict(y_low=y_low, y_high=y_high, x_risers_end=xr)


def nwell_box(c, devs, extra, enc):
    x0 = min(d["x0"] for d in devs + extra) - enc
    x1 = max(d["x1"] for d in devs + extra) + enc
    y1 = max([d["w"] for d in devs] + [TIE_H]) + enc
    c.box(NWELL, snap(x0), -enc, snap(x1), snap(y1))
    return x0, x1


def psd_box(c, devs):
    for d in devs:
        c.box(PSD, d["x0"] - PSD_ENC, -PSD_ENC, d["x1"] + PSD_ENC, d["w"] + PSD_ENC)


# ---------------------------------------------------------------- level shifter
def level_shifter():
    c = Cell("tcim_ls")
    x = 0
    # 1.2 V part: NMOS, substrate tie, then the NWell with the PMOS and its tie
    n_lv = mos(c, x, 300, 130, 1, "n", False, "inb", "in", "vss"); x = n_lv["x1"] + 500
    t_p1 = tie(c, x, "p", "vss"); x = t_p1["x1"] + 180 + 310 + 300 + NW_ENC_LV     # pSD, NW.f, margin
    p_lv = mos(c, x, 600, 130, 1, "p", False, "inb", "in", "vdd")
    t_n1 = tie(c, p_lv["x1"] + PSD_ENC + 300, "n", "vdd")
    psd_box(c, [p_lv])
    nw_lv = nwell_box(c, [p_lv], [t_n1], NW_ENC_LV)
    # 3.3 V part, inside one ThickGateOx region
    x = snap(nw_lv[1] + 1800 + 1000)          # NW.b1 (1.8 um) to the next NWell, and away from the region edge
    tgo_x0 = x - 1000
    t_p2 = tie(c, x, "p", "vss"); x = t_p2["x1"] + 500
    n1 = mos(c, x, 1000, 450, 1, "n", True, "x", "in", "vss"); x = n1["x1"] + DEV_GAP
    n2 = mos(c, x, 1000, 450, 1, "n", True, "xb", "inb", "vss"); x = n2["x1"] + DEV_GAP
    no = mos(c, x, 1000, 450, 1, "n", True, "out", "x", "vss"); x = no["x1"] + 620 + 620 + PSD_ENC   # NW.d1, NW.c1
    p1 = mos(c, x, 300, 450, 1, "p", True, "x", "xb", "vddh"); x = p1["x1"] + DEV_GAP + 2 * PSD_ENC
    p2 = mos(c, x, 300, 450, 1, "p", True, "xb", "x", "vddh"); x = p2["x1"] + DEV_GAP + 2 * PSD_ENC
    po = mos(c, x, 2000, 450, 1, "p", True, "out", "x", "vddh")
    t_n2 = tie(c, po["x1"] + PSD_ENC + 300, "n", "vddh")
    psd_box(c, [p1, p2, po])
    nw_hv = nwell_box(c, [p1, p2, po], [t_n2], NW_ENC_HV)
    devs = [n_lv, p_lv, n1, n2, no, p1, p2, po]
    r = route(c, devs, [t_p1, t_n1, t_p2, t_n2], ["in", "out", "vdd", "vddh", "vss"], nw_hv[1])
    ylo = min(r["y_low"].values()) - 1000
    yhi = max(r["y_high"].values()) + 1000
    c.box(TGO, tgo_x0, ylo, snap(r["x_risers_end"] + 500), yhi)
    netlist = [(f"M{k}", d) for k, d in enumerate(devs)]
    return c, netlist, ["in", "out", "vdd", "vddh", "vss"]


# ---------------------------------------------------------------- word-line driver
def wl_driver():
    c = Cell("tcim_wld")
    x = 1000
    t_p = tie(c, x, "p", "vss"); x = t_p["x1"] + 500
    n = mos(c, x, 6000, 450, 1, "n", True, "out", "in", "vss"); x = n["x1"] + 620 + 620 + PSD_ENC
    p = mos(c, x, 6000, 450, 2, "p", True, "out", "in", "vr")
    t_n = tie(c, p["x1"] + PSD_ENC + 300, "n", "vr")
    psd_box(c, [p])
    nw = nwell_box(c, [p], [t_n], NW_ENC_HV)
    r = route(c, [n, p], [t_p, t_n], ["in", "out", "vr", "vss"], nw[1])
    ylo = min(r["y_low"].values()) - 1000
    yhi = max(r["y_high"].values()) + 1000
    c.box(TGO, 0, ylo, snap(max(r["x_risers_end"], nw[1]) + 1000), yhi)
    return c, [("M0", n), ("M1", p)], ["in", "out", "vr", "vss"]


# ---------------------------------------------------------------- connectivity self-check
CONNECT = [(METAL1, CONT), (CONT, ACTIV), (CONT, GATPOLY), (METAL1, VIA1), (VIA1, METAL2)]


def touches(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def self_check(c):
    """Shapes with an assigned net: same-layer shapes of different nets must not touch; shapes on connected layers
    that overlap must carry the same net; every net must be one connected piece. Transistor Activ is not given a
    net (it carries source, drain and channel), so a contact on device Activ is checked against its own column only."""
    sh = c.net_shapes
    errs = []
    n = len(sh)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            li, bi, ni = sh[i]
            lj, bj, nj = sh[j]
            if not touches(bi, bj):
                continue
            same = li == lj
            conn = (li, lj) in CONNECT or (lj, li) in CONNECT
            if same or conn:
                if ni != nj:
                    # metal-metal spacing is a DRC matter; touching or overlapping is a short
                    errs.append(f"short {ni}/{nj} on {li}/{lj} at {bi} {bj}")
                else:
                    parent[find(i)] = find(j)
    roots = {}
    for i, (_, _, net) in enumerate(sh):
        roots.setdefault(net, set()).add(find(i))
    # source/drain columns of one device are joined through the transistor channel only in the extracted netlist,
    # not by geometry, so a net may legitimately be several pieces here only if it has no Metal2 track; all nets have one
    for net, rs in roots.items():
        if len(rs) != 1:
            errs.append(f"net {net} in {len(rs)} pieces")
    return errs


# ---------------------------------------------------------------- output
def _rec(rt, dt, data=b""):
    return struct.pack(">HBB", 4 + len(data), rt, dt) + data


def _real8(x):
    e = 64
    while x < 1 / 16:
        x *= 16; e -= 1
    while x >= 1:
        x /= 16; e += 1
    return struct.pack(">Q", (e << 56) | int(round(x * 2 ** 56)))


def _str(s):
    b = s.encode()
    return b + b"\0" * (len(b) % 2)


def write_gds(path, cells):
    ts = struct.pack(">12h", 2026, 10, 9, 0, 0, 0, 2026, 10, 9, 0, 0, 0)
    out = _rec(0x00, 0x02, struct.pack(">h", 600)) + _rec(0x01, 0x02, ts) + _rec(0x02, 0x06, _str("TCIM"))
    out += _rec(0x03, 0x05, _real8(1e-3) + _real8(1e-9))
    for c in cells:
        out += _rec(0x05, 0x02, ts) + _rec(0x06, 0x06, _str(c.name))
        for (ly, dt), x0, y0, x1, y1 in c.shapes:
            out += _rec(0x08, 0x00) + _rec(0x0D, 0x02, struct.pack(">h", ly)) + _rec(0x0E, 0x02, struct.pack(">h", dt))
            out += _rec(0x10, 0x03, struct.pack(">10i", x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)) + _rec(0x11, 0x00)
        for (ly, dt), x, y, s in c.texts:
            out += _rec(0x0C, 0x00) + _rec(0x0D, 0x02, struct.pack(">h", ly)) + _rec(0x16, 0x02, struct.pack(">h", dt))
            out += _rec(0x10, 0x03, struct.pack(">2i", x, y)) + _rec(0x19, 0x06, _str(s)) + _rec(0x11, 0x00)
        out += _rec(0x07, 0x00)
    out += _rec(0x04, 0x00)
    Path(path).write_bytes(out)


def cdl(name, devs, ports):
    lines = [f".SUBCKT {name} {' '.join(ports)}"]
    for inst, d in devs:
        model = f"sg13_{'hv' if d['hv'] else 'lv'}_{d['kind']}mos"
        bulk = d["s"]                    # NMOS sources are vss, PMOS sources are their well's supply
        w = d["w"] * d["nf"]
        lines.append(f"{inst} {d['d']} {d['g']} {d['s']} {bulk} {model} w={w / 1000:g}u l={d['l'] / 1000:g}u ng={d['nf']} m=1")
    lines.append(f".ENDS {name}")
    return "\n".join(lines)


if __name__ == "__main__":
    ls, ls_devs, ls_ports = level_shifter()
    wd, wd_devs, wd_ports = wl_driver()
    res = dict(gds=str(GDS.relative_to(ROOT)), cdl=str(CDL.relative_to(ROOT)), cells={})
    for c, devs, ports in ((ls, ls_devs, ls_ports), (wd, wd_devs, wd_ports)):
        errs = self_check(c)
        xs = [s[1] for s in c.shapes] + [s[3] for s in c.shapes]
        ys = [s[2] for s in c.shapes] + [s[4] for s in c.shapes]
        res["cells"][c.name] = dict(ports=ports, transistors=[cdl(c.name, [x], ports).splitlines()[1] for x in devs],
                                    shapes=len(c.shapes), width_um=(max(xs) - min(xs)) / 1000, height_um=(max(ys) - min(ys)) / 1000,
                                    area_um2=round((max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6, 2),
                                    self_check_errors=errs)
        print(c.name, "self-check:", "clean" if not errs else errs)
    write_gds(GDS, [ls, wd])
    CDL.write_text("* schematic netlists of layout/tcim_periphery.gds (from circuits/gnucap/periphery.py sizes)\n"
                   + cdl(ls.name, ls_devs, ls_ports) + "\n\n" + cdl(wd.name, wd_devs, wd_ports) + "\n")
    res["not_included"] = ("first-cut sizes; no layout-extracted simulation yet; the word-line driver is not pitch-matched "
                           "to the 2T2R row (it is drawn as a standalone cell); no guard rings beyond the ties")
    (ROOT / "results" / "periphery_layout.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "transistors"} for k, v in res["cells"].items()}, indent=1))
