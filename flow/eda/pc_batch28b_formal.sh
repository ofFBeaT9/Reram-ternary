#!/bin/bash
# PC batch 28b (reram-eda image, /w), 7 November 2026: the lfsr task again with depth 20 (at depth 3 its planted fault was not
# caught: the base case ended at step 3, where the fault first shows), results/formal.log rebuilt from batch 28's logs and this
# one, then every planted fault again (24 at a time).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch28; md5sum rtl/*.sv formal/*.sv formal/*.sby formal/check_faults.py Makefile > $O/md5_formal_inputs_28b.txt
D=/tmp/f_lfsr; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv $D/rtl/; cp formal/*.sby formal/*.sv $D/formal/
(cd $D/formal && sby -f tcim_core.sby lfsr > $O/lfsr.log 2>&1; echo "lfsr28b rc=$?" >> $O/F.txt)
cat $O/spi.log $O/safety.log $O/safety_pnx.log $O/progress.log $O/lfsr.log > results/formal.log
grep -h "DONE" results/formal.log results/security/miter_*.log
cp $O/faults.log $O/faults_28_depth3.log; cp results/formal_faults.json $O/formal_faults_28_depth3.json 2>/dev/null
JOBS=24 python3 formal/check_faults.py > $O/faults.log 2>&1; echo "faults28b rc=$?" >> $O/F.txt
tail -n 3 $O/faults.log
echo FORMAL28B_DONE
