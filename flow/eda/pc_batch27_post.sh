#!/bin/bash
# PC batch 27, part T (reram-eda image, /w), after part P: gate-level runs of the routed block (as routed, xnor fault, icg
# fault), the top level (top.py: LVS with a planted fault), Magic DRC and antenna (make signoff), the antenna cross-check,
# then ChipFoundry's precheck in their versions (pc_batch24.sh, with the local PDK mirror flow/eda/cfpdk_mirror).
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch27; mkdir -p $O
[ -d /w/chip/sky130/caravan_rev46 ] || cp -a /w/chip/sky130/caravan /w/chip/sky130/caravan_rev46
N=flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base/6_final.v
( bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls > results/sky130_chip/gls_chip_routed.log 2>&1; echo "gls rc=$?" > $O/G.txt
  bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls_x xnor > results/sky130_chip/gls_chip_fault_xnor.log 2>&1; echo "gls xnor rc=$?" >> $O/G.txt
  bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls_i icg > results/sky130_chip/gls_chip_fault_icg.log 2>&1; echo "gls icg rc=$?" >> $O/G.txt ) &
( cd layout/sky130/periph && python3 top.py > $O/top.log 2>&1; echo "top rc=$?" > $O/T.txt
  cd /w && make signoff > $O/signoff.log 2>&1; echo "signoff rc=$?" >> $O/T.txt
  gzip -c flow/orfs/outdig/antenna_openroad_verbose27.rpt > flow/eda/antenna_openroad_verbose27.rpt.gz; cp flow/orfs/outdig/antenna_openroad27.log flow/eda/
  XC_RPT=flow/eda/antenna_openroad_verbose27.rpt.gz XC_LOG=flow/eda/antenna_openroad27.log python3 layout/sky130/periph/antenna_crosscheck.py > $O/antx.log 2>&1
  echo "antenna crosscheck rc=$?" >> $O/T.txt ) &
wait
cat $O/G.txt $O/T.txt; tail -n 3 results/sky130_chip/gls_chip_*.log; tail -n 5 $O/top.log
grep -q "top rc=0" $O/T.txt && grep -q "signoff rc=0" $O/T.txt && bash /w/flow/eda/pc_batch24.sh > /w/flow/eda/pc_batch27_precheck.log 2>&1
grep -E '\[ *[0-9]+/14\]|PRECHECK|SIGNOFF' /w/flow/eda/pc_batch27_precheck.log
echo POST27_DONE
