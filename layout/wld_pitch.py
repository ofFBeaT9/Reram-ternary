"""Pitch-matched word-line driver column for the 72-row TCIM0 array in IHP SG13G2 (10 October 2026).

The drawn 2T2R array (layout/cell_2t2r.py) has two rows per 2.17 um (two rows mirrored about a shared source).
The driver column repeats the same idea: one slice of 2.17 um holds the drivers of two rows, NMOS 6/0.45 um and
PMOS 12/0.45 um each (the sizes of circuits/gnucap/periphery.py, which met the word-line timing at all corners),
with the transistor width along x and the two rows of a slice mirrored about a shared source strip:
    y:  drain (row 2j) | gate 2j | shared source (vss / vr) | gate 2j+1 | drain (row 2j+1)
Each gate is one horizontal GatPoly line through the NMOS and the PMOS of its row, contacted at its left end and
fed by a Metal2 input line from the left (decoder side). The two drains of a row are joined by a Metal1 line that
continues to the right edge, where the word line of the array starts. vss and vr are vertical Metal2 rails over the
NMOS and the PMOS, joined to the source strips; substrate and n-well ties are vertical Activ columns at the left
and right, contacted once per slice at the source height (LU.a / LU.b: every device within 20 um of a tie).
36 slices (72 rows), all in ThickGateOx. Ports: in<k>, out<k> (k = 0..71), vss, vr.
Writes layout/tcim_wld72.gds, layout/tcim_wld72.cdl, results/wld_pitch.json. All coordinates in nm."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import periphery_layout as P                     # noqa: E402
from cell_2t2r import PAIR_PITCH                  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GDS, CDL = ROOT / "layout" / "tcim_wld72.gds", ROOT / "layout" / "tcim_wld72.cdl"
M1_TEXT = (8, 25)
H = PAIR_PITCH                                    # 2170
N_SLICES = 36
WN, WP, L = 6000, 12000, 450
# y inside a slice (Activ 1960 tall, 105 margin each side -> 210 Activ spacing to the next slice: Act.b)
Y_ACT0 = 105
Y_G0 = Y_ACT0 + 340                               # gate 2j: 445 .. 895
Y_S0 = Y_G0 + L                                   # shared source: 895 .. 1275
Y_G1 = Y_S0 + 380                                 # gate 2j+1: 1275 .. 1725
Y_D1 = Y_G1 + L                                   # drain 2j+1: 1725 .. 2065
Y_ACT1 = Y_D1 + 340
X_TIEP, X_N, X_P = 0, 2500, 9800                  # p-tie column, NMOS Activ, PMOS Activ
X_PAD = X_N - P.CNT_POLY_ACT - P.CNT              # poly contact (Cnt.e from Activ)
X_RAIL_N, X_RAIL_P = 4000, 10500                  # vertical Metal2 rails, 600 wide
X_TIEN = X_P + WP + P.PSD_ENC + 300               # n-tie column
X_OUT = X_TIEN + P.TIE_W + 620 + 400              # right end of the output lines (outside the n-well)
X_IN = -600                                       # left end of the input lines


def contacts_x(c, x0, x1, yc, net):
    """A row of contacts along x between Activ edges x0, x1 (Cnt.c), centred at height yc."""
    n = max(1, (x1 - x0 - 2 * P.CNT_ACT + P.CNT_SP) // (P.CNT + P.CNT_SP))
    span = n * P.CNT + (n - 1) * P.CNT_SP
    s = P.snap(x0 + (x1 - x0 - span) / 2)
    for k in range(n):
        xx = s + k * (P.CNT + P.CNT_SP)
        c.box(P.CONT, xx, yc - P.CNT // 2, xx + P.CNT, yc + P.CNT // 2, net)
    return s, s + span


def slice_(c, j, y0, devs):
    r0, r1 = 2 * j, 2 * j + 1
    yd0 = y0 + Y_ACT0 + P.CNT_ACT + P.CNT // 2     # drain contact centres (Cnt.c from the Activ edge,
    yd1 = y0 + Y_ACT1 - P.CNT_ACT - P.CNT // 2     # Cnt.f 110 from the gate)
    ys = y0 + (Y_S0 + Y_G1) // 2                   # source contact centre
    yg = (y0 + (Y_G0 + Y_S0) // 2, y0 + (Y_G1 + Y_D1) // 2)
    for x0, w, src, kind in ((X_N, WN, "vss", "n"), (X_P, WP, "vr", "p")):
        c.box(P.ACTIV, x0, y0 + Y_ACT0, x0 + w, y0 + Y_ACT1)
        contacts_x(c, x0, x0 + w, yd0, f"out{r0}")
        contacts_x(c, x0, x0 + w, yd1, f"out{r1}")
        a, b = contacts_x(c, x0, x0 + w, ys, src)
        c.box(P.METAL1, a - 50, ys - 130, b + 50, ys + 130, src)              # source strip (M1.c1 end caps)
        xr = X_RAIL_N if kind == "n" else X_RAIL_P
        c.box(P.VIA1, xr + 300 - P.V // 2, ys - P.V // 2, xr + 300 + P.V // 2, ys + P.V // 2, src)
        devs.append(dict(kind=kind, d=f"out{r0}", g=f"in{r0}", s=src, w=w))
        devs.append(dict(kind=kind, d=f"out{r1}", g=f"in{r1}", s=src, w=w))
    for r, yd in ((r0, yd0), (r1, yd1)):          # output line: NMOS drain -> PMOS drain -> right edge
        c.box(P.METAL1, X_N + P.CNT_ACT - 50, yd - 130, X_OUT, yd + 130, f"out{r}")
        c.text(M1_TEXT, X_OUT - 200, yd, f"out{r}")
    for r, (gy0, gy1), ygc in ((r0, (Y_G0, Y_S0), yg[0]), (r1, (Y_G1, Y_D1), yg[1])):
        c.box(P.GATPOLY, X_PAD - P.POLY_ENC, y0 + gy0, X_P + WP + P.POLY_END, y0 + gy1, f"in{r}")
        c.box(P.CONT, X_PAD, ygc - P.CNT // 2, X_PAD + P.CNT, ygc + P.CNT // 2, f"in{r}")
        xc = X_PAD + P.CNT // 2
        c.box(P.METAL1, xc - 150, ygc - 155, xc + 150, ygc + 155, f"in{r}")    # 300 x 310: M1.d area 0.093 um2
        c.box(P.VIA1, xc - P.V // 2, ygc - P.V // 2, xc + P.V // 2, ygc + P.V // 2, f"in{r}")
        c.box(P.METAL2, X_IN, ygc - 100, xc + P.V // 2 + 50, ygc + 100, f"in{r}")
        c.text(P.M2_TEXT, X_IN + 100, ygc, f"in{r}")
    # ties: contacted once per slice at the source height; Metal1 pad, Via1, Metal2 connector to the rail
    for xt, net, xr in ((X_TIEP, "vss", X_RAIL_N), (X_TIEN, "vr", X_RAIL_P)):
        xc = xt + P.TIE_W // 2
        c.box(P.CONT, xc - P.CNT // 2, ys - P.CNT // 2, xc + P.CNT // 2, ys + P.CNT // 2, net)
        c.box(P.METAL1, xc - 155, ys - 155, xc + 155, ys + 155, net)                  # M1.d area >= 0.09 um2
        c.box(P.VIA1, xc - P.V // 2, ys - P.V // 2, xc + P.V // 2, ys + P.V // 2, net)
        lo, hi = sorted((xc, xr + 300))
        c.box(P.METAL2, lo - P.V // 2 - 50, ys - 100, hi + P.V // 2 + 50, ys + 100, net)


def column(n=N_SLICES, name="tcim_wld72"):
    c = P.Cell(name)
    devs = []
    for j in range(n):
        slice_(c, j, j * H, devs)
    top = n * H
    for xt, net in ((X_TIEP, "vss"), (X_TIEN, "vr")):                        # tie Activ columns
        c.box(P.ACTIV, xt, Y_ACT0, xt + P.TIE_W, top - Y_ACT0, net)
    c.box(P.PSD, X_TIEP - 180, Y_ACT0 - 180, X_TIEP + P.TIE_W + 180, top - Y_ACT0 + 180)
    c.box(P.PSD, X_P - P.PSD_ENC, Y_ACT0 - P.PSD_ENC, X_P + WP + P.PSD_ENC, top - Y_ACT0 + P.PSD_ENC)
    c.box(P.NWELL, X_P - 620, Y_ACT0 - 620, X_TIEN + P.TIE_W + 620, top - Y_ACT0 + 620)
    for xr, net in ((X_RAIL_N, "vss"), (X_RAIL_P, "vr")):                    # vertical rails
        c.box(P.METAL2, xr, 0, xr + 600, top, net)
        c.text(P.M2_TEXT, xr + 300, top - 300, net)
    c.box(P.TGO, X_IN - 1000, -1000, X_OUT + 1000, top + 1000)
    return c, devs


def cdl(name, devs, ports):
    lines = [f".SUBCKT {name} " + " ".join(ports[:16])] + ["+ " + " ".join(ports[i:i + 16]) for i in range(16, len(ports), 16)]
    for k, d in enumerate(devs):
        b = "vss" if d["kind"] == "n" else "vr"
        lines.append(f"M{k} {d['d']} {d['g']} {d['s']} {b} sg13_hv_{d['kind']}mos w={d['w'] / 1000:g}u l={L / 1000:g}u ng=1 m=1")
    lines.append(f".ENDS {name}")
    return "\n".join(lines)


if __name__ == "__main__":
    c, devs = column()
    ports = [f"in{k}" for k in range(2 * N_SLICES)] + [f"out{k}" for k in range(2 * N_SLICES)] + ["vss", "vr"]
    # connectivity self-check on a two-slice column (the slices repeat; the check is quadratic in the shape count)
    small, _ = column(2, "check")
    errs = P.self_check(small)
    print("self-check (two slices):", "clean" if not errs else errs[:10])
    P.write_gds(GDS, [c])
    CDL.write_text("* schematic netlist of layout/tcim_wld72.gds: 72 word-line drivers\n" + cdl(c.name, devs, ports) + "\n")
    xs = [s[1] for s in c.shapes] + [s[3] for s in c.shapes]
    res = dict(gds=str(GDS.relative_to(ROOT)), cdl=str(CDL.relative_to(ROOT)), cell=c.name, rows=2 * N_SLICES,
               slice_height_um=H / 1000, row_pitch_um=H / 2000, column_height_um=N_SLICES * H / 1000,
               width_um=(max(xs) - min(xs)) / 1000, nmos=f"{WN / 1000:g}/{L / 1000:g} um", pmos=f"{WP / 1000:g}/{L / 1000:g} um",
               transistors=len(devs), shapes=len(c.shapes), self_check_errors_two_slices=errs)
    (ROOT / "results" / "wld_pitch.json").write_text(json.dumps(res, indent=1))
    print(res)
