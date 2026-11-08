"""Layout of the forming switch (circuits/gnucap/forming.py, part A) in IHP SG13G2, drawn by script (10 October 2026).

Cell tcim_form: the floating-rail level shifter, the two stacked PMOS of the switch with the mid-node clamp, the
stacked bit-line pull-down and the stacked column switch, with the sizes of circuits/gnucap/forming.py (NMOS
L = 0.6 um and PMOS L = 0.5 um: the lengths for which the process specification states VGS <= 3.3 V).
Ports: en, enb, dis (control, 0 / 3.0 V), vcas (cascode gates, 3.0 V), vmuxa, vmuxb (column-switch gates),
vform (forming supply, up to 5 V), vmid (VFORM - 3.0 V), bl, blsa, vss.

Same style and helpers as layout/periphery_layout.py: one row of transistors, a Metal2 track per net. The PMOS sit
in four separate n-wells, each tied to the device's own source as the circuit requires (vform; ya; yb; the switch
mid node m), at the HV n-well spacing NW.b1 (1.8 um) from one another. All devices are in one ThickGateOx region.
Checked on the PC with the PDK's KLayout DRC and LVS (layout/ihp_checks.sh). Writes layout/tcim_form.gds,
layout/tcim_form.cdl and adds the cell to results/forming_layout.json."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import periphery_layout as P                      # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "circuits" / "gnucap"))

ROOT = Path(__file__).resolve().parents[1]
GDS, CDL = ROOT / "layout" / "tcim_form.gds", ROOT / "layout" / "tcim_form.cdl"
LN, LP = 600, 500
PORTS = ["en", "enb", "dis", "vcas", "vmuxa", "vmuxb", "vform", "vmid", "bl", "blsa", "vss"]


def forming_cell():
    c = P.Cell("tcim_form")
    x = 1000
    t_p = P.tie(c, x, "p", "vss"); x = t_p["x1"] + 500
    nm = []
    # NMOS (body: substrate = vss). (name, drain, gate, source, total W in nm, fingers)
    for name, d, g, s, w, nf in (("na1", "a1", "en", "vss", 2000, 1), ("na2", "xa", "vcas", "a1", 2000, 1),
                                 ("nb1", "b1", "enb", "vss", 2000, 1), ("nb2", "xb", "vcas", "b1", 2000, 1),
                                 ("nd1", "vss", "dis", "d1", 10000, 2), ("nd2", "d1", "vcas", "bl", 10000, 2),
                                 ("nma", "bl", "vmuxa", "ca", 10000, 2), ("nmb", "ca", "vmuxb", "blsa", 10000, 2)):
        dv = P.mos(c, x, w // nf, LN, nf, "n", True, d, g, s); dv["name"] = name; dv["b"] = "vss"
        nm.append(dv); x = dv["x1"] + P.DEV_GAP
    x += 620 + 620 + P.PSD_ENC
    pm, ties, wells = [], [t_p], []
    groups = (("vform", (("pa1", "ya", "yb", "vform", 1000, 1), ("pb1", "yb", "ya", "vform", 1000, 1),
                         ("ps1", "m", "ya", "vform", 20000, 2))),
              ("ya", (("pa2", "xa", "vmid", "ya", 4000, 1),)),
              ("yb", (("pb2", "xb", "vmid", "yb", 4000, 1),)),
              ("m", (("ps2", "bl", "vmid", "m", 20000, 2), ("pc", "vmid", "yb", "m", 1000, 1))))
    for body, devs in groups:
        grp = []
        for name, d, g, s, w, nf in devs:
            dv = P.mos(c, x, w // nf, LP, nf, "p", True, d, g, s); dv["name"] = name; dv["b"] = body
            grp.append(dv); x = dv["x1"] + P.DEV_GAP + 2 * P.PSD_ENC
        tn = P.tie(c, grp[-1]["x1"] + P.PSD_ENC + 300, "n", body)
        P.psd_box(c, grp)
        nw = P.nwell_box(c, grp, [tn], P.NW_ENC_HV)
        wells.append(nw); pm += grp; ties.append(tn)
        x = P.snap(nw[1] + 1800 + P.NW_ENC_HV + P.PSD_ENC)        # NW.b1 1.8 um to the next well
    devs = nm + pm
    r = P.route(c, devs, ties, PORTS, wells[-1][1])
    ylo = min(r["y_low"].values()) - 1000
    yhi = max(r["y_high"].values()) + 1000
    c.box(P.TGO, 0, ylo, P.snap(max(r["x_risers_end"], wells[-1][1]) + 1000), yhi)
    return c, devs


def cdl(name, devs, ports):
    lines = [f".SUBCKT {name} {' '.join(ports)}"]
    for k, d in enumerate(devs):
        model = f"sg13_hv_{d['kind']}mos"
        lines.append(f"M{k} {d['d']} {d['g']} {d['s']} {d['b']} {model} w={d['w'] * d['nf'] / 1000:g}u l={d['l'] / 1000:g}u ng={d['nf']} m=1")
    lines.append(f".ENDS {name}")
    return "\n".join(lines)


if __name__ == "__main__":
    c, devs = forming_cell()
    errs = P.self_check(c)
    print("self-check:", "clean" if not errs else errs)
    xs = [s[1] for s in c.shapes] + [s[3] for s in c.shapes]
    ys = [s[2] for s in c.shapes] + [s[4] for s in c.shapes]
    P.write_gds(GDS, [c])
    CDL.write_text("* schematic netlist of layout/tcim_form.gds (circuits/gnucap/forming.py, part A)\n" + cdl(c.name, devs, PORTS) + "\n")
    res = dict(gds=str(GDS.relative_to(ROOT)), cdl=str(CDL.relative_to(ROOT)), cell=c.name, ports=PORTS,
               transistors=cdl(c.name, devs, PORTS).splitlines()[1:-1], shapes=len(c.shapes),
               width_um=(max(xs) - min(xs)) / 1000, height_um=(max(ys) - min(ys)) / 1000,
               area_um2=round((max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6, 1), self_check_errors=errs)
    (ROOT / "results" / "forming_layout.json").write_text(json.dumps(res, indent=1))
    print({k: v for k, v in res.items() if k != "transistors"})
