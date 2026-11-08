"""Antenna rule, two checkers on the routed chip block (12 October 2026): writes results/sky130_chip/antenna_crosscheck.json.

Magic's check of the whole user area (signoff.py, results/sky130_chip/top_signoff.json) flags four gates, all inside the
digital block. OpenROAD's check of the routed block (flow/eda/pc_batch13_orfs.sh: check_antennas -verbose on 6_final.odb,
LEF rules of the sky130_fd_sc_hd technology LEF) reports 0 violations. For each Magic hit this script finds the gate's
instance (Magic's gate rectangle, minus the block's origin in the user area, against the DEF placements; nearest
instance of the reported cell type) and its input nets, and reads OpenROAD's ratios for that instance pin, so the two
checkers' numbers for the same gate stand side by side.
usage: python3 antenna_crosscheck.py"""
import gzip, json, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# defaults: the final routing; the environment variables select another (the first routing is kept in
# results/sky130_chip/first_routing/, see STATUS.md section 9.7)
DIG = Path(os.environ.get("XC_DEF_DIR", ROOT / "flow" / "orfs" / "outdig" / "results" / "sky130hd" / "tcim_chip_digital" / "base"))
RPT = Path(os.environ.get("XC_RPT", ROOT / "flow" / "eda" / "antenna_openroad_verbose.rpt.gz"))
LOG = Path(os.environ.get("XC_LOG", ROOT / "flow" / "eda" / "antenna_openroad.log"))
SIGNOFF = Path(os.environ.get("XC_SIGNOFF", ROOT / "results" / "sky130_chip" / "top_signoff.json"))
OUT = Path(os.environ.get("XC_OUT", ROOT / "results" / "sky130_chip" / "antenna_crosscheck.json"))
DX, DY = 409.0, 1444.0                       # origin of tcim_chip_digital in the user area (top.py)


def openroad_pins():
    """{(instance, pin): [(ratio / required, layer, kind, ratio, required), ...]} from the verbose report."""
    out = {}
    with gzip.open(RPT, "rt") as f:
        txt = f.read()
    for blk in re.split(r"\n(?=Net: )", txt):
        m = re.match(r"Net: (\S+)", blk)
        if not m:
            continue
        for pin in re.split(r"\n  Pin: ", blk)[1:]:
            pm = re.match(r"\s*(\S+)/(\S+) \((\S+)\)", pin)
            rows = []
            for lay in re.split(r"\n    Layer: ", pin)[1:]:
                ln = lay.split("\n")[0].strip()
                for r, req, kind in re.findall(r"Partial area ratio:\s+([\d.]+)\n\s+Required ratio:\s+([\d.]+) \(([^)]+)\)", lay):
                    if float(req) > 0:
                        rows.append((round(float(r) / float(req), 4), ln, kind, float(r), float(req)))
            out[(pm.group(1), pm.group(2))] = dict(net=m.group(1), cell=pm.group(3), rows=sorted(rows, reverse=True))
    return out


if __name__ == "__main__":
    so = json.loads(SIGNOFF.read_text())
    d = (DIG / "6_final.def").read_text() if (DIG / "6_final.def").exists() else gzip.open(DIG / "6_final.def.gz", "rt").read()
    comps = re.findall(r"- (\S+) (sky130_fd_sc_hd__\S+) \+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \) (\S+)", d)
    orp = openroad_pins()
    log = LOG.read_text()
    res = dict(openroad=dict(net_violations=int(re.search(r"Found (\d+) net violations", log).group(1)),
                             pin_violations=int(re.search(r"Found (\d+) pin violations", log).group(1)),
                             rules="sky130_fd_sc_hd technology LEF: metal side-area ratio 400 (PWL with diode area), via cut-area ratio 6"),
               magic=dict(violations=so["antenna_violation_count"], rules=so["antenna_rules"]), hits=[])
    for v in so["antenna_violations"]:
        typ = re.sub(r"_\d+$", "", v["cell"])
        x0, y0, x1, y1 = v["gate_rect_um"]
        gx, gy = (x0 + x1) / 2 - DX, (y0 + y1) / 2 - DY
        cand = sorted((abs(int(a) / 1000 - gx) + abs(int(b) / 1000 - gy), n) for n, m, a, b, o in comps if m == typ)
        dist, inst = cand[0]
        pins = {p: dict(net=q["net"], openroad_worst=q["rows"][:2]) for (i, p), q in orp.items() if i == inst}
        res["hits"].append(dict(magic=v, instance=inst if dist < 5.0 else None, distance_um=round(dist, 2),
                                openroad_pins=pins if dist < 5.0 else {}))
    OUT.write_text(json.dumps(res, indent=1))
    for h in res["hits"]:
        print(h["magic"]["cell"], h["magic"]["plane"], h["magic"]["ratio"], "->", h["instance"], h["distance_um"],
              {p: (q["net"], q["openroad_worst"][:1]) for p, q in h["openroad_pins"].items()})
    print("OpenROAD:", res["openroad"])
