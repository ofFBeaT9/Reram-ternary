"""Shortest clock period at which the routed block meets setup and hold at one library corner (post-route, extracted
parasitics, optionally scaled). The flow's SDC is rewritten for each period: create_clock -period P and the input and
output delays at 30 % of P (the assumption of flow/orfs/<platform>/constraint.sdc). Bisection to 0.05 ns.
usage: min_period.py <platform> <work dir> <liberty> [spef scale k] [lo_ns hi_ns]
Prints one JSON line; with a work dir written by post_corners.sh, k=0.8/1.2 use its spef_k<k> folder."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

D = Path(__file__).resolve().parent
plat, work, lib = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
k = sys.argv[4] if len(sys.argv) > 4 else "1"
lo, hi = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (8.0, 40.0)
base = work / f"results/{plat}/{os.environ.get('DESIGN', 'tcim_top')}/base"
src = base if k in ("1", "1.0") else work / f"spef_k{k}"
sdc0 = (base / "6_final.sdc").read_text()
tmp = Path(tempfile.mkdtemp())
for f in ("6_final.v", "6_final.spef"):
    os.symlink((src / f).resolve(), tmp / f)


def slack(p):
    s = re.sub(r"create_clock -name clk -period [0-9.]+", f"create_clock -name clk -period {p:.4f}", sdc0)
    s = re.sub(r"(set_(input|output)_delay) [0-9.]+ ", lambda m: f"{m.group(1)} {0.3 * p:.4f} ", s)
    (tmp / "6_final.sdc").write_text(s)
    out = subprocess.run(["sta", "-no_init", "-exit", str(D / "sta_post.tcl")], capture_output=True, text=True,
                         env=dict(os.environ, POST_LIB=lib, POST_DIR=str(tmp))).stdout
    g = lambda key: float(re.search(rf"@@ {key} (\S+)", out).group(1)) * 1e9
    return g("setup_wns"), g("hold_wns")


s_hi = slack(hi)
assert s_hi[0] >= 0, f"fails even at {hi} ns: {s_hi}"
while hi - lo > 0.05:
    mid = (lo + hi) / 2
    if slack(mid)[0] >= 0:
        hi = mid
    else:
        lo = mid
s = slack(hi)
shutil.rmtree(tmp)
print(json.dumps(dict(platform=plat, liberty=Path(lib).name, spef_scale=float(k), min_period_ns=round(hi, 2),
                      f_max_MHz=round(1000 / hi, 1), setup_wns_ns=round(s[0], 3), hold_wns_ns=round(s[1], 3))))
