"""Picture of layout/tcim_2t2r_block.gds as drawn by cell_2t2r.py (front-end layers and Metal1 left, the
metal stack right). Writes layout/tcim_2t2r_block.png. Not a substitute for KLayout; it only shows the shapes."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cell_2t2r as c  # noqa: E402

c.draw()
STYLE = {c.TGO: ("ThickGateOx", "#d9d2e9", 0.5), c.PSD: ("pSD", "#fde2c4", 0.6), c.ACTIV: ("Activ", "#7fbf7f", 0.8),
         c.GATPOLY: ("GatPoly (word line)", "#d64545", 0.85), c.CONT: ("Cont", "#222222", 1.0), c.METAL1: ("Metal1", "#4a7fd6", 0.45),
         c.VIA1: ("Via1", "#111111", 1.0), c.METAL2: ("Metal2 (source line)", "#e3a21a", 0.55), c.VIA2: ("Via2 = ReRAM placeholder", "#c0392b", 1.0),
         c.METAL3: ("Metal3 (bit line)", "#2aa198", 0.45)}
left = (c.TGO, c.PSD, c.ACTIV, c.GATPOLY, c.CONT, c.METAL1)
right = (c.ACTIV, c.METAL2, c.METAL3, c.VIA1, c.VIA2)
fig, axes = plt.subplots(1, 2, figsize=(14, 4.9))
for ax, layers, title in ((axes[0], left, "front end and Metal1"), (axes[1], right, "metal stack (Activ for reference)")):
    for lay in layers:
        name, col, a = STYLE[lay]
        for l, x0, y0, x1, y1 in c.shapes:
            if l == lay:
                ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, facecolor=col, alpha=a, edgecolor="none"))
    xs = [s[1] for s in c.shapes] + [s[3] for s in c.shapes]; ys = [s[2] for s in c.shapes] + [s[4] for s in c.shapes]
    ax.set_xlim(min(xs) / 1000 - 0.3, max(xs) / 1000 + 0.3); ax.set_ylim(min(ys) / 1000 - 0.3, max(ys) / 1000 + 0.3)
    ax.set_aspect("equal"); ax.set_xlabel("µm"); ax.set_ylabel("µm"); ax.set_title(title, fontsize=11)
    ax.legend(handles=[Patch(facecolor=STYLE[l][1], alpha=STYLE[l][2], label=STYLE[l][0]) for l in layers], loc="upper center",
              bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8, frameon=False)
fig.suptitle("TCIM0 array transistors, IHP SG13G2: 4 rows × 2 column pairs (16 × 3.3 V NMOS, W 4.5 µm, L 0.45 µm), DRC clean", fontsize=11)
fig.tight_layout()
fig.savefig(Path(__file__).resolve().parent / "tcim_2t2r_block.png", dpi=130)
print("written")
