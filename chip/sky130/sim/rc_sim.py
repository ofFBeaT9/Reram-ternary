"""Read and word-line timing with the wiring of the drawn macro (11 October 2026).

periph_sim.py simulated the sense amplifier with a 60 fF / 75 ohm bit line and the word-line driver straight into the
array's poly word line. Here the worst routed lines of the drawn macro (layout/sky130/periph/macro_rc.py:
results/sky130_chip/macro_rc.json) are added:
  read / verify: cell -> array bit line (C_array) -> routed wire (R_route) -> slice side (C_route) -> column switch ->
  sense amplifier; same cases as periph_sim part D (transient);
  word line: driver -> routed wire (R_route, C_route split half / half) -> 8.3 kohm poly word line with 48 gates (part B)
  and its extracted wiring capacitance spread along it.
Writes the section "resim" of results/sky130_chip/macro_rc.json."""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice as S        # noqa: E402
import periph_sim as P   # noqa: E402

ROOT = HERE.parents[2]
RC = ROOT / "results" / "sky130_chip" / "macro_rc.json"


def read_tran(corner, temp, op, gcell, r_route, c_array, c_route):
    vccd = 1.8
    deck = P.sa_deck(corner, temp, vccd, op).replace("Xcs bl vdda sa 0", "Xcs bl csg sa 0")
    deck = deck.replace("Bc bl d i=v(gc)*v(bl,d)", "Bc bla d i=v(gc)*v(bla,d)").replace("Ru bl du", "Ru bla du")
    assert "Bc bla d" in deck and "Ru bla du" in deck
    deck += f"""Vgc gc 0 {gcell}
Vcs csg 0 pwl(0 0 20n 0 20.2n 3.3 800n 3.3)
Rrt bla bl {r_route}
Carr bla 0 {c_array}
Crt bl 0 {c_route}
.ic v(bl)=0 v(bla)=0
.control
tran 0.05n 800n
wrdata out.txt v(out)
.endc
.end
"""
    a, _ = S.run(deck)
    t, out = a[:, 0], a[:, 1]
    final = out[-1] > vccd / 2
    wrong = np.nonzero((out > vccd / 2) != final)[0]
    ts = (t[wrong[-1] + 1] if len(wrong) else t[0]) - 20.1e-9
    return dict(G_uS=round(gcell * 1e6, 2), reads=int(final), settle_ns=round(max(ts, 0) * 1e9, 2))


def wl_tran(corner, temp, vwl, r_route, c_route, c_array, vdda=3.3):
    n = 12
    rseg = 172.8 * 48.2 / n
    lines = []
    for k in range(n):
        lines.append(f"R{k} w{k} w{k + 1} {rseg:.4g}")
        lines.append(f"Cw{k} w{k + 1} 0 {c_array / n:.4g}")            # the poly line's own wiring capacitance
        for j in range(4):
            lines.append(f"Xg{k}_{j} 0 w{k + 1} 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5")
    deck = P.hdr(corner, temp) + f"""Vda vdda 0 {vdda}
Vwl vwl 0 {vwl}
Vs sel 0 pwl(0 0 10n 0 10.2n {vdda} 60n {vdda} 60.2n 0 120n 0)
Vsb selb 0 pwl(0 {vdda} 10n {vdda} 10.2n 0 60n 0 60.2n {vdda} 120n {vdda})
X1 vwl wd sel selb vdda 0 wld
Cr1 wd 0 {c_route / 2}
Rrt wd w0 {r_route}
Cr2 w0 0 {c_route / 2}
{chr(10).join(lines)}
.control
tran 0.02n 120n
wrdata out.txt v(w{n})
.endc
.end
"""
    a, _ = S.run(deck)
    t, far = a[:, 0], a[:, 1]
    r = S.cross(t, far, 0.9 * vwl, True, 10e-9)
    f = S.cross(t, far, 0.1 * vwl, False, 60e-9)
    return dict(far_rise_90_ns=None if r is None else round((r - 10.1e-9) * 1e9, 3),
                far_fall_10_ns=None if f is None else round((f - 60.1e-9) * 1e9, 3))


def _job(a):
    kind, args = a
    return read_tran(*args) if kind == "read" else wl_tran(*args)


if __name__ == "__main__":
    d = json.loads(RC.read_text())
    w = d["worst_case"]
    rb, ca, cr = w["R_bitline_ohm"], w["C_bitline_array_F"], w["C_bitline_route_F"]
    rw, cw, cwa = w["R_wordline_route_ohm"], w["C_wordline_route_F"], w["C_wordline_array_F"]
    pts = (("tt", 27), ("ss", 125), ("ff", -40), ("ss", -40), ("ff", 125))
    cases = [(op, g) for op, gs in (("read", (30e-6, 4.5e-6)), ("set", (30e-6, 20e-6)), ("reset", (4.5e-6, 10e-6))) for g in gs]
    jobs = [("read", (c, T, op, g, rb, ca, cr)) for c, T in pts for op, g in cases]
    jobs += [("wl", (c, T, v, rw, cw, cwa)) for c, T in pts for v in (1.7, 2.0, 3.0, 3.3)]
    with Pool(int(os.environ.get("JOBS", "2"))) as pool:
        res = pool.map(_job, jobs)
    rr = [dict(corner=a[1][0], temp=a[1][1], op=a[1][2], **r) for a, r in zip(jobs, res) if a[0] == "read"]
    wr = [dict(corner=a[1][0], temp=a[1][1], vwl=a[1][2], **r) for a, r in zip(jobs, res) if a[0] == "wl"]
    exp = {("read", 30.0): 1, ("read", 4.5): 0, ("set", 30.0): 1, ("set", 20.0): 0, ("reset", 4.5): 0, ("reset", 10.0): 1}
    d["resim"] = dict(read=rr, wordline=wr,
                      all_decisions_correct=all(r["reads"] == exp[(r["op"], r["G_uS"])] for r in rr),
                      read_settle_max_ns=max(r["settle_ns"] for r in rr if r["op"] == "read"),
                      verify_settle_max_ns=max(r["settle_ns"] for r in rr if r["op"] != "read"),
                      wl_rise_max_ns=max(r["far_rise_90_ns"] for r in wr), wl_fall_max_ns=max(r["far_fall_10_ns"] for r in wr))
    RC.write_text(json.dumps(d, indent=1))
    print(json.dumps({k: v for k, v in d["resim"].items() if k not in ("read", "wordline")}, indent=1))
