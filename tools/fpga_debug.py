"""Analog-mode check on the FPGA board (or the simulation) with simple inputs, against the weights read back from the
emulated array. Run after tools/fpga_host.py has programmed the array (it is not redrawn here). 10 October 2026.
  python3 tools/fpga_debug.py --port COM5 | --sim <exe>  [--json out.json]
Inputs: one +1 on a single row; one -1 on a single row; all +1; all -1; alternating. For each, the column results
of the digital and the analog mode and the exact dot product of the read-back weights."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fpga_host import TCIM, SerialLink, SimLink, ROWS, COLS   # noqa: E402

ap = argparse.ArgumentParser()
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--sim"); g.add_argument("--port")
ap.add_argument("--json"); ap.add_argument("--program", action="store_true", help="redraw the array and program random weights first (seed 1)")
a = ap.parse_args()
link = SimLink(a.sim) if a.sim else SerialLink(a.port)
t = TCIM(link)
if a.program:
    import random
    rng = random.Random(1)
    t.emu(0, 1, True); t.ctrl(en=True)
    for r in range(ROWS):
        t.program_row(r, [rng.choice((-1, 0, 1)) for _ in range(COLS)])
W = [t.read_row(r)[0] for r in range(ROWS)]
cases = {}
for name, x in (("row0 +1", [1] + [0] * (ROWS - 1)), ("row0 -1", [-1] + [0] * (ROWS - 1)),
                ("row5 +1", [0] * 5 + [1] + [0] * (ROWS - 6)), ("all +1", [1] * ROWS), ("all -1", [-1] * ROWS),
                ("alternating", [1 if r % 2 == 0 else -1 for r in range(ROWS)])):
    exact = [sum(x[r] * W[r][c] for r in range(ROWS)) for c in range(COLS)]
    d, _ = t.product(x, analog=False)
    an, st = t.product(x, analog=True)
    cases[name] = dict(exact=exact, digital=d, analog=an, analog_minus_exact=[an[c] - exact[c] for c in range(COLS)], sat=st["sat"])
    print(name, "\n  exact  ", exact, "\n  digital", d, "\n  analog ", an, flush=True)
link.close()
if a.json:
    Path(a.json).write_text(json.dumps(dict(weights=W, cases=cases), indent=1))
