#!/bin/bash
# Gate-level test of the routed digital block of the SKY130 chip (tcim_chip_digital, 11 October 2026): the chip build of
# the test bench (tb/tb_tcim.cc -DTCIM_CHIP, line-level macro model with its electrical and timing checks) on a Verilator
# model of the routed netlist (shim tb/verilator/tcim_chip_core.h). Each standard cell is modelled from the "function" and
# flip-flop groups of its Liberty
# file (Yosys read_liberty); clock-gating cells from icg_models.v. Zero-delay: logic of the routed netlist, not timing.
# The tie outputs (tie_hi / tie_lo, the pad controls) are checked by the test bench through TCIM_CHIP_TIES.
# usage: gls_chip.sh <6_final.v> <liberty> <work dir> [fault]      fault = xnor | icg (expected result: TEST FAILED)
# TB_CFG ("ts,tp,tr") is passed through; default 1,1,0 as in the RTL run.
set -u
NET=$1; LIB=$2; W=$3; FAULT=${4:-}
mkdir -p "$W"
cp "$NET" "$W/net.v"
if [ "$FAULT" = xnor ]; then
  # the first xnor2_1 whose output reaches a flip-flop other than the dummy accumulators (revision 4.6, 6 November 2026:
  # the first xnor2_1 of the revision 4.6 netlist feeds only d_acc[216], which by design has no effect on any result, so
  # changing it was unobservable, not missed; batch 25)
  python3 - "$W/net.v" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
insts = list(re.finditer(r"^\s*(sky130_fd_sc_hd__\S+)\s+(\S+)\s*\((.*?)\);", s, re.M | re.S))
loads, ff = {}, {}
for m in insts:
    c, name, body = m.group(1), m.group(2), m.group(3)
    pins = dict((a, n.strip()) for a, n in re.findall(r"\.(\w+)\(([^)]*)\)", body))
    outs = [pins[k] for k in ("X", "Y", "Q", "Q_N", "GCLK", "COUT", "SUM") if k in pins]
    for k, n in pins.items():
        if n in outs: continue
        loads.setdefault(n, []).append((c, name, outs))
def reaches_real_ff(net):
    seen, todo = set(), [net]
    while todo:
        n = todo.pop()
        if n in seen: continue
        seen.add(n)
        for c, name, outs in loads.get(n, []):
            if "__df" in c or "__sdf" in c:
                if "d_acc" not in name: return True
            else: todo.extend(outs)
    return False
for m in insts:
    if m.group(1) == "sky130_fd_sc_hd__xnor2_1":
        y = re.search(r"\.Y\(([^)]*)\)", m.group(3)).group(1).strip()
        if reaches_real_ff(y):
            s = s[:m.start(1)] + s[m.start(1):m.end(1)].replace("xnor2_1", "xor2_1") + s[m.end(1):]
            open(p, "w").write(s); print("xnor fault in", m.group(2), "output", y); break
PY
fi
if [ "$FAULT" = icg ]; then
  # the clock gate with the most flip-flops behind it (the first one in the file gates only s_sat, which never changes on
  # the chip because it has no converter: a fault there is unobservable, not missed)
  python3 - "$W/net.v" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
cells = list(re.finditer(r"(sky130_fd_sc_hd__s?dlclkp_\d)\s+(\S+)\s*\((.*?)\);", s, re.S))
assert cells, "no clock-gating cell in the netlist"
insts = [(c, b) for c, b in re.findall(r"^\s*(sky130_fd_sc_hd__\S+)\s+\S+\s*\((.*?)\);", s, re.M | re.S)]
loads = {}                                    # net -> list of (cell, output net or None)
for c, b in insts:
    pins = dict((a, n.strip()) for a, n in re.findall(r"\.(\w+)\(([^)]*)\)", b))
    if re.search(r"(clkbuf|clkdlybuf|buf|clkinv|inv)_", c) and "A" in pins:
        loads.setdefault(pins["A"], []).append((c, pins.get("X") or pins.get("Y")))
    elif "__df" in c and "CLK" in pins:
        loads.setdefault(pins["CLK"], []).append((c, None))
def fanout(m):
    todo, n = [re.search(r"\.GCLK\(([^)]*)\)", m.group(3)).group(1).strip()], 0
    while todo:                               # through the clock-tree buffers to the flip-flops
        for c, out in loads.get(todo.pop(), []):
            if out is None: n += 1
            else: todo.append(out)
    return n
m = max(cells, key=fanout)
body = re.sub(r"\.GATE\s*\([^)]*\)", ".GATE(1'b0)", m.group(3), count=1)
s = s[:m.start(3)] + body + s[m.end(3):]
open(p, "w").write(s); print("icg fault in", m.group(2), "gating", fanout(m), "flip-flops")
PY
fi
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
yosys -q -l "$W/flatten.log" -p "read_verilog $D/icg_models.v; proc; read_liberty -ignore_miss_func -ignore_miss_dir -ignore_redef $LIB; read_verilog $W/net.v; hierarchy -top tcim_chip_digital; proc; flatten; opt_clean; rename tcim_chip_digital tcim_chip_core; write_verilog -noattr $W/gl_flat.v"
echo YOSYS=$? >> "$W/flatten.log"
$VERILATOR_ROOT/bin/verilator --cc --exe --build -j 2 -O3 -Wno-fatal -Wno-lint -Wno-style --top-module tcim_chip_core \
  -Mdir "$W/obj" -CFLAGS "-std=c++17 -O1 -DTCIM_CHIP -DTCIM_CHIP_TIES -I$R/tb/verilator" "$W/gl_flat.v" "$R/tb/tb_tcim.cc" -o tb_gls > "$W/build.log" 2>&1
echo BUILD=$? >> "$W/build.log"
if [ -n "$FAULT" ]; then export TB_FAIL_FAST=1; fi
export TB_CFG=${TB_CFG:-1,1,0}
"$W/obj/tb_gls" "$R/tb/vectors" > "$W/tb_gls.log" 2>&1
echo EXIT=$? >> "$W/tb_gls.log"
tail -3 "$W/tb_gls.log"
grep -q "TEST PASSED" "$W/tb_gls.log"       # exit status: 0 when the test bench passed
