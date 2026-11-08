# OpenROAD-flow-scripts design configuration: TCIM0 digital block on SkyWater SKY130 (sky130_fd_sc_hd), block level.
# Run on the PC: revision 4.2 (8 October 2026, out42, results/rev42) and revision 4.3 with clock gating (out43, results/pnr.json).
export DESIGN_NAME     = tcim_top
export DESIGN_NICKNAME = tcim_top
export PLATFORM        = sky130hd
TCIM_FLOW             ?= /design

export VERILOG_FILES = $(TCIM_FLOW)/src/tcim_top.v
export SDC_FILE      = $(TCIM_FLOW)/sky130hd/constraint.sdc

export CORE_UTILIZATION = 40
export PLACE_DENSITY   ?= 0.60
export TNS_END_PERCENT  = 100

# Revision 4.3: integrated clock gating. Yosys clockgate gives every group of flip-flops that shares an enable a
# clock-gating cell of the library (the RTL is unchanged; same transformation as synth/run_synth.sh with CLKGATE).
export INFER_CLKGATES        = 1
export POS_CLKGATE_AND_PORTS = sky130_fd_sc_hd__dlclkp_1 GATE:CLK:GCLK
