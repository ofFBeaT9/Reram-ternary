#!/bin/bash
# PC batch 29j (reram-eda image, /w), 9 November 2026: batch 29's timing miter found two copies that differ at step 6,270: an erase whose
# verify answers (secret in the miter) differ leaves one copy locked and the other unlocked. The LOCK state is public (STAT.WERR, SEC.LOCK),
# so formal/tcim_miter.sv now assumes both copies hold the same LOCK. Both miters again (FORMAL_ANYLOCK, abc pdr and k-induction).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29j; mkdir -p $O; rm -f $O/F.txt
md5sum rtl/tcim_core.sv formal/tcim_miter.sv formal/tcim_miter.sby > $O/md5_inputs.txt
run() {
  local D=/tmp/j_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv $D/rtl/; cp formal/tcim_miter.sby formal/tcim_miter.sv $D/formal/
  sed -i "s/^abc pdr$/abc pdr\nsmtbmc yices/" $D/formal/tcim_miter.sby
  local t0=$(date +%s)
  (cd $D/formal && timeout 30000 sby -f tcim_miter.sby $1 > $O/miter_$1.log 2>&1; echo "$1 rc=$? $(( $(date +%s) - t0 )) s" >> $O/F.txt)
}
run prove & run prove_pnx & wait
cat $O/F.txt; grep -h "DONE" $O/miter_*.log
echo B29J_DONE
