#!/bin/bash
# PC batch 29c (reram-eda image, /w), 9 November 2026: batch 29's precheck failed Magic DRC (met3.2 x8) and KLayout BEOL (m3.2 x4)
# at two channel tracks above the revision 4.9 block, where a block pin lies within 1.2 um of the macro pin above it and the 0.4 um
# track between the two via pads left 0.1 um notches. top.py now fills such gaps at the pads' height. Rebuild the top level, then
# sign-off, the antenna cross-check and ChipFoundry's precheck again.
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch29; mkdir -p $O
md5sum layout/sky130/periph/top.py flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base/6_final.def > $O/md5_29c.txt
( cd layout/sky130/periph && python3 top.py > $O/top_29c.log 2>&1; echo "top rc=$?" > $O/T29c.txt )
make signoff > $O/signoff_29c.log 2>&1; echo "signoff rc=$?" >> $O/T29c.txt
XC_RPT=flow/eda/antenna_openroad_verbose29.rpt.gz XC_LOG=flow/eda/antenna_openroad29.log python3 layout/sky130/periph/antenna_crosscheck.py > $O/antx_29c.log 2>&1
echo "antenna crosscheck rc=$?" >> $O/T29c.txt
python3 -c "import json;d=json.load(open('results/sky130_chip/top_signoff.json'));print('drc_markers',d['drc_markers'],'antenna',d['antenna_violation_count'])" >> $O/T29c.txt
cat $O/T29c.txt; tail -n 3 $O/top_29c.log
bash /w/flow/eda/pc_batch24.sh > /w/flow/eda/pc_batch29c_precheck.log 2>&1
grep -E '\[ *[0-9]+/14\]|PRECHECK|SIGNOFF|Violation' /w/flow/eda/pc_batch29c_precheck.log
echo B29C_DONE
