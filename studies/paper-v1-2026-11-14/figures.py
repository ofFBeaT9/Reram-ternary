"""Figures of paper v1 from results/security/v1/ (14 November 2026). Writes fig/*.png and fig/*.svg.

Colors: the first four slots of a validated categorical palette (checked for color-vision deficiency separation), in fixed
order; every series is also labelled directly, and every figure's numbers are in a table of the paper."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1] / "results" / "security" / "v1"
FIG = HERE / "fig"; FIG.mkdir(exist_ok=True)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.titlesize": 10, "axes.titlecolor": INK, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight"); fig.savefig(FIG / f"{name}.svg", bbox_inches="tight"); plt.close(fig)


def line(ax, x, y, c, label, **kw):
    ax.plot(x, y, color=c, lw=2, marker="o", ms=6, mec=SURF, mew=1.5, label=label, solid_capstyle="round", **kw)


def fig_sequence():
    z = np.load(V1 / "seq_mm_shared.npz"); G = list(z["G_uS"]); nom = z["nominal_uA"]
    t = np.arange(13) * 62.5
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    for k, (g, lab) in enumerate(((60.0, "LRS device, 60 µS"), (4.5, "HRS device, 4.5 µS"))):
        y = nom[G.index(g)]
        ax.step(t, np.r_[y, y[-1]], where="post", color=C[k], lw=2, label=lab)
    for x0, x1, lab in ((62.5, 250, "precharge\nword line off"), (250, 500, "read\nword line on"), (500, 625, "recharge\nword line off")):
        ax.axvspan(x0, x1, color=GRID, alpha=0.35, lw=0); ax.text((x0 + x1) / 2, 3.35, lab, ha="center", va="top", fontsize=8, color=INK2)
    ax.text(380, 2.47, "LRS", color=INK, fontsize=8.5, ha="center", va="bottom"); ax.text(380, 1.13, "HRS", color=INK, fontsize=8.5, ha="center", va="bottom")
    ax.set_xlim(0, 750); ax.set_ylim(0, 3.4); ax.set_xlabel("time in one row read (ns)"); ax.set_ylabel("amplifier supply current (µA)")
    ax.set_title("One sense amplifier over one read: mean current per clock cycle")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    save(fig, "fig1_read_sequence")


def fig_attack():
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    series = (("zeros_2t2r", "2T2R as built"), ("zeros_1of3_drawn", "one-of-three as drawn"),
              ("zeros_1of3_drawn_rot", "as drawn, with rotation"), ("zeros_1of3_bal_rot", "balanced bit lines, with rotation"))
    for k, (f, lab) in enumerate(series):
        r = json.loads((V1 / f"{f}.json").read_text())["results"]
        x = [a["reads_per_row"] for a in r]; y = [a["corr_mean"] for a in r]
        line(ax, x, y, C[k], lab, ls="--" if k == 2 else "-")
    ax.set_xscale("log"); ax.set_ylim(-0.08, 1.05); ax.set_xlabel("reads of every row that the attacker averages"); ax.set_ylabel("correlation, true vs estimated zero count")
    ax.set_title("Profiled zero-count attack against the reads per row")
    ax.text(30, 0.85, "2T2R", color=INK, fontsize=8.5); ax.text(2.5e4, 0.62, "one-of-three as drawn\n(with or without rotation)", color=INK, fontsize=8.5, ha="right")
    ax.text(3e5, 0.07, "balanced, rotated", color=INK, fontsize=8.5)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8)
    save(fig, "fig2_attack")


def fig_layers():
    e = json.loads((V1 / "extras.json").read_text())
    w = np.arange(12); fig, ax = plt.subplots(figsize=(6.6, 3.3))
    ys = ((np.abs(e["t2t2r_zero_minus_nonzero_uA"]), "2T2R: zero weight vs non-zero (count)"),
          (np.array(e["conductance_fixed_pattern_sd_uA"]["HRS"]), "one HRS device: conductance spread (sd)"),
          (np.array(e["mismatch_sd_lrs_minus_hrs_uA"]), "one amplifier: mismatch of LRS − HRS (sd)"),
          (np.abs(e["layout_term_nA"]["zero_minus_nonzero"]) / 1e3, "one-of-three as drawn: zero vs non-zero (bit lines)"))
    for k, (y, lab) in enumerate(ys):
        y = np.where(np.array(y) < 2e-4, np.nan, y)
        line(ax, w, y, C[k], lab)
    ax.axhline(5.0, color=INK2, lw=1, ls=":"); ax.text(11.4, 5.6, "assumed noise per read, 5 µA rms", ha="right", fontsize=8, color=INK2)
    ax.set_yscale("log"); ax.set_ylim(2e-4, 20); ax.set_xticks(w); ax.set_xlabel("clock cycle of the row read (precharge 1–3, read 4–7, recharge 8–9)")
    ax.set_ylabel("current per weight or device (µA)"); ax.set_title("Size of each leakage layer, per clock cycle")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    save(fig, "fig3_layers")


if __name__ == "__main__":
    fig_sequence(); fig_attack(); fig_layers(); print(sorted(p.name for p in FIG.iterdir()))
