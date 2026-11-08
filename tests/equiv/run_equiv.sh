#!/bin/bash
# Two proofs about the RTL (needs yosys with the slang front end). Writes results/equiv.log and results/equiv.json.
#  1. The conversion table equals its arithmetic definition for every 10-bit value, in both trit codes.
#  2. The present RTL in the default trit code against the reference RTL (tests/equiv/rtl_rev45 since revision 4.6;
#     tests/equiv/rtl_rev41 before): every
#     register and output is matched by name and an equivalence is attempted by induction. Revision 4.2 changed
#     the digital-product sequencer on purpose (one request per non-zero row, back to back), so this comparison is
#     expected to leave points unproven; it is run to show WHICH points, i.e. that the change is confined to the
#     product sequencer. The unproven signal names are written to results/equiv_unproven.txt.
#     (Revision 4.1 had proven the present logic equal to revision 4 at 2,410 points; tests/equiv/rtl_rev4 is kept.)
#     Revision 4.6 (security study, 4 November 2026) changed the product sequencer (fixed latency, rotated start, dummy
#     accumulators), the programming sequencer (constant time), and added SEC, MARG and the margin check, on purpose;
#     the reference was moved to the revision 4.5 RTL (the logic taped out on 12 October), so the unproven points
#     show exactly what revision 4.6 changed.
#  3. flow/orfs/src/tcim_top.v, the plain-Verilog copy handed to place and route, is the same logic as the RTL.
# The second proof covers the default code only. The BSD-PNX build has no earlier reference; it is covered by the
# test bench (make rtl-pnx) and the fault campaign (make mutation-pnx).
set -e
cd "$(dirname "$0")/../.."
R=rtl; G=tests/equiv/rtl_rev45; W=tests/equiv/build; mkdir -p $W
FILES="tcim_pkg.sv tcim_core.sv tcim_spi.sv tcim_top.sv"
: > results/equiv.log
for D in "" "-D TCIM_ENC_PNX"; do
  yosys -q -l $W/table.log -p "read_slang $D --top cmp $R/tcim_pkg.sv tests/equiv/table_vs_definition.sv; hierarchy -top cmp; proc; flatten; memory_map; opt; sat -prove ok 1 -verify"
  echo "table = definition, defines '$D': $(grep -o 'SUCCESS!\|FAIL!' $W/table.log | tail -1)" | tee -a results/equiv.log
done
cat > $W/eq.ys <<YS
read_slang --top tcim_top $(for f in $FILES; do printf '%s ' $G/$f; done)
hierarchy -top tcim_top; proc; flatten; opt_clean; memory_map; opt -fast; async2sync
rename tcim_top gold
design -stash gold
read_slang --top tcim_top $(for f in $FILES; do printf '%s ' $R/$f; done)
hierarchy -top tcim_top; proc; flatten; opt_clean; memory_map; opt -fast; async2sync
rename tcim_top gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 1
equiv_induct -seq 1
equiv_status
YS
yosys -q -l $W/eq.log $W/eq.ys
grep -E "Of those cells|Equivalence successfully proven" $W/eq.log | sed 's/^ *//' | tee -a results/equiv.log
grep -F 'Unproven $equiv' $W/eq.log | sed -E 's/^.*: \\([^ ]+)_gold.*$/\1/' | sort -u > results/equiv_unproven.txt || true
# 3. The plain-Verilog copy for place and route (flow/orfs/src/tcim_top.v) is the same logic as the RTL.
if [ -f flow/orfs/src/tcim_top.v ]; then
  sed -e "s#^read_slang --top tcim_top $(for f in $FILES; do printf '%s ' $G/$f; done)#read_slang --top tcim_top $(for f in $FILES; do printf '%s ' $R/$f; done)#" \
      -e "0,/^read_slang/! s#^read_slang .*#read_verilog flow/orfs/src/tcim_top.v#" $W/eq.ys > $W/eq_orfs.ys
  sed -i 's/^equiv_status$/equiv_status -assert/' $W/eq_orfs.ys
  yosys -q -l $W/eq_orfs.log $W/eq_orfs.ys
  echo "place-and-route source: $(grep -E 'Of those cells' $W/eq_orfs.log | sed 's/^ *//')" | tee -a results/equiv.log
fi
python3 - <<'PY'
import json, re
t = open("results/equiv.log").read()
m = re.search(r"Of those cells (\d+) are proven and (\d+) are unproven", t)
json.dump(dict(table_equals_definition_default="defines '': SUCCESS!" in t, table_equals_definition_pnx="TCIM_ENC_PNX': SUCCESS!" in t,
               reference="tests/equiv/rtl_rev45 (the RTL of revision 4.5, on the 12 October chip); differences expected in the product and programming sequencers and the new registers (revisions 4.6 and 4.7)",
               unproven_signals=open("results/equiv_unproven.txt").read().split(), equivalence_points=int(m.group(1)) + int(m.group(2)),
               proven=int(m.group(1)), unproven=int(m.group(2)),
               place_and_route_source=(lambda q: dict(proven=int(q.group(1)), unproven=int(q.group(2))) if q else None)(
                   re.search(r"place-and-route source: Of those cells (\d+) are proven and (\d+) are unproven", t))),
          open("results/equiv.json", "w"), indent=1)
PY
