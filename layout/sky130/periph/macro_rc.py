"""Wiring of the drawn analog macro: resistance and capacitance of every bit line, source line and word line between the
array and its driver, and the circuits simulated again with them (11 October 2026).

R: the routing that macro.py draws between the array edge and each slice is a chain of rectangles joined by vias. The
script rebuilds those shapes (macro.build()), joins touching shapes of a layer and shapes joined by a via into nets
(union-find), finds the net of every array line from where it leaves the array, and sums the squares of its rectangles
times the sheet resistance of their layer plus the resistance of its vias. Summing every rectangle in series over-states
the resistance (pads and overlaps are counted as wire), so the value is an upper bound. Sheet resistances: the
resistclasses of the extraction (poly 48.2, li 12.8, metal1/2 0.125, metal3/4 0.047, metal5 0.029 ohm/sq); contacts: poly
152, li-metal1 9.3, via1 4.5, via2/3 3.41, via4 0.38 ohm per cut (SKY130 typical values).
C: magic's extraction of the whole macro (parasitic capacitance to substrate and coupling between nets, `ext2spice
cthresh 0`, flat), summed per net: the array's own share and the routing outside the array.
Then: the read of a 30 uS / 4.5 uS cell with the worst bit line (periph_sim part D transient with the extracted R and C
instead of 75 ohm / 60 fF), the word-line rise with the worst routed word line added (part B), and the programming ladders
with the worst bit-line and source-line resistance in series (macro_sim.py with RBL / RSL).
Writes results/sky130_chip/macro_rc.json (and macro_sim_rc.json through macro_sim.py)."""
import json, os, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen    # noqa: E402
import macro  # noqa: E402

ROOT = gen.ROOT
OUT = ROOT / "results" / "sky130_chip" / "macro_rc.json"
RS = {"poly": 48.2, "locali": 12.8, "metal1": 0.125, "metal2": 0.125, "metal3": 0.047, "metal4": 0.047, "metal5": 0.029}
VIA = {"polycont": ("poly", "locali", 152.0), "viali": ("locali", "metal1", 9.3), "via1": ("metal1", "metal2", 4.5), "via2": ("metal2", "metal3", 3.41), "via3": ("metal3", "metal4", 3.41),
       "via4": ("metal4", "metal5", 0.38)}
ROWS, COLS, CW, CH = 72, 24, 3.6, 3.0
RX = re.compile(r"box values (\S+)um (\S+)um (\S+)um (\S+)um\npaint (\S+)")


def shapes(W):
    out = []
    for s in W.m + W.v:
        m = RX.match(s)
        x0, y0, x1, y1, lay = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)
        out.append((lay, x0, y0, x1, y1))
    return out


def nets(sh):
    par = list(range(len(sh)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            par[a] = b
    grid = defaultdict(list)                        # (layer, gx, gy) -> shape indices; metal layers only
    G = 5.0
    def cells(x0, y0, x1, y1):
        for gx in range(int(x0 // G), int(x1 // G) + 1):
            for gy in range(int(y0 // G), int(y1 // G) + 1):
                yield gx, gy
    for i, (lay, x0, y0, x1, y1) in enumerate(sh):
        if lay in RS:
            for g in cells(x0, y0, x1, y1):
                grid[(lay, *g)].append(i)
    touch = lambda a, b: a[1] <= b[3] and b[1] <= a[3] and a[2] <= b[4] and b[2] <= a[4]
    for i, s in enumerate(sh):
        if s[0] not in RS and s[0] not in VIA:          # diode diffusion and its contact: not routing
            continue
        lays = [s[0]] if s[0] in RS else list(VIA[s[0]][:2])
        for lay in lays:
            for g in cells(*s[1:]):
                for j in grid[(lay, *g)]:
                    if j != i and touch(s, sh[j]):
                        union(i, j)
    groups = defaultdict(list)
    for i in range(len(sh)):
        groups[find(i)].append(i)
    return groups, find


def resistance(sh, idx):
    r = 0.0
    for i in idx:
        lay, x0, y0, x1, y1 = sh[i]
        if lay in RS:
            w, l = sorted((x1 - x0, y1 - y0))
            r += RS[lay] * l / max(w, 1e-3)
        elif lay in VIA:
            r += VIA[lay][2]
    return r


def line_nets(sh, groups, find):
    """Net of each array line: the routing shape that starts at the line's exit on the array edge (macro.py: bit and
    source lines leave the bottom edge at x = 3.6 c + 0.80 / 1.80 / 2.80, word lines the right edge at y = 3.0 r + 1.2)."""
    found = {}
    for c in range(COLS):
        for name, xo, lays in ((f"BLP{c}", 0.80, ("metal2",)), (f"SL{c}", 1.80, ("metal1",)), (f"BLN{c}", 2.80, ("metal2",))):
            x = c * CW + xo
            cand = [i for i, (lay, x0, y0, x1, y1) in enumerate(sh)
                    if lay in lays and abs((x0 + x1) / 2 - x) < 0.01 and abs(y1 - 0.05) < 0.01]
            found[name] = find(cand[0]) if len(cand) == 1 else None
    for r in range(ROWS):
        y = r * CH + 1.2
        cand = [i for i, (lay, x0, y0, x1, y1) in enumerate(sh)
                if lay == "poly" and abs(x0 - 86.3) < 0.01 and abs((y0 + y1) / 2 - y) < 0.01]
        found[f"WL{r}"] = find(cand[0]) if len(cand) == 1 else None
    return found


UNIT = {"": 1.0, "f": 1e-15, "a": 1e-18, "p": 1e-12, "n": 1e-9}


def label_points():
    """A point on the routed wire of every array line (macro coordinates, layer), outside the array."""
    pts = {}
    for c in range(COLS):
        pts[f"BLP{c}"] = (c * CW + 0.80, -1.5, "metal2")
        pts[f"BLN{c}"] = (c * CW + 2.80, -1.5, "metal2")
        pts[f"SL{c}"] = (c * CW + 1.80, -2.0, "metal2")
    for r in range(ROWS):
        pts[f"WL{r}"] = (88.2, r * CH + 1.2, "metal2")
    return pts


def flat_caps(cell, labels, d):
    """Flat extraction of `cell` (copied .mag files in folder d) with extra labels at the given points; returns the total
    capacitance (F) of every net: to substrate plus every coupling capacitance to another net."""
    tcl = [f"load {cell}", "snap internal"]
    for name, (x, y, lay) in labels.items():
        tcl.append(f"box values {x:.3f}um {y:.3f}um {x:.3f}um {y:.3f}um\nlabel {name}_X 0 {lay}")
    tcl += ["extract do capacitance", "extract do coupling", "extract all", "ext2spice hierarchy off", "ext2spice format ngspice",
            "ext2spice cthresh 0", f"ext2spice -o {cell}_cap.spice", "quit -noprompt"]
    (d / "cap.tcl").write_text("\n".join(tcl) + "\n")
    r = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(gen.RC), "cap.tcl"], cwd=d, capture_output=True,
                       text=True, timeout=7200, stdin=subprocess.DEVNULL)
    (d / f"{cell}_cap.log").write_text(r.stdout + r.stderr)
    tot = defaultdict(float)
    for line in (d / f"{cell}_cap.spice").read_text().splitlines():
        m = re.match(r"^C\S*\s+(\S+)\s+(\S+)\s+([0-9.eE+-]+)([a-zA-Z]?)", line)
        if m:
            v = float(m.group(3)) * UNIT.get(m.group(4).lower()[:1] if m.group(4) else "", 1.0)
            for n in (m.group(1), m.group(2)):
                tot[n] += v
    return tot


def pick(tot, names, suffix):
    out = {}
    for name in names:
        hits = [k for k in tot if k == f"{name}{suffix}" or k.endswith(f"/{name}{suffix}")]
        out[name] = tot[hits[0]] if hits else None
    return out


def caps():
    import shutil, tempfile
    d = Path(tempfile.mkdtemp(prefix="macro_rc_"))
    for f in gen.WORK.glob("*.mag"):
        shutil.copy(f, d / f.name)
    lab = label_points()
    whole = pick(flat_caps("tcim_macro", lab, d), lab, "_X")
    arr = pick(flat_caps("tcim_sky130_array", {}, d), lab, "")          # the array's own port names
    return whole, arr, str(d)


if __name__ == "__main__":
    place, W, labels, info = macro.build()
    sh = shapes(W)
    groups, find = nets(sh)
    ln = line_nets(sh, groups, find)
    res = {}
    for name, g in ln.items():
        if g is None:
            res[name] = None
            continue
        idx = groups[g]
        res[name] = dict(R_ohm=round(resistance(sh, idx), 1), shapes=len(idx))
    missing = [k for k, v in res.items() if v is None]
    summ = {}
    for kind in ("BLP", "BLN", "SL", "WL"):
        rs = [v["R_ohm"] for k, v in res.items() if re.fullmatch(kind + r"\d+", k) and v]
        summ[kind] = dict(n=len(rs), R_max_ohm=max(rs) if rs else None, R_min_ohm=min(rs) if rs else None)
    print(json.dumps(dict(summary=summ, missing=missing), indent=1))
    d = json.loads(OUT.read_text()) if OUT.exists() else {}
    d.update(routing_R=dict(summary=summ, missing=missing, lines=res))
    if "R" not in sys.argv[1:]:
        whole, arr, folder = caps()
        cl = {k: dict(C_total_fF=None if whole[k] is None else round(whole[k] * 1e15, 2),
                      C_array_fF=None if arr[k] is None else round(arr[k] * 1e15, 2)) for k in whole}
        bad = [k for k, v in cl.items() if v["C_total_fF"] is None or v["C_array_fF"] is None]
        d["routing_C"] = dict(lines=cl, missing=bad, folder=folder)
        bl = [k for k in cl if k.startswith("BL") and k not in bad]
        wl = [k for k in cl if k.startswith("WL") and k not in bad]
        kb = max(bl, key=lambda k: cl[k]["C_total_fF"]); kw = max(wl, key=lambda k: cl[k]["C_total_fF"])
        rbl = max(v["R_ohm"] for k, v in res.items() if k.startswith("BL"))
        rsl = max(v["R_ohm"] for k, v in res.items() if k.startswith("SL"))
        rwl = max(v["R_ohm"] for k, v in res.items() if k.startswith("WL"))
        mc_set = json.loads((ROOT / "results" / "sky130_chip" / "periph_sim.json").read_text())["D"]["mc set"]["max_uS"]
        try:
            mc_set = max(mc_set, json.loads((ROOT / "results" / "sky130_chip" / "mc_libcheck.json").read_text())["set"]["full_max_uS"])
        except (FileNotFoundError, KeyError):
            pass
        d["worst_case"] = dict(
            note="longest routed lines and the largest line capacitance; the array's own 75 / 40 ohm added to the routing",
            R_bitline_ohm=round(75 + rbl, 1), R_sourceline_ohm=round(40 + rsl, 1), R_wordline_route_ohm=rwl,
            C_bitline_array_F=cl[kb]["C_array_fF"] * 1e-15, C_bitline_route_F=(cl[kb]["C_total_fF"] - cl[kb]["C_array_fF"]) * 1e-15,
            C_bitline_line=kb, C_wordline_route_F=(cl[kw]["C_total_fF"] - cl[kw]["C_array_fF"]) * 1e-15, C_wordline_array_F=cl[kw]["C_array_fF"] * 1e-15,
            C_wordline_line=kw,
            set_target_uS=mc_set)
        print(json.dumps(d["worst_case"], indent=1), "missing C:", bad)
    OUT.write_text(json.dumps(d, indent=1))
