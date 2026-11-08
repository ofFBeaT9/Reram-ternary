#!/bin/bash
# PC batch 23 (openroad/orfs:26Q4-71-g9b26ff8ff, repository at /w), 4 November 2026, revision 4.6 (security study):
#  1. mutation test of TCIM0, both trit codes (pack from tb/mutation_remote.py gen: flow/eda/mutpack23.tgz), in the
#     background on 24 cores
#  2. place and route of tcim_chip_digital from scratch, the same as batch 17 (batch 7 + antenna repair after detailed
#     routing), then DRC, abstract, OpenROAD's antenna check and export
#     (flow/orfs/export/outdig.tgz; outdig_tall.tgz if the fallback die was needed).
# The revision 4.5 results stay in flow/orfs/outdig_rev45 (not touched here).
echo "=== mutation (background)"
( cd /w/flow/eda && rm -rf mutpack23 && tar xzf mutpack23.tgz && \
  nice python3 mutpack23/mutation_remote.py run mutpack23 24 > mutation23.log 2>&1; echo MUTATION_EXIT=$? >> mutation23.log ) &
MUTPID=$!
echo "=== place and route"
# The die of revision 4.5 is kept (config.mk), so that top.py connects the block as before. If that does not route,
# a taller die (same width, 142 rows instead of 114) is tried in flow/orfs/outdig_tall, for which top.py must change.
pnr() {   # $1 work folder, then extra make arguments (VAR=value, each one word)
  local W=$1; shift
  mkdir -p $W && cd $W && rm -rf results/sky130hd/tcim_chip_digital logs/sky130hd/tcim_chip_digital \
     reports/sky130hd/tcim_chip_digital objects/sky130hd/tcim_chip_digital
  cd /OpenROAD-flow-scripts/flow && source ../env.sh > /dev/null 2>&1 || true
  local M=(make DESIGN_CONFIG=/w/flow/orfs/sky130hd_chip/config.mk PLATFORM_HOME=/w/flow/orfs/platforms_b WORK_HOME=$W TCIM_FLOW=/w/flow/orfs "$@")
  "${M[@]}" && echo "=== drc" && "${M[@]}" drc && echo "=== abstract" && ("${M[@]}" generate_abstract || echo ABSTRACT_FAILED) || { echo "FLOW_FAILED $W"; return 1; }
  local RR=results/sky130hd/tcim_chip_digital/base
  grep -h "TCIM_POST_DRT\|GRT-0015\|ANT-000" $W/logs/sky130hd/tcim_chip_digital/base/5_2_route.log
  printf 'read_db %s/6_final.odb\ncheck_antennas -verbose -report_file %s/antenna_openroad_verbose23.rpt\n' $W/$RR $W > /tmp/a.tcl
  openroad -exit -no_init /tmp/a.tcl 2>&1 | grep "ANT-" | tee $W/antenna_openroad23.log
  cd $W && mkdir -p /w/flow/orfs/export && tar czf /w/flow/orfs/export/$(basename $W).tgz logs reports antenna_openroad23.log \
     antenna_openroad_verbose23.rpt $RR/6_final.v $RR/6_final.sdc $RR/6_final.spef $RR/6_final.gds $RR/6_final.def $(ls $RR/*.lef 2>/dev/null) \
     && echo "=== exported $(basename $W)"
}
[ -d /w/flow/orfs/outdig_rev45 ] || cp -a /w/flow/orfs/outdig /w/flow/orfs/outdig_rev45   # keep the taped-out run
md5sum /w/flow/orfs/src/tcim_chip_digital.v /w/flow/orfs/sky130hd_chip/config.mk
pnr /w/flow/orfs/outdig || pnr /w/flow/orfs/outdig_tall "DIE_AREA=0 0 550.32 419.155" "CORE_AREA=16.1 16.32 534.06 402.56"
echo "=== waiting for the mutation test"
wait $MUTPID
tail -3 /w/flow/eda/mutation23.log
cd /w/flow/eda && tar czf mutres23.tgz mutpack23/*.json mutation23.log && echo "=== mutation exported"
echo BATCH23_DONE
