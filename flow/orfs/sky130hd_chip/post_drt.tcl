# Sourced by ORFS detail_route.tcl after its own antenna repair (POST_DETAIL_ROUTE_TCL), 12 October 2026.
# Magic's antenna check of the assembled chip flagged four gates of this block that OpenROAD passes (two of them located at 96 % and 67 %
# of its limits; layout/sky130/periph/antenna_crosscheck.py). Magic's figure for the via between metal4 and metal5 is about
# four times stricter than the LEF rule, so repair again with a 76 % margin: a diode on every net that OpenROAD puts above
# 24 % of a limit, then route again. (A 40 % margin, batch 15, cleared three of the four.)
puts "TCIM_POST_DRT: repair_antennas -ratio_margin 76"
set tcim_n0 [llength [lsearch -all -inline [lmap i [[ord::get_db_block] getInsts] {[$i getMaster] getName}] "sky130_fd_sc_hd__diode_2"]]
# the arguments of the flow's own detailed_route call (5_2_route.log of batch 7); this file is sourced inside a procedure
set tcim_args [list -output_drc $::env(REPORTS_DIR)/5_route_drc.rpt -output_maze $::env(RESULTS_DIR)/maze.log \
               -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5]
if { [info exists ::all_args] } { set tcim_args $::all_args }
# one iteration and diodes only: with detailed routing as the source OpenROAD allows one iteration, and its jumper
# insertion stopped with GRT-0127 in batch 17
if { [repair_antennas -ratio_margin 76 -iterations 1 -diode_only] } {
  detailed_route {*}$tcim_args
}
# routing around the new diodes can push a few nets over the limit itself: repair those at the normal limit (margin 0)
for {set k 0} {$k < 3 && [check_antennas] > 0} {incr k} {
  puts "TCIM_POST_DRT: repair at margin 0, pass $k"
  repair_antennas -iterations 1 -diode_only
  detailed_route {*}$tcim_args
}
# revision 4.7 (batch 27): a net the margin-0 pass leaves exactly at OpenROAD's limit (ratio 1.00 on metal3) was 5 % over it in
# Magic's check of the assembled chip (420.6 against 400). Last pass: a diode on every net above 85 % of a limit, route again,
# then the margin-0 repair once more.
puts "TCIM_POST_DRT: final repair_antennas -ratio_margin 15"
if { [repair_antennas -ratio_margin 15 -iterations 1 -diode_only] } {
  detailed_route {*}$tcim_args
}
for {set k 0} {$k < 3 && [check_antennas] > 0} {incr k} {
  puts "TCIM_POST_DRT: final repair at margin 0, pass $k"
  repair_antennas -iterations 1 -diode_only
  detailed_route {*}$tcim_args
}
set tcim_n1 [llength [lsearch -all -inline [lmap i [[ord::get_db_block] getInsts] {[$i getMaster] getName}] "sky130_fd_sc_hd__diode_2"]]
puts "TCIM_POST_DRT: diodes before $tcim_n0, after $tcim_n1"
check_antennas
