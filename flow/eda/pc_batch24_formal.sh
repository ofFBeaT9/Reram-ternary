#!/bin/bash
# PC batch 24, part 2 (reram-eda image, repository at /w), 5 November 2026: the formal proofs of revision 4.6, run beside
# the precheck. Each task gets its own copy of the .sby file (never two tasks of one .sby file in parallel: they share a
# status database), so the slow BSD-PNX safety proof runs alongside the others. Then the injected faults
# (formal/check_faults.py -> results/formal_faults.json). Logs: flow/eda/formal24/.
cd /w/formal
L=/w/flow/eda/formal24; rm -rf $L; mkdir -p $L
yosys -q -p "read_slang --help" > /dev/null 2>&1 || {
  echo "read_slang needs the plugin: loading it in the .sby files"
  for f in tcim_spi.sby tcim_core.sby tcim_miter.sby; do sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done; }
cp tcim_core.sby tcim_core_b.sby; cp tcim_core.sby tcim_core_c.sby
( sby -f tcim_core.sby safety_pnx > $L/safety_pnx.log 2>&1 ) &
( sby -f tcim_core_b.sby safety > $L/safety.log 2>&1 ) &
( sby -f tcim_core_c.sby progress > $L/progress.log 2>&1 ) &
( sby -f tcim_spi.sby > $L/spi.log 2>&1; sby -f tcim_miter.sby prove > $L/miter_prove.log 2>&1; sby -f tcim_miter.sby prove_pnx > $L/miter_prove_pnx.log 2>&1 ) &
( cd /w && SBY=sby python3 formal/check_faults.py > $L/check_faults.log 2>&1 ) &
wait
grep -h "DONE\|summary: Elapsed clock" $L/*.log
tail -n 2 $L/check_faults.log
rm -f tcim_core_b.sby tcim_core_c.sby
for f in tcim_spi.sby tcim_core.sby tcim_miter.sby; do sed -i '/^plugin -i slang$/d' $f; done
echo FORMAL24_DONE
