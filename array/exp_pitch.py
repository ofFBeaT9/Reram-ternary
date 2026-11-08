"""E5 (audit): does the assumed row pitch matter? The tile model assumes 2.0 um along the bit line. A count of
the transistor layout rules (model/cell_footprint.py) gives a lower bound of 1.085 um. Shorter bit-line segments
have less resistance, so the assumed pitch should be the pessimistic one. This runs the thin-metal wiring case
(the one most sensitive to wire resistance) and the TopMetal1 case at both pitches.
Writes results/array_pitch.json."""
import sys, json
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import exp_analog_error as E

fp = json.load(open(__file__.rsplit('/', 2)[0] + "/results/cell_footprint.json"))
out = {}
for name in ("A: BL Metal2-5 0.4um, SL Metal2-5 1um, one end", "B: BL TopMetal1, SL Metal2-5 1um, one end"):
    for pitch in (2.0, fp["row_pitch_um"]):
        key = f"{name} | row pitch {pitch:g} um"
        E.WIRING[key] = dict(E.WIRING[name], row_pitch_um=pitch)
        r = E.run("LRS3", key, None, 1.0)
        out[key] = r
        print(f"{key}: uncalibrated rms {r['raw']['rms']:.3f}, calibrated rms {r['cal']['rms']:.3f}", flush=True)
json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/array_pitch.json", "w"), indent=1)
