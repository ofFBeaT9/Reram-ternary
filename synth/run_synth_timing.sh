#!/bin/bash
# Timing-driven synthesis of one top module for static timing analysis (make sta).
#   usage: synth/run_synth_timing.sh <tag> <liberty> <clock period in ps> <top> <source files...>
# Differs from run_synth.sh (the minimum-area netlist behind the area and energy numbers): ABC is given the
# clock period, a driving cell and a load, so it sizes gates and inserts buffers. Environment: SYNTH_DEFS,
# e.g. "-D TCIM_ENC_PNX"; ABC_DRIVER, ABC_LOAD (fF) override the constraint file.
set -e
TAG=$1; LIB=$2; PERIOD=$3; TOP=$4; shift 4
OUT=$(dirname "$0")/build_sta
mkdir -p "$OUT"
DRV=${ABC_DRIVER:?set ABC_DRIVER to a buffer cell of the library}
echo "set_driving_cell $DRV" >  "$OUT/$TOP.$TAG.constr"
echo "set_load ${ABC_LOAD:-10}" >> "$OUT/$TOP.$TAG.constr"
cat > "$OUT/$TOP.$TAG.ys" <<YS
read_slang $SYNTH_DEFS --top $TOP $@
hierarchy -top $TOP
synth -top $TOP -flatten
dfflibmap -liberty $LIB
abc -liberty $LIB -D $PERIOD -constr $OUT/$TOP.$TAG.constr
opt_clean -purge
hilomap -singleton -hicell ${TIEHI:?set TIEHI="cell port"} -locell ${TIELO:?set TIELO="cell port"}
splitnets -format __
opt_clean -purge
stat -liberty $LIB
write_verilog -noattr -noexpr -nohex -nodec $OUT/$TOP.$TAG.v
YS
yosys -q -l "$OUT/$TOP.$TAG.log" "$OUT/$TOP.$TAG.ys"
grep -A400 "Printing statistics" "$OUT/$TOP.$TAG.log" | grep -E "Number of cells|Chip area" | head -3
