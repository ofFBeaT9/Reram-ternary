#!/bin/bash
# Run inside openroad/orfs:26Q4-71-g9b26ff8ff with the repository at /w (flow/eda/pc_batch3.bat).
# 1. platform copy: /w/flow/orfs/platforms_b/sky130hd = ORFS sky130hd with
#      TECH_LEF  -> sky130B libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
#      LIB_FILES -> sky130B libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib
#    The RC table of the platform (setRC.tcl) stays the sky130A one: the variant changes the via1 and metal2 heights,
#    which this table does not describe; noted in the results.
# 2. full flow (synthesis to routing, DRC) of flow/orfs/sky130hd_b/config.mk, then an export for the sandbox
set -e
cd /w; mkdir -p /tmp/pdk; tar xzf export/pdk_sky130B.tgz -C /tmp/pdk
P=/w/flow/orfs/platforms_b/sky130hd; mkdir -p /w/flow/orfs/platforms_b; [ -d $P ] && mv $P $P.old.$$
cp -rL /OpenROAD-flow-scripts/flow/platforms/sky130hd $P          # -L: the platform holds symbolic links (rcx rules)
B=/tmp/pdk/sky130B/libs.ref/sky130_fd_sc_hd
cp $B/techlef/sky130_fd_sc_hd__nom.tlef $P/lef/sky130_fd_sc_hd_b.tlef
cp $B/lib/sky130_fd_sc_hd__ss_100C_1v60.lib $P/lib/
grep -n "TECH_LEF\|LIB_FILES" $P/config.mk
sed -i -e 's#^export TECH_LEF .*#export TECH_LEF = $(PLATFORM_DIR)/lef/sky130_fd_sc_hd_b.tlef#' \
       -e 's#^export LIB_FILES ?=.*#export LIB_FILES = $(PLATFORM_DIR)/lib/sky130_fd_sc_hd__ss_100C_1v60.lib#' $P/config.mk
grep -n "TECH_LEF\|LIB_FILES" $P/config.mk
echo "=== technology LEF, sky130A (platform) against sky130B:"; diff -w /OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef $P/lef/sky130_fd_sc_hd_b.tlef | head -80 || true
cd /OpenROAD-flow-scripts/flow
source ../env.sh > /dev/null 2>&1 || true
M="make DESIGN_CONFIG=/w/flow/orfs/sky130hd_b/config.mk PLATFORM_HOME=/w/flow/orfs/platforms_b WORK_HOME=/w/flow/orfs/out44b TCIM_FLOW=/w/flow/orfs"
$M && echo "=== drc" && $M drc || echo FLOW_FAILED
cd /w/flow/orfs/out44b && mkdir -p /w/flow/orfs/export && tar czf /w/flow/orfs/export/out44b_sky130hd.tgz logs reports \
   results/sky130hd/tcim_top/base/6_final.v results/sky130hd/tcim_top/base/6_final.sdc results/sky130hd/tcim_top/base/6_final.spef \
   /w/flow/orfs/platforms_b/sky130hd/config.mk && echo "=== exported"
