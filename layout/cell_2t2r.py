"""Layout of the transistor part of the 2T2R array in IHP SG13G2, drawn by script (8 October 2026).

What is drawn (a 4-row x 2-column-pair block, i.e. 4 x 2 ternary cells = 16 select transistors):
- 3.3 V NMOS select transistors, W = 4.5 um, L = 0.45 um (ThickGateOx), as sized in roadmap section 18.3.
- Word lines are GatPoly lines along a row, contacted at the left end. Two rows share one source diffusion and are
  mirrored about it (the arrangement model/cell_footprint.py assumed).
- Source line: one per column pair (tile model, roadmap 18.3), Metal2, running along the column; the source strip
  in Metal1 joins the two transistors of a pair; 4 Via1 per source strip (0.4 mA each: 1.6 mA >= 1.2 mA).
- Drain: 13 contacts, Metal1, 3 Via1, Metal2 landing pad, 3 Via2, Metal3 bit line along the column.
  THE Via2 STACK MARKS WHERE THE ReRAM ELEMENT GOES. The open PDK has no MEMRES layers, so the element, its
  rules and the metal levels it sits between are NOT drawn. The foundry cell replaces this stack.
- Substrate ties (p+ Activ in pSD, contacts, Metal1) below and above the block for the latch-up rule.

Checked with the PDK's own KLayout DRC deck (libs.tech/klayout/tech/drc/run_drc.py, density excluded because a
block this small cannot meet fill density). Writes layout/tcim_2t2r_block.gds and results/cell_layout.json.
All coordinates are integers in nm on the 5 nm grid."""
import json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GDS = ROOT / "layout" / "tcim_2t2r_block.gds"

# layers (layer, datatype) from libs.tech/klayout/tech/drc/rule_decks/layers_def.drc
ACTIV, GATPOLY, CONT, METAL1, VIA1, METAL2, VIA2, METAL3, PSD, TGO = (1, 0), (5, 0), (6, 0), (8, 0), (19, 0), (10, 0), (29, 0), (30, 0), (14, 0), (44, 0)

# rule values (um -> nm) from rule_decks/sg13g2_tech_default.json; names as in the deck
W, L = 4500, 450               # transistor width (design choice), Gat.a3 = 0.45 (3.3 V NMOS minimum length)
ACT_SP = 210                   # Act.b (between row pairs, along the bit line)
DEV_SP = 250                   # along the word line: Gat.b1 = 0.25 (unrelated 3.3 V gates over Activ); Act.b alone (0.21) fails
CNT, CNT_SP, CNT_ACT, CNT_GATE = 160, 180, 70, 110   # Cnt.a, Cnt.b, Cnt.c, Cnt.f
CNT_POLY_ACT = 240             # Cnt.e = 0.14 minimum; 0.24 used to keep the gate pad's Metal1 away
POLY_ENC_CNT, POLY_END = 70, 180   # Cnt.d, Gat.c
M1_END, V_END = 50, 50         # M1.c1, V1.c1 / Vn.c1 endcap enclosures
V, V_SP = 190, 220             # V1.a, V1.b (and Vn.a, Vn.b for Via2)
TGO_MARGIN = 500               # >= TGO.a 0.27 (over Activ), TGO.c 0.34 (over GatPoly)

H_ACT = 2 * (CNT_ACT + CNT + CNT_GATE) + 2 * L + (CNT_GATE + CNT + CNT_GATE)   # 1960: drain, gate, source, gate, drain
PAIR_PITCH = H_ACT + ACT_SP          # two rows
DEV_PITCH = W + DEV_SP               # along the word line
ROW_PAIRS, COL_PAIRS = 2, 2

shapes = []


def box(layer, x0, y0, x1, y1):
    assert x1 > x0 and y1 > y0
    for v in (x0, y0, x1, y1):
        assert v % 5 == 0, ("off grid", layer, x0, y0, x1, y1)
    shapes.append((layer, int(x0), int(y0), int(x1), int(y1)))


def via_row(layer, xc, yc, n):
    """n vias of size V in a row along x centred at (xc, yc); returns the x extent."""
    span = n * V + (n - 1) * V_SP
    x = xc - span // 2
    for k in range(n):
        box(layer, x + k * (V + V_SP), yc - V // 2, x + k * (V + V_SP) + V, yc + V // 2)
    return xc - span // 2, xc + span // 2


def contacts(x0, x1, yc):
    """As many contacts as fit in Activ [x0, x1] at height yc, centred; returns the outer contact extent."""
    n = (x1 - x0 - 2 * CNT_ACT + CNT_SP) // (CNT + CNT_SP)
    span = n * CNT + (n - 1) * CNT_SP
    s = x0 + ((x1 - x0) - span) // 2
    s -= s % 5
    for k in range(n):
        box(CONT, s + k * (CNT + CNT_SP), yc - CNT // 2, s + k * (CNT + CNT_SP) + CNT, yc + CNT // 2)
    return s, s + span, n


def draw():
    y_cnt = dict(dA=CNT_ACT + CNT // 2, gA=CNT_ACT + CNT + CNT_GATE + L // 2,
                 s=CNT_ACT + CNT + CNT_GATE + L + CNT_GATE + CNT // 2,
                 gB=H_ACT - (CNT_ACT + CNT + CNT_GATE + L // 2), dB=H_ACT - CNT_ACT - CNT // 2)
    n_dev = 2 * COL_PAIRS
    x_last = (n_dev - 1) * DEV_PITCH + W
    m1h = V + 2 * 10                         # Metal1 strip height where a Via1 lands (V1.c = 0.01 each side)
    n_cnt = None
    for p in range(ROW_PAIRS):
        y0 = p * PAIR_PITCH
        # word lines: one GatPoly line per row, contacted at the left end
        for g in ("gA", "gB"):
            yc = y0 + y_cnt[g]
            cx1 = -CNT_POLY_ACT
            cx0 = cx1 - CNT
            box(GATPOLY, cx0 - POLY_ENC_CNT, yc - L // 2, x_last + POLY_END, yc + L // 2)
            box(CONT, cx0, yc - CNT // 2, cx1, yc + CNT // 2)
            box(METAL1, cx0 - M1_END, yc - 175, cx1 + M1_END, yc + 175)        # 0.26 x 0.35 um >= M1.d 0.09 um2
        for cp in range(COL_PAIRS):
            xa = cp * 2 * DEV_PITCH                       # left device of the pair
            xb = xa + DEV_PITCH                           # right device
            for x in (xa, xb):
                box(ACTIV, x, y0, x + W, y0 + H_ACT)
                for d in ("dA", "s", "dB"):
                    c0, c1, n_cnt = contacts(x, x + W, y0 + y_cnt[d])
                    if d != "s":
                        box(METAL1, c0 - M1_END, y0 + y_cnt[d] - m1h // 2, c1 + M1_END, y0 + y_cnt[d] + m1h // 2)
            # source strip joins both transistors of the pair; source line in Metal2 at the pair centre
            xs0 = xa + 130 - M1_END
            xs1 = xb + W - 130 + M1_END
            ys = y0 + y_cnt["s"]
            box(METAL1, xs0, ys - m1h // 2, xs1, ys + m1h // 2)
            xc_sl = xa + W + DEV_SP // 2 - ((xa + W + DEV_SP // 2) % 5)
            v0, v1 = via_row(VIA1, xc_sl, ys, 4)
            if p == 0:
                box(METAL2, v0 - V_END, -TGO_MARGIN, v1 + V_END, ROW_PAIRS * PAIR_PITCH - ACT_SP + TGO_MARGIN)
            # drains: Via1 x3 -> Metal2 pad -> Via2 x3 (ReRAM placeholder) -> Metal3 bit line
            for x, xbl in ((xa, xa + 2055), (xb, xb + W - 2055)):
                xbl -= xbl % 5
                for d in ("dA", "dB"):
                    yd = y0 + y_cnt[d]
                    u0, u1 = via_row(VIA1, xbl, yd, 3)
                    via_row(VIA2, xbl, yd, 3)
                    box(METAL2, u0 - V_END, yd - V // 2 - V_END, u1 + V_END, yd + V // 2 + V_END)
                if p == 0:
                    box(METAL3, u0 - V_END, -TGO_MARGIN, u1 + V_END, ROW_PAIRS * PAIR_PITCH - ACT_SP + TGO_MARGIN)
    y_top = ROW_PAIRS * PAIR_PITCH - ACT_SP
    x_left = -CNT_POLY_ACT - CNT - POLY_ENC_CNT
    box(TGO, x_left - TGO_MARGIN, -TGO_MARGIN, x_last + POLY_END + TGO_MARGIN, y_top + TGO_MARGIN)
    # substrate ties below and above
    tie = []
    for yc in (-TGO_MARGIN - 1000, y_top + TGO_MARGIN + 1000):
        a0, a1 = x_left, x_last
        box(ACTIV, a0, yc - 180, a1, yc + 180)
        box(PSD, a0 - 300, yc - 480, a1 + 300, yc + 480)
        c0, c1, _ = contacts(a0, a1, yc)
        box(METAL1, c0 - M1_END, yc - 105, c1 + M1_END, yc + 105)
        tie.append(yc)
    return dict(n_contacts_per_terminal=n_cnt, x_extent_nm=(x_left - TGO_MARGIN, x_last + POLY_END + TGO_MARGIN),
                y_extent_nm=(-TGO_MARGIN - 1000 - 480, y_top + TGO_MARGIN + 1000 + 480), tie_rows_nm=tie)


# ---------------------------------------------------------------- minimal GDSII writer (boundaries only)
def _rec(rt, dt, data=b""):
    return struct.pack(">HBB", 4 + len(data), rt, dt) + data


def _real8(x):
    if x == 0:
        return b"\0" * 8
    e = 64
    while x < 1 / 16:
        x *= 16; e -= 1
    while x >= 1:
        x /= 16; e += 1
    m = int(round(x * 2 ** 56))
    return struct.pack(">Q", (e << 56) | m)


def write_gds(path, cell="tcim_2t2r_block"):
    ts = struct.pack(">12h", 2026, 10, 8, 0, 0, 0, 2026, 10, 8, 0, 0, 0)
    out = _rec(0x00, 0x02, struct.pack(">h", 600)) + _rec(0x01, 0x02, ts)
    lib = b"TCIM"
    out += _rec(0x02, 0x06, lib) + _rec(0x03, 0x05, _real8(1e-3) + _real8(1e-9))
    out += _rec(0x05, 0x02, ts)
    nm = cell.encode()
    nm += b"\0" * (len(nm) % 2)
    out += _rec(0x06, 0x06, nm)
    for (ly, dt), x0, y0, x1, y1 in shapes:
        out += _rec(0x08, 0x00) + _rec(0x0D, 0x02, struct.pack(">h", ly)) + _rec(0x0E, 0x02, struct.pack(">h", dt))
        out += _rec(0x10, 0x03, struct.pack(">10i", x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)) + _rec(0x11, 0x00)
    out += _rec(0x07, 0x00) + _rec(0x04, 0x00)
    Path(path).write_bytes(out)


if __name__ == "__main__":
    info = draw()
    GDS.parent.mkdir(exist_ok=True)
    write_gds(GDS)
    row_pitch = PAIR_PITCH / 2 / 1000
    dev_pitch = DEV_PITCH / 1000
    rows, cols = 72, 24
    # tile estimate: 36 row pairs; tie rows at top, middle and bottom (latch-up rule LU.b: <= 20 um to a tie)
    tie_block = (TGO_MARGIN + 1000 + 480) * 2 / 1000          # one tie row between two thick-oxide regions, as drawn
    wl_contact = (CNT_POLY_ACT + CNT + POLY_ENC_CNT + TGO_MARGIN) / 1000
    tile_w = cols * 2 * dev_pitch - DEV_SP / 1000 + wl_contact + (POLY_END + TGO_MARGIN) / 1000
    tile_h = rows * row_pitch - ACT_SP / 1000 + 3 * tie_block
    res = dict(
        drawn=dict(gds=str(GDS.relative_to(ROOT)), cell="tcim_2t2r_block", rows=2 * ROW_PAIRS, column_pairs=COL_PAIRS,
                   transistors=4 * ROW_PAIRS * COL_PAIRS, shapes=len(shapes),
                   width_um=(info["x_extent_nm"][1] - info["x_extent_nm"][0]) / 1000,
                   height_um=(info["y_extent_nm"][1] - info["y_extent_nm"][0]) / 1000),
        transistor=dict(W_um=W / 1000, L_um=L / 1000, contacts_per_terminal=info["n_contacts_per_terminal"]),
        row_pitch_um=row_pitch, device_pitch_um=dev_pitch, column_pair_pitch_um=2 * dev_pitch,
        area_per_device_um2=round(row_pitch * dev_pitch, 4), area_per_ternary_cell_um2=round(2 * row_pitch * dev_pitch, 4),
        tile_estimate=dict(width_um=round(tile_w, 2), height_um=round(tile_h, 2), area_mm2=round(tile_w * tile_h * 1e-6, 5),
                           tie_rows=3, note="72 x 24 cells at the drawn pitch plus word-line contacts and three tie rows; "
                                            "no ReRAM element (MEMRES layers not in the open PDK), no drivers"),
        source_line=dict(metal="Metal2", vias_per_source_strip=4, via_rating_mA=0.4, worst_current_mA=1.2),
        bit_line=dict(metal="Metal3 (placeholder level)", vias_per_drain=3),
        not_included="ReRAM element and its rules; the metal levels it actually sits between; word-line strapping; "
                     "periphery; fill. The Via2 stack on each drain marks where the element goes.")
    (ROOT / "results" / "cell_layout.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
