#!/bin/bash
# Size and delay of the integer-to-tryte conversion alone, as a chain of dividers and as a table.
# Needs yosys with slang, OpenSTA, IHP_STDCELL_LIB. Writes results/conv_study.json.
set -e
cd "$(dirname "$0")/../.."
W=synth/conv_study/build; mkdir -p $W
LIB=${IHP_STDCELL_LIB:?set IHP_STDCELL_LIB}
printf 'set_driving_cell sg13g2_buf_4\nset_load 6\n' > $W/c.constr
cat > $W/sta.tcl <<TCL
read_liberty $LIB
read_verilog \$::env(NETLIST)
link_design conv_wrap
create_clock -name clk -period 10 [get_ports clk]
puts "@@ [expr 10.0 - [sta::worst_slack_cmd max]*1e9]"
TCL
OUT="{"
for V in chain table; do
  D=""; [ $V = chain ] && D="-D CONV_CHAIN"
  yosys -q -l $W/$V.log -p "read_slang $D --top conv_wrap rtl/tcim_pkg.sv synth/conv_study/conv_wrap.sv; hierarchy -top conv_wrap; synth -top conv_wrap -flatten; dfflibmap -liberty $LIB; abc -liberty $LIB -D 3000 -constr $W/c.constr; opt_clean -purge; stat -liberty $LIB; write_verilog -noattr -noexpr -nohex -nodec $W/$V.v"
  CELLS=$(grep -E "^ +[0-9]+ +[0-9.E+]+ cells$" $W/$V.log | tail -1 | awk '{print $1}')
  PATHNS=$(NETLIST=$W/$V.v sta -no_init -exit $W/sta.tcl 2>&1 | grep "^@@" | awk '{printf "%.2f", $2}')
  echo "$V: $CELLS cells (22 of them flip-flops), register-to-register path $PATHNS ns"
  OUT="$OUT\"$V\": {\"cells_with_22_flip_flops\": $CELLS, \"path_ns\": $PATHNS},"
done
echo "${OUT%,}, \"note\": \"IHP SG13G2 typical corner, mapped for a 3 ns target, no wires; path includes clock-to-output and setup of the two registers\"}" > results/conv_study.json
