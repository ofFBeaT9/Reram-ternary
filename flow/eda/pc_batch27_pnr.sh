#!/bin/bash
# PC batch 27, part P (openroad/orfs:26Q4-71-g9b26ff8ff, /w), 6 November 2026, revision 4.7: place and route of
# tcim_chip_digital (same die as revision 4.5/4.6; a taller die only if that fails), antenna check, export; then timing
# after layout at every corner (post_corners.sh, min_period.py with the corner libraries in flow/eda/sky130libs, made by
# tools/make_sky130_corner_libs.sh) and collect_chip_digital.py. The revision 4.6 run is kept in flow/orfs/outdig_rev46.
[ -d /w/flow/orfs/outdig_rev46 ] || cp -a /w/flow/orfs/outdig /w/flow/orfs/outdig_rev46
command -v sta > /dev/null || { mkdir -p /tmp/bin; printf '#!/bin/bash\nexec openroad "$@"\n' > /tmp/bin/sta; chmod +x /tmp/bin/sta; export PATH=/tmp/bin:$PATH; }
pnr() {
  local W=$1; shift
  mkdir -p $W && cd $W && rm -rf results/sky130hd/tcim_chip_digital logs/sky130hd/tcim_chip_digital \
     reports/sky130hd/tcim_chip_digital objects/sky130hd/tcim_chip_digital
  cd /OpenROAD-flow-scripts/flow && source ../env.sh > /dev/null 2>&1 || true
  local M=(make DESIGN_CONFIG=/w/flow/orfs/sky130hd_chip/config.mk PLATFORM_HOME=/w/flow/orfs/platforms_b WORK_HOME=$W TCIM_FLOW=/w/flow/orfs "$@")
  "${M[@]}" && echo "=== drc" && "${M[@]}" drc && echo "=== abstract" && ("${M[@]}" generate_abstract || echo ABSTRACT_FAILED) || { echo "FLOW_FAILED $W"; return 1; }
  local RR=results/sky130hd/tcim_chip_digital/base
  grep -h "TCIM_POST_DRT\|GRT-0015\|ANT-000" $W/logs/sky130hd/tcim_chip_digital/base/5_2_route.log
  printf 'read_db %s/6_final.odb\ncheck_antennas -verbose -report_file %s/antenna_openroad_verbose27.rpt\n' $W/$RR $W > /tmp/a.tcl
  openroad -exit -no_init /tmp/a.tcl 2>&1 | grep "ANT-" | tee $W/antenna_openroad27.log
  echo "=== exported $(basename $W)"
}
md5sum /w/flow/orfs/src/tcim_chip_digital.v /w/flow/orfs/sky130hd_chip/config.mk
pnr /w/flow/orfs/outdig || { pnr /w/flow/orfs/outdig_tall "DIE_AREA=0 0 550.32 419.155" "CORE_AREA=16.1 16.32 534.06 402.56"; echo TALL_DIE_USED; }
cd /w && L=/w/flow/eda/sky130libs W=/w/flow/orfs/outdig
DESIGN=tcim_chip_digital bash flow/orfs/post/post_corners.sh sky130hd $W $L 2>&1 | tail -n 12
rm -f $W/min_period.jsonl
for k in 1 1.2; do DESIGN=tcim_chip_digital python3 flow/orfs/post/min_period.py sky130hd $W $L/sky130_fd_sc_hd__ss_100C_1v60.lib $k | tee -a $W/min_period.jsonl; done
python3 flow/orfs/post/collect_chip_digital.py | head -n 30
cd /w/flow/orfs/outdig && tar czf /w/flow/orfs/export/outdig27.tgz logs reports antenna_openroad27.log antenna_openroad_verbose27.rpt min_period.jsonl post_*.rpt \
   results/sky130hd/tcim_chip_digital/base/6_final.v results/sky130hd/tcim_chip_digital/base/6_final.sdc \
   results/sky130hd/tcim_chip_digital/base/6_final.spef results/sky130hd/tcim_chip_digital/base/6_final.def $(ls results/sky130hd/tcim_chip_digital/base/*.lef 2>/dev/null)
echo PNR27_DONE
