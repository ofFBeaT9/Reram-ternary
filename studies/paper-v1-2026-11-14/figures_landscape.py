"""Figures for section 11 of BOS_BRIEF.md (17 November 2026): logic-node roadmap and the maturity of computing technologies.

Sources are listed in section 11 of the brief. Node years after 2026 are roadmap projections (imec, as reported in July 2026),
not results. Maturity stages are the author's placement of the cited demonstrations, not a published scale."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path(__file__).resolve().parent / "fig"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "savefig.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.titlelocation": "left"})


def fig_nodes():
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    prod = [(2025, 2.0, "N2 / SF2 / 18A\nin production"), (2026.8, 1.6, "A16\n(planned Q4 2026)")]
    road = [(2028, 1.4, "A14"), (2031, 1.0, "A10\nforksheet"), (2034, 0.7, "A7\nCFET"), (2038, 0.3, "A3"), (2043, 0.2, "A2\n2D-channel FET")]
    ax.plot([p[0] for p in prod], [p[1] for p in prod], color=C[0], lw=2, marker="o", ms=8, mec=SURF, mew=1.5, label="node name, in production or planned")
    ax.plot([prod[-1][0]] + [r[0] for r in road], [prod[-1][1]] + [r[1] for r in road], color=C[0], lw=2, ls="--", marker="o", ms=8,
            mfc=SURF, mew=1.8, label="node name, imec roadmap (projection)")
    for x, y, t in prod + road:
        below = t.startswith("A16") or t.startswith("A14")
        ax.text(x + (0.6 if t.startswith("A14") else 0), y / 1.35 if below else y * 1.22, t, ha="center",
                va="top" if below else "bottom", fontsize=7.6, color=INK)
    ax.plot([2028, 2031, 2034], [45, 42, 42], color=C[1], lw=2, marker="s", ms=7, mec=SURF, mew=1.5, label="contacted gate pitch (projection)")
    ax.text(2031, 55, "gate pitch stays near 42–45 nm", ha="center", fontsize=8, color=INK)
    ax.set_yscale("log"); ax.set_ylim(0.1, 150); ax.set_xlim(2024, 2045); ax.set_xticks(range(2025, 2046, 5)); ax.set_xticklabels([str(y) for y in range(2025, 2046, 5)])
    ax.set_yticks([0.2, 0.5, 1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10", "20", "50", "100"])
    ax.set_ylabel("nm"); ax.set_title('"Sub-1 nm" is a name: node names shrink 10x, the gate pitch hardly moves')
    ax.legend(frameon=False, fontsize=7.8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.savefig(FIG / "brief_nodes.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def fig_maturity():
    stages = ["device", "small circuit", "processor or\nsystem demo", "foundry flow\nor product", "volume\nproduction"]
    rows = [("Silicon nanosheet (GAA)", 5, "N2, SF2, 18A since 2025", 0),
            ("Silicon CFET", 2, "prototype chips (Intel, Samsung, TSMC)", 0),
            ("2D semiconductor (MoS2)", 3, "32-bit RISC-V, 5,900 transistors (Nature 2025)", 0),
            ("Carbon nanotube FET", 3, "RISC-V 2019, 2-bit TPU 2024; 200 mm foundry flow", 0),
            ("Ternary transistors", 2, "wafer-scale devices, small gates (2019–2026)", 3),
            ("Memristor compute-in-memory", 3, "chips with 32x32 to 64x64 arrays (2026)", 1),
            ("Digital neuromorphic", 4, "Hala Point 1.15 B neurons; chips on sale", 1),
            ("Photonic AI", 3, "128x128 tensor cores; 64x64 accelerator (Nature 2025)", 1),
            ("Qubits with error correction", 3, "below threshold, distance 7 (Nature 2025)", 2),
            ("Qudits (d = 3 to 7)", 3, "processor d <= 7; error-corrected qutrit, ququart", 2)]
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.grid(False)
    for k in range(5):
        ax.axvline(k + 1, color=GRID, lw=0.8)
    for i, (name, s, ev, c) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([1, s], [y, y], color=C[c], lw=2, solid_capstyle="round")
        ax.plot(s, y, "o", color=C[c], ms=8, mec=SURF, mew=1.5)
        ax.text(-0.1, y, name, ha="right", va="center", fontsize=8, color=INK)
        ax.text(s + 0.15, y, ev, ha="left", va="center", fontsize=7.2, color=INK2)
    ax.set_xlim(0.8, 7.6); ax.set_xticks(range(1, 6)); ax.set_xticklabels(stages, fontsize=7.5)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_title("How far each technology has come (author's placement of the cited results)", x=-0.42)
    fig.savefig(FIG / "brief_maturity.png", dpi=200, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_nodes(); fig_maturity(); print("ok")
