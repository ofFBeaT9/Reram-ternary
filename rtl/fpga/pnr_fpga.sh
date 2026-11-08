#!/bin/bash
# Place, route and pack the Tang Nano 9K bitstream from the netlist synthesized in the sandbox
# (tb/fpga/run_fpga_checks.sh writes rtl/fpga/build/tcim_fpga_syn.json; that netlist passed the gate-level host test).
#   docker run --rm -v <repo>:/w reram-eda bash /w/rtl/fpga/pnr_fpga.sh
set -e
cd /w
O=${FPGA_BUILD:-rtl/fpga/build}; R=${FPGA_RESULTS:-results/fpga}; mkdir -p $R
echo "seed ${SEED:-1}" > $R/pnr_seed.txt; nextpnr-himbaechel --version > $R/pnr_tools.txt 2>&1; which gowin_pack openFPGALoader >> $R/pnr_tools.txt
nextpnr-himbaechel --json $O/tcim_fpga_syn.json --write $O/tcim_fpga_pnr.json --device GW1NR-LV9QN88PC6/I5 \
    --vopt family=GW1N-9C --vopt cst=rtl/fpga/tangnano9k.cst --freq 13.5 --pre-pack rtl/fpga/clocks.py --seed ${SEED:-1} \
    --report $R/nextpnr_report.json -l $R/nextpnr.log
gowin_pack -d GW1N-9C -o $O/tcim_fpga.fs $O/tcim_fpga_pnr.json
sha256sum $O/tcim_fpga.fs $O/tcim_fpga_syn.json > $R/bitstream_sha256.txt
ls -l $O/tcim_fpga.fs >> $R/bitstream_sha256.txt
echo PNR_DONE
