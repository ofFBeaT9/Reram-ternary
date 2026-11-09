"""Programming through the SKY130 periphery for the next-chip 3T3R one-of-three cell (8 November 2026).

macro_sim.py with three devices per weight: two rows x two ternary columns, each weight P, Z, N (12 devices, each with
its select transistor nfet_g5v0d10v5 W 1.0 / L 0.5 um on a shared word line and source line), driven by the bld / sld
cells of periph.spice as tcim_actl drives them with the Z bit line (rtl/chip/tcim_actl.sv, TCIM_CELL_1OF3): a set pulse
puts VPRG on the masked bit lines and grounds every other line; a reset pulse grounds the masked bit lines and puts VPRG
on every other bit line and on the source lines. The target is device P of column 0, row 0, as in macro_sim.py; Z and N of
the same weight now both share its source line. Same quasi-static method, model and targets as macro_sim.py.
Runs: set ladders at word line 2.0 V (the proposed map) at tt 27 C, ss -40 C, ff 125 C; reset ladders for cells 0-3
decades slower than the fitted reset rate at the same corners; disturb = largest change of read conductance of the 11
other devices. Writes results/next_chip/macro_sim3.json."""
import json, math, os, sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import macro_sim as M      # noqa: E402
import spice as S          # noqa: E402

DEV = ("p", "z", "n")
M.KEYS = [f"r{r}c{c}{d}" for r in (0, 1) for c in (0, 1) for d in DEV]
OUT = M.ROOT / "results" / "next_chip" / "macro_sim3.json"


def vcell_table3(op, vwl, vprg, gaps, corner="tt", temp=27):
    on, off = "vdda", "0"
    def bld(name, mode):
        p = mode == "prg"
        return f"X{name} vprg {name} nc_{name} {on if p else off} {off if p else on} {off if p else on} 0 vdda 0 bld\nR{name}_nc nc_{name} 0 1e9"
    def sld(name, mode):
        p = mode == "prg"
        return f"X{name} vprg {name} {on if p else off} {off if p else on} {off if p else on} vdda 0 sld"
    if op == "set":                # PULSE_SET with only P of column 0 masked
        mb = {f"bl{d}{c}": ("prg" if (d, c) == ("p", 0) else "dn") for c in (0, 1) for d in DEV}; ms = {"sl0": "dn", "sl1": "dn"}
    else:                          # PULSE_RST with only P of column 0 masked
        mb = {f"bl{d}{c}": ("dn" if (d, c) == ("p", 0) else "prg") for c in (0, 1) for d in DEV}; ms = {"sl0": "prg", "sl1": "prg"}
    lines = [bld(n, m) for n, m in mb.items()] + [sld(n, m) for n, m in ms.items()]
    cells = []
    for k in M.KEYS:
        r, c, d = int(k[1]), int(k[3]), k[4]
        gnode = "V(gt)" if k == "r0c0p" else f"{gaps[k]:.6f}"
        cells.append(f"Rb{k} bl{d}{c} te{k} {M.RBL}\n"
                     f"B{k} te{k} be{k} I = {M.P.I0}*exp(-{gnode}/{M.P.g0 * 1e9:.6g})*sinh(V(te{k},be{k})/{M.P.V0})\n"
                     f"Xt{k} be{k} wl{r} s{k} 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5\nRs{k} s{k} sl{c} {M.RSL}")
    deck = f"""* 3T3R macro DC
{S.lib(corner)}.temp {temp}
{M.CELLS}
Vda vdda 0 3.3
Vp vprg 0 {vprg}
Vwp wlpad 0 {vwl}
Vgt gt 0 1.0
Xrm wlpad vwl vdda 0 vdda 0 tg wn=8 wp=16
Xw0 vwl wl0 vdda 0 vdda 0 wld
Xw1 vwl wl1 0 vdda vdda 0 wld
{chr(10).join(lines)}
{chr(10).join(cells)}
.control
dc Vgt {M.GRID[0]} {M.GRID[-1]} 0.01
wrdata out.txt {' '.join(f'v(te{k},be{k})' for k in M.KEYS)}
.endc
.end
"""
    a, log = S.run(deck)
    if len(a) != len(M.GRID) or abs(a[-1, 0] - M.GRID[-1]) > 1e-6:
        raise RuntimeError("DC sweep incomplete:\n" + log[-1500:])
    return {k: a[:, 2 * i + 1] for i, k in enumerate(M.KEYS)}


M.vcell_table = vcell_table3


def start_gaps(lrs_others):
    """weights of the 2 x 2 corner: every weight one LRS device (one-of-three). r0c0 holds Z (target P must be set);
    the others: r0c1 = +1 (P), r1c0 = -1 (N), r1c1 = 0 (Z)."""
    hrs, lrs = M.gap_for(4.5e-6), M.gap_for(60e-6)
    g = {k: hrs for k in M.KEYS}
    for k in ("r0c0z", "r0c1p", "r1c0n", "r1c1z") if lrs_others else ():
        g[k] = lrs
    return g


def ladder_set(vwl, corner, temp):
    gaps = start_gaps(True); g0 = dict(gaps); steps = []
    F = 10 ** M.LOGF[1.0]
    for k in range(20):
        vprg = round(1.4 + 0.1 * k, 2)
        gaps, vcell = M.pulse("set", vwl, vprg, gaps, F, corner, temp)
        g = M.g_read(gaps["r0c0p"]); steps.append(dict(VPRG=vprg, cell_V=round(vcell, 3), G_uS=round(g * 1e6, 2)))
        if g >= M.SET_TARGET:
            break
    dist = {k: round((M.g_read(gaps[k]) - M.g_read(g0[k])) * 1e6, 4) for k in gaps if k != "r0c0p"}
    return dict(op="set", VWLP=vwl, corner=corner, temp=temp, pulses=len(steps), reached=M.g_read(gaps["r0c0p"]) >= M.SET_TARGET,
                final_uS=round(M.g_read(gaps["r0c0p"]) * 1e6, 2), max_disturb_uS=max(abs(v) for v in dist.values()), disturb_uS=dist, steps=steps)


def ladder_reset(slow, corner, temp):
    F = 10 ** (M.LOGF[1.0] - slow)
    gaps = start_gaps(True); gaps["r0c0p"] = M.gap_for(60e-6); gaps["r0c0z"] = M.gap_for(4.5e-6)   # r0c0 = +1, to be reset
    g0 = dict(gaps); steps = []
    seq = [(round(2.5 + 0.1 * i, 2), 2.4) for i in range(6)] + [(3.0, round(2.5 + 0.1 * i, 2)) for i in range(6)]
    for vwl, vprg in seq:
        gaps, vcell = M.pulse("reset", vwl, vprg, gaps, F, corner, temp)
        g = M.g_read(gaps["r0c0p"]); steps.append(dict(VWLP=vwl, VPRG=vprg, cell_V=round(vcell, 3), G_uS=round(g * 1e6, 2)))
        if g <= M.RESET_TARGET:
            break
    dist = {k: round((M.g_read(gaps[k]) - M.g_read(g0[k])) * 1e6, 4) for k in gaps if k != "r0c0p"}
    return dict(op="reset", slower_decades=slow, log10F=round(math.log10(F), 3), corner=corner, temp=temp, pulses=len(steps),
                reached=M.g_read(gaps["r0c0p"]) <= M.RESET_TARGET, final_uS=round(M.g_read(gaps["r0c0p"]) * 1e6, 2),
                max_disturb_uS=max(abs(v) for v in dist.values()), disturb_uS=dist, steps=steps)


def _job(a):
    kind, args = a
    return (ladder_set if kind == "set" else ladder_reset)(*args)


if __name__ == "__main__":
    C = (("tt", 27), ("ss", -40), ("ff", 125))
    jobs = [("set", (2.0, c, T)) for c, T in C] + [("reset", (sl, c, T)) for sl in (0, 1, 2, 3) for c, T in C]
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        jobs = jobs[:1]
    with Pool(int(os.environ.get("JOBS", "2"))) as pool:
        res = pool.map(_job, jobs)
    for r in res:
        print({k: v for k, v in r.items() if k not in ("steps", "disturb_uS")}, flush=True)
    out = dict(note=__doc__.split("\n\n")[0], set_target_uS=M.SET_TARGET * 1e6, reset_target_uS=M.RESET_TARGET * 1e6,
               set=[r for r in res if r["op"] == "set"], reset=[r for r in res if r["op"] == "reset"],
               max_disturb_uS=max(r["max_disturb_uS"] for r in res))
    if len(sys.argv) == 1:
        OUT.write_text(json.dumps(out, indent=1))
