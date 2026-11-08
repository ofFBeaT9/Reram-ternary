#!/bin/bash
# Gate-level test of a routed netlist: the full RTL test bench (tb/tb_tcim.cc) on Verilator,
# with each standard cell modelled from the "function" and flip-flop groups of its Liberty file (Yosys read_liberty).
# Zero-delay: checks the logic of the routed netlist, not its timing (timing: sta_post.tcl).
# usage: gls.sh <6_final.v> <liberty> <work dir> [fault]
#   fault = "xnor": the first sg13g2_xnor2_1 instance becomes sg13g2_xor2_1, to show that the test detects a
#   one-gate change in the netlist (expected result: TEST FAILED).
#   fault = "icg": the enable of the first clock-gating cell is tied to 0, so its flip-flops never load
#   (expected result: TEST FAILED). Clock-gating cells are simulated with flow/orfs/post/icg_models.v.
# needs: yosys, VERILATOR_ROOT; run from the repository root.
set -u
NET=$1; LIB=$2; W=$3; FAULT=${4:-}
mkdir -p "$W"
cp "$NET" "$W/net.v"
if [ "$FAULT" = xnor ]; then sed -i '0,/sg13g2_xnor2_1 /s//sg13g2_xor2_1 /' "$W/net.v"; fi
if [ "$FAULT" = icg ]; then
  python3 - "$W/net.v" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
m = re.search(r"(sg13g2_s?lgcp_\d|sky130_fd_sc_hd__s?dlclkp_\d)\s+\S+\s*\((.*?)\);", s, re.S)
assert m, "no clock-gating cell in the netlist"
body = re.sub(r"\.GATE\s*\([^)]*\)", ".GATE(1'b0)", m.group(2), count=1)
s = s[:m.start(2)] + body + s[m.end(2):]
open(p, "w").write(s); print("icg fault in", m.group(0)[:80].replace("\n", " "))
PY
fi
D=$(cd "$(dirname "$0")" && pwd)
yosys -q -l "$W/flatten.log" -p "read_verilog $D/icg_models.v; proc; read_liberty -ignore_miss_func -ignore_miss_dir -ignore_redef $LIB; read_verilog $W/net.v; hierarchy -top tcim_top; proc; flatten; opt_clean; write_verilog -noattr $W/gl_flat.v"
$VERILATOR_ROOT/bin/verilator --cc --exe --build -j 2 -O3 -Wno-fatal -Wno-lint -Wno-style --top-module tcim_top \
  -Mdir "$W/obj" -CFLAGS "-std=c++17 -O1 -I$PWD/tb/verilator" "$W/gl_flat.v" tb/tb_tcim.cc -o tb_gls > "$W/build.log" 2>&1
echo BUILD=$? >> "$W/build.log"
# with a fault the run stops at the first failure (TB_FAIL_FAST), as in the mutation test
if [ -n "$FAULT" ]; then export TB_FAIL_FAST=1; fi
"$W/obj/tb_gls" tb/vectors > "$W/tb_gls.log" 2>&1
echo EXIT=$? >> "$W/tb_gls.log"
tail -3 "$W/tb_gls.log"
