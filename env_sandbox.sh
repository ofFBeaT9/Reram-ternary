# Tool paths used in the cloud sandbox (source this file). On another machine set the same three variables.
export PATH=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/tools/prefix/bin:$PATH
export LD_LIBRARY_PATH=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/tools/prefix/lib:$LD_LIBRARY_PATH
export IHP_GNUCAP=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/src/IHP-Open-PDK/ihp-sg13g2/libs.tech/gnucap
export IHP_STDCELL_LIB=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
# Verilator 5 (make lint, rtl-verilator, gls), SymbiYosys (make formal), OpenSTA is in the prefix above
export VERILATOR_ROOT=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/ext/verilator
export SBY="python3 /tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/ext/sby/sbysrc/sby.py"
export SKY130_FD_PR=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/sky130pdk/fd_pr
export SKY130_STDCELL_LIB=/tmp/claude-0/-home-claude/56ca8d3c-a497-5f0b-b50b-013425ed5316/scratchpad/sky130/sky130_fd_sc_hd__tt_025C_1v80.lib
