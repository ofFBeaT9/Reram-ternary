#!/bin/bash
# PC batch 28c (reram-eda image, /w), 7 November 2026: ChipFoundry's precheck again on the batch 28 GDS (in batch 28 the
# container could not reach archive.ubuntu.com, KLayout's dependencies were missing and the XOR check failed).
cd /w && bash /w/flow/eda/pc_batch24.sh > /w/flow/eda/pc_batch28_precheck.log 2>&1
grep -E '\[ *[0-9]+/14\]|PRECHECK|SIGNOFF|KLAYOUT' /w/flow/eda/pc_batch28_precheck.log
echo PRECHECK28C_DONE
