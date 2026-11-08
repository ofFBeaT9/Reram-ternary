#!/bin/bash
# PC batch 28, part F (reram-eda image, /w), 7 November 2026, revision 4.7 with the restructured properties: every formal task
# side by side, each in its own copy (tasks of one .sby file must not share a folder), then the planted faults (24 at a time).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch28; mkdir -p $O results/security
md5sum rtl/*.sv formal/*.sv formal/*.sby formal/check_faults.py Makefile > $O/md5_formal_inputs.txt
run() {   # run <name> <sby file> <task> <log>
  local D=/tmp/f_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv $D/rtl/; cp formal/*.sby formal/*.sv $D/formal/
  (cd $D/formal && timeout 30000 sby -f $2 ${3:+$3} > $4 2>&1; echo "$1 rc=$?" >> $O/F.txt)
}
rm -f $O/F.txt
run spi tcim_spi.sby "" $O/spi.log &
run safety tcim_core.sby safety $O/safety.log &
run safety_pnx tcim_core.sby safety_pnx $O/safety_pnx.log &
run progress tcim_core.sby progress $O/progress.log &
run lfsr tcim_core.sby lfsr $O/lfsr.log &
run miter tcim_miter.sby prove /w/results/security/miter_prove.log &
run miter_pnx tcim_miter.sby prove_pnx /w/results/security/miter_prove_pnx.log &
wait
cat $O/spi.log $O/safety.log $O/safety_pnx.log $O/progress.log $O/lfsr.log > results/formal.log
cat $O/F.txt; grep -h "DONE" results/formal.log results/security/miter_*.log
JOBS=24 python3 formal/check_faults.py > $O/faults.log 2>&1; echo "faults rc=$?" >> $O/F.txt
tail -n 3 $O/faults.log
echo FORMAL28_DONE
