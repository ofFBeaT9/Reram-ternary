"""Explanatory figures for BOS_BRIEF.md (17 November 2026). Writes fig/brief_*.png.

Numbers are those quoted in the brief (sources there). The publication timeline is a plan, not a result."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
FIG = HERE / "fig"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "savefig.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def box(ax, x, y, w, h, title, body, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03", fc=SURF, ec=color, lw=2))
    ax.text(x + 0.02, y + h - 0.05, title, fontsize=9, fontweight="bold", color=INK, va="top")
    ax.text(x + 0.02, y + h - 0.13, body, fontsize=8, color=INK2, va="top", linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, label, dy=0.02):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.4, shrinkA=2, shrinkB=2))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, label, fontsize=7.8, color=INK, ha="center", va="bottom",
            bbox=dict(fc=SURF, ec="none", pad=1))


def fig_map():
    fig, ax = plt.subplots(figsize=(8.4, 4.4)); ax.set_xlim(-0.02, 1.02); ax.set_ylim(0, 1.1); ax.axis("off")
    w = 0.28
    box(ax, 0.00, 0.58, w, 0.38, "Min. intelligence scale",
        "How few bits does a model\nof a physical system need?\nState: definition, 3-seed pilot\nOutput: ML paper (months)", C[0])
    box(ax, 0.36, 0.58, w, 0.38, "TCIM0 ternary ReRAM tile",
        "Weights stored in memory;\nmultiply inside the array\nState: chip drawn, draft 1.0\nOutput: security paper (weeks)", C[1])
    box(ax, 0.72, 0.58, w, 0.38, "REBEL-6 (USN)",
        "Balanced-ternary CPU,\nfabricated silicon\nRole: host CPU and the\nfirst measured numbers", C[3])
    box(ax, 0.20, 0.03, 0.60, 0.36, "KAIROS instrument",
        "Benchtop living-cell pharmacology (organ-on-a-chip)\nForecasts sealed before dosing, scored on tissue\nState: design article, 12 synthetic studies\nOutput: design preprint now; experiments = PhD (years)", C[2])
    arrow(ax, 0.28, 0.77, 0.36, 0.77, "")
    ax.text(0.32, 1.0, "small models\nto run", fontsize=7.6, ha="center", va="bottom", color=INK)
    arrow(ax, 0.72, 0.77, 0.64, 0.77, "")
    ax.text(0.68, 1.0, "tile is a\ndevice of", fontsize=7.6, ha="center", va="bottom", color=INK)
    arrow(ax, 0.14, 0.58, 0.32, 0.39, "model sizes tested\non tissue", dy=0.0)
    arrow(ax, 0.50, 0.58, 0.50, 0.39, "on-instrument\ncompute (later)", dy=-0.04)
    ax.set_title("How the projects fit together: each can be published alone")
    fig.savefig(FIG / "brief_map.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def fig_radix():
    fig, ax = plt.subplots(figsize=(8.4, 2.6)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    st = [("Input", "72 trits\n(−1, 0, +1)", "ternary", C[3]),
          ("Weights (ReRAM)", "2T2R: 2 devices\none-of-three: 3\n(each on/off)", "binary devices,\nternary code", C[1]),
          ("Sense amps", "one bit per device\n(digital read: exact)", "binary", C[0]),
          ("Counters", "integer sum\n−72 … +72", "two's complement", C[0]),
          ("To REBEL-6", "24 results as\nbalanced-ternary\ntrytes", "ternary", C[3])]
    w, g = 0.17, 0.03
    for k, (t, b, r, c) in enumerate(st):
        x = 0.01 + k * (w + g)
        ax.add_patch(FancyBboxPatch((x, 0.30), w, 0.58, boxstyle="round,pad=0.01,rounding_size=0.02", fc=SURF, ec=c, lw=2))
        ax.text(x + w / 2, 0.83, t, ha="center", va="top", fontsize=8.5, fontweight="bold", color=INK)
        ax.text(x + w / 2, 0.66, b, ha="center", va="top", fontsize=7.8, color=INK2, linespacing=1.3)
        ax.text(x + w / 2, 0.20, r, ha="center", va="top", fontsize=7.8, color=INK, fontstyle="italic")
        if k:
            ax.annotate("", (x - 0.002, 0.59), (x - g + 0.002, 0.59), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.4))
    ax.set_title("TCIM0 is already mixed radix: each stage uses the radix that suits it")
    fig.savefig(FIG / "brief_radix.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def fig_mis():
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    ax.grid(True, color=GRID, lw=0.6)
    ax.axvline(0.61, color=INK2, lw=1, ls=":"); ax.text(0.64, 50, "equations\n610 bits", fontsize=8, color=INK2, va="top")
    ax.plot([0.88, 3.2], [9.8, 3.6], color=C[0], lw=2, marker="o", ms=7, mec=SURF, mew=1.5, label="structured like the physics")
    ax.plot([8.4, 23], [13.8, 8.9], color=C[1], lw=2, marker="s", ms=7, mec=SURF, mew=1.5, label="ternary weights, trained")
    ax.hlines(15.6, 0.5, 285, color=C[2], lw=2, ls="--", label="unconstrained networks: never below this, up to 285 kbit")
    ax.text(12, 70, "ternary weights set after training:\nabove 85 % error (off the chart)", fontsize=8, color=INK, ha="center")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.5, 400); ax.set_ylim(2, 120)
    ax.set_yticks([2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["2", "5", "10", "20", "50", "100"])
    ax.set_xlabel("model size (kbit)"); ax.set_ylabel("error outside the training range (%)")
    ax.set_title("Scale pilot (3 seeds, simulation): structure beats size; ternary is not free")
    ax.legend(frameon=False, fontsize=7.8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    fig.savefig(FIG / "brief_mis.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def fig_plan():
    m = ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    rows = [("TCIM0: review, balanced layout, preprint", 0, 2, C[1]), ("TCIM0: submit to a venue", 2, 1, C[1]),
            ("REBEL-6: noise floor, TMAC.T test", 0, 2, C[3]), ("REBEL-6 + TCIM0 logic on FPGA; ISMVL paper", 1, 3, C[3]),
            ("Scale: 10 seeds, baselines, 2 systems", 0, 4, C[0]), ("Scale: preprint and workshop", 4, 2, C[0]),
            ("KAIROS: design preprint", 2, 2, C[2]), ("KAIROS: host laboratory search", 0, 7, C[2])]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for i, (lab, s, d, c) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, d - 0.08, left=s + 0.04, height=0.55, color=c, edgecolor=SURF)
        ax.text(-0.1, y, lab, ha="right", va="center", fontsize=8, color=INK)
    ax.set_yticks([]); ax.set_xticks([k + 0.5 for k in range(7)]); ax.set_xticklabels(m); ax.set_xlim(0, 7)
    for k in range(8):
        ax.axvline(k, color=GRID, lw=0.6)
    ax.spines["left"].set_visible(False)
    ax.set_title("Proposed plan, December 2026 to June 2027 (a plan, not a commitment)", x=-0.62)
    fig.savefig(FIG / "brief_plan.png", dpi=200, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_map(); fig_radix(); fig_mis(); fig_plan(); print("ok")
