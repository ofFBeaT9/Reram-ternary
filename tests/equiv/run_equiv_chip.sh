#!/bin/bash
# The SKY130 chip's logic (12 October 2026). Needs yosys with the slang front end and Verilator.
#  1. Lint of the chip RTL (Verilator, all warnings), top tcim_chip_digital.
#  2. flow/orfs/src/tcim_chip_digital.v, the plain-Verilog copy handed to place and route, is the same logic as the RTL
#     (rtl/tcim_*.sv + rtl/chip/*.sv): every register and output matched by name, equivalence by induction, must prove all.
# Writes results/sky130_chip/equiv_chip.log.
set -e
cd "$(dirname "$0")/../.."
VL=${VERILATOR:-verilator}
RTLF="rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv rtl/tcim_top.sv rtl/chip/tcim_actl.sv rtl/chip/tcim_chip_core.sv rtl/chip/tcim_chip_digital.sv"
W=tests/equiv/build; mkdir -p $W results/sky130_chip
L=results/sky130_chip/equiv_chip.log
$VL --lint-only -Wall --top-module tcim_chip_digital $RTLF > $W/lint_chip.log 2>&1 && echo "lint (Verilator -Wall, tcim_chip_digital): 0 warnings" | tee $L \
  || { echo "lint (Verilator -Wall, tcim_chip_digital): FAILED" | tee $L; cat $W/lint_chip.log; exit 1; }
cat > $W/eq_chip.ys <<YS
read_slang --top tcim_chip_digital $RTLF
hierarchy -top tcim_chip_digital; proc; flatten; opt_clean; memory_map; opt -fast; async2sync
rename tcim_chip_digital gold
design -stash gold
read_verilog flow/orfs/src/tcim_chip_digital.v
hierarchy -top tcim_chip_digital; proc; flatten; opt_clean; memory_map; opt -fast; async2sync
rename tcim_chip_digital gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 1
equiv_induct -seq 1
equiv_status -assert
YS
yosys -q -l $W/eq_chip.log $W/eq_chip.ys
echo "place-and-route source of the chip block: $(grep -E 'Of those cells' $W/eq_chip.log | sed 's/^ *//')" | tee -a $L
md5sum rtl/chip/*.sv flow/orfs/src/tcim_chip_digital.v | tee -a $L
