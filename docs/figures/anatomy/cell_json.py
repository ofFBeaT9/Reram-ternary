"""Writes cell.json for the isometric figures: the rr2t2r rectangles (GDS) and sky130B layer heights (Magic tech file)."""
import json, sys
sys.path.insert(0, "/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/page")
import layers
names = {(65, 20): "diff", (65, 44): "tap", (66, 20): "poly", (66, 44): "licon", (67, 20): "li1", (67, 44): "mcon",
         (68, 20): "met1", (68, 44): "via1", (201, 20): "reram", (69, 20): "met2"}
out = dict(rects={n: layers.R[k] for k, n in names.items()}, z={k: list(v) for k, v in layers.Z.items()},
           rr_split=layers.Z["via1"][1] - 0.20, source="layout/sky130/tcim_sky130_array.gds (rr2t2r); sky130B.tech heights")
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(out["z"], out["rr_split"])
