"""Supply current of one sense amplifier during a read, as a waveform (8 November 2026; paper study, item H8).

sa_power.py gave the DC current. Here the same deck (periph_sim.sa_deck: reference bias, sense amplifier, column switch,
the selected cell with its select transistor, 71 unselected cells lumped) runs as a transient: the bit line starts
discharged, the column switch closes at 20 ns and the read lasts 4 clock cycles at 16 MHz (250 ns, the shortest read
window of the controller). The sense amplifier is on its own 1.8 V source, so its current is measured alone.

  devices:  HRS 2, 3, 4.5, 6, 7.93 uS and LRS 30, 45, 60, 90, 120 uS (SkyWater: set 30-120 uS, reset about 4.5 uS)
  mismatch: N local-mismatch samples (tt_mm, 27 C), each with every device value (the same seed for one sample, so a
            sample is one physical sense amplifier); and the nominal tt 27 C deck
Output: results/security/sa_transient.npz (t, G, nominal[G, t], mm[seed, G, t], in uA) and a summary JSON.
The waveforms are averaged into windows (WIN ns) as a bandwidth-limited probe would see them."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S          # noqa: E402
import periph_sim as PS    # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "results" / "security" / "sa_transient"
G_HRS = [2e-6, 3e-6, 4.5e-6, 6e-6, 7.93e-6]
G_LRS = [30e-6, 45e-6, 60e-6, 90e-6, 120e-6]
G_ALL = G_HRS + G_LRS
T_END, DT, WIN = 250e-9, 0.25e-9, 10e-9
NMM = int(os.environ.get("NMM", "40"))


def deck(g, mm):
    d = PS.sa_deck("tt", 27, 1.8, "read", mm).replace("Xcs bl vdda sa 0", "Xcs bl csg sa 0")
    d = d.replace("Xsa sa out vbp vcl vccd 0 sa", "Vsa vsa 0 1.8\nXsa sa out vbp vcl vsa 0 sa")
    return d + f"""Vgc gc 0 {g}
Vcs csg 0 pwl(0 0 20n 0 20.2n 3.3 {T_END * 1e9:.0f}n 3.3)
Cbl bl 0 60f
.ic v(bl)=0
.control
tran {DT * 1e9:.3g}n {T_END * 1e9:.0f}n
wrdata out.txt i(Vsa) v(out)
.endc
.end
"""


def one(job):
    g, seed = job
    a, _ = S.run(deck(g, seed is not None), seed=seed)
    t, i = a[:, 0], -a[:, 1] * 1e6               # current drawn from the 1.8 V source, uA
    edges = np.arange(0, T_END + 1e-15, WIN)
    w = np.array([np.trapezoid(np.interp(np.linspace(a0, a1, 41), t, i), np.linspace(a0, a1, 41)) / (a1 - a0)
                  for a0, a1 in zip(edges[:-1], edges[1:])])
    return g, seed, w, float(a[-1, 3] if a.shape[1] > 3 else a[-1, 2])


def main():
    jobs = [(g, None) for g in G_ALL] + [(g, 1000 + s) for s in range(NMM) for g in G_ALL]
    with ProcessPoolExecutor(int(os.environ.get("JOBS", "2"))) as ex:
        res = list(ex.map(one, jobs))
    nwin = len(res[0][2])
    nom = np.zeros((len(G_ALL), nwin)); mm = np.zeros((NMM, len(G_ALL), nwin)); outs = {}
    for g, seed, w, vout in res:
        k = G_ALL.index(g)
        if seed is None:
            nom[k] = w
        else:
            mm[seed - 1000, k] = w
        outs.setdefault(round(g * 1e6, 2), []).append(vout)
    tw = (np.arange(nwin) + 0.5) * WIN
    np.savez(OUT.with_suffix(".npz"), t_ns=tw * 1e9, G_uS=np.array(G_ALL) * 1e6, nominal_uA=nom, mm_uA=mm)
    lrs = [G_ALL.index(g) for g in G_LRS]; hrs = [G_ALL.index(g) for g in G_HRS]
    summ = dict(note=__doc__.split("\n\n")[0], window_ns=WIN * 1e9, read_ns=T_END * 1e9, mismatch_samples=NMM,
                mean_uA_nominal={f"{G_ALL[k] * 1e6:g}uS": round(float(nom[k].mean()), 4) for k in range(len(G_ALL))},
                peak_uA_nominal={f"{G_ALL[k] * 1e6:g}uS": round(float(nom[k].max()), 4) for k in range(len(G_ALL))},
                lrs_spread_over_G_uA=round(float(np.abs(nom[lrs] - nom[lrs].mean(0)).max()), 4),
                hrs_spread_over_G_uA=round(float(np.abs(nom[hrs] - nom[hrs].mean(0)).max()), 4),
                mismatch_sd_uA_LRS60=round(float(mm[:, G_ALL.index(60e-6)].std(0).max()), 4),
                mismatch_sd_uA_HRS4p5=round(float(mm[:, G_ALL.index(4.5e-6)].std(0).max()), 4),
                lrs_minus_hrs_uA=round(float((nom[lrs].mean(0) - nom[hrs].mean(0)).max()), 4),
                reads_correct=all((v > 0.9) == (g >= 30) for g, vs in outs.items() for v in vs))
    OUT.with_suffix(".json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "programmed":
        # the states the drawn drivers program in macro_sim3.py (set stops at 28.4-29.9 uS, one reset pulse ends at 0.31 uS)
        # next to SkyWater's published states (red-team finding 9, 8 November 2026): nominal mean supply current per state
        gs = [0.31e-6, 1e-6, 4.5e-6, 28e-6, 29.9e-6, 60e-6]
        with ProcessPoolExecutor(2) as ex:
            r = list(ex.map(one, [(g, None) for g in gs]))
        res = dict(note="sense-amplifier mean supply current over the 250 ns read, tt 27 C, nominal; programmed states of macro_sim3 "
                        "(set 28.4-29.9 uS, reset 0.31 uS) and SkyWater's published states (60 uS, 4.5 uS)",
                   mean_uA={f"{g * 1e6:g}uS": round(float(w.mean()), 4) for g, _, w, _ in r},
                   read_correct={f"{g * 1e6:g}uS": bool((v > 0.9) == (g >= 12e-6)) for g, _, _, v in r})
        OUT.with_name("sa_programmed_states.json").write_text(json.dumps(res, indent=1)); print(res); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        import time; t0 = time.time(); r = one((60e-6, None)); print(round(time.time() - t0, 1), "s", r[2].round(3), r[3]); sys.exit()
    main()
