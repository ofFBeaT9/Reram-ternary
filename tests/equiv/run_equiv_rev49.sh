#!/bin/bash
# Revision 4.9 (9 November 2026): which registers and outputs differ from the revision 4.8 logic (= 4.7, tests/equiv/rtl_rev48).
# Revision 4.9 changes the logic on purpose (programming refused under LOCK; read-back and the margin check's PDATA only
# for rows programmed since reset, new register r_wsr), so points are expected to stay unproven. The list shows WHICH.
# Both builds: the default cell and TCIM_CELL_1OF3. Writes results/rev49/equiv_vs_rev48*.{log,txt}.
set -e
cd "$(dirname "$0")/../.."
G=tests/equiv/rtl_rev48; O=results/rev49; mkdir -p $O tests/equiv/build
for B in default 1of3; do
  D=""; [ $B = 1of3 ] && D="-D TCIM_CELL_1OF3"
  cat > tests/equiv/build/eq49_$B.ys <<YS
read_slang $D --top tcim_core $G/tcim_pkg.sv $G/tcim_core.sv
proc; flatten; opt_clean; memory_map; opt -fast; async2sync; rename tcim_core gold; design -stash gold
read_slang $D --top tcim_core rtl/tcim_pkg.sv rtl/tcim_core.sv
proc; flatten; opt_clean; memory_map; opt -fast; async2sync; rename tcim_core gate; design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 1
equiv_induct -seq 1
equiv_status
YS
  yosys -q -l $O/equiv_vs_rev48_$B.log tests/equiv/build/eq49_$B.ys
  grep -F 'Unproven $equiv' $O/equiv_vs_rev48_$B.log | sed -E 's/^.*: \\([^ ]+)_gold.*$/\1/' | sed -E 's/\[[0-9]+\]$//' | sort -u > $O/equiv_vs_rev48_unproven_$B.txt || true
  echo "$B: $(grep -E 'Of those cells' $O/equiv_vs_rev48_$B.log | sed 's/^ *//'); unproven signals: $(tr '\n' ' ' < $O/equiv_vs_rev48_unproven_$B.txt)"
done
