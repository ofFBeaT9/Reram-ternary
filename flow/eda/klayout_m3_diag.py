# Diagnostic for the KLayout BEOL deck (12 October 2026): batch 11 stalled for 8 h in the deck's first metal3 area rule
# (m3.with_area, sky130B_mr.drc line 1460) on the GDS of 11 October. Prints, per metal layer, shape counts and the size
# of the merged polygons (vertex and hole counts), first for the top cell's own shapes, then for the whole hierarchy.
# usage: klayout -b -r klayout_m3_diag.py -rd gdsin=<file.gds>
import time
import pya

ly = pya.Layout()
ly.read(gdsin)  # noqa: F821  (defined by -rd)
top = ly.top_cell()
print("top cell", top.name, "dbu", ly.dbu, flush=True)
for name, (l, d) in (("met2", (69, 20)), ("met3", (70, 20)), ("met4", (71, 20))):
    li = ly.find_layer(l, d)
    if li is None:
        print(name, "absent"); continue
    for scope in ("top only", "hierarchy"):
        t = time.time()
        r = pya.Region(top.shapes(li)) if scope == "top only" else pya.Region(top.begin_shapes_rec(li))
        n = r.count()
        m = r.merged()
        mv = max((p.num_points() for p in m.each()), default=0)
        mh = max((p.holes() for p in m.each()), default=0)
        big = sorted(((p.num_points(), p.holes(), str(p.bbox())) for p in m.each()), reverse=True)[:3]
        print(f"{name} {scope}: shapes {n}, merged polygons {m.count()}, max vertices {mv}, max holes {mh}, "
              f"{time.time() - t:.1f} s; largest {big}", flush=True)
