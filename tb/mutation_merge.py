"""Join the part files written by tb/mutation_test.py into results/rtl_mutation<TAG>.json and print a summary.
Usage: python3 tb/mutation_merge.py [TAG]        (exit status 1 if a fault was not detected or a part is missing)"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tb"))
tag = sys.argv[1] if len(sys.argv) > 1 else ""
import re

parts = sorted(p for p in (ROOT / "results").glob(f"rtl_mutation{tag}_*.json") if re.fullmatch(rf"rtl_mutation{re.escape(tag)}_\d+_\d+\.json", p.name))
rows = {}
for p in parts:
    for r in json.loads(p.read_text()):
        rows[r["id"]] = r
src = (ROOT / "tb" / "mutation_test.py").read_text()
main_list, pnx_list = src.split("\nMP = [")                    # MP: the faults that only matter in the BSD-PNX code
n_total = len(re.findall(r'^    \("', main_list, re.M)) + (len(re.findall(r'^    \("', pnx_list, re.M)) if tag == "_pnx" else 0)
missing = [k for k in range(n_total) if k not in rows]
res = [rows[k] for k in sorted(rows)]
caught = [r for r in res if r["status"] == "caught"]
other = [r for r in res if r["status"] != "caught"]
bench = {"": "tb/tb_tcim.cc", "_pnx": "tb/tb_tcim.cc, RTL and test bench built with TCIM_ENC_PNX"}.get(tag, "revision 3 (tb/build/tb_rev3_failfast.cc)")
out = dict(test_bench=bench, faults=n_total, run=len(res), detected=len(caught),
           not_detected=[dict(id=r["id"], name=r["name"], status=r["status"]) for r in other], missing=missing, results=res)
(ROOT / "results" / f"rtl_mutation{tag}.json").write_text(json.dumps(out, indent=1))
print(f"{len(caught)} of {n_total} faults detected" + (f"; missing runs: {missing}" if missing else ""))
for r in other:
    print(f"  {r['status']}: #{r['id']} {r['name']}")
if not missing:
    for p in parts:
        p.unlink()
sys.exit(1 if (other or missing) else 0)
