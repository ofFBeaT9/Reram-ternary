#!/bin/bash
# FPGA demonstration checks in the sandbox (9 October 2026):
#  1. RTL simulation (Verilator, SystemVerilog source) + host test, spread banks 0/1/2
#  2. synthesis for the GW1NR-9 with Yosys (slang front end) at DIV=8, gate-level simulation of the mapped netlist
#     (Yosys' Gowin cell models + tb/fpga/gowin_models.v for the block RAM) + host test, bank 0
#  3. board synthesis (DIV=117: 115200 baud at 13.5 MHz, clock from the PLL: TCIM_FPGA_PLL): $OB/tcim_fpga_syn.json for nextpnr on the PC
# FPGA_BUILD / FPGA_RESULTS (default rtl/fpga/build, results/fpga): where the netlists and results go. Revision 4.6
# writes to rtl/fpga/build_rev46 and results/fpga/rev46, so the bitstream of the board runs and its results stay as they are.
set -e
cd "$(dirname "$0")/../.."
export OB=${FPGA_BUILD:-rtl/fpga/build} RF=${FPGA_RESULTS:-results/fpga}
source env_sandbox.sh
VL=$VERILATOR_ROOT/bin/verilator
SH=$(dirname $(which yosys))/../share/yosys/gowin
# revision 4.6: the dummy accumulators of tcim_core do not fit the GW1NR-9 (TCIM_NO_DUMMY removes them here only)
FP="rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/fpga/arr_emu.sv rtl/fpga/uart.sv rtl/fpga/tcim_fpga_top.sv"
export B=${FPGA_TBBUILD:-tb/fpga/build}; mkdir -p $B $RF $OB
python3 tools/make_devlut.py
$VL --lint-only +define+TCIM_NO_DUMMY -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Irtl/fpga --top-module tcim_fpga_top $FP 2>&1 | tee $RF/lint.log
$VL --cc --exe --build +define+TCIM_NO_DUMMY -j 2 -O3 -Wno-fatal -Wno-PROCASSINIT -Irtl/fpga --top-module tcim_fpga_top -GDIV=8 -Mdir $B/rtl -CFLAGS -O2 $FP tb/fpga/tb_fpga.cc > $B/rtl.log 2>&1
for b in 0 1 2; do python3 tools/fpga_host.py --sim $B/rtl/Vtcim_fpga_top --products 100 --bank $b --noise 1 --json $RF/sim_bank$b.json > /dev/null; done
yosys -l $B/syn8.log -q -p "read_slang -D TCIM_NO_DUMMY -I rtl/fpga -G DIV=8 --top tcim_fpga_top $FP; hierarchy -top tcim_fpga_top; synth_gowin -top tcim_fpga_top; write_verilog -noattr $B/syn8.v"
sed -e '/^module DPB(/,/^endmodule/d' -e '/^module MULT18X18(/,/^endmodule/d' -e '/^module MULT9X9(/,/^endmodule/d' $SH/cells_xtra_gw1n.v > $B/cells_xtra_nodpb.v; sed -e '/^module SPX9 (/,/^endmodule/d' $SH/cells_sim.v > $B/cells_sim_nospx9.v
# every cell in the netlist must have a behavioural model (Yosys ships DPB, SPX9 and MULT18X18 as black boxes;
# tb/fpga/gowin_models.v supplies them); a black box would simulate as constant outputs
python3 - "$B/syn8.v" "$B/cells_sim_nospx9.v" "$B/cells_xtra_nodpb.v" tb/fpga/gowin_models.v <<'PY'
import re, sys
net = open(sys.argv[1]).read(); lib = "".join(open(f).read() for f in sys.argv[2:])
bad = []
for c in sorted(set(re.findall(r"^  ([A-Z][A-Z0-9_]+) ", net, re.M))):
    bodies = [m.group(0) for m in re.finditer(r"^module " + c + r"\b.*?^endmodule", lib, re.M | re.S)]
    if len(bodies) != 1 or not re.search(r"\balways\b|\bassign\b|^\s*[A-Z][A-Z0-9_]+ ", bodies[0][20:], re.M):
        bad.append((c, len(bodies)))
print("cells without a single behavioural model:", bad)
sys.exit(1 if bad else 0)
PY
$VL --cc --exe --build -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tcim_fpga_top -Mdir $B/gls -CFLAGS -O1 \
    $B/syn8.v $B/cells_sim_nospx9.v $B/cells_xtra_nodpb.v tb/fpga/gowin_models.v tb/fpga/tb_fpga.cc > $B/gls.log 2>&1
python3 tools/fpga_host.py --sim $B/gls/Vtcim_fpga_top --products 100 --bank 0 --noise 1 --json $RF/gls_bank0.json > /dev/null
python3 tools/fpga_host.py --sim $B/rtl/Vtcim_fpga_top --products 100 --bank 0 --noise 1 --json $B/rtl_bank0_again.json > /dev/null
yosys -l $RF/yosys_board.log -q -p "read_slang -D TCIM_FPGA_PLL -D TCIM_NO_DUMMY -I rtl/fpga --top tcim_fpga_top rtl/fpga/rpll_bb.sv $FP; hierarchy -top tcim_fpga_top; synth_gowin -top tcim_fpga_top -json $OB/tcim_fpga_syn.json; tee -o $RF/yosys_stat.txt stat"
yosys -V > $RF/yosys_version.txt
python3 - <<'PY'
import json
import os; RF, OB, B = os.environ["RF"], os.environ["OB"], os.environ["B"]
r = json.load(open(f"{RF}/gls_bank0.json")); s = json.load(open(f"{B}/rtl_bank0_again.json"))
for d in (r, s): d.pop("host_seconds")
print("gate-level run identical to RTL run (same seed, same cycle-exact behaviour):", r == s)
json.dump(dict(identical=r == s, gls=r, rtl=s), open(f"{RF}/gls_vs_rtl.json", "w"), indent=1)
PY
# 4. every multiplier of the board netlist must be unsigned (ASIGN = BSIGN = GND): on the GW1NR-9 board a signed product
#    of a negative operand was wrong (10 October 2026) although the gate-level model agreed with the RTL
python3 - <<'PY'
import json, sys
import os; RF, OB = os.environ["RF"], os.environ["OB"]
m = json.load(open(f"{OB}/tcim_fpga_syn.json"))["modules"]["tcim_fpga_top"]
drv = {}
for c in m["cells"].values():
    for p, b in c["connections"].items():
        if c["port_directions"].get(p) == "output":
            for x in b: drv[x] = c["type"]
bad = []
for n, c in m["cells"].items():
    if c["type"].startswith("MULT"):
        for p in ("ASIGN", "BSIGN"):
            b = c["connections"][p][0]
            if not (b == "0" or drv.get(b) == "GND"): bad.append((n[-30:], p, drv.get(b, b)))
print("signed multipliers in the board netlist:", bad)
json.dump(dict(signed_multipliers=bad), open(f"{RF}/mult_sign_check.json", "w"))
sys.exit(1 if bad else 0)
PY
