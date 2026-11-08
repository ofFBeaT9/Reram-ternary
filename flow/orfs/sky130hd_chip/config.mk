# OpenROAD-flow-scripts configuration: digital part of the SKY130 test chip (TCIM0 + array controller,
# rtl/chip/tcim_chip_core.sv), sky130hd cells, sky130B technology LEF, slow-corner library (as sky130hd_b).
# Macro-side pins (to the analog macro) on the top edge, pad-side pins on the bottom edge; VPWR/VGND rings on
# met4/met5 around the core for the connection to vccd1/vssd1 in the Caravan wrapper. 11 October 2026.
export DESIGN_NAME     = tcim_chip_digital
export DESIGN_NICKNAME = tcim_chip_digital
export PLATFORM        = sky130hd
TCIM_FLOW             ?= /design

export VERILOG_FILES = $(TCIM_FLOW)/src/tcim_chip_digital.v
export SDC_FILE      = $(TCIM_FLOW)/sky130hd_chip/constraint.sdc
export IO_CONSTRAINTS = $(TCIM_FLOW)/sky130hd_chip/io.tcl
export PDN_TCL       = $(TCIM_FLOW)/sky130hd_chip/pdn.tcl

# revision 4.6 (4 November 2026): the die and core of revision 4.5 kept exactly (they came from utilization 40,
# aspect ratio 0.6, margin 16), so that the top level (layout/sky130/periph/top.py) places and connects the block as
# before; the block grew from 60,400 to 82,400 um^2 of cells (yosys + abc on the typical library, before buffering).
export DIE_AREA        ?= 0 0 550.32 342.995
export CORE_AREA       ?= 16.1 16.32 534.06 326.4
export PLACE_DENSITY   ?= 0.72
export TNS_END_PERCENT  = 100

export INFER_CLKGATES        = 1
export POS_CLKGATE_AND_PORTS = sky130_fd_sc_hd__dlclkp_1 GATE:CLK:GCLK

# antenna repair with a 76 % margin after detailed routing (12 October 2026; sky130hd_chip/post_drt.tcl)
export POST_DETAIL_ROUTE_TCL = $(TCIM_FLOW)/sky130hd_chip/post_drt.tcl
