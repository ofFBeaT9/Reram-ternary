#!/bin/bash
# PC batch 25 (reram-eda image, repository at /w), 6 November 2026. The cloud sandbox's container (with its own yosys,
# Verilator and SymbiYosys builds) was reclaimed on 5 November before these runs of revision 4.6 finished, so they run
# here with the image's OSS CAD Suite (versions written to flow/eda/batch25/tools.txt):
#   G1 make rtl, make lint, make rtl-verilator        G2 make rtl-pnx
#   G3 make rtl-chip, make rtl-chip-verilator, tb/chip/mutation_chip.py
#   G4 gate-level runs of the routed block (batch 23) with the full test bench: as routed, xnor fault, icg fault
#   G5 formal/check_faults.py (all 22 faults; one fault rewritten after batch 24 because it did not elaborate)
#   G6 make equiv, make equiv-chip
# The precheck runs beside this in its own container (pc_batch24.sh, started by pc_batch25.bat).
cd /w
O=/w/flow/eda/batch25; rm -rf $O; mkdir -p $O
mkdir -p /tmp/bin && printf '#!/bin/bash\nexec /opt/oss-cad-suite/bin/yosys -m slang "$@"\n' > /tmp/bin/yosys && chmod +x /tmp/bin/yosys
export PATH=/tmp/bin:$PATH
VR=/opt/oss-cad-suite/share/verilator
if [ ! -x $VR/bin/verilator ]; then
  mkdir -p /tmp/vroot/bin && ln -sf /opt/oss-cad-suite/bin/verilator* /tmp/vroot/bin/ && ln -sf $VR/include /tmp/vroot/include; VR=/tmp/vroot; fi
export VERILATOR_ROOT=$VR SBY=sby
export SKY130_STDCELL_LIB=/opt/pdk/sky130B/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
{ yosys -V; $VERILATOR_ROOT/bin/verilator --version; sby --version 2>&1 | head -1; g++ --version | head -1; cat /opt/oss-cad-suite.url; } > $O/tools.txt 2>&1
yosys -q -p "read_slang --help" > /dev/null 2>&1 && echo "slang OK" >> $O/tools.txt || echo "slang MISSING" >> $O/tools.txt
md5sum rtl/*.sv rtl/chip/*.sv tb/tb_tcim.cc formal/check_faults.py flow/orfs/src/*.v > $O/md5_inputs.txt
rm -rf tb/build tb/build_pnx tb/build_chip tb/build_vl tb/build_vl_pnx tb/build_vl_chip
N=flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base/6_final.v
( make rtl > $O/rtl.log 2>&1; echo "rtl rc=$?" > $O/G1.txt; make lint > $O/lint.log 2>&1; echo "lint rc=$?" >> $O/G1.txt
  make rtl-verilator > $O/rtl_verilator.log 2>&1; echo "rtl-verilator rc=$?" >> $O/G1.txt ) &
( make rtl-pnx > $O/rtl_pnx.log 2>&1; echo "rtl-pnx rc=$?" > $O/G2.txt ) &
( make rtl-chip > $O/rtl_chip.log 2>&1; echo "rtl-chip rc=$?" > $O/G3.txt; make rtl-chip-verilator > $O/rtl_chip_vl.log 2>&1
  echo "rtl-chip-verilator rc=$?" >> $O/G3.txt; python3 tb/chip/mutation_chip.py > $O/mutation_chip.log 2>&1; echo "mutation_chip rc=$?" >> $O/G3.txt ) &
( bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls > results/sky130_chip/gls_chip_routed.log 2>&1; echo "gls rc=$?" > $O/G4.txt
  bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls_x xnor > results/sky130_chip/gls_chip_fault_xnor.log 2>&1; echo "gls xnor rc=$?" >> $O/G4.txt
  bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls_i icg > results/sky130_chip/gls_chip_fault_icg.log 2>&1; echo "gls icg rc=$?" >> $O/G4.txt ) &
( cd formal && for f in tcim_core.sby tcim_miter.sby; do grep -q '^plugin -i slang' $f || sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done
  cd /w && python3 formal/check_faults.py > $O/check_faults.log 2>&1; echo "check_faults rc=$?" > $O/G5.txt
  cd formal && for f in tcim_core.sby tcim_miter.sby; do sed -i '/^plugin -i slang$/d' $f; done ) &
( make equiv > $O/equiv.log 2>&1; echo "equiv rc=$?" > $O/G6.txt; make equiv-chip VERILATOR_ROOT=$VERILATOR_ROOT > $O/equiv_chip.log 2>&1; echo "equiv-chip rc=$?" >> $O/G6.txt ) &
wait
cat $O/G*.txt
grep -h "checks," results/rtl_test.log results/rtl_test_pnx.log results/rtl_test_verilator.log results/rtl_test_verilator_pnx.log \
   results/sky130_chip/rtl_chip_*.log results/sky130_chip/gls_chip_*.log
tail -n 2 $O/check_faults.log $O/mutation_chip.log
echo BATCH25_DONE
