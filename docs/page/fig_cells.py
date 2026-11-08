"""Figure for the page: the 2T2R cell of this chip and the 3T3R one-of-three cell of the next chip, side by side, to scale,
every rectangle read from the cells' GDS (layout/sky130/next_3t3r/rr2t2r_ref.gds, rr3t3r.gds). Returns an SVG string."""
from pathlib import Path
import gdstk

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "layout" / "sky130" / "next_3t3r"
# (gds layer, datatype): (name, css colour, opacity, order)
LAYERS = [((65, 20), "diff", "#4aa04a", .55), ((65, 44), "tap", "#7fbf7f", .55), ((66, 20), "poly", "#c83232", .55),
          ((67, 20), "li1", "#8c6ec8", .45), ((68, 20), "met1", "#2f6edc", .45), ((201, 20), "ReRAM", "#f2b705", .95),
          ((69, 20), "met2", "#d246be", .35)]


def cell_svg(gds, name, x0, y0, s):
    c = next(x for x in gdstk.read_gds(str(gds)).cells if x.name == name)
    out = []
    for (ld, lab, col, op) in LAYERS:
        for p in c.polygons:
            if (p.layer, p.datatype) != ld:
                continue
            (a, b), (e, f) = p.bounding_box()
            out.append(f'<rect x="{x0 + a * s:.1f}" y="{y0 + (3.0 - f) * s:.1f}" width="{(e - a) * s:.1f}" height="{(f - b) * s:.1f}" '
                       f'fill="{col}" fill-opacity="{op}" data-tip="{lab}: {e - a:.2f} × {f - b:.2f} µm"/>')
    return "".join(out)


def figure():
    s = 52.0
    w2, w3 = 3.6 * s, 5.6 * s
    x2, x3, y0 = 40, 40 + w2 + 70, 40
    H = y0 + 3.0 * s + 70
    W = x3 + w3 + 30
    o = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="The 2T2R cell of this chip (3.6 by 3.0 micrometres) and the 3T3R '
         f'one-of-three cell of the next chip (5.6 by 3.0 micrometres), to scale, drawn from their GDS files.">']
    for x, w, lab, g, n in ((x2, w2, "2T2R (this chip): 3.6 × 3.0 µm = 10.8 µm²", D / "rr2t2r_ref.gds", "rr2t2r"),
                            (x3, w3, "3T3R one-of-three (next chip): 5.6 × 3.0 µm = 16.8 µm²", D / "rr3t3r.gds", "rr3t3r")):
        o.append(f'<rect x="{x}" y="{y0}" width="{w:.1f}" height="{3.0 * s:.1f}" fill="none" stroke="currentColor" stroke-dasharray="4 3" stroke-width=".8"/>')
        o.append(cell_svg(g, n, x, y0, s))
        o.append(f'<text x="{x}" y="{y0 - 12}" class="sm">{lab}</text>')
    for i, t in enumerate(("BL+", "BL−")):
        o.append(f'<text x="{x2 + (0.8 + 2.0 * i) * s:.1f}" y="{y0 + 3.0 * s + 18:.1f}" text-anchor="middle" class="sm">{t}</text>')
    for i, t in enumerate(("BL P", "BL Z", "BL N")):
        o.append(f'<text x="{x3 + (0.8 + 2.0 * i) * s:.1f}" y="{y0 + 3.0 * s + 18:.1f}" text-anchor="middle" class="sm">{t}</text>')
    for x in (x2, x3):
        o.append(f'<text x="{x + 1.8 * s:.1f}" y="{y0 + 3.0 * s + 36:.1f}" text-anchor="middle" class="sm">SL</text>')
    lx = 40
    for (_, lab, col, op) in LAYERS:
        o.append(f'<rect x="{lx}" y="{H - 16}" width="11" height="11" fill="{col}" fill-opacity="{op}"/><text x="{lx + 15}" y="{H - 6}" class="sm">{lab}</text>')
        lx += 70
    o.append("</svg>")
    return "".join(o)


if __name__ == "__main__":
    print(figure()[:300])
