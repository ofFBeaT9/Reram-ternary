#!/bin/bash
# PC batch 13, part 1 (openroad/orfs image, repository at /w), 12 October 2026: OpenROAD's antenna check of the routed
# chip block, every net with its ratios (-verbose), and the nets of the four gates Magic's antenna check flags
# (layout/sky130/periph/signoff.py; instances located from Magic's gate coordinates).
cd /OpenROAD-flow-scripts/flow
source ../env.sh > /dev/null 2>&1 || true
R=/w/flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base
cat > /tmp/ant.tcl <<TCL
read_db $R/6_final.odb
check_antennas -verbose -report_file /w/flow/eda/antenna_openroad_verbose.rpt
set block [ord::get_db_block]
foreach n {_09982_ _10531_ _12789_ _10755_ _10756_} {
  set i [\$block findInst \$n]
  if {\$i eq "NULL"} { puts "INST \$n not found"; continue }
  foreach it [\$i getITerms] {
    set net [\$it getNet]
    if {\$net ne "NULL"} { puts "INST \$n [[\$i getMaster] getName] [[\$it getMTerm] getName] [\$net getName]" }
  }
}
TCL
openroad -exit -no_init /tmp/ant.tcl 2>&1 | tee /w/flow/eda/antenna_openroad.log | grep -v "^\[INFO ODB" | tail -40
echo ORFS13_DONE
