#!/bin/bash
# PC batch 14 (reram-eda image, repository at /w), 12 October 2026: the formal proofs one task after another.
# Batch 12 started the three tasks of tcim_core.sby in parallel; they share the task's status database and two of them
# (safety_pnx, progress) stopped with "No such file or directory: .../tcim_core/status.sqlite" before proving anything.
cd /w/formal
yosys -q -p "read_slang --help" > /dev/null 2>&1 || {
  echo "read_slang needs the plugin: loading it in copies of the .sby files"
  for f in tcim_spi.sby tcim_core.sby; do sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done; }
( sby -f tcim_spi.sby && sby -f tcim_core.sby safety && sby -f tcim_core.sby safety_pnx && sby -f tcim_core.sby progress ) > /w/flow/eda/formal14.log 2>&1
echo "SBY_RC=$?"
grep "DONE" /w/flow/eda/formal14.log
for f in tcim_spi.sby tcim_core.sby; do sed -i '/^plugin -i slang$/d' $f; done
echo BATCH14_DONE
