#!/bin/bash
# PC batch 1 (10 October 2026), in the reram-eda image, repository mounted at /w:
#  1. Tang Nano 9K bitstream (rtl/fpga/pnr_fpga.sh)
#  2. export of the sky130B PDK parts and of magic/netgen (same Ubuntu 24.04 as the cloud sandbox) so that layout,
#     DRC, LVS and the read-path Monte Carlo can run in the sandbox
cd /w
mkdir -p export
echo "=== fpga"; bash rtl/fpga/pnr_fpga.sh > rtl/fpga/pnr_fpga.log 2>&1; tail -3 rtl/fpga/pnr_fpga.log
echo "=== versions"; cat /usr/local/magic.commit /usr/local/netgen.commit /opt/pdk.version
P=/opt/pdk/sky130B
du -sh $P/libs.tech/* $P/libs.ref/* 2>/dev/null
ls $P/libs.ref/sky130_fd_pr_reram $P/libs.ref/sky130_fd_sc_hd
tar czf export/pdk_sky130B.tgz -C /opt/pdk sky130B/libs.tech/magic sky130B/libs.tech/netgen sky130B/libs.tech/ngspice \
    sky130B/libs.tech/klayout sky130B/libs.ref/sky130_fd_pr_reram sky130B/libs.ref/sky130_fd_sc_hd/lib \
    sky130B/libs.ref/sky130_fd_sc_hd/lef sky130B/libs.ref/sky130_fd_sc_hd/techlef sky130B/SOURCES 2>&1 | tail -2
tar czf export/pdk_sky130A_tech.tgz -C /opt/pdk sky130A/libs.tech/magic sky130A/libs.tech/netgen sky130A/libs.ref/sky130_fd_sc_hd/techlef 2>&1 | tail -2
tar czf export/eda_tools.tgz /usr/local/bin/magic /usr/local/bin/netgen /usr/local/lib/magic /usr/local/lib/netgen \
    /usr/local/magic.commit /usr/local/netgen.commit /usr/lib/x86_64-linux-gnu/libtcl8.6.so* /usr/lib/x86_64-linux-gnu/libtk8.6.so* \
    /usr/share/tcltk /usr/lib/tcltk 2>&1 | tail -2
ls -l export
cd export && split -b 300000000 -d pdk_sky130B.tgz pdk_sky130B.part_ && ls -l
echo BATCH1_DONE
