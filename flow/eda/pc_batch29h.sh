#!/bin/bash
# PC batch 29h (reram-eda image, /w), 9 November 2026: in batch 29g the PDR tasks still added about one clause per frame. Two more
# lemmas in rtl/tcim_core.sv (the row in hand is verified when it finishes; after an erase every row is). Each PDR task now runs a
# portfolio in parallel, first to finish wins: abc pdr and k-induction (smtbmc yices, depth 40).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29h; mkdir -p $O; rm -f $O/F.txt
W=/tmp/w29h; rm -rf $W; mkdir -p $W/results/security $W/results/next_chip $W/formal $W/rtl
cp rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv $W/rtl/; cp formal/*.sby formal/*.sv formal/check_faults.py $W/formal/
for t in safety safety_pnx progress safety_1of3; do sed -i "s/^$t: abc pdr$/$t: abc pdr\n$t: smtbmc yices/" $W/formal/tcim_core.sby; done
sed -i "s/^mode prove$/mode prove\nsafety: depth 40\nsafety_pnx: depth 40\nprogress: depth 40\nsafety_1of3: depth 40/" $W/formal/tcim_core.sby
sed -i "s/^abc pdr$/abc pdr\nsmtbmc yices/" $W/formal/tcim_miter.sby
grep -n "pdr\|smtbmc\|depth" $W/formal/tcim_core.sby $W/formal/tcim_miter.sby > $O/engines.txt
md5sum $W/rtl/*.sv $W/formal/* > $O/md5_inputs.txt
run() {   # run <name> <sby file> <task> <log>
  local D=/tmp/k_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp $W/rtl/*.sv $D/rtl/; cp $W/formal/*.sby $W/formal/*.sv $D/formal/
  (cd $D/formal && timeout 30000 sby -f $2 ${3:+$3} > $4 2>&1; echo "$1 rc=$?" >> $O/F.txt)
}
run spi tcim_spi.sby "" $O/spi.log &
run safety tcim_core.sby safety $O/safety.log &
run safety_pnx tcim_core.sby safety_pnx $O/safety_pnx.log &
run progress tcim_core.sby progress $O/progress.log &
run lfsr tcim_core.sby lfsr $O/lfsr.log &
run lock tcim_core.sby lock $O/lock.log &
run safety_1of3 tcim_core.sby safety_1of3 $W/results/next_chip/formal_1of3.log &
run miter tcim_miter.sby prove $W/results/security/miter_prove.log &
run miter_pnx tcim_miter.sby prove_pnx $W/results/security/miter_prove_pnx.log &
wait
cat $O/spi.log $O/safety.log $O/safety_pnx.log $O/progress.log $O/lfsr.log $O/lock.log > $W/results/formal.log
cat $O/F.txt; grep -h "DONE" $W/results/formal.log $W/results/next_chip/formal_1of3.log $W/results/security/miter_*.log
cd $W && JOBS=16 python3 formal/check_faults.py > $O/faults.log 2>&1; echo "faults rc=$?" >> $O/F.txt
FAULTS=1of3 JOBS=4 python3 formal/check_faults.py > $O/faults_1of3.log 2>&1; echo "faults 1of3 rc=$?" >> $O/F.txt
tail -n 1 $O/faults.log $O/faults_1of3.log
if [ $(grep -c "rc=0" $O/F.txt) -eq 11 ]; then
  cp $W/results/formal.log $W/results/formal_faults.json /w/results/; cp $W/results/next_chip/formal_1of3.log $W/results/next_chip/formal_faults_1of3.json /w/results/next_chip/
  cp $W/results/security/miter_prove.log $W/results/security/miter_prove_pnx.log /w/results/security/; echo "COPIED to results" >> $O/F.txt
fi
cat $O/F.txt
cd /w && python3 tools/collect_rev49.py > $O/summary.txt 2>&1
echo B29H_DONE
