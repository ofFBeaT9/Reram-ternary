#!/bin/bash
# PC batch 23, part 2 (reram-eda image, repository at /w): nextpnr of the revision 4.6 FPGA netlist
# (rtl/fpga/build_rev46/tcim_fpga_syn.json, built by tb/fpga/run_fpga_checks.sh with FPGA_BUILD=rtl/fpga/build_rev46).
# The design is near the GW1NR-9's placement limit; up to three placement seeds are tried. The board bitstream of
# revision 4.5 (rtl/fpga/build) is not touched.
export FPGA_BUILD=rtl/fpga/build_rev46 FPGA_RESULTS=results/fpga/rev46
for s in 1 2 3; do
  echo "=== seed $s"
  if SEED=$s bash /w/rtl/fpga/pnr_fpga.sh; then echo "PLACED_WITH_SEED=$s"; break; fi
  cp /w/results/fpga/rev46/nextpnr.log /w/results/fpga/rev46/nextpnr_seed$s.log 2>/dev/null
done
grep -E "LUT4:|DFF:|ALU" /w/results/fpga/rev46/nextpnr.log | head -n 6
echo FPGA23_DONE
