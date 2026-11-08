"""Layout generator for the SKY130 periphery cells of chip/sky130/sim/periph.spice (11 October 2026).

Transistors come from the PDK's own magic generators (sky130::<device>_draw, with guard ring), one subcell per
size. A cell is a row of transistors, centred on y = 0, wired by template:
  drain / source : metal1 jog outward at y = 0, via1, metal2 stub UP to a metal3 track above the row
  gate           : bottom gate contact enlarged, via1, metal2 stub DOWN to a metal3 track below the row
  body           : the guard ring's local interconnect, mcon, via1, metal2 stub DOWN to a track below the row
A net with connections above and below gets a metal2 riser beyond the right end of the row joining its two tracks.
Every cell port is a metal3 label on its track. Each cell is checked with magic DRC, extracted, and compared with its
subcircuit in periph.spice by netgen; then a copy with one transistor's gate moved to another net must fail LVS.

Usage: python3 gen.py [cell ...]   (needs magic, netgen, PDK_ROOT with sky130B). Writes results/sky130_chip/periph_layout.json.
"""
import json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = HERE / "work"
PDK = Path(os.environ["PDK_ROOT"]) / "sky130B"
RC = PDK / "libs.tech" / "magic" / "sky130B.magicrc"
NETGEN_SETUP = PDK / "libs.tech" / "netgen" / "sky130B_setup.tcl"
SPICE = ROOT / "chip" / "sky130" / "sim" / "periph.spice"

# ---------------------------------------------------------------- the cells
# Each cell is a subcircuit of periph.spice, flattened to transistors (instances of other subcircuits expanded,
# multipliers m=N drawn as N transistors). The layout is generated from that list; LVS then compares the extracted
# layout with the same netlist, so a wrong wire, an open or a short drawn by the generator is caught.
HV_N, HV_P, LV_N, LV_P = "nfet_g5v0d10v5", "pfet_g5v0d10v5", "nfet_01v8", "pfet_01v8"
# slices are stacked in the macro; their shared nets are joined by vertical metal4 straps in this left margin (um)
STRAP = 2.4
MARGIN = {"rowslice": 4 * STRAP + 1.0, "blslice": 8 * STRAP + 1.0, "sld": 6 * STRAP + 1.0}
CELL_NAMES = ["tg", "wld", "bld", "sld", "ls_lv2hv", "sa", "refbias", "nor3hv", "nor2hv", "rowslice", "blslice", "ctrlglob"]


def cell_spec(name):
    """(ports, [(type, w, l, D, G, S, B), ...]) from the flattened subcircuit."""
    lines = subckt_text(name).splitlines()
    ports = lines[0].split()[2:]
    devs = []
    for l in lines[1:-1]:
        f = l.split()
        d, g, s_, b, model = f[1:6]
        kv = dict(x.split("=") for x in f[6:])
        t = model.replace("sky130_fd_pr__", "")
        for _ in range(int(kv.get("m", 1))):
            devs.append((t, float(kv["w"]), float(kv["l"]), d, g, s_, b))
    return ports, devs


UM = 1.0
TRACK, TRACKW, VIA1, VIA2, PAD = 1.0, 0.6, 0.32, 0.4, 0.5     # um


def devname(t, w, l):
    return f"d_{t}_w{w:g}_l{l:g}".replace(".", "p")


def magic(script, log):
    WORK.mkdir(exist_ok=True)
    (WORK / "run.tcl").write_text(script + "\nquit -noprompt\n")
    r = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(RC), "run.tcl"], cwd=WORK, capture_output=True, text=True,
                       timeout=3600, stdin=subprocess.DEVNULL)
    (WORK / log).write_text(r.stdout + r.stderr)
    return r.stdout + r.stderr


def make_devices(devs):
    tcl = []
    for t, w, l in sorted(devs):
        n = devname(t, w, l)
        (WORK / f"{n}.mag").unlink(missing_ok=True)
        tcl.append(f"""load {n} -force
set p [dict merge [sky130::sky130_fd_pr__{t}_defaults] [list w {w} l {l} nf 1]]
set p [sky130::sky130_fd_pr__{t}_check $p]
sky130::sky130_fd_pr__{t}_draw $p
save {n}""")
    magic("\n".join(tcl), "devices.log")


def parse_dev(n):
    """Port points, metal1 rectangles, guard-ring outline and outline of everything (um)."""
    txt = (WORK / f"{n}.mag").read_text()
    unit = 0.005 if "magscale 1 2" in txt else 0.01
    layer, rects, labels = None, {}, {}
    for line in txt.splitlines():
        m = re.match(r"<< (\S+) >>", line)
        if m:
            layer = m.group(1); continue
        if line.startswith("rect") and layer:
            x0, y0, x1, y1 = (int(v) * unit for v in line.split()[1:5])
            rects.setdefault(layer, []).append((x0, y0, x1, y1))
        if line.startswith("rlabel"):
            f = line.split()
            labels[f[-1]] = (f[1], int(f[2]) * unit, int(f[3]) * unit)
    allr = [r for k, v in rects.items() if k != "checkpaint" for r in v]
    box = (min(r[0] for r in allr), min(r[1] for r in allr), max(r[2] for r in allr), max(r[3] for r in allr))
    ring = [r for k, v in rects.items() if "subdiff" in k and "cont" not in k for r in v]
    rbox = (min(r[0] for r in ring), min(r[1] for r in ring), max(r[2] for r in ring), max(r[3] for r in ring))
    m1 = rects.get("metal1", []) + rects.get("viali", [])      # a contact tile carries metal1 too
    def m1at(x, y):
        c = [r for r in m1 if r[0] - 1e-6 <= x <= r[2] + 1e-6 and r[1] - 1e-6 <= y <= r[3] + 1e-6]
        return (min(r[0] for r in c), min(r[1] for r in c), max(r[2] for r in c), max(r[3] for r in c)) if c else None
    d = labels["D"]; s = labels["S"]; g = labels["G"]
    gate_pads = [r for r in m1 if r[0] < 0 < r[2] and abs(r[1]) > 0.05]
    gbot = [r for r in gate_pads if r[3] < 0]
    gb = (min(r[0] for r in gbot), min(r[1] for r in gbot), max(r[2] for r in gbot), max(r[3] for r in gbot))
    gtop = [r for r in gate_pads if r[1] > 0]
    gt = (min(r[0] for r in gtop), min(r[1] for r in gtop), max(r[2] for r in gtop), max(r[3] for r in gtop))
    li = rects.get("locali", [])
    ymin = min(r[1] for r in li)
    lib = [r for r in li if abs(r[1] - ymin) < 1e-6]                    # bottom side of the guard ring's li
    li_bottom = (min(r[0] for r in lib), ymin, max(r[2] for r in lib), max(r[3] for r in lib))
    return dict(unit=unit, box=box, ring=rbox, D=m1at(d[1], d[2]), S=m1at(s[1], s[2]), Gbot=gb, Gtop=gt, li=li, li_bottom=li_bottom)


def R(layer, x0, y0, x1, y1):
    return f"box values {x0:.3f}um {y0:.3f}um {x1:.3f}um {y1:.3f}um\npaint {layer}"


def build_cell(name, spec, fault=False, margin=0.0):
    """margin: free width (um) left of the row, which every port track crosses (for vertical straps)."""
    ports, devs = spec
    info = {}
    for t, w, l, *_ in devs:
        n = devname(t, w, l)
        if n not in info:
            info[n] = parse_dev(n)
    out = [f"load {name} -force", "snap internal"]
    x = 0.0
    top_conn, bot_conn = {}, {}           # net -> list of x of stubs
    stubs_top, stubs_bot = [], []         # (net, x, y_start)
    prev_kind = None
    for k, (t, w, l, D, G, S_, B) in enumerate(devs):
        if fault and k == 0:
            G = S_ if G == D else D        # LVS fault: first transistor's gate moved to another of its nets
        n = devname(t, w, l); d = info[n]
        kind = ("hv" if "g5v0" in t else "lv") + t[0]
        gap = ({"hvp": 2.1, "lvp": 1.5}.get(kind, 0.6)) if kind == prev_kind else 2.6   # n-wells: HV 2.0, LV 1.27 um
        if prev_kind is None:
            gap = 0.0
        cx = x + gap - d["box"][0]
        x = cx + d["box"][2]
        prev_kind = kind
        out.append(f"box values {cx:.3f}um 0um {cx:.3f}um 0um\ngetcell {n} child 0 0 parent {cx:.3f}um 0um")
        # drain (left) and source (right): metal1 jog outward at y = 0, via1, metal2 pad
        for net, r, side in ((D, d["D"], -1), (S_, d["S"], +1)):
            xo = r[0] if side < 0 else r[2]
            xp = cx + xo + side * (0.30 + PAD / 2)
            out.append(R("metal1", cx + min(xo, xo + side * 0.36), -0.15, cx + max(xo, xo + side * 0.36), 0.15))
            out.append(R("metal1", xp - PAD / 2, -PAD / 2, xp + PAD / 2, PAD / 2))
            out.append(R("metal2", xp - PAD / 2, -PAD / 2, xp + PAD / 2, PAD / 2))
            out.append(R("via1", xp - VIA1 / 2, -VIA1 / 2, xp + VIA1 / 2, VIA1 / 2))
            stubs_top.append((net, xp, 0.0))
        # gate: bottom contact, enlarged downward
        g = d["Gbot"]; gx = cx + (g[0] + g[2]) / 2; gy1 = g[3]
        out.append(R("metal1", gx - PAD / 2, gy1 - PAD, gx + PAD / 2, gy1))
        out.append(R("metal2", gx - PAD / 2, gy1 - PAD, gx + PAD / 2, gy1))
        out.append(R("via1", gx - VIA1 / 2, gy1 - PAD / 2 - VIA1 / 2, gx + VIA1 / 2, gy1 - PAD / 2 + VIA1 / 2))
        stubs_bot.append((G, gx, gy1 - PAD / 2))
        t_ = d["Gtop"]                     # the unused top gate contact: metal1 grown to its minimum area
        out.append(R("metal1", gx - 0.2, cx * 0 + t_[1], gx + 0.2, t_[1] + 0.3))
        # body: guard ring bottom side, left part
        rb = d["ring"]; lb = d["li_bottom"]
        bx = cx + lb[0] + 0.085; by = (lb[1] + lb[3]) / 2         # bottom-left corner of the ring
        out.append(R("viali", bx - 0.085, lb[1], bx + 0.085, lb[3]))
        out.append(R("metal1", bx - PAD / 2, by - PAD / 2, bx + PAD / 2, by + PAD / 2))
        out.append(R("metal2", bx - PAD / 2, by - PAD / 2, bx + PAD / 2, by + PAD / 2))
        out.append(R("via1", bx - VIA1 / 2, by - VIA1 / 2, bx + VIA1 / 2, by + VIA1 / 2))
        stubs_bot.append((B, bx, by))
    ytop = max(info[devname(t, w, l)]["box"][3] for t, w, l, *_ in devs) + 1.0
    ybot = min(info[devname(t, w, l)]["box"][1] for t, w, l, *_ in devs) - 1.0
    nets_top = sorted({n for n, *_ in stubs_top}); nets_bot = sorted({n for n, *_ in stubs_bot})
    yt = {n: ytop + i * TRACK for i, n in enumerate(nets_top)}
    yb = {n: ybot - i * TRACK for i, n in enumerate(nets_bot)}
    xmin = -1.0 - margin
    xr = x + 1.5                                 # risers beyond the right end
    risers = sorted(set(nets_top) & set(nets_bot))
    xrise = {n: xr + i * TRACK for i, n in enumerate(risers)}
    xmax = xr + len(risers) * TRACK + 0.5
    vias2 = []
    for net, sx, sy in stubs_top:
        y = yt[net]
        out.append(R("metal2", sx - 0.15, sy, sx + 0.15, y + VIA2 / 2))
        out.append(R("metal2", sx - VIA2 / 2 - 0.05, y - VIA2 / 2 - 0.05, sx + VIA2 / 2 + 0.05, y + VIA2 / 2 + 0.05))
        vias2.append((sx, y))
    for net, sx, sy in stubs_bot:
        y = yb[net]
        out.append(R("metal2", sx - 0.15, y - VIA2 / 2, sx + 0.15, sy))
        out.append(R("metal2", sx - VIA2 / 2 - 0.05, y - VIA2 / 2 - 0.05, sx + VIA2 / 2 + 0.05, y + VIA2 / 2 + 0.05))
        vias2.append((sx, y))
    for net, y in list(yt.items()) + list(yb.items()):
        x1 = xrise.get(net, max(sx for n, sx, _ in stubs_top + stubs_bot if n == net)) + 0.3
        if net in ports:
            x1 = xmax                            # port tracks cross the whole cell: reachable from either side
        out.append(R("metal3", xmin, y - TRACKW / 2, x1, y + TRACKW / 2))
    for net, xx in xrise.items():
        out.append(R("metal2", xx - 0.15, yb[net], xx + 0.15, yt[net]))
        for y in (yt[net], yb[net]):
            out.append(R("metal2", xx - VIA2 / 2 - 0.05, y - VIA2 / 2 - 0.05, xx + VIA2 / 2 + 0.05, y + VIA2 / 2 + 0.05))
            vias2.append((xx, y))
    for vx, vy in vias2:                          # contacts last: painting a metal over a contact can erase it
        out.append(R("via2", vx - VIA2 / 2, vy - VIA2 / 2, vx + VIA2 / 2, vy + VIA2 / 2))
    for i, port in enumerate(ports):
        y = yt.get(port, yb.get(port))
        if y is None:
            if not fault:
                raise RuntimeError(f"{name}: port {port} not connected")
            y = ybot - (len(nets_bot) + 1) * TRACK          # the fault left this port unconnected: an isolated pad
            out.append(R("metal3", xmin, y - TRACKW / 2, xmin + 1.0, y + TRACKW / 2))
        out.append(f"box values {xmin:.3f}um {y - TRACKW / 2:.3f}um {xmin + 0.4:.3f}um {y + TRACKW / 2:.3f}um\nlabel {port} c metal3\nport make {i + 1}")
    out.append(f"save {name}")
    ytop_all = max(yt.values()) + TRACKW / 2 + 0.5 if yt else 0
    ybot_all = min(yb.values()) - TRACKW / 2 - 0.5 if yb else 0
    port_y = {pn: round(yt.get(pn, yb.get(pn, 0.0)), 4) for pn in ports}
    return "\n".join(out), dict(width_um=round(xmax - xmin, 2), height_um=round(ytop_all - ybot_all, 2),
                                 bbox=[round(xmin, 4), round(ybot_all, 4), round(xmax, 4), round(ytop_all, 4)], port_y=port_y)


def subckts():
    """Subcircuits of periph.spice: name -> (ports, default parameters, body lines)."""
    out = {}
    for m in re.finditer(r"^\.subckt (\S+)([^\n]*)\n(.*?)^\.ends", SPICE.read_text(), re.S | re.M):
        head = m.group(2).split()
        ports = [h for h in head if "=" not in h]
        pars = dict(h.split("=") for h in head if "=" in h)
        body = [l for l in m.group(3).splitlines() if l.strip() and not l.startswith("*")]
        out[m.group(1)] = (ports, pars, body)
    return out


def subckt_text(name):
    """The cell's subcircuit from periph.spice, flattened to transistors (instances of tg expanded with their sizes),
    used both to generate the layout and as the reference for LVS."""
    sc = subckts()
    def flat(cell, conn, pars, prefix):
        ports, defaults, body = sc[cell]
        p = dict(defaults); p.update(pars)
        m = dict(zip(ports, conn))
        lines = []
        for l in body:
            f = l.split()
            nodes = [x for x in f[1:] if "=" not in x]
            kv = dict(x.split("=") for x in f[1:] if "=" in x)
            kv = {k: str(p.get(v.strip("{}"), v)) if v.startswith("{") else v for k, v in kv.items()}
            model = nodes[-1]; nodes = nodes[:-1]
            nodes = [m.get(n, prefix + n) for n in nodes]
            if model in sc:
                lines += flat(model, nodes, kv, prefix + f[0] + "_")
            else:
                lines.append(f"{prefix}{f[0]} {' '.join(nodes)} {model} " + " ".join(f"{k}={v}" for k, v in kv.items()))
        return lines
    ports = sc[name][0]
    return f".subckt {name} {' '.join(ports)}\n" + "\n".join(flat(name, ports, {}, "")) + "\n.ends"


def run_cell(name):
    spec = cell_spec(name)
    for c in (name, name + "_fault"):            # 'load -force' would read an old copy and paint on top of it
        (WORK / f"{c}.mag").unlink(missing_ok=True)
    tcl, geo = build_cell(name, spec, margin=MARGIN.get(name, 0.0))
    tclf, _ = build_cell(name + "_fault", spec, fault=True, margin=MARGIN.get(name, 0.0))
    log = magic(tcl + "\n" + tclf + f"""
foreach c {{{name} {name}_fault}} {{
  load $c
  select top cell
  drc style drc(full)
  drc check; drc catchup
  puts "DRCCOUNT $c [drc list count total]"
  puts "DRCWHY $c [drc listall why]"
  extract all
  ext2spice lvs
  ext2spice -o $c.spice
}}""", f"{name}.log")
    drc = {m.group(1): int(m.group(2)) for m in re.finditer(r"DRCCOUNT (\S+) (\d+)", log)}
    why = re.findall(r"DRCWHY (\S+) (.*)", log)
    ref = WORK / f"{name}_ref.spice"
    sub = subckt_text(name)
    ref.write_text("* reference\n" + sub + "\n")
    res = {}
    for c in (name, name + "_fault"):
        r = subprocess.run(["netgen", "-batch", "lvs", f"{c}.spice {c}", f"{ref.name} {name}", str(NETGEN_SETUP), f"{c}_lvs.out"],
                           cwd=WORK, capture_output=True, text=True, timeout=600)
        out = (WORK / f"{c}_lvs.out").read_text() if (WORK / f"{c}_lvs.out").exists() else r.stdout
        res[c] = ("Circuits match uniquely" in out and "Final result: Circuits match" in (r.stdout + out)
                  and "property errors" not in (r.stdout + out))      # device sizes must agree as well
    return dict(cell=name, drc_errors=drc.get(name), drc_why=[w for c, w in why if c == name][0][:600] if drc.get(name) else "",
                lvs_match=res[name], fault_lvs_match=res[name + "_fault"], fault_drc=drc.get(name + "_fault"), **geo)


if __name__ == "__main__":
    names = sys.argv[1:] or CELL_NAMES
    devs = set()
    for n in CELL_NAMES:
        devs |= {(t, w, l) for t, w, l, *_ in cell_spec(n)[1]}
    make_devices(devs)
    out = ROOT / "results" / "sky130_chip" / "periph_layout.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    for n in names:
        r = run_cell(n)
        old[n] = r
        print(json.dumps(r), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(old, indent=1))
