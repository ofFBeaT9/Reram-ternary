#!/bin/bash
# PC batch 29d (reram-eda image, /w), 9 November 2026: batch 29's mutation test found that the fault "LOCK does not hide PITER" survived:
# under revision 4.9 a program command under LOCK is refused and clears PITER, so the test bench's check read 0 either way. The test bench
# now programs row 31 before LOCK and reads PITER right after LOCK. Waits for batch 29's mutation runs to end, then runs every test bench
# and every mutation campaign again with the new test bench (results overwrite batch 29's).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29d; mkdir -p $O; rm -f $O/V.txt
until grep -q "chip 1of3 rc" /w/flow/eda/batch29/M.txt 2>/dev/null; do sleep 30; done
NP=$(nproc); J=$((NP > 4 ? NP - 2 : 2)); echo "cores $NP, jobs $J" | tee $O/info.txt
md5sum rtl/*.sv rtl/chip/*.sv tb/tb_tcim.cc tb/mutation_test.py tb/chip/mutation_chip.py > $O/md5_inputs.txt
( make rtl > $O/rtl.log 2>&1; echo "rtl rc=$?" >> $O/V.txt ) &
( make rtl-pnx > $O/rtl_pnx.log 2>&1; echo "rtl-pnx rc=$?" >> $O/V.txt ) &
( make rtl-1of3 > $O/rtl_1of3.log 2>&1; echo "rtl-1of3 rc=$?" >> $O/V.txt ) &
( make rtl-chip > $O/rtl_chip.log 2>&1; echo "rtl-chip rc=$?" >> $O/V.txt ) &
( make rtl-chip-1of3 > $O/rtl_chip_1of3.log 2>&1; echo "rtl-chip-1of3 rc=$?" >> $O/V.txt ) &
( make rtl-verilator > $O/rtl_vl.log 2>&1; echo "rtl-verilator rc=$?" >> $O/V.txt ) &
wait
cat $O/V.txt
mut() {   # mut <tag> <env...>: every fault of that build, then the merged file results/rtl_mutation<tag>.json
  local T=$1; shift
  local N=$(env "$@" python3 tb/mutation_test.py count)
  rm -f results/rtl_mutation${T}_*_*.json
  seq 0 $((N - 1)) | xargs -P $J -I{} env "$@" python3 tb/mutation_test.py {} {} > $O/mut${T}.log 2>&1
  python3 - "$T" "$N" <<'PY'
import json, re, sys
from pathlib import Path
T, N = sys.argv[1], int(sys.argv[2]); R = Path("/w/results")
parts = [p for p in R.glob(f"rtl_mutation{T}_*_*.json") if re.fullmatch(rf"rtl_mutation{re.escape(T)}_\d+_\d+\.json", p.name)]
rows = {r["id"]: r for p in parts for r in json.loads(p.read_text())}
res = [rows[k] for k in sorted(rows)]; miss = [k for k in range(N) if k not in rows]
bad = [dict(id=r["id"], name=r["name"], status=r["status"]) for r in res if r["status"] != "caught"]
(R / f"rtl_mutation{T}.json").write_text(json.dumps(dict(test_bench="tb/tb_tcim.cc (revision 4.9, PC batch 29)", faults=N, run=len(res),
    detected=len(res) - len(bad), not_detected=bad, missing=miss, results=res), indent=1))
print(T, len(res) - len(bad), "of", N, "caught; missing", miss, "; not caught", bad)
for p in parts: p.unlink()
PY
}
mut "" > $O/M.txt
mut "_pnx" TB_ENC=pnx >> $O/M.txt
mut "_1of3full" TB_CELL=1of3full >> $O/M.txt
NC=$(python3 tb/chip/mutation_chip.py count)
seq 0 $((NC - 1)) | xargs -P $J -I{} python3 tb/chip/mutation_chip.py {} {} > $O/mut_chip.log 2>&1
python3 - "$NC" <<'PY' >> $O/M.txt
import json, sys
from pathlib import Path
N = int(sys.argv[1]); R = Path("/w/results/sky130_chip")
res = sorted((r for k in range(N) if (R / f"mutation_chip_{k}_{k}.json").exists() for r in json.loads((R / f"mutation_chip_{k}_{k}.json").read_text())["results"]), key=lambda r: r["id"])
(R / "mutation_chip.json").write_text(json.dumps(dict(faults=N, run=len(res), detected=sum(r["status"] == "caught" for r in res), results=res), indent=1))
for k in range(N): (R / f"mutation_chip_{k}_{k}.json").unlink(missing_ok=True)
print("chip", sum(r["status"] == "caught" for r in res), "of", N, "caught")
PY
CHIP_CELL=1of3 python3 tb/chip/mutation_chip.py > $O/mut_chip_1of3.log 2>&1; echo "chip 1of3 rc=$?" >> $O/M.txt
cat $O/M.txt
python3 tools/collect_rev49.py > $O/summary.txt 2>&1
echo B29D_DONE
