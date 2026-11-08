# Copy to env.sh, set the three paths for your machine, then:  source env.sh
PREFIX=$HOME/reram-tools/prefix                       # where tools/build_tools.sh installed the simulators
PDK=$HOME/reram-tools/src/IHP-Open-PDK                # a clone of https://github.com/IHP-GmbH/IHP-Open-PDK
export PATH=$PREFIX/bin:$PATH
export LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH
export IHP_GNUCAP=$PDK/ihp-sg13g2/libs.tech/gnucap
export IHP_STDCELL_LIB=$PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
# optional, for the targets added in revision 4.2
export VERILATOR_ROOT=$HOME/reram-tools/verilator      # a Verilator 5 build (make lint, rtl-verilator, gls)
export SBY="sby"                                       # SymbiYosys, https://github.com/YosysHQ/sby (make formal)
export SKY130_FD_PR=$HOME/reram-tools/skywater-pdk-libs-sky130_fd_pr   # make sky130-port
export SKY130_STDCELL_LIB=$PDK/../sky130_fd_sc_hd__tt_025C_1v80.lib     # make sta, SKY130 corner
