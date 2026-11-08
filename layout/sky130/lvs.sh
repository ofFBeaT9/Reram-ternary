#!/bin/bash
# LVS of the SKY130 tile: magic-extracted netlist against schematic.spice, then against schematic_fault.spice
# (one ReRAM element on the wrong bit line), which must fail. netgen with the sky130B setup file.
S=$PDK_ROOT/sky130B/libs.tech/netgen/sky130B_setup.tcl
netgen -batch lvs "tcim_sky130_array.spice tcim_sky130_array" "schematic.spice tcim_sky130_array" $S lvs.out -json > lvs.log 2>&1
netgen -batch lvs "tcim_sky130_array.spice tcim_sky130_array" "schematic_fault.spice tcim_sky130_array" $S lvs_fault.out > lvs_fault.log 2>&1
echo "LVS:        $(grep -E 'Netlists match|Netlists do not match|Final result' lvs.out | tail -2 | tr '\n' ' ')"
echo "LVS fault:  $(grep -E 'Netlists match|Netlists do not match|Final result' lvs_fault.out | tail -2 | tr '\n' ' ')"
