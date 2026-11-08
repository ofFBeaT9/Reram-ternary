#!/bin/bash
# PC batch 15 (openroad/orfs:26Q4-71-g9b26ff8ff, repository at /w), 12 October 2026: place and route of tcim_chip_digital
# again from scratch, the same as batch 7 plus a second antenna repair with a 40 % margin after detailed routing
# (flow/orfs/sky130hd_chip/post_drt.tcl), then DRC, abstract, export, and OpenROAD's antenna check with every ratio.
cd /w/flow/orfs/outdig && rm -rf results/sky130hd/tcim_chip_digital logs/sky130hd/tcim_chip_digital \
   reports/sky130hd/tcim_chip_digital objects/sky130hd/tcim_chip_digital
bash /w/flow/eda/pc_batch7.sh
R=/w/flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base
grep -h "TCIM_POST_DRT\|GRT-0015\|ANT-000" /w/flow/orfs/outdig/logs/sky130hd/tcim_chip_digital/base/5_2_route.log
cd /OpenROAD-flow-scripts/flow && source ../env.sh > /dev/null 2>&1 || true
printf 'read_db %s/6_final.odb\ncheck_antennas -verbose -report_file /w/flow/eda/antenna_openroad_verbose15.rpt\n' $R > /tmp/a.tcl
openroad -exit -no_init /tmp/a.tcl 2>&1 | grep "ANT-" | tee /w/flow/eda/antenna_openroad15.log
echo BATCH15_DONE
