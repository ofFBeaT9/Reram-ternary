#!/bin/bash
# PC batch 20 (reram-eda image, repository at /w), 12 October 2026: copies of the parts of ChipFoundry's pinned PDK
# (open_pdks 3e0e31d, ciel, ChipFoundry's release site) that the chip sign-off reads, for the sandbox: the sky130B
# standard-cell GDS, SPICE and LEF, the ReRAM library, and the Magic, netgen and KLayout technology files.
# Batch 19 found that ChipFoundry's LVS (that PDK) expects the tie cell conb_1 with 0.045 um poly resistors, while the GDS
# carries the 0.5 um version of open_pdks 1e35547.
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install ciel > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
export CIEL_DATA_SOURCE=static-web:https://chipfoundry.github.io/ciel-releases
/tmp/v/bin/ciel enable 3e0e31dcce8519a7dbb82590346db16d91b7244f --pdk-root /opt/cfpdk --pdk sky130A > /tmp/ciel.log 2>&1 || tail -20 /tmp/ciel.log
O=/w/flow/eda/cfpdk_3e0e31d; rm -rf $O; mkdir -p $O/sky130B/libs.ref $O/sky130B/libs.tech
cp /opt/cfpdk/sky130B/SOURCES $O/sky130B/ 2>/dev/null
cp -r /opt/cfpdk/sky130B/libs.ref/sky130_fd_sc_hd $O/sky130B/libs.ref/
cp -r /opt/cfpdk/sky130B/libs.ref/sky130_fd_pr_reram $O/sky130B/libs.ref/ 2>/dev/null || echo "no sky130_fd_pr_reram in libs.ref"
cp -r /opt/cfpdk/sky130B/libs.tech/magic /opt/cfpdk/sky130B/libs.tech/netgen /opt/cfpdk/sky130B/libs.tech/klayout $O/sky130B/libs.tech/
ls /opt/cfpdk/sky130B/libs.ref; du -sh $O
find /opt/cfpdk/sky130B -iname "*reram*" | head -20
echo BATCH20_DONE
