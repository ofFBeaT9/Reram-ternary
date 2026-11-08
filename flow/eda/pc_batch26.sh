#!/bin/bash
# PC batch 26 (reram-eda image, repository at /w), 6 November 2026, after the council review of revision 4.6:
# two properties added (NOSHUF start row, back-to-back read requests) with a fault each, header comments corrected, make
# formal now stops on a failed proof and runs the miter, check_faults refuses to count faults without passing base proofs,
# the gate-level xnor fault moved off the dummy accumulators. Runs with the image's OSS CAD Suite:
#   F  make formal (spi, safety, safety_pnx, progress, both miter tasks, then the 24 faults)   -> results/formal.log, ...
#   S  make rtl, make rtl-pnx, make equiv, make equiv-chip (the RTL file changed in comments and FORMAL code only)
#   G  gate-level run of the routed block with the xnor fault
#   P  ReRAM library commit of the PDK the design was drawn with (/opt/pdk, open_pdks 1e35547)
cd /w
O=/w/flow/eda/batch26; rm -rf $O; mkdir -p $O
mkdir -p /tmp/bin && printf '#!/bin/bash\nexec /opt/oss-cad-suite/bin/yosys -m slang "$@"\n' > /tmp/bin/yosys && chmod +x /tmp/bin/yosys
export PATH=/tmp/bin:$PATH
VR=/opt/oss-cad-suite/share/verilator
if [ ! -x $VR/bin/verilator ]; then
  mkdir -p /tmp/vroot/bin && ln -sf /opt/oss-cad-suite/bin/verilator* /tmp/vroot/bin/ && ln -sf $VR/include /tmp/vroot/include; VR=/tmp/vroot; fi
export VERILATOR_ROOT=$VR SBY=sby
export SKY130_STDCELL_LIB=/opt/pdk/sky130B/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
{ yosys -V; $VERILATOR_ROOT/bin/verilator --version; sby --version 2>&1 | head -1; } > $O/tools.txt 2>&1
md5sum rtl/*.sv rtl/chip/*.sv tb/tb_tcim.cc formal/*.sv formal/*.sby formal/check_faults.py tb/mutation_test.py flow/orfs/src/*.v \
   flow/orfs/post/gls_chip.sh Makefile > $O/md5_inputs.txt
grep -h '"sky130_fd_pr_reram"' /opt/pdk/sky130B/.config/nodeinfo.json > $O/pdk_reram_commit.txt 2>&1; cat /opt/pdk/sky130B/SOURCES >> $O/pdk_reram_commit.txt 2>&1
N=flow/orfs/outdig/results/sky130hd/tcim_chip_digital/base/6_final.v
( cd formal && for f in tcim_spi.sby tcim_core.sby tcim_miter.sby; do grep -q '^plugin -i slang' $f || sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done
  cd /w && make formal > $O/formal.log 2>&1; echo "formal rc=$?" > $O/F.txt
  cd formal && for f in tcim_spi.sby tcim_core.sby tcim_miter.sby; do sed -i '/^plugin -i slang$/d' $f; done ) &
( rm -rf tb/build tb/build_pnx; make rtl > $O/rtl.log 2>&1; echo "rtl rc=$?" > $O/S.txt; make rtl-pnx > $O/rtl_pnx.log 2>&1; echo "rtl-pnx rc=$?" >> $O/S.txt
  make equiv > $O/equiv.log 2>&1; echo "equiv rc=$?" >> $O/S.txt; make equiv-chip VERILATOR_ROOT=$VERILATOR_ROOT > $O/equiv_chip.log 2>&1; echo "equiv-chip rc=$?" >> $O/S.txt ) &
( bash flow/orfs/post/gls_chip.sh $N $SKY130_STDCELL_LIB /tmp/gls_x xnor > results/sky130_chip/gls_chip_fault_xnor.log 2>&1; echo "gls xnor rc=$?" > $O/G.txt ) &
wait
cat $O/F.txt $O/S.txt $O/G.txt
grep -h "DONE" results/formal.log results/security/miter_*.log
tail -n 1 $O/formal.log
grep -h "checks," results/rtl_test.log results/rtl_test_pnx.log; tail -n 3 results/sky130_chip/gls_chip_fault_xnor.log
echo BATCH26_DONE
