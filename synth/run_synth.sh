#!/bin/bash
# Synthesize one top module on the IHP SG13G2 standard cells (typical corner, 1.2 V, 25 C).
#   usage: synth/run_synth.sh <top> <source files...>
# Needs: yosys with the slang front end; IHP_STDCELL_LIB = path to sg13g2_stdcell_typ_1p20V_25C.lib
# CLKGATE="<cell> <enable>:<clock>:<gated clock>" (e.g. "sg13g2_lgcp_1 GATE:CLK:GCLK"): every group of flip-flops that
# shares an enable gets an integrated clock-gating cell (Yosys clockgate, as INFER_CLKGATES in OpenROAD-flow-scripts);
# the outputs are then named <top>_cg.*
set -e
TOP=$1; shift
LIB=${IHP_STDCELL_LIB:?set IHP_STDCELL_LIB}
OUT=$(dirname "$0")/build
NAME=$TOP${CLKGATE:+_cg}
CGCMD=${CLKGATE:+clockgate -pos $CLKGATE}
mkdir -p "$OUT"
cat > "$OUT/$NAME.ys" <<YS
read_slang --top $TOP $@
hierarchy -top $TOP
synth -top $TOP -flatten
$CGCMD
dfflibmap -liberty $LIB
abc -liberty $LIB
opt_clean -purge
stat -liberty $LIB
write_json $OUT/$NAME.json
write_verilog -noattr $OUT/$NAME.mapped.v
YS
yosys -q -l "$OUT/$NAME.log" "$OUT/$NAME.ys"
grep -A200 "Printing statistics" "$OUT/$NAME.log" | grep -E "Number of cells|Chip area|sg13g2_df|sg13g2_dl" | head -12
