"""Scale every capacitance and resistance of a SPEF file, for a parasitic-sensitivity check of the timing.
OpenROAD-flow-scripts extracts the parasitics once (OpenRCX, typical RC corner). Re-timing with all R and C
scaled by 0.8 (fast wires: a best-case stand-in for the hold check) and 1.2 (slow wires, setup check) bounds how
much the result depends on the extraction corner. usage: spef_scale.py in.spef out.spef factor"""
import re, sys

src, dst, k = sys.argv[1], sys.argv[2], float(sys.argv[3])
sec = None
num = re.compile(r"^(\s*\d+\s+\S+(?:\s+\S+)?\s+)([-+0-9.eE]+)(\s*)$")
with open(src) as f, open(dst, "w") as g:
    for line in f:
        s = line.strip()
        if s.startswith("*CAP"):
            sec = "c"
        elif s.startswith("*RES"):
            sec = "r"
        elif s.startswith("*END") or s.startswith("*CONN") or s.startswith("*D_NET"):
            sec = None
        if s.startswith("*D_NET"):           # total net capacitance
            p = line.split()
            p[-1] = f"{float(p[-1]) * k:.6g}"
            g.write(" ".join(p) + "\n"); continue
        if sec in ("c", "r") and not s.startswith("*"):
            m = num.match(line.rstrip("\n"))
            if m:
                g.write(f"{m.group(1)}{float(m.group(2)) * k:.6g}{m.group(3)}\n"); continue
        g.write(line)
