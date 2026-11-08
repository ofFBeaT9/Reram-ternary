#!/bin/bash
# PC batch 7 (openroad/orfs:26Q4-71-g9b26ff8ff, repository at /w): place and route of tcim_chip_digital for the SKY130 chip
# with the sky130B platform copy of batch 3 (flow/orfs/platforms_b), then DRC, abstract LEF and export.
set -e
cd /OpenROAD-flow-scripts/flow
source ../env.sh > /dev/null 2>&1 || true
M="make DESIGN_CONFIG=/w/flow/orfs/sky130hd_chip/config.mk PLATFORM_HOME=/w/flow/orfs/platforms_b WORK_HOME=/w/flow/orfs/outdig TCIM_FLOW=/w/flow/orfs"
$M && echo "=== drc" && $M drc && echo "=== abstract" && ($M generate_abstract || echo ABSTRACT_FAILED) || echo FLOW_FAILED
R=/w/flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base
cd /w/flow/orfs/outdig && mkdir -p /w/flow/orfs/export && tar czf /w/flow/orfs/export/outdig.tgz logs reports \
   results/sky130hd/tcim_chip_digital/base/6_final.v results/sky130hd/tcim_chip_digital/base/6_final.sdc \
   results/sky130hd/tcim_chip_digital/base/6_final.spef results/sky130hd/tcim_chip_digital/base/6_final.gds \
   results/sky130hd/tcim_chip_digital/base/6_final.def $(ls $R/*.lef 2>/dev/null) && echo "=== exported"
echo BATCH7_DONE
