#!/bin/bash
# PC batch 29k (reram-eda image, /w), 9 November 2026: batch 29i showed the safety task closes with every revision 4.9 property but the
# lemmas (A, B, C pass in 61-81 min) and stays open with the lemmas (D, E). So the full set without lemmas (F, the run that counts), and
# with only the two simple lemmas (G); the same for safety_pnx, progress and safety_1of3 without lemmas.
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29k; mkdir -p $O; rm -f $O/F.txt
md5sum rtl/tcim_core.sv formal/tcim_core.sby > $O/md5_inputs.txt
var() {   # var <name> <task> <selection to remove> <log>
  local D=/tmp/k2_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv $D/rtl/; cp formal/tcim_core.sby $D/formal/
  sed -i "s/^\[files\]$/$2: chformal -remove $3\n\n[files]/" $D/formal/tcim_core.sby
  local t0=$(date +%s)
  (cd $D/formal && timeout 20000 sby -f tcim_core.sby $2 > $4 2>&1; echo "$1 rc=$? $(( $(date +%s) - t0 )) s" >> $O/F.txt)
}
var F safety "c:l49_*" $O/safety.log &
var G safety "c:l49_rows* c:l49_last c:l49_fin c:l49_all c:l49_idle" $O/safety_G.log &
var Fp safety_pnx "c:l49_*" $O/safety_pnx.log &
var Fq progress "c:l49_*" $O/progress.log &
var F3 safety_1of3 "c:l49_*" $O/safety_1of3.log &
wait
cat $O/F.txt
echo B29K_DONE
