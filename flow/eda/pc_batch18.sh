#!/bin/bash
# PC batch 18 (reram-eda image), 12 October 2026: the "progress" proof of tcim_core.sby in its own copy of the folders,
# in parallel with batch 14 (which proves the tasks one after another and is still on safety_pnx). A separate copy has
# its own task database, so the two runs do not interfere.
mkdir -p /tmp/x && cp -r /w/rtl /tmp/x/rtl && mkdir -p /tmp/x/formal && cp /w/formal/tcim_core.sby /tmp/x/formal/
cd /tmp/x/formal
yosys -q -p "read_slang --help" > /dev/null 2>&1 || sed -i "s/^\[script\]$/[script]\nplugin -i slang/" tcim_core.sby
md5sum /tmp/x/rtl/tcim_pkg.sv /tmp/x/rtl/tcim_core.sv
sby -f tcim_core.sby progress > /w/flow/eda/formal18_progress.log 2>&1
echo "SBY_RC=$?"
grep "DONE" /w/flow/eda/formal18_progress.log
echo BATCH18_DONE
