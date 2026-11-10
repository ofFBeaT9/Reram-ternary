#!/bin/bash
# PC batch 29i (reram-eda image, /w), 9 November 2026: which revision 4.9 property keeps PDR from closing? The safety task (FORMAL_ANYLOCK,
# abc pdr) with subsets of the new properties (labels p49_* and lemmas l49_* in rtl/tcim_core.sv), side by side; plus progress with none.
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29i; mkdir -p $O; rm -f $O/F.txt
md5sum rtl/tcim_core.sv formal/tcim_core.sby > $O/md5_inputs.txt
var() {   # var <name> <task> <selection to remove>
  local D=/tmp/v_$1; rm -rf $D; mkdir -p $D/formal $D/rtl; cp rtl/tcim_pkg.sv rtl/tcim_core.sv $D/rtl/; cp formal/tcim_core.sby $D/formal/
  sed -i "s/^\[files\]$/$2: chformal -remove $3\n\n[files]/" $D/formal/tcim_core.sby
  local t0=$(date +%s)
  (cd $D/formal && timeout 10800 sby -f tcim_core.sby $2 > $O/$1.log 2>&1; echo "$1 rc=$? $(( $(date +%s) - t0 )) s" >> $O/F.txt)
}
var A safety "c:p49_* c:l49_*" &
var B safety "c:l49_* c:p49_unlock c:p49_end c:p49_order*" &
var C safety "c:l49_* c:p49_unlock c:p49_noprog c:p49_nordbk c:p49_erzero" &
var D safety "c:p49_order* c:p49_end c:p49_noprog c:p49_nordbk c:p49_erzero" &
var E safety "c:p49_unlock" &
var P progress "c:p49_* c:l49_*" &
wait
cat $O/F.txt
echo B29I_DONE
