#!/bin/bash
# PC batch 29, part V (reram-eda image, /w), 9 November 2026: verification of revision 4.9 (locked at reset, erase of the whole
# array to unlock, programming refused under LOCK, LOCK held in three flip-flops). Everything side by side on the PC's cores:
#  1. test benches: both trit codes, 3T3R build, chip build (3 settings) and its 3T3R build, Verilator, serial-port fuzzing
#  2. mutation tests, one fault per process: default, BSD-PNX, 3T3R with every fault; controller faults of the chip build
#  3. formal: every task in its own copy (tasks of one .sby must not share a folder), then the planted faults
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29; mkdir -p $O results/security results/next_chip results/sky130_chip; rm -f $O/V.txt $O/F.txt
NP=$(nproc); J=$((NP > 4 ? NP - 2 : 2)); echo "cores $NP, jobs $J" | tee $O/info.txt
md5sum rtl/*.sv rtl/chip/*.sv tb/tb_tcim.cc tb/mutation_test.py tb/chip/mutation_chip.py formal/*.sby formal/*.sv formal/check_faults.py Makefile > $O/md5_inputs.txt
make tb/vectors/net_x.txt > /dev/null 2>&1
# ---- 1. test benches (each target has its own build folder; fuzz reuses tb/build, so it follows make rtl)
( make rtl > $O/rtl.log 2>&1; echo "rtl rc=$?" >> $O/V.txt; make fuzz > $O/fuzz.log 2>&1; echo "fuzz rc=$?" >> $O/V.txt ) &
( make rtl-pnx > $O/rtl_pnx.log 2>&1; echo "rtl-pnx rc=$?" >> $O/V.txt ) &
( make rtl-1of3 > $O/rtl_1of3.log 2>&1; echo "rtl-1of3 rc=$?" >> $O/V.txt ) &
( make rtl-chip > $O/rtl_chip.log 2>&1; echo "rtl-chip rc=$?" >> $O/V.txt ) &
( make rtl-chip-1of3 > $O/rtl_chip_1of3.log 2>&1; echo "rtl-chip-1of3 rc=$?" >> $O/V.txt ) &
( make rtl-verilator > $O/rtl_vl.log 2>&1; echo "rtl-verilator rc=$?" >> $O/V.txt ) &
( make lint > results/rev49/lint.log 2>&1; echo "lint rc=$?" >> $O/V.txt; make equiv > $O/equiv.log 2>&1; echo "equiv rc=$?" >> $O/V.txt
  bash tests/equiv/run_equiv_rev49.sh > $O/equiv49.log 2>&1; echo "equiv49 rc=$?" >> $O/V.txt ) &
wait
cat $O/V.txt
# ---- 3. formal, base proofs (side by side with the mutation test below)
run() {   # run <name> <sby file> <task> <log>
  local D=/tmp/f_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv $D/rtl/; cp formal/*.sby formal/*.sv $D/formal/
  (cd $D/formal && timeout 30000 sby -f $2 ${3:+$3} > $4 2>&1; echo "$1 rc=$?" >> $O/F.txt)
}
( run spi tcim_spi.sby "" $O/spi.log &
  run safety tcim_core.sby safety $O/safety.log &
  run safety_pnx tcim_core.sby safety_pnx $O/safety_pnx.log &
  run progress tcim_core.sby progress $O/progress.log &
  run lfsr tcim_core.sby lfsr $O/lfsr.log &
  run safety_1of3 tcim_core.sby safety_1of3 /w/results/next_chip/formal_1of3.log &
  run miter tcim_miter.sby prove /w/results/security/miter_prove.log &
  run miter_pnx tcim_miter.sby prove_pnx /w/results/security/miter_prove_pnx.log &
  wait
  cat $O/spi.log $O/safety.log $O/safety_pnx.log $O/progress.log $O/lfsr.log > results/formal.log
  JOBS=8 python3 formal/check_faults.py > $O/faults.log 2>&1; echo "faults rc=$?" >> $O/F.txt
  FAULTS=1of3 JOBS=3 python3 formal/check_faults.py > $O/faults_1of3.log 2>&1; echo "faults 1of3 rc=$?" >> $O/F.txt
  echo FORMAL_DONE >> $O/F.txt ) &
FPID=$!
# ---- 2. mutation tests, one fault per process
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
wait $FPID
cat $O/F.txt; grep -h "DONE" results/formal.log results/next_chip/formal_1of3.log results/security/miter_*.log; tail -n 2 $O/faults.log $O/faults_1of3.log
python3 tools/collect_rev49.py > $O/summary.txt 2>&1
echo VERIFY29_DONE
