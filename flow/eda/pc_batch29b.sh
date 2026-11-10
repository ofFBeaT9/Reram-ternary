#!/bin/bash
# PC batch 29b (reram-eda image, /w), 9 November 2026: batch 29's safety_1of3 failed on a property written before the erase existed
# (the Z device set only for a PDATA weight 0; an erase writes weight 0 whatever PDATA holds). The property is now scoped to program
# commands (rtl/tcim_core.sv, FORMAL block only). Waits until batch 29 has tried its 3T3R proof faults, then runs safety_1of3 again
# and the 3T3R planted faults (one more: an erase that sends reset pulses to Z).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29; until grep -q "faults 1of3 rc" $O/F.txt 2>/dev/null; do sleep 30; done
md5sum rtl/tcim_core.sv formal/check_faults.py > $O/md5_29b.txt
D=/tmp/f_s13b; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv $D/rtl/; cp formal/*.sby formal/*.sv $D/formal/
(cd $D/formal && timeout 30000 sby -f tcim_core.sby safety_1of3 > /w/results/next_chip/formal_1of3.log 2>&1; echo "safety_1of3 (29b) rc=$?" >> $O/F29b.txt)
FAULTS=1of3 JOBS=4 python3 formal/check_faults.py > $O/faults_1of3_29b.log 2>&1; echo "faults 1of3 (29b) rc=$?" >> $O/F29b.txt
tail -n 2 $O/faults_1of3_29b.log; cat $O/F29b.txt
echo B29B_DONE
